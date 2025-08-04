"""Team management routes for agent coordination"""
import json
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..dependencies import get_current_user, get_redis
from ..core.orchestration.orchestrator import orchestrator, Event

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])

class CreateTeamRequest(BaseModel):
    name: str
    description: str = ""
    agent_ids: List[str]

class TeamResponse(BaseModel):
    id: str
    name: str
    description: str
    agent_ids: List[str]
    created_at: str
    owner: str

class TeamTaskRequest(BaseModel):
    objective: str  # What the team should accomplish
    context: Optional[dict] = {}  # Additional context
    task_type: Optional[str] = "consensus"  # consensus, parallel, sequential

@router.get("", response_model=List[TeamResponse])
async def list_teams(
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """List all teams for the current user"""
    teams = []
    
    keys = await redis.keys("team:*")
    for key in keys:
        data = await redis.get(key)
        if data:
            team = json.loads(data)
            if team.get("owner") == user:
                teams.append(TeamResponse(**team))
    
    return teams

@router.post("", response_model=TeamResponse)
async def create_team(
    request: CreateTeamRequest,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Create a new agent team"""
    team_id = str(uuid.uuid4())
    
    # Verify all agents exist and belong to user
    for agent_id in request.agent_ids:
        agent_data = await redis.get(f"agent:{agent_id}")
        if not agent_data:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        agent = json.loads(agent_data)
        if agent.get("owner") != user:
            raise HTTPException(status_code=403, detail=f"Access denied to agent {agent_id}")
    
    team = {
        "id": team_id,
        "name": request.name,
        "description": request.description,
        "agent_ids": request.agent_ids,
        "created_at": datetime.utcnow().isoformat(),
        "owner": user
    }
    
    # Save team
    await redis.set(f"team:{team_id}", json.dumps(team))
    
    return TeamResponse(**team)

@router.post("/{team_id}/coordinate")
async def coordinate_team(
    team_id: str,
    request: TeamTaskRequest,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Coordinate a task among team members"""
    # Get team
    team_data = await redis.get(f"team:{team_id}")
    if not team_data:
        raise HTTPException(status_code=404, detail="Team not found")
    
    team = json.loads(team_data)
    if team.get("owner") != user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Publish coordination event
    await orchestrator.publish_event(Event(
        "team.coordinate",
        f"user:{user}",
        {
            "team_id": team_id,
            "objective": request.objective,
            "context": request.context,
            "type": request.task_type,
            "agent_ids": team.get("agent_ids", [])
        }
    ))
    
    return {"message": f"Coordination task submitted to team {team_id}"}

@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Get team details"""
    team_data = await redis.get(f"team:{team_id}")
    if not team_data:
        raise HTTPException(status_code=404, detail="Team not found")
    
    team = json.loads(team_data)
    if team.get("owner") != user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return TeamResponse(**team)

@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Delete a team"""
    team_data = await redis.get(f"team:{team_id}")
    if not team_data:
        raise HTTPException(status_code=404, detail="Team not found")
    
    team = json.loads(team_data)
    if team.get("owner") != user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await redis.delete(f"team:{team_id}")
    
    return {"message": "Team deleted"}