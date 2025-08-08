"""Application configuration with validation"""
from typing import Optional, List
from pydantic import validator
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Settings
    api_title: str = "VTuber Autonomy Platform"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    
    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    admin_password: str
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_pool_size: int = 10
    
    # OpenAI API Keys (for VTuber LLM)
    openai_api_key: Optional[str] = None
    
    # Docker
    docker_network: str = "vtuber_network"
    agent_image: str = "autogen_agent_with_neo4j:latest"
    agent_memory_limit: str = "1g"
    agent_cpu_limit: float = 1.0
    
    # Orchestrator
    orchestrator_health_check_interval: int = 30
    orchestrator_task_timeout: int = 300
    max_retries: int = 3
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Environment
    environment: str = "development"
    
    # VTuber Configuration
    vtuber_enabled: bool = True
    vtuber_host: str = "neurosync_s1"
    vtuber_port: int = 5001
    autogen_host: str = "autogen_agent"
    autogen_port: int = 8000
    
    # Performance Tuning
    update_frequency: int = 30
    
    # Master Configuration (for distributed systems)
    master_secret_key: Optional[str] = None
    enable_distributed: bool = False
    
    @validator("jwt_secret")
    def jwt_secret_required(cls, v):
        if not v:
            raise ValueError("JWT_SECRET environment variable is required")
        
        # Check for common weak defaults
        weak_secrets = [
            "change-me-in-production",
            "change-me", 
            "secret",
            "jwt-secret",
            "your-secret-here",
            "supersecret",
            "jwt_secret"
        ]
        
        if v.lower() in [s.lower() for s in weak_secrets]:
            raise ValueError(f"JWT_SECRET cannot be a default value. Use a cryptographically secure random string.")
        
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long for security")
            
        return v
    
    @validator("admin_password")
    def admin_password_required(cls, v):
        if not v:
            raise ValueError("ADMIN_PASSWORD environment variable is required")
        
        # Check for common weak defaults
        weak_passwords = [
            "admin",
            "admin123", 
            "password",
            "123456",
            "change-me",
            "admin-password",
            "your-password-here"
        ]
        
        if v.lower() in [s.lower() for s in weak_passwords]:
            raise ValueError(f"ADMIN_PASSWORD cannot be a default value. Use a strong, unique password.")
        
        if len(v) < 12:
            raise ValueError("ADMIN_PASSWORD must be at least 12 characters long for security")
            
        return v
    
    @validator("environment")
    def environment_valid(cls, v):
        allowed = ["development", "staging", "production", "test"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Export common settings
IS_PRODUCTION = settings.environment == "production"
IS_DEVELOPMENT = settings.environment == "development"