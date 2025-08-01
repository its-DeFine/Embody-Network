"""
GPU Orchestrator Integration Module

This module extends the core orchestrator to support GPU-accelerated agents,
enabling high-performance computing for trading analysis, risk calculations,
and machine learning models.

Features:
- GPU resource discovery and allocation
- CUDA-aware task scheduling
- GPU memory management
- Multi-GPU coordination
- Performance monitoring
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import uuid

try:
    import torch
    import numpy as np
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    CUDA_AVAILABLE = False
    torch = None
    np = None

from .orchestrator import Event, orchestrator
from .dependencies import get_redis

logger = logging.getLogger(__name__)


class GPUResource:
    """Represents a GPU resource with its capabilities"""
    
    def __init__(self, device_id: int, name: str, memory_total: int, memory_free: int):
        self.device_id = device_id
        self.name = name
        self.memory_total = memory_total
        self.memory_free = memory_free
        self.allocated_agents: List[str] = []
        self.utilization = 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "memory_total": self.memory_total,
            "memory_free": self.memory_free,
            "allocated_agents": self.allocated_agents,
            "utilization": self.utilization,
            "memory_used_percent": (1 - self.memory_free / self.memory_total) * 100
        }


class GPUOrchestrator:
    """Extended orchestrator with GPU support"""
    
    def __init__(self):
        self.gpu_resources: Dict[int, GPUResource] = {}
        self.gpu_agents: Dict[str, Dict[str, Any]] = {}  # agent_id -> gpu_info
        self.redis = None
        self.monitoring_task = None
        
    async def initialize(self):
        """Initialize GPU orchestrator"""
        self.redis = await get_redis()
        
        # Discover GPU resources
        await self._discover_gpus()
        
        # Register GPU-specific event handlers
        orchestrator.event_handlers.update({
            "gpu.task.created": self._handle_gpu_task,
            "gpu.agent.started": self._handle_gpu_agent_started,
            "gpu.agent.stopped": self._handle_gpu_agent_stopped,
            "gpu.memory.low": self._handle_memory_warning
        })
        
        logger.info(f"GPU Orchestrator initialized with {len(self.gpu_resources)} GPUs")
        
    async def start_monitoring(self):
        """Start GPU monitoring"""
        self.monitoring_task = asyncio.create_task(self._monitor_gpus())
        
    async def stop_monitoring(self):
        """Stop GPU monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            
    async def _discover_gpus(self):
        """Discover available GPU resources"""
        if not CUDA_AVAILABLE:
            logger.warning("CUDA not available, running in CPU-only mode")
            return
            
        try:
            gpu_count = torch.cuda.device_count()
            
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                memory_total = props.total_memory
                memory_free = memory_total - torch.cuda.memory_allocated(i)
                
                gpu = GPUResource(
                    device_id=i,
                    name=props.name,
                    memory_total=memory_total,
                    memory_free=memory_free
                )
                
                self.gpu_resources[i] = gpu
                
                # Store in Redis for visibility
                await self.redis.set(
                    f"gpu:resource:{i}",
                    json.dumps(gpu.to_dict())
                )
                
                logger.info(f"Discovered GPU {i}: {props.name} ({memory_total / 1e9:.1f}GB)")
                
        except Exception as e:
            logger.error(f"Error discovering GPUs: {e}")
            
    async def allocate_gpu(self, agent_id: str, memory_required: int = 0) -> Optional[int]:
        """Allocate a GPU to an agent"""
        best_gpu = None
        max_free_memory = 0
        
        for gpu_id, gpu in self.gpu_resources.items():
            if gpu.memory_free >= memory_required and gpu.memory_free > max_free_memory:
                if len(gpu.allocated_agents) < 4:  # Max 4 agents per GPU
                    best_gpu = gpu_id
                    max_free_memory = gpu.memory_free
                    
        if best_gpu is not None:
            self.gpu_resources[best_gpu].allocated_agents.append(agent_id)
            self.gpu_agents[agent_id] = {
                "device_id": best_gpu,
                "allocated_at": datetime.utcnow().isoformat(),
                "memory_allocated": memory_required
            }
            
            # Update Redis
            await self.redis.set(
                f"gpu:allocation:{agent_id}",
                json.dumps(self.gpu_agents[agent_id])
            )
            
            logger.info(f"Allocated GPU {best_gpu} to agent {agent_id}")
            return best_gpu
            
        logger.warning(f"No GPU available for agent {agent_id} (required: {memory_required})")
        return None
        
    async def release_gpu(self, agent_id: str):
        """Release GPU allocation for an agent"""
        if agent_id in self.gpu_agents:
            gpu_info = self.gpu_agents[agent_id]
            device_id = gpu_info["device_id"]
            
            if device_id in self.gpu_resources:
                self.gpu_resources[device_id].allocated_agents.remove(agent_id)
                
            del self.gpu_agents[agent_id]
            await self.redis.delete(f"gpu:allocation:{agent_id}")
            
            logger.info(f"Released GPU {device_id} from agent {agent_id}")
            
    async def _monitor_gpus(self):
        """Monitor GPU health and utilization"""
        while True:
            try:
                if CUDA_AVAILABLE:
                    for gpu_id, gpu in self.gpu_resources.items():
                        # Update memory stats
                        memory_free = torch.cuda.get_device_properties(gpu_id).total_memory
                        memory_free -= torch.cuda.memory_allocated(gpu_id)
                        gpu.memory_free = memory_free
                        
                        # Get utilization via nvidia-smi
                        try:
                            result = subprocess.run(
                                ["nvidia-smi", "--query-gpu=utilization.gpu", 
                                 "--format=csv,noheader,nounits", f"-i={gpu_id}"],
                                capture_output=True, text=True
                            )
                            if result.returncode == 0:
                                gpu.utilization = float(result.stdout.strip())
                        except:
                            pass
                            
                        # Check for low memory
                        if gpu.memory_free < gpu.memory_total * 0.1:  # Less than 10% free
                            await orchestrator.publish_event(Event(
                                "gpu.memory.low",
                                "gpu_orchestrator",
                                {
                                    "device_id": gpu_id,
                                    "memory_free": gpu.memory_free,
                                    "allocated_agents": gpu.allocated_agents
                                }
                            ))
                            
                        # Update Redis
                        await self.redis.set(
                            f"gpu:resource:{gpu_id}",
                            json.dumps(gpu.to_dict())
                        )
                        
                await asyncio.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring GPUs: {e}")
                await asyncio.sleep(30)
                
    async def _handle_gpu_task(self, event: Dict):
        """Handle GPU-accelerated task"""
        task = event["data"]
        task_type = task.get("gpu_type", "compute")
        memory_required = task.get("memory_required", 1e9)  # Default 1GB
        
        # Find best GPU agent
        agent_id = await self._find_best_gpu_agent(task_type, memory_required)
        
        if agent_id:
            task["assigned_to"] = agent_id
            task["gpu_device"] = self.gpu_agents[agent_id]["device_id"]
            
            # Send to agent
            await self.redis.publish(f"agent:{agent_id}:tasks", json.dumps(task))
            logger.info(f"GPU task {task['id']} assigned to agent {agent_id}")
        else:
            # Queue for later
            await self.redis.lpush("tasks:gpu:pending", json.dumps(task))
            logger.warning(f"No GPU agent available for task {task['id']}")
            
    async def _handle_gpu_agent_started(self, event: Dict):
        """Handle GPU agent startup"""
        agent_id = event["data"]["agent_id"]
        memory_required = event["data"].get("memory_required", 2e9)  # Default 2GB
        
        # Allocate GPU
        device_id = await self.allocate_gpu(agent_id, memory_required)
        
        if device_id is not None:
            # Notify agent of GPU allocation
            await self.redis.publish(
                f"agent:{agent_id}:config",
                json.dumps({"gpu_device": device_id})
            )
            
    async def _handle_gpu_agent_stopped(self, event: Dict):
        """Handle GPU agent shutdown"""
        agent_id = event["data"]["agent_id"]
        await self.release_gpu(agent_id)
        
        # Check for pending GPU tasks
        await self._process_pending_gpu_tasks()
        
    async def _handle_memory_warning(self, event: Dict):
        """Handle low GPU memory warning"""
        device_id = event["data"]["device_id"]
        allocated_agents = event["data"]["allocated_agents"]
        
        logger.warning(f"Low memory on GPU {device_id}, attempting to rebalance")
        
        # Could implement memory pressure relief strategies here
        # For now, just log the warning
        
    async def _find_best_gpu_agent(self, task_type: str, memory_required: int) -> Optional[str]:
        """Find the best GPU agent for a task"""
        candidates = []
        
        # Get all GPU agents
        for agent_id, gpu_info in self.gpu_agents.items():
            agent_data = await self.redis.get(f"agent:{agent_id}")
            if agent_data:
                agent = json.loads(agent_data)
                if agent.get("status") == "running" and agent.get("gpu_enabled"):
                    device_id = gpu_info["device_id"]
                    gpu = self.gpu_resources.get(device_id)
                    
                    if gpu and gpu.memory_free >= memory_required:
                        candidates.append({
                            "agent_id": agent_id,
                            "device_id": device_id,
                            "utilization": gpu.utilization,
                            "memory_free": gpu.memory_free
                        })
                        
        # Sort by lowest utilization and most free memory
        candidates.sort(key=lambda x: (x["utilization"], -x["memory_free"]))
        
        if candidates:
            return candidates[0]["agent_id"]
            
        return None
        
    async def _process_pending_gpu_tasks(self):
        """Process any pending GPU tasks"""
        while True:
            task_data = await self.redis.lpop("tasks:gpu:pending")
            if not task_data:
                break
                
            task = json.loads(task_data)
            await orchestrator.publish_event(Event(
                "gpu.task.created",
                "gpu_orchestrator",
                task
            ))
            
    async def get_gpu_stats(self) -> Dict[str, Any]:
        """Get current GPU statistics"""
        stats = {
            "total_gpus": len(self.gpu_resources),
            "cuda_available": CUDA_AVAILABLE,
            "gpus": {},
            "allocated_agents": len(self.gpu_agents),
            "total_memory": 0,
            "total_memory_free": 0,
            "average_utilization": 0
        }
        
        total_util = 0
        for gpu_id, gpu in self.gpu_resources.items():
            stats["gpus"][gpu_id] = gpu.to_dict()
            stats["total_memory"] += gpu.memory_total
            stats["total_memory_free"] += gpu.memory_free
            total_util += gpu.utilization
            
        if len(self.gpu_resources) > 0:
            stats["average_utilization"] = total_util / len(self.gpu_resources)
            
        return stats


# Global GPU orchestrator instance
gpu_orchestrator = GPUOrchestrator()