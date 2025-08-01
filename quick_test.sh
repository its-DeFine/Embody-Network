#!/bin/bash

echo "=== Quick System Test ==="

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# 1. Health check
echo -e "\n1. Health Check:"
curl -s http://localhost:8000/health | jq '.' || echo "API not ready yet"

# 2. Test login
echo -e "\n2. Testing Login:"
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')

if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo "✅ Login successful!"
    echo "Token: ${TOKEN:0:50}..."
else
    echo "❌ Login failed"
    exit 1
fi

# 3. Test API
echo -e "\n3. Testing API - List Agents:"
curl -s http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" | jq '.' | head -20

# 4. Check frontend
echo -e "\n4. Frontend Status:"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
echo "Frontend HTTP Status: $STATUS"

echo -e "\n✅ System is running!"
echo "Access the UI at: http://localhost:8000"
echo "Login with: admin@example.com / admin123"