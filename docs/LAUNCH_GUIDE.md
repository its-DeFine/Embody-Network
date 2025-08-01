# AutoGen Platform Launch Guide

## Quick Start

To launch the AutoGen Platform, use the following commands:

```bash
# Start all services
make up

# Or using docker compose directly
docker compose up -d
```

## Verify Installation

1. Check container status:
   ```bash
   make status
   # or
   docker compose ps
   ```

2. Test the API health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

3. Access the API documentation:
   - Open http://localhost:8000/docs in your browser

## Available Commands

- `make up` - Start all services
- `make down` - Stop all services  
- `make restart` - Restart all services
- `make logs` - View logs (follow mode)
- `make build` - Build/rebuild Docker images
- `make status` - Show container status
- `make shell` - Open shell in app container
- `make clean` - Clean everything (containers, volumes, images)
- `make test` - Run tests

## Services

- **API**: http://localhost:8000
  - Health check: `/health`
  - API docs: `/docs`
  - ReDoc: `/redoc`
  
- **Redis**: localhost:6379
  - Used for state management and event queuing

## Environment Variables

Create a `.env` file with:

```env
# Required
JWT_SECRET=your-secure-secret-here
ADMIN_PASSWORD=your-admin-password

# Optional
OPENAI_API_KEY=your-openai-key
REDIS_URL=redis://redis:6379
```

## Troubleshooting

1. If containers fail to start:
   ```bash
   make logs
   ```

2. To rebuild after code changes:
   ```bash
   make build
   make up
   ```

3. To completely reset:
   ```bash
   make clean
   make build  
   make up
   ```

## Next Steps

1. Access the API docs at http://localhost:8000/docs
2. Create your first agent using the API
3. Deploy teams of agents for your use cases

For more information, see the main documentation in `/docs/DOCUMENTATION.md`.