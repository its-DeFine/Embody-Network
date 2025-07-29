#!/bin/bash

# Test dual-mode trading using Docker containers
# This ensures all dependencies are available

set -e

echo "=========================================="
echo "Dual-Mode Trading Docker Test"
echo "=========================================="

# Build a test container with all dependencies
echo "Building test container..."

cat > /tmp/Dockerfile.dualmode.test << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    ccxt \
    numpy \
    pandas \
    scipy \
    asyncio \
    aiohttp \
    python-dotenv

# Copy the code
COPY customer_agents/base /app/customer_agents/base
COPY scripts/test_dual_mode_local.py /app/test_dual_mode_local.py

# Set environment variables for testing
ENV PYTHONPATH=/app
ENV TRADING_MODE=comparison
ENV COMPARISON_MODE=true
ENV SIMULATION_VOLATILITY=1.0
ENV ENABLE_TESTNET=true

CMD ["python", "test_dual_mode_local.py"]
EOF

# Build the test container
docker build -f /tmp/Dockerfile.dualmode.test -t dual-mode-test .

# Run the test
echo ""
echo "Running dual-mode trading tests..."
echo ""

docker run --rm \
  -e TRADING_MODE=comparison \
  -e COMPARISON_MODE=true \
  -e SIMULATION_VOLATILITY=1.0 \
  -e BINANCE_API_KEY=test_key \
  -e BINANCE_API_SECRET=test_secret \
  -e BINANCE_TESTNET=true \
  dual-mode-test

echo ""
echo "Test completed!"