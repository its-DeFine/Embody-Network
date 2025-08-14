# Orchestrator Auto-Update Activation & Testing Guide

## Prerequisites
- Docker and Docker Compose installed
- GitHub Container Registry (GHCR) access configured
- Central Manager running (optional, for API control)

## Step 1: Activate Auto-Updates

### 1.1 Start the System with Watchtower
```bash
cd /home/geo/operation/autonomy

# Start all services including Watchtower
docker compose up -d

# Verify Watchtower is running
docker ps | grep watchtower_orchestrator
```

### 1.2 Verify Watchtower Configuration
```bash
# Check Watchtower logs
docker logs watchtower_orchestrator

# You should see:
# - "Watchtower started"
# - "Found X containers to monitor"
# - "Monitoring vtuber_orchestrator"
```

### 1.3 Verify Orchestrator Labels
```bash
# Check that orchestrator has the correct labels
docker inspect vtuber_orchestrator | grep -A 2 "Labels"

# Should show:
# "com.centurylinklabs.watchtower.enable": "true"
# "com.centurylinklabs.watchtower.scope": "autonomy-cluster"
```

## Step 2: Test Auto-Update Locally

### 2.1 Monitor-Only Mode Test (Safe)
```bash
# Set Watchtower to monitor-only mode (no actual updates)
export WATCHTOWER_MONITOR_ONLY=true
export WATCHTOWER_INTERVAL=60  # Check every minute for testing

# Restart Watchtower with monitor-only
docker compose up -d watchtower

# Watch the logs
docker logs -f watchtower_orchestrator
```

### 2.2 Simulate an Update
```bash
# Tag current orchestrator image with a new version
docker tag ghcr.io/its-define/autonomy-orchestrator:autonomy-latest \
          ghcr.io/its-define/autonomy-orchestrator:autonomy-test

# Update the orchestrator to use test tag
docker compose stop orchestrator
docker compose rm -f orchestrator

# Edit docker-compose.yml temporarily to use :autonomy-test tag
# Then start it again
docker compose up -d orchestrator

# Now push the "new" version back as latest
docker tag ghcr.io/its-define/autonomy-orchestrator:autonomy-test \
          ghcr.io/its-define/autonomy-orchestrator:autonomy-latest
docker push ghcr.io/its-define/autonomy-orchestrator:autonomy-latest

# Watch Watchtower detect and update (if not in monitor-only mode)
docker logs -f watchtower_orchestrator
```

### 2.3 Test with Actual Updates
```bash
# Disable monitor-only mode
export WATCHTOWER_MONITOR_ONLY=false
export WATCHTOWER_INTERVAL=60  # Fast interval for testing

# Restart Watchtower
docker compose up -d watchtower

# Make a small change to orchestrator code
cd /home/geo/operation/autonomy/orchestrator/src
echo "# Test update $(date)" >> main.py

# Build and push new image manually (simulating CI/CD)
cd /home/geo/operation/autonomy/orchestrator
docker build -t ghcr.io/its-define/autonomy-orchestrator:autonomy-latest .
docker push ghcr.io/its-define/autonomy-orchestrator:autonomy-latest

# Watch Watchtower detect and apply the update
docker logs -f watchtower_orchestrator

# Verify orchestrator was updated
docker ps | grep vtuber_orchestrator
docker logs vtuber_orchestrator | tail -20
```

## Step 3: Test Central Manager Control

### 3.1 Start Central Manager
```bash
cd /home/geo/operation
docker compose -f docker-compose.manager.yml up -d
```

### 3.2 Get Update Status
```bash
# Get current auto-update configuration
curl -X GET http://localhost:8010/api/v1/management/orchestrator/update/status \
  -H "Content-Type: application/json"
```

### 3.3 Configure Update Settings
```bash
# Configure update interval and settings
curl -X POST http://localhost:8010/api/v1/management/orchestrator/update/configure \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "interval_seconds": 300,
    "monitor_only": false,
    "rolling_restart": true,
    "cleanup_old_images": true
  }'
```

### 3.4 Test Update Commands
```bash
# Pause auto-updates
curl -X POST http://localhost:8010/api/v1/management/orchestrator/update/command \
  -H "Content-Type: application/json" \
  -d '{"action": "pause", "reason": "Testing pause functionality"}'

# Check status shows paused
curl -X GET http://localhost:8010/api/v1/management/orchestrator/update/status

# Resume auto-updates
curl -X POST http://localhost:8010/api/v1/management/orchestrator/update/command \
  -H "Content-Type: application/json" \
  -d '{"action": "resume"}'

# Trigger immediate update check
curl -X POST http://localhost:8010/api/v1/management/orchestrator/update/command \
  -H "Content-Type: application/json" \
  -d '{"action": "trigger", "reason": "Manual update test"}'
```

### 3.5 Test Rollback
```bash
# Get available versions
curl -X GET http://localhost:8010/api/v1/management/orchestrator/versions

# Rollback to specific version
curl -X POST http://localhost:8010/api/v1/management/orchestrator/update/command \
  -H "Content-Type: application/json" \
  -d '{
    "action": "rollback",
    "target_version": "autonomy-abc123",
    "reason": "Testing rollback"
  }'
```

## Step 4: Run Automated Tests

```bash
cd /home/geo/operation

# Run the auto-update test suite
pytest tests/test_orchestrator_autoupdate.py -v

# Run specific test categories
pytest tests/test_orchestrator_autoupdate.py::TestOrchestratorAutoUpdate -v
pytest tests/test_orchestrator_autoupdate.py::TestCentralManagerIntegration -v
pytest tests/test_orchestrator_autoupdate.py::TestDocumentation -v

# Run integration tests (requires Docker)
pytest tests/test_orchestrator_autoupdate.py -v -m integration
```

## Step 5: Production Deployment

### 5.1 Configure GHCR Access
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Ensure the image repository is public or accessible
# Go to: https://github.com/orgs/its-define/packages
# Find: autonomy-orchestrator package
# Set visibility to public or configure access tokens
```

### 5.2 Set Production Configuration
```bash
# Create production .env file
cat > /home/geo/operation/autonomy/.env << EOF
# Watchtower Configuration
WATCHTOWER_INTERVAL=300  # 5 minutes for production
WATCHTOWER_MONITOR_ONLY=false
WATCHTOWER_CLEANUP=true
WATCHTOWER_INCLUDE_STOPPED=false
WATCHTOWER_INCLUDE_RESTARTING=false

# GHCR Configuration
GHCR_OWNER=its-define
EOF

# Start with production settings
docker compose --env-file .env up -d
```

### 5.3 Monitor Production Updates
```bash
# Set up log monitoring
docker logs -f watchtower_orchestrator 2>&1 | tee watchtower.log

# Set up alerts (example using grep)
docker logs -f watchtower_orchestrator 2>&1 | \
  grep -E "(Updated|Failed|Error)" | \
  while read line; do
    echo "[$(date)] Alert: $line"
    # Add notification logic here (email, Slack, etc.)
  done
```

## Troubleshooting

### Issue: Watchtower not detecting updates
```bash
# Check if labels are correct
docker inspect vtuber_orchestrator | jq '.[] | .Config.Labels'

# Check Watchtower logs for errors
docker logs watchtower_orchestrator --tail 100

# Verify network connectivity to GHCR
docker pull ghcr.io/its-define/autonomy-orchestrator:autonomy-latest
```

### Issue: Updates failing
```bash
# Check orchestrator health after update
docker inspect vtuber_orchestrator | jq '.[] | .State.Health'

# Review rollback options
docker images | grep autonomy-orchestrator

# Manually rollback if needed
docker compose stop orchestrator
docker run -d --name vtuber_orchestrator \
  --network vtuber_network \
  ghcr.io/its-define/autonomy-orchestrator:autonomy-<previous-sha>
```

### Issue: Central Manager not controlling updates
```bash
# Check Redis connectivity
docker exec -it redis_scb redis-cli ping

# Verify API endpoints
curl http://localhost:8010/api/v1/management/orchestrator/update/status

# Check manager logs
docker logs central_manager --tail 100
```

## Verification Checklist

- [ ] Watchtower container is running
- [ ] Orchestrator has correct labels
- [ ] Watchtower shows orchestrator in monitoring list
- [ ] Monitor-only mode works (see logs, no actual updates)
- [ ] Manual update trigger works via API
- [ ] Pause/resume functionality works
- [ ] Update actually happens when new image is pushed
- [ ] Old images are cleaned up after update
- [ ] Health checks pass after update
- [ ] Rollback functionality works

## Security Considerations

1. **GHCR Access**: Ensure proper authentication for private images
2. **Update Windows**: Configure specific times for updates in production
3. **Rollback Plan**: Always maintain previous image versions
4. **Health Monitoring**: Set up alerts for failed updates
5. **Network Security**: Watchtower needs Docker socket access - ensure host security

## Next Steps

Once testing is complete:
1. Set production update interval (recommended: 300-600 seconds)
2. Configure monitoring and alerting
3. Document rollback procedures for your team
4. Set up update notifications (Slack, email, etc.)
5. Create update approval workflow if needed