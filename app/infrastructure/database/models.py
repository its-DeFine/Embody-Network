"""
Database models for the VTuber system
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import json


class AgentStatus(str, Enum):
    """Agent status types"""
    ONLINE = "online"
    OFFLINE = "offline"
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"


class StreamStatus(str, Enum):
    """Stream status types"""
    LIVE = "live"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


class CommandType(str, Enum):
    """Command types for agents"""
    SPEAK = "speak"
    GESTURE = "gesture"
    EMOTION = "emotion"
    MOVE = "move"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"


@dataclass
class VTuberAgent:
    """VTuber agent model"""
    id: str
    name: str
    character_type: str
    status: AgentStatus
    personality_traits: List[str]
    voice_model: Optional[str]
    avatar_model: Optional[str]
    stream_key: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_active: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["status"] = self.status.value
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        if self.last_active:
            result["last_active"] = self.last_active.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VTuberAgent":
        """Create VTuberAgent from dictionary"""
        return cls(
            id=data["id"],
            name=data["name"],
            character_type=data["character_type"],
            status=AgentStatus(data["status"]),
            personality_traits=data.get("personality_traits", []),
            voice_model=data.get("voice_model"),
            avatar_model=data.get("avatar_model"),
            stream_key=data.get("stream_key"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            last_active=datetime.fromisoformat(data["last_active"]) if data.get("last_active") else None
        )


@dataclass
class AgentSession:
    """Session model for agent activities"""
    id: str
    agent_id: str
    session_type: str  # "stream", "interaction", "performance"
    started_at: datetime
    ended_at: Optional[datetime]
    stream_url: Optional[str]
    viewer_count: int
    interaction_count: int
    commands_executed: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["started_at"] = self.started_at.isoformat()
        if self.ended_at:
            result["ended_at"] = self.ended_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSession":
        """Create AgentSession from dictionary"""
        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            session_type=data["session_type"],
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            stream_url=data.get("stream_url"),
            viewer_count=data.get("viewer_count", 0),
            interaction_count=data.get("interaction_count", 0),
            commands_executed=data.get("commands_executed", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class AgentCommand:
    """Command sent to an agent"""
    id: str
    agent_id: str
    command_type: CommandType
    payload: Dict[str, Any]
    priority: int
    status: str  # "pending", "executing", "completed", "failed"
    created_at: datetime
    executed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["command_type"] = self.command_type.value
        result["created_at"] = self.created_at.isoformat()
        if self.executed_at:
            result["executed_at"] = self.executed_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCommand":
        """Create AgentCommand from dictionary"""
        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            command_type=CommandType(data["command_type"]),
            payload=data.get("payload", {}),
            priority=data.get("priority", 5),
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]),
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None,
            result=data.get("result"),
            error=data.get("error")
        )


@dataclass
class StreamMetrics:
    """Metrics for streaming sessions"""
    id: str
    session_id: str
    timestamp: datetime
    viewer_count: int
    chat_messages: int
    donations_received: float
    engagement_rate: float
    sentiment_score: float
    fps: float
    bitrate: int
    dropped_frames: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamMetrics":
        """Create StreamMetrics from dictionary"""
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            viewer_count=data.get("viewer_count", 0),
            chat_messages=data.get("chat_messages", 0),
            donations_received=data.get("donations_received", 0.0),
            engagement_rate=data.get("engagement_rate", 0.0),
            sentiment_score=data.get("sentiment_score", 0.0),
            fps=data.get("fps", 30.0),
            bitrate=data.get("bitrate", 0),
            dropped_frames=data.get("dropped_frames", 0)
        )