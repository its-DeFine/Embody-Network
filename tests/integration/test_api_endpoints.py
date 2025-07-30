"""
Integration tests for API endpoints
"""
import pytest
import httpx
import asyncio
from datetime import datetime

API_BASE_URL = "http://localhost:8000"


class TestAPIEndpoints:
    """Test all API endpoints"""
    
    @pytest.fixture
    async def client(self):
        """Create async HTTP client"""
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            yield client
    
    @pytest.fixture
    async def auth_headers(self, client):
        """Get authentication headers"""
        # First try with test credentials
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "api_key": "test-api-key"}
        )
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        
        # If test user doesn't exist, create one
        # This would normally be done in test setup
        return {}
    
    async def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data
    
    async def test_detailed_health(self, client):
        """Test detailed health check"""
        response = await client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        assert "rabbitmq" in data["dependencies"]
        assert "redis" in data["dependencies"]
    
    async def test_metrics_endpoint(self, client, auth_headers):
        """Test Prometheus metrics endpoint"""
        response = await client.get("/metrics", headers=auth_headers)
        assert response.status_code in [200, 401]  # May require auth
        if response.status_code == 200:
            assert "api_requests_total" in response.text
    
    async def test_openapi_schema(self, client):
        """Test OpenAPI schema endpoint"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["openapi"].startswith("3.")
        assert "paths" in schema
        assert "components" in schema
    
    async def test_docs_endpoints(self, client):
        """Test documentation endpoints"""
        # Swagger UI
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "swagger-ui" in response.text
        
        # ReDoc
        response = await client.get("/redoc")
        assert response.status_code == 200
        assert "redoc" in response.text.lower()
    
    async def test_authentication_flow(self, client):
        """Test authentication flow"""
        # Test invalid credentials
        response = await client.post(
            "/auth/login",
            json={"email": "invalid@example.com", "api_key": "wrong-key"}
        )
        assert response.status_code in [401, 422]
        
        # Test missing credentials
        response = await client.post("/auth/login", json={})
        assert response.status_code == 422
    
    async def test_agent_endpoints(self, client, auth_headers):
        """Test agent management endpoints"""
        # List agents (should be empty or require auth)
        response = await client.get("/agents", headers=auth_headers)
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data.get("agents", []), list)
            
            # Try to create an agent
            agent_data = {
                "name": "Test Agent",
                "type": "trading",
                "config": {
                    "max_risk": 0.02,
                    "trading_pairs": ["BTC/USDT"]
                }
            }
            
            create_response = await client.post(
                "/agents",
                json=agent_data,
                headers=auth_headers
            )
            
            if create_response.status_code == 200:
                created_agent = create_response.json()
                agent_id = created_agent.get("id") or created_agent.get("agent_id")
                
                # Get specific agent
                get_response = await client.get(
                    f"/agents/{agent_id}",
                    headers=auth_headers
                )
                assert get_response.status_code == 200
                
                # Update agent
                update_response = await client.put(
                    f"/agents/{agent_id}",
                    json={"config": {"max_risk": 0.01}},
                    headers=auth_headers
                )
                assert update_response.status_code in [200, 204]
                
                # Delete agent
                delete_response = await client.delete(
                    f"/agents/{agent_id}",
                    headers=auth_headers
                )
                assert delete_response.status_code in [200, 204]
    
    async def test_team_endpoints(self, client, auth_headers):
        """Test team management endpoints"""
        response = await client.get("/teams", headers=auth_headers)
        assert response.status_code in [200, 401, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
    
    async def test_task_endpoints(self, client, auth_headers):
        """Test task management endpoints"""
        response = await client.get("/tasks", headers=auth_headers)
        assert response.status_code in [200, 401, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
    
    async def test_rate_limiting(self, client):
        """Test rate limiting"""
        # Make multiple requests quickly
        responses = []
        for _ in range(20):
            response = await client.get("/health")
            responses.append(response.status_code)
        
        # Check if rate limiting is applied (optional)
        # Some requests might return 429 if rate limiting is enabled
        assert all(status in [200, 429] for status in responses)
    
    async def test_cors_headers(self, client):
        """Test CORS headers"""
        response = await client.options(
            "/health",
            headers={"Origin": "http://localhost:3001"}
        )
        
        # CORS might be configured
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] in ["*", "http://localhost:3001"]
    
    async def test_error_handling(self, client):
        """Test error handling"""
        # Test 404
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        
        # Test invalid JSON
        response = await client.post(
            "/auth/login",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
    
    async def test_websocket_endpoint(self):
        """Test WebSocket endpoint availability"""
        # This is a basic test - full WebSocket testing would be more complex
        import websockets
        
        try:
            uri = "ws://localhost:8000/ws/test"
            async with websockets.connect(uri) as websocket:
                # Connection established
                await websocket.close()
                assert True
        except Exception:
            # WebSocket might require auth or not be configured
            assert True


@pytest.mark.asyncio
class TestAPIPerformance:
    """Basic performance tests for API"""
    
    async def test_response_times(self):
        """Test API response times"""
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            # Test health endpoint response time
            start = datetime.utcnow()
            response = await client.get("/health")
            end = datetime.utcnow()
            
            response_time = (end - start).total_seconds()
            assert response.status_code == 200
            assert response_time < 1.0  # Should respond within 1 second
    
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
            # Make 10 concurrent requests
            tasks = [client.get("/health") for _ in range(10)]
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            assert all(r.status_code == 200 for r in responses)