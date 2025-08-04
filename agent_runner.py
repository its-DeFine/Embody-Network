#!/usr/bin/env python3
"""
Dedicated Agent Container Runner
Runs a single agent in its own container with proper lifecycle management
and automatic registration with the central manager.
"""
import asyncio
import json
import logging
import os
import sys
import signal
import socket
from datetime import datetime
from typing import Dict, Any, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI
from uvicorn import Config, Server
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentContainer:
    """Dedicated agent container with lifecycle management and cluster registration"""
    
    def __init__(self):
        self.agent_id = os.getenv("AGENT_ID", "unknown")
        self.agent_type = os.getenv("AGENT_TYPE", "trading")
        self.agent_config = json.loads(os.getenv("AGENT_CONFIG", "{}"))
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.port = int(os.getenv("AGENT_PORT", "8001"))
        self.central_manager_url = os.getenv("CENTRAL_MANAGER_URL", "http://app:8000")
        self.container_name = os.getenv("CONTAINER_NAME", socket.gethostname())
        
        self.redis = None
        self.app = FastAPI(title=f"Agent {self.agent_id}")
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.container_id: Optional[str] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"🤖 Agent Container Initialized:")
        logger.info(f"   Agent ID: {self.agent_id}")
        logger.info(f"   Agent Type: {self.agent_type}")
        logger.info(f"   Port: {self.port}")
        logger.info(f"   Redis: {self.redis_url}")
        logger.info(f"   Central Manager: {self.central_manager_url}")
    
    async def start(self):
        """Start the agent container"""
        try:
            # Connect to Redis
            self.redis = aioredis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("✅ Connected to Redis")
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession()
            
            # Register with central manager
            await self._register_with_cluster()
            
            # Register agent endpoints
            self._setup_endpoints()
            
            # Update agent status in Redis
            await self._update_status("running")
            
            # Start metrics tracking
            asyncio.create_task(self._metrics_tracker())
            
            # Start agent logic
            asyncio.create_task(self._agent_logic_loop())
            
            # Start heartbeat to central manager
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Start FastAPI server
            config = Config(
                app=self.app,
                host="0.0.0.0",
                port=self.port,
                log_level="info"
            )
            server = Server(config)
            
            self.running = True
            logger.info(f"🚀 Agent {self.agent_id} started successfully on port {self.port}")
            
            await server.serve()
            
        except Exception as e:
            logger.error(f"❌ Failed to start agent: {e}")
            await self._update_status("failed", str(e))
            sys.exit(1)
    
    def _setup_endpoints(self):
        """Setup FastAPI endpoints for agent"""
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.get("/status")
        async def get_status():
            metrics = await self.redis.hgetall(f"agent:{self.agent_id}:metrics")
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": "running",
                "config": self.agent_config,
                "metrics": {
                    "tasks_completed": int(metrics.get(b"tasks_completed", 0)) if metrics else 0,
                    "uptime_seconds": int(metrics.get(b"uptime_seconds", 0)) if metrics else 0,
                    "last_activity": metrics.get(b"last_activity", b"").decode() if metrics else ""
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.post("/task")
        async def execute_task(task: Dict[str, Any]):
            """Execute a task on this agent"""
            try:
                result = await self._execute_task(task)
                await self._increment_metric("tasks_completed")
                await self._update_metric("last_activity", datetime.utcnow().isoformat())
                
                return {
                    "status": "completed",
                    "task_id": task.get("id", "unknown"),
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                return {
                    "status": "failed",
                    "task_id": task.get("id", "unknown"),
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        @self.app.post("/stop")
        async def stop_agent():
            """Stop the agent gracefully"""
            logger.info(f"🛑 Agent {self.agent_id} stop requested")
            await self._update_status("stopping")
            asyncio.create_task(self._graceful_shutdown())
            return {"message": "Agent stopping"}
    
    async def _agent_logic_loop(self):
        """Main agent logic loop"""
        logger.info(f"🔄 Starting agent logic loop for {self.agent_type} agent")
        
        while self.running:
            try:
                # Agent-specific logic based on type
                if self.agent_type == "trading":
                    await self._trading_logic()
                elif self.agent_type == "analysis":
                    await self._analysis_logic()
                elif self.agent_type == "risk":
                    await self._risk_logic()
                else:
                    await self._generic_logic()
                
                # Update last activity
                await self._update_metric("last_activity", datetime.utcnow().isoformat())
                
                # Sleep between iterations
                await asyncio.sleep(30)  # 30 second cycle
                
            except Exception as e:
                logger.error(f"Agent logic error: {e}")
                await asyncio.sleep(60)  # Longer sleep on error
    
    async def _trading_logic(self):
        """Trading agent specific logic"""
        logger.debug("🔸 Trading agent cycle")
        
        # Simulate trading decision making
        await asyncio.sleep(1)
        
        # Check for trading signals
        # Simulate market analysis
        # Execute trades if conditions met
        
        # For demo, just log activity
        await self._increment_metric("trading_cycles")
    
    async def _analysis_logic(self):
        """Analysis agent specific logic"""
        logger.debug("🔸 Analysis agent cycle")
        
        # Simulate market analysis
        await asyncio.sleep(1)
        
        # Analyze market conditions
        # Generate insights
        # Update analysis results
        
        await self._increment_metric("analysis_cycles")
    
    async def _risk_logic(self):
        """Risk management agent specific logic"""
        logger.debug("🔸 Risk agent cycle")
        
        # Simulate risk assessment
        await asyncio.sleep(1)
        
        # Monitor portfolio risk
        # Check exposure limits
        # Generate risk alerts
        
        await self._increment_metric("risk_checks")
    
    async def _generic_logic(self):
        """Generic agent logic"""
        logger.debug("🔸 Generic agent cycle")
        await asyncio.sleep(1)
        await self._increment_metric("generic_cycles")
    
    async def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task"""
        task_type = task.get("type", "unknown")
        logger.info(f"📋 Executing task: {task_type}")
        
        # Simulate task execution
        await asyncio.sleep(2)
        
        return {
            "task_type": task_type,
            "execution_time": 2.0,
            "status": "completed",
            "agent_type": self.agent_type
        }
    
    async def _metrics_tracker(self):
        """Track agent metrics"""
        start_time = datetime.utcnow()
        
        while self.running:
            try:
                # Update uptime
                uptime_seconds = (datetime.utcnow() - start_time).total_seconds()
                await self._update_metric("uptime_seconds", int(uptime_seconds))
                
                # Sleep for 10 seconds
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Metrics tracking error: {e}")
                await asyncio.sleep(30)
    
    async def _update_status(self, status: str, error: str = None):
        """Update agent status in Redis"""
        try:
            agent_data = {
                "id": self.agent_id,
                "type": self.agent_type,
                "status": status,
                "container_id": f"real-{self.agent_id}",
                "config": self.agent_config,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if error:
                agent_data["error"] = error
            
            await self.redis.set(f"agent:{self.agent_id}", json.dumps(agent_data))
            logger.info(f"📊 Agent status updated: {status}")
            
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
    
    async def _update_metric(self, key: str, value: Any):
        """Update agent metric"""
        try:
            await self.redis.hset(f"agent:{self.agent_id}:metrics", key, str(value))
        except Exception as e:
            logger.error(f"Failed to update metric {key}: {e}")
    
    async def _increment_metric(self, key: str):
        """Increment agent metric"""
        try:
            await self.redis.hincrby(f"agent:{self.agent_id}:metrics", key, 1)
        except Exception as e:
            logger.error(f"Failed to increment metric {key}: {e}")
    
    async def _graceful_shutdown(self):
        """Gracefully shutdown the agent"""
        logger.info(f"🔄 Graceful shutdown initiated for agent {self.agent_id}")
        
        # Wait a bit for current operations to complete
        await asyncio.sleep(2)
        
        # Update status
        await self._update_status("stopped")
        
        # Stop the main loop
        self.running = False
        
        # Close Redis connection
        if self.redis:
            await self.redis.close()
        
        logger.info(f"✅ Agent {self.agent_id} shutdown complete")
        sys.exit(0)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"🛑 Received signal {signum}, initiating shutdown")
        asyncio.create_task(self._graceful_shutdown())
    
    async def _register_with_cluster(self):
        """Register this container with the central manager"""
        try:
            # Get container's host IP
            hostname = socket.gethostname()
            host_ip = socket.gethostbyname(hostname)
            
            # Prepare registration data
            registration_data = {
                "container_name": self.container_name,
                "host_address": host_ip,
                "api_endpoint": f"http://{host_ip}:{self.port}",
                "capabilities": ["agent_runner"],
                "resources": {
                    "cpu_count": os.cpu_count() or 1,
                    "memory_limit": 2 * 1024 * 1024 * 1024,  # 2GB default
                },
                "metadata": {
                    "agent_type": self.agent_type,
                    "agent_id": self.agent_id,
                    "version": "1.0.0"
                }
            }
            
            # Authenticate first (if needed)
            auth_data = {
                "email": "admin@trading.system",
                "password": os.getenv("ADMIN_PASSWORD", "default-admin-password-change-in-production-32chars!")
            }
            
            async with self.session.post(
                f"{self.central_manager_url}/api/v1/auth/login",
                json=auth_data
            ) as resp:
                if resp.status == 200:
                    auth_response = await resp.json()
                    token = auth_response.get("access_token")
                    
                    # Register container
                    headers = {"Authorization": f"Bearer {token}"}
                    async with self.session.post(
                        f"{self.central_manager_url}/api/v1/cluster/containers/register",
                        json=registration_data,
                        headers=headers
                    ) as reg_resp:
                        if reg_resp.status in [200, 201]:
                            reg_data = await reg_resp.json()
                            self.container_id = reg_data.get("container_id")
                            logger.info(f"✅ Registered with cluster as container {self.container_id}")
                        else:
                            logger.warning(f"Failed to register with cluster: {reg_resp.status}")
                else:
                    logger.warning(f"Failed to authenticate with central manager: {resp.status}")
                    
        except Exception as e:
            logger.warning(f"Could not register with cluster: {e}")
            # Continue running even if registration fails
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to central manager"""
        heartbeat_interval = 30  # seconds
        
        while self.running:
            try:
                await asyncio.sleep(heartbeat_interval)
                
                if self.container_id and self.session:
                    # Get metrics
                    metrics = await self.redis.hgetall(f"agent:{self.agent_id}:metrics")
                    
                    heartbeat_data = {
                        "container_id": self.container_id,
                        "health_score": 100,  # Simple health score
                        "resources": {
                            "cpu_usage_percent": 20,  # Would calculate real usage
                            "memory_percent": 30
                        },
                        "agent_count": 1,
                        "metadata": {
                            "agent_id": self.agent_id,
                            "tasks_completed": int(metrics.get(b"tasks_completed", 0)) if metrics else 0
                        }
                    }
                    
                    # Send heartbeat (would need auth token in real implementation)
                    async with self.session.post(
                        f"{self.central_manager_url}/api/v1/cluster/containers/{self.container_id}/heartbeat",
                        json=heartbeat_data
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"Heartbeat failed: {resp.status}")
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(heartbeat_interval)

async def main():
    """Main entry point"""
    agent = AgentContainer()
    await agent.start()

if __name__ == "__main__":
    asyncio.run(main())