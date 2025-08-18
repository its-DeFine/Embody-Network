#!/usr/bin/env python3
"""
Containerized Payment Distributor Service for Livepeer Orchestrators
Monitors orchestrator uptime and distributes payments per minute
"""

import asyncio
import httpx
import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaymentDistributor:
    """Automated payment distribution service for orchestrators"""
    
    def __init__(self):
        # Configuration from environment
        self.manager_url = os.environ.get("MANAGER_URL", "http://central-manager:8000")
        self.admin_email = os.environ.get("ADMIN_EMAIL", "admin@system.com")
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "LivepeerManager2025!Secure")
        
        # Payment configuration
        self.payment_interval = int(os.environ.get("PAYMENT_INTERVAL_SECONDS", "60"))
        self.payment_amount = float(os.environ.get("PAYMENT_AMOUNT", "10.0"))
        self.min_uptime_threshold = float(os.environ.get("MIN_UPTIME_THRESHOLD", "95.0"))
        
        # State
        self.auth_token = None
        self.orchestrator_stats: Dict[str, Dict] = {}
        self.payment_history: List[Dict] = []
        self.running = False
        
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
                    return False
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return False
    
    async def get_orchestrators(self) -> List[Dict]:
        """Get list of registered orchestrators"""
        if not self.auth_token:
            await self.authenticate()
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.manager_url}/api/v1/livepeer/orchestrators",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("orchestrators", [])
                else:
                    logger.error(f"Failed to get orchestrators: {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Error fetching orchestrators: {e}")
                return []
    
    async def check_orchestrator_health(self, orchestrator: Dict) -> Dict:
        """Check health and uptime of an orchestrator via service monitoring"""
        orchestrator_id = orchestrator.get("orchestrator_id")
        endpoint = orchestrator.get("endpoint", "")
        
        # Initialize stats if not exists
        if orchestrator_id not in self.orchestrator_stats:
            self.orchestrator_stats[orchestrator_id] = {
                "checks": 0,
                "successful_checks": 0,
                "uptime_percentage": 0.0,
                "service_uptime_percentage": 0.0,
                "last_payment": None,
                "total_payments": 0,
                "capabilities": orchestrator.get("capabilities", [])
            }
        
        stats = self.orchestrator_stats[orchestrator_id]
        stats["checks"] += 1
        
        # Default values
        is_healthy = False
        service_uptime = 0.0
        
        try:
            # Check if orchestrator has agent-net capability (service monitoring)
            if "agent-net" in orchestrator.get("capabilities", []):
                # Get worker endpoint (port 9876 for service monitoring)
                worker_endpoint = endpoint.replace(":9995", ":9876").replace("https", "http")
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Check service uptime endpoint
                    response = await client.get(f"{worker_endpoint}/service-uptime")
                    if response.status_code == 200:
                        data = response.json()
                        service_uptime = data.get("overall_uptime_percentage", 0.0)
                        is_healthy = data.get("eligible_for_payment", False)
                        
                        stats["service_uptime_percentage"] = service_uptime
                        stats["successful_checks"] += 1
                        
                        logger.info(
                            f"Service check for {orchestrator_id}: "
                            f"uptime={service_uptime:.2f}%, eligible={is_healthy}"
                        )
                    else:
                        logger.warning(f"Service check failed for {orchestrator_id}: HTTP {response.status_code}")
            else:
                # Fallback: just check if orchestrator is connected
                if orchestrator.get("status") == "connected":
                    is_healthy = True
                    stats["successful_checks"] += 1
                    service_uptime = 100.0
                        
        except Exception as e:
            logger.error(f"Service check error for {orchestrator_id}: {e}")
            is_healthy = False
        
        # Calculate orchestrator uptime (connection reliability)
        stats["uptime_percentage"] = (stats["successful_checks"] / stats["checks"]) * 100
        
        return {
            "orchestrator_id": orchestrator_id,
            "is_healthy": is_healthy,
            "uptime_percentage": stats["uptime_percentage"],
            "service_uptime_percentage": service_uptime,
            "stats": stats
        }
    
    async def process_payment(self, orchestrator_id: str, amount: float) -> bool:
        """Process payment for an orchestrator"""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        payment_data = {
            "call_type": "uptime_payment",
            "orchestrator_id": orchestrator_id,
            "amount": amount,
            "currency": "USD",
            "recipient": orchestrator_id,
            "reference": f"uptime-payment-{int(time.time())}"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.manager_url}/api/v1/livepeer/payments/process",
                    json=payment_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.info(f"Payment processed for {orchestrator_id}: ${amount}")
                    return True
                else:
                    logger.error(f"Payment failed for {orchestrator_id}: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"Payment error for {orchestrator_id}: {e}")
                return False
    
    async def distribute_payments(self):
        """Main payment distribution cycle"""
        logger.info("Starting payment distribution cycle")
        
        # Get orchestrators
        orchestrators = await self.get_orchestrators()
        if not orchestrators:
            logger.warning("No orchestrators found")
            return
        
        logger.info(f"Processing {len(orchestrators)} orchestrators")
        
        # Check health and process payments
        for orchestrator in orchestrators:
            health_check = await self.check_orchestrator_health(orchestrator)
            orchestrator_id = health_check["orchestrator_id"]
            
            # Check if eligible for payment based on service uptime
            if health_check["is_healthy"]:
                success = await self.process_payment(orchestrator_id, self.payment_amount)
                
                if success:
                    self.orchestrator_stats[orchestrator_id]["last_payment"] = datetime.now().isoformat()
                    self.orchestrator_stats[orchestrator_id]["total_payments"] += 1
                    
                    self.payment_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "orchestrator_id": orchestrator_id,
                        "amount": self.payment_amount,
                        "service_uptime": health_check["service_uptime_percentage"],
                        "success": True
                    })
                    
                    logger.info(
                        f"Payment processed for {orchestrator_id}: "
                        f"service uptime {health_check['service_uptime_percentage']:.2f}%"
                    )
            else:
                logger.warning(
                    f"Skipping payment for {orchestrator_id}: "
                    f"service uptime {health_check['service_uptime_percentage']:.2f}% < {self.min_uptime_threshold}% "
                    f"or services not healthy"
                )
    
    async def print_statistics(self):
        """Print current statistics"""
        logger.info("=" * 60)
        logger.info("PAYMENT DISTRIBUTOR STATISTICS")
        logger.info("=" * 60)
        
        for orchestrator_id, stats in self.orchestrator_stats.items():
            logger.info(f"\nOrchestrator: {orchestrator_id}")
            logger.info(f"  Uptime: {stats['uptime_percentage']:.2f}%")
            logger.info(f"  Total Payments: {stats['total_payments']}")
            logger.info(f"  Last Payment: {stats['last_payment'] or 'Never'}")
            logger.info(f"  Capabilities: {', '.join(stats['capabilities'])}")
        
        total_payments = sum(s["total_payments"] for s in self.orchestrator_stats.values())
        total_amount = total_payments * self.payment_amount
        logger.info(f"\nTotal Payments Made: {total_payments}")
        logger.info(f"Total Amount Distributed: ${total_amount:.2f}")
        logger.info("=" * 60)
    
    async def run(self):
        """Main run loop"""
        logger.info("Payment Distributor Service Starting")
        logger.info(f"Payment Interval: {self.payment_interval} seconds")
        logger.info(f"Payment Amount: ${self.payment_amount} per orchestrator")
        logger.info(f"Minimum Uptime Threshold: {self.min_uptime_threshold}%")
        
        # Authenticate first
        if not await self.authenticate():
            logger.error("Failed to authenticate, exiting")
            return
        
        self.running = True
        cycle = 0
        
        while self.running:
            cycle += 1
            logger.info(f"\n--- Payment Cycle {cycle} ---")
            
            try:
                await self.distribute_payments()
                
                # Print statistics every 5 cycles
                if cycle % 5 == 0:
                    await self.print_statistics()
                    
            except Exception as e:
                logger.error(f"Error in payment cycle: {e}")
            
            # Wait for next cycle
            logger.info(f"Waiting {self.payment_interval} seconds until next cycle...")
            await asyncio.sleep(self.payment_interval)
    
    def stop(self):
        """Stop the service"""
        logger.info("Stopping Payment Distributor Service")
        self.running = False


async def main():
    """Main entry point"""
    distributor = PaymentDistributor()
    
    # Handle shutdown
    import signal
    def shutdown_handler(sig, frame):
        logger.info("Shutdown signal received")
        distributor.stop()
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    try:
        await distributor.run()
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        await distributor.print_statistics()


if __name__ == "__main__":
    asyncio.run(main())