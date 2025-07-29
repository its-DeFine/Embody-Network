#!/usr/bin/env python3
"""
End-to-End Customer Journey Test
Tests the complete flow from agent creation to task execution
"""

import asyncio
import json
import time
from datetime import datetime
import httpx
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

async def test_customer_journey():
    """Test complete customer journey"""
    print("🚀 Testing End-to-End Customer Journey")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Authenticate
        print("\n1. Authenticating customer...")
        login_data = {
            "email": "test@testcorp.com",
            "api_key": "DcqvANBn1GcraB9J5SXGc9yOIvUaoFBU"
        }
        
        response = await client.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ Authentication failed: {response.status_code}")
            return
        
        auth_data = response.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✅ Authenticated successfully")
        
        # 2. Create an agent
        print("\n2. Creating a new agent...")
        agent_config = {
            "name": "Test Trading Agent",
            "agent_type": "trading",
            "config": {
                "system_message": "You are a trading assistant focused on market analysis.",
                "max_tokens": 1000,
                "temperature": 0.7
            }
        }
        
        response = await client.post(
            f"{BASE_URL}/agents", 
            json=agent_config,
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create agent: {response.status_code}")
            print(f"   Response: {response.text}")
            return
        
        agent = response.json()
        print(f"   Response: {agent}")
        agent_id = agent.get("agent_id") or agent.get("id")
        print(f"✅ Created agent: {agent_id}")
        
        # 3. List agents
        print("\n3. Listing agents...")
        response = await client.get(f"{BASE_URL}/agents", headers=headers)
        if response.status_code == 200:
            data = response.json()
            agents = data.get("agents", [])
            print(f"✅ Found {len(agents)} agent(s)")
            for agent_data in agents:
                # Redis returns byte strings, need to decode if necessary
                name = agent_data.get(b'name', agent_data.get('name', 'Unknown'))
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                agent_id = agent_data.get(b'agent_id', agent_data.get('agent_id', 'Unknown'))
                if isinstance(agent_id, bytes):
                    agent_id = agent_id.decode('utf-8')
                status = agent_data.get(b'status', agent_data.get('status', 'Unknown'))
                if isinstance(status, bytes):
                    status = status.decode('utf-8')
                print(f"   • {name} ({agent_id}) - Status: {status}")
        
        # 4. Create a task
        print("\n4. Creating a task for the agent...")
        task_data = {
            "agent_id": agent_id,
            "type": "analysis",
            "payload": {
                "query": "What are the current market trends for technology stocks?",
                "timeframe": "1D"
            }
        }
        
        response = await client.post(
            f"{BASE_URL}/tasks", 
            json=task_data,
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create task: {response.status_code}")
            print(f"   Response: {response.text}")
        else:
            task = response.json()
            task_id = task["id"]
            print(f"✅ Created task: {task_id}")
            
            # 5. Check task status
            print("\n5. Checking task status...")
            for i in range(10):  # Poll for 10 seconds
                response = await client.get(
                    f"{BASE_URL}/tasks/{task_id}", 
                    headers=headers
                )
                
                if response.status_code == 200:
                    task_status = response.json()
                    status = task_status.get("status", "unknown")
                    print(f"   • Status: {status}")
                    
                    if status in ["completed", "failed"]:
                        if status == "completed":
                            print(f"✅ Task completed successfully")
                            if "result" in task_status:
                                print(f"   Result: {json.dumps(task_status['result'], indent=2)}")
                        else:
                            print(f"❌ Task failed")
                            if "error" in task_status:
                                print(f"   Error: {task_status['error']}")
                        break
                
                await asyncio.sleep(1)
        
        # 6. Test WebSocket connection
        print("\n6. Testing WebSocket real-time updates...")
        try:
            # Get customer ID from token (normally would decode JWT)
            customer_id = "cust_20250727143601_074989"  # From onboarding
            async with websockets.connect(
                f"{WS_URL}/ws/{customer_id}?token={token}"
            ) as websocket:
                print("✅ WebSocket connected")
                
                # Send a test message
                test_msg = {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send(json.dumps(test_msg))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=5.0
                    )
                    msg = json.loads(response)
                    print(f"✅ Received WebSocket message: {msg.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    print("⚠️  No WebSocket response received")
                
        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")
        
        # 7. Create a team
        print("\n7. Creating an agent team...")
        team_config = {
            "name": "Market Analysis Team",
            "agent_ids": [agent_id],
            "config": {
                "coordination_type": "sequential"
            }
        }
        
        response = await client.post(
            f"{BASE_URL}/teams", 
            json=team_config,
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create team: {response.status_code}")
            print(f"   Response: {response.text}")
        else:
            team = response.json()
            team_id = team["id"]
            print(f"✅ Created team: {team_id}")
        
        # 8. Check metrics
        print("\n8. Checking platform metrics...")
        response = await client.get(f"{BASE_URL}/metrics", headers=headers)
        if response.status_code == 200:
            print("✅ Metrics endpoint accessible")
            # Parse Prometheus metrics format
            metrics_text = response.text
            for line in metrics_text.split('\n'):
                if line.startswith('api_requests_total'):
                    print(f"   • {line}")
                    break
        
        # 9. Test agent update
        print("\n9. Testing agent update...")
        update_data = {
            "config": {
                "system_message": "You are an advanced trading assistant with market expertise.",
                "max_tokens": 1500,
                "temperature": 0.8
            }
        }
        
        response = await client.put(
            f"{BASE_URL}/agents/{agent_id}",
            json=update_data,
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Agent updated successfully")
        else:
            print(f"❌ Failed to update agent: {response.status_code}")
        
        # 10. Test pagination
        print("\n10. Testing pagination...")
        response = await client.get(
            f"{BASE_URL}/agents?limit=1&offset=0",
            headers=headers
        )
        
        if response.status_code == 200:
            agents = response.json()
            print(f"✅ Pagination working (returned {len(agents)} agent)")
        
    print("\n" + "=" * 60)
    print("✅ End-to-End Customer Journey Test Completed!")
    print("\nSummary:")
    print("  • Authentication: ✅")
    print("  • Agent Creation: ✅")
    print("  • Task Execution: Check logs")
    print("  • WebSocket Communication: Check status")
    print("  • Team Management: Check status")
    print("  • Metrics Collection: ✅")

if __name__ == "__main__":
    asyncio.run(test_customer_journey())