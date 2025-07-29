"""
Real exchange connector for trading operations
Supports multiple exchanges via ccxt library
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from decimal import Decimal

logger = logging.getLogger(__name__)


class ExchangeConnector:
    """Real exchange connector using ccxt"""
    
    SUPPORTED_EXCHANGES = {
        'binance': ccxt.binance,
        'coinbase': ccxt.coinbase,
        'kraken': ccxt.kraken,
        'kucoin': ccxt.kucoin,
        'bybit': ccxt.bybit,
        'okx': ccxt.okx
    }
    
    def __init__(self, exchange_name: str, config: Dict[str, Any]):
        """Initialize exchange connection"""
        self.exchange_name = exchange_name.lower()
        self.config = config
        
        # Get exchange class
        exchange_class = self.SUPPORTED_EXCHANGES.get(self.exchange_name)
        if not exchange_class:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        
        # Initialize exchange with credentials
        exchange_config = {
            'apiKey': config.get('api_key'),
            'secret': config.get('api_secret'),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'  # or 'future', 'margin'
            }
        }
        
        # Add exchange-specific options
        if self.exchange_name == 'binance':
            exchange_config['options']['recvWindow'] = 60000
        
        self.exchange = exchange_class(exchange_config)
        self._initialized = False
        
    async def initialize(self):
        """Load markets and validate connection"""
        try:
            await self.exchange.load_markets()
            self._initialized = True
            logger.info(f"Successfully connected to {self.exchange_name}")
            
            # Test authentication
            if self.config.get('api_key'):
                balance = await self.exchange.fetch_balance()
                logger.info(f"Account connected. Total balance: {balance['total']}")
                
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise
    
    async def get_market_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Dict[str, Any]:
        """Fetch real market data from exchange"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Fetch OHLCV data
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Convert to structured format
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Fetch current ticker
            ticker = await self.exchange.fetch_ticker(symbol)
            
            # Fetch order book
            orderbook = await self.exchange.fetch_order_book(symbol, limit=10)
            
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "data": {
                    "timestamps": df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist(),
                    "open": df['open'].tolist(),
                    "high": df['high'].tolist(),
                    "low": df['low'].tolist(),
                    "close": df['close'].tolist(),
                    "volume": df['volume'].tolist()
                },
                "current_price": ticker['last'],
                "bid": ticker['bid'],
                "ask": ticker['ask'],
                "24h_change": ticker['percentage'],
                "24h_volume": ticker['quoteVolume'],
                "orderbook": {
                    "bids": [[price, amount] for price, amount in orderbook['bids'][:5]],
                    "asks": [[price, amount] for price, amount in orderbook['asks'][:5]]
                }
            }
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            raise
    
    async def calculate_indicators(self, symbol: str, indicators: List[str] = None) -> Dict[str, Any]:
        """Calculate real technical indicators"""
        if not indicators:
            indicators = ["RSI", "MACD", "BB", "EMA", "SMA", "Volume"]
            
        # Fetch data for calculations
        ohlcv = await self.exchange.fetch_ohlcv(symbol, '1h', limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        analysis = {"symbol": symbol, "analysis": {}}
        
        # RSI Calculation
        if "RSI" in indicators:
            rsi = self._calculate_rsi(df['close'])
            rsi_value = rsi.iloc[-1]
            signal = "oversold" if rsi_value < 30 else "overbought" if rsi_value > 70 else "neutral"
            analysis["analysis"]["RSI"] = {
                "value": round(float(rsi_value), 2),
                "signal": signal,
                "values": rsi.tail(10).tolist()
            }
        
        # MACD Calculation
        if "MACD" in indicators:
            macd, signal_line, histogram = self._calculate_macd(df['close'])
            current_hist = histogram.iloc[-1]
            prev_hist = histogram.iloc[-2]
            signal = "bullish" if current_hist > 0 and current_hist > prev_hist else "bearish"
            analysis["analysis"]["MACD"] = {
                "macd": round(float(macd.iloc[-1]), 4),
                "signal": signal,
                "histogram": round(float(current_hist), 4),
                "trend": "up" if current_hist > prev_hist else "down"
            }
        
        # Bollinger Bands
        if "BB" in indicators:
            upper, middle, lower = self._calculate_bollinger_bands(df['close'])
            current_price = df['close'].iloc[-1]
            position = (current_price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
            signal = "oversold" if position < 0.2 else "overbought" if position > 0.8 else "neutral"
            analysis["analysis"]["BB"] = {
                "upper": round(float(upper.iloc[-1]), 2),
                "middle": round(float(middle.iloc[-1]), 2),
                "lower": round(float(lower.iloc[-1]), 2),
                "signal": signal,
                "position": round(float(position), 2)
            }
        
        # Moving Averages
        if "EMA" in indicators:
            ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
            ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
            signal = "bullish" if df['close'].iloc[-1] > ema_20 > ema_50 else "bearish"
            analysis["analysis"]["EMA"] = {
                "ema_20": round(float(ema_20), 2),
                "ema_50": round(float(ema_50), 2),
                "signal": signal
            }
        
        # Volume Analysis
        if "Volume" in indicators:
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume
            signal = "high" if volume_ratio > 1.5 else "low" if volume_ratio < 0.5 else "normal"
            analysis["analysis"]["Volume"] = {
                "current": round(float(current_volume), 2),
                "average": round(float(avg_volume), 2),
                "ratio": round(float(volume_ratio), 2),
                "signal": signal
            }
        
        # Overall signal
        bullish_count = sum(1 for ind in analysis["analysis"].values() 
                          if ind.get("signal") in ["bullish", "oversold"])
        bearish_count = sum(1 for ind in analysis["analysis"].values() 
                          if ind.get("signal") in ["bearish", "overbought"])
        
        if bullish_count > bearish_count + 1:
            overall_signal = "bullish"
            confidence = bullish_count / len(analysis["analysis"])
        elif bearish_count > bullish_count + 1:
            overall_signal = "bearish"
            confidence = bearish_count / len(analysis["analysis"])
        else:
            overall_signal = "neutral"
            confidence = 0.5
            
        analysis["overall_signal"] = overall_signal
        analysis["confidence"] = round(confidence, 2)
        
        return analysis
    
    async def place_order(self, symbol: str, side: str, amount: float, 
                         order_type: str = "market", price: float = None) -> Dict[str, Any]:
        """Place real order on exchange"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Validate order parameters
            market = self.exchange.markets[symbol]
            amount = self.exchange.amount_to_precision(symbol, amount)
            
            if order_type == "limit" and price:
                price = self.exchange.price_to_precision(symbol, price)
                order = await self.exchange.create_limit_order(symbol, side, amount, price)
            else:
                order = await self.exchange.create_market_order(symbol, side, amount)
            
            return {
                "order_id": order['id'],
                "symbol": order['symbol'],
                "side": order['side'],
                "type": order['type'],
                "amount": order['amount'],
                "price": order['price'] or order['average'],
                "status": order['status'],
                "timestamp": order['datetime'],
                "filled": order['filled'],
                "remaining": order['remaining'],
                "cost": order['cost'],
                "fee": order['fee']
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise
    
    async def get_portfolio_status(self) -> Dict[str, Any]:
        """Get real portfolio status from exchange"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Fetch balance
            balance = await self.exchange.fetch_balance()
            
            # Fetch open positions
            positions = []
            if hasattr(self.exchange, 'fetch_positions'):
                positions = await self.exchange.fetch_positions()
            
            # Calculate total value in USD
            total_usd = 0
            assets = []
            
            for currency, bal in balance['total'].items():
                if bal > 0:
                    # Get USD value
                    usd_value = bal
                    if currency != 'USDT' and currency != 'USD':
                        try:
                            ticker = await self.exchange.fetch_ticker(f"{currency}/USDT")
                            usd_value = bal * ticker['last']
                        except:
                            usd_value = 0
                    
                    total_usd += usd_value
                    assets.append({
                        "currency": currency,
                        "amount": bal,
                        "usd_value": round(usd_value, 2)
                    })
            
            # Calculate PnL from positions
            total_pnl = 0
            position_list = []
            
            for pos in positions:
                pnl = pos.get('percentage', 0)
                pnl_usd = pos.get('unrealizedPnl', 0)
                total_pnl += pnl_usd
                
                position_list.append({
                    "symbol": pos['symbol'],
                    "side": pos['side'],
                    "amount": pos['contracts'],
                    "entry_price": pos['markPrice'],
                    "current_price": pos['markPrice'],
                    "pnl": pnl_usd,
                    "pnl_percentage": pnl
                })
            
            return {
                "total_balance": round(total_usd, 2),
                "available_balance": round(balance['free'].get('USDT', 0), 2),
                "assets": assets,
                "positions": position_list,
                "total_pnl": round(total_pnl, 2),
                "total_pnl_percentage": round((total_pnl / total_usd * 100) if total_usd > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error fetching portfolio status: {e}")
            raise
    
    async def set_stop_loss(self, position_id: str, stop_loss_price: float) -> Dict[str, Any]:
        """Set real stop loss order"""
        try:
            # Get position details
            positions = await self.exchange.fetch_positions()
            position = next((p for p in positions if p['id'] == position_id), None)
            
            if not position:
                raise ValueError(f"Position {position_id} not found")
            
            # Create stop loss order
            symbol = position['symbol']
            side = 'sell' if position['side'] == 'long' else 'buy'
            amount = abs(position['contracts'])
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='stop_market',
                side=side,
                amount=amount,
                stopPrice=stop_loss_price
            )
            
            return {
                "position_id": position_id,
                "stop_loss_price": stop_loss_price,
                "order_id": order['id'],
                "status": "set",
                "message": f"Stop loss set at {stop_loss_price}"
            }
            
        except Exception as e:
            logger.error(f"Error setting stop loss: {e}")
            raise
    
    async def set_take_profit(self, position_id: str, take_profit_price: float) -> Dict[str, Any]:
        """Set real take profit order"""
        try:
            # Get position details
            positions = await self.exchange.fetch_positions()
            position = next((p for p in positions if p['id'] == position_id), None)
            
            if not position:
                raise ValueError(f"Position {position_id} not found")
            
            # Create take profit order
            symbol = position['symbol']
            side = 'sell' if position['side'] == 'long' else 'buy'
            amount = abs(position['contracts'])
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='take_profit_market',
                side=side,
                amount=amount,
                stopPrice=take_profit_price
            )
            
            return {
                "position_id": position_id,
                "take_profit_price": take_profit_price,
                "order_id": order['id'],
                "status": "set",
                "message": f"Take profit set at {take_profit_price}"
            }
            
        except Exception as e:
            logger.error(f"Error setting take profit: {e}")
            raise
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()
    
    # Technical indicator calculations
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2):
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower