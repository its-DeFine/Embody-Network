"""
Market Data API endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from ..dependencies import get_current_user
from ..core.market.market_data import market_data_service

router = APIRouter(
    prefix="/api/v1/market",
    tags=["market"],
    dependencies=[Depends(get_current_user)]
)


class PriceRequest(BaseModel):
    """Request for current price"""
    symbol: str
    use_cache: bool = True


class HistoricalDataRequest(BaseModel):
    """Request for historical data"""
    symbol: str
    period: str = "1d"  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    interval: str = "1h"  # 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo


class TechnicalIndicatorsRequest(BaseModel):
    """Request for technical indicators"""
    symbol: str
    period: str = "1d"


@router.get("/price/{symbol}")
async def get_current_price(symbol: str, use_cache: bool = Query(True)):
    """Get current price for a symbol"""
    price = await market_data_service.get_current_price(symbol, use_cache)
    
    if price is None:
        raise HTTPException(status_code=404, detail=f"Price not found for {symbol}")
        
    return {
        "symbol": symbol,
        "price": price,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/prices")
async def get_multiple_prices(symbols: List[str]):
    """Get current prices for multiple symbols"""
    results = {}
    
    for symbol in symbols:
        price = await market_data_service.get_current_price(symbol)
        results[symbol] = price
        
    return {
        "prices": results,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get detailed quote for a symbol"""
    quote = await market_data_service.get_quote(symbol)
    
    if quote is None:
        raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")
        
    return quote


@router.post("/quotes")
async def get_multiple_quotes(symbols: List[str]):
    """Get quotes for multiple symbols"""
    quotes = await market_data_service.get_market_summary(symbols)
    
    return {
        "quotes": quotes,
        "count": len(quotes),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/historical")
async def get_historical_data(request: HistoricalDataRequest):
    """Get historical OHLCV data"""
    data = await market_data_service.get_historical_data(
        request.symbol,
        request.period,
        request.interval
    )
    
    if data is None:
        raise HTTPException(status_code=404, detail=f"Historical data not found for {request.symbol}")
        
    # Convert DataFrame to JSON-friendly format
    return {
        "symbol": request.symbol,
        "period": request.period,
        "interval": request.interval,
        "data": data.reset_index().to_dict(orient='records'),
        "count": len(data),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/indicators")
async def get_technical_indicators(request: TechnicalIndicatorsRequest):
    """Get technical indicators for a symbol"""
    indicators = await market_data_service.get_technical_indicators(
        request.symbol,
        request.period
    )
    
    if not indicators:
        raise HTTPException(status_code=404, detail=f"Could not calculate indicators for {request.symbol}")
        
    return {
        "symbol": request.symbol,
        "indicators": indicators,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/summary")
async def get_market_summary():
    """Get market summary for major indices and popular stocks"""
    # Define symbols to track
    indices = ["^GSPC", "^DJI", "^IXIC", "^VIX"]  # S&P 500, Dow, Nasdaq, VIX
    popular_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM"]
    
    # Get quotes for all symbols
    all_symbols = indices + popular_stocks
    quotes = await market_data_service.get_market_summary(all_symbols)
    
    # Separate indices and stocks
    index_quotes = [q for q in quotes if q['symbol'] in indices]
    stock_quotes = [q for q in quotes if q['symbol'] in popular_stocks]
    
    # Calculate market statistics
    total_market_cap = sum(q.get('marketCap', 0) for q in stock_quotes if q.get('marketCap'))
    
    # Find top gainers and losers
    sorted_by_change = sorted(
        [q for q in stock_quotes if q.get('changePercent')],
        key=lambda x: float(str(x.get('changePercent', '0')).replace('%', '')),
        reverse=True
    )
    
    top_gainers = sorted_by_change[:3] if len(sorted_by_change) >= 3 else sorted_by_change
    top_losers = sorted_by_change[-3:] if len(sorted_by_change) >= 3 else []
    
    return {
        "indices": index_quotes,
        "popular_stocks": stock_quotes,
        "market_stats": {
            "total_market_cap": total_market_cap,
            "stocks_up": len([q for q in stock_quotes if float(str(q.get('changePercent', '0')).replace('%', '')) > 0]),
            "stocks_down": len([q for q in stock_quotes if float(str(q.get('changePercent', '0')).replace('%', '')) < 0]),
            "stocks_unchanged": len([q for q in stock_quotes if float(str(q.get('changePercent', '0')).replace('%', '')) == 0])
        },
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/search")
async def search_symbols(query: str = Query(..., min_length=1)):
    """Search for symbols (basic implementation)"""
    # For now, return common symbols that match
    common_symbols = {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "AMZN": "Amazon.com Inc.",
        "TSLA": "Tesla Inc.",
        "META": "Meta Platforms Inc.",
        "NVDA": "NVIDIA Corporation",
        "JPM": "JPMorgan Chase & Co.",
        "V": "Visa Inc.",
        "JNJ": "Johnson & Johnson",
        "WMT": "Walmart Inc.",
        "PG": "Procter & Gamble Co.",
        "UNH": "UnitedHealth Group Inc.",
        "HD": "Home Depot Inc.",
        "DIS": "Walt Disney Co.",
        "MA": "Mastercard Inc.",
        "PYPL": "PayPal Holdings Inc.",
        "BAC": "Bank of America Corp.",
        "NFLX": "Netflix Inc.",
        "ADBE": "Adobe Inc."
    }
    
    # Filter symbols that match the query
    query_upper = query.upper()
    matches = []
    
    for symbol, name in common_symbols.items():
        if query_upper in symbol or query.lower() in name.lower():
            matches.append({
                "symbol": symbol,
                "name": name
            })
            
    return {
        "query": query,
        "matches": matches[:10],  # Limit to 10 results
        "count": len(matches)
    }