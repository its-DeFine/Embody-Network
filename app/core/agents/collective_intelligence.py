"""
Collective Intelligence System

Advanced multi-agent collective decision making system that implements:
- Consensus algorithms for trading decisions
- Risk assessment across all agents
- Portfolio optimization using collective data
- Market sentiment aggregation
- Distributed decision logging
- Swarm intelligence patterns
"""

import asyncio
import json
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import statistics

from ...dependencies import get_redis
from .agent_manager import agent_manager, AgentMessage, MessageType

logger = logging.getLogger(__name__)


class ConsensusAlgorithm(str, Enum):
    """Consensus algorithm types"""
    SIMPLE_MAJORITY = "simple_majority"
    WEIGHTED_MAJORITY = "weighted_majority"
    BYZANTINE_FAULT_TOLERANT = "byzantine_fault_tolerant"
    PROOF_OF_STAKE = "proof_of_stake"
    DELEGATED = "delegated"


class RiskLevel(str, Enum):
    """Risk levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class SentimentScore(str, Enum):
    """Market sentiment scores"""
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"


@dataclass
class CollectiveDecision:
    """Collective decision result"""
    decision_id: str
    decision_type: str
    subject: str  # symbol, strategy, etc.
    algorithm: ConsensusAlgorithm
    participants: List[str]
    votes: Dict[str, Any]
    result: Dict[str, Any]
    confidence: float
    timestamp: str
    execution_time_ms: int


@dataclass
class RiskAssessment:
    """Multi-agent risk assessment"""
    assessment_id: str
    symbol: str
    assessors: List[str]
    individual_risks: Dict[str, float]
    collective_risk: float
    risk_level: RiskLevel
    factors: Dict[str, float]
    recommendations: List[str]
    timestamp: str


@dataclass
class MarketSentiment:
    """Aggregated market sentiment"""
    symbol: str
    sentiment_score: float  # -1.0 to 1.0
    sentiment_level: SentimentScore
    contributing_agents: List[str]
    individual_sentiments: Dict[str, float]
    confidence: float
    volume_weighted: bool
    timestamp: str


@dataclass
class PortfolioOptimization:
    """Collective portfolio optimization result"""
    optimization_id: str
    current_portfolio: Dict[str, float]
    recommended_portfolio: Dict[str, float]
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    participating_agents: List[str]
    algorithm_used: str
    timestamp: str


class CollectiveIntelligence:
    """Advanced collective intelligence system"""
    
    def __init__(self):
        self.redis = None
        self.running = False
        self.decision_history: List[CollectiveDecision] = []
        self.active_decisions: Dict[str, Dict[str, Any]] = {}
        self.agent_weights: Dict[str, float] = {}
        self.performance_tracking: Dict[str, Dict[str, float]] = defaultdict(dict)
        
    async def initialize(self):
        """Initialize collective intelligence system"""
        self.redis = await get_redis()
        await self._load_agent_weights()
        await self._load_performance_history()
        logger.info("Collective Intelligence system initialized")
        
    async def start(self):
        """Start the collective intelligence system"""
        await self.initialize()
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._decision_monitor())
        asyncio.create_task(self._performance_tracker())
        asyncio.create_task(self._sentiment_aggregator())
        asyncio.create_task(self._risk_monitor())
        
        logger.info("Collective Intelligence system started")
        
    async def stop(self):
        """Stop the collective intelligence system"""
        self.running = False
        logger.info("Collective Intelligence system stopped")
        
    # Consensus Algorithms
    
    async def make_collective_decision(self, 
                                     decision_type: str,
                                     subject: str,
                                     algorithm: ConsensusAlgorithm,
                                     timeout_seconds: int = 30,
                                     options: List[str] = None) -> Optional[CollectiveDecision]:
        """Make a collective decision using specified algorithm"""
        try:
            start_time = datetime.utcnow()
            decision_id = f"decision_{start_time.strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Get eligible agents
            eligible_agents = await self._get_eligible_agents(decision_type)
            
            if len(eligible_agents) < 2:
                logger.warning(f"Not enough agents for collective decision: {len(eligible_agents)}")
                return None
                
            # Initialize decision tracking
            self.active_decisions[decision_id] = {
                "type": decision_type,
                "subject": subject,
                "algorithm": algorithm,
                "participants": eligible_agents,
                "votes": {},
                "options": options or ["approve", "reject"],
                "start_time": start_time,
                "timeout": timeout_seconds
            }
            
            # Request votes from agents
            await self._request_votes(decision_id, eligible_agents, {
                "decision_type": decision_type,
                "subject": subject,
                "options": options or ["approve", "reject"]
            })
            
            # Wait for votes or timeout
            end_time = start_time + timedelta(seconds=timeout_seconds)
            while datetime.utcnow() < end_time and len(self.active_decisions[decision_id]["votes"]) < len(eligible_agents):
                await asyncio.sleep(0.5)
                
            # Process decision using specified algorithm
            result = await self._process_decision(decision_id, algorithm)
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            decision = CollectiveDecision(
                decision_id=decision_id,
                decision_type=decision_type,
                subject=subject,
                algorithm=algorithm,
                participants=eligible_agents,
                votes=self.active_decisions[decision_id]["votes"],
                result=result,
                confidence=result.get("confidence", 0.5),
                timestamp=datetime.utcnow().isoformat(),
                execution_time_ms=execution_time
            )
            
            # Store decision
            self.decision_history.append(decision)
            await self._store_decision(decision)
            
            # Clean up
            del self.active_decisions[decision_id]
            
            logger.info(f"Collective decision {decision_id} completed: {result}")
            return decision
            
        except Exception as e:
            logger.error(f"Error in collective decision making: {e}")
            return None
            
    async def _process_decision(self, decision_id: str, algorithm: ConsensusAlgorithm) -> Dict[str, Any]:
        """Process decision using specified consensus algorithm"""
        decision_data = self.active_decisions[decision_id]
        votes = decision_data["votes"]
        participants = decision_data["participants"]
        
        if algorithm == ConsensusAlgorithm.SIMPLE_MAJORITY:
            return await self._simple_majority(votes)
        elif algorithm == ConsensusAlgorithm.WEIGHTED_MAJORITY:
            return await self._weighted_majority(votes, participants)
        elif algorithm == ConsensusAlgorithm.BYZANTINE_FAULT_TOLERANT:
            return await self._byzantine_fault_tolerant(votes, participants)
        elif algorithm == ConsensusAlgorithm.PROOF_OF_STAKE:
            return await self._proof_of_stake(votes, participants)
        elif algorithm == ConsensusAlgorithm.DELEGATED:
            return await self._delegated_consensus(votes, participants)
        else:
            return await self._simple_majority(votes)
            
    async def _simple_majority(self, votes: Dict[str, str]) -> Dict[str, Any]:
        """Simple majority consensus"""
        if not votes:
            return {"approved": False, "confidence": 0.0, "reason": "no_votes"}
            
        vote_counts = Counter(votes.values())
        total_votes = len(votes)
        
        if not vote_counts:
            return {"approved": False, "confidence": 0.0, "reason": "no_valid_votes"}
            
        winner = vote_counts.most_common(1)[0]
        winning_vote = winner[0]
        winning_count = winner[1]
        
        confidence = winning_count / total_votes
        approved = winning_vote == "approve"
        
        return {
            "approved": approved,
            "confidence": confidence,
            "vote_distribution": dict(vote_counts),
            "algorithm": "simple_majority"
        }
        
    async def _weighted_majority(self, votes: Dict[str, str], participants: List[str]) -> Dict[str, Any]:
        """Weighted majority based on agent performance"""
        if not votes:
            return {"approved": False, "confidence": 0.0, "reason": "no_votes"}
            
        weighted_votes = defaultdict(float)
        total_weight = 0.0
        
        for agent_id, vote in votes.items():
            weight = self.agent_weights.get(agent_id, 1.0)
            weighted_votes[vote] += weight
            total_weight += weight
            
        if total_weight == 0:
            return await self._simple_majority(votes)
            
        # Find winning vote
        max_weight = max(weighted_votes.values())
        winning_votes = [vote for vote, weight in weighted_votes.items() if weight == max_weight]
        
        if len(winning_votes) > 1:
            # Tie - fall back to simple majority
            return await self._simple_majority(votes)
            
        winning_vote = winning_votes[0]
        confidence = max_weight / total_weight
        approved = winning_vote == "approve"
        
        return {
            "approved": approved,
            "confidence": confidence,
            "weighted_distribution": dict(weighted_votes),
            "total_weight": total_weight,
            "algorithm": "weighted_majority"
        }
        
    async def _byzantine_fault_tolerant(self, votes: Dict[str, str], participants: List[str]) -> Dict[str, Any]:
        """Byzantine fault tolerant consensus (simplified PBFT)"""
        n = len(participants)
        f = (n - 1) // 3  # Maximum number of Byzantine failures
        
        if len(votes) < 2 * f + 1:
            return {"approved": False, "confidence": 0.0, "reason": "insufficient_votes_for_bft"}
            
        vote_counts = Counter(votes.values())
        
        for vote_option, count in vote_counts.items():
            if count >= 2 * f + 1:
                confidence = count / len(votes)
                approved = vote_option == "approve"
                
                return {
                    "approved": approved,
                    "confidence": confidence,
                    "vote_distribution": dict(vote_counts),
                    "byzantine_threshold": 2 * f + 1,
                    "algorithm": "byzantine_fault_tolerant"
                }
                
        return {"approved": False, "confidence": 0.0, "reason": "no_bft_consensus"}
        
    async def _proof_of_stake(self, votes: Dict[str, str], participants: List[str]) -> Dict[str, Any]:
        """Proof of stake consensus based on agent stakes"""
        if not votes:
            return {"approved": False, "confidence": 0.0, "reason": "no_votes"}
            
        # Get agent stakes (could be based on portfolio value, performance, etc.)
        stakes = {}
        total_stake = 0.0
        
        for agent_id in participants:
            # Use performance as stake proxy
            stake = max(self.performance_tracking.get(agent_id, {}).get("total_return", 0.1), 0.1)
            stakes[agent_id] = stake
            total_stake += stake
            
        # Calculate weighted votes by stake
        weighted_votes = defaultdict(float)
        
        for agent_id, vote in votes.items():
            stake_weight = stakes.get(agent_id, 0.1) / total_stake
            weighted_votes[vote] += stake_weight
            
        # Find winner
        if not weighted_votes:
            return {"approved": False, "confidence": 0.0, "reason": "no_weighted_votes"}
            
        max_weight = max(weighted_votes.values())
        winning_votes = [vote for vote, weight in weighted_votes.items() if weight == max_weight]
        
        if len(winning_votes) > 1:
            return await self._simple_majority(votes)
            
        winning_vote = winning_votes[0]
        approved = winning_vote == "approve"
        
        return {
            "approved": approved,
            "confidence": max_weight,
            "stake_weighted_distribution": dict(weighted_votes),
            "total_stake": total_stake,
            "algorithm": "proof_of_stake"
        }
        
    async def _delegated_consensus(self, votes: Dict[str, str], participants: List[str]) -> Dict[str, Any]:
        """Delegated consensus - delegate to top performing agents"""
        if not votes:
            return {"approved": False, "confidence": 0.0, "reason": "no_votes"}
            
        # Select top 3 performing agents as delegates
        delegate_count = min(3, len(participants))
        
        # Sort agents by performance
        agent_performance = []
        for agent_id in participants:
            performance = self.performance_tracking.get(agent_id, {}).get("sharpe_ratio", 0.0)
            agent_performance.append((agent_id, performance))
            
        agent_performance.sort(key=lambda x: x[1], reverse=True)
        delegates = [agent_id for agent_id, _ in agent_performance[:delegate_count]]
        
        # Only count delegate votes
        delegate_votes = {agent_id: vote for agent_id, vote in votes.items() if agent_id in delegates}
        
        if not delegate_votes:
            return await self._simple_majority(votes)
            
        # Simple majority among delegates
        result = await self._simple_majority(delegate_votes)
        result["algorithm"] = "delegated"
        result["delegates"] = delegates
        result["delegate_votes"] = delegate_votes
        
        return result
        
    # Risk Assessment
    
    async def assess_collective_risk(self, symbol: str, position_size: float = None) -> RiskAssessment:
        """Perform collective risk assessment"""
        try:
            assessment_id = f"risk_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Get risk-capable agents
            risk_agents = await self._get_risk_agents()
            
            if not risk_agents:
                logger.warning("No risk agents available for assessment")
                return None
                
            # Request risk assessments from agents
            individual_risks = {}
            risk_factors = defaultdict(list)
            recommendations = []
            
            # Get market data for risk calculation
            current_price = await market_data_service.get_current_price(symbol)
            historical_data = await market_data_service.get_historical_data(symbol, "30d", "1d")
            technical_indicators = await market_data_service.get_technical_indicators(symbol)
            
            # Calculate base risk metrics
            volatility = 0.0
            if historical_data is not None and len(historical_data) > 1:
                returns = historical_data['Close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Annualized volatility
                
            # Simulate individual agent risk assessments
            for agent_id in risk_agents:
                # Each agent may have different risk models
                agent_risk = await self._simulate_agent_risk_assessment(
                    agent_id, symbol, current_price, volatility, technical_indicators, position_size
                )
                individual_risks[agent_id] = agent_risk["risk_score"]
                
                # Collect risk factors
                for factor, value in agent_risk["factors"].items():
                    risk_factors[factor].append(value)
                    
                recommendations.extend(agent_risk["recommendations"])
                
            # Aggregate risk scores
            if individual_risks:
                risk_scores = list(individual_risks.values())
                collective_risk = statistics.mean(risk_scores)
                
                # Determine risk level
                if collective_risk <= 0.2:
                    risk_level = RiskLevel.VERY_LOW
                elif collective_risk <= 0.4:
                    risk_level = RiskLevel.LOW
                elif collective_risk <= 0.6:
                    risk_level = RiskLevel.MEDIUM
                elif collective_risk <= 0.8:
                    risk_level = RiskLevel.HIGH
                else:
                    risk_level = RiskLevel.VERY_HIGH
                    
                # Aggregate factors
                aggregated_factors = {}
                for factor, values in risk_factors.items():
                    aggregated_factors[factor] = statistics.mean(values)
                    
                assessment = RiskAssessment(
                    assessment_id=assessment_id,
                    symbol=symbol,
                    assessors=risk_agents,
                    individual_risks=individual_risks,
                    collective_risk=collective_risk,
                    risk_level=risk_level,
                    factors=aggregated_factors,
                    recommendations=list(set(recommendations)),  # Remove duplicates
                    timestamp=datetime.utcnow().isoformat()
                )
                
                # Store assessment
                await self._store_risk_assessment(assessment)
                
                logger.info(f"Collective risk assessment completed for {symbol}: {risk_level.value}")
                return assessment
                
        except Exception as e:
            logger.error(f"Error in collective risk assessment: {e}")
            return None
            
    # Market Sentiment Aggregation
    
    async def aggregate_market_sentiment(self, symbol: str) -> MarketSentiment:
        """Aggregate market sentiment from multiple agents"""
        try:
            # Get sentiment-capable agents
            sentiment_agents = await self._get_sentiment_agents()
            
            if not sentiment_agents:
                logger.warning("No sentiment agents available")
                return None
                
            individual_sentiments = {}
            confidence_scores = []
            
            # Get sentiment from each agent
            for agent_id in sentiment_agents:
                sentiment_data = await self._get_agent_sentiment(agent_id, symbol)
                if sentiment_data:
                    individual_sentiments[agent_id] = sentiment_data["sentiment"]
                    confidence_scores.append(sentiment_data["confidence"])
                    
            if not individual_sentiments:
                return None
                
            # Aggregate sentiments
            sentiments = list(individual_sentiments.values())
            
            # Weighted average by confidence
            if confidence_scores:
                weighted_sentiment = sum(s * c for s, c in zip(sentiments, confidence_scores)) / sum(confidence_scores)
                overall_confidence = statistics.mean(confidence_scores)
            else:
                weighted_sentiment = statistics.mean(sentiments)
                overall_confidence = 0.5
                
            # Determine sentiment level
            if weighted_sentiment <= -0.6:
                sentiment_level = SentimentScore.VERY_BEARISH
            elif weighted_sentiment <= -0.2:
                sentiment_level = SentimentScore.BEARISH
            elif weighted_sentiment <= 0.2:
                sentiment_level = SentimentScore.NEUTRAL
            elif weighted_sentiment <= 0.6:
                sentiment_level = SentimentScore.BULLISH
            else:
                sentiment_level = SentimentScore.VERY_BULLISH
                
            sentiment = MarketSentiment(
                symbol=symbol,
                sentiment_score=weighted_sentiment,
                sentiment_level=sentiment_level,
                contributing_agents=list(individual_sentiments.keys()),
                individual_sentiments=individual_sentiments,
                confidence=overall_confidence,
                volume_weighted=False,  # Could be enhanced
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Store sentiment
            await self._store_market_sentiment(sentiment)
            
            logger.info(f"Market sentiment aggregated for {symbol}: {sentiment_level.value}")
            return sentiment
            
        except Exception as e:
            logger.error(f"Error aggregating market sentiment: {e}")
            return None
    
    async def _get_sentiment_agents(self) -> List[str]:
        """Get agents capable of sentiment analysis"""
        # For now, return all active agents
        # In production, filter by agent capabilities
        return list(self.agent_weights.keys())
    
    async def _get_agent_sentiment(self, agent_id: str, symbol: str) -> Optional[Dict]:
        """Get sentiment analysis from a specific agent"""
        # Simplified implementation - in production would query agent
        import random
        return {
            "sentiment": random.uniform(-1, 1),
            "confidence": random.uniform(0.5, 1.0)
        }
            
    # Portfolio Optimization
    
    async def optimize_portfolio_collectively(self, current_portfolio: Dict[str, float]) -> PortfolioOptimization:
        """Collective portfolio optimization"""
        try:
            optimization_id = f"portfolio_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Get portfolio-capable agents
            portfolio_agents = await self._get_portfolio_agents()
            
            if not portfolio_agents:
                logger.warning("No portfolio agents available")
                return None
                
            # Get optimization suggestions from agents
            optimization_suggestions = []
            
            for agent_id in portfolio_agents:
                suggestion = await self._get_portfolio_suggestion(agent_id, current_portfolio)
                if suggestion:
                    optimization_suggestions.append(suggestion)
                    
            if not optimization_suggestions:
                return None
                
            # Aggregate suggestions using ensemble method
            recommended_portfolio = await self._aggregate_portfolio_suggestions(
                optimization_suggestions, current_portfolio
            )
            
            # Calculate expected metrics
            expected_return = await self._calculate_expected_return(recommended_portfolio)
            expected_risk = await self._calculate_expected_risk(recommended_portfolio)
            sharpe_ratio = expected_return / expected_risk if expected_risk > 0 else 0.0
            
            optimization = PortfolioOptimization(
                optimization_id=optimization_id,
                current_portfolio=current_portfolio,
                recommended_portfolio=recommended_portfolio,
                expected_return=expected_return,
                expected_risk=expected_risk,
                sharpe_ratio=sharpe_ratio,
                participating_agents=portfolio_agents,
                algorithm_used="ensemble_weighted_average",
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Store optimization
            await self._store_portfolio_optimization(optimization)
            
            logger.info(f"Portfolio optimization completed: Expected Sharpe ratio {sharpe_ratio:.3f}")
            return optimization
            
        except Exception as e:
            logger.error(f"Error in portfolio optimization: {e}")
            return None
            
    # Decision Logging and Analytics
    
    async def get_decision_history(self, limit: int = 100) -> List[CollectiveDecision]:
        """Get decision history"""
        try:
            decisions = await self.redis.lrange("decisions:history", 0, limit - 1)
            
            decision_objects = []
            for decision_data in decisions:
                decision_dict = json.loads(decision_data)
                decision_objects.append(CollectiveDecision(**decision_dict))
                
            return decision_objects
            
        except Exception as e:
            logger.error(f"Error getting decision history: {e}")
            return []
            
    async def analyze_decision_performance(self) -> Dict[str, Any]:
        """Analyze collective decision performance"""
        try:
            decisions = await self.get_decision_history(1000)
            
            if not decisions:
                return {"error": "No decisions to analyze"}
                
            # Performance metrics
            total_decisions = len(decisions)
            approved_decisions = sum(1 for d in decisions if d.result.get("approved", False))
            
            # Algorithm performance
            algorithm_performance = defaultdict(list)
            for decision in decisions:
                algorithm_performance[decision.algorithm.value].append(decision.confidence)
                
            # Average confidence by algorithm
            avg_confidence_by_algorithm = {}
            for algorithm, confidences in algorithm_performance.items():
                avg_confidence_by_algorithm[algorithm] = statistics.mean(confidences)
                
            # Execution time analysis
            execution_times = [d.execution_time_ms for d in decisions]
            avg_execution_time = statistics.mean(execution_times) if execution_times else 0
            
            return {
                "total_decisions": total_decisions,
                "approved_rate": approved_decisions / total_decisions if total_decisions > 0 else 0,
                "avg_confidence_by_algorithm": avg_confidence_by_algorithm,
                "avg_execution_time_ms": avg_execution_time,
                "decision_types": dict(Counter(d.decision_type for d in decisions)),
                "recent_performance": self._analyze_recent_performance(decisions[-50:]) if len(decisions) >= 50 else {}
            }
            
        except Exception as e:
            logger.error(f"Error analyzing decision performance: {e}")
            return {"error": str(e)}
            
    # Private Helper Methods
    
    async def _get_eligible_agents(self, decision_type: str) -> List[str]:
        """Get agents eligible for a decision type"""
        if not hasattr(agent_manager, 'agents'):
            return []
            
        eligible = []
        for agent_id, agent in agent_manager.agents.items():
            if agent.get("status") == "active":
                agent_type = agent.get("type", "")
                
                if decision_type == "trade" and agent_type in ["trading", "portfolio"]:
                    eligible.append(agent_id)
                elif decision_type == "risk" and agent_type in ["risk", "trading", "portfolio"]:
                    eligible.append(agent_id)
                elif decision_type == "strategy" and agent_type in ["trading", "analysis", "portfolio"]:
                    eligible.append(agent_id)
                elif decision_type == "general":
                    eligible.append(agent_id)
                    
        return eligible
        
    async def _request_votes(self, decision_id: str, agents: List[str], context: Dict[str, Any]):
        """Request votes from agents"""
        for agent_id in agents:
            message = AgentMessage(
                message_id=f"vote_request_{decision_id}",
                message_type=MessageType.CONSENSUS_REQUEST,
                sender_id="collective_intelligence",
                recipient_id=agent_id,
                content={
                    "decision_id": decision_id,
                    "context": context,
                    "timeout": 30
                },
                timestamp=datetime.utcnow().isoformat(),
                requires_response=True
            )
            
            await agent_manager.send_message(message)
            
    async def _store_decision(self, decision: CollectiveDecision):
        """Store decision in history"""
        await self.redis.lpush("decisions:history", json.dumps(asdict(decision)))
        await self.redis.ltrim("decisions:history", 0, 9999)  # Keep last 10k decisions
        
    async def _load_agent_weights(self):
        """Load agent performance weights"""
        try:
            weights_data = await self.redis.hgetall("agent_weights")
            for agent_id, weight in weights_data.items():
                self.agent_weights[agent_id.decode()] = float(weight)
        except Exception as e:
            logger.error(f"Error loading agent weights: {e}")
            
    async def _load_performance_history(self):
        """Load agent performance history"""
        try:
            performance_keys = await self.redis.keys("performance:*")
            for key in performance_keys:
                agent_id = key.decode().split(":")[-1]
                performance_data = await self.redis.hgetall(key)
                
                performance = {}
                for metric, value in performance_data.items():
                    try:
                        performance[metric.decode()] = float(value)
                    except ValueError:
                        performance[metric.decode()] = value.decode()
                        
                self.performance_tracking[agent_id] = performance
                
        except Exception as e:
            logger.error(f"Error loading performance history: {e}")
            
    # Background Tasks
    
    async def _decision_monitor(self):
        """Monitor active decisions"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                expired_decisions = []
                
                for decision_id, decision_data in self.active_decisions.items():
                    start_time = decision_data["start_time"]
                    timeout = decision_data["timeout"]
                    
                    if (current_time - start_time).total_seconds() > timeout:
                        expired_decisions.append(decision_id)
                        
                # Clean up expired decisions
                for decision_id in expired_decisions:
                    logger.warning(f"Decision {decision_id} expired")
                    del self.active_decisions[decision_id]
                    
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in decision monitor: {e}")
                await asyncio.sleep(5)
                
    async def _performance_tracker(self):
        """Track agent performance"""
        while self.running:
            try:
                # Update agent weights based on recent performance
                for agent_id in list(self.agent_weights.keys()):
                    performance = self.performance_tracking.get(agent_id, {})
                    
                    # Calculate weight based on Sharpe ratio and success rate
                    sharpe_ratio = performance.get("sharpe_ratio", 0.0)
                    success_rate = performance.get("success_rate", 0.5)
                    
                    # Weight formula (can be customized)
                    weight = max(0.1, min(2.0, (sharpe_ratio + success_rate) / 2))
                    self.agent_weights[agent_id] = weight
                    
                # Save updated weights
                if self.agent_weights:
                    await self.redis.hset("agent_weights", mapping={
                        agent_id: str(weight) for agent_id, weight in self.agent_weights.items()
                    })
                    
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in performance tracker: {e}")
                await asyncio.sleep(300)
                
    async def _sentiment_aggregator(self):
        """Continuously aggregate market sentiment"""
        # Wait before starting to allow agents to register
        await asyncio.sleep(5)
        
        while self.running:
            try:
                # Get top symbols to analyze
                symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "BTC", "ETH"]  # Can be dynamic
                
                for symbol in symbols:
                    sentiment = await self.aggregate_market_sentiment(symbol)
                    if sentiment:
                        # Store in time series for trend analysis
                        await self.redis.zadd(
                            f"sentiment_history:{symbol}",
                            {json.dumps(asdict(sentiment)): datetime.utcnow().timestamp()}
                        )
                        
                        # Keep only recent data
                        await self.redis.zremrangebyrank(f"sentiment_history:{symbol}", 0, -1001)
                        
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in sentiment aggregator: {e}")
                await asyncio.sleep(300)
                
    async def _risk_monitor(self):
        """Monitor collective risk across portfolio"""
        while self.running:
            try:
                # Get current positions
                position_keys = await self.redis.keys("position:*")
                symbols = set()
                
                for key in position_keys:
                    position_data = await self.redis.hgetall(key)
                    if position_data:
                        symbol = position_data.get(b"symbol", b"").decode()
                        if symbol:
                            symbols.add(symbol)
                            
                # Assess risk for each symbol
                for symbol in symbols:
                    assessment = await self.assess_collective_risk(symbol)
                    if assessment and assessment.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
                        # Send risk alert
                        await self._send_risk_alert(symbol, assessment)
                        
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in risk monitor: {e}")
                await asyncio.sleep(300)
                
    # Additional helper methods would go here...
    
    async def _simulate_agent_risk_assessment(self, agent_id: str, symbol: str, 
                                           current_price: float, volatility: float,
                                           technical_indicators: Dict[str, Any],
                                           position_size: float = None) -> Dict[str, Any]:
        """Simulate individual agent risk assessment"""
        # This would be replaced by actual agent communication in production
        base_risk = min(volatility, 1.0)  # Cap at 100%
        
        # Add some agent-specific variation
        agent_factor = hash(agent_id) % 100 / 1000  # -0.05 to +0.05
        risk_score = max(0.0, min(1.0, base_risk + agent_factor))
        
        factors = {
            "volatility": volatility,
            "technical_risk": 0.3 if technical_indicators.get("rsi", 50) > 70 else 0.1,
            "market_risk": 0.2,  # Could be calculated from market conditions
            "liquidity_risk": 0.1  # Could be based on volume data
        }
        
        recommendations = []
        if risk_score > 0.7:
            recommendations.append("reduce_position")
        elif risk_score < 0.3:
            recommendations.append("consider_increase")
            
        return {
            "risk_score": risk_score,
            "factors": factors,
            "recommendations": recommendations
        }
        
    # More helper methods would continue here...


# Global collective intelligence instance
collective_intelligence = CollectiveIntelligence()