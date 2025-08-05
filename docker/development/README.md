# Development Docker Configurations

This directory contains Docker Compose configurations for development, testing, and debugging.

## 🛠️ Development Deployments

### 1. Distributed Development Environment
**File**: `docker-compose.distributed.yml`  
**Use Case**: Local development and testing of distributed container system  
**Components**: Central manager + 3 specialized agent containers + 1 worker  
**Best For**: Developing and testing distributed functionality  

```bash
# Start full distributed development environment
cd docker/development
docker-compose -f docker-compose.distributed.yml up -d

# View logs
docker-compose -f docker-compose.distributed.yml logs -f

# Scale worker containers
docker-compose -f docker-compose.distributed.yml up -d --scale agent-worker-1=3
```

### 2. Debug Environment
**File**: `docker-compose.debug.yml`  
**Use Case**: Minimal setup for debugging orchestrator issues  
**Components**: Central manager + Redis only  
**Best For**: Debugging orchestrator deployment pattern issues  

```bash
# Start minimal debug environment
cd docker/development
docker-compose -f docker-compose.debug.yml up -d

# Debug orchestrator registration
python ../../scripts/debug_orchestrator_registration.py
```

## 🔍 Development Tools

### Container Testing
```bash
# Test distributed system
python ../../scripts/demo/test_distributed_system.py

# Debug cluster status
python ../../scripts/debug_cluster_status.py

# Test orchestrator deployment pattern
python ../../scripts/test_orchestrator_deployment.py
```

### Monitoring
```bash
# Real-time cluster visualization
python ../../scripts/monitoring/visualize_cluster.py

# Monitor container logs
docker-compose logs -f central-manager
docker-compose logs -f agent-container-1

# Check resource usage
docker stats
```

## 🧪 Testing Scenarios

### 1. Agent Deployment Testing
```bash
# Deploy various agent types
curl -X POST http://localhost:8000/api/v1/cluster/agents/deploy \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "trading", "deployment_strategy": "least_loaded"}'
```

### 2. Container Failure Testing
```bash
# Simulate container failure
docker stop autogen-agent-01

# Watch automatic recovery
curl http://localhost:8000/api/v1/cluster/status
```

### 3. Load Testing
```bash
# Deploy multiple agents
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/cluster/agents/deploy \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"agent_type\": \"trading\", \"agent_config\": {\"name\": \"trader_$i\"}}"
done
```

## ⚙️ Development Configuration

### Environment Variables
Development environments use default values safe for local testing:

```bash
# Debug environment (.env.debug)
REDIS_URL=redis://redis:6379
ENABLE_DISTRIBUTED=true
JWT_SECRET=debug-jwt-secret-not-for-production
ADMIN_PASSWORD=debug-admin-password-change-for-production
LOG_LEVEL=DEBUG

# Distributed development (.env.distributed)
DISCOVERY_INTERVAL=10
HEALTH_CHECK_INTERVAL=5
REBALANCE_INTERVAL=60
```

### Resource Limits
Development containers use minimal resources:

- **Central Manager**: 1 CPU, 1GB RAM
- **Agent Containers**: 0.5 CPU, 512MB RAM each
- **Redis**: 0.25 CPU, 256MB RAM

## 🐛 Debugging Guide

### Common Issues

1. **Container Won't Register**
   ```bash
   # Check network connectivity
   docker network ls
   docker exec autogen-redis redis-cli ping
   
   # Check container logs
   docker logs autogen-agent-01
   ```

2. **Agent Deployment Fails**
   ```bash
   # Check available containers
   curl http://localhost:8000/api/v1/cluster/containers
   
   # Check container capabilities
   curl http://localhost:8000/api/v1/cluster/status
   ```

3. **Performance Issues**
   ```bash
   # Monitor resources
   docker stats
   
   # Check Redis performance
   docker exec autogen-redis redis-cli --latency
   ```

### Debug Scripts
- `scripts/debug_cluster_status.py` - Debug cluster API responses
- `scripts/debug_orchestrator_registration.py` - Debug container registration
- `scripts/debug_orchestrator_deployment.py` - Debug deployment issues

## 🔄 Development Workflow

1. **Start Environment**
   ```bash
   cd docker/development
   docker-compose -f docker-compose.distributed.yml up -d
   ```

2. **Make Code Changes**
   - Edit files in `app/` directory
   - Changes are automatically reflected (volume mounts)

3. **Test Changes**
   ```bash
   # Test specific functionality
   python scripts/demo/test_distributed_system.py
   
   # Run validation tests
   python scripts/test_orchestrator_deployment.py
   ```

4. **Debug Issues**
   ```bash
   # Use debug environment for minimal setup
   docker-compose -f docker-compose.debug.yml up -d
   
   # Run debug scripts
   python scripts/debug_cluster_status.py
   ```

5. **Clean Up**
   ```bash
   docker-compose down -v
   docker system prune -f
   ```

## 📝 Notes

- **Never use development configs in production**
- **Default passwords are intentionally weak for development**
- **Resource limits are minimal for development machines**
- **Debug logging enabled by default**
- **Volume mounts allow real-time code changes**