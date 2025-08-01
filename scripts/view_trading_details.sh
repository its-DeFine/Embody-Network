#!/bin/bash

echo "=== Detailed Trading Results ==="

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

# Get all completed trading tasks with full details
echo -e "\n💹 Detailed Trading History:"
echo "================================"

curl -s http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | jq -r '
  [.[] | select(.type == "trading" and .status == "completed")] | 
  sort_by(.created_at) | 
  .[] | 
  "Trade ID: \(.id)
Time: \(.created_at)
Action: \(.data.action)
Symbol: \(.data.symbol)
Quantity: \(.data.quantity)
Order Type: \(.data.order_type // "market")
------ RESULT ------
\(.result | to_entries | map("\(.key): \(.value)") | join("\n"))
===================="'

# Check for trading results in Redis
echo -e "\n📊 Checking Redis for additional trading data..."
redis-cli --raw KEYS "task:*" | head -10 | while read key; do
    echo "Key: $key"
    redis-cli GET "$key" | jq -C '.' 2>/dev/null || echo "Not JSON"
    echo "---"
done

# Look for any trading logs
echo -e "\n📝 Recent Trading Logs:"
if [ -f /home/geo/operation/agent/trader.log ]; then
    echo "=== Trader Log ==="
    tail -20 /home/geo/operation/agent/trader.log
fi

if [ -f /home/geo/operation/agent/analyst.log ]; then
    echo -e "\n=== Analyst Log ==="
    tail -20 /home/geo/operation/agent/analyst.log
fi

# Check the frontend for viewing results
echo -e "\n🖥️  Frontend Access:"
echo "You can view the trading results in the web UI at:"
echo "http://localhost:8000"
echo ""
echo "Login with:"
echo "Email: admin@example.com"
echo "Password: admin123"
echo ""
echo "Navigate to:"
echo "- Dashboard: Overview of all activity"
echo "- Tasks: Detailed view of all trading tasks"
echo "- Agents: Status of trading agents"

# Summary statistics
echo -e "\n📈 Trading Summary Statistics:"
curl -s http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | jq '
  [.[] | select(.type == "trading" and .status == "completed")] |
  {
    total_trades: length,
    symbols_traded: [.[].data.symbol] | unique,
    buy_orders: [.[] | select(.data.action == "buy")] | length,
    sell_orders: [.[] | select(.data.action == "sell")] | length,
    market_orders: [.[] | select(.data.order_type == "market" or .data.order_type == null)] | length,
    limit_orders: [.[] | select(.data.order_type == "limit")] | length,
    latest_trade: (sort_by(.created_at) | reverse | .[0])
  }'