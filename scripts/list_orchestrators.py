#!/usr/bin/env python3
"""
List all registered orchestrators in the manager
"""

import httpx
import asyncio
import json

MANAGER_URL = "http://localhost:8010"
ADMIN_EMAIL = "admin@system.com"
ADMIN_PASSWORD = "LivepeerManager2025!Secure"

async def main():
    async with httpx.AsyncClient() as client:
        # Get auth token
        auth_response = await client.post(
            f"{MANAGER_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if auth_response.status_code != 200:
            print(f"Auth failed: {auth_response.text}")
            return
            
        token = auth_response.json()["access_token"]
        print(f"✅ Authenticated successfully\n")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get list of orchestrators
        response = await client.get(
            f"{MANAGER_URL}/api/v1/livepeer/orchestrators",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            orchestrators = data.get('orchestrators', [])
            
            print(f"📋 Registered Orchestrators: {len(orchestrators)}")
            print("=" * 60)
            
            for orch in orchestrators:
                print(f"\n🎬 Orchestrator: {orch.get('orchestrator_id')}")
                print(f"   Status: {orch.get('status')}")
                print(f"   Endpoint: {orch.get('endpoint')}")
                print(f"   Capabilities: {', '.join(orch.get('capabilities', []))}")
                print(f"   Last Heartbeat: {orch.get('last_heartbeat', 'N/A')}")
                
            if not orchestrators:
                print("No orchestrators registered yet")
        else:
            print(f"❌ Failed to get orchestrators: {response.status_code}")
            print(f"   Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())