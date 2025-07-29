# Event-Driven Adaptive Trading System Specifications

## Overview
A clean, modular trading system that responds to time-based and API events to execute trades adaptively.

## Core Requirements

### 1. Event System
- **Time-based events**: Execute actions every X seconds (configurable)
- **API-triggered events**: Monitor external APIs for specific conditions
- **Custom events**: Agent can schedule its own events dynamically

### 2. Trading Agent
- Single, focused agent that handles all trading logic
- Minimal dependencies (no complex AI frameworks)
- Clear separation of concerns
- Readable by both engineers and LLMs

### 3. Event Types

#### 3.1 Periodic Events
```yaml
periodic_events:
  - name: "market_scan"
    interval: 30  # seconds
    action: "scan_and_trade"
  
  - name: "position_check"
    interval: 10
    action: "monitor_positions"
```

#### 3.2 API Monitor Events
```yaml
api_events:
  - name: "price_spike"
    endpoint: "https://api.coingecko.com/api/v3/simple/price"
    condition: "price_change > 5%"
    action: "execute_momentum_trade"
  
  - name: "volume_surge"
    endpoint: "https://api.exchange.com/volume"
    condition: "volume > 2x_average"
    action: "execute_volume_trade"
```

#### 3.3 Dynamic Events
- Agent can create events based on market conditions
- Example: After opening position, schedule check in 5 minutes

## Architecture Components

### 1. Event Loop (Core)
```python
class EventLoop:
    - Manages all event scheduling
    - Checks API conditions
    - Triggers appropriate handlers
    - Non-blocking, async design
```

### 2. Event Handlers
```python
class EventHandler:
    - One handler per event type
    - Clean interface: handle(event_data)
    - Returns actions to execute
```

### 3. Trading Engine
```python
class TradingEngine:
    - Executes trades based on events
    - Manages positions
    - Risk management
    - Simple paper trading
```

### 4. API Monitor
```python
class APIMonitor:
    - Polls configured endpoints
    - Evaluates conditions
    - Triggers events when conditions met
```

## Data Flow

1. **Event Loop** continuously runs
2. Checks **time-based triggers**
3. Polls **API endpoints** for conditions
4. When event fires → calls **Event Handler**
5. Handler analyzes data → returns **Trading Decision**
6. **Trading Engine** executes decision
7. Engine can schedule **new events** dynamically

## Configuration

### config.yaml
```yaml
system:
  loop_interval: 1  # Main loop runs every 1 second
  
trading:
  starting_balance: 100
  max_positions: 5
  position_size: 20%  # of available balance
  
events:
  periodic:
    - market_scan: 30s
    - position_monitor: 10s
    - performance_check: 300s
    
  api_monitors:
    - endpoint: "coingecko"
      tokens: ["BTC", "ETH", "ARB"]
      conditions:
        - price_change_1h: "> 3%"
        - volume_change: "> 50%"
```

## Key Design Principles

1. **Simplicity**: No unnecessary complexity
2. **Modularity**: Each component has single responsibility
3. **Readability**: Clear variable names, documented functions
4. **Extensibility**: Easy to add new event types or handlers
5. **Reliability**: Graceful error handling, no crashes

## Minimal Dependencies
- aiohttp: For async HTTP requests
- pyyaml: For configuration
- Standard library for everything else

## File Structure
```
event-driven-trader/
├── config.yaml          # All configuration
├── src/
│   ├── __init__.py
│   ├── event_loop.py    # Main event loop
│   ├── events.py        # Event definitions
│   ├── handlers.py      # Event handlers
│   ├── trading.py       # Trading engine
│   ├── monitor.py       # API monitor
│   └── utils.py         # Helper functions
├── tests/              # Unit tests
└── run.py              # Entry point
```