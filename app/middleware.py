"""Middleware for logging, monitoring, security, and request tracking"""
import time
import uuid
from typing import Callable, Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Add request ID and structured logging to all requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log with request ID
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"request_id": request_id}
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log completion
            logger.info(
                f"Request completed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = str(duration)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            raise

class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect metrics for monitoring"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # In production, send to Prometheus/StatsD
            # For now, just log
            logger.debug(
                "Request metrics",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration": duration
                }
            )
            
            return response
            
        except Exception as e:
            # Track errors
            logger.error(
                "Request error metrics",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e)
                }
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse and attacks"""
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        current_time = time.time()
        
        # Initialize client tracking
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []
        
        # Clean old requests (older than 1 minute)
        minute_ago = current_time - 60
        self.client_requests[client_ip] = [
            req_time for req_time in self.client_requests[client_ip] 
            if req_time > minute_ago
        ]
        
        # Check rate limit
        if len(self.client_requests[client_ip]) >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for {client_ip}: {len(self.client_requests[client_ip])} requests"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record this request
        self.client_requests[client_ip].append(current_time)
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add critical security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class TradingSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security for financial trading endpoints"""
    
    def __init__(self, app):
        super().__init__(app)
        self.trading_attempts: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Enhanced rate limiting for trading endpoints
        if request.url.path.startswith("/api/v1/trading/"):
            client_ip = request.client.host
            current_time = time.time()
            
            # Initialize tracking
            if client_ip not in self.trading_attempts:
                self.trading_attempts[client_ip] = []
            
            # Clean old attempts (older than 5 minutes)
            five_minutes_ago = current_time - 300
            self.trading_attempts[client_ip] = [
                attempt_time for attempt_time in self.trading_attempts[client_ip] 
                if attempt_time > five_minutes_ago
            ]
            
            # Stricter limits for trading operations (financial protection)
            max_trading_attempts = 10  # 10 trading operations per 5 minutes
            
            if len(self.trading_attempts[client_ip]) >= max_trading_attempts:
                logger.warning(
                    f"Trading rate limit exceeded for {client_ip}: {len(self.trading_attempts[client_ip])} attempts"
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Trading rate limit exceeded",
                        "message": f"Maximum {max_trading_attempts} trading operations per 5 minutes allowed for financial security",
                        "retry_after": 300
                    },
                    headers={"Retry-After": "300"}
                )
            
            # Record this attempt
            self.trading_attempts[client_ip].append(current_time)
        
        return await call_next(request)