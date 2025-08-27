# Force Rebuild on VTuber Update Feature

*Created: 2025-08-27*

## Overview

This feature ensures that whenever the Unreal VTuber repository receives updates (commits or PRs to the main branch), the entire cluster is rebuilt from scratch to maintain consistency and prevent cache-related issues.

## Configuration

### Environment Variable

Set the following environment variable to enable forced rebuilds:

```bash
export FORCE_REBUILD_ON_VTUBER_UPDATE=true
```

This can be set in:
- `.env` file in the project root
- Docker Compose environment section
- System environment variables

### Default Behavior

By default, this feature is **ENABLED** (`true`) in:
- `/autonomy/update-manager/docker-compose.yml`
- `/autonomy/update-orchestrator/docker-compose.yml`

To disable, explicitly set:
```bash
export FORCE_REBUILD_ON_VTUBER_UPDATE=false
```

## How It Works

### 1. Detection Phase
The update manager monitors for changes in:
- The `docker-vtuber` submodule
- Any files containing "vtuber" in the path
- Commits to the Unreal VTuber repository

### 2. Force Rebuild Trigger
When VTuber updates are detected AND `FORCE_REBUILD_ON_VTUBER_UPDATE=true`:
- Update type is forced to `STRUCTURAL`
- Full cluster rebuild is initiated
- Docker build uses `--no-cache` flag
- Old images are removed before rebuild

### 3. Rebuild Process
```bash
# Stop all containers
docker-compose down

# Remove old images and volumes
docker-compose down --rmi local -v

# Pull latest changes
git pull origin main
git submodule update --init --recursive

# Build from scratch (no cache)
docker-compose build --no-cache

# Start new containers
docker-compose up -d
```

### 4. Health Checks
After rebuild, the system verifies:
- Orchestrator health at port 8082
- NeuroSync S1 health at port 5001
- AutoGen Agent health at port 8200

## Command Line Usage

### Manual Trigger
```bash
# Force rebuild manually
python scripts/dual_update_manager.py \
  --repo-path /home/geo/operation \
  --force-rebuild-on-vtuber-update
```

### Check Mode
```bash
# Check what would be rebuilt
python scripts/dual_update_manager.py \
  --repo-path /home/geo/operation \
  --force-rebuild-on-vtuber-update \
  --check-only
```

## Benefits

1. **Consistency**: Ensures production matches exact build specifications
2. **Security**: Fresh builds include latest security patches
3. **Reliability**: Eliminates stale cache issues
4. **Compliance**: Provides validated, reproducible builds

## Trade-offs

1. **Build Time**: Increases from ~30s to 5-10 minutes
2. **Downtime**: Brief service interruption during rebuild
3. **Resource Usage**: Higher CPU/network usage during builds
4. **Bandwidth**: Downloads all base images fresh

## Monitoring

Check rebuild status in logs:
```bash
# View update manager logs
docker logs update_manager

# View orchestrator logs
docker logs update_orchestrator

# Check last update time
cat /state/last_check.json
```

## Rollback

If a rebuild fails, the system automatically:
1. Restores backup configuration
2. Rebuilds using previous version
3. Sends failure notification

Manual rollback:
```bash
# Restore from backup
cp backups/[timestamp]/* autonomy/
docker-compose up -d
```

## Related Documentation

- [Dual Update System](/docs/DUAL_UPDATE_SYSTEM.md)
- [Full Cluster Update Guide](/docs/FULL_CLUSTER_UPDATE_GUIDE.md)
- [Update Manager Configuration](/autonomy/update-manager/update_config.yaml)

## GitHub Integration

This feature integrates with GitHub to:
- Create issues documenting VTuber updates
- Generate PRs for review
- Track rebuild history

Example issue created:
```
Title: [Auto-Update] Structural Changes Detected
Labels: enhancement
Body: VTuber updates detected - forcing full cluster rebuild
```

## Troubleshooting

### Rebuild Not Triggering
1. Check environment variable: `echo $FORCE_REBUILD_ON_VTUBER_UPDATE`
2. Verify submodule status: `git submodule status`
3. Check logs: `docker logs update_orchestrator`

### Build Failures
1. Check disk space: `df -h`
2. Verify Docker daemon: `docker info`
3. Check network connectivity: `docker pull hello-world`

### Performance Issues
1. Increase Docker memory allocation
2. Use parallel builds: `docker-compose build --parallel`
3. Consider build cache strategies for non-VTuber services