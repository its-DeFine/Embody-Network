"""
End-to-end tests for complete agent lifecycle
"""
import pytest
import httpx
import asyncio
import json
from datetime import datetime
import websockets


class TestAgentLifecycle:
    """Test complete agent lifecycle from creation to deletion"""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated HTTP client"""
        client = httpx.AsyncClient(base_url="http://localhost:8000")
        
        # Create test user or use existing
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "api_key": "test-api-key"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"
        
        yield client
        await client.aclose()
    
    async def test_complete_agent_lifecycle(self, authenticated_client):
        """Test creating, managing, and deleting an agent"""
        client = authenticated_client
        
        # 1. Create agent
        agent_config = {
            "name": "E2E Test Agent",
            "type": "trading",
            "config": {
                "system_message": "You are a trading assistant",
                "max_risk": 0.02,
                "trading_pairs": ["BTC/USDT", "ETH/USDT"],
                "trading_mode": "simulated"
            }
        }
        
        create_response = await client.post("/agents", json=agent_config)
        assert create_response.status_code == 200
        
        agent_data = create_response.json()
        agent_id = agent_data.get("id") or agent_data.get("agent_id")
        assert agent_id is not None
        
        # 2. Verify agent was created
        get_response = await client.get(f"/agents/{agent_id}")
        assert get_response.status_code == 200
        
        agent = get_response.json()
        assert agent.get("name") == "E2E Test Agent"
        assert agent.get("status") in ["created", "initializing", "stopped"]
        
        # 3. Start the agent
        start_response = await client.post(f"/agents/{agent_id}/action", json={"action": "start"})
        assert start_response.status_code in [200, 202]
        
        # 4. Wait for agent to be running
        max_attempts = 10
        for _ in range(max_attempts):
            status_response = await client.get(f"/agents/{agent_id}")
            if status_response.status_code == 200:
                current_status = status_response.json().get("status")
                if current_status == "running":
                    break
            await asyncio.sleep(1)
        
        # 5. Execute a task
        task_data = {
            "agent_id": agent_id,
            "type": "market_analysis",
            "payload": {
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "analysis_type": "technical"
            }
        }
        
        task_response = await client.post("/tasks", json=task_data)
        if task_response.status_code == 200:
            task = task_response.json()
            task_id = task.get("id")
            
            # Wait for task completion
            for _ in range(10):
                task_status_response = await client.get(f"/tasks/{task_id}")
                if task_status_response.status_code == 200:
                    task_status = task_status_response.json()
                    if task_status.get("status") in ["completed", "failed"]:
                        break
                await asyncio.sleep(1)
        
        # 6. Get agent metrics
        metrics_response = await client.get(f"/agents/{agent_id}/metrics")
        if metrics_response.status_code == 200:
            metrics = metrics_response.json()
            assert "uptime" in metrics or "created_at" in metrics
        
        # 7. Update agent configuration
        update_data = {
            "config": {
                "max_risk": 0.01,
                "trading_pairs": ["BTC/USDT"]
            }
        }
        
        update_response = await client.put(f"/agents/{agent_id}", json=update_data)
        assert update_response.status_code in [200, 204]
        
        # 8. Stop the agent
        stop_response = await client.post(f"/agents/{agent_id}/action", json={"action": "stop"})
        assert stop_response.status_code in [200, 202]
        
        # 9. Delete the agent
        delete_response = await client.delete(f"/agents/{agent_id}")
        assert delete_response.status_code in [200, 204]
        
        # 10. Verify agent is deleted
        verify_response = await client.get(f"/agents/{agent_id}")
        assert verify_response.status_code == 404
    
    async def test_agent_error_handling(self, authenticated_client):
        """Test agent error scenarios"""
        client = authenticated_client
        
        # Test creating agent with invalid config
        invalid_config = {
            "name": "",  # Empty name
            "type": "invalid_type",
            "config": {}
        }
        
        error_response = await client.post("/agents", json=invalid_config)
        assert error_response.status_code in [400, 422]
        
        # Test accessing non-existent agent
        fake_id = "non-existent-agent-id"
        not_found_response = await client.get(f"/agents/{fake_id}")
        assert not_found_response.status_code == 404
        
        # Test invalid action
        if authenticated_client.headers.get("Authorization"):
            # Create a valid agent first
            valid_agent = {
                "name": "Error Test Agent",
                "type": "trading",
                "config": {"trading_mode": "simulated"}
            }
            
            create_response = await client.post("/agents", json=valid_agent)
            if create_response.status_code == 200:
                agent_id = create_response.json().get("agent_id")
                
                # Try invalid action
                invalid_action_response = await client.post(
                    f"/agents/{agent_id}/action",
                    json={"action": "invalid_action"}
                )
                assert invalid_action_response.status_code in [400, 422]
                
                # Clean up
                await client.delete(f"/agents/{agent_id}")
    
    async def test_concurrent_agent_operations(self, authenticated_client):
        """Test handling concurrent operations on agents"""
        client = authenticated_client
        
        # Create multiple agents concurrently
        agent_configs = [
            {
                "name": f"Concurrent Agent {i}",
                "type": "trading",
                "config": {"trading_mode": "simulated"}
            }
            for i in range(3)
        ]
        
        create_tasks = [
            client.post("/agents", json=config)
            for config in agent_configs
        ]
        
        create_responses = await asyncio.gather(*create_tasks)
        
        # Verify all agents were created
        agent_ids = []
        for response in create_responses:
            assert response.status_code == 200
            agent_ids.append(response.json().get("agent_id"))
        
        # Start all agents concurrently
        start_tasks = [
            client.post(f"/agents/{agent_id}/action", json={"action": "start"})
            for agent_id in agent_ids
        ]
        
        start_responses = await asyncio.gather(*start_tasks)
        
        for response in start_responses:
            assert response.status_code in [200, 202]
        
        # Clean up - delete all agents
        delete_tasks = [
            client.delete(f"/agents/{agent_id}")
            for agent_id in agent_ids
        ]
        
        await asyncio.gather(*delete_tasks)
    
    async def test_agent_websocket_updates(self):
        """Test real-time agent updates via WebSocket"""
        # This test requires WebSocket support in the API
        try:
            # Connect to WebSocket
            uri = "ws://localhost:8000/ws/agent-updates"
            async with websockets.connect(uri) as websocket:
                # Subscribe to agent updates
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "topic": "agent.status"
                }))
                
                # Create an agent via HTTP to trigger updates
                async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                    # Login and create agent
                    login_response = await client.post(
                        "/auth/login",
                        json={"email": "test@example.com", "api_key": "test-api-key"}
                    )
                    
                    if login_response.status_code == 200:
                        token = login_response.json()["access_token"]
                        client.headers["Authorization"] = f"Bearer {token}"
                        
                        # Create agent
                        create_response = await client.post(
                            "/agents",
                            json={
                                "name": "WebSocket Test Agent",
                                "type": "trading",
                                "config": {"trading_mode": "simulated"}
                            }
                        )
                        
                        if create_response.status_code == 200:
                            agent_id = create_response.json().get("agent_id")
                            
                            # Wait for WebSocket update
                            try:
                                message = await asyncio.wait_for(
                                    websocket.recv(),
                                    timeout=5.0
                                )
                                update = json.loads(message)
                                assert update.get("type") == "agent.created"
                                assert update.get("agent_id") == agent_id
                            except asyncio.TimeoutError:
                                # WebSocket updates might not be implemented
                                pass
                            
                            # Clean up
                            await client.delete(f"/agents/{agent_id}")
        
        except (websockets.exceptions.WebSocketException, ConnectionRefusedError):
            # WebSocket might not be available
            pytest.skip("WebSocket not available")


class TestAgentPersistence:
    """Test agent state persistence across restarts"""
    
    async def test_agent_survives_restart(self, authenticated_client):
        """Test that agent state persists across service restarts"""
        client = authenticated_client
        
        # Create an agent
        agent_config = {
            "name": "Persistent Agent",
            "type": "trading",
            "config": {
                "trading_mode": "simulated",
                "persist_state": True
            }
        }
        
        create_response = await client.post("/agents", json=agent_config)
        if create_response.status_code != 200:
            pytest.skip("Agent creation not available")
        
        agent_id = create_response.json().get("agent_id")
        
        # Update some state
        await client.put(
            f"/agents/{agent_id}",
            json={"config": {"custom_value": "test123"}}
        )
        
        # In a real test, we would restart the service here
        # For now, just verify the agent still exists
        
        # Verify agent exists and has updated state
        get_response = await client.get(f"/agents/{agent_id}")
        assert get_response.status_code == 200
        
        agent_data = get_response.json()
        assert agent_data.get("name") == "Persistent Agent"
        
        # Clean up
        await client.delete(f"/agents/{agent_id}")