# Test Suite Organization

This test suite is organized into three main categories to match the architecture of the 24/7 autonomous trading system:

## 🔒 Security Tests (`test_security_*.py`)

Tests that validate security implementations and prevent vulnerabilities:

### Current Security Tests
- ✅ `test_security_core.py` - Core security validation (22 tests passing)
- ✅ `test_basic_imports.py` - Basic import and configuration security

### TODO: Security Test Expansion
- `test_security_suite.py` - Extended security test scenarios
- Authentication flow testing with edge cases  
- Rate limiting effectiveness under load
- Input validation bypass attempt scenarios
- JWT token lifecycle and revocation testing

**Run Security Tests:**
```bash
pytest -m security -v
```

## 🎛️ Central Manager Tests (`test_central_manager.py`)

Tests for the master management system that coordinates multiple trading instances:

### TODO: Central Manager Logic Testing
- Master Manager API command handling
- Cross-instance bridge communication
- System orchestration and coordination
- Audit logging and monitoring integration
- Collective intelligence coordination

**Components to Test:**
- `app/api/master.py` - Master manager API endpoints
- `app/infrastructure/messaging/cross_instance_bridge.py` - Inter-instance communication
- `app/core/orchestration/orchestrator.py` - System coordination
- `app/infrastructure/monitoring/audit_logger.py` - Audit and monitoring
- `app/core/agents/collective_intelligence.py` - Multi-instance coordination

**Run Central Manager Tests:**
```bash
pytest -m central_manager -v
```

## 📦 Container Logic Tests (`test_container_logic.py`)

Tests for individual trading container components:

### TODO: Container Component Testing
- Agent management and lifecycle
- Trading engine and strategies
- Market data processing 
- GPU orchestration
- WebSocket management
- P&L tracking accuracy

**Components to Test:**
- `app/core/agents/agent_manager.py` - Agent lifecycle management
- `app/core/trading/trading_engine.py` - Trading execution
- `app/core/trading/trading_strategies.py` - Strategy implementations
- `app/core/market/market_data.py` - Market data processing
- `app/core/orchestration/gpu_orchestrator.py` - GPU resource management
- `app/infrastructure/messaging/websocket_manager.py` - Real-time communication
- `app/core/trading/pnl_tracker.py` - Profit/loss tracking

**Run Container Tests:**
```bash
pytest -m container -v
```

## 🔧 Test Organization TODOs

### Immediate Priorities
1. **[HIGH]** Implement central manager API tests for master coordination
2. **[HIGH]** Create container agent management tests
3. **[MEDIUM]** Add trading strategy validation tests
4. **[MEDIUM]** Implement market data processing tests

### Testing Infrastructure TODOs
1. **[HIGH]** Set up test data fixtures for trading scenarios
2. **[MEDIUM]** Create mock services for external dependencies
3. **[MEDIUM]** Add performance benchmarking for critical paths
4. **[LOW]** Set up continuous integration test automation

## Running Tests by Category

```bash
# All tests
pytest

# Security tests only
pytest -m security

# Central manager tests only  
pytest -m central_manager

# Container logic tests only
pytest -m container

# Integration tests
pytest -m integration

# Performance tests
pytest -m performance
```

## Test Coverage Goals

- **Security Tests**: 100% coverage of authentication, validation, and security middleware
- **Central Manager Tests**: 90% coverage of orchestration and cross-instance logic
- **Container Tests**: 85% coverage of trading, agent, and market data components
- **Overall Coverage**: 80%+ across the entire codebase