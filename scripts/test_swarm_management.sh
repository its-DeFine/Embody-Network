#!/bin/bash

echo "🐝 Testing Docker Swarm Management Commands"
echo "=========================================="

# Test 1: List services
echo -e "\n1. Listing all services:"
docker service ls

# Test 2: Scale services
echo -e "\n2. Scaling API Gateway to 3 replicas:"
docker service scale autogen_api-gateway=3

# Wait for scaling
sleep 5

# Test 3: Check service status
echo -e "\n3. Checking service details:"
docker service ps autogen_api-gateway --no-trunc

# Test 4: List tasks
echo -e "\n4. Listing all tasks in the stack:"
docker stack ps autogen --no-trunc

# Test 5: Check service logs
echo -e "\n5. Getting API Gateway logs:"
docker service logs autogen_api-gateway --tail 5

# Test 6: Inspect a service
echo -e "\n6. Inspecting API Gateway service:"
docker service inspect autogen_api-gateway --pretty

# Test 7: Update service environment variable
echo -e "\n7. Testing service update with new environment variable:"
docker service update --env-add TEST_VAR=hello autogen_api-gateway

# Test 8: Check node status
echo -e "\n8. Checking node status:"
docker node ls

# Test 9: List networks
echo -e "\n9. Listing overlay networks:"
docker network ls --filter driver=overlay

# Test 10: Test service connectivity
echo -e "\n10. Testing API Gateway connectivity:"
curl -s http://localhost:8000/health || echo "API Gateway not responding"

echo -e "\n✅ Swarm management commands tested!"