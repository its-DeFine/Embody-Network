"""
Audit API endpoints
Provides access to audit logs and system history
"""

from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends
import logging

from ..dependencies import get_current_user
from ..infrastructure.monitoring.audit_logger import audit_logger, AuditEventType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/audit", 
    tags=["audit"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/events")
async def get_audit_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return")
):
    """Get audit events with filtering"""
    
    # Convert event type string to enum
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = AuditEventType(event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
    
    events = await audit_logger.query_events(
        event_type=event_type_enum,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    # Filter by severity if requested
    if severity:
        events = [e for e in events if e.get("severity") == severity]
    
    return events


@router.get("/trades")
async def get_trade_history(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    success_only: bool = Query(True, description="Only show successful trades")
):
    """Get trade history from audit logs"""
    
    trades = await audit_logger.get_trade_history(symbol=symbol, days=days)
    
    if success_only:
        trades = [t for t in trades if t["data"].get("success", True)]
    
    return {
        "trades": trades,
        "count": len(trades),
        "period_days": days,
        "symbol_filter": symbol
    }


@router.get("/portfolio-snapshots")
async def get_portfolio_snapshots(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """Get portfolio snapshots over time"""
    
    start_date = datetime.utcnow() - timedelta(hours=hours)
    
    snapshots = await audit_logger.query_events(
        event_type=AuditEventType.PORTFOLIO_SNAPSHOT,
        start_date=start_date,
        limit=hours  # Roughly one per hour
    )
    
    return {
        "snapshots": snapshots,
        "count": len(snapshots),
        "period_hours": hours
    }


@router.get("/risk-events")
async def get_risk_events(
    days: int = Query(7, ge=1, le=30, description="Days to look back")
):
    """Get risk-related events"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Query multiple risk event types
    risk_types = [
        AuditEventType.RISK_LIMIT_HIT,
        AuditEventType.STOP_LOSS_TRIGGERED,
        AuditEventType.EMERGENCY_STOP
    ]
    
    all_events = []
    for risk_type in risk_types:
        events = await audit_logger.query_events(
            event_type=risk_type,
            start_date=start_date
        )
        all_events.extend(events)
    
    # Sort by timestamp
    all_events.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "risk_events": all_events,
        "count": len(all_events),
        "period_days": days
    }


@router.get("/system-health")
async def get_system_health_report():
    """Get system health report from audit logs"""
    
    report = await audit_logger.get_system_health_report()
    
    # Add current status
    report["current_status"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "health_score": calculate_health_score(report)
    }
    
    return report


@router.get("/agent-activity")
async def get_agent_activity(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
):
    """Get agent activity from audit logs"""
    
    start_date = datetime.utcnow() - timedelta(hours=hours)
    
    # Query agent events
    agent_types = [
        AuditEventType.AGENT_CREATED,
        AuditEventType.AGENT_STARTED,
        AuditEventType.AGENT_STOPPED,
        AuditEventType.AGENT_ERROR
    ]
    
    all_events = []
    for agent_type in agent_types:
        events = await audit_logger.query_events(
            event_type=agent_type,
            start_date=start_date
        )
        
        # Filter by agent ID if specified
        if agent_id:
            events = [e for e in events if e["data"].get("agent_id") == agent_id]
            
        all_events.extend(events)
    
    return {
        "agent_events": all_events,
        "count": len(all_events),
        "period_hours": hours,
        "agent_filter": agent_id
    }


@router.post("/export")
async def export_audit_data(
    format: str = Query("json", enum=["json", "csv"], description="Export format"),
    days: int = Query(7, ge=1, le=90, description="Days to export"),
    event_type: Optional[str] = Query(None, description="Filter by event type")
):
    """Export audit data for analysis"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    try:
        export_file = await audit_logger.export_audit_data(
            format=format,
            start_date=start_date,
            end_date=datetime.utcnow()
        )
        
        return {
            "status": "success",
            "file": export_file,
            "format": format,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{event_id}")
async def verify_event_integrity(event_id: str):
    """Verify the integrity of a specific audit event"""
    
    # Get event
    events = await audit_logger.query_events(limit=10000)
    event = next((e for e in events if e["id"] == event_id), None)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Verify checksum
    original_checksum = event["checksum"]
    calculated_checksum = audit_logger._calculate_checksum(event)
    
    return {
        "event_id": event_id,
        "timestamp": event["timestamp"],
        "type": event["type"],
        "integrity_valid": original_checksum == calculated_checksum,
        "original_checksum": original_checksum,
        "calculated_checksum": calculated_checksum
    }


def calculate_health_score(report: dict) -> float:
    """Calculate overall health score from report"""
    
    score = 100.0
    
    # Deduct for failed trades
    if report["trades"]["total"] > 0:
        failure_rate = report["trades"]["failed"] / report["trades"]["total"]
        score -= failure_rate * 20
    
    # Deduct for errors
    score -= min(report["errors"]["total"] * 2, 30)
    
    # Deduct for risk events
    score -= report["risk_events"]["stop_losses"] * 5
    score -= report["risk_events"]["risk_limits"] * 10
    score -= report["risk_events"]["emergency_stops"] * 20
    
    # Deduct for system restarts
    score -= report["system_events"]["restarts"] * 15
    
    return max(0, min(100, score))