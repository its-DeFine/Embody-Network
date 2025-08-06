# Oracle Architecture - Central Market Data Oracle

## Overview

The system has been refactored to establish the **Manager** as the central oracle for all market data operations. This architecture provides:

- **Centralized API Key Management**: All market data API keys are managed exclusively by the Manager
- **Data Validation & Aggregation**: Multiple data sources are validated and aggregated for accuracy
- **Hybrid Oracle Model**: Off-chain data via Manager, on-chain data via Chainlink
- **Rate Limiting & Caching**: Intelligent rate limiting and caching to optimize API usage
- **High Availability**: Automatic failover between multiple data providers

## Architecture Components

### 1. Oracle Manager (Central Oracle)

The `OracleManager` class (`/app/core/oracle/oracle_manager.py`) serves as the single source of truth for all market data:

```
┌─────────────────────────────────────────────┐
│             Oracle Manager                  │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │     API Key Vault (Centralized)     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │    Data Validation & Aggregation    │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │     Rate Limiting & Caching         │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │      Provider Management             │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

#### Key Features:

- **Centralized API Keys**: All API keys stored and managed in one place
- **Data Consensus**: Requires multiple sources to agree on price data
- **Smart Caching**: Different TTLs for different data types
- **Rate Limit Management**: Tracks and enforces rate limits per provider
- **Automatic Failover**: Falls back to alternative providers when primary fails

### 2. Data Sources

#### Off-Chain Providers (Manager-Controlled)
- **Yahoo Finance**: Free, 2,000 requests/hour
- **Alpha Vantage**: 500 calls/day (API key required)
- **Twelve Data**: 800 calls/day (API key required)
- **Finnhub**: 86,400 calls/day (API key required)
- **MarketStack**: 1,000 calls/month (API key required)
- **CoinGecko**: Free tier for crypto data
- **Binance/Coinbase**: Public endpoints for crypto

#### On-Chain Providers (Chainlink)
- **Chainlink Price Feeds**: Direct blockchain reads
- **Multiple Networks**: Ethereum, Polygon, BSC, Avalanche, Arbitrum
- **Free Access**: Uses public RPC endpoints
- **Real-time Data**: Direct from smart contracts

### 3. Oracle Types

```python
class OracleType(Enum):
    OFFCHAIN = "offchain"  # Traditional APIs via Manager
    ONCHAIN = "onchain"    # Chainlink blockchain oracles
    HYBRID = "hybrid"      # Combination of both
```

### 4. API Endpoints

The Oracle Manager exposes RESTful endpoints at `/api/v1/oracle/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/oracle/price/{symbol}` | GET | Get current price with validation |
| `/oracle/quote/{symbol}` | GET | Get detailed quote information |
| `/oracle/historical/{symbol}` | GET | Get historical OHLCV data |
| `/oracle/health` | GET | Oracle system health status |
| `/oracle/api-keys/status` | GET | API key configuration status |
| `/oracle/api-keys/rotate` | POST | Rotate API keys securely |
| `/oracle/validate` | POST | Validate price data consistency |

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Client     │────▶│   Manager    │────▶│   Oracle     │
│  Component   │     │   (Router)   │     │   Manager    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                            ┌─────────────────────┼─────────────────────┐
                            │                     │                     │
                      ┌─────▼─────┐        ┌─────▼─────┐        ┌─────▼─────┐
                      │  Off-Chain │        │  On-Chain │        │   Cache   │
                      │  Providers │        │ Chainlink │        │   Redis   │
                      └───────────┘        └───────────┘        └───────────┘
```

### Request Flow:

1. **Client Request**: Component requests market data
2. **Cache Check**: Oracle checks Redis cache first
3. **Source Selection**: Determines best sources based on:
   - Symbol type (stock vs crypto)
   - Rate limits
   - Provider availability
4. **Data Fetching**: Queries multiple sources in parallel
5. **Validation**: Validates data consistency
6. **Aggregation**: Aggregates using median for robustness
7. **Caching**: Stores result in cache with TTL
8. **Response**: Returns validated, aggregated data

## Security Model

### API Key Protection

- **Environment Variables**: Keys loaded from secure environment
- **Key Masking**: API keys never exposed in logs or responses
- **Rotation Support**: Keys can be rotated without restart
- **Access Control**: Only authenticated users can manage keys

### Data Validation

```python
validation_config = {
    "max_price_deviation": 0.1,     # 10% max deviation
    "stale_data_threshold": 300,    # 5 minutes
    "min_sources_required": 2,      # Consensus requirement
}
```

## Testing Strategy

### Mock Provider Isolation

- **Production Code**: No mock providers in `/app/core/`
- **Test Mocks**: All mocks in `/tests/mocks/`
- **Environment Detection**: `ENVIRONMENT` variable controls mock loading
- **Test Safety**: Mocks raise error if used outside tests

### Test Structure

```
tests/
├── mocks/
│   └── market_data_mock.py    # Isolated mock provider
├── test_oracle_manager.py     # Oracle Manager tests
├── test_market_data.py        # Market data tests
└── test_integration.py        # Integration tests
```

## Migration Guide

### For Existing Deployments

1. **Update Environment Variables**:
```bash
# Set environment to production
export ENVIRONMENT=production

# Add API keys (if available)
export ALPHA_VANTAGE_API_KEY=your_key
export FINNHUB_API_KEY=your_key
export TWELVEDATA_API_KEY=your_key
```

2. **Update Service Dependencies**:
- Replace direct `market_data_service` calls with `oracle_manager`
- Use new `/oracle/` endpoints instead of `/market/`

3. **Testing**:
```bash
# Run tests with mock provider
export ENVIRONMENT=test
pytest tests/

# Run production without mocks
export ENVIRONMENT=production
python -m app.main
```

## Performance Characteristics

### Latency Targets

- **Cache Hit**: < 10ms
- **Single Provider**: < 200ms
- **Multi-Provider Consensus**: < 500ms
- **Chainlink Oracle**: < 300ms

### Throughput

- **Requests/Second**: 100+ (with caching)
- **Concurrent Symbols**: 50+
- **Cache Hit Rate**: > 80% (typical)

## Monitoring & Observability

### Health Metrics

```json
{
  "status": "healthy|degraded|critical",
  "providers": {
    "yahoo": {
      "available": true,
      "rate_limit_ok": true,
      "requests_made": 245
    }
  },
  "cache_connected": true,
  "api_keys_configured": 4
}
```

### Logging

- **Info Level**: API calls, cache hits/misses
- **Warning Level**: Rate limit approaching, provider failures
- **Error Level**: Complete provider failure, validation errors

## Future Enhancements

### Planned Features

1. **Machine Learning Price Prediction**: Use historical data for ML models
2. **Custom Oracle Aggregation**: User-defined aggregation strategies
3. **WebSocket Streaming**: Real-time price updates
4. **Decentralized Oracle Network**: Integration with multiple oracle protocols
5. **Advanced Caching**: Predictive cache warming
6. **Circuit Breakers**: Automatic provider isolation on failures

### Scalability Path

1. **Horizontal Scaling**: Multiple Oracle Manager instances
2. **Regional Deployment**: Geo-distributed oracles
3. **Provider Pools**: Dynamic provider allocation
4. **Edge Caching**: CDN integration for global distribution

## Compliance & Audit

### Data Governance

- **Audit Logging**: All oracle requests logged
- **Data Lineage**: Track data source for each response
- **Compliance Mode**: Restrict to approved providers only
- **Rate Limit Compliance**: Automatic enforcement

### Regulatory Considerations

- **Market Data Rights**: Respect provider terms of service
- **Data Accuracy**: Best-effort validation and consensus
- **Availability SLA**: 99.9% uptime target
- **Disaster Recovery**: Automatic failover capabilities

## Conclusion

The Oracle Manager architecture provides a robust, scalable, and secure solution for centralized market data management. By establishing the Manager as the central oracle, we achieve:

- **Single Source of Truth**: All market data flows through one validated channel
- **Enhanced Security**: Centralized API key management and validation
- **Improved Reliability**: Multiple providers with automatic failover
- **Cost Optimization**: Intelligent caching and rate limit management
- **Future-Proof Design**: Easy to add new providers and features

This architecture ensures that market data is accurate, reliable, and efficiently managed across the entire trading system.