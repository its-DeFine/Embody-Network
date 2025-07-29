"""
Pytest configuration and shared fixtures
"""
import pytest
import asyncio
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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