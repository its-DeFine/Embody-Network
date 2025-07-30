"""Retry logic and circuit breaker patterns"""
import asyncio
import functools
import logging
from typing import TypeVar, Callable, Optional, Type, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        
    def call_failed(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
    def call_succeeded(self):
        """Record a successful call"""
        self.failure_count = 0
        self.state = "closed"
        
    def can_execute(self) -> bool:
        """Check if we can execute a call"""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            if self.last_failure_time:
                if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                    self.state = "half-open"
                    return True
            return False
            
        return True  # half-open state

def with_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries - 1:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {retries} attempts failed for {func.__name__}")
                        
            raise last_exception
            
        return wrapper
    return decorator

class RetryableTask:
    """Wrapper for tasks that can be retried"""
    
    def __init__(self, task_id: str, max_retries: int = 3):
        self.task_id = task_id
        self.max_retries = max_retries
        self.attempts = 0
        self.last_error: Optional[str] = None
        
    async def execute(self, func: Callable, *args, **kwargs):
        """Execute task with retry logic"""
        while self.attempts < self.max_retries:
            try:
                self.attempts += 1
                result = await func(*args, **kwargs)
                logger.info(f"Task {self.task_id} succeeded on attempt {self.attempts}")
                return result
            except Exception as e:
                self.last_error = str(e)
                logger.error(
                    f"Task {self.task_id} failed on attempt {self.attempts}: {e}"
                )
                
                if self.attempts < self.max_retries:
                    wait_time = self.attempts * 2  # Simple linear backoff
                    await asyncio.sleep(wait_time)
                else:
                    raise
                    
        raise Exception(f"Task {self.task_id} failed after {self.max_retries} attempts")