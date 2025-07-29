#!/usr/bin/env python3
"""
Run live trading simulation directly
This simulates actual trading activity without complex container setup
"""

import asyncio
import logging
import os
import sys
import json
from datetime import datetime
import random

# Setup paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'customer_agents', 'base'))

# Import our trading components
from customer_agents.base.dual_mode_trading import DualModeTradingEngine
from customer_agents.base.comparison_reporter import ComparisonReporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('LiveTradingSimulation')


class LiveTradingBot:
    """Simulated trading bot that executes trades continuously"""
    
    def __init__(self, mode='simulated'):
        self.mode = mode
        self.config = {
            'exchange': 'binance',
            'testnet': True
        }
        self.trading_pairs = ['BTC/USDT', 'ETH/USDT']
        self.risk_limit = 0.02  # 2% risk per trade
        self.trade_count = 0
        self.trade_history = []
        
    async def initialize(self):
        """Initialize trading engine"""
        os.environ['TRADING_MODE'] = self.mode
        self.engine = DualModeTradingEngine(self.config)
        await self.engine.initialize()
        self.reporter = ComparisonReporter()
        logger.info(f"Trading bot initialized in {self.mode} mode")
        
    async def analyze_market(self, symbol):
        """Simple market analysis (random for demo)"""
        # In real implementation, this would use technical indicators
        market_data = await self.engine.get_market_data(symbol)
        
        # Random strategy for demonstration
        rsi = random.randint(20, 80)
        trend = random.choice(['bullish', 'bearish', 'neutral'])
        
        signal = None
        if rsi < 30 and trend == 'bullish':
            signal = 'buy'
        elif rsi > 70 and trend == 'bearish':
            signal = 'sell'
            
        return {
            'symbol': symbol,
            'market_data': market_data,
            'analysis': {
                'rsi': rsi,
                'trend': trend,
                'signal': signal
            }
        }
    
    async def execute_trade_cycle(self):
        """Execute one trading cycle"""
        logger.info(f"\n{'='*50}")
        logger.info(f"Trade Cycle #{self.trade_count + 1}")
        logger.info(f"{'='*50}")
        
        for symbol in self.trading_pairs:
            try:
                # Analyze market
                analysis = await self.analyze_market(symbol)
                logger.info(f"\n{symbol} Analysis:")
                logger.info(f"  RSI: {analysis['analysis']['rsi']}")
                logger.info(f"  Trend: {analysis['analysis']['trend']}")
                logger.info(f"  Signal: {analysis['analysis']['signal'] or 'No trade'}")
                
                # Execute trade if signal
                if analysis['analysis']['signal']:
                    amount = 0.001 if 'BTC' in symbol else 0.01
                    
                    order = {
                        'symbol': symbol,
                        'side': analysis['analysis']['signal'],
                        'amount': amount,
                        'type': 'market'
                    }
                    
                    logger.info(f"\nExecuting {order['side'].upper()} order for {amount} {symbol.split('/')[0]}")
                    
                    # Execute trade
                    result = await self.engine.execute_trade(order)
                    self.trade_count += 1
                    
                    # Log results based on mode
                    if self.mode == 'simulated':
                        if 'results' in result and 'simulated' in result['results']:
                            sim = result['results']['simulated']
                            logger.info(f"  Executed at: ${sim.get('price', 0):.2f}")
                            logger.info(f"  Status: {sim.get('status', 'unknown')}")
                            logger.info(f"  Slippage: {sim.get('slippage', 0)*10000:.1f} bps")
                    
                    elif self.mode == 'comparison':
                        if 'divergence_analysis' in result:
                            div = result['divergence_analysis']
                            logger.info(f"  Price divergence: {div.get('price_divergence_pct', 0):.2f}%")
                            if div.get('alert') == 'high_divergence':
                                logger.warning("  ⚠️  HIGH DIVERGENCE DETECTED!")
                    
                    # Store trade
                    self.trade_history.append({
                        'timestamp': datetime.utcnow().isoformat(),
                        'trade_num': self.trade_count,
                        'symbol': symbol,
                        'order': order,
                        'result': result
                    })
                    
            except Exception as e:
                logger.error(f"Error trading {symbol}: {e}")
        
        # Portfolio status
        portfolio = await self.engine.get_portfolio_status()
        logger.info("\nPortfolio Status:")
        
        if self.mode == 'simulated' and 'simulated' in portfolio:
            sim_portfolio = portfolio['simulated']
            logger.info(f"  Balance: ${sim_portfolio.get('total_value', 0):.2f}")
            logger.info(f"  Total trades: {sim_portfolio.get('total_trades', 0)}")
            logger.info(f"  Win rate: {sim_portfolio.get('win_rate', 0)*100:.1f}%")
            
        # Analytics
        if self.trade_count > 0:
            analytics = self.engine.get_execution_analytics()
            logger.info(f"\nExecution Analytics:")
            logger.info(f"  Total executions: {analytics['total_executions']}")
            
            if self.mode == 'comparison' and 'divergence_stats' in analytics:
                stats = analytics['divergence_stats']
                logger.info(f"  Avg divergence: {stats['average_price_divergence']*100:.2f}%")
    
    async def generate_report(self):
        """Generate trading report"""
        if self.mode == 'comparison' and len(self.engine.execution_history) > 1:
            # Get last real and simulated data for comparison
            last_exec = self.engine.execution_history[-1]
            if 'results' in last_exec:
                results = last_exec['results']
                if 'real' in results and 'simulated' in results:
                    report = self.reporter.generate_comparison_report(
                        results['real'],
                        results['simulated'],
                        self.engine.execution_history
                    )
                    
                    # Save report
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    filename = f"live_trading_report_{timestamp}.json"
                    with open(filename, 'w') as f:
                        json.dump(report, f, indent=2)
                    
                    logger.info(f"\n📊 Report saved to {filename}")
                    
                    # Show summary
                    if 'summary' in report:
                        logger.info(f"  Accuracy: {report['summary']['overall_accuracy']:.1f}%")
                        logger.info(f"  Confidence: {report['summary']['confidence_level']}")
    
    async def run(self, duration_minutes=5, interval_seconds=30):
        """Run the trading bot"""
        await self.initialize()
        
        logger.info(f"\n🤖 Starting Live Trading Bot")
        logger.info(f"Mode: {self.mode}")
        logger.info(f"Duration: {duration_minutes} minutes")
        logger.info(f"Trade interval: {interval_seconds} seconds")
        logger.info(f"Trading pairs: {', '.join(self.trading_pairs)}")
        
        start_time = datetime.utcnow()
        end_time = start_time.timestamp() + (duration_minutes * 60)
        
        while datetime.utcnow().timestamp() < end_time:
            try:
                await self.execute_trade_cycle()
                
                # Generate report periodically
                if self.trade_count > 0 and self.trade_count % 5 == 0:
                    await self.generate_report()
                
                # Wait for next cycle
                remaining = end_time - datetime.utcnow().timestamp()
                if remaining > interval_seconds:
                    logger.info(f"\n⏳ Waiting {interval_seconds}s for next cycle...")
                    await asyncio.sleep(interval_seconds)
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}", exc_info=True)
                await asyncio.sleep(10)
        
        # Final summary
        await self.shutdown()
    
    async def shutdown(self):
        """Cleanup and final report"""
        logger.info(f"\n{'='*60}")
        logger.info("TRADING SESSION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total trades executed: {self.trade_count}")
        
        if self.trade_count > 0:
            # Final analytics
            analytics = self.engine.get_execution_analytics()
            logger.info(f"\nFinal Analytics:")
            logger.info(f"  Mode: {analytics['mode']}")
            logger.info(f"  Total executions: {analytics['total_executions']}")
            
            # Save trade history
            filename = f"trade_history_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(self.trade_history, f, indent=2)
            logger.info(f"\n📁 Trade history saved to {filename}")
            
            # Generate final report
            await self.generate_report()
        
        await self.engine.close()
        logger.info("\n✅ Trading bot shutdown complete")


async def main():
    """Run live trading simulation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run live trading simulation')
    parser.add_argument('--mode', default='simulated', 
                       choices=['real', 'simulated', 'hybrid', 'comparison', 'shadow'],
                       help='Trading mode')
    parser.add_argument('--duration', type=int, default=5, 
                       help='Duration in minutes')
    parser.add_argument('--interval', type=int, default=30,
                       help='Trade interval in seconds')
    
    args = parser.parse_args()
    
    # Run trading bot
    bot = LiveTradingBot(mode=args.mode)
    await bot.run(duration_minutes=args.duration, interval_seconds=args.interval)


if __name__ == "__main__":
    # For container testing, we'll start in simulated mode
    print("\n🚀 Starting Live Trading Simulation in Container\n")
    
    # Set mode from environment or default to simulated
    mode = os.getenv('TRADING_MODE', 'simulated')
    
    bot = LiveTradingBot(mode=mode)
    asyncio.run(bot.run(duration_minutes=10, interval_seconds=20))