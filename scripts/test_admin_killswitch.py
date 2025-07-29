#!/usr/bin/env python3
"""
Test Admin Killswitch Functionality
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000"
ADMIN_BASE = "http://localhost:8001"
ADMIN_API_KEY = "test_admin_key_123"  # Change this to your actual admin key


async def test_admin_functions():
    """Test admin functionality including killswitch"""
    print("🧪 Testing Admin Killswitch and Control Functions")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Admin Login
        print("\n1. Testing admin login...")
        response = await client.post(
            f"{API_BASE}/admin/auth/login?api_key={ADMIN_API_KEY}"
        )
        
        if response.status_code != 200:
            print(f"❌ Admin login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
        
        auth_data = response.json()
        admin_token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        print("✅ Admin login successful")
        
        # 2. Get platform stats
        print("\n2. Getting platform statistics...")
        response = await client.get(
            f"{API_BASE}/admin/stats/overview",
            headers=headers
        )
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ Platform Statistics:")
            print(f"   • Total Customers: {stats['total_customers']}")
            print(f"   • Total Agents: {stats['total_agents']}")
            print(f"   • Total Tasks: {stats['total_tasks']}")
            print(f"   • Total Teams: {stats['total_teams']}")
            print(f"   • Agents by Status: {json.dumps(stats['agents_by_status'], indent=2)}")
        
        # 3. List all agents
        print("\n3. Listing all agents (admin view)...")
        response = await client.get(
            f"{API_BASE}/admin/agents?limit=10",
            headers=headers
        )
        
        if response.status_code == 200:
            agents = response.json()
            print(f"✅ Found {len(agents)} agents")
            
            if agents:
                # Test stop on first agent
                test_agent = agents[0]
                agent_id = test_agent.get("agent_id")
                
                if agent_id:
                    print(f"\n4. Testing admin stop on agent {agent_id}...")
                    response = await client.post(
                        f"{API_BASE}/admin/agents/{agent_id}/stop?reason=Test%20admin%20stop&force=false",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        print("✅ Admin stop command sent successfully")
                    else:
                        print(f"❌ Admin stop failed: {response.status_code}")
        
        # 5. Test container stats (if admin control service is running)
        print("\n5. Testing container statistics...")
        try:
            admin_headers = {"Authorization": f"Bearer {ADMIN_API_KEY}"}
            response = await client.get(
                f"{ADMIN_BASE}/stats/containers",
                headers=admin_headers
            )
            
            if response.status_code == 200:
                container_stats = response.json()
                print(f"✅ Container statistics retrieved: {len(container_stats)} containers")
                for stat in container_stats[:3]:  # Show first 3
                    print(f"   • Agent {stat['agent_id']}: CPU {stat['cpu_percent']}%, Memory {stat['memory_usage_mb']}MB")
            else:
                print(f"⚠️  Admin control service not accessible: {response.status_code}")
        except:
            print("⚠️  Admin control service not running on port 8001")
        
        # 6. Test broadcast message
        print("\n6. Testing admin broadcast...")
        response = await client.post(
            f"{API_BASE}/admin/broadcast",
            headers=headers,
            params={
                "message": "Test broadcast from admin",
                "target": "all"
            }
        )
        
        if response.status_code == 200:
            print("✅ Broadcast message sent")
        
        # 7. Test killswitch (commented out for safety)
        print("\n7. Killswitch test...")
        print("⚠️  Killswitch test skipped for safety")
        print("   To test killswitch, uncomment the code below:")
        print("   - Emergency stop all: POST /killswitch/all")
        print("   - Stop customer agents: POST /killswitch/customer/{customer_id}")
        print("   - Force stop agent: POST /agents/{agent_id}/force-stop")
        
        # Uncomment to test killswitch (DANGEROUS!)
        # if input("\n⚠️  Test emergency killswitch? (yes/no): ").lower() == "yes":
        #     response = await client.post(
        #         f"{ADMIN_BASE}/killswitch/all",
        #         headers=admin_headers,
        #         json={
        #             "reason": "Test emergency stop",
        #             "force": True
        #         }
        #     )
        #     if response.status_code == 200:
        #         result = response.json()
        #         print(f"✅ Killswitch activated! Affected: {result['affected_count']} containers")


async def test_admin_dashboard():
    """Test admin dashboard availability"""
    print("\n\n📊 Admin Dashboard Information")
    print("=" * 60)
    print("Admin Dashboard should be accessible at:")
    print("  • Dashboard: http://localhost:8001/dashboard")
    print("  • API Docs: http://localhost:8001/docs")
    print("\nDefault Admin API Key: Use the key from Docker secrets or environment")
    print("\nAdmin Endpoints:")
    print("  • POST   /admin/auth/login - Admin login")
    print("  • GET    /admin/agents - List all agents")
    print("  • POST   /admin/agents/{id}/stop - Stop specific agent")
    print("  • GET    /admin/stats/overview - Platform statistics")
    print("  • POST   /admin/broadcast - Broadcast message")
    print("  • POST   /killswitch/all - Emergency stop all")
    print("  • POST   /killswitch/customer/{id} - Stop customer agents")
    print("  • GET    /stats/containers - Container resource stats")
    print("  • GET    /audit-logs - Admin action audit trail")


if __name__ == "__main__":
    asyncio.run(test_admin_functions())
    asyncio.run(test_admin_dashboard())