"""
Mock Market Data Provider for Testing

This module provides mock market data for testing purposes only.
It should never be used in production environments.
"""

import random
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MockMarketDataProvider:
    """Mock provider with realistic price movements for testing only"""
    
    def __init__(self):
        self.base_prices = {
            "AAPL": 180.0,
            "MSFT": 350.0, 
            "GOOGL": 140.0,
            "TSLA": 250.0,
            "NVDA": 120.0,
            "META": 450.0,
            "AMZN": 150.0,
            "SPY": 450.0,
            "QQQ": 380.0,
            "BTC": 45000.0,
            "ETH": 2500.0
        }
        self.price_history = {}
        self._is_test_mode = True  # Flag to ensure this is only used in tests
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Generate realistic price with small fluctuations for testing"""
        if not self._is_test_mode:
            raise RuntimeError("MockMarketDataProvider should only be used in tests")
            
        if symbol not in self.base_prices:
            return None
            
        # Get last price or use base price
        last_price = self.price_history.get(symbol, self.base_prices[symbol])
        
        # Add realistic price movement (-0.5% to +0.5%)
        change_pct = random.uniform(-0.005, 0.005)
        new_price = last_price * (1 + change_pct)
        
        # Store for consistency
        self.price_history[symbol] = new_price
        
        logger.debug(f"Mock data: {symbol} = ${new_price:.2f}")
        return new_price
        
    async def get_historical_data(self, symbol: str, period: str = "1d", interval: str = "1h") -> Optional[pd.DataFrame]:
        """Generate mock historical data for testing"""
        if not self._is_test_mode:
            raise RuntimeError("MockMarketDataProvider should only be used in tests")
            
        if symbol not in self.base_prices:
            return None
            
        # Generate mock historical data
        end_time = datetime.now()
        if period == "1d":
            start_time = end_time - timedelta(days=1)
            freq = "1H"
        elif period == "5d":
            start_time = end_time - timedelta(days=5)
            freq = "1H"
        elif period == "1mo":
            start_time = end_time - timedelta(days=30)
            freq = "1D"
        else:
            start_time = end_time - timedelta(days=7)
            freq = "1H"
            
        # Create time index
        date_range = pd.date_range(start=start_time, end=end_time, freq=freq)
        
        # Generate OHLCV data
        base_price = self.base_prices[symbol]
        data = []
        
        for timestamp in date_range:
            # Generate realistic OHLC values
            open_price = base_price * (1 + random.uniform(-0.02, 0.02))
            high_price = open_price * (1 + random.uniform(0, 0.01))
            low_price = open_price * (1 - random.uniform(0, 0.01))
            close_price = random.uniform(low_price, high_price)
            volume = random.randint(1000000, 10000000)
            
            data.append({
                "Open": open_price,
                "High": high_price,
                "Low": low_price,
                "Close": close_price,
                "Volume": volume
            })
            
            # Update base price for next iteration
            base_price = close_price
            
        df = pd.DataFrame(data, index=date_range)
        df.index.name = "Date"
        
        return df
        
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get mock quote information for testing"""
        if not self._is_test_mode:
            raise RuntimeError("MockMarketDataProvider should only be used in tests")
            
        if symbol not in self.base_prices:
            return None
            
        current_price = await self.get_current_price(symbol)
        if not current_price:
            return None
            
        # Generate mock quote data
        prev_close = self.base_prices[symbol]
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
        
        return {
            "symbol": symbol,
            "price": current_price,
            "previousClose": prev_close,
            "change": change,
            "changePercent": change_pct,
            "volume": random.randint(10000000, 100000000),
            "averageVolume": random.randint(20000000, 80000000),
            "marketCap": current_price * random.randint(1000000000, 10000000000),
            "bid": current_price - 0.01,
            "ask": current_price + 0.01,
            "bidSize": random.randint(100, 1000),
            "askSize": random.randint(100, 1000),
            "dayHigh": current_price * 1.01,
            "dayLow": current_price * 0.99,
            "fiftyTwoWeekHigh": current_price * 1.3,
            "fiftyTwoWeekLow": current_price * 0.7,
            "peRatio": random.uniform(15, 35),
            "eps": random.uniform(5, 15),
            "timestamp": datetime.now().isoformat()
        }
        
    async def get_technical_indicators(self, symbol: str, period: str = "1d") -> Optional[Dict[str, Any]]:
        """Generate mock technical indicators for testing"""
        if not self._is_test_mode:
            raise RuntimeError("MockMarketDataProvider should only be used in tests")
            
        # Get historical data
        df = await self.get_historical_data(symbol, period)
        if df is None or df.empty:
            return None
            
        # Generate mock indicators
        return {
            "rsi": random.uniform(30, 70),
            "macd": random.uniform(-2, 2),
            "macd_signal": random.uniform(-2, 2),
            "sma_20": df['Close'].mean(),
            "sma_50": df['Close'].mean() * 0.98,
            "ema_12": df['Close'].mean() * 1.01,
            "ema_26": df['Close'].mean() * 0.99,
            "bb_upper": df['Close'].mean() * 1.02,
            "bb_middle": df['Close'].mean(),
            "bb_lower": df['Close'].mean() * 0.98,
            "volume_sma": df['Volume'].mean(),
            "atr": random.uniform(1, 5),
            "stoch_k": random.uniform(20, 80),
            "stoch_d": random.uniform(20, 80)
        }


def create_mock_provider() -> MockMarketDataProvider:
    """Factory function to create mock provider for tests"""
    return MockMarketDataProvider()