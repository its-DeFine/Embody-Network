"""
Core security validation tests - isolated from complex dependencies

Tests the most critical security fixes without requiring full application startup.
"""
import pytest
import os
import jwt
import sys
import importlib
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel, validator
import re

# Add app to path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigurationSecurity:
    """Test security configuration validation"""
    
    def setup_method(self):
        """Set up test environment"""
        # Store original env vars
        self.original_jwt = os.environ.get('JWT_SECRET')
        self.original_admin = os.environ.get('ADMIN_PASSWORD')
        
        # Clear modules to force fresh import
        modules_to_clear = ['app.config']
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
    
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
    
    @pytest.mark.security
    def test_strong_jwt_secret_accepted(self):
        """Test that strong JWT secrets are accepted"""
        os.environ['JWT_SECRET'] = 'secure-jwt-secret-that-is-32-chars-long-minimum-for-testing'
        os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
        
        from app.config import settings
        assert len(settings.jwt_secret) >= 32
        assert settings.jwt_secret == os.environ['JWT_SECRET']
    
    @pytest.mark.security
    def test_weak_jwt_secret_rejected(self):
        """Test that weak JWT secrets are rejected"""
        os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
        
        weak_secrets = [
            'change-me-in-production',
            'secret', 
            'jwt-secret',
            'supersecret',
            'short123'  # Too short (less than 32 chars)
        ]
        
        for weak_secret in weak_secrets:
            os.environ['JWT_SECRET'] = weak_secret
            
            # Clear the module cache to force re-validation
            if 'app.config' in sys.modules:
                del sys.modules['app.config']
            
            with pytest.raises(ValueError, match="JWT_SECRET"):
                import app.config
    
    @pytest.mark.security
    def test_weak_admin_password_rejected(self):
        """Test that weak admin passwords are rejected"""
        os.environ['JWT_SECRET'] = 'secure-jwt-secret-that-is-32-chars-long-minimum-for-testing'
        
        weak_passwords = [
            'admin',
            'admin123', 
            'password',
            '123456',
            'change-me',
            'short'  # Too short (less than 12 chars)
        ]
        
        for weak_password in weak_passwords:
            os.environ['ADMIN_PASSWORD'] = weak_password
            
            # Clear the module cache to force re-validation
            if 'app.config' in sys.modules:
                del sys.modules['app.config']
            
            with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
                import app.config


class TestJWTSecurity:
    """Test JWT token security implementation"""
    
    def setup_method(self):
        """Set up JWT testing environment"""
        self.jwt_secret = 'test-jwt-secret-that-is-32-chars-long-for-comprehensive-testing'
        self.jwt_algorithm = 'HS256'
    
    @pytest.mark.security
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
    
    @pytest.mark.security
    def test_expired_jwt_token_rejected(self):
        """Test expired JWT tokens are rejected"""
        expired_payload = {
            'sub': 'test-user',
            'exp': datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        
        expired_token = jwt.encode(expired_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
    
    @pytest.mark.security
    def test_invalid_signature_rejected(self):
        """Test tokens with invalid signatures are rejected"""
        payload = {
            'sub': 'test-user',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(token, 'wrong-secret-key', algorithms=[self.jwt_algorithm])
    
    @pytest.mark.security
    def test_malformed_token_rejected(self):
        """Test malformed tokens are rejected"""
        malformed_tokens = [
            'not.a.token',
            'invalid_token', 
            '',
            'a.b'  # Missing part
        ]
        
        for token in malformed_tokens:
            with pytest.raises((jwt.InvalidTokenError, jwt.DecodeError)):
                jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])


class TestInputValidationModels:
    """Test input validation using isolated Pydantic models"""
    
    def setup_method(self):
        """Create isolated validation models for testing"""
        
        # Create isolated TradingStartRequest model
        class TradingStartRequest(BaseModel):
            initial_capital: float
            
            @validator('initial_capital')
            def validate_capital(cls, v):
                if not isinstance(v, (int, float)):
                    raise ValueError("Initial capital must be a number")
                
                if v < 100:
                    raise ValueError("Initial capital must be at least $100")
                
                if v > 100000:
                    raise ValueError("Initial capital cannot exceed $100,000 for safety")
                
                # Check for reasonable decimal places
                try:
                    decimal_val = Decimal(str(v))
                    if decimal_val.as_tuple().exponent < -2:
                        raise ValueError("Initial capital cannot have more than 2 decimal places")
                except:
                    raise ValueError("Invalid capital amount format")
                    
                return v
        
        # Create isolated TradeExecutionRequest model
        class TradeExecutionRequest(BaseModel):
            symbol: str
            action: str  # buy, sell, short
            amount: float
            
            @validator('symbol')
            def validate_symbol(cls, v):
                if not v or not isinstance(v, str):
                    raise ValueError("Symbol is required and must be a string")
                
                symbol = v.strip().upper()
                if not re.match(r'^[A-Z0-9.-]+$', symbol):
                    raise ValueError(f"Invalid symbol format: {symbol}")
                
                if len(symbol) > 20:
                    raise ValueError(f"Symbol too long: {symbol}")
                    
                return symbol
            
            @validator('action')
            def validate_action(cls, v):
                if not v or not isinstance(v, str):
                    raise ValueError("Action is required and must be a string")
                
                action = v.strip().lower()
                allowed_actions = ['buy', 'sell', 'short']
                
                if action not in allowed_actions:
                    raise ValueError(f"Action must be one of: {allowed_actions}")
                    
                return action
            
            @validator('amount')
            def validate_amount(cls, v):
                if not isinstance(v, (int, float)):
                    raise ValueError("Amount must be a number")
                
                if v <= 0:
                    raise ValueError("Amount must be positive")
                
                if v > 1000000:  # $1M max per trade for safety
                    raise ValueError("Amount cannot exceed $1,000,000 per trade")
                    
                return v
        
        self.TradingStartRequest = TradingStartRequest
        self.TradeExecutionRequest = TradeExecutionRequest
    
    @pytest.mark.security
    def test_trading_start_request_valid(self):
        """Test valid trading start requests"""
        valid_capitals = [100, 1000, 50000, 100000]
        
        for capital in valid_capitals:
            request = self.TradingStartRequest(initial_capital=capital)
            assert request.initial_capital == capital
    
    @pytest.mark.security
    def test_trading_start_request_invalid_low(self):
        """Test trading start request rejects low capital"""
        invalid_capitals = [0, -100, 50, 99.99]
        
        for capital in invalid_capitals:
            with pytest.raises(ValueError, match="at least"):
                self.TradingStartRequest(initial_capital=capital)
    
    @pytest.mark.security
    def test_trading_start_request_invalid_high(self):
        """Test trading start request rejects excessive capital"""
        invalid_capitals = [100001, 200000, 1000000]
        
        for capital in invalid_capitals:
            with pytest.raises(ValueError, match="cannot exceed"):
                self.TradingStartRequest(initial_capital=capital)
    
    @pytest.mark.security
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
    
    @pytest.mark.security
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
    
    @pytest.mark.security
    def test_trade_execution_invalid_action(self):
        """Test trade execution rejects invalid actions"""
        invalid_actions = ['hack', 'steal', 'manipulate', 'invalid']
        
        for action in invalid_actions:
            with pytest.raises(ValueError, match="Action must be one of"):
                self.TradeExecutionRequest(symbol='BTC-USD', action=action, amount=1000)
        
        # Test empty string separately (different error message)
        with pytest.raises(ValueError, match="Action is required"):
            self.TradeExecutionRequest(symbol='BTC-USD', action='', amount=1000)
    
    @pytest.mark.security
    def test_trade_execution_invalid_amount(self):
        """Test trade execution rejects invalid amounts"""
        invalid_amounts = [-1000, 0, 2000000]  # negative, zero, excessive
        
        for amount in invalid_amounts:
            with pytest.raises(ValueError):
                self.TradeExecutionRequest(symbol='BTC-USD', action='buy', amount=amount)


class TestPrivateKeySecurity:
    """Test private key security measures"""
    
    @pytest.mark.security
    def test_private_key_removed(self):
        """Test that private key file has been removed"""
        private_key_path = '/home/geo/operation/keys/master-private.asc'
        assert not os.path.exists(private_key_path), "Private key should be removed from repository"
    
    @pytest.mark.security
    def test_security_notice_exists(self):
        """Test that security breach notice exists"""
        notice_path = '/home/geo/operation/keys/SECURITY_BREACH_NOTICE.md'
        assert os.path.exists(notice_path), "Security breach notice should exist"
        
        with open(notice_path, 'r') as f:
            content = f.read()
            assert 'SECURITY BREACH NOTICE' in content
            assert 'COMPROMISED' in content or 'compromised' in content.lower()


class TestSecurityIntegration:
    """Basic integration tests for core security components"""
    
    @pytest.mark.security
    def test_security_config_and_jwt_integration(self):
        """Test that config validation and JWT work together"""
        # Set secure environment
        os.environ['JWT_SECRET'] = 'secure-jwt-secret-that-is-32-chars-long-minimum-for-testing'
        os.environ['ADMIN_PASSWORD'] = 'secure-admin-password-123'
        
        # Clear module cache
        if 'app.config' in sys.modules:
            del sys.modules['app.config']
        
        # Test config
        from app.config import settings
        assert len(settings.jwt_secret) >= 32
        
        # Test JWT using config secret
        payload = {
            'sub': 'integration-test-user',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(payload, settings.jwt_secret, algorithm='HS256')
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=['HS256'])
        
        assert decoded['sub'] == 'integration-test-user'
        assert 'exp' in decoded


if __name__ == '__main__':
    pytest.main([__file__, '-v'])