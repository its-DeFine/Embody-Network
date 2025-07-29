# AutoGen Platform

A production-ready platform for deploying and managing AutoGen-powered AI agents with Docker orchestration, designed for scalable multi-agent systems.

## 🌟 Features

- **AutoGen Integration**: Deploy Microsoft AutoGen agents in containerized environments
- **Multi-Agent Orchestration**: Create teams of specialized agents that collaborate
- **Docker Swarm Ready**: Scale across multiple hosts with built-in orchestration
- **Real-time Monitoring**: Prometheus + Grafana metrics and monitoring
- **Event-Driven Architecture**: RabbitMQ message queue for agent communication
- **RESTful API**: Complete API with JWT authentication
- **WebSocket Support**: Real-time updates and agent communication
- **Admin Controls**: Killswitch functionality and platform management

## 🚀 Quick Start

```bash
# Clone repository
git clone <repository-url>
cd operation

# Start platform
docker-compose up -d

# Create your first agent (see quickstart.sh)
./scripts/quickstart.sh
```

**[Full Quick Start Guide →](./docs/QUICK_START.md)**

## 📋 Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- Ports: 8000, 8001, 15672, 6379, 3000, 9090

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API Gateway   │────▶│  Agent Manager  │────▶│ AutoGen Agents  │
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │                         
         ▼                       ▼                         
┌─────────────────┐     ┌─────────────────┐              
│    RabbitMQ     │◀────│     Redis       │              
└─────────────────┘     └─────────────────┘              
         │                                                
         ▼                                                
┌─────────────────┐     ┌─────────────────┐              
│   Prometheus    │────▶│    Grafana      │              
└─────────────────┘     └─────────────────┘              
```

## 🤖 Agent Types

1. **Trading Agents**: Execute trades based on market conditions
2. **Analysis Agents**: Perform technical and sentiment analysis
3. **Risk Management Agents**: Monitor and manage portfolio risk
4. **Portfolio Optimization Agents**: Optimize asset allocation
5. **Custom Agents**: Create your own agent types

## 📚 Documentation

- **[Quick Start Tutorial](./docs/QUICK_START.md)** - Get running in 5 minutes
- **[User Guide](./docs/USER_GUIDE.md)** - Complete usage documentation
- **[Deployment Guide](./docs/DEPLOYMENT_GUIDE.md)** - Production deployment instructions
- **[API Reference](http://localhost:8000/docs)** - Interactive API documentation
- **[Architecture Overview](./docs/ARCHITECTURE.md)** - System design details

## 🔧 Key Components

### Services
- **API Gateway**: REST API and WebSocket endpoint
- **Agent Manager**: Container lifecycle management
- **Admin Control**: Platform administration and killswitch
- **Update Pipeline**: GitOps-based agent updates
- **Monitoring Stack**: Prometheus, Grafana, Loki

### Technologies
- **AutoGen**: Microsoft's multi-agent framework
- **FastAPI**: High-performance Python web framework
- **Docker Swarm**: Container orchestration
- **RabbitMQ**: Message queue for event-driven architecture
- **Redis**: State management and caching
- **PostgreSQL**: Persistent data storage

## 🚢 Deployment Options

### Local Development
```bash
docker-compose up -d
```

### Docker Swarm (Recommended)
```bash
docker swarm init
docker stack deploy -c docker-compose.swarm.yml autogen
```

### Kubernetes
```bash
kubectl apply -f deployments/k8s/
```

**[Full Deployment Guide →](./docs/DEPLOYMENT_GUIDE.md)**

## 🛡️ Security Features

- JWT authentication with role-based access
- API key management
- Environment-based secrets
- Admin killswitch functionality
- Audit logging
- TLS support

## 📊 Monitoring

Access monitoring dashboards:
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- RabbitMQ: http://localhost:15672 (admin/password)

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
./scripts/test_integration.sh

# Test swarm deployment
./scripts/test_swarm_management.sh
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## ⚠️ Current Limitations

- Container creation requires privileged mode or proper Docker socket permissions
- AutoGen conversations require LLM API keys (OpenAI/Anthropic)
- Some features are in preview and not production-ready

See [PLATFORM_STATUS.md](./docs/PLATFORM_STATUS.md) for detailed status.

## 📝 License

[License Type] - see LICENSE file for details

## 🆘 Support

- GitHub Issues: [Report bugs and request features]
- Documentation: See `/docs` directory
- API Docs: http://localhost:8000/docs when running

## 🎯 Roadmap

- [ ] Kubernetes Helm charts
- [ ] Web UI dashboard
- [ ] Additional LLM provider support
- [ ] Enhanced agent templates
- [ ] Distributed training support
- [ ] Multi-region deployment

---

Built with ❤️ for the AutoGen community