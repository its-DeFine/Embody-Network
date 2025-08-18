"""
Service Monitor for Autonomy Cluster
Tracks uptime and health of VTuber services for payment eligibility
"""

import os
import time
import logging
import docker
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class ServiceMonitor:
    """Monitors Docker container services in the autonomy cluster"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except:
            # Fallback to Docker socket
            self.docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            
        # Services to monitor (core autonomy services)
        self.monitored_services = [
            "vtuber_orchestrator",
            "redis_scb", 
            "autogen_agent",
            "autogen_postgres",
            "autogen_neo4j",
            "scb_gateway",
            "vtuber-ollama",
            "s1_*",  # Pattern for S1 services
            "s2_*",  # Pattern for S2 services
        ]
        
        # Tracking state
        self.service_stats: Dict[str, Dict] = {}
        self.check_interval = 10  # seconds
        self.uptime_window = 60  # Track last 60 seconds
        self.last_check = None
        
    def _is_monitored_service(self, container_name: str) -> bool:
        """Check if a container should be monitored"""
        for pattern in self.monitored_services:
            if '*' in pattern:
                base = pattern.replace('*', '')
                if container_name.startswith(base):
                    return True
            elif container_name == pattern:
                return True
        return False
    
    def check_services(self) -> Dict[str, Any]:
        """Check status of all monitored services"""
        try:
            containers = self.docker_client.containers.list(all=True)
            current_time = time.time()
            
            services_status = {}
            
            for container in containers:
                name = container.name
                
                if not self._is_monitored_service(name):
                    continue
                    
                # Initialize tracking if new service
                if name not in self.service_stats:
                    self.service_stats[name] = {
                        "checks": [],
                        "uptime_percentage": 0.0,
                        "last_status": None,
                        "total_uptime_seconds": 0
                    }
                
                # Check container status
                is_running = container.status == "running"
                
                # Add check to history
                self.service_stats[name]["checks"].append({
                    "timestamp": current_time,
                    "running": is_running
                })
                
                # Keep only checks within window
                cutoff_time = current_time - self.uptime_window
                self.service_stats[name]["checks"] = [
                    c for c in self.service_stats[name]["checks"]
                    if c["timestamp"] > cutoff_time
                ]
                
                # Calculate uptime percentage
                checks = self.service_stats[name]["checks"]
                if checks:
                    running_checks = sum(1 for c in checks if c["running"])
                    uptime_pct = (running_checks / len(checks)) * 100
                else:
                    uptime_pct = 0.0
                
                self.service_stats[name]["uptime_percentage"] = uptime_pct
                self.service_stats[name]["last_status"] = "running" if is_running else "stopped"
                
                # Add to response
                services_status[name] = {
                    "status": container.status,
                    "running": is_running,
                    "uptime_percentage": uptime_pct,
                    "checks_count": len(checks),
                    "health": container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown")
                }
                
            self.last_check = current_time
            
            return {
                "timestamp": datetime.now().isoformat(),
                "services": services_status,
                "monitored_count": len(services_status),
                "summary": self.get_summary()
            }
            
        except Exception as e:
            logger.error(f"Error checking services: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "services": {},
                "monitored_count": 0
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        total_services = len(self.service_stats)
        if total_services == 0:
            return {
                "overall_uptime": 0.0,
                "services_up": 0,
                "services_down": 0,
                "total_services": 0,
                "eligible_for_payment": False,
                "min_uptime_required": float(os.environ.get("MIN_SERVICE_UPTIME", "80.0"))
            }
        
        # Calculate overall uptime
        total_uptime = sum(s["uptime_percentage"] for s in self.service_stats.values())
        overall_uptime = total_uptime / total_services if total_services > 0 else 0.0
        
        # Count services by status
        services_up = sum(1 for s in self.service_stats.values() if s.get("last_status") == "running")
        services_down = total_services - services_up
        
        # Payment eligibility (e.g., 80% overall uptime)
        min_uptime_threshold = float(os.environ.get("MIN_SERVICE_UPTIME", "80.0"))
        eligible = overall_uptime >= min_uptime_threshold
        
        return {
            "overall_uptime": overall_uptime,
            "services_up": services_up,
            "services_down": services_down,
            "total_services": total_services,
            "eligible_for_payment": eligible,
            "min_uptime_required": min_uptime_threshold
        }
    
    async def start_monitoring(self):
        """Start background monitoring loop"""
        while True:
            self.check_services()
            await asyncio.sleep(self.check_interval)


# Global instance
service_monitor = ServiceMonitor()