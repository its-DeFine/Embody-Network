# API Reference

**Complete API documentation for the VTuber Autonomy Platform.**

## 🔐 Authentication

All API endpoints (except `/health`) require authentication using JWT tokens.

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-admin-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Using Authentication
Include the token in all subsequent requests:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## 🆕 System Information

### Get Version
```http
GET /api/v1/version
```

**Response:**
```json
{
  "version": "0.1.0",
  "major": 0,
  "minor": 1,
  "patch": 0,
  "prerelease": null,
  "build": null
}
```

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-11T10:30:00Z",
  "version": "0.1.0"
}
```

## 🎭 VTuber Agent Management

### List Agents
```http
GET /api/v1/embodiment/agents
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "agent_id": "luna_001",
    "name": "Luna",
    "status": "online",
    "type": "character",
    "created_at": "2025-08-11T10:00:00Z"
  }
]
```

### Dashboard
```http
GET /dashboard/
```

Returns the VTuber management dashboard HTML with real-time agent monitoring.

## 💹 Trading API (Legacy)

### Start Trading System
```http
POST /api/v1/trading/start
Content-Type: application/json
Authorization: Bearer <token>

{
  "initial_capital": 1000.0
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Trading system started successfully",
  "initial_capital": 1000.0,
  "trading_id": "trade_session_123",
  "strategies_active": 5,
  "started_at": "2025-08-04T14:30:00Z"
}
```

### Stop Trading System
```http
POST /api/v1/trading/stop
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Trading system stopped successfully",
  "final_portfolio_value": 1245.67,
  "total_pnl": 245.67,
  "stopped_at": "2025-08-04T18:30:00Z"
}
```

### Get Trading Status
```http
GET /api/v1/trading/status
```

**Response:**
```json
{
  "trading_active": true,
  "system_uptime": "4h 23m 15s",
  "strategies_running": 5,
  "market_data_connected": true,
  "redis_connected": true,
  "last_trade": "2025-08-04T14:25:00Z",
  "health_status": "healthy",
  "api_providers_active": 4
}
```

### Get Portfolio Status
```http
GET /api/v1/trading/portfolio
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total_value": 1245.67,
  "cash": 234.56,
  "invested": 1011.11,
  "daily_pnl": 12.34,
  "total_pnl": 245.67,
  "return_pct": 24.57,
  "positions_count": 8,
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 5.0,
      "avg_cost": 200.50,
      "current_price": 206.66,
      "market_value": 1033.30,
      "unrealized_pnl": 30.80,
      "unrealized_pnl_pct": 1.54
    }
  ]
}
```

### Get Performance Metrics
```http
GET /api/v1/trading/performance?period=daily
Authorization: Bearer <token>
```

**Query Parameters:**
- `period`: `daily`, `weekly`, `monthly`, `all_time`

**Response:**
```json
{
  "period": "daily",
  "total_return": 0.0234,
  "total_return_pct": 2.34,
  "total_trades": 15,
  "winning_trades": 10,
  "losing_trades": 5,
  "win_rate": 0.67,
  "profit_factor": 1.42,
  "avg_win": 0.0312,
  "avg_loss": -0.0156,
  "sharpe_ratio": 1.85,
  "max_drawdown": -0.0234,
  "strategies": {
    "mean_reversion": {
      "return": 0.008,
      "trades": 3,
      "win_rate": 0.67
    },
    "momentum": {
      "return": 0.012,
      "trades": 5,
      "win_rate": 0.60
    }
  }
}
```

### Get Trade History
```http
GET /api/v1/trading/trades?limit=50&offset=0
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit`: Number of trades to return (default: 50, max: 500)
- `offset`: Number of trades to skip (default: 0)
- `symbol`: Filter by symbol (optional)
- `strategy`: Filter by strategy (optional)

**Response:**
```json
{
  "trades": [
    {
      "id": "trade_123",
      "timestamp": "2025-08-04T14:25:00Z",
      "symbol": "AAPL",
      "action": "buy",
      "quantity": 5.0,
      "price": 200.50,
      "commission": 1.00,
      "strategy": "mean_reversion",
      "pnl": 0.0,
      "status": "executed"
    }
  ],
  "total_count": 247,
  "has_more": true
}
```

### Get Current Positions
```http
GET /api/v1/trading/positions
Authorization: Bearer <token>
```

**Response:**
```json
{
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 5.0,
      "avg_cost": 200.50,
      "current_price": 206.66,
      "market_value": 1033.30,
      "unrealized_pnl": 30.80,
      "unrealized_pnl_pct": 1.54,
      "entry_date": "2025-08-04T10:15:00Z",
      "strategy": "mean_reversion"
    }
  ],
  "total_positions": 8,
  "total_market_value": 1011.11,
  "total_unrealized_pnl": 45.67
}
```

## 📊 Market Data API

### Get Current Price
```http
GET /api/v1/market/price/{symbol}
```

**Example:**
```http
GET /api/v1/market/price/AAPL
```

**Response:**
```json
{
  "symbol": "AAPL",
  "price": 206.66,
  "change": 1.34,
  "change_pct": 0.65,
  "volume": 45123456,
  "timestamp": "2025-08-04T14:30:00Z",
  "provider": "yahoo_finance"
}
```

### Get Multiple Prices
```http
POST /api/v1/market/prices
Content-Type: application/json

{
  "symbols": ["AAPL", "GOOGL", "MSFT", "BTC-USD"]
}
```

**Response:**
```json
{
  "prices": [
    {
      "symbol": "AAPL",
      "price": 206.66,
      "timestamp": "2025-08-04T14:30:00Z"
    },
    {
      "symbol": "GOOGL", 
      "price": 194.42,
      "timestamp": "2025-08-04T14:30:00Z"
    }
  ],
  "provider": "yahoo_finance",
  "request_time": "2025-08-04T14:30:01Z"
}
```

### Get Historical Data
```http
GET /api/v1/market/historical/{symbol}?period=30d&interval=1h
```

**Query Parameters:**
- `period`: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`
- `interval`: `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, `3mo`

**Response:**
```json
{
  "symbol": "AAPL",
  "period": "30d",
  "interval": "1h",
  "data": [
    {
      "timestamp": "2025-07-05T14:30:00Z",
      "open": 200.50,
      "high": 202.10,
      "low": 199.80,
      "close": 201.75,
      "volume": 1234567
    }
  ],
  "count": 720
}
```

### Get Market Status
```http
GET /api/v1/market/status
```

**Response:**
```json
{
  "market_open": true,
  "next_open": "2025-08-05T09:30:00Z",
  "next_close": "2025-08-04T16:00:00Z",
  "timezone": "America/New_York",
  "providers": [
    {
      "name": "yahoo_finance",
      "status": "active",
      "last_update": "2025-08-04T14:30:00Z",
      "rate_limit_remaining": 1850
    },
    {
      "name": "twelvedata",
      "status": "active", 
      "last_update": "2025-08-04T14:29:45Z",
      "rate_limit_remaining": 750
    }
  ]
}
```

### Get Provider Status
```http
GET /api/v1/market/providers
```

**Response:**
```json
{
  "providers": [
    {
      "name": "yahoo_finance",
      "status": "active",
      "priority": 1,
      "rate_limit": {
        "requests_per_hour": 2000,
        "remaining": 1850,
        "reset_time": "2025-08-04T15:00:00Z"
      },
      "response_time_ms": 245,
      "success_rate": 0.987,
      "last_error": null
    }
  ],
  "active_provider": "yahoo_finance",
  "backup_providers": ["twelvedata", "finnhub"]
}
```

## 🤖 Agent Management API

### List Agents
```http
GET /api/v1/agents
Authorization: Bearer <token>
```

**Response:**
```json
{
  "agents": [
    {
      "id": "agent_123",
      "name": "Mean Reversion Trader",
      "type": "trading",
      "status": "active",
      "strategy": "mean_reversion",
      "created_at": "2025-08-04T10:00:00Z",
      "last_activity": "2025-08-04T14:25:00Z",
      "performance": {
        "total_trades": 15,
        "win_rate": 0.73,
        "total_pnl": 34.56
      }
    }
  ],
  "total_agents": 8,
  "active_agents": 5
}
```

### Create Agent
```http
POST /api/v1/agents
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Custom Momentum Trader",
  "type": "trading",
  "config": {
    "strategy": "momentum",
    "symbols": ["TSLA", "NVDA"],
    "risk_level": "moderate",
    "max_position_size": 200.0
  }
}
```

**Response:**
```json
{
  "id": "agent_456",
  "name": "Custom Momentum Trader",
  "type": "trading",
  "status": "created",
  "config": {
    "strategy": "momentum",
    "symbols": ["TSLA", "NVDA"],
    "risk_level": "moderate",
    "max_position_size": 200.0
  },
  "created_at": "2025-08-04T14:35:00Z"
}
```

## ⚙️ System Management API

### System Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-04T14:30:00Z",
  "version": "1.0.0",
  "uptime": "4h 23m 15s",
  "components": {
    "database": "healthy",
    "market_data": "healthy", 
    "trading_engine": "healthy",
    "websocket": "healthy"
  }
}
```

### System Metrics
```http
GET /metrics
Authorization: Bearer <token>
```

**Response:**
```json
{
  "system": {
    "cpu_usage": 25.4,
    "memory_usage": 512.3,
    "disk_usage": 12.8,
    "network_io": {
      "bytes_sent": 1234567,
      "bytes_received": 2345678
    }
  },
  "application": {
    "active_connections": 15,
    "requests_per_minute": 120,
    "error_rate": 0.002,
    "avg_response_time": 145
  },
  "trading": {
    "trades_today": 47,
    "active_strategies": 5,
    "portfolio_value": 1245.67,
    "daily_pnl": 12.34
  }
}
```

### Update Configuration
```http
PUT /api/v1/management/config
Content-Type: application/json
Authorization: Bearer <token>

{
  "max_position_pct": 0.15,
  "stop_loss_pct": 0.025,
  "target_symbols": ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META"],
  "enable_strategies": {
    "mean_reversion": true,
    "momentum": true,
    "arbitrage": false,
    "scalping": false,
    "dca": true
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Configuration updated successfully",
  "updated_at": "2025-08-04T14:35:00Z",
  "restart_required": false
}
```

## 🔄 WebSocket API

### Connect to WebSocket
```javascript
// Connect to general WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// Connect to authenticated WebSocket
const wsAuth = new WebSocket('ws://localhost:8000/ws/authenticated?token=<jwt-token>');

// Connect to market data stream
const wsMarket = new WebSocket('ws://localhost:8000/ws/market');
```

### WebSocket Message Types

**System Events:**
```json
{
  "type": "system.status_change",
  "data": {
    "status": "healthy",
    "timestamp": "2025-08-04T14:30:00Z"
  }
}
```

**Trading Events:**
```json
{
  "type": "trading.order_executed",
  "data": {
    "trade_id": "trade_123",
    "symbol": "AAPL",
    "action": "buy",
    "quantity": 5.0,
    "price": 206.66,
    "timestamp": "2025-08-04T14:30:00Z"
  }
}
```

**Market Data Events:**
```json
{
  "type": "market.price_update",
  "data": {
    "symbol": "AAPL",
    "price": 206.66,
    "change": 1.34,
    "timestamp": "2025-08-04T14:30:00Z"
  }
}
```

**Portfolio Events:**
```json
{
  "type": "portfolio.value_changed", 
  "data": {
    "total_value": 1245.67,
    "daily_pnl": 12.34,
    "change": 2.50,
    "timestamp": "2025-08-04T14:30:00Z"
  }
}
```

## 📝 Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "TRADING_001",
    "message": "Insufficient balance for trade execution",
    "details": {
      "required_balance": 1000.0,
      "available_balance": 245.67,
      "symbol": "AAPL",
      "quantity": 5.0
    },
    "timestamp": "2025-08-04T14:30:00Z"
  }
}
```

### Common Error Codes

| Code | Message | Description |
|------|---------|-------------|
| AUTH_001 | Invalid credentials | Login failed |
| AUTH_002 | Token expired | JWT token has expired |
| AUTH_003 | Insufficient permissions | User lacks required permissions |
| TRADING_001 | Insufficient balance | Not enough cash for trade |
| TRADING_002 | Invalid symbol | Symbol not supported |
| TRADING_003 | Market closed | Trading outside market hours |
| TRADING_004 | Position limit exceeded | Max position size exceeded |
| MARKET_001 | Data provider error | Market data unavailable |
| MARKET_002 | Rate limit exceeded | API rate limit hit |
| SYSTEM_001 | Service unavailable | System maintenance or error |

## 🔄 Rate Limits

### API Rate Limits

| Endpoint Category | Authenticated | Unauthenticated |
|------------------|---------------|-----------------|
| Trading API | 100 req/min | N/A |
| Market Data | 200 req/min | 50 req/min |
| System Management | 50 req/min | N/A |
| WebSocket | 10 connections | 2 connections |

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1625097600
```

## 📊 Pagination

### Paginated Responses
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_pages": 10,
    "total_count": 487,
    "has_next": true,
    "has_prev": false
  }
}
```

### Pagination Parameters
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 50, max: 500)
- `sort`: Sort field (default: timestamp)
- `order`: `asc` or `desc` (default: desc)

This comprehensive API reference provides all the information needed to interact with the trading system programmatically.