from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    UPDATING = "updating"
    ERROR = "error"
    TERMINATED = "terminated"


class AgentType(str, Enum):
    TRADING = "trading"
    ANALYSIS = "analysis"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    CUSTOM = "custom"


class AgentConfig(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier")
    customer_id: str = Field(..., description="Customer identifier")
    agent_type: AgentType
    name: str
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    autogen_config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"


class AgentInstance(BaseModel):
    agent_id: str
    container_id: Optional[str] = None
    status: AgentStatus = AgentStatus.INITIALIZING
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)  # For GPU deployment info


class AgentMessage(BaseModel):
    message_id: str = Field(..., description="Unique message identifier")
    source_agent_id: str
    target_agent_id: Optional[str] = None  # None means broadcast
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


class AgentTeam(BaseModel):
    team_id: str = Field(..., description="Unique team identifier")
    customer_id: str
    name: str
    description: Optional[str] = None
    agent_ids: List[str] = Field(default_factory=list)
    orchestrator_config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class CustomerConfig(BaseModel):
    customer_id: str = Field(..., description="Unique customer identifier")
    name: str
    email: str
    api_key: str
    tier: str = "basic"  # basic, pro, enterprise
    max_agents: int = 5
    max_teams: int = 2
    rate_limits: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True