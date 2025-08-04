# Production Deployment Guide

**Complete guide for deploying the 24/7 Autonomous Trading System to production.**

## 🚀 Quick Deploy (30 seconds)

```bash
# Clone, configure, and start trading in one command
git clone <repo-url> && cd operation && \
cp .env.example .env && \
docker-compose up -d && \
sleep 30 && \
curl -X POST "http://localhost:8000/api/v1/trading/start" \
  -H "Content-Type: application/json" \
  -d '{"initial_capital": 1000.0}'
```

## 📋 Prerequisites

### System Requirements

**Minimum (Development):**
- CPU: 2 cores, 2.0 GHz
- RAM: 4GB  
- Storage: 20GB SSD
- Network: Stable internet (>10 Mbps)

**Recommended (Production):**
- CPU: 4+ cores, 3.0+ GHz
- RAM: 8GB+
- Storage: 50GB+ SSD with backup
- Network: Redundant internet connections
- OS: Linux (Ubuntu 20.04+), macOS, Windows with WSL2

### Software Dependencies

```bash
# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Git
sudo apt update && sudo apt install git

# Python 3.9+ (optional, for local development)
sudo apt install python3.9 python3.9-pip python3.9-venv
```

### Required API Keys (Free Tiers)

Get free API keys from these providers:

1. **Finnhub** - https://finnhub.io/
   - Free: 60 calls/minute
   - Primary stock market data

2. **Twelve Data** - https://twelvedata.com/
   - Free: 800 calls/day
   - Real-time quotes & historical data

3. **MarketStack** - https://marketstack.com/
   - Free: 1,000 calls/month
   - Market data backup

4. **Alpha Vantage** (optional) - https://www.alphavantage.co/
   - Free: 5 calls/minute, 500/day
   - Additional market data source

## 🔧 Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd operation
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables:**
```env
# Security (CHANGE THESE!)
JWT_SECRET=your-super-secure-jwt-secret-minimum-32-characters
ADMIN_PASSWORD=your-secure-admin-password-12chars-min

# Market Data API Keys
FINNHUB_API_KEY=your-finnhub-api-key-here
TWELVEDATA_API_KEY=your-twelvedata-api-key-here
MARKETSTACK_API_KEY=your-marketstack-api-key-here

# Trading Configuration
INITIAL_CAPITAL=1000.00                    # Starting capital
MAX_POSITION_PCT=0.10                      # Max 10% per position
STOP_LOSS_PCT=0.02                         # 2% stop loss
TARGET_SYMBOLS=AAPL,MSFT,GOOGL,TSLA,NVDA  # Symbols to trade

# System Configuration
REDIS_URL=redis://redis:6379
ENVIRONMENT=production
LOG_LEVEL=INFO

# Optional: Additional API Keys
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
POLYGON_API_KEY=your-polygon-key
```

### 3. Production Security Configuration

**Generate Secure Secrets:**
```bash
# Generate JWT secret
openssl rand -hex 32

# Generate admin password
openssl rand -base64 24
```

**File Permissions:**
```bash
# Secure environment file
chmod 600 .env

# Secure keys directory (if using PGP)
chmod 700 keys/
chmod 600 keys/*.asc
```

### 4. Build and Deploy

```bash
# Build application
docker-compose build

# Start services in background
docker-compose up -d

# Verify deployment
docker-compose ps
```

Expected output:
```
NAME              COMMAND                  SERVICE   STATUS    PORTS
operation-app-1   "uvicorn app.main:ap…"   app       running   0.0.0.0:8000->8000/tcp
operation-redis-1 "docker-entrypoint.s…"   redis     running   0.0.0.0:6379->6379/tcp
```

### 5. Initialize Trading System

```bash
# Health check
curl http://localhost:8000/health

# Start trading with $1,000
curl -X POST "http://localhost:8000/api/v1/trading/start" \
  -H "Content-Type: application/json" \
  -d '{"initial_capital": 1000.0}'

# Verify trading started
curl http://localhost:8000/api/v1/trading/status
```

## 🔍 Verification & Testing

### 1. System Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Detailed system status
curl http://localhost:8000/api/v1/trading/status

# Check portfolio
curl http://localhost:8000/api/v1/trading/portfolio

# View recent logs
docker-compose logs -f app --tail 50
```

### 2. Market Data Verification

```bash
# Test market data providers
curl http://localhost:8000/api/v1/market/providers

# Get real-time price
curl http://localhost:8000/api/v1/market/price/AAPL

# Check data sources
curl http://localhost:8000/api/v1/market/status
```

### 3. Trading System Tests

```bash
# Check active strategies
curl http://localhost:8000/api/v1/trading/strategies

# View trading performance
curl http://localhost:8000/api/v1/trading/performance

# Check recent trades
curl http://localhost:8000/api/v1/trading/trades?limit=10
```

## 🔒 Security Hardening

### 1. Network Security

```bash
# UFW Firewall (Ubuntu)
sudo ufw enable
sudo ufw allow 22/tcp          # SSH
sudo ufw allow 8000/tcp        # Trading API
sudo ufw deny 6379/tcp         # Block external Redis access

# Or use iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6379 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6379 -j DROP
```

### 2. SSL/TLS Configuration (Production)

```bash
# Install Nginx for SSL termination
sudo apt install nginx certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-trading-domain.com

# Nginx configuration
cat > /etc/nginx/sites-available/trading <<EOF
server {
    listen 80;
    server_name your-trading-domain.com;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl;
    server_name your-trading-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-trading-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-trading-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/trading /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

### 3. Monitoring & Alerting

```bash
# Set up log monitoring
mkdir -p /var/log/trading
chown $(whoami):$(whoami) /var/log/trading

# Configure log rotation
cat > /etc/logrotate.d/trading <<EOF
/var/log/trading/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 644 $(whoami) $(whoami)
}
EOF
```

## 📊 Monitoring & Maintenance

### 1. System Monitoring

```bash
# Monitor container resources
docker stats

# View system metrics
curl http://localhost:8000/metrics

# Check Redis status
docker-compose exec redis redis-cli ping

# Monitor trading activity
watch -n 5 'curl -s http://localhost:8000/api/v1/trading/portfolio | jq'
```

### 2. Log Management

```bash
# View live logs
docker-compose logs -f app

# Search for errors
docker-compose logs app | grep -i error

# Check trading decisions
docker-compose logs app | grep -i "trade\|buy\|sell"

# Monitor P&L
docker-compose logs app | grep -i "pnl\|profit\|loss"
```

### 3. Backup Procedures

```bash
# Backup Redis data
docker-compose exec redis redis-cli BGSAVE

# Backup configuration
tar -czf trading-backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml keys/

# Backup trading data
mkdir -p backups/$(date +%Y%m%d)
docker-compose exec redis redis-cli --rdb backups/$(date +%Y%m%d)/dump.rdb
```

## 🚨 Emergency Procedures

### Emergency Stop Trading
```bash
# Immediate stop (keeps system running)
curl -X POST http://localhost:8000/api/v1/trading/stop

# Complete system shutdown
docker-compose down

# Force stop if unresponsive
docker-compose kill
```

### Disaster Recovery
```bash
# Restore from backup
docker-compose down
cp trading-backup-YYYYMMDD.tar.gz .
tar -xzf trading-backup-YYYYMMDD.tar.gz
docker-compose up -d

# Restore Redis data
docker-compose exec redis redis-cli FLUSHALL
docker-compose exec redis redis-cli --rdb /data/dump.rdb
```

## 🔧 Troubleshooting

### Common Issues

**1. Container fails to start:**
```bash
# Check logs
docker-compose logs app

# Rebuild image
docker-compose build --no-cache app
docker-compose up -d
```

**2. API errors:**
```bash
# Verify API keys
curl -H "Authorization: Bearer $FINNHUB_API_KEY" \
  "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$FINNHUB_API_KEY"

# Check environment
docker-compose exec app env | grep API_KEY
```

**3. Trading not executing:**
```bash
# Check market hours
curl http://localhost:8000/api/v1/market/status

# Verify balance
curl http://localhost:8000/api/v1/trading/portfolio

# Check strategy status
curl http://localhost:8000/api/v1/trading/strategies
```

**4. High resource usage:**
```bash
# Monitor resources
docker stats operation-app-1

# Reduce symbol count
# Edit TARGET_SYMBOLS in .env
docker-compose restart app
```

### Performance Optimization

```bash
# Increase memory limits
echo 'services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G' >> docker-compose.override.yml

# Optimize Redis
echo 'maxmemory 1gb
maxmemory-policy allkeys-lru' > redis.conf

# Restart with optimizations
docker-compose restart
```

## 🎯 Production Checklist

**Pre-Deployment:**
- [ ] API keys configured and tested
- [ ] Secure JWT_SECRET and ADMIN_PASSWORD set
- [ ] Firewall configured
- [ ] SSL certificate installed (if public)
- [ ] Backup procedures tested
- [ ] Monitoring setup complete

**Post-Deployment:**
- [ ] Health checks passing
- [ ] Trading system initialized
- [ ] Market data flowing
- [ ] Logs being captured
- [ ] Emergency procedures documented
- [ ] Team trained on operations

**Daily Operations:**
- [ ] Check system health
- [ ] Review trading performance  
- [ ] Monitor resource usage
- [ ] Verify backup completion
- [ ] Check error logs

---

## 📞 Support

**First-line troubleshooting:**
1. Check system health: `curl http://localhost:8000/health`
2. Review recent logs: `docker-compose logs -f app --tail 100`
3. Verify configuration: Check `.env` file for missing/incorrect values
4. Test API keys: Use manual API calls to verify external services

**Emergency contact procedures:**
- System automatically saves state for recovery
- All trades and positions persist in Redis
- Emergency stop available via API
- Complete system logs available via Docker

**Performance monitoring:**
- API response times via `/metrics`
- Trading performance via `/api/v1/trading/performance`
- System resources via `docker stats`
- Error rates via log analysis

The system is designed to be resilient and self-recovering. Most issues can be resolved by restarting services or adjusting configuration.