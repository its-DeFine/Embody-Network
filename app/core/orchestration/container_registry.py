"""
Container Registry

Manages registration, tracking, and lifecycle of remote containers in the cluster.
Provides container capability tracking, resource monitoring, and health status management.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from ...config import settings
from ...dependencies import get_redis

logger = logging.getLogger(__name__)


class ContainerRegistration(BaseModel):
    """Container registration model"""
    container_id: str
    container_name: str
    host_address: str
    api_endpoint: str
    capabilities: List[str] = []
    resources: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    registered_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_heartbeat: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "registered"
    health_score: int = 100


class ContainerEvent(BaseModel):
    """Container lifecycle event"""
    event_type: str
    container_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = {}


class ContainerRegistry:
    """
    Central registry for managing container registrations and lifecycle.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.heartbeat_timeout = 60  # seconds
        self.cleanup_interval = 30  # seconds
        self.cleanup_task: Optional[asyncio.Task] = None
        self.event_handlers: Dict[str, List[callable]] = {}
        
    async def start(self):
        """Start the container registry service"""
        try:
            self.redis = await aioredis.from_url(self.redis_url)
            await self.redis.ping()
            
            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Subscribe to container events
            asyncio.create_task(self._event_listener())
            
            logger.info("Container registry service started")
            
        except Exception as e:
            logger.error(f"Failed to start container registry: {e}")
            raise
    
    async def stop(self):
        """Stop the container registry service"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Container registry service stopped")
    
    async def register_container(self, registration: ContainerRegistration) -> bool:
        """Register a new container"""
        try:
            container_key = f"container:registry:{registration.container_id}"
            
            # Check if already registered
            exists = await self.redis.exists(container_key)
            if exists:
                logger.warning(f"Container {registration.container_id} already registered")
                return await self.update_container(registration)
            
            # Store registration
            await self.redis.hset(container_key, mapping={
                "container_id": registration.container_id,
                "container_name": registration.container_name,
                "host_address": registration.host_address,
                "api_endpoint": registration.api_endpoint,
                "capabilities": json.dumps(registration.capabilities),
                "resources": json.dumps(registration.resources),
                "metadata": json.dumps(registration.metadata),
                "registered_at": registration.registered_at,
                "last_heartbeat": registration.last_heartbeat,
                "status": registration.status,
                "health_score": registration.health_score
            })
            
            # Add to indices
            await self.redis.sadd("containers:registered", registration.container_id)
            await self.redis.hset("containers:by_name", registration.container_name, registration.container_id)
            
            # Add to capability indices
            for capability in registration.capabilities:
                await self.redis.sadd(f"containers:capability:{capability}", registration.container_id)
            
            # Publish registration event
            await self._publish_event(ContainerEvent(
                event_type="container_registered",
                container_id=registration.container_id,
                data=registration.dict()
            ))
            
            logger.info(f"Container {registration.container_name} ({registration.container_id}) registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error registering container: {e}")
            return False
    
    async def update_container(self, registration: ContainerRegistration) -> bool:
        """Update existing container registration"""
        try:
            container_key = f"container:registry:{registration.container_id}"
            
            # Update registration
            await self.redis.hset(container_key, mapping={
                "host_address": registration.host_address,
                "api_endpoint": registration.api_endpoint,
                "capabilities": json.dumps(registration.capabilities),
                "resources": json.dumps(registration.resources),
                "metadata": json.dumps(registration.metadata),
                "last_heartbeat": registration.last_heartbeat,
                "status": registration.status,
                "health_score": registration.health_score
            })
            
            # Update capability indices
            # First remove from all capability sets
            all_capabilities = await self.redis.keys("containers:capability:*")
            for cap_key in all_capabilities:
                await self.redis.srem(cap_key, registration.container_id)
            
            # Then add to new capability sets
            for capability in registration.capabilities:
                await self.redis.sadd(f"containers:capability:{capability}", registration.container_id)
            
            # Publish update event
            await self._publish_event(ContainerEvent(
                event_type="container_updated",
                container_id=registration.container_id,
                data=registration.dict()
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating container: {e}")
            return False
    
    async def deregister_container(self, container_id: str, reason: str = "manual") -> bool:
        """Deregister a container"""
        try:
            container_key = f"container:registry:{container_id}"
            
            # Get container info before deletion
            container_data = await self.redis.hgetall(container_key)
            if not container_data:
                logger.warning(f"Container {container_id} not found")
                return False
            
            # Update status
            await self.redis.hset(container_key, "status", "deregistered")
            
            # Remove from indices
            await self.redis.srem("containers:registered", container_id)
            
            # Remove from capability indices
            capabilities_raw = container_data.get(b"capabilities", b"[]")
            capabilities = json.loads(capabilities_raw.decode() if isinstance(capabilities_raw, bytes) else capabilities_raw)
            for capability in capabilities:
                await self.redis.srem(f"containers:capability:{capability}", container_id)
            
            # Remove from name index
            container_name = container_data.get(b"container_name", b"").decode()
            if container_name:
                await self.redis.hdel("containers:by_name", container_name)
            
            # Archive the container data
            await self.redis.hset(f"container:archive:{container_id}", mapping={
                k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
                for k, v in container_data.items()
            })
            await self.redis.hset(f"container:archive:{container_id}", 
                                "deregistered_at", datetime.utcnow().isoformat(),
                                "deregister_reason", reason)
            
            # Delete active registration
            await self.redis.delete(container_key)
            
            # Publish deregistration event
            await self._publish_event(ContainerEvent(
                event_type="container_deregistered",
                container_id=container_id,
                data={"reason": reason}
            ))
            
            logger.info(f"Container {container_id} deregistered (reason: {reason})")
            return True
            
        except Exception as e:
            logger.error(f"Error deregistering container: {e}")
            return False
    
    async def heartbeat(self, container_id: str, health_data: Optional[Dict[str, Any]] = None) -> bool:
        """Update container heartbeat"""
        try:
            container_key = f"container:registry:{container_id}"
            
            # Check if container exists
            exists = await self.redis.exists(container_key)
            if not exists:
                logger.warning(f"Heartbeat from unknown container: {container_id}")
                return False
            
            # Update heartbeat
            updates = {
                "last_heartbeat": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            # Update health data if provided
            if health_data:
                if "health_score" in health_data:
                    updates["health_score"] = health_data["health_score"]
                if "resources" in health_data:
                    updates["resources"] = json.dumps(health_data["resources"])
            
            await self.redis.hset(container_key, mapping=updates)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating heartbeat: {e}")
            return False
    
    async def get_container(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get container information"""
        try:
            container_key = f"container:registry:{container_id}"
            container_data = await self.redis.hgetall(container_key)
            
            if not container_data:
                return None
            
            # Parse container data
            container_info = {}
            for key, value in container_data.items():
                key_str = key.decode() if isinstance(key, bytes) else key
                value_str = value.decode() if isinstance(value, bytes) else value
                
                if key_str in ["capabilities", "resources", "metadata"]:
                    try:
                        container_info[key_str] = json.loads(value_str)
                    except:
                        container_info[key_str] = value_str
                else:
                    container_info[key_str] = value_str
            
            return container_info
            
        except Exception as e:
            logger.error(f"Error getting container info: {e}")
            return None
    
    async def get_containers_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Get all containers with a specific capability"""
        try:
            container_ids = await self.redis.smembers(f"containers:capability:{capability}")
            containers = []
            
            for container_id_bytes in container_ids:
                container_id = container_id_bytes.decode() if isinstance(container_id_bytes, bytes) else container_id_bytes
                container_info = await self.get_container(container_id)
                if container_info and container_info.get("status") in ["active", "ContainerStatus.ACTIVE"]:
                    containers.append(container_info)
            
            return containers
            
        except Exception as e:
            logger.error(f"Error getting containers by capability: {e}")
            return []
    
    async def get_all_containers(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all registered containers"""
        try:
            container_ids = await self.redis.smembers("containers:registered")
            containers = []
            
            for container_id_bytes in container_ids:
                container_id = container_id_bytes.decode() if isinstance(container_id_bytes, bytes) else container_id_bytes
                container_info = await self.get_container(container_id)
                
                if container_info:
                    if include_inactive or container_info.get("status") in ["active", "ContainerStatus.ACTIVE"]:
                        containers.append(container_info)
            
            return containers
            
        except Exception as e:
            logger.error(f"Error getting all containers: {e}")
            return []
    
    async def get_container_by_name(self, container_name: str) -> Optional[Dict[str, Any]]:
        """Get container by name"""
        try:
            container_id = await self.redis.hget("containers:by_name", container_name)
            if not container_id:
                return None
            
            container_id_str = container_id.decode() if isinstance(container_id, bytes) else container_id
            return await self.get_container(container_id_str)
            
        except Exception as e:
            logger.error(f"Error getting container by name: {e}")
            return None
    
    async def _cleanup_loop(self):
        """Cleanup inactive containers"""
        while True:
            try:
                await self._cleanup_inactive_containers()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    async def _cleanup_inactive_containers(self):
        """Remove containers that haven't sent heartbeat"""
        try:
            container_ids = await self.redis.smembers("containers:registered")
            timeout_threshold = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout)
            
            for container_id_bytes in container_ids:
                container_id = container_id_bytes.decode() if isinstance(container_id_bytes, bytes) else container_id_bytes
                container_info = await self.get_container(container_id)
                
                if not container_info:
                    continue
                
                # Check last heartbeat
                last_heartbeat_str = container_info.get("last_heartbeat")
                if last_heartbeat_str:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
                    
                    if last_heartbeat < timeout_threshold:
                        logger.warning(f"Container {container_id} timed out (last heartbeat: {last_heartbeat_str})")
                        await self.deregister_container(container_id, reason="heartbeat_timeout")
                        
        except Exception as e:
            logger.error(f"Error cleaning up inactive containers: {e}")
    
    async def _event_listener(self):
        """Listen for container events"""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe("events:container:*")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                    data = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]
                    
                    try:
                        event_data = json.loads(data)
                        await self._handle_event(channel, event_data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid event data: {data}")
                        
        except Exception as e:
            logger.error(f"Error in event listener: {e}")
    
    async def _handle_event(self, channel: str, event_data: Dict[str, Any]):
        """Handle container events"""
        event_type = channel.split(":")[-1]
        
        # Call registered handlers
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    async def _publish_event(self, event: ContainerEvent):
        """Publish container event"""
        try:
            channel = f"events:container:{event.event_type}"
            await self.redis.publish(channel, event.json())
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
    
    def register_event_handler(self, event_type: str, handler: callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall cluster status"""
        try:
            all_containers = await self.get_all_containers(include_inactive=True)
            active_containers = [c for c in all_containers if c.get("status") == "active"]
            
            # Calculate resource totals
            total_cpu = sum(c.get("resources", {}).get("cpu_count", 0) for c in active_containers)
            total_memory = sum(c.get("resources", {}).get("memory_limit", 0) for c in active_containers)
            
            # Get capability distribution
            capability_counts = {}
            for container in active_containers:
                for capability in container.get("capabilities", []):
                    capability_counts[capability] = capability_counts.get(capability, 0) + 1
            
            return {
                "total_containers": len(all_containers),
                "active_containers": len(active_containers),
                "inactive_containers": len(all_containers) - len(active_containers),
                "total_cpu_cores": total_cpu,
                "total_memory_bytes": total_memory,
                "capability_distribution": capability_counts,
                "cluster_health": "healthy" if len(active_containers) > 0 else "unhealthy",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cluster status: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Singleton instance
container_registry = ContainerRegistry()