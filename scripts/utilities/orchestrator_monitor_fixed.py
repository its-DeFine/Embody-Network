#!/usr/bin/env python3
"""
Fixed Orchestrator Monitor for Livepeer Pipeline
Properly authenticates with the manager before monitoring
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


class OrchestratorMonitor:
    """Monitors orchestrator health with proper authentication"""
    
    def __init__(self):
        self.manager_url = os.environ.get("MANAGER_URL", "http://central-manager:8000")
        self.admin_email = os.environ.get("ADMIN_EMAIL", "admin@system.com")
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "LivepeerManager2025!Secure")
        self.auth_token = None
        self.orchestrators: List[Dict] = []
        
    async def authenticate(self) -> bool:
        """Authenticate with the manager API"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.manager_url}/api/v1/auth/login",
                    json={"email": self.admin_email, "password": self.admin_password}
                )
                
                if response.status_code == 200:
                    self.auth_token = response.json()["access_token"]
                    logger.info("Authentication successful")
                    return True
                else:
                    logger.error(f"Authentication failed: {response.status_code}")
                    if response.status_code == 404:
                        logger.error("Auth endpoint not found - manager may not be fully initialized")
                    return False
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return False
    
    async def fetch_orchestrators(self) -> List[Dict]:
        """Fetch list of connected orchestrators from manager"""
        if not self.auth_token:
            if not await self.authenticate():
                return []
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.manager_url}/api/v1/livepeer/orchestrators",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    self.orchestrators = data.get("orchestrators", [])
                    logger.info(f"Fetched {len(self.orchestrators)} orchestrators")
                    return self.orchestrators
                elif response.status_code == 401:
                    # Token expired, re-authenticate
                    logger.info("Token expired, re-authenticating...")
                    self.auth_token = None
                    if await self.authenticate():
                        return await self.fetch_orchestrators()
                    return []
                else:
                    logger.error(f"Failed to fetch orchestrators: {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Error fetching orchestrators: {e}")
                return []
    
    async def check_orchestrator_health(self, orchestrator: Dict) -> Dict[str, Any]:
        """Check health of individual orchestrator"""
        orch_id = orchestrator.get("orchestrator_id")
        endpoint = orchestrator.get("endpoint", "")
        
        health = {
            "orchestrator_id": orch_id,
            "status": "unknown",
            "response_time_ms": 0,
            "last_check": datetime.now().isoformat()
        }
        
        # Try to ping the orchestrator endpoint
        if endpoint:
            try:
                start_time = time.time()
                async with httpx.AsyncClient(timeout=5.0) as client:
                    # Remove https and add http
                    test_endpoint = endpoint.replace("https://", "http://").rstrip("/") + "/status"
                    response = await client.get(test_endpoint, follow_redirects=True)
                    
                    response_time = (time.time() - start_time) * 1000
                    health["response_time_ms"] = response_time
                    
                    if response.status_code == 200:
                        health["status"] = "healthy"
                    else:
                        health["status"] = "unhealthy"
                        health["error"] = f"HTTP {response.status_code}"
            except Exception as e:
                health["status"] = "unreachable"
                health["error"] = str(e)
        
        return health
    
    async def update_orchestrator_status(self, health_data: Dict):
        """Update orchestrator status in manager"""
        if not self.auth_token:
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                # Try to update status via API
                response = await client.post(
                    f"{self.manager_url}/api/v1/livepeer/orchestrators/{health_data['orchestrator_id']}/status",
                    headers=headers,
                    json={"status": health_data["status"], "health": health_data}
                )
                
                if response.status_code == 200:
                    logger.debug(f"Updated status for {health_data['orchestrator_id']}")
                elif response.status_code == 404:
                    # Endpoint might not exist, that's okay
                    pass
                else:
                    logger.warning(f"Failed to update status: {response.status_code}")
            except Exception as e:
                logger.debug(f"Could not update status: {e}")
    
    async def monitor_health_cycle(self):
        """Single monitoring cycle"""
        orchestrators = await self.fetch_orchestrators()
        
        if not orchestrators:
            logger.warning("No orchestrators to monitor")
            return
        
        # Check health of each orchestrator
        health_tasks = []
        for orch in orchestrators:
            health_tasks.append(self.check_orchestrator_health(orch))
        
        health_results = await asyncio.gather(*health_tasks)
        
        # Update statuses
        update_tasks = []
        for health in health_results:
            update_tasks.append(self.update_orchestrator_status(health))
        
        await asyncio.gather(*update_tasks)
        
        # Log summary
        healthy = sum(1 for h in health_results if h["status"] == "healthy")
        unhealthy = sum(1 for h in health_results if h["status"] == "unhealthy")
        unreachable = sum(1 for h in health_results if h["status"] == "unreachable")
        
        logger.info(
            f"Health Status - Total: {len(orchestrators)}, "
            f"Healthy: {healthy}, Unhealthy: {unhealthy}, Unreachable: {unreachable}"
        )
        
        # Log details for problematic orchestrators
        for health in health_results:
            if health["status"] != "healthy":
                logger.warning(
                    f"Orchestrator {health['orchestrator_id']}: "
                    f"{health['status']} - {health.get('error', 'Unknown error')}"
                )
    
    async def monitor_loop(self, interval: int = 30):
        """Main monitoring loop"""
        logger.info(f"Starting orchestrator health monitoring (interval: {interval}s)")
        logger.info(f"Manager URL: {self.manager_url}")
        
        # Initial authentication
        if not await self.authenticate():
            logger.error("Initial authentication failed - will retry in loop")
        
        while True:
            try:
                await self.monitor_health_cycle()
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
            
            await asyncio.sleep(interval)


async def main():
    """Main entry point"""
    monitor = OrchestratorMonitor()
    
    # Get interval from environment or use default
    interval = int(os.environ.get("CHECK_INTERVAL", "30"))
    
    try:
        await monitor.monitor_loop(interval)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())