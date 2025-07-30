# OpenBB Integration Guide

This guide explains how to use the OpenBB financial data integration in the AutoGen platform.

## Overview

The OpenBB adapter service provides agents with access to comprehensive financial market data, technical analysis, and portfolio analytics through a unified API interface.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   AutoGen   │────▶│   OpenBB    │────▶│   OpenBB    │
│   Agents    │     │   Adapter   │     │  Platform   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │   (Cache)   │
                    └─────────────┘
```

## Features

### 1. Market Data Access
- Real-time and historical price data
- Multiple asset classes (stocks, crypto, forex, commodities)
- Configurable time intervals
- Automatic caching for performance

### 2. Technical Analysis
- Built-in technical indicators:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)  
  - Bollinger Bands
  - EMA (Exponential Moving Average)
  - And many more...

### 3. Portfolio Analytics
- Portfolio performance metrics
- Risk analysis (VaR, CVaR)
- Sharpe ratio, Sortino ratio
- Portfolio optimization suggestions

## Using OpenBB in Agents

### For Agent Developers

The base agent class automatically initializes an OpenBB client. You can access it through these methods:

```python
# In your agent code
async def analyze_market(self):
    # Get market data
    data = await self.get_market_data("AAPL", "1d")
    
    # Get technical indicators
    analysis = await self.get_technical_analysis(
        "AAPL", 
        ["RSI", "MACD", "BB"]
    )
    
    # Analyze portfolio
    positions = [
        {"symbol": "AAPL", "quantity": 100, "cost_basis": 150},
        {"symbol": "GOOGL", "quantity": 50, "cost_basis": 2800}
    ]
    portfolio_metrics = await self.analyze_portfolio(positions)
```

### For Trading Agents

Trading agents have enhanced integration that automatically uses OpenBB data when available:

```python
# The trading agent will use OpenBB first, with fallback to exchange data
market_data = await trading_agent.get_market_data("BTC/USDT")

# Technical analysis with OpenBB
indicators = await trading_agent.analyze_technicals(
    "BTC/USDT",
    ["RSI", "MACD", "BB", "EMA"]
)
```

## API Endpoints

The OpenBB adapter exposes the following REST API endpoints:

### Health Check
```bash
GET http://localhost:8003/health
```

### Market Data
```bash
GET http://localhost:8003/api/v1/market/data?symbol=AAPL&interval=1d
```

Parameters:
- `symbol`: Asset symbol (required)
- `interval`: Time interval - 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M
- `start_date`: ISO format date (optional)
- `end_date`: ISO format date (optional)

### Technical Analysis
```bash
POST http://localhost:8003/api/v1/analysis/technical
Content-Type: application/json

{
  "symbol": "AAPL",
  "indicators": ["RSI", "MACD", "BB", "EMA"]
}
```

### Portfolio Analysis
```bash
POST http://localhost:8003/api/v1/portfolio/analyze
Content-Type: application/json

{
  "positions": [
    {"symbol": "AAPL", "quantity": 100, "cost_basis": 150.00},
    {"symbol": "GOOGL", "quantity": 50, "cost_basis": 2800.00}
  ],
  "benchmark": "SPY",
  "risk_free_rate": 0.05
}
```

## Event-Driven Updates

The OpenBB adapter also publishes market updates via RabbitMQ:

### Subscribe to Market Updates
```python
# Topic pattern: market.update.{symbol}
# Example: market.update.AAPL

# The adapter publishes real-time updates when available
```

## Configuration

### Environment Variables

Configure the OpenBB adapter through environment variables:

```bash
# Redis cache settings
REDIS_URL=redis://redis:6379
CACHE_TTL=1800  # 30 minutes

# RabbitMQ settings
RABBITMQ_URL=amqp://admin:password@rabbitmq:5672/

# Logging
LOG_LEVEL=info
```

### Cache Configuration

The adapter uses Redis to cache API responses:
- Market data: 5 minutes default TTL
- Technical analysis: 10 minutes default TTL
- Portfolio analysis: Not cached (always fresh)

## Performance Considerations

1. **Caching**: All market data and technical analysis results are cached to reduce API calls
2. **Rate Limiting**: The adapter respects OpenBB rate limits automatically
3. **Fallback**: Agents can fall back to exchange data if OpenBB is unavailable
4. **Batch Requests**: Use batch endpoints when analyzing multiple symbols

## Error Handling

The adapter provides graceful error handling:

```python
# Agents automatically handle OpenBB failures
result = await self.get_market_data("INVALID_SYMBOL")
if "error" in result:
    # Handle error or use fallback data
    logger.warning(f"OpenBB error: {result['error']}")
```

## Monitoring

Monitor the OpenBB adapter through:
- Health endpoint: `http://localhost:8003/health`
- Prometheus metrics: `http://localhost:8003/metrics`
- Logs: Available in Docker logs or Loki

## Examples

### Example 1: Market Analysis Agent
```python
async def analyze_market_conditions(self):
    # Get multiple symbols
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN"]
    
    analyses = []
    for symbol in symbols:
        # Get market data
        data = await self.get_market_data(symbol, "1d")
        
        # Get technical indicators
        technicals = await self.get_technical_analysis(
            symbol,
            ["RSI", "MACD", "BB"]
        )
        
        analyses.append({
            "symbol": symbol,
            "price": data.get("last_price"),
            "change": data.get("change_24h"),
            "rsi": technicals.get("indicators", {}).get("RSI", {}).get("value"),
            "signal": technicals.get("overall_signal")
        })
    
    return analyses
```

### Example 2: Portfolio Optimization
```python
async def optimize_portfolio(self):
    # Current positions
    positions = [
        {"symbol": "AAPL", "quantity": 100, "cost_basis": 150},
        {"symbol": "GOOGL", "quantity": 50, "cost_basis": 2800},
        {"symbol": "MSFT", "quantity": 75, "cost_basis": 380}
    ]
    
    # Analyze current portfolio
    analysis = await self.analyze_portfolio(positions)
    
    # Check risk metrics
    if analysis["risk_analysis"]["volatility"] > 0.25:
        return {
            "action": "rebalance",
            "reason": "High volatility detected",
            "suggestions": analysis.get("recommendations", [])
        }
    
    return {"action": "hold", "metrics": analysis["metrics"]}
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure OpenBB adapter is running: `docker ps | grep openbb-adapter`
   - Check logs: `docker logs openbb-adapter`

2. **Cache Issues**
   - Clear Redis cache: `docker exec redis redis-cli FLUSHDB`
   - Adjust cache TTL in environment variables

3. **No Data Returned**
   - Verify symbol is valid
   - Check OpenBB service status
   - Review adapter logs for API errors

### Debug Mode

Enable debug logging for detailed information:
```bash
LOG_LEVEL=debug docker-compose up openbb-adapter
```

## Security Considerations

1. **API Keys**: OpenBB API keys should be stored securely as environment variables
2. **Network**: The adapter should only be accessible within the Docker network
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Data Validation**: All input is validated before processing

## Future Enhancements

Planned improvements for the OpenBB integration:
- Real-time WebSocket data feeds
- More asset classes (options, futures)
- Advanced portfolio optimization algorithms
- Machine learning model integration
- Custom indicator development framework