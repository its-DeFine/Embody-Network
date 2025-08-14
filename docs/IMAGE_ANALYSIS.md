# Docker Image Analysis for Autonomy Stack

## Summary
- **Total Services**: 19 active containers
- **Locally Built Images**: 5 (need CI/CD pipeline)
- **Public Images**: 14 (auto-update ready)
- **Private/Custom Images**: 1 (already on GHCR)

## Image Categories

### 🔴 Locally Built Images (Need Upload to Registry)
These images are built from local Dockerfiles and won't auto-update without being pushed to a registry:

1. **neurosync_s1** (`autonomy-neurosync_s1:latest`)
   - Size: 10.9GB (very large!)
   - Built from: `docker-vtuber/app/AVATAR/NeuroBridge/dockerfile`
   - **Action Required**: Push to GHCR for auto-updates
   - **Priority**: HIGH - Core VTuber avatar system

2. **orchestrator** (`autonomy-orchestrator:latest`)
   - Size: 88.5MB
   - Built from: `./orchestrator/Dockerfile`
   - **Action Required**: Push to GHCR for auto-updates
   - **Priority**: HIGH - Main routing agent (Watchtower target)

3. **scb_gateway** (`autonomy-scb_gateway:latest`)
   - Size: 60.7MB
   - Built from: `./docker-vtuber/app/CORE/autogen-agent/scb_gateway`
   - **Action Required**: Push to GHCR for auto-updates
   - **Priority**: MEDIUM - SCB communication layer

4. **ollama_exporter** (`autonomy-ollama_exporter:latest`)
   - Size: 53.2MB
   - Built from: `./monitoring/exporters/Dockerfile.ollama`
   - **Action Required**: Push to GHCR for auto-updates
   - **Priority**: LOW - Monitoring only

5. **autogen_agent** (`autogen_agent_with_neo4j:latest`)
   - Size: 187MB
   - Uses pre-built image but named locally
   - **Action Required**: Push to GHCR or use official image
   - **Priority**: HIGH - Core multi-agent system

### 🟢 Public Images (Auto-Update Ready)
These images are from public registries and will auto-update if configured:

#### Infrastructure
- `ollama/ollama:latest` - LLM runtime
- `redis:7-alpine` - Cache/message broker (commented out)
- `ankane/pgvector:latest` - PostgreSQL with vector support
- `neo4j:5-community` - Graph database

#### Monitoring Stack
- `prom/prometheus:latest` - Metrics collection
- `grafana/grafana:latest` - Visualization
- `prom/node-exporter:latest` - System metrics
- `gcr.io/cadvisor/cadvisor:latest` - Container metrics
- `oliver006/redis_exporter:latest` - Redis metrics
- `prometheuscommunity/postgres-exporter:latest` - PostgreSQL metrics
- `nginx/nginx-prometheus-exporter:latest` - NGINX metrics

#### Utilities
- `containrrr/watchtower:latest` - Auto-updater
- `curlimages/curl:latest` - Ollama model loader
- `tiangolo/nginx-rtmp:latest` - RTMP streaming

### 🟡 Already on GHCR
- `ghcr.io/remsky/kokoro-fastapi-cpu:latest` - TTS service (third-party)

## Auto-Update Readiness

### ✅ Ready for Auto-Updates (14/19)
All public registry images can be auto-updated by Watchtower if labels are added.

### ❌ Not Ready for Auto-Updates (5/19)
Locally built images need to be pushed to a registry:
1. neurosync_s1 (10.9GB)
2. orchestrator (88.5MB) - **Most Critical**
3. scb_gateway (60.7MB)
4. ollama_exporter (53.2MB)
5. autogen_agent (187MB)

## Recommended Actions

### Immediate Priority
1. **Push orchestrator to GHCR** - This is your Watchtower target
   ```bash
   docker tag autonomy-orchestrator:latest ghcr.io/its-define/autonomy-orchestrator:latest
   docker push ghcr.io/its-define/autonomy-orchestrator:latest
   ```

2. **Update docker-compose.yml** for orchestrator:
   ```yaml
   orchestrator:
     image: ghcr.io/its-define/autonomy-orchestrator:latest
     # Remove the build: section
   ```

### Secondary Priority
3. **Set up CI/CD for other local builds**:
   - neurosync_s1 (consider size optimization first - 10.9GB is huge!)
   - autogen_agent
   - scb_gateway
   - ollama_exporter

### Optional Enhancements
4. **Add Watchtower labels to other services** for comprehensive updates:
   ```yaml
   labels:
     - "com.centurylinklabs.watchtower.enable=true"
   ```

5. **Consider using specific versions** instead of `:latest` for stability:
   - Pin versions in production
   - Use `:latest` only in development

## Storage Considerations
- **Total image size**: ~15GB
- **Largest image**: neurosync_s1 at 10.9GB (needs optimization!)
- **Registry storage needed**: ~11.3GB for local images

## Security Notes
- Ensure GHCR packages are properly scoped (public vs private)
- Use image signing for production deployments
- Implement vulnerability scanning in CI/CD pipeline
- Consider using digest-based image references for immutability