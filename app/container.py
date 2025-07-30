"""Dependency injection container"""
from typing import Optional
import redis.asyncio as redis
import docker
from .config import settings
from .orchestrator import Orchestrator
from .openbb_client import OpenBBClient

class Container:
    """Service container for dependency injection"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._docker: Optional[docker.DockerClient] = None
        self._orchestrator: Optional[Orchestrator] = None
        self._openbb: Optional[OpenBBClient] = None
        
    async def get_redis(self) -> redis.Redis:
        """Get or create Redis client"""
        if not self._redis:
            self._redis = await redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_pool_size
            )
        return self._redis
        
    def get_docker(self) -> docker.DockerClient:
        """Get or create Docker client"""
        if not self._docker:
            self._docker = docker.from_env()
        return self._docker
        
    async def get_orchestrator(self) -> Orchestrator:
        """Get or create orchestrator"""
        if not self._orchestrator:
            self._orchestrator = Orchestrator()
            await self._orchestrator.initialize()
        return self._orchestrator
        
    async def get_openbb(self) -> OpenBBClient:
        """Get or create OpenBB client"""
        if not self._openbb:
            self._openbb = OpenBBClient(settings.openbb_url)
        return self._openbb
        
    async def shutdown(self):
        """Clean shutdown of all services"""
        if self._redis:
            await self._redis.close()
        if self._docker:
            self._docker.close()
        if self._orchestrator:
            await self._orchestrator.stop()
        if self._openbb:
            await self._openbb.close()

# Global container instance
container = Container()