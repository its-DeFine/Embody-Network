#!/bin/bash

# Script to set up PGP keys for secure instance communication

echo "==========================================="
echo "PGP KEY SETUP FOR SECURE DEPLOYMENT"
echo "==========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if gpg is installed
if ! command -v gpg &> /dev/null; then
    echo -e "${RED}GPG is not installed. Please install it first.${NC}"
    exit 1
fi

# Key directory
KEY_DIR="./keys"
mkdir -p "$KEY_DIR"

echo -e "\n${YELLOW}1. GENERATE MASTER PGP KEY${NC}"
echo "This key will be used to sign one-time key requests."
echo ""

# Check if master key already exists
if [ -f "$KEY_DIR/master-private.asc" ]; then
    echo -e "${YELLOW}Master key already exists at $KEY_DIR/master-private.asc${NC}"
    echo "Do you want to generate a new one? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Using existing key."
    else
        # Generate new master key
        gpg --batch --generate-key <<EOF
Key-Type: RSA
Key-Length: 4096
Name-Real: Trading Platform Master
Name-Email: master@trading-platform.local
Expire-Date: 2y
%no-protection
%commit
EOF
        
        # Export keys
        KEY_ID=$(gpg --list-secret-keys --keyid-format LONG | grep sec | tail -1 | awk '{print $2}' | cut -d'/' -f2)
        gpg --armor --export-secret-keys "$KEY_ID" > "$KEY_DIR/master-private.asc"
        gpg --armor --export "$KEY_ID" > "$KEY_DIR/master-public.asc"
        
        echo -e "${GREEN}Master key generated!${NC}"
        echo "Fingerprint: $(gpg --fingerprint $KEY_ID | grep fingerprint | tail -1)"
    fi
else
    # Generate new master key
    echo "Generating new master PGP key..."
    gpg --batch --generate-key <<EOF
Key-Type: RSA
Key-Length: 4096
Name-Real: Trading Platform Master
Name-Email: master@trading-platform.local
Expire-Date: 2y
%no-protection
%commit
EOF
    
    # Export keys
    KEY_ID=$(gpg --list-secret-keys --keyid-format LONG | grep sec | tail -1 | awk '{print $2}' | cut -d'/' -f2)
    gpg --armor --export-secret-keys "$KEY_ID" > "$KEY_DIR/master-private.asc"
    gpg --armor --export "$KEY_ID" > "$KEY_DIR/master-public.asc"
    
    echo -e "${GREEN}Master key generated!${NC}"
    echo "Fingerprint: $(gpg --fingerprint $KEY_ID | grep fingerprint | tail -1)"
fi

echo -e "\n${YELLOW}2. GENERATE INSTANCE KEY (Optional)${NC}"
echo "Generate a key for a specific instance? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Enter instance name (e.g., production-1):"
    read -r INSTANCE_NAME
    
    gpg --batch --generate-key <<EOF
Key-Type: RSA
Key-Length: 4096
Name-Real: Trading Instance $INSTANCE_NAME
Name-Email: $INSTANCE_NAME@trading-platform.local
Expire-Date: 1y
%no-protection
%commit
EOF
    
    # Export instance keys
    INSTANCE_KEY_ID=$(gpg --list-secret-keys --keyid-format LONG | grep sec | tail -1 | awk '{print $2}' | cut -d'/' -f2)
    gpg --armor --export-secret-keys "$INSTANCE_KEY_ID" > "$KEY_DIR/instance-$INSTANCE_NAME-private.asc"
    gpg --armor --export "$INSTANCE_KEY_ID" > "$KEY_DIR/instance-$INSTANCE_NAME-public.asc"
    
    echo -e "${GREEN}Instance key generated!${NC}"
fi

echo -e "\n${YELLOW}3. CREATE DEPLOYMENT CONFIGURATION${NC}"

cat > "$KEY_DIR/deployment-config.sh" <<'EOF'
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
EOF

chmod +x "$KEY_DIR/deployment-config.sh"

echo -e "\n${YELLOW}4. CREATE DOCKER DEPLOYMENT SCRIPT${NC}"

cat > "$KEY_DIR/secure-deploy.sh" <<'EOF'
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
EOF

chmod +x "$KEY_DIR/secure-deploy.sh"

echo -e "\n${GREEN}Setup complete!${NC}"
echo ""
echo "Generated files:"
echo "  - $KEY_DIR/master-private.asc (KEEP SECURE - Master private key)"
echo "  - $KEY_DIR/master-public.asc (Share with instances)"
echo "  - $KEY_DIR/deployment-config.sh (Helper functions)"
echo "  - $KEY_DIR/secure-deploy.sh (Deployment script)"
echo ""
echo -e "${YELLOW}Security recommendations:${NC}"
echo "  1. NEVER commit private keys to Git"
echo "  2. Add keys/ to .gitignore"
echo "  3. Use GitHub Secrets for MASTER_URL"
echo "  4. Distribute master-public.asc securely to instances"
echo "  5. Each instance should have its own PGP key pair"
echo ""
echo -e "${YELLOW}For GitHub deployment:${NC}"
echo "  1. Add master-public.asc to your repository (safe to share)"
echo "  2. Set MASTER_URL as a GitHub Secret"
echo "  3. Use secure-deploy.sh in your CI/CD pipeline"