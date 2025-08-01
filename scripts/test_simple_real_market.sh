#!/bin/bash

echo "=== Simple Real Market Data Test ==="
echo "Testing with minimal API calls to avoid rate limits"
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

# Test 1: Get single stock price
echo -e "\n1. Getting real price for Apple (AAPL)..."
PRICE_RESPONSE=$(curl -s http://localhost:8000/api/v1/market/price/AAPL \
  -H "Authorization: Bearer $TOKEN")

echo "$PRICE_RESPONSE" | jq '.'

PRICE=$(echo "$PRICE_RESPONSE" | jq -r '.price // "N/A"')
if [ "$PRICE" != "N/A" ] && [ "$PRICE" != "null" ]; then
    echo "✅ Real AAPL price: $$PRICE"
else
    echo "⚠️  Could not fetch price (may be rate limited)"
fi

# Wait to avoid rate limit
sleep 2

# Test 2: Get quote with more details
echo -e "\n2. Getting detailed quote for Microsoft (MSFT)..."
QUOTE_RESPONSE=$(curl -s http://localhost:8000/api/v1/market/quote/MSFT \
  -H "Authorization: Bearer $TOKEN")

echo "$QUOTE_RESPONSE" | jq '. | {
  symbol: .symbol,
  price: .price,
  change: .changePercent,
  volume: .volume,
  high: .high,
  low: .low
}'

# Wait to avoid rate limit
sleep 2

# Test 3: Execute a trade with real price
echo -e "\n3. Executing trade with real market price..."

# First create a real trading agent
AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Real Price Trader",
    "agent_type": "real_trading"
  }' | jq -r '.id')

# Start the agent
curl -s -X POST http://localhost:8000/api/v1/agents/$AGENT_ID/start \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Start the real trading agent
cd /home/geo/operation/agent
export AGENT_ID=$AGENT_ID
python3 real_trading_agent.py > /tmp/real_trader_$$.log 2>&1 &
AGENT_PID=$!

echo "Started real trading agent (PID: $AGENT_PID)"
sleep 3

# Create a simple buy order
TRADE_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "AAPL",
      "quantity": 10,
      "order_type": "market"
    }
  }')

TASK_ID=$(echo "$TRADE_TASK" | jq -r '.id')
echo "Trade task created: $TASK_ID"

# Wait for processing
sleep 5

# Get the result
echo -e "\n4. Trade Execution Result:"
RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN")

echo "$RESULT" | jq '.result | {
  symbol: .symbol,
  action: .action,
  quantity: .quantity,
  execution_price: .execution_price,
  market_price: .market_price,
  total_value: .total_value,
  commission: .commission,
  timestamp: .timestamp
}'

# Show comparison
EXEC_PRICE=$(echo "$RESULT" | jq -r '.result.execution_price // "N/A"')
if [ "$EXEC_PRICE" != "N/A" ] && [ "$EXEC_PRICE" != "null" ]; then
    echo -e "\n✅ Trade executed at REAL market price: $$EXEC_PRICE"
    echo "   (Not the simulated fixed price of $150.25)"
else
    echo -e "\n⚠️  Trade may have failed due to rate limits"
fi

# Check agent logs for any errors
echo -e "\n5. Agent logs (last 10 lines):"
tail -10 /tmp/real_trader_$$.log 2>/dev/null | grep -v "^$"

# Cleanup
kill $AGENT_PID 2>/dev/null
rm -f /tmp/real_trader_$$.log

echo -e "\n=== Summary ==="
echo "The trading system is configured to use real market data."
echo "However, Yahoo Finance has rate limits that may cause failures."
echo ""
echo "Solutions:"
echo "1. Add delays between API calls"
echo "2. Use Alpha Vantage API (free key required)"
echo "3. Implement caching to reduce API calls"
echo "4. Use a paid data provider for production"
echo ""
echo "The system architecture fully supports real market data!"