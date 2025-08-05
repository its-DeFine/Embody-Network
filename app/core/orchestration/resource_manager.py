"""
Resource Management Service

Focused microservice responsible for:
- Dynamic memory allocation and monitoring
- CPU resource management
- Disk space monitoring and cleanup
- Container resource limits adjustment
- Automatic garbage collection
- Memory leak detection and prevention
"""
import asyncio
import psutil
import gc
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import deque
import statistics

from .base_service import BaseOrchestrationService

logger = logging.getLogger(__name__)


class ResourceManager(BaseOrchestrationService):
    """Microservice for dynamic resource management"""
    
    def __init__(self, redis=None):
        super().__init__("resource_manager", redis)
        
        # Resource tracking
        self.memory_history: deque = deque(maxlen=1000)
        self.cpu_history: deque = deque(maxlen=1000)
        self.disk_history: deque = deque(maxlen=1000)
        
        # Container resource limits (dynamic)
        self.container_limits: Dict[str, Dict] = {}
        self.default_limits = {
            "memory_mb": 2048,  # Start with 2GB, can grow
            "cpu_cores": 2.0,
            "max_memory_mb": 8192,  # Maximum 8GB
            "min_memory_mb": 512,   # Minimum 512MB
        }
        
        # Memory management
        self.memory_threshold_warning = 70.0  # %
        self.memory_threshold_critical = 85.0  # %
        self.memory_cleanup_history: deque = deque(maxlen=100)
        
        # Auto-scaling settings
        self.auto_scaling_enabled = True
        self.scale_up_threshold = 80.0  # % resource usage
        self.scale_down_threshold = 30.0  # % resource usage
        
    async def setup(self):
        """Initialize resource manager"""
        # Subscribe to resource-related events
        asyncio.create_task(self.subscribe_to_events([
            "agent.started",
            "agent.stopped",
            "agent.metrics",
            "system.alert",
            "container.resource_request"
        ]))
        
        # Initialize system resource baseline
        await self._initialize_resource_baseline()
        
    async def _service_loop(self):
        """Main resource management loop"""
        while self.running:
            try:
                await self._monitor_system_resources()
                await self._manage_container_resources()
                await self._detect_memory_leaks()
                await self._cleanup_if_needed()
                
                await asyncio.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in resource manager loop: {e}")
                await asyncio.sleep(30)
                
    def get_background_tasks(self):
        """Background tasks for resource manager"""
        return [
            self._garbage_collector(),
            self._resource_optimizer(),
            self._container_scaler(),
            self._disk_cleanup_manager()
        ]
        
    async def handle_event(self, event: Dict[str, Any]):
        """Handle resource-related events"""
        event_type = event["type"]
        data = event["data"]
        
        if event_type == "agent.started":
            await self._handle_agent_started(data)
        elif event_type == "agent.stopped":
            await self._handle_agent_stopped(data)
        elif event_type == "agent.metrics":
            await self._handle_agent_metrics(data)
        elif event_type == "system.alert":
            await self._handle_system_alert(data)
        elif event_type == "container.resource_request":
            await self._handle_resource_request(data)
            
    async def _initialize_resource_baseline(self):
        """Initialize system resource baseline measurements"""
        try:
            # Get system specs
            total_memory = psutil.virtual_memory().total
            cpu_count = psutil.cpu_count()
            disk_total = psutil.disk_usage('/').total
            
            baseline = {
                "total_memory_gb": round(total_memory / (1024**3), 2),
                "cpu_cores": cpu_count,
                "disk_total_gb": round(disk_total / (1024**3), 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store baseline
            await self.redis.set("system:resource_baseline", json.dumps(baseline))
            
            self.logger.info(f"💾 Resource baseline: {baseline['total_memory_gb']}GB RAM, {cpu_count} cores, {baseline['disk_total_gb']}GB disk")
            
        except Exception as e:
            self.logger.error(f"Error initializing resource baseline: {e}")
            
    async def _monitor_system_resources(self):
        """Monitor system-wide resource usage"""
        try:
            # Memory
            memory = psutil.virtual_memory()
            memory_snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
                "cached_gb": round(memory.cached / (1024**3), 2) if hasattr(memory, 'cached') else 0
            }
            self.memory_history.append(memory_snapshot)
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "percent": cpu_percent,
                "cores": psutil.cpu_count(),
                "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
            self.cpu_history.append(cpu_snapshot)
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round((disk.used / disk.total) * 100, 2)
            }
            self.disk_history.append(disk_snapshot)
            
            # Store current metrics
            current_metrics = {
                "memory": memory_snapshot,
                "cpu": cpu_snapshot, 
                "disk": disk_snapshot
            }
            
            await self.redis.set(
                "system:current_resources",
                json.dumps(current_metrics),
                ex=60  # Expire in 1 minute
            )
            
            # Check thresholds
            await self._check_resource_thresholds(current_metrics)
            
        except Exception as e:
            self.logger.error(f"Error monitoring system resources: {e}")
            
    async def _check_resource_thresholds(self, metrics: Dict[str, Any]):
        """Check if resource usage exceeds thresholds"""
        memory_percent = metrics["memory"]["percent"]
        cpu_percent = metrics["cpu"]["percent"]
        disk_percent = metrics["disk"]["percent"]
        
        # Memory threshold checks
        if memory_percent >= self.memory_threshold_critical:
            await self._trigger_emergency_memory_cleanup()
            await self.publish_event("resource.memory_critical", {
                "memory_percent": memory_percent,
                "available_gb": metrics["memory"]["available_gb"]
            })
        elif memory_percent >= self.memory_threshold_warning:
            await self._trigger_memory_optimization()
            await self.publish_event("resource.memory_warning", {
                "memory_percent": memory_percent,
                "available_gb": metrics["memory"]["available_gb"]
            })
            
        # CPU threshold checks
        if cpu_percent >= 90:
            await self.publish_event("resource.cpu_critical", {
                "cpu_percent": cpu_percent,
                "load_avg": metrics["cpu"]["load_avg"]
            })
        elif cpu_percent >= 75:
            await self.publish_event("resource.cpu_warning", {
                "cpu_percent": cpu_percent
            })
            
        # Disk threshold checks
        if disk_percent >= 90:
            await self._trigger_disk_cleanup()
            await self.publish_event("resource.disk_critical", {
                "disk_percent": disk_percent,
                "free_gb": metrics["disk"]["free_gb"]
            })
            
    async def _manage_container_resources(self):
        """Dynamically manage container resource limits"""
        try:
            # Get current system load
            memory_usage = self.memory_history[-1]["percent"] if self.memory_history else 50
            cpu_usage = self.cpu_history[-1]["percent"] if self.cpu_history else 50
            
            # Adjust container limits based on system load
            for container_id, limits in self.container_limits.items():
                new_limits = await self._calculate_optimal_limits(
                    container_id, memory_usage, cpu_usage
                )
                
                if new_limits != limits:
                    await self._update_container_limits(container_id, new_limits)
                    self.container_limits[container_id] = new_limits
                    
        except Exception as e:
            self.logger.error(f"Error managing container resources: {e}")
            
    async def _calculate_optimal_limits(self, container_id: str, memory_usage: float, cpu_usage: float) -> Dict[str, Any]:
        """Calculate optimal resource limits for a container"""
        current_limits = self.container_limits.get(container_id, self.default_limits.copy())
        
        # Memory adjustment
        memory_mb = current_limits["memory_mb"]
        
        if memory_usage > 80:
            # System under pressure, reduce container limits
            memory_mb = max(
                current_limits["min_memory_mb"],
                int(memory_mb * 0.9)  # Reduce by 10%
            )
        elif memory_usage < 40:
            # System has capacity, allow growth
            memory_mb = min(
                current_limits["max_memory_mb"],
                int(memory_mb * 1.1)  # Increase by 10%
            )
            
        # CPU adjustment
        cpu_cores = current_limits["cpu_cores"]
        
        if cpu_usage > 80:
            cpu_cores = max(0.5, cpu_cores * 0.9)  # Reduce by 10%
        elif cpu_usage < 40:
            cpu_cores = min(4.0, cpu_cores * 1.1)  # Increase by 10%
            
        return {
            "memory_mb": memory_mb,
            "cpu_cores": round(cpu_cores, 1),
            "max_memory_mb": current_limits["max_memory_mb"],
            "min_memory_mb": current_limits["min_memory_mb"]
        }
        
    async def _update_container_limits(self, container_id: str, new_limits: Dict[str, Any]):
        """Update container resource limits"""
        try:
            # In a real implementation, this would update Docker container limits
            # For now, we'll publish an event that the container can respond to
            
            await self.publish_event("container.limits_updated", {
                "container_id": container_id,
                "new_limits": new_limits,
                "previous_limits": self.container_limits.get(container_id, {})
            })
            
            self.logger.info(f"📊 Updated limits for {container_id}: {new_limits['memory_mb']}MB, {new_limits['cpu_cores']} cores")
            
        except Exception as e:
            self.logger.error(f"Error updating container limits for {container_id}: {e}")
            
    async def _detect_memory_leaks(self):
        """Detect potential memory leaks"""
        if len(self.memory_history) < 10:
            return
            
        try:
            # Analyze memory trend over last 10 measurements
            recent_memory = [m["percent"] for m in list(self.memory_history)[-10:]]
            
            # Calculate trend
            if len(recent_memory) >= 5:
                # Simple linear regression to detect upward trend
                x = list(range(len(recent_memory)))
                y = recent_memory
                
                n = len(x)
                sum_x = sum(x)
                sum_y = sum(y)
                sum_xy = sum(x[i] * y[i] for i in range(n))
                sum_x2 = sum(x[i] ** 2 for i in range(n))
                
                # Calculate slope (trend)
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
                
                # If slope > 2, memory is increasing by 2% per measurement
                if slope > 2.0 and recent_memory[-1] > 70:
                    await self.publish_event("resource.memory_leak_detected", {
                        "trend_slope": slope,
                        "current_memory_percent": recent_memory[-1],
                        "recommendation": "Consider garbage collection or container restart"
                    })
                    
                    self.logger.warning(f"🚨 Potential memory leak detected: slope={slope:.2f}")
                    
        except Exception as e:
            self.logger.error(f"Error detecting memory leaks: {e}")
            
    async def _cleanup_if_needed(self):
        """Perform cleanup if resources are running low"""
        if not self.memory_history:
            return
            
        current_memory = self.memory_history[-1]["percent"]
        
        if current_memory > self.memory_threshold_warning:
            await self._trigger_memory_optimization()
            
    async def _trigger_memory_optimization(self):
        """Trigger memory optimization procedures"""
        try:
            cleanup_actions = []
            
            # 1. Python garbage collection
            collected = gc.collect()
            cleanup_actions.append(f"Python GC: {collected} objects")
            
            # 2. Clear application caches (would be implemented per app)
            await self.publish_event("system.clear_caches", {
                "reason": "memory_optimization",
                "timestamp": datetime.utcnow().isoformat()
            })
            cleanup_actions.append("Application caches cleared")
            
            # 3. Suggest container memory limits reduction
            await self.publish_event("system.reduce_memory_usage", {
                "reason": "memory_optimization"
            })
            cleanup_actions.append("Container limits optimization requested")
            
            # Log cleanup
            cleanup_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "reason": "memory_optimization",
                "actions": cleanup_actions,
                "memory_before": self.memory_history[-1]["percent"] if self.memory_history else 0
            }
            
            self.memory_cleanup_history.append(cleanup_record)
            
            self.logger.info(f"🧹 Memory optimization triggered: {', '.join(cleanup_actions)}")
            
        except Exception as e:
            self.logger.error(f"Error in memory optimization: {e}")
            
    async def _trigger_emergency_memory_cleanup(self):
        """Emergency memory cleanup when critically low"""
        try:
            self.logger.warning("🚨 EMERGENCY MEMORY CLEANUP TRIGGERED")
            
            # Force garbage collection multiple times
            for _ in range(3):
                collected = gc.collect()
                await asyncio.sleep(0.1)
                
            # Emergency cache clearing
            await self.publish_event("system.emergency_cleanup", {
                "reason": "critical_memory_shortage",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Request immediate container memory reduction
            await self.publish_event("system.emergency_memory_reduction", {
                "severity": "critical"
            })
            
            self.logger.warning("🚨 Emergency cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error in emergency memory cleanup: {e}")
            
    async def _trigger_disk_cleanup(self):
        """Trigger disk space cleanup"""
        try:
            cleanup_actions = []
            
            # 1. Clean up log files
            await self.publish_event("system.cleanup_logs", {
                "max_age_days": 7,
                "reason": "disk_space_low"
            })
            cleanup_actions.append("Old log files")
            
            # 2. Clean up temporary files
            await self.publish_event("system.cleanup_temp", {
                "reason": "disk_space_low"
            })
            cleanup_actions.append("Temporary files")
            
            # 3. Clean up old metrics
            await self.publish_event("system.cleanup_metrics", {
                "max_age_days": 30,
                "reason": "disk_space_low"
            })
            cleanup_actions.append("Old metrics data")
            
            self.logger.info(f"🧹 Disk cleanup triggered: {', '.join(cleanup_actions)}")
            
        except Exception as e:
            self.logger.error(f"Error in disk cleanup: {e}")
            
    async def _handle_agent_started(self, data: Dict):
        """Handle agent startup - allocate resources"""
        agent_id = data.get("agent_id")
        requested_resources = data.get("resources", {})
        
        if agent_id:
            # Allocate resources for new agent
            limits = self.default_limits.copy()
            
            # Adjust based on requested resources
            if "memory_mb" in requested_resources:
                limits["memory_mb"] = min(
                    requested_resources["memory_mb"],
                    limits["max_memory_mb"]
                )
                
            self.container_limits[agent_id] = limits
            
            self.logger.info(f"📦 Allocated resources for agent {agent_id}: {limits}")
            
    async def _handle_agent_stopped(self, data: Dict):
        """Handle agent shutdown - deallocate resources"""
        agent_id = data.get("agent_id")
        
        if agent_id in self.container_limits:
            freed_resources = self.container_limits.pop(agent_id)
            self.logger.info(f"♻️ Freed resources from agent {agent_id}: {freed_resources}")
            
    async def _handle_agent_metrics(self, data: Dict):
        """Handle agent metrics for resource optimization"""
        agent_id = data.get("agent_id")
        metrics = data.get("metrics", {})
        
        if agent_id in self.container_limits:
            # Use metrics to optimize resource allocation
            memory_usage = metrics.get("memory_usage", 0)
            cpu_usage = metrics.get("cpu_usage", 0)
            
            # If agent is consistently under-utilizing, reduce limits
            # If over-utilizing, increase limits
            # This would be more sophisticated in production
            
    async def _handle_system_alert(self, data: Dict):
        """Handle system alerts related to resources"""
        alert_type = data.get("type", "")
        
        if "memory" in alert_type:
            await self._trigger_memory_optimization()
        elif "disk" in alert_type:
            await self._trigger_disk_cleanup()
            
    async def _handle_resource_request(self, data: Dict):
        """Handle container resource requests"""
        container_id = data.get("container_id")
        requested_resources = data.get("resources", {})
        
        if container_id:
            # Evaluate if we can grant the request
            can_grant = await self._evaluate_resource_request(requested_resources)
            
            if can_grant:
                self.container_limits[container_id] = requested_resources
                await self.publish_event("container.resources_granted", {
                    "container_id": container_id,
                    "granted_resources": requested_resources
                })
            else:
                await self.publish_event("container.resources_denied", {
                    "container_id": container_id,
                    "requested_resources": requested_resources,
                    "reason": "insufficient_system_resources"
                })
                
    async def _evaluate_resource_request(self, requested: Dict[str, Any]) -> bool:
        """Evaluate if a resource request can be granted"""
        if not self.memory_history or not self.cpu_history:
            return False
            
        current_memory = self.memory_history[-1]["percent"]
        current_cpu = self.cpu_history[-1]["percent"]
        
        # Simple evaluation - in production would be more sophisticated
        if current_memory > 75 or current_cpu > 75:
            return False
            
        return True
        
    # Background task implementations
    
    async def _garbage_collector(self):
        """Periodic garbage collection"""
        while self.running:
            try:
                # Run garbage collection every 5 minutes
                collected = gc.collect()
                
                if collected > 0:
                    self.logger.debug(f"🗑️ Garbage collected: {collected} objects")
                    
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in garbage collector: {e}")
                await asyncio.sleep(300)
                
    async def _resource_optimizer(self):
        """Optimize resource allocation periodically"""
        while self.running:
            try:
                # Analyze resource usage patterns and optimize
                if len(self.memory_history) > 60:  # Have at least 10 minutes of data
                    await self._analyze_resource_patterns()
                    
                await asyncio.sleep(600)  # Optimize every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Error in resource optimizer: {e}")
                await asyncio.sleep(600)
                
    async def _analyze_resource_patterns(self):
        """Analyze resource usage patterns for optimization"""
        try:
            # Analyze last hour of memory usage
            recent_memory = [m["percent"] for m in list(self.memory_history)[-60:]]
            avg_memory = statistics.mean(recent_memory)
            
            # If consistently low usage, we can be more generous with limits
            if avg_memory < 40:
                await self.publish_event("resource.optimization", {
                    "type": "increase_limits",
                    "reason": "low_utilization",
                    "avg_memory_usage": avg_memory
                })
            # If consistently high usage, we need to be more conservative
            elif avg_memory > 70:
                await self.publish_event("resource.optimization", {
                    "type": "decrease_limits", 
                    "reason": "high_utilization",
                    "avg_memory_usage": avg_memory
                })
                
        except Exception as e:
            self.logger.error(f"Error analyzing resource patterns: {e}")
            
    async def _container_scaler(self):
        """Auto-scale container resources"""
        while self.running:
            try:
                if self.auto_scaling_enabled:
                    await self._evaluate_scaling_needs()
                    
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                self.logger.error(f"Error in container scaler: {e}")
                await asyncio.sleep(120)
                
    async def _evaluate_scaling_needs(self):
        """Evaluate if containers need scaling"""
        if not self.memory_history or not self.cpu_history:
            return
            
        current_memory = self.memory_history[-1]["percent"]
        current_cpu = self.cpu_history[-1]["percent"]
        
        # Scale up if resources are heavily utilized
        if current_memory > self.scale_up_threshold or current_cpu > self.scale_up_threshold:
            await self.publish_event("system.scale_up_needed", {
                "memory_usage": current_memory,
                "cpu_usage": current_cpu,
                "reason": "high_resource_utilization"
            })
            
        # Scale down if resources are under-utilized
        elif current_memory < self.scale_down_threshold and current_cpu < self.scale_down_threshold:
            # Only scale down if consistently low for 10 minutes
            if len(self.memory_history) >= 60:
                recent_avg_memory = statistics.mean([m["percent"] for m in list(self.memory_history)[-60:]])
                recent_avg_cpu = statistics.mean([c["percent"] for c in list(self.cpu_history)[-60:]])
                
                if recent_avg_memory < self.scale_down_threshold and recent_avg_cpu < self.scale_down_threshold:
                    await self.publish_event("system.scale_down_opportunity", {
                        "avg_memory_usage": recent_avg_memory,
                        "avg_cpu_usage": recent_avg_cpu,
                        "reason": "sustained_low_utilization"
                    })
                    
    async def _disk_cleanup_manager(self):
        """Manage disk space cleanup"""
        while self.running:
            try:
                if self.disk_history:
                    current_disk = self.disk_history[-1]["percent"]
                    
                    if current_disk > 85:
                        await self._trigger_disk_cleanup()
                        
                await asyncio.sleep(1800)  # Check every 30 minutes
                
            except Exception as e:
                self.logger.error(f"Error in disk cleanup manager: {e}")
                await asyncio.sleep(1800)
                
    async def get_resource_summary(self) -> Dict[str, Any]:
        """Get comprehensive resource summary"""
        current_memory = self.memory_history[-1] if self.memory_history else {}
        current_cpu = self.cpu_history[-1] if self.cpu_history else {}
        current_disk = self.disk_history[-1] if self.disk_history else {}
        
        return {
            "service": "resource_manager",
            "memory": {
                "current_percent": current_memory.get("percent", 0),
                "available_gb": current_memory.get("available_gb", 0),
                "trend": "stable"  # Would calculate actual trend
            },
            "cpu": {
                "current_percent": current_cpu.get("percent", 0),
                "cores": current_cpu.get("cores", 0),
                "load_avg": current_cpu.get("load_avg", [0, 0, 0])
            },
            "disk": {
                "current_percent": current_disk.get("percent", 0),
                "free_gb": current_disk.get("free_gb", 0)
            },
            "containers": {
                "managed": len(self.container_limits),
                "total_allocated_memory_mb": sum(limits.get("memory_mb", 0) for limits in self.container_limits.values())
            },
            "cleanup_history": len(self.memory_cleanup_history),
            "auto_scaling_enabled": self.auto_scaling_enabled,
            "timestamp": datetime.utcnow().isoformat()
        }