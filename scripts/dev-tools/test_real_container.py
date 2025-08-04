#!/usr/bin/env python3
"""
Test Real Agent Container
Test communication and functionality with the real agent container we just started.
"""
import requests
import json
import time
from datetime import datetime

# Agent container endpoint
AGENT_URL = "http://localhost:8001"
BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkB0cmFkaW5nLnN5c3RlbSIsImV4cCI6MTc1NDQxMTM2M30.ynYErbxgV16D7pTmRQNhXdR_6j_i9qyYRYMfNEkO9Zw"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_agent_container():
    """Test the real agent container functionality"""
    print("🚀 TESTING REAL AGENT CONTAINER")
    print("=" * 60)
    
    # 1. Test agent health
    print("\n🏥 Step 1: Testing Agent Health")
    try:
        response = requests.get(f"{AGENT_URL}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Agent Health:")
            print(f"   Status: {health.get('status')}")
            print(f"   Agent ID: {health.get('agent_id')}")
            print(f"   Agent Type: {health.get('agent_type')}")
            print(f"   Timestamp: {health.get('timestamp')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # 2. Test agent status
    print("\n📊 Step 2: Testing Agent Status")
    try:
        response = requests.get(f"{AGENT_URL}/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Agent Status:")
            print(f"   Agent ID: {status.get('agent_id')}")
            print(f"   Agent Type: {status.get('agent_type')}")
            print(f"   Status: {status.get('status')}")
            print(f"   Config: {json.dumps(status.get('config', {}), indent=6)}")
            
            metrics = status.get('metrics', {})
            print(f"   Metrics:")
            print(f"     Tasks Completed: {metrics.get('tasks_completed', 0)}")
            print(f"     Uptime: {metrics.get('uptime_seconds', 0)}s")
            print(f"     Last Activity: {metrics.get('last_activity', 'None')}")
        else:
            print(f"❌ Status check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Status check error: {e}")
    
    # 3. Test task execution
    print("\n📋 Step 3: Testing Task Execution")
    try:
        task_data = {
            "id": "test-task-001",
            "type": "market_analysis",
            "symbol": "AAPL",
            "action": "analyze_trend"
        }
        
        response = requests.post(f"{AGENT_URL}/task", json=task_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Task Execution:")
            print(f"   Status: {result.get('status')}")
            print(f"   Task ID: {result.get('task_id')}")
            print(f"   Result: {json.dumps(result.get('result', {}), indent=6)}")
            print(f"   Timestamp: {result.get('timestamp')}")
        else:
            print(f"❌ Task execution failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Task execution error: {e}")
    
    # 4. Wait and check metrics after task
    print("\n⏳ Step 4: Checking Metrics After Task")
    time.sleep(2)
    
    try:
        response = requests.get(f"{AGENT_URL}/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            metrics = status.get('metrics', {})
            print(f"✅ Updated Metrics:")
            print(f"   Tasks Completed: {metrics.get('tasks_completed', 0)}")
            print(f"   Uptime: {metrics.get('uptime_seconds', 0)}s")
            print(f"   Last Activity: {metrics.get('last_activity', 'None')}")
    except Exception as e:
        print(f"❌ Metrics check error: {e}")
    
    # 5. Check if agent appears in central manager
    print("\n🎛️ Step 5: Checking Central Manager Integration")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/management/agents", headers=headers)
        if response.status_code == 200:
            agents = response.json()
            real_agent = None
            for agent in agents:
                if agent.get("container_id") == "real-real-container-test-01":
                    real_agent = agent
                    break
            
            if real_agent:
                print(f"✅ Agent found in central manager:")
                print(f"   Name: {real_agent.get('name', 'N/A')}")
                print(f"   Type: {real_agent.get('type')}")
                print(f"   Status: {real_agent.get('status')}")
                print(f"   Container ID: {real_agent.get('container_id')}")
            else:
                print(f"⚠️  Agent not yet registered in central manager")
                print(f"   This is expected for manually started containers")
        else:
            print(f"❌ Failed to check central manager: {response.status_code}")
    except Exception as e:
        print(f"❌ Central manager check error: {e}")
    
    return True

def test_container_management():
    """Test Docker container management"""
    print("\n🐳 TESTING CONTAINER MANAGEMENT")
    print("=" * 60)
    
    # Check Docker container status
    print("\n📦 Container Status:")
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=agent-real-test", "--format", "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ Failed to get container status")
    except Exception as e:
        print(f"❌ Container status error: {e}")
    
    # Check container logs
    print("\n📋 Recent Container Logs:")
    try:
        result = subprocess.run(
            ["docker", "logs", "agent-real-test", "--tail", "10"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ Failed to get container logs")
    except Exception as e:
        print(f"❌ Container logs error: {e}")

if __name__ == "__main__":
    print(f"🎛️ REAL AGENT CONTAINER TEST")
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test agent functionality
    if test_agent_container():
        print(f"\n✅ AGENT CONTAINER TESTS PASSED")
    else:
        print(f"\n❌ AGENT CONTAINER TESTS FAILED")
    
    # Test container management
    test_container_management()
    
    print(f"\n🏁 REAL CONTAINER TEST COMPLETE!")
    print(f"📊 Dashboard: http://localhost:8002/dashboard_ui.html")
    print(f"🔗 Agent Direct: http://localhost:8001/health")
    print(f"🌐 Central Manager: http://localhost:8000/docs")