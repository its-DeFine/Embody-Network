"""Application configuration with validation"""
from typing import Optional, List
from pydantic import validator
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Settings
    api_title: str = "AutoGen Platform"
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
    
    # OpenBB
    openbb_url: Optional[str] = None
    openbb_api_key: Optional[str] = None
    
    # Market Data API Keys
    openai_api_key: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    twelvedata_api_key: Optional[str] = None
    marketstack_api_key: Optional[str] = None
    
    # Docker
    docker_network: str = "autogen-network"
    agent_image: str = "autogen-agent:latest"
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
    
    # Trading Configuration
    initial_capital: float = 1000.00
    max_position_pct: float = 0.10
    stop_loss_pct: float = 0.02
    commission_pct: float = 0.001
    target_symbols: str = "AAPL,MSFT,GOOGL,TSLA,NVDA"
    
    # Strategy Configuration
    enable_mean_reversion: bool = True
    enable_momentum: bool = True
    enable_arbitrage: bool = True
    enable_scalping: bool = False
    enable_dca: bool = True
    
    # Risk Management
    daily_loss_limit: float = 0.05
    max_daily_trades: int = 50
    confidence_threshold: float = 0.6
    
    # Performance Tuning
    update_frequency: int = 30
    rebalance_frequency: int = 3600
    
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