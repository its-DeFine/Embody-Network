"""
Cross-Instance Bridge
Enables secure communication between instances through the master
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import httpx
import hmac
import hashlib

from ...dependencies import get_redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of cross-instance messages"""
    MARKET_SIGNAL = "market_signal"
    STRATEGY_SYNC = "strategy_sync"
    RISK_ALERT = "risk_alert"
    POSITION_SHARE = "position_share"
    COLLECTIVE_VOTE = "collective_vote"
    ARBITRAGE_OPPORTUNITY = "arbitrage_opportunity"


class CrossInstanceMessage(BaseModel):
    """Message format for cross-instance communication"""
    message_id: str
    source_instance: str
    target_instances: List[str]  # ["all"] for broadcast
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    requires_response: bool = False
    ttl: int = 300  # 5 minutes


class CrossInstanceBridge:
    """
    Manages secure communication between instances
    All messages are routed through the master for security
    """
    
    def __init__(self):
        self.instance_id = None
        self.master_url = None
        self.api_key = None
        self.redis = None
        self.message_handlers = {}
        self.pending_responses = {}
        self.running = False
        
    async def initialize(self, instance_id: str, master_url: str, api_key: str):
        """Initialize the bridge"""
        self.instance_id = instance_id
        self.master_url = master_url
        self.api_key = api_key
        self.redis = await get_redis()
        
        # Register default handlers
        self._register_default_handlers()
        
        logger.info(f"Cross-instance bridge initialized for {instance_id}")
        
    def _register_default_handlers(self):
        """Register default message handlers"""
        
        @self.register_handler(MessageType.MARKET_SIGNAL)
        async def handle_market_signal(message: CrossInstanceMessage):
            """Handle market signals from other instances"""
            signal = message.payload
            
            # Store in Redis for local agents
            await self.redis.publish(
                "cross_instance:market_signal",
                json.dumps({
                    "source": message.source_instance,
                    "signal": signal
                })
            )
            
            # Process if it's a strong signal
            if signal.get("confidence", 0) > 0.8:
                logger.info(f"Strong market signal from {message.source_instance}: {signal}")
                
        @self.register_handler(MessageType.ARBITRAGE_OPPORTUNITY)
        async def handle_arbitrage(message: CrossInstanceMessage):
            """Handle arbitrage opportunities"""
            opportunity = message.payload
            
            # Check if we can participate
            if opportunity.get("required_capital", 0) < 10000:
                # Signal our trading engine
                await self.redis.publish(
                    "trading:arbitrage_opportunity",
                    json.dumps(opportunity)
                )
                
        @self.register_handler(MessageType.COLLECTIVE_VOTE)
        async def handle_vote_request(message: CrossInstanceMessage):
            """Participate in collective decision making"""
            vote_request = message.payload
            
            # Get our vote from collective intelligence
            our_vote = await self._get_collective_vote(vote_request)
            
            # Send response back
            if message.requires_response:
                await self.send_response(
                    message.message_id,
                    message.source_instance,
                    {"vote": our_vote, "confidence": 0.85}
                )
                
    def register_handler(self, message_type: MessageType):
        """Decorator to register message handlers"""
        def decorator(func):
            self.message_handlers[message_type] = func
            return func
        return decorator
        
    async def send_message(
        self,
        target_instances: List[str],
        message_type: MessageType,
        payload: Dict[str, Any],
        requires_response: bool = False
    ) -> Optional[str]:
        """Send message to other instances through master"""
        
        message = CrossInstanceMessage(
            message_id=f"{self.instance_id}-{datetime.utcnow().timestamp()}",
            source_instance=self.instance_id,
            target_instances=target_instances,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.utcnow(),
            requires_response=requires_response
        )
        
        # Route through master
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.master_url}/relay-message",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=message.dict()
            )
            
        if response.status_code == 200:
            if requires_response:
                self.pending_responses[message.message_id] = asyncio.Event()
            return message.message_id
        else:
            logger.error(f"Failed to send cross-instance message: {response.text}")
            return None
            
    async def send_response(
        self,
        original_message_id: str,
        target_instance: str,
        response_payload: Dict[str, Any]
    ):
        """Send response to a message"""
        await self.send_message(
            target_instances=[target_instance],
            message_type=MessageType.COLLECTIVE_VOTE,
            payload={
                "response_to": original_message_id,
                "response": response_payload
            }
        )
        
    async def broadcast_market_insight(self, insight: Dict[str, Any]):
        """Broadcast market insight to all instances"""
        await self.send_message(
            target_instances=["all"],
            message_type=MessageType.MARKET_SIGNAL,
            payload=insight
        )
        
    async def share_strategy_performance(self, strategy_data: Dict[str, Any]):
        """Share strategy performance with other instances"""
        await self.send_message(
            target_instances=["all"],
            message_type=MessageType.STRATEGY_SYNC,
            payload={
                "strategy": strategy_data["name"],
                "performance": strategy_data["metrics"],
                "parameters": strategy_data.get("public_params", {})
            }
        )
        
    async def request_collective_decision(
        self,
        decision_type: str,
        context: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Request collective decision from other instances"""
        
        message_id = await self.send_message(
            target_instances=["all"],
            message_type=MessageType.COLLECTIVE_VOTE,
            payload={
                "decision_type": decision_type,
                "context": context,
                "timeout": timeout
            },
            requires_response=True
        )
        
        if not message_id:
            return {"error": "Failed to send request"}
            
        # Wait for responses
        responses = await self._collect_responses(message_id, timeout)
        
        # Aggregate responses
        return self._aggregate_collective_decision(responses)
        
    async def alert_risk_condition(self, risk_data: Dict[str, Any]):
        """Alert other instances about risk conditions"""
        await self.send_message(
            target_instances=["all"],
            message_type=MessageType.RISK_ALERT,
            payload=risk_data
        )
        
    async def _get_collective_vote(self, vote_request: Dict[str, Any]) -> str:
        """Get our instance's vote for a collective decision"""
        # Implement your voting logic here
        # This is a simplified example
        
        decision_type = vote_request.get("decision_type")
        
        if decision_type == "market_direction":
            # Analyze our local data
            bullish_signals = await self.redis.get("signals:bullish_count") or 0
            bearish_signals = await self.redis.get("signals:bearish_count") or 0
            
            return "bullish" if int(bullish_signals) > int(bearish_signals) else "bearish"
            
        elif decision_type == "risk_adjustment":
            # Check our risk metrics
            current_risk = await self.redis.get("risk:current_level") or 0.5
            return "increase" if float(current_risk) < 0.3 else "decrease"
            
        return "neutral"
        
    async def _collect_responses(
        self,
        message_id: str,
        timeout: int
    ) -> List[Dict[str, Any]]:
        """Collect responses from other instances"""
        responses = []
        
        # This would be implemented with actual response collection
        # For now, return empty list
        return responses
        
    def _aggregate_collective_decision(
        self,
        responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate responses into collective decision"""
        if not responses:
            return {"decision": "no_consensus", "confidence": 0}
            
        # Simple majority voting
        votes = {}
        total_confidence = 0
        
        for response in responses:
            vote = response.get("vote", "neutral")
            confidence = response.get("confidence", 0.5)
            
            votes[vote] = votes.get(vote, 0) + confidence
            total_confidence += confidence
            
        # Find winning vote
        winning_vote = max(votes.items(), key=lambda x: x[1])
        
        return {
            "decision": winning_vote[0],
            "confidence": winning_vote[1] / total_confidence if total_confidence > 0 else 0,
            "votes": votes,
            "participant_count": len(responses)
        }
        
    async def start_listening(self):
        """Start listening for cross-instance messages"""
        self.running = True
        
        # Subscribe to our instance channel
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"instance:{self.instance_id}:messages")
        
        logger.info(f"Cross-instance bridge listening for messages")
        
        while self.running:
            try:
                message = await pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    await self._handle_incoming_message(message["data"])
                    
            except Exception as e:
                logger.error(f"Error in message listener: {e}")
                await asyncio.sleep(5)
                
    async def _handle_incoming_message(self, data: bytes):
        """Handle incoming cross-instance message"""
        try:
            message_data = json.loads(data.decode())
            message = CrossInstanceMessage(**message_data)
            
            # Check if it's for us
            if (self.instance_id in message.target_instances or 
                "all" in message.target_instances):
                
                # Get handler
                handler = self.message_handlers.get(message.message_type)
                if handler:
                    await handler(message)
                else:
                    logger.warning(f"No handler for message type: {message.message_type}")
                    
        except Exception as e:
            logger.error(f"Error handling cross-instance message: {e}")


# Global instance
cross_instance_bridge = CrossInstanceBridge()