#!/usr/bin/env python3
"""
Central Manager Only Test Script

Launches only the central manager components for testing without agent containers.
Tests the core APIs and system status endpoints.
"""
import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import structlog

# Import only central manager components
from app.api import auth, management, master, audit, security, trading
from app.dependencies import get_redis
from app.config import settings
from app.middleware import LoggingMiddleware, SecurityHeadersMiddleware, RateLimitMiddleware
from app.errors import PlatformError, platform_exception_handler
from app.infrastructure.monitoring.audit_logger import audit_logger

# Configure minimal logging for testing
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
    """Minimal lifespan - only central manager components"""
    logger.info("🎛️ Starting Central Manager (Test Mode)...")
    
    # Connect to Redis
    redis = await get_redis()
    await redis.ping()
    logger.info("✅ Redis connected")
    
    # Initialize only essential components for central manager
    try:
        await audit_logger.initialize()
        logger.info("✅ Audit logger initialized")
    except Exception as e:
        logger.warning(f"⚠️ Audit logger failed: {e}")
    
    # Initialize security manager
    try:
        from app.infrastructure.security.key_manager import secure_key_manager
        await secure_key_manager.initialize()
        logger.info("✅ Security manager initialized")
    except Exception as e:
        logger.warning(f"⚠️ Security manager failed: {e}")
    
    logger.info("🚀 Central Manager started successfully!")
    logger.info("📊 Access API docs at http://localhost:8000/docs")
    logger.info("🔍 Test endpoints:")
    logger.info("   - GET  /health - System health")
    logger.info("   - GET  /api/v1/management/system/status - System status")
    logger.info("   - POST /api/v1/auth/login - Authentication")
    logger.info("   - GET  /api/v1/master/health - Master manager health")
    
    yield
    
    logger.info("🛑 Shutting down Central Manager...")

def create_central_manager_app():
    """Create FastAPI app with only central manager components"""
    
    app = FastAPI(
        title="24/7 Trading System - Central Manager",
        description="Central management and orchestration API (Test Mode)",
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
    app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
    app.add_middleware(LoggingMiddleware)
    
    # Add exception handler
    app.add_exception_handler(PlatformError, platform_exception_handler)
    
    # Include only central manager APIs
    app.include_router(auth.router)
    app.include_router(management.router) 
    app.include_router(master.router)
    app.include_router(audit.router)
    app.include_router(security.router)
    app.include_router(trading.router)  # For status endpoints
    
    # Basic health endpoint
    @app.get("/health")
    async def health_check():
        """Basic health check for central manager"""
        try:
            redis = await get_redis()
            await redis.ping()
            redis_status = "healthy"
        except Exception as e:
            redis_status = f"unhealthy: {e}"
        
        return {
            "status": "healthy",
            "service": "central-manager",
            "mode": "test",
            "components": {
                "redis": redis_status,
                "auth": "enabled",
                "management": "enabled", 
                "master": "enabled",
                "audit": "enabled",
                "security": "enabled"
            },
            "timestamp": structlog.processors.TimeStamper(fmt="iso")._stamper()
        }
    
    return app

async def main():
    """Main function to run central manager"""
    print("🎛️ 24/7 Trading System - Central Manager Test")
    print("=" * 50)
    
    # Create the app
    app = create_central_manager_app()
    
    # Configure uvicorn
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
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
        print("\n🛑 Central Manager stopped by user")
    except Exception as e:
        print(f"❌ Central Manager failed: {e}")
        sys.exit(1)