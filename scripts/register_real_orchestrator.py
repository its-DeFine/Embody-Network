#!/usr/bin/env python3
"""
Register the real Livepeer orchestrator with the manager
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
        print(f"✅ Authenticated successfully")
        
        # Register the real orchestrator
        registration_data = {
            "orchestrator_id": "autonomy-orchestrator-001",
            "endpoint": "http://livepeer-orchestrator:9995",
            "capabilities": ["agent-net", "video_transcoding"],
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
            print(f"✅ Orchestrator registered successfully!")
            print(f"   ID: {data.get('orchestrator_id')}")
            print(f"   Challenge: {data.get('challenge')}")
            print(f"   Message: {data.get('message')}")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())