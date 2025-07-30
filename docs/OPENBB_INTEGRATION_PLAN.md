# OpenBB Integration Plan for AutoGen Platform

## Executive Summary

This plan outlines the integration of OpenBB (Open Source Investment Research Terminal) into the AutoGen platform to provide comprehensive financial data and analysis capabilities for AI agents.

## 🎯 Integration Objectives

1. **Enhanced Data Access**: Provide agents with 700+ financial data sources
2. **Professional Analysis**: Enable institutional-grade financial analysis
3. **Unified Interface**: Single API for all financial data needs
4. **Real-time Capabilities**: Support live trading decisions
5. **Cost Efficiency**: Reduce external API costs through OpenBB's aggregation

## 📋 Implementation Plan

### Phase 1: Service Architecture (Week 1)

#### 1.1 Create OpenBB Adapter Service

**Location**: `/services/openbb-adapter/`

**Architecture**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Agents    │────▶│   OpenBB    │────▶│   OpenBB    │
│             │     │   Adapter   │     │   Platform  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  RabbitMQ   │
                    │  (Events)   │
                    └─────────────┘
```

#### 1.2 Service Structure

```
services/openbb-adapter/
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py
├── models/
│   ├── __init__.py
│   ├── market_data.py
│   ├── analysis.py
│   └── portfolio.py
├── handlers/
│   ├── __init__.py
│   ├── equity_handler.py
│   ├── crypto_handler.py
│   ├── economy_handler.py
│   └── portfolio_handler.py
├── cache/
│   └── redis_cache.py
└── tests/
    └── test_openbb_adapter.py
```

### Phase 2: Core Implementation (Week 2)

#### 2.1 Base Service Implementation

```python
# services/openbb-adapter/main.py
from fastapi import FastAPI, HTTPException
from openbb import obb
import asyncio
from typing import Dict, Any, Optional
import redis.asyncio as redis
from datetime import datetime, timedelta

app = FastAPI(title="OpenBB Adapter Service")

class OpenBBService:
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = 300  # 5 minutes default
        
    async def startup(self):
        # Initialize OpenBB
        obb.account.login(api_key=os.getenv("OPENBB_API_KEY"))
        
        # Connect to Redis for caching
        self.redis_client = await redis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379")
        )
        
    async def get_market_data(
        self, 
        symbol: str, 
        interval: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get historical market data with caching"""
        cache_key = f"market:{symbol}:{interval}:{start_date}:{end_date}"
        
        # Check cache
        cached = await self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Fetch from OpenBB
        data = obb.equity.price.historical(
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date
        )
        
        # Cache result
        await self.redis_client.setex(
            cache_key, 
            self.cache_ttl,
            json.dumps(data.to_dict())
        )
        
        return data.to_dict()
```

#### 2.2 Event-Driven Integration

```python
# services/openbb-adapter/handlers/market_events.py
import aio_pika
from typing import Dict, Any

class MarketDataHandler:
    def __init__(self, openbb_service: OpenBBService):
        self.service = openbb_service
        self.connection = None
        self.channel = None
        
    async def connect(self):
        self.connection = await aio_pika.connect_robust(
            os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
        )
        self.channel = await self.connection.channel()
        
        # Declare exchange
        self.exchange = await self.channel.declare_exchange(
            "openbb_events",
            aio_pika.ExchangeType.TOPIC
        )
        
        # Set up consumer
        queue = await self.channel.declare_queue("openbb_requests")
        await queue.bind(self.exchange, "data.request.*")
        await queue.consume(self.handle_request)
        
    async def handle_request(self, message: aio_pika.IncomingMessage):
        async with message.process():
            request = json.loads(message.body)
            
            if request["type"] == "market_data":
                data = await self.service.get_market_data(**request["params"])
                await self.publish_response(request["correlation_id"], data)
```

### Phase 3: Agent Integration (Week 3)

#### 3.1 Update Base Agent Class

```python
# agents/base/agent.py
from typing import Optional
import httpx

class BaseAgent:
    def __init__(self, config: dict):
        self.config = config
        self.openbb_client = httpx.AsyncClient(
            base_url="http://openbb-adapter:8003"
        )
        
    async def get_market_data(self, symbol: str, **kwargs):
        """Get market data through OpenBB adapter"""
        response = await self.openbb_client.post(
            "/market/data",
            json={"symbol": symbol, **kwargs}
        )
        return response.json()
        
    async def get_analysis(self, symbol: str, indicators: list):
        """Get technical analysis through OpenBB"""
        response = await self.openbb_client.post(
            "/analysis/technical",
            json={"symbol": symbol, "indicators": indicators}
        )
        return response.json()
```

#### 3.2 Enhanced Trading Agent

```python
# agents/agent_types/trading_agent.py
class TradingAgent(BaseAgent):
    async def analyze_opportunity(self, symbol: str):
        # Get comprehensive data from OpenBB
        market_data = await self.get_market_data(symbol)
        
        # Get multiple technical indicators
        analysis = await self.get_analysis(
            symbol,
            indicators=["rsi", "macd", "bollinger", "sma", "ema"]
        )
        
        # Get fundamental data
        fundamentals = await self.get_fundamentals(symbol)
        
        # Get news sentiment
        sentiment = await self.get_sentiment(symbol)
        
        # Make informed decision
        signal = self.generate_trading_signal(
            market_data, analysis, fundamentals, sentiment
        )
        
        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": signal.confidence,
            "analysis": {
                "technical": analysis,
                "fundamental": fundamentals,
                "sentiment": sentiment
            }
        }
```

### Phase 4: Enhanced Features (Week 4)

#### 4.1 Portfolio Management Integration

```python
# services/openbb-adapter/handlers/portfolio_handler.py
class PortfolioHandler:
    async def analyze_portfolio(self, holdings: list) -> Dict[str, Any]:
        """Comprehensive portfolio analysis"""
        # Get portfolio metrics
        metrics = obb.portfolio.metrics(holdings)
        
        # Risk analysis
        risk = obb.portfolio.risk.var(holdings, confidence=0.95)
        sharpe = obb.portfolio.risk.sharpe(holdings)
        
        # Optimization suggestions
        optimal = obb.portfolio.optimize(
            holdings,
            objective="sharpe",
            constraints={"min_weight": 0.05, "max_weight": 0.4}
        )
        
        return {
            "current_metrics": metrics,
            "risk_analysis": {
                "var_95": risk,
                "sharpe_ratio": sharpe
            },
            "optimization": optimal
        }
```

#### 4.2 Real-time Data Streaming

```python
# services/openbb-adapter/streaming.py
class MarketDataStreamer:
    def __init__(self):
        self.websocket_clients = set()
        
    async def stream_prices(self, symbols: list):
        """Stream real-time prices to connected agents"""
        while True:
            for symbol in symbols:
                try:
                    price = obb.equity.price.quote(symbol)
                    await self.broadcast({
                        "type": "price_update",
                        "symbol": symbol,
                        "data": price.to_dict(),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error streaming {symbol}: {e}")
            
            await asyncio.sleep(1)  # 1 second updates
```

### Phase 5: Testing & Deployment (Week 5)

#### 5.1 Integration Tests

```python
# tests/integration/test_openbb_integration.py
import pytest
import httpx

@pytest.mark.asyncio
async def test_market_data_retrieval():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8003/market/data",
            json={"symbol": "AAPL", "interval": "1d"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "prices" in data
        assert len(data["prices"]) > 0

@pytest.mark.asyncio
async def test_technical_analysis():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8003/analysis/technical",
            json={
                "symbol": "AAPL",
                "indicators": ["rsi", "macd"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "rsi" in data
        assert "macd" in data
```

#### 5.2 Docker Integration

```yaml
# Addition to docker-compose.yml
  openbb-adapter:
    build:
      context: ./services/openbb-adapter
      dockerfile: Dockerfile
    container_name: openbb-adapter
    ports:
      - "8003:8003"
    environment:
      - OPENBB_API_KEY=${OPENBB_API_KEY}
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - POLYGON_API_KEY=${POLYGON_API_KEY}
      - FRED_API_KEY=${FRED_API_KEY}
      - NEWS_API_KEY=${NEWS_API_KEY}
    depends_on:
      - redis
      - rabbitmq
    networks:
      - autogen-network
    volumes:
      - ./shared:/app/shared:ro
    restart: unless-stopped
```

### Phase 6: Documentation & Training (Week 6)

#### 6.1 API Documentation

Create comprehensive API documentation:
- Endpoint specifications
- Data models
- Usage examples
- Rate limiting guidelines

#### 6.2 Agent Developer Guide

```markdown
# Using OpenBB in Your Agents

## Quick Start

```python
# In your agent
data = await self.get_market_data("AAPL")
analysis = await self.get_analysis("AAPL", ["rsi", "macd"])
```

## Available Data Types

1. **Market Data**
   - Historical prices
   - Real-time quotes
   - Options chains
   - Crypto prices

2. **Technical Analysis**
   - 100+ indicators
   - Chart patterns
   - Backtesting

3. **Fundamental Data**
   - Financial statements
   - Ratios
   - Earnings
   - Insider trading

4. **Alternative Data**
   - News sentiment
   - Social media
   - Economic indicators
```

## 📊 Performance Considerations

1. **Caching Strategy**
   - 5-minute cache for market data
   - 1-hour cache for fundamentals
   - No cache for real-time data

2. **Rate Limiting**
   - Implement per-API limits
   - Queue requests during high load
   - Fallback to cached data

3. **Cost Optimization**
   - Use free tiers where possible
   - Batch requests
   - Share data between agents

## 🚀 Rollout Plan

### Week 1-2: Development
- Set up OpenBB adapter service
- Implement core functionality
- Basic testing

### Week 3-4: Integration
- Update agents to use OpenBB
- Test with existing workflows
- Performance optimization

### Week 5: Testing
- Comprehensive integration tests
- Load testing
- Security audit

### Week 6: Deployment
- Production deployment
- Documentation completion
- Team training

## 📈 Success Metrics

1. **Data Quality**
   - 99.9% uptime
   - <100ms latency for cached data
   - <1s for fresh data

2. **Agent Performance**
   - 50% better trading decisions
   - 3x more data sources
   - 80% reduction in data costs

3. **Developer Experience**
   - Single API for all data
   - Comprehensive documentation
   - Easy integration

## 🎯 Deliverables

1. **OpenBB Adapter Service** - Fully functional microservice
2. **Updated Agents** - All agents using OpenBB
3. **Documentation** - Complete integration guide
4. **Tests** - Comprehensive test suite
5. **Monitoring** - Dashboard for OpenBB usage

## Next Steps

1. Review and approve plan
2. Set up OpenBB API keys
3. Begin Phase 1 implementation
4. Weekly progress reviews

---

**Estimated Timeline**: 6 weeks  
**Estimated Effort**: 2 developers  
**Priority**: High  
**ROI**: High (better data = better trading)