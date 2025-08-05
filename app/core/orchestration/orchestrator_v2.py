"""
Microservices-Based Orchestrator (v2)

This is the new lightweight orchestrator that coordinates focused microservices:
- TaskCoordinator: Handles task routing and load balancing
- HealthMonitor: Monitors system and agent health
- ResourceManager: Manages resources and auto-scaling
- FailoverManager: Handles failure detection and recovery

This replaces the monolithic orchestrator.py with a distributed architecture
that scales horizontally and provides better fault isolation.
"""
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from .base_service import BaseOrchestrationService
from .task_coordinator import TaskCoordinator
from .health_monitor import HealthMonitor
from ...dependencies import get_redis

logger = logging.getLogger(__name__)


class MicroservicesOrchestrator:
    """Lightweight orchestrator that coordinates specialized microservices"""
    
    def __init__(self):
        self.redis = None
        self.services: Dict[str, BaseOrchestrationService] = {}
        self.running = False
        self.event_handlers = {}
        
        # Initialize microservices
        self.task_coordinator = TaskCoordinator()
        self.health_monitor = HealthMonitor()
        
        self.services = {
            "task_coordinator": self.task_coordinator,
            "health_monitor": self.health_monitor
        }
        
        logger.info("🎯 Microservices Orchestrator initialized")
        
    async def initialize(self):
        """Initialize orchestrator and all microservices"""
        self.redis = await get_redis()
        
        # Initialize all services
        for service_name, service in self.services.items():
            try:
                await service.initialize(self.redis)
                logger.info(f"✅ {service_name} initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {service_name}: {e}")
                raise
                
        # Set up event routing
        await self._setup_event_routing()
        
        logger.info("🚀 Microservices Orchestrator ready")
        
    async def start(self):
        """Start orchestrator and all microservices"""
        self.running = True
        
        # Start all services
        for service_name, service in self.services.items():
            try:
                await service.start()
                logger.info(f"🟢 {service_name} started")
            except Exception as e:
                logger.error(f"🔴 Failed to start {service_name}: {e}")
                raise
                
        # Start orchestrator coordination loop
        asyncio.create_task(self._coordination_loop())
        
        logger.info("✅ All microservices started successfully")
        
    async def stop(self):
        """Stop orchestrator and all microservices"""
        self.running = False
        
        # Stop all services gracefully
        for service_name, service in self.services.items():
            try:
                await service.stop()
                logger.info(f"🔴 {service_name} stopped")
            except Exception as e:
                logger.error(f"⚠️ Error stopping {service_name}: {e}")
                
        logger.info("🛑 Microservices Orchestrator stopped")
        
    async def _setup_event_routing(self):
        """Set up event routing between microservices"""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe("orchestrator:events")
            
            asyncio.create_task(self._event_router(pubsub))
            logger.info("📡 Event routing established")
            
        except Exception as e:
            logger.error(f"Failed to set up event routing: {e}")
            raise
            
    async def _event_router(self, pubsub):
        """Route events between microservices"""
        async for message in pubsub.listen():
            if message["type"] == "message" and self.running:
                try:
                    event = json.loads(message["data"])
                    await self._route_event(event)
                except Exception as e:
                    logger.error(f"Error routing event: {e}")
                    
    async def _route_event(self, event: Dict[str, Any]):
        """Route event to appropriate microservices"""
        event_type = event.get("type", "")
        
        # Route to multiple services if needed
        if event_type.startswith("task."):
            # Task-related events go to task coordinator
            await self.task_coordinator.handle_event(event)
            
        if event_type.startswith("agent.") or event_type.startswith("system."):
            # Health/system events go to health monitor
            await self.health_monitor.handle_event(event)
            
        # Log coordination events
        if event_type in ["task.created", "agent.started", "system.alert"]:
            logger.info(f"📬 Routed event: {event_type} from {event.get('source', 'unknown')}")
            
    async def _coordination_loop(self):
        """Main coordination loop for microservices orchestrator"""
        while self.running:
            try:
                # Check service health
                await self._check_service_health()
                
                # Coordinate cross-service operations
                await self._coordinate_services()
                
                # Publish orchestrator health
                await self._publish_orchestrator_health()
                
                await asyncio.sleep(30)  # Coordinate every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in coordination loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
                
    async def _check_service_health(self):
        """Check health of all microservices"""
        unhealthy_services = []
        
        for service_name, service in self.services.items():
            try:
                health = await service.get_service_health()
                if health.get("status") != "healthy":
                    unhealthy_services.append(service_name)
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                unhealthy_services.append(service_name)
                
        if unhealthy_services:
            logger.warning(f"⚠️ Unhealthy services: {unhealthy_services}")
            await self._handle_unhealthy_services(unhealthy_services)
            
    async def _handle_unhealthy_services(self, services: List[str]):
        """Handle unhealthy microservices"""
        for service_name in services:
            logger.warning(f"🔄 Attempting to restart {service_name}")
            
            # Simple restart logic - in production would be more sophisticated
            try:
                service = self.services[service_name]
                await service.stop()
                await asyncio.sleep(5)  # Brief pause
                await service.start()
                logger.info(f"✅ Restarted {service_name}")
            except Exception as e:
                logger.error(f"❌ Failed to restart {service_name}: {e}")
                
    async def _coordinate_services(self):
        """Coordinate operations between services"""
        try:
            # Get status from all services
            task_stats = await self.task_coordinator.get_coordinator_stats()
            health_summary = await self.health_monitor.get_health_summary()
            
            # Cross-service coordination logic
            pending_tasks = task_stats.get("pending_tasks", 0)
            healthy_agents = health_summary.get("healthy_agents", 0)
            
            # If we have many pending tasks but few healthy agents, alert
            if pending_tasks > 10 and healthy_agents < 3:
                await self._publish_coordination_alert("task_backlog", {
                    "pending_tasks": pending_tasks,
                    "healthy_agents": healthy_agents,
                    "recommendation": "Consider scaling up agents"
                })
                
            # If system health is poor but we're still assigning tasks, slow down
            health_score = health_summary.get("overall_health_score", 100)
            if health_score < 50:
                await self._publish_coordination_alert("system_degraded", {
                    "health_score": health_score,
                    "recommendation": "Reducing task assignment rate"
                })
                
        except Exception as e:
            logger.error(f"Error in service coordination: {e}")
            
    async def _publish_coordination_alert(self, alert_type: str, data: Dict[str, Any]):
        """Publish coordination alert"""
        alert = {
            "type": f"coordination.{alert_type}",
            "source": "orchestrator_coordinator",
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.publish("orchestrator:events", json.dumps(alert))
        logger.warning(f"🚨 Coordination alert: {alert_type} - {data.get('recommendation', 'No recommendation')}")
        
    async def _publish_orchestrator_health(self):
        """Publish overall orchestrator health"""
        try:
            service_health = {}
            for service_name, service in self.services.items():
                health = await service.get_service_health()
                service_health[service_name] = health.get("status", "unknown")
                
            orchestrator_health = {
                "type": "orchestrator.health",
                "source": "microservices_orchestrator",
                "data": {
                    "overall_status": "healthy" if all(status == "healthy" for status in service_health.values()) else "degraded",
                    "service_health": service_health,
                    "active_services": len([s for s in service_health.values() if s == "healthy"]),
                    "total_services": len(service_health)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis.publish("orchestrator:events", json.dumps(orchestrator_health))
            
        except Exception as e:
            logger.error(f"Error publishing orchestrator health: {e}")
            
    # API methods for external interaction
    
    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create a new task (API method)"""
        task_id = f"task_{datetime.utcnow().timestamp()}"
        
        event = {
            "type": "task.created",
            "source": "api",
            "data": {
                "task_id": task_id,
                "task": task_data,
                "dependencies": task_data.get("dependencies", [])
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.publish("orchestrator:events", json.dumps(event))
        logger.info(f"📝 Task created: {task_id}")
        
        return task_id
        
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            task_stats = await self.task_coordinator.get_coordinator_stats()
            health_summary = await self.health_monitor.get_health_summary()
            
            return {
                "orchestrator_type": "microservices_v2",
                "overall_status": health_summary.get("system_status", "unknown"),
                "health_score": health_summary.get("overall_health_score", 0),
                "services": {
                    "task_coordinator": {
                        "pending_tasks": task_stats.get("pending_tasks", 0),
                        "active_tasks": task_stats.get("active_tasks", 0),
                        "known_agents": task_stats.get("known_agents", 0)
                    },
                    "health_monitor": {
                        "healthy_agents": health_summary.get("healthy_agents", 0),
                        "active_alerts": health_summary.get("active_alerts", 0),
                        "avg_response_time": health_summary.get("avg_response_time", 0)
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "orchestrator_type": "microservices_v2",
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def register_agent(self, agent_data: Dict[str, Any]):
        """Register a new agent (API method)"""
        event = {
            "type": "agent.started",
            "source": "api",
            "data": agent_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.publish("orchestrator:events", json.dumps(event))
        logger.info(f"🤖 Agent registered: {agent_data.get('agent_id', 'unknown')}")
        
    async def unregister_agent(self, agent_id: str):
        """Unregister an agent (API method)"""
        event = {
            "type": "agent.stopped",
            "source": "api", 
            "data": {"agent_id": agent_id},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.publish("orchestrator:events", json.dumps(event))
        logger.info(f"🛑 Agent unregistered: {agent_id}")


# Global orchestrator instance
orchestrator_v2 = MicroservicesOrchestrator()