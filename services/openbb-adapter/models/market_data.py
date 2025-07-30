"""
Market data models for OpenBB Adapter
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MarketDataRequest(BaseModel):
    """Request model for market data"""
    symbol: str = Field(..., description="Stock/crypto symbol")
    interval: str = Field(default="1d", description="Time interval (1m, 5m, 1h, 1d)")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "interval": "1d",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        }


class MarketDataResponse(BaseModel):
    """Response model for market data"""
    symbol: str
    interval: str
    data: Dict[str, Any]
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "interval": "1d",
                "data": {
                    "open": [150.0, 151.0],
                    "high": [152.0, 153.0],
                    "low": [149.0, 150.0],
                    "close": [151.0, 152.0],
                    "volume": [1000000, 1100000]
                },
                "timestamp": "2024-01-15T10:00:00Z"
            }
        }


class QuoteRequest(BaseModel):
    """Request model for real-time quote"""
    symbols: List[str] = Field(..., description="List of symbols to get quotes for")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["AAPL", "GOOGL", "MSFT"]
            }
        }


class QuoteResponse(BaseModel):
    """Response model for real-time quote"""
    quotes: Dict[str, Dict[str, Any]]
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "quotes": {
                    "AAPL": {
                        "price": 150.25,
                        "change": 1.25,
                        "change_percent": 0.84,
                        "volume": 50000000
                    }
                },
                "timestamp": "2024-01-15T10:00:00Z"
            }
        }