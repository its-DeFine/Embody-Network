# Dual-Mode Update System Documentation

## Overview

The Dual-Mode Update System provides intelligent, automated updates for orchestrator clusters by combining the best of both worlds:

1. **Watchtower** - Fast, zero-downtime image updates
2. **Full Revamp** - Complete cluster reconstruction for structural changes
3. **GitHub Integration** - Automated issue and PR workflow for both repositories

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Dual-Mode Update System               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐       ┌──────────────┐               │
│  │   Detector  │──────>│   Decision   │               │
│  │             │       │    Engine    │               │
│  └─────────────┘       └──────┬───────┘               │
│                               │                        │
│                    ┌──────────┴──────────┐            │
│                    │                      │            │
│         ┌──────────▼──────┐    ┌─────────▼────────┐  │
│         │   Image-Only    │    │    Structural    │  │
│         │   (Watchtower)  │    │   (Full Revamp)  │  │
│         └─────────────────┘    └──────────────────┘  │
│                                                        │
│  ┌────────────────────────────────────────────────┐  │
│  │            GitHub Integration                   │  │
│  │  - Create Issues (agent-net & Unreal_Vtuber)  │  │
│  │  - Generate PRs                                │  │
│  │  - Track Changes                               │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Update Detector (`scripts/dual_update_manager.py`)

The core intelligence that analyzes changes and determines update strategy:

- **Image-Only Changes**: New container versions, rebuilt images
- **Structural Changes**: New services, removed services, config changes
- **Mixed Changes**: Both image and structural updates

### 2. GitHub Integration

Automated workflow management:

- **Issue Creation**: Documents detected changes
- **PR Generation**: Creates review-ready pull requests
- **Dual-Repo Support**: Handles both main and submodule repositories

### 3. Update Orchestrator

Executes the appropriate update strategy:

- **Watchtower Mode**: Triggers immediate image updates
- **Full Revamp Mode**: Stops, updates, and recreates entire cluster
- **Health Checks**: Validates services after updates
- **Rollback**: Automatic recovery on failure

## Installation

### Step 1: Deploy the Update Orchestrator

```bash
cd /home/geo/operation/autonomy/update-orchestrator
docker compose up -d
```

### Step 2: Configure GitHub Workflow

The workflow is already configured in `.github/workflows/dual-update-system.yml`

Enable it in your repository's Actions tab.

### Step 3: Set Environment Variables

Create `.env` file in `autonomy/update-orchestrator/`:

```env
# Update Configuration
UPDATE_MODE=dual              # dual, watchtower_only, revamp_only
CHECK_INTERVAL=3600           # Check every hour
AUTO_APPROVE=false            # Require manual approval

# GitHub Integration
GITHUB_TOKEN=ghp_xxxxxxxxxxxx # Personal access token
WEBHOOK_URL=https://hooks.slack.com/... # Optional notifications

# Logging
LOG_LEVEL=INFO
```

## Usage

### Manual Update Check

```bash
# Check for updates without applying
python scripts/dual_update_manager.py --check-only

# Apply updates with approval prompt
python scripts/dual_update_manager.py

# Auto-approve and apply updates
python scripts/dual_update_manager.py --auto
```

### Monitor Dashboard

Access the web dashboard at: http://localhost:8090

### GitHub Workflow

Trigger manually from Actions tab or wait for scheduled run.

## Update Decision Matrix

| Change Type | Detection | Action | GitHub |
|------------|-----------|---------|---------|
| Image tag only | Image version changed | Watchtower | Issue only |
| New service | Service added to compose | Full revamp | Issue + PR |
| Remove service | Service removed from compose | Full revamp | Issue + PR |
| Port change | Port mapping modified | Full revamp | Issue + PR |
| Volume change | Volume mapping modified | Full revamp | Issue + PR |
| Env change | Environment variables changed | Full revamp | Issue + PR |
| Code change | Python/JS files modified | Image rebuild + Watchtower | Issue + PR (submodule) |

## Workflow Examples

### Example 1: Image-Only Update

1. Developer pushes code changes to `orchestrator/`
2. GitHub Actions builds new image
3. Detector identifies image-only change
4. Watchtower automatically pulls and updates
5. Issue closed as completed

### Example 2: Structural Update

1. Developer modifies `docker-compose.yml`
2. Detector identifies structural change
3. System creates GitHub issue
4. System creates PR with changes
5. After approval, full revamp executes
6. Health checks validate deployment
7. Issue and PR marked as completed

### Example 3: Dual-Repository Update

1. Changes detected in both main repo and submodule
2. Issues created in both repositories
3. PRs created for each repository
4. Coordinated update after both PRs approved
5. Full system validation

## Health Checks

Critical services monitored after updates:

- **Orchestrator**: http://localhost:8082/health
- **NeuroSync S1**: http://localhost:5001/health
- **AutoGen Agent**: http://localhost:8200/health
- **Ollama**: http://localhost:11434/api/tags

## Rollback Procedure

Automatic rollback triggers on:

- Health check failures
- Service startup failures
- Network connectivity issues

Manual rollback:

```bash
# Restore from backup
cd /home/geo/operation/backups/latest/autonomy
docker compose down
docker compose up -d

# Or use git to revert
git checkout previous-version
cd autonomy
docker compose down
docker compose up -d
```

## Monitoring

### Logs

```bash
# Update orchestrator logs
docker logs -f update_orchestrator

# Watchtower logs
docker logs -f watchtower_orchestrator

# System logs
journalctl -u orchestrator-update.service -f
```

### Metrics

The dashboard provides real-time metrics:

- Update frequency
- Success/failure rates
- Average update duration
- Service health status

## Security Considerations

1. **GitHub Token**: Use fine-grained personal access tokens
2. **Docker Socket**: Update orchestrator requires Docker access
3. **SSH Keys**: Needed for private repository access
4. **Webhooks**: Use HTTPS and validate signatures

## Troubleshooting

### Updates Not Detected

```bash
# Check git fetch
cd /home/geo/operation
git fetch origin
git status

# Check submodule
git submodule status
git submodule update --remote
```

### Watchtower Not Updating

```bash
# Check Watchtower status
docker ps | grep watchtower

# Check labels
docker inspect vtuber_orchestrator | grep -A 2 Labels

# Trigger manual update
docker exec watchtower_orchestrator sh -c 'kill -USR1 1'
```

### Full Revamp Fails

```bash
# Check docker-compose syntax
cd autonomy
docker compose config

# Validate services
docker compose ps

# Check logs
docker compose logs
```

### GitHub Integration Issues

```bash
# Test GitHub CLI
gh auth status

# Test issue creation
gh issue create --repo its-DeFine/agent-net --title "Test" --body "Test"

# Check workflow runs
gh run list --workflow=dual-update-system.yml
```

## Best Practices

1. **Test in Staging**: Always test updates in staging environment first
2. **Monitor Health**: Set up alerts for health check failures
3. **Regular Backups**: Ensure backup directory has sufficient space
4. **Review PRs**: Even with auto-update, review structural changes
5. **Gradual Rollout**: Update one cluster at a time in production
6. **Document Changes**: Keep CHANGELOG updated
7. **Version Tags**: Use semantic versioning for images

## Advanced Configuration

### Custom Update Strategies

Edit `scripts/dual_update_manager.py` to add custom logic:

```python
class CustomUpdateStrategy:
    def should_update(self, changes):
        # Custom logic here
        return True
    
    def execute(self):
        # Custom update process
        pass
```

### Multiple Cluster Management

```yaml
# multi-cluster.yml
clusters:
  - name: production-us
    url: https://us.example.com
    auto_approve: false
    
  - name: production-eu
    url: https://eu.example.com
    auto_approve: false
    
  - name: staging
    url: https://staging.example.com
    auto_approve: true
```

### Notification Integrations

```python
# Add to dual_update_manager.py
def notify_slack(message):
    requests.post(webhook_url, json={"text": message})

def notify_email(subject, body):
    # Email notification logic
    pass
```

## API Reference

### REST Endpoints (Future Enhancement)

```
GET  /api/status          - Current update status
GET  /api/history         - Update history
POST /api/check           - Trigger update check
POST /api/apply           - Apply pending updates
POST /api/rollback        - Rollback to previous version
GET  /api/health          - System health status
```

## Conclusion

The Dual-Mode Update System provides a robust, intelligent solution for managing orchestrator cluster updates. By combining Watchtower's efficiency with full revamp capabilities and GitHub integration, it ensures your clusters stay current while maintaining stability and traceability.