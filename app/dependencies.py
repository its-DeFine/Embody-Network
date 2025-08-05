"""Shared dependencies for FastAPI"""
import os
from typing import Optional, List
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps
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
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {
            "email": email,
            "role": payload.get("role", "viewer"),  # Default to viewer role
            "permissions": payload.get("permissions", [])
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Role-based authorization system
ROLE_PERMISSIONS = {
    "admin": [
        "trading:start", "trading:stop", "trading:execute", "trading:config",
        "system:manage", "user:manage", "audit:view", "gpu:manage"
    ],
    "trader": [
        "trading:start", "trading:stop", "trading:execute", "trading:view",
        "market:view", "portfolio:view"
    ],
    "viewer": [
        "trading:view", "market:view", "portfolio:view"
    ]
}

def require_permission(permission: str):
    """Decorator to require specific permission for endpoint access"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (injected by FastAPI dependency)
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, dict) and "email" in value and "role" in value:
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            user_role = current_user.get("role", "viewer")
            user_permissions = ROLE_PERMISSIONS.get(user_role, [])
            
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access denied. Required permission: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Convenience functions for common authorization patterns
async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def require_trader(current_user: dict = Depends(get_current_user)):
    """Require trader or admin role"""
    role = current_user.get("role")
    if role not in ["admin", "trader"]:
        raise HTTPException(status_code=403, detail="Trader access required")
    return current_user

async def require_trading_access(current_user: dict = Depends(get_current_user)):
    """Require trading permissions (admin or trader)"""
    role = current_user.get("role")
    if role not in ["admin", "trader"]:
        raise HTTPException(status_code=403, detail="Trading access required")
    return current_user