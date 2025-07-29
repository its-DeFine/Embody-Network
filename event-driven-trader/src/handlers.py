"""
Event handlers - Process events and make trading decisions.
Each handler is responsible for one type of event.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from .events import Event, create_dynamic_event
from .trading import TradingEngine


logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """
    Base class for all event handlers.
    Handlers process events and return actions for the system to take.
    """
    
    def __init__(self, trading_engine: TradingEngine):
        self.trading_engine = trading_engine
        self.events_handled = 0
    
    @abstractmethod
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        """
        Handle an event and return any actions to take.
        
        Returns dict with optional keys:
        - schedule_events: List of events to schedule
        - trades: List of trades to execute
        """
        pass
    
    def log_handling(self, event: Event):
        """Log that we're handling an event"""
        self.events_handled += 1
        logger.info(f"{self.__class__.__name__} handling: {event.name}")


class MarketScanHandler(EventHandler):
    """
    Scans the market for trading opportunities.
    Runs periodically to find good entry points.
    """
    
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        # Get current positions
        positions = self.trading_engine.get_positions()
        max_positions = self.trading_engine.config.get('max_positions', 5)
        
        if len(positions) >= max_positions:
            logger.info("Max positions reached, skipping market scan")
            return None
        
        # Get token prices from event data (would come from API in real system)
        api_data = event.data.get('api_data', {})
        
        # Simple trading logic: Look for momentum
        trades_to_execute = []
        
        for token_config in self.trading_engine.config.get('tokens', []):
            symbol = token_config['symbol']
            
            # Skip if we already have a position
            if symbol in positions:
                continue
            
            # Get price data (simplified for demo)
            price_change = api_data.get(f"{symbol}_24h_change", 0)
            
            # Simple momentum strategy
            if price_change > 5:
                trades_to_execute.append({
                    'action': 'BUY',
                    'symbol': symbol,
                    'reason': f"Positive momentum: {price_change:.1f}%"
                })
            elif price_change < -5:
                trades_to_execute.append({
                    'action': 'SELL',
                    'symbol': symbol,
                    'reason': f"Negative momentum: {price_change:.1f}%"
                })
        
        # Execute trades
        for trade in trades_to_execute:
            self.trading_engine.execute_trade(
                symbol=trade['symbol'],
                action=trade['action'],
                reason=trade['reason']
            )
        
        return None


class PositionMonitorHandler(EventHandler):
    """
    Monitors open positions and manages exits.
    Checks stop loss and take profit conditions.
    """
    
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        positions = self.trading_engine.get_positions()
        if not positions:
            return None
        
        events_to_schedule = []
        
        for symbol, position in positions.items():
            # Check if we should close the position
            should_close, reason = self.trading_engine.check_exit_conditions(position)
            
            if should_close:
                self.trading_engine.close_position(symbol, reason)
                
                # Schedule a market scan after closing
                scan_event = create_dynamic_event(
                    name=f"market_scan_after_{symbol}_close",
                    handler="MarketScanHandler",
                    data={'trigger': f"Closed {symbol}"}
                )
                events_to_schedule.append({
                    'event': scan_event,
                    'delay': 5  # Scan again in 5 seconds
                })
        
        if events_to_schedule:
            return {'schedule_events': events_to_schedule}
        
        return None


class PriceSpikeHandler(EventHandler):
    """
    Handles sudden price spikes detected by API monitor.
    Implements momentum trading on spikes.
    """
    
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        # Extract data from the event
        api_data = event.data.get('api_data', {})
        condition = event.data.get('condition', {})
        
        # Determine which token spiked
        field = condition.get('field', '')
        if 'bitcoin' in field:
            symbol = 'BTC'
        elif 'ethereum' in field:
            symbol = 'ETH'
        else:
            symbol = 'ARB'
        
        # Check if we already have a position
        if symbol in self.trading_engine.get_positions():
            logger.info(f"Already have position in {symbol}, skipping spike trade")
            return None
        
        # Execute momentum trade
        self.trading_engine.execute_trade(
            symbol=symbol,
            action='BUY',
            reason=f"Price spike detected: {condition}"
        )
        
        # Schedule a check in 1 minute
        check_event = create_dynamic_event(
            name=f"check_{symbol}_spike_trade",
            handler="PositionMonitorHandler",
            data={'symbol': symbol, 'trigger': 'price_spike'}
        )
        
        return {
            'schedule_events': [{
                'event': check_event,
                'delay': 60
            }]
        }


class PriceCrashHandler(EventHandler):
    """
    Handles sudden price drops detected by API monitor.
    Can implement short selling or buying the dip.
    """
    
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        # Similar to spike handler but for drops
        api_data = event.data.get('api_data', {})
        condition = event.data.get('condition', {})
        
        # For now, we'll avoid catching falling knives
        logger.info(f"Price crash detected: {condition}")
        logger.info("Waiting for stabilization before entering")
        
        # Schedule a check to see if price stabilizes
        stabilization_event = create_dynamic_event(
            name="check_crash_stabilization",
            handler="MarketScanHandler",
            data={'trigger': 'price_crash', 'condition': condition}
        )
        
        return {
            'schedule_events': [{
                'event': stabilization_event,
                'delay': 300  # Check in 5 minutes
            }]
        }


class PerformanceHandler(EventHandler):
    """
    Tracks and reports trading performance.
    Runs periodically to log statistics.
    """
    
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        stats = self.trading_engine.get_performance_stats()
        
        logger.info("=== Performance Report ===")
        logger.info(f"Balance: ${stats['current_balance']:.2f}")
        logger.info(f"P&L: ${stats['total_pnl']:.2f} ({stats['pnl_percent']:.1f}%)")
        logger.info(f"Open Positions: {stats['open_positions']}")
        logger.info(f"Total Trades: {stats['total_trades']}")
        logger.info(f"Win Rate: {stats['win_rate']:.1f}%")
        logger.info("========================")
        
        return None


class HandlerRegistry:
    """
    Registry of all available handlers.
    Maps handler names to handler instances.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # Create trading engine
        self.trading_engine = TradingEngine()
        
        # Register traditional handlers
        self.handlers: Dict[str, EventHandler] = {
            'MarketScanHandler': MarketScanHandler(self.trading_engine),
            'PositionMonitorHandler': PositionMonitorHandler(self.trading_engine),
            'PriceSpikeHandler': PriceSpikeHandler(self.trading_engine),
            'PriceCrashHandler': PriceCrashHandler(self.trading_engine),
            'PerformanceHandler': PerformanceHandler(self.trading_engine),
        }
        
        # Register AI handlers if enabled
        if config and config.get('system', {}).get('enable_ai', False):
            try:
                from .autogen_teams import AutoGenTeamManager
                from .ai_handlers import (
                    AIMarketAnalysisHandler,
                    AISignalHandler,
                    AIRiskMonitorHandler,
                    AIPerformanceHandler
                )
                
                # Create team manager
                ai_config = config.get('ai_config', {})
                self.team_manager = AutoGenTeamManager(ai_config)
                
                # Register AI handlers
                self.handlers.update({
                    'AIMarketAnalysisHandler': AIMarketAnalysisHandler(self.trading_engine, self.team_manager),
                    'AISignalHandler': AISignalHandler(self.trading_engine, self.team_manager),
                    'AIRiskMonitorHandler': AIRiskMonitorHandler(self.trading_engine, self.team_manager),
                    'AIPerformanceHandler': AIPerformanceHandler(self.trading_engine, self.team_manager),
                })
                
                logger.info("AI handlers registered successfully")
            except Exception as e:
                logger.warning(f"Could not register AI handlers: {e}")
        
        logger.info(f"Registered {len(self.handlers)} handlers")
    
    def get_handler(self, handler_name: str) -> Optional[EventHandler]:
        """Get a handler by name"""
        return self.handlers.get(handler_name)
    
    def get_trading_engine(self) -> TradingEngine:
        """Get the trading engine instance"""
        return self.trading_engine