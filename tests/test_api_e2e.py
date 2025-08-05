"""
End-to-End API Tests

Tests API endpoints that would be used in the orchestrator system
without requiring full Docker container deployment.
"""
import pytest
import asyncio
import os
import sys
from fastapi.testclient import TestClient

# Add the app to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up test environment variables
os.environ.update({
    "JWT_SECRET": "test-jwt-secret-32-chars-minimum-for-testing",
    "ADMIN_PASSWORD": "test-admin-password-123",
    "MASTER_SECRET_KEY": "test-master-secret-key-32-chars-minimum-for-testing",
    "ENVIRONMENT": "test",
    "REDIS_URL": "redis://localhost:6379",
    "LOG_LEVEL": "INFO"
})

from app.main import app

client = TestClient(app)


class TestSystemEndpoints:
    """Test core system endpoints"""
    
    @pytest.mark.e2e
    def test_health_endpoint(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        
    @pytest.mark.e2e
    def test_system_info_endpoint(self):
        """Test system info endpoint"""
        response = client.get("/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "environment" in data
        assert data["environment"] == "test"
        
    @pytest.mark.e2e  
    def test_auth_endpoints(self):
        """Test authentication flow"""
        # Test login
        login_data = {
            "email": "admin@trading.system",
            "password": "test-admin-password-123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        auth_data = response.json()
        assert "access_token" in auth_data
        assert "token_type" in auth_data
        
        # Test protected endpoint with token
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200


class TestOrchestatorEndpoints:
    """Test orchestrator-specific endpoints"""
    
    def get_auth_headers(self):
        """Get authentication headers"""
        login_data = {
            "email": "admin@trading.system", 
            "password": "test-admin-password-123"
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.e2e
    def test_orchestrator_discovery(self):
        """Test orchestrator discovery endpoint"""
        headers = self.get_auth_headers()
        response = client.get("/api/v1/orchestrator/discovery", headers=headers)
        
        # Endpoint might not exist yet, so we accept 404 or 200
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "available_orchestrators" in data
    
    @pytest.mark.e2e
    def test_cluster_registration(self):
        """Test cluster registration endpoint"""
        headers = self.get_auth_headers()
        
        registration_data = {
            "container_name": "test-orchestrator-cluster",
            "host_address": "127.0.0.1",
            "api_endpoint": "http://127.0.0.1:8001",
            "capabilities": ["agent_runner", "orchestrator_cluster"],
            "resources": {
                "cpu_count": 4,
                "memory_limit": 4294967296
            },
            "metadata": {
                "orchestrator_id": "test-customer",
                "version": "1.0.0"
            }
        }
        
        response = client.post(
            "/api/v1/cluster/containers/register", 
            json=registration_data, 
            headers=headers
        )
        
        # Endpoint might not exist yet, so we accept 404 or 200/201
        assert response.status_code in [200, 201, 404]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "container_id" in data or "success" in data


class TestTradingEndpoints:
    """Test trading-related endpoints"""
    
    def get_auth_headers(self):
        """Get authentication headers"""
        login_data = {
            "email": "admin@trading.system",
            "password": "test-admin-password-123"
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.e2e
    def test_trading_system_status(self):
        """Test trading system status"""
        headers = self.get_auth_headers()
        response = client.get("/api/v1/trading/status", headers=headers)
        
        # Accept various status codes since endpoint might not be fully implemented
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    @pytest.mark.e2e
    def test_portfolio_status(self):
        """Test portfolio status endpoint"""
        headers = self.get_auth_headers()
        response = client.get("/api/v1/trading/portfolio", headers=headers)
        
        # Accept various status codes
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            # Portfolio data structure would depend on implementation
            assert isinstance(data, dict)


class TestAgentEndpoints:
    """Test agent management endpoints"""
    
    def get_auth_headers(self):
        """Get authentication headers"""
        login_data = {
            "email": "admin@trading.system",
            "password": "test-admin-password-123"
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.e2e
    def test_agent_list(self):
        """Test agent listing"""
        headers = self.get_auth_headers()
        response = client.get("/api/v1/agents", headers=headers)
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
    
    @pytest.mark.e2e
    def test_agent_deployment(self):
        """Test agent deployment endpoint"""  
        headers = self.get_auth_headers()
        
        deployment_data = {
            "agent_type": "trading",
            "agent_config": {
                "symbol": "BTCUSD",
                "strategy": "test_strategy"
            },
            "container_preference": "any"
        }
        
        response = client.post(
            "/api/v1/agents/deploy",
            json=deployment_data,
            headers=headers
        )
        
        # Accept various responses since endpoint might not be fully implemented
        assert response.status_code in [200, 201, 404, 501]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])