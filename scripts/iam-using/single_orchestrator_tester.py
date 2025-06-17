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
        "endpoint": "http://localhost:9999/process/request/agent-net",  # Direct gateway (no Caddy)
        "capability_name": "agent-net", 
        "run_command": "agent-net",
        "payload_generator": lambda agent_id: {
            "action": "gpu-check",
            "agent_id": agent_id,
            "include_utilization": True,
            "timestamp": time.time()
        }
    },
   
}

@dataclass
class GPUInfo:
    """Information about agent GPU status"""
    agent_id: str
    vram_available_gb: float
    vram_used_gb: float
    vram_total_gb: float
    models_loaded: int
    model_names: List[str] = field(default_factory=list)
    gpu_available: bool = True
    last_check: datetime = None

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
    """Capability tester that adjusts job rate based on actual VRAM usage"""
    
    def __init__(self, 
                 base_jobs_per_minute: int,
                 capabilities: List[str],
                 target_agent_id: str,
                 gateway_url: str = "http://localhost:9999",  # Direct gateway (no Caddy)
                 gpu_query_interval: int = 30):
        """
        Initialize the VRAM-aware tester
        
        Args:
            base_jobs_per_minute: Base job rate when VRAM > 30GB
            capabilities: List of capabilities to test
            target_agent_id: ID of the agent to monitor
            gateway_url: URL of the Livepeer gateway
            gpu_query_interval: How often to query GPU status (seconds)
        """
        self.base_jobs_per_minute = base_jobs_per_minute
        self.capabilities = capabilities
        self.target_agent_id = target_agent_id
        self.gateway_url = gateway_url.rstrip('/')
        self.gpu_query_interval = gpu_query_interval
        
        self.running = True
        self.stats = {cap: RequestStats() for cap in capabilities}
        self.current_gpu_info: Optional[GPUInfo] = None
        self.current_delay_seconds = 0  # Additional delay between jobs
        self.start_time = time.time()
        self.jobs_sent = 0
        
        # Validate capabilities
        invalid_caps = [cap for cap in capabilities if cap not in CAPABILITIES]
        if invalid_caps:
            raise ValueError(f"Invalid capabilities: {invalid_caps}. Available: {list(CAPABILITIES.keys())}")
            
    async def get_agent_gpu_status_from_job_response(self, response_text: str) -> Optional[GPUInfo]:
        """Extract GPU status from BYOC job response (eliminates duplicate monitoring calls)"""
        try:
            data = json.loads(response_text)
            
            # Extract actual VRAM usage by models (keep in MB)
            vram_usage_mb = data.get('vram_usage_mb', 0.0)
            
            model_name = data.get('model_name', '')
            model_names = [model_name] if model_name else []
            
            return GPUInfo(
                agent_id=data.get('agent_id', self.target_agent_id),
                vram_available_gb=vram_usage_mb,  # Actually MB, but keeping field name for compatibility
                vram_used_gb=vram_usage_mb,       # Actually MB, but keeping field name for compatibility  
                vram_total_gb=vram_usage_mb,      # Actually MB, but keeping field name for compatibility
                models_loaded=data.get('total_models', 0),
                model_names=model_names,
                gpu_available=data.get('gpu_count', 0) > 0,
                last_check=datetime.now()
            )
                        
        except Exception as e:
            print(f"❌ Error parsing GPU status from job response: {e}")
            return None
            
    def calculate_delay(self, gpu_info: GPUInfo) -> float:
        """
        Calculate additional delay based on model VRAM usage (in MB)
        
        Case 2a: Models using > 30,000MB VRAM and models exist -> no delay (big models get priority)
        Case 2b: Models using < 30,000MB VRAM -> add delay (small models get delayed)
        """
        model_vram_usage_mb = gpu_info.vram_used_gb  # Actually MB despite field name
        
        if model_vram_usage_mb > 30000.0 and gpu_info.models_loaded > 0:
            # Case 2a: Big models (>30GB = 30,000MB) get priority - no delay
            return 0.0
        else:
            # Case 2b: Small models get delayed
            if model_vram_usage_mb > 1000.0:
                # Medium models (1-30GB = 1,000-30,000MB) get moderate delay
                return 5.0  # 5 second delay
            else:
                # Tiny models (<1GB = <1,000MB) get longer delay
                return 15.0  # 15 second delay
                
    def get_job_interval(self) -> float:
        """Calculate total interval between jobs (base rate + VRAM delay)"""
        base_interval = 60.0 / self.base_jobs_per_minute
        return base_interval + self.current_delay_seconds
        
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
            
            print(f"🔍 JOB REQUEST: {capability_config['endpoint']}")
            print(f"📦 Payload: {payload}")
            print(f"📋 Headers: {headers}")
            
            response = requests.post(
                capability_config["endpoint"],
                headers=headers,
                json=payload,
                timeout=25
            )
            
            print(f"📥 JOB RESPONSE: Status={response.status_code}, Body={response.text[:200]}...")
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Return response data - GPU status will be extracted in the main loop
            
            return (
                response.status_code,
                response_time,
                response.text if response.status_code != 200 else None,
                payload,
                response.text if response.status_code == 200 else None  # Add successful response data
            )
            
        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            return (0, response_time, "Request timeout", {}, None)
            
        except requests.exceptions.RequestException as e:
            response_time = (time.time() - start_time) * 1000
            return (-1, response_time, str(e), {}, None)
            
    # GPU monitoring eliminated - we get GPU status from each job response instead
            
    async def run_job_loop(self):
        """Main loop that sends jobs with VRAM-based delay logic (GPU data from job responses)"""
        print(f"\n🚀 SIMPLIFIED VRAM-AWARE CAPABILITY TESTER STARTED")
        print(f"🎯 Target Agent: {self.target_agent_id}")
        print(f"📦 Base Job Rate: {self.base_jobs_per_minute} jobs/min")
        print(f"🎪 Capabilities: {', '.join(self.capabilities)}")
        print(f"🧠 Logic: Case 2a (VRAM>30GB+models): No delay | Case 2b (other): Add delay")
        print(f"🔄 GPU Status: Extracted from each job response (no separate monitoring)")
        print("=" * 80)
        
        try:
            # Start with default delay until first job response gives us GPU data
            self.current_delay_seconds = 5.0  # Default moderate delay
            print(f"\n⏳ Initial delay: {self.current_delay_seconds}s (will update from first job response)")
            
            while self.running:
                    
                # Calculate delay between jobs
                delay_seconds = self.get_job_interval()
                
                # Send a job for a random capability
                capability = random.choice(self.capabilities)
                
                                # Make the request
                status_code, response_time, error, payload, success_response = self.make_single_request(capability)
                self.stats[capability].add_response(status_code, response_time, error)
                self.jobs_sent += 1
                
                # Extract GPU data from successful responses (eliminating separate monitoring)
                if status_code == 200 and success_response:
                    gpu_info = await self.get_agent_gpu_status_from_job_response(success_response)
                    if gpu_info:
                        old_delay = self.current_delay_seconds
                        self.current_gpu_info = gpu_info
                        self.current_delay_seconds = self.calculate_delay(gpu_info)
                        if old_delay != self.current_delay_seconds:
                            print(f"📊 Delay updated from job response: {old_delay}s → {self.current_delay_seconds}s")
                            case_status = "2a" if self.current_delay_seconds == 0 else "2b"
                            print(f"   VRAM: {gpu_info.vram_used_gb:.0f}MB, Models: {gpu_info.models_loaded} (Case {case_status})")
                
                # Log result
                if status_code == 200:
                    status_emoji = "✅"
                else:
                    status_emoji = "❌"
                    
                # Display current status
                if self.current_gpu_info:
                    model_names = ', '.join(self.current_gpu_info.model_names)
                    vram_display = f"{self.current_gpu_info.vram_used_gb:.0f}MB"
                else:
                    model_names = "Waiting for data..."
                    vram_display = "Unknown"
                    
                print(f"{status_emoji} [{datetime.now().strftime('%H:%M:%S')}] {capability}: "
                      f"{status_code} ({response_time:.0f}ms) | "
                      f"Delay: {self.current_delay_seconds}s | "
                      f"VRAM: {vram_display} | "
                      f"Models: {model_names}")
                
                # Print statistics periodically
                if self.jobs_sent % 50 == 0:
                    self.print_statistics()
                    
                # Wait before next job
                await asyncio.sleep(delay_seconds)
                
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal")
        finally:
            self.running = False
                
    def print_statistics(self):
        """Print current statistics"""
        print(f"\n📊 STATISTICS SUMMARY")
        print("=" * 80)
        
        total_time = time.time() - self.start_time
        print(f"🕐 Total Runtime: {total_time:.1f}s")
        print(f"📤 Total Jobs Sent: {self.jobs_sent}")
        print(f"⚡ Current Job Delay: {self.current_delay_seconds} seconds")
        
        if self.current_gpu_info:
            print(f"\n🖥️  GPU STATUS (via Ollama)")
            print("-" * 40)
            print(f"  🆔 Agent ID: {self.current_gpu_info.agent_id}")
            print(f"  🤖 VRAM: {self.current_gpu_info.vram_available_gb:.2f} GB")
            print(f"  🤖 Models: {self.current_gpu_info.models_loaded}")
            print(f"  🤖 GPU Available: {'Yes' if self.current_gpu_info.gpu_available else 'No'}")
            
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
        description="VRAM-Aware Capability Tester - Real VRAM-based job delay logic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 60 jobs/min base rate for agent-001
  python single_orchestrator_tester.py --agent agent-001 --rate 60
  
  # Test multiple capabilities
  python single_orchestrator_tester.py --agent agent-001 --rate 30 --capabilities gpu-check text-to-image
  
  # Test with frequent GPU checks (every 10 seconds)  
  python single_orchestrator_tester.py --agent agent-001 --rate 60 --uptime-interval 10

VRAM-Based Delay Logic:
  - Case 2a: VRAM > 30GB + models loaded: No delay (full rate)
  - Case 2b: VRAM < 30GB but > 1GB: 5 second delay between jobs
  - Case 2b: VRAM < 1GB: 15 second delay between jobs
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
        help='Base jobs per minute for Case 2a (VRAM>30GB+models) (default: 60)'
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
        default='http://localhost:9999',
        help='Direct Livepeer gateway URL (default: http://localhost:9999, no Caddy)'
    )
    
    parser.add_argument(
        '--uptime-interval',
        type=int,
        default=30,
        help='How often to query GPU status in seconds (default: 30)'
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
        gpu_query_interval=args.uptime_interval
    )
    
    try:
        await tester.run_job_loop()
    finally:
        tester.print_statistics()

if __name__ == "__main__":
    asyncio.run(main())