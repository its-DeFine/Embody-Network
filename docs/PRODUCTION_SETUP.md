# VTuber Autonomy Platform - Production Setup Guide
*Created: 2025-08-10 19:30*

## Overview
This document provides instructions for deploying the VTuber Autonomy Platform in a production environment with proper security and configuration.

## Prerequisites
- Docker and Docker Compose installed
- Redis server (v6.0+)
- Python 3.11+
- Minimum 8GB RAM, 4 CPU cores
- Open ports: 8010, 8081, 8082, 8085, 1935

## Initial Setup

### 1. Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your secure values
# IMPORTANT: Generate strong passwords and secrets
```

### 2. Generate Secure Secrets
```bash
# Generate JWT secret
openssl rand -hex 32

# Generate admin password
openssl rand -base64 32
```

### 3. Configure Redis
Ensure Redis is running and accessible:
```bash
redis-cli ping
# Should return: PONG
```

## Service Deployment

### 1. Central Manager
```bash
# Build and start the manager
docker-compose -f docker-compose.manager.debug.yml up -d

# Verify it's running
curl http://localhost:8010/health
```

### 2. VTuber Autonomy System
```bash
# Navigate to autonomy directory
cd autonomy

# Start all VTuber services
docker-compose -f docker-compose.yml up -d

# Check service status
docker-compose ps
```

### 3. Dashboard Interface
```bash
# Start the dashboard server
python3 -m http.server 8081 --directory . &

# Access dashboard at:
# http://localhost:8081/vtuber-dashboard-v3.html
```

## Service Architecture

### Core Components
1. **Central Manager** (Port 8010)
   - Authentication and authorization
   - Agent registry and coordination
   - Command routing

2. **NeuroSync S1** (Port 5001)
   - Avatar control and rendering
   - Character management
   - Speech synthesis

3. **AutoGen Multi-Agent** (Port 8200)
   - Cognitive processing
   - Decision making
   - Agent behaviors

4. **SCB Gateway** (Port 8082)
   - Message routing
   - Inter-service communication
   - Event handling

5. **RTMP Streaming** (Port 1935/8085)
   - Audio/video streaming
   - HLS output
   - Stream monitoring

## Security Configuration

### Authentication
- All API endpoints require JWT authentication
- Default admin user: `admin@system.com`
- Password must be set via environment variable

### Network Security
```bash
# Recommended firewall rules (UFW example)
ufw allow 8010/tcp  # Manager API
ufw allow 8081/tcp  # Dashboard
ufw allow 1935/tcp  # RTMP
ufw allow 8085/tcp  # RTMP HTTP
```

### Secret Management
- Never commit `.env` files
- Use environment variables for all secrets
- Rotate JWT secrets regularly
- Use strong passwords (min 32 characters)

## Agent Management

### Creating Agents
Agents can be created through:
1. Dashboard UI (recommended)
2. Python scripts (`agent_manager_v2.py`)
3. Direct API calls

### Agent Categories
- **Orchestrators**: Coordination systems
- **Agents**: Character entities with personalities
- **Infrastructure**: Service containers

### Agent Templates
Pre-configured templates available:
- Luna Streamer (Content Creator)
- Diana Educator (Teacher)
- Sophia Trader (Financial Analyst)

## Monitoring and Maintenance

### Health Checks
```bash
# Check all services
docker ps

# Check manager logs
docker logs debug-central-manager-auth

# Check VTuber services
cd autonomy && docker-compose logs -f
```

### Backup
Regular backups should include:
- Redis data (`redis-cli BGSAVE`)
- Agent configurations
- Character templates

### Updates
```bash
# Pull latest changes
git pull

# Rebuild services
docker-compose build

# Restart with new images
docker-compose down && docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **Manager won't start**
   - Check Redis connectivity
   - Verify environment variables
   - Check port 8010 availability

2. **Agents not registering**
   - Verify authentication token
   - Check network connectivity
   - Review manager logs

3. **RTMP stream not working**
   - Ensure port 1935 is open
   - Check NGINX RTMP logs
   - Verify stream key configuration

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
docker-compose up
```

## Performance Tuning

### Redis Optimization
```bash
# Add to redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Docker Resources
```yaml
# Add to docker-compose.yml services
resources:
  limits:
    cpus: '2.0'
    memory: 4G
```

## Production Checklist

- [ ] Environment variables configured
- [ ] Strong passwords generated
- [ ] Redis secured with password
- [ ] Firewall rules configured
- [ ] SSL/TLS certificates (if public)
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured
- [ ] Log rotation enabled
- [ ] Resource limits set
- [ ] Health checks verified

## Support and Documentation

- Architecture docs: `/docs/ARCHITECTURE.md`
- API documentation: `/docs/API.md`
- Agent templates: `/autonomy/docker-vtuber/app/AVATAR/NeuroBridge/NeuroSync_Player/characters/`

## License
Proprietary - All rights reserved