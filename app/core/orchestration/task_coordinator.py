"""
Task Coordination Service

Focused microservice responsible for:
- Task routing and assignment
- Agent load balancing
- Task dependency management
- Task failure recovery
- Performance optimization for task distribution
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import statistics

from .base_service import BaseOrchestrationService

logger = logging.getLogger(__name__)


class TaskCoordinator(BaseOrchestrationService):
    """Microservice for task coordination and routing"""
    
    def __init__(self, redis=None):
        super().__init__("task_coordinator", redis)
        
        # Task management
        self.pending_tasks: Dict[str, Dict] = {}
        self.active_tasks: Dict[str, Dict] = {}
        self.task_dependencies: Dict[str, List[str]] = {}
        
        # Agent tracking (lightweight)
        self.agent_metrics: Dict[str, Dict] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        
        # Performance tracking
        self.task_completion_times: deque = deque(maxlen=1000)
        self.agent_performance: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
    async def setup(self):
        """Initialize task coordinator"""
        # Subscribe to relevant events
        asyncio.create_task(self.subscribe_to_events([
            "task.created",
            "task.completed",
            "task.failed",
            "agent.started",
            "agent.stopped",
            "agent.metrics"
        ]))
        
    async def _service_loop(self):
        """Main task coordination loop"""
        while self.running:
            try:
                await self._process_pending_tasks()
                await self._check_task_timeouts()
                await self._optimize_task_distribution()
                
                await asyncio.sleep(5)  # Fast processing for tasks
                
            except Exception as e:
                self.logger.error(f"Error in task coordinator loop: {e}")
                await asyncio.sleep(10)
                
    def get_background_tasks(self):
        """Background tasks for task coordinator"""
        return [
            self._performance_analyzer(),
            self._load_balancer(),
            self._dependency_resolver()
        ]
        
    async def handle_event(self, event: Dict[str, Any]):
        """Handle incoming events"""
        event_type = event["type"]
        data = event["data"]
        
        if event_type == "task.created":
            await self._handle_task_created(data)
        elif event_type == "task.completed":
            await self._handle_task_completed(data)
        elif event_type == "task.failed":
            await self._handle_task_failed(data)
        elif event_type == "agent.started":
            await self._handle_agent_started(data)
        elif event_type == "agent.stopped":
            await self._handle_agent_stopped(data)
        elif event_type == "agent.metrics":
            await self._handle_agent_metrics(data)
            
    async def _process_pending_tasks(self):
        """Process pending tasks and assign to agents"""
        if not self.pending_tasks:
            return
            
        for task_id, task in list(self.pending_tasks.items()):
            try:
                # Check dependencies first
                if await self._check_dependencies_ready(task_id):
                    # Find best agent for this task
                    best_agent = await self._find_best_agent(task)
                    
                    if best_agent:
                        await self._assign_task_to_agent(task_id, task, best_agent)
                        del self.pending_tasks[task_id]
                        self.active_tasks[task_id] = task
                        
            except Exception as e:
                self.logger.error(f"Error processing task {task_id}: {e}")
                
    async def _find_best_agent(self, task: Dict) -> Optional[str]:
        """Find the best agent for a task based on load and capabilities"""
        task_type = task.get("type", "generic")
        required_capabilities = task.get("capabilities", [])
        
        # Filter agents by capabilities
        capable_agents = []
        for agent_id, capabilities in self.agent_capabilities.items():
            if all(cap in capabilities for cap in required_capabilities):
                if agent_id in self.agent_metrics:
                    capable_agents.append(agent_id)
                    
        if not capable_agents:
            return None
            
        # Score agents based on current load and performance
        best_agent = None
        best_score = float('inf')
        
        for agent_id in capable_agents:
            metrics = self.agent_metrics.get(agent_id, {})
            
            # Calculate load score (0-100, lower is better)
            cpu_load = metrics.get("cpu_usage", 50)
            memory_load = metrics.get("memory_usage", 50)
            active_tasks = metrics.get("active_tasks", 0)
            
            # Performance factor (average completion time)
            performance = self.agent_performance[agent_id]
            avg_completion_time = statistics.mean(performance) if performance else 30.0
            
            # Combined score (lower is better)
            load_score = (cpu_load + memory_load) / 2
            task_pressure = min(active_tasks * 10, 50)  # Cap task pressure impact
            performance_penalty = min(avg_completion_time / 10, 20)  # Normalize performance
            
            total_score = load_score + task_pressure + performance_penalty
            
            if total_score < best_score:
                best_score = total_score
                best_agent = agent_id
                
        return best_agent
        
    async def _assign_task_to_agent(self, task_id: str, task: Dict, agent_id: str):
        """Assign task to specific agent"""
        try:
            assignment = {
                "task_id": task_id,
                "task": task,
                "assigned_agent": agent_id,
                "assigned_at": datetime.utcnow().isoformat()
            }
            
            # Send to agent via Redis
            await self.redis.lpush(f"agent:{agent_id}:tasks", json.dumps(assignment))
            
            # Update metrics
            if agent_id in self.agent_metrics:
                self.agent_metrics[agent_id]["active_tasks"] = \
                    self.agent_metrics[agent_id].get("active_tasks", 0) + 1
                    
            self.logger.info(f"📋 Assigned task {task_id} to agent {agent_id}")
            
            # Publish assignment event
            await self.publish_event("task.assigned", {
                "task_id": task_id,
                "agent_id": agent_id,
                "task_type": task.get("type", "unknown")
            })
            
        except Exception as e:
            self.logger.error(f"Failed to assign task {task_id} to {agent_id}: {e}")
            
    async def _check_dependencies_ready(self, task_id: str) -> bool:
        """Check if task dependencies are satisfied"""
        dependencies = self.task_dependencies.get(task_id, [])
        
        for dep_task_id in dependencies:
            # Check if dependency is completed
            if dep_task_id in self.active_tasks:
                return False  # Still active
            if dep_task_id in self.pending_tasks:
                return False  # Not even started
                
        return True  # All dependencies satisfied
        
    async def _check_task_timeouts(self):
        """Check for timed out tasks and reassign"""
        current_time = datetime.utcnow()
        timeout_threshold = timedelta(minutes=10)  # Configurable timeout
        
        for task_id, task in list(self.active_tasks.items()):
            assigned_at = datetime.fromisoformat(task.get("assigned_at", current_time.isoformat()))
            
            if current_time - assigned_at > timeout_threshold:
                self.logger.warning(f"⏰ Task {task_id} timed out, reassigning...")
                
                # Move back to pending
                self.pending_tasks[task_id] = task
                del self.active_tasks[task_id]
                
                # Publish timeout event
                await self.publish_event("task.timeout", {
                    "task_id": task_id,
                    "original_agent": task.get("assigned_agent")
                })
                
    async def _handle_task_created(self, data: Dict):
        """Handle new task creation"""
        task_id = data.get("task_id")
        task = data.get("task", {})
        dependencies = data.get("dependencies", [])
        
        self.pending_tasks[task_id] = task
        if dependencies:
            self.task_dependencies[task_id] = dependencies
            
        self.logger.info(f"📥 New task received: {task_id}")
        
    async def _handle_task_completed(self, data: Dict):
        """Handle task completion"""
        task_id = data.get("task_id")
        agent_id = data.get("agent_id")
        completion_time = data.get("completion_time", 30.0)
        
        # Remove from active tasks
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            
        # Update agent metrics
        if agent_id in self.agent_metrics:
            self.agent_metrics[agent_id]["active_tasks"] = \
                max(0, self.agent_metrics[agent_id].get("active_tasks", 0) - 1)
                
        # Track performance
        self.task_completion_times.append(completion_time)
        self.agent_performance[agent_id].append(completion_time)
        
        self.logger.info(f"✅ Task {task_id} completed by {agent_id} in {completion_time:.2f}s")
        
    async def _handle_task_failed(self, data: Dict):
        """Handle task failure"""
        task_id = data.get("task_id")
        agent_id = data.get("agent_id")
        error = data.get("error", "Unknown error")
        
        # Move back to pending for retry
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            retry_count = task.get("retry_count", 0) + 1
            
            if retry_count <= 3:  # Max 3 retries
                task["retry_count"] = retry_count
                self.pending_tasks[task_id] = task
                self.logger.warning(f"🔄 Task {task_id} failed, retry #{retry_count}")
            else:
                self.logger.error(f"❌ Task {task_id} failed permanently after 3 retries")
                await self.publish_event("task.failed_permanently", {
                    "task_id": task_id,
                    "error": error
                })
                
            del self.active_tasks[task_id]
            
        # Update agent metrics
        if agent_id in self.agent_metrics:
            self.agent_metrics[agent_id]["active_tasks"] = \
                max(0, self.agent_metrics[agent_id].get("active_tasks", 0) - 1)
                
    async def _handle_agent_started(self, data: Dict):
        """Handle agent startup"""
        agent_id = data.get("agent_id")
        capabilities = data.get("capabilities", [])
        
        self.agent_capabilities[agent_id] = capabilities
        self.agent_metrics[agent_id] = {
            "active_tasks": 0,
            "cpu_usage": 0,
            "memory_usage": 0,
            "last_seen": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"🤖 Agent {agent_id} started with capabilities: {capabilities}")
        
    async def _handle_agent_stopped(self, data: Dict):
        """Handle agent shutdown"""
        agent_id = data.get("agent_id")
        
        # Reassign active tasks from this agent
        tasks_to_reassign = []
        for task_id, task in self.active_tasks.items():
            if task.get("assigned_agent") == agent_id:
                tasks_to_reassign.append((task_id, task))
                
        for task_id, task in tasks_to_reassign:
            self.pending_tasks[task_id] = task
            del self.active_tasks[task_id]
            
        # Clean up agent data
        self.agent_capabilities.pop(agent_id, None)
        self.agent_metrics.pop(agent_id, None)
        
        self.logger.warning(f"🛑 Agent {agent_id} stopped, reassigned {len(tasks_to_reassign)} tasks")
        
    async def _handle_agent_metrics(self, data: Dict):
        """Handle agent metrics update"""
        agent_id = data.get("agent_id")
        metrics = data.get("metrics", {})
        
        if agent_id in self.agent_metrics:
            self.agent_metrics[agent_id].update(metrics)
            self.agent_metrics[agent_id]["last_seen"] = datetime.utcnow().isoformat()
            
    async def _performance_analyzer(self):
        """Analyze task and agent performance"""
        while self.running:
            try:
                # Calculate system-wide metrics
                if self.task_completion_times:
                    avg_completion = statistics.mean(self.task_completion_times)
                    await self.publish_event("system.performance", {
                        "avg_task_completion": avg_completion,
                        "total_tasks_completed": len(self.task_completion_times),
                        "active_tasks": len(self.active_tasks),
                        "pending_tasks": len(self.pending_tasks)
                    })
                    
                await asyncio.sleep(60)  # Analyze every minute
                
            except Exception as e:
                self.logger.error(f"Error in performance analyzer: {e}")
                await asyncio.sleep(60)
                
    async def _load_balancer(self):
        """Balance load across agents"""
        while self.running:
            try:
                if len(self.agent_metrics) > 1:
                    # Find overloaded and underloaded agents
                    overloaded = []
                    underloaded = []
                    
                    for agent_id, metrics in self.agent_metrics.items():
                        load_score = (metrics.get("cpu_usage", 0) + metrics.get("memory_usage", 0)) / 2
                        active_tasks = metrics.get("active_tasks", 0)
                        
                        if load_score > 80 and active_tasks > 2:
                            overloaded.append((agent_id, load_score, active_tasks))
                        elif load_score < 30 and active_tasks < 2:
                            underloaded.append((agent_id, load_score, active_tasks))
                            
                    # Rebalance if needed
                    if overloaded and underloaded:
                        await self._rebalance_tasks(overloaded, underloaded)
                        
                await asyncio.sleep(30)  # Balance every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in load balancer: {e}")
                await asyncio.sleep(30)
                
    async def _rebalance_tasks(self, overloaded: List, underloaded: List):
        """Rebalance tasks between agents"""
        # This is a simplified rebalancing - in production would be more sophisticated
        self.logger.info(f"⚖️ Rebalancing tasks: {len(overloaded)} overloaded, {len(underloaded)} underloaded")
        
        await self.publish_event("system.rebalancing", {
            "overloaded_agents": len(overloaded),
            "underloaded_agents": len(underloaded)
        })
        
    async def _dependency_resolver(self):
        """Resolve task dependencies and update ready tasks"""
        while self.running:
            try:
                # Check if any pending tasks have dependencies that are now satisfied
                ready_tasks = []
                for task_id in list(self.pending_tasks.keys()):
                    if await self._check_dependencies_ready(task_id):
                        ready_tasks.append(task_id)
                        
                if ready_tasks:
                    self.logger.info(f"🔓 {len(ready_tasks)} tasks became dependency-ready")
                    
                await asyncio.sleep(10)  # Check dependencies every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in dependency resolver: {e}")
                await asyncio.sleep(10)
                
    async def get_coordinator_stats(self) -> Dict[str, Any]:
        """Get task coordinator statistics"""
        return {
            "service": "task_coordinator",
            "pending_tasks": len(self.pending_tasks),
            "active_tasks": len(self.active_tasks),
            "known_agents": len(self.agent_metrics),
            "avg_completion_time": statistics.mean(self.task_completion_times) if self.task_completion_times else 0,
            "total_completed": len(self.task_completion_times),
            "timestamp": datetime.utcnow().isoformat()
        }