#!/bin/bash
# Full Orchestrator Cluster Update Script
# This handles complete docker-compose changes, not just image updates

set -e

# Configuration
REPO_URL="https://github.com/its-DeFine/agent-net.git"
BRANCH="embody-alpha"
UPDATE_DIR="/tmp/orchestrator-update-$$"
AUTONOMY_DIR="/home/geo/operation/autonomy"
BACKUP_DIR="/home/geo/operation/backups/$(date +%Y%m%d_%H%M%S)"
HEALTH_CHECK_TIMEOUT=60
ROLLBACK_ON_FAILURE=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Step 1: Check for updates
check_for_updates() {
    log "Checking for updates..."
    
    cd "$AUTONOMY_DIR"
    git fetch origin "$BRANCH"
    
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/"$BRANCH")
    
    if [ "$LOCAL" = "$REMOTE" ]; then
        log "No updates available"
        return 1
    else
        log "Updates available: $LOCAL -> $REMOTE"
        return 0
    fi
}

# Step 2: Pull latest changes
pull_updates() {
    log "Pulling latest changes..."
    
    # Clone fresh copy to temp directory
    rm -rf "$UPDATE_DIR"
    git clone --recurse-submodules "$REPO_URL" -b "$BRANCH" "$UPDATE_DIR"
    
    if [ $? -ne 0 ]; then
        error "Failed to clone repository"
        return 1
    fi
    
    # Preserve local configurations
    if [ -f "$AUTONOMY_DIR/.env" ]; then
        cp "$AUTONOMY_DIR/.env" "$UPDATE_DIR/autonomy/.env"
    fi
    
    if [ -f "$AUTONOMY_DIR/api_registry.yaml" ]; then
        cp "$AUTONOMY_DIR/api_registry.yaml" "$UPDATE_DIR/autonomy/api_registry.yaml"
    fi
    
    return 0
}

# Step 3: Backup current state
backup_current() {
    log "Backing up current configuration..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup docker-compose and configs
    cp -r "$AUTONOMY_DIR" "$BACKUP_DIR/"
    
    # Export running container list
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" > "$BACKUP_DIR/running_containers.txt"
    
    # Backup volumes (optional, can be large)
    # docker run --rm -v autonomy_ollama_data:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/ollama_data.tar.gz /data
    
    log "Backup created at: $BACKUP_DIR"
}

# Step 4: Health check function
health_check() {
    local service=$1
    local port=$2
    local endpoint=${3:-/health}
    local timeout=${4:-30}
    
    log "Checking health of $service on port $port..."
    
    for i in $(seq 1 $timeout); do
        if curl -s -f "http://localhost:$port$endpoint" > /dev/null 2>&1; then
            log "$service is healthy"
            return 0
        fi
        sleep 1
    done
    
    error "$service failed health check"
    return 1
}

# Step 5: Perform rolling update
rolling_update() {
    log "Starting rolling update..."
    
    cd "$UPDATE_DIR/autonomy"
    
    # Compare docker-compose files
    if diff -q "$AUTONOMY_DIR/docker-compose.yml" "$UPDATE_DIR/autonomy/docker-compose.yml" > /dev/null; then
        log "No docker-compose changes, using Watchtower for image updates only"
        docker exec watchtower_orchestrator sh -c 'kill -USR1 1'  # Trigger immediate update
        return 0
    fi
    
    log "Docker-compose changes detected, performing full update..."
    
    # Stop and remove old containers
    cd "$AUTONOMY_DIR"
    docker compose down --remove-orphans
    
    # Start new containers
    cd "$UPDATE_DIR/autonomy"
    docker compose up -d
    
    # Wait for services to be healthy
    sleep 10
    
    # Check critical services
    health_check "orchestrator" 8082 /health || return 1
    health_check "neurosync_s1" 5001 /health || return 1
    health_check "autogen_agent" 8200 /health || return 1
    
    log "All services healthy"
    return 0
}

# Step 6: Rollback function
rollback() {
    error "Update failed, rolling back..."
    
    if [ "$ROLLBACK_ON_FAILURE" = true ] && [ -d "$BACKUP_DIR" ]; then
        cd "$BACKUP_DIR/autonomy"
        docker compose down --remove-orphans
        docker compose up -d
        
        log "Rollback completed"
    else
        error "Rollback disabled or backup not found"
    fi
}

# Step 7: Cleanup
cleanup() {
    log "Cleaning up..."
    
    # Remove temp directory
    rm -rf "$UPDATE_DIR"
    
    # Remove old images
    docker image prune -f
    
    # Keep only last 5 backups
    ls -t "$AUTONOMY_DIR/../backups" | tail -n +6 | xargs -I {} rm -rf "$AUTONOMY_DIR/../backups/{}"
}

# Step 8: Update current directory
update_current_dir() {
    log "Updating current autonomy directory..."
    
    # Replace current with new
    rm -rf "$AUTONOMY_DIR.old"
    mv "$AUTONOMY_DIR" "$AUTONOMY_DIR.old"
    mv "$UPDATE_DIR/autonomy" "$AUTONOMY_DIR"
    
    log "Directory updated"
}

# Main execution
main() {
    log "=== Starting Full Orchestrator Update ==="
    
    # Check if running as part of automated system
    if [ "$1" = "--auto" ]; then
        log "Running in automated mode"
        ROLLBACK_ON_FAILURE=true
    fi
    
    # Check for updates
    if ! check_for_updates; then
        exit 0
    fi
    
    # Pull latest changes
    if ! pull_updates; then
        error "Failed to pull updates"
        exit 1
    fi
    
    # Backup current state
    backup_current
    
    # Perform update
    if rolling_update; then
        log "Update successful!"
        update_current_dir
        cleanup
        
        # Send notification (optional)
        # curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
        #   -H 'Content-Type: application/json' \
        #   -d '{"text":"Orchestrator cluster updated successfully"}'
        
        exit 0
    else
        error "Update failed!"
        rollback
        exit 1
    fi
}

# Run main function
main "$@"