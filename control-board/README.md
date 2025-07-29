# AutoGen Control Board

A modern web interface for managing the AutoGen GPU swarm orchestration platform.

## Features

- **Real-time Dashboard**: Monitor GPU orchestrators, agents, and system health
- **GPU Orchestrator Management**: View GPU status, temperature, memory usage, and utilization
- **Agent Deployment**: Deploy and manage GPU/CPU agents with various models
- **Monitoring**: Track system metrics, resource usage, and events
- **Settings Management**: Configure GPU allocation strategies, system parameters, and trading settings
- **WebSocket Support**: Real-time updates for orchestrator health and agent status

## Technology Stack

- **React 18** with TypeScript
- **Material-UI** for component library
- **React Query** for data fetching and caching
- **Socket.IO** for real-time communication
- **Recharts** for data visualization
- **Vite** for fast development and building

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The application will be available at http://localhost:3001

### Build

```bash
npm run build
```

## Docker Deployment

Build and run with Docker:

```bash
docker build -t autogen-control-board .
docker run -p 80:80 autogen-control-board
```

Or use with the main docker-compose:

```yaml
control-board:
  build: ./control-board
  ports:
    - "3001:80"
  networks:
    - autogen-network
  depends_on:
    - api-gateway
    - orchestrator-adapter
```

## API Endpoints

The control board connects to:
- `/api/*` - Main API gateway (port 8000)
- `/gpu/*` - GPU orchestrator adapter (port 8002)
- `/ws/*` - WebSocket connections

## Default Credentials

- Username: `admin`
- Password: `admin123`

## Configuration

Environment variables can be set in `.env`:

```bash
VITE_API_URL=http://localhost:8000
VITE_GPU_URL=http://localhost:8002
VITE_WS_URL=ws://localhost:8000
```

## Security Notes

- Always change default credentials in production
- Use HTTPS in production environments
- Configure proper CORS settings
- Implement rate limiting for API endpoints

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `npm test`
5. Submit a pull request