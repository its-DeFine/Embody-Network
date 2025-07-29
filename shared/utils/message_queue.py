import os
import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
import aio_pika
from aio_pika import Message, ExchangeType, DeliveryMode
from contextlib import asynccontextmanager

from ..events.event_types import Event, EventType

logger = logging.getLogger(__name__)


class MessageQueue:
    """RabbitMQ message queue implementation for inter-service communication"""
    
    def __init__(self, connection_url: Optional[str] = None):
        if connection_url is None:
            # Build connection URL from environment variables
            user = "admin"
            password = os.getenv("RABBITMQ_PASSWORD", "rabbitmq_secure_password_123")
            host = "rabbitmq"
            port = "5672"
            connection_url = f"amqp://{user}:{password}@{host}:{port}/"
        self.connection_url = connection_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchanges: Dict[str, aio_pika.Exchange] = {}
        self.queues: Dict[str, aio_pika.Queue] = {}
        self.consumers: Dict[str, asyncio.Task] = {}
        
    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(
                self.connection_url,
                client_properties={
                    "connection_name": "autogen-message-queue"
                }
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Create default exchanges
            await self._setup_exchanges()
            
            logger.info("Successfully connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self):
        """Close connection to RabbitMQ"""
        # Cancel all consumers
        for consumer_tag, task in self.consumers.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def _setup_exchanges(self):
        """Setup default exchanges"""
        # Events exchange for pub/sub pattern
        self.exchanges['events'] = await self.channel.declare_exchange(
            'autogen.events',
            ExchangeType.TOPIC,
            durable=True
        )
        
        # Direct exchange for point-to-point messaging
        self.exchanges['direct'] = await self.channel.declare_exchange(
            'autogen.direct',
            ExchangeType.DIRECT,
            durable=True
        )
        
        # Fanout exchange for broadcasts
        self.exchanges['broadcast'] = await self.channel.declare_exchange(
            'autogen.broadcast',
            ExchangeType.FANOUT,
            durable=True
        )
    
    async def publish_event(self, event: Event):
        """Publish an event to the events exchange"""
        if not self.channel:
            await self.connect()
        
        routing_key = event.event_type.value
        message_body = json.dumps(event.dict(), default=str).encode()
        
        message = Message(
            body=message_body,
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type='application/json',
            timestamp=datetime.utcnow(),
            message_id=event.event_id,
            correlation_id=event.correlation_id
        )
        
        await self.exchanges['events'].publish(
            message,
            routing_key=routing_key
        )
        
        logger.debug(f"Published event {event.event_id} with type {event.event_type}")
    
    async def subscribe_to_events(
        self,
        event_types: List[EventType],
        handler: Callable[[Event], Any],
        queue_name: Optional[str] = None
    ) -> str:
        """Subscribe to specific event types"""
        if not self.channel:
            await self.connect()
        
        # Create or get queue
        if queue_name is None:
            queue_name = f"autogen.events.{handler.__name__}.{id(handler)}"
        
        queue = await self.channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                'x-message-ttl': 3600000,  # 1 hour TTL
                'x-max-length': 10000
            }
        )
        
        # Bind queue to event types
        for event_type in event_types:
            await queue.bind(
                self.exchanges['events'],
                routing_key=event_type.value
            )
        
        # Start consumer
        consumer_tag = f"consumer-{queue_name}"
        
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    event = Event(**data)
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Message will be requeued due to process context
                    raise
        
        # Start consuming
        task = asyncio.create_task(self._consume_messages(queue, process_message))
        self.consumers[consumer_tag] = task
        self.queues[queue_name] = queue
        
        return consumer_tag
    
    async def _consume_messages(self, queue: aio_pika.Queue, handler: Callable):
        """Consume messages from a queue"""
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await handler(message)
    
    async def send_direct_message(
        self,
        target: str,
        message_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        """Send a direct message to a specific service or agent"""
        if not self.channel:
            await self.connect()
        
        message_data = {
            "message_type": message_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id
        }
        
        message = Message(
            body=json.dumps(message_data).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type='application/json',
            correlation_id=correlation_id
        )
        
        await self.exchanges['direct'].publish(
            message,
            routing_key=target
        )
    
    async def receive_direct_messages(
        self,
        service_name: str,
        handler: Callable[[Dict[str, Any]], Any]
    ) -> str:
        """Receive direct messages for a service"""
        if not self.channel:
            await self.connect()
        
        queue_name = f"autogen.direct.{service_name}"
        queue = await self.channel.declare_queue(
            queue_name,
            durable=True
        )
        
        await queue.bind(
            self.exchanges['direct'],
            routing_key=service_name
        )
        
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error processing direct message: {e}")
                    raise
        
        consumer_tag = f"direct-{service_name}"
        task = asyncio.create_task(self._consume_messages(queue, process_message))
        self.consumers[consumer_tag] = task
        
        return consumer_tag
    
    async def broadcast_message(self, message_type: str, payload: Dict[str, Any]):
        """Broadcast a message to all connected services"""
        if not self.channel:
            await self.connect()
        
        message_data = {
            "message_type": message_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = Message(
            body=json.dumps(message_data).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type='application/json'
        )
        
        await self.exchanges['broadcast'].publish(
            message,
            routing_key=''
        )
    
    async def receive_broadcasts(
        self,
        service_name: str,
        handler: Callable[[Dict[str, Any]], Any]
    ) -> str:
        """Receive broadcast messages"""
        if not self.channel:
            await self.connect()
        
        queue_name = f"autogen.broadcast.{service_name}"
        queue = await self.channel.declare_queue(
            queue_name,
            durable=False,
            exclusive=True
        )
        
        await queue.bind(self.exchanges['broadcast'])
        
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error processing broadcast message: {e}")
                    raise
        
        consumer_tag = f"broadcast-{service_name}"
        task = asyncio.create_task(self._consume_messages(queue, process_message))
        self.consumers[consumer_tag] = task
        
        return consumer_tag


@asynccontextmanager
async def get_message_queue(connection_url: Optional[str] = None):
    """Context manager for message queue connection"""
    mq = MessageQueue(connection_url)
    try:
        await mq.connect()
        yield mq
    finally:
        await mq.disconnect()