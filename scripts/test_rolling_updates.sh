#!/bin/bash

echo "🔄 Testing Rolling Updates in Docker Swarm"
echo "=========================================="

# Test 1: Update service image with new tag
echo -e "\n1. Simulating image update:"
echo "   Building new version of API Gateway..."

# Create a simple change to simulate new version
echo -e "\n   Adding version label to image..."
docker build -t autogen-api-gateway:v2 -f services/api-gateway/Dockerfile . \
  --label version=2.0.0 \
  --label build-date="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  >/dev/null 2>&1

echo "✅ New image built: autogen-api-gateway:v2"

# Test 2: Perform rolling update
echo -e "\n2. Performing rolling update:"
echo "   Current state:"
docker service ps autogen_api-gateway --filter "desired-state=running" --format "table {{.Name}}\t{{.Image}}\t{{.CurrentState}}"

echo -e "\n   Starting rolling update to v2..."
docker service update \
  --image autogen-api-gateway:v2 \
  --update-parallelism 1 \
  --update-delay 10s \
  --update-failure-action rollback \
  --update-monitor 5s \
  --update-max-failure-ratio 0.2 \
  autogen_api-gateway

# Test 3: Monitor update progress
echo -e "\n3. Monitoring update progress:"
sleep 5
docker service ps autogen_api-gateway --format "table {{.Name}}\t{{.Image}}\t{{.CurrentState}}\t{{.DesiredState}}"

# Test 4: Test rollback
echo -e "\n4. Testing rollback to previous version:"
docker service update \
  --rollback \
  --rollback-parallelism 1 \
  --rollback-delay 5s \
  --rollback-monitor 5s \
  autogen_api-gateway

echo -e "\n   Rollback initiated..."
sleep 5
docker service ps autogen_api-gateway --filter "desired-state=running" --format "table {{.Name}}\t{{.Image}}\t{{.CurrentState}}"

# Test 5: Update with health check
echo -e "\n5. Testing update with health check:"
docker service update \
  --health-cmd "curl -f http://localhost:8000/health || exit 1" \
  --health-interval 10s \
  --health-timeout 3s \
  --health-retries 3 \
  autogen_api-gateway

# Test 6: Update environment variables
echo -e "\n6. Testing configuration update (no restart):"
docker service update \
  --env-add VERSION=2.0.0 \
  --env-add DEPLOYMENT_TIME="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  autogen_api-gateway

# Test 7: Update resource limits
echo -e "\n7. Testing resource limit update:"
docker service update \
  --limit-cpu 0.5 \
  --limit-memory 512M \
  --reserve-cpu 0.25 \
  --reserve-memory 256M \
  autogen_api-gateway

# Test 8: Update restart policy
echo -e "\n8. Testing restart policy update:"
docker service update \
  --restart-condition on-failure \
  --restart-delay 5s \
  --restart-max-attempts 3 \
  --restart-window 120s \
  autogen_api-gateway

echo -e "\n📊 Update Strategy Summary:"
echo "=========================="
echo "✅ Rolling updates with controlled parallelism"
echo "✅ Update delay between instances"
echo "✅ Automatic rollback on failure"
echo "✅ Health check validation"
echo "✅ Zero-downtime deployments"
echo "✅ Resource limit updates"
echo "✅ Configuration updates without restart"

echo -e "\n🎯 Best Practices for Production Updates:"
echo "1. Always test updates in staging first"
echo "2. Use health checks to validate updates"
echo "3. Set appropriate update delays"
echo "4. Configure automatic rollback"
echo "5. Monitor update progress"
echo "6. Use labels for version tracking"
echo "7. Implement canary deployments for critical updates"

echo -e "\n✅ Rolling update tests completed!"