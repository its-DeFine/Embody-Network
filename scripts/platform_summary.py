#!/usr/bin/env python3
"""
Platform Summary - Shows the current state of the AutoGen Platform
"""

import subprocess
import json
import sys

def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "Error running command"

def get_container_status():
    """Get status of all containers"""
    print("🐳 Docker Container Status")
    print("=" * 60)
    
    cmd = 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
    output = run_command(cmd)
    print(output)
    print()

def get_service_health():
    """Check health of key services"""
    print("🏥 Service Health Checks")
    print("=" * 60)
    
    services = [
        ("API Gateway", "http://localhost:8000/health"),
        ("RabbitMQ", "http://localhost:15672/api/health/checks/virtual-hosts"),
        ("Prometheus", "http://localhost:9090/-/healthy"),
        ("Grafana", "http://localhost:3000/api/health"),
    ]
    
    for name, url in services:
        cmd = f'curl -s -o /dev/null -w "%{{http_code}}" {url} 2>/dev/null'
        status = run_command(cmd)
        if status == "200":
            print(f"✅ {name}: Healthy")
        else:
            print(f"❌ {name}: Unhealthy (HTTP {status})")
    print()

def get_redis_stats():
    """Get Redis statistics"""
    print("📊 Redis Statistics")
    print("=" * 60)
    
    # Count different key types
    patterns = [
        ("Customers", "customer:*"),
        ("Agents", "agent:*"),
        ("Tasks", "task:*"),
        ("Teams", "team:*"),
    ]
    
    for name, pattern in patterns:
        cmd = f'docker exec redis redis-cli --scan --pattern "{pattern}" | wc -l'
        count = run_command(cmd)
        print(f"  • {name}: {count}")
    print()

def get_platform_summary():
    """Get overall platform summary"""
    print("📋 Platform Summary")
    print("=" * 60)
    
    print("✅ Completed Features:")
    print("  • API Gateway with authentication")
    print("  • Agent creation and management")
    print("  • Task creation and tracking")
    print("  • Team management")
    print("  • Metrics collection")
    print("  • Health monitoring")
    print("  • WebSocket support")
    print("  • Pagination and limits")
    print("  • Circuit breakers and retry logic")
    print("  • Structured logging")
    
    print("\n⚠️  Known Issues:")
    print("  • Agent Manager and Update Pipeline need Docker socket permissions")
    print("  • Tasks remain pending without Agent Manager")
    print("  • Team creation has Redis serialization issue")
    
    print("\n🚀 Next Steps:")
    print("  • Fix Docker socket permissions for agent containers")
    print("  • Implement actual AutoGen agent execution")
    print("  • Add agent communication protocols")
    print("  • Complete update pipeline implementation")
    print()

def main():
    print("\n🤖 AutoGen Platform Status Report")
    print("=" * 60)
    print()
    
    get_container_status()
    get_service_health()
    get_redis_stats()
    get_platform_summary()
    
    print("📌 Access URLs:")
    print("  • API Gateway: http://localhost:8000")
    print("  • API Docs: http://localhost:8000/docs")
    print("  • RabbitMQ: http://localhost:15672 (guest/guest)")
    print("  • Grafana: http://localhost:3000 (admin/admin)")
    print("  • Prometheus: http://localhost:9090")
    print()

if __name__ == "__main__":
    main()