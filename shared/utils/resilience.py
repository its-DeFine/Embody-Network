"""
Resilience patterns - Circuit breakers, retries, and monitoring
"""
from pybreaker import CircuitBreaker
import structlog
from functools import wraps
from typing import Callable, Any
import asyncio

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Get structured logger
def get_logger(name: str):
    """Get a structured logger instance"""
    return structlog.get_logger(name)


# Circuit breaker configurations
class CircuitBreakers:
    """Centralized circuit breakers for external services"""
    
    # Exchange API circuit breaker
    exchange_api = CircuitBreaker(
        fail_max=5,
        reset_timeout=60,
        exclude=[KeyError, ValueError]  # Don't trip on client errors
    )
    
    # Database circuit breaker
    database = CircuitBreaker(
        fail_max=3,
        reset_timeout=30
    )
    
    # Message queue circuit breaker
    message_queue = CircuitBreaker(
        fail_max=5,
        reset_timeout=45
    )
    
    # External services circuit breaker
    external_service = CircuitBreaker(
        fail_max=10,
        reset_timeout=120
    )


def with_circuit_breaker(breaker: CircuitBreaker):
    """Decorator to apply circuit breaker to a function"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker(func)(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker(func)(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Monitoring helpers
class MetricsCollector:
    """Collect metrics for Prometheus"""
    
    def __init__(self):
        from prometheus_client import Counter, Histogram, Gauge
        
        # Request metrics
        self.request_count = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint']
        )
        
        # Agent metrics
        self.agents_created = Counter(
            'agents_created_total',
            'Total number of agents created',
            ['agent_type', 'customer_tier']
        )
        
        self.active_agents = Gauge(
            'active_agents',
            'Number of currently active agents',
            ['agent_type']
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half-open)',
            ['service']
        )
        
        # Task metrics
        self.task_execution_duration = Histogram(
            'task_execution_duration_seconds',
            'Task execution duration',
            ['task_type', 'agent_type']
        )
        
        self.task_success_rate = Counter(
            'task_success_total',
            'Number of successful tasks',
            ['task_type']
        )
        
        self.task_failure_rate = Counter(
            'task_failure_total',
            'Number of failed tasks',
            ['task_type', 'failure_reason']
        )
    
    def record_circuit_breaker_state(self, service: str, breaker: CircuitBreaker):
        """Record circuit breaker state"""
        state_map = {
            'closed': 0,
            'open': 1,
            'half-open': 2
        }
        state = breaker.current_state
        self.circuit_breaker_state.labels(service=service).set(state_map.get(state, -1))


# Global metrics instance
metrics = MetricsCollector()


# Rate limiting helper
class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = asyncio.get_event_loop().time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens, returns True if successful"""
        async with self.lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Add new tokens
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_for_token(self, tokens: int = 1):
        """Wait until tokens are available"""
        while not await self.acquire(tokens):
            wait_time = tokens / self.rate
            await asyncio.sleep(wait_time)


# Timeout decorator
def with_timeout(seconds: float):
    """Decorator to add timeout to async functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
        return wrapper
    return decorator