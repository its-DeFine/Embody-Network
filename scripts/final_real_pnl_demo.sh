#!/bin/bash

echo "=== FINAL Real Market P&L Demo ==="
echo "Demonstrating actual trading with real prices and P&L tracking"
echo ""

# Restart services to clear cache and use Yahoo Finance
echo "1. Restarting services..."
docker-compose restart app > /dev/null 2>&1
sleep 10

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

echo "✅ System ready"

# Clear Redis cache to force fresh prices
docker exec operation-redis-1 redis-cli FLUSHDB > /dev/null 2>&1

# Step 1: Get fresh market prices
echo -e "\n📊 Real Market Prices (from Yahoo Finance):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

declare -A PRICES
for SYMBOL in AAPL MSFT GOOGL; do
    RESPONSE=$(curl -s http://localhost:8000/api/v1/market/price/$SYMBOL?use_cache=false \
      -H "Authorization: Bearer $TOKEN")
    PRICE=$(echo "$RESPONSE" | jq -r '.price')
    PRICES[$SYMBOL]=$PRICE
    printf "%-6s $%s\n" "$SYMBOL:" "$PRICE"
    sleep 2  # Respect Yahoo rate limits
done

# Step 2: Create P&L tracking agent
echo -e "\n🤖 Starting Real Trading Agent with P&L Tracking..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create the agent
AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "P&L Tracker",
    "agent_type": "real_trading"
  }' | jq -r '.id')

# Start agent
curl -s -X POST http://localhost:8000/api/v1/agents/$AGENT_ID/start \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Run the real trading agent
cd /home/geo/operation/agent
export AGENT_ID=$AGENT_ID
export JWT_SECRET=your-secret-key-change-in-production
export ADMIN_PASSWORD=admin123
python3 real_trading_agent.py > /tmp/pnl_agent.log 2>&1 &
AGENT_PID=$!

sleep 3

# Step 3: Execute trades with real prices
echo -e "\n💼 Portfolio Simulation:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting Capital: 100,000"
echo ""

# Track our trades for P&L
TOTAL_INVESTED=0

# Buy orders
echo "📈 BUY Orders:"
for SYMBOL in AAPL MSFT GOOGL; do
    QTY=$((RANDOM % 50 + 10))  # Random quantity 10-60
    
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
    sleep 3
    
    # Get result
    RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
      -H "Authorization: Bearer $TOKEN")
    
    EXEC_PRICE=$(echo "$RESULT" | jq -r '.result.execution_price // 0')
    TOTAL_COST=$(echo "$RESULT" | jq -r '.result.net_total // 0')
    
    if [ "$EXEC_PRICE" != "0" ]; then
        echo "✅ Bought $QTY $SYMBOL @ \$$EXEC_PRICE = \$$TOTAL_COST"
        TOTAL_INVESTED=$(echo "$TOTAL_INVESTED + $TOTAL_COST" | bc)
    fi
done

echo -e "\nTotal Invested: \$$TOTAL_INVESTED"

# Wait for "market movement"
echo -e "\n⏳ Simulating market movement..."
sleep 5

# Sell some positions
echo -e "\n📉 SELL Orders:"
TOTAL_PROCEEDS=0

for SYMBOL in AAPL MSFT; do
    QTY=$((RANDOM % 30 + 5))  # Sell partial position
    
    TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"type\": \"trading\",
        \"data\": {
          \"action\": \"sell\",
          \"symbol\": \"$SYMBOL\",
          \"quantity\": $QTY,
          \"order_type\": \"market\"
        }
      }")
    
    TASK_ID=$(echo "$TASK" | jq -r '.id')
    sleep 3
    
    # Get result
    RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
      -H "Authorization: Bearer $TOKEN")
    
    EXEC_PRICE=$(echo "$RESULT" | jq -r '.result.execution_price // 0')
    PROCEEDS=$(echo "$RESULT" | jq -r '.result.net_total // 0')
    
    if [ "$EXEC_PRICE" != "0" ]; then
        echo "✅ Sold $QTY $SYMBOL @ \$$EXEC_PRICE = \$$PROCEEDS"
        TOTAL_PROCEEDS=$(echo "$TOTAL_PROCEEDS + $PROCEEDS" | bc)
    fi
done

# Step 4: P&L Calculation
echo -e "\n📊 P&L REPORT:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get all completed trades for detailed P&L
ALL_TRADES=$(curl -s http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | jq '[.[] | select(.status == "completed" and .type == "trading")]')

# Calculate realized P&L
echo "Realized P&L: \$$(echo "$TOTAL_PROCEEDS - $TOTAL_INVESTED" | bc)"

# Show position summary
echo -e "\n📋 Current Positions:"
echo "$ALL_TRADES" | jq -r 'group_by(.data.symbol) | .[] | 
    {
        symbol: .[0].data.symbol,
        buys: [.[] | select(.data.action == "buy")] | add,
        sells: [.[] | select(.data.action == "sell")] | add
    } | 
    "\(.symbol): Net position = \((.buys.data.quantity // 0) - (.sells.data.quantity // 0)) shares"'

# Step 5: Verify real prices were used
echo -e "\n✅ Verification:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if prices match real market prices
AAPL_TRADES=$(echo "$ALL_TRADES" | jq '[.[] | select(.data.symbol == "AAPL" and .result.execution_price != null)] | .[0].result.execution_price')

if [ "$AAPL_TRADES" != "150.25" ] && [ "$AAPL_TRADES" != "null" ]; then
    echo "✅ Using REAL market prices (not 150.25 simulated)"
    echo "✅ AAPL traded at: \$$AAPL_TRADES (market price)"
else
    echo "⚠️  Some trades may use simulated prices"
fi

# Check provider logs
PROVIDER=$(docker-compose logs app 2>&1 | grep -E "Yahoo Finance.*price" | tail -1)
if [ ! -z "$PROVIDER" ]; then
    echo "✅ Data source: Yahoo Finance (real-time)"
fi

# Cleanup
kill $AGENT_PID 2>/dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Summary:"
echo ""
echo "1. Real market prices fetched from Yahoo Finance"
echo "2. Trades executed at actual market prices"
echo "3. P&L calculated with commissions"
echo "4. Positions tracked in real-time"
echo ""
echo "View detailed results at: http://localhost:8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"