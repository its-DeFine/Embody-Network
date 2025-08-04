#!/usr/bin/env python3
"""
Register an instance with the master manager
"""

import sys
import httpx
import json

def register_instance(master_url, master_key, name, endpoint, owner_email):
    """Register a new instance with the master"""
    
    url = f"{master_url}/register-instance"
    
    data = {
        "name": name,
        "endpoint": endpoint,
        "owner_email": owner_email,
        "metadata": {
            "version": "1.0.0",
            "region": "us-east-1"
        }
    }
    
    headers = {
        "master-key": master_key,
        "Content-Type": "application/json"
    }
    
    response = httpx.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Instance registered successfully!")
        print(f"Instance ID: {result['instance_id']}")
        print(f"API Key: {result['api_key']}")
        print("\n⚠️  Save these credentials securely!")
        
        # Save to .env file
        with open(".env.instance", "w") as f:
            f.write(f"INSTANCE_ID={result['instance_id']}\n")
            f.write(f"INSTANCE_API_KEY={result['api_key']}\n")
            f.write(f"MASTER_SECRET_KEY={master_key}\n")
        
        print("\nCredentials saved to .env.instance")
        
    else:
        print(f"❌ Registration failed: {response.text}")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python register_instance.py <master_url> <master_key> <name> <endpoint> <owner_email>")
        print("Example: python register_instance.py http://localhost:9000 secret-key 'Production Instance' https://trading.example.com admin@example.com")
        sys.exit(1)
    
    master_url = sys.argv[1]
    master_key = sys.argv[2]
    name = sys.argv[3]
    endpoint = sys.argv[4]
    owner_email = sys.argv[5] if len(sys.argv) > 5 else "admin@example.com"
    
    register_instance(master_url, master_key, name, endpoint, owner_email)