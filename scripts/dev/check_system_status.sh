#!/bin/bash

echo "=== VTuber Autonomy System Status ==="
echo ""
echo "Core Services:"

# Check NeuroSync S1
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "  ✓ NeuroSync S1: healthy (port 5001)"
else
    echo "  ✗ NeuroSync S1: offline"
fi

# Check AutoGen Agent
if curl -s http://localhost:8200/health > /dev/null 2>&1; then
    status=$(curl -s http://localhost:8200/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "running")
    echo "  ✓ AutoGen Agent: $status (port 8200)"
else
    echo "  ✗ AutoGen Agent: offline"
fi

# Check SCB Gateway
if curl -s http://localhost:8300/health > /dev/null 2>&1; then
    echo "  ✓ SCB Gateway: healthy (port 8300)"
else
    echo "  ✗ SCB Gateway: offline"
fi

# Check Orchestrator
if curl -s http://localhost:8082/health > /dev/null 2>&1; then
    echo "  ✓ Orchestrator: healthy (port 8082)"
else
    echo "  ✗ Orchestrator: offline"
fi

echo ""
echo "Streaming Infrastructure:"
echo "  ✓ NGINX RTMP: rtmp://localhost:1935/live"
echo "  ✓ HLS/Monitor: http://localhost:8085"

echo ""
echo "Management:"

# Check Central Manager
if curl -s http://localhost:8010/health > /dev/null 2>&1; then
    echo "  ✓ Central Manager: healthy (port 8010)"
else
    echo "  ✗ Central Manager: offline"
fi

echo "  ✓ Dashboard: http://localhost:8010/dashboard"

echo ""
echo "Data Stores:"
# Check Redis
if docker exec shared-redis redis-cli ping > /dev/null 2>&1; then
    echo "  ✓ Redis (shared): healthy (port 6379)"
else
    echo "  ✗ Redis: offline"
fi

# Check PostgreSQL
if docker exec autogen_postgres pg_isready > /dev/null 2>&1; then
    echo "  ✓ PostgreSQL: healthy (port 5434)"
else
    echo "  ✗ PostgreSQL: offline"
fi

# Check Neo4j
if curl -s http://localhost:7474 > /dev/null 2>&1; then
    echo "  ✓ Neo4j: healthy (port 7474/7687)"
else
    echo "  ✗ Neo4j: offline"
fi

# Check Ollama
if curl -s http://localhost:11434 > /dev/null 2>&1; then
    echo "  ✓ Ollama LLM: healthy (port 11434)"
else
    echo "  ✗ Ollama LLM: offline"
fi