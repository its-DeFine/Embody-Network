#!/bin/bash

echo "=== Advanced Trading Demo with Multiple Agents ==="

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

# Step 1: Create multiple specialized agents
echo -e "\n1. Creating specialized trading agents..."

# Analysis Agent
ANALYST=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Market Analyst", "agent_type": "analysis", "config": {}}' | jq -r '.id')
echo "✅ Analysis Agent: $ANALYST"

# Trading Agent
TRADER=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Trade Executor", "agent_type": "trading", "config": {}}' | jq -r '.id')
echo "✅ Trading Agent: $TRADER"

# Risk Agent
RISK_MGR=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Risk Manager", "agent_type": "risk", "config": {}}' | jq -r '.id')
echo "✅ Risk Agent: $RISK_MGR"

# Start all agents
curl -s -X POST http://localhost:8000/api/v1/agents/$ANALYST/start -H "Authorization: Bearer $TOKEN" > /dev/null
curl -s -X POST http://localhost:8000/api/v1/agents/$TRADER/start -H "Authorization: Bearer $TOKEN" > /dev/null
curl -s -X POST http://localhost:8000/api/v1/agents/$RISK_MGR/start -H "Authorization: Bearer $TOKEN" > /dev/null

# Step 2: Create a trading team
echo -e "\n2. Creating Trading Team..."
TEAM_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/teams \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Algo Trading Team",
    "description": "Automated trading with risk management",
    "agent_ids": ["'$ANALYST'", "'$TRADER'", "'$RISK_MGR'"]
  }')

TEAM_ID=$(echo "$TEAM_RESPONSE" | jq -r '.id')
echo "✅ Team created: $TEAM_ID"

# Step 3: Start agent processes
echo -e "\n3. Starting agent processes..."
cd /home/geo/operation/agent

# Start Analysis Agent
AGENT_ID=$ANALYST AGENT_TYPE=analysis python3 simulated_agent.py > analyst.log 2>&1 &
PID1=$!

# Start Trading Agent  
AGENT_ID=$TRADER AGENT_TYPE=trading python3 simulated_agent.py > trader.log 2>&1 &
PID2=$!

# Start Risk Agent
AGENT_ID=$RISK_MGR AGENT_TYPE=risk python3 simulated_agent.py > risk.log 2>&1 &
PID3=$!

echo "Agent processes started: $PID1, $PID2, $PID3"
sleep 3

# Step 4: Execute trading workflow
echo -e "\n4. Executing Trading Workflow..."

# 4.1: Market Analysis
echo -e "\n📊 Running market analysis..."
ANALYSIS=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "analysis",
    "data": {
      "action": "analyze",
      "targets": ["AAPL", "MSFT", "GOOGL"],
      "strategy": "momentum",
      "timeframe": "1H"
    }
  }')

sleep 3

# 4.2: Risk Assessment
echo -e "\n🛡️ Assessing portfolio risk..."
RISK_CHECK=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "risk",
    "data": {
      "action": "assess",
      "capital": 100000,
      "current_positions": {"AAPL": 100, "MSFT": 50},
      "new_trade": {"symbol": "GOOGL", "quantity": 20}
    }
  }')

sleep 3

# 4.3: Execute Trades
echo -e "\n💰 Executing trades based on analysis..."

# Buy GOOGL
BUY1=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
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

# Sell some AAPL
SELL1=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "trading",
    "data": {
      "action": "sell",
      "symbol": "AAPL",
      "quantity": 30,
      "order_type": "market",
      "reason": "rebalancing"
    }
  }')

sleep 3

# Step 5: Team Coordination Task
echo -e "\n5. Team Coordination: Complex Trading Strategy..."
TEAM_TASK=$(curl -s -X POST http://localhost:8000/api/v1/teams/$TEAM_ID/coordinate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Execute momentum trading strategy with risk limits",
    "context": {
      "strategy": "momentum",
      "risk_limit": 0.02,
      "target_symbols": ["NVDA", "AMD", "TSLA"],
      "capital": 50000
    }
  }')

echo "$TEAM_TASK" | jq '.'

# Step 6: Show results
echo -e "\n6. Trading Results Summary..."
sleep 5

# Get all completed tasks
echo -e "\n📋 Completed Tasks:"
curl -s http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | jq '[.[] | select(.status == "completed") | {
    type: .type,
    action: .data.action,
    symbol: .data.symbol,
    result: .result
  }]' | jq -r '.[] | "
Type: \(.type)
Action: \(.action // "N/A")
Symbol: \(.symbol // "N/A")
Result: \(.result | tostring | .[0:100])...
---"'

# Show agent activity
echo -e "\n📊 Agent Activity:"
echo "Analysis Agent (last 5 lines):"
tail -5 analyst.log
echo -e "\nTrading Agent (last 5 lines):"
tail -5 trader.log
echo -e "\nRisk Agent (last 5 lines):"
tail -5 risk.log

# Cleanup
kill $PID1 $PID2 $PID3 2>/dev/null
echo -e "\n✅ Advanced trading demo completed!"

# Final summary
echo -e "\n🎯 Demo Summary:"
echo "- Created 3 specialized agents (Analysis, Trading, Risk)"
echo "- Formed a coordinated trading team"
echo "- Executed market analysis on multiple stocks"
echo "- Performed risk assessment before trading"
echo "- Executed buy/sell orders"
echo "- Demonstrated team coordination for complex strategies"