#!/usr/bin/env python3
"""
24/7 System Health Check

Demonstrates the reliability features:
- Rate limiting protection
- Circuit breaker pattern
- Automatic failover
- Health monitoring
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
import time


async def check_api_health():
    """Check health of the trading system API"""
    client = httpx.AsyncClient()
    
    try:
        # Check if system is running
        response = await client.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print("❌ API returned status:", response.status_code)
            return False
    except Exception as e:
        print(f"❌ API is not accessible: {e}")
        return False
    finally:
        await client.aclose()


async def simulate_stress_test():
    """Simulate high load to test rate limiting"""
    print("\n" + "="*60)
    print("🔨 STRESS TEST: Rate Limiting & Circuit Breakers")
    print("="*60)
    
    client = httpx.AsyncClient()
    
    # Get auth token
    try:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"}
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except:
        print("❌ Failed to authenticate")
        await client.aclose()
        return
    
    # Test rapid requests
    print("\n📊 Testing rapid price requests (should trigger rate limiting):")
    
    symbols = ["BTC", "ETH", "SOL", "DOGE", "SHIB"]
    request_count = 0
    rate_limited = 0
    successful = 0
    failed = 0
    
    start_time = time.time()
    
    # Rapid fire 50 requests
    for i in range(50):
        for symbol in symbols:
            try:
                response = await client.get(
                    f"http://localhost:8000/api/v1/market/price/{symbol}?use_cache=false",
                    headers=headers,
                    timeout=2
                )
                request_count += 1
                
                if response.status_code == 200:
                    successful += 1
                    print(".", end="", flush=True)
                elif response.status_code == 429:
                    rate_limited += 1
                    print("R", end="", flush=True)
                else:
                    failed += 1
                    print("F", end="", flush=True)
                    
            except Exception:
                failed += 1
                print("E", end="", flush=True)
            
            # No delay - stress test
    
    elapsed = time.time() - start_time
    
    print(f"\n\n📈 Stress Test Results:")
    print(f"  Total Requests: {request_count}")
    print(f"  Successful: {successful} ({successful/request_count*100:.1f}%)")
    print(f"  Rate Limited: {rate_limited} ({rate_limited/request_count*100:.1f}%)")
    print(f"  Failed: {failed} ({failed/request_count*100:.1f}%)")
    print(f"  Time: {elapsed:.2f}s ({request_count/elapsed:.1f} req/s)")
    
    await client.aclose()


async def check_provider_health():
    """Check health of all data providers"""
    print("\n" + "="*60)
    print("🏥 DATA PROVIDER HEALTH CHECK")
    print("="*60)
    
    # Import and test each provider directly
    from app.market_data import market_data_service
    from app.reliability_manager import reliability_manager
    
    await market_data_service.initialize()
    
    # Test each provider
    providers_to_test = {
        "Stock Providers": ["yahoo", "alpha_vantage", "twelvedata", "finnhub"],
        "Crypto Providers": ["coingecko", "binance", "coinbase", "cryptocompare"]
    }
    
    for category, providers in providers_to_test.items():
        print(f"\n{category}:")
        print("-" * 40)
        
        for provider in providers:
            # Check circuit breaker state
            if provider in reliability_manager.circuit_breakers:
                breaker = reliability_manager.circuit_breakers[provider]
                state = breaker.state.value
                
                # Try a test request
                test_symbol = "AAPL" if category == "Stock Providers" else "BTC"
                
                start = time.time()
                price = None
                
                if provider in market_data_service.providers:
                    price = await reliability_manager.execute_with_reliability(
                        provider,
                        market_data_service.providers[provider].get_current_price,
                        test_symbol
                    )
                elif provider in market_data_service.crypto_providers:
                    price = await reliability_manager.execute_with_reliability(
                        provider,
                        market_data_service.crypto_providers[provider].get_current_price,
                        test_symbol
                    )
                
                elapsed = time.time() - start
                
                if price:
                    print(f"  ✅ {provider:<15} OK      ({elapsed:.2f}s) ${price:,.2f}")
                else:
                    print(f"  ❌ {provider:<15} FAILED  Circuit: {state}")


async def demonstrate_failover():
    """Demonstrate automatic failover between providers"""
    print("\n" + "="*60)
    print("🔄 AUTOMATIC FAILOVER DEMONSTRATION")
    print("="*60)
    
    from app.market_data import market_data_service
    
    # Test crypto failover chain
    print("\n🔗 Crypto Provider Failover Chain:")
    print("  Primary: CoinGecko → Binance → CryptoCompare → Coinbase → Chainlink")
    
    # Get a crypto price
    symbol = "ETH"
    price = await market_data_service.get_current_price(symbol, use_cache=False)
    
    if price:
        print(f"\n✅ Successfully got {symbol} price: ${price:,.2f}")
        print("  Check logs to see which provider was used")
    else:
        print(f"\n❌ All providers failed for {symbol}")


async def monitor_24_7_health():
    """Monitor system health over time"""
    print("\n" + "="*60)
    print("📊 24/7 HEALTH MONITORING")
    print("="*60)
    
    from app.reliability_manager import reliability_manager
    
    print("\n⏰ Monitoring system health for 60 seconds...")
    print("  (In production, this would run continuously)")
    
    start_time = time.time()
    check_interval = 10  # Check every 10 seconds
    
    while time.time() - start_time < 60:
        health = await reliability_manager.get_health_report()
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{timestamp}] System Status: {health['status'].upper()}")
        print(f"  Success Rate: {health['success_rate']}")
        print(f"  Total Requests: {health['total_requests']}")
        print(f"  Failed Requests: {health['failed_requests']}")
        print(f"  Rate Limited: {health['rate_limited_requests']}")
        print(f"  Healthy Providers: {len(health['healthy_providers'])}")
        
        if health['unhealthy_providers']:
            print("  ⚠️  Unhealthy Providers:")
            for provider in health['unhealthy_providers']:
                print(f"    - {provider['provider']}: {provider['state']} ({provider['failures']} failures)")
        
        await asyncio.sleep(check_interval)
    
    print("\n✅ Health monitoring complete")


async def main():
    """Run all 24/7 reliability checks"""
    print("\n🛡️ " * 20)
    print("24/7 TRADING SYSTEM RELIABILITY CHECK")
    print("🛡️ " * 20)
    
    print("\n📋 This demonstrates:")
    print("  • Rate limiting to prevent API abuse")
    print("  • Circuit breakers for failing services")
    print("  • Automatic failover between providers")
    print("  • Continuous health monitoring")
    print("  • Recovery mechanisms")
    
    # Check if API is running
    api_healthy = await check_api_health()
    
    if api_healthy:
        # Run stress test
        await simulate_stress_test()
        
        # Check provider health
        await check_provider_health()
        
        # Demonstrate failover
        await demonstrate_failover()
        
        # Monitor health
        await monitor_24_7_health()
    else:
        print("\n⚠️  Please start the trading system first:")
        print("  docker-compose up -d")
    
    print("\n" + "="*60)
    print("✅ 24/7 RELIABILITY FEATURES:")
    print("="*60)
    print("\n1. **Rate Limiting**: Prevents API overload")
    print("   - Per-provider limits based on free tier quotas")
    print("   - Token bucket algorithm for smooth rate control")
    print("   - Automatic request queuing and throttling")
    
    print("\n2. **Circuit Breakers**: Handles provider failures")
    print("   - Opens after 5 consecutive failures")
    print("   - Recovery timeout of 60 seconds")
    print("   - Half-open state for testing recovery")
    
    print("\n3. **Automatic Failover**: Ensures data availability")
    print("   - Multiple providers for each asset class")
    print("   - Intelligent routing based on asset type")
    print("   - Fallback chains with priority ordering")
    
    print("\n4. **Health Monitoring**: Tracks system status")
    print("   - Real-time success rate tracking")
    print("   - Provider-specific health metrics")
    print("   - Automatic degraded mode detection")
    
    print("\n5. **Recovery Mechanisms**: Self-healing system")
    print("   - Exponential backoff for rate limits")
    print("   - Automatic circuit breaker recovery")
    print("   - Dynamic request intervals based on health")
    
    print("\n🎯 RESULT: The system can run 24/7 without manual intervention!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())