import os
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
import docker
import redis.asyncio as redis

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import shared modules
import sys
sys.path.append('/app')
from shared.utils.resilience import with_circuit_breaker, CircuitBreakers, get_logger

# Security
security = HTTPBearer()

# Admin API key from Docker secret
def get_admin_api_key():
    """Get admin API key from Docker secret or environment"""
    try:
        with open('/run/secrets/admin_api_key', 'r') as f:
            return f.read().strip()
    except:
        return os.getenv("ADMIN_API_KEY", "default_admin_key_change_me")

ADMIN_API_KEY = get_admin_api_key()


# Request/Response models
class KillswitchRequest(BaseModel):
    reason: str
    force: bool = False
    target: Optional[str] = None  # 'all', 'customer_id', or 'agent_id'
    target_id: Optional[str] = None

class AdminActionResponse(BaseModel):
    action: str
    status: str
    affected_count: int
    details: Dict[str, Any]
    timestamp: str

class ContainerStats(BaseModel):
    container_id: str
    agent_id: str
    customer_id: str
    cpu_percent: float
    memory_usage_mb: float
    network_io_mb: float
    status: str
    uptime_seconds: int

class ResourceQuota(BaseModel):
    customer_id: str
    max_containers: int = 10
    max_cpu_per_container: float = 1.0  # CPU cores
    max_memory_per_container: int = 2048  # MB
    max_total_cpu: float = 10.0
    max_total_memory: int = 20480  # MB


# Admin Control Service
class AdminControlService:
    def __init__(self, docker_client: docker.DockerClient, redis_client: redis.Redis):
        self.docker = docker_client
        self.redis = redis_client
        self.logger = get_logger("admin-control")
        
    async def emergency_stop_all(self, reason: str, force: bool = False) -> AdminActionResponse:
        """Emergency stop all agent containers"""
        self.logger.warning(f"KILLSWITCH ACTIVATED: Stopping all agents. Reason: {reason}")
        
        affected_containers = []
        errors = []
        
        try:
            # Get all containers with agent labels
            containers = self.docker.containers.list(
                filters={"label": "agent_id"}
            )
            
            for container in containers:
                try:
                    agent_id = container.labels.get("agent_id")
                    customer_id = container.labels.get("customer_id")
                    
                    if force:
                        container.kill()
                    else:
                        container.stop(timeout=10)
                    
                    affected_containers.append({
                        "agent_id": agent_id,
                        "customer_id": customer_id,
                        "container_id": container.id[:12]
                    })
                    
                    # Update Redis status
                    await self.redis.hset(
                        f"agent_instance:{agent_id}",
                        "status", "killed_by_admin"
                    )
                    
                    # Log admin action
                    await self._log_admin_action("killswitch_all", {
                        "agent_id": agent_id,
                        "customer_id": customer_id,
                        "reason": reason,
                        "force": force
                    })
                    
                except Exception as e:
                    errors.append({
                        "container_id": container.id[:12],
                        "error": str(e)
                    })
            
            return AdminActionResponse(
                action="emergency_stop_all",
                status="completed",
                affected_count=len(affected_containers),
                details={
                    "stopped_containers": affected_containers,
                    "errors": errors,
                    "reason": reason
                },
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"Killswitch failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Killswitch operation failed: {str(e)}"
            )
    
    async def stop_customer_agents(self, customer_id: str, reason: str, force: bool = False) -> AdminActionResponse:
        """Stop all agents for a specific customer"""
        self.logger.warning(f"Stopping all agents for customer {customer_id}. Reason: {reason}")
        
        affected_containers = []
        errors = []
        
        try:
            # Get containers for specific customer
            containers = self.docker.containers.list(
                filters={
                    "label": [
                        f"customer_id={customer_id}"
                    ]
                }
            )
            
            for container in containers:
                try:
                    agent_id = container.labels.get("agent_id")
                    
                    if force:
                        container.kill()
                    else:
                        container.stop(timeout=10)
                    
                    affected_containers.append({
                        "agent_id": agent_id,
                        "container_id": container.id[:12]
                    })
                    
                    # Update Redis status
                    await self.redis.hset(
                        f"agent_instance:{agent_id}",
                        "status", "killed_by_admin"
                    )
                    
                except Exception as e:
                    errors.append({
                        "container_id": container.id[:12],
                        "error": str(e)
                    })
            
            # Log admin action
            await self._log_admin_action("killswitch_customer", {
                "customer_id": customer_id,
                "affected_count": len(affected_containers),
                "reason": reason,
                "force": force
            })
            
            return AdminActionResponse(
                action="stop_customer_agents",
                status="completed",
                affected_count=len(affected_containers),
                details={
                    "customer_id": customer_id,
                    "stopped_containers": affected_containers,
                    "errors": errors,
                    "reason": reason
                },
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"Customer killswitch failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Customer killswitch operation failed: {str(e)}"
            )
    
    async def force_stop_agent(self, agent_id: str, reason: str) -> AdminActionResponse:
        """Force stop a specific agent"""
        self.logger.warning(f"Force stopping agent {agent_id}. Reason: {reason}")
        
        try:
            # Find container by agent_id label
            containers = self.docker.containers.list(
                filters={"label": f"agent_id={agent_id}"}
            )
            
            if not containers:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent {agent_id} not found"
                )
            
            container = containers[0]
            customer_id = container.labels.get("customer_id")
            
            # Force kill the container
            container.kill()
            
            # Update Redis status
            await self.redis.hset(
                f"agent_instance:{agent_id}",
                "status", "killed_by_admin"
            )
            
            # Log admin action
            await self._log_admin_action("force_stop_agent", {
                "agent_id": agent_id,
                "customer_id": customer_id,
                "reason": reason
            })
            
            return AdminActionResponse(
                action="force_stop_agent",
                status="completed",
                affected_count=1,
                details={
                    "agent_id": agent_id,
                    "customer_id": customer_id,
                    "container_id": container.id[:12],
                    "reason": reason
                },
                timestamp=datetime.utcnow().isoformat()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Force stop failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Force stop operation failed: {str(e)}"
            )
    
    async def get_container_stats(self) -> List[ContainerStats]:
        """Get resource usage statistics for all containers"""
        stats = []
        
        try:
            containers = self.docker.containers.list(
                filters={"label": "agent_id"}
            )
            
            for container in containers:
                try:
                    # Get container stats
                    container_stats = container.stats(stream=False)
                    
                    # Calculate CPU percentage
                    cpu_delta = container_stats['cpu_stats']['cpu_usage']['total_usage'] - \
                               container_stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = container_stats['cpu_stats']['system_cpu_usage'] - \
                                  container_stats['precpu_stats']['system_cpu_usage']
                    cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
                    
                    # Calculate memory usage
                    memory_usage_mb = container_stats['memory_stats']['usage'] / (1024 * 1024)
                    
                    # Calculate network I/O
                    net_io = 0
                    if 'networks' in container_stats:
                        for interface in container_stats['networks'].values():
                            net_io += interface.get('rx_bytes', 0) + interface.get('tx_bytes', 0)
                    network_io_mb = net_io / (1024 * 1024)
                    
                    # Calculate uptime
                    created = container.attrs['Created']
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    uptime_seconds = int((datetime.utcnow() - created_dt.replace(tzinfo=None)).total_seconds())
                    
                    stats.append(ContainerStats(
                        container_id=container.id[:12],
                        agent_id=container.labels.get("agent_id", "unknown"),
                        customer_id=container.labels.get("customer_id", "unknown"),
                        cpu_percent=round(cpu_percent, 2),
                        memory_usage_mb=round(memory_usage_mb, 2),
                        network_io_mb=round(network_io_mb, 2),
                        status=container.status,
                        uptime_seconds=uptime_seconds
                    ))
                    
                except Exception as e:
                    self.logger.error(f"Error getting stats for container {container.id}: {str(e)}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting container stats: {str(e)}")
            return stats
    
    async def set_resource_quota(self, quota: ResourceQuota) -> Dict[str, Any]:
        """Set resource quotas for a customer"""
        try:
            # Store quota in Redis
            await self.redis.hset(
                f"customer_quota:{quota.customer_id}",
                mapping=quota.dict()
            )
            
            # Log admin action
            await self._log_admin_action("set_resource_quota", quota.dict())
            
            return {"status": "success", "quota": quota.dict()}
            
        except Exception as e:
            self.logger.error(f"Error setting resource quota: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to set resource quota: {str(e)}"
            )
    
    async def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get admin action audit logs"""
        try:
            # Get recent audit logs from Redis
            logs = []
            cursor = 0
            
            async for key in self.redis.scan_iter(match="admin_audit:*", count=limit):
                log_data = await self.redis.hgetall(key)
                logs.append({
                    "timestamp": log_data.get("timestamp"),
                    "action": log_data.get("action"),
                    "details": json.loads(log_data.get("details", "{}"))
                })
            
            # Sort by timestamp descending
            logs.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return logs[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting audit logs: {str(e)}")
            return []
    
    async def _log_admin_action(self, action: str, details: Dict[str, Any]):
        """Log admin actions for audit trail"""
        try:
            timestamp = datetime.utcnow().isoformat()
            log_key = f"admin_audit:{timestamp}:{action}"
            
            await self.redis.hset(
                log_key,
                mapping={
                    "timestamp": timestamp,
                    "action": action,
                    "details": json.dumps(details)
                }
            )
            
            # Expire after 90 days
            await self.redis.expire(log_key, 90 * 24 * 60 * 60)
            
        except Exception as e:
            self.logger.error(f"Error logging admin action: {str(e)}")


# FastAPI app setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Initialize connections
    app.state.redis = await redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379"),
        encoding="utf-8",
        decode_responses=True
    )
    
    app.state.docker = docker.from_env()
    
    app.state.admin_service = AdminControlService(
        app.state.docker,
        app.state.redis
    )
    
    yield
    
    # Cleanup
    await app.state.redis.close()


app = FastAPI(
    title="AutoGen Admin Control API",
    description="Administrative control panel for AutoGen agent platform",
    version="1.0.0",
    lifespan=lifespan
)


# Authentication dependency
async def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify admin API key"""
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    return True


# Admin endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "admin-control"}


@app.post("/killswitch/all", response_model=AdminActionResponse)
async def emergency_killswitch(
    request: KillswitchRequest,
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_admin),
    admin_service: AdminControlService = Depends(lambda: app.state.admin_service)
):
    """Emergency stop all agent containers"""
    return await admin_service.emergency_stop_all(
        reason=request.reason,
        force=request.force
    )


@app.post("/killswitch/customer/{customer_id}", response_model=AdminActionResponse)
async def customer_killswitch(
    customer_id: str,
    request: KillswitchRequest,
    _: bool = Depends(verify_admin),
    admin_service: AdminControlService = Depends(lambda: app.state.admin_service)
):
    """Stop all agents for a specific customer"""
    return await admin_service.stop_customer_agents(
        customer_id=customer_id,
        reason=request.reason,
        force=request.force
    )


@app.post("/agents/{agent_id}/force-stop", response_model=AdminActionResponse)
async def force_stop_agent(
    agent_id: str,
    request: KillswitchRequest,
    _: bool = Depends(verify_admin),
    admin_service: AdminControlService = Depends(lambda: app.state.admin_service)
):
    """Force stop a specific agent"""
    return await admin_service.force_stop_agent(
        agent_id=agent_id,
        reason=request.reason
    )


@app.get("/stats/containers", response_model=List[ContainerStats])
async def get_container_stats(
    _: bool = Depends(verify_admin),
    admin_service: AdminControlService = Depends(lambda: app.state.admin_service)
):
    """Get resource usage statistics for all containers"""
    return await admin_service.get_container_stats()


@app.post("/quotas", response_model=Dict[str, Any])
async def set_resource_quota(
    quota: ResourceQuota,
    _: bool = Depends(verify_admin),
    admin_service: AdminControlService = Depends(lambda: app.state.admin_service)
):
    """Set resource quotas for a customer"""
    return await admin_service.set_resource_quota(quota)


@app.get("/audit-logs", response_model=List[Dict[str, Any]])
async def get_audit_logs(
    limit: int = 100,
    _: bool = Depends(verify_admin),
    admin_service: AdminControlService = Depends(lambda: app.state.admin_service)
):
    """Get admin action audit logs"""
    return await admin_service.get_audit_logs(limit=limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)