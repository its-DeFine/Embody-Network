"""
Database models for cluster tracking
"""
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./central-manager.db")

# Create engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite specific settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # PostgreSQL settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

class ClusterRegistration(Base):
    """Track orchestrator cluster registrations"""
    __tablename__ = "cluster_registrations"
    
    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(String, unique=True, index=True, nullable=False)
    cluster_name = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    agent_type = Column(String, nullable=False)
    
    # Connection info
    host_address = Column(String, nullable=False)
    api_port = Column(Integer, nullable=False)
    external_ip = Column(String)
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    registered_at = Column(DateTime, default=datetime.utcnow)
    
    # Capabilities and metadata
    capabilities = Column(Text)  # JSON string
    resources = Column(Text)  # JSON string
    cluster_metadata = Column(Text)  # JSON string

class ClusterHeartbeat(Base):
    """Track cluster heartbeat history"""
    __tablename__ = "cluster_heartbeats"
    
    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    health_score = Column(Integer)
    active_agents = Column(Integer, default=0)
    resources = Column(Text)  # JSON string

class Trade(Base):
    """Track individual trades"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)  # 'buy' or 'sell'
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    
    # Status and timestamps
    status = Column(String, default='pending')  # pending, executed, failed
    executed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Strategy and agent info
    strategy = Column(String)
    agent_id = Column(String)
    cluster_name = Column(String)  # Name of the cluster that executed the trade
    reason = Column(Text)
    
class Position(Base):
    """Track current positions"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    average_price = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float)
    market_value = Column(Float)
    unrealized_pnl = Column(Float)
    unrealized_pnl_percent = Column(Float)
    
    # Timestamps
    first_bought_at = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
class PortfolioSnapshot(Base):
    """Track portfolio value over time"""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)
    daily_pnl = Column(Float)
    daily_pnl_percent = Column(Float)
    total_pnl = Column(Float)
    total_pnl_percent = Column(Float)
    
    # Additional metrics
    num_positions = Column(Integer, default=0)
    winning_positions = Column(Integer, default=0)
    losing_positions = Column(Integer, default=0)

# Database initialization
def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database initialized successfully with URL: {DATABASE_URL}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions for cluster tracking
def register_cluster(db, container_id: str, cluster_name: str, agent_id: str, 
                    host_address: str, api_port: int, **kwargs):
    """Register a new cluster or update existing"""
    cluster = db.query(ClusterRegistration).filter_by(container_id=container_id).first()
    
    if cluster:
        # Update existing
        cluster.is_active = True
        cluster.last_heartbeat = datetime.utcnow()
        cluster.host_address = host_address
        cluster.api_port = api_port
        for key, value in kwargs.items():
            if hasattr(cluster, key):
                setattr(cluster, key, value)
    else:
        # Create new
        cluster = ClusterRegistration(
            container_id=container_id,
            cluster_name=cluster_name,
            agent_id=agent_id,
            agent_type=kwargs.get('agent_type', 'orchestrator_cluster'),
            host_address=host_address,
            api_port=api_port,
            external_ip=kwargs.get('external_ip'),
            capabilities=kwargs.get('capabilities'),
            resources=kwargs.get('resources'),
            cluster_metadata=kwargs.get('cluster_metadata')
        )
        db.add(cluster)
    
    db.commit()
    return cluster

def update_heartbeat(db, container_id: str, health_score: int = 100, **kwargs):
    """Update cluster heartbeat"""
    # Update cluster registration
    cluster = db.query(ClusterRegistration).filter_by(container_id=container_id).first()
    if cluster:
        cluster.last_heartbeat = datetime.utcnow()
        cluster.is_active = True
        
        # Record heartbeat history
        heartbeat = ClusterHeartbeat(
            container_id=container_id,
            health_score=health_score,
            active_agents=kwargs.get('active_agents', 0),
            resources=kwargs.get('resources')
        )
        db.add(heartbeat)
        db.commit()
        return True
    return False

def get_active_clusters(db):
    """Get all active clusters"""
    # Consider clusters active if heartbeat within last 2 minutes
    from datetime import timedelta
    cutoff_time = datetime.utcnow() - timedelta(minutes=2)
    
    clusters = db.query(ClusterRegistration).filter(
        ClusterRegistration.is_active == True,
        ClusterRegistration.last_heartbeat > cutoff_time
    ).all()
    
    return clusters

def mark_cluster_inactive(db, container_id: str):
    """Mark cluster as inactive"""
    cluster = db.query(ClusterRegistration).filter_by(container_id=container_id).first()
    if cluster:
        cluster.is_active = False
        db.commit()
        return True
    return False

# Trading data functions
def record_trade(db, trade_data: dict):
    """Record a new trade"""
    trade = Trade(
        trade_id=trade_data.get('trade_id', f"trade_{datetime.utcnow().timestamp()}"),
        symbol=trade_data['symbol'],
        side=trade_data['side'],
        quantity=trade_data['quantity'],
        price=trade_data['price'],
        total_value=trade_data['quantity'] * trade_data['price'],
        status=trade_data.get('status', 'executed'),
        strategy=trade_data.get('strategy'),
        agent_id=trade_data.get('agent_id'),
        cluster_name=trade_data.get('cluster_name'),
        reason=trade_data.get('reason')
    )
    db.add(trade)
    
    # Update position
    update_position(db, trade_data['symbol'], trade_data['side'], 
                   trade_data['quantity'], trade_data['price'])
    
    db.commit()
    return trade

def update_position(db, symbol: str, side: str, quantity: int, price: float):
    """Update position after a trade"""
    position = db.query(Position).filter_by(symbol=symbol).first()
    
    if not position:
        if side == 'buy':
            position = Position(
                symbol=symbol,
                quantity=quantity,
                average_price=price,
                first_bought_at=datetime.utcnow()
            )
            db.add(position)
    else:
        if side == 'buy':
            # Update average price
            total_value = (position.quantity * position.average_price) + (quantity * price)
            position.quantity += quantity
            position.average_price = total_value / position.quantity if position.quantity > 0 else 0
        else:  # sell
            position.quantity -= quantity
            if position.quantity <= 0:
                db.delete(position)
    
    if position and position.quantity > 0:
        position.last_updated = datetime.utcnow()
    
    db.commit()

def get_portfolio_status(db):
    """Get current portfolio status"""
    positions = db.query(Position).filter(Position.quantity > 0).all()
    total_value = 0
    
    position_data = {}
    for pos in positions:
        if pos.current_price:
            pos.market_value = pos.quantity * pos.current_price
            pos.unrealized_pnl = pos.market_value - (pos.quantity * pos.average_price)
            pos.unrealized_pnl_percent = (pos.unrealized_pnl / (pos.quantity * pos.average_price)) * 100
            total_value += pos.market_value
        
        position_data[pos.symbol] = {
            'quantity': pos.quantity,
            'average_price': pos.average_price,
            'current_price': pos.current_price,
            'market_value': pos.market_value,
            'unrealized_pnl': pos.unrealized_pnl,
            'unrealized_pnl_percent': pos.unrealized_pnl_percent
        }
    
    # Get recent trades
    recent_trades = db.query(Trade).order_by(Trade.executed_at.desc()).limit(10).all()
    
    return {
        'positions': position_data,
        'total_value': total_value,
        'num_positions': len(positions),
        'recent_trades': [{
            'symbol': t.symbol,
            'side': t.side,
            'quantity': t.quantity,
            'price': t.price,
            'total_value': t.total_value,
            'executed_at': t.executed_at.isoformat() if t.executed_at else None,
            'agent_id': t.agent_id,
            'cluster_name': t.cluster_name
        } for t in recent_trades]
    }

def record_portfolio_snapshot(db, cash_balance: float = 100000.0):
    """Record a portfolio snapshot"""
    portfolio = get_portfolio_status(db)
    positions_value = portfolio['total_value']
    total_value = cash_balance + positions_value
    
    # Get yesterday's snapshot for daily P&L
    yesterday = datetime.utcnow() - timedelta(days=1)
    prev_snapshot = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.timestamp > yesterday
    ).order_by(PortfolioSnapshot.timestamp.desc()).first()
    
    daily_pnl = 0
    daily_pnl_percent = 0
    if prev_snapshot:
        daily_pnl = total_value - prev_snapshot.total_value
        daily_pnl_percent = (daily_pnl / prev_snapshot.total_value) * 100 if prev_snapshot.total_value > 0 else 0
    
    snapshot = PortfolioSnapshot(
        total_value=total_value,
        cash_balance=cash_balance,
        positions_value=positions_value,
        daily_pnl=daily_pnl,
        daily_pnl_percent=daily_pnl_percent,
        num_positions=portfolio['num_positions']
    )
    
    db.add(snapshot)
    db.commit()
    return snapshot