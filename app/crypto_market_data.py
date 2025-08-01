"""
Crypto Market Data Providers

Free APIs with generous limits for cryptocurrency data.
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


class CoinGeckoProvider(MarketDataProvider):
    """
    CoinGecko - Completely FREE, no API key required!
    - 10-30 calls/minute
    - Real-time prices
    - Historical data
    - 8000+ cryptocurrencies
    """
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.client = httpx.AsyncClient()
        self.coin_map = {
            # Map common symbols to CoinGecko IDs
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "SOL": "solana",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "AVAX": "avalanche-2",
            "DOT": "polkadot",
            "MATIC": "matic-network",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "ATOM": "cosmos",
            "XLM": "stellar",
            "ALGO": "algorand",
            "NEAR": "near",
            "FTM": "fantom",
            "SAND": "the-sandbox",
            "MANA": "decentraland",
            "AAVE": "aave",
            "CRV": "curve-dao-token",
            "SUSHI": "sushi",
            "COMP": "compound-governance-token",
        }
        
    def _get_coin_id(self, symbol: str) -> str:
        """Convert symbol to CoinGecko ID"""
        return self.coin_map.get(symbol.upper(), symbol.lower())
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from CoinGecko"""
        try:
            coin_id = self._get_coin_id(symbol)
            
            response = await self.client.get(
                f"{self.base_url}/simple/price",
                params={
                    "ids": coin_id,
                    "vs_currencies": "usd"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if coin_id in data:
                    price = data[coin_id]["usd"]
                    logger.info(f"CoinGecko: {symbol} price: ${price}")
                    return float(price)
                    
            return None
            
        except Exception as e:
            logger.error(f"CoinGecko error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1", interval: str = "hourly") -> Optional[pd.DataFrame]:
        """Get historical data from CoinGecko"""
        try:
            coin_id = self._get_coin_id(symbol)
            days = {"1": 1, "7": 7, "30": 30, "90": 90, "365": 365}.get(period, 1)
            
            response = await self.client.get(
                f"{self.base_url}/coins/{coin_id}/market_chart",
                params={
                    "vs_currency": "usd",
                    "days": days
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Convert to DataFrame
                prices = data["prices"]
                df = pd.DataFrame(prices, columns=["timestamp", "price"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                
                # Add OHLCV format (CoinGecko only provides close prices)
                df["Open"] = df["price"]
                df["High"] = df["price"]
                df["Low"] = df["price"]
                df["Close"] = df["price"]
                df["Volume"] = 0  # CoinGecko doesn't provide volume in this endpoint
                
                df = df[["Open", "High", "Low", "Close", "Volume"]]
                
                logger.info(f"CoinGecko: Retrieved {len(df)} records for {symbol}")
                return df
                
            return None
            
        except Exception as e:
            logger.error(f"CoinGecko historical error for {symbol}: {e}")
            return None
            
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed quote from CoinGecko"""
        try:
            coin_id = self._get_coin_id(symbol)
            
            response = await self.client.get(
                f"{self.base_url}/coins/{coin_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                market_data = data["market_data"]
                
                return {
                    "symbol": symbol.upper(),
                    "name": data["name"],
                    "price": market_data["current_price"]["usd"],
                    "market_cap": market_data["market_cap"]["usd"],
                    "volume": market_data["total_volume"]["usd"],
                    "high_24h": market_data["high_24h"]["usd"],
                    "low_24h": market_data["low_24h"]["usd"],
                    "price_change_24h": market_data["price_change_24h"],
                    "price_change_percentage_24h": market_data["price_change_percentage_24h"],
                    "circulating_supply": market_data["circulating_supply"],
                    "total_supply": market_data["total_supply"],
                    "ath": market_data["ath"]["usd"],
                    "ath_date": market_data["ath_date"]["usd"],
                    "atl": market_data["atl"]["usd"],
                    "atl_date": market_data["atl_date"]["usd"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            return None
            
        except Exception as e:
            logger.error(f"CoinGecko quote error for {symbol}: {e}")
            return None


class BinancePublicProvider(MarketDataProvider):
    """
    Binance Public API - No API key required!
    - 1200 requests/minute
    - Real-time prices
    - Order book data
    - Historical klines
    """
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.client = httpx.AsyncClient()
        
    def _format_symbol(self, symbol: str) -> str:
        """Format symbol for Binance (e.g., BTC -> BTCUSDT)"""
        if symbol.upper().endswith("USDT"):
            return symbol.upper()
        return f"{symbol.upper()}USDT"
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Binance"""
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            response = await self.client.get(
                f"{self.base_url}/ticker/price",
                params={"symbol": formatted_symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                price = float(data["price"])
                logger.info(f"Binance: {symbol} price: ${price}")
                return price
                
            return None
            
        except Exception as e:
            logger.error(f"Binance error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Get historical klines from Binance"""
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            # Map intervals
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d"
            }
            
            response = await self.client.get(
                f"{self.base_url}/klines",
                params={
                    "symbol": formatted_symbol,
                    "interval": interval_map.get(interval, "1h"),
                    "limit": 500  # Max 500 per request
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=[
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ])
                
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                
                # Convert to float and rename
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = df[col].astype(float)
                    
                df = df[["open", "high", "low", "close", "volume"]]
                df.columns = ["Open", "High", "Low", "Close", "Volume"]
                
                logger.info(f"Binance: Retrieved {len(df)} records for {symbol}")
                return df
                
            return None
            
        except Exception as e:
            logger.error(f"Binance historical error for {symbol}: {e}")
            return None
            
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get 24hr ticker from Binance"""
        try:
            formatted_symbol = self._format_symbol(symbol)
            
            response = await self.client.get(
                f"{self.base_url}/ticker/24hr",
                params={"symbol": formatted_symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "symbol": symbol.upper(),
                    "price": float(data["lastPrice"]),
                    "bid": float(data["bidPrice"]),
                    "ask": float(data["askPrice"]),
                    "open": float(data["openPrice"]),
                    "high": float(data["highPrice"]),
                    "low": float(data["lowPrice"]),
                    "volume": float(data["volume"]),
                    "quote_volume": float(data["quoteVolume"]),
                    "price_change": float(data["priceChange"]),
                    "price_change_percent": float(data["priceChangePercent"]),
                    "trades": int(data["count"]),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Binance quote error for {symbol}: {e}")
            return None


class CoinbasePublicProvider(MarketDataProvider):
    """
    Coinbase Public API - No API key required!
    - 10 requests/second
    - Real-time prices
    - Order book
    """
    
    def __init__(self):
        self.base_url = "https://api.coinbase.com/v2"
        self.client = httpx.AsyncClient()
        
    def _format_pair(self, symbol: str) -> str:
        """Format symbol for Coinbase (e.g., BTC -> BTC-USD)"""
        if "-" in symbol:
            return symbol.upper()
        return f"{symbol.upper()}-USD"
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Coinbase"""
        try:
            pair = self._format_pair(symbol)
            
            response = await self.client.get(
                f"{self.base_url}/exchange-rates",
                params={"currency": symbol.upper()}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "rates" in data["data"] and "USD" in data["data"]["rates"]:
                    price = float(data["data"]["rates"]["USD"])
                    logger.info(f"Coinbase: {symbol} price: ${price}")
                    return price
                    
            return None
            
        except Exception as e:
            logger.error(f"Coinbase error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Coinbase doesn't provide historical data without API key"""
        return None
        
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get spot price from Coinbase"""
        try:
            pair = self._format_pair(symbol)
            
            response = await self.client.get(
                f"{self.base_url}/prices/{pair}/spot"
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    return {
                        "symbol": symbol.upper(),
                        "price": float(data["data"]["amount"]),
                        "currency": data["data"]["currency"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
            return None
            
        except Exception as e:
            logger.error(f"Coinbase quote error for {symbol}: {e}")
            return None


class CryptoCompareProvider(MarketDataProvider):
    """
    CryptoCompare - Free tier available
    - 100,000 calls/month free
    - Historical data
    - Real-time prices
    """
    
    def __init__(self):
        self.base_url = "https://min-api.cryptocompare.com/data"
        self.client = httpx.AsyncClient()
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from CryptoCompare"""
        try:
            response = await self.client.get(
                f"{self.base_url}/price",
                params={
                    "fsym": symbol.upper(),
                    "tsyms": "USD"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "USD" in data:
                    price = data["USD"]
                    logger.info(f"CryptoCompare: {symbol} price: ${price}")
                    return float(price)
                    
            return None
            
        except Exception as e:
            logger.error(f"CryptoCompare error for {symbol}: {e}")
            return None
            
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "hour") -> Optional[pd.DataFrame]:
        """Get historical data from CryptoCompare"""
        try:
            # Determine endpoint based on interval
            if interval in ["minute", "1m", "5m", "15m", "30m"]:
                endpoint = "histominute"
                limit = 1440  # 24 hours of minutes
            elif interval in ["hour", "1h", "2h", "4h"]:
                endpoint = "histohour"
                limit = 168  # 7 days of hours
            else:
                endpoint = "histoday"
                limit = 30  # 30 days
                
            response = await self.client.get(
                f"{self.base_url}/{endpoint}",
                params={
                    "fsym": symbol.upper(),
                    "tsym": "USD",
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "Data" in data:
                    df = pd.DataFrame(data["Data"])
                    df["time"] = pd.to_datetime(df["time"], unit="s")
                    df.set_index("time", inplace=True)
                    df = df[["open", "high", "low", "close", "volumefrom"]]
                    df.columns = ["Open", "High", "Low", "Close", "Volume"]
                    
                    logger.info(f"CryptoCompare: Retrieved {len(df)} records for {symbol}")
                    return df
                    
            return None
            
        except Exception as e:
            logger.error(f"CryptoCompare historical error for {symbol}: {e}")
            return None
            
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get full data from CryptoCompare"""
        try:
            response = await self.client.get(
                f"{self.base_url}/pricemultifull",
                params={
                    "fsyms": symbol.upper(),
                    "tsyms": "USD"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "DISPLAY" in data and symbol.upper() in data["DISPLAY"]:
                    display = data["DISPLAY"][symbol.upper()]["USD"]
                    raw = data["RAW"][symbol.upper()]["USD"]
                    
                    return {
                        "symbol": symbol.upper(),
                        "price": raw["PRICE"],
                        "open": raw["OPEN24HOUR"],
                        "high": raw["HIGH24HOUR"],
                        "low": raw["LOW24HOUR"],
                        "volume": raw["VOLUME24HOUR"],
                        "market_cap": raw["MKTCAP"],
                        "change_24h": raw["CHANGE24HOUR"],
                        "change_pct_24h": raw["CHANGEPCT24HOUR"],
                        "supply": raw["SUPPLY"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
            return None
            
        except Exception as e:
            logger.error(f"CryptoCompare quote error for {symbol}: {e}")
            return None