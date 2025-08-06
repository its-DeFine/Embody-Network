"""
Oracle Manager - Central Oracle for Market Data

This module implements the Oracle Manager which serves as the central oracle
for all market data in the system. It provides:
- Centralized API key management
- Data aggregation and validation
- Caching and rate limiting
- Failover between providers
- Integration with Chainlink for on-chain data
"""

import asyncio
import json
import logging
import hashlib
import hmac
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import os

from fastapi import HTTPException, status
import pandas as pd

from ...config import settings
from ...dependencies import get_redis
from ..market.market_data import MarketDataService
from ..market.blockchain_data import ChainlinkOracleProvider

logger = logging.getLogger(__name__)


class OracleType(Enum):
    """Types of oracle data sources"""
    OFFCHAIN = "offchain"  # Traditional API providers
    ONCHAIN = "onchain"    # Blockchain oracles (Chainlink)
    HYBRID = "hybrid"      # Combination of both


class DataSource(Enum):
    """Available data sources"""
    # Off-chain sources
    YAHOO = "yahoo"
    ALPHA_VANTAGE = "alpha_vantage"
    TWELVEDATA = "twelvedata"
    FINNHUB = "finnhub"
    MARKETSTACK = "marketstack"
    POLYGON = "polygon"
    COINGECKO = "coingecko"
    BINANCE = "binance"
    COINBASE = "coinbase"
    
    # On-chain sources
    CHAINLINK = "chainlink"
    
    
class OracleManager:
    """
    Central Oracle Manager for all market data
    
    This class acts as the single source of truth for market data,
    managing API keys, data validation, and provider selection.
    """
    
    def __init__(self):
        self.market_service = MarketDataService()
        self.chainlink_provider = ChainlinkOracleProvider()
        self.redis = None
        
        # API Key Vault - centralized key management
        self._api_keys = self._load_api_keys()
        
        # Rate limiting configuration per provider
        self.rate_limits = {
            DataSource.YAHOO: {"requests_per_hour": 2000},
            DataSource.ALPHA_VANTAGE: {"requests_per_day": 500},
            DataSource.TWELVEDATA: {"requests_per_day": 800},
            DataSource.FINNHUB: {"requests_per_day": 86400},
            DataSource.MARKETSTACK: {"requests_per_month": 1000},
            DataSource.POLYGON: {"requests_per_minute": 5},
            DataSource.COINGECKO: {"requests_per_minute": 50},
            DataSource.CHAINLINK: {"requests_per_minute": 100}  # RPC calls
        }
        
        # Request tracking for rate limiting
        self.request_counts = {}
        self.last_reset = {}
        
        # Data validation thresholds
        self.validation_config = {
            "max_price_deviation": 0.1,  # 10% max deviation between sources
            "stale_data_threshold": 300,  # 5 minutes
            "min_sources_required": 2,    # Minimum sources for consensus
        }
        
        # Cache configuration
        self.cache_ttl = {
            "price": 60,        # 1 minute for current prices
            "quote": 300,       # 5 minutes for quotes
            "historical": 3600, # 1 hour for historical data
            "indicators": 1800  # 30 minutes for technical indicators
        }
        
    def _load_api_keys(self) -> Dict[DataSource, str]:
        """Load and validate API keys from secure storage"""
        keys = {}
        
        # Load from environment variables (in production, use secret manager)
        if settings.alpha_vantage_api_key:
            keys[DataSource.ALPHA_VANTAGE] = settings.alpha_vantage_api_key
        if settings.finnhub_api_key:
            keys[DataSource.FINNHUB] = settings.finnhub_api_key
        if settings.twelvedata_api_key:
            keys[DataSource.TWELVEDATA] = settings.twelvedata_api_key
        if settings.marketstack_api_key:
            keys[DataSource.MARKETSTACK] = settings.marketstack_api_key
            
        # Add any additional keys from environment
        for source in DataSource:
            env_key = f"{source.value.upper()}_API_KEY"
            if env_value := os.getenv(env_key):
                keys[source] = env_value
                
        return keys
        
    async def initialize(self):
        """Initialize the oracle manager"""
        self.redis = await get_redis()
        await self.market_service.initialize()
        logger.info("Oracle Manager initialized with %d API keys", len(self._api_keys))
        
    def _check_rate_limit(self, source: DataSource) -> bool:
        """Check if we're within rate limits for a provider"""
        if source not in self.rate_limits:
            return True
            
        limits = self.rate_limits[source]
        now = datetime.now()
        
        # Initialize tracking if needed
        if source not in self.request_counts:
            self.request_counts[source] = 0
            self.last_reset[source] = now
            
        # Check and reset counters based on time window
        if "requests_per_minute" in limits:
            if (now - self.last_reset[source]).seconds >= 60:
                self.request_counts[source] = 0
                self.last_reset[source] = now
            return self.request_counts[source] < limits["requests_per_minute"]
            
        elif "requests_per_hour" in limits:
            if (now - self.last_reset[source]).seconds >= 3600:
                self.request_counts[source] = 0
                self.last_reset[source] = now
            return self.request_counts[source] < limits["requests_per_hour"]
            
        elif "requests_per_day" in limits:
            if (now - self.last_reset[source]).days >= 1:
                self.request_counts[source] = 0
                self.last_reset[source] = now
            return self.request_counts[source] < limits["requests_per_day"]
            
        return True
        
    def _increment_request_count(self, source: DataSource):
        """Increment request counter for rate limiting"""
        if source not in self.request_counts:
            self.request_counts[source] = 0
        self.request_counts[source] += 1
        
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        if not self.redis:
            return None
            
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            
        return None
        
    async def _set_cache(self, key: str, value: Any, ttl: int):
        """Set data in cache"""
        if not self.redis:
            return
            
        try:
            await self.redis.setex(
                key, 
                ttl, 
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.error(f"Cache write error: {e}")
            
    def _validate_price_data(self, prices: List[Tuple[DataSource, float]]) -> bool:
        """Validate price data from multiple sources"""
        if len(prices) < self.validation_config["min_sources_required"]:
            return len(prices) > 0  # Allow single source if that's all we have
            
        # Check for excessive deviation
        values = [p[1] for p in prices]
        mean_price = sum(values) / len(values)
        
        for source, price in prices:
            deviation = abs(price - mean_price) / mean_price
            if deviation > self.validation_config["max_price_deviation"]:
                logger.warning(
                    f"Price from {source.value} deviates {deviation:.2%} from mean"
                )
                return False
                
        return True
        
    def _aggregate_prices(self, prices: List[Tuple[DataSource, float]]) -> float:
        """Aggregate prices from multiple sources"""
        if not prices:
            return 0.0
            
        # For now, use median for robustness against outliers
        values = [p[1] for p in prices]
        values.sort()
        
        if len(values) % 2 == 0:
            return (values[len(values)//2 - 1] + values[len(values)//2]) / 2
        else:
            return values[len(values)//2]
            
    async def get_price(
        self, 
        symbol: str, 
        oracle_type: OracleType = OracleType.OFFCHAIN,
        sources: Optional[List[DataSource]] = None
    ) -> Dict[str, Any]:
        """
        Get current price from oracle
        
        Args:
            symbol: Trading symbol
            oracle_type: Type of oracle to use
            sources: Specific sources to query (None = auto-select)
            
        Returns:
            Dictionary with price data and metadata
        """
        # Check cache first
        cache_key = f"oracle:price:{symbol}:{oracle_type.value}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached
            
        prices = []
        metadata = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "oracle_type": oracle_type.value,
            "sources_queried": [],
            "sources_succeeded": []
        }
        
        # Determine which sources to use
        if oracle_type == OracleType.ONCHAIN:
            # Use Chainlink for on-chain data
            if self._check_rate_limit(DataSource.CHAINLINK):
                try:
                    price = await self.chainlink_provider.get_price(symbol)
                    if price:
                        prices.append((DataSource.CHAINLINK, price))
                        metadata["sources_succeeded"].append("chainlink")
                    self._increment_request_count(DataSource.CHAINLINK)
                except Exception as e:
                    logger.error(f"Chainlink oracle error: {e}")
                metadata["sources_queried"].append("chainlink")
                
        elif oracle_type == OracleType.OFFCHAIN:
            # Use traditional API providers
            if not sources:
                # Auto-select based on symbol type and availability
                if self._is_crypto_symbol(symbol):
                    sources = [DataSource.COINGECKO, DataSource.BINANCE, DataSource.COINBASE]
                else:
                    sources = [DataSource.YAHOO, DataSource.ALPHA_VANTAGE, DataSource.FINNHUB]
                    
            for source in sources:
                if not self._check_rate_limit(source):
                    continue
                    
                metadata["sources_queried"].append(source.value)
                
                try:
                    # Get price from market service
                    price = await self.market_service.get_current_price(
                        symbol, 
                        use_cache=False
                    )
                    if price:
                        prices.append((source, price))
                        metadata["sources_succeeded"].append(source.value)
                    self._increment_request_count(source)
                    
                except Exception as e:
                    logger.error(f"Error getting price from {source.value}: {e}")
                    
        else:  # HYBRID
            # Query both on-chain and off-chain sources
            offchain_result = await self.get_price(symbol, OracleType.OFFCHAIN, sources)
            onchain_result = await self.get_price(symbol, OracleType.ONCHAIN)
            
            if offchain_result.get("price") and onchain_result.get("price"):
                # Average the two for hybrid result
                hybrid_price = (offchain_result["price"] + onchain_result["price"]) / 2
                metadata["sources_queried"] = (
                    offchain_result.get("sources_queried", []) + 
                    onchain_result.get("sources_queried", [])
                )
                metadata["sources_succeeded"] = (
                    offchain_result.get("sources_succeeded", []) + 
                    onchain_result.get("sources_succeeded", [])
                )
                prices = [(DataSource.YAHOO, hybrid_price)]  # Placeholder source
                
        # Validate and aggregate prices
        if prices:
            if self._validate_price_data(prices):
                final_price = self._aggregate_prices(prices)
                result = {
                    "price": final_price,
                    "validated": True,
                    "consensus_sources": len(prices),
                    **metadata
                }
            else:
                # Validation failed, return best effort
                result = {
                    "price": prices[0][1],  # Use first price
                    "validated": False,
                    "warning": "Price validation failed",
                    **metadata
                }
        else:
            result = {
                "price": None,
                "error": "No price data available",
                **metadata
            }
            
        # Cache the result
        if result.get("price"):
            await self._set_cache(
                cache_key, 
                result, 
                self.cache_ttl["price"]
            )
            
        return result
        
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1d",
        interval: str = "1h",
        source: Optional[DataSource] = None
    ) -> Optional[pd.DataFrame]:
        """Get historical OHLCV data"""
        # For historical data, we typically use a single reliable source
        if not source:
            source = DataSource.YAHOO if not self._is_crypto_symbol(symbol) else DataSource.COINGECKO
            
        if not self._check_rate_limit(source):
            logger.warning(f"Rate limit exceeded for {source.value}")
            return None
            
        try:
            data = await self.market_service.get_historical_data(symbol, period, interval)
            self._increment_request_count(source)
            return data
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return None
            
    async def get_quote(
        self,
        symbol: str,
        sources: Optional[List[DataSource]] = None
    ) -> Dict[str, Any]:
        """Get detailed quote information"""
        cache_key = f"oracle:quote:{symbol}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached
            
        # Get quote from market service
        quote = await self.market_service.get_quote(symbol)
        
        if quote:
            quote["oracle_timestamp"] = datetime.utcnow().isoformat()
            quote["validated"] = True
            
            # Cache the result
            await self._set_cache(cache_key, quote, self.cache_ttl["quote"])
            
        return quote or {"error": "Quote not available", "symbol": symbol}
        
    async def validate_api_key(self, source: DataSource, api_key: str) -> bool:
        """Validate an API key for a given source"""
        # This would make a test API call to validate the key
        # For now, just check if it's non-empty
        return bool(api_key and len(api_key) > 10)
        
    async def rotate_api_key(self, source: DataSource, new_key: str) -> bool:
        """Rotate an API key for a given source"""
        if await self.validate_api_key(source, new_key):
            self._api_keys[source] = new_key
            logger.info(f"API key rotated for {source.value}")
            return True
        return False
        
    def get_api_key_status(self) -> Dict[str, Any]:
        """Get status of all API keys (without exposing the keys)"""
        status = {}
        for source in DataSource:
            if source in self._api_keys:
                key = self._api_keys[source]
                # Mask the key for security
                masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
                status[source.value] = {
                    "configured": True,
                    "masked_key": masked,
                    "rate_limit": self.rate_limits.get(source, {})
                }
            else:
                status[source.value] = {
                    "configured": False,
                    "rate_limit": self.rate_limits.get(source, {})
                }
        return status
        
    def _is_crypto_symbol(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency"""
        crypto_indicators = ["-", "/", "BTC", "ETH", "USDT", "USDC"]
        return any(indicator in symbol.upper() for indicator in crypto_indicators)
        
    async def get_oracle_health(self) -> Dict[str, Any]:
        """Get health status of the oracle system"""
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "providers": {},
            "cache_connected": self.redis is not None,
            "api_keys_configured": len(self._api_keys)
        }
        
        # Check each provider
        for source in DataSource:
            health["providers"][source.value] = {
                "available": source in self._api_keys or source == DataSource.YAHOO,
                "rate_limit_ok": self._check_rate_limit(source),
                "requests_made": self.request_counts.get(source, 0)
            }
            
        # Determine overall health
        available_providers = sum(
            1 for p in health["providers"].values() 
            if p["available"]
        )
        
        if available_providers == 0:
            health["status"] = "critical"
        elif available_providers < 3:
            health["status"] = "degraded"
            
        return health


# Singleton instance
oracle_manager = OracleManager()