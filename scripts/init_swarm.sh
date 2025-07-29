#!/bin/bash

# Initialize Docker Swarm Mode
# Usage: ./init_swarm.sh [manager-ip]

set -e

echo "🐝 Initializing Docker Swarm Mode"
echo "=================================="

# Get manager IP address
if [ -z "$1" ]; then
    # Try to get default IP
    MANAGER_IP=$(hostname -I | awk '{print $1}')
    echo "No IP provided, using detected IP: $MANAGER_IP"
else
    MANAGER_IP=$1
fi

# Check if already in swarm mode
if docker info | grep -q "Swarm: active"; then
    echo "✅ Already in swarm mode"
    docker info | grep "Swarm:"
    docker info | grep "NodeID:"
    docker info | grep "Is Manager:"
else
    # Initialize swarm
    echo "Initializing swarm with manager IP: $MANAGER_IP"
    docker swarm init --advertise-addr $MANAGER_IP
fi

echo ""
echo "📋 Swarm Status:"
docker node ls

echo ""
echo "🏷️  Creating node labels for service placement:"

# Label current node for specific services
NODE_ID=$(docker info -f '{{.Swarm.NodeID}}')
echo "Current node ID: $NODE_ID"

# Add labels for service placement
docker node update --label-add rabbitmq=true $NODE_ID
docker node update --label-add redis=true $NODE_ID
docker node update --label-add monitoring=true $NODE_ID

echo ""
echo "🔐 Creating Docker secrets:"

# Create secrets for sensitive data
# JWT Secret
if ! docker secret ls | grep -q jwt_secret; then
    openssl rand -base64 32 | docker secret create jwt_secret -
    echo "✅ Created jwt_secret"
else
    echo "⚠️  jwt_secret already exists"
fi

# Admin API Key
if ! docker secret ls | grep -q admin_api_key; then
    openssl rand -base64 32 | docker secret create admin_api_key -
    echo "✅ Created admin_api_key"
else
    echo "⚠️  admin_api_key already exists"
fi

# RabbitMQ Password
if ! docker secret ls | grep -q rabbitmq_password; then
    echo "rabbitmq_secure_password_123" | docker secret create rabbitmq_password -
    echo "✅ Created rabbitmq_password"
else
    echo "⚠️  rabbitmq_password already exists"
fi

# RabbitMQ Erlang Cookie
if ! docker secret ls | grep -q rabbitmq_erlang_cookie; then
    openssl rand -base64 32 | docker secret create rabbitmq_erlang_cookie -
    echo "✅ Created rabbitmq_erlang_cookie"
else
    echo "⚠️  rabbitmq_erlang_cookie already exists"
fi

# Grafana Password
if ! docker secret ls | grep -q grafana_password; then
    echo "admin" | docker secret create grafana_password -
    echo "✅ Created grafana_password"
else
    echo "⚠️  grafana_password already exists"
fi

echo ""
echo "🌐 Creating overlay network:"
if ! docker network ls | grep -q autogen-overlay; then
    docker network create --driver overlay --attachable autogen-overlay
    echo "✅ Created autogen-overlay network"
else
    echo "⚠️  autogen-overlay network already exists"
fi

echo ""
echo "📝 Worker join command:"
echo "To add workers to this swarm, run the following command on worker nodes:"
docker swarm join-token worker

echo ""
echo "📝 Manager join command:"
echo "To add additional managers to this swarm, run:"
docker swarm join-token manager

echo ""
echo "✅ Swarm initialization complete!"
echo ""
echo "Next steps:"
echo "1. Join worker nodes using the command above"
echo "2. Deploy the stack: docker stack deploy -c docker-compose.swarm.yml autogen-platform"
echo "3. Monitor services: docker service ls"
echo "4. View logs: docker service logs [service-name]"