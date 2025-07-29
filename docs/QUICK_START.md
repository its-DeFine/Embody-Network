# AutoGen Platform - Quick Start Tutorial

## 🚀 5-Minute Setup

### Step 1: Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd operation

# Create environment file
cat > .env << EOF
JWT_SECRET=dev-secret-change-in-production
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=password
REDIS_HOST=redis
ADMIN_API_KEY=admin-secret
EOF
```

### Step 2: Start the Platform

```bash
# Start all services
docker-compose up -d

# Wait for services to be ready (about 30 seconds)
sleep 30

# Verify services are running
docker-compose ps
```

### Step 3: Create Your First Agent

```bash
# 1. Register as a customer
CUSTOMER_RESPONSE=$(curl -s -X POST http://localhost:8000/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Company",
    "email": "test@example.com"
  }')

# Extract API key
API_KEY=$(echo $CUSTOMER_RESPONSE | jq -r '.api_key')
echo "Your API Key: $API_KEY"

# 2. Get authentication token
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"test@example.com\",
    \"api_key\": \"$API_KEY\"
  }")

# Extract token
TOKEN=$(echo $AUTH_RESPONSE | jq -r '.access_token')
echo "Your Token: $TOKEN"

# 3. Create a trading agent
AGENT_RESPONSE=$(curl -s -X POST http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Trading Bot",
    "agent_type": "trading",
    "config": {
      "exchange": "binance",
      "trading_pairs": ["BTC/USDT"],
      "risk_limit": 0.02
    }
  }')

AGENT_ID=$(echo $AGENT_RESPONSE | jq -r '.agent_id')
echo "Agent Created: $AGENT_ID"
```

### Step 4: Run Your First Task

```bash
# Create a market analysis task
TASK_RESPONSE=$(curl -s -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"agent_id\": \"$AGENT_ID\",
    \"type\": \"analyze_market\",
    \"parameters\": {
      \"symbol\": \"BTC/USDT\",
      \"timeframe\": \"1h\"
    }
  }")

TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
echo "Task Created: $TASK_ID"

# Check task status
curl -s -X GET http://localhost:8000/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN" | jq
```

## 📖 Complete Setup Script

Save this as `quickstart.sh`:

```bash
#!/bin/bash

echo "🚀 AutoGen Platform Quick Start"
echo "=============================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start services
echo "1️⃣ Starting services..."
docker-compose up -d

# Wait for services
echo "2️⃣ Waiting for services to be ready..."
sleep 30

# Create customer
echo "3️⃣ Creating test customer..."
CUSTOMER=$(curl -s -X POST http://localhost:8000/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "QuickStart Company",
    "email": "quickstart@example.com"
  }')

API_KEY=$(echo $CUSTOMER | jq -r '.api_key')

if [ "$API_KEY" = "null" ]; then
    echo "❌ Failed to create customer. Services may not be ready."
    echo "Response: $CUSTOMER"
    exit 1
fi

# Login
echo "4️⃣ Logging in..."
AUTH=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"quickstart@example.com\",
    \"api_key\": \"$API_KEY\"
  }")

TOKEN=$(echo $AUTH | jq -r '.access_token')

# Create agents
echo "5️⃣ Creating agents..."

# Trading agent
TRADER=$(curl -s -X POST http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "QuickStart Trader",
    "agent_type": "trading",
    "config": {
      "exchange": "binance",
      "trading_pairs": ["BTC/USDT", "ETH/USDT"]
    }
  }')

# Analysis agent
ANALYZER=$(curl -s -X POST http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "QuickStart Analyzer",
    "agent_type": "analysis",
    "config": {
      "analysis_types": ["technical", "sentiment"]
    }
  }')

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📋 Your Credentials:"
echo "===================="
echo "Email: quickstart@example.com"
echo "API Key: $API_KEY"
echo "Token: $TOKEN"
echo ""
echo "🤖 Your Agents:"
echo "==============="
echo "Trading Agent: $(echo $TRADER | jq -r '.agent_id')"
echo "Analysis Agent: $(echo $ANALYZER | jq -r '.agent_id')"
echo ""
echo "📚 Next Steps:"
echo "=============="
echo "1. View API docs: http://localhost:8000/docs"
echo "2. Monitor metrics: http://localhost:3000 (admin/admin)"
echo "3. RabbitMQ dashboard: http://localhost:15672 (admin/password)"
echo ""
echo "🎯 Try these commands:"
echo "======================"
echo "# List your agents"
echo "curl -H \"Authorization: Bearer $TOKEN\" http://localhost:8000/agents | jq"
echo ""
echo "# Create a task"
echo "curl -X POST -H \"Authorization: Bearer $TOKEN\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"agent_id\": \"$(echo $TRADER | jq -r '.agent_id')\", \"type\": \"analyze_market\", \"parameters\": {\"symbol\": \"BTC/USDT\"}}' \\"
echo "  http://localhost:8000/tasks"
```

Make it executable:
```bash
chmod +x quickstart.sh
./quickstart.sh
```

## 🎯 Common Operations

### Check Platform Health
```bash
# API Gateway health
curl http://localhost:8000/health

# Check all services
docker-compose ps

# View logs
docker-compose logs -f api-gateway
```

### Stop/Restart Platform
```bash
# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Update and restart
docker-compose pull
docker-compose up -d
```

### Clean Up
```bash
# Stop and remove everything
docker-compose down -v

# Remove all data
docker system prune -a
```

## 🆘 Troubleshooting

### Services Won't Start
```bash
# Check port conflicts
lsof -i :8000
lsof -i :5672
lsof -i :6379

# Check Docker resources
docker system df
```

### API Returns 500 Error
```bash
# Check service logs
docker-compose logs api-gateway
docker-compose logs rabbitmq
docker-compose logs redis
```

### Can't Create Agents
```bash
# Verify agent-manager is running
docker-compose ps agent-manager

# Check Docker socket permissions
ls -la /var/run/docker.sock
```

## 📚 Learn More

- [Full Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [User Guide](./USER_GUIDE.md)
- [API Reference](http://localhost:8000/docs)
- [Architecture Overview](./ARCHITECTURE.md)