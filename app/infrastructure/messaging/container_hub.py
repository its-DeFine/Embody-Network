"""
Container Communication Hub

Provides secure inter-container communication, message routing, and event broadcasting
for the distributed container management system.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum

import aiohttp
import redis.asyncio as aioredis
from cryptography.fernet import Fernet

from ...config import settings
from ...dependencies import get_redis

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Message types for container communication"""

    COMMAND = "command"
    QUERY = "query"
    EVENT = "event"
    HEARTBEAT = "heartbeat"
    RESPONSE = "response"
    BROADCAST = "broadcast"


class MessagePriority(str, Enum):
    """Message priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ContainerMessage:
    """Container message structure"""

    message_id: str
    message_type: MessageType
    source_container: str
    target_container: Optional[str]  # None for broadcasts
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: str = None
    ttl: int = 300  # seconds
    encrypted: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ContainerMessage":
        """Create from dictionary"""
        return cls(**data)


class ContainerCommunicationHub:
    """
    Central hub for secure inter-container communication and message routing.
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.PubSub] = None

        # Message routing
        self.message_handlers: Dict[MessageType, List[Callable]] = {
            msg_type: [] for msg_type in MessageType
        }
        self.container_subscriptions: Dict[str, Set[str]] = {}  # container_id -> topics
        self.active_connections: Dict[str, Dict[str, Any]] = {}  # container_id -> connection info

        # Security
        self.encryption_key = None
        self.cipher_suite = None

        # Message processing
        self.message_queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self.listening_task: Optional[asyncio.Task] = None

        # Statistics
        self.message_stats = {"sent": 0, "received": 0, "routed": 0, "failed": 0}

    async def initialize(self):
        """Initialize the communication hub"""
        try:
            # Setup Redis connection
            self.redis = await aioredis.from_url(self.redis_url)
            await self.redis.ping()

            # Setup encryption
            await self._setup_encryption()

            # Start message processing
            self.processing_task = asyncio.create_task(self._process_messages())
            self.listening_task = asyncio.create_task(self._listen_for_messages())

            # Setup default handlers
            self._setup_default_handlers()

            logger.info("Container Communication Hub initialized")

        except Exception as e:
            logger.error(f"Failed to initialize communication hub: {e}")
            raise

    async def shutdown(self):
        """Shutdown the communication hub"""
        if self.processing_task:
            self.processing_task.cancel()
        if self.listening_task:
            self.listening_task.cancel()

        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()

        logger.info("Container Communication Hub shutdown")

    async def _setup_encryption(self):
        """Setup encryption for secure communication"""
        try:
            # Try to get existing key from Redis
            encryption_key = await self.redis.get("container:hub:encryption_key")

            if not encryption_key:
                # Generate new key
                encryption_key = Fernet.generate_key()
                await self.redis.set("container:hub:encryption_key", encryption_key)
                logger.info("Generated new encryption key for container communication")

            self.encryption_key = encryption_key
            self.cipher_suite = Fernet(encryption_key)

        except Exception as e:
            logger.error(f"Error setting up encryption: {e}")
            # Fallback to no encryption
            self.encryption_key = None
            self.cipher_suite = None

    def _setup_default_handlers(self):
        """Setup default message handlers"""
        # Heartbeat handler
        self.register_handler(MessageType.HEARTBEAT, self._handle_heartbeat)

        # Query handler
        self.register_handler(MessageType.QUERY, self._handle_query)

    async def send_message(self, message: ContainerMessage) -> bool:
        """Send a message to a container"""
        try:
            # Validate message
            if not message.source_container:
                raise ValueError("Source container is required")

            # Encrypt payload if needed
            if message.encrypted and self.cipher_suite:
                encrypted_payload = self.cipher_suite.encrypt(json.dumps(message.payload).encode())
                message.payload = {"encrypted_data": encrypted_payload.decode()}

            # Route message
            if message.target_container:
                # Direct message
                channel = f"container:messages:{message.target_container}"
                await self.redis.publish(channel, json.dumps(message.to_dict()))
                logger.debug(f"Sent message {message.message_id} to {message.target_container}")
            else:
                # Broadcast message
                await self.broadcast_message(message)

            # Update statistics
            self.message_stats["sent"] += 1

            # Store message for reliability (with TTL)
            message_key = f"message:{message.message_id}"
            await self.redis.setex(message_key, message.ttl, json.dumps(message.to_dict()))

            return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.message_stats["failed"] += 1
            return False

    async def broadcast_message(self, message: ContainerMessage):
        """Broadcast a message to all containers"""
        try:
            message.message_type = MessageType.BROADCAST
            channel = "container:messages:broadcast"
            await self.redis.publish(channel, json.dumps(message.to_dict()))
            logger.debug(f"Broadcast message {message.message_id} from {message.source_container}")

        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")

    async def send_command(
        self, source: str, target: str, command: str, params: Dict[str, Any] = None
    ) -> str:
        """Send a command to a container"""
        message = ContainerMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.COMMAND,
            source_container=source,
            target_container=target,
            payload={"command": command, "params": params or {}},
            priority=MessagePriority.HIGH,
        )

        await self.send_message(message)
        return message.message_id

    async def send_query(
        self, source: str, target: str, query: str, params: Dict[str, Any] = None
    ) -> str:
        """Send a query to a container"""
        message = ContainerMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.QUERY,
            source_container=source,
            target_container=target,
            payload={"query": query, "params": params or {}},
        )

        await self.send_message(message)
        return message.message_id

    async def send_event(self, source: str, event_type: str, event_data: Dict[str, Any]):
        """Send an event notification"""
        message = ContainerMessage(
            message_id=str(uuid.uuid4()),
            message_type=MessageType.EVENT,
            source_container=source,
            target_container=None,  # Broadcast to all
            payload={"event_type": event_type, "event_data": event_data},
        )

        await self.broadcast_message(message)

    async def wait_for_response(
        self, message_id: str, timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Wait for a response to a message"""
        response_key = f"response:{message_id}"

        # Poll for response
        for _ in range(timeout):
            response_data = await self.redis.get(response_key)
            if response_data:
                response = json.loads(response_data)
                await self.redis.delete(response_key)  # Clean up
                return response

            await asyncio.sleep(1)

        return None

    async def send_response(
        self, original_message_id: str, source: str, response_data: Dict[str, Any]
    ):
        """Send a response to a message"""
        response_key = f"response:{original_message_id}"
        response = {
            "original_message_id": original_message_id,
            "source_container": source,
            "response_data": response_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.redis.setex(response_key, 60, json.dumps(response))

    def register_handler(self, message_type: MessageType, handler: Callable):
        """Register a message handler"""
        if handler not in self.message_handlers[message_type]:
            self.message_handlers[message_type].append(handler)
            logger.debug(f"Registered handler for {message_type}")

    def unregister_handler(self, message_type: MessageType, handler: Callable):
        """Unregister a message handler"""
        if handler in self.message_handlers[message_type]:
            self.message_handlers[message_type].remove(handler)

    async def register_container(self, container_id: str, container_info: Dict[str, Any]):
        """Register a container with the hub"""
        try:
            # Store container info
            container_key = f"container:hub:registered:{container_id}"
            await self.redis.hset(
                container_key,
                mapping={
                    "container_id": container_id,
                    "registered_at": datetime.utcnow().isoformat(),
                    "info": json.dumps(container_info),
                    "status": "active",
                },
            )

            # Add to active containers
            await self.redis.sadd("container:hub:active", container_id)

            # Setup subscriptions
            self.container_subscriptions[container_id] = set()

            logger.info(f"Container {container_id} registered with communication hub")

            # Send registration event
            await self.send_event(
                "hub",
                "container_registered",
                {"container_id": container_id, "info": container_info},
            )

        except Exception as e:
            logger.error(f"Error registering container: {e}")

    async def unregister_container(self, container_id: str):
        """Unregister a container from the hub"""
        try:
            # Update status
            container_key = f"container:hub:registered:{container_id}"
            await self.redis.hset(container_key, "status", "inactive")

            # Remove from active containers
            await self.redis.srem("container:hub:active", container_id)

            # Clean up subscriptions
            if container_id in self.container_subscriptions:
                del self.container_subscriptions[container_id]

            logger.info(f"Container {container_id} unregistered from communication hub")

            # Send unregistration event
            await self.send_event("hub", "container_unregistered", {"container_id": container_id})

        except Exception as e:
            logger.error(f"Error unregistering container: {e}")

    async def subscribe_container(self, container_id: str, topics: List[str]):
        """Subscribe a container to specific topics"""
        if container_id not in self.container_subscriptions:
            self.container_subscriptions[container_id] = set()

        self.container_subscriptions[container_id].update(topics)

        # Store in Redis for persistence
        sub_key = f"container:hub:subscriptions:{container_id}"
        await self.redis.sadd(sub_key, *topics)

    async def unsubscribe_container(self, container_id: str, topics: List[str]):
        """Unsubscribe a container from topics"""
        if container_id in self.container_subscriptions:
            self.container_subscriptions[container_id].difference_update(topics)

        # Update Redis
        sub_key = f"container:hub:subscriptions:{container_id}"
        await self.redis.srem(sub_key, *topics)

    async def _listen_for_messages(self):
        """Listen for incoming messages"""
        try:
            self.pubsub = self.redis.pubsub()

            # Subscribe to hub channel
            await self.pubsub.subscribe("container:messages:hub")

            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        msg_data = json.loads(message["data"])
                        container_message = ContainerMessage.from_dict(msg_data)
                        await self.message_queue.put(container_message)
                        self.message_stats["received"] += 1
                    except Exception as e:
                        logger.error(f"Error processing incoming message: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in message listener: {e}")

    async def _process_messages(self):
        """Process messages from the queue"""
        while True:
            try:
                message = await self.message_queue.get()

                # Decrypt if needed
                if message.encrypted and self.cipher_suite:
                    try:
                        encrypted_data = message.payload.get("encrypted_data", "").encode()
                        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
                        message.payload = json.loads(decrypted_data.decode())
                    except Exception as e:
                        logger.error(f"Error decrypting message: {e}")
                        continue

                # Route to handlers
                handlers = self.message_handlers.get(message.message_type, [])
                for handler in handlers:
                    try:
                        await handler(message)
                        self.message_stats["routed"] += 1
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _handle_heartbeat(self, message: ContainerMessage):
        """Handle heartbeat messages"""
        container_id = message.source_container

        # Update last seen
        heartbeat_key = f"container:hub:heartbeat:{container_id}"
        await self.redis.setex(heartbeat_key, 120, datetime.utcnow().isoformat())

        # Send acknowledgment
        await self.send_response(
            message.message_id,
            "hub",
            {"status": "acknowledged", "timestamp": datetime.utcnow().isoformat()},
        )

    async def _handle_query(self, message: ContainerMessage):
        """Handle query messages"""
        query = message.payload.get("query")

        if query == "hub_status":
            response_data = {
                "status": "active",
                "active_containers": await self.redis.scard("container:hub:active"),
                "message_stats": self.message_stats,
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self.send_response(message.message_id, "hub", response_data)

    async def create_api_proxy(self, container_id: str, api_endpoint: str) -> str:
        """Create an API proxy endpoint for a remote container"""
        proxy_id = str(uuid.uuid4())
        proxy_key = f"container:hub:proxy:{proxy_id}"

        await self.redis.hset(
            proxy_key,
            mapping={
                "container_id": container_id,
                "api_endpoint": api_endpoint,
                "created_at": datetime.utcnow().isoformat(),
                "status": "active",
            },
        )

        return proxy_id

    async def proxy_request(
        self, proxy_id: str, method: str, path: str, **kwargs
    ) -> Dict[str, Any]:
        """Proxy an API request to a remote container"""
        try:
            # Get proxy info
            proxy_key = f"container:hub:proxy:{proxy_id}"
            proxy_info = await self.redis.hgetall(proxy_key)

            if not proxy_info:
                raise ValueError(f"Proxy {proxy_id} not found")

            api_endpoint = proxy_info.get(b"api_endpoint", b"").decode()

            # Make proxied request
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{api_endpoint}{path}"

                async with session.request(method, url, **kwargs) as response:
                    return {
                        "status": response.status,
                        "data": (
                            await response.json()
                            if response.content_type == "application/json"
                            else await response.text()
                        ),
                        "headers": dict(response.headers),
                    }

        except Exception as e:
            logger.error(f"Error in proxy request: {e}")
            return {"status": 500, "error": str(e)}

    async def get_hub_statistics(self) -> Dict[str, Any]:
        """Get communication hub statistics"""
        active_containers = await self.redis.scard("container:hub:active")

        # Get message volume over last hour
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)

        return {
            "active_containers": active_containers,
            "message_stats": self.message_stats,
            "subscriptions": {
                container_id: list(topics)
                for container_id, topics in self.container_subscriptions.items()
            },
            "encryption_enabled": self.cipher_suite is not None,
            "timestamp": now.isoformat(),
        }


# Singleton instance
container_hub = ContainerCommunicationHub()

# Alias for backwards compatibility
ContainerHub = ContainerCommunicationHub
