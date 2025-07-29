# AutoGen Platform - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Creating Your First Agent](#creating-your-first-agent)
3. [Managing Agents](#managing-agents)
4. [Running Tasks](#running-tasks)
5. [Team Collaboration](#team-collaboration)
6. [API Examples](#api-examples)
7. [Use Cases](#use-cases)

## Getting Started

### 1. Create an Account

First, register as a customer:

```bash
curl -X POST http://localhost:8000/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ACME Corp",
    "email": "admin@acme.com"
  }'
```

Response:
```json
{
  "customer_id": "cust_123abc",
  "api_key": "sk_live_abc123...",
  "message": "Customer created successfully"
}
```

### 2. Authenticate

Use your API key to get a JWT token:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "api_key": "sk_live_abc123..."
  }'
```

Response:
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 3. Set Authorization Header

For all subsequent requests:
```bash
export TOKEN="eyJhbG..."
```

## Creating Your First Agent

### Trading Agent Example

```bash
curl -X POST http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BTC Trading Bot",
    "agent_type": "trading",
    "config": {
      "exchange": "binance",
      "trading_pairs": ["BTC/USDT", "ETH/USDT"],
      "risk_limit": 0.02,
      "strategy": "momentum"
    },
    "autogen_config": {
      "temperature": 0.7,
      "max_consecutive_auto_reply": 10,
      "system_message": "You are a professional crypto trader focused on momentum strategies."
    }
  }'
```

### Analysis Agent Example

```bash
curl -X POST http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Market Analyzer",
    "agent_type": "analysis",
    "config": {
      "analysis_types": ["technical", "sentiment", "fundamental"],
      "data_sources": ["coingecko", "newsapi", "twitter"],
      "update_frequency": "hourly"
    },
    "autogen_config": {
      "temperature": 0.5,
      "system_message": "You are a market analysis expert providing actionable insights."
    }
  }'
```

### Risk Management Agent

```bash
curl -X POST http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Risk Guardian",
    "agent_type": "risk_management",
    "config": {
      "max_portfolio_risk": 0.06,
      "max_position_size": 0.1,
      "stop_loss_percentage": 0.05,
      "risk_metrics": ["var", "sharpe", "sortino"]
    }
  }'
```

## Managing Agents

### List Your Agents

```bash
curl -X GET http://localhost:8000/agents \
  -H "Authorization: Bearer $TOKEN"
```

### Get Agent Details

```bash
curl -X GET http://localhost:8000/agents/{agent_id} \
  -H "Authorization: Bearer $TOKEN"
```

### Update Agent Configuration

```bash
curl -X PUT http://localhost:8000/agents/{agent_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "risk_limit": 0.01
    }
  }'
```

### Start/Stop Agent

```bash
# Start agent
curl -X POST http://localhost:8000/agents/{agent_id}/start \
  -H "Authorization: Bearer $TOKEN"

# Stop agent
curl -X POST http://localhost:8000/agents/{agent_id}/stop \
  -H "Authorization: Bearer $TOKEN"
```

### Delete Agent

```bash
curl -X DELETE http://localhost:8000/agents/{agent_id} \
  -H "Authorization: Bearer $TOKEN"
```

## Running Tasks

### Create a Task

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_123",
    "type": "analyze_market",
    "parameters": {
      "symbol": "BTC/USDT",
      "timeframe": "4h",
      "indicators": ["RSI", "MACD", "Volume"]
    }
  }'
```

### Task Types

#### Trading Tasks
```json
{
  "type": "execute_trade",
  "parameters": {
    "action": "buy",
    "symbol": "BTC/USDT",
    "amount": 0.01,
    "strategy": "dca"
  }
}
```

#### Analysis Tasks
```json
{
  "type": "market_analysis",
  "parameters": {
    "symbols": ["BTC/USDT", "ETH/USDT"],
    "analysis_depth": "comprehensive",
    "include_predictions": true
  }
}
```

#### Risk Assessment
```json
{
  "type": "portfolio_risk_check",
  "parameters": {
    "include_stress_test": true,
    "scenarios": ["market_crash", "high_volatility"]
  }
}
```

### Monitor Task Status

```bash
# Get task status
curl -X GET http://localhost:8000/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN"

# List all tasks
curl -X GET http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN"
```

## Team Collaboration

### Create a Team

```bash
curl -X POST http://localhost:8000/teams \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alpha Trading Team",
    "description": "Multi-strategy trading team",
    "agent_ids": ["agent_123", "agent_456", "agent_789"],
    "orchestrator_config": {
      "strategy": "round_robin",
      "consensus_required": true,
      "min_consensus_threshold": 0.66
    }
  }'
```

### Team Task Execution

```bash
curl -X POST http://localhost:8000/teams/{team_id}/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "collaborative_analysis",
    "parameters": {
      "objective": "Identify best trading opportunity",
      "timeframe": "next_24h",
      "risk_tolerance": "moderate"
    }
  }'
```

## API Examples

### Python Client Example

```python
import requests
import json

class AutoGenClient:
    def __init__(self, base_url, api_key, email):
        self.base_url = base_url
        self.api_key = api_key
        self.email = email
        self.token = None
        self.authenticate()
    
    def authenticate(self):
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": self.email, "api_key": self.api_key}
        )
        self.token = response.json()["access_token"]
    
    def create_agent(self, name, agent_type, config):
        return requests.post(
            f"{self.base_url}/agents",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "name": name,
                "agent_type": agent_type,
                "config": config
            }
        ).json()
    
    def run_task(self, agent_id, task_type, parameters):
        return requests.post(
            f"{self.base_url}/tasks",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "agent_id": agent_id,
                "type": task_type,
                "parameters": parameters
            }
        ).json()

# Usage
client = AutoGenClient(
    "http://localhost:8000",
    "sk_live_abc123...",
    "admin@acme.com"
)

# Create trading agent
agent = client.create_agent(
    "BTC Trader",
    "trading",
    {"exchange": "binance", "trading_pairs": ["BTC/USDT"]}
)

# Run analysis task
task = client.run_task(
    agent["agent_id"],
    "analyze_market",
    {"symbol": "BTC/USDT"}
)
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

class AutoGenClient {
    constructor(baseUrl, apiKey, email) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.email = email;
        this.token = null;
    }
    
    async authenticate() {
        const response = await axios.post(`${this.baseUrl}/auth/login`, {
            email: this.email,
            api_key: this.apiKey
        });
        this.token = response.data.access_token;
    }
    
    async createAgent(name, agentType, config) {
        const response = await axios.post(
            `${this.baseUrl}/agents`,
            {
                name: name,
                agent_type: agentType,
                config: config
            },
            {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            }
        );
        return response.data;
    }
}

// Usage
const client = new AutoGenClient(
    'http://localhost:8000',
    'sk_live_abc123...',
    'admin@acme.com'
);

await client.authenticate();
const agent = await client.createAgent(
    'BTC Trader',
    'trading',
    { exchange: 'binance', trading_pairs: ['BTC/USDT'] }
);
```

## Use Cases

### 1. Automated Trading System

```bash
# 1. Create specialized agents
# Trading executor
curl -X POST http://localhost:8000/agents -H "Authorization: Bearer $TOKEN" -d '{
  "name": "Trade Executor",
  "agent_type": "trading",
  "config": {"exchange": "binance", "execution_style": "aggressive"}
}'

# Market analyzer  
curl -X POST http://localhost:8000/agents -H "Authorization: Bearer $TOKEN" -d '{
  "name": "Market Scanner", 
  "agent_type": "analysis",
  "config": {"scan_interval": 300, "pattern_detection": true}
}'

# Risk manager
curl -X POST http://localhost:8000/agents -H "Authorization: Bearer $TOKEN" -d '{
  "name": "Risk Controller",
  "agent_type": "risk_management", 
  "config": {"max_drawdown": 0.1, "position_sizing": "kelly"}
}'

# 2. Create trading team
curl -X POST http://localhost:8000/teams -H "Authorization: Bearer $TOKEN" -d '{
  "name": "Algo Trading Team",
  "agent_ids": ["agent_1", "agent_2", "agent_3"]
}'

# 3. Execute collaborative trading
curl -X POST http://localhost:8000/teams/{team_id}/tasks -H "Authorization: Bearer $TOKEN" -d '{
  "type": "execute_trading_strategy",
  "parameters": {"strategy": "momentum", "capital": 10000}
}'
```

### 2. Portfolio Management

```bash
# Create portfolio optimization agent
curl -X POST http://localhost:8000/agents -H "Authorization: Bearer $TOKEN" -d '{
  "name": "Portfolio Optimizer",
  "agent_type": "portfolio_optimization",
  "config": {
    "optimization_method": "mean_variance",
    "rebalance_frequency": "weekly",
    "constraints": {
      "min_weight": 0.05,
      "max_weight": 0.30,
      "max_assets": 10
    }
  }
}'

# Run optimization
curl -X POST http://localhost:8000/tasks -H "Authorization: Bearer $TOKEN" -d '{
  "agent_id": "portfolio_agent_id",
  "type": "optimize_portfolio",
  "parameters": {
    "target_return": 0.15,
    "risk_tolerance": "moderate"
  }
}'
```

### 3. Real-time Market Monitoring

```bash
# Create monitoring agent
curl -X POST http://localhost:8000/agents -H "Authorization: Bearer $TOKEN" -d '{
  "name": "Market Monitor",
  "agent_type": "analysis",
  "config": {
    "monitoring_mode": "realtime",
    "alert_conditions": [
      {"type": "price_change", "threshold": 0.05},
      {"type": "volume_spike", "multiplier": 3},
      {"type": "pattern", "patterns": ["breakout", "reversal"]}
    ]
  }
}'

# Subscribe to alerts via WebSocket
wscat -c ws://localhost:8000/ws \
  -H "Authorization: Bearer $TOKEN" \
  -x '{"action": "subscribe", "channel": "alerts"}'
```

## Best Practices

### 1. Agent Configuration
- Start with conservative risk limits
- Test strategies with small amounts first
- Use appropriate temperature settings for LLMs
- Implement proper error handling

### 2. Task Management
- Break complex operations into smaller tasks
- Use task priorities for time-sensitive operations
- Monitor task completion rates
- Implement retry logic for failed tasks

### 3. Team Coordination
- Define clear roles for each agent
- Use consensus mechanisms for critical decisions
- Implement fallback strategies
- Monitor team performance metrics

### 4. Security
- Rotate API keys regularly
- Use environment variables for sensitive data
- Implement IP whitelisting for production
- Monitor for unusual activity

## Troubleshooting

### Common Issues

1. **Agent Not Responding**
   - Check agent status: `GET /agents/{id}/status`
   - View agent logs: `GET /agents/{id}/logs`
   - Restart agent: `POST /agents/{id}/restart`

2. **Task Failures**
   - Check task details: `GET /tasks/{id}`
   - View error messages in response
   - Verify agent has required permissions

3. **Authentication Errors**
   - Ensure token hasn't expired
   - Verify API key is correct
   - Check customer account status

### Support Resources

- API Documentation: http://localhost:8000/docs
- System Status: http://localhost:8000/status
- Metrics Dashboard: http://localhost:3000
- Contact Support: support@autogen-platform.com