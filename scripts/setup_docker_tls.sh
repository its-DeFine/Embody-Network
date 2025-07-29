#!/bin/bash

# Setup Docker daemon with TLS for remote access
# Usage: ./setup_docker_tls.sh [hostname]

set -e

HOSTNAME=${1:-$(hostname)}
CERT_DIR="/etc/docker/certs"
CLIENT_CERT_DIR="./docker-certs/client"

echo "🔐 Setting up Docker TLS for remote access"
echo "=========================================="
echo "Hostname: $HOSTNAME"

# Create directories
sudo mkdir -p $CERT_DIR
mkdir -p $CLIENT_CERT_DIR

# Generate CA private key
echo "📝 Generating CA private key..."
openssl genrsa -aes256 -out ca-key.pem 4096

# Generate CA certificate
echo "📝 Generating CA certificate..."
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem \
    -subj "/C=US/ST=State/L=City/O=AutoGen Platform/CN=$HOSTNAME"

# Generate server private key
echo "📝 Generating server private key..."
openssl genrsa -out server-key.pem 4096

# Generate server certificate request
echo "📝 Generating server certificate request..."
openssl req -subj "/CN=$HOSTNAME" -sha256 -new -key server-key.pem -out server.csr

# Create extensions file for server certificate
cat > extfile.cnf <<EOF
subjectAltName = DNS:$HOSTNAME,DNS:localhost,IP:127.0.0.1,IP:$(hostname -I | awk '{print $1}')
extendedKeyUsage = serverAuth
EOF

# Generate server certificate
echo "📝 Generating server certificate..."
openssl x509 -req -days 365 -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem \
    -CAcreateserial -out server-cert.pem -extfile extfile.cnf

# Generate client private key
echo "📝 Generating client private key..."
openssl genrsa -out key.pem 4096

# Generate client certificate request
echo "📝 Generating client certificate request..."
openssl req -subj '/CN=client' -new -key key.pem -out client.csr

# Create extensions file for client certificate
echo extendedKeyUsage = clientAuth > extfile-client.cnf

# Generate client certificate
echo "📝 Generating client certificate..."
openssl x509 -req -days 365 -sha256 -in client.csr -CA ca.pem -CAkey ca-key.pem \
    -CAcreateserial -out cert.pem -extfile extfile-client.cnf

# Remove certificate requests and extension files
rm -f server.csr client.csr extfile.cnf extfile-client.cnf

# Set permissions
echo "🔒 Setting permissions..."
chmod 400 ca-key.pem key.pem server-key.pem
chmod 444 ca.pem server-cert.pem cert.pem

# Copy server certificates to Docker directory
echo "📁 Copying server certificates..."
sudo cp ca.pem server-cert.pem server-key.pem $CERT_DIR/

# Copy client certificates
echo "📁 Copying client certificates..."
cp ca.pem cert.pem key.pem $CLIENT_CERT_DIR/

# Create Docker daemon configuration
echo "⚙️  Creating Docker daemon configuration..."
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
    "tls": true,
    "tlsverify": true,
    "tlscacert": "$CERT_DIR/ca.pem",
    "tlscert": "$CERT_DIR/server-cert.pem",
    "tlskey": "$CERT_DIR/server-key.pem",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "default-ulimits": {
        "nofile": {
            "Name": "nofile",
            "Hard": 64000,
            "Soft": 64000
        }
    }
}
EOF

# Create systemd override for Docker
echo "⚙️  Creating systemd override..."
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
EOF

# Reload systemd and restart Docker
echo "🔄 Restarting Docker daemon..."
sudo systemctl daemon-reload
sudo systemctl restart docker

# Test connection
echo ""
echo "🧪 Testing TLS connection..."
docker --tlsverify \
    --tlscacert=$CLIENT_CERT_DIR/ca.pem \
    --tlscert=$CLIENT_CERT_DIR/cert.pem \
    --tlskey=$CLIENT_CERT_DIR/key.pem \
    -H tcp://$HOSTNAME:2376 version

echo ""
echo "✅ Docker TLS setup complete!"
echo ""
echo "📋 Client connection instructions:"
echo "1. Copy client certificates from: $CLIENT_CERT_DIR"
echo "2. Set environment variables:"
echo "   export DOCKER_TLS_VERIFY=1"
echo "   export DOCKER_HOST=tcp://$HOSTNAME:2376"
echo "   export DOCKER_CERT_PATH=/path/to/client/certs"
echo ""
echo "Or use Docker with flags:"
echo "   docker --tlsverify \\"
echo "          --tlscacert=$CLIENT_CERT_DIR/ca.pem \\"
echo "          --tlscert=$CLIENT_CERT_DIR/cert.pem \\"
echo "          --tlskey=$CLIENT_CERT_DIR/key.pem \\"
echo "          -H tcp://$HOSTNAME:2376 \\"
echo "          <command>"
echo ""
echo "🔥 Firewall: Remember to open port 2376 for remote access"