"""
Ollama API endpoints
Manage local LLM models for agents
"""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging

from ..dependencies import get_current_user
from ..services.ollama_integration import ollama_manager
from ..core.agents.agent_manager import agent_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ollama",
    tags=["ollama"],
    dependencies=[Depends(get_current_user)]
)


class OllamaModelRequest(BaseModel):
    """Request to pull an Ollama model"""
    model_name: str


class OllamaAgentRequest(BaseModel):
    """Request to create an Ollama-powered agent"""
    agent_name: str
    agent_type: str = "trading"
    model: str = "llama2"
    config: Optional[Dict] = {}


class OllamaPromptRequest(BaseModel):
    """Request for Ollama generation"""
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048


@router.get("/status")
async def get_ollama_status():
    """Get Ollama service status"""
    
    # Check if Ollama is running
    is_running = await ollama_manager.provider.check_health()
    
    return {
        "running": is_running,
        "base_url": ollama_manager.provider.base_url,
        "available_models": ollama_manager.available_models,
        "active_agents": len(ollama_manager.agents),
        "status": ollama_manager.get_status()
    }


@router.get("/models")
async def list_ollama_models():
    """List available Ollama models"""
    
    models = await ollama_manager.provider.list_models()
    
    return {
        "models": models,
        "count": len(models),
        "recommended": ["llama2", "mistral", "phi", "neural-chat"]
    }


@router.post("/models/pull")
async def pull_ollama_model(request: OllamaModelRequest):
    """Pull a new Ollama model"""
    
    try:
        success = await ollama_manager.provider.pull_model(request.model_name)
        
        if success:
            # Refresh available models
            ollama_manager.available_models = await ollama_manager.provider.list_models()
            
            return {
                "status": "success",
                "message": f"Model {request.model_name} pulled successfully",
                "available_models": ollama_manager.available_models
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to pull model")
            
    except Exception as e:
        logger.error(f"Error pulling Ollama model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_with_ollama(request: OllamaPromptRequest):
    """Generate text using Ollama"""
    
    if not ollama_manager.available_models:
        raise HTTPException(status_code=503, detail="No Ollama models available")
        
    model = request.model or ollama_manager.available_models[0]
    
    try:
        # Collect response from async generator
        response_parts = []
        async for part in ollama_manager.provider.generate(
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        ):
            response_parts.append(part)
        
        response = "".join(response_parts)
        
        return {
            "model": model,
            "response": response,
            "tokens_used": len(response.split())  # Approximate
        }
        
    except Exception as e:
        logger.error(f"Ollama generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/create")
async def create_ollama_agent(request: OllamaAgentRequest):
    """Create a new agent powered by Ollama"""
    
    if not ollama_manager.available_models:
        raise HTTPException(status_code=503, detail="No Ollama models available")
        
    # Ensure model exists
    if request.model not in ollama_manager.available_models:
        raise HTTPException(status_code=400, detail=f"Model {request.model} not available")
        
    try:
        # Create agent with Ollama config
        agent_id = f"ollama-{request.agent_name}-{request.model}"
        
        config = request.config.copy()
        config["use_ollama"] = True
        config["ollama_model"] = request.model
        
        # Register agent
        from ..core.agents.agent_manager import AgentType
        agent_type = AgentType(request.agent_type)
        
        success = await agent_manager.register_agent(
            agent_id=agent_id,
            agent_type=agent_type,
            config=config
        )
        
        if success:
            return {
                "status": "success",
                "agent_id": agent_id,
                "model": request.model,
                "type": request.agent_type,
                "message": f"Ollama agent created with {request.model} model"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create agent")
            
    except Exception as e:
        logger.error(f"Error creating Ollama agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_ollama_agents():
    """List all Ollama-powered agents"""
    
    ollama_agents = []
    
    for agent_id, agent_data in agent_manager.agents.items():
        if agent_data.get("config", {}).get("ollama_enabled"):
            ollama_agents.append({
                "id": agent_id,
                "type": agent_data["type"],
                "model": agent_data["config"].get("ollama_model", "unknown"),
                "status": agent_data["status"],
                "created_at": agent_data["registered_at"]
            })
            
    return {
        "agents": ollama_agents,
        "count": len(ollama_agents)
    }


@router.post("/analyze")
async def analyze_with_ollama(data: Dict):
    """Use Ollama agents to analyze data"""
    
    if not ollama_manager.available_models:
        raise HTTPException(status_code=503, detail="No Ollama models available")
        
    try:
        # Get analysis from multiple agent perspectives
        analysis = await ollama_manager.consult_agents(
            question=f"Analyze this data and provide insights: {data}",
            agent_roles=["trading", "analysis", "risk"]
        )
        
        return {
            "analysis": analysis,
            "models_used": ollama_manager.available_models
        }
        
    except Exception as e:
        logger.error(f"Ollama analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_ollama_recommendations():
    """Get model recommendations based on use case"""
    
    return {
        "trading": {
            "recommended": ["llama2", "mistral"],
            "reason": "Good at numerical reasoning and following instructions"
        },
        "analysis": {
            "recommended": ["mixtral", "neural-chat"],
            "reason": "Excellent at detailed analysis and explanations"
        },
        "risk": {
            "recommended": ["llama2", "phi"],
            "reason": "Conservative and good at risk assessment"
        },
        "fast_inference": {
            "recommended": ["phi", "tinyllama"],
            "reason": "Small models with quick response times"
        }
    }