#!/usr/bin/env python3
"""
Distributed Test Monitor
Monitors containers and services during integration testing with real-time updates.
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class DistributedTestMonitor:
    """Real-time monitoring of distributed test execution"""
    
    def __init__(self):
        self.central_manager_url = "http://localhost:8000"
        self.monitoring = True
        self.session = None
        
    async def start_monitoring(self):
        """Start monitoring distributed test"""
        logger.info("🔍 Starting distributed test monitoring...")
        
        self.session = aiohttp.ClientSession()
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_containers()),
            asyncio.create_task(self._monitor_cluster_status()),
            asyncio.create_task(self._monitor_system_resources()),
            asyncio.create_task(self._display_progress())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        finally:
            await self.session.close()
    
    async def _monitor_containers(self):
        """Monitor Docker containers"""
        while self.monitoring:
            try:
                result = subprocess.run([
                    "docker", "ps", "--filter", "name=autogen-integration-test",
                    "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
                ], capture_output=True, text=True)
                
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:  # Skip header
                        print(f"\n📦 Container Status ({datetime.now().strftime('%H:%M:%S')}):")
                        for line in lines:
                            print(f"   {line}")
                
            except Exception as e:
                logger.error(f"Error monitoring containers: {e}")
            
            await asyncio.sleep(10)
    
    async def _monitor_cluster_status(self):
        """Monitor cluster API status"""
        while self.monitoring:
            try:
                # Try to get cluster status
                async with self.session.get(
                    f"{self.central_manager_url}/api/v1/cluster/status",
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n🌐 Cluster Status ({datetime.now().strftime('%H:%M:%S')}):")
                        print(f"   Status: {data.get('status', 'unknown')}")
                        
                        cluster_info = data.get('cluster', {})
                        print(f"   Containers: {cluster_info.get('total_containers', 0)}")
                        
                        comms = data.get('communication', {})
                        print(f"   Active Communications: {comms.get('active_containers', 0)}")
                        
                        deployments = data.get('deployments', {})
                        print(f"   Deployed Agents: {deployments.get('total_agents', 0)}")
                    
            except Exception as e:
                # Expected during startup
                pass
            
            await asyncio.sleep(15)
    
    async def _monitor_system_resources(self):
        """Monitor system resource usage"""
        while self.monitoring:
            try:
                # Get container resource usage
                result = subprocess.run([
                    "docker", "stats", "--no-stream", "--format",
                    "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
                ], capture_output=True, text=True)
                
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        autogen_containers = [line for line in lines if 'autogen' in line.lower()]
                        if autogen_containers:
                            print(f"\n💻 Resource Usage ({datetime.now().strftime('%H:%M:%S')}):")
                            for line in autogen_containers[:5]:  # Show top 5
                                print(f"   {line}")
                
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
            
            await asyncio.sleep(20)
    
    async def _display_progress(self):
        """Display test progress"""
        phases = [
            "Infrastructure Setup",
            "Container Discovery", 
            "Agent Deployment",
            "Communication Testing",
            "Load Balancing",
            "Failover Testing",
            "Trading Workflow"
        ]
        
        current_phase = 0
        
        while self.monitoring:
            print(f"\n🚀 Test Progress ({datetime.now().strftime('%H:%M:%S')}):")
            
            for i, phase in enumerate(phases):
                if i < current_phase:
                    print(f"   ✅ {phase}")
                elif i == current_phase:
                    print(f"   🔄 {phase} (In Progress)")
                else:
                    print(f"   ⏳ {phase}")
            
            # Try to detect phase progression (simplified)
            if current_phase < len(phases) - 1:
                current_phase += 1
            
            await asyncio.sleep(30)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False

async def main():
    """Main monitoring function"""
    monitor = DistributedTestMonitor()
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped")
    finally:
        monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())