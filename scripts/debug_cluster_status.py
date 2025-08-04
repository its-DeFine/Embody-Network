#!/usr/bin/env python3
"""
Debug Cluster Status Test
Check what the cluster status endpoint actually returns.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import aiohttp

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_cluster_status():
    """Test cluster status endpoint"""
    print("🔍 Debug Cluster Status API")
    print("=" * 40)
    
    # Start a quick test environment
    central_manager_project = "debug-cluster-status"
    orchestrator_project = "debug-orchestrator-status"
    
    try:
        # Deploy central manager
        print("🏢 Deploying Central Manager...")
        compose_file = _create_central_compose(central_manager_project)
        _run_command([
            "docker-compose", "-f", compose_file, 
            "-p", central_manager_project, "up", "-d", "--build"
        ])
        
        # Wait for service
        await _wait_for_service("http://127.0.0.1:8000")
        
        # Deploy orchestrator
        print("🎯 Deploying Orchestrator...")
        orch_compose = _create_orchestrator_compose(orchestrator_project)
        _run_command([
            "docker-compose", "-f", orch_compose,
            "-p", orchestrator_project, "up", "-d", "--build"
        ])
        
        await _wait_for_service("http://127.0.0.1:8001")
        
        # Wait for registration
        print("⏳ Waiting for registration...")
        await asyncio.sleep(10)
        
        # Test cluster status API
        async with aiohttp.ClientSession() as session:
            # Authenticate
            async with session.post(
                "http://127.0.0.1:8000/api/v1/auth/token",
                data={
                    "username": "admin", 
                    "password": "central-admin-password-for-orchestrator-deployment-testing"
                }
            ) as response:
                token_data = await response.json()
                token = token_data["access_token"]
            
            # Get cluster status
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(
                "http://127.0.0.1:8000/api/v1/cluster/status",
                headers=headers
            ) as response:
                print(f"📊 Cluster Status Response ({response.status}):")
                data = await response.json()
                print(json.dumps(data, indent=2))
                
                # Check what the test is looking for
                total_containers_root = data.get("total_containers", "NOT_FOUND")
                total_containers_cluster = data.get("cluster", {}).get("total_containers", "NOT_FOUND")
                
                print(f"\n🔍 Test Analysis:")
                print(f"   Root level 'total_containers': {total_containers_root}")
                print(f"   cluster.total_containers: {total_containers_cluster}")
                
                if total_containers_cluster >= 1:
                    print(f"   ✅ Should use: cluster_stats.get('cluster', {{}}).get('total_containers', 0)")
                else:
                    print(f"   ❌ Something is wrong with container registration")
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        _cleanup_deployment(central_manager_project)
        _cleanup_deployment(orchestrator_project)

def _create_central_compose(project_name: str) -> str:
    compose_file = project_root / f"docker-compose.{project_name}.yml"
    compose_content = f"""
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: {project_name}-redis
    command: redis-server --appendonly yes --bind 0.0.0.0
    ports:
      - "6379:6379"
    networks: [{project_name}-network]
  central-manager:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: {project_name}-manager
    environment:
      - REDIS_URL=redis://redis:6379
      - ENABLE_DISTRIBUTED=true
      - JWT_SECRET=central-manager-jwt-secret-for-orchestrator-testing-32chars
      - ADMIN_PASSWORD=central-admin-password-for-orchestrator-deployment-testing
      - MASTER_SECRET_KEY=central-master-key-for-secure-orchestrator-communication-32chars
      - LOG_LEVEL=INFO
    ports: ["8000:8000"]
    depends_on: [redis]
    networks: [{project_name}-network]
    volumes: ["./app:/app/app", "./keys:/app/keys"]
networks:
  {project_name}-network:
    driver: bridge
    name: {project_name}-network
"""
    with open(compose_file, "w") as f:
        f.write(compose_content.strip())
    return str(compose_file)

def _create_orchestrator_compose(project_name: str) -> str:
    compose_file = project_root / f"docker-compose.{project_name}.yml"
    compose_content = f"""
version: '3.8'
services:
  orchestrator-agent:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: {project_name}-agent
    environment:
      - AGENT_ID={project_name}-agent
      - AGENT_TYPE=orchestrator_cluster
      - AGENT_PORT=8001
      - REDIS_URL=redis://host.docker.internal:6379
      - CENTRAL_MANAGER_URL=http://host.docker.internal:8000
      - ADMIN_PASSWORD=central-admin-password-for-orchestrator-deployment-testing
      - CONTAINER_NAME={project_name}-cluster
      - EXTERNAL_IP=127.0.0.1
      - AGENT_CONFIG={{"capabilities":["agent_runner","orchestrator_cluster"],"max_agents":10}}
      - AUTO_REGISTER=true
      - HEARTBEAT_INTERVAL=30
    ports: ["8001:8001"]
    networks: [{project_name}-network]
    extra_hosts: ["host.docker.internal:host-gateway"]
networks:
  {project_name}-network:
    driver: bridge
    name: {project_name}-network
"""
    with open(compose_file, "w") as f:
        f.write(compose_content.strip())
    return str(compose_file)

async def _wait_for_service(url: str):
    for _ in range(30):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health", timeout=5) as response:
                    if response.status == 200:
                        return
        except:
            pass
        await asyncio.sleep(1)

def _run_command(command):
    result = subprocess.run(command, capture_output=True, text=True, cwd=project_root)
    if result.returncode != 0:
        print(f"Command failed: {result.stderr}")

def _cleanup_deployment(project_name: str):
    try:
        compose_file = project_root / f"docker-compose.{project_name}.yml"
        if compose_file.exists():
            _run_command([
                "docker-compose", "-f", str(compose_file),
                "-p", project_name, "down", "-v", "--remove-orphans"
            ])
            compose_file.unlink()
    except:
        pass

if __name__ == "__main__":
    asyncio.run(test_cluster_status())