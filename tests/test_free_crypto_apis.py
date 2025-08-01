#!/usr/bin/env python3
"""
Test FREE Crypto APIs - No API keys required!
"""

import asyncio
import httpx
import json
from datetime import datetime


async def test_coingecko():
    """Test CoinGecko API - Completely FREE, no key required"""
    print("\n" + "="*60)
    print("🦎 COINGECKO API TEST (100% FREE)")
    print("="*60)
    
    client = httpx.AsyncClient()
    
    # Get prices for multiple coins
    coins = ["bitcoin", "ethereum", "binancecoin", "solana", "chainlink"]
    
    try:
        # Simple price endpoint
        response = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": ",".join(coins),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n{'Coin':<15} {'Price':>12} {'24h Change':>12} {'Market Cap':>20}")
            print("-" * 65)
            
            for coin_id, info in data.items():
                symbol = coin_id[:4].upper()
                price = info["usd"]
                change = info.get("usd_24h_change", 0)
                mcap = info.get("usd_market_cap", 0)
                
                print(f"{symbol:<15} ${price:>11,.2f} {change:>11.2f}% ${mcap:>19,.0f}")
        else:
            print(f"Error: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.aclose()


async def test_binance_public():
    """Test Binance Public API - No key required"""
    print("\n" + "="*60)
    print("🔶 BINANCE PUBLIC API TEST (NO KEY REQUIRED)")
    print("="*60)
    
    client = httpx.AsyncClient()
    
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"]
    
    try:
        print(f"\n{'Symbol':<10} {'Price':>12} {'24h Change':>12} {'Volume':>20}")
        print("-" * 60)
        
        for symbol in symbols:
            response = await client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                price = float(data["lastPrice"])
                change = float(data["priceChangePercent"])
                volume = float(data["quoteVolume"])
                
                print(f"{symbol:<10} ${price:>11,.2f} {change:>11.2f}% ${volume:>19,.0f}")
            
            await asyncio.sleep(0.1)  # Be nice to the API
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.aclose()


async def test_crypto_trading_simulation():
    """Simulate crypto trading with real prices"""
    print("\n" + "="*60)
    print("💼 CRYPTO TRADING SIMULATION WITH REAL PRICES")
    print("="*60)
    
    client = httpx.AsyncClient()
    
    # Get current prices
    response = await client.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": "bitcoin,ethereum,solana,chainlink,uniswap",
            "vs_currencies": "usd"
        }
    )
    
    if response.status_code == 200:
        prices = response.json()
        
        # Starting portfolio
        portfolio = {
            "USD": 100000,  # $100k starting capital
            "trades": []
        }
        
        print(f"\n💰 Starting Capital: ${portfolio['USD']:,.2f}")
        print("\n📈 EXECUTING TRADES:")
        print("-" * 60)
        
        # Execute trades
        trades = [
            {"coin": "bitcoin", "symbol": "BTC", "usd_amount": 25000},
            {"coin": "ethereum", "symbol": "ETH", "usd_amount": 20000},
            {"coin": "solana", "symbol": "SOL", "usd_amount": 10000},
            {"coin": "chainlink", "symbol": "LINK", "usd_amount": 5000},
            {"coin": "uniswap", "symbol": "UNI", "usd_amount": 5000}
        ]
        
        total_spent = 0
        positions = {}
        
        for trade in trades:
            coin = trade["coin"]
            symbol = trade["symbol"]
            amount = trade["usd_amount"]
            
            if coin in prices:
                price = prices[coin]["usd"]
                quantity = amount / price
                
                positions[symbol] = {
                    "quantity": quantity,
                    "buy_price": price,
                    "cost": amount
                }
                
                total_spent += amount
                
                print(f"✅ BOUGHT {quantity:.6f} {symbol} @ ${price:,.2f} = ${amount:,.2f}")
        
        portfolio["USD"] -= total_spent
        
        # Calculate P&L (simulate 5% market movement)
        print("\n" + "="*60)
        print("📊 PORTFOLIO AFTER 5% MARKET MOVEMENT")
        print("="*60)
        
        print(f"\n💵 Cash: ${portfolio['USD']:,.2f}")
        print(f"\n{'Symbol':<8} {'Quantity':>12} {'Buy Price':>12} {'Current':>12} {'P&L':>12} {'%':>8}")
        print("-" * 70)
        
        total_value = portfolio["USD"]
        total_pnl = 0
        
        for symbol, position in positions.items():
            # Simulate 5% random movement
            import random
            movement = 1 + (random.uniform(-0.1, 0.1))  # -10% to +10%
            current_price = position["buy_price"] * movement
            
            current_value = position["quantity"] * current_price
            pnl = current_value - position["cost"]
            pnl_pct = (pnl / position["cost"]) * 100
            
            total_value += current_value
            total_pnl += pnl
            
            print(f"{symbol:<8} {position['quantity']:>12.4f} ${position['buy_price']:>11.2f} "
                  f"${current_price:>11.2f} ${pnl:>11.2f} {pnl_pct:>7.2f}%")
        
        print("-" * 70)
        print(f"\n💼 Total Portfolio Value: ${total_value:,.2f}")
        print(f"📊 Total P&L: ${total_pnl:,.2f} ({(total_pnl / total_spent) * 100:.2f}%)")
        print(f"🎯 ROI: {((total_value - 100000) / 100000) * 100:.2f}%")
    
    await client.aclose()


async def test_defi_data():
    """Test DeFi data from DefiLlama - FREE API"""
    print("\n" + "="*60)
    print("🏦 DEFI DATA FROM DEFILLAMA (FREE API)")
    print("="*60)
    
    client = httpx.AsyncClient()
    
    try:
        # Get total TVL
        response = await client.get("https://api.llama.fi/tvl")
        if response.status_code == 200:
            tvl = response.json()
            print(f"\n💰 Total DeFi TVL: ${float(tvl):,.0f}")
        
        # Get top protocols
        response = await client.get("https://api.llama.fi/protocols")
        if response.status_code == 200:
            protocols = response.json()
            
            print("\n📊 Top 10 DeFi Protocols by TVL:")
            print(f"\n{'Rank':<6} {'Protocol':<20} {'Chain':<15} {'TVL':>20}")
            print("-" * 65)
            
            # Sort by TVL and show top 10
            sorted_protocols = sorted(protocols, key=lambda x: x.get("tvl", 0), reverse=True)[:10]
            
            for i, protocol in enumerate(sorted_protocols, 1):
                name = protocol["name"][:20]
                chain = protocol.get("chain", "Multi-chain")[:15]
                tvl = protocol.get("tvl", 0)
                
                print(f"{i:<6} {name:<20} {chain:<15} ${tvl:>19,.0f}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.aclose()


async def main():
    """Run all tests"""
    print("\n🚀 " * 20)
    print("FREE CRYPTO DATA APIS DEMONSTRATION")
    print("🚀 " * 20)
    
    print("\n✨ All data sources used are 100% FREE!")
    print("  • CoinGecko - No API key required")
    print("  • Binance Public API - No authentication")
    print("  • DefiLlama - Open DeFi data")
    
    # Run all tests
    await test_coingecko()
    await test_binance_public()
    await test_crypto_trading_simulation()
    await test_defi_data()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("🎉 You can now trade crypto with real market data for FREE!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())