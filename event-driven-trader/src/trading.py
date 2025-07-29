"""
Trading Engine - Executes trades and manages positions.
Simple, clean implementation focused on paper trading.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import yaml


logger = logging.getLogger(__name__)


@dataclass
class Position:
    """
    Represents an open trading position.
    
    Attributes:
        symbol: Token symbol (BTC, ETH, etc)
        entry_price: Price when position was opened
        size: Position size in USD
        side: 'LONG' or 'SHORT'
        entry_time: When position was opened
        stop_loss: Stop loss price
        take_profit: Take profit price
    """
    symbol: str
    entry_price: float
    size: float
    side: str
    entry_time: datetime
    stop_loss: float
    take_profit: float
    
    def get_pnl(self, current_price: float) -> float:
        """Calculate current P&L for this position"""
        if self.side == 'LONG':
            return self.size * (current_price / self.entry_price - 1)
        else:  # SHORT
            return self.size * (1 - current_price / self.entry_price)
    
    def get_pnl_percent(self, current_price: float) -> float:
        """Calculate P&L percentage"""
        if self.side == 'LONG':
            return (current_price / self.entry_price - 1) * 100
        else:  # SHORT
            return (1 - current_price / self.entry_price) * 100


class TradingEngine:
    """
    Simple trading engine for paper trading.
    
    Features:
    - Position management
    - Risk management (position sizing, stops)
    - Performance tracking
    - Clean, understandable logic
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.config = config.get('trading', {})
        
        # Initialize state
        self.balance = self.config.get('starting_balance', 100.0)
        self.starting_balance = self.balance
        self.positions: Dict[str, Position] = {}
        
        # Risk parameters
        self.max_positions = self.config.get('max_positions', 5)
        self.position_size_percent = self.config.get('position_size_percent', 20)
        self.stop_loss_percent = self.config.get('stop_loss_percent', 5)
        self.take_profit_percent = self.config.get('take_profit_percent', 10)
        
        # Track performance
        self.trades_history = []
        self.total_trades = 0
        self.winning_trades = 0
        
        logger.info(f"Trading engine initialized with ${self.balance:.2f}")
    
    def execute_trade(self, symbol: str, action: str, reason: str = "") -> bool:
        """
        Execute a trade (BUY/SELL).
        
        Args:
            symbol: Token to trade
            action: 'BUY' or 'SELL' (SELL opens short position)
            reason: Why this trade is being made
            
        Returns:
            True if trade executed successfully
        """
        # Check if we already have a position
        if symbol in self.positions:
            logger.warning(f"Already have position in {symbol}")
            return False
        
        # Check max positions
        if len(self.positions) >= self.max_positions:
            logger.warning("Max positions reached")
            return False
        
        # Calculate position size
        position_size = self.balance * (self.position_size_percent / 100)
        if position_size > self.balance:
            position_size = self.balance * 0.95  # Use 95% of available
        
        if position_size < 1:
            logger.warning("Insufficient balance for trade")
            return False
        
        # Get current price (simplified - would come from API)
        current_price = self._get_current_price(symbol)
        
        # Determine position side
        side = 'LONG' if action == 'BUY' else 'SHORT'
        
        # Calculate stops
        if side == 'LONG':
            stop_loss = current_price * (1 - self.stop_loss_percent / 100)
            take_profit = current_price * (1 + self.take_profit_percent / 100)
        else:
            stop_loss = current_price * (1 + self.stop_loss_percent / 100)
            take_profit = current_price * (1 - self.take_profit_percent / 100)
        
        # Create position
        position = Position(
            symbol=symbol,
            entry_price=current_price,
            size=position_size,
            side=side,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Update state
        self.positions[symbol] = position
        self.balance -= position_size
        self.total_trades += 1
        
        # Log trade
        logger.info(f"Opened {side} position: {symbol} @ ${current_price:.2f}")
        logger.info(f"Size: ${position_size:.2f}, Stop: ${stop_loss:.2f}, Target: ${take_profit:.2f}")
        logger.info(f"Reason: {reason}")
        
        # Record trade
        self.trades_history.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': side,
            'entry_price': current_price,
            'size': position_size,
            'reason': reason
        })
        
        return True
    
    def close_position(self, symbol: str, reason: str = "") -> bool:
        """Close an open position"""
        if symbol not in self.positions:
            logger.warning(f"No position in {symbol} to close")
            return False
        
        position = self.positions[symbol]
        current_price = self._get_current_price(symbol)
        
        # Calculate P&L
        pnl = position.get_pnl(current_price)
        pnl_percent = position.get_pnl_percent(current_price)
        
        # Update balance
        self.balance += position.size + pnl
        
        # Track wins
        if pnl > 0:
            self.winning_trades += 1
        
        # Remove position
        del self.positions[symbol]
        
        # Log closure
        logger.info(f"Closed {position.side} position: {symbol}")
        logger.info(f"P&L: ${pnl:.2f} ({pnl_percent:.1f}%)")
        logger.info(f"Reason: {reason}")
        
        return True
    
    def check_exit_conditions(self, position: Position) -> Tuple[bool, str]:
        """
        Check if a position should be closed.
        
        Returns:
            (should_close, reason)
        """
        current_price = self._get_current_price(position.symbol)
        
        # Check stop loss
        if position.side == 'LONG' and current_price <= position.stop_loss:
            return True, "Stop loss hit"
        elif position.side == 'SHORT' and current_price >= position.stop_loss:
            return True, "Stop loss hit"
        
        # Check take profit
        if position.side == 'LONG' and current_price >= position.take_profit:
            return True, "Take profit hit"
        elif position.side == 'SHORT' and current_price <= position.take_profit:
            return True, "Take profit hit"
        
        # Check hold time (optional: close after X hours)
        hold_time = (datetime.now() - position.entry_time).total_seconds() / 3600
        if hold_time > 24:  # Close after 24 hours
            return True, "Max hold time reached"
        
        return False, ""
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all open positions"""
        return self.positions.copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total_value = self.balance
        for position in self.positions.values():
            current_price = self._get_current_price(position.symbol)
            total_value += position.size + position.get_pnl(current_price)
        
        total_pnl = total_value - self.starting_balance
        pnl_percent = (total_pnl / self.starting_balance) * 100
        
        win_rate = 0
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
        
        return {
            'current_balance': self.balance,
            'total_value': total_value,
            'total_pnl': total_pnl,
            'pnl_percent': pnl_percent,
            'open_positions': len(self.positions),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': win_rate
        }
    
    def _get_current_price(self, symbol: str) -> float:
        """
        Get current price for a symbol.
        In production, this would fetch from an API.
        For now, using mock prices.
        """
        # Mock prices for testing
        mock_prices = {
            'BTC': 43000.0,
            'ETH': 2200.0,
            'ARB': 1.80
        }
        
        base_price = mock_prices.get(symbol, 100.0)
        
        # Add some random variation to simulate price movement
        import random
        variation = random.uniform(0.99, 1.01)
        
        return base_price * variation