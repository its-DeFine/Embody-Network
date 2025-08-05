"""
DEX Trading API endpoints
Provides access to decentralized exchange trading
"""

from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
import logging

from ..dependencies import get_current_user
# DEX trading temporarily disabled due to web3 dependency conflicts
# from ..core.trading.dex_trading import dex_trading_engine
dex_trading_engine = None
from ..infrastructure.database.models import TradeType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/dex",
    tags=["dex"],
    dependencies=[Depends(get_current_user)]
)


class DEXTradeRequest(BaseModel):
    """DEX trade request"""
    symbol: str
    action: str  # "buy" or "sell"
    amount: float
    preferred_chain: Optional[str] = None
    slippage: Optional[float] = 0.5


@router.get("/supported-tokens")
async def get_supported_tokens():
    """Get list of tokens supported for DEX trading"""
    
    tokens = dex_trading_engine.get_supported_tokens()
    
    return {
        "tokens": tokens,
        "count": len(tokens),
        "chains": ["ethereum", "bsc", "polygon", "arbitrum", "avalanche"]
    }


@router.get("/price/{symbol}")
async def get_dex_price(
    symbol: str,
    detailed: bool = Query(False, description="Include price breakdown by DEX")
):
    """Get token price across DEXs"""
    
    symbol = symbol.upper()
    
    if detailed:
        # Get prices from all DEXs
        prices = await dex_trading_engine.aggregator.get_dex_prices(symbol)
        
        if not prices:
            raise HTTPException(status_code=404, detail=f"Token {symbol} not found on DEXs")
            
        # Calculate average and find best prices
        all_prices = [p["price"] for p in prices.values()]
        avg_price = sum(all_prices) / len(all_prices)
        
        return {
            "symbol": symbol,
            "average_price": avg_price,
            "best_buy": min(prices.items(), key=lambda x: x[1]["price"]),
            "best_sell": max(prices.items(), key=lambda x: x[1]["price"]),
            "all_prices": prices
        }
    else:
        # Just get average price
        price = await dex_trading_engine.get_token_price(symbol)
        
        if price is None:
            raise HTTPException(status_code=404, detail=f"Token {symbol} not found")
            
        return {
            "symbol": symbol,
            "price": price
        }


@router.post("/trade")
async def execute_dex_trade(trade_request: DEXTradeRequest):
    """Execute a DEX trade"""
    
    try:
        # Validate action
        if trade_request.action.lower() not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="Action must be 'buy' or 'sell'")
            
        action = TradeType.BUY if trade_request.action.lower() == "buy" else TradeType.SELL
        
        # Execute trade
        trade = await dex_trading_engine.execute_trade(
            symbol=trade_request.symbol.upper(),
            action=action,
            amount=Decimal(str(trade_request.amount)),
            preferred_chain=trade_request.preferred_chain
        )
        
        if trade:
            return {
                "status": "success",
                "trade": {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "action": trade.action.value,
                    "quantity": float(trade.quantity),
                    "price": float(trade.price),
                    "total": float(trade.quantity * trade.price),
                    "exchange": trade.exchange,
                    "timestamp": trade.timestamp.isoformat()
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Trade execution failed")
            
    except Exception as e:
        logger.error(f"DEX trade error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/arbitrage/scan")
async def scan_arbitrage_opportunities():
    """Scan for arbitrage opportunities across DEXs"""
    
    opportunities = await dex_trading_engine.scan_arbitrage()
    
    # Sort by profit potential
    opportunities.sort(key=lambda x: x["profit_pct"], reverse=True)
    
    return {
        "opportunities": opportunities[:10],  # Top 10
        "total_found": len(opportunities),
        "best_opportunity": opportunities[0] if opportunities else None
    }


@router.get("/chains")
async def get_supported_chains():
    """Get supported blockchain networks"""
    
    chains = []
    for chain_name, config in dex_trading_engine.aggregator.chains.items():
        chains.append({
            "name": chain_name,
            "chain_id": config["chain_id"],
            "native_token": config["native_token"],
            "dexs": list(config["routers"].keys()),
            "explorer": config["explorer"]
        })
        
    return {"chains": chains}


@router.get("/liquidity/{symbol}")
async def get_token_liquidity(symbol: str):
    """Get liquidity information for a token across DEXs"""
    
    symbol = symbol.upper()
    
    # Get prices which indicates liquidity presence
    prices = await dex_trading_engine.aggregator.get_dex_prices(symbol)
    
    if not prices:
        raise HTTPException(status_code=404, detail=f"No liquidity found for {symbol}")
        
    liquidity_info = []
    
    for dex_key, info in prices.items():
        liquidity_info.append({
            "dex": dex_key,
            "chain": info["chain"],
            "has_liquidity": True,
            "price": info["price"],
            "router": info["router"],
            "token_address": info["token_address"]
        })
        
    return {
        "symbol": symbol,
        "liquidity_sources": liquidity_info,
        "total_sources": len(liquidity_info)
    }


@router.post("/simulate")
async def simulate_dex_trade(trade_request: DEXTradeRequest):
    """Simulate a DEX trade without executing"""
    
    symbol = trade_request.symbol.upper()
    
    # Get current prices
    prices = await dex_trading_engine.aggregator.get_dex_prices(symbol)
    
    if not prices:
        raise HTTPException(status_code=404, detail=f"Token {symbol} not found")
        
    # Find best execution
    if trade_request.action.lower() == "buy":
        best_dex = min(prices.items(), key=lambda x: x[1]["price"])
        total_cost = trade_request.amount * best_dex[1]["price"]
        
        return {
            "simulation": {
                "action": "buy",
                "token": symbol,
                "amount": trade_request.amount,
                "best_dex": best_dex[0],
                "price": best_dex[1]["price"],
                "total_cost": total_cost,
                "chain": best_dex[1]["chain"],
                "router": best_dex[1]["router"]
            }
        }
    else:
        best_dex = max(prices.items(), key=lambda x: x[1]["price"])
        total_received = trade_request.amount * best_dex[1]["price"]
        
        return {
            "simulation": {
                "action": "sell",
                "token": symbol,
                "amount": trade_request.amount,
                "best_dex": best_dex[0],
                "price": best_dex[1]["price"],
                "total_received": total_received,
                "chain": best_dex[1]["chain"],
                "router": best_dex[1]["router"]
            }
        }


@router.get("/gas-prices")
async def get_gas_prices():
    """Get current gas prices for supported chains"""
    
    gas_prices = {}
    
    for chain_name, w3 in dex_trading_engine.aggregator.web3_connections.items():
        try:
            gas_price = w3.eth.gas_price
            gas_prices[chain_name] = {
                "gas_price_wei": gas_price,
                "gas_price_gwei": gas_price / 10**9,
                "estimated_swap_cost": gas_price * 200000 / 10**18  # ~200k gas for swap
            }
        except:
            gas_prices[chain_name] = {"error": "Unable to fetch gas price"}
            
    return gas_prices