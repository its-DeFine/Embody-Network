#!/bin/bash
# Real-time monitoring script for 24/7 trading system

set -e

# Configuration
MONITOR_INTERVAL=30
HEALTH_CHECK_URL="http://localhost:8000/api/v1/trading/health"
PORTFOLIO_URL="http://localhost:8000/api/v1/trading/portfolio"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_monitor() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')] MONITOR${NC} $1"
}

log_alert() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ALERT${NC} $1"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS${NC} $1"
}

# Function to format currency
format_currency() {
    printf "%.2f" "$1"
}

# Function to format percentage
format_percentage() {
    printf "%.2f%%" "$1"
}

log_monitor "Starting 24/7 Trading System Monitor"
log_info "Monitoring interval: ${MONITOR_INTERVAL} seconds"

# Initialize tracking variables
previous_value=""
previous_trades=""
alert_sent=false

while true; do
    # Health check
    if ! health_response=$(curl -s -f "$HEALTH_CHECK_URL" 2>/dev/null); then
        log_alert "Health check failed - system may be down"
        sleep $MONITOR_INTERVAL
        continue
    fi
    
    # Parse health data
    overall_health=$(echo "$health_response" | grep -o '"overall_health":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$overall_health" != "healthy" ]; then
        log_alert "System health: $overall_health"
    fi
    
    # Portfolio status
    if portfolio_response=$(curl -s -f "$PORTFOLIO_URL" 2>/dev/null); then
        # Extract portfolio data
        current_value=$(echo "$portfolio_response" | grep -o '"current_value":[0-9.]*' | cut -d':' -f2)
        available_cash=$(echo "$portfolio_response" | grep -o '"available_cash":[0-9.]*' | cut -d':' -f2)
        total_trades=$(echo "$portfolio_response" | grep -o '"total_trades":[0-9]*' | cut -d':' -f2)
        total_return_pct=$(echo "$portfolio_response" | grep -o '"total_return_pct":[0-9.-]*' | cut -d':' -f2)
        
        # Count positions
        positions_count=$(echo "$portfolio_response" | grep -o '"positions":{[^}]*}' | grep -o ':[^,}]*' | wc -l)
        
        # Display current status
        log_monitor "Portfolio: \$$(format_currency $current_value) | Cash: \$$(format_currency $available_cash) | Return: $(format_percentage $total_return_pct) | Trades: $total_trades | Positions: $positions_count"
        
        # Check for significant changes
        if [ -n "$previous_value" ]; then
            value_change=$(echo "$current_value - $previous_value" | bc -l 2>/dev/null || echo "0")
            trade_change=$(echo "$total_trades - $previous_trades" | bc -l 2>/dev/null || echo "0")
            
            # Alert on significant value change (>$10)
            if [ "$(echo "$value_change > 10 || $value_change < -10" | bc -l 2>/dev/null)" = "1" ]; then
                if [ "$(echo "$value_change > 0" | bc -l 2>/dev/null)" = "1" ]; then
                    log_success "Portfolio gained \$$(format_currency $value_change)"
                else
                    log_alert "Portfolio lost \$$(format_currency ${value_change#-})"
                fi
            fi
            
            # Alert on new trades
            if [ "$(echo "$trade_change > 0" | bc -l 2>/dev/null)" = "1" ]; then
                log_info "New trades executed: $trade_change"
            fi
        fi
        
        # Risk alerts
        if [ "$(echo "$total_return_pct < -10" | bc -l 2>/dev/null)" = "1" ]; then
            log_alert "High loss detected: $(format_percentage $total_return_pct)"
        fi
        
        if [ "$(echo "$available_cash < 50" | bc -l 2>/dev/null)" = "1" ]; then
            log_alert "Low cash available: \$$(format_currency $available_cash)"
        fi
        
        # Update tracking variables
        previous_value="$current_value"
        previous_trades="$total_trades"
        
    else
        log_alert "Failed to get portfolio status"
    fi
    
    # Check system resources
    if command -v docker &> /dev/null; then
        # Check Docker container health
        app_status=$(docker-compose ps -q app | xargs docker inspect -f '{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
        redis_status=$(docker-compose ps -q redis | xargs docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "unknown")
        
        if [ "$app_status" != "healthy" ] && [ "$app_status" != "unknown" ]; then
            log_alert "App container health: $app_status"
        fi
        
        if [ "$redis_status" != "running" ]; then
            log_alert "Redis container status: $redis_status"
        fi
    fi
    
    sleep $MONITOR_INTERVAL
done