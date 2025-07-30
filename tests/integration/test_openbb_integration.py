"""
OpenBB Integration Tests
Tests the integration between agents and the OpenBB adapter service
"""
import pytest
import asyncio
import httpx
from unittest.mock import Mock, patch, AsyncMock
import json

# Import the components to test
from agents.base.agent import CustomerAgent
from agents.base.agent_types.trading_agent import TradingAgent


class TestOpenBBIntegration:
    """Test OpenBB integration with agents"""
    
    @pytest.mark.asyncio
    async def test_openbb_client_initialization(self):
        """Test that OpenBB client is properly initialized"""
        with patch.dict('os.environ', {
            'AGENT_ID': 'test-agent-1',
            'CUSTOMER_ID': 'test-customer',
            'AGENT_TYPE': 'trading',
            'AGENT_NAME': 'TestAgent',
            'CONFIG': '{}',
            'AUTOGEN_CONFIG': '{}',
            'OPENBB_SERVICE_URL': 'http://openbb-adapter:8003'
        }):
            agent = CustomerAgent()
            
            # Mock the message queue and OpenBB health check
            agent._connect_message_queue = AsyncMock(return_value=Mock())
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_client.return_value.get = AsyncMock(return_value=mock_response)
                
                await agent.initialize()
                
                assert agent.openbb_client is not None
                mock_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_market_data_from_openbb(self):
        """Test fetching market data from OpenBB service"""
        with patch.dict('os.environ', {
            'AGENT_ID': 'test-agent-1',
            'CUSTOMER_ID': 'test-customer',
            'AGENT_TYPE': 'trading',
            'AGENT_NAME': 'TestAgent',
            'CONFIG': '{}',
            'AUTOGEN_CONFIG': '{}'
        }):
            agent = CustomerAgent()
            
            # Mock OpenBB client response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "open": [100, 101, 102],
                    "high": [105, 106, 107],
                    "low": [99, 100, 101],
                    "close": [104, 105, 106],
                    "volume": [1000000, 1100000, 1200000]
                },
                "last_price": 106,
                "change_24h": 2.5
            }
            
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            agent.openbb_client = mock_client
            
            # Test market data retrieval
            result = await agent.get_market_data("BTC/USDT", "1h")
            
            assert result is not None
            assert "error" not in result
            mock_client.get.assert_called_once_with(
                "/api/v1/market/data",
                params={"symbol": "BTC/USDT", "interval": "1h"}
            )
    
    @pytest.mark.asyncio
    async def test_get_technical_analysis_from_openbb(self):
        """Test fetching technical analysis from OpenBB service"""
        with patch.dict('os.environ', {
            'AGENT_ID': 'test-agent-1',
            'CUSTOMER_ID': 'test-customer',
            'AGENT_TYPE': 'trading',
            'AGENT_NAME': 'TestAgent',
            'CONFIG': '{}',
            'AUTOGEN_CONFIG': '{}'
        }):
            agent = CustomerAgent()
            
            # Mock OpenBB client response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "indicators": {
                    "RSI": {"value": 65, "signal": "neutral"},
                    "MACD": {"value": 100, "signal": "bullish"},
                    "BB": {"upper": 110, "middle": 105, "lower": 100}
                },
                "overall_signal": "bullish",
                "confidence": 0.85
            }
            
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            agent.openbb_client = mock_client
            
            # Test technical analysis
            result = await agent.get_technical_analysis("BTC/USDT", ["RSI", "MACD", "BB"])
            
            assert result is not None
            assert "error" not in result
            mock_client.post.assert_called_once_with(
                "/api/v1/analysis/technical",
                json={"symbol": "BTC/USDT", "indicators": ["RSI", "MACD", "BB"]}
            )
    
    @pytest.mark.asyncio
    async def test_trading_agent_uses_openbb_data(self):
        """Test that trading agent properly uses OpenBB data when available"""
        mock_openbb_client = AsyncMock()
        
        # Mock successful OpenBB response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"close": [100, 101, 102]},
            "last_price": 102,
            "change_24h": 2.0
        }
        mock_openbb_client.get = AsyncMock(return_value=mock_response)
        
        # Create trading agent with mocked OpenBB client
        trading_agent = TradingAgent({}, mock_openbb_client)
        trading_agent._initialized = True
        
        # Mock the trading engine
        trading_agent.trading_engine = Mock()
        trading_agent.trading_engine.get_market_data = AsyncMock()
        
        # Get market data
        result = await trading_agent.get_market_data("BTC/USDT")
        
        # Verify OpenBB was called
        mock_openbb_client.get.assert_called_once()
        assert result["source"] == "openbb"
        
        # Verify trading engine was not called (OpenBB succeeded)
        trading_agent.trading_engine.get_market_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_trading_agent_fallback_when_openbb_fails(self):
        """Test that trading agent falls back to exchange when OpenBB fails"""
        mock_openbb_client = AsyncMock()
        
        # Mock failed OpenBB response
        mock_openbb_client.get = AsyncMock(side_effect=Exception("OpenBB service unavailable"))
        
        # Create trading agent with mocked OpenBB client
        trading_agent = TradingAgent({}, mock_openbb_client)
        trading_agent._initialized = True
        
        # Mock the trading engine fallback
        expected_data = {
            "symbol": "BTC/USDT",
            "data": {"close": [100, 101, 102]},
            "current_price": 102
        }
        trading_agent.trading_engine = Mock()
        trading_agent.trading_engine.get_market_data = AsyncMock(return_value=expected_data)
        
        # Get market data
        result = await trading_agent.get_market_data("BTC/USDT")
        
        # Verify fallback to trading engine
        trading_agent.trading_engine.get_market_data.assert_called_once_with("BTC/USDT", "1h")
        assert result == expected_data
    
    @pytest.mark.asyncio
    async def test_analyze_portfolio_integration(self):
        """Test portfolio analysis through OpenBB service"""
        with patch.dict('os.environ', {
            'AGENT_ID': 'test-agent-1',
            'CUSTOMER_ID': 'test-customer',
            'AGENT_TYPE': 'portfolio_optimization',
            'AGENT_NAME': 'TestAgent',
            'CONFIG': '{}',
            'AUTOGEN_CONFIG': '{}'
        }):
            agent = CustomerAgent()
            
            # Mock OpenBB client response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "total_value": 100000,
                "total_return": 5000,
                "total_return_pct": 0.05,
                "positions": [
                    {"symbol": "AAPL", "value": 50000, "weight": 0.5},
                    {"symbol": "GOOGL", "value": 50000, "weight": 0.5}
                ],
                "metrics": {
                    "sharpe_ratio": 1.25,
                    "beta": 1.1
                }
            }
            
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            agent.openbb_client = mock_client
            
            # Test portfolio analysis
            positions = [
                {"symbol": "AAPL", "quantity": 100, "cost_basis": 150},
                {"symbol": "GOOGL", "quantity": 50, "cost_basis": 2800}
            ]
            result = await agent.analyze_portfolio(positions)
            
            assert result is not None
            assert result["total_value"] == 100000
            assert "metrics" in result
            mock_client.post.assert_called_once_with(
                "/api/v1/portfolio/analyze",
                json={"positions": positions}
            )
    
    @pytest.mark.asyncio
    async def test_openbb_client_cleanup(self):
        """Test that OpenBB client is properly cleaned up"""
        with patch.dict('os.environ', {
            'AGENT_ID': 'test-agent-1',
            'CUSTOMER_ID': 'test-customer',
            'AGENT_TYPE': 'trading',
            'AGENT_NAME': 'TestAgent',
            'CONFIG': '{}',
            'AUTOGEN_CONFIG': '{}'
        }):
            agent = CustomerAgent()
            
            # Mock the clients
            mock_openbb_client = AsyncMock()
            mock_mq = AsyncMock()
            
            agent.openbb_client = mock_openbb_client
            agent.mq = mock_mq
            agent.running = True
            
            # Cleanup
            await agent.cleanup()
            
            # Verify cleanup was called
            mock_openbb_client.aclose.assert_called_once()
            mock_mq.disconnect.assert_called_once()
            assert agent.running is False


class TestOpenBBServiceEndpoints:
    """Test OpenBB adapter service endpoints"""
    
    @pytest.mark.asyncio
    async def test_openbb_health_endpoint(self, httpx_client):
        """Test OpenBB service health endpoint"""
        # This would be an actual integration test with the running service
        # For unit testing, we'll mock it
        mock_response = {"status": "healthy", "version": "1.0.0"}
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.get("http://openbb-adapter:8003/health")
                
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_openbb_market_data_endpoint(self, httpx_client):
        """Test OpenBB market data endpoint"""
        mock_response = {
            "symbol": "AAPL",
            "data": {
                "open": [150, 151, 152],
                "close": [151, 152, 153],
                "volume": [1000000, 1100000, 1200000]
            },
            "last_price": 153,
            "change_24h": 2.0
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://openbb-adapter:8003/api/v1/market/data",
                    params={"symbol": "AAPL", "interval": "1d"}
                )
                
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert "data" in data


@pytest.fixture
def httpx_client():
    """Fixture for httpx async client"""
    return httpx.AsyncClient


if __name__ == "__main__":
    pytest.main([__file__, "-v"])