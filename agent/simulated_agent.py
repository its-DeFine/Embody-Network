#!/usr/bin/env python3
"""
Simulated AutoGen Agent Container
Processes tasks from Redis queue and returns results
"""
import os
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import redis.asyncio as redis
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimulatedAgent:
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.redis_client = None
        self.running = True
        
    async def connect_redis(self):
        """Connect to Redis"""
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = await redis.from_url(redis_url)
        logger.info(f"Agent {self.agent_id} connected to Redis")
        
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate task processing"""
        logger.info(f"Processing task: {task['id']} - {task['type']}")
        
        # Simulate different task types
        if task['type'] == 'analysis':
            # Simulate market analysis
            result = {
                "analysis": "Market Analysis Complete",
                "summary": f"Analyzed {task.get('data', {}).get('target', 'market')}",
                "findings": [
                    "Trend: Bullish momentum detected",
                    "Volume: Above average trading volume",
                    "Sentiment: 72% positive"
                ],
                "recommendations": [
                    "Consider long positions",
                    "Set stop loss at -2%"
                ],
                "confidence": 0.85,
                "timestamp": datetime.utcnow().isoformat()
            }
            # Simulate processing time
            await asyncio.sleep(2)
            
        elif task['type'] == 'trading':
            # Simulate trading execution
            data = task.get('data', {})
            result = {
                "action": data.get('action', 'buy'),
                "symbol": data.get('symbol', 'UNKNOWN'),
                "quantity": data.get('quantity', 0),
                "status": "executed",
                "price": 150.25,  # Simulated price
                "total": 150.25 * data.get('quantity', 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            await asyncio.sleep(1)
            
        elif task['type'] == 'risk':
            # Simulate risk assessment
            result = {
                "risk_score": 0.3,
                "risk_level": "LOW",
                "factors": [
                    "Market volatility: Normal",
                    "Portfolio exposure: Balanced",
                    "Correlation risk: Minimal"
                ],
                "max_recommended_position": 10000,
                "timestamp": datetime.utcnow().isoformat()
            }
            await asyncio.sleep(1.5)
            
        else:
            # Generic task processing
            result = {
                "status": "completed",
                "message": f"Processed {task['type']} task",
                "data": task.get('data', {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            await asyncio.sleep(1)
            
        return result
        
    async def listen_for_tasks(self):
        """Listen for tasks assigned to this agent"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"agent:{self.agent_id}:tasks")
        
        logger.info(f"Agent {self.agent_id} listening for tasks...")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    # Parse task
                    task_data = json.loads(message['data'])
                    task_id = task_data['id']
                    
                    logger.info(f"Received task {task_id}")
                    
                    # Update task status to running
                    task_data['status'] = 'running'
                    task_data['started_at'] = datetime.utcnow().isoformat()
                    await self.redis_client.set(
                        f"task:{task_id}", 
                        json.dumps(task_data)
                    )
                    
                    # Process task
                    result = await self.process_task(task_data)
                    
                    # Update task with result
                    task_data['status'] = 'completed'
                    task_data['result'] = result
                    task_data['completed_at'] = datetime.utcnow().isoformat()
                    await self.redis_client.set(
                        f"task:{task_id}", 
                        json.dumps(task_data)
                    )
                    
                    # Publish completion event
                    await self.redis_client.publish(
                        "events",
                        json.dumps({
                            "type": "task.completed",
                            "source": f"agent:{self.agent_id}",
                            "data": {
                                "task_id": task_id,
                                "result": result
                            }
                        })
                    )
                    
                    logger.info(f"Task {task_id} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Error processing task: {e}")
                    if 'task_id' in locals():
                        # Mark task as failed
                        task_data['status'] = 'failed'
                        task_data['error'] = str(e)
                        await self.redis_client.set(
                            f"task:{task_id}", 
                            json.dumps(task_data)
                        )
    
    async def heartbeat(self):
        """Send periodic heartbeat"""
        while self.running:
            try:
                # Update agent status
                agent_info = {
                    "id": self.agent_id,
                    "type": self.agent_type,
                    "status": "running",
                    "last_heartbeat": datetime.utcnow().isoformat(),
                    "container_id": f"simulated-{self.agent_id}"
                }
                await self.redis_client.set(
                    f"agent:{self.agent_id}:status",
                    json.dumps(agent_info),
                    ex=60  # Expire after 60 seconds
                )
                
                # Publish heartbeat event
                await self.redis_client.publish(
                    "events",
                    json.dumps({
                        "type": "agent.heartbeat",
                        "source": f"agent:{self.agent_id}",
                        "data": agent_info
                    })
                )
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
    
    async def run(self):
        """Main agent loop"""
        try:
            await self.connect_redis()
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(self.heartbeat())
            
            # Start listening for tasks
            await self.listen_for_tasks()
            
        except KeyboardInterrupt:
            logger.info("Agent shutting down...")
            self.running = False
        except Exception as e:
            logger.error(f"Agent error: {e}")
        finally:
            if self.redis_client:
                await self.redis_client.close()

async def main():
    """Run simulated agent"""
    # Get agent configuration from environment or use defaults
    agent_id = os.getenv('AGENT_ID', str(uuid.uuid4()))
    agent_type = os.getenv('AGENT_TYPE', 'analysis')
    
    logger.info(f"Starting simulated agent: {agent_id} (type: {agent_type})")
    
    agent = SimulatedAgent(agent_id, agent_type)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())