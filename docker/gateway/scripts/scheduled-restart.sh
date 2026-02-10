#!/bin/bash
# =============================================================================
# IBKR Gateway Scheduled Restart
# =============================================================================
#
# Triggers a clean Gateway container restart.
# Schedule this to run at 4:30 PM ET daily (after market close).
#
# Windows (Task Scheduler via WSL):
#   wsl -d Ubuntu /path/to/scheduled-restart.sh
#
# Linux (cron):
#   30 16 * * 1-5 /path/to/scheduled-restart.sh
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(dirname "$SCRIPT_DIR")"
CONTAINER_NAME="ibkr-gateway"
LOG_FILE="${COMPOSE_DIR}/restart.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Load environment for Discord webhook (if configured)
if [ -f "${COMPOSE_DIR}/.env" ]; then
    source "${COMPOSE_DIR}/.env"
fi

log "Starting scheduled Gateway restart"

# Pre-restart: Log current memory usage
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    MEM_USAGE=$(docker stats --no-stream --format "{{.MemUsage}}" "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
    log "Pre-restart memory usage: $MEM_USAGE"
fi

# Restart container
cd "$COMPOSE_DIR"
log "Executing: docker compose restart gateway"
docker compose restart gateway

# Wait for container to be healthy
log "Waiting for container to become healthy..."
for i in {1..60}; do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "starting")
    if [ "$HEALTH" = "healthy" ]; then
        log "Container healthy after $i seconds"
        break
    fi
    sleep 2
done

# Final status
FINAL_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
if [ "$FINAL_HEALTH" = "healthy" ]; then
    log "SUCCESS: Gateway restarted and healthy"

    # Discord notification (if webhook configured)
    if [ -n "${DISCORD_WEBHOOK_URL:-}" ]; then
        curl -s -X POST "$DISCORD_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d '{"content": "🔄 IBKR Gateway restarted (scheduled 4:30 PM ET)"}' || true
    fi
else
    log "WARNING: Gateway restart completed but health status is '$FINAL_HEALTH'"

    if [ -n "${DISCORD_WEBHOOK_URL:-}" ]; then
        curl -s -X POST "$DISCORD_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"content\": \"⚠️ IBKR Gateway restart completed but health is $FINAL_HEALTH\"}" || true
    fi
fi

log "Scheduled restart complete"
