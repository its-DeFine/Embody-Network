#!/bin/bash

echo "=== Running Simulated Agent Locally ==="

# Install required Python packages if needed
echo "Checking dependencies..."
pip install redis asyncio > /dev/null 2>&1

# Get the agent ID from the API
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

# Get first agent ID
AGENT_ID=$(curl -s http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')

if [ -z "$AGENT_ID" ] || [ "$AGENT_ID" == "null" ]; then
    echo "No agents found. Creating one..."
    AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"name": "Simulated Agent", "agent_type": "analysis", "config": {}}' | jq -r '.id')
fi

echo "Using Agent ID: $AGENT_ID"

# Run the agent
export AGENT_ID=$AGENT_ID
export AGENT_TYPE="analysis"
export REDIS_URL="redis://localhost:6379"

echo "Starting agent..."
python3 simulated_agent.py