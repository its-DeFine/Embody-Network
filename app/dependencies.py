"""Shared dependencies for FastAPI"""
import os
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import redis.asyncio as redis
import docker

# Security
security = HTTPBearer()

# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"

# Global clients
redis_client: Optional[redis.Redis] = None
docker_client: Optional[docker.DockerClient] = None

async def get_redis():
    """Get Redis client"""
    global redis_client
    if not redis_client:
        redis_client = await redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
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