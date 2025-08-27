#!/usr/bin/env python3
"""
Send VTuber commands to remote orchestrators using proper format
"""
import httpx
import asyncio
import json
import uuid
from datetime import datetime

async def send_vtuber_commands():
    """Send properly formatted commands to Frank's VTuber agents"""
    
    print("=" * 70)
    print("SENDING VTUBER COMMANDS TO FRANK'S REMOTE AGENTS")
    print("=" * 70)
    
    orchestrator_url = "http://62.34.58.208:8082"
    
    # Test stimuli to send
    stimuli = [
        {
            "name": "Greeting to S1",
            "request": {
                "stimulus_id": str(uuid.uuid4()),
                "text": "Hello from the Central Manager! How are you doing today? Can you tell me about yourself?",
                "context": {
                    "source": "central_manager",
                    "target_system": "s1",
                    "character": "luna"
                },
                "priority": "normal"
            }
        },
        {
            "name": "Question to S2 (AutoGen)",
            "request": {
                "stimulus_id": str(uuid.uuid4()),
                "text": "Can you explain quantum entanglement in simple terms?",
                "context": {
                    "source": "central_manager",
                    "target_system": "s2",
                    "require_analysis": True
                },
                "priority": "normal"
            }
        },
        {
            "name": "Creative Request",
            "request": {
                "stimulus_id": str(uuid.uuid4()),
                "text": "Write a haiku about artificial intelligence and virtual reality",
                "context": {
                    "source": "central_manager",
                    "creative": True
                },
                "priority": "low"
            }
        },
        {
            "name": "High Priority Alert",
            "request": {
                "stimulus_id": str(uuid.uuid4()),
                "text": "System check: Please confirm all agents are operational",
                "context": {
                    "source": "central_manager",
                    "system_check": True
                },
                "priority": "high"
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First check health
        print("\n📡 Health Check:")
        try:
            response = await client.get(f"{orchestrator_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ Orchestrator is healthy")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Check API registry
        print("\n📡 Available APIs:")
        try:
            response = await client.get(f"{orchestrator_url}/api/registry")
            if response.status_code == 200:
                apis = response.json()
                for system, endpoints in apis.items():
                    print(f"   - {system}: {endpoints.get('base_url', 'N/A')}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Send stimuli through routing
        print("\n" + "=" * 70)
        print("ROUTING STIMULI TO AGENTS")
        print("=" * 70)
        
        for stimulus_info in stimuli:
            print(f"\n📨 {stimulus_info['name']}:")
            print(f"   Stimulus ID: {stimulus_info['request']['stimulus_id']}")
            print(f"   Text: {stimulus_info['request']['text'][:60]}...")
            print(f"   Priority: {stimulus_info['request']['priority']}")
            
            try:
                # Use the combined process endpoint that routes and executes
                response = await client.post(
                    f"{orchestrator_url}/process",
                    json=stimulus_info['request'],
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ SUCCESS! Processed by: {result.get('system', 'unknown')}")
                    print(f"   Execution time: {result.get('execution_time_ms', 'N/A')}ms")
                    
                    # Show the response from the agent
                    if 'response' in result:
                        print(f"   Agent Response: {json.dumps(result.get('response'), indent=6)[:400]}")
                    elif 'result' in result:
                        print(f"   Result: {json.dumps(result.get('result'), indent=6)[:400]}")
                    else:
                        print(f"   Full Response: {json.dumps(result, indent=6)[:400]}")
                        
                else:
                    print(f"   ❌ Processing failed: {response.status_code}")
                    print(f"   Error: {response.text[:200]}")
                    
            except httpx.TimeoutException:
                print(f"   ❌ Timeout (30s) - Agent might be processing")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:200]}")
            
            # Small delay between requests
            await asyncio.sleep(2)
    
    print("\n" + "=" * 70)
    print("COMMAND TEST COMPLETE")
    print("=" * 70)
    print("\nFrank's VTuber agents should have received and processed the stimuli.")
    print("Check Frank's logs for agent responses!")

if __name__ == "__main__":
    asyncio.run(send_vtuber_commands())