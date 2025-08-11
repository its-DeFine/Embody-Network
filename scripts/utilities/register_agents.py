#!/usr/bin/env python3
import requests
import json

# Read auth token
with open(".auth_token", "r") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

base_url = "http://localhost:8010/api/v1/embodiment"

# Register agents
agents = [
    {
        "agent_id": "neurosync-s1",
        "name": "NeuroSync S1 - Avatar System",
        "endpoint": "http://localhost:5001",
        "capabilities": ["speech", "tts", "avatar", "animation"],
        "metadata": {
            "type": "avatar_controller",
            "tts_engine": "kokoro",
            "voice": "af_sarah",
            "port": 5001
        }
    },
    {
        "agent_id": "autogen-multi-agent",
        "name": "AutoGen Multi-Agent System",
        "endpoint": "http://localhost:8200",
        "capabilities": ["reasoning", "planning", "multi-agent", "teams"],
        "metadata": {
            "type": "cognitive_engine",
            "teams": ["trader", "educator", "streamer"],
            "llm": "ollama",
            "port": 8200
        }
    },
    {
        "agent_id": "scb-gateway",
        "name": "SCB Gateway - Message Router",
        "endpoint": "http://localhost:8300",
        "capabilities": ["messaging", "routing", "redis", "pubsub"],
        "metadata": {
            "type": "message_broker",
            "protocol": "redis",
            "port": 8300
        }
    },
    {
        "agent_id": "vtuber-orchestrator",
        "name": "VTuber Orchestrator",
        "endpoint": "http://localhost:8082",
        "capabilities": ["orchestration", "coordination", "workflow"],
        "orchestrator_id": "vtuber-main",
        "metadata": {
            "type": "orchestrator",
            "manages": ["neurosync-s1", "autogen-multi-agent", "scb-gateway"],
            "port": 8082
        }
    },
    {
        "agent_id": "rtmp-streamer",
        "name": "NGINX RTMP Streaming Server",
        "endpoint": "rtmp://localhost:1935/live",
        "capabilities": ["streaming", "rtmp", "hls", "audio"],
        "metadata": {
            "type": "streaming_server",
            "rtmp_port": 1935,
            "http_port": 8085,
            "stream_key": "mystream"
        }
    }
]

print("Registering agents with Central Manager...")
print("=" * 50)

for agent in agents:
    print(f"\nRegistering: {agent['name']}")
    resp = requests.post(
        f"{base_url}/agents/register",
        json=agent,
        headers=headers
    )
    
    if resp.ok:
        print(f"  ✓ Registered successfully: {agent['agent_id']}")
    else:
        print(f"  ✗ Failed: {resp.status_code} - {resp.text}")

# List all registered agents
print("\n" + "=" * 50)
print("Fetching registered agents...")
resp = requests.get(f"{base_url}/agents", headers=headers)

if resp.ok:
    agents = resp.json()
    print(f"\n✓ Found {len(agents)} registered agents:")
    for agent in agents:
        print(f"  - {agent.get('name', 'Unknown')} ({agent.get('agent_id', 'Unknown')})")
        print(f"    Status: {agent.get('status', 'Unknown')}")
        print(f"    Capabilities: {', '.join(agent.get('capabilities', []))}")
else:
    print(f"✗ Failed to list agents: {resp.status_code}")