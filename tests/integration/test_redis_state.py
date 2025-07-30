"""
Integration tests for Redis state management
"""
import pytest
import redis.asyncio as redis
import json
from datetime import datetime, timedelta
import asyncio


class TestRedisState:
    """Test Redis state management functionality"""
    
    @pytest.fixture
    async def redis_client(self):
        """Create Redis client"""
        client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
        yield client
        await client.close()
    
    async def test_connection(self, redis_client):
        """Test Redis connection"""
        pong = await redis_client.ping()
        assert pong is True
    
    async def test_basic_operations(self, redis_client):
        """Test basic Redis operations"""
        # Set and get
        await redis_client.set("test_key", "test_value")
        value = await redis_client.get("test_key")
        assert value == "test_value"
        
        # Delete
        await redis_client.delete("test_key")
        value = await redis_client.get("test_key")
        assert value is None
    
    async def test_json_storage(self, redis_client):
        """Test storing JSON data"""
        test_data = {
            "id": "123",
            "name": "Test Agent",
            "config": {
                "max_risk": 0.02,
                "trading_pairs": ["BTC/USDT", "ETH/USDT"]
            },
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store JSON
        await redis_client.set(
            "agent:123",
            json.dumps(test_data)
        )
        
        # Retrieve and parse
        stored = await redis_client.get("agent:123")
        retrieved_data = json.loads(stored)
        
        assert retrieved_data["id"] == "123"
        assert retrieved_data["config"]["max_risk"] == 0.02
        assert len(retrieved_data["config"]["trading_pairs"]) == 2
    
    async def test_hash_operations(self, redis_client):
        """Test Redis hash operations for agent data"""
        agent_id = "agent_456"
        
        # Store agent data as hash
        await redis_client.hset(
            f"agent:{agent_id}",
            mapping={
                "name": "Trading Bot",
                "type": "trading",
                "status": "running",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        # Get all fields
        agent_data = await redis_client.hgetall(f"agent:{agent_id}")
        assert agent_data["name"] == "Trading Bot"
        assert agent_data["status"] == "running"
        
        # Update single field
        await redis_client.hset(f"agent:{agent_id}", "status", "stopped")
        status = await redis_client.hget(f"agent:{agent_id}", "status")
        assert status == "stopped"
        
        # Check field exists
        exists = await redis_client.hexists(f"agent:{agent_id}", "name")
        assert exists is True
    
    async def test_list_operations(self, redis_client):
        """Test Redis list operations for event logs"""
        event_key = "events:agent:789"
        
        # Push events
        events = [
            {"type": "created", "timestamp": "2024-01-01T10:00:00"},
            {"type": "started", "timestamp": "2024-01-01T10:01:00"},
            {"type": "trade_executed", "timestamp": "2024-01-01T10:05:00"}
        ]
        
        for event in events:
            await redis_client.lpush(event_key, json.dumps(event))
        
        # Get recent events
        recent = await redis_client.lrange(event_key, 0, 1)
        assert len(recent) == 2
        
        # Get all events
        all_events = await redis_client.lrange(event_key, 0, -1)
        assert len(all_events) == 3
        
        # Pop oldest event
        oldest = await redis_client.rpop(event_key)
        oldest_event = json.loads(oldest)
        assert oldest_event["type"] == "created"
    
    async def test_set_operations(self, redis_client):
        """Test Redis set operations for active agents"""
        # Add agents to active set
        await redis_client.sadd("active_agents", "agent_1", "agent_2", "agent_3")
        
        # Check membership
        is_member = await redis_client.sismember("active_agents", "agent_2")
        assert is_member is True
        
        # Get all members
        members = await redis_client.smembers("active_agents")
        assert len(members) == 3
        assert "agent_1" in members
        
        # Remove member
        await redis_client.srem("active_agents", "agent_2")
        members = await redis_client.smembers("active_agents")
        assert len(members) == 2
        assert "agent_2" not in members
    
    async def test_sorted_set_operations(self, redis_client):
        """Test Redis sorted set for leaderboards"""
        leaderboard_key = "agent_performance"
        
        # Add agents with scores
        agents_scores = [
            ("agent_alpha", 95.5),
            ("agent_beta", 87.3),
            ("agent_gamma", 92.1),
            ("agent_delta", 88.9)
        ]
        
        for agent, score in agents_scores:
            await redis_client.zadd(leaderboard_key, {agent: score})
        
        # Get top performers
        top_agents = await redis_client.zrevrange(
            leaderboard_key, 0, 1, withscores=True
        )
        assert top_agents[0][0] == "agent_alpha"
        assert top_agents[0][1] == 95.5
        
        # Get rank
        rank = await redis_client.zrevrank(leaderboard_key, "agent_gamma")
        assert rank == 1  # 0-indexed, so second place
        
        # Update score
        await redis_client.zadd(
            leaderboard_key,
            {"agent_beta": 96.0},
            xx=True  # Only update existing
        )
        
        new_top = await redis_client.zrevrange(
            leaderboard_key, 0, 0, withscores=True
        )
        assert new_top[0][0] == "agent_beta"
    
    async def test_expiration(self, redis_client):
        """Test key expiration"""
        # Set key with expiration
        await redis_client.setex("temp_key", 2, "temporary_value")
        
        # Key should exist
        value = await redis_client.get("temp_key")
        assert value == "temporary_value"
        
        # Wait for expiration
        await asyncio.sleep(3)
        
        # Key should be gone
        value = await redis_client.get("temp_key")
        assert value is None
    
    async def test_atomic_operations(self, redis_client):
        """Test atomic operations"""
        # Initialize counter
        await redis_client.set("counter", "0")
        
        # Increment
        new_value = await redis_client.incr("counter")
        assert new_value == 1
        
        # Increment by amount
        new_value = await redis_client.incrby("counter", 5)
        assert new_value == 6
        
        # Decrement
        new_value = await redis_client.decr("counter")
        assert new_value == 5
    
    async def test_pub_sub(self, redis_client):
        """Test Redis pub/sub functionality"""
        # Create pubsub
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("test_channel")
        
        # Publish message
        await redis_client.publish("test_channel", "Hello, World!")
        
        # Receive message
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        assert message is not None
        assert message["data"] == "Hello, World!"
        
        await pubsub.unsubscribe("test_channel")
        await pubsub.close()
    
    async def test_transactions(self, redis_client):
        """Test Redis transactions"""
        # Use pipeline for transaction
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.set("key1", "value1")
            pipe.set("key2", "value2")
            pipe.get("key1")
            pipe.get("key2")
            
            results = await pipe.execute()
        
        # Check results
        assert results[0] is True  # SET key1
        assert results[1] is True  # SET key2
        assert results[2] == "value1"  # GET key1
        assert results[3] == "value2"  # GET key2
    
    async def test_agent_state_management(self, redis_client):
        """Test complete agent state management pattern"""
        agent_id = "test_agent_999"
        customer_id = "customer_123"
        
        # Store agent metadata
        agent_data = {
            "name": "Advanced Trading Bot",
            "type": "trading",
            "status": "initializing",
            "customer_id": customer_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Use transaction to ensure atomicity
        async with redis_client.pipeline(transaction=True) as pipe:
            # Store agent data
            pipe.hset(f"agent:{agent_id}", mapping=agent_data)
            
            # Add to customer's agent set
            pipe.sadd(f"customer:{customer_id}:agents", agent_id)
            
            # Add to global active agents
            pipe.sadd("agents:active", agent_id)
            
            # Set initial metrics
            pipe.hset(
                f"agent:{agent_id}:metrics",
                mapping={
                    "trades_executed": 0,
                    "profit_loss": 0.0,
                    "uptime_seconds": 0
                }
            )
            
            await pipe.execute()
        
        # Verify storage
        stored_agent = await redis_client.hgetall(f"agent:{agent_id}")
        assert stored_agent["name"] == "Advanced Trading Bot"
        
        customer_agents = await redis_client.smembers(f"customer:{customer_id}:agents")
        assert agent_id in customer_agents
        
        # Update agent status
        await redis_client.hset(f"agent:{agent_id}", "status", "running")
        
        # Log event
        event = {
            "type": "status_changed",
            "old_status": "initializing",
            "new_status": "running",
            "timestamp": datetime.utcnow().isoformat()
        }
        await redis_client.lpush(
            f"agent:{agent_id}:events",
            json.dumps(event)
        )
        
        # Clean up
        await redis_client.delete(
            f"agent:{agent_id}",
            f"agent:{agent_id}:metrics",
            f"agent:{agent_id}:events"
        )
        await redis_client.srem(f"customer:{customer_id}:agents", agent_id)
        await redis_client.srem("agents:active", agent_id)