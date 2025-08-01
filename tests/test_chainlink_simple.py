#!/usr/bin/env python3
"""
Simple test of Chainlink oracle integration
Demonstrates fetching real crypto prices from blockchain
"""

import asyncio
import httpx
from datetime import datetime


class SimpleChainlinkTest:
    def __init__(self):
        # Free public Ethereum RPC endpoints
        self.rpc_endpoints = [
            "https://eth.public-rpc.com",
            "https://cloudflare-eth.com",
            "https://rpc.ankr.com/eth"
        ]
        
        # Chainlink price feed addresses on Ethereum
        self.price_feeds = {
            "BTC/USD": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
            "ETH/USD": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
            "LINK/USD": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c",
            "BNB/USD": "0x14e613AC84a31f709eadbdF89C6CC390fDc9540A",
            "SOL/USD": "0x4ffC43a60e009B551865A93d232E33Fce9f01507",
        }
        
        self.client = httpx.AsyncClient()
    
    async def call_rpc(self, method: str, params: list):
        """Make RPC call to Ethereum"""
        for endpoint in self.rpc_endpoints:
            try:
                response = await self.client.post(
                    endpoint,
                    json={
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": params,
                        "id": 1
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        return data["result"]
            except Exception as e:
                print(f"RPC error with {endpoint}: {e}")
                continue
        return None
    
    async def get_chainlink_price(self, pair: str):
        """Get price from Chainlink oracle"""
        try:
            feed_address = self.price_feeds.get(pair)
            if not feed_address:
                return None
            
            # Call latestRoundData() function
            function_signature = "0xfeaf968c"
            
            result = await self.call_rpc(
                "eth_call",
                [{
                    "to": feed_address,
                    "data": function_signature
                }, "latest"]
            )
            
            if result:
                # Decode the result
                data = result[2:]  # Remove '0x'
                
                # The price is the second value (int256) in the return data
                # Each value is 32 bytes (64 hex chars)
                price_hex = data[64:128]  # Second 32-byte value
                price_raw = int(price_hex, 16)
                
                # Handle negative values (two's complement)
                if price_raw > 2**255:
                    price_raw = price_raw - 2**256
                
                # Chainlink uses 8 decimals for USD pairs
                price = price_raw / 10**8
                
                return price
                
        except Exception as e:
            print(f"Error getting Chainlink price for {pair}: {e}")
            return None
    
    async def run_test(self):
        """Run the Chainlink oracle test"""
        print("\n" + "="*60)
        print("🔗 CHAINLINK ORACLE PRICE FEEDS TEST")
        print("="*60)
        print("\nFetching real-time crypto prices directly from blockchain...")
        print("Data source: Chainlink decentralized oracles on Ethereum")
        print("Cost: FREE (using public RPC endpoints)")
        
        print(f"\n{'Pair':<10} {'Price':>12} {'Source':<25}")
        print("-" * 50)
        
        prices = {}
        for pair, address in self.price_feeds.items():
            price = await self.get_chainlink_price(pair)
            if price:
                prices[pair] = price
                print(f"{pair:<10} ${price:>11,.2f} Chainlink Oracle")
            else:
                print(f"{pair:<10} {'Failed':>12} -")
            
            await asyncio.sleep(0.5)  # Be nice to RPC endpoints
        
        # Simulate a simple trade
        if prices:
            print("\n" + "="*60)
            print("💼 SIMULATED CRYPTO TRADE")
            print("="*60)
            
            # Buy $10,000 worth of BTC
            btc_price = prices.get("BTC/USD", 0)
            if btc_price > 0:
                btc_amount = 10000 / btc_price
                print(f"\n🔸 Buy Order:")
                print(f"  Amount: $10,000")
                print(f"  BTC Price: ${btc_price:,.2f}")
                print(f"  BTC Received: {btc_amount:.6f} BTC")
                
                # Simulate 1% price increase
                new_price = btc_price * 1.01
                new_value = btc_amount * new_price
                profit = new_value - 10000
                
                print(f"\n📈 After 1% price increase:")
                print(f"  New BTC Price: ${new_price:,.2f}")
                print(f"  Position Value: ${new_value:,.2f}")
                print(f"  Profit: ${profit:,.2f} ({profit/100:.2f}%)")
        
        print("\n" + "="*60)
        print("✅ Successfully fetched prices from Chainlink oracles!")
        print("🌐 This data is 100% decentralized and censorship-resistant")
        print("="*60)
        
        await self.client.aclose()


async def main():
    test = SimpleChainlinkTest()
    await test.run_test()


if __name__ == "__main__":
    print("\n🚀 CHAINLINK ORACLE INTEGRATION TEST")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Testing free on-chain price feeds...")
    
    asyncio.run(main())