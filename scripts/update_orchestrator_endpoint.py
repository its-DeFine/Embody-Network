#!/usr/bin/env python3
"""
Update the orchestrator registration with correct worker endpoint
"""

import httpx
import asyncio

MANAGER_URL = "http://localhost:8010"
ADMIN_EMAIL = "admin@system.com"
ADMIN_PASSWORD = "LivepeerManager2025!Secure"

async def main():
    async with httpx.AsyncClient() as client:
        # Authenticate
        auth_response = await client.post(
            f"{MANAGER_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if auth_response.status_code != 200:
            print(f"Auth failed: {auth_response.text}")
            return
            
        token = auth_response.json()["access_token"]
        print(f"✅ Authenticated successfully")
        
        # Update the autonomy orchestrator with accessible worker endpoint
        registration_data = {
            "orchestrator_id": "autonomy-orchestrator-001",
            "endpoint": "http://host.docker.internal:9876",  # Worker endpoint accessible from Docker containers
            "capabilities": ["agent-net", "service_monitoring"],
            "eth_address": "0xb09f0576730F5DEaec893166E2555Ab5052D881C"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.post(
            f"{MANAGER_URL}/api/v1/livepeer/orchestrators/register",
            json=registration_data,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Orchestrator updated successfully!")
            print(f"   ID: {data.get('orchestrator_id')}")
            print(f"   New endpoint: {registration_data['endpoint']}")
        else:
            print(f"❌ Update failed: {response.status_code}")
            print(f"   Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())