#!/usr/bin/env python3
"""
Modified Uptime-Aware Configurable Capability Tester for Livepeer Gateway
Queries GPU uptime directly from worker endpoints instead of a separate ping system.
Implements client-side punishment logic based on GPU uptime.
"""

import requests
import time
import json
import random
import base64
import threading
import argparse
import signal
import sys
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration for different capabilities
CAPABILITIES = {
    "gpu-check": {
        "endpoint": "http://localhost:8088/gateway/process/request/agent-net",
        "capability_name": "agent-net", 
        "run_command": "agent-net",
        "payload_generator": lambda agent_id: {
            "action": "gpu-check",
            "agent_id": agent_id,
            "include_utilization": True,
            "timestamp": time.time()
        }
    },
    "text-to-image": {
        "endpoint": "http://localhost:8088/gateway/process/request/text-to-image",
        "capability_name": "text-to-image",
        "run_command": "text-to-image",
        "payload_generator": lambda agent_id: {
            "prompt": random.choice([
                "a beautiful sunset over mountains",
                "a cyberpunk city at night",
                "a magical forest with glowing plants",
                "an underwater coral reef scene"
            ]),
            "agent_id": agent_id,
            "seed": random.randint(1, 1000000),
            "timestamp": time.time()
        }
    }
}

@dataclass
class UptimeInfo:
    """Information about agent uptime from GPU check"""
    agent_id: str
    uptime_percent: float
    last_check: datetime = None
    gpu_available: bool = True
    model_name: str = None
    vram_usage_mb: float = 0.0
    total_models: int = 0
    
@dataclass 
class RequestStats:
    """Statistics for tracking request performance"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    delayed_requests: int = 0  # Requests not sent due to punishment
    response_times: List[float] = field(default_factory=list)
    status_codes: Dict[int, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def add_response(self, status_code: int, response_time: float, error: str = None):
        """Add a response to the statistics"""
        self.total_requests += 1
        self.response_times.append(response_time)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        
        if status_code == 200:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)
                
    def add_delayed(self):
        """Record a delayed request due to punishment"""
        self.delayed_requests += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the statistics"""
        if not self.response_times and self.delayed_requests == 0:
            return {"status": "no_requests"}
            
        total_attempted = len(self.response_times)
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "delayed_requests": self.delayed_requests,
            "success_rate": f"{(self.successful_requests / max(total_attempted, 1) * 100):.2f}%" if total_attempted > 0 else "N/A",
            "avg_response_time": f"{sum(self.response_times) / len(self.response_times):.2f}ms" if self.response_times else "N/A",
            "min_response_time": f"{min(self.response_times):.2f}ms" if self.response_times else "N/A",
            "max_response_time": f"{max(self.response_times):.2f}ms" if self.response_times else "N/A",
            "status_codes": self.status_codes,
            "recent_errors": self.errors[-5:] if self.errors else []
        }

class UptimeAwareCapabilityTester:
    """Capability tester that adjusts job rate based on agent uptime from direct GPU checks"""
    
    def __init__(self, 
                 base_jobs_per_minute: int,
                 capabilities: List[str],
                 target_agent_id: str,
                 gateway_url: str = "http://localhost:8088",
                 uptime_query_interval: int = 30):
        """
        Initialize the uptime-aware tester
        
        Args:
            base_jobs_per_minute: Base job rate for 99%+ uptime
            capabilities: List of capabilities to test
            target_agent_id: ID of the agent to monitor
            gateway_url: URL of the Livepeer gateway
            uptime_query_interval: How often to query uptime (seconds)
        """
        self.base_jobs_per_minute = base_jobs_per_minute
        self.capabilities = capabilities
        self.target_agent_id = target_agent_id
        self.gateway_url = gateway_url.rstrip('/')
        self.uptime_query_interval = uptime_query_interval
        
        self.running = True
        self.stats = {cap: RequestStats() for cap in capabilities}
        self.current_uptime_info: Optional[UptimeInfo] = None
        self.current_job_rate = base_jobs_per_minute
        self.start_time = time.time()
        self.jobs_sent = 0
        
        # Validate capabilities
        invalid_caps = [cap for cap in capabilities if cap not in CAPABILITIES]
        if invalid_caps:
            raise ValueError(f"Invalid capabilities: {invalid_caps}. Available: {list(CAPABILITIES.keys())}")
            
    async def get_agent_uptime(self) -> Optional[UptimeInfo]:
        """Query worker GPU check endpoint for GPU/VRAM status"""
        try:
            # Query worker's GPU check endpoint
            async with aiohttp.ClientSession() as session:
                # Use the worker endpoint through Caddy proxy
                url = f"{self.gateway_url.rstrip('/')}/worker/gpu-check"
                payload = {"agent_id": self.target_agent_id}
                
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        print(f"❌ Failed to get GPU status: HTTP {resp.status}")
                        return None
                        
                    data = await resp.json()
                    
                    # Extract data from response
                    return UptimeInfo(
                        agent_id=data.get('agent_id', self.target_agent_id),
                        uptime_percent=data.get('uptime_percent', 85.0),
                        last_check=datetime.now(),
                        gpu_available=data.get('gpu_count', 0) > 0,
                        model_name=data.get('model_name', 'Unknown'),
                        vram_usage_mb=data.get('vram_usage_mb', 0.0),
                        total_models=data.get('total_models', 0)
                    )
                        
        except Exception as e:
            print(f"❌ Error querying GPU status: {e}")
            return None
            
    def calculate_job_rate(self, uptime_percent: float) -> int:
        """
        Calculate jobs per minute based on uptime percentage
        
        Punishment strategy:
        - 99%+ uptime: 100% job rate (base rate)
        - 95-99% uptime: 50% job rate  
        - 90-95% uptime: 10% job rate
        - <90% uptime: 0% job rate (full punishment)
        """
        if uptime_percent >= 99.0:
            return self.base_jobs_per_minute
        elif uptime_percent >= 95.0:
            return int(self.base_jobs_per_minute * 0.5)
        elif uptime_percent >= 90.0:
            return int(self.base_jobs_per_minute * 0.1)
        else:
            return 0
            
    def create_livepeer_headers(self, capability_config: Dict[str, str]) -> Dict[str, str]:
        """Create proper Livepeer headers for gateway requests"""
        job_header = base64.b64encode(json.dumps({
            "request": json.dumps({"run": capability_config["run_command"]}),
            "parameters": json.dumps({}),
            "capability": capability_config["capability_name"],
            "timeout_seconds": 30
        }).encode()).decode()
        
        return {
            'Content-Type': 'application/json',
            'Livepeer': job_header
        }
        
    def make_single_request(self, capability_name: str) -> tuple:
        """Make a single request for a given capability"""
        start_time = time.time()
        
        try:
            capability_config = CAPABILITIES[capability_name]
            headers = self.create_livepeer_headers(capability_config)
            payload = capability_config["payload_generator"](self.target_agent_id)
            
            response = requests.post(
                capability_config["endpoint"],
                headers=headers,
                json=payload,
                timeout=25
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # We're getting real GPU data from Ollama, so ignore response metadata
            # The mock server's metadata would overwrite our real Ollama data
            
            return (
                response.status_code,
                response_time,
                response.text if response.status_code != 200 else None,
                payload
            )
            
        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            return (0, response_time, "Request timeout", {})
            
        except requests.exceptions.RequestException as e:
            response_time = (time.time() - start_time) * 1000
            return (-1, response_time, str(e), {})
            
    async def update_uptime_loop(self):
        """Background loop to periodically update uptime information"""
        while self.running:
            uptime_info = await self.get_agent_uptime()
            if uptime_info:
                self.current_uptime_info = uptime_info
                old_rate = self.current_job_rate
                self.current_job_rate = self.calculate_job_rate(uptime_info.uptime_percent)
                
                if old_rate != self.current_job_rate:
                    print(f"\n📊 Job rate changed: {old_rate} → {self.current_job_rate} jobs/min")
                    print(f"   Model: {uptime_info.model_name}")
                    print(f"   VRAM: {uptime_info.vram_usage_mb:.0f}MB")
                    print(f"   GPU Score: {uptime_info.uptime_percent:.1f}%")
                    
            await asyncio.sleep(self.uptime_query_interval)
            
    async def run_job_loop(self):
        """Main loop that sends jobs at calculated rate"""
        print(f"\n🚀 UPTIME-AWARE CAPABILITY TESTER STARTED")
        print(f"🎯 Target Agent: {self.target_agent_id}")
        print(f"📦 Base Job Rate: {self.base_jobs_per_minute} jobs/min")
        print(f"🎪 Capabilities: {', '.join(self.capabilities)}")
        print(f"🔄 Uptime Query Interval: {self.uptime_query_interval}s")
        print("=" * 80)
        
        # Start uptime monitoring
        uptime_task = asyncio.create_task(self.update_uptime_loop())
        
        try:
            # Get initial uptime data
            initial_uptime = await self.get_agent_uptime()
            if initial_uptime:
                self.current_uptime_info = initial_uptime
                self.current_job_rate = self.calculate_job_rate(initial_uptime.uptime_percent)
                print(f"\n🤖 Model: {initial_uptime.model_name}")
                print(f"💾 VRAM Usage: {initial_uptime.vram_usage_mb:.0f} MB")
                print(f"📊 GPU Score: {initial_uptime.uptime_percent:.1f}%")
                print(f"📊 Initial job rate: {self.current_job_rate} jobs/min")
            
            while self.running:
                # Wait for initial uptime data
                if self.current_uptime_info is None:
                    print("⏳ Waiting for initial uptime data...")
                    await asyncio.sleep(1)
                    continue
                    
                # Check current job rate
                if self.current_job_rate == 0:
                    # Full punishment - no jobs
                    print(f"\n🛑 Job sending suspended - GPU Score too low ({self.current_uptime_info.uptime_percent:.1f}%) - VRAM: {self.current_uptime_info.vram_usage_mb:.0f}MB")
                    
                    # Record delayed requests
                    for cap in self.capabilities:
                        self.stats[cap].add_delayed()
                        
                    await asyncio.sleep(60)  # Check again in a minute
                    continue
                    
                # Calculate delay between jobs
                delay_seconds = 60.0 / self.current_job_rate
                
                # Send a job for a random capability
                capability = random.choice(self.capabilities)
                
                # Make the request
                status_code, response_time, error, payload = self.make_single_request(capability)
                self.stats[capability].add_response(status_code, response_time, error)
                self.jobs_sent += 1
                
                # Log result
                if status_code == 200:
                    status_emoji = "✅"
                else:
                    status_emoji = "❌"
                    
                # Ensure we have valid uptime info
                if self.current_uptime_info:
                    model_name = self.current_uptime_info.model_name or "Unknown"
                    vram_mb = self.current_uptime_info.vram_usage_mb or 0.0
                else:
                    model_name = "No data"
                    vram_mb = 0.0
                    
                print(f"{status_emoji} [{datetime.now().strftime('%H:%M:%S')}] {capability}: "
                      f"{status_code} ({response_time:.0f}ms) | "
                      f"Rate: {self.current_job_rate}/min | "
                      f"Model: {model_name} | "
                      f"VRAM: {vram_mb:.0f}MB")
                
                # Print statistics periodically
                if self.jobs_sent % 50 == 0:
                    self.print_statistics()
                    
                # Wait before next job
                await asyncio.sleep(delay_seconds)
                
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal")
        finally:
            self.running = False
            uptime_task.cancel()
            try:
                await uptime_task
            except asyncio.CancelledError:
                pass
                
    def print_statistics(self):
        """Print current statistics"""
        print(f"\n📊 STATISTICS SUMMARY")
        print("=" * 80)
        
        total_time = time.time() - self.start_time
        print(f"🕐 Total Runtime: {total_time:.1f}s")
        print(f"📤 Total Jobs Sent: {self.jobs_sent}")
        print(f"⚡ Current Job Rate: {self.current_job_rate} jobs/min")
        
        if self.current_uptime_info:
            print(f"\n🖥️  GPU STATUS (via Ollama)")
            print("-" * 40)
            print(f"  🆔 Agent ID: {self.current_uptime_info.agent_id}")
            print(f"  🤖 Model: {self.current_uptime_info.model_name}")
            print(f"  💾 VRAM Usage: {self.current_uptime_info.vram_usage_mb:.0f} MB ({self.current_uptime_info.vram_usage_mb/1024:.2f} GB)")
            print(f"  📊 GPU Score: {self.current_uptime_info.uptime_percent:.2f}%")
            print(f"  🖥️  GPU Available: {'Yes' if self.current_uptime_info.gpu_available else 'No'}")
            print(f"  📚 Total Models: {self.current_uptime_info.total_models}")
            print(f"  🕐 Last Check: {self.current_uptime_info.last_check.strftime('%H:%M:%S')}")
            
        for capability, stats in self.stats.items():
            print(f"\n🎯 {capability.upper()}")
            print("-" * 40)
            summary = stats.get_summary()
            
            if summary.get("status") == "no_requests":
                print("  📭 No requests sent yet")
                continue
                
            print(f"  📤 Total Attempts: {summary['total_requests']}")
            print(f"  ✅ Successful: {summary['successful_requests']}")
            print(f"  ❌ Failed: {summary['failed_requests']}")
            print(f"  ⏳ Delayed (Punished): {summary['delayed_requests']}")
            print(f"  📈 Success Rate: {summary['success_rate']}")
            if summary['avg_response_time'] != "N/A":
                print(f"  ⏱️  Avg Response Time: {summary['avg_response_time']}")
                print(f"  🏃 Min/Max: {summary['min_response_time']} / {summary['max_response_time']}")
            print(f"  📊 Status Codes: {summary['status_codes']}")
            
            if summary['recent_errors']:
                print(f"  🚨 Recent Errors: {summary['recent_errors']}")
                
def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    print(f"\n🛑 Received signal {signum}")
    sys.exit(0)
    
async def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Modified Uptime-Aware Capability Tester - Queries GPU status directly from worker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 60 jobs/min base rate for agent-001
  python modified_uptime_aware_capability_tester.py --agent agent-001 --rate 60
  
  # Test multiple capabilities
  python modified_uptime_aware_capability_tester.py --agent agent-001 --rate 30 --capabilities gpu-check text-to-image
  
  # Test with frequent uptime checks (every 10 seconds)
  python modified_uptime_aware_capability_tester.py --agent agent-001 --rate 60 --uptime-interval 10

Punishment Strategy:
  - 99%+ uptime: 100% job rate (base rate)
  - 95-99% uptime: 50% job rate  
  - 90-95% uptime: 10% job rate
  - <90% uptime: 0% job rate (full punishment)
        """
    )
    
    parser.add_argument(
        '--agent',
        required=True,
        help='Target agent ID to monitor'
    )
    
    parser.add_argument(
        '--rate',
        type=int,
        default=60,
        help='Base jobs per minute for 99%+ uptime (default: 60)'
    )
    
    parser.add_argument(
        '--capabilities',
        nargs='+',
        default=['gpu-check'],
        choices=list(CAPABILITIES.keys()),
        help=f'Capabilities to test (choices: {list(CAPABILITIES.keys())})'
    )
    
    parser.add_argument(
        '--gateway-url',
        default='http://localhost:8088',
        help='Livepeer gateway URL (default: http://localhost:8088)'
    )
    
    parser.add_argument(
        '--uptime-interval',
        type=int,
        default=30,
        help='How often to query uptime in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run the tester
    tester = UptimeAwareCapabilityTester(
        base_jobs_per_minute=args.rate,
        capabilities=args.capabilities,
        target_agent_id=args.agent,
        gateway_url=args.gateway_url,
        uptime_query_interval=args.uptime_interval
    )
    
    try:
        await tester.run_job_loop()
    finally:
        tester.print_statistics()

if __name__ == "__main__":
    asyncio.run(main())