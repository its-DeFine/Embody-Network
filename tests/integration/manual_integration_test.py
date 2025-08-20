#!/usr/bin/env python3
"""
Manual Integration Test - Testing without automatic container discovery
"""

import asyncio
import json
import subprocess
import time
from datetime import datetime

import aiohttp

async def main():
    print("🚀 Manual Distributed Container Integration Test")
    print("=" * 60)
    
    # Use existing services (already running)
    print("📦 Using existing services...")
    print("⏳ Waiting for services to be ready...")
    await asyncio.sleep(2)
    
    # Test authentication
    print("🔐 Testing authentication...")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/v1/auth/login",
            json={
                "email": "admin@trading.system",
                "password": "default-admin-password-change-in-production-32chars!"
            }
        ) as resp:
            if resp.status == 200:
                token_data = await resp.json()
                token = token_data["access_token"]
                print("✅ Authentication successful")
            else:
                print("❌ Authentication failed")
                return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test cluster status
        print("📊 Testing cluster status...")
        async with session.get(
            "http://localhost:8000/api/v1/cluster/status",
            headers=headers
        ) as resp:
            if resp.status == 200:
                status = await resp.json()
                print(f"✅ Cluster status: {status.get('status', 'unknown')}")
            else:
                print(f"❌ Cluster status failed: {resp.status}")
        
        # Test health endpoint
        print("🏥 Testing health endpoint...")
        async with session.get("http://localhost:8000/health") as resp:
            if resp.status == 200:
                health = await resp.json()
                print(f"✅ Health check: {health.get('status', 'unknown')}")
            else:
                print(f"❌ Health check failed: {resp.status}")
        
        # Test communication stats
        print("📡 Testing communication stats...")
        async with session.get(
            "http://localhost:8000/api/v1/cluster/communication/stats",
            headers=headers
        ) as resp:
            if resp.status == 200:
                stats = await resp.json()
                print(f"✅ Communication hub: {stats}")
            else:
                print(f"❌ Communication stats failed: {resp.status}")
                
        # Test cluster actions
        print("⚙️ Testing cluster actions...")
        async with session.post(
            "http://localhost:8000/api/v1/cluster/actions",
            headers=headers,
            json={"action": "health_check", "params": {}}
        ) as resp:
            if resp.status == 200:
                action_result = await resp.json()
                print(f"✅ Health check action: {action_result}")
            else:
                print(f"❌ Cluster action failed: {resp.status}")
    
    # Skip cleanup to preserve running containers for further testing
    print("🧹 Skipping cleanup (containers preserved for further testing)...")
    
    print("✅ Manual integration test completed!")

if __name__ == "__main__":
    asyncio.run(main())