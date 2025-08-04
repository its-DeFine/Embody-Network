"""
Trading API endpoints for the 24/7 trading system
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, Optional
from decimal import Decimal
import logging
import asyncio

from ..services.trading_service import trading_service
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])


@router.post("/start")
async def start_trading(
    initial_capital: Optional[float] = 1000.0,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Start the 24/7 trading system with specified initial capital
    """
    try:
        capital = Decimal(str(initial_capital)) if initial_capital else Decimal("1000")
        
        if capital < Decimal("100"):
            raise HTTPException(
                status_code=400,
                detail="Initial capital must be at least $100"
            )
        
        if capital > Decimal("100000"):
            raise HTTPException(
                status_code=400,
                detail="Initial capital cannot exceed $100,000 for safety"
            )
        
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
    trade_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Execute a trade order (used by adaptive trading system)
    """
    try:
        # Import trading engine
        from ..core.trading.trading_engine import trading_engine
        
        # Validate trade data
        required_fields = ["symbol", "action", "amount"]
        for field in required_fields:
            if field not in trade_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Execute the trade
        symbol = trade_data["symbol"]
        action = trade_data["action"].lower()
        amount = Decimal(str(trade_data["amount"]))
        
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