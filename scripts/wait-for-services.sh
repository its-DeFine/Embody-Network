#!/bin/bash
# Wait for all services to be ready with intelligent health checks

set -e

# Configuration
MAX_WAIT_TIME=300  # 5 minutes
CHECK_INTERVAL=2   # 2 seconds

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Services to check
declare -A SERVICES=(
    ["RabbitMQ"]="rabbitmq"
    ["Redis"]="redis://localhost:6379"
    ["API Gateway"]="http://localhost:8000/health"
    ["Control Board"]="http://localhost:3001"
)

# Function to print with color
print_status() {
    echo -e "${2}${1}${NC}"
}

# Function to check if a URL is accessible
check_http_service() {
    local url=$1
    curl -s -f -o /dev/null "$url" 2>/dev/null
}

# Function to check Redis
check_redis() {
    docker exec redis redis-cli ping 2>/dev/null | grep -q PONG
}

# Function to check RabbitMQ
check_rabbitmq() {
    docker exec rabbitmq rabbitmqctl status > /dev/null 2>&1
}

# Function to wait for a service
wait_for_service() {
    local name=$1
    local url=$2
    local start_time=$(date +%s)
    
    print_status "⏳ Waiting for $name..." "$YELLOW"
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        # Check if max wait time exceeded
        if [ $elapsed -gt $MAX_WAIT_TIME ]; then
            print_status "❌ $name failed to start within ${MAX_WAIT_TIME}s" "$RED"
            return 1
        fi
        
        # Check service based on type
        if [[ "$url" == redis://* ]]; then
            if check_redis; then
                print_status "✅ $name is ready (${elapsed}s)" "$GREEN"
                return 0
            fi
        elif [[ "$url" == "rabbitmq" ]]; then
            if check_rabbitmq; then
                print_status "✅ $name is ready (${elapsed}s)" "$GREEN"
                return 0
            fi
        elif check_http_service "$url"; then
            print_status "✅ $name is ready (${elapsed}s)" "$GREEN"
            return 0
        fi
        
        # Show progress
        printf "\r⏳ Waiting for $name... ${elapsed}s"
        sleep $CHECK_INTERVAL
    done
}

# Function to check service readiness (not just availability)
check_service_readiness() {
    local name=$1
    
    case "$name" in
        "API Gateway")
            # Check if API can handle requests
            response=$(curl -s http://localhost:8000/health 2>/dev/null || echo "{}")
            if [[ "$response" == *"healthy"* ]]; then
                # Check if required dependencies are also healthy
                detailed=$(curl -s http://localhost:8000/health/detailed 2>/dev/null || echo "{}")
                if [[ "$detailed" == *"rabbitmq"* ]] && [[ "$detailed" == *"redis"* ]]; then
                    return 0
                fi
            fi
            return 1
            ;;
        "RabbitMQ")
            # Check if RabbitMQ is fully operational
            if docker exec rabbitmq rabbitmqctl status > /dev/null 2>&1; then
                return 0
            fi
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

# Main execution
main() {
    print_status "🚀 Waiting for AutoGen services to be ready..." "$BLUE"
    print_status "Maximum wait time: ${MAX_WAIT_TIME}s" "$BLUE"
    echo ""
    
    # First, ensure Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_status "❌ Docker is not running!" "$RED"
        exit 1
    fi
    
    # Check if compose project exists
    if ! docker-compose ps > /dev/null 2>&1; then
        print_status "❌ No Docker Compose services found. Run 'docker-compose up -d' first." "$RED"
        exit 1
    fi
    
    # Wait for each service
    all_ready=true
    for service in "${!SERVICES[@]}"; do
        if ! wait_for_service "$service" "${SERVICES[$service]}"; then
            all_ready=false
        fi
    done
    
    # If all services started, do readiness checks
    if [ "$all_ready" = true ]; then
        echo ""
        print_status "🔍 Performing readiness checks..." "$BLUE"
        
        for service in "${!SERVICES[@]}"; do
            printf "%-20s" "$service:"
            if check_service_readiness "$service"; then
                print_status "Ready" "$GREEN"
            else
                print_status "Starting..." "$YELLOW"
            fi
        done
        
        # Final wait for stabilization
        echo ""
        print_status "⏳ Waiting for services to stabilize..." "$YELLOW"
        sleep 5
        
        # Final health check
        echo ""
        if bash "$(dirname "$0")/check_health.sh" > /dev/null 2>&1; then
            print_status "✅ All services are ready!" "$GREEN"
            exit 0
        else
            print_status "⚠️  Some services may not be fully ready" "$YELLOW"
            exit 1
        fi
    else
        print_status "❌ Some services failed to start" "$RED"
        echo ""
        print_status "Debug information:" "$YELLOW"
        docker-compose ps
        exit 1
    fi
}

# Handle interrupts gracefully
trap 'echo -e "\n${RED}Interrupted!${NC}"; exit 1' INT TERM

# Run main function
main "$@"