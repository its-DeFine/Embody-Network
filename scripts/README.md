# Scripts Directory Structure

This directory contains various scripts for managing and testing the trading system.

## Directory Organization

### 📊 `/trading/`
Scripts for managing the live trading system:
- **`monitor_trading.sh`** - Consolidated monitoring tool with multiple modes:
  - `./monitor_trading.sh status` - Show current system status
  - `./monitor_trading.sh live` - Real-time monitoring
  - `./monitor_trading.sh history` - View detailed trading history
- **`start_1k_trading.sh`** - Start 24/7 trading with $1,000
- **`start_trading.sh`** - General trading startup script
- **`start_dashboard.sh`** - Launch the web dashboard

**Deprecated scripts** (functionality merged into `monitor_trading.sh`):
- `check_live_trading.sh`, `check_trading_status.sh`, `view_trading_details.sh`, `check_real_pnl.sh`

### 🧪 `/testing/`
Test scripts for various system components:
- **`test_runner.sh`** - Unified test runner with multiple modes:
  - `./test_runner.sh quick` - Basic health check and login
  - `./test_runner.sh api` - Test all API endpoints
  - `./test_runner.sh market [--real-data]` - Market data tests
  - `./test_runner.sh trading [--with-pnl]` - Trading functionality
  - `./test_runner.sh system` - Run all tests comprehensively
  - Options: `--real-data`, `--with-pnl`, `--crypto-only`, `--verbose`, `--timeout=N`

**Specialized test scripts** (kept separate due to unique functionality):
- **`test_gpu_trading.sh`** - GPU acceleration tests
- **`test_new_architecture.sh`** - Architecture validation tests
- **`run_tests.sh`** - Legacy comprehensive test runner

**Deprecated scripts** (functionality merged into `test_runner.sh`):
- `quick_test.sh`, `test_login_and_api.sh` → use `test_runner.sh quick/api`
- `test_real_market_trading.sh`, `test_simple_real_market.sh` → use `test_runner.sh market --real-data`
- `test_crypto_trading_pnl.sh` → use `test_runner.sh trading --crypto-only --with-pnl`
- `test_trading_scenario.sh`, `test_agent_simulation.sh` → use `test_runner.sh trading`

### 🎯 `/demo/`
Demonstration scripts:
- **`demo_cross_instance.py`** - Cross-instance collaboration demo
- **`demo_live_system.py`** - Live system demonstration
- Various trading scenario demos

### ⚙️ `/setup/`
Configuration and setup scripts:
- **`configure_apis.sh`** - Consolidated API configuration tool:
  - `./configure_apis.sh setup` - Interactive setup wizard
  - `./configure_apis.sh show` - View current configuration
  - `./configure_apis.sh test` - Test API connections
- **`register_instance.py`** - Register trading instance

**Deprecated scripts** (functionality merged into `configure_apis.sh`):
- `configure_market_apis.sh`, `setup_api_keys.sh`

### 🔧 `/dev/`
Development and debugging scripts:
- **`run_local.sh`** - Run system locally
- **`run_separate_agents.sh`** - Run agents separately for debugging

## Usage Examples

### Start Trading
```bash
cd trading
./start_1k_trading.sh
```

### Monitor System
```bash
cd trading
./monitor_trading.sh live  # Real-time monitoring
```

### Configure APIs
```bash
cd setup
./configure_apis.sh setup  # Interactive setup
```

### Run Tests
```bash
cd testing
# Quick test
./test_runner.sh quick

# Test with real market data
./test_runner.sh market --real-data

# Full system test
./test_runner.sh system --verbose
```

## Best Practices

1. Always use the consolidated scripts when available
2. Check script help with `./script_name.sh help`
3. Ensure Docker is running before executing trading scripts
4. Configure API keys before starting live trading