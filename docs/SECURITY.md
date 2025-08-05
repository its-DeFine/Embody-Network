# Security Guide

**Comprehensive security configuration and best practices for the 24/7 Trading System.**

## 🔒 Security Overview

The trading system implements multiple layers of security to protect against unauthorized access, data breaches, and financial fraud. Security is critical when dealing with real money and market data.

### Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Security Layers                          │
├─────────────────────────────────────────────────────────────┤
│  1. Network Security (Firewall, SSL/TLS)                   │
│  2. Application Security (JWT, PGP Authentication)         │  
│  3. Data Security (Encryption, Secure Storage)             │
│  4. Infrastructure Security (Container, Host Hardening)    │
│  5. Operational Security (Audit Logs, Monitoring)          │
└─────────────────────────────────────────────────────────────┘
```

## 🛡️ Authentication & Authorization

### ✅ SECURITY STATUS: All Critical Vulnerabilities Fixed

**Security Hardening Complete (2025-08-04)**:
- ✅ **Authentication Architecture** - Centralized and consistent
- ✅ **Authorization Controls** - Role-based access implemented  
- ✅ **Input Validation** - Comprehensive protection added
- ✅ **Rate Limiting** - API abuse protection active
- ✅ **Error Handling** - Silent failures eliminated
- ✅ **Private Key Security** - Repository cleaned
- ✅ **WebSocket Security** - JWT validation implemented

### JWT-Based Authentication

**Centralized Authentication System** (`app/dependencies.py`):
```python
# All authentication now centralized in dependencies.py
from app.dependencies import get_current_user, require_admin, require_trader

# Enhanced JWT tokens with role-based access
{
  "sub": "user@domain.com",
  "role": "trader",  # admin/trader/viewer
  "permissions": ["trading:start", "trading:stop"],
  "exp": timestamp
}
```

**Configuration**:
```env
# Generate secure JWT secret (minimum 32 characters)
JWT_SECRET=your-super-secure-jwt-secret-minimum-32-characters-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### Role-Based Authorization System

**Three Security Roles**:

**1. Admin Role**:
- Full system access and configuration
- User management and security settings
- Trading operations and system control
- Audit log access and monitoring

**2. Trader Role**:
- Trading operations (start, stop, execute)
- Market data and portfolio access
- Limited to trading functions only

**3. Viewer Role**:
- Read-only access to market data
- Portfolio viewing only
- No trading or configuration access

**API Endpoint Protection**:
```python
# Trading endpoints now secured by role
@router.post("/start")
async def start_trading(
    request: TradingStartRequest,
    current_user: dict = Depends(require_trading_access)  # Trader or Admin only
)

@router.post("/config") 
async def update_config(
    request: ConfigRequest,
    current_user: dict = Depends(require_admin)  # Admin only
)
```

**Generate Secure JWT Secret**:
```bash
# Generate cryptographically secure secret
openssl rand -hex 32

# Or using Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**API Authentication**:
```bash
# Login to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-admin-password"}'

# Use token for authenticated requests
curl -H "Authorization: Bearer <jwt-token>" \
  http://localhost:8000/api/v1/trading/portfolio
```

### Admin Password Security

**Password Requirements**:
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, and symbols
- Not based on dictionary words
- Unique to this system

**Generate Secure Password**:
```bash
# Generate secure password
openssl rand -base64 24

# Or using custom characters
python3 -c "import secrets, string; chars=string.ascii_letters+string.digits+'!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range(16)))"
```

### PGP-Based Security (Advanced)

**Setup PGP Keys**:
```bash
# Generate PGP key pair
gpg --gen-key

# Export public key
gpg --armor --export your-email@domain.com > keys/public.asc

# Export private key (keep secure!)
gpg --armor --export-secret-keys your-email@domain.com > keys/private.asc

# Set secure permissions
chmod 700 keys/
chmod 600 keys/*.asc
```

**PGP Configuration**:
```env
# PGP settings
PGP_ENABLED=true
PGP_PUBLIC_KEY_PATH=keys/public.asc
PGP_PRIVATE_KEY_PATH=keys/private.asc
PGP_PASSPHRASE=your-pgp-passphrase
```

## 🌐 Network Security

### Firewall Configuration

**UFW (Ubuntu Firewall)**:
```bash
# Enable firewall
sudo ufw enable

# Allow SSH (change port if using non-standard)
sudo ufw allow 22/tcp

# Allow trading API
sudo ufw allow 8000/tcp

# Block direct Redis access from external
sudo ufw deny 6379/tcp

# Allow from specific IP only (recommended)
sudo ufw allow from YOUR_IP_ADDRESS to any port 8000

# Check firewall status
sudo ufw status verbose
```

**iptables Configuration**:
```bash
# Basic iptables rules
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6379 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6379 -j DROP
sudo iptables -P INPUT DROP

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

### SSL/TLS Configuration

**Install SSL Certificate**:
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot certonly --standalone -d your-trading-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

**Nginx SSL Configuration**:
```nginx
# /etc/nginx/sites-available/trading
server {
    listen 80;
    server_name your-trading-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-trading-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-trading-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-trading-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to trading application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}
```

## 🔐 Data Security

### Environment Variables Security

**Secure .env File**:
```bash
# Set secure permissions
chmod 600 .env

# Verify ownership
chown $USER:$USER .env

# Never commit .env to version control
echo ".env" >> .gitignore
```

**Environment Variables Validation**:
```python
# app/config.py - Environment validation
from pydantic import BaseSettings, validator
import secrets

class Settings(BaseSettings):
    jwt_secret: str
    admin_password: str
    
    @validator('jwt_secret')
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError('JWT_SECRET must be at least 32 characters')
        return v
    
    @validator('admin_password')
    def validate_admin_password(cls, v):
        if len(v) < 12:
            raise ValueError('ADMIN_PASSWORD must be at least 12 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('ADMIN_PASSWORD must contain uppercase letters')
        if not any(c.islower() for c in v):
            raise ValueError('ADMIN_PASSWORD must contain lowercase letters')
        if not any(c.isdigit() for c in v):
            raise ValueError('ADMIN_PASSWORD must contain digits')
        return v
```

### API Key Security

**API Key Management**:
```env
# Store API keys securely
FINNHUB_API_KEY=your-finnhub-key-here
TWELVEDATA_API_KEY=your-twelvedata-key-here

# Rotate keys regularly (monthly)
# Keep backup keys for failover
FINNHUB_API_KEY_BACKUP=your-backup-finnhub-key
```

**API Key Rotation Script**:
```bash
#!/bin/bash
# api_key_rotation.sh

echo "Starting API key rotation..."

# Backup current keys
cp .env .env.backup.$(date +%Y%m%d)

# Update with new keys (manual process)
echo "Please update API keys in .env file"
echo "Press enter when complete..."
read

# Test new keys
echo "Testing new API keys..."
curl -s "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$FINNHUB_API_KEY" | jq .c

if [ $? -eq 0 ]; then
    echo "API key rotation successful"
    docker-compose restart app
else
    echo "API key test failed, reverting..."
    cp .env.backup.$(date +%Y%m%d) .env
    docker-compose restart app
fi
```

### Data Encryption

**Redis Data Encryption**:
```bash
# Enable Redis AUTH
echo "requirepass your-redis-password" >> redis.conf

# Update Redis URL
export REDIS_URL="redis://:your-redis-password@localhost:6379"
```

**Sensitive Data Encryption**:
```python
# app/security/encryption.py
from cryptography.fernet import Fernet
import os

class DataEncryption:
    def __init__(self):
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            print(f"Generated encryption key: {key.decode()}")
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
    
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# Usage for sensitive trading data
encryptor = DataEncryption()
encrypted_position = encryptor.encrypt(json.dumps(position_data))
```

## 🔍 Audit & Logging

### Comprehensive Audit Logging

**Audit Configuration**:
```python
# app/infrastructure/monitoring/audit_logger.py
import logging
import json
from datetime import datetime

class AuditLogger:
    def __init__(self):
        self.audit_logger = logging.getLogger('audit')
        handler = logging.FileHandler('/var/log/trading/audit.log')
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)
    
    def log_trade(self, trade_data):
        self.audit_logger.info(json.dumps({
            'event': 'trade_executed',
            'timestamp': datetime.utcnow().isoformat(),
            'user': trade_data.get('user_id'),
            'symbol': trade_data.get('symbol'),
            'action': trade_data.get('action'),
            'quantity': trade_data.get('quantity'),
            'price': trade_data.get('price')
        }))
    
    def log_auth(self, auth_data):
        self.audit_logger.info(json.dumps({
            'event': 'authentication',
            'timestamp': datetime.utcnow().isoformat(),
            'user': auth_data.get('user'),
            'ip': auth_data.get('ip'),
            'success': auth_data.get('success')
        }))
```

**Log Security Configuration**:
```bash
# Secure log directory
sudo mkdir -p /var/log/trading
sudo chown $USER:$USER /var/log/trading
sudo chmod 750 /var/log/trading

# Log rotation
cat > /etc/logrotate.d/trading <<EOF
/var/log/trading/*.log {
    daily
    rotate 365
    compress
    delaycompress
    missingok
    notifempty
    create 640 $USER $USER
    postrotate
        docker-compose restart app
    endscript
}
EOF
```

### Security Monitoring

**Intrusion Detection**:
```bash
# Install fail2ban
sudo apt install fail2ban

# Configure fail2ban for trading app
cat > /etc/fail2ban/jail.local <<EOF
[trading-auth]
enabled = true
port = 8000
filter = trading-auth
logpath = /var/log/trading/audit.log
maxretry = 5
bantime = 3600
findtime = 600

[trading-api]
enabled = true
port = 8000
filter = trading-api
logpath = /var/log/trading/app.log
maxretry = 10
bantime = 1800
findtime = 300
EOF

# Create filters
cat > /etc/fail2ban/filter.d/trading-auth.conf <<EOF
[Definition]
failregex = .*"event": "authentication".*"success": false.*"ip": "<HOST>"
ignoreregex =
EOF
```

**Automated Security Monitoring**:
```bash
#!/bin/bash
# security_monitor.sh

LOG_FILE="/var/log/trading/security.log"

# Monitor failed authentications
failed_auths=$(grep '"success": false' /var/log/trading/audit.log | wc -l)
if [ $failed_auths -gt 10 ]; then
    echo "$(date): WARNING: $failed_auths failed authentication attempts" >> $LOG_FILE
fi

# Monitor unusual trading patterns
large_trades=$(grep -E '"quantity": [0-9]{4,}' /var/log/trading/audit.log | wc -l)
if [ $large_trades -gt 5 ]; then
    echo "$(date): WARNING: $large_trades large trades detected" >> $LOG_FILE
fi

# Monitor system resource abuse
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
if (( $(echo "$cpu_usage > 80" | bc -l) )); then
    echo "$(date): WARNING: High CPU usage: $cpu_usage%" >> $LOG_FILE
fi
```

## 🚨 Incident Response

### Security Incident Response Plan

**Phase 1: Detection and Analysis**
```bash
#!/bin/bash
# incident_detection.sh

# Check for suspicious activities
echo "=== Security Incident Detection ==="

# 1. Check failed login attempts
echo "Failed logins in last hour:"
grep '"success": false' /var/log/trading/audit.log | \
    grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" | wc -l

# 2. Check unusual trading volumes
echo "Large trades in last hour:"
grep -E '"quantity": [0-9]{4,}' /var/log/trading/audit.log | \
    grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" | wc -l

# 3. Check system resource usage
echo "Current system load:"
uptime

# 4. Check network connections
echo "Active connections:"
netstat -an | grep :8000 | wc -l
```

**Phase 2: Containment**
```bash
#!/bin/bash
# incident_containment.sh

echo "=== Security Incident Containment ==="

# 1. Stop trading immediately
curl -X POST http://localhost:8000/api/v1/trading/stop

# 2. Block suspicious IPs
suspicious_ips=$(grep '"success": false' /var/log/trading/audit.log | \
    grep "$(date '+%Y-%m-%d')" | \
    jq -r '.ip' | sort | uniq -c | sort -nr | head -5 | awk '$1 > 10 {print $2}')

for ip in $suspicious_ips; do
    sudo ufw insert 1 deny from $ip
    echo "Blocked IP: $ip"
done

# 3. Change admin password
echo "Generate new admin password:"
openssl rand -base64 24

# 4. Rotate JWT secret
echo "Generate new JWT secret:"
openssl rand -hex 32
```

**Phase 3: Recovery**
```bash
#!/bin/bash
# incident_recovery.sh

echo "=== Security Incident Recovery ==="

# 1. Update security credentials
echo "Update .env with new credentials"
echo "Restart system: docker-compose restart"

# 2. Verify system integrity
echo "Verifying system integrity:"
curl http://localhost:8000/health

# 3. Check data integrity
echo "Checking Redis data integrity:"
docker-compose exec redis redis-cli dbsize

# 4. Resume trading (manual decision)
echo "Manual decision required to resume trading"
echo "curl -X POST http://localhost:8000/api/v1/trading/start -d '{\"initial_capital\": 1000}'"
```

## 🔧 Security Best Practices

### Operational Security

**Daily Security Checklist**:
- [ ] Review authentication logs for failed attempts
- [ ] Check system resource usage for anomalies
- [ ] Verify SSL certificate validity
- [ ] Monitor unusual trading patterns
- [ ] Check firewall logs for blocked attempts

**Weekly Security Tasks**:
- [ ] Rotate API keys (if policy requires)
- [ ] Update system packages and security patches
- [ ] Review and analyze security logs
- [ ] Test backup and recovery procedures
- [ ] Verify audit log integrity

**Monthly Security Tasks**:
- [ ] Security vulnerability assessment
- [ ] Penetration testing (if applicable)
- [ ] Review and update security policies
- [ ] Security awareness training
- [ ] Disaster recovery testing

### Development Security

**Secure Coding Practices**:
```python
# Input validation
from pydantic import BaseModel, validator

class TradeRequest(BaseModel):
    symbol: str
    quantity: float
    
    @validator('symbol')
    def validate_symbol(cls, v):
        # Only allow alphanumeric and common trading symbols
        if not re.match(r'^[A-Z0-9.-]+$', v):
            raise ValueError('Invalid symbol format')
        return v
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0 or v > 1000000:  # Reasonable limits
            raise ValueError('Invalid quantity')
        return v

# SQL injection prevention (if using SQL)
# Always use parameterized queries
cursor.execute("SELECT * FROM trades WHERE symbol = %s", (symbol,))

# XSS prevention
from markupsafe import escape
safe_output = escape(user_input)
```

### Container Security

**Docker Security Hardening**:
```dockerfile
# Use non-root user
FROM python:3.11-slim
RUN groupadd -r trading && useradd -r -g trading trading
USER trading

# Minimal base image
FROM python:3.11-slim as base
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Read-only root filesystem
# In docker-compose.yml:
# read_only: true
# tmpfs:
#   - /tmp
#   - /var/run
```

**Container Runtime Security**:
```yaml
# docker-compose.yml security settings
version: '3.8'
services:
  app:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
```

This comprehensive security guide ensures the trading system is protected against common threats while maintaining operational efficiency and compliance with security best practices.