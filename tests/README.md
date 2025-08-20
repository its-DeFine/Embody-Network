# Test Suite

This directory contains all tests for the Livepeer BYOC Payment System.

## Structure

```
tests/
├── unit/          # Unit tests for individual components
├── integration/   # Integration tests for system components
└── README.md      # This file
```

## Integration Tests

### Livepeer Tests
- `test_livepeer_connectivity.py` - Tests Livepeer gateway and orchestrator connectivity
- `test_livepeer_auth.py` - Tests authentication with Livepeer services
- `test_orchestrator_deployment.py` - Tests orchestrator deployment and registration

### BYOC Tests
- `continuous_byoc_test.py` - Continuous testing of BYOC job processing
- `test_distributed_integration.py` - Tests distributed system integration
- `test_cross_network.py` - Tests cross-network communication

### Monitoring Tests
- `live_distributed_test.py` - Live testing of distributed components
- `monitor_distributed_test.py` - Tests monitoring system
- `manual_integration_test.py` - Manual integration testing utilities

## Running Tests

### All Tests
```bash
pytest tests/
```

### Unit Tests Only
```bash
pytest tests/unit/
```

### Integration Tests Only
```bash
pytest tests/integration/
```

### Specific Test
```bash
pytest tests/integration/test_livepeer_connectivity.py
```

### With Coverage
```bash
pytest --cov=app --cov=scripts tests/
```

## Test Configuration

Tests use environment variables from `.env.test` (if exists) or `.env`.

Required environment variables:
- `MANAGER_URL` - Central manager URL
- `ADMIN_EMAIL` - Admin email for authentication
- `ADMIN_PASSWORD` - Admin password
- `ETH_RPC_URL` - Ethereum RPC endpoint
- `ORCHESTRATOR_SECRET` - Orchestrator secret