"""
Alternative Free Market Data Providers

This module implements providers with better rate limits for free usage.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import pandas as pd

from .market_data import MarketDataProvider

logger = logging.getLogger(__name__)


class TwelveDataProvider(MarketDataProvider):
    """
    Twelve Data - 800 API calls/day free tier
    Real-time and historical data
    """
    
    def __init__(self, api_key: str = "demo"):
        self.api_key = api_key
        self.base_url = "https://api.twelvedata.com"
        self.client = httpx.AsyncClient()
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Twelve Data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/price",
                params={
                    "symbol": symbol,
                    "apikey": self.api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                price = float(data.get("price", 0))
                logger.info(f"Twelve Data: {symbol} price: ${price}")
                return price
            else:
                logger.warning(f"Twelve Data error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Twelve Data error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1day", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Get historical data from Twelve Data"""
        try:
            # Map period to outputsize
            outputsize = 24 if period == "1day" else 100
            
            response = await self.client.get(
                f"{self.base_url}/time_series",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "outputsize": outputsize,
                    "apikey": self.api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "values" in data:
                    df = pd.DataFrame(data["values"])
                    df["datetime"] = pd.to_datetime(df["datetime"])
                    df.set_index("datetime", inplace=True)
                    
                    # Convert to float
                    for col in ["open", "high", "low", "close", "volume"]:
                        df[col] = df[col].astype(float)
                        
                    # Rename columns
                    df.columns = ["Open", "High", "Low", "Close", "Volume"]
                    
                    logger.info(f"Twelve Data: Retrieved {len(df)} records for {symbol}")
                    return df
                    
            return None
            
        except Exception as e:
            logger.error(f"Twelve Data historical error for {symbol}: {e}")
            return None
            
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from Twelve Data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/quote",
                params={
                    "symbol": symbol,
                    "apikey": self.api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": symbol,
                    "price": float(data.get("close", 0)),
                    "open": float(data.get("open", 0)),
                    "high": float(data.get("high", 0)),
                    "low": float(data.get("low", 0)),
                    "volume": int(data.get("volume", 0)),
                    "previousClose": float(data.get("previous_close", 0)),
                    "change": float(data.get("change", 0)),
                    "changePercent": float(data.get("percent_change", 0)),
                    "timestamp": data.get("datetime", datetime.utcnow().isoformat())
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Twelve Data quote error for {symbol}: {e}")
            return None


class MarketStackProvider(MarketDataProvider):
    """
    MarketStack - 1000 API calls/month free
    End-of-day data
    """
    
    def __init__(self, api_key: str = "demo"):
        self.api_key = api_key
        self.base_url = "http://api.marketstack.com/v1"
        self.client = httpx.AsyncClient()
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get latest price from MarketStack"""
        try:
            response = await self.client.get(
                f"{self.base_url}/eod/latest",
                params={
                    "access_key": self.api_key,
                    "symbols": symbol
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    price = data["data"][0]["close"]
                    logger.info(f"MarketStack: {symbol} price: ${price}")
                    return float(price)
                    
            return None
            
        except Exception as e:
            logger.error(f"MarketStack error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1day", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Get historical data from MarketStack (daily only)"""
        try:
            # MarketStack only provides daily data in free tier
            response = await self.client.get(
                f"{self.base_url}/eod",
                params={
                    "access_key": self.api_key,
                    "symbols": symbol,
                    "limit": 100
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    df = pd.DataFrame(data["data"])
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)
                    df = df[["open", "high", "low", "close", "volume"]]
                    df.columns = ["Open", "High", "Low", "Close", "Volume"]
                    
                    logger.info(f"MarketStack: Retrieved {len(df)} records for {symbol}")
                    return df
                    
            return None
            
        except Exception as e:
            logger.error(f"MarketStack historical error for {symbol}: {e}")
            return None
            
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from MarketStack"""
        # Use the same endpoint as current price
        price = await self.get_current_price(symbol)
        if price:
            return {
                "symbol": symbol,
                "price": price,
                "timestamp": datetime.utcnow().isoformat()
            }
        return None


class FinnhubProvider(MarketDataProvider):
    """
    Finnhub - 60 API calls/minute free
    Real-time data
    """
    
    def __init__(self, api_key: str = "demo"):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.client = httpx.AsyncClient()
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Finnhub"""
        try:
            response = await self.client.get(
                f"{self.base_url}/quote",
                params={
                    "symbol": symbol,
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                price = data.get("c", 0)  # Current price
                if price > 0:
                    logger.info(f"Finnhub: {symbol} price: ${price}")
                    return float(price)
                    
            return None
            
        except Exception as e:
            logger.error(f"Finnhub error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1day", interval: str = "60") -> Optional[pd.DataFrame]:
        """Get historical data from Finnhub"""
        try:
            # Calculate timestamps
            to_timestamp = int(datetime.now().timestamp())
            from_timestamp = to_timestamp - (86400 if period == "1day" else 604800)  # 1 day or 1 week
            
            # Map interval to resolution
            resolution = "60" if interval == "1h" else "D"
            
            response = await self.client.get(
                f"{self.base_url}/stock/candle",
                params={
                    "symbol": symbol,
                    "resolution": resolution,
                    "from": from_timestamp,
                    "to": to_timestamp,
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("s") == "ok":
                    df = pd.DataFrame({
                        "Open": data["o"],
                        "High": data["h"],
                        "Low": data["l"],
                        "Close": data["c"],
                        "Volume": data["v"],
                        "timestamp": data["t"]
                    })
                    
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
                    df.set_index("timestamp", inplace=True)
                    
                    logger.info(f"Finnhub: Retrieved {len(df)} records for {symbol}")
                    return df
                    
            return None
            
        except Exception as e:
            logger.error(f"Finnhub historical error for {symbol}: {e}")
            return None
            
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from Finnhub"""
        try:
            response = await self.client.get(
                f"{self.base_url}/quote",
                params={
                    "symbol": symbol,
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": symbol,
                    "price": data.get("c", 0),
                    "open": data.get("o", 0),
                    "high": data.get("h", 0),
                    "low": data.get("l", 0),
                    "previousClose": data.get("pc", 0),
                    "change": data.get("d", 0),
                    "changePercent": data.get("dp", 0),
                    "timestamp": datetime.fromtimestamp(data.get("t", 0)).isoformat()
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Finnhub quote error for {symbol}: {e}")
            return None


class PolygonProvider(MarketDataProvider):
    """
    Polygon.io - 5 API calls/minute free
    High-quality data but limited in free tier
    """
    
    def __init__(self, api_key: str = "demo"):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self.client = httpx.AsyncClient()
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Polygon"""
        try:
            response = await self.client.get(
                f"{self.base_url}/v2/aggs/ticker/{symbol}/prev",
                params={"apiKey": self.api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "results" in data and len(data["results"]) > 0:
                    price = data["results"][0]["c"]  # Close price
                    logger.info(f"Polygon: {symbol} price: ${price}")
                    return float(price)
                    
            return None
            
        except Exception as e:
            logger.error(f"Polygon error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1day", interval: str = "hour") -> Optional[pd.DataFrame]:
        """Get historical data from Polygon"""
        try:
            # Calculate date range
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
            
            response = await self.client.get(
                f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/{interval}/{from_date}/{to_date}",
                params={"apiKey": self.api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    df = pd.DataFrame(data["results"])
                    df["timestamp"] = pd.to_datetime(df["t"], unit="ms")
                    df.set_index("timestamp", inplace=True)
                    df = df[["o", "h", "l", "c", "v"]]
                    df.columns = ["Open", "High", "Low", "Close", "Volume"]
                    
                    logger.info(f"Polygon: Retrieved {len(df)} records for {symbol}")
                    return df
                    
            return None
            
        except Exception as e:
            logger.error(f"Polygon historical error for {symbol}: {e}")
            return None
            
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from Polygon"""
        try:
            response = await self.client.get(
                f"{self.base_url}/v3/quotes/{symbol}",
                params={"apiKey": self.api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    result = data["results"]
                    return {
                        "symbol": symbol,
                        "bid": result.get("bid_price", 0),
                        "ask": result.get("ask_price", 0),
                        "bidSize": result.get("bid_size", 0),
                        "askSize": result.get("ask_size", 0),
                        "timestamp": result.get("participant_timestamp", datetime.utcnow().isoformat())
                    }
                    
            # Fallback to previous day's data
            return await self._get_prev_quote(symbol)
            
        except Exception as e:
            logger.error(f"Polygon quote error for {symbol}: {e}")
            return None
            
    async def _get_prev_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get previous day's quote as fallback"""
        price = await self.get_current_price(symbol)
        if price:
            return {
                "symbol": symbol,
                "price": price,
                "timestamp": datetime.utcnow().isoformat()
            }
        return None


# Free tier API keys for testing
FREE_API_KEYS = {
    "twelvedata": "demo",  # Replace with your free key from https://twelvedata.com/apikey
    "marketstack": "demo",  # Replace with your free key from https://marketstack.com/signup/free
    "finnhub": "c2q2r8iad3i9rjb92vfg",     # Free demo key with limits
    "polygon": "demo",      # Replace with your free key from https://polygon.io/
    "alphavantage": "demo"  # Demo key for testing
}