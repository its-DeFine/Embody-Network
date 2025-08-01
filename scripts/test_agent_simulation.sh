#!/bin/bash

echo "=== Testing Agent Simulation ==="

# Wait for services to start
sleep 3

# Step 1: Login and get token
echo -e "\n1. Getting authentication token..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

echo "Token: ${TOKEN:0:50}..."

# Step 2: Create an agent
echo -e "\n2. Creating an agent..."
AGENT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Simulated Analysis Agent",
    "agent_type": "analysis",
    "config": {"model": "gpt-4"}
  }')

AGENT_ID=$(echo "$AGENT_RESPONSE" | jq -r '.id')
echo "Created agent: $AGENT_ID"

# Step 3: Start the agent
echo -e "\n3. Starting the agent..."
curl -s -X POST http://localhost:8000/api/v1/agents/$AGENT_ID/start \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Step 4: Run the simulated agent in background
echo -e "\n4. Starting simulated agent process..."
cd /home/geo/operation/agent
export AGENT_ID=$AGENT_ID
export AGENT_TYPE="analysis"
export REDIS_URL="redis://localhost:6379"

# Make script executable and install dependencies
chmod +x simulated_agent.py
pip install redis > /dev/null 2>&1

# Run agent in background
python3 simulated_agent.py > agent.log 2>&1 &
AGENT_PID=$!
echo "Agent process started with PID: $AGENT_PID"

# Wait for agent to connect
sleep 2

# Step 5: Create a task
echo -e "\n5. Creating a task for the agent..."
TASK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "analysis",
    "data": {
      "target": "Technology sector stocks",
      "action": "analyze market trends"
    }
  }')

TASK_ID=$(echo "$TASK_RESPONSE" | jq -r '.id')
echo "Created task: $TASK_ID"

# Step 6: Wait for task completion
echo -e "\n6. Waiting for task to complete..."
for i in {1..10}; do
  sleep 2
  TASK_STATUS=$(curl -s http://localhost:8000/api/v1/tasks/$TASK_ID \
    -H "Authorization: Bearer $TOKEN" | jq '.')
  
  STATUS=$(echo "$TASK_STATUS" | jq -r '.status')
  echo "Task status: $STATUS"
  
  if [ "$STATUS" == "completed" ]; then
    echo -e "\n✅ Task completed successfully!"
    echo "Result:"
    echo "$TASK_STATUS" | jq '.result'
    break
  fi
done

# Step 7: Check agent logs
echo -e "\n7. Agent logs (last 10 lines):"
tail -10 agent.log

# Step 8: Cleanup
echo -e "\n8. Cleaning up..."
kill $AGENT_PID 2>/dev/null
echo "Agent process stopped"

echo -e "\n✅ Test completed!"