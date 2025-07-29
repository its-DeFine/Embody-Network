"""
AutoGen Multi-Agent Teams for AI-powered trading decisions.
Clean implementation with specialized agents working together.
"""

import logging
from typing import Dict, List, Any, Optional
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

logger = logging.getLogger(__name__)


class TradingTeamBase:
    """Base class for AutoGen trading teams."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_config = {
            "model": config.get("model", "gpt-4"),
            "api_key": config.get("api_key"),
            "temperature": config.get("temperature", 0.7),
        }
        self.agents = []
        self.chat_history = []
        
    def create_agent(self, name: str, role: str, system_message: str) -> AssistantAgent:
        """Create a specialized agent for the team."""
        agent = AssistantAgent(
            name=name,
            system_message=system_message,
            llm_config=self.llm_config,
        )
        self.agents.append(agent)
        return agent
        
    async def deliberate(self, topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Team deliberation on a topic with provided data."""
        raise NotImplementedError("Subclasses must implement deliberate()")


class MarketAnalysisTeam(TradingTeamBase):
    """
    AutoGen team for comprehensive market analysis.
    Multiple agents analyze different aspects of the market.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._create_team()
        
    def _create_team(self):
        """Create the market analysis team agents."""
        
        # Technical Analyst Agent
        self.technical_analyst = self.create_agent(
            name="technical_analyst",
            role="Technical Analysis Expert",
            system_message="""You are a technical analysis expert for cryptocurrency trading.
            Analyze price patterns, support/resistance levels, and technical indicators.
            Focus on: trend direction, momentum, volume patterns, and key levels.
            Provide clear BUY/SELL/HOLD signals with confidence levels."""
        )
        
        # Fundamental Analyst Agent
        self.fundamental_analyst = self.create_agent(
            name="fundamental_analyst",
            role="Market Fundamentals Expert",
            system_message="""You are a cryptocurrency fundamental analyst.
            Evaluate market conditions, news sentiment, and on-chain metrics.
            Consider: market fear/greed, major news events, protocol updates.
            Provide insights on market strength and potential catalysts."""
        )
        
        # Risk Manager Agent
        self.risk_manager = self.create_agent(
            name="risk_manager",
            role="Risk Management Specialist",
            system_message="""You are a risk management specialist for trading.
            Assess risk/reward ratios, position sizing, and market volatility.
            Focus on: maximum drawdown, portfolio exposure, correlation risks.
            Recommend appropriate stop losses and position sizes."""
        )
        
        # Coordinator Agent
        self.coordinator = self.create_agent(
            name="coordinator",
            role="Team Coordinator",
            system_message="""You coordinate the trading team's analysis.
            Synthesize insights from technical, fundamental, and risk analysis.
            Build consensus and provide final trading recommendations.
            Output format: {action: BUY/SELL/HOLD, confidence: 0-100, reasoning: string}"""
        )
        
    async def deliberate(self, topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Team deliberation on market conditions.
        
        Args:
            topic: What to analyze (e.g., "BTC trading opportunity")
            data: Market data including price, volume, indicators
            
        Returns:
            Team consensus with action, confidence, and reasoning
        """
        # Create group chat for team discussion
        group_chat = GroupChat(
            agents=self.agents,
            messages=[],
            max_round=self.config.get("max_rounds", 5)
        )
        
        # Create group chat manager
        manager = GroupChatManager(groupchat=group_chat, llm_config=self.llm_config)
        
        # Format the analysis request
        analysis_prompt = f"""
        Analyze {topic} with the following market data:
        
        Price: ${data.get('price', 0):.2f}
        24h Change: {data.get('change_24h', 0):.1f}%
        Volume: ${data.get('volume', 0):,.0f}
        Market Cap: ${data.get('market_cap', 0):,.0f}
        Fear/Greed Index: {data.get('fear_greed', 50)}/100
        
        Each specialist should provide their analysis.
        Coordinator should synthesize and provide final recommendation.
        """
        
        # Initiate team discussion
        user_proxy = UserProxyAgent(
            name="user",
            system_message="You request market analysis from the team.",
            code_execution_config=False,
            human_input_mode="NEVER",
        )
        
        # Start the conversation
        user_proxy.initiate_chat(
            manager,
            message=analysis_prompt,
            clear_history=True
        )
        
        # Extract team consensus from chat history
        consensus = self._extract_consensus(group_chat.messages)
        
        logger.info(f"Market Analysis Team Consensus: {consensus}")
        return consensus
        
    def _extract_consensus(self, messages: List[Dict]) -> Dict[str, Any]:
        """Extract the final consensus from team discussion."""
        # Look for coordinator's final message
        for message in reversed(messages):
            if message.get("name") == "coordinator":
                content = message.get("content", "")
                # Parse coordinator's structured output
                try:
                    # Simple parsing - in production use proper JSON parsing
                    if "BUY" in content.upper():
                        action = "BUY"
                    elif "SELL" in content.upper():
                        action = "SELL"
                    else:
                        action = "HOLD"
                        
                    # Extract confidence (look for percentage)
                    import re
                    confidence_match = re.search(r'(\d+)%', content)
                    confidence = int(confidence_match.group(1)) if confidence_match else 50
                    
                    return {
                        "action": action,
                        "confidence": confidence,
                        "reasoning": content,
                        "team": "market_analysis"
                    }
                except:
                    pass
                    
        # Default if parsing fails
        return {
            "action": "HOLD",
            "confidence": 0,
            "reasoning": "Unable to reach consensus",
            "team": "market_analysis"
        }


class ExecutionTeam(TradingTeamBase):
    """
    AutoGen team for trade execution decisions.
    Focuses on entry points, exits, and position sizing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._create_team()
        
    def _create_team(self):
        """Create the execution team agents."""
        
        # Entry Strategist Agent
        self.entry_strategist = self.create_agent(
            name="entry_strategist",
            role="Entry Point Specialist",
            system_message="""You are an entry point specialist for trading.
            Determine optimal entry prices and timing for positions.
            Consider: support levels, momentum, order book depth.
            Recommend specific entry strategies (market, limit, scaled)."""
        )
        
        # Exit Strategist Agent
        self.exit_strategist = self.create_agent(
            name="exit_strategist",
            role="Exit Strategy Expert",
            system_message="""You are an exit strategy expert.
            Design stop loss and take profit levels for trades.
            Consider: volatility, support/resistance, risk/reward ratios.
            Recommend trailing stops and partial exit strategies."""
        )
        
        # Position Sizer Agent
        self.position_sizer = self.create_agent(
            name="position_sizer",
            role="Position Sizing Specialist",
            system_message="""You are a position sizing specialist.
            Calculate optimal position sizes based on risk parameters.
            Consider: account size, volatility, correlation, max drawdown.
            Recommend position size as percentage of portfolio."""
        )
        
        # Executor Agent
        self.executor = self.create_agent(
            name="executor",
            role="Trade Executor",
            system_message="""You are the trade execution coordinator.
            Synthesize entry, exit, and sizing recommendations.
            Provide final execution plan with all parameters.
            Output format: {entry_price, stop_loss, take_profit, position_size_pct}"""
        )
        
    async def deliberate(self, topic: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Team deliberation on trade execution.
        
        Args:
            topic: Trade to execute (e.g., "BTC long position")
            data: Market data and analysis results
            
        Returns:
            Execution parameters
        """
        # Create group chat
        group_chat = GroupChat(
            agents=self.agents,
            messages=[],
            max_round=self.config.get("max_rounds", 4)
        )
        
        manager = GroupChatManager(groupchat=group_chat, llm_config=self.llm_config)
        
        # Format execution request
        execution_prompt = f"""
        Plan execution for {topic}:
        
        Current Price: ${data.get('price', 0):.2f}
        Market Analysis: {data.get('analysis', {}).get('action', 'BUY')}
        Confidence: {data.get('analysis', {}).get('confidence', 70)}%
        Account Balance: ${data.get('balance', 100):.2f}
        Max Position Size: {data.get('max_position_pct', 30)}%
        
        Each specialist should provide their recommendations.
        Executor should provide final execution parameters.
        """
        
        # Initiate discussion
        user_proxy = UserProxyAgent(
            name="user",
            system_message="You request execution plan from the team.",
            code_execution_config=False,
            human_input_mode="NEVER",
        )
        
        user_proxy.initiate_chat(
            manager,
            message=execution_prompt,
            clear_history=True
        )
        
        # Extract execution plan
        execution_plan = self._extract_execution_plan(group_chat.messages)
        
        logger.info(f"Execution Team Plan: {execution_plan}")
        return execution_plan
        
    def _extract_execution_plan(self, messages: List[Dict]) -> Dict[str, Any]:
        """Extract execution parameters from team discussion."""
        # Look for executor's final message
        for message in reversed(messages):
            if message.get("name") == "executor":
                content = message.get("content", "")
                
                # Extract execution parameters
                # In production, use structured output parsing
                import re
                
                price_match = re.search(r'entry.*?(\d+\.?\d*)', content, re.I)
                stop_match = re.search(r'stop.*?(\d+\.?\d*)', content, re.I)
                target_match = re.search(r'(target|profit).*?(\d+\.?\d*)', content, re.I)
                size_match = re.search(r'size.*?(\d+)%', content, re.I)
                
                return {
                    "entry_price": float(price_match.group(1)) if price_match else None,
                    "stop_loss": float(stop_match.group(1)) if stop_match else None,
                    "take_profit": float(target_match.group(2)) if target_match else None,
                    "position_size_pct": int(size_match.group(1)) if size_match else 20,
                    "execution_type": "limit",
                    "reasoning": content,
                    "team": "execution"
                }
                
        # Default conservative execution
        return {
            "entry_price": None,  # Market order
            "stop_loss": 0.95,    # 5% stop
            "take_profit": 1.10,  # 10% target
            "position_size_pct": 10,
            "execution_type": "market",
            "reasoning": "Default conservative execution",
            "team": "execution"
        }


class AutoGenTeamManager:
    """
    Manages all AutoGen teams and coordinates their activities.
    Single point of access for the event system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.teams = {
            'market_analysis': MarketAnalysisTeam(config.get('market_analysis', {})),
            'execution': ExecutionTeam(config.get('execution', {}))
        }
        
    async def get_market_analysis(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get market analysis from the analysis team."""
        team = self.teams['market_analysis']
        topic = f"{symbol} trading opportunity"
        return await team.deliberate(topic, market_data)
        
    async def get_execution_plan(self, symbol: str, analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get execution plan from the execution team."""
        team = self.teams['execution']
        topic = f"{symbol} {analysis['action'].lower()} position"
        
        data = {
            'price': context.get('price', 0),
            'analysis': analysis,
            'balance': context.get('balance', 100),
            'max_position_pct': context.get('max_position_pct', 30)
        }
        
        return await team.deliberate(topic, data)