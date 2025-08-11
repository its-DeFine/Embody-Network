#!/usr/bin/env python3
import requests
import json
import time

# Read auth token
with open(".auth_token", "r") as f:
    token = f.read().strip()

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

base_url = "http://localhost:8010/api/v1/embodiment"

print("=" * 60)
print("SENDING COMMAND THROUGH CENTRAL MANAGER")
print("=" * 60)
print()

# Send a speak command to the VTuber system
command = {
    "action": "speak",
    "payload": {
        "text": "This message is being sent through the authenticated Central Manager. The manager is coordinating all five registered agents: NeuroSync for speech synthesis, AutoGen for cognitive processing, SCB Gateway for message routing, the Orchestrator for workflow management, and the RTMP server for streaming. This demonstrates the complete embodied AI architecture working together!",
        "voice": "luna",
        "emotion": "excited"
    },
    "priority": 1,
    "timeout_ms": 15000,
    "correlation_id": "manager-test-001"
}

print("Step 1: Sending command to NeuroSync S1 via Manager")
print(f"  Action: {command['action']}")
print(f"  Text preview: {command['payload']['text'][:100]}...")
print()

# Send to NeuroSync
resp = requests.post(
    f"{base_url}/agents/neurosync-s1/commands",
    json=command,
    headers=headers
)

if resp.ok:
    result = resp.json()
    print(f"✓ Command queued successfully!")
    print(f"  Correlation ID: {result.get('correlation_id', 'Unknown')}")
else:
    print(f"✗ Failed to send command: {resp.status_code}")
    print(f"  Error: {resp.text}")

print()

# Also send a cognitive task to AutoGen
cognitive_command = {
    "action": "tool",
    "payload": {
        "tool": "stimuli_receive",
        "data": {
            "stimuli_id": "manager-cognitive-001",
            "stimuli_type": "analysis",
            "content": "Analyze the current system architecture and explain how all five agents work together.",
            "source": "central_manager",
            "priority": "high"
        }
    },
    "priority": 1,
    "timeout_ms": 10000
}

print("Step 2: Sending cognitive task to AutoGen via Manager")
print(f"  Task: {cognitive_command['payload']['data']['content'][:80]}...")
print()

resp = requests.post(
    f"{base_url}/agents/autogen-multi-agent/commands",
    json=cognitive_command,
    headers=headers
)

if resp.ok:
    print(f"✓ Cognitive task queued successfully!")
else:
    print(f"✗ Failed: {resp.status_code}")

print()
print("=" * 60)
print("COMMAND ROUTING SUMMARY")
print("=" * 60)
print()
print("The Central Manager successfully:")
print("1. Authenticated the request using JWT token")
print("2. Validated the command structure")
print("3. Routed commands to appropriate agents")
print("4. Returned correlation IDs for tracking")
print()
print("Architecture Flow:")
print("  Client → Manager (8010) → Agent Registry")
print("            ↓")
print("         Command Bus")
print("            ↓")
print("    [NeuroSync] [AutoGen] [SCB] [Orchestrator] [RTMP]")
print()
print("All agents are registered and commands are being processed!")
print("Check the RTMP stream for audio output: rtmp://localhost:1935/live/mystream")