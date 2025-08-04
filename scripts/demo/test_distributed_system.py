#!/usr/bin/env python3
"""
Test script for distributed container management system.
Demonstrates container registration, agent deployment, and migration.
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime

# Configuration
CENTRAL_MANAGER_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@trading.system"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default-admin-password-change-in-production-32chars!")


async def authenticate():
    """Get authentication token"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{CENTRAL_MANAGER_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["access_token"]
            else:
                print(f"❌ Authentication failed: {resp.status}")
                return None


async def test_cluster_status(token):
    """Test cluster status endpoint"""
    print("\n🔍 Testing Cluster Status...")
    
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{CENTRAL_MANAGER_URL}/api/v1/cluster/status",
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print("✅ Cluster Status:")
                print(f"   Status: {data['status']}")
                print(f"   Registered Containers: {data['cluster']['registered_containers']}")
                print(f"   Active Containers: {data['cluster']['active_containers']}")
                print(f"   Discovery Running: {data['discovery']['is_running']}")
                print(f"   Total Agents: {data['deployments']['total_agents']}")
                return True
            else:
                print(f"❌ Failed to get cluster status: {resp.status}")
                return False


async def register_test_container(token, container_name="test-agent-01"):
    """Register a test container"""
    print(f"\n📦 Registering Container: {container_name}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    registration_data = {
        "container_name": container_name,
        "host_address": "172.17.0.3",  # Docker internal IP
        "api_port": 8001,
        "capabilities": ["agent_runner", "gpu_compute"],
        "resources": {
            "cpu_count": 4,
            "memory_limit": 4294967296,  # 4GB
            "gpu_available": True
        },
        "metadata": {
            "version": "1.0.0",
            "environment": "test"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{CENTRAL_MANAGER_URL}/api/v1/cluster/containers/register",
            json=registration_data,
            headers=headers
        ) as resp:
            if resp.status in [200, 201]:
                data = await resp.json()
                print(f"✅ Container registered: {data['container_id']}")
                return data["container_id"]
            else:
                print(f"❌ Failed to register container: {resp.status}")
                error = await resp.text()
                print(f"   Error: {error}")
                return None


async def deploy_agent(token, agent_type="trading", strategy="least_loaded"):
    """Deploy an agent to the cluster"""
    print(f"\n🤖 Deploying {agent_type} agent with {strategy} strategy...")
    
    headers = {"Authorization": f"Bearer {token}"}
    deployment_data = {
        "agent_type": agent_type,
        "agent_config": {
            "name": f"{agent_type}_agent_{datetime.now().strftime('%H%M%S')}",
            "trading_pairs": ["BTC/USD", "ETH/USD"],
            "risk_level": "medium"
        },
        "resource_requirements": {
            "min_cpu": 1,
            "min_memory": 1073741824,  # 1GB
            "preferred_gpu": True
        },
        "deployment_strategy": strategy,
        "constraints": {
            "require_capability": "gpu_compute" if agent_type == "analysis" else None
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{CENTRAL_MANAGER_URL}/api/v1/cluster/agents/deploy",
            json=deployment_data,
            headers=headers
        ) as resp:
            if resp.status in [200, 201]:
                data = await resp.json()
                print(f"✅ Agent deployed: {data['agent_id']}")
                print(f"   Container: {data['container_id']}")
                return data["agent_id"]
            else:
                print(f"❌ Failed to deploy agent: {resp.status}")
                error = await resp.text()
                print(f"   Error: {error}")
                return None


async def get_cluster_distribution(token):
    """Get agent distribution across cluster"""
    print("\n📊 Cluster Distribution...")
    
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{CENTRAL_MANAGER_URL}/api/v1/cluster/metrics/distribution",
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Total Containers: {data['total_containers']}")
                print(f"   Total Agents: {data['total_agents']}")
                
                for container_id, info in data['distribution'].items():
                    print(f"\n   Container: {info['container_name']} ({container_id})")
                    print(f"   - Agents: {info['agent_count']}")
                    print(f"   - Health: {info['health_score']}")
                    if info['agents']:
                        for agent in info['agents']:
                            print(f"     • {agent}")
            else:
                print(f"❌ Failed to get distribution: {resp.status}")


async def migrate_agent(token, agent_id, target_container=None):
    """Migrate an agent to a different container"""
    print(f"\n🔄 Migrating agent {agent_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    migration_data = {
        "agent_id": agent_id,
        "target_container_id": target_container,
        "reason": "load_balancing",
        "preserve_state": True
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{CENTRAL_MANAGER_URL}/api/v1/cluster/agents/{agent_id}/migrate",
            json=migration_data,
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Agent migrated successfully")
                print(f"   From: {data.get('from_container')}")
                print(f"   To: {data.get('to_container')}")
                return True
            else:
                print(f"❌ Failed to migrate agent: {resp.status}")
                return False


async def trigger_rebalance(token):
    """Trigger cluster rebalancing"""
    print("\n⚖️ Triggering cluster rebalance...")
    
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{CENTRAL_MANAGER_URL}/api/v1/cluster/actions",
            json={"action": "rebalance"},
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Rebalance completed")
                print(f"   Migrations: {data.get('migrations_performed', 0)}")
                return True
            else:
                print(f"❌ Failed to rebalance: {resp.status}")
                return False


async def main():
    """Run distributed system tests"""
    print("🚀 Testing Distributed Container Management System")
    print("=" * 50)
    
    # Authenticate
    token = await authenticate()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    print("✅ Authenticated successfully")
    
    # Test cluster status
    await test_cluster_status(token)
    
    # Register test containers
    container1 = await register_test_container(token, "test-agent-01")
    await asyncio.sleep(1)
    container2 = await register_test_container(token, "test-agent-02")
    
    if container1 and container2:
        # Deploy some agents
        agent1 = await deploy_agent(token, "trading", "round_robin")
        await asyncio.sleep(1)
        agent2 = await deploy_agent(token, "analysis", "least_loaded")
        await asyncio.sleep(1)
        agent3 = await deploy_agent(token, "risk", "capability_match")
        
        # Check distribution
        await get_cluster_distribution(token)
        
        # Test migration if we have agents
        if agent1:
            await migrate_agent(token, agent1, container2)
            
        # Trigger rebalance
        await trigger_rebalance(token)
        
        # Final distribution
        await get_cluster_distribution(token)
    
    print("\n✅ Distributed system test completed!")


if __name__ == "__main__":
    asyncio.run(main())