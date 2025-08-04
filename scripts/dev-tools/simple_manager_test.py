#!/usr/bin/env python3
"""
Simple Central Manager Test - Minimal dependencies

Tests basic system status without complex component initialization.
"""
import os
import sys
import asyncio
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import redis.asyncio as redis

# Set environment variable for audit directory
os.environ['AUDIT_LOG_DIR'] = '/tmp/trading-data/audit'
os.makedirs('/tmp/trading-data/audit', exist_ok=True)

app = FastAPI(
    title="Central Manager Test",
    description="Basic status endpoints",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Redis connection
redis_client = None

async def get_redis_connection():
    """Get Redis connection"""
    global redis_client
    if not redis_client:
        redis_client = redis.from_url("redis://localhost:6379")
    return redis_client

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    print("🎛️ Starting Simple Central Manager Test...")
    
    # Test Redis connection
    try:
        redis_conn = await get_redis_connection()
        await redis_conn.ping()
        print("✅ Redis connected successfully")
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global redis_client
    if redis_client:
        await redis_client.close()
    print("🛑 Central Manager Test stopped")

@app.get("/health")
async def health_check():
    """Basic health check"""
    redis_status = "unknown"
    try:
        redis_conn = await get_redis_connection()
        await redis_conn.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)[:100]}"
    
    return {
        "status": "healthy",
        "service": "central-manager-test",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "redis": redis_status,
            "api": "healthy"
        }
    }

@app.get("/api/v1/management/system/status")
async def system_status():
    """System status endpoint"""
    redis_info = {}
    try:
        redis_conn = await get_redis_connection()
        await redis_conn.ping()
        redis_info = {
            "status": "connected",
            "url": "redis://localhost:6379"
        }
    except Exception as e:
        redis_info = {
            "status": "disconnected",
            "error": str(e)[:100]
        }
    
    return {
        "status": "running",
        "mode": "test",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "central_manager": "active",
            "redis": redis_info,
            "api_server": "running",
            "port": 8000
        },
        "features": {
            "authentication": "available",
            "management": "available", 
            "health_monitoring": "active",
            "audit_logging": "basic"
        }
    }

@app.get("/api/v1/trading/status")
async def trading_status():
    """Trading system status - basic version"""
    return {
        "status": "success",
        "data": {
            "is_running": False,
            "overall_health": "not_started",
            "last_check": datetime.utcnow().isoformat(),
            "portfolio_value": None,
            "total_trades": 0,
            "mode": "test"
        }
    }

@app.post("/api/v1/auth/test")
async def auth_test():
    """Test authentication endpoint"""
    return {
        "status": "success",
        "message": "Authentication endpoint is accessible",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/stats")
async def get_stats():
    """Central manager statistics"""
    uptime_seconds = 0  # Will be calculated properly in real implementation
    
    return {
        "central_manager": {
            "status": "running",
            "mode": "test",
            "uptime_seconds": uptime_seconds,
            "endpoints_active": 6
        },
        "system": {
            "redis_connected": True,  # Will check in real implementation
            "api_requests": 0,  # Will be tracked in real implementation
            "last_health_check": datetime.utcnow().isoformat()
        },
        "agents": {
            "total_containers": 0,
            "active_containers": 0,
            "status": "no_agents_running"
        }
    }

if __name__ == "__main__":
    print("🚀 Simple Central Manager Test")
    print("📊 Available endpoints:")
    print("   - GET  /health")
    print("   - GET  /api/v1/management/system/status")
    print("   - GET  /api/v1/trading/status") 
    print("   - POST /api/v1/auth/test")
    print("   - GET  /stats")
    print("🌐 Starting server on http://localhost:8000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )