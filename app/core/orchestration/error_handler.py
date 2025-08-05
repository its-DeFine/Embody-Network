"""
Comprehensive Error Handling Service

Replaces bare except clauses with proper error handling:
- Structured error categorization
- Error recovery strategies
- Error reporting and alerting
- Error pattern analysis
- Circuit breaker implementation
"""
import asyncio
import logging
import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Type, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import functools

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for better handling"""
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    RESOURCE = "resource"
    SECURITY = "security"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Context information for errors"""
    error_id: str
    timestamp: str
    service: str
    function: str
    severity: ErrorSeverity
    category: ErrorCategory
    error_type: str
    message: str
    traceback: str
    context_data: Dict[str, Any]
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0


class ErrorRecoveryStrategy:
    """Base class for error recovery strategies"""
    
    def __init__(self, max_retries: int = 3, backoff_multiplier: float = 2.0):
        self.max_retries = max_retries
        self.backoff_multiplier = backoff_multiplier
        
    async def can_recover(self, error_context: ErrorContext) -> bool:
        """Check if error can be recovered from"""
        return error_context.retry_count < self.max_retries
        
    async def recover(self, error_context: ErrorContext, original_func: Callable, *args, **kwargs) -> Any:
        """Attempt to recover from error"""
        raise NotImplementedError
        
    def calculate_backoff_delay(self, retry_count: int) -> float:
        """Calculate backoff delay for retry"""
        return min(60.0, (self.backoff_multiplier ** retry_count))  # Cap at 60 seconds


class NetworkErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for network errors"""
    
    async def can_recover(self, error_context: ErrorContext) -> bool:
        # Network errors are often transient
        return (error_context.category == ErrorCategory.NETWORK and 
                error_context.retry_count < self.max_retries)
                
    async def recover(self, error_context: ErrorContext, original_func: Callable, *args, **kwargs) -> Any:
        """Retry network operations with exponential backoff"""
        delay = self.calculate_backoff_delay(error_context.retry_count)
        await asyncio.sleep(delay)
        
        return await original_func(*args, **kwargs)


class ResourceErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for resource errors"""
    
    async def can_recover(self, error_context: ErrorContext) -> bool:
        # Resource errors might be recoverable with cleanup
        return (error_context.category == ErrorCategory.RESOURCE and
                error_context.retry_count < 2)  # Fewer retries for resource errors
                
    async def recover(self, error_context: ErrorContext, original_func: Callable, *args, **kwargs) -> Any:
        """Attempt resource cleanup and retry"""
        # Trigger garbage collection
        import gc
        gc.collect()
        
        # Wait a bit for resources to free up
        await asyncio.sleep(5.0)
        
        return await original_func(*args, **kwargs)


class DatabaseErrorRecovery(ErrorRecoveryStrategy):
    """Recovery strategy for database errors"""
    
    async def can_recover(self, error_context: ErrorContext) -> bool:
        # Database connection errors are often recoverable
        return (error_context.category == ErrorCategory.DATABASE and
                "connection" in error_context.message.lower() and
                error_context.retry_count < self.max_retries)
                
    async def recover(self, error_context: ErrorContext, original_func: Callable, *args, **kwargs) -> Any:
        """Retry database operations with connection refresh"""
        delay = self.calculate_backoff_delay(error_context.retry_count)
        await asyncio.sleep(delay)
        
        # In a real implementation, would refresh database connection here
        return await original_func(*args, **kwargs)


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        
    def should_allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if (datetime.utcnow() - self.last_failure_time).seconds >= self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
            
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = "closed"
        
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"🔴 Circuit breaker opened after {self.failure_count} failures")


class ErrorHandler:
    """Comprehensive error handling service"""
    
    def __init__(self):
        self.redis = None
        self.error_history: deque = deque(maxlen=1000)
        self.error_patterns: Dict[str, int] = defaultdict(int)
        self.recovery_strategies: Dict[ErrorCategory, ErrorRecoveryStrategy] = {
            ErrorCategory.NETWORK: NetworkErrorRecovery(),
            ErrorCategory.RESOURCE: ResourceErrorRecovery(),
            ErrorCategory.DATABASE: DatabaseErrorRecovery(),
        }
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.running = False
        
    async def initialize(self, redis):
        """Initialize error handler"""
        self.redis = redis
        
        # Load error patterns from Redis
        await self._load_error_patterns()
        
        logger.info("🛡️ Error handler initialized")
        
    async def start(self):
        """Start error handler background tasks"""
        self.running = True
        
        asyncio.create_task(self._error_pattern_analyzer())
        asyncio.create_task(self._error_reporter())
        asyncio.create_task(self._circuit_breaker_monitor())
        
        logger.info("✅ Error handler started")
        
    async def stop(self):
        """Stop error handler"""
        self.running = False
        logger.info("🛑 Error handler stopped")
        
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and message"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Network errors
        if any(keyword in error_message for keyword in ['connection', 'timeout', 'network', 'dns', 'socket']):
            return ErrorCategory.NETWORK
            
        # Database errors
        if any(keyword in error_message for keyword in ['database', 'redis', 'sql', 'connection pool']):
            return ErrorCategory.DATABASE
            
        # Resource errors
        if any(keyword in error_message for keyword in ['memory', 'disk', 'cpu', 'resource']):
            return ErrorCategory.RESOURCE
            
        # Validation errors
        if any(keyword in error_message for keyword in ['validation', 'invalid', 'format']):
            return ErrorCategory.VALIDATION
            
        # Security errors
        if any(keyword in error_message for keyword in ['unauthorized', 'forbidden', 'authentication', 'permission']):
            return ErrorCategory.SECURITY
            
        # External API errors
        if any(keyword in error_message for keyword in ['api', 'http', 'request', 'response']):
            return ErrorCategory.EXTERNAL_API
            
        # Default to system error
        return ErrorCategory.SYSTEM
        
    def determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity"""
        error_message = str(error).lower()
        
        # Critical errors
        if any(keyword in error_message for keyword in ['critical', 'fatal', 'emergency', 'security']):
            return ErrorSeverity.CRITICAL
            
        # High severity
        if category in [ErrorCategory.SECURITY, ErrorCategory.DATABASE] or \
           any(keyword in error_message for keyword in ['permission', 'unauthorized', 'connection']):
            return ErrorSeverity.HIGH
            
        # Medium severity  
        if category in [ErrorCategory.NETWORK, ErrorCategory.RESOURCE, ErrorCategory.EXTERNAL_API]:
            return ErrorSeverity.MEDIUM
            
        # Default to low
        return ErrorSeverity.LOW
        
    async def handle_error(
        self,
        error: Exception,
        service: str,
        function: str,
        context_data: Dict[str, Any] = None,
        original_func: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Any:
        """Handle error with recovery attempts"""
        
        # Create error context
        error_context = ErrorContext(
            error_id=f"{datetime.utcnow().timestamp()}_{hash(str(error)) % 10000}",
            timestamp=datetime.utcnow().isoformat(),
            service=service,
            function=function,
            severity=self.determine_severity(error, self.categorize_error(error)),
            category=self.categorize_error(error),
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
            context_data=context_data or {},
            retry_count=kwargs.get('_retry_count', 0)
        )
        
        # Record error
        await self._record_error(error_context)
        
        # Check circuit breaker
        circuit_key = f"{service}:{function}"
        if circuit_key not in self.circuit_breakers:
            self.circuit_breakers[circuit_key] = CircuitBreaker()
            
        circuit_breaker = self.circuit_breakers[circuit_key]
        
        if not circuit_breaker.should_allow_request():
            logger.error(f"🔴 Circuit breaker open for {circuit_key}, rejecting request")
            raise Exception(f"Circuit breaker open for {service}:{function}")
            
        # Attempt recovery if possible
        if original_func and error_context.category in self.recovery_strategies:
            recovery_strategy = self.recovery_strategies[error_context.category]
            
            if await recovery_strategy.can_recover(error_context):
                try:
                    error_context.recovery_attempted = True
                    error_context.retry_count += 1
                    
                    # Add retry count to kwargs to track retries
                    kwargs['_retry_count'] = error_context.retry_count
                    
                    result = await recovery_strategy.recover(error_context, original_func, *args, **kwargs)
                    
                    error_context.recovery_successful = True
                    circuit_breaker.record_success()
                    
                    logger.info(f"✅ Recovered from {error_context.category} error in {service}:{function}")
                    
                    # Update error record with recovery success
                    await self._update_error_record(error_context)
                    
                    return result
                    
                except Exception as recovery_error:
                    logger.error(f"❌ Recovery failed for {service}:{function}: {recovery_error}")
                    circuit_breaker.record_failure()
                    
                    # If recovery fails, raise the original error
                    raise error
            else:
                circuit_breaker.record_failure()
                raise error
        else:
            circuit_breaker.record_failure()
            raise error
            
    async def _record_error(self, error_context: ErrorContext):
        """Record error for analysis"""
        # Add to local history
        self.error_history.append(error_context)
        
        # Update error patterns
        pattern_key = f"{error_context.category}:{error_context.error_type}"
        self.error_patterns[pattern_key] += 1
        
        # Store in Redis
        await self.redis.lpush(
            "errors:history",
            json.dumps(asdict(error_context))
        )
        
        # Keep only recent errors in Redis
        await self.redis.ltrim("errors:history", 0, 999)
        
        # Log error appropriately
        if error_context.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"🚨 CRITICAL ERROR in {error_context.service}:{error_context.function} - {error_context.message}")
        elif error_context.severity == ErrorSeverity.HIGH:
            logger.error(f"❌ HIGH ERROR in {error_context.service}:{error_context.function} - {error_context.message}")
        elif error_context.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"⚠️ MEDIUM ERROR in {error_context.service}:{error_context.function} - {error_context.message}")
        else:
            logger.info(f"ℹ️ LOW ERROR in {error_context.service}:{error_context.function} - {error_context.message}")
            
    async def _update_error_record(self, error_context: ErrorContext):
        """Update error record with recovery information"""
        # Update in local history
        for i, stored_context in enumerate(self.error_history):
            if stored_context.error_id == error_context.error_id:
                self.error_history[i] = error_context
                break
                
        # Update in Redis (simplified - in production would maintain a proper index)
        await self.redis.lpush(
            "errors:recovered",
            json.dumps(asdict(error_context))
        )
        
    async def _load_error_patterns(self):
        """Load error patterns from Redis"""
        try:
            patterns = await self.redis.hgetall("errors:patterns")
            for pattern, count in patterns.items():
                self.error_patterns[pattern.decode()] = int(count)
                
            logger.info(f"📊 Loaded {len(self.error_patterns)} error patterns")
            
        except Exception as e:
            logger.error(f"Failed to load error patterns: {e}")
            
    async def _error_pattern_analyzer(self):
        """Analyze error patterns and generate insights"""
        while self.running:
            try:
                # Analyze patterns every 5 minutes
                await asyncio.sleep(300)
                
                if len(self.error_history) < 10:
                    continue
                    
                # Analyze recent errors (last hour)
                recent_errors = [
                    error for error in self.error_history
                    if (datetime.utcnow() - datetime.fromisoformat(error.timestamp)).seconds < 3600
                ]
                
                if len(recent_errors) > 20:  # High error rate
                    await self._publish_error_alert("high_error_rate", {
                        "error_count": len(recent_errors),
                        "time_window": "1_hour",
                        "top_errors": self._get_top_error_patterns(recent_errors, 5)
                    })
                    
                # Store patterns in Redis
                for pattern, count in self.error_patterns.items():
                    await self.redis.hset("errors:patterns", pattern, count)
                    
            except Exception as e:
                logger.error(f"Error in pattern analyzer: {e}")
                
    async def _error_reporter(self):
        """Generate error reports"""
        while self.running:
            try:
                # Generate reports every hour
                await asyncio.sleep(3600)
                
                report = await self._generate_error_report()
                
                # Publish report
                await self.redis.publish(
                    "orchestrator:events",
                    json.dumps({
                        "type": "system.error_report",
                        "source": "error_handler",
                        "data": report,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                )
                
            except Exception as e:
                logger.error(f"Error in error reporter: {e}")
                
    async def _circuit_breaker_monitor(self):
        """Monitor circuit breaker states"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                open_breakers = [
                    key for key, breaker in self.circuit_breakers.items()
                    if breaker.state == "open"
                ]
                
                if open_breakers:
                    await self._publish_error_alert("circuit_breakers_open", {
                        "open_breakers": open_breakers,
                        "count": len(open_breakers)
                    })
                    
            except Exception as e:
                logger.error(f"Error in circuit breaker monitor: {e}")
                
    def _get_top_error_patterns(self, errors: List[ErrorContext], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get top error patterns from error list"""
        pattern_counts = defaultdict(int)
        
        for error in errors:
            pattern_key = f"{error.category}:{error.error_type}"
            pattern_counts[pattern_key] += 1
            
        # Sort by count and return top N
        sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"pattern": pattern, "count": count}
            for pattern, count in sorted_patterns[:top_n]
        ]
        
    async def _generate_error_report(self) -> Dict[str, Any]:
        """Generate comprehensive error report"""
        recent_errors = [
            error for error in self.error_history
            if (datetime.utcnow() - datetime.fromisoformat(error.timestamp)).seconds < 3600
        ]
        
        return {
            "total_errors_hour": len(recent_errors),
            "total_errors_stored": len(self.error_history),
            "error_by_severity": {
                severity.value: len([e for e in recent_errors if e.severity == severity])
                for severity in ErrorSeverity
            },
            "error_by_category": {
                category.value: len([e for e in recent_errors if e.category == category])
                for category in ErrorCategory
            },
            "recovery_success_rate": self._calculate_recovery_rate(recent_errors),
            "top_error_patterns": self._get_top_error_patterns(recent_errors),
            "circuit_breaker_status": {
                key: breaker.state
                for key, breaker in self.circuit_breakers.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def _calculate_recovery_rate(self, errors: List[ErrorContext]) -> float:
        """Calculate error recovery success rate"""
        attempted_recoveries = [e for e in errors if e.recovery_attempted]
        
        if not attempted_recoveries:
            return 0.0
            
        successful_recoveries = [e for e in attempted_recoveries if e.recovery_successful]
        
        return (len(successful_recoveries) / len(attempted_recoveries)) * 100
        
    async def _publish_error_alert(self, alert_type: str, data: Dict[str, Any]):
        """Publish error-related alert"""
        alert = {
            "type": f"system.error_alert.{alert_type}",
            "source": "error_handler",
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.redis.publish("orchestrator:events", json.dumps(alert))
        logger.warning(f"🚨 Error alert: {alert_type} - {data}")


# Decorator for automatic error handling
def handle_errors(
    service: str,
    function: str = None,
    category: ErrorCategory = None,
    severity: ErrorSeverity = None
):
    """Decorator for automatic error handling"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Use global error handler if available
                if hasattr(func, '_error_handler'):
                    error_handler = func._error_handler
                else:
                    error_handler = ErrorHandler()  # Create local instance
                    
                return await error_handler.handle_error(
                    error=e,
                    service=service,
                    function=function or func.__name__,
                    original_func=func,
                    *args,
                    **kwargs
                )
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # For sync functions, just log and re-raise with better context
                logger.error(f"Error in {service}:{function or func.__name__}: {e}")
                raise
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Global error handler instance
error_handler = ErrorHandler()