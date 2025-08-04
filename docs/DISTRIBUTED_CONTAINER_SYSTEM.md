# Distributed Container Management System

## Overview

The distributed container management system enables the central manager to automatically detect, register, and manage agent containers across a cluster. This allows for seamless scaling, load balancing, and fault tolerance in multi-container deployments.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Central Manager                           │
│  ┌─────────────┐ ┌──────────────────┐ ┌────────────────────┐  │
│  │  Discovery   │ │    Registry      │ │  Agent Manager     │  │
│  │  Service     │ │    Service       │ │  (Distributed)     │  │
│  └─────────────┘ └──────────────────┘ └────────────────────┘  │
│         │                 │                      │               │
│  ┌──────┴─────────────────┴──────────────────────┴──────────┐  │
│  │              Container Communication Hub                   │  │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────┬───────────────────────┬──────────────────┘
                      │                       │
         ┌────────────┴──────────┐ ┌─────────┴────────────┐
         │   Agent Container 1    │ │   Agent Container 2   │
         │  ┌────────────────┐   │ │  ┌────────────────┐  │
         │  │ Trading Agent  │   │ │  │ Analysis Agent │  │
         │  └────────────────┘   │ │  └────────────────┘  │
         └───────────────────────┘ └──────────────────────┘
```

## Core Components

### 1. Container Discovery Service
- **Auto-detection**: Scans Docker networks for compatible containers
- **Health monitoring**: Continuous health checks on discovered containers
- **Capability assessment**: Determines what each container can do
- **Network topology mapping**: Tracks container connectivity

### 2. Container Registry
- **Registration management**: Tracks all containers in the cluster
- **Lifecycle tracking**: Monitors container states and transitions
- **Resource monitoring**: Tracks CPU, memory, and other resources
- **Event handling**: Publishes container lifecycle events

### 3. Distributed Agent Manager
- **Intelligent placement**: Deploys agents to optimal containers
- **Load balancing**: Distributes agents evenly across containers
- **Failure recovery**: Automatically migrates agents from failed containers
- **Rebalancing**: Periodically optimizes agent distribution

### 4. Container Communication Hub
- **Secure messaging**: Encrypted inter-container communication
- **Event broadcasting**: Cluster-wide event distribution
- **API proxying**: Route API calls between containers
- **Message routing**: Intelligent message delivery

### 5. Cluster API
- **REST endpoints**: Full control over cluster operations
- **Container management**: Register, monitor, and control containers
- **Agent deployment**: Deploy agents across the cluster
- **Monitoring**: Real-time cluster health and metrics

## Container Registration Flow

1. **Container Startup**
   - Agent container starts and initializes
   - Reads environment configuration
   - Establishes Redis connection

2. **Cluster Registration**
   - Container authenticates with central manager
   - Sends registration request with capabilities
   - Receives unique container ID

3. **Heartbeat Loop**
   - Sends periodic health updates
   - Reports resource usage and agent count
   - Maintains active status in registry

4. **Discovery**
   - Central manager discovery service finds container
   - Validates container capabilities
   - Adds to active container pool

## Agent Deployment Flow

1. **Deployment Request**
   ```bash
   POST /api/v1/cluster/deploy/agent
   {
     "agent_type": "trading",
     "agent_config": {...},
     "placement_strategy": "least_loaded",
     "preferred_capabilities": ["gpu_compute"]
   }
   ```

2. **Container Selection**
   - Evaluates available containers
   - Applies placement strategy
   - Selects optimal container

3. **Remote Deployment**
   - Sends deployment command to container
   - Container creates agent instance
   - Agent starts processing

4. **Health Monitoring**
   - Continuous health checks
   - Automatic failure detection
   - Migration if container fails

## Placement Strategies

### Round Robin
- Distributes agents evenly in order
- Simple and predictable
- Good for homogeneous workloads

### Least Loaded
- Places on container with lowest load
- Considers CPU, memory, and agent count
- Optimal for varying workloads

### Capability Match
- Matches agent requirements to container capabilities
- Ensures agents run on suitable hardware
- Essential for specialized workloads

### Resource Optimal
- Finds best resource fit
- Minimizes resource waste
- Ideal for resource-intensive agents

## API Endpoints

### Cluster Management
- `GET /api/v1/cluster/status` - Overall cluster status
- `GET /api/v1/cluster/topology` - Network topology
- `POST /api/v1/cluster/rebalance` - Trigger rebalancing

### Container Operations
- `GET /api/v1/cluster/containers` - List all containers
- `POST /api/v1/cluster/containers/register` - Register container
- `POST /api/v1/cluster/containers/{id}/heartbeat` - Update heartbeat
- `DELETE /api/v1/cluster/containers/{id}` - Deregister container

### Agent Deployment
- `POST /api/v1/cluster/deploy/agent` - Deploy new agent
- `GET /api/v1/cluster/agents` - List distributed agents
- `POST /api/v1/cluster/agents/{id}/migrate` - Migrate agent
- `DELETE /api/v1/cluster/agents/{id}` - Stop agent

## Configuration

### Environment Variables

**Central Manager:**
```bash
ENABLE_DISTRIBUTED=true
DISCOVERY_INTERVAL=30
HEALTH_CHECK_INTERVAL=15
REBALANCE_INTERVAL=300
```

**Agent Container:**
```bash
AGENT_ID=unique-agent-id
AGENT_TYPE=trading
CENTRAL_MANAGER_URL=http://central-manager:8000
REDIS_URL=redis://redis:6379
ADMIN_PASSWORD=your-secure-password
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  central-manager:
    image: autogen-platform:latest
    environment:
      - ENABLE_DISTRIBUTED=true
    ports:
      - "8000:8000"
    networks:
      - autogen-network

  agent-1:
    image: autogen-agent:latest
    environment:
      - AGENT_ID=agent-001
      - AGENT_TYPE=trading
      - CENTRAL_MANAGER_URL=http://central-manager:8000
    networks:
      - autogen-network
    labels:
      - "autogen.agent.capable=true"

  agent-2:
    image: autogen-agent:latest
    environment:
      - AGENT_ID=agent-002
      - AGENT_TYPE=analysis
      - CENTRAL_MANAGER_URL=http://central-manager:8000
    networks:
      - autogen-network
    labels:
      - "autogen.agent.capable=true"

networks:
  autogen-network:
    driver: bridge
```

## Monitoring and Debugging

### Check Cluster Status
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/cluster/status
```

### View Container Logs
```bash
docker logs -f container-name
```

### Monitor Agent Distribution
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/cluster/agents
```

### Trigger Manual Rebalance
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/cluster/rebalance
```

## Best Practices

1. **Container Sizing**
   - Keep containers appropriately sized
   - Don't overload individual containers
   - Monitor resource usage

2. **Network Configuration**
   - Use dedicated networks for agent communication
   - Ensure proper DNS resolution
   - Configure firewall rules appropriately

3. **Fault Tolerance**
   - Run multiple agent containers
   - Enable automatic migration
   - Monitor container health

4. **Security**
   - Use strong authentication
   - Encrypt inter-container communication
   - Limit container capabilities

5. **Scaling**
   - Start with 2-3 containers minimum
   - Add containers based on load
   - Use placement strategies wisely

## Troubleshooting

### Container Not Discovered
- Check Docker labels (`autogen.agent.capable=true`)
- Verify network connectivity
- Check discovery service logs

### Registration Fails
- Verify authentication credentials
- Check central manager URL
- Ensure network connectivity

### Agent Migration Issues
- Check target container health
- Verify sufficient resources
- Review migration logs

### Performance Problems
- Monitor resource usage
- Check network latency
- Review agent distribution