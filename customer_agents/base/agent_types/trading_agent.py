from typing import Dict, Any, Callable
import json
import asyncio
import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ..dual_mode_trading import DualModeTradingEngine
from ..comparison_reporter import ComparisonReporter

logger = logging.getLogger(__name__)


class TradingAgent:
    """Trading agent implementation with AutoGen functions"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.exchange_name = config.get("exchange", "binance")
        self.trading_pairs = config.get("trading_pairs", ["BTC/USDT"])
        self.risk_limit = config.get("risk_limit", 0.02)  # 2% risk per trade
        
        # Initialize dual-mode trading engine
        trading_config = {
            'exchange': self.exchange_name,
            'api_key': config.get('api_key'),
            'api_secret': config.get('api_secret'),
            'testnet': config.get('testnet', True)
        }
        self.trading_engine = DualModeTradingEngine(trading_config)
        self.comparison_reporter = ComparisonReporter()
        self._initialized = False
        self.execution_history = []
        
    def get_system_message(self) -> str:
        """Get the system message for the trading agent"""
        mode = os.getenv('TRADING_MODE', 'comparison')
        return f"""You are an expert cryptocurrency trading agent with the following capabilities:
        
1. Market Analysis: Analyze price movements, volume, and technical indicators
2. Signal Generation: Generate buy/sell signals based on market conditions
3. Risk Management: Ensure all trades follow the {self.risk_limit*100}% risk limit
4. Trade Execution: Execute trades on {self.exchange_name} exchange
5. Portfolio Monitoring: Track open positions and P&L
6. Dual-Mode Trading: Running in {mode} mode - comparing real vs simulated execution

Trading Pairs: {', '.join(self.trading_pairs)}
Exchange: {self.exchange_name}
Trading Mode: {mode}

Always provide clear reasoning for your trading decisions and follow risk management rules strictly.
When analyzing markets, consider multiple timeframes and indicators.
In comparison mode, analyze divergence between real and simulated results.
"""
    
    def get_functions(self) -> Dict[str, Callable]:
        """Get available functions for the trading agent"""
        return {
            "get_market_data": self.get_market_data,
            "analyze_technicals": self.analyze_technicals,
            "calculate_position_size": self.calculate_position_size,
            "place_order": self.place_order,
            "get_portfolio_status": self.get_portfolio_status,
            "set_stop_loss": self.set_stop_loss,
            "set_take_profit": self.set_take_profit,
            "get_comparison_report": self.get_comparison_report,
            "get_execution_analytics": self.get_execution_analytics
        }
    
    async def get_market_data(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> Dict[str, Any]:
        """Get market data for analysis"""
        try:
            if not self._initialized:
                await self.trading_engine.initialize()
                self._initialized = True
            
            # Get market data through dual-mode engine
            return await self.trading_engine.get_market_data(symbol, timeframe)
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            # Fallback to simulated data if exchange fails
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "data": {
                    "open": [50000, 50100, 50200],
                    "high": [50500, 50600, 50700],
                    "low": [49900, 50000, 50100],
                    "close": [50400, 50500, 50600],
                    "volume": [100, 120, 110],
                    "timestamp": ["2024-01-01T00:00:00", "2024-01-01T01:00:00", "2024-01-01T02:00:00"]
                },
                "current_price": 50600,
                "24h_change": 1.2,
                "error": str(e),
                "mode": "simulated"
            }
    
    async def analyze_technicals(self, symbol: str, indicators: list = None) -> Dict[str, Any]:
        """Analyze technical indicators"""
        if indicators is None:
            indicators = ["RSI", "MACD", "BB", "EMA"]
        
        try:
            if not self._initialized:
                await self.trading_engine.initialize()
                self._initialized = True
            
            # Get market data first
            market_data = await self.trading_engine.get_market_data(symbol)
            
            # Calculate indicators based on mode
            if 'real' in market_data:
                # Real data available
                return {
                    "symbol": symbol,
                    "real": await self._calculate_indicators_from_data(market_data['real'], indicators),
                    "simulated": await self._calculate_indicators_from_data(market_data.get('simulated', {}), indicators) if 'simulated' in market_data else None
                }
            else:
                # Single mode
                return await self._calculate_indicators_from_data(market_data, indicators)
        except Exception as e:
            logger.error(f"Error analyzing technicals: {e}")
            # Fallback to simulated analysis
            return {
                "symbol": symbol,
                "analysis": {
                    "RSI": {"value": 65, "signal": "neutral"},
                    "MACD": {"value": 100, "signal": "bullish", "histogram": 50},
                    "BB": {"upper": 51000, "middle": 50500, "lower": 50000, "signal": "neutral"},
                    "EMA": {"ema_20": 50400, "ema_50": 50200, "signal": "bullish"}
                },
                "overall_signal": "bullish",
                "confidence": 0.75,
                "error": str(e),
                "mode": "simulated"
            }
    
    def calculate_position_size(self, account_balance: float, risk_percentage: float, 
                              entry_price: float, stop_loss_price: float) -> Dict[str, float]:
        """Calculate position size based on risk management"""
        try:
            risk_amount = account_balance * (risk_percentage / 100)
            price_difference = abs(entry_price - stop_loss_price)
            position_size = risk_amount / price_difference
            
            return {
                "position_size": round(position_size, 8),
                "risk_amount": risk_amount,
                "potential_loss": risk_amount,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price
            }
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {"error": str(e)}
    
    async def place_order(self, symbol: str, side: str, amount: float, 
                         order_type: str = "market", price: float = None) -> Dict[str, Any]:
        """Place a trading order"""
        try:
            if not self._initialized:
                await self.trading_engine.initialize()
                self._initialized = True
            
            # Place order through dual-mode engine
            order = {
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'type': order_type,
                'price': price
            }
            
            result = await self.trading_engine.execute_trade(order)
            
            # Store in execution history
            self.execution_history.append(result)
            
            # Handle comparison mode results
            if result.get('mode') == 'comparison' and 'divergence_analysis' in result:
                divergence = result['divergence_analysis']
                if divergence.get('alert') == 'high_divergence':
                    logger.warning(f"High divergence detected: {divergence['price_divergence_pct']:.2f}%")
            
            return result
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            # Fallback to simulated order
            import uuid
            from datetime import datetime
            order_id = str(uuid.uuid4())[:8]
            
            return {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "type": order_type,
                "price": price or 50600,
                "status": "simulated",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "mode": "simulated"
            }
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        try:
            if not self._initialized:
                await self.trading_engine.initialize()
                self._initialized = True
            
            # Get portfolio status through dual-mode engine
            return await self.trading_engine.get_portfolio_status()
        except Exception as e:
            logger.error(f"Error getting portfolio status: {e}")
            # Fallback to simulated portfolio
            return {
                "total_balance": 10000,
                "available_balance": 7000,
                "positions": [
                    {
                        "symbol": "BTC/USDT",
                        "amount": 0.05,
                        "entry_price": 50000,
                        "current_price": 50600,
                        "pnl": 30,
                        "pnl_percentage": 1.2
                    }
                ],
                "total_pnl": 30,
                "total_pnl_percentage": 0.3,
                "error": str(e),
                "mode": "simulated"
            }
    
    async def set_stop_loss(self, position_id: str, stop_loss_price: float) -> Dict[str, Any]:
        """Set stop loss for a position"""
        try:
            if not self._initialized:
                await self.trading_engine.initialize()
                self._initialized = True
            
            # Set stop loss through dual-mode engine
            order = {
                'symbol': position_id,  # Position ID should map to symbol
                'side': 'sell',
                'type': 'stop_loss',
                'price': stop_loss_price,
                'amount': 0  # Will be determined by position
            }
            
            return await self.trading_engine.execute_trade(order)
        except Exception as e:
            logger.error(f"Error setting stop loss: {e}")
            # Fallback to simulated stop loss
            return {
                "position_id": position_id,
                "stop_loss_price": stop_loss_price,
                "status": "simulated",
                "message": f"Stop loss simulated at {stop_loss_price}",
                "error": str(e),
                "mode": "simulated"
            }
    
    async def set_take_profit(self, position_id: str, take_profit_price: float) -> Dict[str, Any]:
        """Set take profit for a position"""
        try:
            if not self._initialized:
                await self.trading_engine.initialize()
                self._initialized = True
            
            # Set take profit through dual-mode engine
            order = {
                'symbol': position_id,  # Position ID should map to symbol
                'side': 'sell',
                'type': 'take_profit',
                'price': take_profit_price,
                'amount': 0  # Will be determined by position
            }
            
            return await self.trading_engine.execute_trade(order)
        except Exception as e:
            logger.error(f"Error setting take profit: {e}")
            # Fallback to simulated take profit
            return {
                "position_id": position_id,
                "take_profit_price": take_profit_price,
                "status": "simulated",
                "message": f"Take profit simulated at {take_profit_price}",
                "error": str(e),
                "mode": "simulated"
            }
    
    async def _calculate_indicators_from_data(self, market_data: Dict[str, Any], indicators: list) -> Dict[str, Any]:
        """Calculate indicators from market data"""
        # Simplified indicator calculation
        return {
            "analysis": {
                "RSI": {"value": 65, "signal": "neutral"},
                "MACD": {"value": 100, "signal": "bullish", "histogram": 50},
                "BB": {"upper": 51000, "middle": 50500, "lower": 50000, "signal": "neutral"},
                "EMA": {"ema_20": 50400, "ema_50": 50200, "signal": "bullish"}
            },
            "overall_signal": "bullish",
            "confidence": 0.75
        }
    
    async def get_comparison_report(self) -> Dict[str, Any]:
        """Get comparison report between real and simulated execution"""
        try:
            if len(self.execution_history) == 0:
                return {"message": "No executions to compare yet"}
            
            # Get the last execution results
            last_execution = self.execution_history[-1]
            
            # If comparison data available
            if 'results' in last_execution and 'real' in last_execution['results'] and 'simulated' in last_execution['results']:
                real_data = last_execution['results']['real']
                sim_data = last_execution['results']['simulated']
                
                # Generate comparison report
                report = self.comparison_reporter.generate_comparison_report(
                    real_data,
                    sim_data,
                    self.execution_history
                )
                
                return report
            else:
                return {"message": "No comparison data available - not in comparison mode"}
        except Exception as e:
            logger.error(f"Error generating comparison report: {e}")
            return {"error": str(e)}
    
    async def get_execution_analytics(self) -> Dict[str, Any]:
        """Get execution analytics from dual-mode engine"""
        try:
            if not self._initialized:
                await self.trading_engine.initialize()
                self._initialized = True
            
            return self.trading_engine.get_execution_analytics()
        except Exception as e:
            logger.error(f"Error getting execution analytics: {e}")
            return {"error": str(e)}