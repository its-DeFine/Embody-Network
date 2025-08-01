#!/bin/bash
# Production startup script for 24/7 trading system

set -e

echo "🚀 Starting 24/7 Trading System..."

# Configuration
INITIAL_CAPITAL=${INITIAL_CAPITAL:-1000.00}
WAIT_TIMEOUT=60
HEALTH_CHECK_URL="http://localhost:8000/health"
TRADING_START_URL="http://localhost:8000/api/v1/trading/start"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Pre-flight checks
log_info "Performing pre-flight checks..."

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

if [ ! -f ".env" ]; then
    log_warning ".env file not found. Creating from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_info "Please edit .env file with your API keys and settings"
        exit 1
    else
        log_error "No .env.example template found"
        exit 1
    fi
fi

# Check required environment variables
log_info "Checking environment configuration..."

required_vars=(
    "JWT_SECRET"
    "ADMIN_PASSWORD"
    "FINNHUB_API_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" .env || grep -q "^$var=your-" .env || grep -q "^$var=change-me" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    log_error "Missing or placeholder values for required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    log_info "Please update your .env file with actual values"
    exit 1
fi

log_success "Environment configuration OK"

# Build and start services
log_info "Building Docker images..."
docker-compose build --pull

log_info "Starting services..."
docker-compose up -d

# Wait for services to be ready
log_info "Waiting for services to start..."
sleep 10

# Health check with timeout
log_info "Performing health checks..."
timeout_counter=0
while [ $timeout_counter -lt $WAIT_TIMEOUT ]; do
    if curl -f -s $HEALTH_CHECK_URL > /dev/null 2>&1; then
        log_success "Application is healthy"
        break
    fi
    
    timeout_counter=$((timeout_counter + 5))
    if [ $timeout_counter -ge $WAIT_TIMEOUT ]; then
        log_error "Application failed to start within $WAIT_TIMEOUT seconds"
        log_info "Checking service status..."
        docker-compose ps
        log_info "Application logs:"
        docker-compose logs --tail=50 app
        exit 1
    fi
    
    log_info "Waiting for application to be ready... ($timeout_counter/${WAIT_TIMEOUT}s)"
    sleep 5
done

# Check service status
log_info "Service status:"
docker-compose ps

# Initialize trading system
log_info "Initializing trading system with \$${INITIAL_CAPITAL} starting capital..."

# Get authentication token (simplified for demo)
# In production, implement proper authentication
AUTH_HEADER=""

response=$(curl -s -X POST "$TRADING_START_URL" \
    -H "Content-Type: application/json" \
    -d "{\"initial_capital\": $INITIAL_CAPITAL}" \
    $AUTH_HEADER)

echo "Response: $response"

if echo "$response" | grep -q '"status":"success"'; then
    portfolio_id=$(echo "$response" | grep -o '"portfolio_id":"[^"]*"' | cut -d'"' -f4)
    log_success "Trading system started successfully!"
    log_info "Portfolio ID: $portfolio_id"
    log_info "Initial Capital: \$${INITIAL_CAPITAL}"
else
    log_error "Failed to start trading system"
    echo "Response: $response"
    exit 1
fi

# Display system information
log_info "System Information:"
echo "  📊 Portfolio Status: http://localhost:8000/api/v1/trading/portfolio"
echo "  📈 Performance: http://localhost:8000/api/v1/trading/performance"
echo "  💹 Trades: http://localhost:8000/api/v1/trading/trades"
echo "  🔍 Health Check: http://localhost:8000/api/v1/trading/health"
echo "  📋 API Docs: http://localhost:8000/docs"

# Display monitoring commands
echo ""
log_info "Monitoring Commands:"
echo "  📊 Portfolio Status:"
echo "    curl http://localhost:8000/api/v1/trading/portfolio"
echo ""
echo "  📈 Performance Metrics:"
echo "    curl http://localhost:8000/api/v1/trading/performance"
echo ""
echo "  📋 Recent Trades:"
echo "    curl http://localhost:8000/api/v1/trading/trades?limit=10"
echo ""
echo "  🔍 System Health:"
echo "    curl http://localhost:8000/api/v1/trading/health"
echo ""
echo "  📄 View Logs:"
echo "    docker-compose logs -f app"
echo ""
echo "  ⏹️  Stop Trading:"
echo "    curl -X POST http://localhost:8000/api/v1/trading/stop"

# Start real-time monitoring in background
log_info "Starting real-time monitoring..."
nohup ./scripts/monitor_trading.sh > monitoring.log 2>&1 &
echo $! > monitoring.pid

log_success "24/7 Trading System is now LIVE! 🚀"
log_warning "IMPORTANT: This system trades with real money. Monitor it carefully!"

echo ""
echo "To stop the system:"
echo "  🛑 Stop trading: curl -X POST http://localhost:8000/api/v1/trading/stop"
echo "  🔧 Stop services: docker-compose down"