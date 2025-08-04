#!/usr/bin/env python3
"""
Container Dashboard - Real Container Visibility
Get detailed information about agent containers, architecture, and deployment status.
"""
import requests
import docker
import json
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
        else:
            response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def get_docker_containers():
    """Get actual Docker container information"""
    try:
        client = docker.from_env()
        containers = []
        for container in client.containers.list(all=True):
            containers.append({
                "id": container.id[:12],
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": container.status,
                "ports": container.ports,
                "labels": container.labels,
                "created": container.attrs["Created"],
                "network_mode": container.attrs["HostConfig"]["NetworkMode"]
            })
        return containers
    except Exception as e:
        return {"error": str(e)}

def analyze_architecture():
    """Analyze the current container architecture"""
    print("🏗️ CONTAINER ARCHITECTURE ANALYSIS")
    print("="*60)
    
    # 1. Get logical agents from API
    print("\n📊 LOGICAL AGENTS (via API):")
    agents = make_request("GET", "/api/v1/management/agents")
    if isinstance(agents, list):
        for agent in agents:
            container_id = agent.get("container_id", "None")
            status = agent["status"]
            print(f"   🤖 {agent['name']}")
            print(f"      Type: {agent['type']}")
            print(f"      Status: {status}")
            print(f"      Container ID: {container_id}")
            print(f"      Architecture: {'Simulated' if 'simulated' in container_id else 'Real Container'}")
            print()
    
    # 2. Get actual Docker containers
    print("🐳 PHYSICAL CONTAINERS (via Docker):")
    containers = get_docker_containers()
    if isinstance(containers, list):
        for container in containers:
            print(f"   📦 {container['name']}")
            print(f"      Image: {container['image']}")
            print(f"      Status: {container['status']}")
            print(f"      ID: {container['id']}")
            if container['ports']:
                print(f"      Ports: {container['ports']}")
            print()
    
    # 3. Architecture Analysis
    print("🔍 ARCHITECTURE FINDINGS:")
    
    agent_containers = [c for c in containers if 'agent' in c['name'].lower()]
    system_containers = [c for c in containers if c['name'] in ['operation-app-1', 'operation-redis-1', 'operation-ollama-1']]
    
    print(f"   📈 System Containers: {len(system_containers)}")
    print(f"   🤖 Agent Containers: {len(agent_containers)}")
    print(f"   🎯 Logical Agents: {len(agents) if isinstance(agents, list) else 0}")
    
    print(f"\n🏛️ DEPLOYMENT MODEL:")
    if len(agent_containers) == 0 and len(agents) > 0:
        print("   📍 MONOLITHIC: All agents run within main container")
        print("   📦 Main container: operation-app-1")
        print("   🎭 Agent isolation: Logical (not physical containers)")
    else:
        print("   📍 MICROSERVICES: Each agent in separate container")
        print("   🔄 Container orchestration: Active")
    
    # 4. Ollama Integration
    print(f"\n🧠 OLLAMA INTEGRATION:")
    ollama_models = make_request("GET", "/api/v1/ollama/models")
    ollama_container = next((c for c in containers if 'ollama' in c['name']), None)
    
    if ollama_container:
        print(f"   📦 Container: {ollama_container['name']} ({ollama_container['status']})")
        print(f"   🚀 Image: {ollama_container['image']}")
        print(f"   🌐 Ports: {ollama_container.get('ports', {})}")
    
    if isinstance(ollama_models, dict):
        model_count = ollama_models.get('count', 0)
        print(f"   🤖 Available Models: {model_count}")
        if model_count == 0:
            recommended = ollama_models.get('recommended', [])
            print(f"   💡 Recommended: {', '.join(recommended[:3])}...")
    
    # 5. Resource Sharing Analysis
    print(f"\n⚖️ RESOURCE SHARING:")
    if len(agent_containers) == 0:
        print("   🎯 CPU/Memory: Shared across all agents in main container")
        print("   🧠 Ollama Models: Shared service for all agents")
        print("   📊 Redis: Shared state storage")
        print("   ⚡ Benefits: Lower overhead, faster inter-agent communication")
        print("   ⚠️ Considerations: Less isolation, shared resource contention")
    
    return {
        "logical_agents": len(agents) if isinstance(agents, list) else 0,
        "physical_containers": len(containers) if isinstance(containers, list) else 0,
        "agent_containers": len(agent_containers),
        "system_containers": len(system_containers),
        "deployment_model": "monolithic" if len(agent_containers) == 0 else "microservices",
        "ollama_available": ollama_container is not None,
        "ollama_models": ollama_models.get('count', 0) if isinstance(ollama_models, dict) else 0
    }

def create_dashboard_data():
    """Create dashboard data structure"""
    analysis = analyze_architecture()
    
    # Get detailed agent data
    agents = make_request("GET", "/api/v1/management/agents")
    containers = get_docker_containers()
    
    dashboard = {
        "timestamp": datetime.now().isoformat(),
        "architecture": {
            "deployment_model": analysis["deployment_model"],
            "total_containers": analysis["physical_containers"],
            "agent_containers": analysis["agent_containers"],
            "system_containers": analysis["system_containers"]
        },
        "agents": {
            "total": analysis["logical_agents"],
            "running": len([a for a in agents if a.get("status") == "running"]) if isinstance(agents, list) else 0,
            "created": len([a for a in agents if a.get("status") == "created"]) if isinstance(agents, list) else 0,
            "details": agents if isinstance(agents, list) else []
        },
        "containers": {
            "total": len(containers) if isinstance(containers, list) else 0,
            "running": len([c for c in containers if c.get("status") == "running"]) if isinstance(containers, list) else 0,
            "details": containers if isinstance(containers, list) else []
        },
        "services": {
            "ollama": {
                "available": analysis["ollama_available"],
                "models": analysis["ollama_models"]
            },
            "redis": "running" in [c.get("status") for c in containers if "redis" in c.get("name", "")] if isinstance(containers, list) else False,
            "main_app": "running" in [c.get("status") for c in containers if "app" in c.get("name", "")] if isinstance(containers, list) else False
        }
    }
    
    return dashboard

if __name__ == "__main__":
    print("🎛️ CONTAINER DASHBOARD")
    print(f"⏰ Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run analysis
    analysis_results = analyze_architecture()
    
    # Create dashboard
    dashboard = create_dashboard_data()
    
    print(f"\n📊 DASHBOARD SUMMARY:")
    print(f"   🏗️ Architecture: {dashboard['architecture']['deployment_model'].upper()}")
    print(f"   🤖 Agents: {dashboard['agents']['total']} ({dashboard['agents']['running']} running)")
    print(f"   📦 Containers: {dashboard['containers']['total']} ({dashboard['containers']['running']} running)")
    print(f"   🧠 Ollama: {'Available' if dashboard['services']['ollama']['available'] else 'Not Available'}")
    
    # Save dashboard data
    with open('dashboard_data.json', 'w') as f:
        json.dump(dashboard, f, indent=2)
    
    print(f"\n💾 Dashboard data saved to: dashboard_data.json")
    print(f"🌐 API Documentation: {BASE_URL}/docs")