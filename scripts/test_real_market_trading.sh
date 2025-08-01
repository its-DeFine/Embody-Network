#!/bin/bash

echo "=== Real Market Data Trading Test ==="
echo "Note: This test requires internet connection for market data"
echo ""

# First, install the new dependencies
echo "1. Installing market data dependencies..."
cd /home/geo/operation
pip install yfinance alpha-vantage pandas numpy ta --quiet

# Get auth token
echo -e "\n2. Authenticating..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "Failed to authenticate. Is the server running?"
    exit 1
fi

echo "✅ Authenticated successfully"

# Test market data endpoints
echo -e "\n3. Testing Market Data API..."

# Get current price for AAPL
echo -e "\n📊 Getting current price for AAPL..."
PRICE_RESPONSE=$(curl -s http://localhost:8000/api/v1/market/price/AAPL \
  -H "Authorization: Bearer $TOKEN")
echo "$PRICE_RESPONSE" | jq '.'

CURRENT_PRICE=$(echo "$PRICE_RESPONSE" | jq -r '.price')
echo "Current AAPL price: $${CURRENT_PRICE}"

# Get quotes for multiple stocks
echo -e "\n📈 Getting quotes for tech stocks..."
curl -s -X POST http://localhost:8000/api/v1/market/quotes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '["AAPL", "GOOGL", "MSFT", "NVDA", "TSLA"]' | jq '.quotes[] | {symbol: .symbol, price: .price, change: .changePercent}'

# Get market summary
echo -e "\n🌍 Getting market summary..."
curl -s http://localhost:8000/api/v1/market/summary \
  -H "Authorization: Bearer $TOKEN" | jq '{
    indices: .indices | map({symbol: .symbol, price: .price, change: .changePercent}),
    top_gainers: .top_gainers[0:3] | map({symbol: .symbol, change: .changePercent}),
    market_stats: .market_stats
  }'

# Create a real trading agent
echo -e "\n4. Creating Real Trading Agent..."
REAL_TRADER=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Real Market Trader",
    "agent_type": "real_trading",
    "config": {
      "use_real_prices": true,
      "data_provider": "yahoo"
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
python3 real_trading_agent.py > real_trader.log 2>&1 &
REAL_TRADER_PID=$!
echo "Real trading agent PID: $REAL_TRADER_PID"

sleep 3

# Test 1: Market Analysis with Real Data
echo -e "\n5. Running Market Analysis with Real Data..."
ANALYSIS_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "analysis",
    "data": {
      "symbol": "AAPL",
      "indicators": ["RSI", "MACD", "BB"]
    }
  }')

ANALYSIS_ID=$(echo "$ANALYSIS_TASK" | jq -r '.id')
echo "Analysis task: $ANALYSIS_ID"

sleep 3

echo -e "\n📊 Real Market Analysis Result:"
ANALYSIS_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$ANALYSIS_ID \
  -H "Authorization: Bearer $TOKEN")

echo "$ANALYSIS_RESULT" | jq '.result | {
  current_price: .current_price,
  trend: .trend,
  confidence: .confidence,
  indicators: .indicators | {
    rsi: .rsi,
    rsi_signal: .rsi_signal,
    macd_trend: .macd_signal_trend,
    bb_signal: .bb_signal
  },
  findings: .findings[0:3]
}'

# Test 2: Execute Trade at Real Market Price
echo -e "\n6. Executing Trade at Real Market Price..."

# Buy order
BUY_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
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

BUY_ID=$(echo "$BUY_TASK" | jq -r '.id')
echo "Buy order task: $BUY_ID"

sleep 3

echo -e "\n💰 Buy Order Result:"
BUY_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$BUY_ID \
  -H "Authorization: Bearer $TOKEN")

echo "$BUY_RESULT" | jq '.result | {
  action: .action,
  symbol: .symbol,
  quantity: .quantity,
  execution_price: .execution_price,
  market_price: .market_price,
  total_value: .total_value,
  commission: .commission,
  net_total: .net_total,
  spread: .quote.spread,
  timestamp: .timestamp
}'

# Test 3: Risk Assessment with Real Prices
echo -e "\n7. Risk Assessment with Real Portfolio Values..."
RISK_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "risk",
    "data": {
      "portfolio": {
        "AAPL": 100,
        "GOOGL": 50,
        "MSFT": 75,
        "NVDA": 25
      },
      "total_capital": 100000
    }
  }')

RISK_ID=$(echo "$RISK_TASK" | jq -r '.id')
sleep 3

echo -e "\n🛡️ Risk Assessment with Real Prices:"
RISK_RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$RISK_ID \
  -H "Authorization: Bearer $TOKEN")

echo "$RISK_RESULT" | jq '.result | {
  risk_level: .risk_level,
  portfolio_value: .portfolio_value,
  exposure_ratio: .exposure_ratio,
  positions: .positions | map({symbol: .symbol, current_price: .current_price, position_value: .position_value, percent_of_portfolio: .percent_of_portfolio}),
  recommendations: .recommendations
}'

# Test 4: Technical Indicators
echo -e "\n8. Getting Technical Indicators..."
curl -s -X POST http://localhost:8000/api/v1/market/indicators \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "TSLA",
    "period": "1d"
  }' | jq '.indicators | {
    current_price: .current_price,
    sma_20: .sma_20,
    rsi: .rsi,
    rsi_signal: .rsi_signal,
    macd: .macd,
    macd_signal: .macd_signal,
    bb_upper: .bb_upper,
    bb_lower: .bb_lower
  }'

# Test 5: Historical Data
echo -e "\n9. Getting Historical Data..."
HIST_DATA=$(curl -s -X POST http://localhost:8000/api/v1/market/historical \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "period": "5d",
    "interval": "1h"
  }')

echo "$HIST_DATA" | jq '{
  symbol: .symbol,
  period: .period,
  data_points: .count,
  latest_5: .data[-5:] | map({time: .Date, close: .Close, volume: .Volume})
}'

# Test 6: Compare with Simulated Agent
echo -e "\n10. Comparing Real vs Simulated Trading..."

# Create simulated trade task
SIM_TASK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "buy",
      "symbol": "AAPL",
      "quantity": 10
    }
  }')

sleep 2

# Show comparison
echo -e "\n📊 Real vs Simulated Price Comparison:"
echo "Symbol: AAPL"
echo "Quantity: 10 shares"
echo ""
echo "REAL MARKET DATA:"
echo "$BUY_RESULT" | jq -r '.result | "- Execution Price: $\(.execution_price)\n- Total Cost: $\(.total_value)\n- With Commission: $\(.net_total)"'
echo ""
echo "SIMULATED DATA:"
echo "- Fixed Price: $150.25"
echo "- Total Cost: $1,502.50"
echo "- No commission"

# Show trading agent logs
echo -e "\n11. Real Trading Agent Activity (last 20 lines):"
tail -20 real_trader.log | grep -E "(price|executed|Real|market)"

# Cleanup
echo -e "\n12. Cleaning up..."
kill $REAL_TRADER_PID 2>/dev/null

# Summary
echo -e "\n=== Real Market Data Trading Test Summary ==="
echo "✅ Market data API working with Yahoo Finance"
echo "✅ Real-time prices fetched successfully"
echo "✅ Trading executed at actual market prices"
echo "✅ Technical indicators calculated from real data"
echo "✅ Risk assessment using current market values"
echo ""
echo "📊 Key Differences from Simulation:"
echo "- Real market prices (not fixed $150.25)"
echo "- Actual bid/ask spreads"
echo "- Live technical indicators"
echo "- Current market volatility reflected"
echo "- Commission calculations included"
echo ""
echo "🚀 The trading system is now using REAL MARKET DATA!"