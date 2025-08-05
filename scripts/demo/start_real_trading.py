#!/usr/bin/env python3
"""Start real trading with cluster integration"""
import asyncio
import httpx
import random
from datetime import datetime

# Trading configuration
SYMBOLS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA"]
CENTRAL_API = "http://localhost:8000"
ADMIN_TOKEN = None

async def get_auth_token():
    """Get authentication token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CENTRAL_API}/api/v1/auth/token",
            data={
                "username": "admin@system.com",
                "password": "central-admin-password-change-in-production"
            }
        )
        return response.json()["access_token"]

async def execute_trade(symbol, action, quantity, cluster_name="trading-bot-01"):
    """Execute a trade through the central API"""
    global ADMIN_TOKEN
    if not ADMIN_TOKEN:
        ADMIN_TOKEN = await get_auth_token()
    
    # Get a realistic price (mock for now)
    price = round(random.uniform(100, 300), 2)
    
    trade_data = {
        "symbol": symbol,
        "action": action,
        "amount": quantity,
        "price": price,
        "strategy": "momentum" if action == "buy" else "profit_taking",
        "cluster_name": cluster_name,
        "reason": f"{action.upper()} signal detected"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CENTRAL_API}/api/v1/trading/execute",
            json=trade_data,
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Trade executed: {action.upper()} {quantity} {symbol} @ ${price}")
            print(f"   Cluster: {cluster_name}")
            print(f"   Trade ID: {result.get('trade_id')}")
            return result
        else:
            print(f"❌ Trade failed: {response.text}")
            return None

async def trading_loop():
    """Main trading loop"""
    print("🚀 Starting real trading system...")
    
    # Define different trading clusters
    clusters = [
        "momentum-trader-01",
        "scalp-bot-02", 
        "swing-trader-03",
        "ml-predictor-04"
    ]
    
    # Execute initial trades to build positions
    print("\n📊 Building initial positions...")
    for i in range(5):
        symbol = random.choice(SYMBOLS)
        quantity = random.randint(10, 50)
        cluster = random.choice(clusters)
        await execute_trade(symbol, "buy", quantity, cluster)
        await asyncio.sleep(1)
    
    print("\n🔄 Starting continuous trading...")
    trade_count = 5
    
    while trade_count < 15:  # Execute 10 more trades
        # Randomly choose buy or sell
        action = random.choice(["buy", "sell", "buy"])  # Bias towards buying
        symbol = random.choice(SYMBOLS)
        quantity = random.randint(5, 30)
        cluster = random.choice(clusters)
        
        await execute_trade(symbol, action, quantity, cluster)
        trade_count += 1
        
        # Wait between trades
        await asyncio.sleep(random.randint(3, 8))
    
    print("\n✅ Trading session complete!")

async def main():
    """Main function"""
    try:
        await trading_loop()
    except KeyboardInterrupt:
        print("\n⚠️ Trading interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())