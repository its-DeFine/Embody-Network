"""
Oracle API Endpoints

This module provides REST API endpoints for the Oracle Manager,
allowing centralized access to market data through the manager as the central oracle.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel, Field
from datetime import datetime

from ...core.oracle import oracle_manager, OracleManager
from ...core.oracle.oracle_manager import OracleType, DataSource
from ...auth import get_current_user

router = APIRouter(prefix="/oracle", tags=["oracle"])


class PriceRequest(BaseModel):
    """Request model for price data"""
    symbol: str = Field(..., description="Trading symbol")
    oracle_type: OracleType = Field(OracleType.OFFCHAIN, description="Type of oracle to use")
    sources: Optional[List[str]] = Field(None, description="Specific sources to query")
    

class PriceResponse(BaseModel):
    """Response model for price data"""
    symbol: str
    price: Optional[float]
    timestamp: str
    oracle_type: str
    validated: bool
    consensus_sources: Optional[int]
    sources_queried: List[str]
    sources_succeeded: List[str]
    from_cache: bool = False
    warning: Optional[str] = None
    error: Optional[str] = None
    

class QuoteResponse(BaseModel):
    """Response model for quote data"""
    symbol: str
    price: Optional[float]
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    volume: Optional[int]
    change: Optional[float]
    changePercent: Optional[float]
    timestamp: str
    oracle_timestamp: Optional[str]
    validated: bool = False
    from_cache: bool = False
    error: Optional[str] = None
    

class HealthResponse(BaseModel):
    """Response model for oracle health"""
    status: str
    timestamp: str
    providers: Dict[str, Dict[str, Any]]
    cache_connected: bool
    api_keys_configured: int
    

class ApiKeyStatus(BaseModel):
    """Response model for API key status"""
    source: str
    configured: bool
    masked_key: Optional[str]
    rate_limit: Dict[str, int]


@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_price(
    symbol: str,
    oracle_type: OracleType = Query(OracleType.OFFCHAIN),
    sources: Optional[str] = Query(None, description="Comma-separated list of sources"),
    current_user: dict = Depends(get_current_user)
) -> PriceResponse:
    """
    Get current price for a symbol from the oracle
    
    The manager acts as the central oracle, aggregating and validating
    data from multiple sources.
    """
    # Parse sources if provided
    source_list = None
    if sources:
        try:
            source_list = [DataSource[s.upper()] for s in sources.split(",")]
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source: {e}"
            )
    
    # Get price from oracle
    result = await oracle_manager.get_price(symbol, oracle_type, source_list)
    
    return PriceResponse(**result)
    

@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str,
    sources: Optional[str] = Query(None, description="Comma-separated list of sources"),
    current_user: dict = Depends(get_current_user)
) -> QuoteResponse:
    """
    Get detailed quote information for a symbol
    
    Returns comprehensive quote data including OHLCV and change metrics.
    """
    # Parse sources if provided
    source_list = None
    if sources:
        try:
            source_list = [DataSource[s.upper()] for s in sources.split(",")]
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source: {e}"
            )
    
    # Get quote from oracle
    result = await oracle_manager.get_quote(symbol, source_list)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return QuoteResponse(**result)
    

@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    period: str = Query("1d", description="Time period (1d, 5d, 1mo, 3mo, 1y)"),
    interval: str = Query("1h", description="Data interval (1m, 5m, 15m, 1h, 1d)"),
    source: Optional[str] = Query(None, description="Specific source to use"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get historical OHLCV data for a symbol
    
    Returns historical price data in standard OHLCV format.
    """
    # Parse source if provided
    data_source = None
    if source:
        try:
            data_source = DataSource[source.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source: {source}"
            )
    
    # Get historical data
    data = await oracle_manager.get_historical_data(symbol, period, interval, data_source)
    
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No historical data available for {symbol}"
        )
    
    # Convert DataFrame to JSON-serializable format
    return {
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "data": data.to_dict(orient="records"),
        "index": data.index.tolist()
    }
    

@router.get("/health", response_model=HealthResponse)
async def get_oracle_health(
    current_user: dict = Depends(get_current_user)
) -> HealthResponse:
    """
    Get health status of the oracle system
    
    Returns detailed health information about all data providers
    and the overall oracle system status.
    """
    health = await oracle_manager.get_oracle_health()
    return HealthResponse(**health)
    

@router.get("/api-keys/status", response_model=List[ApiKeyStatus])
async def get_api_key_status(
    current_user: dict = Depends(get_current_user)
) -> List[ApiKeyStatus]:
    """
    Get status of all configured API keys
    
    Returns masked API key information and rate limit status
    for all data sources. Keys are masked for security.
    """
    status = oracle_manager.get_api_key_status()
    
    return [
        ApiKeyStatus(
            source=source,
            configured=info["configured"],
            masked_key=info.get("masked_key"),
            rate_limit=info["rate_limit"]
        )
        for source, info in status.items()
    ]
    

@router.post("/api-keys/rotate")
async def rotate_api_key(
    source: str,
    new_key: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Rotate an API key for a specific data source
    
    Allows updating API keys without restarting the service.
    Only accessible to authenticated users.
    """
    try:
        data_source = DataSource[source.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source: {source}"
        )
    
    # Validate and rotate the key
    success = await oracle_manager.rotate_api_key(data_source, new_key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key or rotation failed"
        )
    
    return {
        "message": f"API key for {source} rotated successfully",
        "source": source,
        "timestamp": datetime.utcnow().isoformat()
    }
    

@router.post("/validate")
async def validate_price_data(
    symbol: str,
    prices: List[float],
    sources: List[str],
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate price data from multiple sources
    
    Checks for consistency and deviation between different price sources.
    This endpoint demonstrates the oracle's validation capabilities.
    """
    if len(prices) != len(sources):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of prices must match number of sources"
        )
    
    # Convert to internal format
    price_data = []
    for i, source_str in enumerate(sources):
        try:
            source = DataSource[source_str.upper()]
            price_data.append((source, prices[i]))
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source: {source_str}"
            )
    
    # Validate the data
    is_valid = oracle_manager._validate_price_data(price_data)
    aggregated = oracle_manager._aggregate_prices(price_data)
    
    return {
        "symbol": symbol,
        "valid": is_valid,
        "aggregated_price": aggregated,
        "prices": [{"source": s.value, "price": p} for s, p in price_data],
        "deviation_check": {
            "max_allowed": oracle_manager.validation_config["max_price_deviation"],
            "min_sources": oracle_manager.validation_config["min_sources_required"]
        }
    }