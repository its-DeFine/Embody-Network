# Multi-Host Distributed Container Deployment

## Overview

This document outlines how to deploy the distributed container system across multiple physical computers and networks.

## Current Limitations

The existing system is designed for single-host deployment:
- Uses Docker bridge networks (only works on one machine)
- References containers by internal hostnames (`redis:6379`)
- Relies on Docker's internal service discovery

## Multi-Host Solutions

### Solution 1: External IP Configuration (Recommended)

Configure each container to use external IPs instead of internal hostnames.

**Pros:**
- Simple to implement
- Works across any network topology
- No special infrastructure required

**Cons:**
- Requires manual IP configuration
- Less dynamic than service discovery

### Solution 2: Docker Swarm Mode

Use Docker Swarm for native multi-host container orchestration.

**Pros:**
- Native Docker solution
- Built-in service discovery
- Load balancing and failover

**Cons:**
- Requires Swarm cluster setup
- More complex networking

### Solution 3: External Service Mesh (VPN)

Use VPN or service mesh to connect containers across networks.

**Pros:**
- Secure cross-network communication
- Flexible network topology
- Works with existing Docker setup

**Cons:**
- Additional infrastructure complexity
- VPN configuration required

### Solution 4: Hybrid Cloud Deployment

Deploy using cloud services with external load balancers.

**Pros:**
- Highly scalable
- Professional-grade infrastructure
- Built-in monitoring and logging

**Cons:**
- Cloud costs
- More complex setup

## Implementation Details

### Method 1: External IP Configuration

#### Central Manager Configuration
```yaml
services:
  central-manager:
    environment:
      - REDIS_URL=redis://10.0.1.100:6379  # External Redis IP
      - EXTERNAL_IP=10.0.1.200             # This machine's external IP
      - CLUSTER_PORT=8000
    ports:
      - "8000:8000"
```

#### Agent Container Configuration
```yaml
services:
  agent-container:
    environment:
      - CENTRAL_MANAGER_URL=http://10.0.1.200:8000  # Central manager external IP
      - REDIS_URL=redis://10.0.1.100:6379           # External Redis IP
      - EXTERNAL_IP=10.0.1.201                      # This machine's external IP
    ports:
      - "8001:8001"
```

### Method 2: Docker Swarm Deployment

#### Initialize Swarm on Manager Node
```bash
# On central manager machine
docker swarm init --advertise-addr 10.0.1.200

# Copy join token for worker nodes
docker swarm join-token worker
```

#### Join Worker Nodes
```bash
# On each agent machine
docker swarm join --token <token> 10.0.1.200:2377
```

#### Deploy Stack
```yaml
version: '3.8'
services:
  central-manager:
    image: autogen-platform:latest
    networks:
      - autogen-overlay
    deploy:
      placement:
        constraints: [node.role == manager]
  
  agent-container:
    image: autogen-agent:latest
    networks:
      - autogen-overlay
    deploy:
      replicas: 3
      placement:
        constraints: [node.role == worker]

networks:
  autogen-overlay:
    driver: overlay
    attachable: true
```

### Method 3: VPN-Based Networking

#### WireGuard VPN Configuration

**Manager Node (10.0.100.1)**
```ini
[Interface]
PrivateKey = <manager-private-key>
Address = 10.0.100.1/24
ListenPort = 51820

[Peer]
PublicKey = <agent1-public-key>
AllowedIPs = 10.0.100.2/32

[Peer]
PublicKey = <agent2-public-key>
AllowedIPs = 10.0.100.3/32
```

**Agent Node 1 (10.0.100.2)**
```ini
[Interface]
PrivateKey = <agent1-private-key>
Address = 10.0.100.2/24

[Peer]
PublicKey = <manager-public-key>
Endpoint = <manager-public-ip>:51820
AllowedIPs = 10.0.100.0/24
```

### Method 4: Cloud Native Deployment

#### AWS ECS with ALB
```yaml
version: '3.8'
services:
  central-manager:
    image: autogen-platform:latest
    environment:
      - REDIS_URL=redis://autogen-redis.cache.amazonaws.com:6379
    deploy:
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.api.rule=Host(`api.autogen.com`)"
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: central-manager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: central-manager
  template:
    metadata:
      labels:
        app: central-manager
    spec:
      containers:
      - name: central-manager
        image: autogen-platform:latest
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
---
apiVersion: v1
kind: Service
metadata:
  name: central-manager-service
spec:
  selector:
    app: central-manager
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

## Security Considerations

### Network Security
- Use TLS/SSL for all inter-container communication
- Implement proper firewall rules
- Use VPN or private networks when possible

### Authentication
- JWT tokens for API authentication
- Container-to-container authentication
- Regular key rotation

### Monitoring
- Network latency monitoring
- Connection health checks
- Distributed logging

## Testing Multi-Host Deployment

### Network Connectivity Test
```bash
# Test Redis connectivity from remote machine
telnet 10.0.1.100 6379

# Test API connectivity
curl http://10.0.1.200:8000/health

# Test container registration
curl -X POST http://10.0.1.200:8000/api/v1/cluster/containers/register \
  -H "Content-Type: application/json" \
  -d '{"container_name": "remote-agent", "host_address": "10.0.1.201"}'
```

### Performance Testing
- Measure cross-network latency
- Test under network partition scenarios
- Validate failover mechanisms

## Deployment Checklist

- [ ] Choose deployment method based on infrastructure
- [ ] Configure external IPs or hostnames
- [ ] Setup shared Redis instance accessible to all nodes
- [ ] Configure firewall rules for required ports
- [ ] Test connectivity between all nodes
- [ ] Deploy containers with external configuration
- [ ] Validate container discovery and registration
- [ ] Test agent deployment across networks
- [ ] Monitor system performance and health

## Troubleshooting

### Common Issues
1. **Connection Refused**: Check firewall rules and port accessibility
2. **DNS Resolution**: Use IP addresses instead of hostnames
3. **Redis Connection**: Ensure Redis is accessible from all nodes
4. **Container Registration**: Verify external IP configuration

### Debugging Commands
```bash
# Test network connectivity
ping <remote-ip>
telnet <remote-ip> <port>

# Check Docker network
docker network ls
docker network inspect <network-name>

# Check container logs
docker logs <container-name>

# Test API endpoints
curl -v http://<external-ip>:8000/api/v1/cluster/status
```