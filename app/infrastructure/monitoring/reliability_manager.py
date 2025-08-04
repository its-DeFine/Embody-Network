"""
24/7 Reliability Manager for Trading System

Ensures continuous operation with:
- Rate limiting and request throttling
- Circuit breakers for API failures
- Automatic failover between providers
- Health monitoring and alerting
- Recovery mechanisms
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RateLimiter:
    """Token bucket rate limiter for API calls"""
    requests_per_minute: int
    requests_per_hour: int = 0
    requests_per_day: int = 0
    
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    hourly_requests: List[float] = field(default_factory=list)
    daily_requests: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        self.tokens = float(self.requests_per_minute)
        self.last_update = time.time()
    
    def can_make_request(self) -> bool:
        """Check if request can be made within rate limits"""
        current_time = time.time()
        self._refill_tokens(current_time)
        self._cleanup_old_requests(current_time)
        
        # Check all limits
        if self.tokens < 1:
            return False
            
        if self.requests_per_hour > 0:
            hour_ago = current_time - 3600
            recent_hourly = sum(1 for t in self.hourly_requests if t > hour_ago)
            if recent_hourly >= self.requests_per_hour:
                return False
                
        if self.requests_per_day > 0:
            day_ago = current_time - 86400
            recent_daily = sum(1 for t in self.daily_requests if t > day_ago)
            if recent_daily >= self.requests_per_day:
                return False
        
        return True
    
    def consume_token(self):
        """Consume a token when making request"""
        current_time = time.time()
        self.tokens -= 1
        self.hourly_requests.append(current_time)
        self.daily_requests.append(current_time)
    
    def _refill_tokens(self, current_time: float):
        """Refill tokens based on time passed"""
        time_passed = current_time - self.last_update
        tokens_to_add = (time_passed / 60) * self.requests_per_minute
        self.tokens = min(self.tokens + tokens_to_add, self.requests_per_minute)
        self.last_update = current_time
    
    def _cleanup_old_requests(self, current_time: float):
        """Remove old request timestamps"""
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        
        self.hourly_requests = [t for t in self.hourly_requests if t > hour_ago]
        self.daily_requests = [t for t in self.daily_requests if t > day_ago]


@dataclass
class CircuitBreaker:
    """Circuit breaker for handling API failures"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3
    
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    last_failure_time: Optional[float] = field(default=None)
    half_open_calls: int = field(default=0)
    
    def record_success(self):
        """Record successful API call"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                # Enough successful calls, close circuit
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
                logger.info("Circuit breaker closed - service recovered")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed API call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened - {self.failure_count} failures")
        elif self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, reopen
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            logger.warning("Circuit breaker reopened - recovery test failed")
    
    def can_attempt_request(self) -> bool:
        """Check if request should be attempted"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                time_since_failure = time.time() - self.last_failure_time
                if time_since_failure >= self.recovery_timeout:
                    # Try half-open state
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker half-open - testing recovery")
                    return True
            return False
        
        # Half-open state
        return self.half_open_calls < self.half_open_max_calls


class ReliabilityManager:
    """Manages reliability features for 24/7 operation"""
    
    def __init__(self):
        # Rate limiters for each provider
        self.rate_limiters = {
            # Free tier limits
            "coingecko": RateLimiter(10, 0, 0),  # 10-30/min (conservative)
            "binance": RateLimiter(1200, 0, 0),  # 1200/min
            "coinbase": RateLimiter(10, 0, 0),   # 10/sec = 600/min (conservative)
            "cryptocompare": RateLimiter(50, 2000, 100000),  # Free tier
            "yahoo": RateLimiter(2, 0, 0),       # Very conservative for Yahoo
            "alpha_vantage": RateLimiter(5, 0, 500),  # 5/min, 500/day
            "twelvedata": RateLimiter(8, 0, 800),     # 8/min, 800/day
            "finnhub": RateLimiter(30, 0, 0),         # 30/min
            "polygon": RateLimiter(5, 0, 0),          # 5/min free tier
            "defillama": RateLimiter(20, 0, 0),       # Reasonable estimate
            "ethplorer": RateLimiter(30, 0, 2000),    # 2000/day with freekey
        }
        
        # Circuit breakers for each provider
        self.circuit_breakers = {
            provider: CircuitBreaker() for provider in self.rate_limiters
        }
        
        # Health status
        self.health_status = {
            "start_time": datetime.now(),
            "total_requests": 0,
            "failed_requests": 0,
            "rate_limited_requests": 0,
            "circuit_breaker_trips": 0,
            "provider_health": {}
        }
        
        # Request queue for throttling
        self.request_queue = asyncio.Queue()
        self.processing = False
    
    async def check_rate_limit(self, provider: str) -> bool:
        """Check if request can be made to provider"""
        if provider not in self.rate_limiters:
            return True
        
        limiter = self.rate_limiters[provider]
        if not limiter.can_make_request():
            self.health_status["rate_limited_requests"] += 1
            logger.warning(f"Rate limit hit for {provider}")
            return False
        
        return True
    
    async def check_circuit_breaker(self, provider: str) -> bool:
        """Check if circuit breaker allows request"""
        if provider not in self.circuit_breakers:
            return True
        
        breaker = self.circuit_breakers[provider]
        can_attempt = breaker.can_attempt_request()
        
        if not can_attempt:
            logger.warning(f"Circuit breaker OPEN for {provider}")
            
        return can_attempt
    
    async def execute_with_reliability(
        self, 
        provider: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Optional[Any]:
        """Execute function with reliability features"""
        # Check circuit breaker
        if not await self.check_circuit_breaker(provider):
            return None
        
        # Check rate limit
        if not await self.check_rate_limit(provider):
            # Add exponential backoff for rate limits
            await asyncio.sleep(2 ** min(self.health_status["rate_limited_requests"] % 5, 4))
            return None
        
        # Consume rate limit token
        if provider in self.rate_limiters:
            self.rate_limiters[provider].consume_token()
        
        # Execute with timeout
        try:
            self.health_status["total_requests"] += 1
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=10.0)
            
            # Record success
            if provider in self.circuit_breakers:
                self.circuit_breakers[provider].record_success()
            
            # Update provider health
            if provider not in self.health_status["provider_health"]:
                self.health_status["provider_health"][provider] = {
                    "requests": 0, "failures": 0, "last_success": None
                }
            
            self.health_status["provider_health"][provider]["requests"] += 1
            self.health_status["provider_health"][provider]["last_success"] = datetime.now()
            
            return result
            
        except Exception as e:
            # Record failure
            self.health_status["failed_requests"] += 1
            
            if provider in self.circuit_breakers:
                self.circuit_breakers[provider].record_failure()
            
            if provider in self.health_status["provider_health"]:
                self.health_status["provider_health"][provider]["failures"] += 1
            
            logger.error(f"Provider {provider} failed: {e}")
            return None
    
    async def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        uptime = datetime.now() - self.health_status["start_time"]
        success_rate = 0
        if self.health_status["total_requests"] > 0:
            success_rate = (1 - self.health_status["failed_requests"] / 
                          self.health_status["total_requests"]) * 100
        
        # Check which providers are healthy
        healthy_providers = []
        unhealthy_providers = []
        
        for provider, breaker in self.circuit_breakers.items():
            if breaker.state == CircuitState.CLOSED:
                healthy_providers.append(provider)
            else:
                unhealthy_providers.append({
                    "provider": provider,
                    "state": breaker.state.value,
                    "failures": breaker.failure_count
                })
        
        return {
            "status": "healthy" if len(healthy_providers) > 3 else "degraded",
            "uptime": str(uptime),
            "success_rate": f"{success_rate:.2f}%",
            "total_requests": self.health_status["total_requests"],
            "failed_requests": self.health_status["failed_requests"],
            "rate_limited_requests": self.health_status["rate_limited_requests"],
            "healthy_providers": healthy_providers,
            "unhealthy_providers": unhealthy_providers,
            "provider_details": self.health_status["provider_health"]
        }
    
    async def start_health_monitor(self):
        """Start background health monitoring"""
        while True:
            try:
                # Log health status every 5 minutes
                await asyncio.sleep(300)
                
                health = await self.get_health_report()
                logger.info(f"Health Report: {health['status']} - "
                          f"Success Rate: {health['success_rate']} - "
                          f"Healthy Providers: {len(health['healthy_providers'])}")
                
                # Alert if system is degraded
                if health["status"] == "degraded":
                    logger.warning("System health degraded - consider intervention")
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")


# Global instance
reliability_manager = ReliabilityManager()


# Example integration with market data service
async def reliable_get_price(provider: str, symbol: str, get_price_func):
    """Wrapper for reliable price fetching"""
    return await reliability_manager.execute_with_reliability(
        provider,
        get_price_func,
        symbol
    )