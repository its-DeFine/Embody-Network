"""Agent management routes"""
import json
import uuid
from typing import List
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import docker

from ..dependencies import get_current_user, get_redis, get_docker
from ..config import settings
from ..core.orchestration.orchestrator import orchestrator, Event
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

class AgentType(str, Enum):
    TRADING = "trading"
    ANALYSIS = "analysis"
    RISK = "risk"
    PORTFOLIO = "portfolio"

class CreateAgentRequest(BaseModel):
    name: str
    agent_type: AgentType
    config: dict = {}

class AgentResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    created_at: str
    config: dict

@router.get("", response_model=List[AgentResponse])
async def list_agents(
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """List all agents for the current user"""
    agents = []
    
    # Get all agent keys
    keys = await redis.keys("agent:*")
    for key in keys:
        data = await redis.get(key)
        if data:
            agent = json.loads(data)
            if agent.get("owner") == user:
                agents.append(AgentResponse(**agent))
    
    return agents

@router.post("", response_model=AgentResponse)
async def create_agent(
    request: CreateAgentRequest,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Create a new agent"""
    agent_id = str(uuid.uuid4())
    
    agent = {
        "id": agent_id,
        "name": request.name,
        "type": request.agent_type,
        "status": "created",
        "created_at": datetime.utcnow().isoformat(),
        "config": request.config,
        "owner": user
    }
    
    # Save to Redis
    await redis.set(f"agent:{agent_id}", json.dumps(agent))
    
    return AgentResponse(**agent)

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Get agent details"""
    data = await redis.get(f"agent:{agent_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = json.loads(data)
    if agent.get("owner") != user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return AgentResponse(**agent)

@router.post("/{agent_id}/start")
async def start_agent(
    agent_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Start an agent container"""
    # Get agent data
    data = await redis.get(f"agent:{agent_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = json.loads(data)
    if agent.get("owner") != user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Try to start container
    try:
        docker_client = get_docker()
        image = settings.agent_image
        network = settings.docker_network

        logger.info(
            "Starting agent container",
            extra={
                "agent_id": agent_id,
                "image": image,
                "network": network,
                "agent_type": str(agent["type"]),
            },
        )

        container = docker_client.containers.run(
            image,
            detach=True,
            name=f"agent-{agent_id}",
            environment={
                "AGENT_ID": agent_id,
                "AGENT_TYPE": agent["type"],
                "AGENT_CONFIG": json.dumps(agent["config"]),
                "REDIS_URL": settings.redis_url,
            },
            network=network,
            restart_policy={"Name": "unless-stopped"},
            labels={
                "autogen.agent.capable": "true",
                "container.type": "agent",
            },
        )
        
        # Update status
        agent["status"] = "running"
        agent["container_id"] = container.id
        await redis.set(f"agent:{agent_id}", json.dumps(agent))
        
        return {"message": "Agent started", "container_id": container.id}
        
    except Exception as e:
        # Fallback: simulate agent start without Docker
        logger.warning(f"Docker not available or failed to start agent: {e}")
        agent["status"] = "running"
        agent["container_id"] = f"simulated-{agent_id}"
        await redis.set(f"agent:{agent_id}", json.dumps(agent))
        
        # Publish event for orchestrator
        await orchestrator.publish_event(Event(
            "agent.started",
            f"agent:{agent_id}",
            {"agent_id": agent_id, "simulated": True}
        ))
        
        return {"message": "Agent started (simulated)", "simulated": True}

@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Stop an agent container"""
    # Get agent data
    data = await redis.get(f"agent:{agent_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = json.loads(data)
    if agent.get("owner") != user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Stop container
    if "container_id" in agent:
        try:
            docker_client = get_docker()
            if not agent["container_id"].startswith("simulated-"):
                container = docker_client.containers.get(agent["container_id"])
                container.stop()
                container.remove()
        except Exception as e:
            logger.warning(f"Could not stop container: {e}")
    
    # Update status
    agent["status"] = "stopped"
    agent.pop("container_id", None)
    await redis.set(f"agent:{agent_id}", json.dumps(agent))
    
    # Publish event
    await orchestrator.publish_event(Event(
        "agent.stopped",
        f"agent:{agent_id}",
        {"agent_id": agent_id}
    ))
    
    return {"message": "Agent stopped"}

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Delete an agent"""
    # Stop if running
    await stop_agent(agent_id, user, redis)
    
    # Delete from Redis
    await redis.delete(f"agent:{agent_id}")
    
    return {"message": "Agent deleted"}