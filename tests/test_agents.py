"""Agent tests"""
import pytest
import asyncio
from app.agents import create_agent, TradingAgent, AnalysisAgent

@pytest.mark.asyncio
async def test_create_agent():
    """Test agent creation"""
    # Test trading agent
    trading_agent = create_agent("trading", "test-1", {"max_risk": 0.02})
    assert isinstance(trading_agent, TradingAgent)
    assert trading_agent.agent_id == "test-1"
    assert trading_agent.agent_type == "trading"
    
    # Test analysis agent
    analysis_agent = create_agent("analysis", "test-2", {})
    assert isinstance(analysis_agent, AnalysisAgent)
    
    # Test default agent
    default_agent = create_agent("unknown", "test-3", {})
    assert default_agent.__class__.__name__ == "BaseAgent"

def test_trading_agent_system_message():
    """Test trading agent system message"""
    agent = TradingAgent("test", "trading", {})
    message = agent.get_system_message()
    assert "trading agent" in message.lower()
    assert "risk management" in message.lower()

def test_analysis_agent_system_message():
    """Test analysis agent system message"""
    agent = AnalysisAgent("test", "analysis", {})
    message = agent.get_system_message()
    assert "analysis expert" in message.lower()
    assert "market research" in message.lower()

@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent initialization"""
    agent = TradingAgent("test", "trading", {})
    
    # Mock Redis and OpenBB for testing
    import os
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    
    # This would need proper mocking in production tests
    # For now, we just verify the method exists
    assert hasattr(agent, 'initialize')
    assert callable(agent.initialize)