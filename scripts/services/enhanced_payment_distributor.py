#!/usr/bin/env python3
"""
Enhanced Payment Distributor with BYOC Job Submission
Sends BYOC jobs through Livepeer Gateway and applies payment logic based on responses
"""

import asyncio
import httpx
import json
import os
import time
import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrchestratorStatus(Enum):
    """Orchestrator status levels"""
    EXCELLENT = "excellent"  # >95% uptime
    GOOD = "good"           # 80-95% uptime
    WARNING = "warning"     # 60-80% uptime
    POOR = "poor"          # 40-60% uptime
    CRITICAL = "critical"   # <40% uptime
    OFFLINE = "offline"     # Not responding


@dataclass
class PaymentPolicy:
    """Payment policy based on uptime performance"""
    min_uptime: float
    payment_multiplier: float  # Multiplier for base payment
    delay_seconds: int  # Additional delay before next payment
    description: str


@dataclass
class OrchestratorState:
    """Track orchestrator state and history"""
    orchestrator_id: str
    endpoint: str
    capabilities: List[str] = field(default_factory=list)
    checks_total: int = 0
    checks_successful: int = 0
    uptime_percentage: float = 0.0
    service_uptime: float = 0.0
    last_status: OrchestratorStatus = OrchestratorStatus.OFFLINE
    last_payment_time: Optional[datetime] = None
    next_payment_time: Optional[datetime] = None
    total_payments: int = 0
    total_amount_usd: float = 0.0
    consecutive_failures: int = 0
    punishment_delay: int = 0  # Current punishment delay in seconds
    payment_history: List[Dict] = field(default_factory=list)
    last_byoc_response: Optional[Dict] = None


class EnhancedPaymentDistributor:
    """Enhanced payment distributor that sends BYOC jobs through gateway"""
    
    # Payment policies based on uptime
    PAYMENT_POLICIES = {
        OrchestratorStatus.EXCELLENT: PaymentPolicy(95.0, 1.2, 0, "Bonus for excellent uptime"),
        OrchestratorStatus.GOOD: PaymentPolicy(80.0, 1.0, 0, "Standard payment"),
        OrchestratorStatus.WARNING: PaymentPolicy(60.0, 0.7, 30, "Reduced payment with warning"),
        OrchestratorStatus.POOR: PaymentPolicy(40.0, 0.3, 120, "Minimal payment with delay"),
        OrchestratorStatus.CRITICAL: PaymentPolicy(0.0, 0.1, 300, "Emergency payment only"),
        OrchestratorStatus.OFFLINE: PaymentPolicy(0.0, 0.0, 600, "No payment - offline")
    }
    
    def __init__(self):
        # Configuration from environment
        self.manager_url = os.environ.get("MANAGER_URL", "http://central-manager:8000")
        self.gateway_url = os.environ.get("GATEWAY_URL", "http://livepeer-gateway:8935")
        self.orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://livepeer-orchestrator:9995")
        self.worker_url = os.environ.get("WORKER_URL", "http://livepeer-worker:9876")
        
        self.admin_email = os.environ.get("ADMIN_EMAIL", "admin@system.com")
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "LivepeerManager2025!Secure")
        
        # Payment configuration
        self.base_payment_interval = int(os.environ.get("PAYMENT_INTERVAL_SECONDS", "60"))
        self.base_payment_usd = float(os.environ.get("BASE_PAYMENT_USD", "10.0"))
        
        # Conversion rates (can be fetched from API in production)
        self.eth_to_usd = float(os.environ.get("ETH_TO_USD", "2000.0"))
        self.wei_per_eth = 10**18
        
        # Progressive punishment configuration
        self.max_consecutive_failures = int(os.environ.get("MAX_CONSECUTIVE_FAILURES", "5"))
        self.punishment_multiplier = float(os.environ.get("PUNISHMENT_MULTIPLIER", "2.0"))
        
        # State
        self.auth_token = None
        self.orchestrators: Dict[str, OrchestratorState] = {}
        self.running = False
        self.cycle_count = 0
        
        # BYOC job capability name - must match what worker registers
        self.capability_name = "agent-net"
        
    def get_capability_name(self) -> str:
        """Get the capability name for BYOC jobs"""
        return self.capability_name
        
    def usd_to_wei(self, usd_amount: float) -> int:
        """Convert USD to Wei"""
        eth_amount = usd_amount / self.eth_to_usd
        wei_amount = int(eth_amount * self.wei_per_eth)
        return wei_amount
    
    def wei_to_usd(self, wei_amount: int) -> float:
        """Convert Wei to USD"""
        eth_amount = wei_amount / self.wei_per_eth
        usd_amount = eth_amount * self.eth_to_usd
        return usd_amount
    
    def determine_status(self, uptime_percentage: float) -> OrchestratorStatus:
        """Determine orchestrator status based on uptime"""
        if uptime_percentage >= 95:
            return OrchestratorStatus.EXCELLENT
        elif uptime_percentage >= 80:
            return OrchestratorStatus.GOOD
        elif uptime_percentage >= 60:
            return OrchestratorStatus.WARNING
        elif uptime_percentage >= 40:
            return OrchestratorStatus.POOR
        elif uptime_percentage > 0:
            return OrchestratorStatus.CRITICAL
        else:
            return OrchestratorStatus.OFFLINE
    
    def calculate_payment_amount(self, state: OrchestratorState) -> Tuple[float, str]:
        """Calculate payment amount based on orchestrator state"""
        policy = self.PAYMENT_POLICIES[state.last_status]
        
        # Base calculation
        amount_usd = self.base_payment_usd * policy.payment_multiplier
        
        # Apply progressive punishment for consecutive failures
        if state.consecutive_failures > 0:
            reduction_factor = 1 / (1 + state.consecutive_failures * 0.2)
            amount_usd *= reduction_factor
            reason = f"Reduced by {(1-reduction_factor)*100:.0f}% due to {state.consecutive_failures} failures"
        else:
            reason = policy.description
        
        # Bonus for long-term reliability
        if state.checks_total > 100 and state.uptime_percentage > 98:
            amount_usd *= 1.1
            reason += " + 10% reliability bonus"
        
        return amount_usd, reason
    
    def calculate_next_payment_time(self, state: OrchestratorState) -> datetime:
        """Calculate next payment time with delays"""
        policy = self.PAYMENT_POLICIES[state.last_status]
        base_delay = self.base_payment_interval
        
        # Add policy delay
        total_delay = base_delay + policy.delay_seconds
        
        # Add punishment delay (exponential backoff)
        if state.consecutive_failures > 0:
            punishment_delay = min(
                int(self.base_payment_interval * (self.punishment_multiplier ** state.consecutive_failures)),
                3600  # Max 1 hour delay
            )
            total_delay += punishment_delay
            state.punishment_delay = punishment_delay
        else:
            state.punishment_delay = 0
        
        return datetime.now() + timedelta(seconds=total_delay)
    
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
    
    async def register_orchestrator_with_monitor(self, orchestrator: Dict) -> bool:
        """Register orchestrator with the orchestrator-monitor container"""
        try:
            monitor_data = {
                "orchestrator_id": orchestrator.get("orchestrator_id"),
                "endpoint": orchestrator.get("endpoint"),
                "capabilities": orchestrator.get("capabilities", []),
                "status": "active",
                "registered_at": datetime.now().isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                # Try to register with orchestrator-monitor
                response = await client.post(
                    "http://orchestrator-monitor:8000/register",
                    json=monitor_data,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Registered {orchestrator.get('orchestrator_id')} with monitor")
                    return True
                    
        except Exception as e:
            logger.warning(f"Could not register with monitor: {e}")
        
        return False
    
    async def get_orchestrators(self) -> List[Dict]:
        """Get list of registered orchestrators from manager"""
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
                    orchestrators = data.get("orchestrators", [])
                    
                    # Register each with monitor
                    for orch in orchestrators:
                        await self.register_orchestrator_with_monitor(orch)
                    
                    return orchestrators
                else:
                    logger.error(f"Failed to get orchestrators: {response.status_code}")
                    return []
            except Exception as e:
                logger.error(f"Error fetching orchestrators: {e}")
                return []
    
    def create_livepeer_headers(self, capability_name: str, agent_id: str) -> Dict[str, str]:
        """Create proper Livepeer headers for gateway BYOC requests"""
        job_header = base64.b64encode(json.dumps({
            "request": json.dumps({"run": "agent-net"}),
            "parameters": json.dumps({}),
            "capability": capability_name,
            "timeout_seconds": 30
        }).encode()).decode()
        
        headers = {
            'Content-Type': 'application/json',
            'Livepeer': job_header,
            'Livepeer-Orch-Search-Timeout': '2s',
            'Livepeer-Orch-Search-Resp-Timeout': '1s'
        }
        return headers
    
    async def send_byoc_job_through_gateway(self, state: OrchestratorState) -> Dict[str, Any]:
        """Send BYOC job through gateway and get uptime response"""
        result = {
            "success": False,
            "service_uptime": 0.0,
            "response_time_ms": 0,
            "error": None,
            "response_data": None
        }
        
        # Get capability name for BYOC job
        capability_name = self.get_capability_name()
        agent_id = state.orchestrator_id.split('-')[0] if '-' in state.orchestrator_id else "0"
        
        # Create payload (similar to multi_orchestrator_tester)
        payload = {
            "action": "service-monitoring",
            "agent_id": agent_id,
            "include_utilization": True,
            "timestamp": time.time()
        }
        
        headers = self.create_livepeer_headers(capability_name, agent_id)
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                # Send BYOC job to gateway endpoint
                response = await client.post(
                    f"{self.gateway_url}/process/request/agent-net",
                    headers=headers,
                    json=payload
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                result["response_time_ms"] = response_time_ms
                
                if response.status_code == 200:
                    result["success"] = True
                    response_data = response.json()
                    result["response_data"] = response_data
                    
                    # Extract service uptime from response
                    if "overall_uptime_percentage" in response_data:
                        result["service_uptime"] = response_data["overall_uptime_percentage"]
                    elif "service_uptime" in response_data:
                        result["service_uptime"] = response_data["service_uptime"]
                    elif "uptime_percentage" in response_data:
                        result["service_uptime"] = response_data["uptime_percentage"]
                    else:
                        # If no explicit uptime, consider it healthy (100%)
                        result["service_uptime"] = 100.0
                    
                    logger.info(
                        f"BYOC job successful for {state.orchestrator_id} via {capability_name}: "
                        f"uptime={result['service_uptime']:.1f}%, time={response_time_ms:.0f}ms"
                    )
                elif response.status_code == 503:
                    result["error"] = "No orchestrators available"
                    logger.warning(f"No orchestrators found for {capability_name}: {response.text}")
                else:
                    result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"BYOC job failed for {state.orchestrator_id}: {result['error']}")
                    
        except httpx.TimeoutError:
            result["error"] = "Request timeout after 25s"
            result["response_time_ms"] = 25000
            logger.warning(f"BYOC job timeout for {state.orchestrator_id}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"BYOC job error for {state.orchestrator_id}: {e}")
        
        return result
    
    async def process_payment(self, state: OrchestratorState, amount_usd: float, reason: str) -> bool:
        """Process payment with proper USD to Wei conversion"""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Convert USD to Wei for Livepeer
        amount_wei = self.usd_to_wei(amount_usd)
        
        payment_data = {
            "call_type": "uptime_payment",
            "orchestrator_id": state.orchestrator_id,
            "amount": amount_usd,  # Store USD amount
            "amount_wei": str(amount_wei),  # Include Wei amount
            "currency": "USD",
            "eth_equivalent": amount_usd / self.eth_to_usd,
            "recipient": state.orchestrator_id,
            "reference": f"uptime-{int(time.time())}",
            "reason": reason,
            "uptime_percentage": state.uptime_percentage,
            "service_uptime": state.service_uptime,
            "status": state.last_status.value,
            "byoc_response": state.last_byoc_response  # Include BYOC response
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.manager_url}/api/v1/livepeer/payments/process",
                    json=payment_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.info(
                        f"Payment processed for {state.orchestrator_id}: "
                        f"${amount_usd:.2f} ({amount_wei} wei) - {reason}"
                    )
                    return True
                else:
                    logger.error(f"Payment failed for {state.orchestrator_id}: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"Payment error for {state.orchestrator_id}: {e}")
                return False
    
    async def process_orchestrator(self, orchestrator: Dict):
        """Process a single orchestrator with BYOC job and payment logic"""
        orch_id = orchestrator.get("orchestrator_id")
        
        # Initialize or get state
        if orch_id not in self.orchestrators:
            self.orchestrators[orch_id] = OrchestratorState(
                orchestrator_id=orch_id,
                endpoint=orchestrator.get("endpoint", ""),
                capabilities=orchestrator.get("capabilities", [])
            )
        
        state = self.orchestrators[orch_id]
        
        # Skip if not time for payment yet
        if state.next_payment_time and datetime.now() < state.next_payment_time:
            time_remaining = (state.next_payment_time - datetime.now()).total_seconds()
            logger.debug(f"Skipping {orch_id}: next payment in {time_remaining:.0f}s")
            return
        
        # Send BYOC job through gateway
        byoc_result = await self.send_byoc_job_through_gateway(state)
        state.last_byoc_response = byoc_result
        
        # Update state based on BYOC response
        state.checks_total += 1
        if byoc_result["success"]:
            state.checks_successful += 1
            state.consecutive_failures = 0
            state.service_uptime = byoc_result["service_uptime"]
        else:
            state.consecutive_failures += 1
            state.service_uptime = 0.0
        
        # Calculate uptime percentage
        state.uptime_percentage = (state.checks_successful / state.checks_total) * 100
        
        # Determine status based on service uptime from BYOC response
        state.last_status = self.determine_status(state.service_uptime)
        
        # Calculate payment
        amount_usd, reason = self.calculate_payment_amount(state)
        
        # Process payment if amount > 0 and BYOC was successful
        if amount_usd > 0 and byoc_result["success"]:
            success = await self.process_payment(state, amount_usd, reason)
            
            if success:
                state.last_payment_time = datetime.now()
                state.total_payments += 1
                state.total_amount_usd += amount_usd
                
                # Record in history
                state.payment_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "amount_usd": amount_usd,
                    "amount_wei": self.usd_to_wei(amount_usd),
                    "reason": reason,
                    "uptime": state.service_uptime,
                    "status": state.last_status.value,
                    "response_time_ms": byoc_result["response_time_ms"]
                })
                
                # Keep only last 100 payments in history
                if len(state.payment_history) > 100:
                    state.payment_history = state.payment_history[-100:]
        else:
            if amount_usd == 0:
                logger.warning(f"No payment for {orch_id}: {state.last_status.value}")
            elif not byoc_result["success"]:
                logger.warning(f"Skipping payment for {orch_id}: BYOC job failed - {byoc_result['error']}")
        
        # Calculate next payment time
        state.next_payment_time = self.calculate_next_payment_time(state)
        
        # Log status
        logger.info(
            f"Orchestrator {orch_id}: "
            f"Status={state.last_status.value}, "
            f"Uptime={state.service_uptime:.1f}%, "
            f"Payment=${amount_usd:.2f}, "
            f"ResponseTime={byoc_result['response_time_ms']:.0f}ms, "
            f"Next in {(state.next_payment_time - datetime.now()).total_seconds():.0f}s"
        )
    
    async def distribute_payments(self):
        """Main payment distribution cycle"""
        logger.info(f"Starting payment distribution cycle {self.cycle_count}")
        
        # Get orchestrators
        orchestrators = await self.get_orchestrators()
        if not orchestrators:
            logger.warning("No orchestrators found")
            return
        
        logger.info(f"Processing {len(orchestrators)} orchestrators with BYOC jobs")
        
        # Process each orchestrator
        tasks = [self.process_orchestrator(orch) for orch in orchestrators]
        await asyncio.gather(*tasks)
    
    async def print_statistics(self):
        """Print comprehensive statistics"""
        logger.info("=" * 80)
        logger.info("ENHANCED PAYMENT DISTRIBUTOR STATISTICS (BYOC MODE)")
        logger.info("=" * 80)
        
        total_payments = 0
        total_usd = 0.0
        
        for orch_id, state in self.orchestrators.items():
            logger.info(f"\nOrchestrator: {orch_id}")
            logger.info(f"  Status: {state.last_status.value}")
            logger.info(f"  Service Uptime: {state.service_uptime:.2f}%")
            logger.info(f"  BYOC Success Rate: {state.uptime_percentage:.2f}%")
            logger.info(f"  Total Payments: {state.total_payments}")
            logger.info(f"  Total Amount: ${state.total_amount_usd:.2f}")
            logger.info(f"  Consecutive Failures: {state.consecutive_failures}")
            
            if state.punishment_delay > 0:
                logger.info(f"  Punishment Delay: {state.punishment_delay}s")
            
            if state.last_byoc_response:
                logger.info(f"  Last BYOC Response Time: {state.last_byoc_response['response_time_ms']:.0f}ms")
            
            if state.next_payment_time:
                time_until = (state.next_payment_time - datetime.now()).total_seconds()
                logger.info(f"  Next Payment In: {time_until:.0f}s")
            
            total_payments += state.total_payments
            total_usd += state.total_amount_usd
        
        logger.info(f"\n" + "=" * 40)
        logger.info(f"Total Payments Made: {total_payments}")
        logger.info(f"Total USD Distributed: ${total_usd:.2f}")
        logger.info(f"Total ETH Distributed: {total_usd/self.eth_to_usd:.6f}")
        logger.info(f"Total Wei Distributed: {self.usd_to_wei(total_usd):,}")
        logger.info("=" * 80)
    
    async def run(self):
        """Main run loop"""
        logger.info("Enhanced Payment Distributor Starting (BYOC Mode)")
        logger.info(f"Gateway URL: {self.gateway_url}")
        logger.info(f"Base Payment: ${self.base_payment_usd} USD")
        logger.info(f"Base Interval: {self.base_payment_interval}s")
        logger.info(f"ETH/USD Rate: ${self.eth_to_usd}")
        logger.info(f"Capability Name: {self.capability_name}")
        logger.info("=" * 80)
        
        # Authenticate first
        if not await self.authenticate():
            logger.error("Failed to authenticate, exiting")
            return
        
        self.running = True
        
        while self.running:
            self.cycle_count += 1
            
            try:
                await self.distribute_payments()
                
                # Print statistics every 5 cycles
                if self.cycle_count % 5 == 0:
                    await self.print_statistics()
                    
            except Exception as e:
                logger.error(f"Error in payment cycle: {e}", exc_info=True)
            
            # Short sleep before next check
            await asyncio.sleep(10)  # Check every 10 seconds for orchestrators ready for payment
    
    def stop(self):
        """Stop the service"""
        logger.info("Stopping Enhanced Payment Distributor")
        self.running = False


async def main():
    """Main entry point"""
    distributor = EnhancedPaymentDistributor()
    
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
        logger.error(f"Service error: {e}", exc_info=True)
    finally:
        await distributor.print_statistics()


if __name__ == "__main__":
    asyncio.run(main())