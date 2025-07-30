# OpenBB Adapter Service

The OpenBB Adapter Service provides a unified interface for accessing financial market data through the OpenBB platform. It acts as a bridge between the AutoGen agents and OpenBB's comprehensive financial data ecosystem.

## Features

- **Market Data Access**: Real-time and historical market data
- **Technical Analysis**: Built-in technical indicators (RSI, MACD, Bollinger Bands, etc.)
- **Portfolio Analytics**: Portfolio performance metrics and risk analysis
- **Caching Layer**: Redis-based caching for improved performance
- **Event-Driven Architecture**: RabbitMQ integration for async operations

## API Endpoints

### Health Check
```
GET /health
```

### Market Data
```
GET /api/v1/market/data
Query params:
- symbol: Stock/crypto symbol (e.g., "AAPL", "BTC/USDT")
- interval: Time interval (1m, 5m, 1h, 1d)
- start_date: Optional start date
- end_date: Optional end date
```

### Technical Analysis
```
POST /api/v1/analysis/technical
Body:
{
  "symbol": "AAPL",
  "indicators": ["RSI", "MACD", "BB", "EMA"]
}
```

### Portfolio Analysis
```
POST /api/v1/portfolio/analyze
Body:
{
  "positions": [
    {"symbol": "AAPL", "quantity": 100, "cost_basis": 150.00},
    {"symbol": "GOOGL", "quantity": 50, "cost_basis": 2800.00}
  ]
}
```

## Environment Variables

- `REDIS_URL`: Redis connection URL (default: redis://redis:6379)
- `RABBITMQ_URL`: RabbitMQ connection URL
- `CACHE_TTL`: Cache time-to-live in seconds (default: 1800)
- `LOG_LEVEL`: Logging level (debug, info, warning, error)

## Integration with Agents

Agents can access OpenBB data through the base agent class methods:

```python
# Get market data
data = await agent.get_market_data("AAPL", "1d")

# Get technical analysis
analysis = await agent.get_technical_analysis("AAPL", ["RSI", "MACD"])

# Analyze portfolio
portfolio_metrics = await agent.analyze_portfolio(positions)
```

## Architecture

The service follows a modular architecture:

```
services/openbb-adapter/
├── main.py              # FastAPI application
├── openbb_service.py    # Core OpenBB integration
├── models/              # Pydantic data models
├── handlers/            # Event handlers for RabbitMQ
├── cache/               # Redis caching utilities
└── utils/               # Helper functions
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

## Testing

```bash
# Run integration tests
pytest tests/integration/test_openbb_integration.py -v
```