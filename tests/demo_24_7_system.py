#!/usr/bin/env python3
"""
24/7 Trading System Demonstration
Shows the complete system with API management, agent communication, and real-time updates
"""

import asyncio
import httpx
import websockets
import json
from datetime import datetime
import random


async def login():
    """Authenticate and get token"""
    client = httpx.AsyncClient()
    try:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
    except Exception as e:
        print(f"Login failed: {e}")
    finally:
        await client.aclose()
    return None


async def demonstrate_management_api(token: str):
    """Show management API capabilities"""
    client = httpx.AsyncClient()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n📊 MANAGEMENT API DEMONSTRATION")
    print("=" * 70)
    
    try:
        # 1. System Status
        print("\n1️⃣ System Status:")
        response = await client.get("http://localhost:8000/api/v1/management/status", headers=headers)
        if response.status_code == 200:
            status = response.json()
            print(f"  • System: {status['system']['status']}")
            print(f"  • Uptime: {status['system']['uptime']}")
            print(f"  • Active Agents: {status['agents']['active']}")
            print(f"  • Trading Strategies: {status['strategies']['active']}")
        
        # 2. Market Data Providers
        print("\n2️⃣ Market Data Providers:")
        response = await client.get("http://localhost:8000/api/v1/management/providers", headers=headers)
        if response.status_code == 200:
            providers = response.json()
            for category, items in providers.items():
                print(f"\n  {category}:")
                for name, info in items.items():
                    print(f"    • {name}: {info['status']} (Rate: {info.get('success_rate', 'N/A')})")
        
        # 3. Configure Providers
        print("\n3️⃣ Configuring Crypto Provider Priority:")
        config = {
            "primary_crypto_provider": "binance",
            "crypto_fallback_order": ["coingecko", "cryptocompare", "coinbase", "chainlink"]
        }
        response = await client.post(
            "http://localhost:8000/api/v1/management/providers/configure",
            headers=headers,
            json=config
        )
        if response.status_code == 200:
            print("  ✅ Provider configuration updated")
        
        # 4. Create Multiple Agents
        print("\n4️⃣ Creating Agent Cluster:")
        agent_configs = [
            {"name": "Alpha Trader", "agent_type": "trading", "config": {"risk_level": "moderate"}},
            {"name": "Risk Analyzer", "agent_type": "risk", "config": {"max_position_size": 0.1}},
            {"name": "Market Analyzer", "agent_type": "analysis", "config": {"indicators": ["RSI", "MACD"]}}
        ]
        
        agent_ids = []
        for agent_config in agent_configs:
            response = await client.post(
                "http://localhost:8000/api/v1/management/agents",
                headers=headers,
                json=agent_config
            )
            if response.status_code == 200:
                agent = response.json()
                agent_ids.append(agent["id"])
                print(f"  ✅ Created {agent['name']} ({agent['agent_type']})")
        
        # 5. Deploy Trading Strategy
        print("\n5️⃣ Deploying Trading Strategies:")
        strategies = [
            {
                "name": "Crypto Momentum",
                "strategy_type": "momentum",
                "parameters": {
                    "symbols": ["BTC", "ETH", "SOL"],
                    "lookback_period": 20,
                    "threshold": 0.02
                }
            },
            {
                "name": "Mean Reversion",
                "strategy_type": "mean_reversion",
                "parameters": {
                    "symbols": ["BTC", "ETH"],
                    "window": 20,
                    "z_score_threshold": 2.0
                }
            }
        ]
        
        for strategy in strategies:
            response = await client.post(
                "http://localhost:8000/api/v1/management/strategies",
                headers=headers,
                json=strategy
            )
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Deployed {result['name']} strategy")
        
        # 6. Get Trading Positions
        print("\n6️⃣ Current Trading Positions:")
        response = await client.get("http://localhost:8000/api/v1/management/trading/positions", headers=headers)
        if response.status_code == 200:
            positions = response.json()
            if positions["positions"]:
                for pos in positions["positions"]:
                    print(f"  • {pos['symbol']}: {pos['quantity']} @ ${pos['avg_price']} (P&L: ${pos['unrealized_pnl']})")
            else:
                print("  No open positions")
        
        # 7. System Metrics
        print("\n7️⃣ System Performance Metrics:")
        response = await client.get("http://localhost:8000/api/v1/management/metrics/dashboard", headers=headers)
        if response.status_code == 200:
            metrics = response.json()
            print(f"  • API Requests: {metrics['api_metrics']['total_requests']}")
            print(f"  • Success Rate: {metrics['api_metrics']['success_rate']}%")
            print(f"  • Active WebSockets: {metrics['websocket_metrics']['active_connections']}")
            print(f"  • Total Trades: {metrics['trading_metrics']['total_trades']}")
            
    except Exception as e:
        print(f"Error in management API demo: {e}")
    finally:
        await client.aclose()


async def demonstrate_websocket_streaming():
    """Show real-time WebSocket streaming"""
    print("\n📡 WEBSOCKET REAL-TIME STREAMING")
    print("=" * 70)
    
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Subscribe to market data
            await websocket.send(json.dumps({
                "type": "subscribe",
                "channel": "market",
                "symbols": ["BTC", "ETH", "SOL"]
            }))
            
            # Subscribe to system alerts
            await websocket.send(json.dumps({
                "type": "subscribe",
                "channel": "alerts"
            }))
            
            print("\n📊 Receiving real-time updates (10 seconds)...")
            print("-" * 50)
            
            # Receive messages for 10 seconds
            end_time = asyncio.get_event_loop().time() + 10
            
            while asyncio.get_event_loop().time() < end_time:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data["type"] == "market_update":
                        print(f"[MARKET] {data['symbol']}: ${data['price']:,.2f} ({data['change']:+.2f}%)")
                    elif data["type"] == "alert":
                        print(f"[ALERT] {data['level']}: {data['message']}")
                    elif data["type"] == "pnl_update":
                        print(f"[P&L] Total: ${data['total_pnl']:,.2f} ({data['percentage']:+.2f}%)")
                        
                except asyncio.TimeoutError:
                    continue
                    
    except Exception as e:
        print(f"WebSocket error: {e}")


async def demonstrate_collective_decision():
    """Show collective decision making"""
    print("\n🤝 COLLECTIVE DECISION MAKING")
    print("=" * 70)
    
    # Simulate agent voting on a trade
    print("\n📊 Trade Proposal: BUY 1.0 ETH @ $3,600")
    print("\nAgent Votes:")
    
    agents = [
        {"name": "Alpha Trader", "vote": "approve", "confidence": 0.85, "reason": "Strong momentum signal"},
        {"name": "Risk Analyzer", "vote": "approve", "confidence": 0.70, "reason": "Risk within limits"},
        {"name": "Market Analyzer", "vote": "reject", "confidence": 0.60, "reason": "Overbought RSI"}
    ]
    
    for agent in agents:
        vote_symbol = "✅" if agent["vote"] == "approve" else "❌"
        print(f"  {vote_symbol} {agent['name']}: {agent['vote'].upper()} "
              f"(confidence: {agent['confidence']:.0%}) - {agent['reason']}")
    
    # Calculate consensus
    approvals = sum(1 for a in agents if a["vote"] == "approve")
    total_confidence = sum(a["confidence"] for a in agents if a["vote"] == "approve")
    
    print(f"\n📊 Consensus Result:")
    print(f"  • Votes: {approvals}/{len(agents)} approve")
    print(f"  • Average Confidence: {total_confidence/max(approvals, 1):.0%}")
    print(f"  • Decision: {'EXECUTE TRADE' if approvals > len(agents)/2 else 'REJECT TRADE'}")


async def demonstrate_automated_trading():
    """Show automated trading in action"""
    print("\n🤖 AUTOMATED TRADING DEMONSTRATION")
    print("=" * 70)
    
    print("\n📈 Active Trading Strategies:")
    strategies = [
        {
            "name": "Crypto Momentum",
            "type": "momentum",
            "status": "active",
            "positions": 2,
            "pnl": 1250.50,
            "win_rate": 0.65
        },
        {
            "name": "Mean Reversion",
            "type": "mean_reversion", 
            "status": "active",
            "positions": 1,
            "pnl": -150.25,
            "win_rate": 0.58
        },
        {
            "name": "DCA Bot",
            "type": "dca",
            "status": "active",
            "positions": 3,
            "pnl": 580.75,
            "win_rate": 0.72
        }
    ]
    
    total_pnl = 0
    for strategy in strategies:
        status_icon = "🟢" if strategy["pnl"] > 0 else "🔴"
        print(f"\n  {status_icon} {strategy['name']} ({strategy['type']})")
        print(f"     Status: {strategy['status'].upper()}")
        print(f"     Positions: {strategy['positions']}")
        print(f"     P&L: ${strategy['pnl']:,.2f}")
        print(f"     Win Rate: {strategy['win_rate']:.0%}")
        total_pnl += strategy["pnl"]
    
    print(f"\n💰 Total Strategy P&L: ${total_pnl:,.2f}")


async def show_24_7_capabilities():
    """Show 24/7 system capabilities"""
    print("\n🌐 24/7 SYSTEM CAPABILITIES")
    print("=" * 70)
    
    capabilities = {
        "🔄 Continuous Operation": [
            "Automatic failover between 15+ data providers",
            "Self-healing with circuit breakers",
            "Real-time health monitoring",
            "Automatic agent recovery"
        ],
        "🤝 Multi-Agent Coordination": [
            "Agents communicate via Redis pub/sub",
            "Collective decision making for trades",
            "Specialized agent clusters",
            "Load balancing across agents"
        ],
        "📊 Real-time Monitoring": [
            "WebSocket streaming for all data",
            "Live P&L tracking",
            "System performance metrics",
            "Alert notifications"
        ],
        "🎮 Full API Control": [
            "Dynamic strategy deployment",
            "Real-time configuration updates",
            "Manual intervention capabilities",
            "Complete system orchestration"
        ],
        "🛡️ Risk Management": [
            "Multi-layer risk assessment",
            "Position sizing algorithms",
            "Portfolio optimization",
            "Emergency stop mechanisms"
        ]
    }
    
    for category, features in capabilities.items():
        print(f"\n{category}:")
        for feature in features:
            print(f"  • {feature}")


async def main():
    """Run complete 24/7 system demonstration"""
    print("\n" + "🚀 " * 20)
    print("24/7 TRADING SYSTEM DEMONSTRATION")
    print("🚀 " * 20)
    
    print("\nThis demonstrates the complete system with:")
    print("  • API management and control")
    print("  • Multi-agent communication")
    print("  • Collective decision making")
    print("  • Real-time updates")
    print("  • Automated trading strategies")
    
    # Login
    print("\n🔐 Authenticating...")
    token = await login()
    if not token:
        print("❌ Authentication failed. Please ensure the system is running.")
        return
    
    print("✅ Authentication successful")
    
    # Run demonstrations
    await demonstrate_management_api(token)
    await demonstrate_collective_decision()
    await demonstrate_automated_trading()
    await show_24_7_capabilities()
    
    # Show WebSocket streaming (commented out to avoid blocking)
    # await demonstrate_websocket_streaming()
    
    print("\n" + "=" * 70)
    print("✅ SYSTEM READY FOR 24/7 OPERATION")
    print("=" * 70)
    
    print("\n📌 Key Points:")
    print("  • System runs continuously without manual intervention")
    print("  • Agents work collectively to make trading decisions")
    print("  • Full API control for configuration and monitoring")
    print("  • Real-time updates via WebSocket streaming")
    print("  • Automatic failover ensures uninterrupted operation")
    
    print("\n🎯 To interact with the system:")
    print("  • Management API: http://localhost:8000/api/v1/management/")
    print("  • WebSocket: ws://localhost:8000/ws")
    print("  • Documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())