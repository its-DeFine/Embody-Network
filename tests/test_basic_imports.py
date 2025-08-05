"""
Basic import tests to verify core modules can be loaded without errors.

These tests ensure that the security fixes don't break basic module imports.
"""
import pytest
import os
import sys

# Add app to path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBasicImports:
    """Test that basic modules can be imported"""
    
    def setup_method(self):
        """Set up test environment with required env vars"""
        os.environ['JWT_SECRET'] = 'secure-jwt-secret-that-is-32-chars-long-minimum-for-testing'
        os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
    
    def test_config_import(self):
        """Test that config module can be imported"""
        from app.config import settings, IS_PRODUCTION, IS_DEVELOPMENT
        assert settings is not None
        assert isinstance(IS_PRODUCTION, bool)
        assert isinstance(IS_DEVELOPMENT, bool)
    
    def test_middleware_import(self):
        """Test that middleware modules can be imported"""
        from app.middleware import (
            LoggingMiddleware,
            MetricsMiddleware,
            RateLimitMiddleware,
            SecurityHeadersMiddleware,
            TradingSecurityMiddleware
        )
        
        # Test that they are callable classes
        assert callable(LoggingMiddleware)
        assert callable(MetricsMiddleware) 
        assert callable(RateLimitMiddleware)
        assert callable(SecurityHeadersMiddleware)
        assert callable(TradingSecurityMiddleware)
    
    def test_dependencies_import(self):
        """Test that dependencies module can be imported"""
        from app.dependencies import get_current_user
        assert callable(get_current_user)
    
    def test_errors_import(self):
        """Test that error handling can be imported"""
        from app.errors import PlatformError, platform_exception_handler
        assert PlatformError is not None
        assert callable(platform_exception_handler)
    


class TestEnvironmentVariables:
    """Test environment variable handling"""
    
    def test_required_env_vars_missing(self):
        """Test that missing required env vars are handled properly"""
        # Store originals
        original_jwt = os.environ.get('JWT_SECRET')
        original_admin = os.environ.get('ADMIN_PASSWORD')
        
        try:
            # Remove required env vars
            if 'JWT_SECRET' in os.environ:
                del os.environ['JWT_SECRET']
            if 'ADMIN_PASSWORD' in os.environ:
                del os.environ['ADMIN_PASSWORD']
            
            # Clear module cache to force re-import
            modules_to_clear = [k for k in sys.modules.keys() if k.startswith('app.config')]
            for module in modules_to_clear:
                del sys.modules[module]
            
            # Should raise validation error when trying to create Settings()
            with pytest.raises(Exception):  # Pydantic ValidationError
                from app.config import Settings
                # Create Settings without loading from .env file
                Settings(_env_file=None)  # This should fail without env vars
                
        finally:
            # Restore env vars
            if original_jwt:
                os.environ['JWT_SECRET'] = original_jwt
            else:
                os.environ['JWT_SECRET'] = 'test-jwt-secret-key-that-is-secure-32chars'
            if original_admin:
                os.environ['ADMIN_PASSWORD'] = original_admin
            else:
                os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
            
            # Clear cache again to allow clean re-import
            modules_to_clear = [k for k in sys.modules.keys() if k.startswith('app.config')]
            for module in modules_to_clear:
                del sys.modules[module]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])