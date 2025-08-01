# API Reference

The AutoGen Platform provides a RESTful API for managing agents, teams, and tasks.

## 🔐 Authentication

All API endpoints (except `/health`) require authentication using JWT tokens.

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Using the Token
Include the token in the Authorization header:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## 🤖 Agents

### List Agents
```http
GET /api/v1/agents
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Market Analyzer",
    "type": "analysis",
    "status": "running",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Create Agent
```http
POST /api/v1/agents
Content-Type: application/json

{
  "name": "My Agent",
  "agent_type": "trading",
  "config": {}
}
```

### Get Agent
```http
GET /api/v1/agents/{agent_id}
```

### Start Agent
```http
POST /api/v1/agents/{agent_id}/start
```

### Stop Agent
```http
POST /api/v1/agents/{agent_id}/stop
```

### Delete Agent
```http
DELETE /api/v1/agents/{agent_id}
```

## 👥 Teams

### List Teams
```http
GET /api/v1/teams
```

### Create Team
```http
POST /api/v1/teams
Content-Type: application/json

{
  "name": "Analysis Team",
  "description": "Market analysis team",
  "agent_ids": ["agent-1", "agent-2"]
}
```

### Get Team
```http
GET /api/v1/teams/{team_id}
```

### Coordinate Team Task
```http
POST /api/v1/teams/{team_id}/coordinate
Content-Type: application/json

{
  "objective": "Analyze AAPL stock",
  "context": {
    "timeframe": "1 week"
  }
}
```

### Delete Team
```http
DELETE /api/v1/teams/{team_id}
```

## 📋 Tasks

### List Tasks
```http
GET /api/v1/tasks
```

Query parameters:
- `status`: Filter by status (pending, running, completed, failed)
- `limit`: Number of results (default: 100)
- `offset`: Pagination offset

### Create Task
```http
POST /api/v1/tasks
Content-Type: application/json

{
  "type": "analysis",
  "description": "Analyze market trends",
  "payload": {}
}
```

### Get Task
```http
GET /api/v1/tasks/{task_id}
```

### Cancel Task
```http
POST /api/v1/tasks/{task_id}/cancel
```

## 🔄 WebSocket

### Connect
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'tasks'
}));
```

### Message Types
- `task_created`: New task created
- `task_updated`: Task status changed
- `agent_status`: Agent status update
- `team_update`: Team activity

## 📊 Health & Monitoring

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "version": "1.0.0"
}
```

## 🔍 Error Responses

### Standard Error Format
```json
{
  "detail": "Error message",
  "status_code": 400,
  "request_id": "550e8400-e29b-41d4"
}
```

### Common Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

## 📝 Request/Response Headers

### Request Headers
- `Content-Type`: `application/json`
- `Authorization`: `Bearer {token}`
- `X-Request-ID`: Optional request tracking

### Response Headers
- `X-Request-ID`: Request identifier
- `X-Response-Time`: Processing time
- `Content-Type`: `application/json`

## 🚀 Rate Limiting

- **Default**: 100 requests per minute
- **Authenticated**: 1000 requests per minute
- **Headers**:
  - `X-RateLimit-Limit`: Total allowed
  - `X-RateLimit-Remaining`: Requests left
  - `X-RateLimit-Reset`: Reset timestamp

## 📄 Pagination

List endpoints support pagination:
```http
GET /api/v1/tasks?limit=20&offset=40
```

**Response Headers:**
- `X-Total-Count`: Total items
- `X-Page-Size`: Items per page
- `X-Page-Number`: Current page

## 🔧 API Versioning

The API uses URL versioning:
- Current: `/api/v1/`
- Format: `/api/v{version}/`

## 💡 Examples

### Complete Workflow
```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r .access_token)

# 2. Create agent
AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Agent","agent_type":"analysis"}' \
  | jq -r .id)

# 3. Start agent
curl -X POST http://localhost:8000/api/v1/agents/$AGENT_ID/start \
  -H "Authorization: Bearer $TOKEN"

# 4. Create task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"analysis","description":"Test task"}'
```

## 🔗 Interactive Documentation

When the platform is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide interactive API exploration and testing.