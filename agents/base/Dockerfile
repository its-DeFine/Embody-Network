FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY agents/base/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for OpenBB integration
RUN pip install --no-cache-dir httpx

# Copy shared modules
COPY shared /app/shared

# Copy agent code
COPY agents/base/agent.py .
COPY agents/base/agent_types ./agent_types
COPY agents/base/dual_mode_trading.py .
COPY agents/base/exchange_connector.py .
COPY agents/base/simulation_engine.py .
COPY agents/base/portfolio_optimizer.py .
COPY agents/base/comparison_reporter.py .

# Environment variables for OpenBB service
ENV OPENBB_SERVICE_URL=http://openbb-adapter:8003

# Run the agent
CMD ["python", "-u", "agent.py"]