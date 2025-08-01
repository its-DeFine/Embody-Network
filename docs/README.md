# AutoGen Platform Documentation

Welcome to the AutoGen Platform documentation. This platform provides a production-ready system for orchestrating Microsoft AutoGen AI agents.

## 📚 Documentation Index

### Getting Started
- [**Launch Guide**](./LAUNCH_GUIDE.md) - Quick start guide for running the platform
- [**Platform Architecture**](./PLATFORM_ARCHITECTURE.md) - System design and components

### Development
- [**Engineering Standards**](./ENGINEERING_STANDARDS.md) - Code quality and best practices
- [**API Reference**](./API_REFERENCE.md) - Complete API documentation
- [**Interactive API Docs**](http://localhost:8000/docs) - Swagger UI (when running)

### Operations
- [**Frontend Guide**](./FRONTEND_GUIDE.md) - Using the control board UI
- [**Agent Management**](./AGENT_MANAGEMENT.md) - Creating and managing agents
- [**Team Coordination**](./TEAM_COORDINATION.md) - Working with agent teams

### Architecture Decisions
- [**Simplification Complete**](./SIMPLIFICATION_COMPLETE.md) - Monolith transformation details

## 🚀 Quick Start

```bash
# Start the platform
make up

# Access the UI
open http://localhost:8000

# View API docs
open http://localhost:8000/docs
```

## 📋 Prerequisites

- Docker and Docker Compose
- Git
- Make (optional, for convenience commands)

## 🏗️ Architecture Overview

The platform consists of:
- **Frontend**: React-based control board for managing agents
- **Backend**: FastAPI monolith with event-driven orchestration
- **Redis**: State management and event queuing
- **Docker**: Containerized deployment

## 🔧 Configuration

Create a `.env` file:

```env
JWT_SECRET=your-secure-secret
ADMIN_PASSWORD=your-admin-password
OPENAI_API_KEY=your-openai-key  # If using OpenAI
```

## 📖 Further Reading

- [Microsoft AutoGen Documentation](https://github.com/microsoft/autogen)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)