"""Authentication routes"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
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
    
    # Create token
    token = jwt.encode(
        {
            "sub": request.email,
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    
    return LoginResponse(access_token=token)

# Security
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return current user"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")