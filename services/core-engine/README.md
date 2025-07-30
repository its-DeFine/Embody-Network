# Core Engine Service

The Core Engine orchestrates AutoGen agents and manages the event-driven architecture.

## Features

- **Event Processing**: Handles all platform events through RabbitMQ
- **Agent Orchestration**: Manages agent lifecycle and communication
- **State Management**: Maintains system state in Redis
- **Task Routing**: Routes tasks to appropriate agents
- **Team Coordination**: Manages agent team interactions

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RabbitMQ   │────▶│    Core     │────▶│    Redis    │
│  (Events)   │     │   Engine    │     │   (State)   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   Agents    │
                    │  (AutoGen)  │
                    └─────────────┘
```

## Event Types

### Inbound Events
- `customer.created` - New customer registered
- `agent.create` - Create new agent
- `agent.update` - Update agent configuration
- `agent.delete` - Delete agent
- `task.create` - New task submission
- `team.create` - Create agent team

### Outbound Events
- `agent.created` - Agent successfully created
- `agent.updated` - Agent configuration updated
- `agent.deleted` - Agent removed
- `agent.status_changed` - Agent status change
- `task.started` - Task execution started
- `task.completed` - Task finished
- `task.failed` - Task execution failed

## Message Flow

1. **Event Reception**: Receives events from RabbitMQ
2. **Validation**: Validates event data and permissions
3. **Processing**: Executes business logic
4. **State Update**: Updates Redis state
5. **Event Publication**: Publishes result events

## Configuration

Environment variables:
- `REDIS_URL`: Redis connection URL
- `RABBITMQ_URL`: RabbitMQ connection URL
- `LOG_LEVEL`: Logging level (default: INFO)

## State Management

Redis keys:
- `customers:{customer_id}` - Customer data
- `agents:{agent_id}` - Agent configuration
- `tasks:{task_id}` - Task details
- `teams:{team_id}` - Team configuration
- `agent_status:{agent_id}` - Agent runtime status

## Error Handling

- Circuit breaker pattern for external services
- Exponential backoff for retries
- Dead letter queue for failed messages
- Comprehensive error logging

## Monitoring

- Health endpoint: `/health`
- Prometheus metrics endpoint: `/metrics`
- Structured logging with correlation IDs

## Development

### Running Tests
```bash
pytest tests/test_core_engine.py
```

### Local Development
```bash
docker-compose up core-engine
```