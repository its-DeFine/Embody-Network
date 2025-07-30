"""
OpenBB Adapter Service for AutoGen Platform
Provides unified access to financial data through OpenBB
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
from openbb import obb
import aio_pika
from dotenv import load_dotenv

from models.market_data import MarketDataRequest, MarketDataResponse
from models.analysis import AnalysisRequest, AnalysisResponse
from models.portfolio import PortfolioRequest, PortfolioResponse
from handlers.market_events import MarketDataHandler
from cache.redis_cache import RedisCache

# Load environment variables
load_dotenv()

# Global instances
redis_cache: Optional[RedisCache] = None
market_handler: Optional[MarketDataHandler] = None
openbb_service: Optional['OpenBBService'] = None


class OpenBBService:
    """Main service class for OpenBB operations"""
    
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default
        self.initialized = False
        
    async def startup(self):
        """Initialize OpenBB and connections"""
        try:
            # Initialize OpenBB with API key if provided
            api_key = os.getenv("OPENBB_API_KEY")
            if api_key:
                obb.account.login(api_key=api_key)
            
            # Connect to Redis
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            self.redis_client = await redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            await self.redis_client.ping()
            
            self.initialized = True
            print("OpenBB Service initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize OpenBB Service: {e}")
            raise
    
    async def shutdown(self):
        """Clean up connections"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get_market_data(
        self, 
        symbol: str, 
        interval: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get historical market data with caching"""
        cache_key = f"market:{symbol}:{interval}:{start_date}:{end_date}"
        
        # Check cache
        cached = await self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        try:
            # Fetch from OpenBB
            data = obb.equity.price.historical(
                symbol=symbol,
                interval=interval,
                start_date=start_date,
                end_date=end_date
            )
            
            # Convert to dict
            result = {
                "symbol": symbol,
                "interval": interval,
                "data": data.to_dict() if hasattr(data, 'to_dict') else str(data),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache result
            await self.redis_client.setex(
                cache_key, 
                self.cache_ttl,
                json.dumps(result)
            )
            
            return result
            
        except Exception as e:
            print(f"Error fetching market data: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_technical_analysis(
        self,
        symbol: str,
        indicators: List[str]
    ) -> Dict[str, Any]:
        """Get technical analysis indicators"""
        cache_key = f"analysis:{symbol}:{':'.join(sorted(indicators))}"
        
        # Check cache
        cached = await self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        try:
            # First get price data
            price_data = obb.equity.price.historical(symbol=symbol, interval="1d")
            
            results = {"symbol": symbol, "indicators": {}}
            
            # Calculate each indicator
            for indicator in indicators:
                if indicator == "rsi":
                    results["indicators"]["rsi"] = obb.technical.rsi(price_data).to_dict()
                elif indicator == "macd":
                    results["indicators"]["macd"] = obb.technical.macd(price_data).to_dict()
                elif indicator == "sma":
                    results["indicators"]["sma"] = obb.technical.sma(price_data, length=20).to_dict()
                elif indicator == "ema":
                    results["indicators"]["ema"] = obb.technical.ema(price_data, length=20).to_dict()
                elif indicator == "bollinger":
                    results["indicators"]["bollinger"] = obb.technical.bbands(price_data).to_dict()
                else:
                    results["indicators"][indicator] = f"Indicator {indicator} not implemented"
            
            results["timestamp"] = datetime.utcnow().isoformat()
            
            # Cache result
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(results)
            )
            
            return results
            
        except Exception as e:
            print(f"Error calculating technical analysis: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Get fundamental data for a symbol"""
        cache_key = f"fundamentals:{symbol}"
        cache_ttl = 3600  # 1 hour for fundamentals
        
        # Check cache
        cached = await self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        try:
            # Get various fundamental data
            overview = obb.equity.fundamental.overview(symbol)
            income = obb.equity.fundamental.income(symbol, period="annual", limit=1)
            balance = obb.equity.fundamental.balance(symbol, period="annual", limit=1)
            ratios = obb.equity.fundamental.ratios(symbol)
            
            result = {
                "symbol": symbol,
                "overview": overview.to_dict() if hasattr(overview, 'to_dict') else str(overview),
                "income_statement": income.to_dict() if hasattr(income, 'to_dict') else str(income),
                "balance_sheet": balance.to_dict() if hasattr(balance, 'to_dict') else str(balance),
                "ratios": ratios.to_dict() if hasattr(ratios, 'to_dict') else str(ratios),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache result
            await self.redis_client.setex(
                cache_key,
                cache_ttl,
                json.dumps(result)
            )
            
            return result
            
        except Exception as e:
            print(f"Error fetching fundamentals: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get news and sentiment analysis"""
        cache_key = f"sentiment:{symbol}"
        cache_ttl = 600  # 10 minutes for news
        
        # Check cache
        cached = await self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        try:
            # Get news
            news = obb.news.equity(symbol=symbol, limit=10)
            
            result = {
                "symbol": symbol,
                "news": news.to_dict() if hasattr(news, 'to_dict') else str(news),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache result
            await self.redis_client.setex(
                cache_key,
                cache_ttl,
                json.dumps(result)
            )
            
            return result
            
        except Exception as e:
            print(f"Error fetching news sentiment: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global openbb_service, redis_cache, market_handler
    
    # Startup
    print("Starting OpenBB Adapter Service...")
    
    # Initialize services
    openbb_service = OpenBBService()
    await openbb_service.startup()
    
    # Initialize cache
    redis_cache = RedisCache(openbb_service.redis_client)
    
    # Initialize RabbitMQ handler
    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    market_handler = MarketDataHandler(openbb_service, rabbitmq_url)
    await market_handler.connect()
    
    yield
    
    # Shutdown
    print("Shutting down OpenBB Adapter Service...")
    if market_handler:
        await market_handler.disconnect()
    if openbb_service:
        await openbb_service.shutdown()


# Create FastAPI app
app = FastAPI(
    title="OpenBB Adapter Service",
    description="Financial data service powered by OpenBB",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "openbb-adapter",
        "timestamp": datetime.utcnow().isoformat(),
        "initialized": openbb_service.initialized if openbb_service else False
    }


# Market data endpoints
@app.post("/market/data", response_model=MarketDataResponse)
async def get_market_data(request: MarketDataRequest):
    """Get market data for a symbol"""
    if not openbb_service or not openbb_service.initialized:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = await openbb_service.get_market_data(
        symbol=request.symbol,
        interval=request.interval,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    return MarketDataResponse(**result)


@app.post("/analysis/technical", response_model=AnalysisResponse)
async def get_technical_analysis(request: AnalysisRequest):
    """Get technical analysis indicators"""
    if not openbb_service or not openbb_service.initialized:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    result = await openbb_service.get_technical_analysis(
        symbol=request.symbol,
        indicators=request.indicators
    )
    
    return AnalysisResponse(**result)


@app.get("/fundamentals/{symbol}")
async def get_fundamentals(symbol: str):
    """Get fundamental data for a symbol"""
    if not openbb_service or not openbb_service.initialized:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await openbb_service.get_fundamentals(symbol)


@app.get("/sentiment/{symbol}")
async def get_sentiment(symbol: str):
    """Get news and sentiment for a symbol"""
    if not openbb_service or not openbb_service.initialized:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await openbb_service.get_news_sentiment(symbol)


# WebSocket endpoint for real-time data
@app.websocket("/ws/prices")
async def websocket_prices(websocket):
    """WebSocket endpoint for real-time price updates"""
    await websocket.accept()
    try:
        while True:
            # Receive symbols to track
            data = await websocket.receive_json()
            symbols = data.get("symbols", [])
            
            # Send price updates
            for symbol in symbols:
                try:
                    quote = obb.equity.price.quote(symbol)
                    await websocket.send_json({
                        "type": "price_update",
                        "symbol": symbol,
                        "data": quote.to_dict() if hasattr(quote, 'to_dict') else str(quote),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "symbol": symbol,
                        "error": str(e)
                    })
            
            await asyncio.sleep(1)  # Update every second
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)