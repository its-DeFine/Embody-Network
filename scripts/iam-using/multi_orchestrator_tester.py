#!/usr/bin/env python3
"""
Multi-Orchestrator GPU-Aware Capability Tester
Tests multiple orchestrators with different agents and applies punishment logic based on GPU/VRAM usage via Ollama.
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
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

@dataclass
class OrchestratorConfig:
    """Configuration for a single orchestrator"""
    name: str
    gateway_url: str
    agent_id: str
    
@dataclass
class JobResult:
    """Result of a single job request"""
    orchestrator: str
    agent_id: str
    capability: str
    status_code: int
    response_time: float
    uptime_percent: float
    timestamp: datetime
    error: Optional[str] = None
    model_name: Optional[str] = None
    vram_mb: Optional[float] = None

class MultiOrchestratorTester:
    """Tests multiple orchestrators with uptime-aware punishment logic"""
    
    def __init__(self, 
                 orchestrators: List[OrchestratorConfig],
                 base_jobs_per_minute: int = 60,
                 capabilities: List[str] = ["gpu-check"],
                 test_duration: int = 60):
        """
        Initialize the multi-orchestrator tester
        
        Args:
            orchestrators: List of orchestrator configurations
            base_jobs_per_minute: Base job rate for 99%+ uptime
            capabilities: List of capabilities to test
            test_duration: How long to run the test (seconds)
        """
        self.orchestrators = orchestrators
        self.base_jobs_per_minute = base_jobs_per_minute
        self.capabilities = capabilities
        self.test_duration = test_duration
        
        self.running = True
        self.results: List[JobResult] = []
        self.agent_uptimes: Dict[str, float] = {}
        self.agent_models: Dict[str, str] = {}
        self.agent_vram: Dict[str, float] = {}
        self.start_time = time.time()
        
    async def get_agent_uptime(self, orch: OrchestratorConfig) -> Tuple[float, str, float]:
        """Query worker GPU check endpoint for GPU/VRAM status"""
        try:
            async with aiohttp.ClientSession() as session:
                # Query worker's GPU check endpoint through gateway
                url = f"{orch.gateway_url.rstrip('/')}/worker/gpu-check"
                payload = {"agent_id": orch.agent_id}
                
                async with session.post(url, json=payload, timeout=5) as resp:
                    if resp.status != 200:
                        print(f"{RED}❌ Failed to get GPU status for {orch.name}: HTTP {resp.status}{RESET}")
                        return 85.0, "No GPU data", 0.0  # Default to low uptime
                        
                    data = await resp.json()
                    
                    # Extract data from response
                    uptime = data.get('uptime_percent', 85.0)
                    model_name = data.get('model_name', 'Unknown')
                    total_vram_mb = data.get('vram_usage_mb', 0.0)
                    
                    key = f"{orch.name}:{orch.agent_id}"
                    self.agent_uptimes[key] = uptime
                    self.agent_models[key] = model_name
                    self.agent_vram[key] = total_vram_mb
                    return uptime, model_name, total_vram_mb
                    
        except Exception as e:
            print(f"{RED}❌ Error querying GPU status for {orch.name}: {e}{RESET}")
            return 85.0, "Error", 0.0
            
    def calculate_job_rate(self, uptime_percent: float) -> int:
        """Calculate jobs per minute based on uptime percentage"""
        if uptime_percent >= 99.0:
            return self.base_jobs_per_minute
        elif uptime_percent >= 95.0:
            return int(self.base_jobs_per_minute * 0.5)
        elif uptime_percent >= 90.0:
            return int(self.base_jobs_per_minute * 0.1)
        else:
            return 0
            
    def create_livepeer_headers(self, capability: str) -> Dict[str, str]:
        """Create proper Livepeer headers for gateway requests"""
        job_header = base64.b64encode(json.dumps({
            "request": json.dumps({"run": "agent-net"}),
            "parameters": json.dumps({}),
            "capability": "agent-net",
            "timeout_seconds": 30
        }).encode()).decode()
        
        return {
            'Content-Type': 'application/json',
            'Livepeer': job_header
        }
        
    async def send_job(self, orch: OrchestratorConfig, capability: str, uptime: float, model_name: str, vram_mb: float) -> JobResult:
        """Send a single job to an orchestrator"""
        start_time = time.time()
        
        try:
            headers = self.create_livepeer_headers(capability)
            payload = {
                "action": "gpu-check",
                "agent_id": orch.agent_id,
                "include_utilization": True,
                "timestamp": time.time()
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{orch.gateway_url}/gateway/process/request/agent-net"
                
                async with session.post(url, headers=headers, json=payload, timeout=25) as resp:
                    response_time = (time.time() - start_time) * 1000
                    
                    return JobResult(
                        orchestrator=orch.name,
                        agent_id=orch.agent_id,
                        capability=capability,
                        status_code=resp.status,
                        response_time=response_time,
                        uptime_percent=uptime,
                        timestamp=datetime.now(),
                        error=None if resp.status == 200 else f"HTTP {resp.status}",
                        model_name=model_name,
                        vram_mb=vram_mb
                    )
                    
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return JobResult(
                orchestrator=orch.name,
                agent_id=orch.agent_id,
                capability=capability,
                status_code=0,
                response_time=response_time,
                uptime_percent=uptime,
                timestamp=datetime.now(),
                error="Request timeout",
                model_name=model_name,
                vram_mb=vram_mb
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return JobResult(
                orchestrator=orch.name,
                agent_id=orch.agent_id,
                capability=capability,
                status_code=-1,
                response_time=response_time,
                uptime_percent=uptime,
                timestamp=datetime.now(),
                error=str(e),
                model_name=model_name,
                vram_mb=vram_mb
            )
            
    async def run_test_loop(self):
        """Main test loop that sends jobs to multiple orchestrators"""
        print(f"\n{BLUE}🚀 MULTI-ORCHESTRATOR UPTIME-AWARE TEST STARTED{RESET}")
        print(f"📦 Base Job Rate: {self.base_jobs_per_minute} jobs/min")
        print(f"🎪 Capabilities: {', '.join(self.capabilities)}")
        print(f"⏱️  Test Duration: {self.test_duration} seconds")
        print(f"🌐 Orchestrators: {len(self.orchestrators)}")
        for orch in self.orchestrators:
            print(f"   - {orch.name}: {orch.gateway_url} (Agent: {orch.agent_id})")
        print("=" * 80)
        
        # Initial GPU check for all orchestrators
        print(f"\n{YELLOW}Checking initial GPU status (via Ollama) for all agents...{RESET}")
        for orch in self.orchestrators:
            gpu_score, model_name, vram_mb = await self.get_agent_uptime(orch)
            job_rate = self.calculate_job_rate(gpu_score)
            print(f"  {orch.name} ({orch.agent_id}): {model_name} | {vram_mb:.0f}MB VRAM | {gpu_score:.1f}% score → {job_rate} jobs/min")
        
        print(f"\n{GREEN}Starting job distribution...{RESET}")
        print(f"{BLUE}💡 VRAM Mapping: <2GB=99.5%, 2-4GB=98%, 4-6GB=92%, >6GB=85%{RESET}")
        print("=" * 80)
        
        # Track job counts per orchestrator
        job_counts = {orch.name: 0 for orch in self.orchestrators}
        last_uptime_check = time.time()
        
        while self.running and (time.time() - self.start_time) < self.test_duration:
            # Refresh uptime every 30 seconds
            if time.time() - last_uptime_check > 30:
                for orch in self.orchestrators:
                    _, _, _ = await self.get_agent_uptime(orch)
                last_uptime_check = time.time()
            
            # Select orchestrators that can receive jobs based on uptime
            eligible_orchestrators = []
            for orch in self.orchestrators:
                uptime = self.agent_uptimes.get(f"{orch.name}:{orch.agent_id}", 0)
                job_rate = self.calculate_job_rate(uptime)
                if job_rate > 0:
                    # Add orchestrator multiple times based on its rate ratio
                    weight = int(job_rate / 10)  # Normalize to make selection fair
                    eligible_orchestrators.extend([orch] * max(1, weight))
            
            if not eligible_orchestrators:
                print(f"\n{RED}⚠️  No orchestrators eligible for jobs (all have low GPU scores){RESET}")
                await asyncio.sleep(5)
                continue
            
            # Select a random orchestrator from eligible ones
            selected_orch = random.choice(eligible_orchestrators)
            capability = random.choice(self.capabilities)
            
            # Get current GPU info for the selected orchestrator
            key = f"{selected_orch.name}:{selected_orch.agent_id}"
            uptime = self.agent_uptimes.get(key, 0)
            model_name = self.agent_models.get(key, "Unknown")
            vram_mb = self.agent_vram.get(key, 0.0)
            job_rate = self.calculate_job_rate(uptime)
            
            # Send the job
            result = await self.send_job(selected_orch, capability, uptime, model_name, vram_mb)
            self.results.append(result)
            job_counts[selected_orch.name] += 1
            
            # Log the result
            status_emoji = "✅" if result.status_code == 200 else "❌"
            print(f"{status_emoji} [{datetime.now().strftime('%H:%M:%S')}] "
                  f"{selected_orch.name}: {result.status_code} ({result.response_time:.0f}ms) | "
                  f"Model: {model_name} | VRAM: {vram_mb:.0f}MB | Rate: {job_rate}/min")
            
            # Calculate delay based on aggregate job rate
            total_job_rate = sum(self.calculate_job_rate(u) for u in self.agent_uptimes.values())
            if total_job_rate > 0:
                delay = 60.0 / total_job_rate
            else:
                delay = 5.0  # Default delay if no jobs allowed
                
            await asyncio.sleep(delay)
        
        print(f"\n{GREEN}Test completed!{RESET}")
        self.print_summary(job_counts)
        
    def print_summary(self, job_counts: Dict[str, int]):
        """Print test summary and statistics"""
        print(f"\n{BLUE}📊 TEST SUMMARY{RESET}")
        print("=" * 80)
        
        total_duration = time.time() - self.start_time
        total_jobs = len(self.results)
        
        print(f"⏱️  Total Duration: {total_duration:.1f} seconds")
        print(f"📤 Total Jobs Sent: {total_jobs}")
        print(f"📊 Average Rate: {(total_jobs / total_duration * 60):.1f} jobs/min")
        
        # Per-orchestrator statistics
        print(f"\n{YELLOW}Per-Orchestrator Statistics:{RESET}")
        for orch in self.orchestrators:
            orch_results = [r for r in self.results if r.orchestrator == orch.name]
            if not orch_results:
                print(f"\n  {orch.name}: No jobs sent")
                continue
                
            successful = sum(1 for r in orch_results if r.status_code == 200)
            avg_response_time = sum(r.response_time for r in orch_results) / len(orch_results)
            key = f"{orch.name}:{orch.agent_id}"
            uptime = self.agent_uptimes.get(key, 0)
            model = self.agent_models.get(key, "Unknown")
            vram = self.agent_vram.get(key, 0.0)
            
            print(f"\n  {orch.name} ({orch.agent_id}):")
            print(f"    Model: {model}")
            print(f"    VRAM: {vram:.0f} MB")
            print(f"    GPU Score: {uptime:.1f}%")
            print(f"    Jobs Sent: {len(orch_results)}")
            print(f"    Successful: {successful} ({(successful/len(orch_results)*100):.1f}%)")
            print(f"    Avg Response: {avg_response_time:.1f}ms")
            print(f"    Job Rate: {(len(orch_results) / total_duration * 60):.1f} jobs/min")
            
        # Punishment effectiveness
        print(f"\n{YELLOW}Punishment Effectiveness:{RESET}")
        for orch in self.orchestrators:
            uptime = self.agent_uptimes.get(f"{orch.name}:{orch.agent_id}", 0)
            expected_rate = self.calculate_job_rate(uptime)
            actual_jobs = job_counts.get(orch.name, 0)
            actual_rate = (actual_jobs / total_duration * 60)
            
            print(f"  {orch.name}: Expected {expected_rate} jobs/min, Actual {actual_rate:.1f} jobs/min")

def parse_orchestrator_config(config_str: str) -> OrchestratorConfig:
    """Parse orchestrator configuration from string format: name,url,agent_id"""
    parts = config_str.split(',')
    if len(parts) != 3:
        raise ValueError(f"Invalid orchestrator config: {config_str}. Expected format: name,url,agent_id")
    return OrchestratorConfig(name=parts[0], gateway_url=parts[1], agent_id=parts[2])

async def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Multi-Orchestrator Uptime-Aware Capability Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test two orchestrators with different agents
  python multi_orchestrator_tester.py \\
    --orchestrators "orch1,http://localhost:8088,agent-001" \\
                   "orch2,http://localhost:8089,agent-002"
  
  # Test with custom job rate and duration
  python multi_orchestrator_tester.py \\
    --orchestrators "prod,http://prod.example.com:8088,agent-001" \\
                   "staging,http://staging.example.com:8088,agent-002" \\
    --rate 120 --duration 300

Format for orchestrators: name,gateway_url,agent_id
        """
    )
    
    parser.add_argument(
        '--orchestrators',
        nargs='+',
        required=True,
        help='Orchestrator configurations (format: name,url,agent_id)'
    )
    
    parser.add_argument(
        '--rate',
        type=int,
        default=60,
        help='Base jobs per minute for 99%+ uptime (default: 60)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Test duration in seconds (default: 60)'
    )
    
    parser.add_argument(
        '--capabilities',
        nargs='+',
        default=['gpu-check'],
        help='Capabilities to test (default: gpu-check)'
    )
    
    args = parser.parse_args()
    
    # Parse orchestrator configurations
    try:
        orchestrators = [parse_orchestrator_config(c) for c in args.orchestrators]
    except ValueError as e:
        print(f"{RED}Error: {e}{RESET}")
        sys.exit(1)
    
    # Create and run the tester
    tester = MultiOrchestratorTester(
        orchestrators=orchestrators,
        base_jobs_per_minute=args.rate,
        capabilities=args.capabilities,
        test_duration=args.duration
    )
    
    try:
        await tester.run_test_loop()
    except KeyboardInterrupt:
        print(f"\n{RED}Test interrupted by user{RESET}")
        tester.running = False

if __name__ == "__main__":
    asyncio.run(main())