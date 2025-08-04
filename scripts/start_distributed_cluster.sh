#!/bin/bash
set -e

# Distributed Cluster Startup Script
# Launches the central manager and multiple agent containers

echo "🚀 Starting Distributed AutoGen Cluster"
echo "====================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Stop any existing containers
echo -e "${YELLOW}📦 Stopping existing containers...${NC}"
docker-compose -f docker-compose.distributed.yml down || true

# Build images
echo -e "${YELLOW}🔨 Building Docker images...${NC}"
docker-compose -f docker-compose.distributed.yml build

# Start services
echo -e "${GREEN}🚀 Starting distributed cluster...${NC}"
docker-compose -f docker-compose.distributed.yml up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to initialize...${NC}"
sleep 10

# Check service health
echo -e "${GREEN}🔍 Checking service health...${NC}"

# Check Redis
if docker-compose -f docker-compose.distributed.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is healthy${NC}"
else
    echo -e "${RED}❌ Redis is not responding${NC}"
fi

# Check Central Manager
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Central Manager is healthy${NC}"
    echo "   API Docs: http://localhost:8000/docs"
else
    echo -e "${RED}❌ Central Manager is not responding${NC}"
fi

# Check Agent Containers
for port in 8001 8002 8003; do
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Agent Container on port $port is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Agent Container on port $port is still starting...${NC}"
    fi
done

echo ""
echo -e "${GREEN}📊 Cluster Status:${NC}"
docker-compose -f docker-compose.distributed.yml ps

echo ""
echo -e "${GREEN}🎯 Next Steps:${NC}"
echo "1. View logs: docker-compose -f docker-compose.distributed.yml logs -f"
echo "2. Test distributed system: python scripts/demo/test_distributed_system.py"
echo "3. Access API docs: http://localhost:8000/docs"
echo "4. Monitor containers: docker stats"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "- Agent containers will auto-register with the central manager"
echo "- Use the cluster API to deploy agents across containers"
echo "- Containers will automatically discover each other"
echo "- The system supports automatic failover and migration"

# Optional: Run a quick test
read -p "Run distributed system test? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}🧪 Running distributed system test...${NC}"
    sleep 5  # Give containers more time to fully initialize
    python scripts/demo/test_distributed_system.py
fi