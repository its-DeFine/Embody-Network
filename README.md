# AutoGen Platform

A simple platform for deploying Microsoft AutoGen AI agents.

## Quick Start

```bash
# Clone repo
git clone <repo-url>
cd autogen-platform

# Configure
cp .env.example .env
# Edit .env with your API keys

# Start
make up

# View UI
open http://localhost:8000
```

## Features

- **Central Orchestration**: Event-driven architecture for agent coordination
- **Agent Teams**: Create teams of agents that work together
- **Task Routing**: Intelligent task distribution based on agent capabilities
- **Inter-Agent Communication**: Agents can trigger tasks for each other
- **AutoGen Integration**: Microsoft AutoGen for agent conversations
- **Trading, Analysis, Risk, and Portfolio** agent types
- **Redis State Management** with event queues
- **Optional OpenBB** for financial data
- **REST API + WebSocket** for real-time updates

## Commands

```bash
make help    # Show all commands
make up      # Start services
make down    # Stop services
make logs    # View logs
make test    # Run tests
make clean   # Clean everything
```

## API

### Authentication
- `POST /api/v1/auth/login` - Login

### Agents
- `GET /api/v1/agents` - List agents
- `POST /api/v1/agents` - Create agent
- `POST /api/v1/agents/{id}/start` - Start agent
- `POST /api/v1/agents/{id}/stop` - Stop agent
- `DELETE /api/v1/agents/{id}` - Delete agent

### Teams
- `GET /api/v1/teams` - List teams
- `POST /api/v1/teams` - Create team
- `POST /api/v1/teams/{id}/coordinate` - Coordinate team task

### Tasks
- `GET /api/v1/tasks` - List tasks
- `POST /api/v1/tasks` - Create task
- `GET /api/v1/tasks/{id}` - Get task status

### Real-time
- `WS /ws` - WebSocket for live updates

## Project Structure

```
├── app/
│   ├── main.py          # FastAPI application
│   ├── orchestrator.py  # Central coordination hub
│   ├── api/             # API routes
│   ├── agents/          # Agent implementations
│   ├── dependencies.py  # Shared dependencies
│   ├── openbb_client.py # Financial data integration
│   └── static/          # UI files
├── tests/               # Tests
├── docker-compose.yml   # Docker configuration
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
├── Makefile            # Commands
└── README.md           # This file
```

## Configuration

Environment variables in `.env`:

- `JWT_SECRET` - Secret for JWT tokens
- `ADMIN_PASSWORD` - Admin login password
- `OPENAI_API_KEY` - OpenAI API key for agents
- `REDIS_URL` - Redis connection (default: redis://localhost:6379)

## License

MIT