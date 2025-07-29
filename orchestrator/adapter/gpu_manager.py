"""
GPU Manager - Handles GPU resource allocation and agent distribution
Integrates with agent-net's GPU monitoring and Ollama model management
"""

import os
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import aiohttp
import redis.asyncio as redis
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class GPUNode:
    """Represents a GPU-enabled orchestrator node"""
    orchestrator_id: str
    hostname: str
    gpu_available: bool
    vram_total_mb: int
    vram_used_mb: int
    vram_free_mb: int
    temperature: float
    power_draw: float
    models: List[str]
    status: str
    last_update: datetime
    
    @property
    def utilization(self) -> float:
        """Calculate GPU utilization percentage"""
        if self.vram_total_mb > 0:
            return (self.vram_used_mb / self.vram_total_mb) * 100
        return 0.0
        
    def can_run_model(self, model_name: str, required_vram_mb: int) -> bool:
        """Check if node can run a specific model"""
        return (model_name in self.models and 
                self.vram_free_mb >= required_vram_mb and
                self.gpu_available and
                self.status == 'active')


class GPUManager:
    """Manages GPU orchestrators and distributes agents across them"""
    
    # Model VRAM requirements (approximate)
    MODEL_VRAM_REQUIREMENTS = {
        'codellama:34b-instruct-q4_k_m': 20000,  # ~20GB
        'codellama:13b': 8000,                   # ~8GB
        'codellama:7b': 4000,                    # ~4GB
        'llama2:70b': 40000,                     # ~40GB
        'llama2:13b': 8000,                      # ~8GB
        'llama2:7b': 4000,                       # ~4GB
        'mistral:7b': 4000,                      # ~4GB
        'mixtral:8x7b': 25000,                   # ~25GB
    }
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
        self.orchestrators: Dict[str, GPUNode] = {}
        self.allocation_strategy = os.getenv('GPU_ALLOCATION_STRATEGY', 'least_loaded')
        
    async def initialize(self):
        """Initialize GPU manager"""
        self.redis = await redis.from_url(self.redis_url)
        
        # Load existing orchestrators
        await self._load_orchestrators()
        
        # Start monitoring loop
        asyncio.create_task(self._monitor_orchestrators())
        
        logger.info("GPU Manager initialized")
        
    async def _load_orchestrators(self):
        """Load orchestrator information from Redis"""
        try:
            orchestrators_data = await self.redis.hgetall('orchestrators')
            
            for orch_id, data in orchestrators_data.items():
                orch_info = json.loads(data)
                
                # Get latest metrics
                metrics_data = await self.redis.hget(f'orchestrator:{orch_id}:metrics', 'gpu')
                gpu_metrics = json.loads(metrics_data) if metrics_data else {}
                
                node = GPUNode(
                    orchestrator_id=orch_id,
                    hostname=orch_info.get('node_hostname', 'unknown'),
                    gpu_available=gpu_metrics.get('available', False),
                    vram_total_mb=gpu_metrics.get('vram_total_mb', 0),
                    vram_used_mb=gpu_metrics.get('vram_used_mb', 0),
                    vram_free_mb=gpu_metrics.get('vram_total_mb', 0) - gpu_metrics.get('vram_used_mb', 0),
                    temperature=gpu_metrics.get('temperature', 0),
                    power_draw=gpu_metrics.get('power_draw', 0),
                    models=orch_info.get('capabilities', {}).get('models', []),
                    status=orch_info.get('status', 'unknown'),
                    last_update=datetime.fromisoformat(orch_info.get('registered_at', datetime.utcnow().isoformat()))
                )
                
                self.orchestrators[orch_id] = node
                
        except Exception as e:
            logger.error(f"Error loading orchestrators: {e}")
            
    async def register_orchestrator(self, orchestrator_data: Dict[str, Any]):
        """Register a new GPU orchestrator"""
        orch_id = orchestrator_data['orchestrator_id']
        gpu_info = orchestrator_data['capabilities']['gpu']
        
        node = GPUNode(
            orchestrator_id=orch_id,
            hostname=orchestrator_data['node_hostname'],
            gpu_available=gpu_info.get('available', False),
            vram_total_mb=gpu_info.get('vram_total_mb', 0),
            vram_used_mb=gpu_info.get('vram_used_mb', 0),
            vram_free_mb=gpu_info.get('vram_total_mb', 0) - gpu_info.get('vram_used_mb', 0),
            temperature=gpu_info.get('temperature', 0),
            power_draw=gpu_info.get('power_draw', 0),
            models=orchestrator_data['capabilities'].get('models', []),
            status='active',
            last_update=datetime.utcnow()
        )
        
        self.orchestrators[orch_id] = node
        logger.info(f"Registered GPU orchestrator: {orch_id} with {node.vram_total_mb}MB VRAM")
        
    async def find_best_orchestrator(self, 
                                   model: str, 
                                   min_vram_mb: Optional[int] = None) -> Optional[GPUNode]:
        """Find the best orchestrator for running a specific model"""
        # Get required VRAM
        required_vram = min_vram_mb or self.MODEL_VRAM_REQUIREMENTS.get(model, 8000)
        
        # Filter eligible orchestrators
        eligible = [
            node for node in self.orchestrators.values()
            if node.can_run_model(model, required_vram)
        ]
        
        if not eligible:
            logger.warning(f"No orchestrator available for model {model} requiring {required_vram}MB VRAM")
            return None
            
        # Select based on strategy
        if self.allocation_strategy == 'least_loaded':
            # Sort by utilization (ascending)
            eligible.sort(key=lambda n: n.utilization)
            return eligible[0]
            
        elif self.allocation_strategy == 'round_robin':
            # Simple round-robin (would need state tracking)
            return eligible[0]
            
        elif self.allocation_strategy == 'temperature':
            # Sort by temperature (ascending) - cooler GPUs first
            eligible.sort(key=lambda n: n.temperature)
            return eligible[0]
            
        else:
            # Default to first available
            return eligible[0]
            
    async def allocate_agent(self, agent_config: Dict[str, Any]) -> Optional[str]:
        """Allocate an agent to a GPU orchestrator"""
        model = agent_config.get('model', 'codellama:7b')
        vram_requirement = agent_config.get('gpu_requirement', {}).get('min_vram_mb')
        
        # Find best orchestrator
        orchestrator = await self.find_best_orchestrator(model, vram_requirement)
        
        if not orchestrator:
            return None
            
        # Update allocation in Redis
        await self.redis.hset(
            f'agent:{agent_config["agent_id"]}:allocation',
            'orchestrator_id',
            orchestrator.orchestrator_id
        )
        
        # Update orchestrator load (approximate)
        estimated_vram = self.MODEL_VRAM_REQUIREMENTS.get(model, 8000)
        orchestrator.vram_used_mb += estimated_vram
        orchestrator.vram_free_mb -= estimated_vram
        
        logger.info(f"Allocated agent {agent_config['agent_id']} to orchestrator {orchestrator.orchestrator_id}")
        
        return orchestrator.orchestrator_id
        
    async def deallocate_agent(self, agent_id: str):
        """Deallocate an agent from its orchestrator"""
        # Get allocation info
        orch_id = await self.redis.hget(f'agent:{agent_id}:allocation', 'orchestrator_id')
        
        if orch_id and orch_id in self.orchestrators:
            # Update orchestrator load (would need actual usage tracking)
            orchestrator = self.orchestrators[orch_id]
            
            # Remove allocation
            await self.redis.delete(f'agent:{agent_id}:allocation')
            
            logger.info(f"Deallocated agent {agent_id} from orchestrator {orch_id}")
            
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get overall GPU cluster status"""
        total_nodes = len(self.orchestrators)
        active_nodes = sum(1 for n in self.orchestrators.values() if n.status == 'active')
        
        total_vram = sum(n.vram_total_mb for n in self.orchestrators.values())
        used_vram = sum(n.vram_used_mb for n in self.orchestrators.values())
        
        # Get unique models across cluster
        all_models = set()
        for node in self.orchestrators.values():
            all_models.update(node.models)
            
        return {
            'total_nodes': total_nodes,
            'active_nodes': active_nodes,
            'total_vram_mb': total_vram,
            'used_vram_mb': used_vram,
            'free_vram_mb': total_vram - used_vram,
            'utilization_percent': (used_vram / total_vram * 100) if total_vram > 0 else 0,
            'available_models': list(all_models),
            'nodes': [asdict(node) for node in self.orchestrators.values()]
        }
        
    async def _monitor_orchestrators(self):
        """Monitor orchestrator health and update status"""
        while True:
            try:
                # Check each orchestrator
                for orch_id, node in self.orchestrators.items():
                    # Get latest metrics from Redis
                    metrics_data = await self.redis.hget(f'orchestrator:{orch_id}:metrics', 'gpu')
                    
                    if metrics_data:
                        gpu_metrics = json.loads(metrics_data)
                        
                        # Update node info
                        node.gpu_available = gpu_metrics.get('available', False)
                        node.vram_used_mb = gpu_metrics.get('vram_used_mb', 0)
                        node.vram_free_mb = node.vram_total_mb - node.vram_used_mb
                        node.temperature = gpu_metrics.get('temperature', 0)
                        node.power_draw = gpu_metrics.get('power_draw', 0)
                        node.last_update = datetime.utcnow()
                        
                        # Check if node is stale (no update in 5 minutes)
                        if (datetime.utcnow() - node.last_update).seconds > 300:
                            node.status = 'stale'
                            logger.warning(f"Orchestrator {orch_id} marked as stale")
                            
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in orchestrator monitoring: {e}")
                await asyncio.sleep(60)
                
    async def get_payment_stats(self) -> Dict[str, Any]:
        """Get payment statistics for all orchestrators"""
        stats = {}
        
        for orch_id in self.orchestrators:
            payment_data = await self.redis.hgetall(f'orchestrator:{orch_id}:payments')
            
            if payment_data:
                stats[orch_id] = {
                    'total_tickets': int(payment_data.get(b'total_tickets', 0)),
                    'total_face_value': float(payment_data.get(b'total_face_value', 0)),
                    'average_ticket_value': float(payment_data.get(b'total_face_value', 0)) / 
                                          max(1, int(payment_data.get(b'total_tickets', 1)))
                }
                
        return stats