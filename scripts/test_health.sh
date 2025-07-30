#!/bin/bash
# Simple health test script

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Testing service health checks...${NC}"

# Test RabbitMQ
echo -n "RabbitMQ: "
if docker exec rabbitmq rabbitmqctl status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# Test Redis
echo -n "Redis: "
if docker exec redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# Test if containers are running
echo -e "\n${BLUE}Container status:${NC}"
docker ps | grep -E "(rabbitmq|redis|api-gateway|control-board)" || echo "No containers running"

echo -e "\n${BLUE}Done!${NC}"