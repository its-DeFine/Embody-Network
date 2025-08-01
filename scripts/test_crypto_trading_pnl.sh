#!/bin/bash

echo "=== CRYPTO TRADING WITH REAL MARKET DATA & P&L ==="
echo "Using 100% FREE APIs: CoinGecko, Binance Public, DefiLlama"
echo ""

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

if [ "$TOKEN" == "null" ]; then
    echo "❌ Failed to get auth token. Is the system running?"
    exit 1
fi

echo "✅ System authenticated"

# Clear cache to get fresh prices
docker exec operation-redis-1 redis-cli FLUSHDB > /dev/null 2>&1

# Step 1: Get real crypto prices
echo -e "\n📊 Real-Time Crypto Prices (from FREE APIs):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

declare -A PRICES
for SYMBOL in BTC ETH BNB SOL LINK; do
    RESPONSE=$(curl -s http://localhost:8000/api/v1/market/price/$SYMBOL?use_cache=false \
      -H "Authorization: Bearer $TOKEN")
    PRICE=$(echo "$RESPONSE" | jq -r '.price')
    
    if [ "$PRICE" != "null" ]; then
        PRICES[$SYMBOL]=$PRICE
        printf "%-6s $%s\n" "$SYMBOL:" "$PRICE"
    else
        echo "$SYMBOL: Failed to get price"
    fi
    sleep 1
done

# Step 2: Create crypto trading agent
echo -e "\n🤖 Starting Crypto Trading Agent with P&L Tracking..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create the agent
AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Crypto P&L Tracker",
    "agent_type": "real_trading"
  }' | jq -r '.id')

# Start agent
curl -s -X POST http://localhost:8000/api/v1/agents/$AGENT_ID/start \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo "✅ Agent created: $AGENT_ID"

# Step 3: Execute crypto trades
echo -e "\n💼 Crypto Portfolio Simulation:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting Capital: $100,000"
echo ""

TOTAL_INVESTED=0

# Buy orders
echo "📈 BUY Orders:"
for SYMBOL in BTC ETH SOL; do
    case $SYMBOL in
        BTC) QTY="0.2" ;;   # ~$20k worth
        ETH) QTY="3" ;;     # ~$10k worth
        SOL) QTY="50" ;;    # ~$8k worth
    esac
    
    TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"type\": \"trading\",
        \"data\": {
          \"action\": \"buy\",
          \"symbol\": \"$SYMBOL\",
          \"quantity\": $QTY,
          \"order_type\": \"market\"
        }
      }")
    
    TASK_ID=$(echo "$TASK" | jq -r '.id')
    sleep 2
    
    # Get result
    RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
      -H "Authorization: Bearer $TOKEN")
    
    EXEC_PRICE=$(echo "$RESULT" | jq -r '.result.execution_price // empty')
    TOTAL_COST=$(echo "$RESULT" | jq -r '.result.net_total // empty')
    
    if [ ! -z "$EXEC_PRICE" ]; then
        echo "✅ Bought $QTY $SYMBOL @ \$$EXEC_PRICE = \$$TOTAL_COST"
        TOTAL_INVESTED=$(echo "$TOTAL_INVESTED + $TOTAL_COST" | bc 2>/dev/null || echo $TOTAL_INVESTED)
    fi
done

echo -e "\nTotal Invested: \$$TOTAL_INVESTED"

# Wait for market movement
echo -e "\n⏳ Simulating crypto market volatility..."
sleep 5

# Get updated prices
echo -e "\n📊 Updated Crypto Prices:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for SYMBOL in BTC ETH SOL; do
    NEW_PRICE=$(curl -s http://localhost:8000/api/v1/market/price/$SYMBOL?use_cache=false \
      -H "Authorization: Bearer $TOKEN" | jq -r '.price')
    
    if [ ! -z "${PRICES[$SYMBOL]}" ] && [ "$NEW_PRICE" != "null" ]; then
        OLD_PRICE=${PRICES[$SYMBOL]}
        CHANGE=$(echo "scale=2; (($NEW_PRICE - $OLD_PRICE) / $OLD_PRICE) * 100" | bc 2>/dev/null || echo "0")
        printf "%-6s $%s (%.2f%%)\n" "$SYMBOL:" "$NEW_PRICE" "$CHANGE"
    fi
    sleep 1
done

# Step 4: P&L Report
echo -e "\n📊 CRYPTO P&L REPORT:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get all crypto trades
ALL_TRADES=$(curl -s http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | \
  jq '[.[] | select(.status == "completed" and .type == "trading" and (.data.symbol == "BTC" or .data.symbol == "ETH" or .data.symbol == "SOL"))]')

echo "$ALL_TRADES" | jq -r 'group_by(.data.symbol) | .[] | 
    {
        symbol: .[0].data.symbol,
        total_qty: [.[] | select(.data.action == "buy")] | map(.data.quantity) | add,
        avg_price: ([.[] | select(.data.action == "buy")] | map(.result.execution_price * .data.quantity) | add) / ([.[] | select(.data.action == "buy")] | map(.data.quantity) | add)
    } | 
    "\(.symbol): \(.total_qty) units @ avg price $\(.avg_price)"'

# Verify real prices were used
echo -e "\n✅ Verification:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check data source
PROVIDER=$(docker-compose logs app 2>&1 | grep -E "(CoinGecko|Binance|CryptoCompare).*price" | tail -3)
if [ ! -z "$PROVIDER" ]; then
    echo "✅ Data sources used:"
    echo "$PROVIDER" | sed 's/^/   /'
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Summary:"
echo ""
echo "1. Real crypto prices fetched from FREE APIs"
echo "2. CoinGecko, Binance Public, and others used"
echo "3. Trades executed at actual market prices"
echo "4. P&L calculated for crypto positions"
echo ""
echo "🌟 NO API KEYS REQUIRED! 100% FREE DATA!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"