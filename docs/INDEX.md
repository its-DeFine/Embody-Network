# AutoGen Platform Documentation Index

Complete documentation for the AutoGen Platform - a lean, production-ready system for deploying Microsoft AutoGen AI agents.

## 📖 Documentation Structure

### 🚀 Getting Started
1. **[Main README](../README.md)** - Platform overview and quick start
2. **[Quick Start Guide](./QUICK_START.md)** - Get running in 5 minutes
3. **[User Guide](./USER_GUIDE.md)** - Complete usage documentation

### 🏗️ Architecture & Design
1. **[Architecture Overview](./architecture/autogen-architecture.md)** - System design and components
2. **[Platform Status](./PLATFORM_STATUS.md)** - Current capabilities and limitations
3. **[Platform Enhancements](./PLATFORM_ENHANCEMENTS.md)** - Recent improvements

### 🚢 Deployment & Operations
1. **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Production deployment instructions
2. **[GPU Orchestrator](./GPU_ORCHESTRATOR.md)** - GPU support documentation
3. **[Real Implementations](./REAL_IMPLEMENTATIONS.md)** - Production use cases

### 🧪 Testing & Quality
1. **[Live Test Results](../LIVE_TEST_RESULTS.md)** - Test tracking and execution guide
2. **[Test Documentation](../tests/README.md)** - Testing framework details
3. **[AutoGen Test Results](./AUTOGEN_TEST_RESULTS.md)** - AutoGen-specific test results
4. **[Swarm Test Results](./SWARM_TEST_RESULTS.md)** - Docker Swarm test results

### 🔧 Maintenance & Updates
1. **[Simplification Summary](../SIMPLIFICATION_SUMMARY.md)** - Recent repository cleanup
2. **[Cleanup Summary](../CLEANUP_SUMMARY.md)** - Maintenance performed
3. **[GPU Integration Summary](../GPU_INTEGRATION_SUMMARY.md)** - GPU features added

## 🗺️ Documentation Map

```
docs/
├── INDEX.md                    # This file - documentation index
├── QUICK_START.md             # Getting started quickly
├── USER_GUIDE.md              # Complete user documentation
├── DEPLOYMENT_GUIDE.md        # Production deployment
├── PLATFORM_STATUS.md         # Current platform state
├── PLATFORM_ENHANCEMENTS.md   # Recent improvements
├── GPU_ORCHESTRATOR.md        # GPU support guide
├── REAL_IMPLEMENTATIONS.md    # Production examples
├── AUTOGEN_TEST_RESULTS.md    # AutoGen test results
├── SWARM_TEST_RESULTS.md      # Swarm test results
└── architecture/
    └── autogen-architecture.md # System architecture
```

## 🔍 Quick Links by Topic

### For Developers
- [Architecture Overview](./architecture/autogen-architecture.md)
- [API Documentation](http://localhost:8000/docs) (when running)
- [Test Guide](../tests/README.md)
- [Makefile Commands](../Makefile)

### For DevOps Engineers
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Docker Configurations](../docker-compose.yml)
- [CI/CD Pipeline](../.github/workflows/ci-cd.yml)
- [Monitoring Setup](../monitoring/)

### For Users
- [Quick Start](./QUICK_START.md)
- [User Guide](./USER_GUIDE.md)
- [Control Board UI](http://localhost:3001) (when running)

### For Maintainers
- [Test Results Tracking](../LIVE_TEST_RESULTS.md)
- [Platform Status](./PLATFORM_STATUS.md)
- [Recent Changes](../SIMPLIFICATION_SUMMARY.md)

## 📝 Documentation Standards

### File Naming
- Use UPPERCASE for top-level docs (README.md, QUICK_START.md)
- Use lowercase with hyphens for subdirectories (autogen-architecture.md)
- Keep names descriptive but concise

### Content Structure
1. Clear title and purpose
2. Table of contents for long documents
3. Code examples with syntax highlighting
4. Diagrams where helpful
5. Links to related documentation

### Maintenance
- Update documentation with code changes
- Review quarterly for accuracy
- Archive outdated documentation
- Keep examples working

## 🆕 Recent Documentation Updates

- **2025-07-30**: Major repository simplification
  - Consolidated docker-compose files
  - Archived overlapping projects
  - Updated all documentation links
  - Created comprehensive README

- **2025-07-29**: DevOps infrastructure
  - Added test tracking documentation
  - Created CI/CD pipeline docs
  - Documented health checks

## 🔗 External Resources

- [Microsoft AutoGen Documentation](https://microsoft.github.io/autogen/)
- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)

---

**Last Updated**: 2025-07-30  
**Maintainer**: Platform Team  
**Version**: 1.0.0