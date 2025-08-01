"""
Database models for the trading system
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal
from dataclasses import dataclass, asdict
import json


class TradeStatus(str, Enum):
    """Trade execution status"""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TradeType(str, Enum):
    """Type of trade"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class TradingStrategy(str, Enum):
    """Trading strategy types"""
    ARBITRAGE = "arbitrage"
    SCALPING = "scalping"
    DCA = "dca"  # Dollar Cost Averaging
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"


@dataclass
class Portfolio:
    """Portfolio model to track capital and positions"""
    id: str
    initial_capital: Decimal
    current_capital: Decimal
    available_cash: Decimal
    total_value: Decimal
    positions: Dict[str, Dict[str, Any]]  # symbol -> position data
    performance_metrics: Dict[str, float]
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert Decimal to float for JSON serialization
        result["initial_capital"] = float(self.initial_capital)
        result["current_capital"] = float(self.current_capital)
        result["available_cash"] = float(self.available_cash)
        result["total_value"] = float(self.total_value)
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Portfolio":
        """Create Portfolio from dictionary"""
        return cls(
            id=data["id"],
            initial_capital=Decimal(str(data["initial_capital"])),
            current_capital=Decimal(str(data["current_capital"])),
            available_cash=Decimal(str(data["available_cash"])),
            total_value=Decimal(str(data["total_value"])),
            positions=data["positions"],
            performance_metrics=data["performance_metrics"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


@dataclass
class Trade:
    """Trade model to record all executions"""
    id: str
    portfolio_id: str
    symbol: str
    trade_type: TradeType
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal]
    executed_price: Optional[Decimal]
    executed_quantity: Optional[Decimal]
    status: TradeStatus
    strategy: TradingStrategy
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    commission: Decimal
    pnl: Optional[Decimal]
    metadata: Dict[str, Any]  # Additional trade data
    created_at: datetime
    executed_at: Optional[datetime]
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert Decimal to float for JSON serialization
        result["quantity"] = float(self.quantity)
        result["price"] = float(self.price) if self.price else None
        result["executed_price"] = float(self.executed_price) if self.executed_price else None
        result["executed_quantity"] = float(self.executed_quantity) if self.executed_quantity else None
        result["stop_loss"] = float(self.stop_loss) if self.stop_loss else None
        result["take_profit"] = float(self.take_profit) if self.take_profit else None
        result["commission"] = float(self.commission)
        result["pnl"] = float(self.pnl) if self.pnl else None
        result["created_at"] = self.created_at.isoformat()
        result["executed_at"] = self.executed_at.isoformat() if self.executed_at else None
        result["updated_at"] = self.updated_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trade":
        """Create Trade from dictionary"""
        return cls(
            id=data["id"],
            portfolio_id=data["portfolio_id"],
            symbol=data["symbol"],
            trade_type=TradeType(data["trade_type"]),
            order_type=OrderType(data["order_type"]),
            quantity=Decimal(str(data["quantity"])),
            price=Decimal(str(data["price"])) if data["price"] else None,
            executed_price=Decimal(str(data["executed_price"])) if data["executed_price"] else None,
            executed_quantity=Decimal(str(data["executed_quantity"])) if data["executed_quantity"] else None,
            status=TradeStatus(data["status"]),
            strategy=TradingStrategy(data["strategy"]),
            stop_loss=Decimal(str(data["stop_loss"])) if data["stop_loss"] else None,
            take_profit=Decimal(str(data["take_profit"])) if data["take_profit"] else None,
            commission=Decimal(str(data["commission"])),
            pnl=Decimal(str(data["pnl"])) if data["pnl"] else None,
            metadata=data["metadata"],
            created_at=datetime.fromisoformat(data["created_at"]),
            executed_at=datetime.fromisoformat(data["executed_at"]) if data["executed_at"] else None,
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


@dataclass
class Position:
    """Position model for tracking holdings"""
    id: str
    portfolio_id: str
    symbol: str
    quantity: Decimal
    average_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    cost_basis: Decimal
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert Decimal to float for JSON serialization
        for field in ["quantity", "average_price", "current_price", "market_value", 
                     "unrealized_pnl", "realized_pnl", "cost_basis"]:
            result[field] = float(getattr(self, field))
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        return result


@dataclass
class PerformanceMetrics:
    """Performance metrics model for tracking"""
    id: str
    portfolio_id: str
    period: str  # daily, weekly, monthly, all_time
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    volatility: float
    beta: Optional[float]
    alpha: Optional[float]
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        return result


@dataclass
class TradingSession:
    """Trading session model"""
    id: str
    portfolio_id: str
    strategy: TradingStrategy
    status: str  # active, paused, stopped
    start_time: datetime
    end_time: Optional[datetime]
    target_symbols: List[str]
    parameters: Dict[str, Any]
    performance: Dict[str, float]
    trades_count: int
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["start_time"] = self.start_time.isoformat()
        result["end_time"] = self.end_time.isoformat() if self.end_time else None
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        return result


# In-memory storage for demo purposes
# In production, this should be replaced with a proper database
class InMemoryStorage:
    """Simple in-memory storage for models"""
    
    def __init__(self):
        self.portfolios: Dict[str, Portfolio] = {}
        self.trades: Dict[str, Trade] = {}
        self.positions: Dict[str, Position] = {}
        self.performance_metrics: Dict[str, PerformanceMetrics] = {}
        self.trading_sessions: Dict[str, TradingSession] = {}
    
    def save_portfolio(self, portfolio: Portfolio) -> Portfolio:
        """Save portfolio to storage"""
        portfolio.updated_at = datetime.utcnow()
        self.portfolios[portfolio.id] = portfolio
        return portfolio
    
    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        return self.portfolios.get(portfolio_id)
    
    def save_trade(self, trade: Trade) -> Trade:
        """Save trade to storage"""
        trade.updated_at = datetime.utcnow()
        self.trades[trade.id] = trade
        return trade
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get trade by ID"""
        return self.trades.get(trade_id)
    
    def get_trades_by_portfolio(self, portfolio_id: str) -> List[Trade]:
        """Get all trades for a portfolio"""
        return [trade for trade in self.trades.values() if trade.portfolio_id == portfolio_id]
    
    def save_position(self, position: Position) -> Position:
        """Save position to storage"""
        position.updated_at = datetime.utcnow()
        self.positions[position.id] = position
        return position
    
    def get_positions_by_portfolio(self, portfolio_id: str) -> List[Position]:
        """Get all positions for a portfolio"""
        return [pos for pos in self.positions.values() if pos.portfolio_id == portfolio_id]
    
    def save_performance_metrics(self, metrics: PerformanceMetrics) -> PerformanceMetrics:
        """Save performance metrics to storage"""
        metrics.updated_at = datetime.utcnow()
        self.performance_metrics[metrics.id] = metrics
        return metrics
    
    def get_performance_metrics(self, portfolio_id: str, period: str) -> Optional[PerformanceMetrics]:
        """Get performance metrics by portfolio and period"""
        for metrics in self.performance_metrics.values():
            if metrics.portfolio_id == portfolio_id and metrics.period == period:
                return metrics
        return None
    
    def save_trading_session(self, session: TradingSession) -> TradingSession:
        """Save trading session to storage"""
        session.updated_at = datetime.utcnow()
        self.trading_sessions[session.id] = session
        return session
    
    def get_active_trading_sessions(self, portfolio_id: str) -> List[TradingSession]:
        """Get active trading sessions for a portfolio"""
        return [session for session in self.trading_sessions.values() 
                if session.portfolio_id == portfolio_id and session.status == "active"]


# Global storage instance
storage = InMemoryStorage()