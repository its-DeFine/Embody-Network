#!/bin/bash
# Test if Docker images can be built

set -e

echo "🔨 Testing Docker Image Builds"
echo "=============================="

cd "$(dirname "$0")/.."

# Test building each service
services=("core-engine" "api-gateway" "agent-manager" "update-pipeline")

for service in "${services[@]}"; do
    echo ""
    echo "Building $service..."
    if docker-compose build --no-cache $service > /dev/null 2>&1; then
        echo "✓ $service built successfully"
    else
        echo "❌ $service build failed"
        echo "  Run 'docker-compose build $service' to see detailed error"
    fi
done

# Test building autogen agent
echo ""
echo "Building autogen-agent..."
if docker build -t autogen-agent:latest -f customer_agents/base/Dockerfile . > /dev/null 2>&1; then
    echo "✓ autogen-agent built successfully"
else
    echo "❌ autogen-agent build failed"
    echo "  Run 'docker build -t autogen-agent:latest -f customer_agents/base/Dockerfile .' to see detailed error"
fi

echo ""
echo "Build test complete!"