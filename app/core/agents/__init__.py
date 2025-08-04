"""Agent implementations"""
from .base_agent import BaseAgent
from .trading_agent import TradingAgent
from .analysis_agent import AnalysisAgent

# Agent factory
def create_agent(agent_type: str, agent_id: str, config: dict) -> BaseAgent:
    """Create an agent based on type"""
    agents = {
        "trading": TradingAgent,
        "analysis": AnalysisAgent,
        "risk": BaseAgent,  # Use base for now
        "portfolio": BaseAgent  # Use base for now
    }
    
    agent_class = agents.get(agent_type, BaseAgent)
    return agent_class(agent_id, agent_type, config)

__all__ = ["BaseAgent", "TradingAgent", "AnalysisAgent", "create_agent"]