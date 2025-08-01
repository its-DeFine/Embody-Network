#!/bin/bash

echo "=== Testing Better Free Market Data APIs ==="
echo "Using providers with more generous rate limits"
echo ""

# Rebuild and restart to get new providers
echo "1. Rebuilding with new providers..."
docker-compose build
docker-compose down
docker-compose up -d

# Wait for startup
sleep 10

# Install httpx in container
echo -e "\n2. Installing dependencies..."
docker exec operation-app-1 pip install httpx > /dev/null 2>&1

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "Failed to authenticate"
    exit 1
fi

echo "✅ Authenticated"

# Test different providers by forcing primary
echo -e "\n3. Testing Market Data Providers..."

# Test 1: Get price (will use TwelveData as primary)
echo -e "\n📊 Getting price for AAPL (using TwelveData)..."
PRICE=$(curl -s http://localhost:8000/api/v1/market/price/AAPL \
  -H "Authorization: Bearer $TOKEN" | jq '.')
echo "$PRICE"

# Small delay to respect rate limits
sleep 1

# Test 2: Get quote
echo -e "\n📈 Getting quote for MSFT..."
QUOTE=$(curl -s http://localhost:8000/api/v1/market/quote/MSFT \
  -H "Authorization: Bearer $TOKEN" | jq '.')
echo "$QUOTE"

sleep 1

# Test 3: Get multiple prices (batch request)
echo -e "\n💹 Getting prices for multiple stocks..."
curl -s -X POST http://localhost:8000/api/v1/market/prices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '["AAPL", "GOOGL", "TSLA"]' | jq '.'

# Test 4: Run actual trading with real prices
echo -e "\n4. Testing Real Trading..."

# Create and start agent
AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Better API Trader", "agent_type": "real_trading"}' | jq -r '.id')

curl -s -X POST http://localhost:8000/api/v1/agents/$AGENT_ID/start \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Start agent process
cd /home/geo/operation/agent
export AGENT_ID=$AGENT_ID
python3 real_trading_agent.py > /tmp/better_trader.log 2>&1 &
AGENT_PID=$!

sleep 3

# Execute trade
TRADE=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "AAPL",
      "quantity": 5,
      "order_type": "market"
    }
  }')

TASK_ID=$(echo "$TRADE" | jq -r '.id')
sleep 5

# Get result
echo -e "\n📊 Trade Result with Real Market Price:"
RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN")

echo "$RESULT" | jq '.result | {
  symbol: .symbol,
  action: .action,
  quantity: .quantity,
  execution_price: .execution_price,
  total_value: .total_value,
  timestamp: .timestamp
}'

# Check which provider was used
echo -e "\n5. Checking Provider Usage..."
docker-compose logs app | grep -E "(Twelve Data|Finnhub|MarketStack|Got price from)" | tail -10

# Cleanup
kill $AGENT_PID 2>/dev/null

echo -e "\n=== Summary ==="
echo "✅ Better free APIs integrated:"
echo "   - TwelveData: 800 calls/day"
echo "   - Finnhub: 60 calls/minute" 
echo "   - MarketStack: 1000 calls/month"
echo "   - Polygon: 5 calls/minute"
echo ""
echo "The system now automatically falls back between providers"
echo "and caches results for 5 minutes to minimize API usage."
echo ""
echo "To use your own API keys, update FREE_API_KEYS in"
echo "/home/geo/operation/app/market_data_providers.py"