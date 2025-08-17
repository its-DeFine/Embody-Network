# Environment Files Guide
*Last Updated: 2025-08-17*

## 🟢 ACTIVE FILES (Used by Docker)

These are the ONLY .env files that Docker actually reads:

### 1. `/home/geo/operation/.env`
- **Used by:** `docker-compose.manager.yml`
- **Purpose:** Configuration for Manager + Livepeer Gateway
- **Key Settings:**
  - JWT_SECRET, ADMIN_PASSWORD (security)
  - ETH_RPC_URL, ORCHESTRATOR_ADDRESSES (Livepeer)
  - REDIS_URL (Redis connection)
  - ORCHESTRATOR_SECRET (proof validation)

### 2. `/home/geo/operation/autonomy/.env`
- **Used by:** `autonomy/docker-compose.yml`
- **Purpose:** Configuration for VTuber Autonomy + BYOC services
- **Key Settings:**
  - OPENAI_API_KEY, ELEVENLABS_API_KEY (AI services)
  - OLLAMA settings (local LLM)
  - Livepeer BYOC configuration (at end of file)
  - Redis SCB settings

## 📝 TEMPLATE FILES (For Reference Only)

These files are NOT used by Docker, but provide templates/examples:

### `.env.example`
- Basic template with placeholder values
- Good for understanding required variables
- Safe to share (no secrets)

### `.env.central-manager` ⭐
- **RECOMMENDED**: Use this as source for `.env`
- Contains comprehensive manager settings
- Has good defaults and explanations
- Includes trading/market configurations

### `autonomy/.env.example`
- Basic template for autonomy cluster
- Minimal configuration example

### `autonomy/.env.autonomy.dev`
- Development environment template
- Useful for local development setup

## 🚀 Quick Setup

### For Manager Cluster:
```bash
# Option 1: Start from comprehensive template
cp .env.central-manager .env

# Option 2: Or use basic template
cp .env.example .env

# Then edit .env with your values:
nano .env
# Update: JWT_SECRET, ADMIN_PASSWORD, ETH_RPC_URL, ORCHESTRATOR_ADDRESSES

# Start the manager
docker-compose -f docker-compose.manager.yml up -d
```

### For Autonomy Cluster:
```bash
cd autonomy

# The .env already exists and is configured
# Just update your API keys:
nano .env
# Update: OPENAI_API_KEY, ELEVENLABS_API_KEY

# Start autonomy
docker-compose up -d
```

## ❌ DELETED FILES (No Longer Needed)

These files were removed to avoid confusion:
- `.env.livepeer` - Consolidated into main .env
- `.env.orchestrator` - Not needed

## 📋 Environment Variable Priority

Docker Compose reads environment variables in this order:
1. Shell environment variables (export VAR=value)
2. `.env` file in same directory as docker-compose.yml
3. Default values in docker-compose.yml (${VAR:-default})

## 🔑 Security Notes

- **NEVER** commit `.env` files with real secrets
- `.env` files are in `.gitignore` for protection
- Use `.env.example` for sharing configuration structure
- Rotate secrets regularly in production

## 📍 File Locations Summary

```
/home/geo/operation/
├── .env                    ✅ ACTIVE (Manager)
├── .env.example            📝 Template
├── .env.central-manager    📝 Template (Recommended)
└── autonomy/
    ├── .env               ✅ ACTIVE (Autonomy)
    ├── .env.example       📝 Template
    └── .env.autonomy.dev  📝 Template
```