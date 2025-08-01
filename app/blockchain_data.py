"""
Blockchain Data & Chainlink Oracle Integration

Free on-chain data from Chainlink price feeds and blockchain explorers.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
from decimal import Decimal

logger = logging.getLogger(__name__)


class ChainlinkOracleProvider:
    """
    Chainlink Price Feeds - Completely FREE!
    Read directly from blockchain via public RPC endpoints
    """
    
    def __init__(self):
        # Free public RPC endpoints
        self.rpc_endpoints = {
            "ethereum": [
                "https://eth.public-rpc.com",
                "https://cloudflare-eth.com",
                "https://rpc.ankr.com/eth",
                "https://ethereum.publicnode.com"
            ],
            "polygon": [
                "https://polygon-rpc.com",
                "https://rpc.ankr.com/polygon",
                "https://polygon.publicnode.com"
            ],
            "bsc": [
                "https://bsc-dataseed.binance.org",
                "https://rpc.ankr.com/bsc",
                "https://bsc.publicnode.com"
            ],
            "avalanche": [
                "https://api.avax.network/ext/bc/C/rpc",
                "https://rpc.ankr.com/avalanche",
                "https://avalanche.publicnode.com"
            ],
            "arbitrum": [
                "https://arb1.arbitrum.io/rpc",
                "https://rpc.ankr.com/arbitrum"
            ]
        }
        
        # Chainlink price feed addresses (Ethereum mainnet)
        self.price_feeds = {
            "BTC/USD": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
            "ETH/USD": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
            "LINK/USD": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c",
            "BNB/USD": "0x14e613AC84a31f709eadbdF89C6CC390fDc9540A",
            "MATIC/USD": "0x7bAC85A8a13A4BcD8abb3eB7d6b4d632c5a57676",
            "AVAX/USD": "0xFF3EEb22B5E3dE6e705b44749C2559d704923FD7",
            "SOL/USD": "0x4ffC43a60e009B551865A93d232E33Fce9f01507",
            "ADA/USD": "0xAE48c91dF1fE419994FFDa27da09D5aC69c30f55",
            "DOT/USD": "0x1C07AFb8E2B827c5A4739C6d59Ae3A5035f28734",
            "DOGE/USD": "0x2465CefD3b488BE410b941b1d4b2767088e2A028",
            "UNI/USD": "0x553303d460EE0afB37EdFf9bE42922D8FF63220e",
            "AAVE/USD": "0x547a514d5e3769680Ce22B2361c10Ea13619e8a9",
            "COMP/USD": "0xdbd020CAeF83eFd542f4De03e3cF0C28A4428bd5",
            "SUSHI/USD": "0xCc70F09A6CC17553b2E31954cD36E4A2d89501f7",
            "CRV/USD": "0xCd627aA160A6fA45Eb793D19Ef54f5062F20f33f",
            "XRP/USD": "0xCed2660c6Dd1Ffd856A5A82C67f3482d88C50b12",
            "USDT/USD": "0x3E7d1eAB13ad0104d2750B8863b489D65364e32D",
            "USDC/USD": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
            "DAI/USD": "0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9"
        }
        
        self.client = httpx.AsyncClient()
        
    async def _call_rpc(self, network: str, method: str, params: List) -> Optional[Any]:
        """Make RPC call to blockchain"""
        for endpoint in self.rpc_endpoints.get(network, []):
            try:
                response = await self.client.post(
                    endpoint,
                    json={
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": params,
                        "id": 1
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        return data["result"]
                        
            except Exception as e:
                logger.warning(f"RPC error with {endpoint}: {e}")
                continue
                
        return None
        
    async def get_chainlink_price(self, pair: str) -> Optional[float]:
        """Get price from Chainlink oracle"""
        try:
            feed_address = self.price_feeds.get(pair.upper())
            if not feed_address:
                logger.warning(f"No Chainlink feed for {pair}")
                return None
                
            # ABI for latestRoundData function
            # function latestRoundData() returns (uint80, int256, uint256, uint256, uint80)
            function_signature = "0xfeaf968c"  # keccak256("latestRoundData()")[:10]
            
            # Call the contract
            result = await self._call_rpc(
                "ethereum",
                "eth_call",
                [{
                    "to": feed_address,
                    "data": function_signature
                }, "latest"]
            )
            
            if result:
                # Decode the result (skip first 2 chars '0x')
                data = result[2:]
                
                # The price is the second value (int256) in the return data
                # Each value is 32 bytes (64 hex chars)
                price_hex = data[64:128]  # Second 32-byte value
                price_raw = int(price_hex, 16)
                
                # Handle negative values (two's complement)
                if price_raw > 2**255:
                    price_raw = price_raw - 2**256
                    
                # Chainlink uses 8 decimals for USD pairs
                price = price_raw / 10**8
                
                logger.info(f"Chainlink {pair}: ${price}")
                return float(price)
                
        except Exception as e:
            logger.error(f"Chainlink oracle error for {pair}: {e}")
            
        return None
        
    async def get_all_prices(self) -> Dict[str, float]:
        """Get all available Chainlink prices"""
        prices = {}
        
        for pair, address in self.price_feeds.items():
            price = await self.get_chainlink_price(pair)
            if price:
                symbol = pair.split("/")[0]
                prices[symbol] = price
                
            # Small delay to avoid overwhelming RPC
            await asyncio.sleep(0.1)
            
        return prices


class BlockchainExplorerProvider:
    """
    Free blockchain explorers for transaction data and wallet info
    """
    
    def __init__(self):
        self.explorers = {
            "ethereum": {
                "api": "https://api.etherscan.io/api",
                "key": "YourEtherscanAPIKey"  # Free tier available
            },
            "bsc": {
                "api": "https://api.bscscan.com/api",
                "key": "YourBscScanAPIKey"  # Free tier available
            },
            "polygon": {
                "api": "https://api.polygonscan.com/api",
                "key": "YourPolygonScanAPIKey"  # Free tier available
            }
        }
        
        # Ethplorer - FREE API for token prices and wallet data
        self.ethplorer_url = "https://api.ethplorer.io"
        self.ethplorer_key = "freekey"  # Free key with 2000 requests/day
        
        self.client = httpx.AsyncClient()
        
    async def get_eth_price(self) -> Optional[float]:
        """Get ETH price from Ethplorer"""
        try:
            response = await self.client.get(
                f"{self.ethplorer_url}/getTop",
                params={
                    "apiKey": self.ethplorer_key,
                    "limit": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "ethPrice" in data:
                    return float(data["ethPrice"])
                    
        except Exception as e:
            logger.error(f"Ethplorer error: {e}")
            
        return None
        
    async def get_token_price(self, contract_address: str) -> Optional[Dict[str, Any]]:
        """Get token info and price from Ethplorer"""
        try:
            response = await self.client.get(
                f"{self.ethplorer_url}/getTokenInfo/{contract_address}",
                params={"apiKey": self.ethplorer_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "price" in data:
                    return {
                        "symbol": data.get("symbol"),
                        "name": data.get("name"),
                        "price": float(data["price"]["rate"]),
                        "volume": float(data["price"].get("volume24h", 0)),
                        "market_cap": float(data["price"].get("marketCapUsd", 0)),
                        "decimals": data.get("decimals")
                    }
                    
        except Exception as e:
            logger.error(f"Token price error: {e}")
            
        return None
        
    async def get_wallet_balance(self, address: str) -> Optional[Dict[str, Any]]:
        """Get wallet balance and token holdings"""
        try:
            response = await self.client.get(
                f"{self.ethplorer_url}/getAddressInfo/{address}",
                params={"apiKey": self.ethplorer_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                balance = {
                    "address": address,
                    "ETH": {
                        "balance": float(data.get("ETH", {}).get("balance", 0)),
                        "price": float(data.get("ETH", {}).get("price", {}).get("rate", 0))
                    },
                    "tokens": []
                }
                
                # Add token balances
                for token in data.get("tokens", []):
                    token_info = token.get("tokenInfo", {})
                    balance["tokens"].append({
                        "symbol": token_info.get("symbol"),
                        "balance": float(token.get("balance", 0)) / (10 ** int(token_info.get("decimals", 18))),
                        "price": float(token_info.get("price", {}).get("rate", 0))
                    })
                    
                return balance
                
        except Exception as e:
            logger.error(f"Wallet balance error: {e}")
            
        return None


class DeFiPulseProvider:
    """
    DeFi protocols data - TVL, yields, etc.
    Uses public APIs from DeFi protocols
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient()
        
        # DefiLlama - FREE DeFi data
        self.defillama_url = "https://api.llama.fi"
        
    async def get_defi_tvl(self) -> Optional[Dict[str, Any]]:
        """Get total DeFi TVL from DefiLlama"""
        try:
            response = await self.client.get(f"{self.defillama_url}/tvl")
            
            if response.status_code == 200:
                tvl = response.json()
                return {"total_tvl": float(tvl)}
                
        except Exception as e:
            logger.error(f"DeFi TVL error: {e}")
            
        return None
        
    async def get_protocol_tvl(self, protocol: str) -> Optional[Dict[str, Any]]:
        """Get specific protocol TVL"""
        try:
            response = await self.client.get(
                f"{self.defillama_url}/protocol/{protocol.lower()}"
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": data.get("name"),
                    "symbol": data.get("symbol"),
                    "tvl": data.get("tvl", 0),
                    "chain_tvls": data.get("chainTvls", {})
                }
                
        except Exception as e:
            logger.error(f"Protocol TVL error: {e}")
            
        return None
        
    async def get_stablecoin_rates(self) -> Optional[Dict[str, float]]:
        """Get stablecoin prices to check peg"""
        try:
            response = await self.client.get(f"{self.defillama_url}/stablecoins")
            
            if response.status_code == 200:
                data = response.json()
                
                rates = {}
                for stable in data.get("peggedAssets", []):
                    if stable.get("symbol") in ["USDT", "USDC", "DAI", "BUSD", "TUSD"]:
                        rates[stable["symbol"]] = stable.get("price", 1.0)
                        
                return rates
                
        except Exception as e:
            logger.error(f"Stablecoin rates error: {e}")
            
        return None


# Create a unified crypto data service
class CryptoDataService:
    """Unified service for all crypto data sources"""
    
    def __init__(self):
        self.chainlink = ChainlinkOracleProvider()
        self.explorer = BlockchainExplorerProvider()
        self.defi = DeFiPulseProvider()
        
    async def get_price(self, symbol: str) -> Optional[float]:
        """Get price from best available source"""
        # Try Chainlink first (most reliable)
        price = await self.chainlink.get_chainlink_price(f"{symbol}/USD")
        
        if not price and symbol.upper() == "ETH":
            # Try Ethplorer for ETH
            price = await self.explorer.get_eth_price()
            
        return price
        
    async def get_all_prices(self) -> Dict[str, float]:
        """Get all available prices"""
        return await self.chainlink.get_all_prices()


# Global instance
crypto_data_service = CryptoDataService()