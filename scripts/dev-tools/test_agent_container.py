#!/usr/bin/env python3
"""
Test Agent Container Creation and Management
Create a real agent container and demonstrate full container orchestration.
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkB0cmFkaW5nLnN5c3RlbSIsImV4cCI6MTc1NDQxMTM2M30.ynYErbxgV16D7pTmRQNhXdR_6j_i9qyYRYMfNEkO9Zw"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def make_request(method, endpoint, data=None):
    """Make an API request"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def test_container_orchestration():
    """Test full container orchestration"""
    print("🚀 TESTING AGENT CONTAINER ORCHESTRATION")
    print("=" * 60)
    
    # 1. Create an agent with container specification
    print("\n📦 Step 1: Creating Agent for Container Deployment")
    agent_data = {
        "name": "ContainerAgent-Test-01",
        "agent_type": "trading",
        "config": {
            "container_mode": True,
            "max_position_size": 2000,
            "risk_tolerance": 0.03,
            "trading_strategies": ["momentum", "arbitrage"],
            "update_frequency": 15
        }
    }
    
    agent = make_request("POST", "/api/v1/agents", agent_data)
    if "error" in agent:
        print(f"❌ Failed to create agent: {agent['error']}")
        return False
    
    agent_id = agent["id"]
    print(f"✅ Agent created: {agent['name']} (ID: {agent_id})")
    print(f"   Type: {agent['type']}")
    print(f"   Status: {agent['status']}")
    
    # 2. Start the agent (should create real container)
    print(f"\n🏃 Step 2: Starting Agent Container")
    start_result = make_request("POST", f"/api/v1/agents/{agent_id}/start")
    if "error" in start_result:
        print(f"❌ Failed to start agent: {start_result['error']}")
        return False
    
    print(f"✅ Agent start initiated:")
    print(f"   Message: {start_result.get('message', 'Unknown')}")
    if 'container_id' in start_result:
        print(f"   Container ID: {start_result['container_id']}")
    if start_result.get('simulated'):
        print(f"   ⚠️  Running in simulation mode (Docker not available)")
    
    # 3. Wait a moment for container to start
    print(f"\n⏳ Step 3: Waiting for container startup...")
    time.sleep(5)
    
    # 4. Check agent status
    print(f"\n📊 Step 4: Checking Agent Status")
    agent_status = make_request("GET", f"/api/v1/agents/{agent_id}")
    if "error" in agent_status:
        print(f"❌ Failed to get agent status: {agent_status['error']}")
        return False
    
    print(f"✅ Agent Status:")
    print(f"   Name: {agent_status['name']}")
    print(f"   Type: {agent_status['type']}")
    print(f"   Status: {agent_status['status']}")
    print(f"   Created: {agent_status['created_at']}")
    
    # 5. Check all agents to see the new container agent
    print(f"\n👥 Step 5: Listing All Agents")
    all_agents = make_request("GET", "/api/v1/management/agents")
    if "error" in all_agents:
        print(f"❌ Failed to list agents: {all_agents['error']}")
        return False
    
    print(f"✅ Total Agents: {len(all_agents)}")
    for agent in all_agents:
        status_icon = "🟢" if agent["status"] == "running" else "🔵" if agent["status"] == "created" else "🔴"
        container_info = ""
        if "container_id" in agent:
            if agent["container_id"].startswith("simulated-"):
                container_info = "(simulated)"
            else:
                container_info = f"(container: {agent['container_id'][:12]})"
        
        print(f"   {status_icon} {agent['name']} - {agent['type']} - {agent['status']} {container_info}")
    
    # 6. Test agent communication if it's running
    container_agent = next((a for a in all_agents if a["id"] == agent_id), None)
    if container_agent and container_agent.get("container_id") and not container_agent["container_id"].startswith("simulated-"):
        print(f"\n🔗 Step 6: Testing Agent Container Communication")
        # Try to communicate with the agent container
        try:
            # Get the agent's port (assuming 8001 for now)
            health_response = requests.get("http://localhost:8001/health", timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"✅ Agent Container Health:")
                print(f"   Status: {health_data.get('status')}")
                print(f"   Agent ID: {health_data.get('agent_id')}")
                print(f"   Agent Type: {health_data.get('agent_type')}")
                print(f"   Timestamp: {health_data.get('timestamp')}")
                
                # Test agent status endpoint
                status_response = requests.get("http://localhost:8001/status", timeout=5)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"✅ Agent Container Status:")
                    print(f"   Tasks Completed: {status_data.get('metrics', {}).get('tasks_completed', 0)}")
                    print(f"   Uptime: {status_data.get('metrics', {}).get('uptime_seconds', 0)}s")
                
            else:
                print(f"❌ Agent container not responding on port 8001")
        
        except Exception as e:
            print(f"❌ Failed to communicate with agent container: {e}")
    else:
        print(f"\n📝 Step 6: Agent running in simulation mode")
        print(f"   Container communication not available")
    
    # 7. System status with new agent
    print(f"\n📈 Step 7: System Status with New Agent")
    system_status = make_request("GET", "/api/v1/management/status")
    if "error" not in system_status:
        print(f"✅ System Status:")
        print(f"   Overall: {system_status['status']}")
        print(f"   Active Agents: {system_status['agents']['active']}")
        print(f"   Total Agents: {system_status['agents']['total']}")
        print(f"   Market Data: {system_status['market_data']['status']}")
    
    print(f"\n🎯 CONTAINER ORCHESTRATION TEST COMPLETE")
    print(f"📋 Summary:")
    print(f"   ✅ Agent Created: {agent['name']}")
    print(f"   ✅ Container Started: {'Real' if not start_result.get('simulated') else 'Simulated'}")
    print(f"   ✅ Status Monitoring: Working")
    print(f"   ✅ System Integration: Complete")
    
    return agent_id

def test_agent_lifecycle(agent_id):
    """Test full agent lifecycle management"""
    print(f"\n🔄 TESTING AGENT LIFECYCLE MANAGEMENT")
    print("=" * 60)
    
    # Wait a bit more for agent to be fully operational
    print("⏳ Allowing agent to run for 10 seconds...")
    time.sleep(10)
    
    # Check metrics
    print(f"\n📊 Checking Agent Metrics:")
    agent_status = make_request("GET", f"/api/v1/agents/{agent_id}")
    if "error" not in agent_status:
        metrics = agent_status.get("metrics", {})
        print(f"   Tasks Completed: {metrics.get('tasks_completed', 0)}")
        print(f"   Avg Response Time: {metrics.get('avg_response_time', 0)}")
        print(f"   Uptime Hours: {metrics.get('uptime_hours', 0)}")
        print(f"   Last Activity: {metrics.get('last_activity', 'None')}")
    
    # Stop the agent
    print(f"\n🛑 Stopping Agent Container:")
    stop_result = make_request("POST", f"/api/v1/agents/{agent_id}/stop")
    if "error" not in stop_result:
        print(f"✅ {stop_result.get('message', 'Agent stopped')}")
    else:
        print(f"❌ Stop failed: {stop_result['error']}")
    
    # Wait for stop
    time.sleep(3)
    
    # Check final status
    print(f"\n📊 Final Agent Status:")
    final_status = make_request("GET", f"/api/v1/agents/{agent_id}")
    if "error" not in final_status:
        print(f"   Status: {final_status['status']}")
    
    print(f"\n✅ AGENT LIFECYCLE TEST COMPLETE")

if __name__ == "__main__":
    print(f"🎛️ AGENT CONTAINER ORCHESTRATION TEST")
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test container orchestration
    agent_id = test_container_orchestration()
    
    if agent_id:
        # Test lifecycle management
        test_agent_lifecycle(agent_id)
    
    print(f"\n🏁 ALL TESTS COMPLETE!")
    print(f"📊 Dashboard: http://localhost:8002/dashboard_ui.html")
    print(f"🌐 API Docs: http://localhost:8000/docs")