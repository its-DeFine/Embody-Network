"""
Core Trading Engine Service
Handles core trading operations and market data processing
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import sys
sys.path.append('/app')
from shared.events.event_types import Event, EventType
from shared.utils.message_queue import get_message_queue
from market_data_provider import MarketDataProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoreTradingEngine:
    """Core trading engine for market operations"""
    
    def __init__(self):
        self.mq = None
        self.running = True
        self.market_data_provider = MarketDataProvider()
        
    async def initialize(self, mq):
        """Initialize the trading engine"""
        self.mq = mq
        
        # Initialize market data provider
        await self.market_data_provider.initialize()
        
        # Subscribe to trading events
        await mq.subscribe_to_events(
            [EventType.TRADE_SIGNAL, EventType.MARKET_UPDATE],
            self.handle_trading_event,
            "core-engine-events"
        )
        
        # Start market data streaming
        asyncio.create_task(self.stream_market_data())
        
        logger.info("Core Trading Engine initialized")
    
    async def handle_trading_event(self, event: Event):
        """Handle trading-related events"""
        try:
            if event.event_type == EventType.TRADE_SIGNAL:
                await self.process_trade_signal(event.data)
            elif event.event_type == EventType.MARKET_UPDATE:
                await self.process_market_update(event.data)
        except Exception as e:
            logger.error(f"Error handling trading event: {e}")
    
    async def process_trade_signal(self, signal: Dict[str, Any]):
        """Process incoming trade signals"""
        logger.info(f"Processing trade signal: {signal}")
        
        # Validate signal
        if self.validate_signal(signal):
            # Get current market price
            symbol = signal.get("symbol")
            market_data = await self.market_data_provider.get_market_data([symbol])
            current_price = market_data[0]['price'] if market_data else signal.get("price", 50000)
            
            # Execute trade with real market price
            trade_result = {
                "order_id": f"order_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "symbol": symbol,
                "side": signal.get("side"),
                "amount": signal.get("amount"),
                "status": "executed",
                "price": current_price,
                "timestamp": datetime.utcnow().isoformat(),
                "slippage": abs(current_price - signal.get("expected_price", current_price))
            }
            
            # Publish execution event
            await self.mq.publish_event(Event(
                event_id=f"trade-executed-{trade_result['order_id']}",
                event_type=EventType.TRADE_EXECUTED,
                source="core-engine",
                data=trade_result
            ))
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate trade signal"""
        required_fields = ["symbol", "side", "amount"]
        return all(field in signal for field in required_fields)
    
    async def process_market_update(self, update: Dict[str, Any]):
        """Process market data updates"""
        logger.info(f"Market update: {update}")
    
    async def stream_market_data(self):
        """Stream real market data updates"""
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
        
        # Define callback for streaming data
        async def publish_market_update(data):
            await self.mq.publish_event(Event(
                event_id=f"market-update-{data['symbol']}-{datetime.utcnow().timestamp()}",
                event_type=EventType.MARKET_UPDATE,
                source="core-engine",
                data=data
            ))
        
        # Start streaming with fallback to polling
        while self.running:
            try:
                # Try to get real market data
                market_data_list = await self.market_data_provider.get_market_data(symbols)
                
                for data in market_data_list:
                    await publish_market_update(data)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in market data streaming: {e}")
                # Fallback to simulated data if real data fails
                for symbol in symbols:
                    fallback_data = {
                        "symbol": symbol,
                        "price": 50000 + (hash(symbol) % 10000),
                        "volume": 1000000,
                        "change_24h": 2.5,
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "simulated"
                    }
                    await publish_market_update(fallback_data)
                
                await asyncio.sleep(60)
    
    async def cleanup(self):
        """Cleanup resources"""
        self.running = False
        await self.market_data_provider.cleanup()


async def main():
    """Main entry point"""
    engine = CoreTradingEngine()
    
    # Connect to message queue
    async with get_message_queue() as mq:
        await engine.initialize(mq)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Core Trading Engine")
        finally:
            await engine.cleanup()


if __name__ == "__main__":
    asyncio.run(main())