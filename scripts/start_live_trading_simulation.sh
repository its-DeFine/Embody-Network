#!/bin/bash

# Start live trading simulation in containers
# This will run actual simulated trades in the container cluster

set -e

echo "=========================================="
echo "Starting Live Trading Simulation"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
TRADING_MODE=${TRADING_MODE:-"simulated"}  # Start with simulated mode for safety
LOG_DIR="./logs/live_trading_$(date +%Y%m%d_%H%M%S)"

# Create log directory
mkdir -p "$LOG_DIR"

echo -e "${GREEN}[INFO]${NC} Starting core services..."

# 1. Ensure core services are running
docker-compose up -d rabbitmq redis

# Wait for services
echo "Waiting for services to be ready..."
sleep 10

# 2. Create a live trading agent container
echo -e "${GREEN}[INFO]${NC} Creating live trading agent container..."

cat > docker-compose.live-trading.yml << 'EOF'
version: '3.8'

services:
  live-trading-agent:
    build:
      context: ./customer_agents/base
      dockerfile: Dockerfile
    container_name: live-trading-agent-sim
    environment:
      # Core Configuration
      - AGENT_NAME=live_trading_bot
      - AGENT_TYPE=trading
      - LOG_LEVEL=INFO
      
      # Trading Mode - Start with simulated
      - TRADING_MODE=${TRADING_MODE:-simulated}
      - COMPARISON_MODE=false
      - ENABLE_TRADING=true
      - ENABLE_TESTNET=true
      
      # Simulation Settings
      - SIMULATION_INITIAL_BALANCE=10000
      - SIMULATION_VOLATILITY=1.0
      - SIMULATION_SLIPPAGE_BPS=10
      - SIMULATION_FEES=0.001
      - SIMULATION_BLACK_SWAN=true
      - SIMULATION_MARKET_IMPACT=true
      
      # Trading Configuration
      - TRADING_PAIRS=BTC/USDT,ETH/USDT
      - RISK_LIMIT=0.02
      - MAX_POSITION_SIZE=0.1
      - TRADING_INTERVAL=60  # Trade every 60 seconds
      
      # Exchange Config (for market data)
      - BINANCE_TESTNET=true
      
      # Message Queue
      - RABBITMQ_URL=amqp://admin:${RABBITMQ_PASSWORD:-password}@rabbitmq:5672
      - REDIS_URL=redis://redis:6379
      
    volumes:
      - ./customer_agents/base:/app
      - ./trading_logs:/app/logs
      - ./trading_data:/app/data
    networks:
      - autogen-network
    depends_on:
      - rabbitmq
      - redis
    restart: unless-stopped
    command: python -c "
      import asyncio
      import os
      import sys
      import logging
      from datetime import datetime
      import random
      
      sys.path.append('/app')
      
      # Configure logging
      logging.basicConfig(
          level=logging.INFO,
          format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
      )
      logger = logging.getLogger('LiveTradingBot')
      
      async def run_trading_bot():
          from dual_mode_trading import DualModeTradingEngine
          from agent_types.trading_agent import TradingAgent
          
          logger.info('Starting Live Trading Bot in {} mode'.format(os.getenv('TRADING_MODE', 'simulated')))
          
          # Initialize trading engine
          config = {
              'exchange': 'binance',
              'testnet': True,
              'trading_pairs': os.getenv('TRADING_PAIRS', 'BTC/USDT').split(',')
          }
          
          trading_engine = DualModeTradingEngine(config)
          await trading_engine.initialize()
          
          # Trading bot configuration
          trading_pairs = config['trading_pairs']
          risk_limit = float(os.getenv('RISK_LIMIT', '0.02'))
          interval = int(os.getenv('TRADING_INTERVAL', '60'))
          
          logger.info(f'Trading pairs: {trading_pairs}')
          logger.info(f'Risk limit: {risk_limit*100}%')
          logger.info(f'Trading interval: {interval} seconds')
          
          # Simple trading strategy
          trade_count = 0
          
          while True:
              try:
                  for symbol in trading_pairs:
                      # Get market data
                      market_data = await trading_engine.get_market_data(symbol)
                      logger.info(f'{symbol} market data: {market_data}')
                      
                      # Simple random trading strategy (for demonstration)
                      # In real implementation, this would use technical indicators
                      should_buy = random.random() > 0.6  # 40% chance to buy
                      should_sell = random.random() > 0.7  # 30% chance to sell
                      
                      if should_buy:
                          # Calculate position size based on risk
                          amount = 0.001 if 'BTC' in symbol else 0.01
                          
                          order = {
                              'symbol': symbol,
                              'side': 'buy',
                              'amount': amount,
                              'type': 'market'
                          }
                          
                          logger.info(f'Placing BUY order: {order}')
                          result = await trading_engine.execute_trade(order)
                          
                          trade_count += 1
                          logger.info(f'Trade #{trade_count} executed: {result}')
                          
                          # Log execution details
                          if 'results' in result:
                              if 'simulated' in result['results']:
                                  sim_result = result['results']['simulated']
                                  logger.info(f'Simulated execution: Price=${sim_result.get(\"price\", 0):.2f}, Status={sim_result.get(\"status\")}')
                      
                      elif should_sell and trade_count > 0:
                          # Only sell if we have positions
                          amount = 0.0005 if 'BTC' in symbol else 0.005
                          
                          order = {
                              'symbol': symbol,
                              'side': 'sell',
                              'amount': amount,
                              'type': 'market'
                          }
                          
                          logger.info(f'Placing SELL order: {order}')
                          result = await trading_engine.execute_trade(order)
                          
                          trade_count += 1
                          logger.info(f'Trade #{trade_count} executed: {result}')
                  
                  # Get portfolio status
                  portfolio = await trading_engine.get_portfolio_status()
                  logger.info(f'Portfolio status: {portfolio}')
                  
                  # Get execution analytics
                  if trade_count > 0:
                      analytics = trading_engine.get_execution_analytics()
                      logger.info(f'Execution analytics: {analytics}')
                  
                  # Wait for next trading interval
                  logger.info(f'Waiting {interval} seconds for next trade cycle...')
                  await asyncio.sleep(interval)
                  
              except Exception as e:
                  logger.error(f'Error in trading loop: {e}', exc_info=True)
                  await asyncio.sleep(10)
      
      # Run the trading bot
      asyncio.run(run_trading_bot())
      "

  # Monitor service to watch trades
  trade-monitor:
    build:
      context: ./customer_agents/base
      dockerfile: Dockerfile
    container_name: trade-monitor
    environment:
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    volumes:
      - ./customer_agents/base:/app
      - ./trading_logs:/app/logs
    networks:
      - autogen-network
    depends_on:
      - redis
      - live-trading-agent
    command: python -c "
      import asyncio
      import sys
      import logging
      from datetime import datetime
      
      sys.path.append('/app')
      
      logging.basicConfig(level=logging.INFO)
      logger = logging.getLogger('TradeMonitor')
      
      async def monitor_trades():
          logger.info('Trade Monitor started - watching for trading activity...')
          
          trade_count = 0
          while True:
              try:
                  # In a real implementation, this would connect to Redis
                  # and monitor actual trade events
                  logger.info(f'Monitoring... Total trades observed: {trade_count}')
                  
                  # Simulate monitoring
                  await asyncio.sleep(30)
                  trade_count += 1
                  
              except Exception as e:
                  logger.error(f'Monitor error: {e}')
                  await asyncio.sleep(5)
      
      asyncio.run(monitor_trades())
      "

networks:
  autogen-network:
    external: true

volumes:
  trading_logs:
  trading_data:
EOF

# 3. Start the trading containers
echo -e "${GREEN}[INFO]${NC} Starting trading containers..."
docker-compose -f docker-compose.live-trading.yml up -d

# 4. Wait for containers to start
echo "Waiting for containers to initialize..."
sleep 10

# 5. Check container status
echo -e "\n${GREEN}[INFO]${NC} Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(trading|monitor)"

# 6. Start following logs
echo -e "\n${GREEN}[INFO]${NC} Following trading logs (Ctrl+C to stop)..."
echo "Logs are also being saved to: $LOG_DIR"

# Save logs to file while displaying
docker-compose -f docker-compose.live-trading.yml logs -f | tee "$LOG_DIR/trading_simulation.log"