import os
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import docker
import git
from pathlib import Path
import yaml
import hashlib

# Import shared modules
import sys
sys.path.append('/app')
from shared.events.event_types import Event, EventType
from shared.utils.message_queue import get_message_queue

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UpdatePipeline:
    """Automated update pipeline for agent deployments"""
    
    def __init__(self, docker_client: docker.DockerClient):
        self.docker = docker_client
        self.repo_path = Path("/app/deployments/repo")
        self.config_path = Path("/app/deployments/config")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_url = os.getenv("REPO_URL", "https://github.com/your-org/autogen-agents.git")
        self.mq = None
        self.running = True
        self.deployment_history: List[Dict[str, Any]] = []
        
    async def initialize(self, mq):
        """Initialize the update pipeline"""
        self.mq = mq
        
        # Clone or update repository
        await self._setup_repository()
        
        # Start watching for updates
        asyncio.create_task(self._watch_for_updates())
        
        # Subscribe to deployment requests
        await mq.receive_direct_messages(
            "update-pipeline",
            self._handle_deployment_request
        )
        
        logger.info("Update Pipeline initialized")
    
    async def _setup_repository(self):
        """Setup git repository for deployments"""
        try:
            if not self.repo_path.exists():
                self.repo_path.mkdir(parents=True, exist_ok=True)
                
                # Clone repository
                if self.github_token:
                    auth_url = self.repo_url.replace("https://", f"https://{self.github_token}@")
                    git.Repo.clone_from(auth_url, self.repo_path)
                else:
                    git.Repo.clone_from(self.repo_url, self.repo_path)
                
                logger.info(f"Cloned repository to {self.repo_path}")
            else:
                # Pull latest changes
                repo = git.Repo(self.repo_path)
                origin = repo.remotes.origin
                origin.pull()
                logger.info("Updated repository with latest changes")
                
        except Exception as e:
            logger.error(f"Error setting up repository: {e}")
    
    async def _watch_for_updates(self):
        """Watch for updates in the repository"""
        while self.running:
            try:
                # Check for updates every 5 minutes
                await asyncio.sleep(300)
                
                repo = git.Repo(self.repo_path)
                current_commit = repo.head.commit.hexsha
                
                # Fetch latest changes
                origin = repo.remotes.origin
                origin.fetch()
                
                # Check if there are new commits
                remote_commit = origin.refs.main.commit.hexsha
                
                if current_commit != remote_commit:
                    logger.info(f"New commits detected: {current_commit[:8]} -> {remote_commit[:8]}")
                    
                    # Pull changes
                    origin.pull()
                    
                    # Process updates
                    await self._process_updates(current_commit, remote_commit)
                    
            except Exception as e:
                logger.error(f"Error watching for updates: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _process_updates(self, old_commit: str, new_commit: str):
        """Process repository updates"""
        try:
            repo = git.Repo(self.repo_path)
            
            # Get changed files
            diff = repo.git.diff(f"{old_commit}..{new_commit}", name_only=True)
            changed_files = diff.split('\n') if diff else []
            
            updates = {
                "agent_configs": [],
                "docker_images": [],
                "shared_modules": [],
                "api_changes": []
            }
            
            # Categorize changes
            for file_path in changed_files:
                if "customer_agents/" in file_path:
                    updates["agent_configs"].append(file_path)
                elif "Dockerfile" in file_path:
                    updates["docker_images"].append(file_path)
                elif "shared/" in file_path:
                    updates["shared_modules"].append(file_path)
                elif "services/api-gateway" in file_path:
                    updates["api_changes"].append(file_path)
            
            # Process updates by category
            if updates["docker_images"] or updates["shared_modules"]:
                await self._rebuild_images(updates)
            
            if updates["agent_configs"]:
                await self._update_agent_configs(updates["agent_configs"])
            
            if updates["api_changes"]:
                await self._update_api_gateway()
            
            # Send deployment completed event
            await self._send_deployment_event(EventType.DEPLOYMENT_COMPLETED, {
                "old_commit": old_commit[:8],
                "new_commit": new_commit[:8],
                "updates": updates,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error processing updates: {e}")
            await self._send_deployment_event(EventType.DEPLOYMENT_FAILED, {
                "error": str(e),
                "old_commit": old_commit[:8],
                "new_commit": new_commit[:8]
            })
    
    async def _rebuild_images(self, updates: Dict[str, List[str]]):
        """Rebuild Docker images based on changes"""
        try:
            images_to_rebuild = set()
            
            # Determine which images need rebuilding
            if any("shared/" in f for f in updates["shared_modules"]):
                # Rebuild all images if shared modules changed
                images_to_rebuild.update(["api-gateway", "agent-manager", "autogen-agent"])
            
            for dockerfile in updates["docker_images"]:
                if "api-gateway" in dockerfile:
                    images_to_rebuild.add("api-gateway")
                elif "agent-manager" in dockerfile:
                    images_to_rebuild.add("agent-manager")
                elif "customer_agents" in dockerfile:
                    images_to_rebuild.add("autogen-agent")
            
            # Build images
            for image_name in images_to_rebuild:
                await self._build_image(image_name)
            
            # Update running containers
            await self._update_containers(list(images_to_rebuild))
            
        except Exception as e:
            logger.error(f"Error rebuilding images: {e}")
            raise
    
    async def _build_image(self, image_name: str):
        """Build a Docker image"""
        try:
            build_contexts = {
                "api-gateway": "services/api-gateway",
                "agent-manager": "services/agent-manager",
                "autogen-agent": "customer_agents/base"
            }
            
            context_path = self.repo_path / build_contexts.get(image_name, "")
            
            logger.info(f"Building image: {image_name}")
            
            # Build image with versioning
            version = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            tag = f"{image_name}:{version}"
            latest_tag = f"{image_name}:latest"
            
            # Build image
            image, build_logs = self.docker.images.build(
                path=str(context_path),
                tag=tag,
                rm=True,
                pull=True
            )
            
            # Tag as latest
            image.tag(latest_tag)
            
            # Log build output
            for log in build_logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())
            
            logger.info(f"Successfully built image: {tag}")
            
            # Store build info
            self.deployment_history.append({
                "image": image_name,
                "version": version,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Error building image {image_name}: {e}")
            raise
    
    async def _update_containers(self, image_names: List[str]):
        """Update running containers with new images"""
        try:
            for image_name in image_names:
                # Find containers using this image
                containers = self.docker.containers.list(
                    filters={"ancestor": f"{image_name}:latest"}
                )
                
                for container in containers:
                    logger.info(f"Updating container: {container.name}")
                    
                    # Get container config
                    config = container.attrs['Config']
                    host_config = container.attrs['HostConfig']
                    
                    # Stop and remove old container
                    container.stop(timeout=30)
                    container.remove()
                    
                    # Create new container with same config
                    new_container = self.docker.containers.run(
                        image=f"{image_name}:latest",
                        name=container.name,
                        environment=config['Env'],
                        network_mode=host_config['NetworkMode'],
                        volumes=host_config['Binds'],
                        detach=True,
                        restart_policy=host_config['RestartPolicy']
                    )
                    
                    logger.info(f"Updated container {container.name} with new image")
                    
        except Exception as e:
            logger.error(f"Error updating containers: {e}")
            raise
    
    async def _update_agent_configs(self, config_files: List[str]):
        """Update agent configurations"""
        try:
            for config_file in config_files:
                config_path = self.repo_path / config_file
                
                if config_path.exists() and config_path.suffix in ['.json', '.yaml', '.yml']:
                    # Read configuration
                    with open(config_path, 'r') as f:
                        if config_path.suffix == '.json':
                            config = json.load(f)
                        else:
                            config = yaml.safe_load(f)
                    
                    # Extract agent info from path
                    parts = Path(config_file).parts
                    if len(parts) >= 3 and parts[0] == "customer_agents":
                        customer_id = parts[1]
                        agent_id = config.get("agent_id")
                        
                        if agent_id:
                            # Send update to agent manager
                            await self.mq.send_direct_message(
                                target="agent-manager",
                                message_type="agent.update_config",
                                payload={
                                    "agent_id": agent_id,
                                    "customer_id": customer_id,
                                    "config": config
                                }
                            )
                            
                            logger.info(f"Updated configuration for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Error updating agent configs: {e}")
            raise
    
    async def _update_api_gateway(self):
        """Update API Gateway with rolling deployment"""
        try:
            # Find API Gateway containers
            containers = self.docker.containers.list(
                filters={"label": "service=api-gateway"}
            )
            
            if not containers:
                logger.warning("No API Gateway containers found")
                return
            
            # Perform rolling update
            for i, container in enumerate(containers):
                logger.info(f"Updating API Gateway container {i+1}/{len(containers)}")
                
                # Create new container before stopping old one
                new_container = self.docker.containers.run(
                    image="api-gateway:latest",
                    name=f"{container.name}-new",
                    environment=container.attrs['Config']['Env'],
                    network_mode=container.attrs['HostConfig']['NetworkMode'],
                    detach=True
                )
                
                # Wait for new container to be healthy
                await self._wait_for_health(new_container)
                
                # Stop old container
                container.stop(timeout=30)
                container.remove()
                
                # Rename new container
                new_container.rename(container.name)
                
                # Wait before updating next container
                if i < len(containers) - 1:
                    await asyncio.sleep(30)
            
            logger.info("API Gateway update completed")
            
        except Exception as e:
            logger.error(f"Error updating API Gateway: {e}")
            raise
    
    async def _wait_for_health(self, container, timeout: int = 60):
        """Wait for container to be healthy"""
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).seconds < timeout:
            container.reload()
            
            # Check if container has health check
            health = container.attrs.get('State', {}).get('Health', {})
            status = health.get('Status', 'none')
            
            if status == 'healthy':
                return True
            elif status == 'unhealthy':
                raise Exception(f"Container {container.name} is unhealthy")
            
            await asyncio.sleep(2)
        
        raise Exception(f"Container {container.name} health check timeout")
    
    async def _handle_deployment_request(self, message: Dict[str, Any]):
        """Handle manual deployment requests"""
        try:
            deployment_type = message.get("deployment_type")
            target = message.get("target")
            
            if deployment_type == "rollback":
                await self._rollback_deployment(target)
            elif deployment_type == "deploy_branch":
                await self._deploy_branch(message.get("branch", "main"))
            elif deployment_type == "rebuild":
                await self._rebuild_service(target)
            
        except Exception as e:
            logger.error(f"Error handling deployment request: {e}")
    
    async def _rollback_deployment(self, target: str):
        """Rollback to previous deployment"""
        try:
            # Find previous successful deployment
            previous_deployments = [
                d for d in self.deployment_history 
                if d["image"] == target and d["status"] == "success"
            ]
            
            if len(previous_deployments) < 2:
                raise Exception("No previous deployment found for rollback")
            
            previous_version = previous_deployments[-2]["version"]
            
            # Update containers to previous version
            containers = self.docker.containers.list(
                filters={"ancestor": f"{target}:latest"}
            )
            
            for container in containers:
                # Stop current container
                container.stop(timeout=30)
                container.remove()
                
                # Start container with previous version
                self.docker.containers.run(
                    image=f"{target}:{previous_version}",
                    name=container.name,
                    environment=container.attrs['Config']['Env'],
                    network_mode=container.attrs['HostConfig']['NetworkMode'],
                    volumes=container.attrs['HostConfig']['Binds'],
                    detach=True,
                    restart_policy=container.attrs['HostConfig']['RestartPolicy']
                )
            
            logger.info(f"Rolled back {target} to version {previous_version}")
            
        except Exception as e:
            logger.error(f"Error rolling back deployment: {e}")
            raise
    
    async def _deploy_branch(self, branch: str):
        """Deploy from a specific branch"""
        try:
            repo = git.Repo(self.repo_path)
            
            # Checkout branch
            repo.git.checkout(branch)
            
            # Pull latest changes
            origin = repo.remotes.origin
            origin.pull()
            
            # Rebuild all images
            await self._rebuild_images({
                "docker_images": ["all"],
                "shared_modules": ["all"]
            })
            
            logger.info(f"Deployed branch: {branch}")
            
        except Exception as e:
            logger.error(f"Error deploying branch: {e}")
            raise
    
    async def _rebuild_service(self, service: str):
        """Rebuild a specific service"""
        try:
            await self._build_image(service)
            await self._update_containers([service])
            
            logger.info(f"Rebuilt service: {service}")
            
        except Exception as e:
            logger.error(f"Error rebuilding service: {e}")
            raise
    
    async def _send_deployment_event(self, event_type: EventType, data: Dict[str, Any]):
        """Send deployment event"""
        event = Event(
            event_id=f"deployment-{datetime.utcnow().timestamp()}",
            event_type=event_type,
            source="update-pipeline",
            data=data
        )
        await self.mq.publish_event(event)
    
    async def cleanup(self):
        """Cleanup resources"""
        self.running = False


async def main():
    """Main entry point"""
    # Initialize Docker client
    # docker.from_env() will use DOCKER_HOST environment variable
    docker_client = docker.from_env()
    
    # Create update pipeline
    pipeline = UpdatePipeline(docker_client)
    
    # Connect to message queue and initialize
    async with get_message_queue() as mq:
        await pipeline.initialize(mq)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Update Pipeline")
        finally:
            await pipeline.cleanup()


if __name__ == "__main__":
    asyncio.run(main())