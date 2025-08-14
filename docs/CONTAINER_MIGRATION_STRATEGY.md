# Container Migration & Auto-Update Strategy

## Overview
This document outlines how to handle container migrations, renames, and auto-updates across the distributed orchestrator fleet.

## Auto-Update Architecture

### Current Setup (Limited)
- Only `orchestrator` container auto-updates
- Other containers are built locally or use static images

### Enhanced Setup (Recommended)
All critical containers should auto-update:

| Container | Current Image | Auto-Update Image | Update Trigger |
|-----------|--------------|-------------------|----------------|
| orchestrator | `ghcr.io/its-define/autonomy-orchestrator:autonomy-latest` | ✅ Already configured | Code changes in orchestrator/ |
| neurosync_s1 | Built locally | `ghcr.io/its-define/neurosync-s1:latest` | Changes in AVATAR/ |
| autogen_agent | `autogen_agent_with_neo4j:latest` (local) | `ghcr.io/its-define/autogen-agent:latest` | Changes in CORE/ |
| vtuber-ollama | `ollama/ollama:latest` | ✅ Can auto-update | Ollama releases |
| model_updater | New service | `alpine:latest` | Periodic model pulls |

## Container Migration Strategies

### Strategy 1: Blue-Green Deployment
```yaml
services:
  # Old container (to be removed)
  old_orchestrator:
    image: old-image:latest
    container_name: old_orchestrator
    labels:
      - "com.centurylinklabs.watchtower.enable=false"  # Disable updates
  
  # New container (replacement)
  new_orchestrator:
    image: ghcr.io/its-define/new-orchestrator:latest
    container_name: new_orchestrator
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
```

### Strategy 2: Alias-Based Migration
```yaml
services:
  # Use environment variables for container names
  orchestrator:
    image: ${ORCHESTRATOR_IMAGE:-ghcr.io/its-define/autonomy-orchestrator:autonomy-latest}
    container_name: ${ORCHESTRATOR_NAME:-vtuber_orchestrator}
```

### Strategy 3: Version-Tagged Deployment
```yaml
services:
  orchestrator_v2:
    image: ghcr.io/its-define/orchestrator:v2-latest
    container_name: orchestrator_v2
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
      - "com.centurylinklabs.watchtower.scope=v2-cluster"
```

## Implementation Steps

### 1. Enable Auto-Update for All Services

```bash
# Update docker-compose.yml to use GHCR images
cd /home/geo/operation/autonomy
cp docker-compose.autoupdate.yml docker-compose.yml

# Restart with new configuration
docker compose down
docker compose up -d
```

### 2. Set Up CI/CD Pipelines

The GitHub workflow (`autonomy-services-autoupdate.yml`) will:
- Build and push `neurosync-s1` on changes to AVATAR/
- Build and push `autogen-agent` on changes to CORE/
- Build and push `orchestrator` on changes to orchestrator/

### 3. Model Management

For Ollama models, use the `model_updater` service:
```yaml
environment:
  - OLLAMA_MODELS=llama3.2:3b,mistral,codellama
  - UPDATE_INTERVAL=86400  # Daily updates
```

## Handling Complete Container Revamps

### Scenario: Replacing All Container Names

1. **Create Migration Compose File**:
```yaml
# docker-compose.migration.yml
version: '3.8'
services:
  # New naming scheme
  avatar_controller:  # was: neurosync_s1
    image: ghcr.io/its-define/avatar-controller:latest
    # ... rest of config
  
  agent_coordinator:  # was: autogen_agent
    image: ghcr.io/its-define/agent-coordinator:latest
    # ... rest of config
```

2. **Gradual Migration**:
```bash
# Step 1: Run both old and new containers
docker compose -f docker-compose.yml -f docker-compose.migration.yml up -d

# Step 2: Test new containers
curl http://localhost:new-ports/health

# Step 3: Stop old containers
docker compose stop neurosync_s1 autogen_agent

# Step 4: Remove old containers
docker compose rm -f neurosync_s1 autogen_agent
```

3. **Update Watchtower Scope**:
```yaml
labels:
  - "com.centurylinklabs.watchtower.scope=v2-autonomy"
```

## Distributed Fleet Updates

### Central Control via Management API
```python
# Update all orchestrators in the fleet
import requests

fleet_endpoints = [
    "http://orchestrator1.example.com:8010",
    "http://orchestrator2.example.com:8010",
    # ...
]

for endpoint in fleet_endpoints:
    # Trigger update
    response = requests.post(
        f"{endpoint}/api/v1/management/orchestrator/update/command",
        json={
            "action": "trigger",
            "target_version": "v2-latest",
            "migration_config": {
                "rename_containers": True,
                "preserve_data": True,
                "rollback_on_failure": True
            }
        }
    )
```

### Rollback Strategy
```bash
# If migration fails, rollback to previous version
docker compose down
git checkout previous-version
docker compose up -d

# Or use Watchtower rollback
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --run-once \
  --label-enable \
  --scope autonomy-cluster \
  --rollback
```

## Best Practices

1. **Always Version Tag Images**: Use both `latest` and SHA tags
2. **Test in Staging**: Deploy to staging environment first
3. **Gradual Rollout**: Update one orchestrator at a time
4. **Monitor Health**: Check health endpoints after updates
5. **Maintain Backwards Compatibility**: Ensure new containers work with old ones
6. **Document Changes**: Keep CHANGELOG updated
7. **Backup Data**: Always backup volumes before major migrations

## Monitoring Updates

```bash
# Watch all auto-updates
docker logs -f watchtower_orchestrator

# Check container versions
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"

# Verify health
for port in 5001 8200 8082; do
  curl -s http://localhost:$port/health | jq .
done
```

## Emergency Procedures

### Stop All Updates
```bash
docker stop watchtower_orchestrator
```

### Force Rollback
```bash
# Pull previous versions
docker pull ghcr.io/its-define/orchestrator:autonomy-<previous-sha>
docker pull ghcr.io/its-define/neurosync-s1:<previous-sha>
docker pull ghcr.io/its-define/autogen-agent:<previous-sha>

# Retag as latest
docker tag ghcr.io/its-define/orchestrator:autonomy-<previous-sha> \
           ghcr.io/its-define/orchestrator:autonomy-latest

# Restart services
docker compose restart
```

## Conclusion

With this strategy:
- All critical containers can auto-update
- Container renames are handled gracefully
- The fleet can be centrally managed
- Rollbacks are always possible
- Model updates happen automatically

This ensures your autonomy system stays current while maintaining stability and control.