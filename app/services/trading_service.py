"""
Trading Service - Main service layer for managing trading operations
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from ..core.trading.trading_engine import trading_engine
from ..infrastructure.database.models import storage, Portfolio, Trade, TradingSession, PerformanceMetrics

logger = logging.getLogger(__name__)


class TradingService:
    """Service layer for trading operations"""
    
    def __init__(self):
        self.engine = trading_engine
        self.monitoring_task: Optional[asyncio.Task] = None
        
    async def start_trading_system(self, initial_capital: Optional[Decimal] = None) -> Dict[str, Any]:
        """Start the 24/7 trading system"""
        try:
            if initial_capital:
                self.engine.initial_capital = initial_capital
            
            portfolio_id = await self.engine.start_trading()
            
            # Start monitoring task
            if not self.monitoring_task or self.monitoring_task.done():
                self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            return {
                "status": "success",
                "message": "Trading system started successfully",
                "portfolio_id": portfolio_id,
                "initial_capital": float(self.engine.initial_capital),
                "started_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start trading system: {e}")
            return {
                "status": "error",
                "message": f"Failed to start trading system: {str(e)}"
            }
    
    async def stop_trading_system(self) -> Dict[str, Any]:
        """Stop the trading system"""
        try:
            await self.engine.stop_trading()
            
            # Cancel monitoring task
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            return {
                "status": "success",
                "message": "Trading system stopped successfully",
                "stopped_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to stop trading system: {e}")
            return {
                "status": "error",
                "message": f"Failed to stop trading system: {str(e)}"
            }
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        try:
            status = self.engine.get_portfolio_status()
            if not status:
                return {
                    "status": "error",
                    "message": "No active portfolio found"
                }
            
            return {
                "status": "success",
                "data": status
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio status: {e}")
            return {
                "status": "error",
                "message": f"Failed to get portfolio status: {str(e)}"
            }
    
    def get_trading_performance(self, period: str = "all_time") -> Dict[str, Any]:
        """Get trading performance metrics"""
        try:
            if not self.engine.portfolio:
                return {
                    "status": "error",
                    "message": "No active portfolio found"
                }
            
            portfolio = self.engine.portfolio
            trades = storage.get_trades_by_portfolio(portfolio.id)
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(portfolio, trades, period)
            
            return {
                "status": "success",
                "data": {
                    "period": period,
                    "portfolio_id": portfolio.id,
                    "metrics": metrics,
                    "calculated_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {
                "status": "error",
                "message": f"Failed to get performance metrics: {str(e)}"
            }
    
    def get_trade_history(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get trade history"""
        try:
            trades = self.engine.get_recent_trades(limit + offset)
            
            # Apply pagination
            paginated_trades = trades[offset:offset + limit]
            
            return {
                "status": "success",
                "data": {
                    "trades": paginated_trades,
                    "total": len(trades),
                    "limit": limit,
                    "offset": offset,
                    "has_more": len(trades) > offset + limit
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            return {
                "status": "error",
                "message": f"Failed to get trade history: {str(e)}"
            }
    
    def get_position_details(self) -> Dict[str, Any]:
        """Get detailed position information"""
        try:
            if not self.engine.portfolio:
                return {
                    "status": "error",
                    "message": "No active portfolio found"
                }
            
            positions = []
            for symbol, position_data in self.engine.portfolio.positions.items():
                positions.append({
                    "symbol": symbol,
                    "quantity": position_data["quantity"],
                    "average_price": position_data["average_price"],
                    "current_price": position_data["current_price"],
                    "market_value": position_data["market_value"],
                    "unrealized_pnl": position_data["unrealized_pnl"],
                    "realized_pnl": position_data.get("realized_pnl", 0.0),
                    "pnl_percentage": ((position_data["current_price"] - position_data["average_price"]) / position_data["average_price"]) * 100 if position_data["average_price"] > 0 else 0
                })
            
            return {
                "status": "success",
                "data": {
                    "positions": positions,
                    "total_positions": len(positions),
                    "total_market_value": sum(p["market_value"] for p in positions),
                    "total_unrealized_pnl": sum(p["unrealized_pnl"] for p in positions)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get position details: {e}")
            return {
                "status": "error",
                "message": f"Failed to get position details: {str(e)}"
            }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get trading system health status"""
        try:
            health_status = {
                "is_running": self.engine.is_running,
                "has_portfolio": self.engine.portfolio is not None,
                "monitoring_active": self.monitoring_task and not self.monitoring_task.done(),
                "market_providers_count": len(self.engine.market_providers),
                "strategies_count": len(self.engine.strategies),
                "target_symbols": len(self.engine.target_symbols),
                "last_check": datetime.utcnow().isoformat()
            }
            
            # Add portfolio info if available
            if self.engine.portfolio:
                health_status.update({
                    "portfolio_id": self.engine.portfolio.id,
                    "portfolio_value": float(self.engine.portfolio.total_value),
                    "available_cash": float(self.engine.portfolio.available_cash),
                    "positions_count": len(self.engine.portfolio.positions),
                    "total_trades": self.engine.portfolio.performance_metrics.get("total_trades", 0)
                })
            
            # Determine overall health
            overall_health = "healthy"
            if not self.engine.is_running:
                overall_health = "stopped"
            elif not self.engine.portfolio:
                overall_health = "warning"
            elif not (self.monitoring_task and not self.monitoring_task.done()):
                overall_health = "warning"
            
            health_status["overall_health"] = overall_health
            
            return {
                "status": "success",
                "data": health_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                "status": "error",
                "message": f"Failed to get system health: {str(e)}"
            }
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        logger.info("Starting trading system monitoring")
        
        while True:
            try:
                # Perform health checks
                await self._perform_health_checks()
                
                # Log system status every 5 minutes
                if datetime.utcnow().minute % 5 == 0:
                    await self._log_system_status()
                
                # Wait 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Continue monitoring even if there's an error
    
    async def _perform_health_checks(self) -> None:
        """Perform system health checks"""
        try:
            # Check if engine is still running
            if not self.engine.is_running:
                logger.warning("Trading engine is not running")
                return
            
            # Check portfolio status
            if not self.engine.portfolio:
                logger.warning("No active portfolio found")
                return
            
            # Check for stale data (no updates in last 5 minutes)
            if self.engine.portfolio.updated_at < datetime.utcnow() - timedelta(minutes=5):
                logger.warning("Portfolio data appears stale")
            
            # Check available cash
            if self.engine.portfolio.available_cash < Decimal("10"):
                logger.warning("Low available cash for trading")
            
            # Check for excessive losses
            total_return_pct = self.engine.portfolio.performance_metrics.get("total_return_pct", 0)
            if total_return_pct < -20:  # More than 20% loss
                logger.warning(f"High losses detected: {total_return_pct:.2f}%")
            
        except Exception as e:
            logger.error(f"Error in health checks: {e}")
    
    async def _log_system_status(self) -> None:
        """Log current system status"""
        try:
            if self.engine.portfolio:
                portfolio = self.engine.portfolio
                logger.info(
                    f"Trading System Status - "
                    f"Value: ${portfolio.total_value:.2f}, "
                    f"Cash: ${portfolio.available_cash:.2f}, "
                    f"Positions: {len(portfolio.positions)}, "
                    f"Trades: {portfolio.performance_metrics.get('total_trades', 0)}, "
                    f"Return: {portfolio.performance_metrics.get('total_return_pct', 0):.2f}%"
                )
        except Exception as e:
            logger.error(f"Error logging system status: {e}")
    
    def _calculate_performance_metrics(self, portfolio: Portfolio, trades: List[Trade], period: str) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        try:
            # Filter trades by period
            now = datetime.utcnow()
            if period == "daily":
                start_date = now - timedelta(days=1)
            elif period == "weekly":
                start_date = now - timedelta(weeks=1)
            elif period == "monthly":
                start_date = now - timedelta(days=30)
            else:  # all_time
                start_date = datetime.min
            
            period_trades = [t for t in trades if (t.executed_at or t.created_at) >= start_date]
            
            # Basic metrics
            total_trades = len(period_trades)
            winning_trades = len([t for t in period_trades if t.pnl and t.pnl > 0])
            losing_trades = len([t for t in period_trades if t.pnl and t.pnl < 0])
            
            # P&L metrics
            total_pnl = sum(float(t.pnl) for t in period_trades if t.pnl)
            win_amounts = [float(t.pnl) for t in period_trades if t.pnl and t.pnl > 0]
            loss_amounts = [abs(float(t.pnl)) for t in period_trades if t.pnl and t.pnl < 0]
            
            # Calculate metrics
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            avg_win = sum(win_amounts) / len(win_amounts) if win_amounts else 0
            avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0
            profit_factor = sum(win_amounts) / sum(loss_amounts) if loss_amounts and sum(loss_amounts) > 0 else float('inf') if win_amounts else 0
            
            # Portfolio metrics
            total_return = float(portfolio.total_value - portfolio.initial_capital)
            total_return_pct = (total_return / float(portfolio.initial_capital)) * 100
            
            return {
                "total_return": total_return,
                "total_return_pct": total_return_pct,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "average_win": avg_win,
                "average_loss": avg_loss,
                "largest_win": max(win_amounts) if win_amounts else 0,
                "largest_loss": max(loss_amounts) if loss_amounts else 0,
                "total_pnl": total_pnl,
                "current_portfolio_value": float(portfolio.total_value),
                "available_cash": float(portfolio.available_cash),
                "positions_count": len(portfolio.positions)
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}


# Global trading service instance
trading_service = TradingService()