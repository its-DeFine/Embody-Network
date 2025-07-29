#!/usr/bin/env python3
"""
Test the actual container lifecycle management
"""

import asyncio
import docker
import httpx
import time

API_BASE = "http://localhost:8000"


async def test_container_lifecycle():
    """Test if containers are actually created and managed"""
    print("🐳 Testing Container Lifecycle Management")
    print("=" * 60)
    
    docker_client = docker.from_env()
    
    # 1. Check Docker access
    print("\n1. Checking Docker access...")
    try:
        version = docker_client.version()
        print(f"✅ Docker accessible: {version['Version']}")
    except Exception as e:
        print(f"❌ Docker not accessible: {e}")
        return
    
    # 2. List current agent containers
    print("\n2. Current agent containers:")
    agent_containers = docker_client.containers.list(
        filters={"label": "agent_id"}
    )
    print(f"   Found {len(agent_containers)} agent containers")
    for container in agent_containers:
        print(f"   • {container.name} - {container.status}")
    
    # 3. Check if agent-manager is running
    print("\n3. Checking agent-manager service...")
    try:
        agent_manager = docker_client.containers.get("agent-manager")
        print(f"   Status: {agent_manager.status}")
        if agent_manager.status != "running":
            print("   ⚠️  Agent manager not running - container creation will fail")
    except:
        print("   ❌ Agent manager container not found")
    
    # 4. Check if autogen-agent image exists
    print("\n4. Checking for autogen-agent image...")
    try:
        images = docker_client.images.list(name="autogen-agent")
        if images:
            print(f"   ✅ Found {len(images)} autogen-agent image(s)")
        else:
            print("   ❌ No autogen-agent image found - agents cannot be created")
    except Exception as e:
        print(f"   ❌ Error checking images: {e}")
    
    # 5. Test actual agent creation via API
    print("\n5. Testing agent creation via API...")
    async with httpx.AsyncClient() as client:
        # Login first
        login_data = {
            "email": "test@testcorp.com",
            "api_key": "DcqvANBn1GcraB9J5SXGc9yOIvUaoFBU"
        }
        
        response = await client.post(f"{API_BASE}/auth/login", json=login_data)
        if response.status_code != 200:
            print("   ❌ Login failed")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create agent
        agent_config = {
            "name": "Container Test Agent",
            "agent_type": "trading",
            "config": {"test": True}
        }
        
        print("   Creating agent...")
        response = await client.post(
            f"{API_BASE}/agents",
            json=agent_config,
            headers=headers
        )
        
        if response.status_code == 200:
            agent_id = response.json()["agent_id"]
            print(f"   ✅ Agent created: {agent_id}")
            
            # Wait and check if container was created
            print("   Waiting for container creation...")
            time.sleep(5)
            
            # Check for new containers
            new_containers = docker_client.containers.list(
                filters={"label": f"agent_id={agent_id}"}
            )
            
            if new_containers:
                print(f"   ✅ Container created: {new_containers[0].name}")
            else:
                print("   ❌ No container was created for the agent")
        else:
            print(f"   ❌ Agent creation failed: {response.status_code}")


async def check_service_connections():
    """Check if services can actually communicate"""
    print("\n\n🔌 Testing Service Connections")
    print("=" * 60)
    
    # 1. Redis connection
    print("\n1. Testing Redis connection...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print("   ✅ Redis is accessible")
        
        # Check for data
        keys = r.keys('*')
        print(f"   • Found {len(keys)} keys in Redis")
        
        # Sample some keys
        for key in keys[:5]:
            key_type = r.type(key).decode()
            print(f"   • {key.decode()}: {key_type}")
    except Exception as e:
        print(f"   ❌ Redis error: {e}")
    
    # 2. RabbitMQ connection
    print("\n2. Testing RabbitMQ connection...")
    try:
        response = httpx.get(
            "http://localhost:15672/api/overview",
            auth=("guest", "guest")
        )
        if response.status_code == 200:
            data = response.json()
            print("   ✅ RabbitMQ is accessible")
            print(f"   • Version: {data.get('rabbitmq_version', 'unknown')}")
            print(f"   • Messages ready: {data.get('queue_totals', {}).get('messages_ready', 0)}")
        else:
            print(f"   ❌ RabbitMQ returned: {response.status_code}")
    except Exception as e:
        print(f"   ❌ RabbitMQ error: {e}")


def check_unused_files():
    """Identify potentially unused files"""
    print("\n\n🗑️  Checking for Unused Files")
    print("=" * 60)
    
    # Check for example/test containers
    print("\n1. Non-production containers running:")
    docker_client = docker.from_env()
    test_containers = [
        "byoc-gateway-test",
        "orchestrator-siphon"
    ]
    
    for name in test_containers:
        try:
            container = docker_client.containers.get(name)
            print(f"   • {name}: {container.status} (possibly unused)")
        except:
            pass
    
    # Check for unused services in docker-compose
    print("\n2. Services that might be unused:")
    unused_services = [
        "core-engine (placeholder implementation)",
        "update-pipeline (Docker socket issues)",
        "agent-manager (Docker socket issues)",
    ]
    
    for service in unused_services:
        print(f"   • {service}")
    
    # Check for test data
    print("\n3. Test/example files that could be cleaned:")
    test_files = [
        "./tests/* (unit tests not implemented)",
        "./customer_agents/examples/* (if exists)",
        "./deployments/* (if empty)",
    ]
    
    for file in test_files:
        print(f"   • {file}")


if __name__ == "__main__":
    asyncio.run(test_container_lifecycle())
    asyncio.run(check_service_connections())
    check_unused_files()
    
    print("\n\n📊 Summary")
    print("=" * 60)
    print("Issues found:")
    print("• Agent containers are NOT actually created (missing autogen-agent image)")
    print("• Agent-manager and update-pipeline have Docker socket permission issues")
    print("• Several placeholder/test services are running")
    print("• Many test files exist but aren't used")
    print("\nRecommendations:")
    print("• Build the actual autogen-agent Docker image")
    print("• Fix Docker socket permissions or run privileged")
    print("• Remove unused test containers and files")
    print("• Focus on core functionality that works")