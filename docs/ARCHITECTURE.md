# System Architecture

**Complete architecture overview of the VTuber Autonomy Platform.**

## 🏗️ System Overview

The VTuber Autonomy Platform (v0.1.0) is built as a **production-ready system** with microservices architecture. It combines real-time agent management, AI-driven character control, streaming capabilities, and autonomous decision making in a distributed, highly-available platform.

```
┌─────────────────────────────────────────────────────────────┐
│                   24/7 Trading System                      │
├─────────────────────────────────────────────────────────────┤
│  FastAPI REST API + WebSocket Real-time Updates            │
├─────────────────┬───────────────────┬───────────────────────┤
│   Trading       │    Market Data    │     AI Agents        │
│   Engine        │    Service        │     System           │
├─────────────────┼───────────────────┼───────────────────────┤
│  • Strategies   │  • Multi-Provider │  • Agent Manager     │
│  • Risk Mgmt    │  • Rate Limiting  │  • Collective Intel  │
│  • P&L Tracking │  • Real-time Feed │  • Decision Making   │
│  • Order Exec   │  • Caching        │  • Event System     │
├─────────────────┴───────────────────┴───────────────────────┤
│              Infrastructure Layer                           │
│  • Redis (State/Cache)  • Security  • Monitoring          │
│  • WebSocket Manager    • Audit     • Error Handling      │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Code Architecture

### Core Structure
```
operation/
├── app/
│   ├── main.py                    # FastAPI application entry
│   ├── api/                       # REST API endpoints
│   │   ├── trading.py            # Trading control API
│   │   ├── market.py             # Market data API
│   │   ├── management.py         # System management
│   │   └── auth.py               # Authentication
│   │
│   ├── core/                     # Business logic
│   │   ├── trading/              # Trading engine
│   │   │   ├── trading_engine.py # Main trading orchestrator
│   │   │   ├── trading_strategies.py # Strategy implementations
│   │   │   └── pnl_tracker.py    # Profit/loss tracking
│   │   │
│   │   ├── market/               # Market data processing
│   │   │   ├── market_data.py    # Data service coordinator
│   │   │   └── market_data_providers.py # Provider implementations
│   │   │
│   │   ├── agents/               # AI agent system
│   │   │   ├── agent_manager.py  # Agent lifecycle management
│   │   │   ├── collective_intelligence.py # Multi-agent consensus
│   │   │   └── trading_agent.py  # Trading decision agents
│   │   │
│   │   └── orchestration/        # Task coordination
│   │       ├── orchestrator.py   # Central task orchestrator
│   │       └── gpu_orchestrator.py # GPU task management
│   │
│   ├── infrastructure/           # Support systems
│   │   ├── messaging/            # Communication layer
│   │   │   ├── websocket_manager.py # Real-time updates
│   │   │   └── cross_instance_bridge.py # Multi-instance sync
│   │   │
│   │   ├── monitoring/           # Observability
│   │   │   ├── audit_logger.py   # Audit trail
│   │   │   └── reliability_manager.py # Health monitoring
│   │   │
│   │   └── security/             # Security layer
│   │       └── key_manager.py    # PGP-based authentication
│   │
│   └── services/                 # External integrations
│       ├── trading_service.py    # Trading business logic
│       └── ollama_integration.py # Local LLM integration
│
├── docs/                         # Documentation
├── scripts/                      # Operational scripts
├── tests/                        # Test suite
└── docker-compose.yml           # Container orchestration
```

## 🎯 Core Components

### 1. Trading Engine (`core/trading/`)

**Purpose**: Central trading orchestrator managing all trading activities.

**Key Features**:
- **Strategy Management**: Runs 5 concurrent strategies (Arbitrage, Momentum, Mean Reversion, Scalping, DCA)
- **Risk Management**: Position limits, stop losses, Kelly criterion position sizing
- **Order Execution**: Simulated execution with real market prices
- **P&L Tracking**: Real-time profit/loss calculation with persistence
- **Portfolio Management**: Real-time portfolio value and position tracking

**Architecture**:
```python
TradingEngine
├── Strategy Manager (manages multiple strategies)
├── Risk Manager (enforces limits and stops)
├── Order Executor (executes trades)
├── P&L Tracker (tracks profits/losses)
└── Portfolio Manager (manages positions)
```

### 2. Market Data Service (`core/market/`)

**Purpose**: Multi-provider market data aggregation with failover and rate limiting.

**Data Providers**:
- **Yahoo Finance**: 2,000 requests/hour (primary)
- **Twelve Data**: 800 calls/day
- **Alpha Vantage**: 500 calls/day
- **Finnhub**: 86,400 calls/day

**Features**:
- **Provider Failover**: Automatic fallback if primary provider fails
- **Rate Limiting**: Intelligent request throttling per provider
- **Real-time Streaming**: WebSocket price feeds
- **Data Caching**: Redis-based caching for performance
- **Technical Indicators**: RSI, MACD, Bollinger Bands calculation

### 3. AI Agent System (`core/agents/`)

**Purpose**: Multi-agent AI system for collaborative trading decisions.

**Components**:
- **Agent Manager**: Lifecycle management for AI agents
- **Collective Intelligence**: Multi-agent consensus and decision making
- **Trading Agents**: Specialized agents for different trading strategies
- **Communication System**: Event-driven inter-agent communication

**Agent Types**:
```python
# Trading Agent - Makes buy/sell decisions
class TradingAgent:
    def analyze_market(self, data) -> TradingSignal
    def execute_trade(self, signal) -> TradeResult

# Analysis Agent - Market analysis and predictions  
class AnalysisAgent:
    def analyze_trends(self, data) -> MarketAnalysis
    def generate_signals(self, analysis) -> List[Signal]

# Risk Agent - Risk assessment and management
class RiskAgent:
    def assess_risk(self, portfolio) -> RiskAssessment
    def recommend_adjustments(self, risk) -> List[Adjustment]
```

### 4. Infrastructure Layer (`infrastructure/`)

**Real-time Communication**:
- **WebSocket Manager**: Handles real-time client connections
- **Cross-Instance Bridge**: Synchronizes multiple system instances
- **Event System**: Pub/sub messaging between components

**Monitoring & Security**:
- **Audit Logger**: Comprehensive audit trail for all operations
- **Reliability Manager**: Health monitoring and circuit breakers
- **Security Manager**: PGP-based authentication and encryption

## 🔄 Data Flow Architecture

### 1. Trading Decision Flow
```
Market Data → Technical Analysis → AI Agents → Consensus → Risk Check → Order Execution → P&L Update
     ↓              ↓                ↓           ↓           ↓              ↓             ↓
  [Cache]     [Indicators]    [Collective]  [Approval]  [Validation]  [Simulation]  [Persistence]
```

### 2. Event-Driven Architecture
```python
# Events flow through the system
MarketDataEvent → AnalysisEvent → TradingSignalEvent → OrderEvent → ExecutionEvent → PnLEvent

# Components subscribe to relevant events
TradingEngine.subscribe(MarketDataEvent)
RiskManager.subscribe(TradingSignalEvent) 
PnLTracker.subscribe(ExecutionEvent)
WebSocketManager.subscribe(PnLEvent)
```

### 3. State Management
```
Redis State Store:
├── market:prices:{symbol}        # Real-time price cache
├── trading:portfolio             # Current portfolio state
├── trading:positions:{symbol}    # Individual positions
├── trading:trades:{date}         # Trade history
├── agents:active                 # Active agents list
├── strategies:performance        # Strategy metrics
└── system:health                 # System health status
```

## 🎛️ API Architecture

### REST API Structure
```
/api/v1/
├── trading/                      # Trading control
│   ├── start                     # Start trading system
│   ├── stop                      # Stop trading system
│   ├── status                    # System status
│   ├── portfolio                 # Portfolio information
│   ├── performance               # Performance metrics
│   └── trades                    # Trade history
│
├── market/                       # Market data
│   ├── price/{symbol}            # Current price
│   ├── prices                    # Batch prices
│   ├── historical/{symbol}       # Historical data
│   └── providers                 # Provider status
│
├── agents/                       # Agent management
│   ├── create                    # Create new agent
│   ├── list                      # List all agents
│   ├── {id}/tasks               # Agent tasks
│   └── {id}/status              # Agent status
│
└── management/                   # System management
    ├── health                    # Health checks
    ├── metrics                   # System metrics
    └── config                    # Configuration
```

### WebSocket Architecture
```
WebSocket Channels:
├── /ws                          # General system events
├── /ws/market                   # Market data stream
├── /ws/trading                  # Trading events
└── /ws/agents                   # Agent communications

Event Types:
├── market.price_update          # Real-time price updates
├── trading.order_executed       # Trade executions
├── portfolio.value_changed      # Portfolio updates
└── system.health_changed        # System health alerts
```

## 🔧 Technology Stack

### Core Technologies
- **Python 3.11**: Main application language
- **FastAPI**: High-performance API framework
- **Redis**: In-memory data store and cache
- **Docker**: Containerization and deployment
- **Uvicorn**: ASGI web server

### Trading-Specific Libraries
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **httpx**: Async HTTP client for API calls
- **websockets**: Real-time communication

### Infrastructure
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy and SSL termination (production)
- **Let's Encrypt**: SSL certificate management

## 🚦 Deployment Architecture

### Development Environment
```
Local Machine:
├── Docker Compose
│   ├── App Container (Python/FastAPI)
│   ├── Redis Container (Data/Cache)
│   └── Ollama Container (Local LLM)
└── Host Network (port 8000)
```

### Production Environment
```
Production Server:
├── Nginx (SSL Termination)
│   └── Reverse Proxy → App Container
├── Docker Compose
│   ├── App Container (Trading System)
│   ├── Redis Container (Persistent Storage)
│   └── Monitoring Container (Optional)
├── Firewall (UFW/iptables)
└── Log Management (logrotate)
```

### Scaling Architecture (Future)
```
Load Balancer:
├── Instance 1 (Primary Trading)
├── Instance 2 (Backup/Analysis)
└── Instance 3 (Research/Development)
     ↓
Shared Resources:
├── Redis Cluster (Distributed Cache)
├── PostgreSQL (Long-term Storage)
└── Message Queue (RabbitMQ/Kafka)
```

## 🔍 Design Principles

### 1. **Reliability First**
- Graceful error handling at every level
- Automatic failover between data providers
- Persistent state management for recovery
- Circuit breakers for external services

### 2. **Real-time Performance**
- Async/await throughout the application
- Redis caching for fast data access
- WebSocket streaming for real-time updates
- Efficient data structures and algorithms

### 3. **Security by Design**
- PGP-based authentication system
- Secure environment variable management
- Audit logging for all operations
- Rate limiting and DDoS protection

### 4. **Observability**
- Comprehensive logging and metrics
- Health checks at every component level
- Performance monitoring and alerting
- Audit trails for regulatory compliance

### 5. **Scalability**
- Horizontal scaling capability
- Stateless application design (state in Redis)
- Microservices-ready internal architecture
- Event-driven communication patterns

## 🎯 Key Architectural Decisions

### Why Monolith Instead of Microservices?
1. **Simplicity**: Easier deployment and debugging
2. **Performance**: No network overhead between components
3. **Consistency**: Single database transactions
4. **Development Speed**: Faster iteration and testing

### Why Redis for State Management?
1. **Performance**: Sub-millisecond response times
2. **Persistence**: Configurable durability options
3. **Pub/Sub**: Built-in event system
4. **Clustering**: Easy horizontal scaling when needed

### Why FastAPI Framework?
1. **Performance**: One of the fastest Python frameworks
2. **Type Safety**: Built-in Pydantic validation
3. **Documentation**: Automatic OpenAPI/Swagger docs
4. **Modern**: Async/await support throughout

### Why Event-Driven Architecture?
1. **Decoupling**: Components can evolve independently
2. **Scalability**: Easy to add new event handlers
3. **Reliability**: Failed components don't block others
4. **Observability**: Central event tracking

This architecture provides a solid foundation for a production-ready trading system while maintaining flexibility for future enhancements and scaling requirements.