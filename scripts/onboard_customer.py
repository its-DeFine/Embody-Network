#!/usr/bin/env python3
"""
Customer Onboarding Script for AutoGen Agent Platform

This script automates the process of onboarding new customers:
1. Creates customer account
2. Generates API keys
3. Sets up initial agent configurations
4. Deploys customer agents
"""

import asyncio
import argparse
import secrets
import string
import json
from datetime import datetime
from pathlib import Path
import redis.asyncio as redis
import aiohttp
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))


class CustomerOnboarding:
    def __init__(self, redis_url: str, api_url: str):
        self.redis_url = redis_url
        self.api_url = api_url
        self.redis_client = None
        
    async def connect(self):
        """Connect to Redis"""
        self.redis_client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.aclose()
    
    def generate_api_key(self, length: int = 32) -> str:
        """Generate a secure API key"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_customer_id(self) -> str:
        """Generate a unique customer ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(secrets.choice(string.digits) for _ in range(6))
        return f"cust_{timestamp}_{random_suffix}"
    
    async def create_customer(self, customer_data: dict) -> dict:
        """Create a new customer account"""
        # Generate IDs and keys
        customer_id = self.generate_customer_id()
        api_key = self.generate_api_key()
        
        # Prepare customer configuration
        customer_config = {
            "customer_id": customer_id,
            "name": customer_data["name"],
            "email": customer_data["email"],
            "api_key": api_key,
            "tier": customer_data.get("tier", "basic"),
            "max_agents": customer_data.get("max_agents", 5),
            "max_teams": customer_data.get("max_teams", 2),
            "rate_limits": {
                "requests_per_minute": 60 if customer_data.get("tier") == "basic" else 300,
                "requests_per_hour": 1000 if customer_data.get("tier") == "basic" else 10000
            },
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True
        }
        
        # Store in Redis - convert all values to strings
        await self.redis_client.hset(
            f"customer:{customer_id}",
            mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                    for k, v in customer_config.items()}
        )
        
        # Create email index
        await self.redis_client.set(
            f"customer:email:{customer_config['email']}",
            customer_id
        )
        
        print(f"✓ Created customer account: {customer_id}")
        
        return customer_config
    
    async def create_default_agents(self, customer_id: str, tier: str) -> list:
        """Create default agents based on customer tier"""
        agents = []
        
        # Define default agents by tier
        if tier == "basic":
            agent_configs = [
                {
                    "name": "Trading Assistant",
                    "agent_type": "trading",
                    "description": "Basic trading agent for market analysis",
                    "config": {
                        "trading_pairs": ["BTC/USDT", "ETH/USDT"],
                        "risk_limit": 0.02
                    }
                }
            ]
        elif tier == "pro":
            agent_configs = [
                {
                    "name": "Advanced Trader",
                    "agent_type": "trading",
                    "description": "Advanced trading agent with multiple strategies",
                    "config": {
                        "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
                        "risk_limit": 0.03,
                        "strategies": ["momentum", "mean_reversion"]
                    }
                },
                {
                    "name": "Market Analyst",
                    "agent_type": "analysis",
                    "description": "Comprehensive market analysis agent",
                    "config": {
                        "analysis_types": ["technical", "sentiment"],
                        "update_frequency": "15m"
                    }
                }
            ]
        else:  # enterprise
            agent_configs = [
                {
                    "name": "Enterprise Trader",
                    "agent_type": "trading",
                    "description": "Enterprise-grade trading agent",
                    "config": {
                        "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"],
                        "risk_limit": 0.05,
                        "strategies": ["momentum", "mean_reversion", "arbitrage"]
                    }
                },
                {
                    "name": "Market Intelligence",
                    "agent_type": "analysis",
                    "description": "AI-powered market intelligence",
                    "config": {
                        "analysis_types": ["technical", "fundamental", "sentiment"],
                        "data_sources": ["exchange", "news", "social"],
                        "update_frequency": "5m"
                    }
                },
                {
                    "name": "Risk Guardian",
                    "agent_type": "risk_management",
                    "description": "Advanced risk management agent",
                    "config": {
                        "max_portfolio_risk": 0.10,
                        "max_position_risk": 0.05,
                        "monitoring_frequency": "1m"
                    }
                }
            ]
        
        # Create agents via API
        async with aiohttp.ClientSession() as session:
            # First, get auth token
            auth_data = await self._get_auth_token(session, customer_id)
            headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
            
            for agent_config in agent_configs:
                async with session.post(
                    f"{self.api_url}/agents",
                    json=agent_config,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        agents.append(result)
                        print(f"✓ Created agent: {agent_config['name']}")
                    else:
                        print(f"✗ Failed to create agent: {agent_config['name']}")
        
        return agents
    
    async def _get_auth_token(self, session: aiohttp.ClientSession, customer_id: str) -> dict:
        """Get authentication token for API calls"""
        # Get customer data
        customer_data = await self.redis_client.hgetall(f"customer:{customer_id}")
        
        # Login to get token
        async with session.post(
            f"{self.api_url}/auth/login",
            json={
                "email": customer_data["email"],
                "api_key": customer_data["api_key"]
            }
        ) as response:
            return await response.json()
    
    async def create_welcome_team(self, customer_id: str, agent_ids: list) -> dict:
        """Create a default team for new customers"""
        if len(agent_ids) < 2:
            print("ℹ️  Not enough agents to create a team")
            return {}
        
        async with aiohttp.ClientSession() as session:
            # Get auth token
            auth_data = await self._get_auth_token(session, customer_id)
            headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
            
            # Create team
            team_config = {
                "name": "Default Team",
                "description": "Your first agent team for collaborative trading",
                "agent_ids": agent_ids[:2],  # Use first two agents
                "orchestrator_config": {
                    "max_rounds": 10,
                    "decision_method": "consensus"
                }
            }
            
            async with session.post(
                f"{self.api_url}/teams",
                json=team_config,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✓ Created team: {team_config['name']}")
                    return result
                else:
                    print(f"✗ Failed to create team")
                    return {}
    
    async def send_welcome_email(self, customer_config: dict):
        """Send welcome email to customer (mock implementation)"""
        print("\n📧 Welcome Email Content:")
        print("=" * 50)
        print(f"To: {customer_config['email']}")
        print(f"Subject: Welcome to AutoGen Agent Platform!")
        print(f"\nDear {customer_config['name']},")
        print(f"\nYour account has been successfully created!")
        print(f"\nAccount Details:")
        print(f"- Customer ID: {customer_config['customer_id']}")
        print(f"- API Key: {customer_config['api_key']}")
        print(f"- Tier: {customer_config['tier'].upper()}")
        print(f"- Max Agents: {customer_config['max_agents']}")
        print(f"- Max Teams: {customer_config['max_teams']}")
        print(f"\nAPI Endpoint: {self.api_url}")
        print(f"\nGet started with our documentation at: https://docs.autogen-platform.com")
        print("=" * 50)
    
    async def generate_onboarding_report(self, customer_config: dict, agents: list):
        """Generate onboarding report"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "customer": {
                "id": customer_config["customer_id"],
                "name": customer_config["name"],
                "email": customer_config["email"],
                "tier": customer_config["tier"]
            },
            "resources_created": {
                "agents": len(agents),
                "agent_details": [
                    {
                        "id": agent.get("agent_id"),
                        "name": agent.get("name", "Unknown"),
                        "type": agent.get("agent_type", "Unknown")
                    }
                    for agent in agents
                ]
            },
            "next_steps": [
                "Login to the platform using your API key",
                "Configure your agents via the API",
                "Start your first trading session",
                "Monitor performance in real-time"
            ]
        }
        
        # Save report
        report_path = Path("onboarding_reports")
        report_path.mkdir(exist_ok=True)
        
        report_file = report_path / f"{customer_config['customer_id']}_onboarding.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Onboarding report saved to: {report_file}")
        
        return report


async def main():
    parser = argparse.ArgumentParser(description="Onboard a new customer")
    parser.add_argument("--name", required=True, help="Customer name")
    parser.add_argument("--email", required=True, help="Customer email")
    parser.add_argument("--tier", choices=["basic", "pro", "enterprise"], 
                       default="basic", help="Customer tier")
    parser.add_argument("--max-agents", type=int, help="Maximum agents allowed")
    parser.add_argument("--max-teams", type=int, help="Maximum teams allowed")
    parser.add_argument("--redis-url", default="redis://localhost:6379",
                       help="Redis connection URL")
    parser.add_argument("--api-url", default="http://localhost:8000",
                       help="API Gateway URL")
    
    args = parser.parse_args()
    
    # Prepare customer data
    customer_data = {
        "name": args.name,
        "email": args.email,
        "tier": args.tier
    }
    
    # Override defaults if provided
    if args.max_agents:
        customer_data["max_agents"] = args.max_agents
    if args.max_teams:
        customer_data["max_teams"] = args.max_teams
    
    # Initialize onboarding
    onboarding = CustomerOnboarding(args.redis_url, args.api_url)
    
    try:
        print(f"\n🚀 Starting customer onboarding for: {args.name}")
        print("=" * 50)
        
        # Connect to Redis
        await onboarding.connect()
        
        # Create customer
        customer_config = await onboarding.create_customer(customer_data)
        
        # Create default agents
        print("\n📦 Creating default agents...")
        agents = await onboarding.create_default_agents(
            customer_config["customer_id"],
            customer_config["tier"]
        )
        
        # Create welcome team (if applicable)
        if len(agents) >= 2:
            agent_ids = [agent["agent_id"] for agent in agents]
            await onboarding.create_welcome_team(
                customer_config["customer_id"],
                agent_ids
            )
        
        # Send welcome email
        await onboarding.send_welcome_email(customer_config)
        
        # Generate report
        await onboarding.generate_onboarding_report(customer_config, agents)
        
        print("\n✅ Customer onboarding completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Onboarding failed: {e}")
        raise
    finally:
        await onboarding.disconnect()


if __name__ == "__main__":
    asyncio.run(main())