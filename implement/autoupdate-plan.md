# Implementation Plan - Auto-Update for Autonomy Docker Compose Clusters
**Created: 2025-08-12 14:00**

## Problem Statement
The autonomy docker compose clusters need auto-update functionality when orchestrators are live and guided from the central manager. While CI/CD and documentation exist, the actual implementation is not active in production.

## Current State Analysis

### What Exists:
1. **CI/CD Pipeline** (.github/workflows/autonomy-orchestrator-autoupdate.yml)
   - Builds and pushes to GHCR on main branch changes
   - Tags: `autonomy-latest` (mutable) and `autonomy-<sha>` (immutable)

2. **Documentation** (docs/ORCHESTRATOR_AUTOUPDATE.md)
   - Complete Watchtower setup guide
   - Configuration examples

3. **Deployment Script** (scripts/orchestrator_cluster_autoupdate.sh)
   - Creates Watchtower-enabled clusters

### What's Missing:
1. **No Watchtower in autonomy/docker-compose.yml**
2. **No test coverage for auto-updates**
3. **No central manager integration for orchestrated updates**
4. **No production deployment active**

## Implementation Tasks

### Phase 1: Watchtower Integration
- [ ] Add Watchtower service to autonomy/docker-compose.yml
- [ ] Configure label-based filtering for orchestrator container
- [ ] Add environment variables for update intervals
- [ ] Ensure proper networking and dependencies

### Phase 2: Central Manager Integration
- [ ] Add update control endpoints to central manager
- [ ] Implement rollback capability via central manager
- [ ] Add update status monitoring
- [ ] Create update approval workflow

### Phase 3: Testing Infrastructure
- [ ] Create test fixtures for auto-update scenarios
- [ ] Write integration tests for Watchtower updates
- [ ] Add rollback testing
- [ ] Test central manager update commands

### Phase 4: Production Readiness
- [ ] Add health checks for update validation
- [ ] Configure update windows/schedules
- [ ] Add monitoring and alerting for failed updates
- [ ] Document operational procedures

## Implementation Details

### 1. Watchtower Service Configuration
```yaml
watchtower:
  image: containrrr/watchtower:latest
  container_name: watchtower_orchestrator
  restart: unless-stopped
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  environment:
    - WATCHTOWER_LABEL_ENABLE=true
    - WATCHTOWER_INTERVAL=${WATCHTOWER_INTERVAL:-300}
    - WATCHTOWER_CLEANUP=true
    - WATCHTOWER_ROLLING_RESTART=true
    - WATCHTOWER_INCLUDE_STOPPED=false
    - WATCHTOWER_INCLUDE_RESTARTING=false
  command: --label-enable --scope autonomy-cluster
  networks:
    - vtuber_network
```

### 2. Orchestrator Label Configuration
Add to orchestrator service:
```yaml
labels:
  - "com.centurylinklabs.watchtower.enable=true"
  - "com.centurylinklabs.watchtower.scope=autonomy-cluster"
```

### 3. Test Coverage Areas
- Watchtower container startup and configuration
- Image pull and update triggers
- Rolling restart behavior
- Health check validation post-update
- Rollback procedures
- Central manager commands

## Validation Checklist
- [ ] Watchtower successfully monitors orchestrator
- [ ] Updates trigger on new image push
- [ ] Rolling restart maintains availability
- [ ] Health checks pass after updates
- [ ] Central manager can control updates
- [ ] Tests provide adequate coverage
- [ ] Documentation is complete
- [ ] No breaking changes to existing functionality

## Risk Mitigation
- **Potential Issues**:
  - Updates during active operations
  - Network interruptions during pull
  - Incompatible image updates
  - Container state loss

- **Rollback Strategy**:
  - Git commit checkpoints before changes
  - Immutable image tags for quick rollback
  - Central manager rollback command
  - Manual intervention procedures documented

## Files to Modify
1. `/home/geo/operation/autonomy/docker-compose.yml` - Add Watchtower service
2. `/home/geo/operation/app/api/management.py` - Add update control endpoints
3. `/home/geo/operation/tests/test_orchestrator_autoupdate.py` - New test file
4. `/home/geo/operation/docs/ORCHESTRATOR_AUTOUPDATE.md` - Update with production config

## Success Criteria
- Orchestrators auto-update when new images are pushed to GHCR
- Central manager can control and monitor update process
- Full test coverage for update scenarios
- Zero downtime during updates
- Easy rollback capability