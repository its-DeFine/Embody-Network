"""
Agent Manager with Inter-Agent Communication

This module provides advanced agent management capabilities including:
- Redis pub/sub based inter-agent communication
- Market insights sharing between agents  
- Coordinated trading decisions
- Voting mechanisms for trade decisions
- Agent clustering for specialized tasks
- Real-time agent orchestration

TODO: [CONTAINER] Add comprehensive test coverage for agent lifecycle management
TODO: [CONTAINER] Implement agent performance monitoring and health checks
TODO: [CONTAINER] Add agent failure recovery and automatic restart mechanisms
TODO: [PERFORMANCE] Optimize inter-agent communication for high-frequency scenarios
TODO: [SECURITY] Add agent authentication and authorization for sensitive operations
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict

from ...dependencies import get_redis
from ...config import settings
from ...services.ollama_integration import ollama_manager, OllamaAgent

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Agent type enumeration"""
    TRADING = "trading"
    ANALYSIS = "analysis"
    RISK = "risk"
    PORTFOLIO = "portfolio"
    MARKET_MAKER = "market_maker"
    ARBITRAGE = "arbitrage"
    SENTIMENT = "sentiment"


class MessageType(str, Enum):
    """Inter-agent message types"""
    MARKET_INSIGHT = "market_insight"
    TRADE_PROPOSAL = "trade_proposal"
    RISK_ALERT = "risk_alert"
    CONSENSUS_REQUEST = "consensus_request"
    CONSENSUS_VOTE = "consensus_vote"
    PORTFOLIO_UPDATE = "portfolio_update"
    COORDINATION_REQUEST = "coordination_request"
    HEARTBEAT = "heartbeat"
    CLUSTER_JOIN = "cluster_join"
    CLUSTER_LEAVE = "cluster_leave"


class VoteType(str, Enum):
    """Voting types for consensus"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class AgentMessage:
    """Inter-agent communication message"""
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    content: Dict[str, Any]
    timestamp: str
    expires_at: Optional[str] = None
    requires_response: bool = False
    correlation_id: Optional[str] = None


@dataclass
class MarketInsight:
    """Market insight shared between agents"""
    symbol: str
    insight_type: str  # "bullish", "bearish", "neutral", "volatility", "volume"
    confidence: float  # 0.0 to 1.0
    timeframe: str  # "1m", "5m", "1h", "1d"
    data: Dict[str, Any]
    source: str
    timestamp: str


@dataclass
class TradeProposal:
    """Trade proposal for consensus voting"""
    proposal_id: str
    symbol: str
    action: str  # "buy", "sell"
    quantity: float
    price: Optional[float]
    strategy: str
    reasoning: str
    risk_score: float
    expected_profit: float
    confidence: float
    proposed_by: str
    timestamp: str


@dataclass
class ConsensusVote:
    """Vote on a trade proposal"""
    proposal_id: str
    voter_id: str
    vote: VoteType
    reasoning: str
    timestamp: str


@dataclass
class AgentCluster:
    """Agent cluster for specialized tasks"""
    cluster_id: str
    cluster_type: str
    members: Set[str]
    coordinator: str
    created_at: str
    last_activity: str


class AgentManager:
    """Advanced agent manager with inter-agent communication"""
    
    def __init__(self):
        self.redis = None
        self.running = False
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.clusters: Dict[str, AgentCluster] = {}
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self.consensus_proposals: Dict[str, TradeProposal] = {}
        self.consensus_votes: Dict[str, List[ConsensusVote]] = defaultdict(list)
        
        # Register default message handlers
        self._register_default_handlers()
        
    async def initialize(self):
        """Initialize the agent manager"""
        self.redis = await get_redis()
        await self._load_existing_agents()
        await self._load_existing_clusters()
        logger.info("Agent Manager initialized")
        
    async def start(self):
        """Start the agent manager"""
        await self.initialize()
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._message_processor())
        asyncio.create_task(self._health_monitor())
        asyncio.create_task(self._consensus_monitor())
        asyncio.create_task(self._cluster_coordinator())
        
        logger.info("Agent Manager started")
        
    async def stop(self):
        """Stop the agent manager"""
        self.running = False
        logger.info("Agent Manager stopped")
        
    # Agent Lifecycle Management
    
    async def register_agent(self, agent_id: str, agent_type: AgentType, 
                           config: Dict[str, Any]) -> bool:
        """Register a new agent"""
        try:
            # Check if Ollama is requested
            use_ollama = config.get("use_ollama", False)
            ollama_model = config.get("ollama_model", "llama2")
            
            # Create Ollama agent if requested
            ollama_agent = None
            if use_ollama and ollama_manager.available_models:
                ollama_agent = ollama_manager.create_agent(
                    agent_id=agent_id,
                    model=ollama_model,
                    role=agent_type.value
                )
                config["ollama_enabled"] = True
                config["ollama_model"] = ollama_model
            else:
                config["ollama_enabled"] = False
            
            agent_data = {
                "id": agent_id,
                "type": agent_type.value,
                "status": "active",
                "config": config,
                "registered_at": datetime.utcnow().isoformat(),
                "last_heartbeat": datetime.utcnow().isoformat(),
                "message_count": 0,
                "clusters": [],
                "ollama_agent": ollama_agent
            }
            
            self.agents[agent_id] = agent_data
            
            # Save to Redis
            await self.redis.hset(f"agent:{agent_id}", mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in agent_data.items()
            })
            
            # Announce agent registration
            await self._broadcast_message(AgentMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.HEARTBEAT,
                sender_id=agent_id,
                recipient_id=None,
                content={"action": "joined", "agent_type": agent_type.value},
                timestamp=datetime.utcnow().isoformat()
            ))
            
            logger.info(f"Agent {agent_id} registered as {agent_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            return False
            
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        try:
            if agent_id not in self.agents:
                return False
                
            # Remove from clusters
            for cluster_id in self.agents[agent_id].get("clusters", []):
                await self._leave_cluster(agent_id, cluster_id)
                
            # Announce departure
            await self._broadcast_message(AgentMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.HEARTBEAT,
                sender_id=agent_id,
                recipient_id=None,
                content={"action": "left"},
                timestamp=datetime.utcnow().isoformat()
            ))
            
            # Clean up
            del self.agents[agent_id]
            await self.redis.delete(f"agent:{agent_id}")
            await self.redis.delete(f"agent:{agent_id}:messages")
            
            logger.info(f"Agent {agent_id} unregistered")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {e}")
            return False
            
    # Inter-Agent Communication
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message between agents"""
        try:
            message_data = asdict(message)
            
            if message.recipient_id:
                # Direct message
                await self.redis.lpush(
                    f"agent:{message.recipient_id}:messages",
                    json.dumps(message_data)
                )
                
                # Also publish for real-time processing
                await self.redis.publish(
                    f"agent:{message.recipient_id}:messages",
                    json.dumps(message_data)
                )
            else:
                # Broadcast message
                await self._broadcast_message(message)
                
            # Update sender message count
            if message.sender_id in self.agents:
                self.agents[message.sender_id]["message_count"] += 1
                await self.redis.hincrby(f"agent:{message.sender_id}", "message_count", 1)
                
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
            
    async def get_messages(self, agent_id: str, limit: int = 10) -> List[AgentMessage]:
        """Get messages for an agent"""
        try:
            messages = await self.redis.lrange(f"agent:{agent_id}:messages", 0, limit - 1)
            
            agent_messages = []
            for msg_data in messages:
                msg_dict = json.loads(msg_data)
                agent_messages.append(AgentMessage(**msg_dict))
                
            return agent_messages
            
        except Exception as e:
            logger.error(f"Error getting messages for {agent_id}: {e}")
            return []
            
    # Market Insights Sharing
    
    async def share_market_insight(self, insight: MarketInsight) -> bool:
        """Share market insight with relevant agents"""
        try:
            # Find relevant agents based on symbol and insight type
            relevant_agents = await self._find_relevant_agents(insight.symbol, insight.insight_type)
            
            message = AgentMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.MARKET_INSIGHT,
                sender_id=insight.source,
                recipient_id=None,  # Broadcast to relevant agents
                content=asdict(insight),
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Send to relevant agents
            for agent_id in relevant_agents:
                message.recipient_id = agent_id
                await self.send_message(message)
                
            # Store in market insights index
            await self.redis.zadd(
                f"insights:{insight.symbol}",
                {json.dumps(asdict(insight)): datetime.utcnow().timestamp()}
            )
            
            # Keep only recent insights (last 1000)
            await self.redis.zremrangebyrank(f"insights:{insight.symbol}", 0, -1001)
            
            logger.info(f"Market insight shared for {insight.symbol} by {insight.source}")
            return True
            
        except Exception as e:
            logger.error(f"Error sharing market insight: {e}")
            return False
            
    async def get_market_insights(self, symbol: str, limit: int = 10) -> List[MarketInsight]:
        """Get recent market insights for a symbol"""
        try:
            insights_data = await self.redis.zrevrange(
                f"insights:{symbol}", 0, limit - 1
            )
            
            insights = []
            for data in insights_data:
                insight_dict = json.loads(data)
                insights.append(MarketInsight(**insight_dict))
                
            return insights
            
        except Exception as e:
            logger.error(f"Error getting market insights for {symbol}: {e}")
            return []
            
    # Consensus Decision Making
    
    async def propose_trade(self, proposal: TradeProposal) -> bool:
        """Propose a trade for consensus voting"""
        try:
            self.consensus_proposals[proposal.proposal_id] = proposal
            
            # Store in Redis with expiration
            await self.redis.setex(
                f"proposal:{proposal.proposal_id}",
                3600,  # 1 hour expiration
                json.dumps(asdict(proposal))
            )
            
            # Find eligible voters (exclude proposer)
            eligible_voters = [
                agent_id for agent_id, agent in self.agents.items()
                if agent_id != proposal.proposed_by and 
                agent["type"] in ["trading", "risk", "portfolio"]
            ]
            
            # Send consensus request to eligible voters
            message = AgentMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.CONSENSUS_REQUEST,
                sender_id=proposal.proposed_by,
                recipient_id=None,
                content=asdict(proposal),
                timestamp=datetime.utcnow().isoformat(),
                expires_at=(datetime.utcnow() + timedelta(minutes=5)).isoformat(),
                requires_response=True
            )
            
            for voter_id in eligible_voters:
                message.recipient_id = voter_id
                await self.send_message(message)
                
            logger.info(f"Trade proposal {proposal.proposal_id} sent for consensus")
            return True
            
        except Exception as e:
            logger.error(f"Error proposing trade: {e}")
            return False
            
    async def cast_vote(self, vote: ConsensusVote) -> bool:
        """Cast a vote on a trade proposal"""
        try:
            if vote.proposal_id not in self.consensus_proposals:
                logger.warning(f"Vote cast for unknown proposal: {vote.proposal_id}")
                return False
                
            # Check if agent already voted
            existing_votes = self.consensus_votes[vote.proposal_id]
            if any(v.voter_id == vote.voter_id for v in existing_votes):
                logger.warning(f"Agent {vote.voter_id} already voted on {vote.proposal_id}")
                return False
                
            self.consensus_votes[vote.proposal_id].append(vote)
            
            # Store vote in Redis
            await self.redis.lpush(
                f"votes:{vote.proposal_id}",
                json.dumps(asdict(vote))
            )
            
            # Send vote confirmation
            message = AgentMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.CONSENSUS_VOTE,
                sender_id=vote.voter_id,
                recipient_id=self.consensus_proposals[vote.proposal_id].proposed_by,
                content=asdict(vote),
                timestamp=datetime.utcnow().isoformat()
            )
            
            await self.send_message(message)
            
            logger.info(f"Vote cast by {vote.voter_id} on proposal {vote.proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error casting vote: {e}")
            return False
            
    async def get_consensus_result(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get consensus result for a proposal"""
        try:
            if proposal_id not in self.consensus_proposals:
                return None
                
            votes = self.consensus_votes.get(proposal_id, [])
            
            if not votes:
                return {"status": "pending", "votes": 0}
                
            approve_votes = sum(1 for v in votes if v.vote == VoteType.APPROVE)
            reject_votes = sum(1 for v in votes if v.vote == VoteType.REJECT)
            abstain_votes = sum(1 for v in votes if v.vote == VoteType.ABSTAIN)
            
            total_votes = len(votes)
            
            # Simple majority rule (can be customized)
            consensus_reached = total_votes >= 3  # Minimum votes
            approved = approve_votes > reject_votes
            
            return {
                "status": "completed" if consensus_reached else "pending",
                "approved": approved if consensus_reached else None,
                "votes": {
                    "approve": approve_votes,
                    "reject": reject_votes,
                    "abstain": abstain_votes,
                    "total": total_votes
                },
                "details": [asdict(v) for v in votes]
            }
            
        except Exception as e:
            logger.error(f"Error getting consensus result: {e}")
            return None
            
    # Agent Clustering
    
    async def create_cluster(self, cluster_type: str, coordinator_id: str) -> str:
        """Create a new agent cluster"""
        try:
            cluster_id = f"cluster_{cluster_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            cluster = AgentCluster(
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                members={coordinator_id},
                coordinator=coordinator_id,
                created_at=datetime.utcnow().isoformat(),
                last_activity=datetime.utcnow().isoformat()
            )
            
            self.clusters[cluster_id] = cluster
            
            # Save to Redis
            await self.redis.hset(f"cluster:{cluster_id}", mapping={
                "type": cluster_type,
                "coordinator": coordinator_id,
                "members": json.dumps(list(cluster.members)),
                "created_at": cluster.created_at,
                "last_activity": cluster.last_activity
            })
            
            # Add cluster to coordinator
            if coordinator_id in self.agents:
                self.agents[coordinator_id]["clusters"].append(cluster_id)
                await self.redis.hset(
                    f"agent:{coordinator_id}",
                    "clusters",
                    json.dumps(self.agents[coordinator_id]["clusters"])
                )
                
            logger.info(f"Cluster {cluster_id} created with coordinator {coordinator_id}")
            return cluster_id
            
        except Exception as e:
            logger.error(f"Error creating cluster: {e}")
            return ""
            
    async def join_cluster(self, agent_id: str, cluster_id: str) -> bool:
        """Add agent to cluster"""
        try:
            if cluster_id not in self.clusters:
                return False
                
            if agent_id not in self.agents:
                return False
                
            # Add to cluster
            self.clusters[cluster_id].members.add(agent_id)
            self.clusters[cluster_id].last_activity = datetime.utcnow().isoformat()
            
            # Update Redis
            await self.redis.hset(f"cluster:{cluster_id}", mapping={
                "members": json.dumps(list(self.clusters[cluster_id].members)),
                "last_activity": self.clusters[cluster_id].last_activity
            })
            
            # Add cluster to agent
            self.agents[agent_id]["clusters"].append(cluster_id)
            await self.redis.hset(
                f"agent:{agent_id}",
                "clusters",
                json.dumps(self.agents[agent_id]["clusters"])
            )
            
            # Notify cluster members
            await self._send_cluster_message(cluster_id, AgentMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.CLUSTER_JOIN,
                sender_id=agent_id,
                recipient_id=None,
                content={"cluster_id": cluster_id, "action": "joined"},
                timestamp=datetime.utcnow().isoformat()
            ))
            
            logger.info(f"Agent {agent_id} joined cluster {cluster_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error joining cluster: {e}")
            return False
            
    async def get_cluster_members(self, cluster_id: str) -> List[str]:
        """Get members of a cluster"""
        if cluster_id in self.clusters:
            return list(self.clusters[cluster_id].members)
        return []
        
    # Private Methods
    
    async def _message_processor(self):
        """Process incoming messages"""
        while self.running:
            try:
                # Process messages from Redis pub/sub
                await asyncio.sleep(0.1)  # Prevent tight loop
                
                # This is a simplified version - in production, use Redis pub/sub
                for agent_id in list(self.agents.keys()):
                    messages = await self.get_messages(agent_id, 5)
                    for message in messages:
                        await self._handle_message(message)
                        
            except Exception as e:
                logger.error(f"Error in message processor: {e}")
                await asyncio.sleep(1)
                
    async def _handle_message(self, message: AgentMessage):
        """Handle incoming message"""
        try:
            handlers = self.message_handlers.get(message.message_type, [])
            for handler in handlers:
                await handler(message)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
    async def _health_monitor(self):
        """Monitor agent health"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                for agent_id, agent in list(self.agents.items()):
                    last_heartbeat = datetime.fromisoformat(agent["last_heartbeat"])
                    
                    # Check if agent is inactive (no heartbeat for 2 minutes)
                    if (current_time - last_heartbeat).total_seconds() > 120:
                        logger.warning(f"Agent {agent_id} appears inactive")
                        agent["status"] = "inactive"
                        await self.redis.hset(f"agent:{agent_id}", "status", "inactive")
                        
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(30)
                
    async def _consensus_monitor(self):
        """Monitor consensus proposals and execute approved trades"""
        while self.running:
            try:
                for proposal_id in list(self.consensus_proposals.keys()):
                    result = await self.get_consensus_result(proposal_id)
                    
                    if result and result["status"] == "completed":
                        if result["approved"]:
                            # Execute approved trade
                            await self._execute_consensus_trade(proposal_id)
                        
                        # Clean up completed proposal
                        del self.consensus_proposals[proposal_id]
                        if proposal_id in self.consensus_votes:
                            del self.consensus_votes[proposal_id]
                            
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in consensus monitor: {e}")
                await asyncio.sleep(10)
                
    async def _cluster_coordinator(self):
        """Coordinate cluster activities"""
        while self.running:
            try:
                for cluster in self.clusters.values():
                    # Update cluster activity
                    cluster.last_activity = datetime.utcnow().isoformat()
                    await self.redis.hset(
                        f"cluster:{cluster.cluster_id}",
                        "last_activity",
                        cluster.last_activity
                    )
                    
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error in cluster coordinator: {e}")
                await asyncio.sleep(60)
                
    async def _broadcast_message(self, message: AgentMessage):
        """Broadcast message to all agents"""
        message_data = json.dumps(asdict(message))
        await self.redis.publish("agents:broadcast", message_data)
        
    async def _send_cluster_message(self, cluster_id: str, message: AgentMessage):
        """Send message to all cluster members"""
        if cluster_id in self.clusters:
            for member_id in self.clusters[cluster_id].members:
                message.recipient_id = member_id
                await self.send_message(message)
                
    async def _find_relevant_agents(self, symbol: str, insight_type: str) -> List[str]:
        """Find agents relevant to a market insight"""
        relevant_agents = []
        
        for agent_id, agent in self.agents.items():
            agent_type = agent["type"]
            
            # All trading agents are interested in insights
            if agent_type in ["trading", "analysis", "portfolio"]:
                relevant_agents.append(agent_id)
            # Risk agents interested in risk-related insights
            elif agent_type == "risk" and insight_type in ["volatility", "bearish"]:
                relevant_agents.append(agent_id)
                
        return relevant_agents
        
    async def _execute_consensus_trade(self, proposal_id: str):
        """Execute an approved consensus trade"""
        try:
            proposal = self.consensus_proposals[proposal_id]
            
            # Create trade order
            order_data = {
                "symbol": proposal.symbol,
                "action": proposal.action,
                "quantity": proposal.quantity,
                "price": proposal.price,
                "type": "consensus",
                "proposal_id": proposal_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Queue for execution
            await self.redis.lpush("orders:consensus", json.dumps(order_data))
            
            logger.info(f"Consensus trade executed for proposal {proposal_id}")
            
        except Exception as e:
            logger.error(f"Error executing consensus trade: {e}")
            
    async def _load_existing_agents(self):
        """Load existing agents from Redis"""
        try:
            agent_keys = await self.redis.keys("agent:*")
            
            for key in agent_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                if ":status" in key_str or ":messages" in key_str or ":metrics" in key_str:
                    continue
                    
                agent_data = await self.redis.hgetall(key)
                if agent_data:
                    agent_id = key_str.split(":")[-1]
                    
                    # Convert bytes to strings and parse JSON fields
                    agent = {}
                    for k, v in agent_data.items():
                        key_name = k.decode() if isinstance(k, bytes) else k
                        value = v.decode() if isinstance(v, bytes) else v
                        
                        if key_name in ["config", "clusters"]:
                            try:
                                agent[key_name] = json.loads(value)
                            except:
                                agent[key_name] = {} if key_name == "config" else []
                        else:
                            agent[key_name] = value
                            
                    self.agents[agent_id] = agent
                    
        except Exception as e:
            logger.error(f"Error loading existing agents: {e}")
            
    async def _load_existing_clusters(self):
        """Load existing clusters from Redis"""
        try:
            cluster_keys = await self.redis.keys("cluster:*")
            
            for key in cluster_keys:
                cluster_data = await self.redis.hgetall(key)
                if cluster_data:
                    cluster_id = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
                    
                    members_data = cluster_data.get(b"members", b"[]")
                    if isinstance(members_data, bytes):
                        members_data = members_data.decode()
                        
                    cluster = AgentCluster(
                        cluster_id=cluster_id,
                        cluster_type=cluster_data.get(b"type", b"").decode(),
                        members=set(json.loads(members_data)),
                        coordinator=cluster_data.get(b"coordinator", b"").decode(),
                        created_at=cluster_data.get(b"created_at", b"").decode(),
                        last_activity=cluster_data.get(b"last_activity", b"").decode()
                    )
                    
                    self.clusters[cluster_id] = cluster
                    
        except Exception as e:
            logger.error(f"Error loading existing clusters: {e}")
            
    async def _leave_cluster(self, agent_id: str, cluster_id: str):
        """Remove agent from cluster"""
        try:
            if cluster_id in self.clusters:
                self.clusters[cluster_id].members.discard(agent_id)
                
                # Update Redis
                await self.redis.hset(f"cluster:{cluster_id}", 
                                    "members", 
                                    json.dumps(list(self.clusters[cluster_id].members)))
                
                # If cluster is empty, remove it
                if not self.clusters[cluster_id].members:
                    del self.clusters[cluster_id]
                    await self.redis.delete(f"cluster:{cluster_id}")
                    
        except Exception as e:
            logger.error(f"Error leaving cluster: {e}")
            
    def _register_default_handlers(self):
        """Register default message handlers"""
        self.message_handlers[MessageType.HEARTBEAT].append(self._handle_heartbeat)
        self.message_handlers[MessageType.MARKET_INSIGHT].append(self._handle_market_insight)
        self.message_handlers[MessageType.CONSENSUS_REQUEST].append(self._handle_consensus_request)
        
    async def _handle_heartbeat(self, message: AgentMessage):
        """Handle heartbeat message"""
        sender_id = message.sender_id
        if sender_id in self.agents:
            self.agents[sender_id]["last_heartbeat"] = message.timestamp
            await self.redis.hset(f"agent:{sender_id}", "last_heartbeat", message.timestamp)
            
    async def _handle_market_insight(self, message: AgentMessage):
        """Handle market insight message"""
        # Default handler - can be extended
        pass
        
    async def _handle_consensus_request(self, message: AgentMessage):
        """Handle consensus request message"""
        # Default handler - can be extended
        pass


# Global agent manager instance
agent_manager = AgentManager()