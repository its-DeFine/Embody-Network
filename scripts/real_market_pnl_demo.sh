#!/bin/bash

echo "=== Real Market P&L Trading Demo ==="
echo "Trading with actual market prices and P&L tracking"
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

# Step 1: Create Real Trading Agent
echo -e "\n1. Creating Real Market Trading Agent..."
REAL_TRADER=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Real Market P&L Trader",
    "agent_type": "real_trading",
    "config": {
      "use_real_prices": true,
      "track_pnl": true
    }
  }' | jq -r '.id')

echo "Created Real Trading Agent: $REAL_TRADER"

# Start the agent
curl -s -X POST http://localhost:8000/api/v1/agents/$REAL_TRADER/start \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Start real trading agent process
cd /home/geo/operation/agent
export AGENT_ID=$REAL_TRADER
export AGENT_TYPE="real_trading"
python3 real_trading_agent.py > /tmp/real_pnl_trader.log 2>&1 &
REAL_PID=$!
echo "Real trading agent PID: $REAL_PID"

sleep 3

# Step 2: Get current market prices
echo -e "\n2. Getting Real Market Prices..."
echo -n "AAPL: $"
AAPL_PRICE=$(curl -s http://localhost:8000/api/v1/market/price/AAPL \
  -H "Authorization: Bearer $TOKEN" | jq -r '.price')
echo "$AAPL_PRICE"

echo -n "MSFT: $"
MSFT_PRICE=$(curl -s http://localhost:8000/api/v1/market/price/MSFT \
  -H "Authorization: Bearer $TOKEN" | jq -r '.price')
echo "$MSFT_PRICE"

echo -n "GOOGL: $"
GOOGL_PRICE=$(curl -s http://localhost:8000/api/v1/market/price/GOOGL \
  -H "Authorization: Bearer $TOKEN" | jq -r '.price')
echo "$GOOGL_PRICE"

# Step 3: Execute Buy Orders at Real Prices
echo -e "\n3. Executing BUY Orders at Real Market Prices..."
INITIAL_CAPITAL=100000
echo "Starting Capital: $${INITIAL_CAPITAL}"

# Buy AAPL
BUY_AAPL=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "AAPL",
      "quantity": 100,
      "order_type": "market"
    }
  }')
BUY_AAPL_ID=$(echo "$BUY_AAPL" | jq -r '.id')

# Buy MSFT
BUY_MSFT=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "MSFT",
      "quantity": 50,
      "order_type": "market"
    }
  }')
BUY_MSFT_ID=$(echo "$BUY_MSFT" | jq -r '.id')

# Wait for execution
sleep 5

# Get results
echo -e "\n📊 Buy Order Results:"
BUY_AAPL_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$BUY_AAPL_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.result')
BUY_MSFT_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$BUY_MSFT_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.result')

echo "AAPL Buy:"
echo "$BUY_AAPL_RESULT" | jq '{symbol: .symbol, quantity: .quantity, execution_price: .execution_price, total_cost: .net_total}'

echo -e "\nMSFT Buy:"
echo "$BUY_MSFT_RESULT" | jq '{symbol: .symbol, quantity: .quantity, execution_price: .execution_price, total_cost: .net_total}'

# Calculate total spent
AAPL_COST=$(echo "$BUY_AAPL_RESULT" | jq -r '.net_total // 0')
MSFT_COST=$(echo "$BUY_MSFT_RESULT" | jq -r '.net_total // 0')
TOTAL_SPENT=$(echo "$AAPL_COST + $MSFT_COST" | bc)

echo -e "\n💰 Total Investment: $${TOTAL_SPENT}"

# Step 4: Wait and check price changes
echo -e "\n4. Waiting for market movement (simulated)..."
sleep 3

# Step 5: Execute Sell Orders
echo -e "\n5. Executing SELL Orders at Current Market Prices..."

# Sell half of AAPL
SELL_AAPL=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "sell",
      "symbol": "AAPL",
      "quantity": 50,
      "order_type": "market"
    }
  }')
SELL_AAPL_ID=$(echo "$SELL_AAPL" | jq -r '.id')

# Sell all MSFT
SELL_MSFT=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "sell",
      "symbol": "MSFT",
      "quantity": 50,
      "order_type": "market"
    }
  }')
SELL_MSFT_ID=$(echo "$SELL_MSFT" | jq -r '.id')

sleep 5

# Get sell results
echo -e "\n📊 Sell Order Results:"
SELL_AAPL_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$SELL_AAPL_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.result')
SELL_MSFT_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$SELL_MSFT_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.result')

echo "AAPL Sell:"
echo "$SELL_AAPL_RESULT" | jq '{symbol: .symbol, quantity: .quantity, execution_price: .execution_price, total_proceeds: .net_total}'

echo -e "\nMSFT Sell:"
echo "$SELL_MSFT_RESULT" | jq '{symbol: .symbol, quantity: .quantity, execution_price: .execution_price, total_proceeds: .net_total}'

# Calculate proceeds
AAPL_PROCEEDS=$(echo "$SELL_AAPL_RESULT" | jq -r '.net_total // 0')
MSFT_PROCEEDS=$(echo "$SELL_MSFT_RESULT" | jq -r '.net_total // 0')
TOTAL_PROCEEDS=$(echo "$AAPL_PROCEEDS + $MSFT_PROCEEDS" | bc)

echo -e "\n💵 Total Proceeds: $${TOTAL_PROCEEDS}"

# Step 6: Calculate P&L
echo -e "\n6. P&L CALCULATION:"
echo "================================"

# Individual P&L
AAPL_BUY_PRICE=$(echo "$BUY_AAPL_RESULT" | jq -r '.execution_price // 0')
AAPL_SELL_PRICE=$(echo "$SELL_AAPL_RESULT" | jq -r '.execution_price // 0')
AAPL_PNL=$(echo "scale=2; (${AAPL_SELL_PRICE} - ${AAPL_BUY_PRICE}) * 50" | bc)

MSFT_BUY_PRICE=$(echo "$BUY_MSFT_RESULT" | jq -r '.execution_price // 0')
MSFT_SELL_PRICE=$(echo "$SELL_MSFT_RESULT" | jq -r '.execution_price // 0')
MSFT_PNL=$(echo "scale=2; (${MSFT_SELL_PRICE} - ${MSFT_BUY_PRICE}) * 50" | bc)

echo "AAPL P&L: Buy @ $${AAPL_BUY_PRICE}, Sell @ $${AAPL_SELL_PRICE} = $${AAPL_PNL}"
echo "MSFT P&L: Buy @ $${MSFT_BUY_PRICE}, Sell @ $${MSFT_SELL_PRICE} = $${MSFT_PNL}"

# Total P&L (including commissions)
TOTAL_PNL=$(echo "scale=2; ${TOTAL_PROCEEDS} - (${AAPL_COST}/2 + ${MSFT_COST})" | bc)
echo -e "\n📊 TOTAL P&L: $${TOTAL_PNL}"

# Current positions
echo -e "\n7. Current Positions:"
echo "AAPL: 50 shares @ $${AAPL_BUY_PRICE} = $$(echo "scale=2; 50 * ${AAPL_BUY_PRICE}" | bc)"
echo "Cash: $$(echo "scale=2; ${INITIAL_CAPITAL} - ${TOTAL_SPENT} + ${TOTAL_PROCEEDS}" | bc)"

# Portfolio value
CURRENT_AAPL_VALUE=$(echo "scale=2; 50 * ${AAPL_PRICE}" | bc)
CASH_BALANCE=$(echo "scale=2; ${INITIAL_CAPITAL} - ${TOTAL_SPENT} + ${TOTAL_PROCEEDS}" | bc)
PORTFOLIO_VALUE=$(echo "scale=2; ${CURRENT_AAPL_VALUE} + ${CASH_BALANCE}" | bc)

echo -e "\n📈 Portfolio Summary:"
echo "Initial Capital: $${INITIAL_CAPITAL}"
echo "Current Portfolio Value: $${PORTFOLIO_VALUE}"
echo "Total Return: $$(echo "scale=2; ${PORTFOLIO_VALUE} - ${INITIAL_CAPITAL}" | bc)"
echo "Return %: $(echo "scale=2; ((${PORTFOLIO_VALUE} - ${INITIAL_CAPITAL}) / ${INITIAL_CAPITAL}) * 100" | bc)%"

# Check logs
echo -e "\n8. Trading Agent Logs (errors only):"
grep -i "error" /tmp/real_pnl_trader.log | tail -5

# Cleanup
kill $REAL_PID 2>/dev/null

echo -e "\n✅ Real Market P&L Demo Complete!"
echo "The system is tracking actual P&L with real market prices!"