"""Custom exceptions and error handling"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class PlatformError(Exception):
    """Base exception for platform errors"""
    def __init__(self, message: str, code: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class AgentError(PlatformError):
    """Agent-related errors"""
    pass

class TaskError(PlatformError):
    """Task-related errors"""
    pass

class OrchestrationError(PlatformError):
    """Orchestration-related errors"""
    pass

async def platform_exception_handler(request: Request, exc: PlatformError):
    """Handle platform exceptions"""
    logger.error(f"Platform error: {exc.code} - {exc.message}", extra={
        "error_code": exc.code,
        "details": exc.details,
        "path": request.url.path
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

# Error codes
class ErrorCodes:
    # Agent errors
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_START_FAILED = "AGENT_START_FAILED"
    AGENT_ALREADY_RUNNING = "AGENT_ALREADY_RUNNING"
    
    # Task errors
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ASSIGNMENT_FAILED = "TASK_ASSIGNMENT_FAILED"
    TASK_EXECUTION_FAILED = "TASK_EXECUTION_FAILED"
    
    # Team errors
    TEAM_NOT_FOUND = "TEAM_NOT_FOUND"
    INVALID_TEAM_MEMBERS = "INVALID_TEAM_MEMBERS"
    
    # System errors
    REDIS_CONNECTION_FAILED = "REDIS_CONNECTION_FAILED"
    DOCKER_CONNECTION_FAILED = "DOCKER_CONNECTION_FAILED"
    ORCHESTRATOR_ERROR = "ORCHESTRATOR_ERROR"