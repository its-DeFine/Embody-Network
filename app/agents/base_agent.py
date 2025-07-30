"""
Simplified AutoGen Agent Base
"""
import os
import json
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from autogen import AssistantAgent, UserProxyAgent
import redis.asyncio as redis
import httpx

logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for all AutoGen agents"""
    
    def __init__(self, agent_id: str, agent_type: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = config
        self.redis_client = None
        self.openbb_client = None
        self.running = False
        
        # AutoGen agents
        self.assistant = None
        self.user_proxy = None
        
    async def initialize(self):
        """Initialize the agent"""
        # Connect to Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = await redis.from_url(redis_url)
        
        # Initialize OpenBB client if needed
        if self.agent_type in ["trading", "analysis", "portfolio"]:
            from ..openbb_client import get_openbb_client
            self.openbb_client = await get_openbb_client()
        
        # Setup AutoGen agents
        self.assistant = AssistantAgent(
            name=f"{self.agent_type}_assistant",
            system_message=self.get_system_message(),
            llm_config={
                "temperature": 0.7,
                "model": self.config.get("model", "gpt-3.5-turbo"),
            }
        )
        
        self.user_proxy = UserProxyAgent(
            name=f"{self.agent_type}_user",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config={"use_docker": False}
        )
        
        logger.info(f"Agent {self.agent_id} initialized")
        
    def get_system_message(self) -> str:
        """Get system message for the agent type"""
        messages = {
            "trading": "You are a trading agent. Analyze markets and execute trades wisely.",
            "analysis": "You are an analysis agent. Provide detailed market analysis.",
            "risk": "You are a risk management agent. Monitor and manage portfolio risk.",
            "portfolio": "You are a portfolio optimization agent. Optimize asset allocation."
        }
        return messages.get(self.agent_type, "You are a helpful assistant.")
        
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data from OpenBB"""
        if not self.openbb_client:
            return {}
            
        return await self.openbb_client.get_market_data(symbol)
    
    async def update_status(self, status: str, data: Optional[Dict] = None):
        """Update agent status in Redis"""
        await self.redis_client.hset(
            f"agent:{self.agent_id}:status",
            mapping={
                "status": status,
                "timestamp": asyncio.get_event_loop().time(),
                "data": json.dumps(data or {})
            }
        )
        
    async def run(self):
        """Main agent loop"""
        await self.initialize()
        self.running = True
        
        await self.update_status("running")
        
        while self.running:
            try:
                # Check for tasks
                task = await self.redis_client.blpop(f"agent:{self.agent_id}:tasks", timeout=5)
                
                if task:
                    _, task_data = task
                    await self.handle_task(json.loads(task_data))
                    
            except Exception as e:
                logger.error(f"Error in agent loop: {e}")
                await asyncio.sleep(5)
                
    async def handle_task(self, task: Dict[str, Any]):
        """Handle a task"""
        logger.info(f"Handling task: {task}")
        task_id = task.get("id")
        
        try:
            # Update task status
            await self._update_task_status(task_id, "in_progress")
            
            # Use AutoGen for task execution
            if task.get("type") == "analyze":
                symbol = task.get("symbol", "BTC/USD")
                market_data = await self.get_market_data(symbol)
                
                # Create conversation
                message = f"Analyze the market data for {symbol}: {market_data}"
                self.user_proxy.initiate_chat(self.assistant, message=message)
                
                # Get response
                response = self.assistant.last_message()
                result = response["content"]
                
            else:
                # Default handling
                result = await self._process_task(task)
            
            # Save result
            await self.redis_client.hset(
                f"task:{task_id}:result",
                mapping={
                    "status": "completed",
                    "result": result,
                    "timestamp": str(datetime.utcnow())
                }
            )
            
            # Update task status
            await self._update_task_status(task_id, "completed")
            
            # Publish completion event
            await self._publish_event("task.completed", {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "result": result
            })
            
        except Exception as e:
            logger.error(f"Error handling task {task_id}: {e}")
            await self._update_task_status(task_id, "failed", str(e))
            
    async def _update_task_status(self, task_id: str, status: str, error: str = None):
        """Update task status"""
        task_data = await self.redis_client.get(f"task:{task_id}")
        if task_data:
            task = json.loads(task_data)
            task["status"] = status
            if error:
                task["error"] = error
            await self.redis_client.set(f"task:{task_id}", json.dumps(task))
            
    async def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event to orchestrator"""
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "source": f"agent:{self.agent_id}",
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis_client.lpush("events:global", json.dumps(event))
        
    async def _process_task(self, task: Dict[str, Any]) -> str:
        """Process generic task - override in subclasses"""
        return f"Task {task.get('type')} processed by {self.agent_type} agent"
            
    async def stop(self):
        """Stop the agent"""
        self.running = False
        await self.update_status("stopped")
        
        if self.redis_client:
            await self.redis_client.close()
        if self.openbb_client:
            await self.openbb_client.aclose()


# Agent runner
async def main():
    agent_id = os.getenv("AGENT_ID")
    agent_type = os.getenv("AGENT_TYPE")
    config = json.loads(os.getenv("AGENT_CONFIG", "{}"))
    
    agent = BaseAgent(agent_id, agent_type, config)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())