#!/bin/bash
# Security scanning script

set -e

echo "🔒 Running security scans..."

# Check for hardcoded secrets
echo "🔍 Scanning for hardcoded secrets..."
if command -v gitleaks &> /dev/null; then
    gitleaks detect --source . --verbose
else
    echo "⚠️  gitleaks not installed. Using basic secret detection..."
    # Basic pattern matching for common secrets
    grep -r -E "(password|secret|api_key|token)\s*=\s*[\"'][^\"']+[\"']" . \
        --exclude-dir=node_modules \
        --exclude-dir=.git \
        --exclude-dir=__pycache__ \
        --exclude="*.pyc" \
        --exclude=".env*" || true
fi

# Python dependency security check
echo "🐍 Checking Python dependencies for vulnerabilities..."
if command -v safety &> /dev/null; then
    find . -name "requirements.txt" -type f | while read -r req_file; do
        echo "Checking $req_file..."
        safety check -r "$req_file" || true
    done
else
    echo "⚠️  safety not installed. Installing..."
    pip install safety
    find . -name "requirements.txt" -type f | while read -r req_file; do
        echo "Checking $req_file..."
        safety check -r "$req_file" || true
    done
fi

# Bandit for Python security issues
echo "🚨 Running Bandit security linter..."
if command -v bandit &> /dev/null; then
    bandit -r . -f json -o security_report.json || true
    echo "Security report saved to security_report.json"
else
    echo "⚠️  bandit not installed. Installing..."
    pip install bandit
    bandit -r . -f json -o security_report.json || true
fi

# Check for exposed ports
echo "🌐 Checking for exposed ports in docker-compose..."
grep -r "ports:" docker-compose*.yml | grep -v "#" || true

# Check for default credentials
echo "🔑 Checking for default credentials..."
grep -r -i "default.*password\|admin.*password\|guest.*guest" . \
    --exclude-dir=node_modules \
    --exclude-dir=.git \
    --exclude="*.md" || true

# Docker image vulnerability scanning
echo "🐳 Checking Docker images for vulnerabilities..."
if command -v trivy &> /dev/null; then
    docker images --format "{{.Repository}}:{{.Tag}}" | grep -v "<none>" | while read -r image; do
        echo "Scanning $image..."
        trivy image "$image" --severity HIGH,CRITICAL --quiet || true
    done
else
    echo "⚠️  trivy not installed. Skipping Docker image scanning."
fi

echo "✅ Security scan complete! Review any findings above."