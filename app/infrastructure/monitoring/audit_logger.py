"""
Comprehensive Audit Logging System
Records all trading activities, decisions, and system events
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import aiofiles
from pathlib import Path
import hashlib
import gzip

from ...dependencies import get_redis
from ..database.models import Trade, Position

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events"""
    # Trading events
    TRADE_EXECUTED = "trade_executed"
    TRADE_FAILED = "trade_failed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    STRATEGY_CHANGE = "strategy_change"
    CONFIG_UPDATE = "config_update"
    
    # Market events
    PRICE_UPDATE = "price_update"
    MARKET_SIGNAL = "market_signal"
    ANOMALY_DETECTED = "anomaly_detected"
    
    # Risk events
    RISK_LIMIT_HIT = "risk_limit_hit"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    EMERGENCY_STOP = "emergency_stop"
    
    # Agent events
    AGENT_CREATED = "agent_created"
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    
    # Financial events
    PNL_UPDATE = "pnl_update"
    PORTFOLIO_SNAPSHOT = "portfolio_snapshot"
    CAPITAL_CHANGE = "capital_change"


class AuditLogger:
    """
    Centralized audit logging system with multiple storage backends
    """
    
    def __init__(self):
        # Use environment variable for data directory, fallback to temp in tests
        data_path = os.environ.get("AUDIT_DATA_DIR", "/app/data/audit")
        if not os.access(Path(data_path).parent, os.W_OK):
            # If we can't write to the parent directory, use temp directory
            import tempfile
            data_path = os.path.join(tempfile.gettempdir(), "audit")
        
        self.data_dir = Path(data_path)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.redis = None
        self.current_log_file = None
        self.log_buffer = []
        self.buffer_size = 100
        self.flush_interval = 30  # seconds
        
        # Separate logs by type
        self.log_types = {
            "trades": self.data_dir / "trades",
            "system": self.data_dir / "system",
            "financial": self.data_dir / "financial",
            "errors": self.data_dir / "errors"
        }
        
        for log_dir in self.log_types.values():
            log_dir.mkdir(exist_ok=True)
            
    async def initialize(self):
        """Initialize the audit logger"""
        self.redis = await get_redis()
        
        # Start background tasks
        asyncio.create_task(self._flush_logs_periodically())
        asyncio.create_task(self._rotate_logs_daily())
        
        await self.log_event(
            AuditEventType.SYSTEM_START,
            {"message": "Audit logging system initialized"}
        )
        
    async def log_event(
        self,
        event_type: AuditEventType,
        data: Dict[str, Any],
        severity: str = "INFO"
    ):
        """Log an audit event"""
        event = {
            "id": self._generate_event_id(),
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type.value,
            "severity": severity,
            "data": data,
            "checksum": None  # Will be calculated
        }
        
        # Calculate checksum for integrity
        event["checksum"] = self._calculate_checksum(event)
        
        # Add to buffer
        self.log_buffer.append(event)
        
        # Store in Redis for real-time access
        await self._store_in_redis(event)
        
        # Flush if buffer is full
        if len(self.log_buffer) >= self.buffer_size:
            await self._flush_logs()
            
        # Log critical events immediately
        if severity in ["ERROR", "CRITICAL"]:
            await self._flush_logs()
            
    async def log_trade(self, trade: Trade, success: bool = True):
        """Log trade execution"""
        event_type = AuditEventType.TRADE_EXECUTED if success else AuditEventType.TRADE_FAILED
        
        await self.log_event(
            event_type,
            {
                "trade_id": trade.id,
                "symbol": trade.symbol,
                "action": trade.action,
                "quantity": float(trade.quantity),
                "price": float(trade.price),
                "total": float(trade.total),
                "strategy": trade.strategy,
                "timestamp": trade.timestamp,
                "success": success
            },
            severity="INFO" if success else "ERROR"
        )
        
    async def log_position_change(
        self,
        position: Position,
        action: str,
        pnl: Optional[float] = None
    ):
        """Log position changes"""
        event_type = (
            AuditEventType.POSITION_OPENED if action == "open" 
            else AuditEventType.POSITION_CLOSED
        )
        
        data = {
            "position_id": position.id,
            "symbol": position.symbol,
            "quantity": float(position.quantity),
            "entry_price": float(position.entry_price),
            "action": action
        }
        
        if pnl is not None:
            data["realized_pnl"] = pnl
            
        await self.log_event(event_type, data)
        
    async def log_portfolio_snapshot(self, portfolio_data: Dict[str, Any]):
        """Log periodic portfolio snapshot"""
        await self.log_event(
            AuditEventType.PORTFOLIO_SNAPSHOT,
            {
                "capital": portfolio_data.get("capital"),
                "total_value": portfolio_data.get("total_value"),
                "positions": portfolio_data.get("positions", {}),
                "daily_pnl": portfolio_data.get("daily_pnl"),
                "total_pnl": portfolio_data.get("total_pnl"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    async def log_risk_event(self, risk_type: str, details: Dict[str, Any]):
        """Log risk-related events"""
        event_map = {
            "limit_hit": AuditEventType.RISK_LIMIT_HIT,
            "stop_loss": AuditEventType.STOP_LOSS_TRIGGERED,
            "emergency": AuditEventType.EMERGENCY_STOP
        }
        
        await self.log_event(
            event_map.get(risk_type, AuditEventType.RISK_LIMIT_HIT),
            details,
            severity="WARNING" if risk_type != "emergency" else "CRITICAL"
        )
        
    async def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit events"""
        # Query from Redis for recent events
        events = []
        
        # Get from Redis
        if event_type:
            key = f"audit:events:{event_type.value}"
        else:
            key = "audit:events:*"
            
        # This is simplified - in production use Redis search
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=key, count=100
            )
            
            for k in keys:
                event_data = await self.redis.get(k)
                if event_data:
                    event = json.loads(event_data)
                    
                    # Filter by date
                    event_time = datetime.fromisoformat(event["timestamp"])
                    if start_date and event_time < start_date:
                        continue
                    if end_date and event_time > end_date:
                        continue
                        
                    events.append(event)
                    
            if cursor == 0 or len(events) >= limit:
                break
                
        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return events[:limit]
        
    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get trade history"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        trades = await self.query_events(
            event_type=AuditEventType.TRADE_EXECUTED,
            start_date=start_date
        )
        
        if symbol:
            trades = [t for t in trades if t["data"].get("symbol") == symbol]
            
        return trades
        
    async def get_system_health_report(self) -> Dict[str, Any]:
        """Generate system health report from audit logs"""
        # Get last 24 hours of events
        start_date = datetime.utcnow() - timedelta(days=1)
        
        all_events = await self.query_events(start_date=start_date, limit=10000)
        
        # Analyze events
        report = {
            "period": "last_24_hours",
            "total_events": len(all_events),
            "trades": {
                "total": 0,
                "successful": 0,
                "failed": 0
            },
            "errors": {
                "total": 0,
                "by_type": {}
            },
            "system_events": {
                "restarts": 0,
                "config_changes": 0
            },
            "risk_events": {
                "stop_losses": 0,
                "risk_limits": 0,
                "emergency_stops": 0
            }
        }
        
        for event in all_events:
            event_type = event["type"]
            
            if event_type == AuditEventType.TRADE_EXECUTED.value:
                report["trades"]["total"] += 1
                report["trades"]["successful"] += 1
            elif event_type == AuditEventType.TRADE_FAILED.value:
                report["trades"]["total"] += 1
                report["trades"]["failed"] += 1
            elif event["severity"] == "ERROR":
                report["errors"]["total"] += 1
                error_type = event["data"].get("error_type", "unknown")
                report["errors"]["by_type"][error_type] = \
                    report["errors"]["by_type"].get(error_type, 0) + 1
            elif event_type == AuditEventType.SYSTEM_START.value:
                report["system_events"]["restarts"] += 1
            elif event_type == AuditEventType.CONFIG_UPDATE.value:
                report["system_events"]["config_changes"] += 1
            elif event_type == AuditEventType.STOP_LOSS_TRIGGERED.value:
                report["risk_events"]["stop_losses"] += 1
            elif event_type == AuditEventType.RISK_LIMIT_HIT.value:
                report["risk_events"]["risk_limits"] += 1
            elif event_type == AuditEventType.EMERGENCY_STOP.value:
                report["risk_events"]["emergency_stops"] += 1
                
        return report
        
    async def export_audit_data(
        self,
        format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Export audit data for analysis"""
        events = await self.query_events(
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )
        
        export_file = self.data_dir / f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        if format == "json":
            async with aiofiles.open(export_file, 'w') as f:
                await f.write(json.dumps(events, indent=2))
        elif format == "csv":
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            if events:
                writer = csv.DictWriter(
                    output,
                    fieldnames=["timestamp", "type", "severity", "data", "checksum"]
                )
                writer.writeheader()
                
                for event in events:
                    row = {
                        "timestamp": event["timestamp"],
                        "type": event["type"],
                        "severity": event["severity"],
                        "data": json.dumps(event["data"]),
                        "checksum": event["checksum"]
                    }
                    writer.writerow(row)
                    
            async with aiofiles.open(export_file, 'w') as f:
                await f.write(output.getvalue())
                
        # Compress if large
        if export_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
            compressed_file = export_file.with_suffix(export_file.suffix + '.gz')
            
            with open(export_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.writelines(f_in)
                    
            os.remove(export_file)
            return str(compressed_file)
            
        return str(export_file)
        
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.utcnow().timestamp()
        random_part = os.urandom(8).hex()
        return f"{int(timestamp)}-{random_part}"
        
    def _calculate_checksum(self, event: Dict[str, Any]) -> str:
        """Calculate event checksum for integrity verification"""
        # Remove checksum field for calculation
        event_copy = event.copy()
        event_copy.pop("checksum", None)
        
        # Create deterministic string representation
        event_str = json.dumps(event_copy, sort_keys=True)
        
        # Calculate SHA-256 checksum
        return hashlib.sha256(event_str.encode()).hexdigest()
        
    async def _store_in_redis(self, event: Dict[str, Any]):
        """Store event in Redis for real-time access"""
        # Store in type-specific key
        key = f"audit:events:{event['type']}:{event['id']}"
        
        # Store with expiration (7 days for non-critical events)
        ttl = 7 * 24 * 3600 if event["severity"] != "CRITICAL" else 30 * 24 * 3600
        
        await self.redis.setex(
            key,
            ttl,
            json.dumps(event)
        )
        
        # Also store in time-series for quick queries
        score = datetime.fromisoformat(event["timestamp"]).timestamp()
        await self.redis.zadd(
            f"audit:timeline:{event['type']}",
            {event["id"]: score}
        )
        
    async def _flush_logs(self):
        """Flush log buffer to disk"""
        if not self.log_buffer:
            return
            
        # Group by log type
        grouped_logs = {}
        for event in self.log_buffer:
            log_type = self._get_log_type(event["type"])
            if log_type not in grouped_logs:
                grouped_logs[log_type] = []
            grouped_logs[log_type].append(event)
            
        # Write to respective files
        for log_type, events in grouped_logs.items():
            log_dir = self.log_types[log_type]
            date_str = datetime.utcnow().strftime("%Y%m%d")
            log_file = log_dir / f"{date_str}.jsonl"
            
            async with aiofiles.open(log_file, 'a') as f:
                for event in events:
                    await f.write(json.dumps(event) + '\n')
                    
        # Clear buffer
        self.log_buffer = []
        
        logger.info(f"Flushed {len(self.log_buffer)} audit events to disk")
        
    async def _flush_logs_periodically(self):
        """Periodic log flushing"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self._flush_logs()
            
    async def _rotate_logs_daily(self):
        """Rotate logs daily and compress old ones"""
        while True:
            # Wait until next day
            now = datetime.utcnow()
            next_day = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            wait_seconds = (next_day - now).total_seconds()
            
            await asyncio.sleep(wait_seconds)
            
            # Compress yesterday's logs
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")
            
            for log_dir in self.log_types.values():
                log_file = log_dir / f"{yesterday}.jsonl"
                if log_file.exists():
                    compressed = log_file.with_suffix('.jsonl.gz')
                    
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed, 'wb') as f_out:
                            f_out.writelines(f_in)
                            
                    os.remove(log_file)
                    
            logger.info(f"Rotated logs for {yesterday}")
            
    def _get_log_type(self, event_type: str) -> str:
        """Determine log type from event type"""
        if "trade" in event_type or "position" in event_type:
            return "trades"
        elif "pnl" in event_type or "portfolio" in event_type or "capital" in event_type:
            return "financial"
        elif "error" in event_type or "fail" in event_type:
            return "errors"
        else:
            return "system"


# Global instance
audit_logger = AuditLogger()