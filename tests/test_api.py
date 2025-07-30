"""API endpoint tests"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"

def test_login_success():
    """Test successful login"""
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "admin"  # Default password
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure():
    """Test failed login"""
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrong_password"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

def test_list_agents_unauthorized():
    """Test listing agents without auth"""
    response = client.get("/api/v1/agents")
    assert response.status_code == 403  # Forbidden without auth

def test_agent_crud():
    """Test agent CRUD operations"""
    # First login
    login_response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "admin"
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create agent
    create_response = client.post("/api/v1/agents", 
        json={
            "name": "Test Trading Agent",
            "agent_type": "trading",
            "config": {"max_risk": 0.02}
        },
        headers=headers
    )
    assert create_response.status_code == 200
    agent = create_response.json()
    assert agent["name"] == "Test Trading Agent"
    assert agent["type"] == "trading"
    assert agent["status"] == "created"
    agent_id = agent["id"]
    
    # List agents
    list_response = client.get("/api/v1/agents", headers=headers)
    assert list_response.status_code == 200
    agents = list_response.json()
    assert len(agents) >= 1
    assert any(a["id"] == agent_id for a in agents)
    
    # Get specific agent
    get_response = client.get(f"/api/v1/agents/{agent_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == agent_id
    
    # Delete agent
    delete_response = client.delete(f"/api/v1/agents/{agent_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Agent deleted"
    
    # Verify deletion
    get_deleted = client.get(f"/api/v1/agents/{agent_id}", headers=headers)
    assert get_deleted.status_code == 404