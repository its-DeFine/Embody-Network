#!/usr/bin/env python3
"""
VTuber Orchestrator Monitor
Monitors VTuber orchestrators instead of Livepeer orchestrators
"""

import asyncio
import json
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VTuberOrchestratorMonitor:
    """Monitors VTuber orchestrator health"""
    
    def __init__(self):
        self.manager_url = os.environ.get("MANAGER_URL", "http://central-manager:8000")
        self.admin_email = os.environ.get("ADMIN_EMAIL", "admin@system.com")
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "LivepeerManager2025!Secure")
        self.auth_token = None
        self.orchestrators: List[Dict] = []
        
    async def authenticate(self) -> bool:
        """Authenticate with the manager API"""
        # VTuber orchestrator endpoints don't require authentication for GET requests
        # Only Livepeer endpoints need auth
        logger.info("VTuber orchestrator monitor - authentication not required for read access")
        return True
    
    async def fetch_orchestrators(self) -> List[Dict]:
        """Fetch list of VTuber orchestrators"""
        headers = {}
        if self.auth_token:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with httpx.AsyncClient() as client:
            # Try the VTuber orchestrator endpoint
            endpoints_to_try = [
                f"{self.manager_url}/api/orchestrators",
                f"{self.manager_url}/api/orchestrators/",
                f"{self.manager_url}/api/v1/orchestrators",
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    logger.info(f"Trying endpoint: {endpoint}")
                    response = await client.get(endpoint, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Handle different response formats
                        if isinstance(data, list):
                            self.orchestrators = data
                        elif isinstance(data, dict):
                            self.orchestrators = data.get("orchestrators", data.get("items", []))
                        
                        logger.info(f"✓ Found {len(self.orchestrators)} VTuber orchestrators at {endpoint}")
                        
                        # Log orchestrator details
                        for orch in self.orchestrators:
                            name = orch.get("name", orch.get("orchestrator_name", "unknown"))
                            orch_id = orch.get("id", orch.get("orchestrator_id", "unknown"))
                            url = orch.get("url", orch.get("endpoint", "unknown"))
                            status = orch.get("status", "unknown")
                            logger.info(f"  - {name} (ID: {orch_id}): {status} @ {url}")
                        
                        return self.orchestrators
                    elif response.status_code == 403:
                        logger.warning(f"Access forbidden for {endpoint}")
                    elif response.status_code == 404:
                        logger.debug(f"Endpoint not found: {endpoint}")
                    else:
                        logger.debug(f"Endpoint {endpoint} returned: {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"Error trying {endpoint}: {e}")
            
            # If no VTuber endpoints work, fall back to checking registered orchestrators
            try:
                # Check for orchestrators that have registered
                response = await client.get(f"{self.manager_url}/health", headers=headers)
                if response.status_code == 200:
                    logger.info("Manager is healthy but no VTuber orchestrator endpoint found")
                    logger.info("Orchestrators may be registering at /api/orchestrators/register")
            except:
                pass
                
            logger.warning("Could not fetch VTuber orchestrators from any endpoint")
            return []
    
    async def check_orchestrator_health(self, orchestrator: Dict) -> Dict[str, Any]:
        """Check health of individual VTuber orchestrator"""
        name = orchestrator.get("name", orchestrator.get("orchestrator_name", "unknown"))
        orch_id = orchestrator.get("id", orchestrator.get("orchestrator_id", name))
        endpoint = orchestrator.get("url", orchestrator.get("endpoint", ""))
        
        health = {
            "name": name,
            "orchestrator_id": orch_id,
            "status": "unknown",
            "response_time_ms": 0,
            "last_check": datetime.now().isoformat()
        }
        
        # Try to ping the orchestrator endpoint
        if endpoint and endpoint != "http://host.docker.internal:8082":
            # Skip host.docker.internal as it's not accessible from containers
            if "host.docker.internal" in endpoint:
                logger.warning(f"Orchestrator {name} using host.docker.internal - not accessible from container")
                health["status"] = "unreachable"
                health["error"] = "host.docker.internal not accessible from container"
            else:
                try:
                    start_time = time.time()
                    async with httpx.AsyncClient() as client:
                        # Try health endpoint
                        response = await client.get(
                            f"{endpoint}/health",
                            timeout=5.0
                        )
                        response_time = (time.time() - start_time) * 1000
                        
                        if response.status_code == 200:
                            health["status"] = "healthy"
                            health["response_time_ms"] = round(response_time, 2)
                            logger.info(f"✓ Orchestrator {name}: healthy ({response_time:.0f}ms)")
                        else:
                            health["status"] = "unhealthy"
                            health["error"] = f"HTTP {response.status_code}"
                            logger.warning(f"✗ Orchestrator {name}: unhealthy - HTTP {response.status_code}")
                            
                except httpx.ConnectError as e:
                    health["status"] = "unreachable"
                    health["error"] = str(e)
                    logger.warning(f"✗ Orchestrator {name}: unreachable - {e}")
                except Exception as e:
                    health["status"] = "error"
                    health["error"] = str(e)
                    logger.error(f"✗ Orchestrator {name}: error - {e}")
        else:
            health["status"] = "no_endpoint"
            logger.warning(f"Orchestrator {name} has no valid endpoint")
            
        return health
    
    async def update_orchestrator_status(self, orchestrator_id: str, status: Dict) -> bool:
        """Update orchestrator status in manager"""
        headers = {}
        if self.auth_token:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                # Try to update status
                response = await client.post(
                    f"{self.manager_url}/api/orchestrators/{orchestrator_id}/status",
                    json=status,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    logger.debug(f"Updated status for {orchestrator_id}")
                    return True
                elif response.status_code == 405:
                    logger.debug(f"Status update not supported for {orchestrator_id}")
                    return False
                else:
                    logger.warning(f"Failed to update status for {orchestrator_id}: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"Error updating status for {orchestrator_id}: {e}")
                return False
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("===========================================")
        logger.info("Starting VTuber Orchestrator Monitor")
        logger.info(f"Manager URL: {self.manager_url}")
        logger.info("===========================================")
        
        # Try to authenticate once
        await self.authenticate()
        
        while True:
            try:
                # Fetch orchestrators
                orchestrators = await self.fetch_orchestrators()
                
                if not orchestrators:
                    logger.warning("No VTuber orchestrators found - checking for registrations...")
                    
                    # Check recent registrations in logs (would need actual DB access for this)
                    logger.info("Orchestrators may be registering at /api/orchestrators/register")
                    logger.info("Check Central Manager logs for registration activity")
                else:
                    # Check health of each orchestrator
                    for orch in orchestrators:
                        health = await self.check_orchestrator_health(orch)
                        
                        # Try to update status
                        orch_id = orch.get("id", orch.get("orchestrator_id", orch.get("name")))
                        if orch_id:
                            await self.update_orchestrator_status(orch_id, health)
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(10)


async def main():
    monitor = VTuberOrchestratorMonitor()
    await monitor.monitor_loop()


if __name__ == "__main__":
    asyncio.run(main())