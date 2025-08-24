#!/bin/bash

# Embody Network Orchestrator Registration Script
# This script helps orchestrators register with the remote manager

set -e

echo "======================================"
echo "Embody Network Orchestrator Registration"
echo "======================================"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Error: .env file not found"
    echo "Please create .env from .env.orchestrator-template"
    exit 1
fi

# Validate required variables
if [ -z "$ORCHESTRATOR_ID" ]; then
    echo "❌ Error: ORCHESTRATOR_ID not set in .env"
    exit 1
fi

if [ -z "$MANAGER_API_KEY" ]; then
    echo "❌ Error: MANAGER_API_KEY not set in .env"
    exit 1
fi

if [ -z "$ETH_ADDRESS" ]; then
    echo "❌ Error: ETH_ADDRESS not set in .env"
    exit 1
fi

# Get public IP if not set
if [ "$PUBLIC_IP" == "auto" ] || [ -z "$PUBLIC_IP" ]; then
    echo "🔍 Detecting public IP..."
    PUBLIC_IP=$(curl -s https://api.ipify.org)
    echo "   Public IP: $PUBLIC_IP"
fi

# Check if orchestrator is running
echo "🔍 Checking orchestrator status..."
if ! docker ps | grep -q embody-orchestrator; then
    echo "❌ Error: Orchestrator container not running"
    echo "Please start with: docker-compose -f docker-compose.orchestrator.yml up -d"
    exit 1
fi

# Get orchestrator info
echo "📊 Getting orchestrator information..."
ORCH_INFO=$(docker exec embody-orchestrator curl -s http://localhost:9995/status || echo "{}")

# Prepare registration data
REGISTRATION_DATA=$(cat <<EOF
{
  "orchestrator_id": "$ORCHESTRATOR_ID",
  "name": "${ORCHESTRATOR_NAME:-$ORCHESTRATOR_ID}",
  "address": "http://$PUBLIC_IP:${ORCHESTRATOR_PORT:-9995}",
  "eth_address": "$ETH_ADDRESS",
  "capabilities": ["agent-net", "byoc"],
  "metadata": {
    "region": "${REGION:-unknown}",
    "gpu": ${GPU_ENABLED:-false},
    "public_ip": "$PUBLIC_IP",
    "version": "1.0.0"
  }
}
EOF
)

echo "📝 Registration data:"
echo "$REGISTRATION_DATA" | jq '.' 2>/dev/null || echo "$REGISTRATION_DATA"

# Register with manager
echo ""
echo "📡 Registering with Embody Network Manager..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $MANAGER_API_KEY" \
    -d "$REGISTRATION_DATA" \
    "${MANAGER_URL}/v1/orchestrators/register" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

# Check response
if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    echo "✅ Successfully registered!"
    echo ""
    echo "Registration details:"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    echo ""
    echo "🎉 Your orchestrator is now part of Embody Network!"
    echo ""
    echo "Next steps:"
    echo "1. Monitor your orchestrator: docker logs embody-monitor -f"
    echo "2. Check earnings: curl ${MANAGER_URL}/v1/orchestrators/$ORCHESTRATOR_ID/payments -H 'X-API-Key: $MANAGER_API_KEY'"
    echo "3. View status: curl ${MANAGER_URL}/v1/orchestrators/$ORCHESTRATOR_ID/status -H 'X-API-Key: $MANAGER_API_KEY'"
elif [ "$HTTP_CODE" == "409" ]; then
    echo "ℹ️  Orchestrator already registered"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
else
    echo "❌ Registration failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check your API key is valid"
    echo "2. Ensure orchestrator is accessible on port ${ORCHESTRATOR_PORT:-9995}"
    echo "3. Verify firewall allows incoming connections"
    echo "4. Contact support at orchestrators@embody.network"
    exit 1
fi