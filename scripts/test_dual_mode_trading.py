#!/usr/bin/env python3
"""
Test script for validating dual-mode trading in containers
Tests all modes: real, simulated, hybrid, comparison, shadow
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime
import requests
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Gateway URL (adjust for container testing)
API_BASE_URL = os.getenv('API_GATEWAY_URL', 'http://localhost:8000')
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', 'admin-secret-key-change-in-production')

class DualModeTradingTester:
    """Test harness for dual-mode trading validation"""
    
    def __init__(self):
        self.session = requests.Session()
        self.jwt_token = None
        self.test_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tests': [],
            'summary': {}
        }
    
    def authenticate(self):
        """Get JWT token for API access"""
        try:
            response = self.session.post(
                f"{API_BASE_URL}/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            if response.status_code == 200:
                self.jwt_token = response.json().get('access_token')
                self.session.headers.update({'Authorization': f'Bearer {self.jwt_token}'})
                logger.info("Authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def test_mode(self, mode: str, test_config: dict):
        """Test a specific trading mode"""
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing {mode.upper()} mode")
        logger.info(f"{'='*50}")
        
        test_result = {
            'mode': mode,
            'status': 'pending',
            'tests': [],
            'errors': []
        }
        
        try:
            # 1. Create trading agent with specific mode
            agent_config = {
                "name": f"test_agent_{mode}",
                "type": "trading",
                "config": {
                    "exchange": "binance",
                    "trading_pairs": ["BTC/USDT", "ETH/USDT"],
                    "risk_limit": 0.02,
                    "testnet": True
                },
                "trading_mode": mode
            }
            
            # Set mode-specific environment
            os.environ['TRADING_MODE'] = mode
            
            if mode == 'hybrid':
                os.environ['HYBRID_REAL_WEIGHT'] = str(test_config.get('real_weight', 0.1))
                os.environ['HYBRID_SIM_WEIGHT'] = str(test_config.get('sim_weight', 0.9))
            
            # Create agent
            response = self.session.post(
                f"{API_BASE_URL}/agents",
                json=agent_config
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to create agent: {response.text}")
            
            agent_id = response.json()['agent_id']
            logger.info(f"Created agent: {agent_id}")
            test_result['agent_id'] = agent_id
            
            # 2. Test market data retrieval
            market_test = await self._test_market_data(agent_id, mode)
            test_result['tests'].append(market_test)
            
            # 3. Test order execution
            order_test = await self._test_order_execution(agent_id, mode)
            test_result['tests'].append(order_test)
            
            # 4. Test portfolio status
            portfolio_test = await self._test_portfolio_status(agent_id, mode)
            test_result['tests'].append(portfolio_test)
            
            # 5. Mode-specific tests
            if mode in ['comparison', 'shadow']:
                comparison_test = await self._test_comparison_features(agent_id, mode)
                test_result['tests'].append(comparison_test)
            
            if mode == 'hybrid':
                hybrid_test = await self._test_hybrid_weights(agent_id)
                test_result['tests'].append(hybrid_test)
            
            # Calculate success rate
            total_tests = len(test_result['tests'])
            passed_tests = sum(1 for t in test_result['tests'] if t['passed'])
            test_result['success_rate'] = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            test_result['status'] = 'completed'
            
            logger.info(f"\n{mode.upper()} mode test results:")
            logger.info(f"Total tests: {total_tests}")
            logger.info(f"Passed: {passed_tests}")
            logger.info(f"Failed: {total_tests - passed_tests}")
            logger.info(f"Success rate: {test_result['success_rate']:.1f}%")
            
        except Exception as e:
            logger.error(f"Error testing {mode} mode: {e}")
            test_result['status'] = 'failed'
            test_result['errors'].append(str(e))
        
        return test_result
    
    async def _test_market_data(self, agent_id: str, mode: str):
        """Test market data retrieval"""
        test = {
            'name': 'market_data_retrieval',
            'passed': False,
            'details': {}
        }
        
        try:
            # Request market data through agent
            response = self.session.post(
                f"{API_BASE_URL}/agents/{agent_id}/execute",
                json={
                    "function": "get_market_data",
                    "args": {
                        "symbol": "BTC/USDT",
                        "timeframe": "1h"
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                test['details'] = data
                
                # Validate based on mode
                if mode == 'real':
                    test['passed'] = 'real' in data or 'current_price' in data
                elif mode == 'simulated':
                    test['passed'] = 'simulated' in data or 'price' in data
                elif mode in ['comparison', 'shadow', 'hybrid']:
                    test['passed'] = ('real' in data and 'simulated' in data) or 'mode' in data
                
                # Check for divergence in comparison mode
                if mode == 'comparison' and 'price_divergence_pct' in data:
                    test['divergence'] = data['price_divergence_pct']
                    logger.info(f"Price divergence: {test['divergence']:.2f}%")
            
        except Exception as e:
            test['error'] = str(e)
            logger.error(f"Market data test failed: {e}")
        
        return test
    
    async def _test_order_execution(self, agent_id: str, mode: str):
        """Test order execution"""
        test = {
            'name': 'order_execution',
            'passed': False,
            'details': {}
        }
        
        try:
            # Execute a small test order
            response = self.session.post(
                f"{API_BASE_URL}/agents/{agent_id}/execute",
                json={
                    "function": "place_order",
                    "args": {
                        "symbol": "BTC/USDT",
                        "side": "buy",
                        "amount": 0.001,
                        "order_type": "market"
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                test['details'] = data
                
                # Validate based on mode
                if mode == 'real':
                    test['passed'] = data.get('status') in ['filled', 'simulated']
                elif mode == 'simulated':
                    test['passed'] = data.get('status') in ['filled', 'simulated']
                elif mode == 'comparison':
                    # Should have both real and simulated results
                    test['passed'] = 'results' in data and 'real' in data['results'] and 'simulated' in data['results']
                    
                    # Check divergence analysis
                    if 'divergence_analysis' in data:
                        test['divergence_analysis'] = data['divergence_analysis']
                        logger.info(f"Execution divergence: {data['divergence_analysis'].get('price_divergence_pct', 0):.2f}%")
                
                elif mode == 'hybrid':
                    # Should show weight distribution
                    test['passed'] = 'weights' in data
                    if test['passed']:
                        logger.info(f"Hybrid weights - Real: {data['weights']['real']*100:.1f}%, Sim: {data['weights']['simulated']*100:.1f}%")
                
                elif mode == 'shadow':
                    # Should only have simulated execution
                    test['passed'] = data.get('shadow_mode') == True
            
        except Exception as e:
            test['error'] = str(e)
            logger.error(f"Order execution test failed: {e}")
        
        return test
    
    async def _test_portfolio_status(self, agent_id: str, mode: str):
        """Test portfolio status retrieval"""
        test = {
            'name': 'portfolio_status',
            'passed': False,
            'details': {}
        }
        
        try:
            response = self.session.post(
                f"{API_BASE_URL}/agents/{agent_id}/execute",
                json={
                    "function": "get_portfolio_status"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                test['details'] = data
                
                # Validate based on mode
                if mode in ['comparison', 'shadow']:
                    test['passed'] = 'comparison_metrics' in data
                    if test['passed']:
                        metrics = data['comparison_metrics']
                        logger.info(f"Comparison metrics:")
                        logger.info(f"  Real trades: {metrics['total_trades']['real']}")
                        logger.info(f"  Sim trades: {metrics['total_trades']['simulated']}")
                else:
                    test['passed'] = 'balance' in data or 'total_balance' in data
            
        except Exception as e:
            test['error'] = str(e)
            logger.error(f"Portfolio status test failed: {e}")
        
        return test
    
    async def _test_comparison_features(self, agent_id: str, mode: str):
        """Test comparison-specific features"""
        test = {
            'name': 'comparison_features',
            'passed': False,
            'details': {}
        }
        
        try:
            # Get comparison report
            response = self.session.post(
                f"{API_BASE_URL}/agents/{agent_id}/execute",
                json={
                    "function": "get_comparison_report"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                test['details'] = data
                
                if 'performance_comparison' in data:
                    test['passed'] = True
                    perf = data['performance_comparison']
                    logger.info(f"\nComparison Report:")
                    logger.info(f"  Accuracy Score: {perf.get('accuracy_score', 0):.1f}%")
                    logger.info(f"  Real Returns: {perf.get('returns', {}).get('real', 0):.2f}%")
                    logger.info(f"  Sim Returns: {perf.get('returns', {}).get('simulated', 0):.2f}%")
                    
                    # Show insights
                    if 'insights' in data:
                        logger.info("\nInsights:")
                        for insight in data['insights'][:3]:
                            logger.info(f"  - {insight}")
                    
                    # Show recommendations
                    if 'recommendations' in data:
                        logger.info("\nRecommendations:")
                        for rec in data['recommendations'][:3]:
                            logger.info(f"  - {rec}")
            
        except Exception as e:
            test['error'] = str(e)
            logger.error(f"Comparison features test failed: {e}")
        
        return test
    
    async def _test_hybrid_weights(self, agent_id: str):
        """Test hybrid mode weight distribution"""
        test = {
            'name': 'hybrid_weight_distribution',
            'passed': False,
            'details': {}
        }
        
        try:
            # Get execution analytics
            response = self.session.post(
                f"{API_BASE_URL}/agents/{agent_id}/execute",
                json={
                    "function": "get_execution_analytics"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                test['details'] = data
                
                if 'hybrid_weighted_pnl' in data:
                    test['passed'] = True
                    logger.info(f"Hybrid weighted P&L: ${data['hybrid_weighted_pnl']:.2f}")
            
        except Exception as e:
            test['error'] = str(e)
            logger.error(f"Hybrid weights test failed: {e}")
        
        return test
    
    async def run_all_tests(self):
        """Run tests for all trading modes"""
        logger.info("Starting dual-mode trading validation tests")
        
        # Authenticate first
        if not self.authenticate():
            logger.error("Authentication failed - cannot proceed with tests")
            return
        
        # Test configurations for each mode
        test_configs = {
            'real': {},
            'simulated': {},
            'hybrid': {
                'real_weight': 0.2,
                'sim_weight': 0.8
            },
            'comparison': {},
            'shadow': {}
        }
        
        # Run tests for each mode
        for mode, config in test_configs.items():
            try:
                result = await self.test_mode(mode, config)
                self.test_results['tests'].append(result)
                
                # Wait between tests
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to test {mode} mode: {e}")
        
        # Generate summary
        self._generate_summary()
        
        # Save results
        self._save_results()
    
    def _generate_summary(self):
        """Generate test summary"""
        total_modes = len(self.test_results['tests'])
        successful_modes = sum(1 for t in self.test_results['tests'] if t['status'] == 'completed')
        
        self.test_results['summary'] = {
            'total_modes_tested': total_modes,
            'successful_modes': successful_modes,
            'failed_modes': total_modes - successful_modes,
            'overall_success_rate': (successful_modes / total_modes * 100) if total_modes > 0 else 0
        }
        
        logger.info(f"\n{'='*50}")
        logger.info("OVERALL TEST SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Total modes tested: {total_modes}")
        logger.info(f"Successful: {successful_modes}")
        logger.info(f"Failed: {total_modes - successful_modes}")
        logger.info(f"Overall success rate: {self.test_results['summary']['overall_success_rate']:.1f}%")
        
        # Mode-specific summaries
        for test in self.test_results['tests']:
            if test['status'] == 'completed':
                logger.info(f"\n{test['mode'].upper()} mode: {test['success_rate']:.1f}% success rate")
    
    def _save_results(self):
        """Save test results to file"""
        filename = f"dual_mode_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        logger.info(f"\nTest results saved to: {filename}")


async def main():
    """Main test execution"""
    tester = DualModeTradingTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())