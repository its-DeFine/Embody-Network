"""
Security API endpoints
Handles PGP-based authentication and one-time key generation
"""

from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import json
from datetime import datetime

from ..infrastructure.security.key_manager import secure_key_manager
from ..dependencies import get_current_user

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/security",
    tags=["security"]
)


class GenerateKeyRequest(BaseModel):
    """Request to generate a one-time key"""
    signed_data: str  # JSON with timestamp, purpose, requester info
    pgp_signature: str  # Detached PGP signature
    purpose: str = "instance_registration"
    validity_hours: int = 24


class TrustKeyRequest(BaseModel):
    """Request to trust a new PGP key"""
    public_key: str
    metadata: Dict = {}


class ValidateKeyRequest(BaseModel):
    """Request to validate a one-time key"""
    key: str
    purpose: str


@router.post("/generate-otk")
async def generate_one_time_key(request: GenerateKeyRequest):
    """
    Generate a one-time key for secure instance registration
    
    The signed_data should be a JSON string containing:
    - timestamp: ISO format timestamp
    - purpose: Same as request.purpose
    - requester: Optional identifier
    
    Example:
    ```
    {
        "timestamp": "2025-01-20T10:30:00Z",
        "purpose": "instance_registration",
        "requester": "production-instance-1"
    }
    ```
    
    This data should be signed with your PGP private key.
    """
    try:
        result = await secure_key_manager.generate_one_time_key(
            pgp_signature=request.pgp_signature,
            signed_data=request.signed_data,
            purpose=request.purpose,
            validity_hours=request.validity_hours
        )
        
        if not result:
            raise HTTPException(status_code=401, detail="Invalid signature or request")
            
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error generating one-time key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-otk")
async def validate_one_time_key(request: ValidateKeyRequest):
    """Validate and consume a one-time key"""
    try:
        result = await secure_key_manager.validate_one_time_key(
            key=request.key,
            purpose=request.purpose
        )
        
        if not result:
            raise HTTPException(status_code=401, detail="Invalid or expired key")
            
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error validating one-time key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trust-key", dependencies=[Depends(get_current_user)])
async def add_trusted_pgp_key(request: TrustKeyRequest):
    """Add a new trusted PGP key (requires authentication)"""
    try:
        success = await secure_key_manager.add_trusted_key(
            public_key=request.public_key,
            metadata=request.metadata
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid PGP key")
            
        return {
            "status": "success",
            "message": "PGP key added to trusted list"
        }
        
    except Exception as e:
        logger.error(f"Error adding trusted key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/master-public-key")
async def get_master_public_keys():
    """Get the master public keys for verification"""
    try:
        # Get RSA public key
        rsa_public_key = await secure_key_manager.redis_client.get("master_rsa_public_key")
        
        # Get PGP public key (if available)
        pgp_public_key = None
        if secure_key_manager.pgp_manager.master_key_fingerprint:
            # Export the master public key
            pgp_public_key = secure_key_manager.pgp_manager.gpg.export_keys(
                secure_key_manager.pgp_manager.master_key_fingerprint
            )
        
        return {
            "rsa_public_key": rsa_public_key.decode() if rsa_public_key else None,
            "pgp_public_key": pgp_public_key,
            "pgp_fingerprint": secure_key_manager.pgp_manager.master_key_fingerprint
        }
        
    except Exception as e:
        logger.error(f"Error getting public keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-signature")
async def verify_pgp_signature(data: str = "", signature: str = ""):
    """Verify a PGP signature"""
    try:
        valid = secure_key_manager.pgp_manager.verify_signature(data, signature)
        
        return {
            "valid": valid,
            "data": data[:100] + "..." if len(data) > 100 else data
        }
        
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        raise HTTPException(status_code=500, detail=str(e))