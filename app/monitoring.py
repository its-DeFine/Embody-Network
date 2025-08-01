"""
Monitoring and health check system for the trading platform
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psutil
import os

from .services.trading_service import trading_service
from .models import storage

logger = logging.getLogger(__name__)


class SystemMonitor:
    """System resource monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "disk_total_gb": disk.total / (1024**3),
                "uptime_seconds": time.time() - self.start_time,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {"error": str(e)}


class TradingMonitor:
    """Trading system specific monitoring"""
    
    def __init__(self):
        self.alerts = []
        self.max_alerts = 100
        
    def check_trading_health(self) -> Dict[str, Any]:
        """Comprehensive trading system health check"""
        health_data = {
            "overall_status": "healthy",
            "checks": {},
            "alerts": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check trading service
            service_health = trading_service.get_system_health()
            if service_health["status"] == "success":
                trading_data = service_health["data"]
                health_data["checks"]["trading_service"] = {
                    "status": "healthy" if trading_data["is_running"] else "stopped",
                    "details": trading_data
                }
                
                # Check for alerts
                if not trading_data["is_running"]:
                    health_data["alerts"].append({
                        "level": "warning",
                        "message": "Trading system is not running",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                if trading_data.get("portfolio_value", 0) < 100:
                    health_data["alerts"].append({
                        "level": "critical",
                        "message": "Portfolio value is critically low",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                # Check performance
                total_return_pct = trading_data.get("portfolio_value", 1000) / 1000 - 1
                if total_return_pct < -0.2:  # More than 20% loss
                    health_data["alerts"].append({
                        "level": "critical",
                        "message": f"High losses detected: {total_return_pct*100:.2f}%",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            else:
                health_data["checks"]["trading_service"] = {
                    "status": "error",
                    "details": service_health
                }
                health_data["overall_status"] = "unhealthy"
            
            # Check portfolio status
            portfolio_status = trading_service.get_portfolio_status()
            if portfolio_status["status"] == "success":
                health_data["checks"]["portfolio"] = {
                    "status": "healthy",
                    "details": portfolio_status["data"]
                }
            else:
                health_data["checks"]["portfolio"] = {
                    "status": "error",
                    "details": portfolio_status
                }
                health_data["overall_status"] = "unhealthy"
            
            # Check recent trading activity
            recent_trades = trading_service.get_trade_history(limit=10)
            if recent_trades["status"] == "success":
                trades_data = recent_trades["data"]
                health_data["checks"]["recent_activity"] = {
                    "status": "healthy",
                    "total_trades": trades_data["total"],
                    "recent_trades_count": len(trades_data["trades"])
                }
                
                # Check if there have been recent trades (within last hour)
                if trades_data["trades"]:
                    latest_trade_time = datetime.fromisoformat(
                        trades_data["trades"][0]["executed_at"] or trades_data["trades"][0]["created_at"]
                    )
                    if datetime.utcnow() - latest_trade_time > timedelta(hours=2):
                        health_data["alerts"].append({
                            "level": "info",
                            "message": "No recent trading activity",
                            "timestamp": datetime.utcnow().isoformat()
                        })
            
            # Store alerts
            self.alerts.extend(health_data["alerts"])
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]
            
            return health_data
            
        except Exception as e:
            logger.error(f"Error in trading health check: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get trading performance summary"""
        try:
            performance = trading_service.get_trading_performance("all_time")
            if performance["status"] == "success":
                return {
                    "status": "success",
                    "data": performance["data"]["metrics"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return performance
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return self.alerts[-limit:] if self.alerts else []


class HealthCheckEndpoint:
    """Health check endpoints for monitoring"""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.trading_monitor = TradingMonitor()
    
    async def basic_health(self) -> Dict[str, Any]:
        """Basic health check"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": time.time() - self.system_monitor.start_time,
            "version": "1.0.0"
        }
    
    async def detailed_health(self) -> Dict[str, Any]:
        """Detailed health check with system and trading metrics"""
        try:
            system_metrics = self.system_monitor.get_system_metrics()
            trading_health = self.trading_monitor.check_trading_health()
            
            return {
                "status": "success",
                "overall_health": trading_health["overall_status"],
                "system": system_metrics,
                "trading": trading_health,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in detailed health check: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def prometheus_metrics(self) -> str:
        """Generate Prometheus metrics"""
        try:
            system_metrics = self.system_monitor.get_system_metrics()
            trading_health = self.trading_monitor.check_trading_health()
            performance = self.trading_monitor.get_performance_summary()
            
            metrics = []
            
            # System metrics
            if "error" not in system_metrics:
                metrics.extend([
                    f"# HELP trading_system_cpu_percent CPU usage percentage",
                    f"# TYPE trading_system_cpu_percent gauge",
                    f"trading_system_cpu_percent {system_metrics['cpu_percent']}",
                    f"",
                    f"# HELP trading_system_memory_percent Memory usage percentage",
                    f"# TYPE trading_system_memory_percent gauge",
                    f"trading_system_memory_percent {system_metrics['memory_percent']}",
                    f"",
                    f"# HELP trading_system_uptime_seconds System uptime in seconds",
                    f"# TYPE trading_system_uptime_seconds counter",
                    f"trading_system_uptime_seconds {system_metrics['uptime_seconds']}",
                    f""
                ])
            
            # Trading metrics
            if trading_health["overall_status"] != "error":
                is_running = 1 if trading_health["checks"].get("trading_service", {}).get("status") == "healthy" else 0
                metrics.extend([
                    f"# HELP trading_system_running Trading system running status",
                    f"# TYPE trading_system_running gauge",
                    f"trading_system_running {is_running}",
                    f""
                ])
                
                # Portfolio metrics
                portfolio_data = trading_health["checks"].get("portfolio", {}).get("details", {})
                if portfolio_data:
                    metrics.extend([
                        f"# HELP trading_portfolio_value Current portfolio value",
                        f"# TYPE trading_portfolio_value gauge",
                        f"trading_portfolio_value {portfolio_data.get('current_value', 0)}",
                        f"",
                        f"# HELP trading_available_cash Available cash for trading",
                        f"# TYPE trading_available_cash gauge",
                        f"trading_available_cash {portfolio_data.get('available_cash', 0)}",
                        f"",
                        f"# HELP trading_positions_count Number of open positions",
                        f"# TYPE trading_positions_count gauge",
                        f"trading_positions_count {len(portfolio_data.get('positions', {}))}",
                        f""
                    ])
            
            # Performance metrics
            if performance["status"] == "success":
                perf_data = performance["data"]
                metrics.extend([
                    f"# HELP trading_total_return_pct Total return percentage",
                    f"# TYPE trading_total_return_pct gauge",
                    f"trading_total_return_pct {perf_data.get('total_return_pct', 0)}",
                    f"",
                    f"# HELP trading_total_trades Total number of trades",
                    f"# TYPE trading_total_trades counter",
                    f"trading_total_trades {perf_data.get('total_trades', 0)}",
                    f"",
                    f"# HELP trading_win_rate Win rate percentage",
                    f"# TYPE trading_win_rate gauge",
                    f"trading_win_rate {perf_data.get('win_rate', 0)}",
                    f""
                ])
            
            return "\n".join(metrics)
            
        except Exception as e:
            logger.error(f"Error generating Prometheus metrics: {e}")
            return f"# Error generating metrics: {e}\n"


# Global monitoring instances
system_monitor = SystemMonitor()
trading_monitor = TradingMonitor()
health_check = HealthCheckEndpoint()


class MonitoringService:
    """Background monitoring service"""
    
    def __init__(self):
        self.monitoring_task: Optional[asyncio.Task] = None
        self.alert_handlers = []
    
    async def start(self):
        """Start background monitoring"""
        if not self.monitoring_task or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Monitoring service started")
    
    async def stop(self):
        """Stop background monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Perform health checks every minute
                health_data = trading_monitor.check_trading_health()
                
                # Log any critical alerts
                for alert in health_data.get("alerts", []):
                    if alert["level"] == "critical":
                        logger.critical(f"Trading Alert: {alert['message']}")
                    elif alert["level"] == "warning":
                        logger.warning(f"Trading Alert: {alert['message']}")
                
                # Wait 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)


# Global monitoring service
monitoring_service = MonitoringService()