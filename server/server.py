import os, time, logging, json
import aiohttp
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from server.register import register_to_orchestrator
from server.service_monitor import service_monitor

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

# Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

# Helper function to query Ollama
async def get_ollama_gpu_status():
    """Query Ollama for real GPU/VRAM status"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_URL}/api/ps", timeout=5) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to get Ollama status: HTTP {resp.status}")
                    return {
                        "available": False,
                        "model_name": "Ollama unavailable",
                        "vram_usage_mb": 0,
                        "total_models": 0
                    }
                
                data = await resp.json()
                models = data.get('models', [])
                
                if not models:
                    return {
                        "available": False,
                        "model_name": "No models loaded",
                        "vram_usage_mb": 0,
                        "total_models": 0
                    }
                
                # Calculate metrics from loaded models
                total_vram_bytes = sum(model.get('size_vram', 0) for model in models)
                total_vram_mb = total_vram_bytes / (1024 * 1024)
                model_name = models[0].get('name', 'unknown')
                
                if total_vram_mb > 0:  # More than 0
                
                    return {
                        "available": True,
                        "model_name": model_name,
                        "vram_usage_mb": total_vram_mb,
                        "total_models": len(models),
                        "models": models
                    }
                
                else: 
                    return {
                        "available": False,
                        "model_name": "No models loaded",
                        "vram_usage_mb": 0,
                        "total_models": 0
                    }
                
    except Exception as e:
        logger.error(f"Error querying Ollama: {e}")
        return {
            "available": False,
            "model_name": "Error",
            "vram_usage_mb": 0,
            "total_models": 0
        }

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting server")
    
    # Register to orchestrator if needed
    if not register_to_orchestrator():
        logger.warning("Failed to register to orchestrator, continuing anyway")
    
    yield
    
    logger.info("Shutting down server")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {"status": "ok"}

@app.get("/service-status")
async def get_service_status():
    """
    Get current status of autonomy cluster services
    Used by payment distributor to determine payment eligibility
    """
    status = service_monitor.check_services()
    return status

@app.get("/service-uptime")
async def get_service_uptime():
    """
    Get uptime summary for payment calculation
    Returns overall uptime percentage and payment eligibility
    """
    summary = service_monitor.get_summary()
    return {
        "timestamp": datetime.now().isoformat(),
        "overall_uptime_percentage": summary["overall_uptime"],
        "services_up": summary["services_up"],
        "services_down": summary["services_down"],
        "total_services": summary["total_services"],
        "eligible_for_payment": summary["eligible_for_payment"],
        "min_uptime_required": summary["min_uptime_required"]
    }

@app.post("/gpu-check")
async def gpu_check(request: Request):
    """
    GPU Check Capability - Returns  GPU information from Ollama
    Queries Ollama to get actual GPU/VRAM usage based on loaded models
    """
    try:
        params = await request.json()
        logger.info(f"GPU check request received: {params}")
        
        # Extract agent_id from params or use default
        agent_id = params.get("agent_id", "can't be default")
        
        # Get  GPU data from Ollama
        gpu_status = await get_ollama_gpu_status()
        logger.info(f"Ollama GPU status : {gpu_status['model_name']}, VRAM: {gpu_status['vram_usage_mb']:.0f}MB")
        
        # Return response 
        response_data = {
            "status": "success",
            "agent_id": agent_id,
            "model_name": gpu_status["model_name"],
            "vram_usage_mb": gpu_status["vram_usage_mb"],
            "total_models": gpu_status["total_models"],
            "timestamp": time.time(),
            "gpu_count": 1 if gpu_status["available"] else 0,
        }
        
        return Response(
            content=json.dumps(response_data), 
            media_type="application/json",
            headers={
                "X-Metadata": json.dumps({
                    "capability": "gpu-check",
                    "agent_id": agent_id,
                    "timestamp": time.time(),
                    "source": "ollama"
                })
            }
        )
        
    except Exception as e:
        logger.error(f"Error in GPU check: {e}")
        error_response = {
            "status": "error",
            "error": str(e),
            "timestamp": time.time(),
            "capability": "gpu-check"
        }
        return Response(
            content=json.dumps(error_response),
            media_type="application/json",
            status_code=500,
            headers={
                "X-Metadata": json.dumps({
                    "capability": "gpu-check",
                    "status": "error",
                    "timestamp": time.time()
                })
            }
        )

@app.post("/agent-net")
async def agent_net(request: Request):
    """
    Agent-net capability endpoint - returns service monitoring status
    For BYOC payment based on VTuber service uptime
    """
    params = await request.json()
    logger.info(f"Agent-net request received: {params}")
    
    # Get agent_id from params
    agent_id = params.get("agent_id", "agent-net-001")
    
    # Get service monitoring status
    service_status = service_monitor.check_services()
    summary = service_monitor.get_summary()
    
    # Return service monitoring data instead of GPU check
    response_data = {
        "status": "success",
        "agent_id": agent_id,
        "capability": "agent-net",
        "timestamp": time.time(),
        "services": {
            "total": summary["total_services"],
            "up": summary["services_up"],
            "down": summary["services_down"],
            "uptime_percentage": summary["overall_uptime"],
            "eligible_for_payment": summary["eligible_for_payment"]
        },
        # Keep some GPU fields for compatibility but with service data
        "model_name": f"Services: {summary['services_up']}/{summary['total_services']} up",
        "vram_usage_mb": summary["overall_uptime"],  # Use uptime % as pseudo-VRAM
        "total_models": summary["services_up"],  # Use services up as model count
        "gpu_count": 1 if summary["eligible_for_payment"] else 0
    }
    
    return Response(
        content=json.dumps(response_data), 
        media_type="application/json",
        headers={
            "X-Metadata": json.dumps({
                "capability": "agent-net",
                "agent_id": agent_id,
                "timestamp": time.time(),
                "uptime": summary["overall_uptime"],
                "eligible": summary["eligible_for_payment"]
            })
        }
    )
