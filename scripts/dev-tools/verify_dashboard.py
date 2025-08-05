#!/usr/bin/env python3
"""Verify dashboard data is accessible"""
import requests
import json

print("=== Dashboard Data Verification ===\n")

# Check trading status
print("1. Trading Status:")
resp = requests.get("http://localhost:8000/api/v1/trading/status")
data = resp.json()
print(f"   - Is Running: {data['data']['is_running']}")
print(f"   - Health: {data['data']['overall_health']}")
print(f"   - Total Trades: {data['data']['total_trades']}")
print(f"   - Portfolio Value: ${data['data']['portfolio_value']:,.2f}")

# Check portfolio
print("\n2. Portfolio Status:")
resp = requests.get("http://localhost:8000/dashboard/api/portfolio-status")
portfolio = resp.json()
print(f"   - Total Value: ${portfolio['total_value']:,.2f}")
print(f"   - Cash Balance: ${portfolio['cash_balance']:,.2f}")
print(f"   - Positions Value: ${portfolio['positions_value']:,.2f}")
print(f"   - Number of Positions: {len(portfolio['positions'])}")
print(f"   - Recent Trades: {len(portfolio['recent_trades'])}")

# Show positions
if portfolio['positions']:
    print("\n3. Current Positions:")
    for symbol, pos in portfolio['positions'].items():
        print(f"   - {symbol}: {pos['quantity']} shares @ ${pos['average_price']:.2f}")
        if 'unrealized_pnl' in pos:
            print(f"     P&L: ${pos['unrealized_pnl']:.2f} ({pos['unrealized_pnl_percent']:.2f}%)")

# Show recent trades
if portfolio['recent_trades']:
    print("\n4. Recent Trades (last 5):")
    for trade in portfolio['recent_trades'][:5]:
        print(f"   - {trade['executed_at'].split('T')[1][:8]} - {trade['side'].upper()} {trade['symbol']}: {trade['quantity']} @ ${trade['price']}")

print("\n✅ Dashboard at http://localhost:8000/dashboard/ should show all this data!")