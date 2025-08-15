"""
Orchestrator Management API Endpoints
Handles registration, heartbeat, and control operations for orchestrators
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import structlog
import httpx
import asyncio
from redis import Redis

from ..config import settings
from ..dependencies import get_redis, get_current_user

logger = structlog.get_logger()

router = APIRouter(prefix="/api/orchestrators", tags=["orchestrators"])


# Data Models
class OrchestratorRegistration(BaseModel):
    """Orchestrator registration request"""
    name: str = Field(..., description="Unique orchestrator name")
    url: str = Field(..., description="Orchestrator API endpoint URL")
    capabilities: List[str] = Field(default_factory=list, description="List of supported capabilities")
    version: str = Field(..., description="Orchestrator version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class OrchestratorHeartbeat(BaseModel):
    """Heartbeat data from orchestrator"""
    status: str = Field("healthy", description="Current status")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Current metrics")
    active_agents: List[str] = Field(default_factory=list, description="List of active agents")
    load: float = Field(0.0, description="Current load (0-1)")


class OrchestratorControl(BaseModel):
    """Control command for orchestrator"""
    command: str = Field(..., description="Command to execute (start/stop/restart)")
    target: str = Field(..., description="Target agent or service")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")


class OrchestratorStatus(BaseModel):
    """Orchestrator status response"""
    id: str
    name: str
    url: str
    status: str
    last_heartbeat: datetime
    capabilities: List[str]
    version: str
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]


# Helper Functions
def get_orchestrator_key(orchestrator_id: str) -> str:
    """Get Redis key for orchestrator data"""
    return f"orchestrator:{orchestrator_id}"


def get_orchestrator_list_key() -> str:
    """Get Redis key for orchestrator list"""
    return "orchestrators:list"


async def send_control_command(url: str, command: OrchestratorControl) -> Dict[str, Any]:
    """Send control command to orchestrator"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{url}/control",
                json=command.dict(),
                headers={"Authorization": f"Bearer {settings.master_secret_key}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to send control command", error=str(e), url=url)
            raise HTTPException(status_code=502, detail=f"Failed to communicate with orchestrator: {str(e)}")


# API Endpoints
@router.post("/register", response_model=Dict[str, str])
async def register_orchestrator(
    registration: OrchestratorRegistration,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis)
):
    """
    Register a new orchestrator with the central manager
    """
    try:
        # Generate unique ID for orchestrator
        orchestrator_id = f"{registration.name}_{datetime.utcnow().timestamp()}"
        
        # Store orchestrator data in Redis
        # Convert metadata values to strings (Redis doesn't support all Python types)
        metadata_str = {k: str(v) for k, v in registration.metadata.items()}
        
        orchestrator_data = {
            "id": orchestrator_id,
            "name": registration.name,
            "url": registration.url,
            "capabilities": ",".join(registration.capabilities),
            "version": registration.version,
            "status": "active",
            "registered_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat(),
            **metadata_str
        }
        
        # Store in Redis with TTL of 5 minutes (heartbeat should refresh)
        await redis.hset(get_orchestrator_key(orchestrator_id), mapping=orchestrator_data)
        await redis.expire(get_orchestrator_key(orchestrator_id), 300)
        
        # Add to orchestrator list
        await redis.sadd(get_orchestrator_list_key(), orchestrator_id)
        
        logger.info("Orchestrator registered", 
                   orchestrator_id=orchestrator_id, 
                   name=registration.name,
                   url=registration.url)
        
        return {
            "orchestrator_id": orchestrator_id,
            "status": "registered",
            "message": "Orchestrator successfully registered"
        }
        
    except Exception as e:
        logger.error("Failed to register orchestrator", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{orchestrator_id}/heartbeat")
async def orchestrator_heartbeat(
    orchestrator_id: str,
    heartbeat: OrchestratorHeartbeat,
    redis: Redis = Depends(get_redis)
):
    """
    Receive heartbeat from orchestrator
    """
    try:
        # Check if orchestrator exists
        if not await redis.exists(get_orchestrator_key(orchestrator_id)):
            raise HTTPException(status_code=404, detail="Orchestrator not found")
        
        # Update heartbeat data
        updates = {
            "last_heartbeat": datetime.utcnow().isoformat(),
            "status": heartbeat.status,
            "active_agents": ",".join(heartbeat.active_agents),
            "load": str(heartbeat.load),
            "metrics": str(heartbeat.metrics)
        }
        
        await redis.hset(get_orchestrator_key(orchestrator_id), mapping=updates)
        await redis.expire(get_orchestrator_key(orchestrator_id), 300)  # Refresh TTL
        
        logger.debug("Heartbeat received", orchestrator_id=orchestrator_id, status=heartbeat.status)
        
        return {"status": "acknowledged", "next_heartbeat": 30}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process heartbeat", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[OrchestratorStatus])
async def list_orchestrators(
    redis: Redis = Depends(get_redis),
    _current_user: dict = Depends(get_current_user)
):
    """
    List all registered orchestrators
    """
    try:
        # Get all orchestrator IDs
        orchestrator_ids = await redis.smembers(get_orchestrator_list_key())
        
        orchestrators = []
        for orch_id in orchestrator_ids:
            orch_id = orch_id.decode() if isinstance(orch_id, bytes) else orch_id
            data = await redis.hgetall(get_orchestrator_key(orch_id))
            
            if data:
                # Convert bytes to strings
                data = {k.decode() if isinstance(k, bytes) else k: 
                       v.decode() if isinstance(v, bytes) else v 
                       for k, v in data.items()}
                
                orchestrators.append(OrchestratorStatus(
                    id=data.get("id", orch_id),
                    name=data.get("name", "unknown"),
                    url=data.get("url", ""),
                    status=data.get("status", "unknown"),
                    last_heartbeat=datetime.fromisoformat(data.get("last_heartbeat", datetime.utcnow().isoformat())),
                    capabilities=data.get("capabilities", "").split(",") if data.get("capabilities") else [],
                    version=data.get("version", "unknown"),
                    metrics=eval(data.get("metrics", "{}")) if data.get("metrics") else {},
                    metadata={k: v for k, v in data.items() 
                             if k not in ["id", "name", "url", "status", "last_heartbeat", 
                                         "capabilities", "version", "metrics"]}
                ))
        
        return orchestrators
        
    except Exception as e:
        logger.error("Failed to list orchestrators", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{orchestrator_id}/control")
async def control_orchestrator(
    orchestrator_id: str,
    control: OrchestratorControl,
    redis: Redis = Depends(get_redis),
    _current_user: dict = Depends(get_current_user)
):
    """
    Send control command to orchestrator
    """
    try:
        # Get orchestrator data
        data = await redis.hgetall(get_orchestrator_key(orchestrator_id))
        if not data:
            raise HTTPException(status_code=404, detail="Orchestrator not found")
        
        # Convert bytes to strings
        data = {k.decode() if isinstance(k, bytes) else k: 
               v.decode() if isinstance(v, bytes) else v 
               for k, v in data.items()}
        
        url = data.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="Orchestrator URL not found")
        
        # Send control command
        result = await send_control_command(url, control)
        
        logger.info("Control command sent", 
                   orchestrator_id=orchestrator_id,
                   command=control.command,
                   target=control.target)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to send control command", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{orchestrator_id}/metrics")
async def get_orchestrator_metrics(
    orchestrator_id: str,
    redis: Redis = Depends(get_redis),
    _current_user: dict = Depends(get_current_user)
):
    """
    Get metrics from specific orchestrator
    """
    try:
        # Get orchestrator data
        data = await redis.hgetall(get_orchestrator_key(orchestrator_id))
        if not data:
            raise HTTPException(status_code=404, detail="Orchestrator not found")
        
        # Convert bytes to strings
        data = {k.decode() if isinstance(k, bytes) else k: 
               v.decode() if isinstance(v, bytes) else v 
               for k, v in data.items()}
        
        metrics = eval(data.get("metrics", "{}")) if data.get("metrics") else {}
        
        return {
            "orchestrator_id": orchestrator_id,
            "name": data.get("name", "unknown"),
            "last_update": data.get("last_heartbeat", "unknown"),
            "metrics": metrics,
            "load": float(data.get("load", 0)),
            "active_agents": data.get("active_agents", "").split(",") if data.get("active_agents") else []
        }
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{orchestrator_id}")
async def unregister_orchestrator(
    orchestrator_id: str,
    redis: Redis = Depends(get_redis),
    _current_user: dict = Depends(get_current_user)
):
    """
    Unregister an orchestrator
    """
    try:
        # Remove from Redis
        await redis.delete(get_orchestrator_key(orchestrator_id))
        await redis.srem(get_orchestrator_list_key(), orchestrator_id)
        
        logger.info("Orchestrator unregistered", orchestrator_id=orchestrator_id)
        
        return {"status": "unregistered", "orchestrator_id": orchestrator_id}
        
    except Exception as e:
        logger.error("Failed to unregister orchestrator", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))