"""
Main entry point for the GPU Orchestrator Adapter service
Bridges agent-net with the AutoGen platform
"""

import os
import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

from swarm_connector import SwarmConnector
from gpu_manager import GPUManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
swarm_connector = None
gpu_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global swarm_connector, gpu_manager
    
    logger.info("Starting GPU Orchestrator Adapter")
    
    # Get configuration from environment
    orchestrator_id = os.getenv('ORCHESTRATOR_ID', 'gpu-orch-1')
    rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672')
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
    
    try:
        # Initialize GPU manager
        gpu_manager = GPUManager(redis_url)
        await gpu_manager.initialize()
        
        # Initialize swarm connector
        swarm_connector = SwarmConnector(orchestrator_id, rabbitmq_url, redis_url)
        await swarm_connector.initialize()
        
        # Register with swarm
        await swarm_connector.register_with_swarm()
        
        logger.info("GPU Orchestrator Adapter started successfully")
        
        yield
        
    finally:
        # Cleanup
        logger.info("Shutting down GPU Orchestrator Adapter")
        
        if swarm_connector:
            await swarm_connector.shutdown()
        
        logger.info("GPU Orchestrator Adapter shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="GPU Orchestrator Adapter",
    description="Bridges agent-net GPU orchestrators with AutoGen platform",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "gpu-orchestrator-adapter",
        "orchestrator_id": swarm_connector.orchestrator_id if swarm_connector else None,
        "registered": swarm_connector.registered if swarm_connector else False
    }


@app.get("/status")
async def get_status():
    """Get detailed status of the orchestrator"""
    if not gpu_manager:
        raise HTTPException(status_code=503, detail="GPU manager not initialized")
    
    cluster_status = await gpu_manager.get_cluster_status()
    
    return {
        "orchestrator_id": swarm_connector.orchestrator_id if swarm_connector else None,
        "cluster": cluster_status,
        "gpu_metrics": swarm_connector.gpu_metrics if swarm_connector else {},
        "available_models": swarm_connector.available_models if swarm_connector else []
    }


@app.post("/agents/allocate")
async def allocate_agent(request: Request):
    """Allocate an agent to a GPU orchestrator"""
    if not gpu_manager:
        raise HTTPException(status_code=503, detail="GPU manager not initialized")
    
    agent_config = await request.json()
    
    # Allocate to best orchestrator
    orchestrator_id = await gpu_manager.allocate_agent(agent_config)
    
    if not orchestrator_id:
        raise HTTPException(
            status_code=503, 
            detail="No suitable GPU orchestrator available"
        )
    
    return {
        "agent_id": agent_config.get("agent_id"),
        "orchestrator_id": orchestrator_id,
        "status": "allocated"
    }


@app.delete("/agents/{agent_id}")
async def deallocate_agent(agent_id: str):
    """Deallocate an agent from its orchestrator"""
    if not gpu_manager:
        raise HTTPException(status_code=503, detail="GPU manager not initialized")
    
    await gpu_manager.deallocate_agent(agent_id)
    
    return {"agent_id": agent_id, "status": "deallocated"}


@app.get("/payments/stats")
async def get_payment_stats():
    """Get payment statistics for orchestrators"""
    if not gpu_manager:
        raise HTTPException(status_code=503, detail="GPU manager not initialized")
    
    stats = await gpu_manager.get_payment_stats()
    
    return {"payment_stats": stats}


@app.post("/webhook/livepeer")
async def livepeer_webhook(request: Request):
    """Handle Livepeer payment webhooks"""
    if not swarm_connector:
        raise HTTPException(status_code=503, detail="Swarm connector not initialized")
    
    payload = await request.json()
    
    # Process payment ticket
    await swarm_connector.handle_livepeer_payment(payload)
    
    return {"status": "processed"}


def handle_shutdown(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown")
    asyncio.create_task(shutdown())


async def shutdown():
    """Graceful shutdown"""
    if swarm_connector:
        await swarm_connector.shutdown()


if __name__ == "__main__":
    # Handle shutdown signals
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Run the service
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )