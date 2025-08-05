#!/usr/bin/env python3
"""Test complete dashboard rendering"""
import requests
import json

print("=== COMPLETE DASHBOARD TEST ===")

# Get all data
apis = {
    "trading": requests.get("http://localhost:8000/api/v1/trading/status").json(),
    "portfolio": requests.get("http://localhost:8000/dashboard/api/portfolio-status").json(),
    "clusters": requests.get("http://localhost:8000/dashboard/api/cluster-status").json()
}

print("\n1. SYSTEM STATUS:")
system = apis["trading"]["data"]
print(f"   Trading Active: {system['is_running']}")
print(f"   Health: {system['overall_health']}")
print(f"   Engine Portfolio: ${system['portfolio_value']:,.2f}")
print(f"   Total Trades: {system['total_trades']}")

print("\n2. PORTFOLIO STATUS:")
portfolio = apis["portfolio"]
print(f"   Total Value: ${portfolio['total_value']:,.2f}")
print(f"   Cash Balance: ${portfolio['cash_balance']:,.2f}")
print(f"   Positions Value: ${portfolio['positions_value']:,.2f}")
print(f"   P&L: ${portfolio['total_pnl']:,.2f} ({portfolio['total_pnl_percent']:.2f}%)")

print("\n3. POSITIONS:")
for symbol, pos in portfolio['positions'].items():
    pnl_color = "🟢" if pos['unrealized_pnl'] > 0 else "🔴"
    print(f"   {symbol}: {pos['quantity']} @ ${pos['average_price']:.2f}")
    print(f"      Current: ${pos['current_price']:.2f}, Value: ${pos['market_value']:,.2f}")
    print(f"      P&L: {pnl_color} ${pos['unrealized_pnl']:,.2f} ({pos['unrealized_pnl_percent']:.2f}%)")

print("\n4. RECENT TRADES:")
for trade in portfolio['recent_trades'][:3]:
    print(f"   {trade['side'].upper()} {trade['symbol']}: {trade['quantity']} @ ${trade['price']}")
    print(f"      Cluster: {trade['cluster_name']}")

print("\n5. CLUSTERS:")
db_clusters = apis["clusters"]["database_clusters"]
print(f"   Registered: {len(db_clusters)}")
for cluster_id, cluster in db_clusters.items():
    print(f"   - {cluster['cluster_name']} ({cluster['agent_type']})")

print("\n✅ Dashboard should display all this data correctly!")