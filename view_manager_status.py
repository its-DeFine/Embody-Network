#!/usr/bin/env python3
import requests
import json
from datetime import datetime

# Read auth token
with open(".auth_token", "r") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}"
}

print("=" * 80)
print("CENTRAL MANAGER - EMBODIED AGENT DASHBOARD")
print("=" * 80)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Get manager health
resp = requests.get("http://localhost:8010/health")
if resp.ok:
    health = resp.json()
    print(f"Manager Status: ✓ {health['status'].upper()}")
    print(f"Version: {health['version']}")
else:
    print("Manager Status: ✗ OFFLINE")
print()

# Get registered agents
print("REGISTERED AGENTS")
print("-" * 80)
resp = requests.get("http://localhost:8010/api/v1/embodiment/agents", headers=headers)

if resp.ok:
    agents = resp.json()
    print(f"Total Agents: {len(agents)}")
    print()
    
    # Group agents by type
    orchestrators = []
    cognitive = []
    avatar = []
    infrastructure = []
    
    for agent in agents:
        metadata = agent.get('metadata', {})
        agent_type = metadata.get('type', 'unknown')
        
        if agent_type == 'orchestrator':
            orchestrators.append(agent)
        elif agent_type in ['cognitive_engine', 'multi-agent']:
            cognitive.append(agent)
        elif agent_type in ['avatar_controller', 'avatar']:
            avatar.append(agent)
        else:
            infrastructure.append(agent)
    
    # Display by category
    if orchestrators:
        print("🎛️  ORCHESTRATORS")
        for agent in orchestrators:
            print(f"  ├─ {agent['name']}")
            print(f"  │  ID: {agent['agent_id']}")
            print(f"  │  Status: {agent['status']}")
            print(f"  │  Port: {agent.get('metadata', {}).get('port', 'N/A')}")
            manages = agent.get('metadata', {}).get('manages', [])
            if manages:
                print(f"  │  Manages: {', '.join(manages)}")
            print(f"  │  Endpoint: {agent['endpoint']}")
            print("  │")
    
    if cognitive:
        print("🧠 COGNITIVE AGENTS")
        for agent in cognitive:
            print(f"  ├─ {agent['name']}")
            print(f"  │  ID: {agent['agent_id']}")
            print(f"  │  Status: {agent['status']}")
            print(f"  │  Capabilities: {', '.join(agent['capabilities'][:3])}")
            teams = agent.get('metadata', {}).get('teams', [])
            if teams:
                print(f"  │  Teams: {', '.join(teams)}")
            print(f"  │  LLM: {agent.get('metadata', {}).get('llm', 'unknown')}")
            print(f"  │  Endpoint: {agent['endpoint']}")
            print("  │")
    
    if avatar:
        print("🎭 AVATAR SYSTEMS")
        for agent in avatar:
            print(f"  ├─ {agent['name']}")
            print(f"  │  ID: {agent['agent_id']}")
            print(f"  │  Status: {agent['status']}")
            print(f"  │  TTS: {agent.get('metadata', {}).get('tts_engine', 'unknown')}")
            print(f"  │  Voice: {agent.get('metadata', {}).get('voice', 'default')}")
            print(f"  │  Capabilities: {', '.join(agent['capabilities'][:3])}")
            print(f"  │  Endpoint: {agent['endpoint']}")
            print("  │")
    
    if infrastructure:
        print("🔧 INFRASTRUCTURE")
        for agent in infrastructure:
            print(f"  ├─ {agent['name']}")
            print(f"  │  ID: {agent['agent_id']}")
            print(f"  │  Status: {agent['status']}")
            print(f"  │  Type: {agent.get('metadata', {}).get('type', 'unknown')}")
            if 'rtmp_port' in agent.get('metadata', {}):
                print(f"  │  RTMP: {agent.get('metadata', {}).get('rtmp_port', 'N/A')}")
                print(f"  │  HTTP: {agent.get('metadata', {}).get('http_port', 'N/A')}")
            print(f"  │  Endpoint: {agent['endpoint']}")
            print("  │")
    
    print()
    print("SYSTEM CAPABILITIES")
    print("-" * 80)
    all_capabilities = set()
    for agent in agents:
        all_capabilities.update(agent.get('capabilities', []))
    
    caps_list = sorted(list(all_capabilities))
    for i in range(0, len(caps_list), 4):
        line_caps = caps_list[i:i+4]
        print("  " + " | ".join(f"{cap:15}" for cap in line_caps))
    
else:
    print(f"Failed to get agents: {resp.status_code}")

print()
print("COMMUNICATION PATHS")
print("-" * 80)
print("  HTTP APIs:")
print(f"    - Manager API:    http://localhost:8010/api/v1/")
print(f"    - NeuroSync:      http://localhost:5001/")
print(f"    - AutoGen:        http://localhost:8200/")
print(f"    - SCB Gateway:    http://localhost:8300/")
print(f"    - Orchestrator:   http://localhost:8082/")
print()
print("  Streaming:")
print(f"    - RTMP:          rtmp://localhost:1935/live/mystream")
print(f"    - HLS:           http://localhost:8085/hls/mystream.m3u8")
print(f"    - Monitor:       http://localhost:8085/")
print()
print("  Shared State:")
print(f"    - Redis:         redis://localhost:6379")
print()
print("=" * 80)