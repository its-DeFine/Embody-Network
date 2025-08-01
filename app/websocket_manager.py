"""
WebSocket Manager for Real-time Updates

Advanced WebSocket management system providing:
- Real-time P&L updates
- Live market data streaming  
- Agent status broadcasting
- System alerts and notifications
- Performance metrics streaming
- Multi-room support for different data types
- Connection pooling and management
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from .dependencies import get_redis
from .market_data import market_data_service
from .agent_manager import agent_manager

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types"""
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    MARKET_DATA = "market_data"
    PNL_UPDATE = "pnl_update"
    AGENT_STATUS = "agent_status"
    SYSTEM_ALERT = "system_alert"
    PERFORMANCE_METRICS = "performance_metrics"
    ORDER_UPDATE = "order_update"
    POSITION_UPDATE = "position_update"
    TRADE_EXECUTED = "trade_executed"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class SubscriptionType(str, Enum):
    """Subscription types"""
    MARKET_DATA = "market_data"
    PNL_UPDATES = "pnl_updates"
    AGENT_STATUS = "agent_status"
    SYSTEM_ALERTS = "system_alerts"
    PERFORMANCE_METRICS = "performance_metrics"
    ORDER_UPDATES = "order_updates"
    POSITION_UPDATES = "position_updates"
    TRADE_UPDATES = "trade_updates"
    ALL = "all"


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str
    id: Optional[str] = None
    room: Optional[str] = None


@dataclass
class ClientConnection:
    """Client connection information"""
    client_id: str
    websocket: WebSocket
    subscriptions: Set[SubscriptionType]
    connected_at: datetime
    last_heartbeat: datetime
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None


class WebSocketManager:
    """Advanced WebSocket connection and broadcasting manager"""
    
    def __init__(self):
        self.connections: Dict[str, ClientConnection] = {}
        self.rooms: Dict[str, Set[str]] = defaultdict(set)  # room -> client_ids
        self.subscriptions: Dict[SubscriptionType, Set[str]] = defaultdict(set)  # type -> client_ids
        self.redis = None
        self.running = False
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self.statistics = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }
        
        # Register default handlers
        self._register_default_handlers()
        
    async def initialize(self):
        """Initialize WebSocket manager"""
        self.redis = await get_redis()
        logger.info("WebSocket Manager initialized")
        
    async def start(self):
        """Start WebSocket manager background tasks"""
        await self.initialize()
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_monitor())
        asyncio.create_task(self._market_data_streamer())
        asyncio.create_task(self._pnl_updater())
        asyncio.create_task(self._agent_status_broadcaster())
        asyncio.create_task(self._performance_metrics_streamer())
        asyncio.create_task(self._system_monitor())
        
        logger.info("WebSocket Manager started")
        
    async def stop(self):
        """Stop WebSocket manager"""
        self.running = False
        
        # Close all connections
        for client_id in list(self.connections.keys()):
            await self.disconnect_client(client_id)
            
        logger.info("WebSocket Manager stopped")
        
    # Connection Management
    
    async def connect_client(self, websocket: WebSocket, user_id: str = None) -> str:
        """Connect a new WebSocket client"""
        try:
            await websocket.accept()
            
            client_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            connection = ClientConnection(
                client_id=client_id,
                websocket=websocket,
                subscriptions=set(),
                connected_at=now,
                last_heartbeat=now,
                user_id=user_id,
                metadata={}
            )
            
            self.connections[client_id] = connection
            self.statistics["total_connections"] += 1
            self.statistics["active_connections"] += 1
            
            # Send welcome message
            await self.send_to_client(client_id, WebSocketMessage(
                type=MessageType.HEARTBEAT,
                data={
                    "status": "connected", 
                    "client_id": client_id,
                    "server_time": now.isoformat()
                },
                timestamp=now.isoformat()
            ))
            
            logger.info(f"WebSocket client {client_id} connected (user: {user_id})")
            return client_id
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket client: {e}")
            raise
            
    async def disconnect_client(self, client_id: str):
        """Disconnect a WebSocket client"""
        try:
            if client_id not in self.connections:
                return
                
            connection = self.connections[client_id]
            
            # Remove from subscriptions
            for sub_type in connection.subscriptions:
                self.subscriptions[sub_type].discard(client_id)
                
            # Remove from rooms
            for room_clients in self.rooms.values():
                room_clients.discard(client_id)
                
            # Close connection
            try:
                await connection.websocket.close()
            except:
                pass
                
            del self.connections[client_id]
            self.statistics["active_connections"] -= 1
            
            logger.info(f"WebSocket client {client_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting client {client_id}: {e}")
            
    async def handle_client_message(self, client_id: str, message: dict):
        """Handle incoming message from client"""
        try:
            self.statistics["messages_received"] += 1
            
            if client_id not in self.connections:
                return
                
            connection = self.connections[client_id]
            connection.last_heartbeat = datetime.utcnow()
            
            message_type = MessageType(message.get("type", ""))
            data = message.get("data", {})
            
            # Route to appropriate handler
            handlers = self.message_handlers.get(message_type, [])
            for handler in handlers:
                await handler(client_id, data)
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            self.statistics["errors"] += 1
            
            await self.send_error_to_client(client_id, f"Message handling error: {e}")
            
    # Subscription Management
    
    async def subscribe_client(self, client_id: str, subscription_type: SubscriptionType, 
                             options: Dict[str, Any] = None):
        """Subscribe client to specific data type"""
        try:
            if client_id not in self.connections:
                return False
                
            connection = self.connections[client_id]
            connection.subscriptions.add(subscription_type)
            self.subscriptions[subscription_type].add(client_id)
            
            # Store subscription options
            if options:
                connection.metadata[f"{subscription_type.value}_options"] = options
                
            # Send confirmation
            await self.send_to_client(client_id, WebSocketMessage(
                type=MessageType.SUBSCRIBE,
                data={
                    "subscription": subscription_type.value,
                    "status": "subscribed",
                    "options": options or {}
                },
                timestamp=datetime.utcnow().isoformat()
            ))
            
            logger.info(f"Client {client_id} subscribed to {subscription_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing client: {e}")
            return False
            
    async def unsubscribe_client(self, client_id: str, subscription_type: SubscriptionType):
        """Unsubscribe client from specific data type"""
        try:
            if client_id not in self.connections:
                return False
                
            connection = self.connections[client_id]
            connection.subscriptions.discard(subscription_type)
            self.subscriptions[subscription_type].discard(client_id)
            
            # Remove subscription options
            if f"{subscription_type.value}_options" in connection.metadata:
                del connection.metadata[f"{subscription_type.value}_options"]
                
            # Send confirmation
            await self.send_to_client(client_id, WebSocketMessage(
                type=MessageType.UNSUBSCRIBE,
                data={
                    "subscription": subscription_type.value,
                    "status": "unsubscribed"
                },
                timestamp=datetime.utcnow().isoformat()
            ))
            
            logger.info(f"Client {client_id} unsubscribed from {subscription_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing client: {e}")
            return False
            
    # Broadcasting Methods
    
    async def broadcast_to_subscription(self, subscription_type: SubscriptionType, 
                                      message: WebSocketMessage):
        """Broadcast message to all clients subscribed to a type"""
        try:
            client_ids = self.subscriptions.get(subscription_type, set()).copy()
            
            if not client_ids:
                return
                
            # Send to all subscribed clients
            tasks = []
            for client_id in client_ids:
                if client_id in self.connections:
                    tasks.append(self.send_to_client(client_id, message))
                    
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                self.statistics["messages_sent"] += len(tasks)
                
        except Exception as e:
            logger.error(f"Error broadcasting to subscription {subscription_type}: {e}")
            
    async def broadcast_to_room(self, room: str, message: WebSocketMessage):
        """Broadcast message to all clients in a room"""
        try:
            client_ids = self.rooms.get(room, set()).copy()
            
            if not client_ids:
                return
                
            tasks = []
            for client_id in client_ids:
                if client_id in self.connections:
                    tasks.append(self.send_to_client(client_id, message))
                    
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                self.statistics["messages_sent"] += len(tasks)
                
        except Exception as e:
            logger.error(f"Error broadcasting to room {room}: {e}")
            
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all connected clients"""
        try:
            client_ids = list(self.connections.keys())
            
            if not client_ids:
                return
                
            tasks = []
            for client_id in client_ids:
                tasks.append(self.send_to_client(client_id, message))
                
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                self.statistics["messages_sent"] += len(tasks)
                
        except Exception as e:
            logger.error(f"Error broadcasting to all clients: {e}")
            
    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """Send message to specific client"""
        try:
            if client_id not in self.connections:
                return False
                
            connection = self.connections[client_id]
            message_data = {
                "type": message.type.value,
                "data": message.data,
                "timestamp": message.timestamp,
                "id": message.id
            }
            
            if message.room:
                message_data["room"] = message.room
                
            await connection.websocket.send_text(json.dumps(message_data))
            return True
            
        except WebSocketDisconnect:
            await self.disconnect_client(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            await self.disconnect_client(client_id)
            return False
            
    async def send_error_to_client(self, client_id: str, error_message: str):
        """Send error message to client"""
        await self.send_to_client(client_id, WebSocketMessage(
            type=MessageType.ERROR,
            data={"error": error_message},
            timestamp=datetime.utcnow().isoformat()
        ))
        
    # Room Management
    
    async def join_room(self, client_id: str, room: str):
        """Add client to a room"""
        if client_id in self.connections:
            self.rooms[room].add(client_id)
            
    async def leave_room(self, client_id: str, room: str):
        """Remove client from a room"""
        if room in self.rooms:
            self.rooms[room].discard(client_id)
            
            # Clean up empty rooms
            if not self.rooms[room]:
                del self.rooms[room]
                
    # Specialized Broadcasting Methods
    
    async def broadcast_market_data(self, symbol: str, data: Dict[str, Any]):
        """Broadcast market data update"""
        message = WebSocketMessage(
            type=MessageType.MARKET_DATA,
            data={
                "symbol": symbol,
                "price": data.get("price"),
                "change": data.get("change"),
                "change_percent": data.get("change_percent"),
                "volume": data.get("volume"),
                "timestamp": data.get("timestamp", datetime.utcnow().isoformat())
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.broadcast_to_subscription(SubscriptionType.MARKET_DATA, message)
        
    async def broadcast_pnl_update(self, pnl_data: Dict[str, Any]):
        """Broadcast P&L update"""
        message = WebSocketMessage(
            type=MessageType.PNL_UPDATE,
            data=pnl_data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.broadcast_to_subscription(SubscriptionType.PNL_UPDATES, message)
        
    async def broadcast_agent_status(self, agent_id: str, status_data: Dict[str, Any]):
        """Broadcast agent status update"""
        message = WebSocketMessage(
            type=MessageType.AGENT_STATUS,
            data={
                "agent_id": agent_id,
                **status_data
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.broadcast_to_subscription(SubscriptionType.AGENT_STATUS, message)
        
    async def broadcast_system_alert(self, alert_level: str, message_text: str, 
                                   details: Dict[str, Any] = None):
        """Broadcast system alert"""
        message = WebSocketMessage(
            type=MessageType.SYSTEM_ALERT,
            data={
                "level": alert_level,
                "message": message_text,
                "details": details or {},
                "alert_id": str(uuid.uuid4())
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.broadcast_to_subscription(SubscriptionType.SYSTEM_ALERTS, message)
        
    async def broadcast_performance_metrics(self, metrics: Dict[str, Any]):
        """Broadcast performance metrics"""
        message = WebSocketMessage(
            type=MessageType.PERFORMANCE_METRICS,
            data=metrics,
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.broadcast_to_subscription(SubscriptionType.PERFORMANCE_METRICS, message)
        
    async def broadcast_order_update(self, order_data: Dict[str, Any]):
        """Broadcast order update"""
        message = WebSocketMessage(
            type=MessageType.ORDER_UPDATE,
            data=order_data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.broadcast_to_subscription(SubscriptionType.ORDER_UPDATES, message)
        
    async def broadcast_position_update(self, position_data: Dict[str, Any]):
        """Broadcast position update"""
        message = WebSocketMessage(
            type=MessageType.POSITION_UPDATE,
            data=position_data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.broadcast_to_subscription(SubscriptionType.POSITION_UPDATES, message)
        
    async def broadcast_trade_executed(self, trade_data: Dict[str, Any]):
        """Broadcast trade execution"""
        message = WebSocketMessage(
            type=MessageType.TRADE_EXECUTED,
            data=trade_data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.broadcast_to_subscription(SubscriptionType.TRADE_UPDATES, message)
        
    # Background Tasks
    
    async def _heartbeat_monitor(self):
        """Monitor client connections and send heartbeats"""
        while self.running:
            try:
                current_time = datetime.utcnow()
                disconnected_clients = []
                
                for client_id, connection in self.connections.items():
                    # Check for stale connections (no heartbeat for 2 minutes)
                    if (current_time - connection.last_heartbeat).total_seconds() > 120:
                        disconnected_clients.append(client_id)
                        continue
                        
                    # Send periodic heartbeat
                    if (current_time - connection.last_heartbeat).total_seconds() > 30:
                        await self.send_to_client(client_id, WebSocketMessage(
                            type=MessageType.HEARTBEAT,
                            data={"server_time": current_time.isoformat()},
                            timestamp=current_time.isoformat()
                        ))
                        
                # Clean up disconnected clients
                for client_id in disconnected_clients:
                    logger.warning(f"Client {client_id} connection timed out")
                    await self.disconnect_client(client_id)
                    
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(30)
                
    async def _market_data_streamer(self):
        """Stream real-time market data"""
        while self.running:
            try:
                # Only stream if there are subscribed clients
                if not self.subscriptions.get(SubscriptionType.MARKET_DATA):
                    await asyncio.sleep(5)
                    continue
                    
                # Get symbols from subscribed clients
                symbols = set()
                for client_id in self.subscriptions[SubscriptionType.MARKET_DATA]:
                    if client_id in self.connections:
                        options = self.connections[client_id].metadata.get("market_data_options", {})
                        client_symbols = options.get("symbols", ["AAPL", "GOOGL", "MSFT"])
                        symbols.update(client_symbols)
                        
                # Fetch and broadcast market data
                for symbol in symbols:
                    try:
                        quote = await market_data_service.get_quote(symbol)
                        if quote:
                            await self.broadcast_market_data(symbol, quote)
                    except Exception as e:
                        logger.error(f"Error streaming market data for {symbol}: {e}")
                        
                await asyncio.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in market data streamer: {e}")
                await asyncio.sleep(5)
                
    async def _pnl_updater(self):
        """Update P&L data"""
        while self.running:
            try:
                # Only update if there are subscribed clients
                if not self.subscriptions.get(SubscriptionType.PNL_UPDATES):
                    await asyncio.sleep(10)
                    continue
                    
                # Get P&L data from Redis
                pnl_data = await self.redis.hgetall("trading:stats:daily")
                
                if pnl_data:
                    formatted_pnl = {
                        "daily_pnl": float(pnl_data.get(b"daily_pnl", 0)),
                        "total_pnl": float(pnl_data.get(b"total_pnl", 0)),
                        "unrealized_pnl": float(pnl_data.get(b"unrealized_pnl", 0)),
                        "realized_pnl": float(pnl_data.get(b"realized_pnl", 0)),
                        "trades_count": int(pnl_data.get(b"trades_count", 0)),
                        "success_rate": float(pnl_data.get(b"success_rate", 0)),
                        "last_updated": datetime.utcnow().isoformat()
                    }
                    
                    await self.broadcast_pnl_update(formatted_pnl)
                    
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in P&L updater: {e}")
                await asyncio.sleep(10)
                
    async def _agent_status_broadcaster(self):
        """Broadcast agent status updates"""
        while self.running:
            try:
                # Only broadcast if there are subscribed clients
                if not self.subscriptions.get(SubscriptionType.AGENT_STATUS):
                    await asyncio.sleep(10)
                    continue
                    
                # Get agent statuses
                if hasattr(agent_manager, 'agents'):
                    for agent_id, agent_data in agent_manager.agents.items():
                        status_data = {
                            "status": agent_data.get("status", "unknown"),
                            "type": agent_data.get("type", "unknown"),
                            "last_heartbeat": agent_data.get("last_heartbeat", ""),
                            "message_count": agent_data.get("message_count", 0),
                            "clusters": agent_data.get("clusters", [])
                        }
                        
                        await self.broadcast_agent_status(agent_id, status_data)
                        
                await asyncio.sleep(15)  # Update every 15 seconds
                
            except Exception as e:
                logger.error(f"Error in agent status broadcaster: {e}")
                await asyncio.sleep(15)
                
    async def _performance_metrics_streamer(self):
        """Stream performance metrics"""
        while self.running:
            try:
                # Only stream if there are subscribed clients
                if not self.subscriptions.get(SubscriptionType.PERFORMANCE_METRICS):
                    await asyncio.sleep(30)
                    continue
                    
                # Collect performance metrics
                metrics = {
                    "websocket": {
                        "active_connections": self.statistics["active_connections"],
                        "total_connections": self.statistics["total_connections"],
                        "messages_sent": self.statistics["messages_sent"],
                        "messages_received": self.statistics["messages_received"],
                        "errors": self.statistics["errors"]
                    },
                    "system": {
                        "timestamp": datetime.utcnow().isoformat(),
                        # Add more system metrics here
                    }
                }
                
                await self.broadcast_performance_metrics(metrics)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in performance metrics streamer: {e}")
                await asyncio.sleep(30)
                
    async def _system_monitor(self):
        """Monitor system health and send alerts"""
        while self.running:
            try:
                # Check system health
                current_time = datetime.utcnow()
                
                # Check Redis connection
                try:
                    await self.redis.ping()
                except Exception as e:
                    await self.broadcast_system_alert(
                        "critical", 
                        "Redis connection lost",
                        {"error": str(e), "timestamp": current_time.isoformat()}
                    )
                    
                # Check market data service health
                try:
                    health = await market_data_service.get_system_health()
                    if health.get("status") == "critical":
                        await self.broadcast_system_alert(
                            "critical",
                            "Market data service critical",
                            health
                        )
                    elif health.get("status") == "degraded":
                        await self.broadcast_system_alert(
                            "warning",
                            "Market data service degraded",
                            health
                        )
                except Exception as e:
                    await self.broadcast_system_alert(
                        "error",
                        "Failed to check market data service health",
                        {"error": str(e)}
                    )
                    
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in system monitor: {e}")
                await asyncio.sleep(60)
                
    # Message Handlers
    
    def _register_default_handlers(self):
        """Register default message handlers"""
        self.message_handlers[MessageType.SUBSCRIBE].append(self._handle_subscribe)
        self.message_handlers[MessageType.UNSUBSCRIBE].append(self._handle_unsubscribe)
        self.message_handlers[MessageType.HEARTBEAT].append(self._handle_heartbeat)
        
    async def _handle_subscribe(self, client_id: str, data: Dict[str, Any]):
        """Handle subscription request"""
        try:
            subscription_type = SubscriptionType(data.get("subscription", ""))
            options = data.get("options", {})
            
            await self.subscribe_client(client_id, subscription_type, options)
            
        except ValueError:
            await self.send_error_to_client(client_id, "Invalid subscription type")
        except Exception as e:
            logger.error(f"Error handling subscribe: {e}")
            await self.send_error_to_client(client_id, f"Subscription error: {e}")
            
    async def _handle_unsubscribe(self, client_id: str, data: Dict[str, Any]):
        """Handle unsubscription request"""
        try:
            subscription_type = SubscriptionType(data.get("subscription", ""))
            await self.unsubscribe_client(client_id, subscription_type)
            
        except ValueError:
            await self.send_error_to_client(client_id, "Invalid subscription type")
        except Exception as e:
            logger.error(f"Error handling unsubscribe: {e}")
            await self.send_error_to_client(client_id, f"Unsubscription error: {e}")
            
    async def _handle_heartbeat(self, client_id: str, data: Dict[str, Any]):
        """Handle heartbeat from client"""
        if client_id in self.connections:
            self.connections[client_id].last_heartbeat = datetime.utcnow()
            
    # Statistics and Management
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket statistics"""
        return {
            **self.statistics,
            "subscriptions": {
                sub_type.value: len(clients) 
                for sub_type, clients in self.subscriptions.items()
            },
            "rooms": {
                room: len(clients) 
                for room, clients in self.rooms.items()
            }
        }
        
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific client"""
        if client_id not in self.connections:
            return None
            
        connection = self.connections[client_id]
        return {
            "client_id": client_id,
            "user_id": connection.user_id,
            "connected_at": connection.connected_at.isoformat(),
            "last_heartbeat": connection.last_heartbeat.isoformat(),
            "subscriptions": [sub.value for sub in connection.subscriptions],
            "metadata": connection.metadata
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()