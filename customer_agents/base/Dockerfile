FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY customer_agents/base/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared /app/shared

# Copy agent code
COPY customer_agents/base/agent.py .
COPY customer_agents/base/agent_types ./agent_types

# Run the agent
CMD ["python", "-u", "agent.py"]