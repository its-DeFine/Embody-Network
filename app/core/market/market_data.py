"""
Market Data Service

This module provides real-time and historical market data from various providers.
It supports multiple data sources with automatic fallback and caching.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import os

import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
import pandas as pd
import numpy as np
import ta

from ...dependencies import get_redis
from ...config import settings
from ...infrastructure.monitoring.reliability_manager import reliability_manager

logger = logging.getLogger(__name__)


class MarketDataProvider(ABC):
    """Abstract base class for market data providers"""
    
    @abstractmethod
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Get historical OHLCV data"""
        pass
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed quote information"""
        pass


class MockMarketDataProvider(MarketDataProvider):
    """Mock provider with realistic price movements for testing"""
    
    def __init__(self):
        self.base_prices = {
            "AAPL": 180.0,
            "MSFT": 350.0, 
            "GOOGL": 140.0,
            "TSLA": 250.0,
            "NVDA": 120.0,
            "META": 450.0,
            "AMZN": 150.0
        }
        self.price_history = {}
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Generate realistic price with small fluctuations"""
        import random
        import time
        
        if symbol not in self.base_prices:
            return None
            
        # Get last price or use base price
        last_price = self.price_history.get(symbol, self.base_prices[symbol])
        
        # Add realistic price movement (-0.5% to +0.5%)
        change_pct = random.uniform(-0.005, 0.005)
        new_price = last_price * (1 + change_pct)
        
        # Store for consistency
        self.price_history[symbol] = new_price
        
        logger.info(f"Mock data: {symbol} = ${new_price:.2f}")
        return new_price
        
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Generate mock historical data"""
        import random
        from datetime import datetime, timedelta
        
        if symbol not in self.base_prices:
            return None
            
        # Generate mock historical data
        end_time = datetime.now()
        if period == "1d":
            start_time = end_time - timedelta(days=1)
            freq = "1H"
        elif period == "5d":
            start_time = end_time - timedelta(days=5)
            freq = "1H"
        else:
            start_time = end_time - timedelta(days=30)
            freq = "1D"
            
        timestamps = pd.date_range(start=start_time, end=end_time, freq=freq)
        base_price = self.base_prices[symbol]
        
        # Generate realistic OHLCV data
        data = []
        current_price = base_price
        
        for ts in timestamps:
            # Random walk with mean reversion
            change = random.uniform(-0.02, 0.02)  # -2% to +2%
            current_price = current_price * (1 + change)
            
            # Generate OHLCV
            open_price = current_price * random.uniform(0.995, 1.005)
            high_price = current_price * random.uniform(1.0, 1.02)
            low_price = current_price * random.uniform(0.98, 1.0)
            close_price = current_price
            volume = random.randint(1000000, 10000000)
            
            data.append({
                "Open": open_price,
                "High": high_price,
                "Low": low_price,
                "Close": close_price,
                "Volume": volume
            })
            
        df = pd.DataFrame(data, index=timestamps)
        return df
        
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Generate mock quote data"""
        import random
        price = await self.get_current_price(symbol)
        if not price:
            return None
            
        return {
            "symbol": symbol,
            "price": price,
            "open": price * 0.995,
            "high": price * 1.01,
            "low": price * 0.99,
            "volume": random.randint(1000000, 10000000),
            "timestamp": datetime.utcnow().isoformat()
        }


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance data provider (free, no API key required)"""
    
    def __init__(self):
        self.cache_ttl = 60  # Cache for 1 minute
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.info
            
            # Try different price fields
            price = data.get('currentPrice') or data.get('regularMarketPrice') or data.get('previousClose')
            
            if price:
                logger.info(f"Yahoo Finance: {symbol} current price: ${price}")
                return float(price)
            else:
                logger.warning(f"Yahoo Finance: No price data for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Yahoo Finance error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Get historical data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Download historical data
            data = ticker.history(period=period, interval=interval)
            
            if not data.empty:
                logger.info(f"Yahoo Finance: Retrieved {len(data)} records for {symbol}")
                return data
            else:
                logger.warning(f"Yahoo Finance: No historical data for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Yahoo Finance historical data error for {symbol}: {e}")
            return None
            
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed quote from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            quote = {
                "symbol": symbol,
                "price": info.get('currentPrice') or info.get('regularMarketPrice'),
                "open": info.get('open') or info.get('regularMarketOpen'),
                "high": info.get('dayHigh') or info.get('regularMarketDayHigh'),
                "low": info.get('dayLow') or info.get('regularMarketDayLow'),
                "volume": info.get('volume') or info.get('regularMarketVolume'),
                "previousClose": info.get('previousClose') or info.get('regularMarketPreviousClose'),
                "change": info.get('regularMarketChange'),
                "changePercent": info.get('regularMarketChangePercent'),
                "bid": info.get('bid'),
                "ask": info.get('ask'),
                "bidSize": info.get('bidSize'),
                "askSize": info.get('askSize'),
                "marketCap": info.get('marketCap'),
                "fiftyTwoWeekHigh": info.get('fiftyTwoWeekHigh'),
                "fiftyTwoWeekLow": info.get('fiftyTwoWeekLow'),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return {k: v for k, v in quote.items() if v is not None}
            
        except Exception as e:
            logger.error(f"Yahoo Finance quote error for {symbol}: {e}")
            return None


class AlphaVantageProvider(MarketDataProvider):
    """Alpha Vantage data provider (requires free API key)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if self.api_key:
            self.ts = TimeSeries(key=self.api_key, output_format='pandas')
            self.ti = TechIndicators(key=self.api_key, output_format='pandas')
        else:
            self.ts = None
            self.ti = None
            logger.warning("Alpha Vantage API key not provided")
            
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Alpha Vantage"""
        if not self.ts:
            return None
            
        try:
            # Get intraday data (most recent price)
            data, _ = await asyncio.to_thread(self.ts.get_intraday, symbol=symbol, interval='1min', outputsize='compact')
            
            if not data.empty:
                # Get the most recent price
                latest_price = data.iloc[0]['4. close']
                logger.info(f"Alpha Vantage: {symbol} current price: ${latest_price}")
                return float(latest_price)
            
        except Exception as e:
            logger.error(f"Alpha Vantage error for {symbol}: {e}")
            
        return None
        
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "60min") -> Optional[pd.DataFrame]:
        """Get historical data from Alpha Vantage"""
        if not self.ts:
            return None
            
        try:
            # Map period to Alpha Vantage function
            if period in ["1d", "5d"]:
                data, _ = await asyncio.to_thread(self.ts.get_intraday, symbol=symbol, interval=interval, outputsize='full')
            else:
                data, _ = await asyncio.to_thread(self.ts.get_daily, symbol=symbol, outputsize='full')
                
            if not data.empty:
                # Rename columns to standard OHLCV format
                data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                logger.info(f"Alpha Vantage: Retrieved {len(data)} records for {symbol}")
                return data
                
        except Exception as e:
            logger.error(f"Alpha Vantage historical data error for {symbol}: {e}")
            
        return None
        
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from Alpha Vantage"""
        if not self.ts:
            return None
            
        try:
            data, _ = await asyncio.to_thread(self.ts.get_quote_endpoint, symbol=symbol)
            
            if not data.empty:
                row = data.iloc[0]
                quote = {
                    "symbol": symbol,
                    "price": float(row['05. price']),
                    "open": float(row['02. open']),
                    "high": float(row['03. high']),
                    "low": float(row['04. low']),
                    "volume": int(row['06. volume']),
                    "previousClose": float(row['08. previous close']),
                    "change": float(row['09. change']),
                    "changePercent": row['10. change percent'].rstrip('%'),
                    "timestamp": row['07. latest trading day']
                }
                return quote
                
        except Exception as e:
            logger.error(f"Alpha Vantage quote error for {symbol}: {e}")
            
        return None


class MarketDataService:
    """Main market data service with caching and fallback support"""
    
    def __init__(self):
        # Import alternative providers
        try:
            from .market_data_providers import (
                TwelveDataProvider, MarketStackProvider, 
                FinnhubProvider, PolygonProvider, FREE_API_KEYS
            )
            from .crypto_market_data import (
                CoinGeckoProvider, BinancePublicProvider,
                CoinbasePublicProvider, CryptoCompareProvider
            )
            from .blockchain_data import crypto_data_service
            
            # Traditional stock providers
            self.providers = {
                "mock": MockMarketDataProvider(),
                "yahoo": YahooFinanceProvider(),
                "alpha_vantage": AlphaVantageProvider(),
                "twelvedata": TwelveDataProvider(FREE_API_KEYS.get("twelvedata", "demo")),
                "marketstack": MarketStackProvider(FREE_API_KEYS.get("marketstack", "demo")),
                "finnhub": FinnhubProvider(FREE_API_KEYS.get("finnhub", "demo")),
                "polygon": PolygonProvider(FREE_API_KEYS.get("polygon", "demo"))
            }
            
            # Crypto providers
            self.crypto_providers = {
                "coingecko": CoinGeckoProvider(),
                "binance": BinancePublicProvider(),
                "coinbase": CoinbasePublicProvider(),
                "cryptocompare": CryptoCompareProvider(),
                "chainlink": crypto_data_service  # Blockchain oracle data
            }
            
            # Combined providers
            self.all_providers = {**self.providers, **self.crypto_providers}
            
            self.primary_provider = "mock"  # For stocks - no rate limits
            self.primary_crypto_provider = "coingecko"  # For crypto
            self.fallback_order = ["yahoo", "twelvedata", "finnhub", "marketstack", "polygon", "alpha_vantage"]
            self.crypto_fallback_order = ["binance", "cryptocompare", "coinbase", "chainlink"]
            
        except ImportError:
            # Fallback if providers not available - but always include mock
            self.providers = {
                "mock": MockMarketDataProvider(),
                "yahoo": YahooFinanceProvider(),
                "alpha_vantage": AlphaVantageProvider()
            }
            self.crypto_providers = {}
            self.all_providers = self.providers
            self.primary_provider = "mock"  # Use mock even in fallback mode
            self.primary_crypto_provider = None
            self.fallback_order = ["yahoo", "alpha_vantage"]
            self.crypto_fallback_order = []
            
        self.redis = None
        self.cache_ttl = 600  # 10 minute cache to reduce API calls
        self.last_request_time = {}
        self.min_request_interval = 2  # Minimum 2 seconds between requests per symbol
        
    async def initialize(self):
        """Initialize the market data service"""
        self.redis = await get_redis()
        logger.info("Market Data Service initialized")
        
    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency"""
        crypto_symbols = {
            "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", 
            "DOT", "MATIC", "LINK", "UNI", "ATOM", "XLM", "ALGO", "NEAR",
            "FTM", "SAND", "MANA", "AAVE", "CRV", "SUSHI", "COMP", "LTC",
            "BCH", "ETC", "XMR", "TRX", "SHIB", "APE", "ARB", "OP"
        }
        return symbol.upper() in crypto_symbols or "-" in symbol or "/" in symbol
        
    async def get_current_price(self, symbol: str, use_cache: bool = True) -> Optional[float]:
        """Get current price with caching, fallback, and reliability features"""
        # Check cache first
        if use_cache and self.redis:
            cache_key = f"market:price:{symbol}"
            cached = await self.redis.get(cache_key)
            if cached:
                return float(cached)
                
        # Determine if crypto or stock
        is_crypto = self._is_crypto(symbol)
        
        if is_crypto and self.primary_crypto_provider:
            # Try crypto providers with reliability wrapper
            provider = self.crypto_providers[self.primary_crypto_provider]
            price = await reliability_manager.execute_with_reliability(
                self.primary_crypto_provider,
                provider.get_current_price,
                symbol
            )
            
            # Fallback to other crypto providers
            if price is None:
                for provider_name in self.crypto_fallback_order:
                    if provider_name in self.crypto_providers:
                        provider = self.crypto_providers[provider_name]
                        if provider_name == "chainlink":
                            # Special handling for chainlink
                            price = await reliability_manager.execute_with_reliability(
                                provider_name,
                                provider.get_price,
                                symbol
                            )
                        else:
                            price = await reliability_manager.execute_with_reliability(
                                provider_name,
                                provider.get_current_price,
                                symbol
                            )
                        if price is not None:
                            logger.info(f"Got crypto price from fallback provider: {provider_name}")
                            break
        else:
            # Try stock providers with reliability wrapper
            provider = self.providers[self.primary_provider]
            price = await reliability_manager.execute_with_reliability(
                self.primary_provider,
                provider.get_current_price,
                symbol
            )
            
            # Fallback to other providers in order
            if price is None:
                for provider_name in self.fallback_order:
                    if provider_name in self.providers:
                        provider = self.providers[provider_name]
                        price = await reliability_manager.execute_with_reliability(
                            provider_name,
                            provider.get_current_price,
                            symbol
                        )
                        if price is not None:
                            logger.info(f"Got price from fallback provider: {provider_name}")
                            break
                            
        # Cache the result
        if price is not None and self.redis:
            await self.redis.set(f"market:price:{symbol}", str(price), ex=self.cache_ttl)
            
        return price
        
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Get historical OHLCV data"""
        is_crypto = self._is_crypto(symbol)
        
        if is_crypto and self.primary_crypto_provider:
            # Try crypto providers
            data = await self.crypto_providers[self.primary_crypto_provider].get_historical_data(symbol, period, interval)
            
            # Fallback
            if data is None:
                for name in self.crypto_fallback_order:
                    if name in self.crypto_providers and name != "chainlink":  # Chainlink doesn't have historical
                        data = await self.crypto_providers[name].get_historical_data(symbol, period, interval)
                        if data is not None:
                            break
        else:
            # Try stock providers
            data = await self.providers[self.primary_provider].get_historical_data(symbol, period, interval)
            
            # Fallback
            if data is None:
                for name, provider in self.providers.items():
                    if name != self.primary_provider:
                        data = await provider.get_historical_data(symbol, period, interval)
                        if data is not None:
                            break
                            
        return data
        
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed quote information"""
        # Check cache
        if self.redis:
            cache_key = f"market:quote:{symbol}"
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
                
        is_crypto = self._is_crypto(symbol)
        
        if is_crypto and self.primary_crypto_provider:
            # Try crypto providers
            quote = await self.crypto_providers[self.primary_crypto_provider].get_quote(symbol)
            
            if quote is None:
                for name in self.crypto_fallback_order:
                    if name in self.crypto_providers and name != "chainlink":
                        quote = await self.crypto_providers[name].get_quote(symbol)
                        if quote is not None:
                            break
        else:
            # Try stock providers
            quote = await self.providers[self.primary_provider].get_quote(symbol)
            
            if quote is None:
                for name, provider in self.providers.items():
                    if name != self.primary_provider:
                        quote = await provider.get_quote(symbol)
                        if quote is not None:
                            break
                            
        # Cache the result
        if quote is not None and self.redis:
            await self.redis.set(f"market:quote:{symbol}", json.dumps(quote), ex=self.cache_ttl)
            
        return quote
        
    async def get_technical_indicators(self, symbol: str, period: str = "1d") -> Dict[str, Any]:
        """Calculate technical indicators"""
        # Get historical data
        data = await self.get_historical_data(symbol, period)
        
        if data is None or data.empty:
            return {}
            
        try:
            # Calculate indicators using ta library
            indicators = {}
            
            # Trend indicators
            indicators['sma_20'] = ta.trend.sma_indicator(data['Close'], window=20).iloc[-1]
            indicators['ema_20'] = ta.trend.ema_indicator(data['Close'], window=20).iloc[-1]
            
            # MACD
            macd = ta.trend.MACD(data['Close'])
            indicators['macd'] = macd.macd().iloc[-1]
            indicators['macd_signal'] = macd.macd_signal().iloc[-1]
            indicators['macd_diff'] = macd.macd_diff().iloc[-1]
            
            # RSI
            indicators['rsi'] = ta.momentum.RSIIndicator(data['Close']).rsi().iloc[-1]
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(data['Close'])
            indicators['bb_upper'] = bb.bollinger_hband().iloc[-1]
            indicators['bb_middle'] = bb.bollinger_mavg().iloc[-1]
            indicators['bb_lower'] = bb.bollinger_lband().iloc[-1]
            
            # Volume indicators
            indicators['volume_sma'] = ta.volume.volume_weighted_average_price(
                data['High'], data['Low'], data['Close'], data['Volume']
            ).iloc[-1]
            
            # Add current price context
            current_price = data['Close'].iloc[-1]
            indicators['current_price'] = current_price
            
            # Add signals
            indicators['rsi_signal'] = 'oversold' if indicators['rsi'] < 30 else 'overbought' if indicators['rsi'] > 70 else 'neutral'
            indicators['macd_signal_trend'] = 'bullish' if indicators['macd'] > indicators['macd_signal'] else 'bearish'
            indicators['bb_signal'] = 'oversold' if current_price < indicators['bb_lower'] else 'overbought' if current_price > indicators['bb_upper'] else 'neutral'
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return {}
            
    async def get_market_summary(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Get market summary for multiple symbols"""
        tasks = []
        for symbol in symbols:
            tasks.append(self.get_quote(symbol))
            
        quotes = await asyncio.gather(*tasks)
        
        # Filter out None values
        return [q for q in quotes if q is not None]
        
    async def stream_prices(self, symbols: List[str], callback):
        """Stream real-time prices with reliability management"""
        logger.info(f"Starting reliable price stream for {symbols}")
        
        # Start health monitor in background
        asyncio.create_task(reliability_manager.start_health_monitor())
        
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        while True:
            try:
                successful_updates = 0
                
                for symbol in symbols:
                    price = await self.get_current_price(symbol, use_cache=False)
                    if price:
                        await callback(symbol, price)
                        successful_updates += 1
                        
                # Reset failure counter on any success
                if successful_updates > 0:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    
                # Check system health
                if consecutive_failures >= max_consecutive_failures:
                    health = await reliability_manager.get_health_report()
                    logger.error(f"Too many consecutive failures. Health: {health['status']}")
                    
                    # Increase delay when system is unhealthy
                    await asyncio.sleep(30)
                    consecutive_failures = 0  # Reset to try again
                    continue
                        
                # Dynamic rate based on symbol types and system health
                crypto_symbols = [s for s in symbols if self._is_crypto(s)]
                stock_symbols = [s for s in symbols if not self._is_crypto(s)]
                
                # Get system health
                health = await reliability_manager.get_health_report()
                
                if health["status"] == "degraded":
                    # Slow down when degraded
                    await asyncio.sleep(10)
                elif crypto_symbols and not stock_symbols:
                    await asyncio.sleep(2)  # Crypto APIs generally allow faster polling
                else:
                    await asyncio.sleep(5)  # Stock APIs have stricter rate limits
                
            except Exception as e:
                logger.error(f"Error in price stream: {e}")
                consecutive_failures += 1
                await asyncio.sleep(10)
                
    async def get_crypto_all_prices(self) -> Dict[str, float]:
        """Get all available crypto prices from Chainlink oracles"""
        if "chainlink" in self.crypto_providers:
            return await self.crypto_providers["chainlink"].get_all_prices()
        return {}
        
    async def get_system_health(self) -> Dict[str, Any]:
        """Get market data system health report"""
        return await reliability_manager.get_health_report()


# Global market data service instance
market_data_service = MarketDataService()