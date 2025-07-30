# Agent Manager Service

The Agent Manager handles the lifecycle of AutoGen agents, managing their deployment, configuration, and runtime state.

## Features

- **Agent Lifecycle Management**: Create, start, stop, and delete agents
- **Container Management**: Deploy agents as Docker containers
- **Configuration Management**: Handle agent and AutoGen configurations
- **Resource Management**: Monitor and enforce resource limits
- **Health Monitoring**: Track agent health and status

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Core      │────▶│   Agent     │────▶│   Docker    │
│   Engine    │     │  Manager    │     │   Daemon    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   Agent     │
                    │ Containers  │
                    └─────────────┘
```

## Agent Types

- **Trading Agent**: Cryptocurrency and stock trading
- **Analysis Agent**: Market and data analysis
- **Risk Management Agent**: Portfolio risk assessment
- **Portfolio Optimization Agent**: Asset allocation optimization
- **Custom Agents**: User-defined agent types

## Container Management

### Agent Container Specs
- Base image: `autogen-agent:latest`
- Memory limit: Configurable (default: 1GB)
- CPU limit: Configurable (default: 1 core)
- Network: `autogen-network`
- Volumes: Shared modules mounted read-only

### Environment Variables
Each agent container receives:
- `AGENT_ID`: Unique agent identifier
- `CUSTOMER_ID`: Owner customer ID
- `AGENT_TYPE`: Agent type (trading, analysis, etc.)
- `AGENT_NAME`: Display name
- `CONFIG`: Agent-specific configuration (JSON)
- `AUTOGEN_CONFIG`: AutoGen framework configuration (JSON)
- `RABBITMQ_URL`: Message queue connection
- `REDIS_URL`: State store connection

## Message Handling

### Inbound Messages
- `agent.create` - Deploy new agent
- `agent.update` - Update configuration
- `agent.start` - Start agent container
- `agent.stop` - Stop agent container
- `agent.delete` - Remove agent and container
- `agent.restart` - Restart agent container

### Outbound Events
- `agent.created` - Agent deployed successfully
- `agent.started` - Agent container started
- `agent.stopped` - Agent container stopped
- `agent.deleted` - Agent removed
- `agent.health` - Health status updates

## Deployment Modes

### Docker Mode (Default)
- Direct Docker daemon access
- Requires volume mount: `/var/run/docker.sock`
- Suitable for single-host deployments

### Swarm Mode
- Deploy as Docker Swarm services
- Automatic load balancing
- Multi-host support

### GPU Mode
- Integration with GPU orchestrator
- GPU resource allocation
- CUDA-enabled containers

## Configuration

Environment variables:
- `DOCKER_HOST`: Docker daemon URL
- `RABBITMQ_URL`: RabbitMQ connection
- `REDIS_URL`: Redis connection
- `DOCKER_NETWORK`: Network name (default: autogen-network)
- `AGENT_IMAGE`: Base agent image (default: autogen-agent:latest)

## Security

- No privileged containers
- Read-only root filesystem
- Dropped capabilities
- Resource limits enforced
- Network isolation

## Monitoring

- Container health checks
- Resource usage tracking
- Event logging
- Status reporting

## Troubleshooting

### Common Issues

1. **Permission Denied on Docker Socket**
   - Ensure proper permissions on `/var/run/docker.sock`
   - Run with appropriate user/group

2. **Container Creation Fails**
   - Check Docker daemon availability
   - Verify network exists
   - Check image availability

3. **Agent Not Responding**
   - Check container logs
   - Verify network connectivity
   - Check resource limits