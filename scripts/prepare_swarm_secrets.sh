#!/bin/bash
# Prepare secrets for Docker Swarm deployment

echo "🔐 Creating Docker Swarm secrets..."

# Create JWT secret
echo "your-secret-jwt-key-change-in-production" | docker secret create jwt_secret - 2>/dev/null || \
  echo "Secret jwt_secret already exists"

# Create RabbitMQ password
echo "password" | docker secret create rabbitmq_password - 2>/dev/null || \
  echo "Secret rabbitmq_password already exists"

# Create admin API key
echo "admin-secret-key-change-in-production" | docker secret create admin_api_key - 2>/dev/null || \
  echo "Secret admin_api_key already exists"

# Create Redis password
echo "redis-password-change-in-production" | docker secret create redis_password - 2>/dev/null || \
  echo "Secret redis_password already exists"

# List all secrets
echo ""
echo "📋 Available secrets:"
docker secret ls

echo ""
echo "✅ Secrets prepared for swarm deployment"