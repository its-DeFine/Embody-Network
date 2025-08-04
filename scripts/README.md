# Scripts Directory

**Production-ready setup and configuration scripts for the 24/7 Trading System.**

## Current Scripts

### ⚙️ `/setup/` - System Configuration
Essential setup scripts for configuring your trading system:

- **`configure_apis.sh`** - API configuration utility:
  - Interactive setup wizard for market data APIs
  - Tests API connectivity and key validity
  - Configures Finnhub, TwelveData, Alpha Vantage

- **`register_instance.py`** - Instance registration:
  - Registers trading instance with master manager
  - Handles PGP key exchange and authentication

### 🔐 Security & Keys
- **`setup_pgp_keys.sh`** - PGP key management:
  - Generates secure PGP key pairs
  - Configures key storage and permissions
  - Sets up secure communication channels

### 🤖 AI Integration  
- **`setup_ollama_models.sh`** - AI model setup:
  - Downloads and configures Ollama LLM models
  - Optimizes for trading analysis and decision making

## Quick Start

### 1. Configure API Keys
```bash
cd setup
./configure_apis.sh
# Follow interactive prompts to configure:
# - Finnhub API key
# - TwelveData API key  
# - Alpha Vantage API key
```

### 2. Setup Security (Optional)
```bash
./setup_pgp_keys.sh
# Generates PGP keys for secure communications
```

### 3. Setup AI Models (Optional)
```bash
./setup_ollama_models.sh
# Downloads Ollama models for enhanced trading intelligence
```

### 4. Start Trading System
```bash
# Return to root directory
cd ..

# Start the system
docker-compose up -d

# Verify system health
curl http://localhost:8000/health
```

## Script Details

### API Configuration (`setup/configure_apis.sh`)
- Interactive setup wizard
- Tests API connectivity
- Validates API keys
- Creates proper `.env` configuration
- Supports multiple data providers

### Instance Registration (`setup/register_instance.py`)
- Registers with master trading manager
- Handles secure key exchange
- Sets up cross-instance communication
- Required for multi-instance deployments

### PGP Key Setup (`setup_pgp_keys.sh`)
- Generates secure PGP key pairs
- Configures GPG keyring
- Sets proper file permissions
- Enables encrypted communications

### Ollama Setup (`setup_ollama_models.sh`)
- Downloads AI models optimized for trading
- Configures model parameters
- Sets up local LLM inference
- Enhances trading decision intelligence

## Production Deployment

For production deployment, run scripts in this order:

1. **`setup/configure_apis.sh`** - Configure all API keys
2. **`setup_pgp_keys.sh`** - Setup security keys
3. **`setup/register_instance.py`** - Register instance (if using master manager)
4. **Start system**: `docker-compose up -d`

## Security Notes

- All scripts handle sensitive data securely
- API keys are never logged or displayed
- PGP keys are generated with secure parameters  
- Scripts validate input and permissions
- Use these scripts instead of manual configuration

## Need Help?

Each script includes help documentation:
```bash
./script_name.sh --help
```

For system issues, see: `/docs/TROUBLESHOOTING.md`