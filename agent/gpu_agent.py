"""
GPU-Accelerated Agent Base Class

This module provides a base class for agents that leverage GPU acceleration
for compute-intensive tasks like neural network inference, matrix operations,
and parallel data processing.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import numpy as np

try:
    import torch
    import torch.nn as nn
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    torch = None
    nn = None
    CUDA_AVAILABLE = False

import redis.asyncio as redis
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPUAgent(ABC):
    """Base class for GPU-accelerated agents"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.device = None
        self.device_id = None
        self.redis_client = None
        self.running = False
        self.models: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize the GPU agent"""
        # Connect to Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = await redis.from_url(redis_url)
        
        # Wait for GPU allocation
        await self._wait_for_gpu_allocation()
        
        # Initialize GPU
        if CUDA_AVAILABLE and self.device_id is not None:
            self.device = torch.device(f"cuda:{self.device_id}")
            torch.cuda.set_device(self.device)
            logger.info(f"GPU Agent {self.agent_id} initialized on GPU {self.device_id}")
        else:
            self.device = torch.device("cpu")
            logger.warning(f"GPU Agent {self.agent_id} running on CPU")
            
        # Load models
        await self.load_models()
        
        # Register agent
        await self._register_agent()
        
    async def _wait_for_gpu_allocation(self):
        """Wait for GPU allocation from orchestrator"""
        logger.info(f"Waiting for GPU allocation for agent {self.agent_id}")
        
        # Subscribe to config channel
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"agent:{self.agent_id}:config")
        
        timeout = 30  # 30 second timeout
        start_time = asyncio.get_event_loop().time()
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                config = json.loads(message["data"])
                if "gpu_device" in config:
                    self.device_id = config["gpu_device"]
                    logger.info(f"Allocated GPU {self.device_id} to agent {self.agent_id}")
                    break
                    
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning("GPU allocation timeout, running on CPU")
                break
                
        await pubsub.unsubscribe()
        
    async def _register_agent(self):
        """Register agent with orchestrator"""
        agent_data = {
            "id": self.agent_id,
            "type": self.agent_type,
            "status": "running",
            "gpu_enabled": True,
            "device_id": self.device_id,
            "capabilities": self.get_capabilities(),
            "started_at": datetime.utcnow().isoformat()
        }
        
        await self.redis_client.set(
            f"agent:{self.agent_id}",
            json.dumps(agent_data)
        )
        
        # Publish started event
        event = {
            "type": "gpu.agent.started",
            "source": self.agent_id,
            "data": {
                "agent_id": self.agent_id,
                "memory_required": self.get_memory_requirement()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis_client.lpush("events:global", json.dumps(event))
        
    @abstractmethod
    async def load_models(self):
        """Load any required models - to be implemented by subclasses"""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        pass
        
    @abstractmethod
    def get_memory_requirement(self) -> int:
        """Return GPU memory requirement in bytes"""
        pass
        
    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task - to be implemented by subclasses"""
        pass
        
    async def run(self):
        """Main agent loop"""
        await self.initialize()
        self.running = True
        
        # Subscribe to task channel
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"agent:{self.agent_id}:tasks")
        
        logger.info(f"GPU Agent {self.agent_id} listening for tasks")
        
        try:
            async for message in pubsub.listen():
                if not self.running:
                    break
                    
                if message["type"] == "message":
                    try:
                        task = json.loads(message["data"])
                        logger.info(f"Processing task: {task.get('id')}")
                        
                        # Update task status
                        task["status"] = "processing"
                        await self.redis_client.set(
                            f"task:{task['id']}",
                            json.dumps(task)
                        )
                        
                        # Process on GPU
                        result = await self.process_task(task)
                        
                        # Update task with result
                        task["status"] = "completed"
                        task["result"] = result
                        task["completed_at"] = datetime.utcnow().isoformat()
                        
                        await self.redis_client.set(
                            f"task:{task['id']}",
                            json.dumps(task)
                        )
                        
                        # Publish completion event
                        event = {
                            "type": "task.completed",
                            "source": self.agent_id,
                            "data": {
                                "task_id": task["id"],
                                "result": result
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await self.redis_client.lpush("events:global", json.dumps(event))
                        
                        logger.info(f"Task {task['id']} completed")
                        
                    except Exception as e:
                        logger.error(f"Error processing task: {e}")
                        if "task" in locals() and "id" in task:
                            task["status"] = "failed"
                            task["error"] = str(e)
                            await self.redis_client.set(
                                f"task:{task['id']}",
                                json.dumps(task)
                            )
                            
        except Exception as e:
            logger.error(f"Agent error: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources"""
        self.running = False
        
        # Clear GPU memory
        if CUDA_AVAILABLE and self.device_id is not None:
            torch.cuda.empty_cache()
            
        # Notify orchestrator
        event = {
            "type": "gpu.agent.stopped",
            "source": self.agent_id,
            "data": {"agent_id": self.agent_id},
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis_client.lpush("events:global", json.dumps(event))
        
        # Update agent status
        await self.redis_client.set(
            f"agent:{self.agent_id}",
            json.dumps({"id": self.agent_id, "status": "stopped"})
        )
        
        await self.redis_client.close()
        logger.info(f"GPU Agent {self.agent_id} stopped")
        
    def to_gpu(self, data):
        """Move data to GPU if available"""
        if CUDA_AVAILABLE and self.device_id is not None:
            if isinstance(data, np.ndarray):
                return torch.from_numpy(data).to(self.device)
            elif torch is not None and isinstance(data, torch.Tensor):
                return data.to(self.device)
        return data
        
    def to_cpu(self, data):
        """Move data back to CPU"""
        if torch is not None and isinstance(data, torch.Tensor):
            return data.cpu().numpy()
        return data