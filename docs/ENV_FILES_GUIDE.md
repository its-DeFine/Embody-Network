# Environment Files Guide
*Last Updated: 2025-08-17*

## 🟢 ACTIVE FILES (Used by Docker)

### 1. `/home/geo/operation/.env`
- **Used by:** `docker-compose.manager.yml`
- **Purpose:** Manager + Livepeer Gateway configuration
- **Based on:** Actual pipeline from `/home/geo/pipelines_tests/agent-net`
- **Key Settings:**
  - Security: JWT_SECRET, ADMIN_PASSWORD
  - Gateway: ETH_RPC_URL, ETH_PASSWORD, ORCHESTRATOR_ADDRESSES
  - Monitoring: ORCHESTRATOR_SECRET, PROOF_INTERVAL

### 2. `/home/geo/operation/autonomy/.env`
- **Used by:** `autonomy/docker-compose.yml`
- **Purpose:** VTuber Autonomy + BYOC Orchestrator
- **Key Settings:**
  - AI Services: OPENAI_API_KEY, ELEVENLABS_API_KEY
  - Ollama: Local LLM configuration
  - BYOC: Livepeer orchestrator settings (end of file)

## 📝 TEMPLATE FILES (For Setup)

### `.env.example`
- Clean template with placeholders
- Shows required variables
- Good for new installations

### `.env.manager-template`
- Complete manager configuration
- Includes actual pipeline values
- Ready to copy and use

### `.env.autonomy-template`
- Complete autonomy configuration
- Based on pipeline orchestrator settings
- Includes BYOC worker configuration

## 🚀 Quick Setup

### For Manager (with Gateway):
```bash
# Option 1: Use template with pipeline values
cp .env.manager-template .env

# Option 2: Use basic template
cp .env.example .env

# Edit with your values:
nano .env
# Main things to update:
# - JWT_SECRET (if you want custom)
# - ETH_PASSWORD (if needed)
# - ORCHESTRATOR_ADDRESSES (your orchestrators)

# Start services
docker-compose -f docker-compose.manager.yml up -d
```

### For Autonomy (with BYOC):
```bash
cd autonomy

# If starting fresh:
cp ../.env.autonomy-template .env

# Update API keys:
nano .env
# Update: OPENAI_API_KEY, ELEVENLABS_API_KEY

# Start services
docker-compose up -d
```

## 📍 Current Structure

```
/home/geo/operation/
├── .env                    ✅ ACTIVE (Manager + Gateway)
├── .env.example            📝 Basic template
├── .env.manager-template   📝 Complete manager template
├── .env.autonomy-template  📝 Complete autonomy template
└── autonomy/
    ├── .env               ✅ ACTIVE (Autonomy + BYOC)
    ├── .env.example       📝 Basic template
    └── .env.autonomy.dev  📝 Dev template
```

## 🔑 Key Variables Explained

### Gateway Variables (from pipeline):
- `ETH_RPC_URL`: Arbitrum RPC endpoint (default: public RPC)
- `ETH_PASSWORD`: Can be empty for BYOC
- `ORCHESTRATOR_ADDRESSES`: Comma-separated list of orchestrators
- `MAX_PRICE_PER_UNIT`: 70000000000000 (from pipeline)

### Orchestrator Variables (from pipeline):
- `LIVEPEER_ORCH_SECRET`: orch-secret (shared secret)
- `PRICE_PER_UNIT`: 65113436683036 (orchestrator pricing)
- `TICKET_EV`: 18087065745288 (ticket expected value)
- `ETH_ORCH_ADDRESS`: Can be empty for BYOC

## ❌ REMOVED FILES
- `.env.central-manager` - Had outdated trading variables
- `.env.livepeer` - Consolidated into main .env
- `.env.orchestrator` - Not needed

## 📋 Notes
- NO ETH_ACCOUNT_ADDRESS needed (was incorrectly added)
- ETH_PASSWORD can be empty for BYOC setup
- Orchestrator addresses are configured manually, not via individual env vars
- All values taken from actual working pipeline configuration