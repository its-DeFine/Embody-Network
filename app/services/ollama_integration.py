"""
Ollama Integration for Local LLM Support
Allows agents to use Ollama models instead of OpenAI
"""

import os
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


class OllamaProvider:
    """
    Ollama provider for local LLM inference
    Supports all Ollama models including Llama, Mistral, Phi, etc.
    """
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama2")
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes for long responses
        
    async def check_health(self) -> bool:
        """Check if Ollama is running"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        logger.info(f"Ollama is running with models: {models}")
                        return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
        return False
        
    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
        return []
        
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama library"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name}
                ) as response:
                    async for line in response.content:
                        if line:
                            data = json.loads(line)
                            if "status" in data:
                                logger.info(f"Pulling {model_name}: {data['status']}")
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
        return False
        
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ):
        """Generate text using Ollama"""
        
        # Build the full prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = prompt
            
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    if stream:
                        async for line in response.content:
                            if line:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                    else:
                        text = await response.text()
                        lines = text.strip().split('\n')
                        full_response = ""
                        for line in lines:
                            if line:
                                data = json.loads(line)
                                if "response" in data:
                                    full_response += data["response"]
                        yield full_response
                        
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            yield f"Error: {str(e)}"
                
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """Chat completion compatible interface"""
        
        # Convert messages to prompt
        prompt = ""
        system_prompt = None
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                prompt += f"\nUser: {content}"
            elif role == "assistant":
                prompt += f"\nAssistant: {content}"
                
        prompt += "\nAssistant:"
        
        # Generate response
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )
        
        return response


class OllamaAgent:
    """
    Agent that uses Ollama for reasoning
    """
    
    def __init__(self, model: str = "llama2", role: str = "trading"):
        self.provider = OllamaProvider(model=model)
        self.role = role
        self.context = []
        
        # Role-specific system prompts
        self.system_prompts = {
            "trading": """You are an expert trading agent. Analyze market data and make informed trading decisions. 
                         Consider risk management, market trends, and technical indicators. Be precise with numbers.""",
            
            "analysis": """You are a financial analyst. Provide detailed market analysis, identify patterns, 
                          and explain market movements. Use technical and fundamental analysis.""",
            
            "risk": """You are a risk management specialist. Evaluate trading risks, set appropriate stop losses,
                      and ensure portfolio safety. Be conservative and protect capital.""",
            
            "arbitrage": """You are an arbitrage specialist. Identify price discrepancies across exchanges,
                           calculate profit potential, and consider transaction costs."""
        }
        
    async def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data and provide insights"""
        
        prompt = f"""Analyze this market data and provide trading insights:

Market Data:
{json.dumps(market_data, indent=2)}

Provide:
1. Market trend (bullish/bearish/neutral)
2. Key support and resistance levels
3. Trading recommendation
4. Risk assessment
5. Confidence level (0-100%)

Format as JSON."""

        response_parts = []
        async for part in self.provider.generate(
            prompt=prompt,
            system_prompt=self.system_prompts.get(self.role, ""),
            temperature=0.3  # Lower temperature for more consistent analysis
        ):
            response_parts.append(part)
        response = "".join(response_parts)
        
        # Try to parse JSON response
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
            
        # Fallback response
        return {
            "trend": "neutral",
            "recommendation": "hold",
            "confidence": 50,
            "analysis": response
        }
        
    async def make_trading_decision(
        self,
        symbol: str,
        current_price: float,
        portfolio: Dict[str, Any],
        market_sentiment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make a trading decision"""
        
        prompt = f"""Make a trading decision for {symbol}:

Current Price: ${current_price}
Portfolio Cash: ${portfolio.get('cash', 0)}
Current Position: {portfolio.get('positions', {}).get(symbol, 0)} shares
Market Sentiment: {market_sentiment or 'neutral'}

Should we BUY, SELL, or HOLD? If BUY/SELL, how many shares?

Respond with JSON: {{"action": "buy/sell/hold", "quantity": 0, "reason": "explanation"}}"""

        response_parts = []
        async for part in self.provider.generate(
            prompt=prompt,
            system_prompt=self.system_prompts["trading"],
            temperature=0.5
        ):
            response_parts.append(part)
        response = "".join(response_parts)
        
        # Parse response
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass
            
        return {"action": "hold", "quantity": 0, "reason": "Unable to parse decision"}
        
    async def evaluate_risk(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate risk for a potential trade"""
        
        prompt = f"""Evaluate the risk of this trade:

Trade Details:
{json.dumps(trade, indent=2)}

Provide risk assessment with:
1. Risk score (0-100, where 100 is highest risk)
2. Potential downside
3. Recommended stop loss
4. Position sizing recommendation
5. Overall recommendation (approve/reject/modify)

Format as JSON."""

        response_parts = []
        async for part in self.provider.generate(
            prompt=prompt,
            system_prompt=self.system_prompts["risk"],
            temperature=0.3
        ):
            response_parts.append(part)
        response = "".join(response_parts)
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except:
            pass
            
        return {
            "risk_score": 50,
            "recommendation": "hold",
            "analysis": response
        }


class OllamaAgentManager:
    """
    Manages multiple Ollama agents
    """
    
    def __init__(self):
        self.agents = {}
        self.available_models = []
        self.provider = OllamaProvider()
        
    async def initialize(self):
        """Initialize Ollama connection"""
        # Check if Ollama is running
        if await self.provider.check_health():
            self.available_models = await self.provider.list_models()
            logger.info(f"Ollama initialized with models: {self.available_models}")
            
            # Ensure we have at least one model
            if not self.available_models:
                logger.info("No models found, pulling llama2...")
                if await self.provider.pull_model("llama2"):
                    self.available_models = ["llama2"]
        else:
            logger.warning("Ollama not available - agents will use fallback logic")
            
    def create_agent(self, agent_id: str, model: str = None, role: str = "trading") -> OllamaAgent:
        """Create a new Ollama agent"""
        if not model:
            model = self.available_models[0] if self.available_models else "llama2"
            
        agent = OllamaAgent(model=model, role=role)
        self.agents[agent_id] = agent
        
        logger.info(f"Created Ollama agent {agent_id} with model {model} for role {role}")
        return agent
        
    def get_agent(self, agent_id: str) -> Optional[OllamaAgent]:
        """Get an existing agent"""
        return self.agents.get(agent_id)
        
    async def consult_agents(self, question: str, agent_roles: List[str] = None) -> Dict[str, Any]:
        """Get opinions from multiple agents"""
        if not agent_roles:
            agent_roles = ["trading", "analysis", "risk"]
            
        responses = {}
        
        for role in agent_roles:
            agent = self.create_agent(f"temp_{role}", role=role)
            
            response_parts = []
            async for part in agent.provider.generate(
                prompt=question,
                system_prompt=agent.system_prompts[role],
                temperature=0.7
            ):
                response_parts.append(part)
            response = "".join(response_parts)
            
            responses[role] = response
            
        return responses
        
    def get_status(self) -> Dict[str, Any]:
        """Get Ollama status"""
        return {
            "available": len(self.available_models) > 0,
            "models": self.available_models,
            "active_agents": len(self.agents),
            "agent_ids": list(self.agents.keys())
        }


# Global instance
ollama_manager = OllamaAgentManager()