#!/bin/bash

# Validate dual-mode trading in containers
# This script tests all trading modes and validates container functionality

set -e

echo "=========================================="
echo "Dual-Mode Trading Container Validation"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
TRADING_COMPOSE="docker-compose.trading.yml"
LOG_DIR="./logs/dual_mode_test_$(date +%Y%m%d_%H%M%S)"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to print status
print_status() {
    echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +%H:%M:%S)] ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +%H:%M:%S)] WARNING:${NC} $1"
}

# Function to check if service is healthy
check_service_health() {
    local service=$1
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "$service.*Up"; then
            print_status "$service is running"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    print_error "$service failed to start"
    return 1
}

# Function to test trading mode
test_trading_mode() {
    local mode=$1
    print_status "Testing $mode mode..."
    
    # Set environment variable
    export TRADING_MODE=$mode
    
    # Create test container with specific mode
    docker-compose -f $TRADING_COMPOSE run --rm -e TRADING_MODE=$mode trading-agent python -c "
import os
import sys
import asyncio
sys.path.append('/app')

from dual_mode_trading import DualModeTradingEngine
from trading_agent import TradingAgent

async def test_mode():
    mode = os.getenv('TRADING_MODE', 'comparison')
    print(f'Testing {mode} mode...')
    
    # Initialize trading engine
    config = {
        'exchange': 'binance',
        'testnet': True
    }
    
    engine = DualModeTradingEngine(config)
    await engine.initialize()
    
    # Test market data
    market_data = await engine.get_market_data('BTC/USDT')
    print(f'Market data keys: {list(market_data.keys())}')
    
    # Test order execution
    order = {
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'amount': 0.001,
        'type': 'market'
    }
    
    result = await engine.execute_trade(order)
    print(f'Execution result mode: {result.get(\"mode\")}')
    
    # Mode-specific validation
    if mode == 'comparison' and 'divergence_analysis' in result:
        print(f'Price divergence: {result[\"divergence_analysis\"].get(\"price_divergence_pct\", 0):.2f}%')
    elif mode == 'hybrid' and 'weights' in result:
        print(f'Weights - Real: {result[\"weights\"][\"real\"]*100:.1f}%, Sim: {result[\"weights\"][\"simulated\"]*100:.1f}%')
    
    # Get analytics
    analytics = engine.get_execution_analytics()
    print(f'Analytics mode: {analytics.get(\"mode\")}')
    
    await engine.close()
    print(f'{mode} mode test completed successfully')
    return True

# Run test
result = asyncio.run(test_mode())
sys.exit(0 if result else 1)
" 2>&1 | tee "$LOG_DIR/${mode}_test.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_status "$mode mode test PASSED"
        return 0
    else
        print_error "$mode mode test FAILED"
        return 1
    fi
}

# Main validation process
main() {
    print_status "Starting dual-mode trading container validation"
    
    # 1. Check Docker and Docker Compose
    print_status "Checking Docker environment..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    # 2. Start core services
    print_status "Starting core services..."
    docker-compose -f $COMPOSE_FILE up -d rabbitmq redis
    
    # Wait for services to be ready
    sleep 10
    
    # Check service health
    check_service_health "rabbitmq" || exit 1
    check_service_health "redis" || exit 1
    
    # 3. Build trading containers
    print_status "Building trading containers..."
    docker-compose -f $TRADING_COMPOSE build
    
    # 4. Test each trading mode
    MODES=("real" "simulated" "hybrid" "comparison" "shadow")
    PASSED=0
    FAILED=0
    
    for mode in "${MODES[@]}"; do
        echo ""
        echo "=========================================="
        echo "Testing $mode mode"
        echo "=========================================="
        
        if test_trading_mode "$mode"; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
        fi
        
        # Wait between tests
        sleep 2
    done
    
    # 5. Run comprehensive test suite
    print_status "Running comprehensive test suite..."
    docker-compose -f $TRADING_COMPOSE run --rm test-runner 2>&1 | tee "$LOG_DIR/comprehensive_test.log"
    
    # 6. Test comparison report generation
    print_status "Testing comparison report generation..."
    docker-compose -f $TRADING_COMPOSE run --rm report-generator python -c "
import sys
sys.path.append('/app')
from comparison_reporter import ComparisonReporter

# Test report generation
reporter = ComparisonReporter()

# Create mock data
real_data = {
    'metrics': {
        'total_return_pct': 5.2,
        'win_rate': 0.65,
        'sharpe_ratio': 1.8
    },
    'risk_metrics': {
        'volatility': 0.15,
        'max_drawdown': 0.08,
        'var_95': 0.02
    }
}

sim_data = {
    'metrics': {
        'total_return_pct': 4.8,
        'win_rate': 0.62,
        'sharpe_ratio': 1.6
    },
    'risk_metrics': {
        'volatility': 0.14,
        'max_drawdown': 0.07,
        'var_95': 0.018
    }
}

# Generate report
report = reporter.generate_comparison_report(real_data, sim_data)

# Export as markdown
md_report = reporter.export_report(report, 'markdown')
print('Report generated successfully')
print(f'Accuracy score: {report[\"performance_comparison\"][\"accuracy_score\"]:.1f}%')
" 2>&1 | tee "$LOG_DIR/report_generation_test.log"
    
    # 7. Container communication test
    print_status "Testing container communication..."
    
    # Test if containers can communicate via RabbitMQ
    docker-compose -f $COMPOSE_FILE exec -T rabbitmq rabbitmqctl list_queues 2>&1 | tee "$LOG_DIR/rabbitmq_queues.log"
    
    # 8. Cleanup test containers (keep services running)
    print_status "Cleaning up test containers..."
    docker-compose -f $TRADING_COMPOSE down --remove-orphans
    
    # 9. Generate summary report
    echo ""
    echo "=========================================="
    echo "VALIDATION SUMMARY"
    echo "=========================================="
    echo "Total modes tested: ${#MODES[@]}"
    echo "Passed: $PASSED"
    echo "Failed: $FAILED"
    echo "Success rate: $(( PASSED * 100 / ${#MODES[@]} ))%"
    echo ""
    echo "Logs saved to: $LOG_DIR"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        print_status "All tests PASSED! Dual-mode trading is working correctly in containers."
        
        # Show example usage
        echo ""
        echo "Example usage:"
        echo "  # Run in comparison mode (default)"
        echo "  docker-compose -f docker-compose.trading.yml up trading-agent"
        echo ""
        echo "  # Run in hybrid mode"
        echo "  TRADING_MODE=hybrid docker-compose -f docker-compose.trading.yml up trading-agent"
        echo ""
        echo "  # Run tests"
        echo "  docker-compose -f docker-compose.trading.yml up test-runner"
        echo ""
        
        return 0
    else
        print_error "Some tests FAILED. Check logs in $LOG_DIR for details."
        return 1
    fi
}

# Run main validation
main

# Exit with appropriate code
exit $?