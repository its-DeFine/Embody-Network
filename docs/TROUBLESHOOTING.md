# Troubleshooting Guide

**Complete troubleshooting guide for diagnosing and resolving common issues with the 24/7 Trading System.**

## 🔍 Quick Diagnostic Commands

### System Health Check
```bash
# Quick system status
curl -s http://localhost:8000/health | jq

# Detailed trading status
curl -s http://localhost:8000/api/v1/trading/status | jq

# Check all containers
docker-compose ps

# View recent logs
docker-compose logs --tail 50 app
```

### Market Data Check
```bash
# Test market data providers
curl -s http://localhost:8000/api/v1/market/providers | jq

# Get sample price
curl -s http://localhost:8000/api/v1/market/price/AAPL | jq

# Check data freshness
curl -s http://localhost:8000/api/v1/market/status | jq
```

## 🚨 Common Issues & Solutions

### 1. System Won't Start

**Symptoms**:
- Containers exit immediately
- "Connection refused" errors
- Application hangs during startup

**Diagnosis**:
```bash
# Check container status
docker-compose ps

# Check logs for errors
docker-compose logs app

# Check resource usage
docker stats
```

**Solutions**:

**A. Port conflicts:**
```bash
# Check if port 8000 is in use
sudo netstat -tlnp | grep :8000

# Kill process using port
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

**B. Memory issues:**
```bash
# Check available memory
free -h

# Increase Docker memory limits
echo '{
  "default-ulimits": {
    "memlock": {"hard": -1, "soft": -1}
  }
}' | sudo tee /etc/docker/daemon.json

sudo systemctl restart docker
```

**C. Environment variable issues:**
```bash
# Validate .env file
cat .env | grep -E "(JWT_SECRET|ADMIN_PASSWORD|API_KEY)"

# Check if all required variables are set
docker-compose config
```

### 2. Application Hangs During Startup

**Symptoms**:
- "Waiting for application startup" message
- No API responses
- Containers running but not functional

**Diagnosis**:
```bash
# Check if stuck in collective intelligence startup
docker-compose logs app | grep -i "collective\|sentiment\|agents"

# Monitor CPU usage
docker stats operation-app-1
```

**Solutions**:

**A. Use simplified startup:**
```bash
# Copy fixed main.py
cp app/main_fixed.py app/main.py

# Restart containers
docker-compose restart app
```

**B. Comment out problematic components:**
```python
# In app/main.py, comment out:
# await collective_intelligence.start()

# Replace with:
# asyncio.create_task(collective_intelligence.start())
```

**C. Clean restart:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 3. No Trades Executing

**Symptoms**:
- Trading status shows active but no trades
- Portfolio value unchanged
- No trade history

**Diagnosis**:
```bash
# Check trading status
curl -s http://localhost:8000/api/v1/trading/status | jq '.trading_active'

# Check strategy status
curl -s http://localhost:8000/api/v1/trading/strategies | jq

# Check market hours
date
curl -s http://localhost:8000/api/v1/market/status | jq '.market_open'
```

**Solutions**:

**A. Market hours issue:**
```bash
# Crypto markets trade 24/7, stocks have hours
# Check if trading appropriate instruments
curl -s http://localhost:8000/api/v1/market/price/BTC-USD | jq
```

**B. Strategy configuration:**
```bash
# Check strategy parameters
docker-compose logs app | grep -i "strategy\|confidence"

# Lower confidence thresholds in strategies if too restrictive
```

**C. Insufficient balance:**
```bash
# Check portfolio balance
curl -s http://localhost:8000/api/v1/trading/portfolio | jq '.cash'

# Ensure sufficient capital for minimum trade sizes
```

**D. API rate limits:**
```bash
# Check API provider status
curl -s http://localhost:8000/api/v1/market/providers | jq

# Wait for rate limits to reset or switch providers
```

### 4. High Resource Usage

**Symptoms**:
- Slow API responses
- High CPU/memory usage
- System lag

**Diagnosis**:
```bash
# Monitor resources
docker stats

# Check Redis memory
docker-compose exec redis redis-cli info memory

# Check disk space
df -h
```

**Solutions**:

**A. Reduce symbol count:**
```bash
# Edit .env file
TARGET_SYMBOLS=AAPL,MSFT,GOOGL  # Reduce from default

# Restart application  
docker-compose restart app
```

**B. Optimize Redis:**
```bash
# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB

# Set memory limits
docker-compose exec redis redis-cli config set maxmemory 1gb
docker-compose exec redis redis-cli config set maxmemory-policy allkeys-lru
```

**C. Increase resources:**
```yaml
# In docker-compose.override.yml
version: '3.8'
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2.0"
```

### 5. API Authentication Errors

**Symptoms**:
- "401 Unauthorized" responses
- "Invalid token" errors
- Login failures

**Diagnosis**:
```bash
# Check JWT secret length
echo $JWT_SECRET | wc -c  # Should be > 32

# Test admin credentials
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

**Solutions**:

**A. Fix JWT secret:**
```bash
# Generate new JWT secret
openssl rand -hex 32

# Update .env file
JWT_SECRET=<new-secret>

# Restart application
docker-compose restart app
```

**B. Reset admin password:**
```bash
# Generate secure password
openssl rand -base64 24

# Update .env file
ADMIN_PASSWORD=<new-password>

# Restart application
docker-compose restart app
```

### 6. Market Data Provider Errors

**Symptoms**:
- "No data available" errors
- Stale prices
- Provider timeouts

**Diagnosis**:
```bash
# Test API keys directly
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$FINNHUB_API_KEY"

# Check provider status
curl -s http://localhost:8000/api/v1/market/providers | jq
```

**Solutions**:

**A. Verify API keys:**
```bash
# Check API key validity at provider websites
# Finnhub: https://finnhub.io/dashboard
# TwelveData: https://twelvedata.com/account/api

# Update keys in .env if expired
```

**B. Check rate limits:**
```bash
# Monitor API usage
docker-compose logs app | grep -i "rate\|limit\|quota"

# Wait for reset or upgrade to paid plans
```

**C. Provider failover:**
```bash
# System should automatically failover
# Check logs for failover messages
docker-compose logs app | grep -i "failover\|backup\|provider"
```

### 7. WebSocket Connection Issues

**Symptoms**:
- Real-time updates not working
- WebSocket connection errors
- Client disconnections

**Diagnosis**:
```bash
# Test WebSocket connection
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:8000/ws
```

**Solutions**:

**A. Proxy configuration (if using Nginx):**
```nginx
# Add WebSocket support to Nginx config
location / {
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

**B. Check firewall:**
```bash
# Ensure WebSocket ports are open
sudo ufw status
sudo ufw allow 8000
```

### 8. Database/Redis Issues

**Symptoms**:
- "Connection to Redis failed"
- Data persistence issues
- Cache misses

**Diagnosis**:
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis

# Check memory usage
docker-compose exec redis redis-cli info memory
```

**Solutions**:

**A. Restart Redis:**
```bash
# Restart Redis container
docker-compose restart redis

# Verify connection
docker-compose exec redis redis-cli ping
```

**B. Clear corrupted data:**
```bash
# Backup first
docker-compose exec redis redis-cli BGSAVE

# Clear database
docker-compose exec redis redis-cli FLUSHDB

# Restart application
docker-compose restart app
```

**C. Check disk space:**
```bash
# Redis needs disk space for persistence
df -h

# Clean up if needed
docker system prune -f
```

## 🔧 Advanced Troubleshooting

### Performance Debugging

**Profile Application Performance**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Monitor slow requests
docker-compose logs app | grep -i "slow\|timeout\|performance"

# Check database query performance
docker-compose exec redis redis-cli --latency
```

**Memory Leak Detection**:
```bash
# Monitor memory growth
while true; do
    echo "$(date): $(docker stats --no-stream --format 'table {{.MemUsage}}' operation-app-1)"
    sleep 300
done > memory_usage.log

# Analyze pattern
tail -f memory_usage.log
```

### Network Troubleshooting

**DNS Issues**:
```bash
# Test DNS resolution
nslookup finnhub.io
dig api.twelvedata.com

# Use public DNS if needed
echo 'nameserver 8.8.8.8' > /etc/resolv.conf
```

**Connection Issues**:
```bash
# Test external connectivity
ping -c 4 finnhub.io
curl -I https://api.twelvedata.com

# Check proxy settings
echo $http_proxy
echo $https_proxy
```

### Container Debugging

**Container Shell Access**:
```bash
# Get shell in running container
docker-compose exec app bash

# Or start debug container
docker run -it --rm operation-app bash
```

**File System Issues**:
```bash
# Check file permissions
docker-compose exec app ls -la /app

# Check disk usage in container
docker-compose exec app df -h
```

## 📋 Troubleshooting Checklists

### Startup Issues Checklist

- [ ] Check Docker is running: `docker --version`
- [ ] Verify docker-compose.yml syntax: `docker-compose config`
- [ ] Check .env file exists and has required variables
- [ ] Verify port 8000 is available: `netstat -tlnp | grep :8000`
- [ ] Check available memory: `free -h`
- [ ] Review container logs: `docker-compose logs app`
- [ ] Try clean rebuild: `docker-compose build --no-cache`

### Trading Issues Checklist

- [ ] Verify trading is started: `curl http://localhost:8000/api/v1/trading/status`
- [ ] Check portfolio balance: `curl http://localhost:8000/api/v1/trading/portfolio`
- [ ] Verify market data: `curl http://localhost:8000/api/v1/market/price/AAPL`
- [ ] Check strategy configuration: Review strategy parameters
- [ ] Verify API keys: Test external API calls
- [ ] Check market hours: Ensure appropriate instruments
- [ ] Review confidence thresholds: May be too restrictive

### Performance Issues Checklist

- [ ] Monitor resource usage: `docker stats`
- [ ] Check Redis memory: `docker-compose exec redis redis-cli info memory`
- [ ] Review log file sizes: `du -sh /var/lib/docker/containers/*/`
- [ ] Check disk space: `df -h`
- [ ] Monitor API rate limits: Review provider status
- [ ] Optimize symbol count: Reduce if necessary
- [ ] Clear caches: `docker-compose exec redis redis-cli FLUSHDB`

## 🆘 Emergency Procedures

### Emergency Stop
```bash
# Immediate trading halt
curl -X POST http://localhost:8000/api/v1/trading/stop

# Complete system shutdown
docker-compose down

# Force kill if unresponsive
docker-compose kill
```

### System Recovery
```bash
# Restore from backup
docker-compose down
tar -xzf backup-YYYYMMDD.tar.gz
docker-compose up -d

# Verify recovery
curl http://localhost:8000/health
```

### Data Recovery
```bash
# Restore Redis data
docker-compose exec redis redis-cli FLUSHALL
docker-compose exec redis redis-cli --rdb backup.rdb
docker-compose restart app
```

## 📞 Getting Help

### Log Collection for Support
```bash
#!/bin/bash
# collect_logs.sh - Gather diagnostic information

SUPPORT_DIR="support-$(date +%Y%m%d-%H%M)"
mkdir -p "$SUPPORT_DIR"

# System information
uname -a > "$SUPPORT_DIR/system_info.txt"
docker --version >> "$SUPPORT_DIR/system_info.txt"
docker-compose --version >> "$SUPPORT_DIR/system_info.txt"

# Container status
docker-compose ps > "$SUPPORT_DIR/container_status.txt"

# Application logs
docker-compose logs app > "$SUPPORT_DIR/app_logs.txt"
docker-compose logs redis > "$SUPPORT_DIR/redis_logs.txt"

# Configuration (sanitized)
cp .env.example "$SUPPORT_DIR/"
grep -v -E "(SECRET|PASSWORD|KEY)" .env > "$SUPPORT_DIR/config_sanitized.txt"

# System resources
docker stats --no-stream > "$SUPPORT_DIR/resource_usage.txt"
df -h > "$SUPPORT_DIR/disk_usage.txt"

# Create archive
tar -czf "$SUPPORT_DIR.tar.gz" "$SUPPORT_DIR"
echo "Support package created: $SUPPORT_DIR.tar.gz"
```

### Common Support Information

When seeking help, provide:

1. **System Information**:
   - Operating system and version
   - Docker and Docker Compose versions
   - Available memory and disk space

2. **Error Details**:
   - Exact error messages
   - Steps to reproduce the issue
   - When the issue started

3. **Configuration**:
   - Sanitized environment variables
   - docker-compose.yml contents
   - Any custom modifications

4. **Logs**:
   - Recent application logs
   - Container status output
   - System resource usage

This comprehensive troubleshooting guide should help resolve most common issues with the trading system. For persistent problems, collect diagnostic information using the provided scripts and seek additional support.