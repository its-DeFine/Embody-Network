"""
Container Discovery Service

Automatically discovers and monitors container instances joining the network.
Provides health monitoring, capability assessment, and network topology mapping.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from enum import Enum

import docker
from docker.errors import DockerException
import redis.asyncio as aioredis

from ...config import settings
from ...dependencies import get_redis

logger = logging.getLogger(__name__)


class ContainerStatus(str, Enum):
    """Container status enumeration"""
    DISCOVERED = "discovered"
    REGISTERING = "registering"
    ACTIVE = "active"
    UNHEALTHY = "unhealthy"
    DISCONNECTED = "disconnected"
    TERMINATED = "terminated"


class ContainerCapability(str, Enum):
    """Container capability types"""
    AGENT_RUNNER = "agent_runner"
    GPU_COMPUTE = "gpu_compute"
    HIGH_MEMORY = "high_memory"
    STORAGE = "storage"
    NETWORK_EDGE = "network_edge"


class ContainerDiscoveryService:
    """
    Service for discovering and monitoring container instances in the cluster.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.docker_client: Optional[docker.DockerClient] = None
        self.discovery_interval = 30  # seconds
        self.health_check_interval = 15  # seconds
        self.discovery_task: Optional[asyncio.Task] = None
        self.health_monitor_task: Optional[asyncio.Task] = None
        self.known_containers: Set[str] = set()
        
    async def start(self):
        """Start the container discovery service"""
        try:
            # Initialize Redis connection
            self.redis = await aioredis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("Container discovery service connected to Redis")
            
            # Initialize Docker client
            self.docker_client = docker.from_env()
            logger.info("Container discovery service connected to Docker")
            
            # Start discovery and monitoring tasks
            self.discovery_task = asyncio.create_task(self._discovery_loop())
            self.health_monitor_task = asyncio.create_task(self._health_monitoring_loop())
            
            logger.info("Container discovery service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start container discovery service: {e}")
            raise
    
    async def stop(self):
        """Stop the container discovery service"""
        if self.discovery_task:
            self.discovery_task.cancel()
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Container discovery service stopped")
    
    async def _discovery_loop(self):
        """Main discovery loop that scans for new containers"""
        while True:
            try:
                await self._discover_containers()
                await asyncio.sleep(self.discovery_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                await asyncio.sleep(self.discovery_interval)
    
    async def _health_monitoring_loop(self):
        """Health monitoring loop for known containers"""
        while True:
            try:
                await self._check_container_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _discover_containers(self):
        """Discover containers in the network"""
        try:
            # Get all running containers
            containers = self.docker_client.containers.list(all=False)
            
            for container in containers:
                container_id = container.id[:12]
                
                # Skip if already known
                if container_id in self.known_containers:
                    continue
                
                # Check if container is compatible (has agent capabilities)
                if await self._is_compatible_container(container):
                    await self._register_container(container)
                    self.known_containers.add(container_id)
                    logger.info(f"Discovered new container: {container.name} ({container_id})")
            
            # Check for removed containers
            current_containers = {c.id[:12] for c in containers}
            removed_containers = self.known_containers - current_containers
            
            for container_id in removed_containers:
                await self._unregister_container(container_id)
                self.known_containers.remove(container_id)
                logger.info(f"Container removed: {container_id}")
                
        except DockerException as e:
            logger.error(f"Docker error during container discovery: {e}")
        except Exception as e:
            logger.error(f"Error discovering containers: {e}")
    
    async def _is_compatible_container(self, container) -> bool:
        """Check if container is compatible with our agent system"""
        try:
            # Check container labels
            labels = container.labels
            
            # Look for our specific labels
            if labels.get("autogen.agent.capable") == "true":
                return True
            
            # Check container image
            if "autogen-agent" in container.image.tags[0] if container.image.tags else False:
                return True
            
            # Check environment variables
            env_vars = container.attrs.get("Config", {}).get("Env", [])
            for env in env_vars:
                if env.startswith("AGENT_CAPABLE=true"):
                    return True
            
            # Check if container is part of our network
            networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            for network_name in networks:
                if "trading-network" in network_name or "operation" in network_name:
                    # Additional check for agent capabilities
                    return await self._probe_container_capabilities(container)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking container compatibility: {e}")
            return False
    
    async def _probe_container_capabilities(self, container) -> bool:
        """Probe container to check if it has agent capabilities"""
        try:
            # Try to execute a capability check command
            result = container.exec_run("test -f /app/agent_runner.py", demux=True)
            return result.exit_code == 0
        except:
            return False
    
    async def _register_container(self, container):
        """Register a discovered container"""
        try:
            container_info = {
                "id": container.id[:12],
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": ContainerStatus.DISCOVERED,
                "discovered_at": datetime.utcnow().isoformat(),
                "last_health_check": datetime.utcnow().isoformat(),
                "capabilities": await self._assess_capabilities(container),
                "resources": await self._get_container_resources(container),
                "network_info": self._get_network_info(container),
                "labels": container.labels,
                "health_score": 100
            }
            
            # Store in Redis
            container_key = f"container:registry:{container.id[:12]}"
            await self.redis.hset(container_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in container_info.items()
            })
            
            # Add to active containers set
            await self.redis.sadd("containers:active", container.id[:12])
            
            # Publish discovery event
            await self.redis.publish("events:container:discovered", json.dumps({
                "event": "container_discovered",
                "container_id": container.id[:12],
                "container_name": container.name,
                "timestamp": datetime.utcnow().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error registering container: {e}")
    
    async def _unregister_container(self, container_id: str):
        """Unregister a removed container"""
        try:
            # Update status
            container_key = f"container:registry:{container_id}"
            await self.redis.hset(container_key, "status", ContainerStatus.TERMINATED)
            
            # Remove from active set
            await self.redis.srem("containers:active", container_id)
            
            # Add to terminated set
            await self.redis.sadd("containers:terminated", container_id)
            
            # Publish removal event
            await self.redis.publish("events:container:removed", json.dumps({
                "event": "container_removed",
                "container_id": container_id,
                "timestamp": datetime.utcnow().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error unregistering container: {e}")
    
    async def _assess_capabilities(self, container) -> List[str]:
        """Assess container capabilities"""
        capabilities = []
        
        try:
            # Check for agent runner capability
            result = container.exec_run("test -f /app/agent_runner.py", demux=True)
            if result.exit_code == 0:
                capabilities.append(ContainerCapability.AGENT_RUNNER)
            
            # Check for GPU support
            result = container.exec_run("nvidia-smi", demux=True)
            if result.exit_code == 0:
                capabilities.append(ContainerCapability.GPU_COMPUTE)
            
            # Check memory resources
            stats = container.stats(stream=False)
            memory_limit = stats.get("memory_stats", {}).get("limit", 0)
            if memory_limit > 8 * 1024 * 1024 * 1024:  # 8GB
                capabilities.append(ContainerCapability.HIGH_MEMORY)
            
            # Check for storage capability
            result = container.exec_run("df -h /data", demux=True)
            if result.exit_code == 0:
                capabilities.append(ContainerCapability.STORAGE)
            
        except Exception as e:
            logger.error(f"Error assessing container capabilities: {e}")
        
        return capabilities
    
    async def _get_container_resources(self, container) -> Dict[str, Any]:
        """Get container resource information"""
        try:
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
            
            return {
                "cpu_count": stats["cpu_stats"]["online_cpus"],
                "cpu_usage_percent": round(cpu_percent, 2),
                "memory_limit": stats["memory_stats"]["limit"],
                "memory_usage": stats["memory_stats"]["usage"],
                "memory_percent": round(
                    (stats["memory_stats"]["usage"] / stats["memory_stats"]["limit"]) * 100, 2
                ) if stats["memory_stats"]["limit"] > 0 else 0,
                "network_rx_bytes": stats["networks"]["eth0"]["rx_bytes"] if "eth0" in stats.get("networks", {}) else 0,
                "network_tx_bytes": stats["networks"]["eth0"]["tx_bytes"] if "eth0" in stats.get("networks", {}) else 0
            }
        except Exception as e:
            logger.error(f"Error getting container resources: {e}")
            return {}
    
    def _get_network_info(self, container) -> Dict[str, Any]:
        """Get container network information"""
        try:
            networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            network_info = {}
            
            for network_name, network_data in networks.items():
                network_info[network_name] = {
                    "ip_address": network_data.get("IPAddress"),
                    "gateway": network_data.get("Gateway"),
                    "mac_address": network_data.get("MacAddress")
                }
            
            return network_info
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
            return {}
    
    async def _check_container_health(self):
        """Check health of all active containers"""
        try:
            # Get active containers from Redis
            active_containers = await self.redis.smembers("containers:active")
            
            for container_id_bytes in active_containers:
                container_id = container_id_bytes.decode() if isinstance(container_id_bytes, bytes) else container_id_bytes
                await self._health_check_container(container_id)
                
        except Exception as e:
            logger.error(f"Error in container health check: {e}")
    
    async def _health_check_container(self, container_id: str):
        """Perform health check on a specific container"""
        try:
            container = self.docker_client.containers.get(container_id)
            container_key = f"container:registry:{container_id}"
            
            # Get current container info
            container_data = await self.redis.hgetall(container_key)
            if not container_data:
                return
            
            # Check container status
            if container.status != "running":
                await self.redis.hset(container_key, mapping={
                    "status": ContainerStatus.UNHEALTHY,
                    "health_score": 0,
                    "last_health_check": datetime.utcnow().isoformat()
                })
                return
            
            # Calculate health score
            health_score = 100
            
            # Check resource usage
            resources = await self._get_container_resources(container)
            if resources.get("cpu_usage_percent", 0) > 90:
                health_score -= 20
            if resources.get("memory_percent", 0) > 90:
                health_score -= 20
            
            # Try to ping agent endpoint if available
            try:
                result = container.exec_run("curl -f http://localhost:8001/health", demux=True)
                if result.exit_code != 0:
                    health_score -= 30
            except:
                pass
            
            # Update health information
            await self.redis.hset(container_key, mapping={
                "status": ContainerStatus.ACTIVE if health_score > 50 else ContainerStatus.UNHEALTHY,
                "health_score": health_score,
                "last_health_check": datetime.utcnow().isoformat(),
                "resources": json.dumps(resources)
            })
            
        except docker.errors.NotFound:
            # Container no longer exists
            await self._unregister_container(container_id)
        except Exception as e:
            logger.error(f"Error checking health of container {container_id}: {e}")
    
    async def get_available_containers(self, capability: Optional[ContainerCapability] = None) -> List[Dict[str, Any]]:
        """Get list of available containers, optionally filtered by capability"""
        try:
            active_containers = await self.redis.smembers("containers:active")
            available = []
            
            for container_id_bytes in active_containers:
                container_id = container_id_bytes.decode() if isinstance(container_id_bytes, bytes) else container_id_bytes
                container_key = f"container:registry:{container_id}"
                container_data = await self.redis.hgetall(container_key)
                
                if not container_data:
                    continue
                
                # Parse container info
                container_info = {}
                for key, value in container_data.items():
                    key_str = key.decode() if isinstance(key, bytes) else key
                    value_str = value.decode() if isinstance(value, bytes) else value
                    
                    if key_str in ["capabilities", "resources", "network_info", "labels"]:
                        try:
                            container_info[key_str] = json.loads(value_str)
                        except:
                            container_info[key_str] = value_str
                    else:
                        container_info[key_str] = value_str
                
                # Filter by capability if specified
                if capability:
                    if capability not in container_info.get("capabilities", []):
                        continue
                
                # Only include healthy containers
                if container_info.get("status") == ContainerStatus.ACTIVE:
                    available.append(container_info)
            
            return available
            
        except Exception as e:
            logger.error(f"Error getting available containers: {e}")
            return []


# Singleton instance
container_discovery_service = ContainerDiscoveryService()