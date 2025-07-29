import os
import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import secrets
import hmac

from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import redis.asyncio as redis
import logging

# Import shared models - adjust path when containerized
import sys
sys.path.append('/app')
from shared.models.agent_models import AgentConfig, AgentStatus, AgentType, CustomerConfig, AgentTeam
from shared.events.event_types import Event, EventType
from shared.utils.message_queue import get_message_queue, MessageQueue
from shared.utils.resilience import get_logger, CircuitBreakers, metrics, with_circuit_breaker

# Setup structured logging
logger = get_logger(__name__)

# JWT Configuration - Secure handling
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable must be set")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security
security = HTTPBearer()


# Request/Response Models
class LoginRequest(BaseModel):
    email: str
    api_key: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CreateAgentRequest(BaseModel):
    name: str
    agent_type: AgentType
    description: Optional[str] = None
    config: Dict[str, Any] = {}
    autogen_config: Dict[str, Any] = {}


class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = None
    agent_ids: list[str] = []
    orchestrator_config: Dict[str, Any] = {}


class AgentActionRequest(BaseModel):
    action: str  # start, stop, pause, update
    config: Optional[Dict[str, Any]] = None


# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, customer_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[customer_id] = websocket
    
    def disconnect(self, customer_id: str):
        self.active_connections.pop(customer_id, None)
    
    async def send_personal_message(self, message: str, customer_id: str):
        if customer_id in self.active_connections:
            await self.active_connections[customer_id].send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)


manager = ConnectionManager()


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("starting_api_gateway")
    
    # Wait for dependencies to be ready
    import asyncio
    await asyncio.sleep(5)  # Give RabbitMQ time to start
    
    try:
        app.state.redis = await redis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379"),
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("redis_connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise
    
    # Setup message queue event handlers with retry
    mq = None
    retries = 0
    while retries < 5:
        try:
            mq = MessageQueue()
            await mq.connect()
            app.state.mq = mq
            logger.info("rabbitmq_connected")
            break
        except Exception as e:
            retries += 1
            logger.warning("waiting_for_rabbitmq", retry=retries, error=str(e))
            await asyncio.sleep(3)
    
    if mq:
        # Subscribe to agent events for WebSocket notifications
        async def handle_agent_event(event: Event):
            if event.customer_id:
                await manager.send_personal_message(
                    event.json(),
                    event.customer_id
                )
        
        try:
            await mq.subscribe_to_events(
                [EventType.AGENT_STARTED, EventType.AGENT_STOPPED, 
                 EventType.AGENT_ERROR, EventType.TRADE_EXECUTED],
                handle_agent_event
            )
        except Exception as e:
            logger.error("event_subscription_failed", error=str(e))
    
    yield
    
    # Shutdown
    if mq:
        await mq.disconnect()
    await app.state.redis.close()


# Request counter for metrics
request_counter = {}

# Create FastAPI app
app = FastAPI(
    title="AutoGen Agent API Gateway",
    description="API Gateway for managing AutoGen-powered trading agents",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware - Secure configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Add request tracking middleware
@app.middleware("http")
async def track_requests(request, call_next):
    start_time = datetime.utcnow()
    
    # Log request
    logger.info("request_started", 
               method=request.method, 
               path=request.url.path,
               client=request.client.host if request.client else "unknown")
    
    try:
        response = await call_next(request)
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Update metrics
        metrics.request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        metrics.request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # Log response
        logger.info("request_completed",
                   method=request.method,
                   path=request.url.path,
                   status=response.status_code,
                   duration=duration)
        
        return response
    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.error("request_failed",
                    method=request.method,
                    path=request.url.path,
                    error=str(e),
                    duration=duration)
        raise


# Authentication helpers
def create_access_token(customer_id: str, role: str = "customer") -> str:
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": customer_id,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: redis.Redis = Depends(lambda: app.state.redis)
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        customer_id = payload.get("sub")
        if customer_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Verify customer exists in Redis
        customer_data = await redis_client.hgetall(f"customer:{customer_id}")
        if not customer_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Customer not found"
            )
        
        return customer_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Get current admin from JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        role = payload.get("role")
        if role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# API Endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "api-gateway"
    }


@app.get("/health/detailed")
async def detailed_health_check(
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    mq = Depends(lambda: app.state.mq)
):
    health_status = {
        "service": "api-gateway",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {}
    }
    
    # Check Redis
    try:
        await redis_client.ping()
        health_status["dependencies"]["redis"] = "healthy"
    except Exception as e:
        health_status["dependencies"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check RabbitMQ
    try:
        if mq and mq.connection and not mq.connection.is_closed:
            health_status["dependencies"]["rabbitmq"] = "healthy"
        else:
            health_status["dependencies"]["rabbitmq"] = "unhealthy: connection closed"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["dependencies"]["rabbitmq"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


@app.post("/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    redis_client: redis.Redis = Depends(lambda: app.state.redis)
):
    # Verify customer credentials (simplified for demo)
    customer_key = f"customer:email:{request.email}"
    customer_id = await redis_client.get(customer_key)
    
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or API key"
        )
    
    # Verify API key with constant-time comparison
    customer_data = await redis_client.hgetall(f"customer:{customer_id}")
    stored_api_key = customer_data.get("api_key", "")
    if not hmac.compare_digest(stored_api_key, request.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or API key"
        )
    
    # Create access token
    access_token = create_access_token(customer_id)
    
    return LoginResponse(
        access_token=access_token,
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )


@app.get("/agents")
async def list_agents(
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    page: int = 1,
    limit: int = 20
):
    # Use scan_iter for efficient pagination instead of keys()
    agent_keys = []
    cursor = 0
    pattern = f"agent:{customer_id}:*"
    
    # Calculate offset
    offset = (page - 1) * limit
    count = 0
    
    async for key in redis_client.scan_iter(match=pattern, count=100):
        if count >= offset and len(agent_keys) < limit:
            agent_keys.append(key)
        count += 1
        if len(agent_keys) >= limit:
            break
    
    # Fetch agent data
    agents = []
    for key in agent_keys:
        agent_data = await redis_client.hgetall(key)
        if agent_data:
            agents.append(agent_data)
    
    return {
        "agents": agents,
        "page": page,
        "limit": limit,
        "total": count
    }


@app.post("/agents")
async def create_agent(
    request: CreateAgentRequest,
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    mq = Depends(lambda: app.state.mq)
):
    # Check customer limits
    customer_data = await redis_client.hgetall(f"customer:{customer_id}")
    max_agents = int(customer_data.get("max_agents", 5))
    current_agents = len(await redis_client.keys(f"agent:{customer_id}:*"))
    
    if current_agents >= max_agents:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent limit reached. Maximum {max_agents} agents allowed."
        )
    
    # Create agent
    agent_id = str(uuid.uuid4())
    
    agent_config = AgentConfig(
        agent_id=agent_id,
        customer_id=customer_id,
        agent_type=request.agent_type,
        name=request.name,
        description=request.description,
        config=request.config,
        autogen_config=request.autogen_config
    )
    
    # Store in Redis (convert None to empty string)
    agent_data = agent_config.dict()
    for key, value in agent_data.items():
        if value is None:
            agent_data[key] = ""
        elif isinstance(value, (dict, list)):
            agent_data[key] = json.dumps(value)
        else:
            agent_data[key] = str(value)
    
    await redis_client.hset(
        f"agent:{customer_id}:{agent_id}",
        mapping=agent_data
    )
    
    # Publish event with circuit breaker
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.AGENT_CREATED,
        source="api-gateway",
        customer_id=customer_id,
        data=agent_config.dict()
    )
    
    @with_circuit_breaker(CircuitBreakers.message_queue)
    async def publish_event():
        await mq.publish_event(event)
    
    await publish_event()
    
    # Log with structured logging
    logger.info("agent_created", agent_id=agent_id, customer_id=customer_id, agent_type=request.agent_type.value)
    
    # Update metrics
    metrics.agents_created.labels(agent_type=request.agent_type.value, customer_tier=customer_data.get("tier", "basic")).inc()
    
    return {"agent_id": agent_id, "status": "created"}


@app.post("/agents/{agent_id}/action")
async def agent_action(
    agent_id: str,
    request: AgentActionRequest,
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    mq = Depends(lambda: app.state.mq)
):
    # Verify agent belongs to customer
    agent_key = f"agent:{customer_id}:{agent_id}"
    agent_data = await redis_client.hgetall(agent_key)
    
    if not agent_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Send action to agent manager
    await mq.send_direct_message(
        target="agent-manager",
        message_type=f"agent.{request.action}",
        payload={
            "agent_id": agent_id,
            "customer_id": customer_id,
            "config": request.config
        }
    )
    
    return {"status": "action_sent", "action": request.action}


@app.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis)
):
    agent_key = f"agent:{customer_id}:{agent_id}"
    agent_data = await redis_client.hgetall(agent_key)
    
    if not agent_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Get instance status
    instance_data = await redis_client.hgetall(f"agent_instance:{agent_id}")
    
    return {
        "agent": agent_data,
        "instance": instance_data
    }


@app.post("/teams")
async def create_team(
    request: CreateTeamRequest,
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    mq = Depends(lambda: app.state.mq)
):
    # Check team limits
    customer_data = await redis_client.hgetall(f"customer:{customer_id}")
    max_teams = int(customer_data.get("max_teams", 2))
    current_teams = len(await redis_client.keys(f"team:{customer_id}:*"))
    
    if current_teams >= max_teams:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Team limit reached. Maximum {max_teams} teams allowed."
        )
    
    # Verify all agents belong to customer
    for agent_id in request.agent_ids:
        agent_key = f"agent:{customer_id}:{agent_id}"
        if not await redis_client.exists(agent_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent {agent_id} not found or doesn't belong to customer"
            )
    
    # Create team
    team_id = str(uuid.uuid4())
    
    team = AgentTeam(
        team_id=team_id,
        customer_id=customer_id,
        name=request.name,
        description=request.description,
        agent_ids=request.agent_ids,
        orchestrator_config=request.orchestrator_config
    )
    
    # Store in Redis
    await redis_client.hset(
        f"team:{customer_id}:{team_id}",
        mapping=team.dict()
    )
    
    # Publish event
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TEAM_CREATED,
        source="api-gateway",
        customer_id=customer_id,
        data=team.dict()
    )
    await mq.publish_event(event)
    
    return {"team_id": team_id, "status": "created"}


# Task Management Endpoints
@app.post("/tasks")
async def create_task(
    request: Dict[str, Any],
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    mq = Depends(lambda: app.state.mq)
):
    """Create a new task for an agent"""
    agent_id = request.get("agent_id")
    if not agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_id is required"
        )
    
    # Verify agent belongs to customer
    agent_key = f"agent:{customer_id}:{agent_id}"
    agent_data = await redis_client.hgetall(agent_key)
    
    if not agent_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Create task
    task_id = str(uuid.uuid4())
    task_data = {
        "task_id": task_id,
        "agent_id": agent_id,
        "customer_id": customer_id,
        "type": request.get("type", "analysis"),
        "payload": json.dumps(request.get("payload", {})),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Store task in Redis
    await redis_client.hset(
        f"task:{customer_id}:{task_id}",
        mapping=task_data
    )
    
    # Send task to agent manager
    await mq.send_direct_message(
        target="agent-manager",
        message_type="task.execute",
        payload=task_data
    )
    
    return {"id": task_id, "status": "pending"}


@app.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis)
):
    """Get task status and result"""
    task_key = f"task:{customer_id}:{task_id}"
    task_data = await redis_client.hgetall(task_key)
    
    if not task_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Parse payload if it's JSON
    if b'payload' in task_data:
        try:
            task_data[b'payload'] = json.loads(task_data[b'payload'])
        except:
            pass
    
    # Convert bytes to strings
    result = {}
    for key, value in task_data.items():
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        result[key] = value
    
    return result


# Team Management Endpoints
@app.post("/teams")
async def create_team(
    request: Dict[str, Any],
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    mq = Depends(lambda: app.state.mq)
):
    """Create a new agent team"""
    # Check customer limits
    customer_data = await redis_client.hgetall(f"customer:{customer_id}")
    max_teams = int(customer_data.get(b"max_teams", customer_data.get("max_teams", 2)))
    
    # Count existing teams
    team_count = 0
    async for _ in redis_client.scan_iter(match=f"team:{customer_id}:*"):
        team_count += 1
    
    if team_count >= max_teams:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Team limit reached. Maximum {max_teams} teams allowed."
        )
    
    # Create team
    team_id = str(uuid.uuid4())
    team_data = {
        "team_id": team_id,
        "customer_id": customer_id,
        "name": request.get("name", "Unnamed Team"),
        "agent_ids": json.dumps(request.get("agent_ids", [])),
        "config": json.dumps(request.get("config", {})),
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Store team in Redis
    await redis_client.hset(
        f"team:{customer_id}:{team_id}",
        mapping=team_data
    )
    
    # Publish event
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.TEAM_CREATED,
        source="api-gateway",
        customer_id=customer_id,
        data=team_data
    )
    
    await mq.publish_event(event)
    
    return {"id": team_id, "status": "created"}


# Agent Update Endpoint
@app.put("/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    request: Dict[str, Any],
    customer_id: str = Depends(get_current_customer),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    mq = Depends(lambda: app.state.mq)
):
    """Update agent configuration"""
    agent_key = f"agent:{customer_id}:{agent_id}"
    agent_data = await redis_client.hgetall(agent_key)
    
    if not agent_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Update config
    if "config" in request:
        await redis_client.hset(
            agent_key,
            "config",
            json.dumps(request["config"])
        )
    
    # Publish update event
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.AGENT_UPDATED,
        source="api-gateway",
        customer_id=customer_id,
        data={
            "agent_id": agent_id,
            "updates": request
        }
    )
    
    await mq.publish_event(event)
    
    return {"status": "updated", "agent_id": agent_id}


# Metrics Endpoint
@app.get("/metrics")
async def get_metrics(
    customer_id: str = Depends(get_current_customer)
):
    """Return Prometheus metrics"""
    # Generate metrics in Prometheus format
    metrics = []
    
    # API request metrics
    metrics.append(f'# HELP api_requests_total Total API requests')
    metrics.append(f'# TYPE api_requests_total counter')
    metrics.append(f'api_requests_total{{customer_id="{customer_id}"}} {request_counter.get(customer_id, 0)}')
    
    # Add more metrics as needed
    metrics.append(f'# HELP api_request_duration_seconds API request duration')
    metrics.append(f'# TYPE api_request_duration_seconds histogram')
    
    return "\n".join(metrics)


# Admin Endpoints
@app.post("/admin/auth/login")
async def admin_login(
    api_key: str,
    redis_client: redis.Redis = Depends(lambda: app.state.redis)
):
    """Admin login with API key"""
    # Get admin API key from environment or Docker secret
    try:
        with open('/run/secrets/admin_api_key', 'r') as f:
            admin_api_key = f.read().strip()
    except:
        admin_api_key = os.getenv("ADMIN_API_KEY", "default_admin_key_change_me")
    
    if api_key != admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    
    # Create admin token
    access_token = create_access_token("admin", role="admin")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "admin"
    }


@app.get("/admin/agents", response_model=List[Dict[str, Any]])
async def admin_list_all_agents(
    admin_id: str = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    page: int = 1,
    limit: int = 50
):
    """List all agents across all customers (admin only)"""
    agents = []
    
    # Scan all agent keys
    async for key in redis_client.scan_iter(match="agent:*:*", count=100):
        agent_data = await redis_client.hgetall(key)
        if agent_data:
            # Include customer_id in response
            agents.append({
                **agent_data,
                "key": key
            })
    
    # Sort by creation time if available
    agents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Paginate
    start = (page - 1) * limit
    end = start + limit
    
    return agents[start:end]


@app.post("/admin/agents/{agent_id}/stop")
async def admin_stop_agent(
    agent_id: str,
    reason: str,
    force: bool = False,
    admin_id: str = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(lambda: app.state.redis),
    mq = Depends(lambda: app.state.mq)
):
    """Admin force stop an agent"""
    # Send stop command to agent manager
    await mq.send_direct_message(
        target="agent-manager",
        message_type="admin.agent.stop",
        payload={
            "agent_id": agent_id,
            "reason": reason,
            "force": force,
            "admin_id": admin_id
        }
    )
    
    # Log admin action
    await redis_client.hset(
        f"admin_audit:{datetime.utcnow().isoformat()}",
        mapping={
            "action": "stop_agent",
            "admin_id": admin_id,
            "agent_id": agent_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return {"status": "stop_command_sent", "agent_id": agent_id}


@app.get("/admin/stats/overview")
async def admin_stats_overview(
    admin_id: str = Depends(get_current_admin),
    redis_client: redis.Redis = Depends(lambda: app.state.redis)
):
    """Get platform overview statistics (admin only)"""
    stats = {
        "total_customers": 0,
        "total_agents": 0,
        "total_tasks": 0,
        "total_teams": 0,
        "agents_by_status": {},
        "agents_by_type": {}
    }
    
    # Count customers
    async for _ in redis_client.scan_iter(match="customer:*", count=100):
        stats["total_customers"] += 1
    
    # Count and analyze agents
    async for key in redis_client.scan_iter(match="agent:*:*", count=100):
        stats["total_agents"] += 1
        agent_data = await redis_client.hgetall(key)
        
        # Count by status
        status = agent_data.get("status", "unknown")
        stats["agents_by_status"][status] = stats["agents_by_status"].get(status, 0) + 1
        
        # Count by type
        agent_type = agent_data.get("agent_type", "unknown")
        stats["agents_by_type"][agent_type] = stats["agents_by_type"].get(agent_type, 0) + 1
    
    # Count tasks
    async for _ in redis_client.scan_iter(match="task:*:*", count=100):
        stats["total_tasks"] += 1
    
    # Count teams
    async for _ in redis_client.scan_iter(match="team:*:*", count=100):
        stats["total_teams"] += 1
    
    return stats


@app.post("/admin/broadcast")
async def admin_broadcast_message(
    message: str,
    target: str = "all",  # all, customers, agents
    admin_id: str = Depends(get_current_admin),
    mq = Depends(lambda: app.state.mq)
):
    """Broadcast a message to all connected clients (admin only)"""
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.ADMIN_BROADCAST,
        source="admin",
        customer_id="*",
        data={
            "message": message,
            "target": target,
            "admin_id": admin_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    await mq.publish_event(event)
    
    return {"status": "broadcast_sent", "target": target}


@app.websocket("/ws/{customer_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    customer_id: str,
    token: str,
    redis_client: redis.Redis = Depends(lambda: app.state.redis)
):
    # Verify JWT token for WebSocket authentication
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        token_customer_id = payload.get("sub")
        if token_customer_id != customer_id:
            await websocket.close(code=4001, reason="Invalid authentication")
            return
    except jwt.InvalidTokenError:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Verify customer exists
    customer_data = await redis_client.hgetall(f"customer:{customer_id}")
    if not customer_data:
        await websocket.close(code=4001, reason="Customer not found")
        return
    
    await manager.connect(customer_id, websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Could handle client messages here if needed
    except WebSocketDisconnect:
        manager.disconnect(customer_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)