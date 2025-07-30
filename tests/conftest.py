"""Test configuration and fixtures"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import redis.asyncio as redis
import docker

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_redis():
    """Mock Redis client"""
    mock = AsyncMock(spec=redis.Redis)
    mock.get.return_value = None
    mock.set.return_value = True
    mock.keys.return_value = []
    mock.delete.return_value = 1
    mock.ping.return_value = True
    return mock

@pytest.fixture
def mock_docker():
    """Mock Docker client"""
    mock = Mock(spec=docker.DockerClient)
    mock.ping.return_value = True
    
    # Mock container operations
    container = Mock()
    container.id = "test-container-id"
    container.stop.return_value = None
    container.remove.return_value = None
    
    mock.containers.run.return_value = container
    mock.containers.get.return_value = container
    
    return mock

@pytest.fixture
def test_token():
    """Generate test JWT token"""
    import jwt
    import os
    from datetime import datetime, timedelta
    
    secret = os.getenv("JWT_SECRET", "test-secret")
    payload = {
        "sub": "test@example.com",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, secret, algorithm="HS256")