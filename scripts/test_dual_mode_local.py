#!/usr/bin/env python3
"""
Local test script for dual-mode trading validation
Tests the implementation without full container deployment
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'customer_agents', 'base'))

from customer_agents.base.dual_mode_trading import DualModeTradingEngine
from customer_agents.base.comparison_reporter import ComparisonReporter
from customer_agents.base.agent_types.trading_agent import TradingAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_trading_mode(mode: str):
    """Test a specific trading mode"""
    print(f"\n{'='*50}")
    print(f"Testing {mode.upper()} mode")
    print(f"{'='*50}")
    
    # Set environment variable
    os.environ['TRADING_MODE'] = mode
    
    # Configure based on mode
    if mode == 'hybrid':
        os.environ['HYBRID_REAL_WEIGHT'] = '0.2'
        os.environ['HYBRID_SIM_WEIGHT'] = '0.8'
    
    try:
        # Initialize trading engine
        config = {
            'exchange': 'binance',
            'testnet': True
        }
        
        engine = DualModeTradingEngine(config)
        await engine.initialize()
        
        print(f"✓ Engine initialized in {mode} mode")
        
        # Test 1: Market Data
        print("\nTest 1: Market Data Retrieval")
        market_data = await engine.get_market_data('BTC/USDT')
        
        if mode == 'real':
            assert 'real' in market_data or 'current_price' in market_data
            print(f"✓ Real market data retrieved")
        elif mode == 'simulated':
            assert 'simulated' in market_data or 'price' in market_data
            print(f"✓ Simulated market data generated")
        elif mode in ['comparison', 'shadow', 'hybrid']:
            if 'real' in market_data and 'simulated' in market_data:
                print(f"✓ Both real and simulated data available")
                if 'price_divergence_pct' in market_data:
                    print(f"  Price divergence: {market_data['price_divergence_pct']:.2f}%")
        
        # Test 2: Order Execution
        print("\nTest 2: Order Execution")
        order = {
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'amount': 0.001,
            'type': 'market'
        }
        
        result = await engine.execute_trade(order)
        print(f"✓ Order executed in {result.get('mode', 'unknown')} mode")
        
        # Mode-specific validation
        if mode == 'comparison' and 'divergence_analysis' in result:
            divergence = result['divergence_analysis']
            print(f"  Price divergence: {divergence.get('price_divergence_pct', 0):.2f}%")
            print(f"  Alert status: {divergence.get('alert', 'none')}")
        
        elif mode == 'hybrid' and 'weights' in result:
            weights = result['weights']
            print(f"  Real weight: {weights['real']*100:.1f}%")
            print(f"  Simulated weight: {weights['simulated']*100:.1f}%")
        
        elif mode == 'shadow' and result.get('shadow_mode'):
            print(f"  Shadow mode confirmed: {result['note']}")
        
        # Test 3: Portfolio Status
        print("\nTest 3: Portfolio Status")
        portfolio = await engine.get_portfolio_status()
        print(f"✓ Portfolio status retrieved")
        
        if 'comparison_metrics' in portfolio:
            metrics = portfolio['comparison_metrics']
            print(f"  Total trades - Real: {metrics['total_trades']['real']}, Simulated: {metrics['total_trades']['simulated']}")
        
        # Test 4: Execution Analytics
        print("\nTest 4: Execution Analytics")
        analytics = engine.get_execution_analytics()
        print(f"✓ Analytics generated for {analytics['mode']} mode")
        print(f"  Total executions: {analytics['total_executions']}")
        
        if 'divergence_stats' in analytics:
            stats = analytics['divergence_stats']
            print(f"  Average divergence: {stats['average_price_divergence']*100:.2f}%")
            print(f"  Max divergence: {stats['max_price_divergence']*100:.2f}%")
        
        # Test 5: Comparison Report (if applicable)
        if mode in ['comparison', 'shadow'] and engine.execution_history:
            print("\nTest 5: Comparison Report")
            
            # Create mock agent to test reporting
            agent_config = {
                'exchange': 'binance',
                'trading_pairs': ['BTC/USDT'],
                'testnet': True
            }
            
            agent = TradingAgent(agent_config)
            agent.trading_engine = engine
            agent.execution_history = engine.execution_history
            
            report = await agent.get_comparison_report()
            if 'performance_comparison' in report:
                print(f"✓ Comparison report generated")
                print(f"  Accuracy score: {report['performance_comparison']['accuracy_score']:.1f}%")
                
                # Show insights
                if 'insights' in report and report['insights']:
                    print("\n  Insights:")
                    for insight in report['insights'][:2]:
                        print(f"    - {insight}")
        
        # Cleanup
        await engine.close()
        
        print(f"\n✅ {mode.upper()} mode test completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ {mode.upper()} mode test failed: {e}")
        logger.error(f"Error testing {mode} mode", exc_info=True)
        return False


async def test_comparison_reporter():
    """Test the comparison reporter functionality"""
    print(f"\n{'='*50}")
    print("Testing Comparison Reporter")
    print(f"{'='*50}")
    
    try:
        reporter = ComparisonReporter()
        
        # Create mock data
        real_data = {
            'metrics': {
                'total_return_pct': 5.2,
                'win_rate': 0.65,
                'sharpe_ratio': 1.8,
                'max_drawdown': 0.08
            },
            'risk_metrics': {
                'volatility': 0.15,
                'max_drawdown': 0.08,
                'var_95': 0.02,
                'risk_adjusted_return': 2.1
            }
        }
        
        sim_data = {
            'metrics': {
                'total_return_pct': 4.8,
                'win_rate': 0.62,
                'sharpe_ratio': 1.6,
                'max_drawdown': 0.07
            },
            'risk_metrics': {
                'volatility': 0.14,
                'max_drawdown': 0.07,
                'var_95': 0.018,
                'risk_adjusted_return': 1.9
            }
        }
        
        # Generate report
        report = reporter.generate_comparison_report(real_data, sim_data)
        
        print("✓ Report generated successfully")
        print(f"  Accuracy score: {report['performance_comparison']['accuracy_score']:.1f}%")
        print(f"  Confidence level: {report['summary']['confidence_level']}")
        print(f"  Recommendation: {report['summary']['recommendation']}")
        
        # Export as markdown
        md_report = reporter.export_report(report, 'markdown')
        print("✓ Markdown export successful")
        
        # Save report
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"comparison_report_test_{timestamp}.md"
        with open(filename, 'w') as f:
            f.write(md_report)
        print(f"✓ Report saved to {filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comparison reporter test failed: {e}")
        logger.error("Error testing comparison reporter", exc_info=True)
        return False


async def main():
    """Run all tests"""
    print("="*60)
    print("DUAL-MODE TRADING SYSTEM VALIDATION")
    print("="*60)
    
    # Test all trading modes
    modes = ['real', 'simulated', 'hybrid', 'comparison', 'shadow']
    results = {}
    
    for mode in modes:
        try:
            results[mode] = await test_trading_mode(mode)
            await asyncio.sleep(1)  # Brief pause between tests
        except Exception as e:
            logger.error(f"Failed to test {mode} mode: {e}")
            results[mode] = False
    
    # Test comparison reporter
    results['reporter'] = await test_comparison_reporter()
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.upper():20} {status}")
    
    print(f"\nTotal: {total_tests} tests")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Save results
    test_results = {
        'timestamp': datetime.utcnow().isoformat(),
        'results': results,
        'summary': {
            'total': total_tests,
            'passed': passed_tests,
            'failed': total_tests - passed_tests,
            'success_rate': (passed_tests/total_tests)*100
        }
    }
    
    with open(f"dual_mode_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print("\n✅ All tests completed!")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)