#!/usr/bin/env python3
"""
Send VTuber commands to remote orchestrators
"""
import httpx
import asyncio
import json
from datetime import datetime

async def send_vtuber_command():
    """Send commands to Frank's VTuber agents"""
    
    print("=" * 70)
    print("SENDING VTUBER COMMANDS TO FRANK'S ORCHESTRATOR")
    print("=" * 70)
    
    orchestrator_url = "http://62.34.58.208:8082"
    
    # Test commands to send
    commands = [
        {
            "name": "Health Check",
            "endpoint": "/health",
            "method": "GET",
            "data": None
        },
        {
            "name": "Get Active Agents",
            "endpoint": "/agents",
            "method": "GET",
            "data": None
        },
        {
            "name": "Send Stimulus to S1",
            "endpoint": "/api/s1/stimulus",
            "method": "POST",
            "data": {
                "content": "Hello from Central Manager! How are you doing today?",
                "character": "luna",
                "metadata": {"source": "central_manager", "test": True}
            }
        },
        {
            "name": "Send Stimulus to S2 (AutoGen)",
            "endpoint": "/api/s2/stimulus",
            "method": "POST",
            "data": {
                "content": "Can you help me understand quantum computing?",
                "metadata": {"source": "central_manager", "test": True}
            }
        },
        {
            "name": "Switch Character",
            "endpoint": "/api/character/switch",
            "method": "POST",
            "data": {
                "character": "sophia",
                "visual_identity": "educator"
            }
        },
        {
            "name": "Get Current Character",
            "endpoint": "/api/character/current",
            "method": "GET",
            "data": None
        }
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for cmd in commands:
            print(f"\n📡 {cmd['name']}:")
            print(f"   Endpoint: {cmd['endpoint']}")
            
            try:
                url = f"{orchestrator_url}{cmd['endpoint']}"
                
                if cmd['method'] == "GET":
                    response = await client.get(url)
                else:
                    response = await client.post(
                        url,
                        json=cmd['data'],
                        headers={"Content-Type": "application/json"}
                    )
                
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"   ✅ Response: {json.dumps(data, indent=2)[:200]}")
                    except:
                        print(f"   ✅ Response: {response.text[:200]}")
                elif response.status_code == 404:
                    print(f"   ⚠️  Endpoint not found")
                else:
                    print(f"   ❌ Error: {response.text[:200]}")
                    
            except httpx.TimeoutException:
                print(f"   ❌ Timeout")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:100]}")
    
    print("\n" + "=" * 70)
    print("DIRECT ORCHESTRATOR API TEST")
    print("=" * 70)
    
    # Try the orchestrator's routing endpoint
    routing_test = {
        "action": "route",
        "content": "Hello, can you hear me?",
        "target": "s1",
        "metadata": {"test": True}
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            print(f"\n📡 Testing Orchestrator Routing:")
            response = await client.post(
                f"{orchestrator_url}/route",
                json=routing_test
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ Routing works!")
                print(f"   Response: {response.json()}")
            else:
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"   Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(send_vtuber_command())