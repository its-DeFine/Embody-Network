# 24/7 Autonomous Trading System

A production-ready 24/7 autonomous trading system with $1,000 starting capital. Features continuous market monitoring, real-time trade execution, multiple trading strategies, and comprehensive risk management.

## 📚 Documentation

**All documentation has been organized in the [`docs/`](./docs/) folder:**

- 🚀 [**Deployment Guide**](./docs/DEPLOYMENT.md) - Complete production deployment
- 📖 [**Trading System Overview**](./docs/TRADING_SYSTEM_OVERVIEW.md) - System architecture
- 🎯 [**Launch Guide**](./docs/LAUNCH_GUIDE.md) - Quick start instructions
- 🤖 [**Agent Management**](./docs/AGENT_MANAGEMENT.md) - AI agent coordination
- 📊 [**Platform Architecture**](./docs/PLATFORM_ARCHITECTURE.md) - Technical details

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd operation

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys (see docs/DEPLOYMENT.md)

# 3. Start the system
./scripts/start_trading.sh

# 4. Monitor trading
curl http://localhost:8000/api/v1/trading/portfolio
```

## ⚡ One-Line Start (with Docker)

```bash
# Start with default $1,000 capital
docker-compose up -d && sleep 30 && curl -X POST "http://localhost:8000/api/v1/trading/start" -H "Content-Type: application/json" -d '{"initial_capital": 1000.0}'
```

## 🎯 Core Features

### 💹 Trading System
- **24/7 Continuous Trading** - Never stops, always monitoring markets
- **$1,000 Starting Capital** - Real money trading with professional risk management
- **Multi-Strategy Engine** - Arbitrage, Scalping, and DCA strategies
- **Real-Time Execution** - Sub-second trade execution with market data
- **Risk Management** - 10% max position size, 2% stop losses, commission tracking

### 📊 Market Data & Analysis
- **Multiple Data Providers** - Finnhub, Twelve Data, MarketStack, Polygon
- **Real-Time Quotes** - Live market prices and volume data
- **Technical Analysis** - Built-in indicators and pattern recognition
- **Portfolio Tracking** - Real-time P&L, positions, and performance metrics

### 🤖 AI Agent Orchestration
- **Agent Teams** - Coordinated AI agents for trading, analysis, and risk management
- **Inter-Agent Communication** - Agents collaborate and share insights
- **AutoGen Integration** - Microsoft AutoGen for sophisticated agent conversations
- **Event-Driven Architecture** - Reactive system with Redis pub/sub

### 🔧 Production Ready
- **Docker Deployment** - Complete containerized solution
- **Health Monitoring** - Comprehensive system health checks and alerts
- **REST API + WebSocket** - Full API coverage with real-time updates
- **Persistent Storage** - Redis for state management and data persistence

## 📋 Trading Commands

### System Control
```bash
# Start trading system
./scripts/start_trading.sh

# Monitor in real-time
./scripts/monitor_trading.sh

# Stop trading (emergency)
curl -X POST http://localhost:8000/api/v1/trading/stop

# System health check
curl http://localhost:8000/api/v1/trading/health
```

### Portfolio & Performance
```bash
# Portfolio status
curl http://localhost:8000/api/v1/trading/portfolio

# Performance metrics
curl http://localhost:8000/api/v1/trading/performance

# Recent trades
curl http://localhost:8000/api/v1/trading/trades?limit=20

# Current positions
curl http://localhost:8000/api/v1/trading/positions
```

### Docker Management  
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

## 🔌 API Endpoints

### Trading Control
- `POST /api/v1/trading/start` - Start trading with initial capital
- `POST /api/v1/trading/stop` - Stop all trading activities  
- `GET /api/v1/trading/status` - Get system status (public)
- `GET /api/v1/trading/health` - Detailed health check

### Portfolio & Performance
- `GET /api/v1/trading/portfolio` - Current portfolio status
- `GET /api/v1/trading/positions` - All current positions
- `GET /api/v1/trading/performance?period=daily|weekly|monthly|all_time` - Performance metrics
- `GET /api/v1/trading/trades?limit=50&offset=0` - Trade history

### Real-time Updates
- `WebSocket /api/v1/trading/ws` - Real-time portfolio and trade updates
- `WebSocket /ws` - General system WebSocket
- `WebSocket /ws/market` - Market data stream

### Authentication & Management
- `POST /api/v1/auth/login` - System authentication
- `GET /api/v1/agents` - AI agent management
- `GET /api/v1/market/status` - Market data provider status

### Monitoring
- `GET /health` - Basic system health
- `GET /metrics` - Prometheus metrics

## 📁 Project Structure

```
operation/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── trading_engine.py       # 24/7 trading engine core logic
│   ├── models.py              # Database models (Portfolio, Trade, etc.)
│   ├── monitoring.py          # System monitoring and health checks
│   ├── api/
│   │   ├── trading.py         # Trading API endpoints
│   │   ├── market.py          # Market data endpoints
│   │   ├── auth.py            # Authentication
│   │   └── agents.py          # AI agent management
│   ├── services/
│   │   └── trading_service.py # Trading business logic layer
│   ├── agents/                # AI agent implementations
│   │   ├── trading_agent.py   # Trading decision agent
│   │   ├── analysis_agent.py  # Market analysis agent
│   │   └── base_agent.py      # Base agent class
│   ├── market_data_providers.py # Market data integrations
│   ├── config.py              # Application configuration
│   └── dependencies.py       # Shared dependencies
├── scripts/
│   ├── start_trading.sh       # Production startup script
│   └── monitor_trading.sh     # Real-time monitoring script
├── tests/                     # All test files (moved from root)
├── docs/
│   ├── DEPLOYMENT.md          # Complete deployment guide
│   └── TRADING_SYSTEM_OVERVIEW.md # System documentation
├── docker-compose.yml         # Production-ready Docker config
├── .env.production           # Production environment template
├── .env.example              # Development environment template
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## ⚙️ Configuration

### Required Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Security
JWT_SECRET=your-super-secure-jwt-secret
ADMIN_PASSWORD=your-secure-admin-password

# Market Data API Keys (get free keys)
FINNHUB_API_KEY=your-finnhub-key           # https://finnhub.io/
TWELVEDATA_API_KEY=your-twelvedata-key     # https://twelvedata.com/
MARKETSTACK_API_KEY=your-marketstack-key   # https://marketstack.com/

# Trading Parameters
INITIAL_CAPITAL=1000.00                    # Starting capital
MAX_POSITION_PCT=0.10                      # Max 10% per position
STOP_LOSS_PCT=0.02                         # 2% stop loss
TARGET_SYMBOLS=AAPL,MSFT,GOOGL,TSLA,NVDA  # Stocks to trade

# System
REDIS_URL=redis://localhost:6379
ENVIRONMENT=production
```

### Trading Strategies

The system includes three built-in strategies:

1. **Arbitrage Bot** - High-frequency, small profits (0.1% minimum)
2. **Scalping Bot** - 20-50 trades/day, short-term momentum
3. **DCA Bot** - Dollar Cost Averaging every 4 hours

## 🔒 Security & Risk Management

- **Position Limits**: Maximum 10% of portfolio per position
- **Stop Losses**: Automatic 2% stop loss on all positions
- **Commission Tracking**: 0.1% commission on all trades
- **Risk Monitoring**: Real-time portfolio risk assessment
- **Emergency Stop**: Instant trading halt via API

## 🚨 Important Warnings

⚠️ **This system trades with real money**
- Start with small amounts ($100-$1000) to test
- Monitor the system regularly
- Have emergency stop procedures ready
- Understand the risks of algorithmic trading

⚠️**Market Hours**
- System runs 24/7 but stock markets have trading hours
- Some strategies work better during active market periods
- Monitor performance during different market conditions

## 📊 Performance Tracking

The system tracks comprehensive metrics:
- Total return and percentage
- Win/loss ratio and profit factor
- Sharpe ratio and maximum drawdown  
- Trade frequency and average hold time
- Real-time P&L and portfolio value

## 🆘 Emergency Procedures

**Stop Trading Immediately:**
```bash
curl -X POST http://localhost:8000/api/v1/trading/stop
```

**Emergency System Shutdown:**
```bash
docker-compose down
```

**Check System Status:**
```bash
curl http://localhost:8000/api/v1/trading/health
```

## 📞 Support

For technical issues:
1. Check the logs: `docker-compose logs -f app`
2. Verify health: `curl http://localhost:8000/health`
3. Review deployment docs: `docs/DEPLOYMENT.md`

## 📜 License

MIT - Use at your own risk. Not financial advice.