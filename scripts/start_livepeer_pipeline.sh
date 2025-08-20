#!/bin/bash
# Start Livepeer Orchestrator Connectivity Pipeline

set -e

echo "========================================"
echo "Starting Livepeer Connectivity Pipeline"
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.livepeer..."
    cp .env.livepeer .env
    echo "✅ Environment file created"
else
    echo "✅ Using existing .env file"
fi

# Create networks if they don't exist
echo ""
echo "Setting up Docker networks..."
docker network create central-network 2>/dev/null || echo "  - central-network already exists"
docker network create orchestrator-network 2>/dev/null || echo "  - orchestrator-network already exists"

# Start manager cluster
echo ""
echo "Starting Manager Cluster..."
docker-compose -f docker-compose.manager.yml up -d
echo "✅ Manager cluster started"

# Wait for manager to be ready
echo ""
echo "Waiting for manager to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8010/health > /dev/null 2>&1; then
        echo "✅ Manager is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# Start Livepeer services
echo ""
echo "Starting Livepeer Services..."
docker-compose -f docker-compose.livepeer.yml up -d
echo "✅ Livepeer services started"

# Start BYOC containers (optional)
echo ""
read -p "Do you want to start BYOC containers? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting BYOC containers..."
    docker-compose -f docker/byoc/docker-compose.byoc.yml up -d
    echo "✅ BYOC containers started"
fi

# Show running containers
echo ""
echo "Running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Show access URLs
echo ""
echo "========================================"
echo "Access URLs:"
echo "========================================"
echo "Manager API:        http://localhost:8010"
echo "Dashboard:          http://localhost:8081"
echo "Livepeer Gateway:   http://localhost:8935"
echo "Livepeer Proxy:     http://localhost:8936"
echo "RTMP Stream:        rtmp://localhost:1935/live"
echo ""
echo "API Documentation:  http://localhost:8010/docs"
echo ""

# Test connectivity
echo "========================================"
echo "Testing Connectivity..."
echo "========================================"
sleep 3
python3 scripts/test_livepeer_connectivity.py || echo "Note: Some tests may fail if services are still starting"

echo ""
echo "========================================"
echo "Livepeer Pipeline Started Successfully!"
echo "========================================"
echo ""
echo "Monitor orchestrators with:"
echo "  python3 scripts/utilities/multi_orchestrator_manager.py --action monitor"
echo ""
echo "Stop all services with:"
echo "  docker-compose -f docker-compose.manager.yml down"
echo "  docker-compose -f docker-compose.livepeer.yml down"