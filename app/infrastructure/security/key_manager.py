"""
Secure Key Management System
Handles PGP-based authentication and one-time keys
"""

import os
import json
import secrets
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
import gnupg
import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from pydantic import BaseModel
import redis.asyncio as redis

from ...dependencies import get_redis
from ...config import settings

import logging
logger = logging.getLogger(__name__)


class OneTimeKey(BaseModel):
    """One-time key model"""
    key: str
    instance_id: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    used: bool = False
    used_at: Optional[datetime] = None
    created_by_fingerprint: str  # PGP key fingerprint
    purpose: str  # "instance_registration", "api_access", etc.


class PGPKeyManager:
    """
    Manages PGP keys for secure authentication
    """
    
    def __init__(self):
        self.gpg_home = os.environ.get("GPG_HOME", "/app/data/.gnupg")
        os.makedirs(self.gpg_home, exist_ok=True)
        self.gpg = gnupg.GPG(gnupghome=self.gpg_home)
        self.master_key_fingerprint = None
        self.trusted_keys: Dict[str, Dict] = {}  # fingerprint -> key info
        
    async def initialize(self):
        """Initialize PGP key manager"""
        # Load master public key from environment or file
        master_key_path = os.environ.get("MASTER_PGP_PUBLIC_KEY_PATH")
        if master_key_path and os.path.exists(master_key_path):
            with open(master_key_path, 'r') as f:
                result = self.gpg.import_keys(f.read())
                if result.count > 0:
                    self.master_key_fingerprint = result.fingerprints[0]
                    logger.info(f"Imported master PGP key: {self.master_key_fingerprint}")
                    
        # Load trusted keys from configuration
        await self._load_trusted_keys()
        
    async def _load_trusted_keys(self):
        """Load trusted PGP keys from Redis"""
        redis_client = await get_redis()
        keys = await redis_client.hgetall("trusted_pgp_keys")
        
        for fingerprint, key_data in keys.items():
            self.trusted_keys[fingerprint.decode()] = json.loads(key_data)
            
    def verify_signature(self, data: str, signature: str, expected_fingerprint: Optional[str] = None) -> bool:
        """Verify PGP signature"""
        try:
            verified = self.gpg.verify_data(signature, data.encode())
            
            if not verified.valid:
                return False
                
            if expected_fingerprint and verified.fingerprint != expected_fingerprint:
                logger.warning(f"Signature fingerprint mismatch: {verified.fingerprint} != {expected_fingerprint}")
                return False
                
            # Check if key is trusted
            if verified.fingerprint not in self.trusted_keys and verified.fingerprint != self.master_key_fingerprint:
                logger.warning(f"Signature from untrusted key: {verified.fingerprint}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
            
    def sign_data(self, data: str, key_fingerprint: Optional[str] = None) -> Optional[str]:
        """Sign data with PGP key"""
        try:
            # Use master key if no specific key provided
            if not key_fingerprint:
                key_fingerprint = self.master_key_fingerprint
                
            signed = self.gpg.sign(data, keyid=key_fingerprint, detach=True)
            
            if signed.data:
                return str(signed)
            return None
            
        except Exception as e:
            logger.error(f"Signing error: {e}")
            return None


class SecureKeyManager:
    """
    Manages secure one-time keys and API keys
    """
    
    def __init__(self):
        self.pgp_manager = PGPKeyManager()
        self.redis_client = None
        self.rsa_private_key = None
        self.rsa_public_key = None
        
    async def initialize(self):
        """Initialize the key manager"""
        self.redis_client = await get_redis()
        await self.pgp_manager.initialize()
        await self._initialize_rsa_keys()
        
    async def _initialize_rsa_keys(self):
        """Initialize RSA keys for additional encryption"""
        # Check if keys exist in Redis
        private_key_pem = await self.redis_client.get("master_rsa_private_key")
        public_key_pem = await self.redis_client.get("master_rsa_public_key")
        
        if not private_key_pem:
            # Generate new RSA key pair
            self.rsa_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            self.rsa_public_key = self.rsa_private_key.public_key()
            
            # Store keys
            private_pem = self.rsa_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_pem = self.rsa_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            await self.redis_client.set("master_rsa_private_key", private_pem)
            await self.redis_client.set("master_rsa_public_key", public_pem)
        else:
            # Load existing keys
            self.rsa_private_key = serialization.load_pem_private_key(
                private_key_pem, password=None, backend=default_backend()
            )
            self.rsa_public_key = serialization.load_pem_public_key(
                public_key_pem, backend=default_backend()
            )
            
    async def generate_one_time_key(
        self,
        pgp_signature: str,
        signed_data: str,
        purpose: str = "instance_registration",
        validity_hours: int = 24
    ) -> Optional[Dict]:
        """
        Generate a one-time key after PGP verification
        
        Args:
            pgp_signature: PGP signature of the request
            signed_data: Data that was signed (should include timestamp, purpose, etc.)
            purpose: Purpose of the key
            validity_hours: How long the key is valid
            
        Returns:
            Dict with key info or None if verification fails
        """
        # Verify PGP signature
        if not self.pgp_manager.verify_signature(signed_data, pgp_signature):
            logger.error("Invalid PGP signature for one-time key request")
            return None
            
        # Parse signed data to verify it's recent and matches purpose
        try:
            data = json.loads(signed_data)
            request_time = datetime.fromisoformat(data['timestamp'])
            
            # Check if request is recent (within 5 minutes)
            if datetime.utcnow() - request_time > timedelta(minutes=5):
                logger.error("One-time key request too old")
                return None
                
            if data.get('purpose') != purpose:
                logger.error(f"Purpose mismatch: {data.get('purpose')} != {purpose}")
                return None
                
        except Exception as e:
            logger.error(f"Invalid signed data format: {e}")
            return None
            
        # Generate secure one-time key
        key = secrets.token_urlsafe(48)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        # Get signer's fingerprint
        verified = self.pgp_manager.gpg.verify_data(pgp_signature, signed_data.encode())
        fingerprint = verified.fingerprint
        
        # Store key info
        otk = OneTimeKey(
            key=key_hash,  # Store hash, not actual key
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=validity_hours),
            created_by_fingerprint=fingerprint,
            purpose=purpose
        )
        
        # Store in Redis with expiration
        await self.redis_client.setex(
            f"otk:{key_hash}",
            validity_hours * 3600,
            otk.json()
        )
        
        # Return the actual key (not the hash) and metadata
        return {
            "key": key,
            "expires_at": otk.expires_at.isoformat(),
            "purpose": purpose,
            "created_by": fingerprint[-8:],  # Last 8 chars of fingerprint
            "instructions": {
                "instance_registration": "Use this key as INSTANCE_API_KEY when starting your container",
                "api_access": "Include this key in X-API-Key header"
            }.get(purpose, "Use as directed")
        }
        
    async def validate_one_time_key(self, key: str, purpose: str) -> Optional[Dict]:
        """Validate and consume a one-time key"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        # Get key info
        key_data = await self.redis_client.get(f"otk:{key_hash}")
        if not key_data:
            return None
            
        otk = OneTimeKey.parse_raw(key_data)
        
        # Check if already used
        if otk.used:
            logger.warning(f"Attempted to reuse one-time key: {key_hash}")
            return None
            
        # Check expiration
        if datetime.utcnow() > otk.expires_at:
            logger.warning(f"Expired one-time key: {key_hash}")
            return None
            
        # Check purpose
        if otk.purpose != purpose:
            logger.warning(f"Wrong purpose for key: {otk.purpose} != {purpose}")
            return None
            
        # Mark as used
        otk.used = True
        otk.used_at = datetime.utcnow()
        
        # Update in Redis
        await self.redis_client.setex(
            f"otk:{key_hash}",
            3600,  # Keep for 1 hour after use for audit
            otk.json()
        )
        
        return {
            "valid": True,
            "created_by": otk.created_by_fingerprint,
            "purpose": otk.purpose
        }
        
    async def generate_instance_jwt(self, instance_id: str, pgp_fingerprint: str) -> str:
        """Generate JWT for instance after successful registration"""
        payload = {
            "instance_id": instance_id,
            "pgp_fingerprint": pgp_fingerprint,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=30),
            "type": "instance_auth"
        }
        
        # Sign with master key
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        
    async def add_trusted_key(self, public_key: str, metadata: Dict) -> bool:
        """Add a new trusted PGP key"""
        try:
            result = self.pgp_manager.gpg.import_keys(public_key)
            if result.count == 0:
                return False
                
            fingerprint = result.fingerprints[0]
            
            # Store in Redis
            await self.redis_client.hset(
                "trusted_pgp_keys",
                fingerprint,
                json.dumps({
                    "added_at": datetime.utcnow().isoformat(),
                    "metadata": metadata
                })
            )
            
            # Update local cache
            self.pgp_manager.trusted_keys[fingerprint] = {
                "added_at": datetime.utcnow().isoformat(),
                "metadata": metadata
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding trusted key: {e}")
            return False


# Global instance
secure_key_manager = SecureKeyManager()