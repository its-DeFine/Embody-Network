"""
Enhanced simulation engine with realistic market dynamics
Runs alongside real trading for comparison and testing
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import logging
import random
from decimal import Decimal

logger = logging.getLogger(__name__)


class MarketSimulator:
    """Sophisticated market simulation with realistic dynamics"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Simulation parameters from config
        self.volatility_multiplier = float(config.get('volatility', 1.0))
        self.slippage_bps = float(config.get('slippage', 10))  # basis points
        self.fee_rate = float(config.get('fees', 0.001))  # 0.1%
        self.latency_ms = int(config.get('latency_ms', 50))
        self.liquidity_factor = float(config.get('liquidity_factor', 1.0))
        
        # Advanced features
        self.enable_black_swan = config.get('black_swan', True)
        self.enable_market_impact = config.get('market_impact', True)
        self.enable_order_book_sim = config.get('order_book_sim', True)
        
        # State tracking
        self.portfolio = {
            'balance': float(config.get('initial_balance', 10000)),
            'positions': {},
            'trades': [],
            'pnl_history': []
        }
        
        # Market state
        self.market_conditions = 'normal'  # normal, volatile, crash, rally
        self.liquidity_state = 1.0  # 0-1, affects slippage
        
    async def simulate_market_data(self, 
                                 real_price: float, 
                                 symbol: str, 
                                 timeframe: str = '1m') -> Dict[str, Any]:
        """Generate realistic market data based on real price"""
        
        # Add realistic noise and volatility
        volatility = self._calculate_volatility(symbol, timeframe)
        noise = np.random.normal(0, volatility * self.volatility_multiplier)
        
        # Simulate micro-structure
        spread = self._calculate_spread(real_price, symbol)
        
        # Apply market conditions
        if self.market_conditions == 'crash':
            noise -= abs(noise) * 2  # Bias downward
        elif self.market_conditions == 'rally':
            noise += abs(noise) * 0.5  # Bias upward
        
        simulated_price = real_price * (1 + noise)
        
        # Generate order book
        order_book = self._generate_order_book(simulated_price, spread, symbol)
        
        # Calculate additional metrics
        volume = self._simulate_volume(symbol)
        
        return {
            'symbol': symbol,
            'price': simulated_price,
            'bid': simulated_price - spread/2,
            'ask': simulated_price + spread/2,
            'spread': spread,
            'volume_24h': volume,
            'orderbook': order_book,
            'liquidity': self.liquidity_state,
            'market_conditions': self.market_conditions,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'simulation',
            'base_real_price': real_price,
            'divergence': abs(simulated_price - real_price) / real_price
        }
    
    async def simulate_order_execution(self, 
                                     order: Dict[str, Any], 
                                     market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate realistic order execution"""
        
        # Simulate network latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        symbol = order['symbol']
        side = order['side']
        amount = float(order['amount'])
        order_type = order.get('type', 'market')
        
        # Check for black swan events
        if self.enable_black_swan and random.random() < 0.001:  # 0.1% chance
            return self._simulate_black_swan_event(order)
        
        # Calculate execution price with slippage
        base_price = market_data['ask'] if side == 'buy' else market_data['bid']
        
        # Market impact
        market_impact = 0
        if self.enable_market_impact:
            market_impact = self._calculate_market_impact(amount, market_data)
        
        # Slippage calculation
        slippage = self._calculate_slippage(amount, market_data)
        
        # Final execution price
        if side == 'buy':
            execution_price = base_price * (1 + slippage + market_impact)
        else:
            execution_price = base_price * (1 - slippage - market_impact)
        
        # Calculate fees
        fee = amount * execution_price * self.fee_rate
        
        # Simulate partial fills for large orders
        filled_amount = amount
        if self.enable_order_book_sim:
            filled_amount = self._simulate_fill_amount(amount, market_data)
        
        # Update portfolio
        cost = filled_amount * execution_price + fee
        
        if side == 'buy':
            if self.portfolio['balance'] >= cost:
                self.portfolio['balance'] -= cost
                if symbol not in self.portfolio['positions']:
                    self.portfolio['positions'][symbol] = {
                        'amount': 0,
                        'avg_price': 0,
                        'realized_pnl': 0
                    }
                
                # Update position
                pos = self.portfolio['positions'][symbol]
                total_amount = pos['amount'] + filled_amount
                if total_amount > 0:
                    pos['avg_price'] = ((pos['amount'] * pos['avg_price']) + 
                                       (filled_amount * execution_price)) / total_amount
                pos['amount'] = total_amount
            else:
                return {
                    'order_id': order.get('order_id', f"sim_{datetime.utcnow().timestamp()}"),
                    'status': 'rejected',
                    'reason': 'insufficient_balance',
                    'required': cost,
                    'available': self.portfolio['balance']
                }
        else:  # sell
            if symbol in self.portfolio['positions']:
                pos = self.portfolio['positions'][symbol]
                if pos['amount'] >= filled_amount:
                    pos['amount'] -= filled_amount
                    self.portfolio['balance'] += (filled_amount * execution_price - fee)
                    
                    # Calculate realized PnL
                    realized_pnl = filled_amount * (execution_price - pos['avg_price'])
                    pos['realized_pnl'] += realized_pnl
                else:
                    return {
                        'order_id': order.get('order_id', f"sim_{datetime.utcnow().timestamp()}"),
                        'status': 'rejected',
                        'reason': 'insufficient_position',
                        'required': filled_amount,
                        'available': pos['amount']
                    }
            else:
                return {
                    'order_id': order.get('order_id', f"sim_{datetime.utcnow().timestamp()}"),
                    'status': 'rejected',
                    'reason': 'no_position'
                }
        
        # Record trade
        trade_record = {
            'order_id': order.get('order_id', f"sim_{datetime.utcnow().timestamp()}"),
            'symbol': symbol,
            'side': side,
            'amount': filled_amount,
            'requested_amount': amount,
            'price': execution_price,
            'fee': fee,
            'slippage': slippage,
            'market_impact': market_impact,
            'timestamp': datetime.utcnow().isoformat(),
            'portfolio_value': self.calculate_portfolio_value(market_data)
        }
        
        self.portfolio['trades'].append(trade_record)
        
        return {
            'order_id': trade_record['order_id'],
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'amount': filled_amount,
            'price': execution_price,
            'status': 'filled' if filled_amount == amount else 'partially_filled',
            'filled': filled_amount,
            'remaining': amount - filled_amount,
            'fee': fee,
            'slippage': slippage,
            'market_impact': market_impact,
            'timestamp': trade_record['timestamp'],
            'execution_quality': self._calculate_execution_quality(execution_price, base_price)
        }
    
    def _calculate_volatility(self, symbol: str, timeframe: str) -> float:
        """Calculate realistic volatility for symbol"""
        base_volatility = {
            'BTC/USDT': 0.02,
            'ETH/USDT': 0.025,
            'SOL/USDT': 0.035,
            'BNB/USDT': 0.02
        }.get(symbol, 0.03)
        
        # Adjust for timeframe
        timeframe_factor = {
            '1m': 0.1,
            '5m': 0.3,
            '15m': 0.5,
            '1h': 1.0,
            '4h': 2.0,
            '1d': 4.0
        }.get(timeframe, 1.0)
        
        return base_volatility * timeframe_factor
    
    def _calculate_spread(self, price: float, symbol: str) -> float:
        """Calculate realistic bid-ask spread"""
        # Base spread in basis points
        base_spread_bps = {
            'BTC/USDT': 1,    # 0.01%
            'ETH/USDT': 2,    # 0.02%
            'SOL/USDT': 5,    # 0.05%
            'BNB/USDT': 3     # 0.03%
        }.get(symbol, 5)
        
        # Adjust for market conditions
        if self.market_conditions == 'volatile':
            base_spread_bps *= 3
        elif self.market_conditions == 'crash':
            base_spread_bps *= 5
        
        # Adjust for liquidity
        base_spread_bps *= (2 - self.liquidity_state)
        
        return price * base_spread_bps / 10000
    
    def _generate_order_book(self, mid_price: float, spread: float, symbol: str) -> Dict[str, List]:
        """Generate realistic order book"""
        order_book = {'bids': [], 'asks': []}
        
        # Generate 10 levels each side
        for i in range(10):
            # Price levels follow power law distribution
            level_spread = spread * (1 + i * 0.5)
            
            # Volume decreases with distance from mid
            base_volume = random.uniform(0.1, 10) / (i + 1)
            
            bid_price = mid_price - level_spread
            ask_price = mid_price + level_spread
            
            order_book['bids'].append([bid_price, base_volume * self.liquidity_state])
            order_book['asks'].append([ask_price, base_volume * self.liquidity_state])
        
        return order_book
    
    def _simulate_volume(self, symbol: str) -> float:
        """Simulate realistic 24h volume"""
        base_volume = {
            'BTC/USDT': 25000000000,  # $25B
            'ETH/USDT': 15000000000,  # $15B
            'SOL/USDT': 2000000000,   # $2B
            'BNB/USDT': 1500000000    # $1.5B
        }.get(symbol, 1000000000)
        
        # Add random variation
        variation = random.uniform(0.5, 1.5)
        
        # Adjust for market conditions
        if self.market_conditions == 'volatile':
            variation *= 2
        elif self.market_conditions == 'crash':
            variation *= 3
        
        return base_volume * variation
    
    def _calculate_slippage(self, amount: float, market_data: Dict[str, Any]) -> float:
        """Calculate realistic slippage"""
        # Base slippage
        slippage = self.slippage_bps / 10000
        
        # Increase with order size
        if amount > 1:
            slippage *= (1 + np.log(amount))
        
        # Adjust for liquidity
        slippage *= (2 - self.liquidity_state)
        
        # Add randomness
        slippage *= random.uniform(0.8, 1.2)
        
        return slippage
    
    def _calculate_market_impact(self, amount: float, market_data: Dict[str, Any]) -> float:
        """Calculate market impact of large orders"""
        if amount < 0.1:
            return 0
        
        # Simple square-root model
        impact = 0.0001 * np.sqrt(amount)
        
        # Adjust for liquidity
        impact *= (2 - self.liquidity_state)
        
        return impact
    
    def _simulate_fill_amount(self, requested: float, market_data: Dict[str, Any]) -> float:
        """Simulate partial fills based on available liquidity"""
        if not self.enable_order_book_sim:
            return requested
        
        # Calculate available liquidity from order book
        available = sum(level[1] for level in market_data['orderbook']['asks'][:5])
        
        if requested <= available:
            return requested
        else:
            # Partial fill
            return available * random.uniform(0.8, 0.95)
    
    def _simulate_black_swan_event(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate rare market events"""
        event_type = random.choice(['flash_crash', 'exchange_outage', 'liquidity_crisis'])
        
        logger.warning(f"BLACK SWAN EVENT: {event_type}")
        
        if event_type == 'flash_crash':
            # Order executes at terrible price
            return {
                'order_id': order.get('order_id'),
                'status': 'filled',
                'price': order['price'] * 0.8,  # 20% worse
                'warning': 'Executed during flash crash',
                'event': event_type
            }
        elif event_type == 'exchange_outage':
            # Order fails
            return {
                'order_id': order.get('order_id'),
                'status': 'failed',
                'reason': 'exchange_unavailable',
                'event': event_type
            }
        else:  # liquidity_crisis
            # Only partial fill at bad price
            return {
                'order_id': order.get('order_id'),
                'status': 'partially_filled',
                'filled': order['amount'] * 0.1,
                'price': order['price'] * 1.05,
                'warning': 'Liquidity crisis - minimal fill',
                'event': event_type
            }
    
    def _calculate_execution_quality(self, exec_price: float, expected_price: float) -> float:
        """Rate execution quality 0-100"""
        slippage_pct = abs(exec_price - expected_price) / expected_price
        
        if slippage_pct < 0.0001:  # < 1 bps
            return 100
        elif slippage_pct < 0.001:  # < 10 bps
            return 90
        elif slippage_pct < 0.01:   # < 100 bps
            return 70
        else:
            return max(0, 50 - slippage_pct * 1000)
    
    def calculate_portfolio_value(self, market_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value"""
        total = self.portfolio['balance']
        
        for symbol, position in self.portfolio['positions'].items():
            if position['amount'] > 0:
                price = market_prices.get(symbol, {}).get('price', position['avg_price'])
                total += position['amount'] * price
        
        return total
    
    def get_portfolio_metrics(self, market_prices: Dict[str, float]) -> Dict[str, Any]:
        """Get comprehensive portfolio metrics"""
        current_value = self.calculate_portfolio_value(market_prices)
        initial_value = self.config.get('initial_balance', 10000)
        
        # Calculate returns
        total_return = (current_value - initial_value) / initial_value
        
        # Calculate trade statistics
        trades = self.portfolio['trades']
        if trades:
            win_count = sum(1 for t in trades if t.get('pnl', 0) > 0)
            loss_count = sum(1 for t in trades if t.get('pnl', 0) < 0)
            win_rate = win_count / len(trades) if trades else 0
            
            avg_slippage = np.mean([t['slippage'] for t in trades])
            total_fees = sum(t['fee'] for t in trades)
        else:
            win_rate = 0
            avg_slippage = 0
            total_fees = 0
        
        # Calculate Sharpe ratio (simplified)
        if len(self.portfolio['pnl_history']) > 1:
            returns = pd.Series(self.portfolio['pnl_history']).pct_change().dropna()
            sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe = 0
        
        return {
            'total_value': current_value,
            'cash_balance': self.portfolio['balance'],
            'positions_value': current_value - self.portfolio['balance'],
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'avg_slippage_bps': avg_slippage * 10000,
            'total_fees': total_fees,
            'sharpe_ratio': sharpe,
            'positions': self.portfolio['positions']
        }
    
    def update_market_conditions(self):
        """Randomly update market conditions for realism"""
        # 1% chance of condition change per update
        if random.random() < 0.01:
            old_condition = self.market_conditions
            self.market_conditions = random.choice(
                ['normal', 'normal', 'normal', 'volatile', 'crash', 'rally']
            )
            if old_condition != self.market_conditions:
                logger.info(f"Market conditions changed: {old_condition} -> {self.market_conditions}")
        
        # Update liquidity
        if self.market_conditions == 'normal':
            self.liquidity_state = min(1.0, self.liquidity_state + 0.01)
        elif self.market_conditions == 'crash':
            self.liquidity_state = max(0.2, self.liquidity_state - 0.1)
        else:
            self.liquidity_state = max(0.5, self.liquidity_state - 0.02)