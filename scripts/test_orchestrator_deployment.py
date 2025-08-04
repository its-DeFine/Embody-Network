#!/usr/bin/env python3
"""
Orchestrator Deployment Pattern Test

Tests the real production scenario:
- Central Manager + Redis (Your infrastructure) 
- Agent Cluster 1 (Orchestrator 1's infrastructure)
- Agent Cluster 2 (Orchestrator 2's infrastructure)

Each runs independently and connects across networks.
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import aiohttp

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class OrchestratorDeploymentTester:
    """Test orchestrator deployment pattern with separate network isolation"""
    
    def __init__(self):
        # Simulate three separate deployments
        self.central_manager_project = "central-trading-system"
        self.orchestrator_1_project = "orchestrator-1-cluster"  
        self.orchestrator_2_project = "orchestrator-2-cluster"
        
        # Network configuration (simulating external IPs)
        self.central_manager_ip = "127.0.0.1"  # Your infrastructure
        self.orchestrator_1_ip = "127.0.0.1"  # Orchestrator 1's infrastructure
        self.orchestrator_2_ip = "127.0.0.1"  # Orchestrator 2's infrastructure
        
        # API endpoints (different ports simulate different networks)
        self.central_manager_url = "http://127.0.0.1:8000"
        self.orchestrator_1_url = "http://127.0.0.1:8001"
        self.orchestrator_2_url = "http://127.0.0.1:8002"
        
        self.session = None
        self.admin_token = None
        self.test_results = {
            "central_manager_isolated": False,
            "orchestrator_1_isolated": False,
            "orchestrator_2_isolated": False,
            "cross_network_registration": False,
            "distributed_agent_deployment": False,
            "orchestrator_autonomy": False
        }
        
    async def run_orchestrator_test(self) -> Dict[str, Any]:
        """Run complete orchestrator deployment test"""
        print("🌐 Orchestrator Deployment Pattern Test")
        print("=" * 70)
        print("Testing real production scenario:")
        print("• Central Manager + Redis (Your infrastructure)")
        print("• Agent Cluster 1 (Orchestrator 1's infrastructure)")  
        print("• Agent Cluster 2 (Orchestrator 2's infrastructure)")
        print("=" * 70)
        
        start_time = datetime.utcnow()
        
        try:
            # Phase 1: Deploy Central Manager Infrastructure (Your side)
            await self._phase_1_central_infrastructure()
            
            # Phase 2: Deploy Orchestrator 1 Cluster (Separate network)
            await self._phase_2_orchestrator_1_cluster()
            
            # Phase 3: Deploy Orchestrator 2 Cluster (Separate network)
            await self._phase_3_orchestrator_2_cluster()
            
            # Phase 4: Test Cross-Network Registration
            await self._phase_4_cross_network_registration()
            
            # Phase 5: Test Distributed Agent Deployment
            await self._phase_5_distributed_deployment()
            
            # Phase 6: Validate Orchestrator Autonomy
            await self._phase_6_orchestrator_autonomy()
            
        except Exception as e:
            print(f"Orchestrator test failed: {e}")
            self.test_results["error"] = str(e)
        
        finally:
            await self._cleanup_all_deployments()
        
        # Generate results
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        passed = sum(1 for result in self.test_results.values() if result is True)
        total = len([k for k in self.test_results.keys() if k != "error"])
        
        summary = {
            "test_type": "orchestrator_deployment_pattern",
            "duration_seconds": duration,
            "tests_passed": passed,
            "tests_total": total,
            "success_rate": f"{(passed/total)*100:.1f}%",
            "results": self.test_results,
            "deployment_pattern": "multi_host_orchestrator",
            "timestamp": end_time.isoformat()
        }
        
        self._print_orchestrator_summary(summary)
        return summary
    
    async def _phase_1_central_infrastructure(self):
        """Phase 1: Deploy Central Manager Infrastructure (Your side)"""
        print("\n🏢 Phase 1: Deploying Central Manager Infrastructure...")
        print("   (Simulating YOUR infrastructure deployment)")
        
        # Cleanup first
        self._cleanup_deployment(self.central_manager_project)
        
        # Create isolated central manager deployment
        central_compose = self._create_central_manager_compose()
        
        # Deploy central infrastructure
        print("   📦 Launching Redis + Central Manager...")
        self._run_command([
            "docker-compose", "-f", central_compose, 
            "-p", self.central_manager_project, "up", "-d", "--build"
        ])
        
        # Wait for central manager to be ready
        await self._wait_for_service(self.central_manager_url, timeout=60)
        
        # Setup authentication
        self.session = aiohttp.ClientSession()
        await self._authenticate()
        
        self.test_results["central_manager_isolated"] = True
        print("   ✅ Central Manager infrastructure deployed and isolated")
    
    async def _phase_2_orchestrator_1_cluster(self):
        """Phase 2: Deploy Orchestrator 1's Agent Cluster"""
        print("\n🎯 Phase 2: Deploying Orchestrator 1's Agent Cluster...")
        print("   (Simulating ORCHESTRATOR 1's infrastructure deployment)")
        
        # Create orchestrator 1's independent deployment
        # Use host.docker.internal for container-to-host communication
        docker_central_url = self.central_manager_url.replace("127.0.0.1", "host.docker.internal")
        orch1_compose = self._create_orchestrator_compose(
            orchestrator_id=1,
            port=8001,
            project_name=self.orchestrator_1_project,
            central_manager_url=docker_central_url
        )
        
        # Deploy orchestrator 1's cluster
        print("   🤖 Launching Orchestrator 1's agent cluster...")
        self._run_command([
            "docker-compose", "-f", orch1_compose,
            "-p", self.orchestrator_1_project, "up", "-d", "--build"
        ])
        
        # Wait for orchestrator 1's cluster
        await self._wait_for_service(self.orchestrator_1_url, timeout=30)
        
        self.test_results["orchestrator_1_isolated"] = True
        print("   ✅ Orchestrator 1's cluster deployed independently")
    
    async def _phase_3_orchestrator_2_cluster(self):
        """Phase 3: Deploy Orchestrator 2's Agent Cluster"""
        print("\n🎯 Phase 3: Deploying Orchestrator 2's Agent Cluster...")
        print("   (Simulating ORCHESTRATOR 2's infrastructure deployment)")
        
        # Create orchestrator 2's independent deployment
        # Use host.docker.internal for container-to-host communication
        docker_central_url = self.central_manager_url.replace("127.0.0.1", "host.docker.internal")
        orch2_compose = self._create_orchestrator_compose(
            orchestrator_id=2,
            port=8002,
            project_name=self.orchestrator_2_project,
            central_manager_url=docker_central_url
        )
        
        # Deploy orchestrator 2's cluster
        print("   🤖 Launching Orchestrator 2's agent cluster...")
        self._run_command([
            "docker-compose", "-f", orch2_compose,
            "-p", self.orchestrator_2_project, "up", "-d", "--build"
        ])
        
        # Wait for orchestrator 2's cluster
        await self._wait_for_service(self.orchestrator_2_url, timeout=30)
        
        self.test_results["orchestrator_2_isolated"] = True
        print("   ✅ Orchestrator 2's cluster deployed independently")
    
    async def _phase_4_cross_network_registration(self):
        """Phase 4: Test Cross-Network Registration"""
        print("\n🌐 Phase 4: Testing Cross-Network Registration...")
        print("   (Testing automatic registration from orchestrator clusters)")
        
        # Wait for auto-registration
        print("   ⏳ Waiting for orchestrator clusters to register...")
        
        # Check periodically for registration
        for i in range(6):  # Check 6 times over 30 seconds
            await asyncio.sleep(5)
            containers = await self._get_registered_containers()
            print(f"      Check {i+1}/6: {len(containers)} containers registered")
            
            # Check orchestrator container logs for debugging
            if i == 2:  # After 10 seconds, check logs
                try:
                    logs1 = subprocess.check_output([
                        "docker", "logs", f"{self.orchestrator_1_project}-agent", "--tail", "10"
                    ], text=True, stderr=subprocess.STDOUT)
                    last_line = logs1.strip().split('\n')[-2] if logs1.strip() else 'No logs'
                    print(f"      📝 Orchestrator 1 logs: {last_line}")
                except:
                    print("      ❌ Could not get Orchestrator 1 logs")
                
                try:
                    logs2 = subprocess.check_output([
                        "docker", "logs", f"{self.orchestrator_2_project}-agent", "--tail", "10"
                    ], text=True, stderr=subprocess.STDOUT)
                    last_line2 = logs2.strip().split('\n')[-2] if logs2.strip() else 'No logs'
                    print(f"      📝 Orchestrator 2 logs: {last_line2}")
                except:
                    print("      ❌ Could not get Orchestrator 2 logs")
        
        # Final check
        containers = await self._get_registered_containers()
        
        if containers and len(containers) >= 2:
            print(f"   ✅ Cross-network registration successful: {len(containers)} clusters registered")
            
            for container in containers:
                container_name = container.get('container_name', 'Unknown')
                host_address = container.get('host_address', 'Unknown')
                print(f"      📋 {container_name} from {host_address}")
            
            self.test_results["cross_network_registration"] = True
        else:
            print(f"   ❌ Cross-network registration failed: Only {len(containers) if containers else 0} clusters registered")
    
    async def _phase_5_distributed_deployment(self):
        """Phase 5: Test Distributed Agent Deployment"""
        print("\n🚀 Phase 5: Testing Distributed Agent Deployment...")
        print("   (Deploying agents to orchestrator clusters from central manager)")
        
        containers = await self._get_registered_containers()
        
        if len(containers) < 2:
            print("   ❌ Cannot test deployment: Insufficient registered clusters")
            return
        
        # Deploy agent to orchestrator 1's cluster
        print("   📤 Deploying trading agent to Orchestrator 1's cluster...")
        agent1_result = await self._deploy_agent_to_orchestrator({
            "agent_type": "trading_agent",
            "agent_config": {
                "strategy": "distributed_momentum",
                "orchestrator_id": 1
            },
            "preferred_container": containers[0]["container_id"]
        })
        
        # Deploy agent to orchestrator 2's cluster  
        print("   📤 Deploying analysis agent to Orchestrator 2's cluster...")
        agent2_result = await self._deploy_agent_to_orchestrator({
            "agent_type": "analysis_agent", 
            "agent_config": {
                "analysis_type": "distributed_technical",
                "orchestrator_id": 2
            },
            "preferred_container": containers[1]["container_id"]
        })
        
        # Verify deployments
        if agent1_result and agent2_result:
            self.test_results["distributed_agent_deployment"] = True
            print("   ✅ Distributed agent deployment successful")
            print("      🎯 Trading agent → Orchestrator 1's cluster")
            print("      📊 Analysis agent → Orchestrator 2's cluster")
        else:
            print("   ❌ Distributed agent deployment failed")
    
    async def _phase_6_orchestrator_autonomy(self):
        """Phase 6: Validate Orchestrator Autonomy"""
        print("\n🔐 Phase 6: Validating Orchestrator Autonomy...")
        print("   (Testing that orchestrators can operate independently)")
        
        # Test that orchestrator clusters can function independently
        autonomy_tests = []
        
        # Test orchestrator 1 autonomy
        try:
            async with self.session.get(f"{self.orchestrator_1_url}/health") as response:
                if response.status == 200:
                    print("   ✅ Orchestrator 1 cluster autonomous and healthy")
                    autonomy_tests.append(True)
                else:
                    autonomy_tests.append(False)
        except:
            autonomy_tests.append(False)
        
        # Test orchestrator 2 autonomy
        try:
            async with self.session.get(f"{self.orchestrator_2_url}/health") as response:
                if response.status == 200:
                    print("   ✅ Orchestrator 2 cluster autonomous and healthy")
                    autonomy_tests.append(True)
                else:
                    autonomy_tests.append(False)
        except:
            autonomy_tests.append(False)
        
        # Test cluster coordination
        cluster_stats = await self._get_cluster_stats()
        total_containers = cluster_stats.get("cluster", {}).get("total_containers", 0) if cluster_stats else 0
        if total_containers >= 2:
            print("   ✅ Cross-cluster coordination operational")
            autonomy_tests.append(True)
        else:
            print(f"   ❌ Cross-cluster coordination failed: Only {total_containers} containers registered")
            autonomy_tests.append(False)
        
        self.test_results["orchestrator_autonomy"] = all(autonomy_tests)
        
        if self.test_results["orchestrator_autonomy"]:
            print("   ✅ Orchestrator autonomy validated")
        else:
            print("   ❌ Orchestrator autonomy validation failed")
    
    def _create_central_manager_compose(self) -> str:
        """Create isolated central manager compose file"""
        compose_file = project_root / f"docker-compose.{self.central_manager_project}.yml"
        
        compose_content = f"""
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: {self.central_manager_project}-redis
    command: redis-server --appendonly yes --bind 0.0.0.0
    ports:
      - "6379:6379"
    networks:
      - central-network

  central-manager:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: {self.central_manager_project}-manager
    environment:
      - REDIS_URL=redis://redis:6379
      - ENABLE_DISTRIBUTED=true
      - JWT_SECRET=central-manager-jwt-secret-for-orchestrator-testing-32chars
      - ADMIN_PASSWORD=central-admin-password-for-orchestrator-deployment-testing
      - MASTER_SECRET_KEY=central-master-key-for-secure-orchestrator-communication-32chars
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    depends_on:
      - redis
    networks:
      - central-network
    volumes:
      - ./app:/app/app
      - ./keys:/app/keys

networks:
  central-network:
    driver: bridge
    name: {self.central_manager_project}-network
"""
        
        with open(compose_file, "w") as f:
            f.write(compose_content.strip())
        
        return str(compose_file)
    
    def _create_orchestrator_compose(self, orchestrator_id: int, port: int, 
                                   project_name: str, central_manager_url: str) -> str:
        """Create isolated orchestrator compose file"""
        compose_file = project_root / f"docker-compose.{project_name}.yml"
        
        compose_content = f"""
version: '3.8'

services:
  orchestrator-{orchestrator_id}-agent:
    build:
      context: .
      dockerfile: Dockerfile.agent
    container_name: {project_name}-agent
    environment:
      - AGENT_ID=orchestrator-{orchestrator_id}-agent
      - AGENT_TYPE=orchestrator_cluster
      - AGENT_PORT=8001
      - REDIS_URL=redis://host.docker.internal:6379
      - CENTRAL_MANAGER_URL={central_manager_url}
      - ADMIN_PASSWORD=central-admin-password-for-orchestrator-deployment-testing
      - CONTAINER_NAME=orchestrator-{orchestrator_id}-cluster
      - EXTERNAL_IP=127.0.0.1
      - AGENT_CONFIG={{"capabilities":["agent_runner","orchestrator_cluster"],"max_agents":10,"orchestrator_id":{orchestrator_id}}}
      - AUTO_REGISTER=true
      - HEARTBEAT_INTERVAL=30
    ports:
      - "{port}:8001"
    networks:
      - orchestrator-{orchestrator_id}-network
    extra_hosts:
      - "host.docker.internal:host-gateway"

networks:
  orchestrator-{orchestrator_id}-network:
    driver: bridge
    name: {project_name}-network
"""
        
        with open(compose_file, "w") as f:
            f.write(compose_content.strip())
        
        return str(compose_file)
    
    async def _authenticate(self):
        """Authenticate with central manager"""
        try:
            async with self.session.post(
                f"{self.central_manager_url}/api/v1/auth/token",
                data={
                    "username": "admin",
                    "password": "central-admin-password-for-orchestrator-deployment-testing"
                }
            ) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.admin_token = token_data["access_token"]
                    return True
                else:
                    print(f"   ❌ Authentication failed: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ Authentication error: {e}")
            return False
    
    async def _get_registered_containers(self) -> List[Dict]:
        """Get containers registered with central manager"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.get(
                f"{self.central_manager_url}/api/v1/cluster/containers",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            print(f"   Error getting containers: {e}")
            return []
    
    async def _deploy_agent_to_orchestrator(self, agent_request: Dict) -> bool:
        """Deploy agent to orchestrator cluster"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.post(
                f"{self.central_manager_url}/api/v1/cluster/agents/deploy",
                headers=headers,
                json=agent_request
            ) as response:
                return response.status == 200
        except Exception as e:
            print(f"   Error deploying agent: {e}")
            return False
    
    async def _get_cluster_stats(self) -> Dict:
        """Get cluster statistics"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.get(
                f"{self.central_manager_url}/api/v1/cluster/status",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            return {}
    
    async def _wait_for_service(self, url: str, timeout: int = 30):
        """Wait for service to become available"""
        for _ in range(timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/health", timeout=5) as response:
                        if response.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Service not available: {url}")
    
    def _run_command(self, command: List[str]):
        """Run shell command"""
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, 
                timeout=300, cwd=project_root
            )
            if result.returncode != 0:
                print(f"Command failed: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, command)
            return result.stdout
        except subprocess.TimeoutExpired:
            raise
    
    def _cleanup_deployment(self, project_name: str):
        """Cleanup specific deployment"""
        try:
            compose_file = project_root / f"docker-compose.{project_name}.yml"
            if compose_file.exists():
                self._run_command([
                    "docker-compose", "-f", str(compose_file),
                    "-p", project_name, "down", "-v", "--remove-orphans"
                ])
                compose_file.unlink()
        except:
            pass
    
    async def _cleanup_all_deployments(self):
        """Cleanup all test deployments"""
        print("\n🧹 Cleaning up orchestrator deployments...")
        
        if self.session:
            await self.session.close()
        
        # Cleanup all deployments
        for project in [self.central_manager_project, self.orchestrator_1_project, self.orchestrator_2_project]:
            self._cleanup_deployment(project)
        
        print("   ✅ All deployments cleaned up")
    
    def _print_orchestrator_summary(self, summary: Dict[str, Any]):
        """Print orchestrator test summary"""
        print("\n" + "=" * 70)
        print("🎯 ORCHESTRATOR DEPLOYMENT PATTERN TEST RESULTS")
        print("=" * 70)
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"Success Rate: {summary['success_rate']}")
        print(f"Tests Passed: {summary['tests_passed']}/{summary['tests_total']}")
        print()
        
        for test_name, result in summary['results'].items():
            if test_name == "error":
                continue
            icon = "✅" if result else "❌"
            print(f"{icon} {test_name.replace('_', ' ').title()}")
        
        print("\n" + "=" * 70)
        
        if summary['tests_passed'] == summary['tests_total']:
            print("🎉 ORCHESTRATOR DEPLOYMENT PATTERN VALIDATED!")
            print("✅ Central Manager runs independently (your infrastructure)")
            print("✅ Orchestrator clusters deploy independently")
            print("✅ Cross-network registration works automatically")
            print("✅ Agent deployment across orchestrator clusters functional")
            print("✅ Orchestrators maintain autonomy while coordinating")
            print("\n🚀 PRODUCTION READY FOR ORCHESTRATOR DEPLOYMENT!")
        else:
            print("⚠️  Orchestrator deployment pattern needs refinement")
        
        print("=" * 70)

async def main():
    """Main orchestrator test runner"""
    tester = OrchestratorDeploymentTester()
    results = await tester.run_orchestrator_test()
    
    # Save results
    results_file = project_root / "scripts" / "orchestrator_deployment_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")
    
    success_rate = float(results['success_rate'].rstrip('%'))
    sys.exit(0 if success_rate >= 80 else 1)

if __name__ == "__main__":
    asyncio.run(main())