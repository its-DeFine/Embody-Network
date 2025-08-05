# 24/7 Autonomous Trading System

**GPU-accelerated autonomous trading platform with AI-driven strategies, unlimited market data, and distributed orchestrator deployment capabilities.**

![System Status](https://img.shields.io/badge/Status-Production%20Ready-green)
![GPU](https://img.shields.io/badge/GPU-Accelerated-blue)
![Trading](https://img.shields.io/badge/Trading-24/7%20Autonomous-orange)
![AI](https://img.shields.io/badge/AI-Ollama%20Integrated-purple)

## 🚀 Quick Deploy

### Orchestrator Node (Recommended)
Deploy a distributed orchestrator node that connects to existing central manager infrastructure:

```bash
# 1. Configure connection to central manager
cp .env.orchestrator .env
# Edit .env: Set CENTRAL_MANAGER_HOST, ADMIN_PASSWORD, JWT_SECRET

# 2. Deploy orchestrator with GPU + AI support
cd docker/production/
docker-compose -f docker-compose.orchestrator-cluster.yml up -d
```

### Central Manager (Full Stack)
Deploy complete trading infrastructure:

```bash
# 1. Configure environment
cp .env.central-manager .env
# Edit .env with your API keys and settings

# 2. Deploy central manager
cd docker/production
docker-compose -f docker-compose.central-manager.yml up -d

# 3. Start trading
curl -X POST "http://localhost:8000/api/v1/trading/start" \
  -H "Content-Type: application/json" \
  -d '{"initial_capital": 10000.0}'
```

## 📋 System Overview

This repository contains a production-ready 24/7 autonomous trading system featuring:

### 🔥 **Core Features**
- **GPU-Accelerated AI**: Nvidia runtime with Ollama for local LLM inference
- **Rate-Limit-Free Data**: Mock market data provider for unlimited testing
- **High-Frequency Strategies**: DCA (2-minute intervals) + Arbitrage (80% trigger rate)
- **Distributed Architecture**: Central manager + multiple orchestrator nodes
- **Real-Time Execution**: Sub-second trade execution with continuous monitoring

### 🎯 **Trading Capabilities**
- **Multiple Strategies**: Arbitrage, DCA, Momentum, Mean Reversion, Scalping
- **Risk Management**: Stop losses, position limits, daily trade limits
- **Multi-Asset Support**: Stocks, crypto, ETFs with configurable symbols
- **Performance Tracking**: Real-time P&L, portfolio metrics, trade statistics

### 🏗️ **Architecture**
- **Central Manager**: Core trading engine with database and Redis
- **Orchestrator Nodes**: Distributed AI agents with GPU acceleration
- **Market Data**: Multiple providers with automatic failover
- **Security**: JWT authentication, role-based access, input validation

## 🔧 Full Orchestrator Deployment

### Prerequisites
- Docker with nvidia runtime support
- GPU-enabled host (for AI acceleration)
- Network access to central manager

### Configuration Steps

1. **Copy orchestrator environment file:**
   ```bash
   cp .env.orchestrator .env
   ```

2. **Configure connection settings in `.env`:**
   ```env
   # Central Manager Connection
   CENTRAL_MANAGER_HOST=<central-manager-ip>
   CENTRAL_MANAGER_URL=http://<central-manager-ip>:8000
   REDIS_URL=redis://:<password>@<central-manager-ip>:6379
   
   # Authentication (must match central manager)
   ADMIN_PASSWORD=<central-manager-admin-password>
   JWT_SECRET=<central-manager-jwt-secret>
   
   # Orchestrator Identity
   ORCHESTRATOR_ID=<unique-id>
   EXTERNAL_IP=<your-external-ip>
   
   # GPU Configuration
   ENABLE_GPU_SUPPORT=true
   OLLAMA_BASE_URL=http://orchestrator-ollama-1:11434
   ```

3. **Deploy orchestrator:**
   ```bash
   cd docker/production
   docker-compose --env-file ../../.env.orchestrator -f docker-compose.orchestrator-cluster.yml up -d
   ```

4. **Verify deployment:**
   ```bash
   docker ps  # Check containers are running
   docker logs orchestrator-cluster-1  # Check connection to central manager
   ```

### Orchestrator Components
- **orchestrator-cluster-1**: Main trading agent with GPU access
- **orchestrator-ollama-1**: Local LLM service for AI-driven decisions
- **Automatic registration**: Connects to central manager on startup

## 📊 API Reference

### Trading Control
```bash
# Start trading
POST /api/v1/trading/start
{"initial_capital": 10000.0}

# System status
GET /api/v1/trading/status

# Portfolio & positions
GET /api/v1/trading/portfolio

# Stop trading
POST /api/v1/trading/stop
```

### Health & Monitoring
```bash
# System health
GET /health

# Trade history
GET /api/v1/trading/trades

# Performance metrics
GET /api/v1/trading/performance
```

## 🛡️ Security & Risk Management

### Built-in Safety Features
- **Position Limits**: Max 10% portfolio per position
- **Stop Losses**: Automatic 2% stop loss on all trades
- **Daily Limits**: Maximum 50 trades per day
- **Real-time Monitoring**: Continuous risk assessment
- **Emergency Stop**: Instant halt via API

### Security Features
- **JWT Authentication**: Secure API access
- **Role-based Access**: Admin/Trader/Viewer permissions
- **Input Validation**: Protection against malicious requests
- **Rate Limiting**: API abuse prevention

## 📚 Documentation

For detailed documentation, see:
- **[ORCHESTRATOR_DEPLOYMENT_PATTERN.md](docs/ORCHESTRATOR_DEPLOYMENT_PATTERN.md)** - Complete orchestrator deployment guide
- **[DISTRIBUTED_QUICK_START.md](docs/DISTRIBUTED_QUICK_START.md)** - Quick start for distributed deployment
- **[SECURITY.md](docs/SECURITY.md)** - Security configuration and best practices
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## ⚠️ Important Disclaimers

- **Real Money Trading**: This system executes real trades with actual capital
- **GPU Requirements**: Orchestrator nodes require nvidia-docker for AI acceleration
- **Market Risk**: All trading involves substantial risk of loss
- **Testing Recommended**: Start with small amounts to validate system behavior

## 📜 License

MIT License - Use at your own risk. This software is for educational purposes. Trading involves substantial risk of loss and past performance does not guarantee future results.

---

**Ready to deploy?** Start with an orchestrator node deployment using the quick deploy commands above.