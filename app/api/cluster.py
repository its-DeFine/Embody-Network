"""
Cluster Management API

REST API endpoints for managing the distributed container cluster,
including container discovery, agent deployment, and cluster monitoring.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio
import httpx
import docker

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json

from ..dependencies import get_current_user, get_redis
from ..core.orchestration.container_discovery import container_discovery_service
from ..core.orchestration.container_registry import container_registry, ContainerRegistration
from ..core.agents.distributed_agent_manager import (
    distributed_agent_manager,
    AgentDeploymentRequest,
    AgentMigrationRequest,
    AgentDeploymentStrategy,
)
from ..infrastructure.messaging.container_hub import container_hub
from ..db_models import get_db, register_cluster, update_heartbeat, get_active_clusters, mark_cluster_inactive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cluster", tags=["cluster"])

# Initialize Docker client for container health checks
try:
    docker_client = docker.from_env()
except Exception as e:
    logger.warning(f"Docker client not available: {e}")
    docker_client = None


# Request/Response Models

async def validate_cluster_health(cluster_name: str) -> Dict[str, Any]:
    """Validate actual cluster health via container checks and health endpoints"""
    try:
        cluster_health = {
            "cluster_name": cluster_name,
            "container_status": "unknown",
            "health_check": False,
            "uptime": None,
            "actual_status": "offline",
            "error": None,
            "last_validated": datetime.utcnow().isoformat()
        }
        
        # Check if container is actually running via Docker API
        if docker_client:
            try:
                container = docker_client.containers.get(cluster_name)
                cluster_health["container_status"] = container.status
                
                if container.status == "running":
                    cluster_health["uptime"] = container.attrs['State']['StartedAt']
                    
                    # Determine port from container name
                    port = 8002 if "cluster2" in cluster_name else 8001
                    
                    # Perform health check via HTTP
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        try:
                            health_response = await client.get(f"http://localhost:{port}/health")
                            cluster_health["health_check"] = health_response.status_code == 200
                            cluster_health["actual_status"] = "online" if health_response.status_code == 200 else "unhealthy"
                        except Exception as e:
                            logger.warning(f"Health check failed for {cluster_name}: {e}")
                            cluster_health["health_check"] = False
                            cluster_health["actual_status"] = "unreachable"
                else:
                    cluster_health["actual_status"] = "stopped"
                    
            except docker.errors.NotFound:
                cluster_health["container_status"] = "not_found"
                cluster_health["actual_status"] = "offline"
            except Exception as e:
                cluster_health["error"] = str(e)
                cluster_health["actual_status"] = "error"
        else:
            cluster_health["error"] = "Docker client not available"
            
        return cluster_health
        
    except Exception as e:
        logger.error(f"Error validating cluster health for {cluster_name}: {e}")
        return {
            "cluster_name": cluster_name,
            "container_status": "error",
            "health_check": False,
            "actual_status": "error", 
            "error": str(e),
            "last_validated": datetime.utcnow().isoformat()
        }


class ContainerRegistrationRequest(BaseModel):
    """Container registration request"""

    container_name: str
    host_address: str
    api_port: int = 8001
    capabilities: List[str] = []
    resources: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class ContainerHeartbeatRequest(BaseModel):
    """Container heartbeat request"""

    container_id: str
    health_score: int = Field(ge=0, le=100)
    resources: Dict[str, Any] = {}
    active_agents: int = 0


class AgentDeploymentRequestAPI(BaseModel):
    """API model for agent deployment request"""

    agent_type: str
    agent_config: Dict[str, Any] = {}
    resource_requirements: Dict[str, Any] = {}
    preferred_container: Optional[str] = None
    deployment_strategy: str = "least_loaded"
    constraints: Dict[str, Any] = {}


class AgentMigrationRequestAPI(BaseModel):
    """API model for agent migration request"""

    agent_id: str
    target_container_id: Optional[str] = None
    reason: str = "manual"
    preserve_state: bool = True


class ClusterActionRequest(BaseModel):
    """Cluster action request"""

    action: str  # rebalance, optimize, health_check
    params: Dict[str, Any] = {}


# Container Management Endpoints


@router.get("/status")
async def get_cluster_status(
    validate_health: bool = True,
    user: dict = Depends(get_current_user), 
    redis=Depends(get_redis)
) -> Dict[str, Any]:
    """Get overall cluster status with optional real-time health validation"""
    try:
        # Get cluster status from container registry
        cluster_status = await container_registry.get_cluster_status()

        # Get discovery statistics
        discovery_stats = container_discovery_service.get_discovery_stats()

        # Get communication hub statistics
        hub_stats = await container_hub.get_hub_statistics()

        # Get deployment statistics
        deployments = await distributed_agent_manager.get_all_deployments()

        # Enhanced: Validate actual cluster health if requested
        validated_clusters = {}
        if validate_health and hub_stats.get("subscriptions"):
            validation_tasks = []
            for cluster_name in hub_stats["subscriptions"].keys():
                validation_tasks.append(validate_cluster_health(cluster_name))
            
            # Run validations concurrently
            validations = await asyncio.gather(*validation_tasks, return_exceptions=True)
            
            for validation in validations:
                if isinstance(validation, dict) and "cluster_name" in validation:
                    validated_clusters[validation["cluster_name"]] = validation

        # Filter subscriptions to show only actually running clusters
        if validate_health and validated_clusters:
            active_subscriptions = {}
            for cluster_name, subscription_data in hub_stats.get("subscriptions", {}).items():
                cluster_validation = validated_clusters.get(cluster_name, {})
                if cluster_validation.get("actual_status") == "online":
                    active_subscriptions[cluster_name] = subscription_data
            
            # Update hub_stats with filtered subscriptions
            hub_stats["subscriptions"] = active_subscriptions
            hub_stats["validated_clusters"] = validated_clusters
            hub_stats["validation_timestamp"] = datetime.utcnow().isoformat()

        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "cluster": cluster_status,
            "discovery": discovery_stats,
            "communication": hub_stats,
            "deployments": {
                "total_agents": len(deployments),
                "agent_distribution": {},  # Would need to calculate
            },
        }

    except Exception as e:
        logger.error(f"Error getting cluster status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers")
async def get_all_containers(
    include_inactive: bool = False, user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> List[Dict[str, Any]]:
    """Get all containers in the cluster"""
    try:
        containers = await container_registry.get_all_containers(include_inactive=include_inactive)
        return containers

    except Exception as e:
        logger.error(f"Error getting containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/containers/{container_id}")
async def get_container_details(
    container_id: str, user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> Dict[str, Any]:
    """Get detailed information about a specific container"""
    try:
        container = await container_registry.get_container(container_id)
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")

        # Get agents on this container
        agents = await distributed_agent_manager.get_container_agents(container_id)
        container["deployed_agents"] = agents

        return container

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting container details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/containers/register")
async def register_container(
    request: ContainerRegistrationRequest,
    user: dict = Depends(get_current_user),
    redis=Depends(get_redis),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Register a new container with the cluster"""
    try:
        # Generate container ID
        container_id = f"{request.container_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Create registration
        registration = ContainerRegistration(
            container_id=container_id,
            container_name=request.container_name,
            host_address=request.host_address,
            api_endpoint=f"http://{request.host_address}:{request.api_port}",
            capabilities=request.capabilities,
            resources=request.resources,
            metadata=request.metadata,
        )

        # Register with container registry
        success = await container_registry.register_container(registration)

        if success:
            # Register with communication hub
            await container_hub.register_container(
                container_id,
                {
                    "name": request.container_name,
                    "host": request.host_address,
                    "port": request.api_port,
                    "capabilities": request.capabilities,
                },
            )
            
            # Also register with container discovery service for manual registration
            container_info = {
                "id": container_id,
                "name": request.container_name,
                "agent_type": request.metadata.get("agent_type", "generic"),
                "agent_port": request.api_port,
                "capabilities": request.capabilities,
                "resources": request.resources,
                "network_info": {"host": request.host_address, "port": request.api_port},
                "labels": request.metadata
            }
            await container_discovery_service.register_container_manually(container_info)
            
            # Register in database
            db_cluster = register_cluster(
                db,
                container_id=container_id,
                cluster_name=request.container_name,
                agent_id=request.metadata.get("agent_id", container_id),
                host_address=request.host_address,
                api_port=request.api_port,
                agent_type=request.metadata.get("agent_type", "orchestrator_cluster"),
                external_ip=request.metadata.get("external_ip"),
                capabilities=json.dumps(request.capabilities) if request.capabilities else None,
                resources=json.dumps(request.resources) if request.resources else None,
                cluster_metadata=json.dumps(request.metadata) if request.metadata else None
            )

            logger.info(f"Container {container_id} registered successfully in database")

            return {
                "success": True,
                "container_id": container_id,
                "message": "Container registered successfully",
            }
        else:
            raise Exception("Failed to register container")

    except Exception as e:
        logger.error(f"Error registering container: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/containers/{container_id}/heartbeat")
async def container_heartbeat(
    container_id: str,
    request: ContainerHeartbeatRequest,
    user: dict = Depends(get_current_user),
    redis=Depends(get_redis),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Update container heartbeat"""
    try:
        success = await container_registry.heartbeat(
            container_id,
            {
                "health_score": request.health_score,
                "resources": request.resources,
                "active_agents": request.active_agents,
            },
        )

        if success:
            # Update heartbeat in database
            db_success = update_heartbeat(
                db,
                container_id=container_id,
                health_score=request.health_score,
                active_agents=request.active_agents,
                resources=json.dumps(request.resources) if request.resources else None
            )
            
            if db_success:
                logger.debug(f"Updated heartbeat for {container_id} in database")
            
            return {"status": "acknowledged"}
        else:
            raise HTTPException(status_code=404, detail="Container not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/containers/{container_id}")
async def deregister_container(
    container_id: str, user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> Dict[str, Any]:
    """Deregister a container from the cluster"""
    try:
        # Handle any agents on this container first
        await distributed_agent_manager.handle_container_failure(container_id)

        # Deregister from container registry
        success = await container_registry.deregister_container(container_id, reason="manual")

        if success:
            # Unregister from communication hub
            await container_hub.unregister_container(container_id)

            return {"success": True, "message": f"Container {container_id} deregistered"}
        else:
            raise HTTPException(status_code=404, detail="Container not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deregistering container: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Container Discovery Endpoints


@router.post("/discovery/scan")
async def trigger_discovery_scan(
    user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> Dict[str, str]:
    """Trigger an immediate container discovery scan"""
    try:
        await container_discovery_service.force_discovery_scan()
        return {"status": "scan_initiated"}

    except Exception as e:
        logger.error(f"Error triggering discovery scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovery/status")
async def get_discovery_status(
    user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> Dict[str, Any]:
    """Get container discovery status"""
    try:
        stats = container_discovery_service.get_discovery_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting discovery status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovery/containers")
async def get_discovered_containers(
    container_type: Optional[str] = None,
    capability: Optional[str] = None,
    healthy_only: bool = True,
    user: dict = Depends(get_current_user),
    redis=Depends(get_redis),
) -> List[Dict[str, Any]]:
    """Get discovered containers with optional filters"""
    try:
        if capability:
            containers = await container_discovery_service.get_containers_by_capability(capability)
        elif container_type:
            containers = await container_discovery_service.get_containers_by_type(container_type)
        elif healthy_only:
            containers = await container_discovery_service.get_healthy_containers()
        else:
            containers = await container_discovery_service.get_all_containers()

        # Containers are already dict format
        return containers

    except Exception as e:
        logger.error(f"Error getting discovered containers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent Deployment Endpoints


@router.post("/agents/deploy")
async def deploy_agent(
    request: AgentDeploymentRequestAPI,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    redis=Depends(get_redis),
) -> Dict[str, Any]:
    """Deploy an agent to the cluster"""
    try:
        # Convert to internal request model
        deployment_request = AgentDeploymentRequest(
            agent_type=request.agent_type,
            agent_config=request.agent_config,
            resource_requirements=request.resource_requirements,
            preferred_container=request.preferred_container,
            deployment_strategy=AgentDeploymentStrategy(request.deployment_strategy),
            constraints=request.constraints,
        )

        # Deploy agent
        result = await distributed_agent_manager.deploy_agent(deployment_request)

        if result["success"]:
            logger.info(f"Agent deployed successfully: {result['agent_id']}")
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Deployment failed"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/migrate")
async def migrate_agent(
    agent_id: str,
    request: AgentMigrationRequestAPI,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    redis=Depends(get_redis),
) -> Dict[str, Any]:
    """Migrate an agent to a different container"""
    try:
        # Ensure agent_id matches
        if request.agent_id != agent_id:
            raise HTTPException(status_code=400, detail="Agent ID mismatch")

        # Convert to internal request model
        migration_request = AgentMigrationRequest(
            agent_id=agent_id,
            target_container_id=request.target_container_id,
            reason=request.reason,
            preserve_state=request.preserve_state,
        )

        # Migrate agent
        result = await distributed_agent_manager.migrate_agent(migration_request)

        if result["success"]:
            logger.info(f"Agent {agent_id} migrated successfully")
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Migration failed"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error migrating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/deployments")
async def get_agent_deployments(
    user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> Dict[str, str]:
    """Get all agent deployments in the cluster"""
    try:
        deployments = await distributed_agent_manager.get_all_deployments()
        return deployments

    except Exception as e:
        logger.error(f"Error getting agent deployments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/deployment")
async def get_agent_deployment(
    agent_id: str, user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> Dict[str, Any]:
    """Get deployment information for a specific agent"""
    try:
        deployment = await distributed_agent_manager.get_agent_deployment(agent_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="Agent deployment not found")

        return deployment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cluster Management Endpoints


@router.post("/actions")
async def perform_cluster_action(
    request: ClusterActionRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    redis=Depends(get_redis),
) -> Dict[str, Any]:
    """Perform a cluster-wide action"""
    try:
        if request.action == "rebalance":
            # Rebalance agents across containers
            result = await distributed_agent_manager.rebalance_agents()
            return result

        elif request.action == "health_check":
            # Perform cluster-wide health check
            containers = await container_registry.get_all_containers()
            health_status = {
                "healthy": len([c for c in containers if c.get("status") == "active"]),
                "unhealthy": len([c for c in containers if c.get("status") != "active"]),
                "total": len(containers),
            }
            return {
                "action": "health_check",
                "status": health_status,
                "timestamp": datetime.utcnow().isoformat(),
            }

        elif request.action == "optimize":
            # Optimize cluster resources
            # This could involve moving agents to better containers based on resource usage
            return {
                "action": "optimize",
                "status": "not_implemented",
                "message": "Cluster optimization not yet implemented",
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing cluster action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Communication Hub Endpoints


@router.get("/communication/stats")
async def get_communication_stats(
    user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> Dict[str, Any]:
    """Get communication hub statistics"""
    try:
        stats = await container_hub.get_hub_statistics()
        return stats

    except Exception as e:
        logger.error(f"Error getting communication stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/communication/message")
async def send_cluster_message(
    source_container: str,
    target_container: Optional[str],
    message_type: str,
    payload: Dict[str, Any],
    user: dict = Depends(get_current_user),
    redis=Depends(get_redis),
) -> Dict[str, str]:
    """Send a message through the communication hub"""
    try:
        if message_type == "command":
            message_id = await container_hub.send_command(
                source_container,
                target_container,
                payload.get("command", ""),
                payload.get("params", {}),
            )
        elif message_type == "query":
            message_id = await container_hub.send_query(
                source_container,
                target_container,
                payload.get("query", ""),
                payload.get("params", {}),
            )
        elif message_type == "event":
            await container_hub.send_event(
                source_container, payload.get("event_type", ""), payload.get("event_data", {})
            )
            message_id = "event_broadcast"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown message type: {message_type}")

        return {"message_id": message_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending cluster message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/distribution")
async def get_cluster_distribution(
    user: dict = Depends(get_current_user), redis=Depends(get_redis)
) -> Dict[str, Any]:
    """Get agent distribution across the cluster"""
    try:
        containers = await container_registry.get_all_containers()
        deployments = await distributed_agent_manager.get_all_deployments()

        # Calculate distribution
        distribution = {}
        for container in containers:
            container_id = container["container_id"]
            agents = await distributed_agent_manager.get_container_agents(container_id)
            distribution[container_id] = {
                "container_name": container.get("container_name"),
                "agent_count": len(agents),
                "agents": agents,
                "health_score": container.get("health_score", 0),
                "resources": container.get("resources", {}),
            }

        return {
            "total_containers": len(containers),
            "total_agents": len(deployments),
            "distribution": distribution,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting cluster distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/stream")
async def stream_cluster_events(user: dict = Depends(get_current_user), redis=Depends(get_redis)):
    """Stream cluster events (WebSocket endpoint placeholder)"""
    # This would typically be implemented as a WebSocket endpoint
    # For now, return a message indicating WebSocket support is needed
    return {
        "message": "Event streaming requires WebSocket connection",
        "websocket_endpoint": "/ws/cluster/events",
    }
