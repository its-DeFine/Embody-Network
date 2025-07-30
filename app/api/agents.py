"""Agent management routes"""
import json
import uuid
from typing import List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import docker

from ..dependencies import get_current_user, get_redis, get_docker

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

class AgentType(str):
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
    redis = Depends(get_redis),
    docker_client = Depends(get_docker)
):
    """Start an agent container"""
    # Get agent data
    data = await redis.get(f"agent:{agent_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = json.loads(data)
    if agent.get("owner") != user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Start container
    try:
        container = docker_client.containers.run(
            "autogen-agent:latest",
            detach=True,
            name=f"agent-{agent_id}",
            environment={
                "AGENT_ID": agent_id,
                "AGENT_TYPE": agent["type"],
                "AGENT_CONFIG": json.dumps(agent["config"]),
                "REDIS_URL": "redis://redis:6379"
            },
            network="autogen-network",
            restart_policy={"Name": "unless-stopped"}
        )
        
        # Update status
        agent["status"] = "running"
        agent["container_id"] = container.id
        await redis.set(f"agent:{agent_id}", json.dumps(agent))
        
        return {"message": "Agent started", "container_id": container.id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis),
    docker_client = Depends(get_docker)
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
            container = docker_client.containers.get(agent["container_id"])
            container.stop()
            container.remove()
        except:
            pass
    
    # Update status
    agent["status"] = "stopped"
    agent.pop("container_id", None)
    await redis.set(f"agent:{agent_id}", json.dumps(agent))
    
    return {"message": "Agent stopped"}

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis),
    docker_client = Depends(get_docker)
):
    """Delete an agent"""
    # Stop if running
    await stop_agent(agent_id, user, redis, docker_client)
    
    # Delete from Redis
    await redis.delete(f"agent:{agent_id}")
    
    return {"message": "Agent deleted"}