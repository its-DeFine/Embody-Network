"""Shared dependencies for FastAPI"""
import os
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import redis.asyncio as redis
import docker

from .config import settings

# Security
security = HTTPBearer()

# Use centralized configuration - no hardcoded defaults
JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = settings.jwt_algorithm

# Global clients
redis_client: Optional[redis.Redis] = None
docker_client: Optional[docker.DockerClient] = None

async def get_redis():
    """Get Redis client"""
    global redis_client
    if not redis_client:
        redis_url = settings.redis_url
        redis_client = redis.from_url(redis_url)
        try:
            # Test the connection
            await redis_client.ping()
        except Exception as e:
            # Reset client on connection failure and close if needed
            if redis_client:
                await redis_client.close()
            redis_client = None
            raise e
    return redis_client

def get_docker():
    """Get Docker client"""
    global docker_client
    if not docker_client:
        docker_client = docker.from_env()
    return docker_client

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT and return current user"""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            JWT_SECRET, 
            algorithms=[JWT_ALGORITHM]
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")