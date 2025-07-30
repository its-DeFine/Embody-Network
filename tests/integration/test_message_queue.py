"""
Integration tests for RabbitMQ message queue
"""
import pytest
import asyncio
import json
import aio_pika
from datetime import datetime


class TestMessageQueue:
    """Test RabbitMQ messaging functionality"""
    
    @pytest.fixture
    async def rabbitmq_connection(self):
        """Create RabbitMQ connection"""
        connection = await aio_pika.connect_robust(
            "amqp://guest:guest@localhost:5672/"
        )
        yield connection
        await connection.close()
    
    @pytest.fixture
    async def channel(self, rabbitmq_connection):
        """Create RabbitMQ channel"""
        channel = await rabbitmq_connection.channel()
        yield channel
        await channel.close()
    
    async def test_connection(self, rabbitmq_connection):
        """Test RabbitMQ connection"""
        assert not rabbitmq_connection.is_closed
    
    async def test_queue_declaration(self, channel):
        """Test queue declaration"""
        queue_name = "test_queue"
        queue = await channel.declare_queue(
            queue_name,
            durable=False,
            auto_delete=True
        )
        assert queue.name == queue_name
    
    async def test_exchange_declaration(self, channel):
        """Test exchange declaration"""
        exchange_name = "test_exchange"
        exchange = await channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=False,
            auto_delete=True
        )
        assert exchange.name == exchange_name
    
    async def test_publish_consume(self, channel):
        """Test basic publish/consume pattern"""
        queue = await channel.declare_queue(
            "test_pub_sub",
            auto_delete=True
        )
        
        test_message = {
            "type": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"value": 42}
        }
        
        # Publish message
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(test_message).encode()
            ),
            routing_key=queue.name
        )
        
        # Consume message
        received = []
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    received.append(json.loads(message.body.decode()))
                    break
        
        assert len(received) == 1
        assert received[0]["type"] == "test"
        assert received[0]["data"]["value"] == 42
    
    async def test_topic_routing(self, channel):
        """Test topic exchange routing"""
        exchange = await channel.declare_exchange(
            "test_topic_exchange",
            aio_pika.ExchangeType.TOPIC,
            auto_delete=True
        )
        
        # Create queues with different routing patterns
        queue1 = await channel.declare_queue("", exclusive=True)
        queue2 = await channel.declare_queue("", exclusive=True)
        
        await queue1.bind(exchange, routing_key="agent.*.created")
        await queue2.bind(exchange, routing_key="agent.#")
        
        # Publish messages
        await exchange.publish(
            aio_pika.Message(body=b"agent created"),
            routing_key="agent.trading.created"
        )
        
        await exchange.publish(
            aio_pika.Message(body=b"agent updated"),
            routing_key="agent.trading.updated"
        )
        
        # Check messages in queues
        # Queue1 should have 1 message (created only)
        msg1 = await queue1.get()
        assert msg1 is not None
        assert msg1.body == b"agent created"
        
        msg1_2 = await queue1.get()
        assert msg1_2 is None  # No more messages
        
        # Queue2 should have 2 messages (all agent messages)
        msg2_1 = await queue2.get()
        assert msg2_1 is not None
        
        msg2_2 = await queue2.get()
        assert msg2_2 is not None
    
    async def test_event_system(self, channel):
        """Test the platform's event system"""
        # Declare the events exchange as used by the platform
        exchange = await channel.declare_exchange(
            "autogen_events",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
        
        # Create a test consumer queue
        queue = await channel.declare_queue("", exclusive=True)
        await queue.bind(exchange, routing_key="agent.*")
        
        # Simulate agent created event
        event = {
            "event_id": "test-123",
            "event_type": "agent.created",
            "source": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "agent_id": "agent-456",
                "name": "Test Agent",
                "type": "trading"
            }
        }
        
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(event).encode(),
                content_type="application/json"
            ),
            routing_key="agent.created"
        )
        
        # Consume and verify
        message = await queue.get(timeout=5)
        assert message is not None
        
        received_event = json.loads(message.body.decode())
        assert received_event["event_type"] == "agent.created"
        assert received_event["data"]["agent_id"] == "agent-456"
    
    async def test_rpc_pattern(self, channel):
        """Test RPC (Remote Procedure Call) pattern"""
        # Create RPC queue
        rpc_queue = await channel.declare_queue("rpc_queue", auto_delete=True)
        
        # Simulate RPC server
        async def process_rpc_request():
            async with rpc_queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        # Process request
                        request = json.loads(message.body.decode())
                        response = {"result": request["value"] * 2}
                        
                        # Send response
                        await channel.default_exchange.publish(
                            aio_pika.Message(
                                body=json.dumps(response).encode()
                            ),
                            routing_key=message.reply_to
                        )
                        return
        
        # Start RPC server
        server_task = asyncio.create_task(process_rpc_request())
        
        # Create callback queue for response
        callback_queue = await channel.declare_queue("", exclusive=True)
        
        # Send RPC request
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps({"value": 21}).encode(),
                reply_to=callback_queue.name
            ),
            routing_key=rpc_queue.name
        )
        
        # Wait for response
        response_message = await callback_queue.get(timeout=5)
        assert response_message is not None
        
        response = json.loads(response_message.body.decode())
        assert response["result"] == 42
        
        # Cleanup
        await server_task
    
    async def test_dead_letter_queue(self, channel):
        """Test dead letter queue functionality"""
        # Create DLX exchange
        dlx_exchange = await channel.declare_exchange(
            "test_dlx",
            aio_pika.ExchangeType.DIRECT,
            auto_delete=True
        )
        
        # Create dead letter queue
        dlq = await channel.declare_queue(
            "test_dlq",
            auto_delete=True
        )
        await dlq.bind(dlx_exchange, routing_key="failed")
        
        # Create main queue with DLX
        main_queue = await channel.declare_queue(
            "test_main_queue",
            auto_delete=True,
            arguments={
                "x-dead-letter-exchange": dlx_exchange.name,
                "x-dead-letter-routing-key": "failed",
                "x-message-ttl": 1000  # 1 second TTL
            }
        )
        
        # Publish message
        await channel.default_exchange.publish(
            aio_pika.Message(body=b"test message"),
            routing_key=main_queue.name
        )
        
        # Wait for message to expire
        await asyncio.sleep(1.5)
        
        # Check dead letter queue
        dlq_message = await dlq.get()
        assert dlq_message is not None
        assert dlq_message.body == b"test message"
    
    async def test_priority_queue(self, channel):
        """Test priority queue functionality"""
        # Create priority queue
        priority_queue = await channel.declare_queue(
            "test_priority_queue",
            auto_delete=True,
            arguments={"x-max-priority": 10}
        )
        
        # Publish messages with different priorities
        messages = [
            (b"low priority", 1),
            (b"high priority", 9),
            (b"medium priority", 5)
        ]
        
        for body, priority in messages:
            await channel.default_exchange.publish(
                aio_pika.Message(body=body, priority=priority),
                routing_key=priority_queue.name
            )
        
        # Consume messages - should be in priority order
        received = []
        for _ in range(3):
            message = await priority_queue.get()
            if message:
                received.append(message.body.decode())
                await message.ack()
        
        # High priority should be first
        assert received[0] == "high priority"


class TestMessageResilience:
    """Test message queue resilience and error handling"""
    
    async def test_connection_recovery(self):
        """Test automatic connection recovery"""
        connection = await aio_pika.connect_robust(
            "amqp://guest:guest@localhost:5672/"
        )
        
        assert not connection.is_closed
        
        # Connection should have reconnect capability
        assert hasattr(connection, 'reconnect')
        
        await connection.close()
    
    async def test_message_acknowledgment(self):
        """Test message acknowledgment patterns"""
        connection = await aio_pika.connect_robust(
            "amqp://guest:guest@localhost:5672/"
        )
        channel = await connection.channel()
        
        queue = await channel.declare_queue("test_ack", auto_delete=True)
        
        # Publish message
        await channel.default_exchange.publish(
            aio_pika.Message(body=b"test"),
            routing_key=queue.name
        )
        
        # Get message without ack
        message = await queue.get(no_ack=False)
        assert message is not None
        
        # Message should still be in queue
        await channel.close()
        channel = await connection.channel()
        queue = await channel.declare_queue("test_ack", passive=True)
        
        # Get and ack message
        message = await queue.get()
        assert message is not None
        await message.ack()
        
        # Queue should be empty now
        message = await queue.get()
        assert message is None
        
        await connection.close()