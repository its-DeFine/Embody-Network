#!/usr/bin/env python3
"""Direct test of Finnhub API"""

import httpx
import asyncio

API_KEY = "c2q2r8iad3i9rjb92vfg"

async def test_finnhub():
    client = httpx.AsyncClient()
    
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    
    print("Testing Finnhub API directly...")
    print("=" * 50)
    
    for symbol in symbols:
        try:
            response = await client.get(
                f"https://finnhub.io/api/v1/quote",
                params={
                    "symbol": symbol,
                    "token": API_KEY
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                price = data.get("c", 0)  # Current price
                print(f"{symbol}: ${price}")
            else:
                print(f"{symbol}: Error {response.status_code}")
                
        except Exception as e:
            print(f"{symbol}: {e}")
            
        await asyncio.sleep(0.5)  # Respect rate limits
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_finnhub())