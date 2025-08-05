"""
Test Docker setup and basic container functionality
"""
import pytest
import docker
import time
import requests
import logging

logger = logging.getLogger(__name__)

@pytest.mark.e2e
def test_docker_available():
    """Test that Docker is available and accessible"""
    try:
        client = docker.from_env()
        info = client.info()
        logger.info(f"✅ Docker info: {info.get('ServerVersion', 'unknown')}")
        assert info is not None
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")

@pytest.mark.e2e  
def test_simple_container():
    """Test basic container functionality"""
    client = docker.from_env()
    
    # Run a simple container
    container = client.containers.run(
        "python:3.11-slim",
        command=["python", "-c", "print('Hello from container'); import time; time.sleep(5)"],
        detach=True,
        remove=True
    )
    
    try:
        # Wait for container to finish
        container.wait(timeout=10)
        logs = container.logs().decode('utf-8')
        assert "Hello from container" in logs
        logger.info("✅ Simple container test passed")
    finally:
        try:
            container.remove(force=True)
        except:
            pass

@pytest.mark.e2e
def test_redis_container():
    """Test Redis container functionality"""
    client = docker.from_env()
    
    # Start Redis container
    redis_container = client.containers.run(
        "redis:7-alpine",
        name="test-redis-simple",
        command=["redis-server", "--bind", "0.0.0.0"],
        ports={"6379/tcp": 6380},  # Use different port to avoid conflicts
        detach=True,
        remove=False
    )
    
    try:
        # Wait for Redis to start
        time.sleep(5)
        
        # Test Redis is responding
        redis_container.reload()
        assert redis_container.status == "running"
        
        logger.info("✅ Redis container test passed")
        
    finally:
        try:
            redis_container.stop(timeout=5)
            redis_container.remove()
        except Exception as e:
            logger.warning(f"Failed to cleanup Redis: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])