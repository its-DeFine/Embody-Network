"""Authentication routes"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Simple login endpoint"""
    # In production, verify against database
    if request.password != os.getenv("ADMIN_PASSWORD", "admin"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = jwt.encode(
        {
            "sub": request.email,
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    
    return LoginResponse(access_token=token)