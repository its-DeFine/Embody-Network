#!/usr/bin/env python3
"""
Central Manager API Demo
Interactive demonstration of API calls to manage agents and the trading system.
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkB0cmFkaW5nLnN5c3RlbSIsImV4cCI6MTc1NDQxMTM2M30.ynYErbxgV16D7pTmRQNhXdR_6j_i9qyYRYMfNEkO9Zw"
AGENT_ID = "e2a8428e-4927-4c3b-93bc-1f49f779516b"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def make_request(method, endpoint, data=None):
    """Make an API request and return the response"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print(f"{'='*60}")

def print_api_call(method, endpoint, description):
    """Print API call details"""
    print(f"\n📡 {method} {endpoint}")
    print(f"   {description}")

def demo_api_interactions():
    """Demonstrate various API interactions"""
    
    print("🎛️ Central Manager API Demo")
    print("🤖 Agent Management & Trading System Control")
    print(f"⏰ Demo Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. System Health & Status
    print_section("System Health & Status Monitoring")
    
    print_api_call("GET", "/health", "Basic system health check")
    health = make_request("GET", "/health")
    print(f"   Status: {health.get('status', 'unknown')}")
    
    print_api_call("GET", "/api/v1/management/system/status", "Detailed system status")
    system_status = make_request("GET", "/api/v1/management/system/status")
    print(f"   Components: {len(system_status.get('components', {}))}")
    
    # 2. Agent Management
    print_section("Agent Management")
    
    print_api_call("GET", "/api/v1/agents", "List all agents")
    agents = make_request("GET", "/api/v1/agents")
    print(f"   Active Agents: {len(agents) if isinstance(agents, list) else 0}")
    
    if agents and len(agents) > 0:
        agent = agents[0]
        print(f"   Agent: {agent['name']} ({agent['type']}) - Status: {agent['status']}")
        
        print_api_call("GET", f"/api/v1/agents/{AGENT_ID}", "Get specific agent details")
        agent_details = make_request("GET", f"/api/v1/agents/{AGENT_ID}")
        print(f"   Config: Risk={agent_details.get('config', {}).get('risk_tolerance', 'N/A')}")
    
    # 3. Trading System Control
    print_section("Trading System Control")
    
    print_api_call("GET", "/api/v1/trading/status", "Get trading system status")
    trading_status = make_request("GET", "/api/v1/trading/status")
    print(f"   Trading Active: {trading_status.get('data', {}).get('is_running', False)}")
    
    print_api_call("GET", "/api/v1/trading/portfolio", "Get portfolio status")
    portfolio = make_request("GET", "/api/v1/trading/portfolio")
    if "error" not in portfolio:
        print(f"   Portfolio Value: ${portfolio.get('data', {}).get('total_value', 'N/A')}")
    else:
        print(f"   Portfolio: {portfolio.get('error', 'Not available')}")
    
    # 4. Market Data
    print_section("Market Data Integration")
    
    print_api_call("GET", "/api/v1/market/status", "Market data service status")
    market_status = make_request("GET", "/api/v1/market/status")
    print(f"   Market Data: {market_status.get('status', 'unknown')}")
    
    print_api_call("GET", "/api/v1/market/symbols", "Available trading symbols")
    symbols = make_request("GET", "/api/v1/market/symbols")
    if isinstance(symbols, list):
        print(f"   Available Symbols: {len(symbols)}")
    
    # 5. GPU & System Resources
    print_section("GPU & System Resources")
    
    print_api_call("GET", "/api/v1/gpu/status", "GPU orchestrator status")
    gpu_status = make_request("GET", "/api/v1/gpu/status")
    print(f"   GPU Status: {gpu_status.get('status', 'unknown')}")
    
    print_api_call("GET", "/api/v1/management/system/resources", "System resource usage")
    resources = make_request("GET", "/api/v1/management/system/resources")
    print(f"   Resources: {resources.get('status', 'unknown')}")
    
    # 6. Team & Task Management
    print_section("Team & Task Coordination")
    
    print_api_call("GET", "/api/v1/teams", "List teams")
    teams = make_request("GET", "/api/v1/teams")
    print(f"   Active Teams: {len(teams) if isinstance(teams, list) else 0}")
    
    print_api_call("GET", "/api/v1/tasks", "List tasks")
    tasks = make_request("GET", "/api/v1/tasks")
    print(f"   Active Tasks: {len(tasks) if isinstance(tasks, list) else 0}")
    
    # 7. Audit & Security
    print_section("Audit & Security Monitoring")
    
    print_api_call("GET", "/api/v1/audit/system-health", "System health audit")
    audit_health = make_request("GET", "/api/v1/audit/system-health")
    print(f"   Audit Status: {audit_health.get('status', 'unknown')}")
    
    print_api_call("GET", "/api/v1/security/status", "Security system status")
    security_status = make_request("GET", "/api/v1/security/status")
    print(f"   Security: {security_status.get('status', 'unknown')}")
    
    # 8. Advanced Features
    print_section("Advanced Features")
    
    print_api_call("GET", "/api/v1/ollama/models", "Available LLM models")
    ollama_models = make_request("GET", "/api/v1/ollama/models")
    if isinstance(ollama_models, list):
        print(f"   Available Models: {len(ollama_models)}")
    
    print_api_call("GET", "/api/v1/dex/chains", "DEX trading chains")
    dex_chains = make_request("GET", "/api/v1/dex/chains")
    if isinstance(dex_chains, list):
        print(f"   Supported Chains: {len(dex_chains)}")
    
    # 9. Agent Control Demo
    print_section("Agent Control Demonstration")
    
    if agents and len(agents) > 0:
        print_api_call("POST", f"/api/v1/agents/{AGENT_ID}/stop", "Stop agent")
        stop_result = make_request("POST", f"/api/v1/agents/{AGENT_ID}/stop")
        print(f"   Stop Result: {stop_result.get('message', 'unknown')}")
        
        time.sleep(2)
        
        print_api_call("POST", f"/api/v1/agents/{AGENT_ID}/start", "Restart agent")
        start_result = make_request("POST", f"/api/v1/agents/{AGENT_ID}/start")
        print(f"   Start Result: {start_result.get('message', 'unknown')}")
    
    # 10. Summary
    print_section("Demo Summary")
    print("✅ Central Manager API Demo Complete!")
    print("📊 Tested major API categories:")
    print("   - System Health & Monitoring")
    print("   - Agent Lifecycle Management")
    print("   - Trading System Control")
    print("   - Market Data Integration")
    print("   - Resource Management")
    print("   - Team & Task coordination")
    print("   - Audit & Security")
    print("   - Advanced Features (LLM, DEX)")
    print("   - Real-time Agent Control")
    print(f"\n🌐 Full API Documentation: {BASE_URL}/docs")

if __name__ == "__main__":
    demo_api_interactions()