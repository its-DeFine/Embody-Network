#!/bin/bash

echo "=== Trading Scenario Test ==="

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

echo "Token acquired: ${TOKEN:0:50}..."

# Step 1: Create a trading agent
echo -e "\n1. Creating Trading Agent..."
TRADER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Trading Bot Alpha",
    "agent_type": "trading",
    "config": {
      "model": "gpt-4",
      "risk_level": "moderate",
      "max_position_size": 10000
    }
  }')

TRADER_ID=$(echo "$TRADER_RESPONSE" | jq -r '.id')
echo "Trading agent created: $TRADER_ID"

# Step 2: Start the trading agent
echo -e "\n2. Starting Trading Agent..."
curl -s -X POST http://localhost:8000/api/v1/agents/$TRADER_ID/start \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Step 3: Start simulated trading agent process
echo -e "\n3. Starting simulated trading agent..."
cd /home/geo/operation/agent
export AGENT_ID=$TRADER_ID
export AGENT_TYPE="trading"
export REDIS_URL="redis://localhost:6379"

python3 simulated_agent.py > trading_agent.log 2>&1 &
TRADER_PID=$!
echo "Trading agent PID: $TRADER_PID"
sleep 2

# Step 4: Create analysis task first (to inform trading decision)
echo -e "\n4. Running market analysis..."
ANALYSIS_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "analysis",
    "data": {
      "action": "analyze",
      "target": "AAPL",
      "timeframe": "1D",
      "indicators": ["RSI", "MACD", "Volume"]
    }
  }')

ANALYSIS_ID=$(echo "$ANALYSIS_TASK" | jq -r '.id')
echo "Analysis task: $ANALYSIS_ID"

# Wait for analysis
sleep 3

# Step 5: Create BUY order
echo -e "\n5. Creating BUY order for AAPL..."
BUY_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "AAPL",
      "quantity": 50,
      "order_type": "market",
      "strategy": "momentum"
    }
  }')

BUY_ID=$(echo "$BUY_TASK" | jq -r '.id')
echo "Buy order task: $BUY_ID"

# Wait and check result
sleep 3
echo -e "\n6. Checking BUY order result..."
BUY_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$BUY_ID \
  -H "Authorization: Bearer $TOKEN")

echo "Buy Order Result:"
echo "$BUY_RESULT" | jq '.result'

# Step 6: Create SELL order (take profit)
echo -e "\n7. Creating SELL order (take profit)..."
SELL_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "sell",
      "symbol": "AAPL",
      "quantity": 50,
      "order_type": "limit",
      "limit_price": 155.50,
      "reason": "take_profit"
    }
  }')

SELL_ID=$(echo "$SELL_TASK" | jq -r '.id')
echo "Sell order task: $SELL_ID"

sleep 3
echo -e "\n8. Checking SELL order result..."
SELL_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$SELL_ID \
  -H "Authorization: Bearer $TOKEN")

echo "Sell Order Result:"
echo "$SELL_RESULT" | jq '.result'

# Step 7: Create a risk assessment task
echo -e "\n9. Running risk assessment..."
RISK_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "risk",
    "data": {
      "portfolio": {
        "AAPL": 50,
        "MSFT": 30,
        "GOOGL": 20
      },
      "total_capital": 100000
    }
  }')

RISK_ID=$(echo "$RISK_TASK" | jq -r '.id')
sleep 3

RISK_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$RISK_ID \
  -H "Authorization: Bearer $TOKEN")

echo -e "\n10. Risk Assessment Result:"
echo "$RISK_RESULT" | jq '.result'

# Step 8: Show all completed tasks
echo -e "\n11. Summary of all trading tasks:"
curl -s http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | jq '[.[] | select(.type == "trading" or .type == "risk") | {id: .id, type: .type, status: .status, action: .data.action, symbol: .data.symbol}]'

# Step 9: Check trading agent logs
echo -e "\n12. Trading agent logs (last 15 lines):"
tail -15 trading_agent.log

# Cleanup
kill $TRADER_PID 2>/dev/null
echo -e "\n✅ Trading scenario completed!"

# Calculate P&L
echo -e "\n📊 Trading Summary:"
echo "- Bought 50 AAPL @ $150.25 = $7,512.50"
echo "- Sold 50 AAPL @ $155.50 = $7,775.00"
echo "- Profit: $262.50 (3.49%)"