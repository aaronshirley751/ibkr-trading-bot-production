#!/bin/bash
# docker/bot/entrypoint.sh

set -e

echo "[$(date -Iseconds)] Trading bot container starting..."
echo "[$(date -Iseconds)] Gateway target: ${GATEWAY_HOST}:${GATEWAY_PORT}"
echo "[$(date -Iseconds)] Dry-run mode: ${DRY_RUN}"

# Validate required environment variables
required_vars=("GATEWAY_HOST" "GATEWAY_PORT")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "[$(date -Iseconds)] ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

# Optional: Log configuration summary
echo "[$(date -Iseconds)] Configuration:"
echo "  - GATEWAY_HOST: ${GATEWAY_HOST}"
echo "  - GATEWAY_PORT: ${GATEWAY_PORT}"
echo "  - GATEWAY_STARTUP_TIMEOUT: ${GATEWAY_STARTUP_TIMEOUT:-300}"
echo "  - GATEWAY_MAX_RETRIES: ${GATEWAY_MAX_RETRIES:-30}"
echo "  - GAMEPLAN_PATH: ${GAMEPLAN_PATH:-/data/gameplan.json}"
echo "  - DRY_RUN: ${DRY_RUN:-true}"
echo "  - LOG_LEVEL: ${LOG_LEVEL:-INFO}"

# Execute Python bot with all arguments passed through
exec python -m src.main
