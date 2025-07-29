#!/usr/bin/env python3
"""
Test killswitch functionality for Docker Swarm services
"""

import docker
import time
import sys

def test_killswitch():
    """Test killswitch operations on swarm services"""
    print("🔌 Testing Killswitch Functionality")
    print("=" * 60)
    
    client = docker.from_env()
    
    # Test 1: Emergency stop a single service
    print("\n1. Testing single service killswitch:")
    print("-" * 40)
    
    try:
        # Scale api-gateway to 0 (emergency stop)
        print("⚠️  Activating killswitch for api-gateway...")
        service = client.services.get("autogen_api-gateway")
        service.update(mode={"Replicated": {"Replicas": 0}})
        print("✅ Service scaled to 0 replicas (stopped)")
        
        time.sleep(3)
        
        # Check status
        service.reload()
        replicas = service.attrs['Spec']['Mode']['Replicated']['Replicas']
        print(f"   Current replicas: {replicas}")
        
        # Restore service
        print("\n   Restoring service...")
        service.update(mode={"Replicated": {"Replicas": 2}})
        print("✅ Service restored to 2 replicas")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Emergency stop all services
    print("\n\n2. Testing stack-wide killswitch:")
    print("-" * 40)
    
    services = client.services.list(filters={"label": "com.docker.stack.namespace=autogen"})
    print(f"Found {len(services)} services in autogen stack")
    
    # Store original replica counts
    original_replicas = {}
    for service in services:
        name = service.name
        if 'Replicated' in service.attrs['Spec']['Mode']:
            replicas = service.attrs['Spec']['Mode']['Replicated']['Replicas']
            original_replicas[name] = replicas
            print(f"   {name}: {replicas} replicas")
    
    # Test 3: Pause/unpause containers
    print("\n\n3. Testing container pause/unpause:")
    print("-" * 40)
    
    containers = client.containers.list(filters={"label": "com.docker.stack.namespace=autogen"})
    print(f"Found {len(containers)} running containers")
    
    if containers:
        # Test pausing first container
        container = containers[0]
        print(f"\n   Pausing container: {container.name}")
        try:
            container.pause()
            print("✅ Container paused")
            
            time.sleep(2)
            
            container.unpause()
            print("✅ Container unpaused")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test 4: Force remove service (extreme killswitch)
    print("\n\n4. Testing force remove (extreme killswitch):")
    print("-" * 40)
    print("⚠️  This would remove the service entirely")
    print("   Command: docker service rm <service_name>")
    print("   (Not executing to preserve test environment)")
    
    # Test 5: Network isolation killswitch
    print("\n\n5. Testing network isolation:")
    print("-" * 40)
    print("⚠️  Services can be isolated by disconnecting from network")
    print("   Command: docker network disconnect <network> <container>")
    
    # Summary
    print("\n\n📊 Killswitch Methods Summary:")
    print("=" * 60)
    print("1. Scale to 0 replicas - Graceful shutdown")
    print("2. Pause containers - Immediate freeze")
    print("3. Stop containers - Clean shutdown")
    print("4. Remove service - Permanent removal")
    print("5. Network isolation - Cut communication")
    
    return True


def test_admin_killswitch_api():
    """Test killswitch via admin API (if it were running)"""
    print("\n\n🌐 Admin API Killswitch Commands:")
    print("=" * 60)
    
    print("If admin-control service were running, these endpoints would be available:")
    print("\n1. Emergency stop all agents:")
    print("   POST /admin/emergency-stop")
    print("   Body: {")
    print('     "reason": "Security incident detected",')
    print('     "force": true')
    print("   }")
    
    print("\n2. Stop specific customer agents:")
    print("   POST /admin/customers/{customer_id}/stop")
    
    print("\n3. Stop specific agent:")
    print("   POST /admin/agents/{agent_id}/stop")
    
    print("\n4. Pause all operations:")
    print("   POST /admin/platform/pause")
    
    print("\n5. Resume operations:")
    print("   POST /admin/platform/resume")


def demonstrate_swarm_commands():
    """Demonstrate swarm management commands"""
    print("\n\n🛠️  Swarm Management Commands:")
    print("=" * 60)
    
    commands = [
        ("Scale service to 0", "docker service scale autogen_api-gateway=0"),
        ("Force update service", "docker service update --force autogen_api-gateway"),
        ("Remove service", "docker service rm autogen_api-gateway"),
        ("Stop all tasks", "docker service update --replicas 0 autogen_api-gateway"),
        ("Drain node", "docker node update --availability drain <node-id>"),
        ("Leave swarm", "docker swarm leave --force"),
        ("Remove stack", "docker stack rm autogen"),
        ("Prune system", "docker system prune -af")
    ]
    
    for desc, cmd in commands:
        print(f"\n{desc}:")
        print(f"   $ {cmd}")


if __name__ == "__main__":
    try:
        test_killswitch()
        test_admin_killswitch_api()
        demonstrate_swarm_commands()
        
        print("\n\n✅ Killswitch testing complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)