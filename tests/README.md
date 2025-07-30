# Test Suite Documentation

This directory contains comprehensive test suites for the AutoGen platform.

## Test Structure

```
tests/
├── integration/        # Integration tests for services
├── e2e/               # End-to-end tests for workflows
├── unit/              # Unit tests (planned)
├── conftest.py        # Shared pytest fixtures
└── test_redis_simple.py  # Basic connectivity test
```

## Test Categories

### 1. Integration Tests (`/integration`)

Tests that verify integration between services:

- **test_api_endpoints.py**: API Gateway endpoint testing
  - Authentication flows
  - CRUD operations
  - Error handling
  
- **test_message_queue.py**: RabbitMQ integration
  - Event publishing
  - Message routing
  - Queue operations
  
- **test_redis_state.py**: Redis state management
  - Data persistence
  - Cache operations
  - State consistency
  
- **test_openbb_integration.py**: OpenBB adapter testing
  - Market data retrieval
  - Technical analysis
  - Portfolio analytics
  - Fallback mechanisms

### 2. End-to-End Tests (`/e2e`)

Complete workflow testing:

- **test_agent_lifecycle.py**: Full agent lifecycle
  - Agent creation
  - Task execution
  - Team collaboration
  - Agent deletion

### 3. Unit Tests (`/unit`) - Planned

Focused component testing:
- Model validation
- Utility functions
- Business logic
- Error handling

## Running Tests

### Run All Tests
```bash
make test
```

### Run Specific Test Suites
```bash
# Integration tests only
make test-integration

# E2E tests only
make test-e2e

# With coverage
make test-coverage
```

### Run Individual Test Files
```bash
# Run a specific test file
pytest tests/integration/test_api_endpoints.py -v

# Run a specific test function
pytest tests/integration/test_api_endpoints.py::test_create_agent -v

# Run with specific markers
pytest -m "not slow" -v
```

## Test Environment

### Configuration

Tests use environment variables from `.env.test`:
```bash
# Test database
REDIS_URL=redis://redis:6379/1  # Use database 1 for tests

# Test credentials
TEST_USER=test@example.com
TEST_PASSWORD=testpass123

# Service URLs
API_URL=http://api-gateway:8000
OPENBB_URL=http://openbb-adapter:8003
```

### Docker Environment

Tests run in Docker containers with:
- Isolated test database
- Mock external services
- Controlled network environment

## Writing Tests

### Test Structure Example
```python
import pytest
from httpx import AsyncClient

class TestFeatureName:
    """Test suite for specific feature"""
    
    @pytest.fixture
    async def setup_data(self):
        """Setup test data"""
        # Create test data
        yield data
        # Cleanup
    
    @pytest.mark.asyncio
    async def test_happy_path(self, setup_data, api_client):
        """Test successful scenario"""
        response = await api_client.post("/endpoint", json=data)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_error_handling(self, api_client):
        """Test error scenarios"""
        response = await api_client.post("/endpoint", json={})
        assert response.status_code == 400
```

### Best Practices

1. **Use Fixtures**: Leverage pytest fixtures for setup/teardown
2. **Async Tests**: Use `@pytest.mark.asyncio` for async functions
3. **Isolation**: Each test should be independent
4. **Descriptive Names**: Test names should describe what they test
5. **Assertions**: Use clear, specific assertions
6. **Mocking**: Mock external dependencies when appropriate

## Fixtures

Common fixtures available in `conftest.py`:

### API Client
```python
@pytest.fixture
async def api_client():
    """Authenticated API client"""
    async with AsyncClient(base_url=API_URL) as client:
        # Login and get token
        yield client
```

### Database
```python
@pytest.fixture
async def redis_client():
    """Redis client for test database"""
    client = await aioredis.create_redis_pool(REDIS_URL)
    yield client
    await client.flushdb()  # Cleanup
```

### Message Queue
```python
@pytest.fixture
async def rabbitmq_connection():
    """RabbitMQ connection for testing"""
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    yield connection
    await connection.close()
```

## Test Data

### Factories

Use factories for consistent test data:
```python
def create_test_agent(name="TestAgent", agent_type="trading"):
    return {
        "name": name,
        "type": agent_type,
        "config": {"risk_limit": 0.02},
        "autogen_config": {"model": "gpt-4"}
    }
```

### Mocking

Mock external services:
```python
@patch('openbb.get_market_data')
async def test_with_mock(mock_market_data):
    mock_market_data.return_value = {"price": 100}
    # Test code
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Nightly builds

CI pipeline includes:
1. Linting (ruff, black)
2. Type checking (mypy)
3. Security scanning
4. Test execution
5. Coverage reporting

## Coverage

### Current Coverage Goals
- Unit tests: 80% coverage
- Integration tests: 70% coverage
- E2E tests: Key workflows

### View Coverage Report
```bash
# Generate HTML report
make test-coverage

# View in browser
open htmlcov/index.html
```

## Debugging Tests

### Verbose Output
```bash
pytest -vvs tests/integration/test_api_endpoints.py
```

### Debug with PDB
```python
import pdb; pdb.set_trace()  # Add breakpoint
```

### Docker Logs
```bash
# View service logs during tests
docker-compose logs -f api-gateway
```

## Performance Testing

### Load Testing
```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_high_load():
    """Test system under load"""
    tasks = []
    for i in range(100):
        task = api_client.post("/agents", json=data)
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks)
    success_rate = sum(1 for r in responses if r.status_code == 201) / 100
    assert success_rate > 0.95  # 95% success rate
```

### Benchmark Tests
```python
@pytest.mark.benchmark
def test_redis_performance(benchmark):
    """Benchmark Redis operations"""
    result = benchmark(redis_client.get, "test_key")
    assert benchmark.stats['median'] < 0.001  # < 1ms
```

## Test Maintenance

### Regular Tasks
1. Update test data when models change
2. Add tests for new features
3. Remove obsolete tests
4. Update documentation
5. Review and improve coverage

### Test Review Checklist
- [ ] Tests pass locally
- [ ] Tests are deterministic
- [ ] No hardcoded values
- [ ] Proper cleanup
- [ ] Clear assertions
- [ ] Good coverage

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure services are running: `docker-compose ps`
   - Check service health: `make health-check`

2. **Authentication Failures**
   - Verify test credentials in `.env.test`
   - Check token expiration

3. **Flaky Tests**
   - Add retries for network operations
   - Increase timeouts for slow operations
   - Ensure proper test isolation

4. **Database State**
   - Use separate test database
   - Clean up after each test
   - Don't rely on specific data order

## Contributing

When adding new tests:
1. Follow existing patterns
2. Add appropriate markers
3. Update this documentation
4. Ensure CI passes
5. Maintain coverage levels