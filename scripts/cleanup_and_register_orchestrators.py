#!/usr/bin/env python3
"""
Clean up test orchestrators and register only real ones
"""

import requests
import json
import sys
import time

def cleanup_and_register():
    """Remove test entries and register real orchestrators"""
    
    # First authenticate
    auth_resp = requests.post(
        "http://localhost:8010/api/v1/auth/login",
        json={"email": "admin@system.com", "password": "LivepeerManager2025!Secure"}
    )
    
    if auth_resp.status_code != 200:
        print(f"Authentication failed: {auth_resp.status_code}")
        return False
        
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current orchestrators
    resp = requests.get(
        "http://localhost:8010/api/v1/livepeer/orchestrators",
        headers=headers
    )
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Current orchestrators: {data['total']}")
        
        # Remove ALL existing orchestrators to start fresh
        for orch in data['orchestrators']:
            orch_id = orch['orchestrator_id']
            # Use the internal API to remove from Redis
            try:
                # Try different approaches to remove
                
                # First try the disconnect endpoint
                disconnect_resp = requests.post(
                    f"http://localhost:8010/api/v1/livepeer/orchestrators/{orch_id}/disconnect",
                    headers=headers
                )
                
                if disconnect_resp.status_code in [200, 204]:
                    print(f"Disconnected orchestrator: {orch_id}")
                
                # Try to delete from Redis directly via the manager
                delete_data = {
                    "action": "remove",
                    "orchestrator_id": orch_id
                }
                
                # Call internal cleanup
                cleanup_resp = requests.post(
                    "http://localhost:8010/api/v1/livepeer/orchestrators/cleanup",
                    json=delete_data,
                    headers=headers
                )
                
                if cleanup_resp.status_code in [200, 204]:
                    print(f"Cleaned up orchestrator: {orch_id}")
                
            except Exception as e:
                print(f"Error removing {orch_id}: {e}")
    
    print("\nWaiting for cleanup to propagate...")
    time.sleep(2)
    
    # Now register the real Livepeer orchestrator
    print("\nRegistering real Livepeer orchestrator...")
    
    orchestrator_data = {
        "orchestrator_id": "livepeer-orchestrator-9995",
        "endpoint": "https://livepeer-orchestrator:9995",
        "capabilities": ["agent-net", "byoc", "transcoding"],
        "region": "docker",
        "status": "active",
        "metadata": {
            "type": "livepeer-orchestrator",
            "container": "livepeer-orchestrator",
            "network": "central-network"
        }
    }
    
    resp = requests.post(
        "http://localhost:8010/api/v1/livepeer/orchestrators/register",
        json=orchestrator_data,
        headers=headers
    )
    
    if resp.status_code == 200:
        print(f"✓ Registered: {orchestrator_data['orchestrator_id']}")
    else:
        print(f"✗ Failed to register: {resp.status_code}")
        print(resp.text)
    
    # Also register the worker as a separate entity
    worker_data = {
        "orchestrator_id": "livepeer-worker-9876",
        "endpoint": "http://livepeer-worker:9876",
        "capabilities": ["agent-net", "service-monitoring"],
        "region": "docker",
        "status": "active",
        "metadata": {
            "type": "byoc-worker",
            "container": "livepeer-worker",
            "network": "vtuber_network"
        }
    }
    
    resp = requests.post(
        "http://localhost:8010/api/v1/livepeer/orchestrators/register",
        json=worker_data,
        headers=headers
    )
    
    if resp.status_code == 200:
        print(f"✓ Registered: {worker_data['orchestrator_id']}")
    else:
        print(f"✗ Failed to register worker: {resp.status_code}")
    
    # List final orchestrators
    print("\n" + "=" * 60)
    print("Final Registered Orchestrators:")
    print("-" * 60)
    
    resp = requests.get(
        "http://localhost:8010/api/v1/livepeer/orchestrators",
        headers=headers
    )
    
    if resp.status_code == 200:
        data = resp.json()
        for orch in data['orchestrators']:
            print(f"• {orch['orchestrator_id']}")
            print(f"  Endpoint: {orch['endpoint']}")
            print(f"  Type: {orch.get('metadata', {}).get('type', 'unknown')}")
            print(f"  Container: {orch.get('metadata', {}).get('container', 'unknown')}")
            print()
        
        print(f"Total: {data['total']} orchestrators registered")
    
    return True

if __name__ == "__main__":
    print("Cleaning up and registering real orchestrators")
    print("=" * 60)
    
    if cleanup_and_register():
        print("\n✓ Setup complete!")
    else:
        print("\n✗ Setup failed!")
        sys.exit(1)