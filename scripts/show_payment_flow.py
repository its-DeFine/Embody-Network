#!/usr/bin/env python3
"""
Show the complete BYOC payment flow in action
"""

import asyncio
import aiohttp
import json
import base64
import time
from datetime import datetime


async def show_flow():
    """Show the complete payment flow"""
    print("=" * 70)
    print("BYOC SERVICE MONITORING PAYMENT FLOW")
    print("=" * 70)
    print()
    
    # 1. Show registered capability
    print("1️⃣  ORCHESTRATOR CAPABILITY REGISTRATION")
    print("   The worker registers 'agent-net' capability with orchestrator")
    print("   Price: 0 (payments based on uptime, not per-job)")
    print("   Check: docker logs livepeer-orchestrator | grep 'registered capability'")
    print()
    
    # 2. Show service monitoring
    print("2️⃣  SERVICE MONITORING (Worker)")
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:9876/service-uptime") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"   Services Monitored: {data['total_services']}")
                print(f"   Services Up: {data['services_up']}")
                print(f"   Uptime: {data['overall_uptime_percentage']:.2f}%")
                print(f"   Payment Eligible: {data['eligible_for_payment']}")
    print()
    
    # 3. Send BYOC job through gateway
    print("3️⃣  BYOC JOB PROCESSING (Gateway → Orchestrator → Worker)")
    
    payload = {
        "action": "check",
        "agent_id": "flow-demo",
        "timestamp": time.time()
    }
    
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
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        async with session.post(
            "http://localhost:8935/process/request/agent-net",
            json=payload,
            headers=headers,
            timeout=10
        ) as resp:
            response_time = (time.time() - start_time) * 1000
            
            if resp.status == 200:
                text = await resp.text()
                data = json.loads(text)
                print(f"   ✅ Job processed in {response_time:.0f}ms")
                print(f"   Services Status: {data['services']['up']}/{data['services']['total']} up")
                print(f"   Uptime: {data['services']['uptime_percentage']:.1f}%")
                print(f"   Eligible: {data['services']['eligible_for_payment']}")
    print()
    
    # 4. Payment distribution
    print("4️⃣  PAYMENT DISTRIBUTION (Every 60 seconds)")
    print("   Payment Distributor checks service uptime")
    print("   If uptime > 95%, pays $10 to orchestrator")
    print("   Check: docker logs payment-distributor | grep autonomy-orchestrator | tail -5")
    print()
    
    # 5. Show payment stats
    print("5️⃣  PAYMENT STATISTICS")
    try:
        # Get latest from payment distributor logs
        import subprocess
        result = subprocess.run(
            ["docker", "logs", "payment-distributor", "--tail", "100"],
            capture_output=True,
            text=True
        )
        
        # Parse for totals
        for line in result.stdout.split('\n'):
            if "Total Payments Made:" in line:
                print(f"   {line.strip().replace('INFO - ', '')}")
            elif "Total Amount Distributed:" in line:
                print(f"   {line.strip().replace('INFO - ', '')}")
    except:
        print("   Check: docker logs payment-distributor | grep 'Total'")
    
    print()
    print("=" * 70)
    print("FLOW SUMMARY")
    print("=" * 70)
    print("1. Worker monitors VTuber services (Docker containers)")
    print("2. Gateway receives BYOC requests, forwards to orchestrator")
    print("3. Orchestrator processes via worker (price=0, no blockchain tickets)")
    print("4. Worker returns service status instead of GPU info")
    print("5. Payment distributor checks uptime every minute")
    print("6. Pays $10/minute when services maintain >95% uptime")
    print()
    print("This is NOT traditional Livepeer video transcoding payments!")
    print("This is BYOC for service monitoring with custom payment logic.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(show_flow())