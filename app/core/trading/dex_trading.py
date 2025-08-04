"""
DEX Trading Integration
Supports decentralized exchange trading on multiple chains
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime
import json
from web3 import Web3
from web3.middleware import geth_poa_middleware
import aiohttp

from ...infrastructure.database.models import Trade, TradeType, OrderType, TradeStatus
from ...infrastructure.monitoring.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class ChainConfig:
    """Configuration for different blockchain networks"""
    
    ETHEREUM = {
        "chain_id": 1,
        "rpc": "https://eth.llamarpc.com",
        "explorer": "https://etherscan.io",
        "native_token": "ETH",
        "wrapped_native": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
        "routers": {
            "uniswap_v2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "sushiswap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
        }
    }
    
    BSC = {
        "chain_id": 56,
        "rpc": "https://bsc-dataseed.binance.org",
        "explorer": "https://bscscan.com",
        "native_token": "BNB",
        "wrapped_native": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
        "routers": {
            "pancakeswap_v2": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
            "pancakeswap_v3": "0x13f4EA83D0bd40E75C8222255bc855a974568Dd4"
        }
    }
    
    POLYGON = {
        "chain_id": 137,
        "rpc": "https://polygon-rpc.com",
        "explorer": "https://polygonscan.com",
        "native_token": "MATIC",
        "wrapped_native": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "routers": {
            "quickswap": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
            "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
        }
    }
    
    ARBITRUM = {
        "chain_id": 42161,
        "rpc": "https://arb1.arbitrum.io/rpc",
        "explorer": "https://arbiscan.io",
        "native_token": "ETH",
        "wrapped_native": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # WETH
        "routers": {
            "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
        }
    }
    
    AVALANCHE = {
        "chain_id": 43114,
        "rpc": "https://api.avax.network/ext/bc/C/rpc",
        "explorer": "https://snowtrace.io",
        "native_token": "AVAX",
        "wrapped_native": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",  # WAVAX
        "routers": {
            "traderjoe": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
            "pangolin": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106"
        }
    }


class TokenInfo:
    """Token information for trading"""
    
    def __init__(self, address: str, symbol: str, decimals: int, chain_id: int):
        self.address = Web3.to_checksum_address(address)
        self.symbol = symbol
        self.decimals = decimals
        self.chain_id = chain_id


class DEXAggregator:
    """
    Aggregates liquidity from multiple DEXs
    Supports multiple chains and finds best routes
    """
    
    def __init__(self):
        self.chains = {
            "ethereum": ChainConfig.ETHEREUM,
            "bsc": ChainConfig.BSC,
            "polygon": ChainConfig.POLYGON,
            "arbitrum": ChainConfig.ARBITRUM,
            "avalanche": ChainConfig.AVALANCHE
        }
        
        self.web3_connections = {}
        self.token_cache = {}
        self.price_cache = {}
        
        # Popular tokens per chain
        self.popular_tokens = {
            1: {  # Ethereum
                "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
                "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
                "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
                "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
                "CRV": "0xD533a949740bb3306d119CC777fa900bA034cd52",
                "SUSHI": "0x6B3595068778DD592e39A122f4f5a5cF09C90fE2",
                "COMP": "0xc00e94Cb662C3520282E6f5717214004A7f26888"
            },
            56: {  # BSC
                "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
                "USDT": "0x55d398326f99059fF775485246999027B3197955",
                "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
                "XVS": "0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63",
                "ALPACA": "0x8F0528cE5eF7B51152A59745bEfDD91D97091d2F"
            },
            137: {  # Polygon
                "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
                "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
                "DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
                "QUICK": "0x831753DD7087CaC61aB5644b308642cc1c33Dc13",
                "AAVE": "0xD6DF932A45C0f255f85145f286eA0b292B21C90B"
            }
        }
        
    async def initialize(self):
        """Initialize Web3 connections for all chains"""
        for chain_name, config in self.chains.items():
            try:
                w3 = Web3(Web3.HTTPProvider(config["rpc"]))
                
                # Add middleware for PoA chains
                if chain_name in ["bsc", "polygon"]:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                    
                if w3.is_connected():
                    self.web3_connections[chain_name] = w3
                    logger.info(f"Connected to {chain_name} chain")
                else:
                    logger.warning(f"Failed to connect to {chain_name}")
                    
            except Exception as e:
                logger.error(f"Error connecting to {chain_name}: {e}")
                
    async def get_token_price_1inch(self, chain: str, token_address: str) -> Optional[float]:
        """Get token price from 1inch API"""
        chain_id = self.chains[chain]["chain_id"]
        
        try:
            url = f"https://api.1inch.exchange/v5.0/{chain_id}/quote"
            
            # Get price in terms of USDC
            usdc_address = self.popular_tokens.get(chain_id, {}).get("USDC")
            if not usdc_address:
                return None
                
            params = {
                "fromTokenAddress": token_address,
                "toTokenAddress": usdc_address,
                "amount": str(10 ** 18)  # 1 token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Convert to price
                        to_amount = int(data["toTokenAmount"])
                        price = to_amount / (10 ** 6)  # USDC has 6 decimals
                        return price
                        
        except Exception as e:
            logger.error(f"Error getting price from 1inch: {e}")
            
        return None
        
    async def get_dex_prices(self, token_symbol: str) -> Dict[str, Any]:
        """Get token prices across all DEXs and chains"""
        prices = {}
        
        # Search for token across chains
        for chain_name, chain_config in self.chains.items():
            chain_id = chain_config["chain_id"]
            
            # Check if token exists on this chain
            token_address = self.popular_tokens.get(chain_id, {}).get(token_symbol.upper())
            
            if token_address:
                # Get prices from different DEXs
                for dex_name, router_address in chain_config["routers"].items():
                    try:
                        price = await self.get_token_price_1inch(chain_name, token_address)
                        
                        if price:
                            key = f"{chain_name}_{dex_name}"
                            prices[key] = {
                                "chain": chain_name,
                                "dex": dex_name,
                                "price": price,
                                "token_address": token_address,
                                "router": router_address
                            }
                            
                    except Exception as e:
                        logger.error(f"Error getting price from {dex_name} on {chain_name}: {e}")
                        
        return prices
        
    async def find_arbitrage_opportunities(self) -> List[Dict[str, Any]]:
        """Find arbitrage opportunities across DEXs"""
        opportunities = []
        
        # Check major tokens
        tokens_to_check = ["USDC", "USDT", "DAI", "WBTC", "LINK", "UNI", "AAVE"]
        
        for token in tokens_to_check:
            prices = await self.get_dex_prices(token)
            
            if len(prices) >= 2:
                # Find price differences
                sorted_prices = sorted(prices.items(), key=lambda x: x[1]["price"])
                
                lowest = sorted_prices[0]
                highest = sorted_prices[-1]
                
                price_diff = highest[1]["price"] - lowest[1]["price"]
                price_diff_pct = (price_diff / lowest[1]["price"]) * 100
                
                # Consider fees (0.3% per swap typical)
                if price_diff_pct > 1.0:  # More than 1% difference
                    opportunities.append({
                        "token": token,
                        "buy_on": lowest[0],
                        "buy_price": lowest[1]["price"],
                        "sell_on": highest[0],
                        "sell_price": highest[1]["price"],
                        "profit_pct": price_diff_pct - 0.6,  # Subtract fees
                        "buy_chain": lowest[1]["chain"],
                        "sell_chain": highest[1]["chain"]
                    })
                    
        return opportunities
        
    async def execute_dex_trade(
        self,
        chain: str,
        dex: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        slippage: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """Execute a trade on a DEX"""
        
        # This is a simulation - in production, you would:
        # 1. Connect wallet
        # 2. Approve token spending
        # 3. Call router contract
        # 4. Wait for transaction confirmation
        
        trade_data = {
            "chain": chain,
            "dex": dex,
            "token_in": token_in,
            "token_out": token_out,
            "amount_in": float(amount_in),
            "slippage": slippage,
            "status": "simulated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log the trade
        await audit_logger.log_event(
            "dex_trade_executed",
            trade_data
        )
        
        return trade_data


class DEXTradingEngine:
    """
    Main DEX trading engine
    Handles cross-chain trading and liquidity aggregation
    """
    
    def __init__(self):
        self.aggregator = DEXAggregator()
        self.active_positions = {}
        self.supported_tokens = set()
        
    async def initialize(self):
        """Initialize DEX connections"""
        await self.aggregator.initialize()
        
        # Build supported tokens list
        for chain_tokens in self.aggregator.popular_tokens.values():
            self.supported_tokens.update(chain_tokens.keys())
            
        logger.info(f"DEX Trading Engine initialized with {len(self.supported_tokens)} tokens")
        
    async def get_token_price(self, symbol: str) -> Optional[float]:
        """Get best token price across all DEXs"""
        prices = await self.aggregator.get_dex_prices(symbol)
        
        if prices:
            # Return average price
            all_prices = [p["price"] for p in prices.values()]
            return sum(all_prices) / len(all_prices)
            
        return None
        
    async def execute_trade(
        self,
        symbol: str,
        action: TradeType,
        amount: Decimal,
        preferred_chain: Optional[str] = None
    ) -> Optional[Trade]:
        """Execute a DEX trade"""
        
        # Find best DEX for the trade
        prices = await self.aggregator.get_dex_prices(symbol)
        
        if not prices:
            logger.error(f"No DEX prices found for {symbol}")
            return None
            
        # Choose best DEX based on action
        if action == TradeType.BUY:
            # Buy from cheapest
            best_dex = min(prices.items(), key=lambda x: x[1]["price"])
        else:
            # Sell to most expensive
            best_dex = max(prices.items(), key=lambda x: x[1]["price"])
            
        dex_key, dex_info = best_dex
        
        # Execute trade
        result = await self.aggregator.execute_dex_trade(
            chain=dex_info["chain"],
            dex=dex_info["dex"],
            token_in="USDC" if action == TradeType.BUY else symbol,
            token_out=symbol if action == TradeType.BUY else "USDC",
            amount_in=amount
        )
        
        if result:
            # Create trade record
            trade = Trade(
                id=f"dex-{datetime.utcnow().timestamp()}",
                symbol=symbol,
                action=action,
                quantity=amount,
                price=Decimal(str(dex_info["price"])),
                timestamp=datetime.utcnow(),
                order_type=OrderType.MARKET,
                status=TradeStatus.EXECUTED,
                exchange=f"{dex_info['chain']}:{dex_info['dex']}"
            )
            
            await audit_logger.log_trade(trade, success=True)
            return trade
            
        return None
        
    async def scan_arbitrage(self) -> List[Dict[str, Any]]:
        """Scan for arbitrage opportunities"""
        return await self.aggregator.find_arbitrage_opportunities()
        
    def get_supported_tokens(self) -> List[str]:
        """Get list of supported tokens"""
        return sorted(list(self.supported_tokens))
        
    async def get_chain_balances(self, wallet_address: str) -> Dict[str, Any]:
        """Get token balances across all chains"""
        balances = {}
        
        for chain_name, w3 in self.aggregator.web3_connections.items():
            try:
                # Get native token balance
                native_balance = w3.eth.get_balance(wallet_address)
                chain_config = self.aggregator.chains[chain_name]
                
                balances[chain_name] = {
                    "native_token": {
                        "symbol": chain_config["native_token"],
                        "balance": native_balance / 10**18,
                        "value_usd": 0  # Would need price oracle
                    },
                    "tokens": {}
                }
                
                # Get ERC20 token balances
                # In production, use multicall for efficiency
                
            except Exception as e:
                logger.error(f"Error getting balances on {chain_name}: {e}")
                
        return balances


# Global instance
dex_trading_engine = DEXTradingEngine()