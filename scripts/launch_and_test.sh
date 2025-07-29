#!/bin/bash
# Launch and test the AutoGen platform

set -e

echo "🚀 AutoGen Platform Launch & Test Script"
echo "========================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed."
    exit 1
fi

cd "$(dirname "$0")/.."

# Load environment variables
if [ -f .env ]; then
    echo "✓ Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

# Function to wait for service
wait_for_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "  Waiting for $service"
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo " ✓"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo " ❌ (timeout)"
    return 1
}

# Build images
echo ""
echo "📦 Building Docker images..."
docker-compose build --quiet || {
    echo "❌ Failed to build images"
    exit 1
}
echo "✓ Images built successfully"

# Start services
echo ""
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."

# Check core services
wait_for_service "Redis" "redis://localhost:6379" || true
wait_for_service "RabbitMQ" "http://localhost:15672" || true
wait_for_service "API Gateway" "http://localhost:8000/health" || true
wait_for_service "Prometheus" "http://localhost:9090/-/ready" || true
wait_for_service "Grafana" "http://localhost:3000/api/health" || true

# Show running containers
echo ""
echo "📊 Running containers:"
docker-compose ps

# Test API Gateway health
echo ""
echo "🔍 Testing API Gateway..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "✓ API Gateway is healthy"
else
    echo "❌ API Gateway health check failed"
fi

# Show logs for debugging
echo ""
echo "📋 Recent logs (last 20 lines per service):"
echo "----------------------------------------"
for service in api-gateway agent-manager core-engine; do
    echo "[$service]"
    docker-compose logs --tail=20 $service 2>/dev/null || echo "  No logs available"
    echo ""
done

# Show access URLs
echo ""
echo "🌐 Access URLs:"
echo "  • API Gateway: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • RabbitMQ Management: http://localhost:15672 (admin/\$RABBITMQ_PASSWORD)"
echo "  • Grafana: http://localhost:3000 (admin/\$GRAFANA_PASSWORD)"
echo "  • Prometheus: http://localhost:9090"

echo ""
echo "✅ Platform launched successfully!"
echo ""
echo "📝 Next steps:"
echo "  1. Create a customer: python3 scripts/onboard_customer.py --name 'Test Co' --email test@example.com"
echo "  2. View logs: docker-compose logs -f [service-name]"
echo "  3. Stop services: docker-compose down"
echo "  4. Stop and remove volumes: docker-compose down -v"