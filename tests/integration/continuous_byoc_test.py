#!/usr/bin/env python3
"""
Continuous BYOC testing to verify payment flow
Sends jobs at regular intervals and monitors the response
"""

import asyncio
import aiohttp
import json
import base64
import time
from datetime import datetime

GATEWAY_URL = "http://localhost:8935"
JOBS_PER_MINUTE = 10
DURATION_MINUTES = 2


async def send_byoc_job(session, job_id):
    """Send a single BYOC job through the gateway"""
    
    payload = {
        "action": "gpu-check",
        "agent_id": f"continuous-test-{job_id}",
        "include_utilization": True,
        "timestamp": time.time()
    }
    
    # Create Livepeer headers for BYOC
    job_header = base64.b64encode(json.dumps({
        "request": json.dumps({"run": "agent-net"}),
        "parameters": json.dumps({}),
        "capability": "agent-net",
        "timeout_seconds": 10
    }).encode()).decode()
    
    headers = {
        'Content-Type': 'application/json',
        'Livepeer': job_header
    }
    
    endpoint = f"{GATEWAY_URL}/process/request/agent-net"
    
    try:
        start_time = time.time()
        async with session.post(endpoint, json=payload, headers=headers, timeout=10) as resp:
            response_time = (time.time() - start_time) * 1000  # ms
            
            if resp.status == 200:
                data = await resp.json()
                
                # Check for payment headers
                payment_balance = resp.headers.get('Livepeer-Payment-Balance', 'N/A')
                
                return {
                    "job_id": job_id,
                    "status": "success",
                    "response_time_ms": response_time,
                    "payment_balance": payment_balance,
                    "gpu_count": data.get("gpu_count", 0),
                    "models": data.get("total_models", 0)
                }
            else:
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": f"HTTP {resp.status}",
                    "response_time_ms": response_time
                }
    except Exception as e:
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e)
        }


async def run_continuous_test():
    """Run continuous BYOC test"""
    print("=" * 60)
    print("CONTINUOUS BYOC PAYMENT TEST")
    print("=" * 60)
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Jobs per minute: {JOBS_PER_MINUTE}")
    print(f"Test duration: {DURATION_MINUTES} minutes")
    print(f"Total jobs to send: {JOBS_PER_MINUTE * DURATION_MINUTES}")
    print("=" * 60)
    
    job_interval = 60.0 / JOBS_PER_MINUTE
    total_jobs = JOBS_PER_MINUTE * DURATION_MINUTES
    
    successful_jobs = 0
    failed_jobs = 0
    total_response_time = 0
    
    async with aiohttp.ClientSession() as session:
        for job_id in range(1, total_jobs + 1):
            # Send job
            result = await send_byoc_job(session, job_id)
            
            # Update statistics
            if result["status"] == "success":
                successful_jobs += 1
                total_response_time += result["response_time_ms"]
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Job #{job_id}: ✅ {result['response_time_ms']:.0f}ms | "
                      f"Balance: {result['payment_balance']} | "
                      f"GPU: {result['gpu_count']} | Models: {result['models']}")
            else:
                failed_jobs += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Job #{job_id}: ❌ {result.get('error', 'Unknown error')}")
            
            # Print periodic statistics
            if job_id % 10 == 0:
                avg_response = total_response_time / successful_jobs if successful_jobs > 0 else 0
                print(f"\n--- Stats after {job_id} jobs ---")
                print(f"Success: {successful_jobs}/{job_id} ({successful_jobs/job_id*100:.1f}%)")
                print(f"Avg Response: {avg_response:.0f}ms")
                print("")
            
            # Wait for next job (unless it's the last one)
            if job_id < total_jobs:
                await asyncio.sleep(job_interval)
    
    # Final statistics
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    print(f"Total Jobs: {total_jobs}")
    print(f"Successful: {successful_jobs}")
    print(f"Failed: {failed_jobs}")
    print(f"Success Rate: {successful_jobs/total_jobs*100:.1f}%")
    if successful_jobs > 0:
        print(f"Avg Response Time: {total_response_time/successful_jobs:.0f}ms")
    print("=" * 60)
    
    print("\n📊 Check payment logs:")
    print("  docker logs payment-distributor --tail 20")
    print("  docker logs livepeer-gateway | grep -i payment | tail -10")
    print("  docker logs livepeer-orchestrator | grep agent-net | tail -10")


async def main():
    """Main entry point"""
    try:
        await run_continuous_test()
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")


if __name__ == "__main__":
    asyncio.run(main())