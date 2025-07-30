"""
Simple Redis connectivity test
"""
import asyncio
import redis.asyncio as redis
import os


async def test_redis_connectivity():
    """Test basic Redis connectivity"""
    # Connect to Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    client = redis.from_url(redis_url, decode_responses=True)
    
    try:
        # Test ping
        result = await client.ping()
        print(f"✅ Redis ping successful: {result}")
        
        # Test set/get
        await client.set("test_key", "test_value")
        value = await client.get("test_key")
        print(f"✅ Redis set/get successful: {value}")
        
        # Test delete
        await client.delete("test_key")
        value = await client.get("test_key")
        print(f"✅ Redis delete successful: {value is None}")
        
        # Test hash operations
        await client.hset("test_hash", "field1", "value1")
        value = await client.hget("test_hash", "field1")
        print(f"✅ Redis hash operations successful: {value}")
        
        # Cleanup
        await client.delete("test_hash")
        
        print("\n🎉 All Redis tests passed!")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_redis_connectivity())