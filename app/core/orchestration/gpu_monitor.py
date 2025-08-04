"""
GPU Memory Management and Monitoring

This module provides comprehensive GPU memory management, monitoring,
and optimization capabilities for the platform.
"""

import asyncio
import json
import logging
import subprocess
import psutil
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import os

try:
    import torch
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except ImportError:
    torch = None
    pynvml = None
    NVML_AVAILABLE = False

from ...dependencies import get_redis

logger = logging.getLogger(__name__)


class GPUMemoryManager:
    """Manages GPU memory allocation and optimization"""
    
    def __init__(self):
        self.redis = None
        self.memory_thresholds = {
            "critical": 0.95,  # 95% usage
            "high": 0.85,      # 85% usage
            "medium": 0.70,    # 70% usage
            "low": 0.50        # 50% usage
        }
        self.cleanup_policies = {
            "aggressive": 0.80,  # Free memory when above 80%
            "moderate": 0.90,    # Free memory when above 90%
            "conservative": 0.95 # Free memory when above 95%
        }
        self.current_policy = "moderate"
        
    async def initialize(self):
        """Initialize memory manager"""
        self.redis = await get_redis()
        logger.info("GPU Memory Manager initialized")
        
    async def get_memory_stats(self, device_id: int) -> Dict[str, Any]:
        """Get detailed memory statistics for a GPU"""
        stats = {
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if NVML_AVAILABLE:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
                
                # Memory info
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                stats["memory"] = {
                    "total": mem_info.total,
                    "used": mem_info.used,
                    "free": mem_info.free,
                    "percent_used": (mem_info.used / mem_info.total) * 100
                }
                
                # Temperature
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                stats["temperature_c"] = temp
                
                # Power usage
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
                    power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
                    stats["power"] = {
                        "current_w": power,
                        "limit_w": power_limit,
                        "percent": (power / power_limit) * 100
                    }
                except:
                    stats["power"] = None
                    
                # Utilization
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                stats["utilization"] = {
                    "gpu": util.gpu,
                    "memory": util.memory
                }
                
                # Running processes
                processes = []
                try:
                    procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                    for proc in procs:
                        processes.append({
                            "pid": proc.pid,
                            "memory_mb": proc.usedGpuMemory / 1024 / 1024,
                            "name": self._get_process_name(proc.pid)
                        })
                except:
                    pass
                stats["processes"] = processes
                
            except Exception as e:
                logger.error(f"Error getting GPU stats via NVML: {e}")
                
        elif torch is not None and torch.cuda.is_available():
            # Fallback to PyTorch
            try:
                stats["memory"] = {
                    "total": torch.cuda.get_device_properties(device_id).total_memory,
                    "used": torch.cuda.memory_allocated(device_id),
                    "free": torch.cuda.get_device_properties(device_id).total_memory - torch.cuda.memory_allocated(device_id),
                    "percent_used": (torch.cuda.memory_allocated(device_id) / torch.cuda.get_device_properties(device_id).total_memory) * 100
                }
            except:
                pass
                
        return stats
        
    async def monitor_memory_usage(self):
        """Monitor memory usage across all GPUs"""
        if not NVML_AVAILABLE:
            return
            
        device_count = pynvml.nvmlDeviceGetCount()
        alerts = []
        
        for device_id in range(device_count):
            stats = await self.get_memory_stats(device_id)
            
            if "memory" in stats:
                percent_used = stats["memory"]["percent_used"]
                
                # Check thresholds
                alert_level = None
                for level, threshold in sorted(self.memory_thresholds.items(), key=lambda x: x[1], reverse=True):
                    if percent_used >= threshold * 100:
                        alert_level = level
                        break
                        
                if alert_level:
                    alerts.append({
                        "device_id": device_id,
                        "level": alert_level,
                        "percent_used": percent_used,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                # Store stats
                await self.redis.set(
                    f"gpu:memory:stats:{device_id}",
                    json.dumps(stats),
                    ex=300  # Expire after 5 minutes
                )
                
        # Process alerts
        for alert in alerts:
            await self._handle_memory_alert(alert)
            
        return alerts
        
    async def _handle_memory_alert(self, alert: Dict[str, Any]):
        """Handle memory alerts"""
        device_id = alert["device_id"]
        level = alert["level"]
        
        logger.warning(f"GPU {device_id} memory alert: {level} ({alert['percent_used']:.1f}% used)")
        
        # Store alert
        await self.redis.lpush(
            "gpu:memory:alerts",
            json.dumps(alert)
        )
        
        # Trim old alerts (keep last 100)
        await self.redis.ltrim("gpu:memory:alerts", 0, 99)
        
        # Take action based on level and policy
        if level == "critical" or (level == "high" and self.current_policy == "aggressive"):
            await self.free_memory(device_id)
            
    async def free_memory(self, device_id: int, target_percent: Optional[float] = None):
        """Free GPU memory by various strategies"""
        if target_percent is None:
            target_percent = self.cleanup_policies[self.current_policy]
            
        logger.info(f"Attempting to free memory on GPU {device_id} to {target_percent*100}%")
        
        strategies_applied = []
        
        # Strategy 1: Clear PyTorch cache
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
            strategies_applied.append("pytorch_cache_cleared")
            
        # Strategy 2: Request agents to reduce batch sizes
        agent_keys = await self.redis.keys(f"gpu:allocation:*")
        for key in agent_keys:
            allocation = await self.redis.get(key)
            if allocation:
                alloc_data = json.loads(allocation)
                if alloc_data.get("device_id") == device_id:
                    agent_id = key.decode().split(":")[-1]
                    # Send memory pressure signal
                    await self.redis.publish(
                        f"agent:{agent_id}:control",
                        json.dumps({
                            "command": "reduce_memory",
                            "reason": "memory_pressure",
                            "device_id": device_id
                        })
                    )
                    strategies_applied.append(f"requested_{agent_id}_reduce_memory")
                    
        # Strategy 3: Kill low-priority processes (if configured)
        if level == "critical" and os.getenv("ALLOW_GPU_PROCESS_KILL", "false").lower() == "true":
            await self._kill_low_priority_processes(device_id)
            strategies_applied.append("killed_low_priority_processes")
            
        # Log cleanup attempt
        await self.redis.lpush(
            "gpu:memory:cleanup_log",
            json.dumps({
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "strategies": strategies_applied,
                "target_percent": target_percent
            })
        )
        
        return strategies_applied
        
    async def _kill_low_priority_processes(self, device_id: int):
        """Kill low-priority GPU processes (use with caution)"""
        # This is a placeholder - implement based on your priority system
        logger.warning(f"Would kill low-priority processes on GPU {device_id} (not implemented)")
        
    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID"""
        try:
            return psutil.Process(pid).name()
        except:
            return f"pid_{pid}"
            
    async def get_memory_history(self, device_id: int, hours: int = 1) -> List[Dict[str, Any]]:
        """Get memory usage history"""
        history = []
        
        # Get from Redis time series (if implemented)
        # For now, return current stats
        stats = await self.get_memory_stats(device_id)
        if stats:
            history.append(stats)
            
        return history
        
    async def predict_memory_usage(self, device_id: int, minutes_ahead: int = 5) -> Dict[str, Any]:
        """Predict future memory usage based on trends"""
        # Simple prediction based on current trend
        history = await self.get_memory_history(device_id)
        
        if not history:
            return {"error": "No history available"}
            
        current = history[-1]["memory"]["percent_used"]
        
        # Simple linear prediction (can be enhanced with ML)
        if len(history) > 1:
            trend = current - history[-2]["memory"]["percent_used"]
            predicted = current + (trend * minutes_ahead)
        else:
            predicted = current
            
        return {
            "device_id": device_id,
            "current_percent": current,
            "predicted_percent": min(100, max(0, predicted)),
            "minutes_ahead": minutes_ahead,
            "prediction_time": datetime.utcnow().isoformat()
        }
        
    async def optimize_memory_allocation(self) -> Dict[str, Any]:
        """Optimize memory allocation across all GPUs"""
        if not NVML_AVAILABLE:
            return {"error": "NVML not available"}
            
        device_count = pynvml.nvmlDeviceGetCount()
        optimization_plan = {
            "timestamp": datetime.utcnow().isoformat(),
            "current_allocations": {},
            "recommended_changes": []
        }
        
        # Gather current state
        gpu_stats = []
        for device_id in range(device_count):
            stats = await self.get_memory_stats(device_id)
            gpu_stats.append(stats)
            
        # Get agent allocations
        agent_allocations = {}
        allocation_keys = await self.redis.keys("gpu:allocation:*")
        for key in allocation_keys:
            allocation = await self.redis.get(key)
            if allocation:
                agent_id = key.decode().split(":")[-1]
                agent_allocations[agent_id] = json.loads(allocation)
                
        # Analyze and optimize
        for agent_id, allocation in agent_allocations.items():
            current_device = allocation["device_id"]
            current_stats = gpu_stats[current_device]
            
            # Find better GPU if current is overloaded
            if current_stats["memory"]["percent_used"] > 80:
                best_device = None
                min_usage = 100
                
                for device_id, stats in enumerate(gpu_stats):
                    if device_id != current_device and stats["memory"]["percent_used"] < min_usage:
                        min_usage = stats["memory"]["percent_used"]
                        best_device = device_id
                        
                if best_device is not None and min_usage < 60:
                    optimization_plan["recommended_changes"].append({
                        "agent_id": agent_id,
                        "from_device": current_device,
                        "to_device": best_device,
                        "reason": f"Load balancing (current: {current_stats['memory']['percent_used']:.1f}%, target: {min_usage:.1f}%)"
                    })
                    
        return optimization_plan
        
    async def set_memory_policy(self, policy: str):
        """Set memory management policy"""
        if policy in self.cleanup_policies:
            self.current_policy = policy
            await self.redis.set("gpu:memory:policy", policy)
            logger.info(f"Memory policy set to: {policy}")
            return True
        return False
        
    async def get_memory_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent memory alerts"""
        alerts = await self.redis.lrange("gpu:memory:alerts", 0, limit - 1)
        return [json.loads(alert) for alert in alerts]


# Global memory manager instance
gpu_memory_manager = GPUMemoryManager()