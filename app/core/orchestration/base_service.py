"""
Base Service for Orchestration Microservices

Provides common functionality for all orchestration services including:
- Redis connectivity
- Event publishing/subscribing
- Logging and monitoring
- Graceful startup/shutdown
"""
import asyncio
import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseOrchestrationService(ABC):
    """Base class for all orchestration microservices"""
    
    def __init__(self, service_name: str, redis=None):
        self.service_name = service_name
        self.redis = redis
        self.running = False
        self.tasks = []
        self.logger = logging.getLogger(f"orchestration.{service_name}")
        
    async def initialize(self, redis):
        """Initialize service with Redis connection"""
        self.redis = redis
        await self.setup()
        self.logger.info(f"🚀 {self.service_name} service initialized")
        
    @abstractmethod
    async def setup(self):
        """Service-specific setup logic"""
        pass
        
    async def start(self):
        """Start the service"""
        self.running = True
        
        # Start main service loop
        self.tasks.append(asyncio.create_task(self._service_loop()))
        
        # Start additional background tasks
        for task_coro in self.get_background_tasks():
            self.tasks.append(asyncio.create_task(task_coro))
            
        self.logger.info(f"✅ {self.service_name} service started")
        
    async def stop(self):
        """Stop the service gracefully"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        await self.cleanup()
        self.logger.info(f"🛑 {self.service_name} service stopped")
        
    @abstractmethod
    async def _service_loop(self):
        """Main service processing loop"""
        pass
        
    def get_background_tasks(self):
        """Return list of background task coroutines"""
        return []
        
    async def cleanup(self):
        """Service-specific cleanup logic"""
        pass
        
    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event to Redis"""
        try:
            event = {
                "type": event_type,
                "source": self.service_name,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis.publish("orchestrator:events", json.dumps(event))
            self.logger.debug(f"📤 Published event: {event_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type}: {e}")
            
    async def subscribe_to_events(self, event_types: list):
        """Subscribe to specific event types"""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe("orchestrator:events")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        if event["type"] in event_types:
                            await self.handle_event(event)
                    except Exception as e:
                        self.logger.error(f"Error processing event: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error in event subscription: {e}")
            
    async def handle_event(self, event: Dict[str, Any]):
        """Handle incoming event - override in subclasses"""
        pass
        
    async def get_service_health(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": self.service_name,
            "status": "healthy" if self.running else "stopped",
            "active_tasks": len([t for t in self.tasks if not t.done()]),
            "timestamp": datetime.utcnow().isoformat()
        }