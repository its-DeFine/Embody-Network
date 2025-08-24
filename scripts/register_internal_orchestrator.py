#!/usr/bin/env python3
"""
Register the internal Livepeer orchestrator with the central manager
"""

import requests
import json
import sys
import os

def register_internal_orchestrator():
    """Register the internal Livepeer orchestrator"""
    
    manager_url = "http://localhost:8010"
    admin_password = os.environ.get("ADMIN_PASSWORD", "super-secure-admin-password-2024-embody-network")
    
    # First authenticate
    print("Authenticating with manager...")
    auth_resp = requests.post(
        f"{manager_url}/api/v1/auth/login",
        json={"email": "admin@system.com", "password": admin_password}
    )
    
    if auth_resp.status_code != 200:
        print(f"Authentication failed: {auth_resp.status_code}")
        print(f"Response: {auth_resp.text}")
        return False
        
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Authentication successful")
    
    # Register the internal Livepeer orchestrator
    orchestrator_data = {
        "orchestrator_id": "internal-livepeer-001",
        "name": "Internal Livepeer Orchestrator",
        "address": "https://livepeer-orchestrator:9995",
        "endpoint": "https://livepeer-orchestrator:9995",  # RPC endpoint
        "eth_address": "0x0000000000000000000000000000000000000000",  # Internal, no ETH address
        "price_per_unit": 0,  # Free for internal use
        "max_price_per_unit": 0,
        "metadata": {
            "type": "internal",
            "region": "local",
            "capabilities": ["agent-net", "byoc", "transcoding"]
        }
    }
    
    print(f"Registering orchestrator: {orchestrator_data['orchestrator_id']}")
    
    # Register with the Livepeer orchestrators endpoint
    resp = requests.post(
        f"{manager_url}/api/v1/livepeer/orchestrators/register",
        headers=headers,
        json=orchestrator_data
    )
    
    if resp.status_code in [200, 201]:
        print(f"Successfully registered internal orchestrator")
        result = resp.json()
        print(json.dumps(result, indent=2))
        return True
    elif resp.status_code == 409:
        print(f"Orchestrator already registered")
        # Try to get its current status
        get_resp = requests.get(
            f"{manager_url}/api/v1/livepeer/orchestrators",
            headers=headers
        )
        if get_resp.status_code == 200:
            data = get_resp.json()
            print(f"Current orchestrators: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Registration failed: {resp.status_code}")
        print(f"Response: {resp.text}")
        return False

if __name__ == "__main__":
    success = register_internal_orchestrator()
    sys.exit(0 if success else 1)