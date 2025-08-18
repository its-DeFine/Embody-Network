#!/usr/bin/env python3
"""
Register the actual Livepeer orchestrator with the central manager
"""

import requests
import json
import sys

def register_livepeer_orchestrator():
    """Register the real Livepeer orchestrator"""
    
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
    
    # Register the actual Livepeer orchestrator
    orchestrator_data = {
        "orchestrator_id": "livepeer-orchestrator-main",
        "endpoint": "https://livepeer-orchestrator:9995",  # Actual orchestrator RPC endpoint
        "capabilities": ["agent-net", "byoc", "transcoding"],
        "region": "local",
        "status": "active"
    }
    
    # First, try to remove test orchestrators
    for test_id in ["autonomy-orchestrator-001", "test-orch-001"]:
        try:
            resp = requests.delete(
                f"http://localhost:8010/api/v1/livepeer/orchestrators/{test_id}",
                headers=headers
            )
            if resp.status_code in [200, 204]:
                print(f"Removed test orchestrator: {test_id}")
            else:
                print(f"Could not remove {test_id}: {resp.status_code}")
        except Exception as e:
            print(f"Error removing {test_id}: {e}")
    
    # Now register the real orchestrator
    resp = requests.post(
        "http://localhost:8010/api/v1/livepeer/orchestrators/register",
        json=orchestrator_data,
        headers=headers
    )
    
    if resp.status_code == 200:
        print(f"Successfully registered Livepeer orchestrator: livepeer-orchestrator-main")
        print(f"Endpoint: {orchestrator_data['endpoint']}")
        print(f"Capabilities: {orchestrator_data['capabilities']}")
        return True
    else:
        print(f"Registration failed: {resp.status_code}")
        print(resp.text)
        return False

def list_orchestrators():
    """List all registered orchestrators"""
    
    # Authenticate
    auth_resp = requests.post(
        "http://localhost:8010/api/v1/auth/login",
        json={"email": "admin@system.com", "password": "LivepeerManager2025!Secure"}
    )
    
    if auth_resp.status_code != 200:
        print(f"Authentication failed: {auth_resp.status_code}")
        return
        
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get orchestrators
    resp = requests.get(
        "http://localhost:8010/api/v1/livepeer/orchestrators",
        headers=headers
    )
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nRegistered Orchestrators: {data['total']}")
        print("-" * 60)
        for orch in data['orchestrators']:
            print(f"ID: {orch['orchestrator_id']}")
            print(f"  Endpoint: {orch['endpoint']}")
            print(f"  Status: {orch['status']}")
            print(f"  Capabilities: {orch['capabilities']}")
            print()
    else:
        print(f"Failed to get orchestrators: {resp.status_code}")

if __name__ == "__main__":
    print("Registering Livepeer Orchestrator with Central Manager")
    print("=" * 60)
    
    if register_livepeer_orchestrator():
        print("\n✓ Registration successful!")
        list_orchestrators()
    else:
        print("\n✗ Registration failed!")
        sys.exit(1)