#!/usr/bin/env python3
"""
Real Trading Agent with Live Market Data

This agent uses actual market data from Yahoo Finance and other providers
to make trading decisions and execute simulated trades at real market prices.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis.asyncio as redis
from app.market_data import market_data_service

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealTradingAgent:
    """Trading agent that uses real market data"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.redis_client = None
        self.running = False
        
    async def connect(self):
        """Connect to Redis and initialize services"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = await redis.from_url(redis_url)
        
        # Initialize market data service
        await market_data_service.initialize()
        
        logger.info(f"Real trading agent {self.agent_id} connected")
        
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process task with real market data"""
        task_type = task.get('type')
        data = task.get('data', {})
        
        logger.info(f"Processing {task_type} task with real market data")
        
        if task_type == 'analysis':
            return await self.analyze_market(data)
        elif task_type == 'trading':
            return await self.execute_trade(data)
        elif task_type == 'risk':
            return await self.assess_risk(data)
        else:
            return await self.generic_task(task)
            
    async def analyze_market(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform market analysis with real data"""
        symbol = data.get('symbol') or data.get('target', 'AAPL')
        
        # Handle generic targets
        if symbol == "Technology sector stocks":
            symbols = ["AAPL", "MSFT", "GOOGL", "META", "NVDA"]
            analyses = []
            for s in symbols:
                analysis = await self.analyze_single_stock(s)
                analyses.append(f"{s}: {analysis['trend']}")
            
            return {
                "analysis": "Technology Sector Analysis",
                "findings": analyses,
                "recommendation": "Bullish on tech leaders",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return await self.analyze_single_stock(symbol)
            
    async def analyze_single_stock(self, symbol: str) -> Dict[str, Any]:
        """Analyze a single stock with real data"""
        try:
            # Get current price and quote
            current_price = await market_data_service.get_current_price(symbol)
            quote = await market_data_service.get_quote(symbol)
            
            # Get technical indicators
            indicators = await market_data_service.get_technical_indicators(symbol)
            
            # Build analysis result
            result = {
                "analysis": f"Real-time analysis for {symbol}",
                "current_price": current_price,
                "quote": quote,
                "indicators": indicators,
                "findings": [],
                "confidence": 0.0
            }
            
            # Analyze the data
            if current_price and quote:
                # Price trend
                change_percent = quote.get('changePercent', 0)
                if isinstance(change_percent, str):
                    change_percent = float(change_percent.replace('%', ''))
                
                if change_percent > 2:
                    result['findings'].append(f"Strong upward movement: +{change_percent:.2f}%")
                    result['trend'] = 'Strongly Bullish'
                    result['confidence'] = 0.85
                elif change_percent > 0:
                    result['findings'].append(f"Positive movement: +{change_percent:.2f}%")
                    result['trend'] = 'Bullish'
                    result['confidence'] = 0.65
                elif change_percent < -2:
                    result['findings'].append(f"Strong downward movement: {change_percent:.2f}%")
                    result['trend'] = 'Strongly Bearish'
                    result['confidence'] = 0.85
                else:
                    result['findings'].append(f"Negative movement: {change_percent:.2f}%")
                    result['trend'] = 'Bearish'
                    result['confidence'] = 0.65
                    
            # Technical indicators analysis
            if indicators:
                # RSI
                rsi = indicators.get('rsi')
                if rsi:
                    result['findings'].append(f"RSI: {rsi:.2f} ({indicators.get('rsi_signal', 'neutral')})")
                    
                # MACD
                macd_trend = indicators.get('macd_signal_trend')
                if macd_trend:
                    result['findings'].append(f"MACD: {macd_trend}")
                    
                # Bollinger Bands
                bb_signal = indicators.get('bb_signal')
                if bb_signal:
                    result['findings'].append(f"Bollinger Bands: {bb_signal}")
                    
            result['timestamp'] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return {
                "analysis": f"Error analyzing {symbol}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def execute_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade with real market prices"""
        action = data.get('action', 'buy')
        symbol = data.get('symbol', 'AAPL')
        quantity = data.get('quantity', 0)
        order_type = data.get('order_type', 'market')
        
        try:
            # Get real market price
            current_price = await market_data_service.get_current_price(symbol)
            
            if not current_price:
                return {
                    "error": f"Could not get price for {symbol}",
                    "status": "failed"
                }
                
            # Get quote for bid/ask
            quote = await market_data_service.get_quote(symbol)
            
            # Determine execution price based on order type
            if order_type == 'market':
                # For market orders, use bid/ask or current price
                if action == 'buy' and quote and 'ask' in quote:
                    execution_price = quote['ask']
                elif action == 'sell' and quote and 'bid' in quote:
                    execution_price = quote['bid']
                else:
                    execution_price = current_price
            else:
                # For limit orders, check if limit price is provided
                limit_price = data.get('limit_price')
                if limit_price:
                    # In real trading, this would check if limit can be filled
                    # For simulation, we'll use current price if favorable
                    if action == 'buy' and current_price <= limit_price:
                        execution_price = current_price
                    elif action == 'sell' and current_price >= limit_price:
                        execution_price = current_price
                    else:
                        return {
                            "status": "pending",
                            "message": f"Limit order not filled. Current: ${current_price}, Limit: ${limit_price}"
                        }
                else:
                    execution_price = current_price
                    
            # Calculate total value
            total_value = execution_price * quantity
            
            # Build result
            result = {
                "action": action,
                "symbol": symbol,
                "quantity": quantity,
                "order_type": order_type,
                "status": "executed",
                "execution_price": execution_price,
                "market_price": current_price,
                "total_value": total_value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add quote details if available
            if quote:
                result['quote'] = {
                    "bid": quote.get('bid'),
                    "ask": quote.get('ask'),
                    "spread": (quote.get('ask', 0) - quote.get('bid', 0)) if quote.get('ask') and quote.get('bid') else None,
                    "volume": quote.get('volume'),
                    "day_high": quote.get('high'),
                    "day_low": quote.get('low')
                }
                
            # Add commission (simulated)
            commission = 0.01 * total_value  # 1% commission
            result['commission'] = commission
            result['net_total'] = total_value + commission if action == 'buy' else total_value - commission
            
            logger.info(f"Executed {action} order: {quantity} {symbol} @ ${execution_price:.2f}")
            
            # For compatibility with existing system
            if action == 'buy':
                result['price'] = execution_price
                result['total'] = result['net_total']
                result['total_cost'] = result['net_total']
            else:
                result['price'] = execution_price
                result['total'] = result['net_total']
                result['total_proceeds'] = result['net_total']
                
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade for {symbol}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def assess_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk with real market data"""
        portfolio = data.get('portfolio', {})
        total_capital = data.get('total_capital', 100000)
        
        try:
            # Get current prices for portfolio
            portfolio_value = 0
            positions = []
            
            for symbol, quantity in portfolio.items():
                price = await market_data_service.get_current_price(symbol)
                if price:
                    position_value = price * quantity
                    portfolio_value += position_value
                    
                    # Get quote for more details
                    quote = await market_data_service.get_quote(symbol)
                    
                    positions.append({
                        "symbol": symbol,
                        "quantity": quantity,
                        "current_price": price,
                        "position_value": position_value,
                        "percent_of_portfolio": (position_value / total_capital) * 100,
                        "day_change": quote.get('change') if quote else 0,
                        "volatility": abs(quote.get('changePercent', 0)) if quote else 0
                    })
                    
            # Calculate risk metrics
            exposure_ratio = portfolio_value / total_capital
            
            # Simple risk scoring based on exposure and volatility
            avg_volatility = sum(p['volatility'] for p in positions) / len(positions) if positions else 0
            
            if exposure_ratio > 0.9:
                risk_score = 0.8
                risk_level = "HIGH"
            elif exposure_ratio > 0.7:
                risk_score = 0.6
                risk_level = "MEDIUM"
            else:
                risk_score = 0.3
                risk_level = "LOW"
                
            # Adjust for volatility
            if avg_volatility > 5:
                risk_score = min(risk_score + 0.2, 1.0)
                
            result = {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "portfolio_value": portfolio_value,
                "total_capital": total_capital,
                "exposure_ratio": exposure_ratio,
                "positions": positions,
                "factors": [
                    f"Portfolio exposure: {exposure_ratio:.2%}",
                    f"Average volatility: {avg_volatility:.2f}%",
                    f"Number of positions: {len(positions)}"
                ],
                "recommendations": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add recommendations
            if exposure_ratio > 0.9:
                result['recommendations'].append("Consider reducing exposure")
            if avg_volatility > 5:
                result['recommendations'].append("High volatility detected - consider hedging")
            if len(positions) < 3:
                result['recommendations'].append("Consider diversifying portfolio")
                
            return result
            
        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            return {
                "risk_score": 0.5,
                "risk_level": "UNKNOWN",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def generic_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic tasks"""
        return {
            "status": "completed",
            "message": f"Processed {task.get('type')} task",
            "data": task.get('data', {}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def run(self):
        """Main agent loop"""
        await self.connect()
        self.running = True
        
        # Subscribe to tasks
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"agent:{self.agent_id}:tasks")
        
        logger.info(f"Real trading agent {self.agent_id} listening for tasks...")
        
        try:
            async for message in pubsub.listen():
                if not self.running:
                    break
                    
                if message['type'] == 'message':
                    try:
                        # Parse task
                        task_data = json.loads(message['data'])
                        task_id = task_data.get('id', 'unknown')
                        
                        logger.info(f"Received task {task_id}")
                        
                        # Update task status
                        task_data['status'] = 'processing'
                        await self.redis_client.set(
                            f"task:{task_id}",
                            json.dumps(task_data)
                        )
                        
                        # Process task with real market data
                        result = await self.process_task(task_data)
                        
                        # Update task with result
                        task_data['status'] = 'completed'
                        task_data['result'] = result
                        task_data['completed_at'] = datetime.utcnow().isoformat()
                        
                        await self.redis_client.set(
                            f"task:{task_id}",
                            json.dumps(task_data)
                        )
                        
                        # Publish completion event
                        await self.redis_client.lpush(
                            "events:global",
                            json.dumps({
                                "type": "task.completed",
                                "source": f"agent:{self.agent_id}",
                                "data": {
                                    "task_id": task_id,
                                    "result": result
                                }
                            })
                        )
                        
                        logger.info(f"Task {task_id} completed successfully")
                        
                    except Exception as e:
                        logger.error(f"Error processing task: {e}")
                        
        except Exception as e:
            logger.error(f"Agent error: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources"""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info(f"Real trading agent {self.agent_id} stopped")


# Main execution
if __name__ == "__main__":
    agent_id = os.getenv("AGENT_ID", "real_trader_001")
    agent_type = os.getenv("AGENT_TYPE", "trading")
    
    agent = RealTradingAgent(agent_id, agent_type)
    
    # Run the agent
    asyncio.run(agent.run())