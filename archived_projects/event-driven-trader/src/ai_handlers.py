"""
AI-powered event handlers using AutoGen teams.
These handlers integrate AI decision-making into the event-driven system.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .handlers import EventHandler
from .events import Event, create_dynamic_event
from .autogen_teams import AutoGenTeamManager
from .trading import TradingEngine


logger = logging.getLogger(__name__)


class AIMarketAnalysisHandler(EventHandler):
    """
    Triggers AutoGen market analysis team to evaluate trading opportunities.
    Runs periodically to scan markets with AI intelligence.
    """
    
    def __init__(self, trading_engine: TradingEngine, team_manager: AutoGenTeamManager):
        super().__init__(trading_engine)
        self.team_manager = team_manager
        self.min_confidence = 70  # Minimum AI confidence to act
        
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        # Get configured tokens to analyze
        tokens = self.trading_engine.config.get('tokens', [])
        events_to_schedule = []
        
        for token_config in tokens:
            symbol = token_config['symbol']
            
            # Skip if we already have a position
            if symbol in self.trading_engine.get_positions():
                continue
                
            # Prepare market data for AI team
            market_data = {
                'symbol': symbol,
                'price': self.trading_engine._get_current_price(symbol),
                'change_24h': event.data.get(f'{symbol}_change_24h', 0),
                'volume': event.data.get(f'{symbol}_volume', 1000000),
                'market_cap': event.data.get(f'{symbol}_market_cap', 10000000),
                'fear_greed': event.data.get('fear_greed', 50)
            }
            
            # Get AI team analysis
            logger.info(f"Requesting AI analysis for {symbol}...")
            analysis = await self.team_manager.get_market_analysis(symbol, market_data)
            
            # If AI team recommends action with high confidence
            if analysis['confidence'] >= self.min_confidence and analysis['action'] != 'HOLD':
                # Schedule signal generation event
                signal_event = create_dynamic_event(
                    name=f"ai_signal_{symbol}",
                    handler="AISignalHandler",
                    data={
                        'symbol': symbol,
                        'analysis': analysis,
                        'market_data': market_data
                    }
                )
                
                events_to_schedule.append({
                    'event': signal_event,
                    'delay': 1  # Execute immediately
                })
                
                logger.info(f"AI Team recommends {analysis['action']} for {symbol} (confidence: {analysis['confidence']}%)")
        
        if events_to_schedule:
            return {'schedule_events': events_to_schedule}
            
        return None


class AISignalHandler(EventHandler):
    """
    Processes AI team signals and executes trades.
    Gets execution parameters from the execution team.
    """
    
    def __init__(self, trading_engine: TradingEngine, team_manager: AutoGenTeamManager):
        super().__init__(trading_engine)
        self.team_manager = team_manager
        
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        # Extract data from event
        symbol = event.data['symbol']
        analysis = event.data['analysis']
        market_data = event.data['market_data']
        
        # Get execution plan from AI execution team
        logger.info(f"Requesting execution plan for {symbol} {analysis['action']}...")
        
        execution_context = {
            'price': market_data['price'],
            'balance': self.trading_engine.balance,
            'max_position_pct': self.trading_engine.position_size_percent
        }
        
        execution_plan = await self.team_manager.get_execution_plan(
            symbol, analysis, execution_context
        )
        
        # Execute the trade with AI parameters
        success = self._execute_ai_trade(symbol, analysis, execution_plan)
        
        if success:
            # Schedule AI monitoring
            monitor_event = create_dynamic_event(
                name=f"ai_monitor_{symbol}",
                handler="AIRiskMonitorHandler",
                data={
                    'symbol': symbol,
                    'entry_analysis': analysis,
                    'execution': execution_plan
                }
            )
            
            return {
                'schedule_events': [{
                    'event': monitor_event,
                    'delay': 30  # Check in 30 seconds
                }]
            }
            
        return None
        
    def _execute_ai_trade(self, symbol: str, analysis: Dict, execution: Dict) -> bool:
        """Execute trade based on AI recommendations."""
        # Calculate position size
        position_size_pct = execution.get('position_size_pct', 20)
        position_size = self.trading_engine.balance * (position_size_pct / 100)
        
        # Override trading engine parameters with AI recommendations
        if execution.get('stop_loss'):
            # Convert to percentage if needed
            stop_pct = abs(1 - execution['stop_loss']) * 100
        else:
            stop_pct = self.trading_engine.stop_loss_percent
            
        if execution.get('take_profit'):
            # Convert to percentage if needed
            target_pct = abs(execution['take_profit'] - 1) * 100
        else:
            target_pct = self.trading_engine.take_profit_percent
            
        # Store original parameters
        orig_stop = self.trading_engine.stop_loss_percent
        orig_target = self.trading_engine.take_profit_percent
        orig_size = self.trading_engine.position_size_percent
        
        # Temporarily override with AI parameters
        self.trading_engine.stop_loss_percent = stop_pct
        self.trading_engine.take_profit_percent = target_pct
        self.trading_engine.position_size_percent = position_size_pct
        
        # Execute trade
        reason = f"AI Team: {analysis['action']} (confidence: {analysis['confidence']}%)"
        success = self.trading_engine.execute_trade(symbol, analysis['action'], reason)
        
        # Restore original parameters
        self.trading_engine.stop_loss_percent = orig_stop
        self.trading_engine.take_profit_percent = orig_target
        self.trading_engine.position_size_percent = orig_size
        
        if success:
            logger.info(f"AI trade executed: {symbol} {analysis['action']}")
            logger.info(f"AI parameters: size={position_size_pct}%, stop={stop_pct}%, target={target_pct}%")
            
        return success


class AIRiskMonitorHandler(EventHandler):
    """
    AI-powered position monitoring.
    Teams continuously evaluate positions and suggest adjustments.
    """
    
    def __init__(self, trading_engine: TradingEngine, team_manager: AutoGenTeamManager):
        super().__init__(trading_engine)
        self.team_manager = team_manager
        
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        symbol = event.data['symbol']
        position = self.trading_engine.get_positions().get(symbol)
        
        if not position:
            logger.info(f"Position {symbol} already closed")
            return None
            
        # Get current market data
        current_price = self.trading_engine._get_current_price(symbol)
        pnl_percent = position.get_pnl_percent(current_price)
        
        # Prepare data for AI team
        monitor_data = {
            'symbol': symbol,
            'entry_price': position.entry_price,
            'current_price': current_price,
            'pnl_percent': pnl_percent,
            'hold_time_hours': position.get_hold_time_minutes() / 60,
            'original_analysis': event.data.get('entry_analysis', {})
        }
        
        # Get AI team assessment
        logger.info(f"AI team monitoring {symbol} position (P&L: {pnl_percent:.1f}%)...")
        
        # Use market analysis team for position monitoring
        reassessment = await self.team_manager.get_market_analysis(
            f"{symbol} position review", monitor_data
        )
        
        # AI team suggests closing?
        if reassessment['action'] == 'SELL' and reassessment['confidence'] >= 80:
            self.trading_engine.close_position(
                symbol, 
                f"AI team recommendation: {reassessment['reasoning'][:100]}"
            )
            logger.info(f"AI team closed {symbol} position")
            return None
            
        # Continue monitoring
        return {
            'schedule_events': [{
                'event': create_dynamic_event(
                    name=f"ai_monitor_{symbol}",
                    handler="AIRiskMonitorHandler",
                    data=event.data
                ),
                'delay': 60  # Check again in 1 minute
            }]
        }


class AIPerformanceHandler(EventHandler):
    """
    AI team reviews overall trading performance and suggests improvements.
    """
    
    def __init__(self, trading_engine: TradingEngine, team_manager: AutoGenTeamManager):
        super().__init__(trading_engine)
        self.team_manager = team_manager
        
    async def handle(self, event: Event, event_loop) -> Optional[Dict[str, Any]]:
        self.log_handling(event)
        
        stats = self.trading_engine.get_performance_stats()
        
        logger.info("=== AI Performance Review ===")
        logger.info(f"Balance: ${stats['current_balance']:.2f}")
        logger.info(f"P&L: ${stats['total_pnl']:.2f} ({stats['pnl_percent']:.1f}%)")
        logger.info(f"Win Rate: {stats['win_rate']:.1f}%")
        logger.info(f"AI Team Decisions: {self.team_manager.teams['market_analysis'].chat_history[-5:]}")
        logger.info("============================")
        
        # Could add AI team performance review here
        
        return None