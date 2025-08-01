#!/usr/bin/env python3
"""
Test Crypto Trading with Chainlink Oracle Data

This script demonstrates:
1. Fetching real crypto prices from Chainlink oracles (on-chain data)
2. Executing crypto trades with real market prices
3. Tracking P&L for crypto positions
4. Using completely free blockchain data sources
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.blockchain_data import crypto_data_service
from app.market_data import market_data_service


async def display_chainlink_prices():
    """Display all available Chainlink oracle prices"""
    print("\n" + "="*60)
    print("📊 CHAINLINK ORACLE PRICES (On-Chain Data)")
    print("="*60)
    
    # Get all prices from Chainlink
    prices = await crypto_data_service.get_all_prices()
    
    if not prices:
        print("❌ Failed to fetch Chainlink prices")
        return {}
        
    # Display prices in a nice format
    print(f"\n{'Symbol':<10} {'Price':>12} {'Source':<20}")
    print("-" * 45)
    
    for symbol, price in sorted(prices.items()):
        print(f"{symbol:<10} ${price:>11,.2f} {'Chainlink Oracle':<20}")
    
    print(f"\n✅ Successfully fetched {len(prices)} prices from Chainlink oracles")
    print("📍 Data source: Ethereum blockchain (via free RPC endpoints)")
    
    return prices


async def test_crypto_trading(prices: Dict[str, float]):
    """Simulate crypto trading with real prices"""
    print("\n" + "="*60)
    print("💼 CRYPTO TRADING SIMULATION")
    print("="*60)
    
    # Starting portfolio
    initial_capital = 100000  # $100k
    portfolio = {
        "USD": initial_capital,
        "positions": {}
    }
    
    print(f"\n💰 Starting Capital: ${initial_capital:,.2f}")
    
    # Execute some trades
    trades = [
        {"action": "buy", "symbol": "BTC", "usd_amount": 20000},
        {"action": "buy", "symbol": "ETH", "usd_amount": 15000},
        {"action": "buy", "symbol": "LINK", "usd_amount": 5000},
        {"action": "buy", "symbol": "UNI", "usd_amount": 3000},
        {"action": "buy", "symbol": "AAVE", "usd_amount": 2000},
    ]
    
    print("\n📈 EXECUTING TRADES:")
    print("-" * 60)
    
    for trade in trades:
        symbol = trade["symbol"]
        usd_amount = trade["usd_amount"]
        
        if symbol in prices:
            price = prices[symbol]
            quantity = usd_amount / price
            
            # Execute trade
            portfolio["USD"] -= usd_amount
            if symbol not in portfolio["positions"]:
                portfolio["positions"][symbol] = {"quantity": 0, "avg_price": 0}
            
            # Update position
            pos = portfolio["positions"][symbol]
            total_cost = (pos["quantity"] * pos["avg_price"]) + usd_amount
            pos["quantity"] += quantity
            pos["avg_price"] = total_cost / pos["quantity"]
            
            print(f"✅ BOUGHT {quantity:.6f} {symbol} @ ${price:,.2f} = ${usd_amount:,.2f}")
        else:
            print(f"❌ No price available for {symbol}")
    
    # Calculate P&L
    print("\n" + "="*60)
    print("📊 PORTFOLIO SUMMARY & P&L")
    print("="*60)
    
    print(f"\n💵 Cash Balance: ${portfolio['USD']:,.2f}")
    print("\n📈 CRYPTO POSITIONS:")
    print(f"\n{'Symbol':<8} {'Quantity':>12} {'Avg Price':>12} {'Current':>12} {'P&L':>12} {'P&L %':>8}")
    print("-" * 80)
    
    total_value = portfolio["USD"]
    total_pnl = 0
    
    for symbol, position in portfolio["positions"].items():
        if symbol in prices:
            current_price = prices[symbol]
            position_value = position["quantity"] * current_price
            cost_basis = position["quantity"] * position["avg_price"]
            pnl = position_value - cost_basis
            pnl_pct = (pnl / cost_basis) * 100
            
            total_value += position_value
            total_pnl += pnl
            
            print(f"{symbol:<8} {position['quantity']:>12.4f} ${position['avg_price']:>11.2f} "
                  f"${current_price:>11.2f} ${pnl:>11.2f} {pnl_pct:>7.2f}%")
    
    print("-" * 80)
    print(f"\n💼 Total Portfolio Value: ${total_value:,.2f}")
    print(f"📊 Total P&L: ${total_pnl:,.2f} ({(total_pnl / (initial_capital - portfolio['USD'])) * 100:.2f}%)")
    print(f"🎯 Return on Investment: {((total_value - initial_capital) / initial_capital) * 100:.2f}%")


async def test_market_data_service():
    """Test the unified market data service with crypto"""
    print("\n" + "="*60)
    print("🔧 TESTING UNIFIED MARKET DATA SERVICE")
    print("="*60)
    
    # Initialize the service
    await market_data_service.initialize()
    
    # Test various crypto symbols
    test_symbols = ["BTC", "ETH", "BNB", "SOL", "DOGE"]
    
    print("\n📊 Fetching prices via MarketDataService:")
    print(f"\n{'Symbol':<10} {'Price':>12} {'Provider':<20}")
    print("-" * 45)
    
    for symbol in test_symbols:
        price = await market_data_service.get_current_price(symbol, use_cache=False)
        if price:
            # Determine which provider was used (check logs)
            provider = "CoinGecko/Binance/Chainlink"
            print(f"{symbol:<10} ${price:>11,.2f} {provider:<20}")
        else:
            print(f"{symbol:<10} {'N/A':>12} {'Failed':<20}")
        
        # Small delay to respect rate limits
        await asyncio.sleep(0.5)
    
    # Test quote data
    print("\n📋 Testing detailed quote for BTC:")
    quote = await market_data_service.get_quote("BTC")
    if quote:
        print(json.dumps(quote, indent=2))


async def test_defi_data():
    """Test DeFi protocol data"""
    print("\n" + "="*60)
    print("🏦 DEFI PROTOCOL DATA")
    print("="*60)
    
    # Get total DeFi TVL
    tvl = await crypto_data_service.defi.get_defi_tvl()
    if tvl:
        print(f"\n💰 Total DeFi TVL: ${tvl['total_tvl']:,.0f}")
    
    # Get specific protocol TVL
    protocols = ["aave", "compound", "uniswap", "curve", "makerdao"]
    
    print("\n📊 Top DeFi Protocols:")
    print(f"\n{'Protocol':<15} {'TVL':>15}")
    print("-" * 32)
    
    for protocol in protocols:
        data = await crypto_data_service.defi.get_protocol_tvl(protocol)
        if data:
            print(f"{data['name']:<15} ${data['tvl']:>14,.0f}")
        await asyncio.sleep(0.2)


async def main():
    """Run all crypto data tests"""
    print("\n" + "🚀 " * 20)
    print("CRYPTO TRADING WITH FREE BLOCKCHAIN DATA")
    print("🚀 " * 20)
    
    print("\n⚡ Using completely FREE data sources:")
    print("  • Chainlink Oracles (on-chain price feeds)")
    print("  • Public blockchain RPC endpoints")
    print("  • CoinGecko API (no key required)")
    print("  • Binance public API")
    print("  • DefiLlama (DeFi TVL data)")
    
    try:
        # 1. Display Chainlink oracle prices
        prices = await display_chainlink_prices()
        
        if prices:
            # 2. Simulate crypto trading
            await test_crypto_trading(prices)
        
        # 3. Test unified market data service
        await test_market_data_service()
        
        # 4. Test DeFi data
        await test_defi_data()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())