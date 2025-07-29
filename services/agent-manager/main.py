import os
import asyncio
import logging
import json
from typing import Dict, Optional, Any
from datetime import datetime
import docker
import redis.asyncio as redis
from contextlib import asynccontextmanager
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import shared modules
import sys
sys.path.append('/app')
from shared.models.agent_models import AgentConfig, AgentInstance, AgentStatus, AgentTeam
from shared.events.event_types import Event, EventType
from shared.utils.message_queue import get_message_queue

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentManager:
    """Manages the lifecycle of customer AutoGen agents"""
    
    def __init__(self, redis_client: redis.Redis, docker_client: docker.DockerClient):
        self.redis = redis_client
        self.docker = docker_client
        self.agents: Dict[str, AgentInstance] = {}
        self.mq = None
        self.running = True
        
    async def initialize(self, mq):
        """Initialize the agent manager"""
        self.mq = mq
        
        # Subscribe to agent events
        await mq.subscribe_to_events(
            [EventType.AGENT_CREATED, EventType.AGENT_UPDATED],
            self.handle_agent_event,
            "agent-manager-events"
        )
        
        # Subscribe to direct messages
        await mq.receive_direct_messages(
            "agent-manager",
            self.handle_direct_message
        )
        
        # Start heartbeat monitor
        asyncio.create_task(self.monitor_agents())
        
        logger.info("Agent Manager initialized")
    
    async def handle_agent_event(self, event: Event):
        """Handle agent lifecycle events"""
        try:
            if event.event_type == EventType.AGENT_CREATED:
                agent_config = AgentConfig(**event.data)
                await self.create_agent_container(agent_config)
            elif event.event_type == EventType.AGENT_UPDATED:
                agent_config = AgentConfig(**event.data)
                await self.update_agent(agent_config)
        except Exception as e:
            logger.error(f"Error handling agent event: {e}")
    
    async def handle_direct_message(self, message: Dict[str, Any]):
        """Handle direct messages for agent actions"""
        try:
            message_type = message.get("message_type")
            payload = message.get("payload", {})
            
            if message_type == "agent.start":
                await self.start_agent(payload["agent_id"])
            elif message_type == "agent.stop":
                await self.stop_agent(payload["agent_id"])
            elif message_type == "agent.pause":
                await self.pause_agent(payload["agent_id"])
            elif message_type == "agent.update":
                await self.update_agent_config(payload["agent_id"], payload.get("config", {}))
            elif message_type == "team.orchestrate":
                await self.orchestrate_team(payload["team_id"])
            elif message_type == "admin.agent.stop":
                # Admin force stop
                agent_id = payload.get("agent_id")
                reason = payload.get("reason", "Admin requested stop")
                force = payload.get("force", False)
                admin_id = payload.get("admin_id")
                
                logger.warning(f"Admin {admin_id} stopping agent {agent_id}. Reason: {reason}")
                
                if force:
                    # Force kill the container
                    instance = self.agents.get(agent_id)
                    if instance and instance.container_id:
                        try:
                            container = self.docker.containers.get(instance.container_id)
                            container.kill()
                            
                            # Update status
                            instance.status = AgentStatus.PAUSED
                            await self.redis.hset(
                                f"agent_instance:{agent_id}",
                                mapping={
                                    **instance.dict(),
                                    "stopped_by": f"admin:{admin_id}",
                                    "stop_reason": reason
                                }
                            )
                            
                            # Publish admin stop event
                            await self.mq.publish_event(Event(
                                event_id=f"admin-stopped-{agent_id}",
                                event_type=EventType.ADMIN_AGENT_STOPPED,
                                source="agent-manager",
                                data={
                                    "agent_id": agent_id,
                                    "admin_id": admin_id,
                                    "reason": reason,
                                    "force": force
                                }
                            ))
                        except Exception as e:
                            logger.error(f"Failed to force stop agent {agent_id}: {str(e)}")
                else:
                    await self.stop_agent(agent_id)
        except Exception as e:
            logger.error(f"Error handling direct message: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(docker.errors.APIError)
    )
    async def create_agent_container(self, agent_config: AgentConfig):
        """Create and start a new agent container with retry logic"""
        try:
            # Create container configuration
            container_name = f"agent-{agent_config.customer_id}-{agent_config.agent_id}"
            
            # Build environment variables
            env_vars = {
                "AGENT_ID": agent_config.agent_id,
                "CUSTOMER_ID": agent_config.customer_id,
                "AGENT_TYPE": agent_config.agent_type.value,
                "AGENT_NAME": agent_config.name,
                "RABBITMQ_URL": os.getenv("RABBITMQ_URL"),
                "REDIS_URL": os.getenv("REDIS_URL"),
                "CONFIG": json.dumps(agent_config.config),
                "AUTOGEN_CONFIG": json.dumps(agent_config.autogen_config)
            }
            
            # Add API keys if available
            if "OPENAI_API_KEY" in os.environ:
                env_vars["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
            if "ANTHROPIC_API_KEY" in os.environ:
                env_vars["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
            
            # Create container
            container = self.docker.containers.run(
                image="autogen-agent:latest",  # Will be built in update pipeline
                name=container_name,
                environment=env_vars,
                network="operation_autogen-network",
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                labels={
                    "agent_id": agent_config.agent_id,
                    "customer_id": agent_config.customer_id,
                    "agent_type": agent_config.agent_type.value
                }
            )
            
            # Create agent instance
            instance = AgentInstance(
                agent_id=agent_config.agent_id,
                container_id=container.id,
                status=AgentStatus.RUNNING,
                started_at=datetime.utcnow()
            )
            
            # Store instance in Redis
            await self.redis.hset(
                f"agent_instance:{agent_config.agent_id}",
                mapping=instance.dict()
            )
            
            self.agents[agent_config.agent_id] = instance
            
            # Publish event
            await self.mq.publish_event(Event(
                event_id=f"agent-started-{agent_config.agent_id}",
                event_type=EventType.AGENT_STARTED,
                source="agent-manager",
                customer_id=agent_config.customer_id,
                data=instance.dict()
            ))
            
            logger.info(f"Created agent container: {container_name}")
            
        except Exception as e:
            logger.error(f"Failed to create agent container: {e}")
            
            # Publish error event
            await self.mq.publish_event(Event(
                event_id=f"agent-error-{agent_config.agent_id}",
                event_type=EventType.AGENT_ERROR,
                source="agent-manager",
                customer_id=agent_config.customer_id,
                data={
                    "agent_id": agent_config.agent_id,
                    "error": str(e)
                }
            ))
    
    async def start_agent(self, agent_id: str):
        """Start a stopped agent"""
        instance = self.agents.get(agent_id)
        if not instance or not instance.container_id:
            logger.error(f"Agent {agent_id} not found")
            return
        
        try:
            container = self.docker.containers.get(instance.container_id)
            container.start()
            
            instance.status = AgentStatus.RUNNING
            instance.started_at = datetime.utcnow()
            
            await self.redis.hset(
                f"agent_instance:{agent_id}",
                mapping=instance.dict()
            )
            
            logger.info(f"Started agent: {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=5)
    )
    async def stop_agent(self, agent_id: str):
        """Stop a running agent with retry logic"""
        instance = self.agents.get(agent_id)
        if not instance or not instance.container_id:
            logger.error(f"Agent {agent_id} not found")
            return
        
        try:
            container = self.docker.containers.get(instance.container_id)
            # Increase timeout for complex agents
            container.stop(timeout=60)
            
            instance.status = AgentStatus.PAUSED
            
            await self.redis.hset(
                f"agent_instance:{agent_id}",
                mapping=instance.dict()
            )
            
            # Get customer_id from Redis
            agent_data = await self.redis.hgetall(f"agent:{instance.agent_id}")
            customer_id = agent_data.get("customer_id")
            
            # Publish event
            await self.mq.publish_event(Event(
                event_id=f"agent-stopped-{agent_id}",
                event_type=EventType.AGENT_STOPPED,
                source="agent-manager",
                customer_id=customer_id,
                data=instance.dict()
            ))
            
            logger.info(f"Stopped agent: {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_id}: {e}")
    
    async def pause_agent(self, agent_id: str):
        """Pause a running agent"""
        instance = self.agents.get(agent_id)
        if not instance or not instance.container_id:
            logger.error(f"Agent {agent_id} not found")
            return
        
        try:
            container = self.docker.containers.get(instance.container_id)
            container.pause()
            
            instance.status = AgentStatus.PAUSED
            
            await self.redis.hset(
                f"agent_instance:{agent_id}",
                mapping=instance.dict()
            )
            
            logger.info(f"Paused agent: {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to pause agent {agent_id}: {e}")
    
    async def update_agent_config(self, agent_id: str, config: Dict[str, Any]):
        """Update agent configuration"""
        instance = self.agents.get(agent_id)
        if not instance:
            logger.error(f"Agent {agent_id} not found")
            return
        
        try:
            # Update configuration in Redis
            await self.redis.hset(
                f"agent:{agent_id}",
                "config",
                json.dumps(config)
            )
            
            # Send update message to agent container
            await self.mq.send_direct_message(
                target=f"agent-{agent_id}",
                message_type="config.update",
                payload=config
            )
            
            logger.info(f"Updated configuration for agent: {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to update agent {agent_id}: {e}")
    
    async def update_agent(self, agent_config: AgentConfig):
        """Update an existing agent with new configuration"""
        instance = self.agents.get(agent_config.agent_id)
        if not instance or not instance.container_id:
            # Agent doesn't exist, create it
            await self.create_agent_container(agent_config)
            return
        
        try:
            # Update status
            instance.status = AgentStatus.UPDATING
            await self.redis.hset(
                f"agent_instance:{agent_config.agent_id}",
                mapping=instance.dict()
            )
            
            # Stop current container
            container = self.docker.containers.get(instance.container_id)
            container.stop(timeout=30)
            container.remove()
            
            # Create new container with updated config
            await self.create_agent_container(agent_config)
            
        except Exception as e:
            logger.error(f"Failed to update agent {agent_config.agent_id}: {e}")
    
    async def orchestrate_team(self, team_id: str):
        """Orchestrate agent team interactions"""
        try:
            # Get team configuration
            team_data = await self.redis.hgetall(f"team:{team_id}")
            if not team_data:
                logger.error(f"Team {team_id} not found")
                return
            
            team = AgentTeam(**team_data)
            
            # Verify all agents are running
            for agent_id in team.agent_ids:
                instance = self.agents.get(agent_id)
                if not instance or instance.status != AgentStatus.RUNNING:
                    logger.warning(f"Agent {agent_id} not running for team {team_id}")
                    return
            
            # Send orchestration messages to agents
            for agent_id in team.agent_ids:
                await self.mq.send_direct_message(
                    target=f"agent-{agent_id}",
                    message_type="team.join",
                    payload={
                        "team_id": team_id,
                        "team_members": team.agent_ids,
                        "orchestrator_config": team.orchestrator_config
                    }
                )
            
            logger.info(f"Orchestrated team: {team_id}")
            
        except Exception as e:
            logger.error(f"Failed to orchestrate team {team_id}: {e}")
    
    async def monitor_agents(self):
        """Monitor agent health and collect metrics"""
        while self.running:
            try:
                for agent_id, instance in self.agents.items():
                    if instance.status == AgentStatus.RUNNING and instance.container_id:
                        try:
                            container = self.docker.containers.get(instance.container_id)
                            stats = container.stats(stream=False)
                            
                            # Update metrics with safe network interface handling
                            network_stats = stats.get("networks", {})
                            eth0_stats = network_stats.get("eth0", {})
                            
                            instance.metrics = {
                                "cpu_usage": self._calculate_cpu_usage(stats),
                                "memory_usage": stats.get("memory_stats", {}).get("usage", 0),
                                "network_rx": eth0_stats.get("rx_bytes", 0),
                                "network_tx": eth0_stats.get("tx_bytes", 0)
                            }
                            instance.last_heartbeat = datetime.utcnow()
                            
                            # Update Redis
                            await self.redis.hset(
                                f"agent_instance:{agent_id}",
                                mapping=instance.dict()
                            )
                            
                        except docker.errors.NotFound:
                            # Container was removed
                            instance.status = AgentStatus.ERROR
                            instance.error_message = "Container not found"
                            
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in agent monitor: {e}")
                await asyncio.sleep(30)
    
    def _calculate_cpu_usage(self, stats: Dict[str, Any]) -> float:
        """Calculate CPU usage percentage from Docker stats"""
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                   stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                      stats["precpu_stats"]["system_cpu_usage"]
        
        if system_delta > 0 and cpu_delta > 0:
            cpu_usage = (cpu_delta / system_delta) * 100.0
            return round(cpu_usage, 2)
        return 0.0
    
    async def cleanup(self):
        """Cleanup resources"""
        self.running = False
        # Stop all agents gracefully
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)


async def main():
    """Main entry point"""
    # Initialize Redis
    redis_client = await redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379"),
        encoding="utf-8",
        decode_responses=True
    )
    
    # Initialize Docker client
    # docker.from_env() will use DOCKER_HOST environment variable
    docker_client = docker.from_env()
    
    # Create agent manager
    manager = AgentManager(redis_client, docker_client)
    
    # Connect to message queue and initialize
    async with get_message_queue() as mq:
        await manager.initialize(mq)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Agent Manager")
        finally:
            await manager.cleanup()
            await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())