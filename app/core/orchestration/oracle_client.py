"""
Oracle Client for Orchestrators and Agents

This module provides a client for orchestrators and agents to request
market data from the central Oracle Manager instead of directly accessing APIs.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
import pandas as pd

from ...config import settings

logger = logging.getLogger(__name__)


class OracleClient:
    """
    Client for accessing market data through the central Oracle Manager
    
    This client is used by orchestrators and agents to request market data
    without needing direct access to market data API keys.
    """
    
    def __init__(self):
        # Get Manager Oracle URL from environment
        self.oracle_url = os.getenv(
            "MANAGER_ORACLE_URL",
            f"{os.getenv('MANAGER_URL', 'http://localhost:8000')}/api/v1/oracle"
        )
        
        # Authentication
        self.auth_token = None
        self.jwt_secret = settings.jwt_secret
        
        # Client settings
        self.timeout = int(os.getenv("ORACLE_REQUEST_TIMEOUT", "30"))
        self.retry_count = int(os.getenv("ORACLE_RETRY_COUNT", "3"))
        self.use_central_oracle = os.getenv("USE_CENTRAL_ORACLE", "true").lower() == "true"
        
        # Local cache settings
        self.cache_enabled = os.getenv("ORACLE_CACHE_LOCAL", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("ORACLE_LOCAL_CACHE_TTL", "30"))
        self._cache = {}
        self._cache_timestamps = {}
        
        # HTTP client
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
        logger.info(f"Oracle Client initialized - URL: {self.oracle_url}, Use Central: {self.use_central_oracle}")
        
    async def authenticate(self, username: str = "orchestrator", password: Optional[str] = None):
        """Authenticate with the Manager to get access token"""
        if not password:
            password = settings.admin_password
            
        try:
            response = await self.client.post(
                f"{self.oracle_url.replace('/oracle', '/auth')}/login",
                data={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                logger.info("Successfully authenticated with Oracle Manager")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
            
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
        
    def _check_cache(self, key: str) -> Optional[Any]:
        """Check local cache for data"""
        if not self.cache_enabled:
            return None
            
        if key in self._cache:
            timestamp = self._cache_timestamps.get(key)
            if timestamp:
                age = (datetime.now() - timestamp).seconds
                if age < self.cache_ttl:
                    logger.debug(f"Cache hit for {key} (age: {age}s)")
                    return self._cache[key]
                    
        return None
        
    def _update_cache(self, key: str, value: Any):
        """Update local cache"""
        if self.cache_enabled:
            self._cache[key] = value
            self._cache_timestamps[key] = datetime.now()
            
    async def get_price(
        self, 
        symbol: str,
        oracle_type: str = "offchain",
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get current price from Oracle Manager
        
        Args:
            symbol: Trading symbol
            oracle_type: Type of oracle (offchain/onchain/hybrid)
            sources: Optional list of specific sources to use
            
        Returns:
            Price data from Oracle Manager
        """
        if not self.use_central_oracle:
            logger.warning("Central Oracle disabled - no market data available")
            return {"error": "Central Oracle disabled", "symbol": symbol}
            
        # Check cache
        cache_key = f"price:{symbol}:{oracle_type}"
        cached = self._check_cache(cache_key)
        if cached:
            return cached
            
        # Build request
        params = {"oracle_type": oracle_type}
        if sources:
            params["sources"] = ",".join(sources)
            
        # Retry logic
        for attempt in range(self.retry_count):
            try:
                response = await self.client.get(
                    f"{self.oracle_url}/price/{symbol}",
                    params=params,
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._update_cache(cache_key, data)
                    return data
                elif response.status_code == 401:
                    # Try to re-authenticate
                    if await self.authenticate():
                        continue
                    else:
                        return {"error": "Authentication failed", "symbol": symbol}
                else:
                    logger.warning(f"Price request failed: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error getting price (attempt {attempt + 1}): {e}")
                
            if attempt < self.retry_count - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        return {"error": "Failed to get price from Oracle", "symbol": symbol}
        
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get detailed quote from Oracle Manager"""
        if not self.use_central_oracle:
            return {"error": "Central Oracle disabled", "symbol": symbol}
            
        # Check cache
        cache_key = f"quote:{symbol}"
        cached = self._check_cache(cache_key)
        if cached:
            return cached
            
        try:
            response = await self.client.get(
                f"{self.oracle_url}/quote/{symbol}",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                self._update_cache(cache_key, data)
                return data
            else:
                return {"error": f"Quote request failed: {response.status_code}", "symbol": symbol}
                
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return {"error": str(e), "symbol": symbol}
            
    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1d",
        interval: str = "1h"
    ) -> Optional[pd.DataFrame]:
        """Get historical data from Oracle Manager"""
        if not self.use_central_oracle:
            logger.warning("Central Oracle disabled - no historical data available")
            return None
            
        try:
            response = await self.client.get(
                f"{self.oracle_url}/historical/{symbol}",
                params={"period": period, "interval": interval},
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                # Convert to DataFrame
                df = pd.DataFrame(data["data"])
                if "index" in data:
                    df.index = pd.to_datetime(data["index"])
                return df
            else:
                logger.error(f"Historical data request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return None
            
    async def get_oracle_health(self) -> Dict[str, Any]:
        """Check Oracle Manager health status"""
        try:
            response = await self.client.get(
                f"{self.oracle_url}/health",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unknown", "error": f"Status code: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error checking oracle health: {e}")
            return {"status": "error", "error": str(e)}
            
    async def validate_prices(
        self,
        symbol: str,
        prices: List[float],
        sources: List[str]
    ) -> Dict[str, Any]:
        """Validate prices through Oracle Manager"""
        try:
            response = await self.client.post(
                f"{self.oracle_url}/validate",
                json={
                    "symbol": symbol,
                    "prices": prices,
                    "sources": sources
                },
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Validation failed: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error validating prices: {e}")
            return {"error": str(e)}
            
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        

# Singleton instance for orchestrators/agents
oracle_client = OracleClient()