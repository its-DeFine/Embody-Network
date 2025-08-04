# Distributed Container System - Quick Start Guide

## Overview

The distributed container management system allows you to run multiple agent containers that automatically register with a central manager. This enables horizontal scaling, fault tolerance, and intelligent agent distribution across your infrastructure.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ for running test scripts
- At least 8GB RAM for running the full cluster
- Network connectivity between containers

## Quick Start

### 1. Launch the Distributed Cluster

```bash
# Start the entire distributed cluster
./scripts/start_distributed_cluster.sh
```

This will:
- Start Redis for shared state
- Launch the central manager
- Start 3 specialized agent containers (trading, analysis, risk)
- Start 1 generic worker container
- Automatically register all containers with the central manager

### 2. Verify Cluster Status

```bash
# Check cluster health
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/cluster/status

# Or use the web UI
open http://localhost:8000/docs
```

### 3. Deploy Agents

```python
# Using the Python test script
python scripts/demo/test_distributed_system.py

# Or via API
curl -X POST http://localhost:8000/api/v1/cluster/agents/deploy \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "trading",
    "agent_config": {
      "name": "high_freq_trader",
      "strategy": "momentum"
    },
    "deployment_strategy": "least_loaded"
  }'
```

## Container Types

### 1. Central Manager
- **Role**: Orchestrates the entire cluster
- **Port**: 8000
- **Features**:
  - Container discovery and registration
  - Agent deployment and migration
  - Load balancing and fault tolerance
  - Cluster-wide monitoring

### 2. Trading Container
- **Role**: Runs trading-focused agents
- **Port**: 8001
- **Capabilities**: trading, market_analysis
- **Resources**: 2 CPUs, 2GB RAM

### 3. Analysis Container
- **Role**: Runs analysis and computation agents
- **Port**: 8002
- **Capabilities**: analysis, gpu_compute
- **Resources**: 4 CPUs, 4GB RAM

### 4. Risk Container
- **Role**: Runs risk management agents
- **Port**: 8003
- **Capabilities**: risk_analysis, compliance
- **Resources**: 2 CPUs, 2GB RAM

### 5. Worker Container
- **Role**: General-purpose agent execution
- **Capabilities**: general_compute
- **Resources**: 1 CPU, 1GB RAM

## Deployment Strategies

### Least Loaded
Deploys agents to the container with the lowest resource usage:
```json
{"deployment_strategy": "least_loaded"}
```

### Round Robin
Distributes agents evenly across containers:
```json
{"deployment_strategy": "round_robin"}
```

### Capability Match
Places agents on containers with required capabilities:
```json
{
  "deployment_strategy": "capability_match",
  "constraints": {
    "require_capability": "gpu_compute"
  }
}
```

### Resource Optimal
Finds the best resource fit for the agent:
```json
{
  "deployment_strategy": "resource_optimal",
  "resource_requirements": {
    "min_cpu": 2,
    "min_memory": 2147483648
  }
}
```

## Common Operations

### View Container Status
```bash
# List all containers
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/cluster/containers

# Get specific container details
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/cluster/containers/CONTAINER_ID
```

### Deploy Multiple Agents
```bash
# Deploy a team of agents
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/cluster/agents/deploy \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"agent_type\": \"trading\",
      \"agent_config\": {
        \"name\": \"trader_$i\"
      },
      \"deployment_strategy\": \"round_robin\"
    }"
done
```

### Migrate an Agent
```bash
curl -X POST http://localhost:8000/api/v1/cluster/agents/AGENT_ID/migrate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "AGENT_ID",
    "target_container_id": "TARGET_CONTAINER_ID",
    "preserve_state": true
  }'
```

### Rebalance the Cluster
```bash
# Automatically redistribute agents for optimal performance
curl -X POST http://localhost:8000/api/v1/cluster/actions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "rebalance"}'
```

## Monitoring

### View Logs
```bash
# All containers
docker-compose -f docker-compose.distributed.yml logs -f

# Specific container
docker logs -f autogen-agent-01

# Central manager only
docker logs -f autogen-central-manager
```

### Monitor Resources
```bash
# Real-time resource usage
docker stats

# Cluster distribution
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/cluster/metrics/distribution
```

### Health Checks
```bash
# Check individual container health
curl http://localhost:8001/health  # Agent container 1
curl http://localhost:8002/health  # Agent container 2
curl http://localhost:8003/health  # Agent container 3
```

## Scaling

### Add More Containers
```bash
# Scale worker containers
docker-compose -f docker-compose.distributed.yml \
  up -d --scale agent-worker-1=5
```

### Custom Container Configuration
Create a new service in docker-compose.distributed.yml:
```yaml
custom-agent:
  build:
    context: .
    dockerfile: Dockerfile.agent
  environment:
    - AGENT_ID=custom-01
    - AGENT_TYPE=custom
    - CAPABILITIES=["special_compute", "ml_training"]
  networks:
    - autogen-network
```

## Troubleshooting

### Container Won't Register
1. Check network connectivity: `docker network ls`
2. Verify Redis connection: `docker exec autogen-redis redis-cli ping`
3. Check container logs: `docker logs autogen-agent-01`
4. Ensure authentication credentials match

### Agent Deployment Fails
1. Check available containers: `GET /api/v1/cluster/containers`
2. Verify resource requirements
3. Check container capabilities match requirements
4. Review deployment strategy

### Performance Issues
1. Monitor resource usage: `docker stats`
2. Check Redis performance: `redis-cli --latency`
3. Review agent distribution
4. Consider rebalancing the cluster

## Security Considerations

1. **Change default passwords** in production
2. **Use TLS** for inter-container communication
3. **Implement network segmentation** for containers
4. **Enable authentication** on all endpoints
5. **Rotate encryption keys** regularly

## Next Steps

1. **Production Deployment**: See [SECURE_DEPLOYMENT_GUIDE.md](SECURE_DEPLOYMENT_GUIDE.md)
2. **Custom Agents**: Implement your own agent types
3. **Monitoring**: Set up Prometheus/Grafana dashboards
4. **High Availability**: Configure Redis replication
5. **Kubernetes**: Deploy on K8s for enterprise scale