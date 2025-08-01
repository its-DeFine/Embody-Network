"""
Central Orchestrator for Agent Coordination

This module implements the core orchestration logic that enables agents to work
together effectively. It provides:

- Event-driven communication between agents
- Intelligent task routing based on agent capabilities and availability
- Health monitoring with automatic failover
- Team coordination patterns (consensus, parallel, sequential)
- Workflow management for complex multi-agent tasks

The orchestrator acts as the central nervous system of the platform, ensuring
that agents collaborate efficiently while maintaining system reliability.

Example:
    >>> orchestrator = Orchestrator()
    >>> await orchestrator.start()
    >>> await orchestrator.publish_event(Event("task.created", "api", task_data))
"""
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .dependencies import get_redis

logger = logging.getLogger(__name__)

class Event:
    """Event for inter-agent communication"""
    def __init__(self, event_type: str, source: str, data: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.type = event_type
        self.source = source
        self.data = data
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp
        }

class Orchestrator:
    """Central orchestrator for agent coordination and task routing"""
    
    def __init__(self):
        self.redis = None
        self.running = False
        self.event_handlers = {
            "agent.started": self._handle_agent_started,
            "agent.stopped": self._handle_agent_stopped,
            "task.created": self._handle_task_created,
            "task.completed": self._handle_task_completed,
            "team.coordinate": self._handle_team_coordination,
            "market.signal": self._handle_market_signal
        }
        
    async def initialize(self):
        """Initialize the orchestrator"""
        self.redis = await get_redis()
        logger.info("Orchestrator initialized")
        
    async def start(self):
        """Start the orchestrator event loop"""
        await self.initialize()
        self.running = True
        
        # Start event processing
        asyncio.create_task(self._process_events())
        
        # Start health monitoring
        asyncio.create_task(self._monitor_agents())
        
        logger.info("Orchestrator started")
        
    async def stop(self):
        """Stop the orchestrator"""
        self.running = False
        logger.info("Orchestrator stopped")
        
    async def publish_event(self, event: Event):
        """Publish an event for all agents"""
        await self.redis.lpush("events:global", json.dumps(event.to_dict()))
        
        # Also publish to specific agent queues if needed
        if event.type.startswith("task."):
            agent_id = event.data.get("agent_id")
            if agent_id:
                await self.redis.lpush(f"agent:{agent_id}:tasks", json.dumps(event.data))
                
    async def _process_events(self):
        """Main event processing loop"""
        while self.running:
            try:
                # Get next event
                result = await self.redis.blpop("events:global", timeout=1)
                if not result:
                    continue
                    
                _, event_data = result
                event = json.loads(event_data)
                
                # Route to appropriate handler
                event_type = event.get("type")
                handler = self.event_handlers.get(event_type)
                
                if handler:
                    await handler(event)
                else:
                    logger.debug(f"No handler for event type: {event_type}")
                    
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                await asyncio.sleep(1)
                
    async def _monitor_agents(self):
        """Monitor agent health and status"""
        while self.running:
            try:
                # Get all agents
                agent_keys = await self.redis.keys("agent:*:status")
                
                for key in agent_keys:
                    status_data = await self.redis.hgetall(key)
                    if status_data:
                        # Check last update time
                        last_update = float(status_data.get(b'timestamp', 0))
                        current_time = asyncio.get_event_loop().time()
                        
                        # If no update for 60 seconds, mark as unhealthy
                        if current_time - last_update > 60:
                            agent_id = key.decode().split(':')[1]
                            await self._mark_agent_unhealthy(agent_id)
                            
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring agents: {e}")
                await asyncio.sleep(30)
                
    async def _handle_agent_started(self, event: Dict):
        """Handle agent started event"""
        agent_id = event["data"]["agent_id"]
        logger.info(f"Agent {agent_id} started")
        
        # Notify other agents
        await self.publish_event(Event(
            "agent.joined",
            "orchestrator",
            {"agent_id": agent_id, "timestamp": datetime.utcnow().isoformat()}
        ))
        
    async def _handle_agent_stopped(self, event: Dict):
        """Handle agent stopped event"""
        agent_id = event["data"]["agent_id"]
        logger.info(f"Agent {agent_id} stopped")
        
        # Reassign any pending tasks
        await self._reassign_agent_tasks(agent_id)
        
    async def _handle_task_created(self, event: Dict):
        """Route task to appropriate agent"""
        task = event["data"]
        task_type = task.get("type")
        
        # Find best agent for the task
        agent_id = await self._find_best_agent(task_type)
        
        if agent_id:
            task["assigned_to"] = agent_id
            # Save task state
            await self.redis.set(f"task:{task['id']}", json.dumps(task))
            # Send to agent via pub/sub
            await self.redis.publish(f"agent:{agent_id}:tasks", json.dumps(task))
            logger.info(f"Task {task['id']} assigned to agent {agent_id}")
        else:
            # No agent available, queue for later
            await self.redis.lpush("tasks:pending", json.dumps(task))
            logger.warning(f"No agent available for task {task['id']}")
            
    async def _handle_task_completed(self, event: Dict):
        """Handle task completion"""
        task_id = event["data"]["task_id"]
        result = event["data"]["result"]
        
        logger.info(f"Task {task_id} completed")
        
        # Check if this triggers other tasks
        await self._check_task_dependencies(task_id, result)
        
    async def _handle_team_coordination(self, event: Dict):
        """Coordinate tasks between team members"""
        team_id = event["data"]["team_id"]
        coordination_type = event["data"]["type"]
        
        # Get team members
        team_data = await self.redis.get(f"team:{team_id}")
        if not team_data:
            return
            
        team = json.loads(team_data)
        agent_ids = team.get("agent_ids", [])
        
        if coordination_type == "consensus":
            # All agents need to agree
            await self._coordinate_consensus(team_id, agent_ids, event["data"])
        elif coordination_type == "parallel":
            # Distribute work among agents
            await self._coordinate_parallel(team_id, agent_ids, event["data"])
        elif coordination_type == "sequential":
            # Chain tasks through agents
            await self._coordinate_sequential(team_id, agent_ids, event["data"])
            
    async def _handle_market_signal(self, event: Dict):
        """Handle market signals and route to relevant agents"""
        signal = event["data"]
        
        # Find all trading and risk agents
        agent_keys = await self.redis.keys("agent:*")
        
        for key in agent_keys:
            agent_data = await self.redis.get(key)
            if agent_data:
                agent = json.loads(agent_data)
                if agent["type"] in ["trading", "risk", "analysis"]:
                    # Send signal to agent
                    await self.redis.lpush(
                        f"agent:{agent['id']}:signals",
                        json.dumps(signal)
                    )
                    
    async def _find_best_agent(self, task_type: str) -> Optional[str]:
        """Find the best available agent for a task type"""
        # Map task types to agent types (flexible mapping)
        task_agent_map = {
            "analysis": ["analysis", "trading"],
            "trading": ["trading"],
            "risk": ["risk", "analysis"],
            "portfolio": ["portfolio", "trading", "analysis"]
        }
        
        # Get suitable agent types, default to any type if not mapped
        suitable_types = task_agent_map.get(task_type, ["analysis", "trading", "risk", "portfolio"])
        
        # Find running agents of suitable types
        agent_keys = await self.redis.keys("agent:*")
        candidates = []
        
        for key in agent_keys:
            # Skip status and task keys
            key_str = key.decode() if isinstance(key, bytes) else key
            if ":status" in key_str or ":tasks" in key_str:
                continue
                
            agent_data = await self.redis.get(key)
            if agent_data:
                agent = json.loads(agent_data)
                if agent.get("status") == "running" and agent.get("type") in suitable_types:
                    # For now, just return the first available agent
                    return agent["id"]
                    
        # No suitable agent found
        return None
        
    async def _reassign_agent_tasks(self, agent_id: str):
        """Reassign tasks from a stopped agent"""
        # Get pending tasks
        tasks = []
        while True:
            task_data = await self.redis.lpop(f"agent:{agent_id}:tasks")
            if not task_data:
                break
            tasks.append(json.loads(task_data))
            
        # Reassign each task
        for task in tasks:
            await self.publish_event(Event(
                "task.created",
                "orchestrator",
                task
            ))
            
    async def _check_task_dependencies(self, task_id: str, result: Any):
        """Check if completed task triggers other tasks"""
        # This could be extended with a workflow engine
        # For now, simple rule-based triggers
        
        if "buy_signal" in str(result):
            # Trigger risk assessment
            await self.publish_event(Event(
                "task.created",
                "orchestrator",
                {
                    "id": str(uuid.uuid4()),
                    "type": "assess_risk",
                    "triggered_by": task_id,
                    "data": {"signal": result}
                }
            ))
            
    async def _coordinate_consensus(self, team_id: str, agent_ids: List[str], data: Dict):
        """Coordinate consensus decision among agents"""
        consensus_id = str(uuid.uuid4())
        
        # Send proposal to all agents
        for agent_id in agent_ids:
            await self.redis.lpush(f"agent:{agent_id}:tasks", json.dumps({
                "id": consensus_id,
                "type": "consensus_vote",
                "team_id": team_id,
                "proposal": data["proposal"]
            }))
            
        # Wait for responses (simplified - in production use proper voting mechanism)
        await asyncio.sleep(5)
        
    async def _coordinate_parallel(self, team_id: str, agent_ids: List[str], data: Dict):
        """Distribute work in parallel"""
        tasks = data.get("tasks", [])
        
        # Round-robin distribution
        for i, task in enumerate(tasks):
            agent_id = agent_ids[i % len(agent_ids)]
            task["team_id"] = team_id
            await self.redis.lpush(f"agent:{agent_id}:tasks", json.dumps(task))
            
    async def _coordinate_sequential(self, team_id: str, agent_ids: List[str], data: Dict):
        """Chain tasks through agents sequentially"""
        # Create workflow
        workflow_id = str(uuid.uuid4())
        workflow = {
            "id": workflow_id,
            "team_id": team_id,
            "steps": data["steps"],
            "current_step": 0,
            "agent_sequence": agent_ids
        }
        
        await self.redis.set(f"workflow:{workflow_id}", json.dumps(workflow))
        
        # Start first task
        first_task = workflow["steps"][0]
        first_task["workflow_id"] = workflow_id
        await self.redis.lpush(f"agent:{agent_ids[0]}:tasks", json.dumps(first_task))
        
    async def _mark_agent_unhealthy(self, agent_id: str):
        """Mark an agent as unhealthy"""
        logger.warning(f"Agent {agent_id} marked as unhealthy")
        
        # Update agent status
        agent_data = await self.redis.get(f"agent:{agent_id}")
        if agent_data:
            agent = json.loads(agent_data)
            agent["status"] = "unhealthy"
            await self.redis.set(f"agent:{agent_id}", json.dumps(agent))
            
        # Reassign tasks
        await self._reassign_agent_tasks(agent_id)

# Global orchestrator instance
orchestrator = Orchestrator()