"""Task management routes"""
import json
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..dependencies import get_current_user, get_redis
from ..core.orchestration.orchestrator import orchestrator, Event

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

class CreateTaskRequest(BaseModel):
    type: str  # analyze_market, execute_trade, assess_risk, etc.
    data: dict
    agent_id: Optional[str] = None  # Specific agent or let orchestrator decide

class TaskResponse(BaseModel):
    id: str
    type: str
    status: str
    data: dict
    created_at: str
    assigned_to: Optional[str] = None
    result: Optional[dict] = None

@router.post("", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Create a new task"""
    task_id = str(uuid.uuid4())
    
    task = {
        "id": task_id,
        "type": request.type,
        "status": "pending",
        "data": request.data,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": user,
        "assigned_to": request.agent_id
    }
    
    # Save task
    await redis.set(f"task:{task_id}", json.dumps(task))
    
    # Publish to orchestrator
    await orchestrator.publish_event(Event(
        "task.created",
        f"user:{user}",
        task
    ))
    
    return TaskResponse(**task)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Get task details"""
    task_data = await redis.get(f"task:{task_id}")
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = json.loads(task_data)
    
    # Check if user has access
    if task.get("created_by") != user:
        # Check if user owns the assigned agent
        if task.get("assigned_to"):
            agent_data = await redis.get(f"agent:{task['assigned_to']}")
            if agent_data:
                agent = json.loads(agent_data)
                if agent.get("owner") != user:
                    raise HTTPException(status_code=403, detail="Access denied")
            else:
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get result if completed
    if task["status"] == "completed":
        result_data = await redis.hgetall(f"task:{task_id}:result")
        if result_data:
            task["result"] = {
                k.decode(): v.decode() for k, v in result_data.items()
            }
    
    return TaskResponse(**task)

@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """List tasks for the current user"""
    tasks = []
    
    # Get all task keys
    keys = await redis.keys("task:*")
    for key in keys:
        if b":result" in key:
            continue
            
        data = await redis.get(key)
        if data:
            task = json.loads(data)
            
            # Filter by user's tasks or assigned to user's agents
            if task.get("created_by") == user:
                if status is None or task["status"] == status:
                    tasks.append(TaskResponse(**task))
            else:
                # Check if assigned to user's agent
                agent_id = task.get("assigned_to")
                if agent_id:
                    agent_data = await redis.get(f"agent:{agent_id}")
                    if agent_data:
                        agent = json.loads(agent_data)
                        if agent.get("owner") == user:
                            if status is None or task["status"] == status:
                                tasks.append(TaskResponse(**task))
    
    # Sort by creation time
    tasks.sort(key=lambda x: x.created_at, reverse=True)
    
    return tasks

@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    user: str = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Cancel a pending task"""
    task_data = await redis.get(f"task:{task_id}")
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = json.loads(task_data)
    
    # Check ownership
    if task.get("created_by") != user:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if task["status"] != "pending":
        raise HTTPException(status_code=400, detail="Can only cancel pending tasks")
    
    # Update status
    task["status"] = "cancelled"
    await redis.set(f"task:{task_id}", json.dumps(task))
    
    # Remove from agent queue if assigned
    if task.get("assigned_to"):
        # This is simplified - in production, need proper queue management
        pass
    
    return {"message": "Task cancelled"}