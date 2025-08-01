# AutoGen Platform Architecture

## Core Concept: Orchestrated Agent Collaboration

This platform maintains the **central management hub logic** and **synergy between agents** through:

### 1. Central Orchestrator (`app/orchestrator.py`)
- **Event-driven architecture** - All agents communicate through events
- **Task routing** - Intelligently assigns tasks to the best available agent
- **Health monitoring** - Tracks agent status and reassigns tasks if needed
- **Workflow management** - Coordinates complex multi-agent workflows

### 2. Agent Communication Flow

```
User → API → Task Created → Orchestrator → Best Agent → Result → User
                                ↓
                          Other Agents
                          (via events)
```

### 3. Example: Trading Team Workflow

```python
# 1. Create agents
trading_agent = create_agent("trading", config={"risk_limit": 0.02})
analysis_agent = create_agent("analysis", config={"indicators": ["RSI", "MACD"]})
risk_agent = create_agent("risk", config={"max_exposure": 0.1})

# 2. Create team
team = create_team("Trading Team", [trading_agent, analysis_agent, risk_agent])

# 3. Coordinate consensus decision
coordinate_team(team.id, {
    "task_type": "consensus",
    "proposal": "Buy BTC at current price?"
})

# Orchestrator ensures all agents vote before proceeding
```

### 4. Event Types

- **Agent Events**: `agent.started`, `agent.stopped`, `agent.joined`
- **Task Events**: `task.created`, `task.completed`, `task.failed`
- **Team Events**: `team.coordinate`, `team.consensus`
- **Market Events**: `market.signal` (broadcast to all relevant agents)

### 5. Task Routing Intelligence

The orchestrator intelligently routes tasks:
- `analyze_market` → Analysis or Trading agents
- `execute_trade` → Trading agents only
- `assess_risk` → Risk or Trading agents
- `optimize_portfolio` → Portfolio or Risk agents

### 6. Inter-Agent Communication

Agents can trigger tasks for each other:
1. Analysis agent detects opportunity → Creates task for Trading agent
2. Trading agent executes → Triggers Risk agent for assessment
3. Risk agent alerts → Portfolio agent rebalances

### 7. Redis State Management

```
Redis Structure:
- agent:{id} - Agent configuration
- agent:{id}:status - Real-time status
- agent:{id}:tasks - Task queue
- task:{id} - Task details
- task:{id}:result - Task results
- team:{id} - Team configuration
- events:global - Global event queue
```

## Benefits of This Architecture

1. **Scalability** - Add more agents without changing core logic
2. **Reliability** - Failed agents don't break the system
3. **Flexibility** - Easy to add new agent types and workflows
4. **Observability** - Central hub tracks all activity
5. **Maintainability** - Clean separation of concerns

## Simple Yet Powerful

While the codebase is now simplified to ~20 files, it retains all the essential orchestration capabilities that make agents work together effectively. The complexity is in the logic, not in the file structure.