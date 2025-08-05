"""Authentication routes"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

from ..config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Use centralized configuration - no hardcoded defaults
JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = settings.jwt_algorithm

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Simple login endpoint"""
    # Use centralized configuration - no hardcoded defaults
    if request.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Determine role based on email (simple role assignment)
    role = "admin" if request.email == "admin@system.com" else "trader"
    
    # Create token with role
    token = jwt.encode(
        {
            "sub": request.email,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    
    return LoginResponse(access_token=token)

@router.post("/token", response_model=LoginResponse)
async def get_token(username: str = Form(), password: str = Form()):
    """OAuth2-style token endpoint for form-based authentication"""
    # Use centralized configuration - no hardcoded defaults
    if password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Determine role based on username (simple role assignment)
    role = "admin" if username == "admin@system.com" else "trader"
    
    # Create token with role
    token = jwt.encode(
        {
            "sub": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    
    return LoginResponse(access_token=token)

# Security moved to dependencies.py for centralized authentication