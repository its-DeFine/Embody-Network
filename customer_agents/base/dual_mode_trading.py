"""
Dual-mode trading engine that runs real and simulated trading in parallel
Enables comparison, hybrid execution, and shadow mode operations
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

from .exchange_connector import ExchangeConnector
from .simulation_engine import MarketSimulator

logger = logging.getLogger(__name__)


class DualModeTradingEngine:
    """Trading engine that supports multiple execution modes"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = os.getenv('TRADING_MODE', 'comparison')
        
        # Initialize components based on mode
        self.real_engine = None
        self.sim_engine = None
        
        # Mode configuration
        self.comparison_mode = os.getenv('COMPARISON_MODE', 'true').lower() == 'true'
        self.sync_prices = os.getenv('COMPARISON_SYNC_PRICES', 'true').lower() == 'true'
        
        # Hybrid mode weights
        self.real_weight = float(os.getenv('HYBRID_REAL_WEIGHT', '0.1'))
        self.sim_weight = float(os.getenv('HYBRID_SIM_WEIGHT', '0.9'))
        
        # Tracking
        self.execution_history = []
        self.divergence_history = []
        self.comparison_metrics = {
            'total_trades': {'real': 0, 'simulated': 0},
            'profitable_trades': {'real': 0, 'simulated': 0},
            'total_pnl': {'real': 0.0, 'simulated': 0.0},
            'total_fees': {'real': 0.0, 'simulated': 0.0},
            'avg_slippage': {'real': 0.0, 'simulated': 0.0}
        }
        
    async def initialize(self):
        """Initialize trading engines based on mode"""
        if self.mode in ['real', 'hybrid', 'comparison', 'shadow']:
            # Initialize real trading engine
            exchange_config = {
                'api_key': os.getenv(f'{self.config["exchange"].upper()}_API_KEY'),
                'api_secret': os.getenv(f'{self.config["exchange"].upper()}_API_SECRET'),
                'testnet': os.getenv('ENABLE_TESTNET', 'true').lower() == 'true'
            }
            self.real_engine = ExchangeConnector(self.config['exchange'], exchange_config)
            await self.real_engine.initialize()
            logger.info("Real trading engine initialized")
        
        if self.mode in ['simulated', 'hybrid', 'comparison', 'shadow']:
            # Initialize simulation engine
            sim_config = {
                'initial_balance': float(os.getenv('SIMULATION_INITIAL_BALANCE', '10000')),
                'volatility': float(os.getenv('SIMULATION_VOLATILITY', '1.0')),
                'slippage': float(os.getenv('SIMULATION_SLIPPAGE_BPS', '10')),
                'fees': float(os.getenv('SIMULATION_FEES', '0.001')),
                'latency_ms': int(os.getenv('SIMULATION_LATENCY_MS', '50')),
                'liquidity_factor': float(os.getenv('SIMULATION_LIQUIDITY_FACTOR', '1.0')),
                'black_swan': os.getenv('SIMULATION_BLACK_SWAN', 'true').lower() == 'true',
                'market_impact': os.getenv('SIMULATION_MARKET_IMPACT', 'true').lower() == 'true',
                'order_book_sim': os.getenv('SIMULATION_ORDER_BOOK_SIM', 'true').lower() == 'true'
            }
            self.sim_engine = MarketSimulator(sim_config)
            logger.info("Simulation engine initialized")
    
    async def get_market_data(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get market data with mode-appropriate source"""
        results = {}
        
        # Get real market data if available
        if self.real_engine and self.mode != 'simulated':
            try:
                real_data = await self.real_engine.get_market_data(symbol, timeframe, 100)
                results['real'] = real_data
                
                # Use real price for simulation if sync enabled
                if self.sync_prices and self.sim_engine:
                    sim_data = await self.sim_engine.simulate_market_data(
                        real_data['current_price'], 
                        symbol, 
                        timeframe
                    )
                    results['simulated'] = sim_data
            except Exception as e:
                logger.error(f"Error getting real market data: {e}")
                results['real'] = {'error': str(e), 'mode': 'failed'}
        
        # Get simulated data if needed and not synced
        if self.sim_engine and not (self.sync_prices and 'real' in results):
            # Use a base price if no real data
            base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 100
            sim_data = await self.sim_engine.simulate_market_data(base_price, symbol, timeframe)
            results['simulated'] = sim_data
        
        # Return based on mode
        if self.mode == 'real':
            return results.get('real', {})
        elif self.mode == 'simulated':
            return results.get('simulated', {})
        else:
            # Return both for comparison/hybrid/shadow modes
            return self._merge_market_data(results)
    
    async def execute_trade(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade based on mode"""
        results = {}
        
        # Validate order
        if not self._validate_order(order):
            return {'error': 'Invalid order parameters'}
        
        # Execute based on mode
        if self.mode == 'real':
            results['real'] = await self._execute_real_trade(order)
        
        elif self.mode == 'simulated':
            results['simulated'] = await self._execute_simulated_trade(order)
        
        elif self.mode == 'hybrid':
            # Split order between real and simulated
            real_order = order.copy()
            sim_order = order.copy()
            
            real_order['amount'] = order['amount'] * self.real_weight
            sim_order['amount'] = order['amount'] * self.sim_weight
            
            # Execute both
            if real_order['amount'] > 0:
                results['real'] = await self._execute_real_trade(real_order)
            if sim_order['amount'] > 0:
                results['simulated'] = await self._execute_simulated_trade(sim_order)
        
        elif self.mode in ['comparison', 'shadow']:
            # Execute both with full amounts
            tasks = []
            
            if self.real_engine and self.mode == 'comparison':
                tasks.append(self._execute_real_trade(order))
            
            if self.sim_engine:
                tasks.append(self._execute_simulated_trade(order))
            
            # Run in parallel
            if tasks:
                task_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                if len(task_results) > 0 and not isinstance(task_results[0], Exception):
                    results['real'] = task_results[0] if self.mode == 'comparison' else None
                
                if len(task_results) > 1 or (len(task_results) == 1 and self.mode == 'shadow'):
                    idx = 1 if self.mode == 'comparison' else 0
                    if not isinstance(task_results[idx], Exception):
                        results['simulated'] = task_results[idx]
        
        # Track execution
        self._track_execution(order, results)
        
        # Analyze divergence if both executed
        if 'real' in results and 'simulated' in results:
            divergence = self._analyze_divergence(results['real'], results['simulated'])
            results['divergence_analysis'] = divergence
        
        return self._format_execution_result(results)
    
    async def _execute_real_trade(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute real trade"""
        try:
            if not self.real_engine:
                return {'error': 'Real engine not initialized', 'mode': 'unavailable'}
            
            result = await self.real_engine.place_order(
                symbol=order['symbol'],
                side=order['side'],
                amount=order['amount'],
                order_type=order.get('type', 'market'),
                price=order.get('price')
            )
            
            result['execution_mode'] = 'real'
            result['execution_time'] = datetime.utcnow().isoformat()
            
            # Update metrics
            self.comparison_metrics['total_trades']['real'] += 1
            if 'fee' in result:
                self.comparison_metrics['total_fees']['real'] += result['fee']
            
            return result
            
        except Exception as e:
            logger.error(f"Real trade execution error: {e}")
            return {'error': str(e), 'mode': 'real', 'status': 'failed'}
    
    async def _execute_simulated_trade(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute simulated trade"""
        try:
            if not self.sim_engine:
                return {'error': 'Simulation engine not initialized', 'mode': 'unavailable'}
            
            # Get current market data for simulation
            market_data = await self.get_market_data(order['symbol'])
            
            # Execute in simulation
            result = await self.sim_engine.simulate_order_execution(order, market_data)
            
            result['execution_mode'] = 'simulated'
            result['execution_time'] = datetime.utcnow().isoformat()
            
            # Update metrics
            self.comparison_metrics['total_trades']['simulated'] += 1
            if 'fee' in result:
                self.comparison_metrics['total_fees']['simulated'] += result['fee']
            if 'slippage' in result:
                # Update average slippage
                total_trades = self.comparison_metrics['total_trades']['simulated']
                current_avg = self.comparison_metrics['avg_slippage']['simulated']
                new_avg = (current_avg * (total_trades - 1) + result['slippage']) / total_trades
                self.comparison_metrics['avg_slippage']['simulated'] = new_avg
            
            return result
            
        except Exception as e:
            logger.error(f"Simulated trade execution error: {e}")
            return {'error': str(e), 'mode': 'simulated', 'status': 'failed'}
    
    def _validate_order(self, order: Dict[str, Any]) -> bool:
        """Validate order parameters"""
        required = ['symbol', 'side', 'amount']
        return all(field in order for field in required)
    
    def _track_execution(self, order: Dict[str, Any], results: Dict[str, Any]):
        """Track execution history"""
        record = {
            'timestamp': datetime.utcnow().isoformat(),
            'order': order,
            'results': results,
            'mode': self.mode
        }
        
        self.execution_history.append(record)
        
        # Keep only last 1000 executions
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def _analyze_divergence(self, real_result: Dict[str, Any], sim_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze divergence between real and simulated execution"""
        divergence = {
            'timestamp': datetime.utcnow().isoformat(),
            'price_divergence': 0.0,
            'fee_divergence': 0.0,
            'slippage_divergence': 0.0,
            'execution_quality_diff': 0.0
        }
        
        # Price divergence
        if 'price' in real_result and 'price' in sim_result:
            real_price = real_result['price']
            sim_price = sim_result['price']
            divergence['price_divergence'] = abs(real_price - sim_price) / real_price
            divergence['price_divergence_pct'] = divergence['price_divergence'] * 100
        
        # Fee divergence
        if 'fee' in real_result and 'fee' in sim_result:
            divergence['fee_divergence'] = abs(real_result['fee'] - sim_result['fee'])
        
        # Slippage comparison
        if 'slippage' in sim_result:
            real_slippage = real_result.get('slippage', 0)
            divergence['slippage_divergence'] = abs(real_slippage - sim_result['slippage'])
        
        # Execution quality
        if 'execution_quality' in sim_result:
            real_quality = real_result.get('execution_quality', 100)
            divergence['execution_quality_diff'] = real_quality - sim_result['execution_quality']
        
        # Track divergence history
        self.divergence_history.append(divergence)
        if len(self.divergence_history) > 1000:
            self.divergence_history = self.divergence_history[-1000:]
        
        # Alert if divergence exceeds threshold
        alert_threshold = float(os.getenv('COMPARISON_ALERT_THRESHOLD', '0.05'))
        if divergence['price_divergence'] > alert_threshold:
            logger.warning(f"High price divergence detected: {divergence['price_divergence_pct']:.2f}%")
            divergence['alert'] = 'high_divergence'
        
        return divergence
    
    def _merge_market_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Merge market data from multiple sources"""
        merged = {
            'mode': self.mode,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if 'real' in results:
            merged['real'] = results['real']
        
        if 'simulated' in results:
            merged['simulated'] = results['simulated']
        
        # Add comparison if both available
        if 'real' in results and 'simulated' in results:
            real_price = results['real'].get('current_price', 0)
            sim_price = results['simulated'].get('price', 0)
            
            if real_price and sim_price:
                merged['price_divergence'] = abs(real_price - sim_price) / real_price
                merged['price_divergence_pct'] = merged['price_divergence'] * 100
        
        return merged
    
    def _format_execution_result(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Format execution results based on mode"""
        formatted = {
            'mode': self.mode,
            'timestamp': datetime.utcnow().isoformat(),
            'results': results
        }
        
        # Add mode-specific formatting
        if self.mode == 'comparison' and 'real' in results and 'simulated' in results:
            # Add comparison summary
            formatted['comparison'] = {
                'real_status': results['real'].get('status', 'unknown'),
                'sim_status': results['simulated'].get('status', 'unknown'),
                'price_match': abs(results['real'].get('price', 0) - 
                                 results['simulated'].get('price', 0)) < 0.001,
                'execution_modes': ['real', 'simulated']
            }
        
        elif self.mode == 'hybrid':
            # Show weight distribution
            formatted['weights'] = {
                'real': self.real_weight,
                'simulated': self.sim_weight
            }
        
        elif self.mode == 'shadow':
            # Emphasize this was shadow execution
            formatted['shadow_mode'] = True
            formatted['note'] = 'Real execution was not performed - shadow mode only'
        
        return formatted
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio status from both engines"""
        status = {
            'mode': self.mode,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Get real portfolio if available
        if self.real_engine and self.mode in ['real', 'hybrid', 'comparison']:
            try:
                status['real'] = await self.real_engine.get_portfolio_status()
            except Exception as e:
                status['real'] = {'error': str(e)}
        
        # Get simulated portfolio
        if self.sim_engine and self.mode in ['simulated', 'hybrid', 'comparison', 'shadow']:
            # Get current prices for portfolio valuation
            prices = {}
            if hasattr(self.sim_engine, 'portfolio') and self.sim_engine.portfolio['positions']:
                for symbol in self.sim_engine.portfolio['positions']:
                    market_data = await self.get_market_data(symbol)
                    prices[symbol] = market_data
            
            status['simulated'] = self.sim_engine.get_portfolio_metrics(prices)
        
        # Add comparison metrics
        if self.mode in ['comparison', 'shadow']:
            status['comparison_metrics'] = self.comparison_metrics
            status['recent_divergence'] = self.divergence_history[-10:] if self.divergence_history else []
        
        return status
    
    def get_execution_analytics(self) -> Dict[str, Any]:
        """Get detailed execution analytics"""
        analytics = {
            'mode': self.mode,
            'total_executions': len(self.execution_history),
            'comparison_metrics': self.comparison_metrics
        }
        
        if self.divergence_history:
            # Calculate average divergence
            avg_divergence = sum(d['price_divergence'] for d in self.divergence_history) / len(self.divergence_history)
            max_divergence = max(d['price_divergence'] for d in self.divergence_history)
            
            analytics['divergence_stats'] = {
                'average_price_divergence': avg_divergence,
                'max_price_divergence': max_divergence,
                'total_comparisons': len(self.divergence_history)
            }
        
        # Mode-specific analytics
        if self.mode == 'hybrid':
            # Calculate weighted performance
            if self.comparison_metrics['total_trades']['real'] > 0:
                real_pnl = self.comparison_metrics['total_pnl']['real']
                sim_pnl = self.comparison_metrics['total_pnl']['simulated']
                weighted_pnl = (real_pnl * self.real_weight) + (sim_pnl * self.sim_weight)
                analytics['hybrid_weighted_pnl'] = weighted_pnl
        
        return analytics
    
    async def update_market_conditions(self):
        """Update market conditions in simulation"""
        if self.sim_engine:
            self.sim_engine.update_market_conditions()
    
    async def close(self):
        """Cleanup resources"""
        if self.real_engine:
            await self.real_engine.close()
        
        # Save execution history if needed
        if self.execution_history:
            filename = f"execution_history_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(self.execution_history, f, indent=2)
            logger.info(f"Execution history saved to {filename}")