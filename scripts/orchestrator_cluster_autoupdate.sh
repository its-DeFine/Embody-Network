#!/usr/bin/env bash
set -euo pipefail

# Simple installer for an auto-updating orchestrator cluster using Watchtower
# Requirements: docker (and docker compose plugin), optional: GHCR login if image is private

GHCR_OWNER="${GHCR_OWNER:-CHANGE_ME}"
WATCH_INTERVAL_SECONDS="${WATCH_INTERVAL_SECONDS:-60}"
TARGET_DIR="${TARGET_DIR:-/opt/orchestrator-cluster}"

echo "[info] Preparing orchestrator cluster at ${TARGET_DIR}"
mkdir -p "${TARGET_DIR}/config" "${TARGET_DIR}/logs/orchestrator"

COMPOSE_FILE="${TARGET_DIR}/docker-compose.orchestrator-cluster.yml"

cat > "${COMPOSE_FILE}" << 'YAML'
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
      --interval ${WATCH_INTERVAL_SECONDS}
      --cleanup
      --scope orchestrator-cluster
      --rolling-restart
YAML

echo "[info] Compose file written to ${COMPOSE_FILE}"

echo "[hint] If the image is private, run: docker login ghcr.io"

echo "[info] Bringing up the cluster..."
docker compose -f "${COMPOSE_FILE}" up -d

echo "[done] Orchestrator cluster is up and will auto-update when a new image is pushed to GHCR"




