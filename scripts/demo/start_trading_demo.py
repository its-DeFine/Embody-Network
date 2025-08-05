#!/usr/bin/env python3
"""
Start trading and generate sample trades for demonstration
"""
import requests
import json
import time
import random

# API base URL
BASE_URL = "http://localhost:8000"

# Get auth token
def get_token():
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin-password"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

# Start trading system
def start_trading(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/api/v1/trading/start", 
                           json={"initial_capital": 100000},
                           headers=headers)
    print("Start trading response:", response.json())
    return response.status_code == 200

# Execute a trade
def execute_trade(token, symbol, action, amount, price=None):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current price if not provided
    if not price:
        price = random.uniform(100, 200)
    
    trade_data = {
        "symbol": symbol,
        "action": action,
        "amount": amount,
        "price": price,
        "strategy": "demo_strategy",
        "confidence": 0.8,
        "reason": f"Demo trade - {action} signal detected"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/trading/execute", 
                           json=trade_data,
                           headers=headers)
    print(f"Trade executed: {symbol} {action} {amount} @ ${price:.2f}")
    return response.json()

# Generate sample trades
def generate_demo_trades(token):
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    actions = ["buy", "sell"]
    
    # Execute 10 demo trades
    for i in range(10):
        symbol = random.choice(symbols)
        action = random.choice(actions)
        amount = random.randint(10, 100)
        
        trade_result = execute_trade(token, symbol, action, amount)
        print(f"Trade {i+1} result:", trade_result)
        
        # Wait between trades
        time.sleep(2)

def main():
    # Get token
    token = get_token()
    if not token:
        print("Failed to authenticate")
        return
    
    print("Successfully authenticated")
    
    # Start trading system
    if start_trading(token):
        print("Trading system started successfully")
    else:
        print("Failed to start trading system")
        return
    
    # Wait for system to initialize
    time.sleep(3)
    
    # Generate demo trades
    print("\nGenerating demo trades...")
    generate_demo_trades(token)
    
    # Check portfolio status
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/trading/portfolio", headers=headers)
    print("\nFinal portfolio status:")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    main()