"""
Trading API endpoints for the 24/7 trading system with enhanced security validation

TODO: [CONTAINER] Add comprehensive test coverage for all trading endpoints
TODO: [SECURITY] Expand input validation tests for edge cases and attack scenarios  
TODO: [PERFORMANCE] Add load testing for high-frequency trading scenarios
TODO: [CONTAINER] Test trading strategy execution and P&L calculation accuracy
TODO: [MONITORING] Add detailed audit logging for all trading operations
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, validator
import logging
import asyncio
import re

from ..services.trading_service import trading_service
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])


class TradingStartRequest(BaseModel):
    """Validated request model for starting trading"""
    initial_capital: float
    
    @validator('initial_capital')
    def validate_capital(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError("Initial capital must be a number")
        
        if v < 100:
            raise ValueError("Initial capital must be at least $100")
        
        if v > 100000:
            raise ValueError("Initial capital cannot exceed $100,000 for safety")
        
        # Check for reasonable decimal places
        try:
            decimal_val = Decimal(str(v))
            if decimal_val.as_tuple().exponent < -2:
                raise ValueError("Initial capital cannot have more than 2 decimal places")
        except InvalidOperation:
            raise ValueError("Invalid capital amount format")
            
        return v


class TradingConfigRequest(BaseModel):
    """Validated request for trading configuration updates"""
    max_position_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    target_symbols: Optional[str] = None
    
    @validator('max_position_pct')
    def validate_max_position(cls, v):
        if v is not None:
            if not 0.01 <= v <= 0.5:  # 1% to 50%
                raise ValueError("Max position percentage must be between 1% and 50%")
        return v
    
    @validator('stop_loss_pct')
    def validate_stop_loss(cls, v):
        if v is not None:
            if not 0.005 <= v <= 0.1:  # 0.5% to 10%
                raise ValueError("Stop loss percentage must be between 0.5% and 10%")
        return v
    
    @validator('target_symbols')
    def validate_symbols(cls, v):
        if v is not None:
            # Validate symbol format (alphanumeric, hyphens, periods)
            symbols = [s.strip().upper() for s in v.split(',')]
            for symbol in symbols:
                if not re.match(r'^[A-Z0-9.-]+$', symbol):
                    raise ValueError(f"Invalid symbol format: {symbol}")
                if len(symbol) > 20:
                    raise ValueError(f"Symbol too long: {symbol}")
            
            if len(symbols) > 100:
                raise ValueError("Cannot track more than 100 symbols")
                
            return ','.join(symbols)
        return v


class TradeExecutionRequest(BaseModel):
    """Validated request for trade execution"""
    symbol: str
    action: str  # buy, sell, short
    amount: float
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Symbol is required and must be a string")
        
        symbol = v.strip().upper()
        if not re.match(r'^[A-Z0-9.-]+$', symbol):
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        if len(symbol) > 20:
            raise ValueError(f"Symbol too long: {symbol}")
            
        return symbol
    
    @validator('action')
    def validate_action(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Action is required and must be a string")
        
        action = v.strip().lower()
        allowed_actions = ['buy', 'sell', 'short']
        
        if action not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
            
        return action
    
    @validator('amount')
    def validate_amount(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError("Amount must be a number")
        
        if v <= 0:
            raise ValueError("Amount must be positive")
        
        if v > 1000000:  # $1M max per trade for safety
            raise ValueError("Amount cannot exceed $1,000,000 per trade")
        
        # Check for reasonable decimal places
        try:
            decimal_val = Decimal(str(v))
            if decimal_val.as_tuple().exponent < -8:
                raise ValueError("Amount cannot have more than 8 decimal places")
        except InvalidOperation:
            raise ValueError("Invalid amount format")
            
        return v


@router.post("/start")
async def start_trading(
    request: TradingStartRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Start the 24/7 trading system with validated initial capital
    """
    try:
        capital = Decimal(str(request.initial_capital))
        
        result = await trading_service.start_trading_system(capital)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid capital amount: {e}")
    except Exception as e:
        logger.error(f"Error starting trading system: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stop")
async def stop_trading(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Stop the trading system and close all positions
    """
    try:
        result = await trading_service.stop_trading_system()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error stopping trading system: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/portfolio")
async def get_portfolio_status(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current portfolio status including positions and performance
    """
    try:
        result = trading_service.get_portfolio_status()
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting portfolio status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/performance")
async def get_trading_performance(
    period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get trading performance metrics for specified period
    
    - **period**: Time period for metrics (daily, weekly, monthly, all_time)
    """
    try:
        result = trading_service.get_trading_performance(period)
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trades")
async def get_trade_history(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get trade history with pagination
    
    - **limit**: Number of trades to return (1-1000)
    - **offset**: Number of trades to skip for pagination
    """
    try:
        result = trading_service.get_trade_history(limit, offset)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/positions")
async def get_positions(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed information about current positions
    """
    try:
        result = trading_service.get_position_details()
        
        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def get_system_health(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get trading system health status and diagnostics
    """
    try:
        result = trading_service.get_system_health()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def get_trading_status() -> Dict[str, Any]:
    """
    Get basic trading system status (public endpoint for monitoring)
    """
    try:
        result = trading_service.get_system_health()
        
        if result["status"] == "success":
            health_data = result["data"]
            return {
                "status": "success",
                "data": {
                    "is_running": health_data["is_running"],
                    "overall_health": health_data["overall_health"],
                    "last_check": health_data["last_check"],
                    "portfolio_value": health_data.get("portfolio_value"),
                    "total_trades": health_data.get("total_trades", 0)
                }
            }
        else:
            return result
        
    except Exception as e:
        logger.error(f"Error getting trading status: {e}")
        return {
            "status": "error",
            "message": "System error",
            "is_running": False,
            "overall_health": "error"
        }


@router.post("/execute")
async def execute_trade(
    request: TradeExecutionRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Execute a validated trade order (used by adaptive trading system)
    """
    try:
        # Import trading engine
        from ..core.trading.trading_engine import trading_engine
        
        # Execute the trade with validated inputs
        symbol = request.symbol
        action = request.action
        amount = Decimal(str(request.amount))
        
        # Handle special actions
        if action == "short":
            # Short selling
            result = await trading_engine.open_short_position(symbol, amount)
        elif action == "buy":
            result = await trading_engine.buy_crypto(symbol, amount)
        elif action == "sell":
            result = await trading_engine.sell_crypto(symbol, amount)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
        
        return {
            "status": "success",
            "trade_id": result.get("trade_id", "N/A"),
            "symbol": symbol,
            "action": action,
            "amount": str(amount),
            "executed_price": result.get("price", 0),
            "timestamp": result.get("timestamp")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_trading_config(
    request: TradingConfigRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update trading system configuration with validation
    """
    try:
        config_updates = {}
        
        if request.max_position_pct is not None:
            config_updates["max_position_pct"] = request.max_position_pct
            
        if request.stop_loss_pct is not None:
            config_updates["stop_loss_pct"] = request.stop_loss_pct
            
        if request.target_symbols is not None:
            config_updates["target_symbols"] = request.target_symbols
        
        if not config_updates:
            raise HTTPException(status_code=400, detail="No configuration parameters provided")
        
        # Update trading service configuration
        result = await trading_service.update_configuration(config_updates)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "status": "success",
            "message": "Trading configuration updated",
            "updated_params": config_updates
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating trading configuration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/account")
async def get_account_info(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get account information including balance and metrics
    """
    try:
        portfolio = trading_service.get_portfolio_status()
        performance = trading_service.get_trading_performance("all_time")
        
        if portfolio["status"] == "error" or performance["status"] == "error":
            raise HTTPException(status_code=500, detail="Failed to get account info")
        
        portfolio_data = portfolio["data"]
        performance_data = performance["data"]
        
        return {
            "balance": portfolio_data["cash_balance"],
            "total_pnl": portfolio_data["total_pnl"],
            "roi_percentage": performance_data.get("roi_percentage", 0),
            "total_trades": performance_data.get("total_trades", 0),
            "winning_trades": performance_data.get("winning_trades", 0),
            "losing_trades": performance_data.get("losing_trades", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates
@router.websocket("/ws")
async def trading_websocket(websocket):
    """
    WebSocket endpoint for real-time trading updates
    """
    await websocket.accept()
    
    try:
        while True:
            # Send portfolio status every 30 seconds
            result = trading_service.get_portfolio_status()
            if result["status"] == "success":
                await websocket.send_json({
                    "type": "portfolio_update",
                    "data": result["data"]
                })
            
            # Send recent trades
            trades_result = trading_service.get_trade_history(limit=5)
            if trades_result["status"] == "success":
                await websocket.send_json({
                    "type": "recent_trades",
                    "data": trades_result["data"]["trades"]
                })
            
            await asyncio.sleep(30)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()