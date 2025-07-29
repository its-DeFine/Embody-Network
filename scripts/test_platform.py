#!/usr/bin/env python3
"""
Test the AutoGen platform with basic operations
"""
import asyncio
import json
import httpx
from datetime import datetime


async def test_platform():
    """Test basic platform functionality"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing AutoGen Platform")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # 1. Test health endpoint
        print("\n1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ API Gateway is healthy")
                print(f"   Response: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return
        
        # 2. Test detailed health
        print("\n2. Testing detailed health...")
        try:
            response = await client.get(f"{base_url}/health/detailed")
            if response.status_code == 200:
                health = response.json()
                print("✅ Detailed health check:")
                for dep, status in health.get("dependencies", {}).items():
                    print(f"   • {dep}: {status}")
            else:
                print(f"❌ Detailed health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # 3. Test authentication (mock customer)
        print("\n3. Testing authentication...")
        login_data = {
            "email": "test@testcorp.com",
            "api_key": "DcqvANBn1GcraB9J5SXGc9yOIvUaoFBU"
        }
        
        try:
            response = await client.post(f"{base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                auth_data = response.json()
                token = auth_data.get("access_token")
                print("✅ Authentication successful")
                print(f"   Token: {token[:20]}...")
                
                # Set auth header for subsequent requests
                headers = {"Authorization": f"Bearer {token}"}
                
                # 4. Test listing agents
                print("\n4. Testing agent listing...")
                response = await client.get(f"{base_url}/agents", headers=headers)
                if response.status_code == 200:
                    agents_data = response.json()
                    print(f"✅ Listed {len(agents_data.get('agents', []))} agents")
                else:
                    print(f"❌ Failed to list agents: {response.status_code}")
                
            elif response.status_code == 401:
                print("❌ Authentication failed - customer not found")
                print("   Run onboard_customer.py first to create a test customer")
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # 5. Test Prometheus metrics
        print("\n5. Testing Prometheus metrics...")
        try:
            response = await client.get("http://localhost:9090/-/ready")
            if response.status_code == 200:
                print("✅ Prometheus is ready")
            else:
                print(f"❌ Prometheus not ready: {response.status_code}")
        except Exception as e:
            print(f"❌ Prometheus error: {e}")
        
        # 6. Test Grafana
        print("\n6. Testing Grafana...")
        try:
            response = await client.get("http://localhost:3000/api/health")
            if response.status_code == 200:
                print("✅ Grafana is healthy")
            else:
                print(f"❌ Grafana not healthy: {response.status_code}")
        except Exception as e:
            print(f"❌ Grafana error: {e}")
        
        # 7. Test RabbitMQ Management
        print("\n7. Testing RabbitMQ Management...")
        try:
            # Default credentials from docker-compose
            auth = ("admin", "rabbitmq_secure_password_123")
            response = await client.get(
                "http://localhost:15672/api/overview",
                auth=auth
            )
            if response.status_code == 200:
                print("✅ RabbitMQ Management is accessible")
                overview = response.json()
                print(f"   • RabbitMQ version: {overview.get('rabbitmq_version', 'unknown')}")
            else:
                print(f"❌ RabbitMQ Management error: {response.status_code}")
        except Exception as e:
            print(f"❌ RabbitMQ error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Platform test completed!")
    print("\nAccess URLs:")
    print("  • API Gateway: http://localhost:8000")
    print("  • API Docs: http://localhost:8000/docs")
    print("  • RabbitMQ: http://localhost:15672")
    print("  • Grafana: http://localhost:3000")
    print("  • Prometheus: http://localhost:9090")


if __name__ == "__main__":
    asyncio.run(test_platform())