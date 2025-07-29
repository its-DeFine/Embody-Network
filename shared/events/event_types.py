from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class EventType(str, Enum):
    # Agent lifecycle events
    AGENT_CREATED = "agent.created"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_UPDATED = "agent.updated"
    AGENT_ERROR = "agent.error"
    AGENT_HEARTBEAT = "agent.heartbeat"
    
    # Team events
    TEAM_CREATED = "team.created"
    TEAM_UPDATED = "team.updated"
    TEAM_DELETED = "team.deleted"
    
    # Trading events
    TRADE_SIGNAL = "trade.signal"
    TRADE_EXECUTED = "trade.executed"
    TRADE_FAILED = "trade.failed"
    MARKET_UPDATE = "market.update"
    
    # Communication events
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_FAILED = "message.failed"
    
    # System events
    DEPLOYMENT_STARTED = "deployment.started"
    DEPLOYMENT_COMPLETED = "deployment.completed"
    DEPLOYMENT_FAILED = "deployment.failed"
    SYSTEM_ALERT = "system.alert"
    
    # Admin events
    ADMIN_BROADCAST = "admin.broadcast"
    ADMIN_KILLSWITCH = "admin.killswitch"
    ADMIN_AGENT_STOPPED = "admin.agent.stopped"
    
    # GPU Orchestrator events
    ORCHESTRATOR_REGISTERED = "orchestrator.registered"
    ORCHESTRATOR_HEALTH_CHECK = "orchestrator.health_check"
    ORCHESTRATOR_HEALTH_UPDATE = "orchestrator.health_update"
    ORCHESTRATOR_SHUTDOWN = "orchestrator.shutdown"
    AGENT_DEPLOY_REQUEST = "agent.deploy_request"
    AGENT_DEPLOYED = "agent.deployed"
    AGENT_DEPLOYMENT_FAILED = "agent.deployment_failed"


class Event(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    event_type: EventType
    source: str = Field(..., description="Service or agent that generated the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    customer_id: Optional[str] = None


class EventHandler:
    """Base class for event handlers"""
    
    def __init__(self, event_types: List[EventType]):
        self.event_types = event_types
    
    async def handle(self, event: Event):
        raise NotImplementedError("Subclasses must implement handle method")
    
    def can_handle(self, event: Event) -> bool:
        return event.event_type in self.event_types