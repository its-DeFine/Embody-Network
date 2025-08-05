#!/usr/bin/env python3
"""Capture exact dashboard state and rendering"""
import requests
import json
from datetime import datetime

print("=== CAPTURING DASHBOARD STATE ===")
print(f"Time: {datetime.now()}")

# Get all API data
apis = {
    "trading_status": "http://localhost:8000/api/v1/trading/status",
    "portfolio_status": "http://localhost:8000/dashboard/api/portfolio-status",
    "cluster_status": "http://localhost:8000/dashboard/api/cluster-status"
}

data = {}
for name, url in apis.items():
    resp = requests.get(url)
    data[name] = resp.json()
    print(f"\n{name}: {resp.status_code}")

# Save complete state
with open("dashboard_state.json", "w") as f:
    json.dump(data, f, indent=2)

# Simulate dashboard JavaScript logic
print("\n=== SIMULATING DASHBOARD JAVASCRIPT ===")

# Extract system data
system = data["trading_status"].get("data", data["trading_status"])
portfolio = data["portfolio_status"]
clusters = data["cluster_status"]

print(f"\nSystem Status:")
print(f"  is_running: {system.get('is_running', 'MISSING')}")
print(f"  overall_health: {system.get('overall_health', 'MISSING')}")
print(f"  portfolio_value: {system.get('portfolio_value', 'MISSING')}")
print(f"  total_trades: {system.get('total_trades', 'MISSING')}")

print(f"\nPortfolio Status:")
print(f"  total_value: ${portfolio.get('total_value', 0):,.2f}")
print(f"  cash_balance: ${portfolio.get('cash_balance', 0):,.2f}")
print(f"  positions_value: ${portfolio.get('positions_value', 0):,.2f}")
print(f"  positions: {list(portfolio.get('positions', {}).keys())}")

# Check for rendering issues
print("\n=== CHECKING FOR ISSUES ===")
issues = []

# Check system values
if system.get('portfolio_value') is None:
    issues.append("System portfolio_value is null")
if not isinstance(system.get('total_trades', 0), (int, float)):
    issues.append(f"System total_trades is not a number: {system.get('total_trades')}")

# Check portfolio values
if portfolio.get('total_value') != portfolio.get('cash_balance') + portfolio.get('positions_value', 0):
    calculated = portfolio.get('cash_balance', 0) + portfolio.get('positions_value', 0)
    issues.append(f"Portfolio total mismatch: {portfolio.get('total_value')} != {calculated}")

# Check positions
for symbol, pos in portfolio.get('positions', {}).items():
    if pos.get('current_price') is None:
        issues.append(f"Position {symbol} has null current_price")
    if pos.get('market_value') is None:
        issues.append(f"Position {symbol} has null market_value")

if issues:
    print("FOUND ISSUES:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("No obvious issues found")

print("\n=== DASHBOARD RENDERING EXPECTATIONS ===")
print(f"1. System card should show:")
print(f"   - Status: {'Online' if system.get('is_running') else 'Offline'}")
print(f"   - Total Trades: {system.get('total_trades', 0)}")
print(f"   - Portfolio Value: ${system.get('portfolio_value', 0) or 0:.2f}")

print(f"\n2. Portfolio card should show:")
print(f"   - Total Value: ${portfolio.get('total_value', 0):,.2f}")
print(f"   - Cash Balance: ${portfolio.get('cash_balance', 0):,.2f}")
print(f"   - Positions: {len(portfolio.get('positions', {}))}")

print("\nCheck dashboard_state.json for complete data")