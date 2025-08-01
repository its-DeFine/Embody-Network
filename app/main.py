"""
AutoGen Platform - Main Application

A production-ready platform for orchestrating Microsoft AutoGen AI agents
with focus on maintainability, observability, and scalability.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
import structlog

from .api import auth, agents, teams, tasks, gpu, market, management
from .dependencies import get_redis, get_docker
from .orchestrator import orchestrator
from .gpu_orchestrator import gpu_orchestrator
from .market_data import market_data_service
from .agent_manager import agent_manager
from .collective_intelligence import collective_intelligence
from .websocket_manager import websocket_manager
from .trading_strategies import strategy_manager
from .config import settings, IS_PRODUCTION, IS_DEVELOPMENT
from .middleware import LoggingMiddleware, MetricsMiddleware
from .errors import PlatformError, platform_exception_handler

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Legacy connection manager removed - using websocket_manager instead

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AutoGen Platform...")
    redis = await get_redis()
    
    # Check Redis connection
    await redis.ping()
    logger.info("Redis connected")
    
    # Try Docker connection (optional)
    try:
        docker = get_docker()
        docker.ping()
        logger.info("Docker connected")
    except Exception as e:
        logger.warning(f"Docker not available: {e}")
        docker = None
    
    # Start orchestrator (enhanced with 24/7 capabilities)
    await orchestrator.start()
    
    # Initialize GPU orchestrator
    await gpu_orchestrator.initialize()
    await gpu_orchestrator.start_monitoring()
    
    # Initialize market data service
    await market_data_service.initialize()
    
    # Initialize agent manager with inter-agent communication
    await agent_manager.start()
    
    # Initialize collective intelligence system
    await collective_intelligence.start()
    
    # Initialize WebSocket manager for real-time updates
    await websocket_manager.start()
    
    # Initialize trading strategies manager
    await strategy_manager.start()
    
    logger.info("Advanced 24/7 Trading Platform started successfully with full orchestration")
    yield
    
    # Shutdown in reverse order
    logger.info("Shutting down 24/7 Trading Platform...")
    await strategy_manager.stop()
    await websocket_manager.stop()
    await collective_intelligence.stop()
    await agent_manager.stop()
    await gpu_orchestrator.stop_monitoring()
    await orchestrator.stop()
    await redis.close()
    if docker:
        docker.close()

# Create app with configuration
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url="/redoc" if not IS_PRODUCTION else None
)

# Add middleware in correct order (last added = first executed)
app.add_middleware(MetricsMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if IS_DEVELOPMENT else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(PlatformError, platform_exception_handler)

# Include routers
app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(teams.router)
app.include_router(tasks.router)
app.include_router(gpu.router)
app.include_router(market.router)
app.include_router(management.router)  # New management API

# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

# Enhanced WebSocket endpoints using WebSocket Manager
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates"""
    client_id = await websocket_manager.connect_client(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            await websocket_manager.handle_client_message(client_id, data)
    except WebSocketDisconnect:
        await websocket_manager.disconnect_client(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket_manager.disconnect_client(client_id)

# Authenticated WebSocket endpoint
@app.websocket("/ws/authenticated")
async def authenticated_websocket(websocket: WebSocket):
    """Authenticated WebSocket endpoint with user context"""
    # Get token from query params
    token = websocket.query_params.get("token")
    user_id = None
    
    # Validate token (simplified - use proper auth in production)
    if token:
        # user_id = validate_token(token)  # Implement token validation
        user_id = "user_123"  # Placeholder
        
    client_id = await websocket_manager.connect_client(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            await websocket_manager.handle_client_message(client_id, data)
    except WebSocketDisconnect:
        await websocket_manager.disconnect_client(client_id)
    except Exception as e:
        logger.error(f"Authenticated WebSocket error: {e}")
        await websocket_manager.disconnect_client(client_id)

# Legacy market data WebSocket (for backward compatibility)
@app.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    """Legacy market data WebSocket for backward compatibility"""
    await websocket.accept()
    
    try:
        # Receive subscription request
        data = await websocket.receive_json()
        symbols = data.get("symbols", ["AAPL", "GOOGL", "MSFT"])
        
        logger.info(f"Starting legacy market data stream for {symbols}")
        
        # Define callback for price updates
        async def send_price_update(symbol: str, price: float):
            await websocket.send_json({
                "type": "price_update",
                "symbol": symbol,
                "price": price,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Start streaming prices
        streaming_task = asyncio.create_task(
            market_data_service.stream_prices(symbols, send_price_update)
        )
        
        # Keep connection alive
        while True:
            # Wait for any message (heartbeat)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        logger.info("Legacy market WebSocket disconnected")
        if 'streaming_task' in locals():
            streaming_task.cancel()
    except Exception as e:
        logger.error(f"Legacy market WebSocket error: {e}")
        await websocket.close()

# Mount static files (UI)
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)