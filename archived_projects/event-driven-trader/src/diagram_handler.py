"""
Event handler for automatic diagram updates.
Integrates diagram generation into the event-driven system.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .handlers import EventHandler
from .events import Event
from .diagram_generator import DiagramGenerator


logger = logging.getLogger(__name__)


class DiagramUpdateHandler(EventHandler):
    """
    Automatically updates architecture diagrams when code changes.
    Can be triggered periodically or on-demand.
    """
    
    def __init__(self, trading_engine=None):
        # Don't need trading engine for diagram updates
        self.generator = DiagramGenerator()
        self.events_handled = 0
        
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        """Check for code changes and update diagram if needed."""
        self.events_handled += 1
        
        logger.info("Checking if architecture diagram needs update...")
        
        # Generate diagram if changes detected
        updated = self.generator.generate_diagram()
        
        if updated:
            logger.info("✅ Architecture diagram updated automatically")
            
            # Could trigger additional events here
            # For example, notify that documentation was updated
            
        else:
            logger.debug("Diagram is up to date")
            
        return None