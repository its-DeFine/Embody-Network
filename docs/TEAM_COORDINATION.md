# Team Coordination Guide

Learn how to create and manage teams of agents that work together to solve complex tasks.

## 👥 Understanding Teams

Teams are groups of agents that:
- Collaborate on complex objectives
- Share information and context
- Coordinate task execution
- Leverage specialized skills

## 🏗️ Team Architecture

### Team Components
1. **Coordinator**: Orchestrates team activities
2. **Agents**: Specialized team members
3. **Communication Channel**: Message passing
4. **Shared Context**: Team memory/state

### Communication Patterns
```
Objective -> Coordinator -> Agent Assignment
                         -> Task Distribution
                         -> Result Aggregation
                         -> Final Output
```

## 📝 Creating Teams

### Basic Team
```json
{
  "name": "Market Analysis Team",
  "description": "Analyzes market trends and opportunities",
  "agent_ids": ["agent-1", "agent-2", "agent-3"]
}
```

### Advanced Team Configuration
```json
{
  "name": "Trading Strategy Team",
  "description": "Develops and executes trading strategies",
  "agent_ids": ["trader-1", "analyst-1", "risk-1"],
  "config": {
    "coordination_strategy": "consensus",
    "communication_protocol": "async",
    "decision_threshold": 0.7,
    "max_iterations": 5
  }
}
```

## 🎯 Coordination Strategies

### Sequential Coordination
Agents work in a defined order:
```
Data Collector -> Analyzer -> Decision Maker -> Executor
```

**Use Cases**:
- Pipeline processing
- Staged workflows
- Quality gates

### Parallel Coordination
Agents work simultaneously:
```
       ┌─> Analyst 1 ─┐
Task ──┼─> Analyst 2 ──┼─> Aggregator
       └─> Analyst 3 ─┘
```

**Use Cases**:
- Multiple perspectives
- Speed optimization
- Redundancy

### Hierarchical Coordination
Manager agent delegates to workers:
```
         Manager
        /   |   \
   Worker1 Worker2 Worker3
```

**Use Cases**:
- Complex projects
- Resource allocation
- Task distribution

### Consensus Coordination
Agents vote on decisions:
```
Agent1 ─┐
Agent2 ──┼─> Voting ─> Decision
Agent3 ─┘
```

**Use Cases**:
- Risk assessment
- Strategy selection
- Quality assurance

## 🚀 Sending Tasks to Teams

### Simple Task
```bash
curl -X POST http://localhost:8000/api/v1/teams/{team_id}/coordinate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Analyze AAPL stock for investment",
    "context": {}
  }'
```

### Complex Task
```json
{
  "objective": "Develop trading strategy for tech sector",
  "context": {
    "timeframe": "3 months",
    "risk_tolerance": "moderate",
    "capital": 100000,
    "constraints": ["no options", "US markets only"]
  },
  "config": {
    "timeout": 600,
    "require_consensus": true,
    "min_confidence": 0.8
  }
}
```

## 📊 Team Patterns

### Research Team
```
Team: Market Research
├── Data Collector Agent
├── Technical Analyst Agent
├── Fundamental Analyst Agent
└── Report Generator Agent
```

**Workflow**:
1. Collector gathers market data
2. Analysts process in parallel
3. Generator creates unified report

### Trading Team
```
Team: Algorithmic Trading
├── Signal Generator Agent
├── Risk Analyzer Agent
├── Position Sizer Agent
└── Order Executor Agent
```

**Workflow**:
1. Signal identifies opportunity
2. Risk evaluates safety
3. Sizer calculates position
4. Executor places trades

### Analysis Team
```
Team: Comprehensive Analysis
├── Quantitative Analyst Agent
├── Sentiment Analyst Agent
├── News Analyst Agent
└── Synthesis Agent
```

**Workflow**:
1. Parallel analysis from different angles
2. Synthesis combines insights
3. Produces holistic view

## 🔄 Team Communication

### Message Types
1. **Task Assignment**: Coordinator to agent
2. **Status Update**: Agent progress reports
3. **Result Submission**: Agent completions
4. **Information Request**: Inter-agent queries
5. **Context Sharing**: Knowledge distribution

### Communication Protocols

**Synchronous**
```python
# All agents must respond before proceeding
results = await team.coordinate_sync(task)
```

**Asynchronous**
```python
# Agents work independently
async for result in team.coordinate_async(task):
    process(result)
```

**Streaming**
```python
# Real-time updates
async for update in team.coordinate_stream(task):
    handle_update(update)
```

## 📈 Team Performance

### Metrics
- **Completion Time**: End-to-end duration
- **Success Rate**: Successful task percentage
- **Consensus Level**: Agreement among agents
- **Resource Usage**: Combined agent resources

### Optimization Strategies
1. **Load Balancing**: Distribute work evenly
2. **Skill Matching**: Assign by expertise
3. **Parallel Processing**: Maximize concurrency
4. **Result Caching**: Reuse computations

## 🛠️ Advanced Team Features

### Dynamic Teams
```python
# Add agents dynamically
team.add_agent(new_agent)

# Remove underperforming agents
team.remove_agent(agent_id)

# Rebalance team composition
team.optimize_composition()
```

### Team Templates
```yaml
# trading_team_template.yaml
name: "Trading Team Template"
agents:
  - type: "trading"
    count: 2
  - type: "analysis"
    count: 1
  - type: "risk"
    count: 1
config:
  strategy: "consensus"
  min_agents: 3
```

### Multi-Team Coordination
```python
# Teams of teams
super_team = TeamOfTeams([
    research_team,
    trading_team,
    risk_team
])

result = await super_team.coordinate(
    "Execute complex trading strategy"
)
```

## 🐛 Troubleshooting Teams

### Common Issues

**Team Not Responding**
- Check all agents are running
- Verify network connectivity
- Review coordinator logs
- Check message queue

**Poor Coordination**
- Review strategy settings
- Check agent compatibility
- Verify shared context
- Monitor communication

**Slow Performance**
- Identify bottleneck agents
- Check sequential dependencies
- Review parallel limits
- Optimize message size

### Debug Tools
```bash
# View team logs
docker logs operation-team-{team_id}

# Monitor team communication
redis-cli MONITOR | grep team:{team_id}

# Check team state
curl http://localhost:8000/api/v1/teams/{team_id}/state
```

## 🎯 Best Practices

### Team Composition
1. **Diverse Skills**: Mix different agent types
2. **Optimal Size**: 3-7 agents per team
3. **Clear Roles**: Define responsibilities
4. **Backup Agents**: Handle failures

### Task Design
1. **Clear Objectives**: Specific goals
2. **Adequate Context**: Provide necessary info
3. **Reasonable Scope**: Match team capabilities
4. **Success Criteria**: Define completion

### Performance
1. **Monitor Metrics**: Track team health
2. **Regular Reviews**: Assess effectiveness
3. **Iterate Composition**: Optimize over time
4. **Learn Patterns**: Identify best practices

## 📚 Examples

### Financial Analysis Team
```python
# Create team
team = client.teams.create(
    name="Financial Analysis",
    agent_ids=[
        fundamental_analyst.id,
        technical_analyst.id,
        risk_analyst.id,
        report_writer.id
    ]
)

# Send task
result = client.teams.coordinate(
    team_id=team.id,
    objective="Analyze TSLA for long-term investment",
    context={
        "horizon": "5 years",
        "focus": ["growth", "innovation", "competition"]
    }
)
```

### Research Team
```python
# Create research team
team = client.teams.create(
    name="Research Team",
    agent_ids=[researcher1.id, researcher2.id, synthesizer.id]
)

# Complex research task
result = client.teams.coordinate(
    team_id=team.id,
    objective="Research quantum computing impact on cryptography",
    context={
        "depth": "comprehensive",
        "sources": ["academic", "industry", "patents"],
        "timeframe": "next decade"
    }
)
```

## 🔗 Related Resources

- [Agent Management Guide](./AGENT_MANAGEMENT.md)
- [API Reference](http://localhost:8000/docs#/teams)
- [Team Examples](./examples/teams/)