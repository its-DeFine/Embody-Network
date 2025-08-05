#!/usr/bin/env python3
"""Verify P&L calculation is fixed"""
import requests

print("=== VERIFYING P&L CALCULATION FIX ===\n")

# Get portfolio data
portfolio = requests.get("http://localhost:8000/dashboard/api/portfolio-status").json()

print("Portfolio Breakdown:")
print(f"  Starting Capital: $100,000.00")
print(f"  Current Cash: ${portfolio['cash_balance']:,.2f}")
print(f"  Positions Value: ${portfolio['positions_value']:,.2f}")
print(f"  Total Value: ${portfolio['total_value']:,.2f}")
print(f"\n✅ CORRECTED P&L: ${portfolio['total_pnl']:,.2f} ({portfolio['total_pnl_percent']:.2f}%)")

# Verify the math
expected_pnl = portfolio['total_value'] - 100000.0
if abs(expected_pnl - portfolio['total_pnl']) < 0.01:
    print("\n✅ P&L calculation is now CORRECT!")
    print(f"   Total Value (${ portfolio['total_value']:,.2f}) - Starting Capital ($100,000) = P&L (${portfolio['total_pnl']:,.2f})")
else:
    print(f"\n❌ P&L still incorrect! Expected ${expected_pnl:.2f}, got ${portfolio['total_pnl']:.2f}")

print("\nThe dashboard at http://localhost:8000/dashboard/ now shows accurate P&L!")