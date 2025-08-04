# Operations Guide

**Complete operational guide for monitoring, maintaining, and troubleshooting the 24/7 Trading System.**

## 📊 System Monitoring

### Health Checks

**Basic Health Check**:
```bash
# Quick system status
curl http://localhost:8000/health

# Expected response:
{
    "status": "healthy",
    "timestamp": "2025-08-04T14:30:00Z",
    "version": "1.0.0"
}
```

**Detailed System Status**:
```bash
# Comprehensive system status
curl http://localhost:8000/api/v1/trading/status

# Expected response:
{
    "trading_active": true,
    "strategies_running": 5,
    "market_data_connected": true,
    "redis_connected": true,
    "last_trade": "2025-08-04T14:25:00Z",
    "system_uptime": "2d 14h 25m"
}
```

### Real-time Monitoring

**Portfolio Monitoring**:
```bash
# Watch portfolio changes in real-time
watch -n 5 'curl -s http://localhost:8000/api/v1/trading/portfolio | jq'

# Monitor specific metrics
watch -n 10 'curl -s http://localhost:8000/api/v1/trading/performance | jq .daily_pnl'
```

**Log Monitoring**:
```bash
# Follow live application logs
docker-compose logs -f app

# Monitor trading activity
docker-compose logs -f app | grep -i "trade\|buy\|sell\|profit\|loss"

# Watch for errors
docker-compose logs -f app | grep -i "error\|exception\|failed"
```

**Resource Monitoring**:
```bash
# Monitor container resources
docker stats

# Monitor system resources
htop

# Check disk space
df -h

# Monitor Redis memory usage
docker-compose exec redis redis-cli info memory
```

## 🔧 Maintenance Tasks

### Daily Maintenance

**Morning Checklist** (5 minutes):
```bash
#!/bin/bash
# Daily morning check script

echo "=== Daily System Check - $(date) ==="

# 1. Health check
echo "1. System Health:"
curl -s http://localhost:8000/health | jq .status

# 2. Trading status
echo "2. Trading Status:"
curl -s http://localhost:8000/api/v1/trading/status | jq .trading_active

# 3. Portfolio value
echo "3. Portfolio Value:"
curl -s http://localhost:8000/api/v1/trading/portfolio | jq '.total_value, .daily_pnl'

# 4. Recent errors
echo "4. Recent Errors:"
docker-compose logs --since="24h" app | grep -i error | tail -5

# 5. Disk space
echo "5. Disk Space:"
df -h /

# 6. Memory usage
echo "6. Memory Usage:"
free -h

echo "=== Check Complete ==="
```

**Evening Checklist** (10 minutes):
```bash
#!/bin/bash
# Daily evening maintenance script

echo "=== Daily Maintenance - $(date) ==="

# 1. Performance summary
echo "1. Daily Performance:"
curl -s http://localhost:8000/api/v1/trading/performance?period=daily | jq

# 2. Backup Redis data
echo "2. Backing up Redis data:"
docker-compose exec redis redis-cli BGSAVE

# 3. Log rotation check
echo "3. Log file sizes:"
du -sh /var/lib/docker/containers/*/

# 4. Strategy performance
echo "4. Strategy Performance:"
curl -s http://localhost:8000/api/v1/trading/strategies | jq '.[] | {name, win_rate, total_pnl}'

# 5. Cleanup old logs (keep 30 days)
echo "5. Cleaning old logs:"
find /var/log -name "*.log" -mtime +30 -delete

echo "=== Maintenance Complete ==="
```

### Weekly Maintenance

**Weekly Tasks**:
```bash
#!/bin/bash
# Weekly maintenance script

echo "=== Weekly Maintenance - $(date) ==="

# 1. Full system backup
echo "1. Creating full backup:"
tar -czf "trading-backup-$(date +%Y%m%d).tar.gz" \
    .env docker-compose.yml keys/ \
    --exclude='*.log' --exclude='__pycache__'

# 2. Redis data backup
echo "2. Redis backup:"
docker-compose exec redis redis-cli --rdb "backup-$(date +%Y%m%d).rdb"

# 3. Performance analysis
echo "3. Weekly Performance Analysis:"
curl -s http://localhost:8000/api/v1/trading/performance?period=weekly | \
    jq '{total_return, win_rate, total_trades, sharpe_ratio}'

# 4. Docker cleanup
echo "4. Docker cleanup:"
docker system prune -f
docker volume prune -f

# 5. Update system packages
echo "5. System updates:"
sudo apt update && sudo apt upgrade -y

# 6. Certificate renewal check (if using SSL)
echo "6. SSL certificate check:"
sudo certbot renew --dry-run

echo "=== Weekly Maintenance Complete ==="
```

### Monthly Maintenance

**Monthly Performance Review**:
```bash
# Generate monthly report
curl -s http://localhost:8000/api/v1/trading/performance?period=monthly | \
    jq '{
        period: "monthly",
        total_return: .total_return,
        total_trades: .total_trades,
        win_rate: .win_rate,
        profit_factor: .profit_factor,
        max_drawdown: .max_drawdown,
        sharpe_ratio: .sharpe_ratio
    }' > "monthly-report-$(date +%Y%m).json"
```

## 🚨 Alerting & Notifications

### Critical Alerts

**System Down Alert**:
```bash
#!/bin/bash
# Check if system is responding
if ! curl -f -s http://localhost:8000/health > /dev/null; then
    echo "CRITICAL: Trading system is DOWN at $(date)" | \
        mail -s "CRITICAL: Trading System Alert" admin@company.com
fi
```

**High Loss Alert**:
```bash
#!/bin/bash
# Check daily P&L
daily_pnl=$(curl -s http://localhost:8000/api/v1/trading/portfolio | jq -r .daily_pnl)

if (( $(echo "$daily_pnl < -50" | bc -l) )); then
    echo "WARNING: Daily loss exceeds $50: $daily_pnl at $(date)" | \
        mail -s "WARNING: High Loss Alert" admin@company.com
fi
```

**Performance Degradation Alert**:
```bash
#!/bin/bash
# Check if system stopped trading
last_trade=$(curl -s http://localhost:8000/api/v1/trading/status | jq -r .last_trade)
current_time=$(date -u +%s)
last_trade_time=$(date -d "$last_trade" +%s)
time_diff=$((current_time - last_trade_time))

# Alert if no trades in last 4 hours (14400 seconds)
if [ $time_diff -gt 14400 ]; then
    echo "WARNING: No trades in last 4 hours. Last trade: $last_trade" | \
        mail -s "WARNING: Trading Inactive" admin@company.com
fi
```

### Monitoring with Cron Jobs

**Setup automated monitoring**:
```bash
# Edit crontab
crontab -e

# Add monitoring jobs
# Check system health every 5 minutes
*/5 * * * * /home/user/scripts/health_check.sh

# Daily morning check at 9 AM
0 9 * * * /home/user/scripts/daily_morning_check.sh

# Daily evening maintenance at 6 PM
0 18 * * * /home/user/scripts/daily_evening_maintenance.sh

# Weekly backup on Sundays at 2 AM
0 2 * * 0 /home/user/scripts/weekly_maintenance.sh

# Monthly report on 1st of month at 1 AM
0 1 1 * * /home/user/scripts/monthly_report.sh
```

## 🛠️ Troubleshooting

### Common Issues and Solutions

**1. System Not Responding**:
```bash
# Check if containers are running
docker-compose ps

# If containers are down, restart
docker-compose up -d

# Check logs for errors
docker-compose logs app --tail 50

# If persistent, rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**2. No Trades Executing**:
```bash
# Check if trading is active
curl http://localhost:8000/api/v1/trading/status

# Check market data connectivity
curl http://localhost:8000/api/v1/market/providers

# Check strategy configurations
curl http://localhost:8000/api/v1/trading/strategies

# Restart trading if needed
curl -X POST http://localhost:8000/api/v1/trading/stop
curl -X POST http://localhost:8000/api/v1/trading/start -d '{"initial_capital": 1000}'
```

**3. High Resource Usage**:
```bash
# Check container stats
docker stats

# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Reduce symbol count if needed
# Edit TARGET_SYMBOLS in .env
docker-compose restart app

# Clear Redis cache if needed
docker-compose exec redis redis-cli FLUSHDB
```

**4. API Errors**:
```bash
# Test API keys
curl -H "Authorization: Bearer $FINNHUB_API_KEY" \
    "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$FINNHUB_API_KEY"

# Check rate limits
curl http://localhost:8000/api/v1/market/providers

# Rotate to backup providers if needed
```

### Advanced Troubleshooting

**Database Issues**:
```bash
# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Check Redis memory and performance
docker-compose exec redis redis-cli info

# Backup and restart Redis if needed
docker-compose exec redis redis-cli BGSAVE
docker-compose restart redis
```

**Performance Issues**:
```bash
# Profile application performance
docker-compose exec app python -m cProfile -o profile.stats app/main.py

# Check slow queries and bottlenecks
docker-compose logs app | grep -i "slow\|timeout\|performance"

# Monitor network connectivity
ping -c 4 finnhub.io
ping -c 4 api.twelvedata.com
```

**Memory Leaks**:
```bash
# Monitor memory growth over time
while true; do
    echo "$(date): $(docker stats --no-stream --format 'table {{.MemUsage}}' operation-app-1)"
    sleep 300  # Check every 5 minutes
done

# If memory leak detected, restart container
docker-compose restart app
```

## 📈 Performance Optimization

### Optimization Strategies

**1. Database Optimization**:
```bash
# Redis performance tuning
echo 'maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000' > redis.conf

# Apply Redis config
docker-compose down
docker-compose up -d
```

**2. Application Optimization**:
```bash
# Increase worker processes
echo 'services:
  app:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2.0"' >> docker-compose.override.yml
```

**3. Network Optimization**:
```bash
# DNS optimization
echo 'nameserver 8.8.8.8
nameserver 8.8.4.4' > /etc/resolv.conf

# Connection pooling
export HTTPX_POOL_CONNECTIONS=20
export HTTPX_POOL_MAXSIZE=50
```

### Monitoring Tools Integration

**Prometheus Metrics** (Advanced):
```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

**Log Analysis with ELK Stack** (Advanced):
```yaml
# docker-compose.logging.yml  
version: '3.8'
services:
  elasticsearch:
    image: elasticsearch:7.14.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"

  kibana:
    image: kibana:7.14.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

## 🔄 Backup and Recovery

### Backup Strategy

**Automated Backup Script**:
```bash
#!/bin/bash
# Comprehensive backup script

BACKUP_DIR="/backups/trading-$(date +%Y%m%d-%H%M)"
mkdir -p "$BACKUP_DIR"

# 1. Application data
tar -czf "$BACKUP_DIR/app-data.tar.gz" \
    .env docker-compose.yml keys/ scripts/

# 2. Redis data  
docker-compose exec redis redis-cli --rdb "$BACKUP_DIR/redis-dump.rdb"

# 3. Logs
tar -czf "$BACKUP_DIR/logs.tar.gz" \
    /var/lib/docker/containers/*/

# 4. Configuration
cp -r docs/ "$BACKUP_DIR/docs/"

# 5. Upload to cloud storage (optional)
# aws s3 sync "$BACKUP_DIR" s3://trading-backups/

echo "Backup completed: $BACKUP_DIR"
```

### Disaster Recovery

**Recovery Procedure**:
```bash
#!/bin/bash
# Disaster recovery script

BACKUP_FILE="$1"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file>"
    exit 1
fi

echo "Starting disaster recovery from $BACKUP_FILE"

# 1. Stop current system
docker-compose down

# 2. Restore application files
tar -xzf "$BACKUP_FILE/app-data.tar.gz"

# 3. Restore Redis data
docker-compose up -d redis
sleep 10
docker-compose exec redis redis-cli FLUSHALL
docker-compose exec redis redis-cli --rdb "$BACKUP_FILE/redis-dump.rdb"

# 4. Restart system
docker-compose up -d

# 5. Verify recovery
sleep 30
curl http://localhost:8000/health

echo "Disaster recovery completed"
```

This operations guide provides comprehensive procedures for maintaining a production trading system with proper monitoring, alerting, troubleshooting, and recovery capabilities.