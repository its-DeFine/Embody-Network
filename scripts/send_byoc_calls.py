#!/usr/bin/env python3
"""
Send BYOC calls directly to orchestrator to trigger work and payments
Based on the original multi_orchestrator_tester.py
"""

import requests
import time
import json
import asyncio
import aiohttp
import base64
from datetime import datetime

# Configuration
ORCHESTRATOR_URL = "https://172.23.0.7:9995"  # Direct to orchestrator
WORKER_URL = "http://localhost:9876"  # Direct to worker for testing
GATEWAY_URL = "http://localhost:8935"  # Gateway HTTP endpoint

async def send_direct_to_worker():
    """Test direct call to worker"""
    print("\n=== Testing Direct Worker Call ===")
    
    payload = {
        "action": "gpu-check",
        "agent_id": "test-001",
        "include_utilization": True,
        "timestamp": time.time()
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Direct to worker endpoint
            async with session.post(f"{WORKER_URL}/agent-net", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Worker responded: {json.dumps(data, indent=2)}")
                    return True
                else:
                    print(f"❌ Worker error: {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ Failed to reach worker: {e}")
        return False

async def send_via_orchestrator():
    """Send BYOC call through orchestrator (with capability)"""
    print("\n=== Testing Orchestrator BYOC Call ===")
    
    # The orchestrator expects a specific format for capability calls
    payload = {
        "capability": "agent-net",
        "request": {
            "action": "gpu-check",
            "agent_id": "orch-test-001",
            "include_utilization": True,
            "timestamp": time.time()
        }
    }
    
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            # Try orchestrator RPC endpoint
            async with session.post(
                f"{ORCHESTRATOR_URL}/rpc", 
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.text()
                    print(f"✅ Orchestrator responded: {data}")
                    return True
                else:
                    print(f"❌ Orchestrator error: {resp.status}")
                    text = await resp.text()
                    print(f"   Response: {text}")
                    return False
    except Exception as e:
        print(f"❌ Failed to reach orchestrator: {e}")
        return False

async def send_service_check():
    """Check service monitoring"""
    print("\n=== Testing Service Monitoring ===")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Check service uptime
            async with session.get(f"{WORKER_URL}/service-uptime") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Service Status:")
                    print(f"   Uptime: {data['overall_uptime_percentage']:.2f}%")
                    print(f"   Services Up: {data['services_up']}/{data['total_services']}")
                    print(f"   Eligible for Payment: {data['eligible_for_payment']}")
                    return True
                else:
                    print(f"❌ Service check failed: {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ Failed service check: {e}")
        return False

async def trigger_payment_flow():
    """Try to trigger actual payment flow"""
    print("\n=== Attempting to Trigger Payment Flow ===")
    
    # For BYOC, payments happen when:
    # 1. Gateway receives a request for a capability
    # 2. Gateway forwards to orchestrator
    # 3. Orchestrator processes via worker
    # 4. Result returned triggers payment
    
    # Use the correct BYOC endpoint format from pipelines_tests
    payload = {
        "action": "gpu-check",
        "agent_id": "gateway-test-001",
        "include_utilization": True,
        "timestamp": time.time()
    }
    
    # Create proper Livepeer headers for BYOC
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
    
    # The correct endpoint for BYOC with pr-3650
    endpoint = f"{GATEWAY_URL}/process/request/agent-net"
    
    async with aiohttp.ClientSession() as session:
        try:
            print(f"\nTrying BYOC endpoint: {endpoint}")
            print(f"Headers: {headers}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            async with session.post(endpoint, json=payload, headers=headers, timeout=10) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.text()
                    print(f"   ✅ Success! Response: {data[:200]}")
                    
                    # Check for payment headers
                    if 'Livepeer-Payment-Balance' in resp.headers:
                        print(f"   💰 Payment Balance: {resp.headers['Livepeer-Payment-Balance']}")
                    
                    return True
                else:
                    text = await resp.text()
                    print(f"   ❌ Error: {text[:200]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return False

async def main():
    """Run all tests"""
    print("=" * 60)
    print("BYOC CALL TESTING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    
    # Test direct worker
    await send_direct_to_worker()
    
    # Test service monitoring
    await send_service_check()
    
    # Try orchestrator
    await send_via_orchestrator()
    
    # Try to trigger payment
    await trigger_payment_flow()
    
    print("\n" + "=" * 60)
    print("MONITORING LOGS")
    print("=" * 60)
    print("\nCheck logs with:")
    print("  docker logs livepeer-gateway | grep -i payment")
    print("  docker logs livepeer-orchestrator | grep -i payment")
    print("  docker logs payment-distributor --tail 20")

if __name__ == "__main__":
    asyncio.run(main())