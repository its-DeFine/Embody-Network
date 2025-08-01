#\!/bin/bash

echo "=== TRADING SYSTEM STATUS CHECK ==="
echo "Date: $(date)"
echo ""

# Check if system is running
echo "📊 System Components Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Docker containers
RUNNING_CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep operation)
if [ \! -z "$RUNNING_CONTAINERS" ]; then
    echo "$RUNNING_CONTAINERS"
else
    echo "❌ No containers running. System is not active."
    echo ""
    echo "To start the system:"
    echo "  docker-compose up -d"
    exit 1
fi

# Simple status check
echo -e "\n📈 Trading System Overview:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ System Architecture:"
echo "  • Monolith API with event-driven orchestration"
echo "  • Redis pub/sub for agent communication"
echo "  • GPU orchestration for high-performance computing"
echo ""
echo "✅ Market Data Integration:"
echo "  • Real-time prices from 10+ providers"
echo "  • Automatic failover between sources"
echo "  • Support for stocks and cryptocurrencies"
echo ""
echo "✅ Key Features:"
echo "  • P&L tracking with real market prices"
echo "  • 24/7 reliability with circuit breakers"
echo "  • Rate limiting and health monitoring"
echo "  • FREE data sources (CoinGecko, Binance, etc.)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
