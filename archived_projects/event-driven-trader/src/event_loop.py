"""
Core event loop that drives the entire trading system.
This is the heart of the system - it manages all events and dispatches them to handlers.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import yaml

from .events import Event, ScheduledEvent, EventType, create_periodic_event
from .handlers import HandlerRegistry
from .monitor import APIMonitor


logger = logging.getLogger(__name__)


class EventLoop:
    """
    Main event loop that:
    1. Manages scheduled events (periodic and dynamic)
    2. Monitors APIs for conditions
    3. Dispatches events to appropriate handlers
    4. Handles dynamic event scheduling from handlers
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Core components
        self.handler_registry = HandlerRegistry(self.config)
        self.api_monitor = APIMonitor(self.config.get('events', {}).get('api_monitors', []))
        
        # Event management
        self.scheduled_events: List[ScheduledEvent] = []
        self.dynamic_events: List[ScheduledEvent] = []
        self.running = False
        
        # Initialize scheduled events from config
        self._init_periodic_events()
        
        # Performance tracking
        self.events_processed = 0
        self.last_event_time = datetime.now()
        
    def _init_periodic_events(self):
        """Initialize periodic events from configuration"""
        periodic_config = self.config.get('events', {}).get('periodic', [])
        
        for event_config in periodic_config:
            if not event_config.get('enabled', True):
                continue
                
            event = create_periodic_event(
                name=event_config['name'],
                handler=event_config['handler'],
                data={'config': event_config}
            )
            
            scheduled = ScheduledEvent(
                event=event,
                next_run=datetime.now(),  # Run immediately on start
                interval=event_config['interval']
            )
            
            self.scheduled_events.append(scheduled)
            logger.info(f"Registered periodic event: {event.name} (every {event_config['interval']}s)")
    
    async def run(self):
        """
        Main event loop. Runs continuously until stopped.
        This is the entry point for the entire system.
        """
        self.running = True
        loop_interval = self.config.get('system', {}).get('loop_interval', 1)
        
        logger.info("Event loop starting...")
        
        try:
            while self.running:
                current_time = datetime.now()
                
                # 1. Check scheduled events (periodic + dynamic)
                await self._process_scheduled_events(current_time)
                
                # 2. Check API monitors
                await self._process_api_monitors()
                
                # 3. Sleep for loop interval
                await asyncio.sleep(loop_interval)
                
        except KeyboardInterrupt:
            logger.info("Event loop interrupted by user")
        except Exception as e:
            logger.error(f"Event loop error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _process_scheduled_events(self, current_time: datetime):
        """Process all scheduled events that are ready to run"""
        # Combine periodic and dynamic events
        all_scheduled = self.scheduled_events + self.dynamic_events
        
        for scheduled in all_scheduled:
            if scheduled.should_run(current_time):
                # Dispatch the event
                await self._dispatch_event(scheduled.event)
                
                # Update or remove the scheduled event
                if scheduled.interval:
                    # Periodic event - reschedule
                    scheduled.update_next_run()
                else:
                    # One-time dynamic event - remove
                    if scheduled in self.dynamic_events:
                        self.dynamic_events.remove(scheduled)
    
    async def _process_api_monitors(self):
        """Check API monitors for triggered conditions"""
        triggered_events = await self.api_monitor.check_conditions()
        
        for event in triggered_events:
            await self._dispatch_event(event)
    
    async def _dispatch_event(self, event: Event):
        """
        Dispatch an event to its handler.
        This is where events get processed.
        """
        logger.debug(f"Dispatching event: {event}")
        
        try:
            # Get handler from registry
            handler = self.handler_registry.get_handler(event.handler)
            if not handler:
                logger.warning(f"No handler found for: {event.handler}")
                return
            
            # Process the event
            result = await handler.handle(event, self)
            
            # Track statistics
            self.events_processed += 1
            self.last_event_time = datetime.now()
            
            # Handle any dynamic events returned by the handler
            if result and 'schedule_events' in result:
                for dynamic_event_config in result['schedule_events']:
                    self.schedule_dynamic_event(
                        event=dynamic_event_config['event'],
                        delay_seconds=dynamic_event_config.get('delay', 0)
                    )
            
        except Exception as e:
            logger.error(f"Error handling event {event.name}: {e}")
    
    def schedule_dynamic_event(self, event: Event, delay_seconds: int = 0):
        """
        Schedule a dynamic event to run after a delay.
        This allows handlers to schedule follow-up events.
        """
        scheduled = ScheduledEvent(
            event=event,
            next_run=datetime.now() + timedelta(seconds=delay_seconds),
            interval=None  # Dynamic events are one-time
        )
        
        self.dynamic_events.append(scheduled)
        logger.info(f"Scheduled dynamic event: {event.name} in {delay_seconds}s")
    
    async def shutdown(self):
        """Clean shutdown of the event loop"""
        logger.info("Shutting down event loop...")
        self.running = False
        
        # Clean up API monitor
        await self.api_monitor.close()
        
        # Final statistics
        logger.info(f"Events processed: {self.events_processed}")
        logger.info(f"Last event: {self.last_event_time}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the event loop"""
        return {
            'running': self.running,
            'events_processed': self.events_processed,
            'scheduled_events': len(self.scheduled_events),
            'dynamic_events': len(self.dynamic_events),
            'last_event': self.last_event_time.isoformat()
        }