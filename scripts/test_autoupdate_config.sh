#!/bin/bash
# Test script for auto-update configuration
# Created: 2025-08-14

echo "=== Testing Auto-Update Configuration ==="
echo

# Check if docker-compose file exists
if [ ! -f "/home/geo/operation/autonomy/docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found in autonomy directory"
    exit 1
fi

echo "✅ docker-compose.yml found"

# Check orchestrator image configuration
echo -n "Checking orchestrator image configuration... "
if grep -q "ghcr.io/its-define/autonomy-orchestrator:autonomy-latest" /home/geo/operation/autonomy/docker-compose.yml; then
    echo "✅ Using GHCR image"
else
    echo "❌ Not using GHCR image"
    exit 1
fi

# Check Watchtower configuration
echo -n "Checking Watchtower service... "
if grep -q "watchtower:" /home/geo/operation/autonomy/docker-compose.yml; then
    echo "✅ Watchtower service configured"
else
    echo "❌ Watchtower service not found"
    exit 1
fi

# Check orchestrator labels
echo -n "Checking orchestrator labels for Watchtower... "
if grep -q "com.centurylinklabs.watchtower.enable=true" /home/geo/operation/autonomy/docker-compose.yml; then
    echo "✅ Watchtower labels configured"
else
    echo "❌ Watchtower labels not found"
    exit 1
fi

# Check GitHub workflow
echo -n "Checking GitHub workflow for auto-update... "
if [ -f "/home/geo/operation/.github/workflows/autonomy-orchestrator-autoupdate.yml" ]; then
    echo "✅ GitHub workflow exists"
else
    echo "❌ GitHub workflow not found"
    exit 1
fi

# Check submodule configuration
echo -n "Checking submodule configuration... "
if [ -f "/home/geo/operation/.gitmodules" ]; then
    if grep -q "autonomy" /home/geo/operation/.gitmodules; then
        echo "✅ Submodule configured"
    else
        echo "❌ Autonomy not in .gitmodules"
        exit 1
    fi
else
    echo "❌ .gitmodules not found"
    exit 1
fi

echo
echo "=== Configuration Test Results ==="
echo "✅ All auto-update configurations are properly set up!"
echo
echo "Next steps to activate auto-updates:"
echo "1. Ensure GHCR access is configured: docker login ghcr.io"
echo "2. Start services in autonomy directory: cd /home/geo/operation/autonomy && docker compose up -d"
echo "3. Monitor Watchtower logs: docker logs -f watchtower_orchestrator"
echo "4. The system will auto-update when new images are pushed to GHCR"