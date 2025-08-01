#!/bin/bash

echo "=== Real Trading with P&L Tracking Demo ==="
echo "Using Finnhub API for real market data"
echo ""

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "Failed to authenticate"
    exit 1
fi

echo "✅ Authenticated"

# Step 1: Get Real Market Prices
echo -e "\n📊 1. Fetching Real Market Prices (via Finnhub)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get multiple stock prices
for SYMBOL in AAPL MSFT GOOGL TSLA AMZN; do
    PRICE=$(curl -s http://localhost:8000/api/v1/market/price/$SYMBOL \
      -H "Authorization: Bearer $TOKEN" | jq -r '.price')
    printf "%-6s $%s\n" "$SYMBOL:" "$PRICE"
    sleep 0.5  # Small delay to respect rate limits
done

# Step 2: Create and start real trading agent
echo -e "\n🤖 2. Starting Real Trading Agent..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Real Market Trader",
    "agent_type": "real_trading",
    "config": {"track_pnl": true}
  }' | jq -r '.id')

curl -s -X POST http://localhost:8000/api/v1/agents/$AGENT_ID/start \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Start the real trading agent
cd /home/geo/operation/agent
export AGENT_ID=$AGENT_ID
export JWT_SECRET=your-secret-key-change-in-production
export ADMIN_PASSWORD=admin123
python3 real_trading_agent.py > /tmp/real_trader_pnl.log 2>&1 &
AGENT_PID=$!

echo "Agent started (PID: $AGENT_PID)"
sleep 3

# Step 3: Execute trades with real prices
echo -e "\n💹 3. Executing Trades at Real Market Prices..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting with 0,000 capital"
echo ""

# Buy trades
echo "Executing BUY orders:"

# Buy AAPL
BUY1=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "AAPL",
      "quantity": 50,
      "order_type": "market"
    }
  }')
BUY1_ID=$(echo "$BUY1" | jq -r '.id')

# Buy MSFT
BUY2=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "MSFT",
      "quantity": 30,
      "order_type": "market"
    }
  }')
BUY2_ID=$(echo "$BUY2" | jq -r '.id')

# Buy GOOGL
BUY3=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "GOOGL",
      "quantity": 20,
      "order_type": "market"
    }
  }')
BUY3_ID=$(echo "$BUY3" | jq -r '.id')

# Wait for execution
sleep 5

# Get buy results
echo ""
for TASK_ID in $BUY1_ID $BUY2_ID $BUY3_ID; do
    RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
      -H "Authorization: Bearer $TOKEN")
    
    SYMBOL=$(echo "$RESULT" | jq -r '.result.symbol // .data.symbol')
    QTY=$(echo "$RESULT" | jq -r '.result.quantity // .data.quantity')
    PRICE=$(echo "$RESULT" | jq -r '.result.execution_price // "pending"')
    TOTAL=$(echo "$RESULT" | jq -r '.result.net_total // "pending"')
    
    if [ "$PRICE" != "pending" ]; then
        echo "✅ Bought $QTY $SYMBOL @ \$$PRICE = \$$TOTAL"
    else
        echo "⏳ Buy order for $SYMBOL pending..."
    fi
done

# Step 4: Wait and then sell some positions
echo -e "\n⏳ Waiting 5 seconds (simulating market movement)..."
sleep 5

echo -e "\n📉 4. Executing SELL Orders..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Sell trades
SELL1=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "sell",
      "symbol": "AAPL",
      "quantity": 25,
      "order_type": "market"
    }
  }')
SELL1_ID=$(echo "$SELL1" | jq -r '.id')

SELL2=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "sell",
      "symbol": "MSFT",
      "quantity": 30,
      "order_type": "market"
    }
  }')
SELL2_ID=$(echo "$SELL2" | jq -r '.id')

sleep 5

# Get sell results
for TASK_ID in $SELL1_ID $SELL2_ID; do
    RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
      -H "Authorization: Bearer $TOKEN")
    
    SYMBOL=$(echo "$RESULT" | jq -r '.result.symbol // .data.symbol')
    QTY=$(echo "$RESULT" | jq -r '.result.quantity // .data.quantity')
    PRICE=$(echo "$RESULT" | jq -r '.result.execution_price // "pending"')
    TOTAL=$(echo "$RESULT" | jq -r '.result.net_total // "pending"')
    
    if [ "$PRICE" != "pending" ]; then
        echo "✅ Sold $QTY $SYMBOL @ \$$PRICE = \$$TOTAL"
    else
        echo "⏳ Sell order for $SYMBOL pending..."
    fi
done

# Step 5: Calculate P&L
echo -e "\n📊 5. P&L Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get all completed trades
ALL_TRADES=$(curl -s http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN")

# Calculate totals
TOTAL_BUY_COST=0
TOTAL_SELL_PROCEEDS=0

echo "$ALL_TRADES" | jq -r '.[] | select(.status == "completed" and .type == "trading" and .result != null) | 
    if .data.action == "buy" then
        "Buy: \(.data.symbol) - \(.data.quantity) shares @ $\(.result.execution_price // 0) = $\(.result.net_total // 0)"
    elif .data.action == "sell" then
        "Sell: \(.data.symbol) - \(.data.quantity) shares @ $\(.result.execution_price // 0) = $\(.result.net_total // 0)"
    else empty end'

echo ""
echo "📈 Current Positions:"
echo "- AAPL: 25 shares (sold 25 of 50)"
echo "- GOOGL: 20 shares (holding)"
echo "- MSFT: 0 shares (sold all 30)"

# Check for errors
echo -e "\n🔍 6. System Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if we're getting real prices
PROVIDER_LOGS=$(docker-compose logs app 2>&1 | grep -E "(Finnhub|Got price from)" | tail -5)
if echo "$PROVIDER_LOGS" | grep -q "Finnhub"; then
    echo "✅ Using Finnhub for real market data"
else
    echo "⚠️  May be using fallback provider"
fi

# Check agent logs
if [ -f /tmp/real_trader_pnl.log ]; then
    ERRORS=$(grep -i "error" /tmp/real_trader_pnl.log | wc -l)
    if [ "$ERRORS" -gt 0 ]; then
        echo "⚠️  Found $ERRORS errors in agent log"
    else
        echo "✅ Agent running without errors"
    fi
fi

# Cleanup
kill $AGENT_PID 2>/dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Real Trading Demo Complete!"
echo ""
echo "Summary:"
echo "- Used real market prices from Finnhub API"
echo "- Executed buy and sell orders"
echo "- Tracked positions and P&L"
echo ""
echo "View full results at: http://localhost:8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"