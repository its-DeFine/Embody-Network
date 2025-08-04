"""
P&L Tracking Module

Tracks profit and loss for all trading activities with real market prices.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from ...dependencies import get_redis

logger = logging.getLogger(__name__)


class PnLTracker:
    """Tracks trading P&L with real market data"""
    
    def __init__(self):
        self.redis = None
        self.positions = defaultdict(lambda: {"quantity": 0, "cost_basis": 0})
        self.realized_pnl = 0
        self.trades = []
        
    async def initialize(self):
        """Initialize P&L tracker"""
        self.redis = await get_redis()
        await self.load_state()
        logger.info("P&L Tracker initialized")
        
    async def record_trade(self, trade: Dict) -> Dict:
        """Record a trade and calculate P&L"""
        symbol = trade.get("symbol")
        action = trade.get("action")
        quantity = trade.get("quantity", 0)
        price = trade.get("execution_price", 0)
        commission = trade.get("commission", 0)
        
        if not all([symbol, action, quantity, price]):
            return {"error": "Invalid trade data"}
            
        # Calculate P&L based on action
        pnl = 0
        if action == "buy":
            # Update position
            current_pos = self.positions[symbol]
            new_quantity = current_pos["quantity"] + quantity
            new_cost = current_pos["cost_basis"] + (price * quantity) + commission
            
            self.positions[symbol] = {
                "quantity": new_quantity,
                "cost_basis": new_cost,
                "avg_price": new_cost / new_quantity if new_quantity > 0 else 0
            }
            
        elif action == "sell":
            # Calculate realized P&L
            current_pos = self.positions[symbol]
            if current_pos["quantity"] > 0:
                avg_cost = current_pos["cost_basis"] / current_pos["quantity"]
                gross_proceeds = price * quantity
                cost_of_sold = avg_cost * quantity
                pnl = gross_proceeds - cost_of_sold - commission
                
                # Update position
                new_quantity = current_pos["quantity"] - quantity
                new_cost = current_pos["cost_basis"] - cost_of_sold
                
                if new_quantity > 0:
                    self.positions[symbol] = {
                        "quantity": new_quantity,
                        "cost_basis": new_cost,
                        "avg_price": new_cost / new_quantity
                    }
                else:
                    # Position closed
                    self.positions[symbol] = {"quantity": 0, "cost_basis": 0}
                    
                self.realized_pnl += pnl
                
        # Record trade
        trade_record = {
            "id": trade.get("id"),
            "timestamp": trade.get("timestamp", datetime.utcnow().isoformat()),
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "commission": commission,
            "pnl": pnl,
            "cumulative_pnl": self.realized_pnl
        }
        
        self.trades.append(trade_record)
        
        # Save state
        await self.save_state()
        
        return trade_record
        
    async def get_position_summary(self) -> Dict:
        """Get current position summary with unrealized P&L"""
        from ..market.market_data import market_data_service
        
        summary = {
            "positions": {},
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": 0,
            "total_pnl": 0,
            "total_value": 0
        }
        
        # Calculate unrealized P&L for open positions
        for symbol, position in self.positions.items():
            if position["quantity"] > 0:
                # Get current market price
                current_price = await market_data_service.get_current_price(symbol)
                
                if current_price:
                    market_value = current_price * position["quantity"]
                    unrealized_pnl = market_value - position["cost_basis"]
                    
                    summary["positions"][symbol] = {
                        "quantity": position["quantity"],
                        "avg_cost": position.get("avg_price", 0),
                        "current_price": current_price,
                        "market_value": market_value,
                        "unrealized_pnl": unrealized_pnl,
                        "percent_change": (unrealized_pnl / position["cost_basis"] * 100) if position["cost_basis"] > 0 else 0
                    }
                    
                    summary["unrealized_pnl"] += unrealized_pnl
                    summary["total_value"] += market_value
                    
        summary["total_pnl"] = summary["realized_pnl"] + summary["unrealized_pnl"]
        
        return summary
        
    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get recent trade history"""
        return self.trades[-limit:]
        
    async def get_daily_pnl(self) -> Dict:
        """Get P&L breakdown by day"""
        daily_pnl = defaultdict(lambda: {"trades": 0, "pnl": 0})
        
        for trade in self.trades:
            date = trade["timestamp"][:10]  # Extract date
            daily_pnl[date]["trades"] += 1
            daily_pnl[date]["pnl"] += trade.get("pnl", 0)
            
        return dict(daily_pnl)
        
    async def save_state(self):
        """Save P&L state to Redis"""
        if self.redis:
            state = {
                "positions": dict(self.positions),
                "realized_pnl": self.realized_pnl,
                "trades": self.trades
            }
            await self.redis.set("pnl:state", json.dumps(state))
            
    async def load_state(self):
        """Load P&L state from Redis"""
        if self.redis:
            state_data = await self.redis.get("pnl:state")
            if state_data:
                state = json.loads(state_data)
                self.positions = defaultdict(lambda: {"quantity": 0, "cost_basis": 0}, state.get("positions", {}))
                self.realized_pnl = state.get("realized_pnl", 0)
                self.trades = state.get("trades", [])
                
    async def reset(self):
        """Reset P&L tracking"""
        self.positions.clear()
        self.realized_pnl = 0
        self.trades = []
        if self.redis:
            await self.redis.delete("pnl:state")
            

# Global P&L tracker instance
pnl_tracker = PnLTracker()