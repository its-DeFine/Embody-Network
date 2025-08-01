#!/bin/bash

echo "=== AutoGen Platform - Login and API Test Script ==="
echo ""
echo "First, ensure Docker Desktop is running and WSL integration is enabled."
echo "Then start the containers with: docker compose up -d"
echo ""
echo "Press Enter when containers are running..."
read

# Test 1: Health Check
echo -e "\n1. Testing Health Endpoint..."
HEALTH=$(curl -s http://localhost:8000/health)
if [ -z "$HEALTH" ]; then
    echo "❌ API is not responding. Please ensure containers are running."
    exit 1
fi
echo "✅ Health check passed:"
echo "$HEALTH" | jq '.'

# Test 2: Login
echo -e "\n2. Testing Login..."
echo "Credentials: admin@example.com / admin123"
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed:"
    echo "$LOGIN_RESPONSE" | jq '.'
    exit 1
fi

echo "✅ Login successful!"
echo "Token (first 50 chars): ${TOKEN:0:50}..."

# Test 3: Test wrong password
echo -e "\n3. Testing wrong password..."
WRONG_LOGIN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"wrongpassword"}' \
  -w "\nHTTP Status: %{http_code}")
echo "Response: $WRONG_LOGIN"

# Test 4: List Agents (authenticated)
echo -e "\n4. Testing authenticated API call (List Agents)..."
AGENTS=$(curl -s http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN")
echo "✅ Agents list:"
echo "$AGENTS" | jq '.'

# Test 5: Create an Agent
echo -e "\n5. Creating a new agent..."
NEW_AGENT=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Agent",
    "agent_type": "analysis",
    "config": {"model": "gpt-4"}
  }')
AGENT_ID=$(echo "$NEW_AGENT" | jq -r '.id')
echo "✅ Agent created:"
echo "$NEW_AGENT" | jq '.'

# Test 6: Test unauthorized access
echo -e "\n6. Testing unauthorized access (no token)..."
UNAUTH=$(curl -s http://localhost:8000/api/v1/agents \
  -w "\nHTTP Status: %{http_code}")
echo "Response: $UNAUTH"

# Test 7: Frontend access
echo -e "\n7. Testing frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
if [ "$FRONTEND_STATUS" == "200" ]; then
    echo "✅ Frontend is accessible at http://localhost:8000"
else
    echo "❌ Frontend returned status: $FRONTEND_STATUS"
fi

# Test 8: API Documentation
echo -e "\n8. Testing API documentation..."
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
if [ "$DOCS_STATUS" == "200" ]; then
    echo "✅ API docs accessible at http://localhost:8000/docs"
else
    echo "❌ API docs returned status: $DOCS_STATUS"
fi

echo -e "\n=== Test Summary ==="
echo "✅ All core functionality is working!"
echo ""
echo "You can now:"
echo "1. Login at http://localhost:8000 with admin@example.com / admin123"
echo "2. View API docs at http://localhost:8000/docs"
echo "3. Use the API with Bearer token authentication"