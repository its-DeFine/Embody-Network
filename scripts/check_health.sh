#!/bin/bash
# Health check script for AutoGen platform services

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🏥 AutoGen Platform Health Check"
echo "================================"

# Function to check service
check_service() {
    local name=$1
    local url=$2
    local expected_response=$3
    
    printf "%-20s" "$name:"
    
    if response=$(curl -s -f "$url" 2>/dev/null); then
        if [[ -z "$expected_response" ]] || [[ "$response" == *"$expected_response"* ]]; then
            echo -e "${GREEN}✅ Healthy${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Unexpected response${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Unreachable${NC}"
        return 1
    fi
}

# Check Docker
printf "%-20s" "Docker:"
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
    exit 1
fi

# Check core services
echo -e "\nCore Services:"
echo "--------------"
# RabbitMQ health check using rabbitmqctl
printf "%-20s" "RabbitMQ:"
if docker exec rabbitmq rabbitmqctl status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi
# Redis health check using redis-cli
printf "%-20s" "Redis:"
if docker exec redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# Check application services
echo -e "\nApplication Services:"
echo "--------------------"
check_service "API Gateway" "http://localhost:8000/health" "healthy"
check_service "Control Board" "http://localhost:3001" "<!DOCTYPE html>"

# Check API endpoints
echo -e "\nAPI Endpoints:"
echo "--------------"
check_service "API Docs" "http://localhost:8000/docs" "swagger-ui"
check_service "Metrics" "http://localhost:8000/metrics" "api_requests_total"

# Check container status
echo -e "\nContainer Status:"
echo "-----------------"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Check resource usage
echo -e "\nResource Usage:"
echo "---------------"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Overall status
echo -e "\n================================"
all_healthy=true
if ! check_service "API Gateway" "http://localhost:8000/health" "healthy" > /dev/null 2>&1; then
    all_healthy=false
fi

if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}✅ All systems operational${NC}"
    exit 0
else
    echo -e "${RED}❌ Some services are unhealthy${NC}"
    exit 1
fi