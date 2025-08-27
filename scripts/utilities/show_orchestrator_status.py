#!/usr/bin/env python3
"""
Show detailed status of connected orchestrators
"""
import subprocess
import json
from datetime import datetime

def get_redis_value(key, field=None):
    """Get value from Redis"""
    if field:
        cmd = f'docker exec central-redis redis-cli HGET "{key}" "{field}"'
    else:
        cmd = f'docker exec central-redis redis-cli HGETALL "{key}"'
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    print("=" * 70)
    print("ORCHESTRATOR STATUS REPORT")
    print("=" * 70)
    
    # Get all orchestrator keys
    cmd = 'docker exec central-redis redis-cli KEYS "orchestrator:*"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    keys = result.stdout.strip().split('\n')
    
    # Filter out non-vtuber orchestrators
    vtuber_keys = [k for k in keys if 'vtuber' in k or not any(x in k for x in ['challenge', 'connection', 'livepeer'])]
    
    for key in vtuber_keys:
        if not key:
            continue
            
        print(f"\n📡 Orchestrator: {key}")
        print("-" * 50)
        
        # Get all fields
        fields = ['name', 'url', 'status', 'last_ip', 'last_heartbeat', 'active_agents', 'version', 'capabilities']
        
        for field in fields:
            value = get_redis_value(key, field)
            if value:
                if field == 'last_heartbeat':
                    # Calculate time since last heartbeat
                    try:
                        last_hb = datetime.fromisoformat(value)
                        now = datetime.utcnow()
                        diff = (now - last_hb).total_seconds()
                        value = f"{value} ({int(diff)}s ago)"
                    except:
                        pass
                
                if field == 'last_ip':
                    print(f"  🌐 Real IP: {value}")
                elif field == 'name':
                    print(f"  📛 Name: {value}")
                elif field == 'url':
                    print(f"  🔗 URL: {value}")
                elif field == 'status':
                    emoji = "✅" if value == "healthy" else "⚠️"
                    print(f"  {emoji} Status: {value}")
                elif field == 'active_agents':
                    print(f"  🤖 Active Agents: {value}")
                elif field == 'version':
                    print(f"  📦 Version: {value}")
                elif field == 'capabilities':
                    print(f"  ⚡ Capabilities: {value}")
                elif field == 'last_heartbeat':
                    print(f"  💓 Last Heartbeat: {value}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()