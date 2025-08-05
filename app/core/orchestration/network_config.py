"""
Dynamic Network Configuration Service

Replaces hardcoded network addresses with dynamic configuration:
- Service discovery and registration
- Dynamic port allocation
- Multi-region network management
- Load balancer configuration
- Network health monitoring
"""
import asyncio
import socket
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration"""
    service_name: str
    host: str
    port: int
    protocol: str = "http"
    health_check_path: str = "/health"
    region: str = "default"
    availability_zone: str = "default"
    
    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"
        
    @property 
    def health_url(self) -> str:
        return f"{self.url}{self.health_check_path}"


class NetworkConfiguration:
    """Dynamic network configuration manager"""
    
    def __init__(self):
        self.redis = None
        self.service_registry: Dict[str, ServiceEndpoint] = {}
        self.port_allocator = PortAllocator()
        self.health_checker = HealthChecker()
        self.running = False
        
        # Network settings
        self.base_port_range = (8000, 9000)  # Configurable port range
        self.external_ip = None
        self.region = os.getenv("REGION", "default")
        self.availability_zone = os.getenv("AZ", "default")
        
        logger.info("🌐 Network configuration manager initialized")
        
    async def initialize(self, redis):
        """Initialize network configuration"""
        self.redis = redis
        
        # Detect external IP
        self.external_ip = await self._detect_external_ip()
        
        # Initialize components
        await self.port_allocator.initialize(redis)
        await self.health_checker.initialize(redis)
        
        # Load existing service registry
        await self._load_service_registry()
        
        logger.info(f"🌐 Network config ready - External IP: {self.external_ip}")
        
    async def start(self):
        """Start network configuration service"""
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._registry_maintenance())
        asyncio.create_task(self._health_monitoring())
        asyncio.create_task(self._cleanup_stale_services())
        
        logger.info("✅ Network configuration service started")
        
    async def stop(self):
        """Stop network configuration service"""
        self.running = False
        logger.info("🛑 Network configuration service stopped")
        
    async def register_service(
        self, 
        service_name: str, 
        preferred_port: Optional[int] = None,
        protocol: str = "http",
        health_check_path: str = "/health"
    ) -> ServiceEndpoint:
        """Register a new service and allocate network resources"""
        try:
            # Allocate port
            if preferred_port and await self.port_allocator.is_port_available(preferred_port):
                port = preferred_port
            else:
                port = await self.port_allocator.allocate_port(service_name)
                
            # Create endpoint
            endpoint = ServiceEndpoint(
                service_name=service_name,
                host=self.external_ip or "localhost",
                port=port,
                protocol=protocol,
                health_check_path=health_check_path,
                region=self.region,
                availability_zone=self.availability_zone
            )
            
            # Register in local registry
            self.service_registry[service_name] = endpoint
            
            # Store in Redis for cluster-wide access
            await self._store_service_endpoint(endpoint)
            
            logger.info(f"📋 Registered service {service_name} at {endpoint.url}")
            return endpoint
            
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            raise
            
    async def unregister_service(self, service_name: str):
        """Unregister a service and free resources"""
        try:
            if service_name in self.service_registry:
                endpoint = self.service_registry[service_name]
                
                # Free port
                await self.port_allocator.free_port(service_name, endpoint.port)
                
                # Remove from registry
                del self.service_registry[service_name]
                
                # Remove from Redis
                await self.redis.hdel("network:services", service_name)
                
                logger.info(f"🗑️ Unregistered service {service_name}")
                
        except Exception as e:
            logger.error(f"Failed to unregister service {service_name}: {e}")
            
    async def discover_service(self, service_name: str) -> Optional[ServiceEndpoint]:
        """Discover a service endpoint"""
        # Check local registry first
        if service_name in self.service_registry:
            return self.service_registry[service_name]
            
        # Check Redis for cluster-wide services
        service_data = await self.redis.hget("network:services", service_name)
        if service_data:
            data = json.loads(service_data)
            return ServiceEndpoint(**data)
            
        return None
        
    async def discover_services_by_type(self, service_prefix: str) -> List[ServiceEndpoint]:
        """Discover all services matching a prefix"""
        services = []
        
        # Get all services from Redis
        all_services = await self.redis.hgetall("network:services")
        
        for service_name, service_data in all_services.items():
            if service_name.decode().startswith(service_prefix):
                data = json.loads(service_data)
                services.append(ServiceEndpoint(**data))
                
        return services
        
    async def get_load_balancer_config(self, service_prefix: str) -> Dict[str, Any]:
        """Get load balancer configuration for a service type"""
        services = await self.discover_services_by_type(service_prefix)
        
        if not services:
            return {"backends": [], "strategy": "round_robin"}
            
        # Filter healthy services
        healthy_services = []
        for service in services:
            if await self.health_checker.is_service_healthy(service):
                healthy_services.append(service)
                
        return {
            "backends": [
                {
                    "name": service.service_name,
                    "url": service.url,
                    "weight": 1,
                    "health_check": service.health_url
                }
                for service in healthy_services
            ],
            "strategy": "round_robin",
            "health_check_interval": 30,
            "timeout": 10
        }
        
    async def update_network_config(self, config: Dict[str, Any]):
        """Update network configuration dynamically"""
        try:
            if "base_port_range" in config:
                self.base_port_range = tuple(config["base_port_range"])
                await self.port_allocator.update_port_range(self.base_port_range)
                
            if "external_ip" in config:
                old_ip = self.external_ip
                self.external_ip = config["external_ip"]
                
                # Update all registered services
                await self._update_service_ips(old_ip, self.external_ip)
                
            if "region" in config:
                self.region = config["region"]
                
            logger.info(f"🔄 Network configuration updated: {config}")
            
        except Exception as e:
            logger.error(f"Failed to update network config: {e}")
            raise
            
    async def _detect_external_ip(self) -> str:
        """Detect external IP address"""
        # Priority order for IP detection
        ip_sources = [
            os.getenv("EXTERNAL_IP"),  # Environment variable
            await self._get_docker_host_ip(),  # Docker host IP
            await self._get_local_ip(),  # Local interface IP
            "127.0.0.1"  # Fallback
        ]
        
        for ip in ip_sources:
            if ip and ip != "127.0.0.1":
                return ip
                
        return "127.0.0.1"
        
    async def _get_docker_host_ip(self) -> Optional[str]:
        """Get Docker host IP"""
        try:
            # In Docker, host.docker.internal resolves to host IP
            return socket.gethostbyname("host.docker.internal")
        except:
            return None
            
    async def _get_local_ip(self) -> Optional[str]:
        """Get local network IP"""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return None
            
    async def _load_service_registry(self):
        """Load service registry from Redis"""
        try:
            services = await self.redis.hgetall("network:services")
            
            for service_name, service_data in services.items():
                data = json.loads(service_data)
                endpoint = ServiceEndpoint(**data)
                self.service_registry[service_name.decode()] = endpoint
                
            logger.info(f"📥 Loaded {len(self.service_registry)} services from registry")
            
        except Exception as e:
            logger.error(f"Failed to load service registry: {e}")
            
    async def _store_service_endpoint(self, endpoint: ServiceEndpoint):
        """Store service endpoint in Redis"""
        service_data = {
            "service_name": endpoint.service_name,
            "host": endpoint.host,
            "port": endpoint.port,
            "protocol": endpoint.protocol,
            "health_check_path": endpoint.health_check_path,
            "region": endpoint.region,
            "availability_zone": endpoint.availability_zone,
            "registered_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.hset(
            "network:services",
            endpoint.service_name,
            json.dumps(service_data)
        )
        
    async def _update_service_ips(self, old_ip: str, new_ip: str):
        """Update IP addresses for all registered services"""
        for service_name, endpoint in self.service_registry.items():
            if endpoint.host == old_ip:
                endpoint.host = new_ip
                await self._store_service_endpoint(endpoint)
                
        logger.info(f"🔄 Updated service IPs from {old_ip} to {new_ip}")
        
    async def _registry_maintenance(self):
        """Maintain service registry"""
        while self.running:
            try:
                # Sync local registry with Redis
                await self._load_service_registry()
                
                # Update service health status
                for service_name, endpoint in list(self.service_registry.items()):
                    health_status = await self.health_checker.check_service_health(endpoint)
                    
                    # Store health status
                    await self.redis.hset(
                        "network:service_health",
                        service_name,
                        json.dumps({
                            "healthy": health_status,
                            "last_check": datetime.utcnow().isoformat()
                        })
                    )
                    
                await asyncio.sleep(60)  # Maintenance every minute
                
            except Exception as e:
                logger.error(f"Error in registry maintenance: {e}")
                await asyncio.sleep(60)
                
    async def _health_monitoring(self):
        """Monitor service health"""
        while self.running:
            try:
                unhealthy_services = []
                
                for service_name, endpoint in self.service_registry.items():
                    if not await self.health_checker.is_service_healthy(endpoint):
                        unhealthy_services.append(service_name)
                        
                if unhealthy_services:
                    logger.warning(f"🚨 Unhealthy services: {unhealthy_services}")
                    
                    # Publish health alert
                    await self.redis.publish(
                        "orchestrator:events",
                        json.dumps({
                            "type": "network.services_unhealthy",
                            "source": "network_config",
                            "data": {
                                "unhealthy_services": unhealthy_services,
                                "total_services": len(self.service_registry)
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    )
                    
                await asyncio.sleep(30)  # Health check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(30)
                
    async def _cleanup_stale_services(self):
        """Clean up stale service registrations"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                stale_threshold = timedelta(hours=1)
                
                services_to_remove = []
                all_services = await self.redis.hgetall("network:services")
                
                for service_name, service_data in all_services.items():
                    data = json.loads(service_data)
                    registered_at = datetime.fromisoformat(data.get("registered_at", current_time.isoformat()))
                    
                    # If service is old and unhealthy, mark for removal
                    if current_time - registered_at > stale_threshold:
                        endpoint = ServiceEndpoint(**data)
                        if not await self.health_checker.is_service_healthy(endpoint):
                            services_to_remove.append(service_name.decode())
                            
                # Remove stale services
                for service_name in services_to_remove:
                    await self.unregister_service(service_name)
                    logger.info(f"🧹 Cleaned up stale service: {service_name}")
                    
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                logger.error(f"Error in stale service cleanup: {e}")
                await asyncio.sleep(3600)


class PortAllocator:
    """Dynamic port allocation manager"""
    
    def __init__(self):
        self.redis = None
        self.allocated_ports: Dict[str, int] = {}
        self.port_range = (8000, 9000)
        
    async def initialize(self, redis):
        """Initialize port allocator"""
        self.redis = redis
        
        # Load existing allocations
        allocations = await self.redis.hgetall("network:port_allocations")
        for service_name, port in allocations.items():
            self.allocated_ports[service_name.decode()] = int(port)
            
    async def allocate_port(self, service_name: str) -> int:
        """Allocate a port for a service"""
        # Check if service already has a port
        if service_name in self.allocated_ports:
            return self.allocated_ports[service_name]
            
        # Find available port
        for port in range(self.port_range[0], self.port_range[1]):
            if await self.is_port_available(port):
                # Allocate port
                self.allocated_ports[service_name] = port
                await self.redis.hset("network:port_allocations", service_name, port)
                
                logger.info(f"🔌 Allocated port {port} to {service_name}")
                return port
                
        raise RuntimeError(f"No available ports in range {self.port_range}")
        
    async def free_port(self, service_name: str, port: int):
        """Free a port allocation"""
        if service_name in self.allocated_ports:
            del self.allocated_ports[service_name]
            await self.redis.hdel("network:port_allocations", service_name)
            logger.info(f"🔌 Freed port {port} from {service_name}")
            
    async def is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        # Check our allocations
        if port in self.allocated_ports.values():
            return False
            
        # Check if port is actually open
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return True
        except OSError:
            return False
            
    async def update_port_range(self, new_range: Tuple[int, int]):
        """Update port allocation range"""
        self.port_range = new_range
        logger.info(f"🔌 Updated port range to {new_range}")


class HealthChecker:
    """Service health monitoring"""
    
    def __init__(self):
        self.redis = None
        self.health_cache: Dict[str, Tuple[bool, datetime]] = {}
        self.cache_ttl = timedelta(seconds=30)
        
    async def initialize(self, redis):
        """Initialize health checker"""
        self.redis = redis
        
    async def check_service_health(self, endpoint: ServiceEndpoint) -> bool:
        """Check service health with caching"""
        # Check cache first
        if endpoint.service_name in self.health_cache:
            is_healthy, checked_at = self.health_cache[endpoint.service_name]
            if datetime.utcnow() - checked_at < self.cache_ttl:
                return is_healthy
                
        # Perform actual health check
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(endpoint.health_url) as response:
                    is_healthy = response.status == 200
                    
        except Exception as e:
            logger.debug(f"Health check failed for {endpoint.service_name}: {e}")
            is_healthy = False
            
        # Cache result
        self.health_cache[endpoint.service_name] = (is_healthy, datetime.utcnow())
        
        return is_healthy
        
    async def is_service_healthy(self, endpoint: ServiceEndpoint) -> bool:
        """Check if service is healthy (with cache)"""
        return await self.check_service_health(endpoint)


# Global network configuration instance
network_config = NetworkConfiguration()