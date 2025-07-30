"""Simple OpenBB client for financial data"""
import os
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OpenBBClient:
    """Client for OpenBB financial data"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("OPENBB_URL", "http://localhost:8003")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for a symbol"""
        try:
            response = await self.client.get(f"/api/v1/market/{symbol}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return {
                "symbol": symbol,
                "price": "N/A",
                "change_24h": "N/A",
                "volume": "N/A",
                "error": str(e)
            }
    
    async def get_technical_indicators(self, symbol: str, indicators: list) -> Dict[str, Any]:
        """Get technical indicators for a symbol"""
        try:
            response = await self.client.post(
                f"/api/v1/analysis/technical",
                json={"symbol": symbol, "indicators": indicators}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get indicators for {symbol}: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()

# Global instance
_openbb_client: Optional[OpenBBClient] = None

async def get_openbb_client() -> OpenBBClient:
    """Get or create OpenBB client"""
    global _openbb_client
    if not _openbb_client:
        _openbb_client = OpenBBClient()
    return _openbb_client