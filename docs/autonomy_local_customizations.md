# Local Customizations in Autonomy Directory

## Important Files to Preserve

### Configuration Files
- `.env` - Local environment configuration
- `.env.autonomy.dev` - Development environment settings
- `api_registry.yaml` - API registry configuration
- `Dockerfile.mock` - Mock service Dockerfile
- `Dockerfile.v2` - Version 2 Dockerfile

### Docker Compose Changes
- Modified orchestrator service to use `localhost:5555/vtuber-orchestrator:latest` image instead of building from source
- Added Watchtower service for auto-updates with labels
- Added labels to orchestrator for Watchtower monitoring
- Changed volume mount from `./orchestrator/config` to `./api_registry.yaml:/config/api_registry.yaml:ro`

### Monitoring Configuration
- `nginx.conf` - Nginx configuration
- `prometheus-config.yml` - Prometheus monitoring configuration

### Test Results and Logs
- `qa_test_output.log` - QA test results
- `speech_timing_output.log` - Speech timing test results
- Various log directories and test outputs

## Files to Keep from Backup
All the files listed above should be restored after setting up the submodule.