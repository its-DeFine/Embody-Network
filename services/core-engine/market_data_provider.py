"""
Real market data provider using multiple data sources
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aiohttp
import json
import os

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """Real-time market data provider"""
    
    def __init__(self):
        self.session = None
        self.data_sources = {
            'coingecko': {
                'base_url': 'https://api.coingecko.com/api/v3',
                'api_key': os.getenv('COINGECKO_API_KEY'),
                'rate_limit': 50  # requests per minute
            },
            'binance': {
                'base_url': 'https://api.binance.com/api/v3',
                'websocket': 'wss://stream.binance.com:9443/ws',
                'rate_limit': 1200
            },
            'coinbase': {
                'base_url': 'https://api.exchange.coinbase.com',
                'rate_limit': 100
            }
        }
        self.cache = {}
        self.cache_ttl = 30  # seconds
        
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    async def get_market_data(self, symbols: List[str], source: str = 'binance') -> List[Dict[str, Any]]:
        """Get real market data for multiple symbols"""
        market_data = []
        
        for symbol in symbols:
            # Check cache first
            cache_key = f"{source}:{symbol}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.utcnow() - cached_data['timestamp'] < timedelta(seconds=self.cache_ttl):
                    market_data.append(cached_data['data'])
                    continue
            
            # Fetch fresh data
            try:
                data = await self._fetch_market_data(symbol, source)
                market_data.append(data)
                
                # Update cache
                self.cache[cache_key] = {
                    'data': data,
                    'timestamp': datetime.utcnow()
                }
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                # Return last known data or empty
                if cache_key in self.cache:
                    market_data.append(self.cache[cache_key]['data'])
        
        return market_data
    
    async def _fetch_market_data(self, symbol: str, source: str) -> Dict[str, Any]:
        """Fetch market data from specific source"""
        if source == 'binance':
            return await self._fetch_binance_data(symbol)
        elif source == 'coingecko':
            return await self._fetch_coingecko_data(symbol)
        elif source == 'coinbase':
            return await self._fetch_coinbase_data(symbol)
        else:
            raise ValueError(f"Unknown data source: {source}")
    
    async def _fetch_binance_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from Binance"""
        # Convert symbol format (BTC/USDT -> BTCUSDT)
        binance_symbol = symbol.replace('/', '')
        
        try:
            # Get ticker data
            ticker_url = f"{self.data_sources['binance']['base_url']}/ticker/24hr"
            async with self.session.get(ticker_url, params={'symbol': binance_symbol}) as resp:
                ticker_data = await resp.json()
            
            # Get order book
            depth_url = f"{self.data_sources['binance']['base_url']}/depth"
            async with self.session.get(depth_url, params={'symbol': binance_symbol, 'limit': 10}) as resp:
                depth_data = await resp.json()
            
            return {
                'symbol': symbol,
                'price': float(ticker_data['lastPrice']),
                'bid': float(ticker_data['bidPrice']),
                'ask': float(ticker_data['askPrice']),
                'volume_24h': float(ticker_data['volume']),
                'volume_quote_24h': float(ticker_data['quoteVolume']),
                'change_24h': float(ticker_data['priceChangePercent']),
                'high_24h': float(ticker_data['highPrice']),
                'low_24h': float(ticker_data['lowPrice']),
                'orderbook': {
                    'bids': [[float(p), float(q)] for p, q in depth_data['bids'][:5]],
                    'asks': [[float(p), float(q)] for p, q in depth_data['asks'][:5]]
                },
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'binance'
            }
        except Exception as e:
            logger.error(f"Binance API error: {e}")
            raise
    
    async def _fetch_coingecko_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from CoinGecko"""
        # Convert symbol to CoinGecko format
        base, quote = symbol.split('/')
        coin_id = self._get_coingecko_id(base)
        
        try:
            url = f"{self.data_sources['coingecko']['base_url']}/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': quote.lower(),
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true',
                'include_market_cap': 'true'
            }
            
            headers = {}
            if self.data_sources['coingecko']['api_key']:
                headers['x-cg-pro-api-key'] = self.data_sources['coingecko']['api_key']
            
            async with self.session.get(url, params=params, headers=headers) as resp:
                data = await resp.json()
            
            coin_data = data.get(coin_id, {})
            quote_lower = quote.lower()
            
            return {
                'symbol': symbol,
                'price': coin_data.get(quote_lower, 0),
                'volume_24h': coin_data.get(f'{quote_lower}_24h_vol', 0),
                'change_24h': coin_data.get(f'{quote_lower}_24h_change', 0),
                'market_cap': coin_data.get(f'{quote_lower}_market_cap', 0),
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'coingecko'
            }
        except Exception as e:
            logger.error(f"CoinGecko API error: {e}")
            raise
    
    async def _fetch_coinbase_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from Coinbase"""
        # Convert symbol format
        coinbase_symbol = symbol.replace('/', '-')
        
        try:
            # Get ticker
            ticker_url = f"{self.data_sources['coinbase']['base_url']}/products/{coinbase_symbol}/ticker"
            async with self.session.get(ticker_url) as resp:
                ticker_data = await resp.json()
            
            # Get 24hr stats
            stats_url = f"{self.data_sources['coinbase']['base_url']}/products/{coinbase_symbol}/stats"
            async with self.session.get(stats_url) as resp:
                stats_data = await resp.json()
            
            return {
                'symbol': symbol,
                'price': float(ticker_data['price']),
                'bid': float(ticker_data['bid']),
                'ask': float(ticker_data['ask']),
                'volume_24h': float(ticker_data['volume']),
                'high_24h': float(stats_data['high']),
                'low_24h': float(stats_data['low']),
                'open_24h': float(stats_data['open']),
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'coinbase'
            }
        except Exception as e:
            logger.error(f"Coinbase API error: {e}")
            raise
    
    def _get_coingecko_id(self, symbol: str) -> str:
        """Map symbol to CoinGecko ID"""
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'BNB': 'binancecoin',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'AVAX': 'avalanche-2',
            'DOT': 'polkadot',
            'MATIC': 'matic-network',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'ATOM': 'cosmos'
        }
        return mapping.get(symbol.upper(), symbol.lower())
    
    async def stream_market_data(self, symbols: List[str], callback):
        """Stream real-time market data via WebSocket"""
        # This would connect to Binance WebSocket for real-time updates
        ws_url = self.data_sources['binance']['websocket']
        
        # Subscribe to ticker streams
        streams = [f"{s.lower().replace('/', '')}@ticker" for s in symbols]
        stream_url = f"{ws_url}/stream?streams={','.join(streams)}"
        
        # Implementation would handle WebSocket connection
        # For now, simulate with polling
        while True:
            try:
                market_data = await self.get_market_data(symbols)
                for data in market_data:
                    await callback(data)
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(10)
    
    async def get_historical_data(self, symbol: str, interval: str = '1h', 
                                limit: int = 100, source: str = 'binance') -> List[Dict[str, Any]]:
        """Get historical OHLCV data"""
        if source == 'binance':
            binance_symbol = symbol.replace('/', '')
            url = f"{self.data_sources['binance']['base_url']}/klines"
            params = {
                'symbol': binance_symbol,
                'interval': interval,
                'limit': limit
            }
            
            async with self.session.get(url, params=params) as resp:
                klines = await resp.json()
            
            return [{
                'timestamp': k[0],
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            } for k in klines]
        else:
            raise NotImplementedError(f"Historical data not implemented for {source}")