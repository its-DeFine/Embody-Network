"""
Event definitions for the trading system.
Clean, simple event types that drive all system behavior.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """Types of events in the system"""
    PERIODIC = "periodic"          # Time-based recurring events
    API_CONDITION = "api_condition" # API monitoring triggered events
    DYNAMIC = "dynamic"            # Events scheduled by the system
    SYSTEM = "system"              # System events (startup, shutdown)


@dataclass
class Event:
    """
    Base event class. All events in the system are instances of this.
    
    Attributes:
        type: The type of event (periodic, api, dynamic, system)
        name: Unique name for this event
        data: Any data associated with the event
        timestamp: When the event was created
        handler: Name of the handler that should process this event
    """
    type: EventType
    name: str
    handler: str
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def __str__(self):
        return f"Event({self.type.value}, {self.name}, {self.handler})"


@dataclass
class ScheduledEvent:
    """
    An event that should fire at a specific time.
    Used by the event loop to track when to fire events.
    """
    event: Event
    next_run: datetime
    interval: Optional[int] = None  # For recurring events (seconds)
    
    def should_run(self, current_time: datetime) -> bool:
        """Check if this event should run now"""
        return current_time >= self.next_run
    
    def update_next_run(self):
        """Update next run time for periodic events"""
        if self.interval:
            self.next_run = datetime.now().timestamp() + self.interval


# Event factory functions for common event types

def create_periodic_event(name: str, handler: str, data: Dict[str, Any] = None) -> Event:
    """Create a periodic event"""
    return Event(
        type=EventType.PERIODIC,
        name=name,
        handler=handler,
        data=data or {}
    )


def create_api_event(name: str, handler: str, condition: str, data: Dict[str, Any]) -> Event:
    """Create an API condition event"""
    event_data = {
        "condition": condition,
        **data
    }
    return Event(
        type=EventType.API_CONDITION,
        name=name,
        handler=handler,
        data=event_data
    )


def create_dynamic_event(name: str, handler: str, data: Dict[str, Any] = None) -> Event:
    """Create a dynamic event (scheduled by the system)"""
    return Event(
        type=EventType.DYNAMIC,
        name=name,
        handler=handler,
        data=data or {}
    )


def create_system_event(name: str, data: Dict[str, Any] = None) -> Event:
    """Create a system event"""
    return Event(
        type=EventType.SYSTEM,
        name=name,
        handler="SystemHandler",
        data=data or {}
    )