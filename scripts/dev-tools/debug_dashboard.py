#!/usr/bin/env python3
"""Debug dashboard rendering issues"""
import requests
from bs4 import BeautifulSoup
import json

# First, get the raw HTML
print("=== FETCHING DASHBOARD HTML ===")
response = requests.get("http://localhost:8000/dashboard/")
print(f"Status: {response.status_code}")

# Save the HTML for inspection
with open("dashboard_output.html", "w") as f:
    f.write(response.text)
print("Saved HTML to dashboard_output.html")

# Check the API endpoints
print("\n=== CHECKING API ENDPOINTS ===")

# 1. Trading status
print("\n1. Trading Status API:")
resp = requests.get("http://localhost:8000/api/v1/trading/status")
print(f"   Status: {resp.status_code}")
data = resp.json()
print(f"   Data: {json.dumps(data, indent=2)}")

# 2. Portfolio status
print("\n2. Portfolio Status API:")
resp = requests.get("http://localhost:8000/dashboard/api/portfolio-status")
print(f"   Status: {resp.status_code}")
data = resp.json()
print(f"   Total Value: ${data.get('total_value', 0):,.2f}")
print(f"   Cash: ${data.get('cash_balance', 0):,.2f}")
print(f"   Positions: {len(data.get('positions', {}))}")
print(f"   Recent Trades: {len(data.get('recent_trades', []))}")

# 3. Cluster status
print("\n3. Cluster Status API:")
resp = requests.get("http://localhost:8000/dashboard/api/cluster-status")
print(f"   Status: {resp.status_code}")
data = resp.json()
print(f"   Database Clusters: {len(data.get('database_clusters', {}))}")

print("\n=== JAVASCRIPT EXECUTION TEST ===")
print("Open dashboard_output.html in browser and check console for errors")
print("Dashboard URL: http://localhost:8000/dashboard/")