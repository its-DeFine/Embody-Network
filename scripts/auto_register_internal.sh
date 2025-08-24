#!/bin/bash
# Auto-register internal Livepeer orchestrator on startup

echo "Waiting for manager to be ready..."
sleep 30

echo "Registering internal Livepeer orchestrator..."
python3 /scripts/register_internal_orchestrator.py

if [ $? -eq 0 ]; then
    echo "Registration successful"
else
    echo "Registration failed, will be retried by monitor"
fi

# Keep container running for monitoring
echo "Registration complete, keeping container alive..."
tail -f /dev/null