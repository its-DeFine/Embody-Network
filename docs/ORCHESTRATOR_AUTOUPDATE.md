### Orchestrator Cluster Auto-Update (from autonomy main branch)

This enables every orchestrator cluster to auto-update when changes land in `main` under `autonomy/orchestrator/**`.

High-level flow:
- CI builds and pushes `ghcr.io/<owner>/autonomy-orchestrator:autonomy-latest` on changes to orchestrator code.
- Each cluster runs Watchtower with label filtering and pulls the new tag automatically, performing a rolling restart.

#### 1) CI: Publish orchestrator image to GHCR
Already added: `.github/workflows/autonomy-orchestrator-autoupdate.yml` builds/pushes on `main` changes.

The image is tagged:
- `autonomy-latest` (mutable tag used by clusters)
- `autonomy-<gitsha>` (immutable for traceability)

Make the GHCR package public or ensure clusters can `docker login ghcr.io` with a token that has `read:packages`.

#### 2) Cluster compose with Watchtower
Use this compose on each orchestrator cluster host (customer/edge):

```yaml
version: '3.8'
services:
  vtuber_orchestrator:
    image: ghcr.io/${GHCR_OWNER}/autonomy-orchestrator:autonomy-latest
    container_name: vtuber_orchestrator
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=INFO
      - OLLAMA_HOST=http://vtuber-ollama:11434
      - API_REGISTRY_PATH=/config/api_registry.yaml
    ports:
      - "8082:8080"
    volumes:
      - ./config:/config:ro
      - ./logs/orchestrator:/logs
    labels:
      - "com.centurylinklabs.watchtower.enable=true"

  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower_orchestrator
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: >
      --label-enable
      --interval 60
      --cleanup
      --scope orchestrator-cluster
      --rolling-restart
```

Then run:

```bash
export GHCR_OWNER=<github org or user>
docker login ghcr.io -u <user> -p <PAT_with_read_packages>
docker compose -f docker/production/docker-compose.orchestrator-cluster.yml up -d
```

Optional environment:
- `WATCH_INTERVAL_SECONDS` to tune poll interval (default 60s)
- `WATCHTOWER_DEBUG=true` for verbose logs

#### 3) Security and rollbacks
- Prefer making the GHCR package public for simple pull.
- For rollbacks, retag to a previous immutable digest: `docker pull ghcr.io/<owner>/autonomy-orchestrator@sha256:<digest>` and restart.

#### 4) Observability
- Watchtower logs show update activity: `docker logs -f watchtower_orchestrator`.
- Orchestrator exposes `/health` on 8080; use any external monitor to gate rolling restarts.





