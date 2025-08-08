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

