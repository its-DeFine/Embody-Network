# AutoGen Platform - Deployment Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Local Development](#local-development)
4. [Production Deployment](#production-deployment)
5. [Multi-Host Swarm Setup](#multi-host-swarm-setup)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd operation

# Start services locally
docker-compose up -d

# Check service health
curl http://localhost:8000/health
```

## Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- Python 3.11+ (for local testing)
- 8GB RAM minimum
- 20GB free disk space

### Required Ports
- 8000: API Gateway
- 8001: Admin Control
- 15672: RabbitMQ Management
- 6379: Redis
- 3000: Grafana
- 9090: Prometheus

## Local Development

### 1. Environment Setup

```bash
# Create .env file
cat > .env << EOF
# JWT Configuration
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# RabbitMQ Configuration
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=password
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis-password

# Admin Configuration
ADMIN_API_KEY=admin-secret-key-change-in-production

# LLM Configuration (for AutoGen agents)
OPENAI_API_KEY=your-openai-key
# or
ANTHROPIC_API_KEY=your-anthropic-key
EOF
```

### 2. Build and Start Services

```bash
# Build all images
docker-compose build

# Start core services only
docker-compose up -d redis rabbitmq api-gateway

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api-gateway
```

### 3. Verify Installation

```bash
# Check services are running
docker-compose ps

# Test API health
curl http://localhost:8000/health

# Access RabbitMQ Management
# http://localhost:15672 (admin/password)

# Access Grafana
# http://localhost:3000 (admin/admin)
```

## Production Deployment

### Option 1: Single Server Deployment

```bash
# 1. Install Docker on your server
curl -fsSL https://get.docker.com | sh

# 2. Copy files to server
scp -r operation/ user@server:/opt/autogen-platform/

# 3. SSH to server
ssh user@server

# 4. Create production env
cd /opt/autogen-platform
cp .env.example .env
# Edit .env with production values

# 5. Deploy with Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Option 2: Docker Swarm Deployment (Recommended)

#### Initialize Swarm Manager

```bash
# On manager node
docker swarm init --advertise-addr <MANAGER-IP>

# Save the join token
docker swarm join-token worker
```

#### Join Worker Nodes

```bash
# On each worker node
docker swarm join --token SWMTKN-1-xxx <MANAGER-IP>:2377
```

#### Deploy Stack

```bash
# On manager node
cd /opt/autogen-platform

# Create secrets
./scripts/prepare_swarm_secrets.sh

# Deploy stack
docker stack deploy -c docker-compose.yml -c docker-compose.swarm.yml autogen

# Check deployment
docker stack services autogen
```

### Option 3: Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f deployments/k8s/

# Check deployment
kubectl get pods -n autogen
kubectl get svc -n autogen
```

## Multi-Host Swarm Setup

### 1. Prepare Nodes

```bash
# On all nodes - Install Docker
curl -fsSL https://get.docker.com | sh

# Configure firewall (on all nodes)
# Open ports: 2377, 7946, 4789
ufw allow 2377/tcp  # Swarm management
ufw allow 7946/tcp  # Container network discovery
ufw allow 7946/udp
ufw allow 4789/udp  # Overlay network
```

### 2. Initialize Swarm

```bash
# On manager node
docker swarm init --advertise-addr <MANAGER-PUBLIC-IP>

# Add more managers (recommended: 3 or 5)
docker swarm join-token manager

# Add workers
docker swarm join-token worker
```

### 3. Label Nodes

```bash
# Label nodes for service placement
docker node update --label-add type=db manager1
docker node update --label-add type=app worker1
docker node update --label-add type=app worker2
```

### 4. Deploy Services

```bash
# Create overlay network
docker network create --driver overlay --attachable autogen-net

# Deploy stack with placement constraints
docker stack deploy -c docker-compose.swarm.yml autogen

# Scale services
docker service scale autogen_api-gateway=5
docker service scale autogen_agent-manager=3
```

## Configuration

### Service Configuration

#### API Gateway
```yaml
environment:
  - LOG_LEVEL=info
  - CORS_ORIGINS=["https://app.example.com"]
  - MAX_AGENTS_PER_CUSTOMER=10
  - RATE_LIMIT_REQUESTS=100
  - RATE_LIMIT_PERIOD=60
```

#### Agent Manager
```yaml
environment:
  - DOCKER_HOST=unix:///var/run/docker.sock
  - AGENT_MEMORY_LIMIT=512m
  - AGENT_CPU_LIMIT=0.5
  - MAX_CONCURRENT_BUILDS=5
```

### Security Configuration

1. **Enable TLS**
```yaml
# docker-compose.override.yml
services:
  api-gateway:
    environment:
      - TLS_CERT=/certs/cert.pem
      - TLS_KEY=/certs/key.pem
    volumes:
      - ./certs:/certs:ro
```

2. **Configure Firewall**
```bash
# Only allow specific IPs to admin endpoints
iptables -A INPUT -p tcp --dport 8001 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8001 -j DROP
```

3. **Use Docker Secrets**
```bash
# Create secrets
echo "production-jwt-secret" | docker secret create jwt_secret -
echo "production-db-password" | docker secret create db_password -

# Reference in compose file
services:
  api-gateway:
    secrets:
      - jwt_secret
    environment:
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
```

### Monitoring Setup

1. **Prometheus Configuration**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

2. **Grafana Dashboards**
```bash
# Import dashboards
curl -X POST http://admin:admin@localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @dashboards/autogen-platform.json
```

### Backup and Recovery

```bash
# Backup script
#!/bin/bash
# backup.sh

# Backup Redis
docker exec redis redis-cli SAVE
docker cp redis:/data/dump.rdb ./backups/redis-$(date +%Y%m%d).rdb

# Backup configurations
tar -czf ./backups/config-$(date +%Y%m%d).tar.gz .env docker-compose.yml

# Backup to S3 (optional)
aws s3 sync ./backups s3://my-bucket/autogen-backups/
```

## Troubleshooting

### Common Issues

#### 1. Services Won't Start
```bash
# Check logs
docker service logs autogen_api-gateway

# Check resource constraints
docker system df
docker system prune -a

# Verify network
docker network ls
docker network inspect autogen_autogen-overlay
```

#### 2. Container Creation Fails
```bash
# Run with privileged mode (development only)
docker service update --cap-add CAP_SYS_ADMIN autogen_agent-manager

# Or use Docker-in-Docker
docker run -d --privileged --name dind docker:dind
```

#### 3. Connection Issues
```bash
# Test internal networking
docker exec -it <container> ping redis
docker exec -it <container> nc -zv rabbitmq 5672

# Check DNS
docker exec -it <container> nslookup redis
```

#### 4. Performance Issues
```bash
# Monitor resources
docker stats
docker service ps autogen_api-gateway --no-trunc

# Scale services
docker service scale autogen_api-gateway=5

# Update resource limits
docker service update --limit-memory 1G autogen_api-gateway
```

### Health Checks

```bash
# Check all services
for service in api-gateway admin-control agent-manager; do
  echo "Checking $service..."
  curl -f http://localhost:8000/health || echo "$service is down"
done

# Monitor with watch
watch -n 5 'docker service ls'
```

### Emergency Procedures

#### Killswitch Activation
```bash
# Stop all agents immediately
docker service scale autogen_agent-manager=0

# Pause all operations
docker service ls | grep autogen | awk '{print $2}' | xargs -I {} docker service scale {}=0

# Remove everything
docker stack rm autogen
```

#### Rollback Deployment
```bash
# Rollback service
docker service rollback autogen_api-gateway

# Restore from backup
docker stack rm autogen
# Restore configs from backup
docker stack deploy -c docker-compose.yml autogen
```

## Maintenance

### Regular Tasks

1. **Update Images**
```bash
# Pull latest images
docker-compose pull

# Rolling update
docker service update --image autogen-api-gateway:latest autogen_api-gateway
```

2. **Clean Up**
```bash
# Remove unused resources
docker system prune -a --volumes

# Clean logs
find /var/lib/docker/containers -name "*.log" -exec truncate -s 0 {} \;
```

3. **Monitor Disk Space**
```bash
# Check disk usage
df -h
docker system df

# Set up log rotation
cat > /etc/docker/daemon.json << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
```

## Support

- Documentation: `/docs/`
- Issues: GitHub Issues
- Logs: `docker service logs <service_name>`
- Metrics: http://localhost:3000 (Grafana)

## Next Steps

1. [User Guide](./USER_GUIDE.md) - Learn how to use the platform
2. [API Reference](./API_REFERENCE.md) - Detailed API documentation
3. [Architecture](./ARCHITECTURE.md) - System design details