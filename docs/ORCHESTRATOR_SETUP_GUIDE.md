# 🎭 Orchestrator Setup Guide for Embody Network

This guide helps you set up your own Livepeer orchestrator node to join the Embody Network and earn rewards based on your service uptime.

## 📋 Prerequisites

- Docker & Docker Compose installed
- Stable internet connection
- Open ports: 9995 (orchestrator), 9876 (worker)
- Minimum 4GB RAM, 20GB storage
- (Optional) GPU for enhanced processing

## 🚀 Quick Start

### Step 1: Download Configuration

```bash
# Create orchestrator directory
mkdir embody-orchestrator && cd embody-orchestrator

# Download the orchestrator-only docker-compose
curl -O https://raw.githubusercontent.com/its-DeFine/Embody-Network/embody-alpha/docker/orchestrator/docker-compose.orchestrator.yml

# Download environment template
curl -O https://raw.githubusercontent.com/its-DeFine/Embody-Network/embody-alpha/.env.orchestrator-template
```

### Step 2: Configure Environment

Create your `.env` file:

```bash
cp .env.orchestrator-template .env
```

Edit `.env` with your settings:

```bash
# REQUIRED: Embody Network Manager Connection
MANAGER_URL=https://embody.network/api  # Production manager URL
MANAGER_API_KEY=your-provided-api-key   # Contact us for API key

# REQUIRED: Your Orchestrator Identity
ORCHESTRATOR_ID=your-unique-id          # e.g., "john-orchestrator-001"
ORCHESTRATOR_NAME=Your Orchestrator Name
ORCHESTRATOR_SECRET=your-secret-key     # Generate a strong secret

# REQUIRED: Ethereum Configuration
ETH_RPC_URL=https://arb1.arbitrum.io/rpc
ETH_ADDRESS=0xYourEthereumAddress       # For receiving payments

# BYOC Configuration
CAPABILITY_NAME=agent-net
CAPABILITY_PRICE_PER_UNIT=0             # Currently in testing phase
MIN_SERVICE_UPTIME=80.0                 # Minimum uptime percentage

# Network Settings
ORCHESTRATOR_PORT=9995
WORKER_PORT=9876
PUBLIC_IP=auto                          # Or specify your public IP

# Optional: GPU Support
NVIDIA_VISIBLE_DEVICES=all              # If you have NVIDIA GPU
```

### Step 3: Launch Orchestrator

```bash
# Start orchestrator services
docker-compose -f docker-compose.orchestrator.yml up -d

# Check logs
docker-compose logs -f
```

### Step 4: Register with Embody Network

#### Option A: Automatic Registration (Recommended)

```bash
# Download registration script
curl -O https://raw.githubusercontent.com/its-DeFine/Embody-Network/embody-alpha/scripts/register_orchestrator.sh

# Make executable
chmod +x register_orchestrator.sh

# Run registration
./register_orchestrator.sh
```

#### Option B: Manual Registration

```bash
# Get your orchestrator info
docker exec embody-orchestrator curl http://localhost:9995/info

# Register via API
curl -X POST https://embody.network/api/v1/orchestrators/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-provided-api-key" \
  -d '{
    "orchestrator_id": "your-unique-id",
    "name": "Your Orchestrator Name",
    "address": "http://YOUR_PUBLIC_IP:9995",
    "eth_address": "0xYourEthereumAddress",
    "capabilities": ["agent-net", "byoc"],
    "metadata": {
      "region": "us-east",
      "gpu": false
    }
  }'
```

### Step 5: Verify Registration

```bash
# Check registration status
curl https://embody.network/api/v1/orchestrators/your-unique-id/status \
  -H "X-API-Key: your-provided-api-key"

# Expected response:
{
  "orchestrator_id": "your-unique-id",
  "status": "registered",
  "uptime": 100.0,
  "last_seen": "2025-08-20T18:00:00Z",
  "payment_eligible": true
}
```

## 📦 Docker Compose File

Create `docker-compose.orchestrator.yml`:

```yaml
version: '3.8'

services:
  livepeer-orchestrator:
    image: livepeer/go-livepeer:latest
    container_name: embody-orchestrator
    restart: unless-stopped
    ports:
      - "${ORCHESTRATOR_PORT:-9995}:9995"
    environment:
      - ETH_RPC_URL=${ETH_RPC_URL}
      - ORCHESTRATOR_SECRET=${ORCHESTRATOR_SECRET}
      - PRICE_PER_UNIT=${CAPABILITY_PRICE_PER_UNIT}
      - MAX_PRICE_PER_UNIT=70000000000000
    command: [
      "-orchestrator",
      "-orchSecret=${ORCHESTRATOR_SECRET}",
      "-pricePerUnit=${CAPABILITY_PRICE_PER_UNIT}",
      "-ethUrl=${ETH_RPC_URL}",
      "-serviceAddr=0.0.0.0:9995",
      "-v=4"
    ]
    volumes:
      - orchestrator_data:/root/.lpData
    networks:
      - embody-network

  livepeer-worker:
    image: its-define/embody-worker:latest
    container_name: embody-worker
    restart: unless-stopped
    ports:
      - "${WORKER_PORT:-9876}:9876"
    environment:
      - ORCHESTRATOR_URL=http://livepeer-orchestrator:9995
      - CAPABILITY_NAME=${CAPABILITY_NAME}
      - MANAGER_URL=${MANAGER_URL}
      - MANAGER_API_KEY=${MANAGER_API_KEY}
      - MIN_SERVICE_UPTIME=${MIN_SERVICE_UPTIME}
    depends_on:
      - livepeer-orchestrator
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - embody-network

  orchestrator-monitor:
    image: its-define/embody-monitor:latest
    container_name: embody-monitor
    restart: unless-stopped
    environment:
      - ORCHESTRATOR_ID=${ORCHESTRATOR_ID}
      - ORCHESTRATOR_URL=http://livepeer-orchestrator:9995
      - MANAGER_URL=${MANAGER_URL}
      - MANAGER_API_KEY=${MANAGER_API_KEY}
      - REPORT_INTERVAL=60
    depends_on:
      - livepeer-orchestrator
      - livepeer-worker
    networks:
      - embody-network

networks:
  embody-network:
    driver: bridge

volumes:
  orchestrator_data:
```

## 🔧 Configuration Options

### Performance Tiers & Rewards

Your orchestrator earns based on uptime:

| Uptime | Status | Payment Multiplier |
|--------|--------|-------------------|
| >95%   | EXCELLENT | 1.2x |
| 80-95% | GOOD | 1.0x |
| 60-80% | WARNING | 0.7x |
| 40-60% | POOR | 0.3x |
| <40%   | CRITICAL | 0.1x |

### Advanced Settings

```bash
# Performance Optimization
CONCURRENT_JOBS=5                # Max concurrent BYOC jobs
BUFFER_SIZE_MB=10                # Stream buffer size
LOW_LATENCY_MODE=true            # Enable low latency

# Monitoring
ENABLE_METRICS=true              # Enable Prometheus metrics
METRICS_PORT=9090                # Metrics endpoint port
LOG_LEVEL=INFO                   # Logging verbosity

# Security
ENABLE_TLS=false                 # Enable TLS (provide certs)
TLS_CERT_PATH=/certs/cert.pem
TLS_KEY_PATH=/certs/key.pem
```

## 📊 Monitoring Your Orchestrator

### Health Check

```bash
# Local health check
curl http://localhost:9995/status

# Worker status
curl http://localhost:9876/health
```

### View Logs

```bash
# Orchestrator logs
docker logs embody-orchestrator --tail 50 -f

# Worker logs
docker logs embody-worker --tail 50 -f

# Monitor logs
docker logs embody-monitor --tail 50 -f
```

### Check Earnings

```bash
# Get payment status
curl https://embody.network/api/v1/orchestrators/your-unique-id/payments \
  -H "X-API-Key: your-provided-api-key"
```

## 🛠️ Troubleshooting

### Registration Failed

```bash
# Check connectivity to manager
curl https://embody.network/api/v1/health

# Verify API key
curl https://embody.network/api/v1/auth/verify \
  -H "X-API-Key: your-provided-api-key"

# Check orchestrator is running
docker ps | grep embody
```

### No Jobs Received

```bash
# Check orchestrator discovery
docker exec embody-worker curl http://livepeer-orchestrator:9995/registeredTranscoders

# Verify capability registration
docker logs embody-worker | grep "Registered capability"
```

### Connection Issues

```bash
# Test port accessibility
nc -zv YOUR_PUBLIC_IP 9995
nc -zv YOUR_PUBLIC_IP 9876

# Check firewall rules
sudo ufw status  # Ubuntu/Debian
sudo firewall-cmd --list-all  # CentOS/RHEL
```

## 🔄 Updates

### Automatic Updates

The orchestrator supports automatic updates:

```bash
# Enable auto-updates in .env
AUTO_UPDATE=true
UPDATE_CHECK_INTERVAL=3600  # seconds
```

### Manual Updates

```bash
# Pull latest images
docker-compose -f docker-compose.orchestrator.yml pull

# Restart services
docker-compose -f docker-compose.orchestrator.yml up -d
```

## 📞 Support

### Getting Help

- **Discord**: https://discord.gg/embody-network
- **Documentation**: https://docs.embody.network
- **Email**: orchestrators@embody.network

### Requesting API Key

To join the network, request your API key:

1. Visit: https://embody.network/orchestrators/apply
2. Or email: orchestrators@embody.network

Include:
- Your orchestrator name
- Expected capacity (jobs/hour)
- Geographic region
- Hardware specifications

## 🎯 Best Practices

1. **Maintain High Uptime**: Keep your orchestrator running 24/7
2. **Monitor Resources**: Ensure adequate CPU/RAM/bandwidth
3. **Update Regularly**: Keep software up-to-date
4. **Secure Your Node**: Use firewalls, secure your API keys
5. **Join Community**: Participate in Discord for tips and updates

## 📈 Scaling

### Adding Multiple Orchestrators

```bash
# Create multiple instances
ORCHESTRATOR_ID=your-id-001 docker-compose -p orch1 up -d
ORCHESTRATOR_ID=your-id-002 docker-compose -p orch2 up -d
```

### GPU Support

```bash
# For NVIDIA GPUs, add to docker-compose:
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## 🎉 Welcome to Embody Network!

Once registered, you'll start receiving BYOC jobs and earning rewards based on your uptime. Monitor your dashboard at https://embody.network/orchestrators/dashboard

Happy orchestrating! 🚀