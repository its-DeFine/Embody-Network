#!/usr/bin/env python3
"""
Full Central Manager Test - Complete API Surface

Launches the central manager with all major API endpoints available for testing.
This includes authentication, trading, management, agents, teams, tasks, GPU, market data, etc.
"""
import os
import sys
import asyncio
from contextlib import asynccontextmanager

# Set up environment for testing
os.environ['AUDIT_LOG_DIR'] = '/tmp/trading-data/audit'
os.makedirs('/tmp/trading-data/audit', exist_ok=True)
os.makedirs('/tmp/trading-data/backups', exist_ok=True)

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import structlog

# Import all API routers - this gives us the full API surface
from app.api import (
    auth, agents, teams, tasks, gpu, market, management, 
    trading, master, audit, dex, ollama, security
)
from app.dependencies import get_redis
from app.config import settings
from app.middleware import LoggingMiddleware, SecurityHeadersMiddleware, RateLimitMiddleware
from app.errors import PlatformError, platform_exception_handler

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Full central manager lifespan with minimal component initialization"""
    logger.info("🎛️ Starting Full Central Manager (Test Mode)...")
    
    # Connect to Redis
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        # Continue anyway for API testing
    
    # Initialize minimal components needed for API functionality
    try:
        # Initialize audit logger with minimal setup
        from app.infrastructure.monitoring.audit_logger import audit_logger
        await audit_logger.initialize()
        logger.info("✅ Audit logger initialized")
    except Exception as e:
        logger.warning(f"⚠️ Audit logger initialization failed: {e}")
    
    # Initialize security manager
    try:
        from app.infrastructure.security.key_manager import secure_key_manager
        await secure_key_manager.initialize()
        logger.info("✅ Security manager initialized")
    except Exception as e:
        logger.warning(f"⚠️ Security manager initialization failed: {e}")
    
    logger.info("🚀 Full Central Manager API started successfully!")
    logger.info("📊 Access complete API docs at http://localhost:8002/docs")
    logger.info("🔧 Available API groups:")
    logger.info("   - Authentication & Authorization")
    logger.info("   - Agent Management")
    logger.info("   - Team Management")  
    logger.info("   - Task Management")
    logger.info("   - GPU Orchestration")
    logger.info("   - Market Data")
    logger.info("   - System Management")
    logger.info("   - 24/7 Trading System")
    logger.info("   - Master Manager Control")
    logger.info("   - Audit & Monitoring")
    logger.info("   - DEX Trading")
    logger.info("   - Ollama LLM Integration")
    logger.info("   - Security Management")
    
    yield
    
    logger.info("🛑 Shutting down Full Central Manager...")

def create_full_manager_app():
    """Create FastAPI app with complete API surface"""
    
    app = FastAPI(
        title="24/7 Trading System - Complete Central Manager",
        description="""
        Complete Central Manager API with all endpoints available for testing.
        
        This includes:
        - 🔐 Authentication & Authorization
        - 🤖 Agent Lifecycle Management  
        - 👥 Team Coordination
        - 📋 Task Management
        - 🖥️ GPU Orchestration
        - 📊 Market Data Integration
        - ⚙️ System Management
        - 💰 24/7 Trading Operations
        - 🎛️ Master Manager Control
        - 📋 Audit & Monitoring
        - 🔄 DEX Trading
        - 🧠 Ollama LLM Integration
        - 🛡️ Security Management
        
        **Total: ~90 API endpoints available for testing**
        """,
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=200)
    app.add_middleware(LoggingMiddleware)
    
    # Add exception handler
    app.add_exception_handler(PlatformError, platform_exception_handler)
    
    # Include ALL API routers - this gives us the complete API surface
    app.include_router(auth.router)           # Authentication
    app.include_router(agents.router)         # Agent management
    app.include_router(teams.router)          # Team management
    app.include_router(tasks.router)          # Task management
    app.include_router(gpu.router)            # GPU orchestration
    app.include_router(market.router)         # Market data
    app.include_router(management.router)     # System management
    app.include_router(trading.router)        # 24/7 Trading
    app.include_router(master.router)         # Master manager
    app.include_router(audit.router)          # Audit logging
    app.include_router(dex.router)            # DEX trading
    app.include_router(ollama.router)         # Ollama LLM
    app.include_router(security.router)       # Security management
    
    # Enhanced health endpoint
    @app.get("/health")
    async def health_check():
        """Enhanced health check showing all available API groups"""
        try:
            redis = await get_redis()
            await redis.ping()
            redis_status = "healthy"
        except Exception as e:
            redis_status = f"unhealthy: {e}"
        
        return {
            "status": "healthy",
            "service": "complete-central-manager",
            "mode": "test",
            "components": {
                "redis": redis_status,
                "api_groups": {
                    "auth": "enabled",
                    "agents": "enabled", 
                    "teams": "enabled",
                    "tasks": "enabled",
                    "gpu": "enabled",
                    "market": "enabled",
                    "management": "enabled",
                    "trading": "enabled",
                    "master": "enabled",
                    "audit": "enabled",
                    "dex": "enabled",
                    "ollama": "enabled",
                    "security": "enabled"
                }
            },
            "total_endpoints": "~90",
            "docs_url": "http://localhost:8002/docs",
            "timestamp": structlog.processors.TimeStamper(fmt="iso")._stamper()
        }
    
    return app

async def main():
    """Main function to run complete central manager"""
    print("🎛️ 24/7 Trading System - Complete Central Manager")
    print("=" * 60)
    print("🚀 Launching with ALL 90 API endpoints...")
    print("📊 Interactive docs: http://localhost:8002/docs")
    print("📋 Alternative docs: http://localhost:8002/redoc")
    
    # Create the app
    app = create_full_manager_app()
    
    # Configure uvicorn
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8002,
        log_level="info",
        reload=False
    )
    
    # Run the server
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Complete Central Manager stopped by user")
    except Exception as e:
        print(f"❌ Complete Central Manager failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)