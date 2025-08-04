"""
Master Manager Integration API
Handles commands from the master central manager

TODO: [CENTRAL-MANAGER] Add comprehensive test coverage for master API endpoints
TODO: [CENTRAL-MANAGER] Implement command queuing for high-availability scenarios
TODO: [SECURITY] Add request signing validation for additional security layers
TODO: [MONITORING] Add detailed audit logging for all master commands
"""

import os
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import logging

from ..dependencies import get_current_user, get_redis
from ..core.orchestration.orchestrator import orchestrator
from ..core.agents.agent_manager import agent_manager
from ..core.trading.trading_engine import trading_engine

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/master",
    tags=["master"]
)

# Master secret for signature verification - require environment variable
MASTER_SECRET_KEY = os.environ.get("MASTER_SECRET_KEY")
if not MASTER_SECRET_KEY:
    raise ValueError("MASTER_SECRET_KEY environment variable must be set for master manager integration")


class MasterCommand(BaseModel):
    """Command from master manager"""
    command: str
    parameters: Optional[Dict] = {}


def verify_master_request(
    x_master_signature: str = Header(...),
    x_timestamp: str = Header(...),
    authorization: str = Header(...)
) -> bool:
    """Verify request is from authorized master manager"""
    
    # Extract instance ID from Bearer token
    try:
        import jwt
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, MASTER_SECRET_KEY, algorithms=["HS256"])
        instance_id = payload.get("instance_id")
        
        if not instance_id:
            raise HTTPException(status_code=401, detail="Invalid authorization")
            
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authorization")
    
    # Verify signature
    message = f"{instance_id}:{x_timestamp}"
    expected_signature = hmac.new(
        MASTER_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(x_master_signature, expected_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Verify timestamp (prevent replay attacks)
    try:
        request_time = datetime.fromisoformat(x_timestamp)
        if datetime.utcnow() - request_time > timedelta(minutes=5):
            raise HTTPException(status_code=403, detail="Request expired")
    except:
        raise HTTPException(status_code=400, detail="Invalid timestamp")
    
    return True


@router.post("/command")
async def receive_master_command(
    command: MasterCommand,
    authorized: bool = Depends(verify_master_request)
):
    """Receive and execute command from master manager"""
    
    logger.info(f"Received master command: {command.command}")
    
    try:
        # Execute different commands
        if command.command == "stop_all_trading":
            # Stop all trading activities
            await trading_engine.stop()
            await agent_manager.stop_all_agents()
            return {"status": "success", "message": "All trading stopped"}
            
        elif command.command == "start_trading":
            # Start trading with specified parameters
            capital = command.parameters.get("capital", 1000)
            await trading_engine.start(initial_capital=capital)
            return {"status": "success", "message": f"Trading started with ${capital}"}
            
        elif command.command == "update_config":
            # Update configuration
            redis = await get_redis()
            for key, value in command.parameters.items():
                await redis.hset("config:instance", key, str(value))
            return {"status": "success", "message": "Configuration updated"}
            
        elif command.command == "restart_agents":
            # Restart all agents
            await agent_manager.stop_all_agents()
            await agent_manager.start()
            return {"status": "success", "message": "Agents restarted"}
            
        elif command.command == "emergency_shutdown":
            # Emergency shutdown
            await orchestrator.emergency_shutdown()
            return {"status": "success", "message": "Emergency shutdown initiated"}
            
        elif command.command == "collect_logs":
            # Collect recent logs
            logs = await orchestrator.collect_logs(
                minutes=command.parameters.get("minutes", 60)
            )
            return {"status": "success", "logs": logs}
            
        elif command.command == "health_check":
            # Detailed health check
            health = await orchestrator.get_health_status()
            return {"status": "success", "health": health}
            
        elif command.command == "scale_agents":
            # Scale agent count
            agent_type = command.parameters.get("agent_type", "trading")
            count = command.parameters.get("count", 1)
            
            for i in range(count):
                await agent_manager.create_agent(
                    name=f"{agent_type}-scaled-{i}",
                    agent_type=agent_type
                )
            
            return {"status": "success", "message": f"Created {count} {agent_type} agents"}
            
        elif command.command == "update_strategy":
            # Update trading strategy parameters
            strategy_id = command.parameters.get("strategy_id")
            config = command.parameters.get("config", {})
            
            await trading_engine.update_strategy(strategy_id, config)
            return {"status": "success", "message": "Strategy updated"}
            
        elif command.command == "export_data":
            # Export trading data
            export_type = command.parameters.get("type", "trades")
            data = await orchestrator.export_data(export_type)
            return {"status": "success", "data": data}
            
        else:
            return {"status": "error", "message": f"Unknown command: {command.command}"}
            
    except Exception as e:
        logger.error(f"Error executing master command: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/instance-info")
async def get_instance_info(authorized: bool = Depends(verify_master_request)):
    """Get detailed information about this instance"""
    
    redis = await get_redis()
    
    # Gather instance information
    info = {
        "instance_id": os.environ.get("INSTANCE_ID", "local"),
        "version": "1.0.0",
        "uptime": await orchestrator.get_uptime(),
        "agents": {
            "total": len(agent_manager.agents),
            "active": sum(1 for a in agent_manager.agents.values() if a.status == "running"),
            "types": {}
        },
        "trading": {
            "is_active": trading_engine.is_running,
            "portfolio_value": await trading_engine.get_portfolio_value() if trading_engine.is_running else 0,
            "daily_pnl": await trading_engine.get_daily_pnl() if trading_engine.is_running else 0,
            "open_positions": len(trading_engine.portfolio.positions) if trading_engine.is_running else 0
        },
        "system": {
            "cpu_usage": await orchestrator.get_cpu_usage(),
            "memory_usage": await orchestrator.get_memory_usage(),
            "disk_usage": await orchestrator.get_disk_usage()
        },
        "configuration": {
            "market_data_providers": await market_data_service.get_active_providers(),
            "strategies": await strategy_manager.get_active_strategies(),
            "risk_limits": await trading_engine.get_risk_limits()
        }
    }
    
    # Count agents by type
    for agent in agent_manager.agents.values():
        agent_type = agent.type
        info["agents"]["types"][agent_type] = info["agents"]["types"].get(agent_type, 0) + 1
    
    return info


@router.post("/emergency-stop")
async def emergency_stop(authorized: bool = Depends(verify_master_request)):
    """Emergency stop - immediately halt all operations"""
    
    logger.warning("EMERGENCY STOP INITIATED BY MASTER")
    
    try:
        # Stop everything immediately
        await trading_engine.emergency_stop()
        await agent_manager.emergency_stop()
        await orchestrator.emergency_shutdown()
        
        # Clear all pending orders
        await trading_engine.cancel_all_orders()
        
        # Notify all connected clients
        await websocket_manager.broadcast({
            "type": "emergency_stop",
            "message": "Emergency stop initiated by master controller"
        })
        
        return {"status": "success", "message": "Emergency stop completed"}
        
    except Exception as e:
        logger.error(f"Error during emergency stop: {e}")
        return {"status": "error", "message": str(e)}