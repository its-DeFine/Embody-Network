"""
Pytest configuration and shared fixtures
"""
import pytest
import asyncio
import os
from pathlib import Path
import sys
import httpx
import redis.asyncio as redis
import aio_pika
import json
import time
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock
import jwt
from faker import Faker

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Initialize Faker for test data generation
fake = Faker()

# Configure event loop
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Common test data
@pytest.fixture
def sample_customer_data():
    return {
        "name": "Test Company",
        "email": "test@example.com",
        "tier": "pro",
        "max_agents": 10,
        "max_teams": 5
    }

@pytest.fixture
def sample_agent_config():
    return {
        "agent_id": "test-agent-123",
        "customer_id": "test-customer-123",
        "agent_type": "trading",
        "name": "Test Trading Agent",
        "description": "Test agent for unit tests",
        "config": {
            "trading_pairs": ["BTC/USDT"],
            "risk_limit": 0.02
        },
        "autogen_config": {
            "temperature": 0.7,
            "max_tokens": 1000
        }
    }

@pytest.fixture
def mock_redis_url():
    return os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")

@pytest.fixture
def mock_rabbitmq_url():
    return os.getenv("TEST_RABBITMQ_URL", "amqp://admin:password@localhost:5672/")


# HTTP Client Fixtures
@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an unauthenticated HTTP client"""
    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=30.0,
        follow_redirects=True
    ) as client:
        yield client


@pytest.fixture
async def authenticated_client(
    client: httpx.AsyncClient
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an authenticated HTTP client with test user"""
    # Login with test credentials
    login_response = await client.post(
        "/auth/login",
        json={
            "email": os.getenv("TEST_USER_EMAIL", "test@example.com"),
            "api_key": os.getenv("TEST_USER_API_KEY", "test-api-key")
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
    else:
        # Create mock token for testing
        token = create_test_jwt("test-user-123")
        client.headers["Authorization"] = f"Bearer {token}"
    
    yield client


@pytest.fixture
async def admin_client(
    client: httpx.AsyncClient
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an authenticated HTTP client with admin user"""
    # Login with admin credentials
    login_response = await client.post(
        "/auth/login",
        json={
            "email": os.getenv("TEST_ADMIN_EMAIL", "admin@example.com"),
            "api_key": os.getenv("TEST_ADMIN_API_KEY", "admin-test-key")
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
    else:
        # Create mock admin token for testing
        token = create_test_jwt("admin-user-123", is_admin=True)
        client.headers["Authorization"] = f"Bearer {token}"
    
    yield client


# Redis Fixtures
@pytest.fixture
async def redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Create Redis client for testing"""
    client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/1"),
        decode_responses=True
    )
    
    # Clear test database before tests
    await client.flushdb()
    
    yield client
    
    # Cleanup after tests
    await client.flushdb()
    await client.close()


# RabbitMQ Fixtures
@pytest.fixture
async def rabbitmq_connection() -> AsyncGenerator[aio_pika.Connection, None]:
    """Create RabbitMQ connection for testing"""
    connection = await aio_pika.connect_robust(
        os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    )
    
    yield connection
    
    await connection.close()


@pytest.fixture
async def rabbitmq_channel(
    rabbitmq_connection: aio_pika.Connection
) -> AsyncGenerator[aio_pika.Channel, None]:
    """Create RabbitMQ channel for testing"""
    channel = await rabbitmq_connection.channel()
    
    # Declare test exchange
    exchange = await channel.declare_exchange(
        "test_exchange",
        aio_pika.ExchangeType.TOPIC,
        durable=False
    )
    
    yield channel
    
    await channel.close()


# Authentication Helpers
def create_test_jwt(
    user_id: str,
    is_admin: bool = False,
    expires_in: int = 3600
) -> str:
    """Create a test JWT token"""
    payload = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(
        payload,
        os.getenv("JWT_SECRET", "test-secret-key"),
        algorithm="HS256"
    )


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create authentication headers for testing"""
    token = create_test_jwt("test-user-123")
    return {"Authorization": f"Bearer {token}"}


# Test Data Fixtures
@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """Sample task data for testing"""
    return {
        "task_id": fake.uuid4(),
        "agent_id": "test-agent-123",
        "type": "market_analysis",
        "status": "pending",
        "payload": {
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "indicators": ["RSI", "MACD"]
        },
        "created_at": datetime.utcnow().isoformat(),
        "priority": "medium"
    }


@pytest.fixture
def sample_team_data() -> Dict[str, Any]:
    """Sample team data for testing"""
    return {
        "team_id": fake.uuid4(),
        "name": fake.company() + " Trading Team",
        "description": fake.text(max_nb_chars=100),
        "agents": [
            "agent-123",
            "agent-456",
            "agent-789"
        ],
        "roles": {
            "agent-123": "lead",
            "agent-456": "analyst",
            "agent-789": "executor"
        },
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Sample market data for testing"""
    base_price = 50000.0
    return {
        "symbol": "BTC/USDT",
        "timestamp": int(time.time() * 1000),
        "open": base_price,
        "high": base_price * 1.02,
        "low": base_price * 0.98,
        "close": base_price * 1.01,
        "volume": fake.random_number(digits=6),
        "bid": base_price * 1.009,
        "ask": base_price * 1.011,
        "bid_volume": fake.random_number(digits=4),
        "ask_volume": fake.random_number(digits=4)
    }


# Mock Response Fixtures
@pytest.fixture
def mock_exchange_response():
    """Mock exchange API response"""
    return {
        "symbol": "BTC/USDT",
        "lastPrice": "50000.00",
        "volume": "12345.67",
        "high24h": "51000.00",
        "low24h": "49000.00",
        "change24h": "2.5"
    }


@pytest.fixture
def mock_agent_response():
    """Mock agent creation response"""
    return {
        "agent_id": fake.uuid4(),
        "status": "created",
        "message": "Agent created successfully",
        "created_at": datetime.utcnow().isoformat()
    }


# Cleanup Fixtures
@pytest.fixture(autouse=True)
async def cleanup_test_agents(authenticated_client):
    """Automatically cleanup test agents after each test"""
    created_agents = []
    
    # Store original post method
    original_post = authenticated_client.post
    
    # Wrap post method to track created agents
    async def tracked_post(url, *args, **kwargs):
        response = await original_post(url, *args, **kwargs)
        if url == "/agents" and response.status_code == 200:
            agent_id = response.json().get("agent_id")
            if agent_id:
                created_agents.append(agent_id)
        return response
    
    authenticated_client.post = tracked_post
    
    yield
    
    # Cleanup created agents
    for agent_id in created_agents:
        try:
            await authenticated_client.delete(f"/agents/{agent_id}")
        except Exception:
            pass  # Ignore cleanup errors


# Performance Testing Helpers
@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    class Timer:
        def __init__(self):
            self.times = {}
        
        def start(self, name: str):
            self.times[name] = time.time()
        
        def stop(self, name: str) -> float:
            if name not in self.times:
                return 0.0
            elapsed = time.time() - self.times[name]
            del self.times[name]
            return elapsed
        
        def measure(self, name: str):
            return self._TimerContext(self, name)
        
        class _TimerContext:
            def __init__(self, timer, name):
                self.timer = timer
                self.name = name
            
            async def __aenter__(self):
                self.timer.start(self.name)
                return self
            
            async def __aexit__(self, *args):
                self.elapsed = self.timer.stop(self.name)
    
    return Timer()


# WebSocket Testing Fixtures
@pytest.fixture
async def websocket_url():
    """WebSocket URL for testing"""
    return "ws://localhost:8000/ws"


# Environment Configuration
@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test environment variables"""
    test_env = {
        "ENVIRONMENT": "test",
        "TESTING": "1",
        "LOG_LEVEL": "DEBUG",
        "DISABLE_AUTH_FOR_TESTS": "false",
        "REDIS_DB": "1",
        "ENABLE_TEST_ENDPOINTS": "true"
    }
    
    # Set environment variables
    for key, value in test_env.items():
        if key not in os.environ:
            os.environ[key] = value
    
    yield
    
    # Cleanup (optional)
    # for key in test_env:
    #     os.environ.pop(key, None)


# Mock Service Fixtures
@pytest.fixture
def mock_redis_service():
    """Mock Redis service for unit tests"""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    mock.hget.return_value = None
    mock.hset.return_value = True
    mock.hgetall.return_value = {}
    mock.lpush.return_value = 1
    mock.rpop.return_value = None
    mock.llen.return_value = 0
    return mock


@pytest.fixture
def mock_rabbitmq_service():
    """Mock RabbitMQ service for unit tests"""
    mock = AsyncMock()
    mock.publish.return_value = True
    mock.consume.return_value = AsyncMock()
    return mock


# Test Markers Configuration
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require external services"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring services"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take more than 5 seconds"
    )
    config.addinivalue_line(
        "markers", "gpu: Tests requiring GPU resources"
    )
    config.addinivalue_line(
        "markers", "performance: Performance/load tests"
    )