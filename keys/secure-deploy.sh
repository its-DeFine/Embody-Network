#!/bin/bash
# Secure deployment script for GitHub

set -e

# Check for required environment variables
if [ -z "$MASTER_URL" ]; then
    echo "Error: MASTER_URL not set"
    exit 1
fi

# Import deployment functions
source ./keys/deployment-config.sh

# Start instance with one-time key
start_instance_with_otk "$MASTER_URL"

echo "Instance started securely!"
