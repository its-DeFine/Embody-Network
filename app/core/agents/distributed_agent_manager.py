"""
Distributed Agent Manager

Manages agent deployment and lifecycle across multiple remote containers.
Provides load balancing, failover, and agent migration capabilities.
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

import aiohttp
from pydantic import BaseModel, Field

from ...config import settings
from ...dependencies import get_redis
from ..orchestration.container_registry import container_registry
from ..orchestration.container_discovery import container_discovery_service

logger = logging.getLogger(__name__)


class AgentDeploymentStrategy(str, Enum):
    """Agent deployment strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RESOURCE_BASED = "resource_based"
    CAPABILITY_BASED = "capability_based"
    AFFINITY_BASED = "affinity_based"


class AgentDeploymentRequest(BaseModel):
    """Agent deployment request model"""
    agent_type: str
    agent_config: Dict[str, Any] = {}
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    preferred_container: Optional[str] = None
    deployment_strategy: AgentDeploymentStrategy = AgentDeploymentStrategy.LEAST_LOADED
    constraints: Dict[str, Any] = Field(default_factory=dict)


class AgentMigrationRequest(BaseModel):
    """Agent migration request model"""
    agent_id: str
    target_container_id: Optional[str] = None
    reason: str = "manual"
    preserve_state: bool = True


class DistributedAgentManager:
    """
    Manages agent deployment and lifecycle across distributed containers.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis = None
        self.deployment_lock = asyncio.Lock()
        self.migration_lock = asyncio.Lock()
        self.agent_deployments: Dict[str, str] = {}  # agent_id -> container_id
        self.deployment_history: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize the distributed agent manager"""
        try:
            self.redis = await get_redis()
            await self._load_deployment_state()
            logger.info("Distributed Agent Manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize distributed agent manager: {e}")
            raise
    
    async def deploy_agent(self, request: AgentDeploymentRequest) -> Dict[str, Any]:
        """Deploy an agent to an optimal container"""
        async with self.deployment_lock:
            try:
                # Select target container based on strategy
                target_container = await self._select_deployment_container(request)
                if not target_container:
                    raise ValueError("No suitable container found for deployment")
                
                # Generate agent ID
                agent_id = f"{request.agent_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
                
                # Prepare deployment configuration
                deployment_config = {
                    "agent_id": agent_id,
                    "agent_type": request.agent_type,
                    "agent_config": request.agent_config,
                    "resource_requirements": request.resource_requirements,
                    "deployment_timestamp": datetime.utcnow().isoformat()
                }
                
                # Deploy to container
                deployment_result = await self._deploy_to_container(
                    target_container, 
                    deployment_config
                )
                
                if deployment_result["success"]:
                    # Record deployment
                    self.agent_deployments[agent_id] = target_container["container_id"]
                    
                    # Save deployment state
                    await self._save_deployment_state()
                    
                    # Record deployment history
                    history_entry = {
                        "agent_id": agent_id,
                        "container_id": target_container["container_id"],
                        "deployment_time": datetime.utcnow().isoformat(),
                        "strategy": request.deployment_strategy,
                        "result": "success"
                    }
                    self.deployment_history.append(history_entry)
                    
                    # Publish deployment event
                    await self._publish_deployment_event("agent_deployed", {
                        "agent_id": agent_id,
                        "container_id": target_container["container_id"],
                        "agent_type": request.agent_type
                    })
                    
                    logger.info(f"Successfully deployed agent {agent_id} to container {target_container['container_id']}")
                    
                    return {
                        "success": True,
                        "agent_id": agent_id,
                        "container_id": target_container["container_id"],
                        "container_name": target_container.get("container_name"),
                        "deployment_details": deployment_result.get("details", {})
                    }
                else:
                    raise Exception(f"Deployment failed: {deployment_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Agent deployment failed: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
    
    async def _select_deployment_container(self, request: AgentDeploymentRequest) -> Optional[Dict[str, Any]]:
        """Select the best container for agent deployment"""
        # Get available containers
        containers = await container_registry.get_containers_by_capability("agent_runner")
        
        if not containers:
            logger.warning("No containers with agent_runner capability found")
            return None
        
        # Filter by constraints
        if request.constraints:
            containers = self._filter_by_constraints(containers, request.constraints)
        
        # Apply deployment strategy
        if request.deployment_strategy == AgentDeploymentStrategy.ROUND_ROBIN:
            return await self._select_round_robin(containers)
        elif request.deployment_strategy == AgentDeploymentStrategy.LEAST_LOADED:
            return await self._select_least_loaded(containers)
        elif request.deployment_strategy == AgentDeploymentStrategy.RESOURCE_BASED:
            return await self._select_resource_based(containers, request.resource_requirements)
        elif request.deployment_strategy == AgentDeploymentStrategy.CAPABILITY_BASED:
            return await self._select_capability_based(containers, request.agent_type)
        elif request.deployment_strategy == AgentDeploymentStrategy.AFFINITY_BASED:
            return await self._select_affinity_based(containers, request.agent_type)
        else:
            # Default to least loaded
            return await self._select_least_loaded(containers)
    
    def _filter_by_constraints(self, containers: List[Dict[str, Any]], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter containers by constraints"""
        filtered = []
        
        for container in containers:
            meets_constraints = True
            
            # Check each constraint
            for key, value in constraints.items():
                if key == "min_memory" and container.get("resources", {}).get("memory_limit", 0) < value:
                    meets_constraints = False
                    break
                elif key == "min_cpu" and container.get("resources", {}).get("cpu_count", 0) < value:
                    meets_constraints = False
                    break
                elif key == "required_capabilities":
                    container_caps = set(container.get("capabilities", []))
                    required_caps = set(value)
                    if not required_caps.issubset(container_caps):
                        meets_constraints = False
                        break
            
            if meets_constraints:
                filtered.append(container)
        
        return filtered
    
    async def _select_round_robin(self, containers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select container using round-robin strategy"""
        if not containers:
            return None
        
        # Get last used container index
        last_index = await self.redis.get("deployment:round_robin:index")
        if last_index:
            last_index = int(last_index)
        else:
            last_index = -1
        
        # Select next container
        next_index = (last_index + 1) % len(containers)
        await self.redis.set("deployment:round_robin:index", next_index)
        
        return containers[next_index]
    
    async def _select_least_loaded(self, containers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select least loaded container"""
        if not containers:
            return None
        
        # Count agents per container
        agent_counts = {}
        for container in containers:
            container_id = container["container_id"]
            count = sum(1 for c_id in self.agent_deployments.values() if c_id == container_id)
            agent_counts[container_id] = count
        
        # Sort by agent count and resource usage
        def load_score(container):
            container_id = container["container_id"]
            agent_count = agent_counts.get(container_id, 0)
            cpu_usage = container.get("resources", {}).get("cpu_usage_percent", 0)
            memory_usage = container.get("resources", {}).get("memory_percent", 0)
            
            # Combined load score (lower is better)
            return agent_count * 100 + cpu_usage + memory_usage
        
        containers.sort(key=load_score)
        return containers[0]
    
    async def _select_resource_based(self, containers: List[Dict[str, Any]], requirements: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select container based on resource availability"""
        if not containers:
            return None
        
        suitable_containers = []
        
        for container in containers:
            resources = container.get("resources", {})
            
            # Check if container meets resource requirements
            meets_requirements = True
            
            if "memory" in requirements:
                available_memory = resources.get("memory_limit", 0) - resources.get("memory_usage", 0)
                if available_memory < requirements["memory"]:
                    meets_requirements = False
            
            if "cpu" in requirements:
                available_cpu = 100 - resources.get("cpu_usage_percent", 0)
                if available_cpu < requirements["cpu"]:
                    meets_requirements = False
            
            if meets_requirements:
                suitable_containers.append(container)
        
        # Select container with most available resources
        if suitable_containers:
            return max(suitable_containers, key=lambda c: 
                (c.get("resources", {}).get("memory_limit", 0) - c.get("resources", {}).get("memory_usage", 0)) +
                (100 - c.get("resources", {}).get("cpu_usage_percent", 0))
            )
        
        return None
    
    async def _select_capability_based(self, containers: List[Dict[str, Any]], agent_type: str) -> Optional[Dict[str, Any]]:
        """Select container based on capabilities"""
        if not containers:
            return None
        
        # Define preferred capabilities for agent types
        preferred_capabilities = {
            "trading": ["gpu_compute", "high_memory", "low_latency"],
            "analysis": ["high_memory", "data_processing"],
            "monitoring": ["network_edge", "low_latency"]
        }
        
        preferred = preferred_capabilities.get(agent_type, [])
        
        # Score containers by capability match
        def capability_score(container):
            capabilities = set(container.get("capabilities", []))
            score = sum(1 for cap in preferred if cap in capabilities)
            return score
        
        containers.sort(key=capability_score, reverse=True)
        return containers[0]
    
    async def _select_affinity_based(self, containers: List[Dict[str, Any]], agent_type: str) -> Optional[Dict[str, Any]]:
        """Select container based on agent affinity (co-location preferences)"""
        if not containers:
            return None
        
        # Count similar agents per container
        affinity_scores = {}
        
        for container in containers:
            container_id = container["container_id"]
            similar_agents = 0
            
            # Count agents of same type on this container
            for agent_id, deployed_container_id in self.agent_deployments.items():
                if deployed_container_id == container_id and agent_type in agent_id:
                    similar_agents += 1
            
            affinity_scores[container_id] = similar_agents
        
        # Sort by affinity score (higher is better for co-location)
        containers.sort(key=lambda c: affinity_scores.get(c["container_id"], 0), reverse=True)
        return containers[0]
    
    async def _deploy_to_container(self, container: Dict[str, Any], deployment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy agent to specific container"""
        try:
            # Get container API endpoint
            api_endpoint = container.get("api_endpoint")
            if not api_endpoint:
                # Construct from host and port
                host = container.get("host_address", "localhost")
                api_endpoint = f"http://{host}:8001"
            
            # Make deployment request to container
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{api_endpoint}/agents/deploy",
                    json=deployment_config,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "details": result
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Container returned {response.status}: {error_text}"
                        }
                        
        except Exception as e:
            logger.error(f"Error deploying to container: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def migrate_agent(self, request: AgentMigrationRequest) -> Dict[str, Any]:
        """Migrate an agent from one container to another"""
        async with self.migration_lock:
            try:
                # Get current container
                current_container_id = self.agent_deployments.get(request.agent_id)
                if not current_container_id:
                    raise ValueError(f"Agent {request.agent_id} not found in deployments")
                
                # Get agent state if preserving
                agent_state = None
                if request.preserve_state:
                    agent_state = await self._get_agent_state(request.agent_id, current_container_id)
                
                # Select target container
                if request.target_container_id:
                    target_container = await container_registry.get_container(request.target_container_id)
                else:
                    # Auto-select based on current deployment strategy
                    deploy_request = AgentDeploymentRequest(
                        agent_type=request.agent_id.split("-")[0],
                        deployment_strategy=AgentDeploymentStrategy.LEAST_LOADED
                    )
                    target_container = await self._select_deployment_container(deploy_request)
                
                if not target_container:
                    raise ValueError("No suitable target container found")
                
                # Stop agent on current container
                await self._stop_agent_on_container(request.agent_id, current_container_id)
                
                # Deploy to new container
                deployment_config = {
                    "agent_id": request.agent_id,
                    "migration": True,
                    "previous_container": current_container_id,
                    "agent_state": agent_state
                }
                
                deployment_result = await self._deploy_to_container(target_container, deployment_config)
                
                if deployment_result["success"]:
                    # Update deployment mapping
                    self.agent_deployments[request.agent_id] = target_container["container_id"]
                    await self._save_deployment_state()
                    
                    # Publish migration event
                    await self._publish_deployment_event("agent_migrated", {
                        "agent_id": request.agent_id,
                        "from_container": current_container_id,
                        "to_container": target_container["container_id"],
                        "reason": request.reason
                    })
                    
                    logger.info(f"Successfully migrated agent {request.agent_id} from {current_container_id} to {target_container['container_id']}")
                    
                    return {
                        "success": True,
                        "from_container": current_container_id,
                        "to_container": target_container["container_id"]
                    }
                else:
                    # Rollback - restart on original container
                    await self._restart_agent_on_container(request.agent_id, current_container_id, agent_state)
                    raise Exception(f"Migration failed: {deployment_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Agent migration failed: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
    
    async def _get_agent_state(self, agent_id: str, container_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state from container"""
        try:
            container = await container_registry.get_container(container_id)
            if not container:
                return None
            
            api_endpoint = container.get("api_endpoint", f"http://{container.get('host_address')}:8001")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{api_endpoint}/agents/{agent_id}/state") as response:
                    if response.status == 200:
                        return await response.json()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting agent state: {e}")
            return None
    
    async def _stop_agent_on_container(self, agent_id: str, container_id: str) -> bool:
        """Stop agent on container"""
        try:
            container = await container_registry.get_container(container_id)
            if not container:
                return False
            
            api_endpoint = container.get("api_endpoint", f"http://{container.get('host_address')}:8001")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{api_endpoint}/agents/{agent_id}/stop") as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Error stopping agent: {e}")
            return False
    
    async def _restart_agent_on_container(self, agent_id: str, container_id: str, agent_state: Optional[Dict[str, Any]]) -> bool:
        """Restart agent on container with state"""
        try:
            container = await container_registry.get_container(container_id)
            if not container:
                return False
            
            deployment_config = {
                "agent_id": agent_id,
                "restart": True,
                "agent_state": agent_state
            }
            
            result = await self._deploy_to_container(container, deployment_config)
            return result["success"]
            
        except Exception as e:
            logger.error(f"Error restarting agent: {e}")
            return False
    
    async def get_agent_deployment(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent deployment information"""
        container_id = self.agent_deployments.get(agent_id)
        if not container_id:
            return None
        
        container = await container_registry.get_container(container_id)
        if not container:
            return None
        
        return {
            "agent_id": agent_id,
            "container_id": container_id,
            "container_name": container.get("container_name"),
            "host_address": container.get("host_address"),
            "deployment_time": "N/A"  # Would need to track this separately
        }
    
    async def get_all_deployments(self) -> Dict[str, str]:
        """Get all agent deployments"""
        return self.agent_deployments.copy()
    
    async def get_container_agents(self, container_id: str) -> List[str]:
        """Get all agents deployed on a container"""
        return [agent_id for agent_id, c_id in self.agent_deployments.items() if c_id == container_id]
    
    async def handle_container_failure(self, container_id: str):
        """Handle container failure by migrating agents"""
        logger.warning(f"Handling failure of container {container_id}")
        
        # Get all agents on failed container
        affected_agents = await self.get_container_agents(container_id)
        
        if not affected_agents:
            logger.info(f"No agents affected by failure of container {container_id}")
            return
        
        logger.info(f"Migrating {len(affected_agents)} agents from failed container {container_id}")
        
        # Migrate each agent
        migration_results = []
        for agent_id in affected_agents:
            result = await self.migrate_agent(AgentMigrationRequest(
                agent_id=agent_id,
                reason="container_failure",
                preserve_state=False  # State might be lost
            ))
            migration_results.append(result)
        
        # Publish container failure event
        await self._publish_deployment_event("container_failed", {
            "container_id": container_id,
            "affected_agents": affected_agents,
            "migration_results": migration_results
        })
    
    async def rebalance_agents(self) -> Dict[str, Any]:
        """Rebalance agents across containers for optimal distribution"""
        logger.info("Starting agent rebalancing")
        
        # Get all containers and their loads
        containers = await container_registry.get_containers_by_capability("agent_runner")
        if len(containers) < 2:
            return {"message": "Not enough containers for rebalancing"}
        
        # Calculate current load distribution
        container_loads = {}
        for container in containers:
            container_id = container["container_id"]
            agent_count = len(await self.get_container_agents(container_id))
            container_loads[container_id] = agent_count
        
        # Calculate average load
        total_agents = sum(container_loads.values())
        avg_load = total_agents / len(containers)
        
        # Identify overloaded and underloaded containers
        overloaded = [(c_id, count) for c_id, count in container_loads.items() if count > avg_load + 1]
        underloaded = [(c_id, count) for c_id, count in container_loads.items() if count < avg_load - 1]
        
        if not overloaded or not underloaded:
            return {"message": "Containers are already balanced"}
        
        # Migrate agents from overloaded to underloaded containers
        migrations = []
        for over_container_id, over_count in overloaded:
            agents_to_migrate = await self.get_container_agents(over_container_id)
            excess_agents = int(over_count - avg_load)
            
            for i in range(min(excess_agents, len(agents_to_migrate))):
                if underloaded:
                    target_container_id, _ = underloaded[0]
                    
                    result = await self.migrate_agent(AgentMigrationRequest(
                        agent_id=agents_to_migrate[i],
                        target_container_id=target_container_id,
                        reason="rebalancing"
                    ))
                    
                    migrations.append(result)
                    
                    # Update load counts
                    container_loads[over_container_id] -= 1
                    container_loads[target_container_id] += 1
                    
                    # Check if target is no longer underloaded
                    if container_loads[target_container_id] >= avg_load - 1:
                        underloaded.pop(0)
        
        return {
            "rebalanced": True,
            "migrations": len(migrations),
            "final_distribution": container_loads
        }
    
    async def _load_deployment_state(self):
        """Load deployment state from Redis"""
        try:
            deployment_data = await self.redis.get("agent:deployments")
            if deployment_data:
                self.agent_deployments = json.loads(deployment_data)
                logger.info(f"Loaded {len(self.agent_deployments)} agent deployments")
        except Exception as e:
            logger.error(f"Error loading deployment state: {e}")
    
    async def _save_deployment_state(self):
        """Save deployment state to Redis"""
        try:
            await self.redis.set("agent:deployments", json.dumps(self.agent_deployments))
        except Exception as e:
            logger.error(f"Error saving deployment state: {e}")
    
    async def _publish_deployment_event(self, event_type: str, data: Dict[str, Any]):
        """Publish deployment event"""
        try:
            event = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
            await self.redis.publish("events:agent:deployment", json.dumps(event))
        except Exception as e:
            logger.error(f"Error publishing deployment event: {e}")


# Singleton instance
distributed_agent_manager = DistributedAgentManager()