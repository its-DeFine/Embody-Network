"""
Redis caching utilities for OpenBB Adapter
"""
import json
import asyncio
from typing import Any, Optional
from datetime import timedelta
import redis.asyncio as redis


class RedisCache:
    """Redis cache wrapper with JSON serialization"""
    
    def __init__(self, redis_client: redis.Redis):
        self.client = redis_client
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = await self.client.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL"""
        serialized = json.dumps(value)
        if ttl:
            return await self.client.setex(key, ttl, serialized)
        return await self.client.set(key, serialized)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        return await self.client.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self.client.exists(key) > 0
    
    async def get_ttl(self, key: str) -> int:
        """Get remaining TTL for key"""
        return await self.client.ttl(key)
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        keys = []
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            return await self.client.delete(*keys)
        return 0
    
    async def get_or_set(
        self,
        key: str,
        factory,
        ttl: Optional[int] = None
    ) -> Any:
        """Get from cache or compute and set"""
        value = await self.get(key)
        if value is not None:
            return value
        
        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        # Cache it
        await self.set(key, value, ttl)
        return value