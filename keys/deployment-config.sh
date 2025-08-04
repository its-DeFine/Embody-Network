#!/bin/bash
# Deployment configuration with PGP keys

# Master public key path (for instances to verify master)
export MASTER_PGP_PUBLIC_KEY_PATH="/app/keys/master-public.asc"

# Instance private key path (for signing requests)
export INSTANCE_PGP_PRIVATE_KEY_PATH="/app/keys/instance-private.asc"

# Function to request one-time key
request_otk() {
    local PURPOSE="${1:-instance_registration}"
    local MASTER_URL="${2:-http://localhost:8000}"
    
    # Create signed data
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    DATA=$(cat <<JSON
{
    "timestamp": "$TIMESTAMP",
    "purpose": "$PURPOSE",
    "requester": "$HOSTNAME"
}
JSON
)
    
    # Sign the data
    SIGNATURE=$(echo -n "$DATA" | gpg --detach-sign --armor)
    
    # Make request
    curl -X POST "$MASTER_URL/api/v1/security/generate-otk" \
        -H "Content-Type: application/json" \
        -d "{
            \"signed_data\": \"$DATA\",
            \"pgp_signature\": \"$SIGNATURE\",
            \"purpose\": \"$PURPOSE\"
        }"
}

# Function to start instance with OTK
start_instance_with_otk() {
    local MASTER_URL="${1:-http://localhost:8000}"
    
    echo "Requesting one-time key from master..."
    RESPONSE=$(request_otk "instance_registration" "$MASTER_URL")
    
    OTK=$(echo "$RESPONSE" | jq -r '.data.key')
    
    if [ -z "$OTK" ] || [ "$OTK" = "null" ]; then
        echo "Failed to get one-time key"
        exit 1
    fi
    
    echo "Got one-time key. Starting instance..."
    
    # Start container with OTK
    docker run -d \
        --name trading-instance \
        -e INSTANCE_API_KEY="$OTK" \
        -e MASTER_URL="$MASTER_URL" \
        -v "$PWD/keys:/app/keys:ro" \
        operation-app
}
