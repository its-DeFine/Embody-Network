"""
RabbitMQ event handler for market data requests
"""
import json
import asyncio
from typing import Dict, Any, Optional
import aio_pika
from datetime import datetime


class MarketDataHandler:
    """Handles market data requests via RabbitMQ"""
    
    def __init__(self, openbb_service, rabbitmq_url: str):
        self.service = openbb_service
        self.rabbitmq_url = rabbitmq_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        
    async def connect(self):
        """Connect to RabbitMQ and set up consumers"""
        try:
            # Create connection
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                "openbb_events",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare and bind queues
            await self._setup_queues()
            
            print("MarketDataHandler connected to RabbitMQ")
            
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
    
    async def _setup_queues(self):
        """Set up message queues and consumers"""
        # Market data queue
        market_queue = await self.channel.declare_queue(
            "openbb.market.requests",
            durable=True
        )
        await market_queue.bind(self.exchange, "market.data.*")
        await market_queue.consume(self._handle_market_request)
        
        # Analysis queue
        analysis_queue = await self.channel.declare_queue(
            "openbb.analysis.requests",
            durable=True
        )
        await analysis_queue.bind(self.exchange, "analysis.*")
        await analysis_queue.consume(self._handle_analysis_request)
        
        # Portfolio queue
        portfolio_queue = await self.channel.declare_queue(
            "openbb.portfolio.requests",
            durable=True
        )
        await portfolio_queue.bind(self.exchange, "portfolio.*")
        await portfolio_queue.consume(self._handle_portfolio_request)
    
    async def _handle_market_request(self, message: aio_pika.IncomingMessage):
        """Handle market data requests"""
        async with message.process():
            try:
                # Parse request
                request = json.loads(message.body.decode())
                correlation_id = message.correlation_id
                
                print(f"Processing market data request: {request}")
                
                # Get data from OpenBB service
                if request["type"] == "historical":
                    data = await self.service.get_market_data(
                        symbol=request["symbol"],
                        interval=request.get("interval", "1d"),
                        start_date=request.get("start_date"),
                        end_date=request.get("end_date")
                    )
                elif request["type"] == "quote":
                    # Real-time quote
                    data = await self._get_quote(request["symbol"])
                else:
                    raise ValueError(f"Unknown request type: {request['type']}")
                
                # Send response
                await self._send_response(
                    correlation_id,
                    "market.data.response",
                    data
                )
                
            except Exception as e:
                print(f"Error handling market request: {e}")
                await self._send_error(
                    message.correlation_id,
                    "market.data.error",
                    str(e)
                )
    
    async def _handle_analysis_request(self, message: aio_pika.IncomingMessage):
        """Handle technical analysis requests"""
        async with message.process():
            try:
                request = json.loads(message.body.decode())
                correlation_id = message.correlation_id
                
                print(f"Processing analysis request: {request}")
                
                # Get analysis from service
                data = await self.service.get_technical_analysis(
                    symbol=request["symbol"],
                    indicators=request["indicators"]
                )
                
                # Send response
                await self._send_response(
                    correlation_id,
                    "analysis.response",
                    data
                )
                
            except Exception as e:
                print(f"Error handling analysis request: {e}")
                await self._send_error(
                    message.correlation_id,
                    "analysis.error",
                    str(e)
                )
    
    async def _handle_portfolio_request(self, message: aio_pika.IncomingMessage):
        """Handle portfolio analysis requests"""
        async with message.process():
            try:
                request = json.loads(message.body.decode())
                correlation_id = message.correlation_id
                
                print(f"Processing portfolio request: {request}")
                
                # Handle different portfolio operations
                if request["type"] == "analysis":
                    # Portfolio analysis logic here
                    data = {"status": "portfolio analysis not yet implemented"}
                elif request["type"] == "optimization":
                    # Portfolio optimization logic here
                    data = {"status": "portfolio optimization not yet implemented"}
                else:
                    raise ValueError(f"Unknown portfolio request type: {request['type']}")
                
                # Send response
                await self._send_response(
                    correlation_id,
                    "portfolio.response",
                    data
                )
                
            except Exception as e:
                print(f"Error handling portfolio request: {e}")
                await self._send_error(
                    message.correlation_id,
                    "portfolio.error",
                    str(e)
                )
    
    async def _send_response(self, correlation_id: str, routing_key: str, data: Dict[str, Any]):
        """Send response message"""
        message = aio_pika.Message(
            body=json.dumps(data).encode(),
            correlation_id=correlation_id,
            content_type="application/json",
            timestamp=datetime.utcnow()
        )
        
        await self.exchange.publish(message, routing_key=routing_key)
    
    async def _send_error(self, correlation_id: str, routing_key: str, error: str):
        """Send error response"""
        data = {
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self._send_response(correlation_id, routing_key, data)
    
    async def _get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote (placeholder)"""
        # This would use OpenBB's real-time data capabilities
        return {
            "symbol": symbol,
            "price": 150.25,  # Placeholder
            "change": 1.25,
            "change_percent": 0.84,
            "volume": 50000000,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def publish_market_update(self, symbol: str, data: Dict[str, Any]):
        """Publish market updates to subscribers"""
        message = aio_pika.Message(
            body=json.dumps({
                "symbol": symbol,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }).encode(),
            content_type="application/json"
        )
        
        await self.exchange.publish(
            message,
            routing_key=f"market.update.{symbol}"
        )