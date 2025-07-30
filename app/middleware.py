"""Middleware for logging, monitoring, and request tracking"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
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
        
        # Add request ID to all logs in this context
        with logger.contextvars.bind(request_id=request_id):
            logger.info(f"Request started: {request.method} {request.url.path}")
            
            try:
                response = await call_next(request)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Log completion
                logger.info(
                    f"Request completed: {request.method} {request.url.path}",
                    extra={
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