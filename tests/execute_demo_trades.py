#!/usr/bin/env python3
"""Quick demo to execute trades and show P&L"""

import asyncio
import httpx
import json
import time

async def main():
    client = httpx.AsyncClient(timeout=30.0)
    base_url = "http://localhost:8000"
    
    try:
        # Login
        print("🔐 Logging in...")
        response = await client.post(
            f"{base_url}/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"}
        )
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.text}")
            return
            
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create agent
        print("🤖 Creating trading agent...")
        response = await client.post(
            f"{base_url}/api/v1/agents",
            headers=headers,
            json={"name": "Demo Profit Trader", "agent_type": "trading"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create agent: {response.text}")
            return
            
        agent = response.json()
        agent_id = agent["id"]
        print(f"✅ Agent created: {agent_id}")
        
        # Start agent
        await client.post(f"{base_url}/api/v1/agents/{agent_id}/start", headers=headers)
        
        # Get initial prices
        print("\n💹 Current Market Prices:")
        print("━" * 50)
        
        symbols = ["BTC", "ETH", "SOL"]
        initial_prices = {}
        
        for symbol in symbols:
            response = await client.get(f"{base_url}/api/v1/market/price/{symbol}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                price = data["price"]
                initial_prices[symbol] = price
                print(f"{symbol}: ${price:,.2f}")
        
        # Execute trades
        print("\n📈 Executing Trades:")
        print("━" * 50)
        
        trades = [
            {"symbol": "BTC", "quantity": 0.001},
            {"symbol": "ETH", "quantity": 0.1},
            {"symbol": "SOL", "quantity": 5}
        ]
        
        total_invested = 0
        positions = {}
        
        for trade in trades:
            symbol = trade["symbol"]
            quantity = trade["quantity"]
            
            # Create task
            response = await client.post(
                f"{base_url}/api/v1/tasks",
                headers=headers,
                json={
                    "type": "trading",
                    "data": {
                        "action": "buy",
                        "symbol": symbol,
                        "quantity": quantity,
                        "order_type": "market"
                    }
                }
            )
            
            if response.status_code == 200:
                task = response.json()
                task_id = task["id"]
                
                # Wait for completion
                await asyncio.sleep(2)
                
                # Get result
                response = await client.get(f"{base_url}/api/v1/tasks/{task_id}", headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    if result["status"] == "completed":
                        exec_price = result["result"]["execution_price"]
                        total = result["result"]["net_total"]
                        
                        print(f"✅ BOUGHT {quantity} {symbol} @ ${exec_price:,.2f} = ${total:,.2f}")
                        
                        positions[symbol] = {
                            "quantity": quantity,
                            "buy_price": exec_price,
                            "cost": total
                        }
                        total_invested += total
        
        print(f"\n💰 Total Invested: ${total_invested:,.2f}")
        
        # Wait for market movement
        print("\n⏳ Waiting 15 seconds for market movement...")
        await asyncio.sleep(15)
        
        # Calculate P&L
        print("\n📊 REAL-TIME P&L CALCULATION:")
        print("━" * 70)
        print(f"{'Symbol':<8} {'Qty':>10} {'Buy Price':>12} {'Current':>12} {'Value':>12} {'P&L':>12} {'%':>8}")
        print("-" * 70)
        
        total_value = 0
        total_pnl = 0
        
        for symbol, position in positions.items():
            # Get current price
            response = await client.get(f"{base_url}/api/v1/market/price/{symbol}", headers=headers)
            if response.status_code == 200:
                current_price = response.json()["price"]
                current_value = position["quantity"] * current_price
                pnl = current_value - position["cost"]
                pnl_pct = (pnl / position["cost"]) * 100
                
                total_value += current_value
                total_pnl += pnl
                
                print(f"{symbol:<8} {position['quantity']:>10.4f} ${position['buy_price']:>11.2f} "
                      f"${current_price:>11.2f} ${current_value:>11.2f} ${pnl:>11.2f} {pnl_pct:>7.2f}%")
        
        print("-" * 70)
        print(f"{'TOTAL':<8} {'':<10} ${total_invested:>11.2f} {'':<12} "
              f"${total_value:>11.2f} ${total_pnl:>11.2f} {(total_pnl/total_invested)*100:>7.2f}%")
        
        print("\n" + "━" * 70)
        
        if total_pnl > 0:
            print(f"🎉 PROFIT: ${total_pnl:,.2f} ({(total_pnl/total_invested)*100:.2f}%)")
        elif total_pnl < 0:
            print(f"📉 LOSS: ${total_pnl:,.2f} ({(total_pnl/total_invested)*100:.2f}%)")
        else:
            print("➡️  BREAKEVEN")
        
        print("\n📌 Note: This is a demo with small positions")
        print("   Actual P&L depends on market movements")
        print("   Data from: CoinGecko, Binance, Yahoo Finance")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())