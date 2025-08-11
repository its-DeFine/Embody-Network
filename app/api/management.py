"""
Management API Endpoints

Provides comprehensive control and monitoring endpoints for the 24/7 trading system.
Includes dynamic routing configuration, strategy management, system health monitoring,
agent orchestration, and real-time configuration updates.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from http import HTTPStatus
from pydantic import BaseModel, Field

from ..dependencies import get_redis, get_current_user
from ..infrastructure.monitoring.reliability_manager import reliability_manager
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/management", tags=["management"])


# Pydantic Models
class ProviderConfig(BaseModel):
    """Market data provider configuration"""
    name: str
    priority: int = Field(ge=1, le=10)
    enabled: bool = True
    rate_limit: Optional[int] = None
    api_key: Optional[str] = None
    config: Dict[str, Any] = {}


class StrategyConfig(BaseModel):
    """Trading strategy configuration"""
    name: str
    enabled: bool = True
    parameters: Dict[str, Any] = {}
    risk_limits: Dict[str, float] = {}
    symbols: List[str] = []
    schedule: Optional[str] = None  # Cron expression


class AgentConfig(BaseModel):
    """Agent configuration"""
    agent_id: str
    agent_type: str
    enabled: bool = True
    resources: Dict[str, Any] = {}
    strategies: List[str] = []
    risk_profile: str = "conservative"


class SystemStatus(str, Enum):
    """System status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"


class ConfigUpdate(BaseModel):
    """Configuration update request"""
    component: str
    config: Dict[str, Any]
    restart_required: bool = False


class TradeOrder(BaseModel):
    """Manual trade order"""
    symbol: str
    action: str  # buy/sell
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None
    agent_id: Optional[str] = None


class AdaptiveDirective(BaseModel):
    """Adaptive trading directive from central manager"""
    ai_prompt: str = Field(..., description="AI guidance prompt for trading decisions")
    max_position_pct: float = Field(default=0.10, ge=0.01, le=0.50)
    risk_level: str = Field(default="medium", pattern="^(low|medium|high)$")
    allowed_strategies: List[str] = Field(default=["all"])
    allow_shorts: bool = Field(default=True)
    allow_leverage: bool = Field(default=False)
    max_leverage: float = Field(default=2.0, ge=1.0, le=10.0)


# Management Endpoints

@router.get("/status")
async def get_system_status(
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Get comprehensive system status"""
    try:
        # Get market data health
        market_health = {"status": "disabled", "message": "Market service removed"}
        
        # Get active agents
        agent_keys = await redis.keys("agent:*")
        active_agents = []
        unhealthy_agents = []
        
        for key in agent_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            if ":status" in key_str or ":tasks" in key_str:
                continue
                
            agent_data = await redis.get(key)
            if agent_data:
                agent = json.loads(agent_data)
                if agent.get("status") == "running":
                    active_agents.append(agent)
                elif agent.get("status") == "unhealthy":
                    unhealthy_agents.append(agent)
        
        # Get trading statistics
        trading_stats = await redis.hgetall("trading:stats:daily")
        
        # Determine overall system status
        overall_status = SystemStatus.HEALTHY
        if market_health["status"] == "degraded" or len(unhealthy_agents) > 0:
            overall_status = SystemStatus.DEGRADED
        elif market_health["status"] == "critical" or len(active_agents) == 0:
            overall_status = SystemStatus.CRITICAL
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "market_data": market_health,
            "agents": {
                "active": len(active_agents),
                "unhealthy": len(unhealthy_agents),
                "total": len(active_agents) + len(unhealthy_agents),
                "details": active_agents[:5]  # Show first 5 for brevity
            },
            "trading": {
                "daily_pnl": float(trading_stats.get(b"daily_pnl", 0)) if trading_stats else 0,
                "trades_today": int(trading_stats.get(b"trades_count", 0)) if trading_stats else 0,
                "success_rate": float(trading_stats.get(b"success_rate", 0)) if trading_stats else 0
            },
            "system": {
                "uptime_hours": 24,  # Placeholder - implement actual uptime tracking
                "memory_usage": 65.2,  # Placeholder - implement actual system monitoring
                "cpu_usage": 45.8  # Placeholder - implement actual system monitoring
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def get_provider_status(
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> List[Dict[str, Any]]:
    """Get market data provider status and configuration"""
    try:
        providers_status = []
        
        # Get provider health from reliability manager
        health_report = await reliability_manager.get_health_report()
        
        # Market providers removed
        all_providers = {}
            provider_health = health_report["providers"].get(provider_name, {})
            
            providers_status.append({
                "name": provider_name,
                "enabled": provider_health.get("status") != "disabled",
                "status": provider_health.get("status", "unknown"),
                "success_rate": provider_health.get("success_rate", 0),
                "avg_response_time": provider_health.get("avg_response_time", 0),
                "last_success": provider_health.get("last_success"),
                "error_count": provider_health.get("error_count", 0),
                "circuit_breaker": provider_health.get("circuit_breaker", "closed")
            })
        
        return sorted(providers_status, key=lambda x: x["success_rate"], reverse=True)
        
    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/providers/configure")
async def configure_provider(
    config: ProviderConfig,
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Configure market data provider settings"""
    try:
        # Update provider configuration in Redis
        config_key = f"provider:config:{config.name}"
        await redis.hset(config_key, mapping={
            "priority": config.priority,
            "enabled": config.enabled,
            "rate_limit": config.rate_limit or 0,
            "config": json.dumps(config.config),
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": user["username"]
        })
        
        # Update market data service routing if this is primary provider
        if config.priority == 1:
            # Market provider configuration removed
            pass
        
        # Reset circuit breaker if re-enabling
        if config.enabled:
            await reliability_manager.reset_circuit_breaker(config.name)
        
        logger.info(f"Provider {config.name} configured by {user['username']}")
        return {"message": f"Provider {config.name} configured successfully"}
        
    except Exception as e:
        logger.error(f"Error configuring provider {config.name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_trading_strategies(
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> List[Dict[str, Any]]:
    """Get all trading strategies and their status"""
    try:
        strategy_keys = await redis.keys("strategy:*")
        strategies = []
        
        for key in strategy_keys:
            strategy_data = await redis.hgetall(key)
            if strategy_data:
                strategy_id = key.decode().split(":")[-1]
                strategies.append({
                    "id": strategy_id,
                    "name": strategy_data.get(b"name", b"").decode(),
                    "enabled": strategy_data.get(b"enabled", b"false").decode() == "true",
                    "type": strategy_data.get(b"type", b"").decode(),
                    "symbols": json.loads(strategy_data.get(b"symbols", b"[]").decode()),
                    "parameters": json.loads(strategy_data.get(b"parameters", b"{}").decode()),
                    "performance": {
                        "pnl_today": float(strategy_data.get(b"pnl_today", 0)),
                        "trades_today": int(strategy_data.get(b"trades_today", 0)),
                        "success_rate": float(strategy_data.get(b"success_rate", 0))
                    },
                    "last_updated": strategy_data.get(b"last_updated", b"").decode()
                })
        
        return strategies
        
    except Exception as e:
        logger.error(f"Error getting trading strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/{strategy_id}/toggle")
async def toggle_strategy(
    strategy_id: str,
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Enable or disable a trading strategy"""
    try:
        strategy_key = f"strategy:{strategy_id}"
        strategy_data = await redis.hgetall(strategy_key)
        
        if not strategy_data:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Toggle enabled status
        current_status = strategy_data.get(b"enabled", b"false").decode() == "true"
        new_status = not current_status
        
        await redis.hset(strategy_key, mapping={
            "enabled": str(new_status).lower(),
            "last_updated": datetime.utcnow().isoformat(),
            "updated_by": user["username"]
        })
        
        # Publish strategy status change event
        await redis.publish("events:strategies", json.dumps({
            "type": "strategy_toggled",
            "strategy_id": strategy_id,
            "enabled": new_status,
            "timestamp": datetime.utcnow().isoformat(),
            "user": user["username"]
        }))
        
        action = "enabled" if new_status else "disabled"
        logger.info(f"Strategy {strategy_id} {action} by {user['username']}")
        
        return {"message": f"Strategy {strategy_id} {action} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies")
async def create_strategy(
    strategy: StrategyConfig,
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Create a new trading strategy"""
    try:
        strategy_id = f"strategy_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        strategy_key = f"strategy:{strategy_id}"
        
        await redis.hset(strategy_key, mapping={
            "name": strategy.name,
            "enabled": str(strategy.enabled).lower(),
            "parameters": json.dumps(strategy.parameters),
            "risk_limits": json.dumps(strategy.risk_limits),
            "symbols": json.dumps(strategy.symbols),
            "schedule": strategy.schedule or "",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user["username"],
            "pnl_today": 0,
            "trades_today": 0,
            "success_rate": 0
        })
        
        logger.info(f"Strategy {strategy.name} created by {user['username']}")
        return {"message": f"Strategy {strategy.name} created with ID {strategy_id}", "strategy_id": strategy_id}
        
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def get_agents_status(
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> List[Dict[str, Any]]:
    """Get all agents status and configuration"""
    try:
        agent_keys = await redis.keys("agent:*")
        agents = []
        
        for key in agent_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            if ":status" in key_str or ":tasks" in key_str:
                continue
                
            agent_data = await redis.get(key)
            if agent_data:
                agent = json.loads(agent_data)
                
                # Get agent metrics
                metrics_key = f"agent:{agent['id']}:metrics"
                metrics = await redis.hgetall(metrics_key)
                
                agents.append({
                    **agent,
                    "metrics": {
                        "tasks_completed": int(metrics.get(b"tasks_completed", 0)) if metrics else 0,
                        "avg_response_time": float(metrics.get(b"avg_response_time", 0)) if metrics else 0,
                        "uptime_hours": float(metrics.get(b"uptime_hours", 0)) if metrics else 0,
                        "last_activity": metrics.get(b"last_activity", b"").decode() if metrics else ""
                    }
                })
        
        return sorted(agents, key=lambda x: x.get("created_at", ""), reverse=True)
        
    except Exception as e:
        logger.error(f"Error getting agents status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents")
async def create_agent(
    agent_config: AgentConfig,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Create and deploy a new trading agent"""
    try:
        agent_data = {
            "id": agent_config.agent_id,
            "type": agent_config.agent_type,
            "status": "creating",
            "enabled": agent_config.enabled,
            "resources": agent_config.resources,
            "strategies": agent_config.strategies,
            "risk_profile": agent_config.risk_profile,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user["username"]
        }
        
        # Save agent configuration
        agent_key = f"agent:{agent_config.agent_id}"
        await redis.set(agent_key, json.dumps(agent_data))
        
        # Schedule agent deployment in background
        background_tasks.add_task(deploy_agent, agent_config.agent_id, agent_data)
        
        logger.info(f"Agent {agent_config.agent_id} creation initiated by {user['username']}")
        return {"message": f"Agent {agent_config.agent_id} deployment initiated"}
        
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}")
async def stop_agent(
    agent_id: str,
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Stop and remove an agent"""
    try:
        agent_key = f"agent:{agent_id}"
        agent_data = await redis.get(agent_key)
        
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Update agent status
        agent = json.loads(agent_data)
        agent["status"] = "stopping"
        agent["stopped_at"] = datetime.utcnow().isoformat()
        agent["stopped_by"] = user["username"]
        
        await redis.set(agent_key, json.dumps(agent))
        
        # Publish stop event
        await redis.publish(f"agent:{agent_id}:control", json.dumps({
            "action": "stop",
            "timestamp": datetime.utcnow().isoformat(),
            "user": user["username"]
        }))
        
        logger.info(f"Agent {agent_id} stop initiated by {user['username']}")
        return {"message": f"Agent {agent_id} stop initiated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading/manual-order")
async def place_manual_order(
    order: TradeOrder,
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Place a manual trading order"""
    try:
        order_id = f"manual_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        order_data = {
            "id": order_id,
            "symbol": order.symbol,
            "action": order.action,
            "quantity": order.quantity,
            "order_type": order.order_type,
            "price": order.price,
            "agent_id": order.agent_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user["username"],
            "source": "manual"
        }
        
        # Save order
        await redis.hset(f"order:{order_id}", mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
            for k, v in order_data.items()
        })
        
        # Queue for execution
        await redis.lpush("orders:pending", json.dumps(order_data))
        
        # Publish order event
        await redis.publish("events:orders", json.dumps({
            "type": "order_created",
            "order_id": order_id,
            "data": order_data
        }))
        
        logger.info(f"Manual order {order_id} placed by {user['username']}")
        return {"message": f"Order {order_id} placed successfully", "order_id": order_id}
        
    except Exception as e:
        logger.error(f"Error placing manual order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading/positions")
async def get_current_positions(
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> List[Dict[str, Any]]:
    """Get current trading positions across all agents"""
    try:
        positions = []
        position_keys = await redis.keys("position:*")
        
        for key in position_keys:
            position_data = await redis.hgetall(key)
            if position_data:
                position = {
                    "symbol": position_data.get(b"symbol", b"").decode(),
                    "quantity": float(position_data.get(b"quantity", 0)),
                    "avg_price": float(position_data.get(b"avg_price", 0)),
                    "current_price": float(position_data.get(b"current_price", 0)),
                    "unrealized_pnl": float(position_data.get(b"unrealized_pnl", 0)),
                    "realized_pnl": float(position_data.get(b"realized_pnl", 0)),
                    "agent_id": position_data.get(b"agent_id", b"").decode(),
                    "last_updated": position_data.get(b"last_updated", b"").decode()
                }
                positions.append(position)
        
        return sorted(positions, key=lambda x: abs(x["unrealized_pnl"]), reverse=True)
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/update")
async def update_system_config(
    config: ConfigUpdate,
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Update system configuration dynamically"""
    try:
        config_key = f"config:{config.component}"
        
        # Validate component
        valid_components = ["market_data", "trading", "risk", "orchestrator", "agents"]
        if config.component not in valid_components:
            raise HTTPException(status_code=400, detail=f"Invalid component. Must be one of: {valid_components}")
        
        # Save configuration
        await redis.hset(config_key, mapping={
            "config": json.dumps(config.config),
            "restart_required": str(config.restart_required).lower(),
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": user["username"]
        })
        
        # Publish configuration change event
        await redis.publish("events:config", json.dumps({
            "type": "config_updated",
            "component": config.component,
            "config": config.config,
            "restart_required": config.restart_required,
            "timestamp": datetime.utcnow().isoformat(),
            "user": user["username"]
        }))
        
        logger.info(f"Configuration for {config.component} updated by {user['username']}")
        return {"message": f"Configuration for {config.component} updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/dashboard")
async def get_dashboard_metrics(
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Get comprehensive dashboard metrics"""
    try:
        # Get trading metrics
        trading_stats = await redis.hgetall("trading:stats:daily")
        
        # Get portfolio value
        portfolio_value = await redis.get("portfolio:total_value")
        
        # Get top performers
        top_symbols = await redis.zrevrange("trading:performance:symbols", 0, 4, withscores=True)
        
        # Get recent trades
        recent_trades = await redis.lrange("trades:recent", 0, 9)
        
        return {
            "trading": {
                "daily_pnl": float(trading_stats.get(b"daily_pnl", 0)) if trading_stats else 0,
                "total_trades": int(trading_stats.get(b"trades_count", 0)) if trading_stats else 0,
                "success_rate": float(trading_stats.get(b"success_rate", 0)) if trading_stats else 0,
                "portfolio_value": float(portfolio_value) if portfolio_value else 0
            },
            "top_performers": [
                {"symbol": symbol.decode(), "pnl": score} 
                for symbol, score in top_symbols
            ] if top_symbols else [],
            "recent_trades": [
                json.loads(trade) for trade in recent_trades
            ] if recent_trades else [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading/adaptive-directive")
async def set_adaptive_directive(
    directive: AdaptiveDirective,
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Set adaptive trading directive from central manager"""
    try:
        # Import the adaptive strategy manager
        # Trading strategies removed - VTuber system\n        adaptive_strategy_manager = None
        
        # Update the directive
        adaptive_strategy_manager.update_directive({
            "ai_prompt": directive.ai_prompt,
            "max_position_pct": directive.max_position_pct,
            "risk_level": directive.risk_level,
            "allowed_strategies": directive.allowed_strategies,
            "allow_shorts": directive.allow_shorts,
            "allow_leverage": directive.allow_leverage,
            "max_leverage": directive.max_leverage
        })
        
        # Save directive to Redis for persistence
        directive_key = "trading:adaptive:directive"
        await redis.hset(directive_key, mapping={
            "ai_prompt": directive.ai_prompt,
            "max_position_pct": str(directive.max_position_pct),
            "risk_level": directive.risk_level,
            "allowed_strategies": json.dumps(directive.allowed_strategies),
            "allow_shorts": str(directive.allow_shorts).lower(),
            "allow_leverage": str(directive.allow_leverage).lower(),
            "max_leverage": str(directive.max_leverage),
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": user["username"]
        })
        
        # Publish directive change event
        await redis.publish("events:trading", json.dumps({
            "type": "adaptive_directive_updated",
            "directive": directive.dict(),
            "timestamp": datetime.utcnow().isoformat(),
            "user": user["username"]
        }))
        
        logger.info(f"Adaptive directive updated by {user['username']}")
        return {"message": "Adaptive trading directive updated successfully"}
        
    except Exception as e:
        logger.error(f"Error setting adaptive directive: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading/adaptive-directive")
async def get_adaptive_directive(
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Get current adaptive trading directive"""
    try:
        directive_key = "trading:adaptive:directive"
        directive_data = await redis.hgetall(directive_key)
        
        if not directive_data:
            # Return default directive
            return {
                "ai_prompt": "Maximize profits while managing risk appropriately",
                "max_position_pct": 0.10,
                "risk_level": "medium",
                "allowed_strategies": ["all"],
                "allow_shorts": True,
                "allow_leverage": False,
                "max_leverage": 2.0,
                "updated_at": None,
                "updated_by": None
            }
        
        return {
            "ai_prompt": directive_data.get(b"ai_prompt", b"").decode(),
            "max_position_pct": float(directive_data.get(b"max_position_pct", 0.10)),
            "risk_level": directive_data.get(b"risk_level", b"medium").decode(),
            "allowed_strategies": json.loads(directive_data.get(b"allowed_strategies", b'["all"]').decode()),
            "allow_shorts": directive_data.get(b"allow_shorts", b"true").decode() == "true",
            "allow_leverage": directive_data.get(b"allow_leverage", b"false").decode() == "true",
            "max_leverage": float(directive_data.get(b"max_leverage", 2.0)),
            "updated_at": directive_data.get(b"updated_at", b"").decode(),
            "updated_by": directive_data.get(b"updated_by", b"").decode()
        }
        
    except Exception as e:
        logger.error(f"Error getting adaptive directive: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parameters")
async def update_trading_parameters(
    parameters: Dict[str, Any],
    user: dict = Depends(get_current_user),
    redis = Depends(get_redis)
) -> Dict[str, str]:
    """Update trading parameters (alias for adaptive directive)"""
    try:
        # Convert to AdaptiveDirective format
        directive = AdaptiveDirective(
            ai_prompt=parameters.get("ai_prompt", "Maximize profits while managing risk appropriately"),
            max_position_pct=parameters.get("max_position_pct", 0.10),
            risk_level=parameters.get("risk_level", "medium"),
            allowed_strategies=parameters.get("allowed_strategies", ["all"]),
            allow_shorts=parameters.get("allow_shorts", True),
            allow_leverage=parameters.get("allow_leverage", False),
            max_leverage=parameters.get("max_leverage", 2.0)
        )
        
        # Call the main directive endpoint
        return await set_adaptive_directive(directive, user, redis)
        
    except Exception as e:
        logger.error(f"Error updating trading parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper Functions

async def deploy_agent(agent_id: str, agent_data: Dict[str, Any]):
    """Deploy a new agent (background task)"""
    try:
        redis = await get_redis()
        
        # Simulate agent deployment process
        await asyncio.sleep(2)  # Simulate deployment time
        
        # Update agent status
        agent_data["status"] = "running"
        agent_data["started_at"] = datetime.utcnow().isoformat()
        
        await redis.set(f"agent:{agent_id}", json.dumps(agent_data))
        
        # Initialize agent metrics
        await redis.hset(f"agent:{agent_id}:metrics", mapping={
            "tasks_completed": 0,
            "avg_response_time": 0,
            "uptime_hours": 0,
            "last_activity": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Agent {agent_id} deployed successfully")
        
    except Exception as e:
        logger.error(f"Error deploying agent {agent_id}: {e}")
        
        # Update agent status to failed
        try:
            redis = await get_redis()
            agent_data["status"] = "failed"
            agent_data["error"] = str(e)
            await redis.set(f"agent:{agent_id}", json.dumps(agent_data))
        except:
            pass