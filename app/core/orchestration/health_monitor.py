"""
Health Monitoring Service

Focused microservice responsible for:
- System health monitoring
- Agent health tracking
- Resource usage monitoring
- Failure detection and alerting
- Health metrics collection and reporting
"""
import asyncio
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict, deque
import statistics

from .base_service import BaseOrchestrationService

logger = logging.getLogger(__name__)


class HealthMonitor(BaseOrchestrationService):
    """Microservice for system and agent health monitoring"""
    
    def __init__(self, redis=None):
        super().__init__("health_monitor", redis)
        
        # Health tracking
        self.agent_health: Dict[str, Dict] = {}
        self.system_health_history: deque = deque(maxlen=1000)
        self.alert_thresholds = {
            "cpu_critical": 90.0,
            "cpu_warning": 75.0,
            "memory_critical": 85.0,
            "memory_warning": 70.0,
            "disk_critical": 90.0,
            "disk_warning": 75.0,
            "response_time_critical": 5000.0,  # ms
            "response_time_warning": 2000.0,   # ms
        }
        
        # Alert tracking
        self.active_alerts: Dict[str, Dict] = {}
        self.alert_history: deque = deque(maxlen=500)
        
        # Performance tracking
        self.response_times: deque = deque(maxlen=1000)
        self.error_rates: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
    async def setup(self):
        """Initialize health monitor"""
        # Subscribe to health-related events
        asyncio.create_task(self.subscribe_to_events([
            "agent.heartbeat",
            "agent.started",
            "agent.stopped",
            "task.completed",
            "task.failed",
            "system.performance"
        ]))
        
    async def _service_loop(self):
        """Main health monitoring loop"""
        while self.running:
            try:
                await self._collect_system_metrics()
                await self._check_agent_health()
                await self._evaluate_alerts()
                
                await asyncio.sleep(15)  # Monitor every 15 seconds
                
            except Exception as e:
                self.logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(30)
                
    def get_background_tasks(self):
        """Background tasks for health monitor"""
        return [
            self._system_health_reporter(),
            self._alert_manager(),
            self._cleanup_old_data()
        ]
        
    async def handle_event(self, event: Dict[str, Any]):
        """Handle incoming health-related events"""
        event_type = event["type"]
        data = event["data"]
        timestamp = event.get("timestamp", datetime.utcnow().isoformat())
        
        if event_type == "agent.heartbeat":
            await self._handle_agent_heartbeat(data, timestamp)
        elif event_type == "agent.started":
            await self._handle_agent_started(data, timestamp)
        elif event_type == "agent.stopped":
            await self._handle_agent_stopped(data, timestamp)
        elif event_type == "task.completed":
            await self._handle_task_completed(data, timestamp)
        elif event_type == "task.failed":
            await self._handle_task_failed(data, timestamp)
        elif event_type == "system.performance":
            await self._handle_system_performance(data, timestamp)
            
    async def _collect_system_metrics(self):
        """Collect system-wide health metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network (if available)
            network_io = psutil.net_io_counters()
            
            # System health snapshot
            health_snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available": memory.available,
                "disk_usage": disk.percent,
                "disk_free": disk.free,
                "network_bytes_sent": network_io.bytes_sent if network_io else 0,
                "network_bytes_recv": network_io.bytes_recv if network_io else 0,
                "active_agents": len([a for a in self.agent_health.values() if a.get("status") == "healthy"]),
                "total_agents": len(self.agent_health),
                "avg_response_time": statistics.mean(self.response_times) if self.response_times else 0
            }
            
            self.system_health_history.append(health_snapshot)
            
            # Store in Redis for external access
            await self.redis.set(
                "system:health:current",
                json.dumps(health_snapshot),
                ex=300  # Expire in 5 minutes
            )
            
            # Check for threshold violations
            await self._check_system_thresholds(health_snapshot)
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            
    async def _check_agent_health(self):
        """Check health of all known agents"""
        current_time = datetime.utcnow()
        stale_threshold = timedelta(minutes=2)  # Agent heartbeat timeout
        
        for agent_id, health_data in list(self.agent_health.items()):
            last_seen = datetime.fromisoformat(health_data.get("last_seen", current_time.isoformat()))
            
            if current_time - last_seen > stale_threshold:
                # Agent appears to be down
                if health_data.get("status") != "unhealthy":
                    health_data["status"] = "unhealthy"
                    health_data["unhealthy_since"] = current_time.isoformat()
                    
                    await self._trigger_alert("agent_unhealthy", {
                        "agent_id": agent_id,
                        "last_seen": health_data["last_seen"],
                        "duration": str(current_time - last_seen)
                    })
                    
                    self.logger.warning(f"🚨 Agent {agent_id} appears unhealthy (last seen: {last_seen})")
                    
    async def _check_system_thresholds(self, metrics: Dict[str, Any]):
        """Check if system metrics exceed alert thresholds"""
        checks = [
            ("cpu_usage", "cpu"),
            ("memory_usage", "memory"),
            ("disk_usage", "disk")
        ]
        
        for metric_key, alert_prefix in checks:
            value = metrics.get(metric_key, 0)
            
            critical_threshold = self.alert_thresholds.get(f"{alert_prefix}_critical", 90)
            warning_threshold = self.alert_thresholds.get(f"{alert_prefix}_warning", 75)
            
            if value >= critical_threshold:
                await self._trigger_alert(f"system_{alert_prefix}_critical", {
                    "metric": metric_key,
                    "value": value,
                    "threshold": critical_threshold
                })
            elif value >= warning_threshold:
                await self._trigger_alert(f"system_{alert_prefix}_warning", {
                    "metric": metric_key,
                    "value": value,
                    "threshold": warning_threshold
                })
                
    async def _trigger_alert(self, alert_type: str, data: Dict[str, Any]):
        """Trigger a system alert"""
        alert_id = f"{alert_type}_{hash(str(data)) % 10000}"
        
        # Avoid duplicate alerts
        if alert_id in self.active_alerts:
            return
            
        alert = {
            "id": alert_id,
            "type": alert_type,
            "data": data,
            "triggered_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Publish alert event
        await self.publish_event("system.alert", alert)
        
        self.logger.warning(f"🚨 Alert triggered: {alert_type} - {data}")
        
    async def _evaluate_alerts(self):
        """Evaluate active alerts and resolve if conditions improved"""
        current_time = datetime.utcnow()
        resolved_alerts = []
        
        for alert_id, alert in list(self.active_alerts.items()):
            alert_type = alert["type"]
            data = alert["data"]
            
            # Check if alert condition is resolved
            if await self._is_alert_resolved(alert_type, data):
                alert["status"] = "resolved"
                alert["resolved_at"] = current_time.isoformat()
                resolved_alerts.append(alert_id)
                
                await self.publish_event("system.alert_resolved", alert)
                self.logger.info(f"✅ Alert resolved: {alert_type}")
                
        # Remove resolved alerts from active list
        for alert_id in resolved_alerts:
            del self.active_alerts[alert_id]
            
    async def _is_alert_resolved(self, alert_type: str, data: Dict[str, Any]) -> bool:
        """Check if an alert condition has been resolved"""
        if alert_type.startswith("system_"):
            # Get current system metrics
            if self.system_health_history:
                current_metrics = self.system_health_history[-1]
                metric = data.get("metric")
                threshold = data.get("threshold", 100)
                
                if metric and metric in current_metrics:
                    current_value = current_metrics[metric]
                    # Resolved if value is 10% below threshold
                    return current_value < (threshold * 0.9)
                    
        elif alert_type == "agent_unhealthy":
            agent_id = data.get("agent_id")
            if agent_id in self.agent_health:
                return self.agent_health[agent_id].get("status") == "healthy"
                
        return False
        
    async def _handle_agent_heartbeat(self, data: Dict, timestamp: str):
        """Handle agent heartbeat"""
        agent_id = data.get("agent_id")
        metrics = data.get("metrics", {})
        
        if agent_id:
            self.agent_health[agent_id] = {
                "status": "healthy",
                "last_seen": timestamp,
                "metrics": metrics,
                "cpu_usage": metrics.get("cpu_usage", 0),
                "memory_usage": metrics.get("memory_usage", 0),
                "active_tasks": metrics.get("active_tasks", 0)
            }
            
            # Track response time if provided
            response_time = metrics.get("response_time_ms")
            if response_time:
                self.response_times.append(response_time)
                
    async def _handle_agent_started(self, data: Dict, timestamp: str):
        """Handle agent startup"""
        agent_id = data.get("agent_id")
        
        if agent_id:
            self.agent_health[agent_id] = {
                "status": "healthy",
                "last_seen": timestamp,
                "started_at": timestamp,
                "metrics": {},
                "cpu_usage": 0,
                "memory_usage": 0,
                "active_tasks": 0
            }
            
            self.logger.info(f"✅ Agent {agent_id} health tracking started")
            
    async def _handle_agent_stopped(self, data: Dict, timestamp: str):
        """Handle agent shutdown"""
        agent_id = data.get("agent_id")
        
        if agent_id in self.agent_health:
            self.agent_health[agent_id]["status"] = "stopped"
            self.agent_health[agent_id]["stopped_at"] = timestamp
            
            self.logger.info(f"🛑 Agent {agent_id} health tracking stopped")
            
    async def _handle_task_completed(self, data: Dict, timestamp: str):
        """Handle task completion for performance tracking"""
        completion_time = data.get("completion_time", 0)
        if completion_time:
            self.response_times.append(completion_time * 1000)  # Convert to ms
            
    async def _handle_task_failed(self, data: Dict, timestamp: str):
        """Handle task failure for error rate tracking"""
        agent_id = data.get("agent_id")
        if agent_id:
            self.error_rates[agent_id].append(1)
            
    async def _handle_system_performance(self, data: Dict, timestamp: str):
        """Handle system performance metrics"""
        avg_completion = data.get("avg_task_completion", 0)
        if avg_completion:
            self.response_times.append(avg_completion * 1000)  # Convert to ms
            
    async def _system_health_reporter(self):
        """Periodically report system health"""
        while self.running:
            try:
                if self.system_health_history:
                    current_health = self.system_health_history[-1]
                    
                    # Calculate health score (0-100)
                    health_score = await self._calculate_health_score(current_health)
                    
                    health_report = {
                        "overall_health_score": health_score,
                        "system_metrics": current_health,
                        "active_alerts": len(self.active_alerts),
                        "healthy_agents": len([a for a in self.agent_health.values() if a.get("status") == "healthy"]),
                        "total_agents": len(self.agent_health),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await self.publish_event("system.health_report", health_report)
                    
                await asyncio.sleep(60)  # Report every minute
                
            except Exception as e:
                self.logger.error(f"Error in health reporter: {e}")
                await asyncio.sleep(60)
                
    async def _calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall system health score (0-100)"""
        try:
            # Component scores (0-100, higher is better)
            cpu_score = max(0, 100 - metrics.get("cpu_usage", 0))
            memory_score = max(0, 100 - metrics.get("memory_usage", 0))
            disk_score = max(0, 100 - metrics.get("disk_usage", 0))
            
            # Agent health score
            healthy_agents = len([a for a in self.agent_health.values() if a.get("status") == "healthy"])
            total_agents = max(1, len(self.agent_health))
            agent_score = (healthy_agents / total_agents) * 100
            
            # Alert penalty
            alert_penalty = min(len(self.active_alerts) * 10, 50)  # Max 50 point penalty
            
            # Weighted average
            overall_score = (
                cpu_score * 0.25 +
                memory_score * 0.25 +
                disk_score * 0.20 +
                agent_score * 0.30
            ) - alert_penalty
            
            return max(0, min(100, overall_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating health score: {e}")
            return 50.0  # Default score on error
            
    async def _alert_manager(self):
        """Manage alert lifecycle and notifications"""
        while self.running:
            try:
                # Auto-resolve old alerts that haven't been updated
                current_time = datetime.utcnow()
                auto_resolve_threshold = timedelta(hours=1)
                
                for alert_id, alert in list(self.active_alerts.items()):
                    triggered_at = datetime.fromisoformat(alert["triggered_at"])
                    
                    if current_time - triggered_at > auto_resolve_threshold:
                        alert["status"] = "auto_resolved"
                        alert["resolved_at"] = current_time.isoformat()
                        del self.active_alerts[alert_id]
                        
                        await self.publish_event("system.alert_auto_resolved", alert)
                        self.logger.info(f"🔄 Auto-resolved stale alert: {alert['type']}")
                        
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in alert manager: {e}")
                await asyncio.sleep(300)
                
    async def _cleanup_old_data(self):
        """Clean up old health and alert data"""
        while self.running:
            try:
                # Clean up stopped agents after 24 hours
                current_time = datetime.utcnow()
                cleanup_threshold = timedelta(hours=24)
                
                agents_to_remove = []
                for agent_id, health_data in self.agent_health.items():
                    if health_data.get("status") == "stopped":
                        stopped_at = health_data.get("stopped_at")
                        if stopped_at:
                            stopped_time = datetime.fromisoformat(stopped_at)
                            if current_time - stopped_time > cleanup_threshold:
                                agents_to_remove.append(agent_id)
                                
                for agent_id in agents_to_remove:
                    del self.agent_health[agent_id]
                    self.logger.info(f"🧹 Cleaned up old agent data: {agent_id}")
                    
                await asyncio.sleep(3600)  # Clean up every hour
                
            except Exception as e:
                self.logger.error(f"Error in data cleanup: {e}")
                await asyncio.sleep(3600)
                
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        current_health = self.system_health_history[-1] if self.system_health_history else {}
        health_score = await self._calculate_health_score(current_health)
        
        return {
            "service": "health_monitor",
            "overall_health_score": health_score,
            "system_status": "healthy" if health_score > 70 else "degraded" if health_score > 40 else "critical",
            "active_alerts": len(self.active_alerts),
            "healthy_agents": len([a for a in self.agent_health.values() if a.get("status") == "healthy"]),
            "unhealthy_agents": len([a for a in self.agent_health.values() if a.get("status") == "unhealthy"]),
            "total_agents": len(self.agent_health),
            "avg_response_time": statistics.mean(self.response_times) if self.response_times else 0,
            "current_metrics": current_health,
            "timestamp": datetime.utcnow().isoformat()
        }