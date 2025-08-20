#!/bin/bash
# Orchestrator entrypoint with auto-registration

echo "Starting orchestrator with auto-registration..."

# Run auto-registration in background
if [ -f /app/scripts/auto_register_orchestrator.py ]; then
    echo "Running auto-registration..."
    python3 /app/scripts/auto_register_orchestrator.py &
else
    echo "Auto-registration script not found, skipping..."
fi

# Start the actual orchestrator
echo "Starting Livepeer orchestrator..."
exec /usr/local/bin/livepeer "$@"