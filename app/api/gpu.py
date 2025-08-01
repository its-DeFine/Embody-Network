"""
GPU Management API endpoints
"""
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from .auth import get_current_user
from ..gpu_orchestrator import gpu_orchestrator
from ..orchestrator import Event, orchestrator
from ..dependencies import get_redis

router = APIRouter(
    prefix="/api/v1/gpu",
    tags=["gpu"],
    dependencies=[Depends(get_current_user)]
)


class GPUTaskRequest(BaseModel):
    """Request to create a GPU-accelerated task"""
    task_type: str  # Type of GPU task (training, inference, analysis)
    gpu_type: str = "compute"  # compute, ml, rendering
    data: Dict[str, Any]  # Task-specific data
    memory_required: int = 1_000_000_000  # Memory required in bytes (default 1GB)
    priority: str = "normal"  # low, normal, high


class GPUAllocationRequest(BaseModel):
    """Request to allocate GPU to an agent"""
    agent_id: str
    memory_required: int = 2_000_000_000  # 2GB default


@router.get("/stats")
async def get_gpu_stats():
    """Get current GPU statistics and availability"""
    stats = await gpu_orchestrator.get_gpu_stats()
    return stats


@router.get("/resources")
async def get_gpu_resources():
    """Get detailed information about available GPU resources"""
    redis = await get_redis()
    resources = []
    
    # Get all GPU resources from Redis
    gpu_keys = await redis.keys("gpu:resource:*")
    for key in gpu_keys:
        resource_data = await redis.get(key)
        if resource_data:
            import json
            resources.append(json.loads(resource_data))
            
    return {"resources": resources}


@router.get("/allocations")
async def get_gpu_allocations():
    """Get current GPU allocations"""
    redis = await get_redis()
    allocations = []
    
    # Get all GPU allocations from Redis
    allocation_keys = await redis.keys("gpu:allocation:*")
    for key in allocation_keys:
        allocation_data = await redis.get(key)
        if allocation_data:
            import json
            agent_id = key.decode().split(":")[-1]
            allocation = json.loads(allocation_data)
            allocation["agent_id"] = agent_id
            allocations.append(allocation)
            
    return {"allocations": allocations}


@router.post("/tasks")
async def create_gpu_task(request: GPUTaskRequest):
    """Create a new GPU-accelerated task"""
    import uuid
    
    task = {
        "id": str(uuid.uuid4()),
        "type": request.task_type,
        "gpu_type": request.gpu_type,
        "data": request.data,
        "memory_required": request.memory_required,
        "priority": request.priority,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Publish GPU task event
    await orchestrator.publish_event(Event(
        "gpu.task.created",
        "api",
        task
    ))
    
    # Store task
    redis = await get_redis()
    await redis.set(f"task:{task['id']}", json.dumps(task))
    
    return task


@router.post("/allocate")
async def allocate_gpu(request: GPUAllocationRequest):
    """Manually allocate GPU to an agent"""
    device_id = await gpu_orchestrator.allocate_gpu(
        request.agent_id,
        request.memory_required
    )
    
    if device_id is None:
        raise HTTPException(
            status_code=503,
            detail="No GPU available with sufficient memory"
        )
        
    return {
        "agent_id": request.agent_id,
        "device_id": device_id,
        "allocated": True
    }


@router.post("/release/{agent_id}")
async def release_gpu(agent_id: str):
    """Release GPU allocation for an agent"""
    await gpu_orchestrator.release_gpu(agent_id)
    return {"agent_id": agent_id, "released": True}


@router.get("/pending-tasks")
async def get_pending_gpu_tasks():
    """Get pending GPU tasks waiting for allocation"""
    redis = await get_redis()
    pending_tasks = []
    
    # Get all pending GPU tasks
    while True:
        task_data = await redis.rpop("tasks:gpu:pending")
        if not task_data:
            break
        pending_tasks.append(json.loads(task_data))
        
    # Put them back in the queue
    for task in pending_tasks:
        await redis.lpush("tasks:gpu:pending", json.dumps(task))
        
    return {"pending_tasks": pending_tasks, "count": len(pending_tasks)}