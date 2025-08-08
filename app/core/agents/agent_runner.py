#!/usr/bin/env python3
"""
Standalone Agent Runner
Allows agents to run as independent processes/containers
"""

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime
from typing import Optional

from ...dependencies import get_redis
from ...infrastructure.database.models import AgentType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StandaloneAgent:
    """Agent that runs independently and communicates via Redis"""
    
    def __init__(self, agent_id: str, agent_type: str, strategy: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.strategy = strategy
        self.redis = None
        self.running = False
        self.strategy_instance = None
        
    async def initialize(self):
        """Initialize agent connections"""
        self.redis = await get_redis()
        
        # Initialize strategy
        if self.strategy == "arbitrage":
            self.strategy_instance = ArbitrageStrategy()
        elif self.strategy == "scalping":
            self.strategy_instance = ScalpingStrategy()
        elif self.strategy == "dca":
            self.strategy_instance = DCAStrategy()
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
            
        logger.info(f"Agent {self.agent_id} initialized with {self.strategy} strategy")
        
    async def start(self):
        """Start the agent"""
        self.running = True
        
        # Register agent
        await self.redis.hset(
            f"agent:{self.agent_id}",
            mapping={
                "status": "running",
                "strategy": self.strategy,
                "started_at": datetime.utcnow().isoformat(),
                "pid": os.getpid(),
                "container_id": os.environ.get("HOSTNAME", f"standalone-{self.agent_id}")
            }
        )
        
        # Subscribe to commands
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"agent:{self.agent_id}:command")
        
        logger.info(f"Agent {self.agent_id} started and listening for commands")
        
        # Main loop
        while self.running:
            try:
                # Check for commands
                message = await pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    await self.handle_command(message["data"])
                
                # Execute strategy
                await self.execute_strategy()
                
                # Update heartbeat
                await self.redis.hset(
                    f"agent:{self.agent_id}",
                    "last_heartbeat",
                    datetime.utcnow().isoformat()
                )
                
                await asyncio.sleep(5)  # Strategy execution interval
                
            except Exception as e:
                logger.error(f"Error in agent loop: {e}")
                await asyncio.sleep(5)
                
    async def handle_command(self, command: bytes):
        """Handle commands from central manager"""
        cmd = command.decode("utf-8")
        logger.info(f"Received command: {cmd}")
        
        if cmd == "stop":
            self.running = False
        elif cmd == "pause":
            await self.redis.hset(f"agent:{self.agent_id}", "status", "paused")
        elif cmd == "resume":
            await self.redis.hset(f"agent:{self.agent_id}", "status", "running")
        elif cmd.startswith("config:"):
            # Update configuration
            config_data = cmd.split(":", 1)[1]
            await self.update_config(config_data)
            
    async def execute_strategy(self):
        """Execute the trading strategy"""
        status = await self.redis.hget(f"agent:{self.agent_id}", "status")
        if status != b"running":
            return
            
        # Get portfolio data
        portfolio_data = await self.redis.hgetall("portfolio:main")
        if not portfolio_data:
            return
            
        # Get market data
        market_data = await self.get_market_data()
        
        # Execute strategy
        if self.strategy_instance and market_data:
            signals = await self.strategy_instance.analyze(market_data)
            
            for signal in signals:
                # Publish trade signal
                await self.redis.publish(
                    "trading:signals",
                    f"{self.agent_id}:{signal['action']}:{signal['symbol']}:{signal['quantity']}"
                )
                
                # Log signal
                logger.info(f"Generated signal: {signal}")
                
    async def get_market_data(self):
        """Get market data from Redis"""
        # Get latest prices from Redis cache
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        market_data = {}
        
        for symbol in symbols:
            price_data = await self.redis.hget("market:prices", symbol)
            if price_data:
                market_data[symbol] = float(price_data)
                
        return market_data
        
    async def update_config(self, config_data: str):
        """Update agent configuration"""
        # Parse and apply configuration
        logger.info(f"Updating configuration: {config_data}")
        
    async def stop(self):
        """Stop the agent"""
        self.running = False
        
        # Update status
        await self.redis.hset(
            f"agent:{self.agent_id}",
            mapping={
                "status": "stopped",
                "stopped_at": datetime.utcnow().isoformat()
            }
        )
        
        # Close connections
        if self.redis:
            await self.redis.close()
            
        logger.info(f"Agent {self.agent_id} stopped")


async def main():
    """Main entry point for standalone agent"""
    # Get configuration from environment
    agent_id = os.environ.get("AGENT_ID", f"agent-{os.getpid()}")
    agent_type = os.environ.get("AGENT_TYPE", "trading")
    strategy = os.environ.get("STRATEGY", "arbitrage")
    
    logger.info(f"Starting agent {agent_id} with {strategy} strategy")
    
    # Create and start agent
    agent = StandaloneAgent(agent_id, agent_type, strategy)
    await agent.initialize()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(agent.stop())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run agent
    try:
        await agent.start()
    except Exception as e:
        logger.error(f"Agent error: {e}")
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())