# AutoGen Platform

A lean, production-ready platform for deploying Microsoft AutoGen AI agents with Docker orchestration.

## 🚀 Quick Start

```bash
# Start the platform
make up

# View the UI
open http://localhost:3001

# Run tests
make test

# Stop everything
make down
```

## 📚 Documentation Index

### Getting Started
- **[Quick Start Guide](./docs/QUICK_START.md)** - Get running in 5 minutes
- **[User Guide](./docs/USER_GUIDE.md)** - Complete usage documentation
- **[Architecture Overview](./docs/architecture/autogen-architecture.md)** - System design

### Operations
- **[Deployment Guide](./docs/DEPLOYMENT_GUIDE.md)** - Production deployment
- **[Test Results Tracking](./LIVE_TEST_RESULTS.md)** - Test execution and tracking
- **[Platform Status](./docs/PLATFORM_STATUS.md)** - Current capabilities and limitations

### Development
- **[GPU Integration](./docs/GPU_ORCHESTRATOR.md)** - GPU orchestrator documentation
- **[OpenBB Integration](./docs/OPENBB_INTEGRATION_PLAN.md)** - Financial data integration
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)
- **[Test Guide](./tests/README.md)** - Testing documentation

### Recent Updates
- **[Simplification Summary](./SIMPLIFICATION_SUMMARY.md)** - Recent repository cleanup
- **[OpenBB Integration](./services/openbb-adapter/README.md)** - New financial data service
- **[Cleanup Summary](./CLEANUP_SUMMARY.md)** - Repository maintenance performed
- **[GPU Integration Summary](./GPU_INTEGRATION_SUMMARY.md)** - GPU features added

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Control     │────▶│    API      │────▶│   Agent     │
│ Board (UI)  │     │  Gateway    │     │  Manager    │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                    │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │  RabbitMQ   │◀────│   AutoGen   │
                    │  (Events)   │     │   Agents    │
                    └──────┬──────┘     └──────┬──────┘
                           │                    │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │    Redis    │     │   OpenBB    │
                    │   (State)   │     │  (FinData)  │
                    └─────────────┘     └─────────────┘
```

## 📁 Project Structure

```
operation/
├── services/          # Core microservices
│   ├── api-gateway/   # REST API & WebSocket server
│   ├── core-engine/   # AutoGen agent orchestration
│   ├── agent-manager/ # Agent lifecycle management
│   ├── admin-control/ # Platform administration
│   ├── update-pipeline/ # GitOps updates
│   └── openbb-adapter/ # OpenBB financial data integration
├── agents/            # Agent implementations
│   ├── base/          # Base agent classes
│   └── agent_types/   # Specialized agents
├── control-board/     # React UI dashboard
├── orchestrator/      # GPU orchestration adapter
├── tests/             # Test suites
│   ├── integration/   # Integration tests
│   ├── e2e/          # End-to-end tests
│   └── unit/         # Unit tests (planned)
├── scripts/           # Utility scripts
├── docs/              # Documentation
├── docker/            # Docker configurations
└── monitoring/        # Prometheus & Grafana configs
```

## 🛠️ Key Commands

All operations are available through the Makefile:

### Development
```bash
make build          # Build all Docker images
make up             # Start all services
make down           # Stop all services
make logs-f         # Follow logs
make ps             # Show running containers
```

### Testing
```bash
make test           # Run all tests
make test-integration # Integration tests only
make test-e2e       # End-to-end tests only
make test-coverage  # Generate coverage report
```

### Production
```bash
make up-prod        # Start with production config
make health         # Check service health
make clean          # Clean up volumes
make reset          # Full reset
```

## 🌟 Features

- **AutoGen Integration** - Deploy Microsoft AutoGen agents in containers
- **Multi-Agent Teams** - Orchestrate collaborating AI agents
- **Web Dashboard** - React-based control board UI
- **REST API** - Full API with JWT authentication
- **Event-Driven** - RabbitMQ for agent communication
- **State Management** - Redis for fast state access
- **Monitoring** - Built-in Prometheus & Grafana
- **GPU Support** - Optional GPU orchestration
- **CI/CD Ready** - GitHub Actions pipeline

## 📋 Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- Available ports: 3001, 5672, 6379, 8000, 15672

## 🔧 Configuration

### Environment Setup
```bash
# Copy example environment
cp .env.example .env

# Edit with your settings
vim .env
```

### Key Configuration Files
- `.env` - Environment variables
- `docker-compose.override.yml` - Local overrides
- `docker-compose.prod.yml` - Production settings

## 🖥️ User Interfaces

When running, access:
- **Control Board**: http://localhost:3001
- **API Docs**: http://localhost:8000/docs
- **OpenBB API**: http://localhost:8003/docs
- **RabbitMQ**: http://localhost:15672 (guest/guest)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 🧪 Testing

The platform includes comprehensive test suites:

```bash
# Run all tests with detailed tracking
make test

# Run specific test suites
make test-integration
make test-e2e

# Generate coverage report
make test-coverage
```

See [Test Results Tracking](./LIVE_TEST_RESULTS.md) for detailed test documentation.

## 🚢 Deployment

### Local Development
```bash
make up
```

### Production Deployment
```bash
# With monitoring and optimizations
make up-prod
```

### GPU-Enabled Deployment
```bash
# GPU orchestration is now standalone
cd orchestrator/adapter
docker compose up -d
```

See [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md) for detailed instructions.

## 🔒 Security

- JWT-based authentication
- API key management  
- Admin killswitch functionality
- Environment-based secrets
- Network isolation
- TLS support (production)

## 📊 Monitoring & Observability

- **Metrics**: Prometheus + Grafana dashboards
- **Logs**: Centralized logging with Loki
- **Tracing**: OpenTelemetry support
- **Health Checks**: Built-in health endpoints

## 🤝 Contributing

1. Keep it simple - avoid unnecessary complexity
2. Follow existing patterns
3. Write tests for new features
4. Update relevant documentation
5. Use the Makefile for common operations

## ⚠️ Known Limitations

- Agent deployment requires Docker socket access
- LLM API keys needed for agent conversations
- GPU features require NVIDIA Docker runtime

See [Platform Status](./docs/PLATFORM_STATUS.md) for current state.

## 🛟 Troubleshooting

### Common Issues

1. **Services won't start**
   ```bash
   make reset
   make up
   ```

2. **Port conflicts**
   - Check `.env` for port configuration
   - Modify `docker-compose.override.yml`

3. **Test failures**
   - See [Test Guide](./LIVE_TEST_RESULTS.md)
   - Check service health: `make health`

## 📝 License

[Your License Here]

## 🔗 Related Projects

- [Microsoft AutoGen](https://github.com/microsoft/autogen)
- [Agent-Net](./orchestrator/agent-net/README.md) - GPU orchestration

---

**Version**: 1.0.0  
**Last Updated**: 2025-07-30  
**Status**: Production Ready (with limitations)

For questions or support, please open an issue or consult the documentation.