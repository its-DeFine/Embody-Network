# 24/7 Trading System Deployment Guide

## Overview

This guide covers the complete deployment of the 24/7 trading system with $1,000 starting capital. The system is designed to run continuously, executing real trades based on market data from multiple providers.

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores, 2.0 GHz
- **RAM**: 4GB (8GB recommended)
- **Storage**: 20GB SSD
- **Network**: Stable internet connection (>10 Mbps)
- **OS**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2

### Recommended Production Setup
- **CPU**: 4+ cores, 3.0 GHz
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD with backup
- **Network**: Redundant internet connections
- **Monitoring**: Dedicated monitoring server

## Prerequisites

### Software Dependencies
```bash
# Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Python 3.9+ (for local development)
sudo apt update
sudo apt install python3.9 python3.9-pip python3.9-venv

# Git
sudo apt install git
```

### API Keys Required
Get free API keys from these providers:
- **Finnhub**: https://finnhub.io/ (60 calls/minute free)
- **Twelve Data**: https://twelvedata.com/ (800 calls/day free)
- **MarketStack**: https://marketstack.com/ (1000 calls/month free)
- **Alpha Vantage** (optional): https://www.alphavantage.co/
- **Polygon.io** (optional): https://polygon.io/

## Installation Steps

### 1. Clone Repository
```bash
git clone https://github.com/your-repo/trading-system.git
cd trading-system
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env
```

**Required Environment Variables:**
```env
# Security
JWT_SECRET=your-super-secure-jwt-secret-here
ADMIN_PASSWORD=your-secure-admin-password

# API Keys
FINNHUB_API_KEY=your-finnhub-key
TWELVEDATA_API_KEY=your-twelvedata-key
MARKETSTACK_API_KEY=your-marketstack-key

# Trading Parameters
INITIAL_CAPITAL=1000.00
MAX_POSITION_PCT=0.10
STOP_LOSS_PCT=0.02
TARGET_SYMBOLS=AAPL,MSFT,GOOGL,TSLA,NVDA,META,AMZN
```

### 3. Production Configuration
For production deployment, use the production environment file:
```bash
cp .env.production .env
# Edit with your production values
```

### 4. Build and Deploy
```bash
# Build the application
docker-compose build

# Start the services
docker-compose up -d

# Check status
docker-compose ps
```

### 5. Initialize Trading System
```bash
# Check if services are running
curl http://localhost:8000/health

# Start trading with $1,000 capital
curl -X POST "http://localhost:8000/api/v1/trading/start" \
  -H "Content-Type: application/json" \
  -d '{"initial_capital": 1000.0}'
```

## Configuration Options

### Trading Parameters
```env
# Starting capital
INITIAL_CAPITAL=1000.00

# Risk management
MAX_POSITION_PCT=0.10      # Max 10% per position
STOP_LOSS_PCT=0.02         # 2% stop loss
COMMISSION_PCT=0.001       # 0.1% commission

# Target stocks
TARGET_SYMBOLS=AAPL,MSFT,GOOGL,TSLA,NVDA,META,AMZN

# Strategy settings
ARBITRAGE_MIN_PROFIT=0.001  # 0.1% minimum profit
SCALPING_TRADES_PER_DAY=35  # Target 35 trades/day
DCA_INTERVAL_HOURS=4        # DCA every 4 hours
```

### Security Settings
```env
# Authentication
JWT_SECRET=generate-a-secure-random-string
JWT_EXPIRATION_HOURS=24
ADMIN_PASSWORD=strong-password-here

# CORS (for production)
ALLOWED_ORIGINS=https://yourdomain.com
```

### Database & Cache
```env
# Redis (included in Docker Compose)
REDIS_URL=redis://redis:6379
REDIS_POOL_SIZE=20

# Optional: External database
DATABASE_URL=postgresql://user:pass@host:5432/trading_db
```

## API Endpoints

### Trading Control
- `POST /api/v1/trading/start` - Start trading system
- `POST /api/v1/trading/stop` - Stop trading system
- `GET /api/v1/trading/status` - Get system status

### Portfolio Management
- `GET /api/v1/trading/portfolio` - Portfolio status
- `GET /api/v1/trading/positions` - Current positions
- `GET /api/v1/trading/performance` - Performance metrics
- `GET /api/v1/trading/trades` - Trade history

### Monitoring
- `GET /health` - Basic health check
- `GET /api/v1/trading/health` - Detailed health check
- `WebSocket /api/v1/trading/ws` - Real-time updates

## Monitoring & Maintenance

### Health Checks
The system includes comprehensive health monitoring:
```bash
# Basic health check
curl http://localhost:8000/health

# Detailed trading health
curl http://localhost:8000/api/v1/trading/health

# System metrics
curl http://localhost:8000/metrics
```

### Log Monitoring
```bash
# View application logs
docker-compose logs -f app

# View trading-specific logs
docker-compose logs -f app | grep -i trading

# Export logs
docker-compose logs app > trading_logs.txt
```

### Performance Monitoring
```bash
# Check portfolio status
curl http://localhost:8000/api/v1/trading/portfolio

# Get performance metrics
curl http://localhost:8000/api/v1/trading/performance

# View recent trades
curl http://localhost:8000/api/v1/trading/trades?limit=20
```

## Backup & Recovery

### Data Backup
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M%S)
docker-compose exec -T redis redis-cli --rdb - > backup-${DATE}.rdb
docker-compose logs app > logs-${DATE}.txt
tar -czf trading-backup-${DATE}.tar.gz backup-${DATE}.rdb logs-${DATE}.txt
EOF

chmod +x backup.sh
./backup.sh
```

### Recovery
```bash
# Stop services
docker-compose down

# Restore Redis data
docker-compose up -d redis
docker-compose exec -T redis redis-cli --pipe < backup-YYYYMMDD-HHMMSS.rdb

# Restart application
docker-compose up -d app
```

## Security Considerations

### Production Security
1. **Change default passwords**
2. **Use strong JWT secrets**
3. **Enable HTTPS/TLS**
4. **Restrict API access**
5. **Regular security updates**

### Network Security
```yaml
# docker-compose.yml - Production additions
services:
  app:
    # Remove port mapping in production, use reverse proxy
    # ports:
    #   - "8000:8000"
    expose:
      - "8000"
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw enable
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw deny 8000/tcp  # Block direct access to app
```

## Troubleshooting

### Common Issues

**1. Trading System Not Starting**
```bash
# Check logs
docker-compose logs app

# Verify API keys
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_API_KEY"

# Check Redis connection
docker-compose exec redis redis-cli ping
```

**2. No Trading Activity**
```bash
# Check market hours
curl http://localhost:8000/api/v1/trading/health

# Verify data providers
curl http://localhost:8000/api/v1/market/status

# Check available cash
curl http://localhost:8000/api/v1/trading/portfolio
```

**3. High Memory Usage**
```bash
# Monitor resources
docker stats

# Restart services
docker-compose restart

# Check for memory leaks
docker-compose logs app | grep -i memory
```

### Emergency Procedures

**Stop All Trading Immediately**
```bash
curl -X POST http://localhost:8000/api/v1/trading/stop
```

**Emergency Shutdown**
```bash
docker-compose down
```

**Data Recovery**
```bash
# Access Redis directly
docker-compose exec redis redis-cli
> KEYS portfolio:*
> GET portfolio:main
```

## Scaling & Performance

### Horizontal Scaling
```yaml
# docker-compose.yml - Multiple instances
services:
  app:
    deploy:
      replicas: 3
  
  nginx:
    image: nginx:alpine
    depends_on:
      - app
```

### Performance Tuning
```env
# Environment variables
REDIS_POOL_SIZE=50
MAX_CONNECTIONS=100
WORKER_PROCESSES=4
```

### Load Balancing
```nginx
# nginx.conf
upstream trading_app {
    server app_1:8000;
    server app_2:8000;
    server app_3:8000;
}
```

## Maintenance Schedule

### Daily Tasks
- Monitor portfolio performance
- Check system health
- Review trade logs
- Backup critical data

### Weekly Tasks
- Update market data providers
- Review risk parameters
- Analyze performance metrics
- Security updates

### Monthly Tasks
- Full system backup
- Performance optimization
- Strategy parameter tuning
- Capacity planning

## Support & Contact

For technical support:
- Check logs first: `docker-compose logs -f`
- Review API documentation: `http://localhost:8000/docs`
- Monitor system health: `http://localhost:8000/health`

**Remember**: This system trades with real money. Always test thoroughly in a development environment first!