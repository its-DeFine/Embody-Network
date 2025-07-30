# API Gateway Service

The API Gateway is the main entry point for all client interactions with the AutoGen platform.

## Features

- **Authentication & Authorization**: JWT-based authentication with role-based access control
- **Customer Management**: CRUD operations for customer accounts
- **Agent Management**: Create, update, delete, and monitor agents
- **Task Management**: Submit and track agent tasks
- **Team Management**: Create and manage agent teams
- **WebSocket Support**: Real-time updates and notifications
- **Admin API**: Platform administration endpoints

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Customer login
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `POST /api/v1/auth/logout` - Logout

### Customer Management
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers/me` - Get current customer
- `PUT /api/v1/customers/me` - Update customer
- `DELETE /api/v1/customers/me` - Delete customer

### Agent Management
- `GET /api/v1/agents` - List agents
- `POST /api/v1/agents` - Create agent
- `GET /api/v1/agents/{agent_id}` - Get agent details
- `PUT /api/v1/agents/{agent_id}` - Update agent
- `DELETE /api/v1/agents/{agent_id}` - Delete agent
- `POST /api/v1/agents/{agent_id}/start` - Start agent
- `POST /api/v1/agents/{agent_id}/stop` - Stop agent

### Task Management
- `GET /api/v1/tasks` - List tasks
- `POST /api/v1/tasks` - Create task
- `GET /api/v1/tasks/{task_id}` - Get task details
- `DELETE /api/v1/tasks/{task_id}` - Cancel task

### Team Management
- `GET /api/v1/teams` - List teams
- `POST /api/v1/teams` - Create team
- `PUT /api/v1/teams/{team_id}` - Update team
- `DELETE /api/v1/teams/{team_id}` - Delete team

### Admin Endpoints
- `POST /api/v1/admin/login` - Admin login
- `GET /api/v1/admin/platform/stats` - Platform statistics
- `GET /api/v1/admin/agents` - List all agents
- `POST /api/v1/admin/broadcast` - Broadcast message

## WebSocket

Connect to `/ws` for real-time updates:
- Agent status changes
- Task progress updates
- System notifications

## Configuration

Environment variables:
- `REDIS_URL`: Redis connection URL
- `RABBITMQ_URL`: RabbitMQ connection URL
- `JWT_SECRET`: Secret for JWT signing
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `JWT_EXPIRATION_MINUTES`: Token expiration time
- `ADMIN_API_KEY`: Admin authentication key

## Security

- JWT tokens for customer authentication
- API key for admin endpoints
- CORS configuration for web clients
- Rate limiting on sensitive endpoints
- Input validation on all endpoints

## Error Handling

Standard error response format:
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

## Health Check

- `GET /health` - Service health status
- `GET /health/ready` - Readiness check (includes dependencies)