"""
GPU Deployment module for agent-manager
Handles deployment of agents to GPU orchestrators
"""

import os
import logging
import json
from typing import Dict, Optional, Any
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class GPUDeploymentHandler:
    """Handles deployment of agents to GPU orchestrators"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.adapter_url = os.getenv('GPU_ADAPTER_URL', 'http://orchestrator-adapter:8002')
        
    async def is_gpu_required(self, agent_config: Dict[str, Any]) -> bool:
        """Check if agent requires GPU resources"""
        # Check for explicit GPU requirement
        if agent_config.get('requires_gpu', False):
            return True
            
        # Check if using large models that need GPU
        model = agent_config.get('model', '')
        gpu_models = [
            'codellama:34b', 'codellama:13b',
            'llama2:70b', 'llama2:13b',
            'mixtral:8x7b', 'mistral:7b-instruct'
        ]
        
        return any(gpu_model in model for gpu_model in gpu_models)
        
    async def deploy_to_gpu(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy agent to GPU orchestrator"""
        agent_id = agent_config['agent_id']
        
        try:
            # Request allocation from GPU adapter
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.adapter_url}/agents/allocate",
                    json=agent_config
                ) as resp:
                    if resp.status == 200:
                        allocation = await resp.json()
                        orchestrator_id = allocation['orchestrator_id']
                        
                        logger.info(f"Agent {agent_id} allocated to GPU orchestrator {orchestrator_id}")
                        
                        # Store allocation info
                        await self.redis.hset(
                            f'agent:{agent_id}:deployment',
                            mapping={
                                'type': 'gpu',
                                'orchestrator_id': orchestrator_id,
                                'deployed_at': datetime.utcnow().isoformat()
                            }
                        )
                        
                        # Create deployment result
                        return {
                            'success': True,
                            'deployment_type': 'gpu',
                            'orchestrator_id': orchestrator_id,
                            'container_id': f'gpu-agent-{agent_id}',
                            'gpu_enabled': True,
                            'model': agent_config.get('model'),
                            'message': f'Agent deployed to GPU orchestrator {orchestrator_id}'
                        }
                        
                    else:
                        error_msg = await resp.text()
                        logger.error(f"GPU allocation failed: {error_msg}")
                        return {
                            'success': False,
                            'error': f'GPU allocation failed: {error_msg}'
                        }
                        
        except Exception as e:
            logger.error(f"Error deploying to GPU: {e}")
            return {
                'success': False,
                'error': f'GPU deployment error: {str(e)}'
            }
            
    async def check_gpu_availability(self) -> Dict[str, Any]:
        """Check GPU cluster availability"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.adapter_url}/status") as resp:
                    if resp.status == 200:
                        status = await resp.json()
                        cluster = status.get('cluster', {})
                        
                        return {
                            'available': cluster.get('active_nodes', 0) > 0,
                            'active_nodes': cluster.get('active_nodes', 0),
                            'total_vram_mb': cluster.get('total_vram_mb', 0),
                            'free_vram_mb': cluster.get('free_vram_mb', 0),
                            'models': cluster.get('available_models', [])
                        }
                        
        except Exception as e:
            logger.error(f"Error checking GPU availability: {e}")
            
        return {'available': False, 'error': str(e)}
        
    async def deallocate_gpu_agent(self, agent_id: str):
        """Deallocate agent from GPU orchestrator"""
        try:
            # Get deployment info
            deployment_data = await self.redis.hgetall(f'agent:{agent_id}:deployment')
            
            if deployment_data and deployment_data.get(b'type') == b'gpu':
                # Request deallocation
                async with aiohttp.ClientSession() as session:
                    async with session.delete(
                        f"{self.adapter_url}/agents/{agent_id}"
                    ) as resp:
                        if resp.status == 200:
                            logger.info(f"Agent {agent_id} deallocated from GPU")
                            
                            # Clean up deployment info
                            await self.redis.delete(f'agent:{agent_id}:deployment')
                            
                            return True
                            
        except Exception as e:
            logger.error(f"Error deallocating GPU agent: {e}")
            
        return False