from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import httpx

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..dependencies import get_current_user
from ..core.embodiment.registry import EmbodiedAgent, embodiment_registry
from ..core.embodiment.command_bus import EmbodimentCommand, command_bus
from ..core.embodiment.autonomy import autonomy_controller

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/embodiment", tags=["embodiment"])


class RegisterAgentRequest(BaseModel):
    agent_id: str
    name: str
    endpoint: str
    capabilities: List[str] = []
    orchestrator_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


@router.post("/agents/register")
async def register_agent(req: RegisterAgentRequest, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    agent = EmbodiedAgent(
        agent_id=req.agent_id,
        name=req.name,
        endpoint=req.endpoint,
        capabilities=req.capabilities,
        orchestrator_id=req.orchestrator_id,
        status="online",
        metadata=req.metadata,
        last_heartbeat=datetime.utcnow().isoformat(),
    )
    await embodiment_registry.register(agent)
    return {"success": True, "agent_id": req.agent_id}


@router.get("/agents")
async def list_agents(user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return await embodiment_registry.list_agents()


async def check_orchestrator_health(endpoint: str) -> bool:
    """Check if an orchestrator endpoint is reachable"""
    if not endpoint:
        return False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{endpoint}/health")
            return response.status_code == 200
    except:
        return False


@router.get("/agents/categorized")
async def get_categorized_agents(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get agents categorized into orchestrators, agents, and infrastructure"""
    all_entities = await embodiment_registry.list_agents()
    
    # Define infrastructure service IDs
    infrastructure_ids = [
        "neurosync-s1",
        "autogen-multi-agent",
        "scb-gateway",
        "rtmp-streamer",
    ]
    
    orchestrators = []
    agents = []
    infrastructure = []
    
    for entity in all_entities:
        entity_id = entity.get("agent_id", "")
        entity_type = entity.get("metadata", {}).get("type", "")
        
        # Categorize based on ID and type
        if entity_id in infrastructure_ids or entity_type in ["streaming_server", "message_broker", "avatar_controller", "cognitive_engine"]:
            infrastructure.append(entity)
        elif "orchestrator" in entity_id.lower() or entity_type == "orchestrator" or entity_id.startswith("orch:"):
            # Check if orchestrator is active
            entity["is_active"] = await check_orchestrator_health(entity.get("endpoint", ""))
            orchestrators.append(entity)
        else:
            # This is an actual agent (character)
            agents.append(entity)
    
    # Get active character from NeuroSync
    active_agent_id = None
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:5001/character/current")
            if response.status_code == 200:
                data = response.json()
                active_agent_id = data.get("current_character", {}).get("id")
    except:
        pass
    
    # Mark active agent
    for agent in agents:
        agent["is_active"] = (agent.get("agent_id") == active_agent_id)
    
    return {
        "orchestrators": {
            "total": len(orchestrators),
            "active": sum(1 for o in orchestrators if o.get("is_active", False)),
            "list": orchestrators
        },
        "agents": {
            "total": len(agents),
            "active": active_agent_id,
            "list": agents
        },
        "infrastructure": {
            "total": len(infrastructure),
            "list": infrastructure
        }
    }


class CommandRequest(BaseModel):
    action: str = Field(..., description="speak|gesture|move|emotion|tool")
    payload: Dict[str, Any] = {}
    priority: int = 5
    timeout_ms: int = 5000
    correlation_id: Optional[str] = None


@router.post("/agents/{agent_id}/commands")
async def send_command(agent_id: str, req: CommandRequest, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    cmd = EmbodimentCommand(
        agent_id=agent_id,
        action=req.action,
        payload=req.payload,
        priority=req.priority,
        timeout_ms=req.timeout_ms,
        correlation_id=req.correlation_id or "",
    )
    cid = await command_bus.enqueue(cmd)
    return {"queued": True, "correlation_id": cid}


class AutonomyRequest(BaseModel):
    enabled: bool
    policy: Dict[str, Any] = {}


@router.post("/agents/{agent_id}/autonomy")
async def configure_autonomy(agent_id: str, req: AutonomyRequest, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if req.enabled:
        await autonomy_controller.start(agent_id, req.policy)
    else:
        await autonomy_controller.stop(agent_id)
    return {"success": True, "enabled": req.enabled}


@router.post("/orchestrators/register")
async def register_orchestrator(orchestrator_id: str, endpoint: str, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    # Store orchestrator as a special agent-type record for now
    await embodiment_registry.register(
        EmbodiedAgent(
            agent_id=f"orch:{orchestrator_id}",
            name=f"orchestrator-{orchestrator_id}",
            endpoint=endpoint,
            capabilities=["orchestrator"],
            orchestrator_id=orchestrator_id,
            status="online",
            metadata={"kind": "orchestrator"},
            last_heartbeat=datetime.utcnow().isoformat(),
        )
    )
    return {"success": True, "orchestrator_id": orchestrator_id}



