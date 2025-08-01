#\!/bin/bash

echo "=== REAL P&L CHECK ==="
echo "Date: $(date)"
echo ""

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate"
    exit 1
fi

# Check if we have any trades
echo "📊 Checking Trading History..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TRADES=$(curl -s http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" | \
  jq '[.[] | select(.type == "trading" and .status == "completed")]')

TRADE_COUNT=$(echo "$TRADES" | jq 'length')

if [ "$TRADE_COUNT" -eq 0 ]; then
    echo "⚠️  No trades have been executed yet\!"
    echo ""
    echo "The system is ready but hasn't made any trades."
    echo "Let me execute some trades now to show P&L..."
    echo ""
    
    # Create a trading agent
    echo "1️⃣ Creating trading agent..."
    AGENT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/agents \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"name": "P&L Demo Trader", "agent_type": "real_trading"}')
    
    AGENT_ID=$(echo "$AGENT_RESPONSE" | jq -r '.id')
    
    if [ \! -z "$AGENT_ID" ] && [ "$AGENT_ID" \!= "null" ]; then
        echo "✅ Agent created: $AGENT_ID"
        
        # Start the agent
        curl -s -X POST http://localhost:8000/api/v1/agents/$AGENT_ID/start \
          -H "Authorization: Bearer $TOKEN" > /dev/null
        
        echo ""
        echo "2️⃣ Executing demo trades with real prices..."
        echo ""
        
        # Execute some crypto trades
        for TRADE in "BTC:0.001" "ETH:0.1" "SOL:5"; do
            SYMBOL=$(echo $TRADE | cut -d: -f1)
            QTY=$(echo $TRADE | cut -d: -f2)
            
            echo -n "Buying $QTY $SYMBOL... "
            
            TASK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
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
            
            TASK_ID=$(echo "$TASK_RESPONSE" | jq -r '.id')
            
            if [ \! -z "$TASK_ID" ] && [ "$TASK_ID" \!= "null" ]; then
                sleep 2
                
                # Get result
                RESULT=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
                  -H "Authorization: Bearer $TOKEN")
                
                PRICE=$(echo "$RESULT" | jq -r '.result.execution_price // empty')
                TOTAL=$(echo "$RESULT" | jq -r '.result.net_total // empty')
                
                if [ \! -z "$PRICE" ]; then
                    echo "✅ Bought at \$$PRICE (total: \$$TOTAL)"
                else
                    echo "❌ Failed"
                fi
            fi
        done
        
        echo ""
        echo "3️⃣ Waiting 10 seconds for market movement..."
        sleep 10
        
        # Re-fetch trades
        TRADES=$(curl -s http://localhost:8000/api/v1/tasks \
          -H "Authorization: Bearer $TOKEN" | \
          jq '[.[] | select(.type == "trading" and .status == "completed")]')
        
        TRADE_COUNT=$(echo "$TRADES" | jq 'length')
    fi
fi

if [ "$TRADE_COUNT" -gt 0 ]; then
    echo ""
    echo "💰 PORTFOLIO & P&L CALCULATION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Calculate positions
    echo "$TRADES" | jq -r '
    group_by(.data.symbol) | 
    map({
        symbol: .[0].data.symbol,
        trades: map({
            action: .data.action,
            quantity: .data.quantity,
            price: .result.execution_price,
            total: .result.net_total,
            time: .created_at
        })
    }) | .[] | 
    "
📈 \(.symbol) Position:
━━━━━━━━━━━━━━━━━━━━━
" + (
    .trades | map(
        "  • \(.action | ascii_upcase) \(.quantity) @ $\(.price) = $\(.total)"
    ) | join("\n")
    )'
    
    echo ""
    echo "📊 REAL-TIME P&L CALCULATION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Get unique symbols
    SYMBOLS=$(echo "$TRADES" | jq -r '[.[].data.symbol] | unique | .[]')
    
    TOTAL_INVESTED=0
    TOTAL_VALUE=0
    
    echo "Symbol   Quantity    Avg Cost    Current     Value       P&L      %"
    echo "────────────────────────────────────────────────────────────────────"
    
    for SYMBOL in $SYMBOLS; do
        # Calculate position
        POSITION=$(echo "$TRADES" | jq -r --arg sym "$SYMBOL" '
            [.[] | select(.data.symbol == $sym)] |
            {
                quantity: ([.[] | select(.data.action == "buy")] | map(.data.quantity) | add // 0) - 
                         ([.[] | select(.data.action == "sell")] | map(.data.quantity) | add // 0),
                cost: [.[] | select(.data.action == "buy")] | map(.result.net_total) | add // 0,
                revenue: [.[] | select(.data.action == "sell")] | map(.result.net_total) | add // 0
            }')
        
        QTY=$(echo "$POSITION" | jq -r '.quantity')
        COST=$(echo "$POSITION" | jq -r '.cost')
        
        if [ "$QTY" \!= "0" ] && [ "$QTY" \!= "null" ]; then
            # Get current price
            CURRENT=$(curl -s http://localhost:8000/api/v1/market/price/$SYMBOL \
              -H "Authorization: Bearer $TOKEN" | jq -r '.price // 0')
            
            if [ "$CURRENT" \!= "0" ]; then
                AVG_COST=$(echo "scale=2; $COST / $QTY" | bc)
                VALUE=$(echo "scale=2; $QTY * $CURRENT" | bc)
                PNL=$(echo "scale=2; $VALUE - $COST" | bc)
                PNL_PCT=$(echo "scale=2; ($PNL / $COST) * 100" | bc)
                
                printf "%-8s %8s  \$%8s  \$%8s  \$%8s  \$%8s  %6s%%\n" \
                    "$SYMBOL" "$QTY" "$AVG_COST" "$CURRENT" "$VALUE" "$PNL" "$PNL_PCT"
                
                TOTAL_INVESTED=$(echo "$TOTAL_INVESTED + $COST" | bc)
                TOTAL_VALUE=$(echo "$TOTAL_VALUE + $VALUE" | bc)
            fi
        fi
    done
    
    echo "────────────────────────────────────────────────────────────────────"
    
    if [ "$TOTAL_INVESTED" \!= "0" ]; then
        TOTAL_PNL=$(echo "scale=2; $TOTAL_VALUE - $TOTAL_INVESTED" | bc)
        TOTAL_PNL_PCT=$(echo "scale=2; ($TOTAL_PNL / $TOTAL_INVESTED) * 100" | bc)
        
        printf "\n%-8s %8s  \$%8s  %9s  \$%8s  \$%8s  %6s%%\n" \
            "TOTAL" "" "$TOTAL_INVESTED" "" "$TOTAL_VALUE" "$TOTAL_PNL" "$TOTAL_PNL_PCT"
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if (( $(echo "$TOTAL_PNL > 0" | bc -l) )); then
            echo "🎉 PROFIT: \$$TOTAL_PNL ($TOTAL_PNL_PCT%)"
        elif (( $(echo "$TOTAL_PNL < 0" | bc -l) )); then
            echo "📉 LOSS: \$$TOTAL_PNL ($TOTAL_PNL_PCT%)"
        else
            echo "➡️  BREAKEVEN: \$0.00"
        fi
    fi
    
    echo ""
    echo "📌 Note: P&L fluctuates with real market prices"
    echo "   Data sources: CoinGecko, Binance, Yahoo Finance"
else
    echo "No trading activity found."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
