# Environment Configuration Guide - Oracle Architecture

## Overview

The system uses a **centralized Oracle architecture** where only the Manager node has market data API keys. All other nodes (orchestrators and agents) request market data through the Manager's Oracle API endpoints.

```
┌─────────────────────────────────────────────────────┐
│                   MANAGER NODE                       │
│              (Central Oracle + API Keys)             │
│                                                      │
│  • All market data API keys stored here             │
│  • Oracle Manager validates & aggregates data       │
│  • Provides /api/v1/oracle/* endpoints              │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────┐
        │                     │              │
┌───────▼──────┐    ┌────────▼──────┐   ┌───▼────┐
│ ORCHESTRATOR │    │ ORCHESTRATOR  │   │ AGENT  │
│   (No Keys)  │    │   (No Keys)   │   │(No Keys)│
│              │    │               │   │         │
│ Uses Oracle  │    │ Uses Oracle   │   │Uses API │
│   Client     │    │   Client      │   │ Client  │
└──────────────┘    └───────────────┘   └─────────┘
```

## Environment Files

### 1. Manager Node Configuration (`.env.manager`)

**Location**: Deploy on the central manager server only
**Purpose**: Contains ALL market data API keys and Oracle configuration
**Key Features**:
- All market data API keys (Finnhub, Alpha Vantage, etc.)
- Oracle Manager settings
- Chainlink RPC endpoints
- Master authentication secrets

```bash
# Only on Manager node
cp .env.manager .env
# Edit with your actual API keys and settings
nano .env
```

**Critical Settings**:
```env
# These ONLY go on the Manager
FINNHUB_API_KEY=your-actual-key
TWELVEDATA_API_KEY=your-actual-key
ALPHA_VANTAGE_API_KEY=your-actual-key
IS_CENTRAL_ORACLE=true
ORACLE_ENABLED=true
```

### 2. Orchestrator Node Configuration (`.env.orchestrator-clean`)

**Location**: Deploy on each orchestrator node
**Purpose**: Configuration WITHOUT any market data API keys
**Key Features**:
- Manager connection settings
- Oracle client configuration
- NO market data API keys

```bash
# On each orchestrator
cp .env.orchestrator-clean .env
# Edit with Manager connection details
nano .env
```

**Critical Settings**:
```env
# Connect to Manager's Oracle
MANAGER_ORACLE_URL=http://manager.domain.com:8000/api/v1/oracle
USE_CENTRAL_ORACLE=true
# NO API KEYS HERE!
# FINNHUB_API_KEY=      # DO NOT SET
# ALPHA_VANTAGE_API_KEY= # DO NOT SET
```

### 3. Agent Node Configuration (`.env.agent`)

**Location**: Deploy on trading agent nodes
**Purpose**: Minimal configuration for agents
**Key Features**:
- Manager/Orchestrator connection
- Trading parameters
- NO API keys whatsoever

```bash
# On each agent
cp .env.agent .env
nano .env
```

## Migration from Old Setup

### Step 1: Identify Current Setup
```bash
# Check if you have API keys in multiple places
grep -r "FINNHUB_API_KEY\|ALPHA_VANTAGE_API_KEY" .env*
```

### Step 2: Consolidate Keys to Manager
1. Copy all API keys to `.env.manager`
2. Remove API keys from orchestrator/agent configs
3. Update connection URLs

### Step 3: Update Services

**On Manager**:
```bash
# Ensure Oracle endpoints are enabled
export ORACLE_ENABLED=true
export IS_CENTRAL_ORACLE=true
docker-compose restart manager
```

**On Orchestrators**:
```bash
# Point to Manager's Oracle
export USE_CENTRAL_ORACLE=true
export MANAGER_ORACLE_URL=http://manager-ip:8000/api/v1/oracle
# Remove any local API keys
unset FINNHUB_API_KEY
unset ALPHA_VANTAGE_API_KEY
docker-compose restart orchestrator
```

## API Key Security

### Best Practices

1. **Never commit API keys**
   ```bash
   # Add to .gitignore
   echo ".env*" >> .gitignore
   git rm --cached .env*
   ```

2. **Use secrets management**
   ```bash
   # For production, use Docker secrets
   docker secret create finnhub_key key.txt
   ```

3. **Rotate keys regularly**
   ```bash
   # Use the Oracle API to rotate keys
   curl -X POST http://manager:8000/api/v1/oracle/api-keys/rotate \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"source": "finnhub", "new_key": "new-key-here"}'
   ```

## Verification

### Check Manager Oracle Status
```bash
# From any node, check if Oracle is accessible
curl http://manager:8000/api/v1/oracle/health

# Expected response:
{
  "status": "healthy",
  "providers": {
    "finnhub": {"available": true, "rate_limit_ok": true},
    "yahoo": {"available": true, "rate_limit_ok": true}
  },
  "api_keys_configured": 4
}
```

### Test Price Request from Orchestrator
```bash
# On orchestrator, test Oracle client
curl http://manager:8000/api/v1/oracle/price/AAPL

# Should return price without needing local API keys
{
  "symbol": "AAPL",
  "price": 185.50,
  "validated": true,
  "sources_succeeded": ["yahoo", "finnhub"]
}
```

### Verify No Keys on Orchestrator
```bash
# On orchestrator node
env | grep -E "FINNHUB|ALPHA_VANTAGE|TWELVEDATA"
# Should return empty - no API keys
```

## Environment Variables Reference

### Manager-Only Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `FINNHUB_API_KEY` | Finnhub API key | `ct7n9n9r01q...` |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage key | `DEMO123...` |
| `TWELVEDATA_API_KEY` | Twelve Data key | `abc123...` |
| `MARKETSTACK_API_KEY` | MarketStack key | `xyz789...` |
| `IS_CENTRAL_ORACLE` | Enable Oracle role | `true` |
| `ORACLE_ENABLED` | Enable Oracle API | `true` |

### Orchestrator/Agent Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `USE_CENTRAL_ORACLE` | Use Manager's Oracle | `true` |
| `MANAGER_ORACLE_URL` | Oracle API endpoint | `http://manager:8000/api/v1/oracle` |
| `ORACLE_REQUEST_TIMEOUT` | Request timeout (s) | `30` |
| `ORACLE_CACHE_LOCAL` | Enable local cache | `true` |

## Troubleshooting

### Issue: Orchestrator can't get market data
```bash
# Check Oracle connectivity
curl -v http://manager:8000/api/v1/oracle/health

# Verify environment
env | grep ORACLE

# Check logs
docker logs orchestrator | grep -i oracle
```

### Issue: "No API key configured" errors
```bash
# On Manager, verify keys are loaded
docker exec manager env | grep API_KEY

# Check Oracle Manager status
curl http://manager:8000/api/v1/oracle/api-keys/status
```

### Issue: Rate limiting errors
```bash
# Check rate limit status
curl http://manager:8000/api/v1/oracle/health | jq .providers

# Oracle Manager handles rate limiting centrally
# Reduces limits across all nodes automatically
```

## Production Deployment

### 1. Secure the Manager
```yaml
# docker-compose.yml for Manager
services:
  manager:
    env_file: .env.manager
    environment:
      - ENVIRONMENT=production
      - IS_CENTRAL_ORACLE=true
    secrets:
      - finnhub_key
      - alpha_vantage_key
```

### 2. Deploy Orchestrators
```yaml
# docker-compose.yml for Orchestrator
services:
  orchestrator:
    env_file: .env.orchestrator-clean
    environment:
      - USE_CENTRAL_ORACLE=true
      - MANAGER_ORACLE_URL=${MANAGER_URL}/api/v1/oracle
    # NO api key secrets needed!
```

### 3. Scale Agents
```bash
# Agents only need Oracle client config
docker service create \
  --name trading-agent \
  --env USE_CENTRAL_ORACLE=true \
  --env MANAGER_ORACLE_URL=http://manager:8000/api/v1/oracle \
  --replicas 10 \
  trading-agent:latest
```

## Monitoring

### Oracle Metrics
- Request count per provider
- Cache hit ratio
- Rate limit usage
- Validation failures
- Provider availability

### Alerts to Configure
```yaml
# Alert when approaching rate limits
- alert: OracleRateLimitWarning
  expr: oracle_rate_limit_remaining < 100
  
# Alert on provider failures
- alert: OracleProviderDown
  expr: oracle_provider_available == 0
```

## Summary

The Oracle Architecture ensures:
1. **Security**: API keys only on Manager node
2. **Efficiency**: Centralized rate limiting and caching
3. **Reliability**: Automatic failover between providers
4. **Scalability**: Add orchestrators/agents without API keys
5. **Compliance**: Centralized audit trail for market data access

Always remember: **Only the Manager has API keys!**