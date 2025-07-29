"""
Swarm Connector - Bridge between agent-net GPU orchestrators and AutoGen platform
Handles orchestrator registration, agent deployment, and inter-container communication
"""

import os
import asyncio
import logging
import json
from typing import Dict, Optional, Any, List
from datetime import datetime
import aiohttp

# Import our platform components
import sys
sys.path.append('/app')
from shared.utils.message_queue import MessageQueue
from shared.events.event_types import Event, EventType
from shared.models.agent_models import AgentConfig, AgentStatus

logger = logging.getLogger(__name__)


class SwarmConnector:
    """Connects agent-net orchestrators to the AutoGen swarm"""
    
    def __init__(self, orchestrator_id: str, rabbitmq_url: str, redis_url: str):
        self.orchestrator_id = orchestrator_id
        self.node_hostname = os.getenv('NODE_HOSTNAME', 'gpu-node-1')
        self.rabbitmq_url = rabbitmq_url
        self.redis_url = redis_url
        
        # Agent-net configuration
        self.agent_net_url = os.getenv('AGENT_NET_URL', 'http://localhost:9876')
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')
        
        # Livepeer orchestrator info
        self.orchestrator_url = os.getenv('ORCHESTRATOR_URL', 'http://orchestrator:9995')
        self.orchestrator_secret = os.getenv('ORCHESTRATOR_SECRET', 'orch-secret')
        
        # Message queue and state
        self.mq = None
        self.redis = None
        self.registered = False
        self.gpu_metrics = {}
        self.available_models = []
        
    async def initialize(self):
        """Initialize connections to platform services"""
        # Connect to message queue
        self.mq = MessageQueue(self.rabbitmq_url)
        await self.mq.connect()
        
        # Import Redis async
        import redis.asyncio as redis
        self.redis = await redis.from_url(self.redis_url)
        
        # Subscribe to orchestrator events
        await self.mq.subscribe_to_events(
            [EventType.AGENT_DEPLOY_REQUEST, EventType.ORCHESTRATOR_HEALTH_CHECK],
            self.handle_swarm_event,
            f"orchestrator-{self.orchestrator_id}"
        )
        
        logger.info(f"SwarmConnector initialized for orchestrator {self.orchestrator_id}")
        
    async def register_with_swarm(self):
        """Register this GPU orchestrator with the AutoGen swarm"""
        try:
            # Get GPU status from agent-net
            gpu_status = await self._get_gpu_status()
            
            # Get available models from Ollama
            models = await self._get_available_models()
            
            registration = {
                'orchestrator_id': self.orchestrator_id,
                'node_hostname': self.node_hostname,
                'type': 'gpu',
                'capabilities': {
                    'gpu': gpu_status,
                    'models': models,
                    'ollama_enabled': True,
                    'livepeer_enabled': True
                },
                'status': 'active',
                'registered_at': datetime.utcnow().isoformat()
            }
            
            # Store in Redis
            await self.redis.hset(
                'orchestrators',
                self.orchestrator_id,
                json.dumps(registration)
            )
            
            # Publish registration event
            await self.mq.publish_event(Event(
                type=EventType.ORCHESTRATOR_REGISTERED,
                timestamp=datetime.utcnow(),
                payload=registration
            ))
            
            self.registered = True
            logger.info(f"Orchestrator {self.orchestrator_id} registered with swarm")
            
            # Start heartbeat
            asyncio.create_task(self._heartbeat_loop())
            
        except Exception as e:
            logger.error(f"Failed to register orchestrator: {e}")
            raise
            
    async def _get_gpu_status(self) -> Dict[str, Any]:
        """Get GPU status from agent-net endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.agent_net_url}/gpu-check") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            'available': data.get('gpu_available', False),
                            'vram_total_mb': data.get('vram_total_mb', 0),
                            'vram_used_mb': data.get('vram_used_mb', 0),
                            'temperature': data.get('temperature', 0),
                            'power_draw': data.get('power_draw', 0),
                            'compute_capability': data.get('compute_capability', 'unknown')
                        }
        except Exception as e:
            logger.error(f"Error getting GPU status: {e}")
            
        return {'available': False, 'error': str(e)}
        
    async def _get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [model['name'] for model in data.get('models', [])]
        except Exception as e:
            logger.error(f"Error getting Ollama models: {e}")
            
        return []
        
    async def handle_swarm_event(self, event: Event):
        """Handle events from the AutoGen swarm"""
        try:
            if event.type == EventType.AGENT_DEPLOY_REQUEST:
                await self._handle_agent_deployment(event.payload)
            elif event.type == EventType.ORCHESTRATOR_HEALTH_CHECK:
                await self._send_health_status()
                
        except Exception as e:
            logger.error(f"Error handling swarm event: {e}")
            
    async def _handle_agent_deployment(self, agent_config: Dict[str, Any]):
        """Deploy an AutoGen agent on this GPU orchestrator"""
        agent_id = agent_config.get('agent_id')
        
        # Check if we have the required model
        required_model = agent_config.get('model', 'codellama:34b')
        if required_model not in self.available_models:
            logger.warning(f"Model {required_model} not available on this orchestrator")
            await self._notify_deployment_failure(agent_id, "Model not available")
            return
            
        try:
            # Create agent container with GPU access
            deployment_result = await self._deploy_gpu_agent(agent_config)
            
            # Notify success
            await self.mq.publish_event(Event(
                type=EventType.AGENT_DEPLOYED,
                timestamp=datetime.utcnow(),
                payload={
                    'agent_id': agent_id,
                    'orchestrator_id': self.orchestrator_id,
                    'deployment': deployment_result
                }
            ))
            
        except Exception as e:
            logger.error(f"Failed to deploy agent {agent_id}: {e}")
            await self._notify_deployment_failure(agent_id, str(e))
            
    async def _deploy_gpu_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy agent container with GPU and Ollama access"""
        # This would integrate with Docker to create the agent container
        # For now, return mock deployment info
        return {
            'container_id': f"agent-{agent_config['agent_id']}-gpu",
            'status': 'running',
            'gpu_allocated': True,
            'model': agent_config.get('model'),
            'ollama_endpoint': self.ollama_url
        }
        
    async def _notify_deployment_failure(self, agent_id: str, reason: str):
        """Notify swarm of deployment failure"""
        await self.mq.publish_event(Event(
            type=EventType.AGENT_DEPLOYMENT_FAILED,
            timestamp=datetime.utcnow(),
            payload={
                'agent_id': agent_id,
                'orchestrator_id': self.orchestrator_id,
                'reason': reason
            }
        ))
        
    async def _send_health_status(self):
        """Send health status to swarm"""
        gpu_status = await self._get_gpu_status()
        
        health = {
            'orchestrator_id': self.orchestrator_id,
            'status': 'healthy' if gpu_status.get('available') else 'degraded',
            'gpu': gpu_status,
            'models': self.available_models,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.mq.publish_event(Event(
            type=EventType.ORCHESTRATOR_HEALTH_UPDATE,
            timestamp=datetime.utcnow(),
            payload=health
        ))
        
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to swarm"""
        while self.registered:
            try:
                await self._send_health_status()
                
                # Update GPU metrics
                self.gpu_metrics = await self._get_gpu_status()
                self.available_models = await self._get_available_models()
                
                # Store updated info in Redis
                await self.redis.hset(
                    f'orchestrator:{self.orchestrator_id}:metrics',
                    'gpu',
                    json.dumps(self.gpu_metrics)
                )
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
                
    async def handle_livepeer_payment(self, ticket_info: Dict[str, Any]):
        """Handle payment tickets from Livepeer orchestrator"""
        # Track payments for this orchestrator
        await self.redis.hincrby(
            f'orchestrator:{self.orchestrator_id}:payments',
            'total_tickets',
            1
        )
        
        await self.redis.hincrbyfloat(
            f'orchestrator:{self.orchestrator_id}:payments',
            'total_face_value',
            float(ticket_info.get('faceValue', 0))
        )
        
        logger.info(f"Payment ticket processed: {ticket_info}")
        
    async def shutdown(self):
        """Clean shutdown of orchestrator"""
        self.registered = False
        
        # Notify swarm of shutdown
        await self.mq.publish_event(Event(
            type=EventType.ORCHESTRATOR_SHUTDOWN,
            timestamp=datetime.utcnow(),
            payload={'orchestrator_id': self.orchestrator_id}
        ))
        
        # Clean up connections
        if self.mq:
            await self.mq.close()
        if self.redis:
            await self.redis.close()