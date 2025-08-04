#!/usr/bin/env python3
"""
Cross-Network Communication Test
Tests container communication across different physical machines and networks.
"""

import asyncio
import json
import socket
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

# Configuration - Update these with your actual network setup
NETWORK_CONFIG = {
    "redis_host": "10.0.1.100",
    "redis_port": 6379,
    "central_manager": {
        "host": "10.0.1.200", 
        "port": 8000,
        "url": "http://10.0.1.200:8000"
    },
    "agent_nodes": [
        {"host": "10.0.1.201", "port": 8001, "type": "trading"},
        {"host": "10.0.1.202", "port": 8001, "type": "analysis"}, 
        {"host": "10.0.1.203", "port": 8001, "type": "risk"}
    ]
}

class CrossNetworkTester:
    """Test distributed container communication across networks"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results = {}
        
    async def run_tests(self) -> Dict:
        """Run comprehensive cross-network tests"""
        print("🌐 Cross-Network Communication Test Suite")
        print("=" * 60)
        
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        
        try:
            # Test 1: Basic Network Connectivity
            await self._test_basic_connectivity()
            
            # Test 2: Redis Connectivity  
            await self._test_redis_connectivity()
            
            # Test 3: Central Manager API
            await self._test_central_manager_api()
            
            # Test 4: Agent Node APIs
            await self._test_agent_node_apis()
            
            # Test 5: Container Registration
            await self._test_container_registration()
            
            # Test 6: Inter-Container Communication
            await self._test_inter_container_communication()
            
        finally:
            await self.session.close()
            
        self._print_summary()
        return self.test_results
    
    async def _test_basic_connectivity(self):
        """Test basic TCP connectivity to all endpoints"""
        print("\n🔌 Testing Basic Network Connectivity...")
        
        tests = [
            ("Redis", NETWORK_CONFIG["redis_host"], NETWORK_CONFIG["redis_port"]),
            ("Central Manager", NETWORK_CONFIG["central_manager"]["host"], 
             NETWORK_CONFIG["central_manager"]["port"])
        ]
        
        for node in NETWORK_CONFIG["agent_nodes"]:
            tests.append((f"Agent {node['type']}", node["host"], node["port"]))
        
        connectivity_results = []
        
        for name, host, port in tests:
            try:
                # Test TCP connection
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=5
                )
                writer.close()
                await writer.wait_closed()
                
                print(f"  ✅ {name} ({host}:{port}) - TCP connection successful")
                connectivity_results.append(True)
                
            except Exception as e:
                print(f"  ❌ {name} ({host}:{port}) - Connection failed: {e}")
                connectivity_results.append(False)
        
        self.test_results["basic_connectivity"] = {
            "passed": sum(connectivity_results),
            "total": len(connectivity_results),
            "success_rate": f"{(sum(connectivity_results)/len(connectivity_results))*100:.1f}%"
        }
    
    async def _test_redis_connectivity(self):
        """Test Redis connectivity and basic operations"""
        print("\n💾 Testing Redis Connectivity...")
        
        try:
            import redis.asyncio as aioredis
            
            redis_url = f"redis://{NETWORK_CONFIG['redis_host']}:{NETWORK_CONFIG['redis_port']}"
            redis_client = await aioredis.from_url(redis_url)
            
            # Test ping
            await redis_client.ping()
            print("  ✅ Redis ping successful")
            
            # Test set/get
            test_key = "cross_network_test"
            test_value = f"test_{int(time.time())}"
            
            await redis_client.set(test_key, test_value)
            retrieved_value = await redis_client.get(test_key)
            
            if retrieved_value.decode() == test_value:
                print("  ✅ Redis set/get operations successful")
                redis_success = True
            else:
                print("  ❌ Redis set/get mismatch")
                redis_success = False
            
            # Cleanup
            await redis_client.delete(test_key)
            await redis_client.close()
            
        except Exception as e:
            print(f"  ❌ Redis connectivity failed: {e}")
            redis_success = False
        
        self.test_results["redis_connectivity"] = redis_success
    
    async def _test_central_manager_api(self):
        """Test Central Manager API endpoints"""
        print("\n🎯 Testing Central Manager API...")
        
        base_url = NETWORK_CONFIG["central_manager"]["url"]
        
        endpoints = [
            ("/health", "Health check"),
            ("/api/v1/cluster/status", "Cluster status"),
            ("/api/v1/cluster/containers", "Container list"),
            ("/api/v1/cluster/discovery/status", "Discovery status")
        ]
        
        api_results = []
        
        for endpoint, description in endpoints:
            try:
                async with self.session.get(f"{base_url}{endpoint}") as response:
                    if response.status in [200, 401]:  # 401 is expected for auth-required endpoints
                        print(f"  ✅ {description} - API responding (status: {response.status})")
                        api_results.append(True)
                    else:
                        print(f"  ⚠️  {description} - Unexpected status: {response.status}")
                        api_results.append(False)
                        
            except Exception as e:
                print(f"  ❌ {description} - Request failed: {e}")
                api_results.append(False)
        
        self.test_results["central_manager_api"] = {
            "passed": sum(api_results),
            "total": len(api_results),
            "success_rate": f"{(sum(api_results)/len(api_results))*100:.1f}%"
        }
    
    async def _test_agent_node_apis(self):
        """Test Agent Node API endpoints"""
        print("\n🤖 Testing Agent Node APIs...")
        
        node_results = []
        
        for node in NETWORK_CONFIG["agent_nodes"]:
            node_url = f"http://{node['host']}:{node['port']}"
            node_name = f"{node['type']} agent"
            
            endpoints = [
                ("/health", "Health check"),
                ("/status", "Status check")
            ]
            
            node_success = []
            
            for endpoint, description in endpoints:
                try:
                    async with self.session.get(f"{node_url}{endpoint}") as response:
                        if response.status == 200:
                            print(f"  ✅ {node_name} {description} - OK")
                            node_success.append(True)
                        else:
                            print(f"  ⚠️  {node_name} {description} - Status: {response.status}")
                            node_success.append(False)
                            
                except Exception as e:
                    print(f"  ❌ {node_name} {description} - Failed: {e}")
                    node_success.append(False)
            
            node_results.append(sum(node_success) / len(node_success))
        
        self.test_results["agent_node_apis"] = {
            "nodes_tested": len(node_results),
            "average_success_rate": f"{(sum(node_results)/len(node_results))*100:.1f}%" if node_results else "0%"
        }
    
    async def _test_container_registration(self):
        """Test container registration with central manager"""
        print("\n📝 Testing Container Registration...")
        
        # This would require authentication, so we'll test the endpoint availability
        registration_url = f"{NETWORK_CONFIG['central_manager']['url']}/api/v1/cluster/containers/register"
        
        try:
            test_registration = {
                "container_name": "test-cross-network",
                "host_address": "127.0.0.1",  # Dummy data for test
                "api_port": 9999,
                "capabilities": ["test"],
                "resources": {"cpu": 1, "memory": "1G"}
            }
            
            async with self.session.post(registration_url, json=test_registration) as response:
                if response.status in [200, 401, 422]:  # Expected responses
                    print(f"  ✅ Registration endpoint responding (status: {response.status})")
                    registration_success = True
                else:
                    print(f"  ⚠️  Registration endpoint unexpected status: {response.status}")
                    registration_success = False
                    
        except Exception as e:
            print(f"  ❌ Registration endpoint failed: {e}")
            registration_success = False
        
        self.test_results["container_registration"] = registration_success
    
    async def _test_inter_container_communication(self):
        """Test communication between containers via central manager"""
        print("\n📡 Testing Inter-Container Communication...")
        
        # Test communication hub endpoint
        comm_url = f"{NETWORK_CONFIG['central_manager']['url']}/api/v1/cluster/communication/stats"
        
        try:
            async with self.session.get(comm_url) as response:
                if response.status in [200, 401]:
                    print(f"  ✅ Communication hub responding (status: {response.status})")
                    
                    if response.status == 200:
                        data = await response.json()
                        active_containers = data.get("active_containers", 0)
                        print(f"  ℹ️  Active containers in communication hub: {active_containers}")
                    
                    comm_success = True
                else:
                    print(f"  ⚠️  Communication hub unexpected status: {response.status}")
                    comm_success = False
                    
        except Exception as e:
            print(f"  ❌ Communication hub failed: {e}")
            comm_success = False
        
        self.test_results["inter_container_communication"] = comm_success
    
    def _print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 CROSS-NETWORK TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in self.test_results.items():
            if isinstance(result, bool):
                total_tests += 1
                if result:
                    passed_tests += 1
                    print(f"✅ {test_name.replace('_', ' ').title()}: PASSED")
                else:
                    print(f"❌ {test_name.replace('_', ' ').title()}: FAILED")
                    
            elif isinstance(result, dict):
                if "passed" in result and "total" in result:
                    total_tests += result["total"]  
                    passed_tests += result["passed"]
                    print(f"📈 {test_name.replace('_', ' ').title()}: {result['passed']}/{result['total']} ({result.get('success_rate', 'N/A')})")
                else:
                    print(f"ℹ️  {test_name.replace('_', ' ').title()}: {result}")
        
        if total_tests > 0:
            overall_success_rate = (passed_tests / total_tests) * 100
            print(f"\n🎯 OVERALL SUCCESS RATE: {passed_tests}/{total_tests} ({overall_success_rate:.1f}%)")
            
            if overall_success_rate >= 80:
                print("🎉 EXCELLENT! Cross-network communication is working well")
            elif overall_success_rate >= 60:
                print("⚠️  GOOD! Most components working, some issues to address")
            else:
                print("❌ POOR! Significant network connectivity issues detected")
        
        print("\n📋 RECOMMENDATIONS:")
        
        if not self.test_results.get("basic_connectivity", {}).get("passed", 0):
            print("• Check firewall rules and network connectivity")
            print("• Ensure all required ports are open (6379, 8000, 8001)")
            
        if not self.test_results.get("redis_connectivity", False):
            print("• Verify Redis is running and accessible")
            print("• Check Redis configuration allows external connections")
            
        if self.test_results.get("central_manager_api", {}).get("passed", 0) == 0:
            print("• Verify Central Manager container is running")
            print("• Check Central Manager logs for errors")
            
        print("\n" + "=" * 60)

async def main():
    """Main test runner"""
    if len(sys.argv) > 1 and sys.argv[1] == "--config":
        print("Current network configuration:")
        print(json.dumps(NETWORK_CONFIG, indent=2))
        return
    
    print("Starting cross-network communication tests...")
    print("Edit the NETWORK_CONFIG in this script to match your setup")
    print()
    
    tester = CrossNetworkTester()
    results = await tester.run_tests()
    
    # Save results to file
    results_file = Path(__file__).parent / "cross_network_test_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())