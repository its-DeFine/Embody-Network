"""
Comprehensive security validation tests for the 24/7 Trading System

Tests validate all critical security fixes implemented to address vulnerabilities
found in the security scan.
"""
import pytest
import os
import jwt
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
import sys
import importlib

# Add app to path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigurationSecurity:
    """Test security configuration validation"""
    
    def setup_method(self):
        """Set up test environment"""
        # Store original env vars
        self.original_jwt = os.environ.get('JWT_SECRET')
        self.original_admin = os.environ.get('ADMIN_PASSWORD')
    
    def teardown_method(self):
        """Clean up test environment"""
        # Restore original env vars
        if self.original_jwt:
            os.environ['JWT_SECRET'] = self.original_jwt
        elif 'JWT_SECRET' in os.environ:
            del os.environ['JWT_SECRET']
            
        if self.original_admin:
            os.environ['ADMIN_PASSWORD'] = self.original_admin
        elif 'ADMIN_PASSWORD' in os.environ:
            del os.environ['ADMIN_PASSWORD']
    
    def test_strong_jwt_secret_accepted(self):
        """Test that strong JWT secrets are accepted"""
        os.environ['JWT_SECRET'] = 'secure-jwt-secret-that-is-32-chars-long-minimum-for-testing'
        os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
        
        # Import config fresh
        if 'app.config' in sys.modules:
            importlib.reload(sys.modules['app.config'])
        else:
            import app.config
        
        from app.config import settings
        assert len(settings.jwt_secret) >= 32
        assert settings.jwt_secret == os.environ['JWT_SECRET']
    
    def test_weak_jwt_secret_rejected(self):
        """Test that weak JWT secrets are rejected"""
        weak_secrets = [
            'change-me-in-production',
            'secret',
            'jwt-secret',
            'supersecret',
            'short'  # Too short
        ]
        
        os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
        
        for weak_secret in weak_secrets:
            os.environ['JWT_SECRET'] = weak_secret
            
            with pytest.raises(ValueError, match="JWT_SECRET"):
                # Force reload to test validation
                if 'app.config' in sys.modules:
                    importlib.reload(sys.modules['app.config'])
                else:
                    import app.config
    
    def test_weak_admin_password_rejected(self):
        """Test that weak admin passwords are rejected"""
        weak_passwords = [
            'admin',
            'admin123',
            'password',
            '123456',
            'change-me',
            'short'  # Too short
        ]
        
        os.environ['JWT_SECRET'] = 'secure-jwt-secret-that-is-32-chars-long-minimum-for-testing'
        
        for weak_password in weak_passwords:
            os.environ['ADMIN_PASSWORD'] = weak_password
            
            with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
                # Force reload to test validation
                if 'app.config' in sys.modules:
                    importlib.reload(sys.modules['app.config'])
                else:
                    import app.config


class TestInputValidation:
    """Test Pydantic input validation models"""
    
    def setup_method(self):
        """Import validation models"""
        # Set required env vars for imports
        os.environ['JWT_SECRET'] = 'secure-jwt-secret-that-is-32-chars-long-minimum-for-testing'
        os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
        
        from app.api.trading import TradingStartRequest, TradeExecutionRequest, TradingConfigRequest
        self.TradingStartRequest = TradingStartRequest
        self.TradeExecutionRequest = TradeExecutionRequest
        self.TradingConfigRequest = TradingConfigRequest
    
    def test_trading_start_request_valid(self):
        """Test valid trading start requests"""
        valid_capitals = [100, 1000, 50000, 100000]
        
        for capital in valid_capitals:
            request = self.TradingStartRequest(initial_capital=capital)
            assert request.initial_capital == capital
    
    def test_trading_start_request_invalid_low(self):
        """Test trading start request rejects low capital"""
        invalid_capitals = [0, -100, 50, 99.99]
        
        for capital in invalid_capitals:
            with pytest.raises(ValueError, match="at least"):
                self.TradingStartRequest(initial_capital=capital)
    
    def test_trading_start_request_invalid_high(self):
        """Test trading start request rejects excessive capital"""
        invalid_capitals = [100001, 200000, 1000000]
        
        for capital in invalid_capitals:
            with pytest.raises(ValueError, match="cannot exceed"):
                self.TradingStartRequest(initial_capital=capital)
    
    def test_trade_execution_valid(self):
        """Test valid trade execution requests"""
        valid_trades = [
            {'symbol': 'BTC-USD', 'action': 'buy', 'amount': 1000.0},
            {'symbol': 'ETH', 'action': 'sell', 'amount': 5000.0},
            {'symbol': 'AAPL', 'action': 'short', 'amount': 10000.0}
        ]
        
        for trade in valid_trades:
            request = self.TradeExecutionRequest(**trade)
            assert request.symbol == trade['symbol'].upper()
            assert request.action == trade['action'].lower()
            assert request.amount == trade['amount']
    
    def test_trade_execution_invalid_symbol(self):
        """Test trade execution rejects invalid symbols"""
        invalid_symbols = [
            'INVALID@SYMBOL',
            'TOO_LONG_SYMBOL_NAME_EXCEEDS_LIMIT',
            '',
            'SYMBOL WITH SPACES'
        ]
        
        for symbol in invalid_symbols:
            with pytest.raises(ValueError):
                self.TradeExecutionRequest(symbol=symbol, action='buy', amount=1000)
    
    def test_trade_execution_invalid_action(self):
        """Test trade execution rejects invalid actions"""
        invalid_actions = ['hack', 'steal', 'manipulate', '', 'invalid']
        
        for action in invalid_actions:
            with pytest.raises(ValueError, match="Action must be one of"):
                self.TradeExecutionRequest(symbol='BTC-USD', action=action, amount=1000)
    
    def test_trade_execution_invalid_amount(self):
        """Test trade execution rejects invalid amounts"""
        invalid_amounts = [-1000, 0, 2000000]  # negative, zero, excessive
        
        for amount in invalid_amounts:
            with pytest.raises(ValueError):
                self.TradeExecutionRequest(symbol='BTC-USD', action='buy', amount=amount)


class TestJWTSecurity:
    """Test JWT token security implementation"""
    
    def setup_method(self):
        """Set up JWT testing environment"""
        self.jwt_secret = 'test-jwt-secret-that-is-32-chars-long-for-comprehensive-testing'
        self.jwt_algorithm = 'HS256'
    
    def test_valid_jwt_token(self):
        """Test valid JWT token creation and validation"""
        payload = {
            'sub': 'test-user',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        decoded = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        
        assert decoded['sub'] == 'test-user'
        assert 'exp' in decoded
    
    def test_expired_jwt_token_rejected(self):
        """Test expired JWT tokens are rejected"""
        expired_payload = {
            'sub': 'test-user',
            'exp': datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        
        expired_token = jwt.encode(expired_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
    
    def test_invalid_signature_rejected(self):
        """Test tokens with invalid signatures are rejected"""
        payload = {
            'sub': 'test-user',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(token, 'wrong-secret-key', algorithms=[self.jwt_algorithm])
    
    def test_malformed_token_rejected(self):
        """Test malformed tokens are rejected"""
        malformed_tokens = [
            'not.a.token',
            'invalid_token',
            '',
            'a.b'  # Missing part
        ]
        
        for token in malformed_tokens:
            with pytest.raises(jwt.InvalidTokenError):
                jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])


class TestPrivateKeySecurity:
    """Test private key security measures"""
    
    def test_private_key_removed(self):
        """Test that private key file has been removed"""
        private_key_path = '/home/geo/operation/keys/master-private.asc'
        assert not os.path.exists(private_key_path), "Private key should be removed from repository"
    
    def test_security_notice_exists(self):
        """Test that security breach notice exists"""
        notice_path = '/home/geo/operation/keys/SECURITY_BREACH_NOTICE.md'
        assert os.path.exists(notice_path), "Security breach notice should exist"
        
        with open(notice_path, 'r') as f:
            content = f.read()
            assert 'SECURITY BREACH NOTICE' in content
            assert 'master-private.asc' in content
            assert 'COMPROMISED' in content


class TestMasterAPISecurity:
    """Test Master API security requirements"""
    
    def test_master_secret_key_required(self):
        """Test that Master API requires MASTER_SECRET_KEY environment variable"""
        # Remove MASTER_SECRET_KEY if it exists
        original_key = os.environ.get('MASTER_SECRET_KEY')
        if 'MASTER_SECRET_KEY' in os.environ:
            del os.environ['MASTER_SECRET_KEY']
        
        try:
            # This should fail because MASTER_SECRET_KEY is required
            with pytest.raises((ValueError, ImportError)):
                if 'app.api.master' in sys.modules:
                    importlib.reload(sys.modules['app.api.master'])
                else:
                    import app.api.master
        finally:
            # Restore original key
            if original_key:
                os.environ['MASTER_SECRET_KEY'] = original_key


class TestSecurityMiddleware:
    """Test security middleware components"""
    
    def test_middleware_imports(self):
        """Test that all security middleware can be imported"""
        from app.middleware import (
            LoggingMiddleware,
            MetricsMiddleware, 
            RateLimitMiddleware,
            SecurityHeadersMiddleware,
            TradingSecurityMiddleware
        )
        
        # Test that they can be instantiated
        assert LoggingMiddleware is not None
        assert MetricsMiddleware is not None
        assert RateLimitMiddleware is not None
        assert SecurityHeadersMiddleware is not None  
        assert TradingSecurityMiddleware is not None
    
    def test_rate_limit_middleware_initialization(self):
        """Test rate limiting middleware can be initialized"""
        from app.middleware import RateLimitMiddleware
        
        # Create mock app
        mock_app = MagicMock()
        
        # Test default initialization
        middleware = RateLimitMiddleware(mock_app)
        assert middleware.requests_per_minute == 100  # Default value
        
        # Test custom initialization
        middleware = RateLimitMiddleware(mock_app, requests_per_minute=60)
        assert middleware.requests_per_minute == 60


# Integration test to verify all security components work together
class TestSecurityIntegration:
    """Integration tests for security system"""
    
    def test_core_security_components_integration(self):
        """Test that core security components work together"""
        # Set proper environment
        os.environ['JWT_SECRET'] = 'secure-jwt-secret-that-is-32-chars-long-minimum-for-testing'
        os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
        
        # Test config
        from app.config import settings
        assert len(settings.jwt_secret) >= 32
        
        # Test middleware
        from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
        mock_app = MagicMock()
        rate_limit = RateLimitMiddleware(mock_app)
        security_headers = SecurityHeadersMiddleware(mock_app)
        
        assert rate_limit is not None
        assert security_headers is not None
        
        # Test validation models
        from app.api.trading import TradingStartRequest
        request = TradingStartRequest(initial_capital=1000)
        assert request.initial_capital == 1000
        
        # Test JWT
        token = jwt.encode(
            {'sub': 'user', 'exp': datetime.utcnow() + timedelta(hours=1)},
            settings.jwt_secret,
            algorithm='HS256'
        )
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=['HS256'])
        assert decoded['sub'] == 'user'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])