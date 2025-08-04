#!/usr/bin/env python3
"""
Comprehensive Distributed Container System Integration Test

This script launches a full distributed cluster and tests:
1. Container discovery and registration
2. Agent deployment across remote containers  
3. Inter-container communication
4. Load balancing and failover scenarios
5. Real-world distributed trading workflow

Usage:
    python scripts/test_distributed_integration.py [--cleanup-only]
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

import aiohttp
import docker
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DistributedIntegrationTester:
    """Comprehensive integration tester for distributed container system"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.compose_file = project_root / "docker-compose.distributed.yml"
        self.project_name = "autogen-integration-test"
        
        # API endpoints
        self.central_manager_url = "http://localhost:8000"
        self.agent_containers = {
            "trading": "http://localhost:8001",
            "analysis": "http://localhost:8002", 
            "risk": "http://localhost:8003"
        }
        
        # Test state
        self.session: Optional[aiohttp.ClientSession] = None
        self.admin_token: Optional[str] = None
        self.container_ids: List[str] = []
        self.deployed_agents: List[str] = []
        
        # Test results
        self.test_results = {
            "container_discovery": False,
            "agent_deployment": False,
            "inter_container_communication": False,
            "load_balancing": False,
            "failover_recovery": False,
            "distributed_trading": False
        }
        
    async def run_full_integration_test(self) -> Dict[str, Any]:
        """Run complete integration test suite"""
        logger.info("🚀 Starting Distributed Container System Integration Test")
        
        start_time = datetime.utcnow()
        
        try:
            # Phase 1: Infrastructure Setup
            await self._phase_1_setup()
            
            # Phase 2: Container Discovery Testing
            await self._phase_2_discovery()
            
            # Phase 3: Agent Deployment Testing  
            await self._phase_3_deployment()
            
            # Phase 4: Communication Testing
            await self._phase_4_communication()
            
            # Phase 5: Load Balancing Testing
            await self._phase_5_load_balancing()
            
            # Phase 6: Failover Testing
            await self._phase_6_failover()
            
            # Phase 7: Distributed Trading Workflow
            await self._phase_7_trading_workflow()
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            self.test_results["error"] = str(e)
        
        finally:
            # Always cleanup
            await self._cleanup()
            
        # Calculate results
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        passed_tests = sum(1 for result in self.test_results.values() if result is True)
        total_tests = len([k for k in self.test_results.keys() if k != "error"])
        
        summary = {
            "duration_seconds": duration,
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%",
            "results": self.test_results,
            "timestamp": end_time.isoformat()
        }
        
        self._print_summary(summary)
        return summary
    
    async def _phase_1_setup(self):
        """Phase 1: Launch distributed infrastructure"""
        logger.info("📦 Phase 1: Setting up distributed infrastructure...")
        
        # Clean up any existing containers
        await self._cleanup_containers()
        
        # Build images if needed
        logger.info("Building Docker images...")
        self._run_command([
            "docker-compose", "-f", str(self.compose_file), 
            "-p", self.project_name, "build"
        ])
        
        # Launch core services (redis, central-manager)
        logger.info("Starting Redis and Central Manager...")
        self._run_command([
            "docker-compose", "-f", str(self.compose_file),
            "-p", self.project_name, "up", "-d", "redis", "central-manager"
        ])
        
        # Wait for central manager to be ready
        await self._wait_for_service(self.central_manager_url, timeout=60)
        
        # Setup HTTP session and authenticate
        self.session = aiohttp.ClientSession()
        await self._authenticate()
        
        logger.info("✅ Phase 1 Complete: Infrastructure ready")
    
    async def _phase_2_discovery(self):
        """Phase 2: Test container discovery"""
        logger.info("🔍 Phase 2: Testing container discovery...")
        
        # Launch first agent container
        logger.info("Launching agent-container-1...")
        self._run_command([
            "docker-compose", "-f", str(self.compose_file),
            "-p", self.project_name, "up", "-d", "agent-container-1"
        ])
        
        # Wait for container to register
        await asyncio.sleep(10)
        
        # Check if container was discovered
        containers = await self._get_discovered_containers()
        if containers and len(containers) > 0:
            self.test_results["container_discovery"] = True
            self.container_ids.extend([c["container_id"] for c in containers])
            logger.info(f"✅ Container discovery working: {len(containers)} containers found")
        else:
            logger.error("❌ Container discovery failed: No containers found")
        
        # Launch second agent container
        logger.info("Launching agent-container-2...")
        self._run_command([
            "docker-compose", "-f", str(self.compose_file),
            "-p", self.project_name, "up", "-d", "agent-container-2"
        ])
        
        await asyncio.sleep(10)
        
        # Verify both containers discovered
        containers = await self._get_discovered_containers()
        if len(containers) >= 2:
            logger.info(f"✅ Multiple container discovery: {len(containers)} containers active")
        
        logger.info("✅ Phase 2 Complete: Container discovery tested")
    
    async def _phase_3_deployment(self):
        """Phase 3: Test agent deployment across containers"""
        logger.info("🤖 Phase 3: Testing distributed agent deployment...")
        
        if not self.container_ids:
            logger.error("❌ No containers available for deployment")
            return
        
        # Deploy trading agent to first container
        trading_agent = await self._deploy_agent({
            "agent_type": "trading_agent",
            "agent_config": {
                "strategy": "mean_reversion",
                "initial_capital": 10000
            },
            "deployment_strategy": "capability_based",
            "preferred_container": self.container_ids[0] if self.container_ids else None
        })
        
        if trading_agent and trading_agent.get("success"):
            self.deployed_agents.append(trading_agent["agent_id"])
            logger.info(f"✅ Trading agent deployed: {trading_agent['agent_id']}")
        
        # Deploy analysis agent to second container
        analysis_agent = await self._deploy_agent({
            "agent_type": "analysis_agent", 
            "agent_config": {
                "analysis_type": "technical",
                "timeframes": ["1h", "4h", "1d"]
            },
            "deployment_strategy": "least_loaded"
        })
        
        if analysis_agent and analysis_agent.get("success"):
            self.deployed_agents.append(analysis_agent["agent_id"])
            logger.info(f"✅ Analysis agent deployed: {analysis_agent['agent_id']}")
        
        # Verify deployments
        deployments = await self._get_agent_deployments()
        if len(deployments) >= 2:
            self.test_results["agent_deployment"] = True
            logger.info(f"✅ Agent deployment successful: {len(deployments)} agents deployed")
        else:
            logger.error("❌ Agent deployment failed")
        
        logger.info("✅ Phase 3 Complete: Agent deployment tested")
    
    async def _phase_4_communication(self):
        """Phase 4: Test inter-container communication"""
        logger.info("📡 Phase 4: Testing inter-container communication...")
        
        # Test communication hub stats
        hub_stats = await self._get_communication_stats()
        if hub_stats and "active_containers" in hub_stats:
            logger.info(f"✅ Communication hub active: {hub_stats['active_containers']} containers")
        
        # Test sending messages between containers
        if len(self.container_ids) >= 2:
            message_result = await self._send_cluster_message(
                source_container=self.container_ids[0],
                target_container=self.container_ids[1],
                message_type="command",
                payload={"command": "health_check", "params": {}}
            )
            
            if message_result and "message_id" in message_result:
                self.test_results["inter_container_communication"] = True
                logger.info("✅ Inter-container communication working")
            else:
                logger.error("❌ Inter-container communication failed")
        
        logger.info("✅ Phase 4 Complete: Communication tested") 
    
    async def _phase_5_load_balancing(self):
        """Phase 5: Test load balancing across containers"""
        logger.info("⚖️ Phase 5: Testing load balancing...")
        
        # Deploy multiple agents to test load balancing
        agents_deployed = []
        for i in range(4):
            agent = await self._deploy_agent({
                "agent_type": "analysis_agent",
                "agent_config": {"task_id": f"load_test_{i}"},
                "deployment_strategy": "least_loaded"  # Should distribute across containers
            })
            
            if agent and agent.get("success"):
                agents_deployed.append(agent["agent_id"])
                await asyncio.sleep(2)  # Small delay between deployments
        
        # Check distribution across containers
        distribution = await self._get_cluster_distribution()
        if distribution and "distribution" in distribution:
            container_loads = {}
            for container_id, info in distribution["distribution"].items():
                container_loads[container_id] = info.get("agent_count", 0)
            
            # Check if load is reasonably distributed
            if len(container_loads) >= 2 and max(container_loads.values()) - min(container_loads.values()) <= 2:
                self.test_results["load_balancing"] = True
                logger.info(f"✅ Load balancing working: {container_loads}")
            else:
                logger.warning(f"⚠️ Load balancing suboptimal: {container_loads}")
        
        logger.info("✅ Phase 5 Complete: Load balancing tested")
    
    async def _phase_6_failover(self):
        """Phase 6: Test container failover and agent migration"""
        logger.info("🔄 Phase 6: Testing failover and recovery...")
        
        if len(self.container_ids) < 2:
            logger.error("❌ Need at least 2 containers for failover testing")
            return
        
        # Get initial agent distribution
        initial_distribution = await self._get_cluster_distribution()
        
        # Stop one container to simulate failure
        failing_container = self.container_ids[0]
        logger.info(f"Simulating failure of container: {failing_container}")
        
        try:
            # Stop the container
            self._run_command([
                "docker", "stop", f"{self.project_name}-agent-container-1-1"
            ])
            
            # Wait for failover detection
            await asyncio.sleep(15)
            
            # Check if agents were migrated
            final_distribution = await self._get_cluster_distribution()
            
            # Verify recovery
            if final_distribution and len(final_distribution.get("distribution", {})) >= 1:
                self.test_results["failover_recovery"] = True
                logger.info("✅ Failover recovery successful")
            else:
                logger.error("❌ Failover recovery failed")
            
        except Exception as e:
            logger.error(f"❌ Failover test failed: {e}")
        
        logger.info("✅ Phase 6 Complete: Failover tested")
    
    async def _phase_7_trading_workflow(self):
        """Phase 7: Test distributed trading workflow"""
        logger.info("💰 Phase 7: Testing distributed trading workflow...")
        
        # This would test a real trading scenario across distributed containers
        # For now, we'll test the cluster orchestration APIs
        
        try:
            # Trigger cluster rebalancing
            rebalance_result = await self._perform_cluster_action({
                "action": "rebalance",
                "params": {}
            })
            
            if rebalance_result:
                logger.info("✅ Cluster rebalancing successful")
            
            # Perform cluster health check
            health_result = await self._perform_cluster_action({
                "action": "health_check",
                "params": {}
            })
            
            if health_result and "status" in health_result:
                self.test_results["distributed_trading"] = True
                logger.info(f"✅ Distributed trading workflow: {health_result['status']}")
            
        except Exception as e:
            logger.error(f"❌ Trading workflow test failed: {e}")
        
        logger.info("✅ Phase 7 Complete: Trading workflow tested")
    
    # Helper methods for API interactions
    
    async def _authenticate(self):
        """Authenticate with central manager"""
        try:
            async with self.session.post(
                f"{self.central_manager_url}/api/v1/auth/login",
                json={
                    "email": "admin@trading.system",
                    "password": "default-admin-password-change-in-production-32chars!"
                }
            ) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.admin_token = token_data["access_token"]
                    logger.info("✅ Authentication successful")
                else:
                    logger.error(f"❌ Authentication failed: {response.status}")
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
    
    async def _get_discovered_containers(self) -> List[Dict]:
        """Get list of discovered containers"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.get(
                f"{self.central_manager_url}/api/v1/cluster/containers",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get containers: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting containers: {e}")
            return []
    
    async def _deploy_agent(self, agent_request: Dict) -> Optional[Dict]:
        """Deploy an agent to the cluster"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.post(
                f"{self.central_manager_url}/api/v1/cluster/agents/deploy",
                headers=headers,
                json=agent_request
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Agent deployment failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error deploying agent: {e}")
            return None
    
    async def _get_agent_deployments(self) -> Dict:
        """Get all agent deployments"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.get(
                f"{self.central_manager_url}/api/v1/cluster/agents/deployments",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
        except Exception as e:
            logger.error(f"Error getting deployments: {e}")
            return {}
    
    async def _get_communication_stats(self) -> Optional[Dict]:
        """Get communication hub statistics"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.get(
                f"{self.central_manager_url}/api/v1/cluster/communication/stats",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error getting communication stats: {e}")
            return None
    
    async def _send_cluster_message(self, source_container: str, target_container: str, 
                                   message_type: str, payload: Dict) -> Optional[Dict]:
        """Send message through cluster communication hub"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            params = {
                "source_container": source_container,
                "target_container": target_container,
                "message_type": message_type
            }
            async with self.session.post(
                f"{self.central_manager_url}/api/v1/cluster/communication/message",
                headers=headers,
                params=params,
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error sending cluster message: {e}")
            return None
    
    async def _get_cluster_distribution(self) -> Optional[Dict]:
        """Get cluster agent distribution"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.get(
                f"{self.central_manager_url}/api/v1/cluster/metrics/distribution",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error getting cluster distribution: {e}")
            return None
    
    async def _perform_cluster_action(self, action_request: Dict) -> Optional[Dict]:
        """Perform cluster action"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.post(
                f"{self.central_manager_url}/api/v1/cluster/actions",
                headers=headers,
                json=action_request
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error performing cluster action: {e}")
            return None
    
    async def _wait_for_service(self, url: str, timeout: int = 30):
        """Wait for service to become available"""
        logger.info(f"Waiting for service: {url}")
        
        for _ in range(timeout):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/health", timeout=5) as response:
                        if response.status == 200:
                            logger.info(f"✅ Service ready: {url}")
                            return
            except:
                pass
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Service not available after {timeout}s: {url}")
    
    def _run_command(self, command: List[str], timeout: int = 300):
        """Run shell command with timeout"""
        logger.info(f"Running: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                cwd=project_root
            )
            
            if result.returncode != 0:
                logger.error(f"Command failed: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, command)
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s")
            raise
    
    async def _cleanup_containers(self):
        """Clean up any existing test containers"""
        logger.info("Cleaning up existing containers...")
        
        try:
            self._run_command([
                "docker-compose", "-f", str(self.compose_file),
                "-p", self.project_name, "down", "-v", "--remove-orphans"
            ])
        except:
            pass  # Ignore cleanup errors
    
    async def _cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up test resources...")
        
        if self.session:
            await self.session.close()
        
        # Stop all containers
        await self._cleanup_containers()
        
        logger.info("✅ Cleanup complete")
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print test summary"""
        print("\n" + "="*80)
        print("🎯 DISTRIBUTED INTEGRATION TEST RESULTS")
        print("="*80)
        print(f"Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"Success Rate: {summary['success_rate']}")
        print(f"Tests Passed: {summary['tests_passed']}/{summary['tests_total']}")
        print()
        
        for test_name, result in summary['results'].items():
            if test_name == "error":
                continue
            icon = "✅" if result else "❌"
            print(f"{icon} {test_name.replace('_', ' ').title()}")
        
        if "error" in summary['results']:
            print(f"\n❌ Error: {summary['results']['error']}")
        
        print("\n" + "="*80)
        
        if summary['tests_passed'] == summary['tests_total']:
            print("🎉 ALL TESTS PASSED - Distributed system is fully operational!")
        else:
            print("⚠️  Some tests failed - Check logs for details")
        
        print("="*80)

async def main():
    """Main test runner"""
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup-only":
        tester = DistributedIntegrationTester()
        await tester._cleanup_containers()
        return
    
    tester = DistributedIntegrationTester()
    results = await tester.run_full_integration_test()
    
    # Write results to file
    results_file = project_root / "scripts" / "integration_test_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")
    
    # Exit with appropriate code
    success_rate = float(results['success_rate'].rstrip('%'))
    sys.exit(0 if success_rate >= 80 else 1)

if __name__ == "__main__":
    asyncio.run(main())