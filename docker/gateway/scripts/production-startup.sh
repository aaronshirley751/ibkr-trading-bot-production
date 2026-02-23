#!/bin/bash
# =============================================================================
# Production Startup Script
# =============================================================================
#
# Invokes the zero-touch orchestrator for production deployment.
# Use this as the target for systemd or Windows Task Scheduler.
#
# Linux (systemd):
#   ExecStart=/path/to/production-startup.sh
#
# Windows (Task Scheduler via WSL):
#   wsl -d Ubuntu /path/to/production-startup.sh
#
# Environment Variables (optional):
#   GATEWAY_HOST             - Gateway hostname (default: localhost)
#   GATEWAY_PORT             - Gateway API port (default: 4002)
#   GATEWAY_HEALTH_TIMEOUT   - Health check timeout (default: 120)
#   GAMEPLAN_PATH            - Path to daily gameplan JSON
#   DISCORD_WEBHOOK_URL      - Discord webhook for alerts
#   BOT_LOG_LEVEL            - Logging level (default: INFO)
#
# =============================================================================

set -euo pipefail

# Determine repository directory (3 levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LOG_DIR="${REPO_DIR}/logs"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="${LOG_DIR}/startup_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Log startup
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting production orchestrator" | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Repository: ${REPO_DIR}" | tee -a "$LOG_FILE"

# Change to repository directory
cd "$REPO_DIR"

# Load environment (if .env exists)
if [ -f ".env" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Loading .env file" | tee -a "$LOG_FILE"
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
fi

# Also try loading from docker/.env if it exists
if [ -f "docker/.env" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Loading docker/.env file" | tee -a "$LOG_FILE"
    set -a
    # shellcheck source=/dev/null
    source docker/.env
    set +a
fi

# Set Docker Compose directory if not already set
export DOCKER_COMPOSE_DIR="${DOCKER_COMPOSE_DIR:-${REPO_DIR}/docker}"

# Invoke orchestrator
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Invoking orchestrator" | tee -a "$LOG_FILE"

if command -v poetry &> /dev/null; then
    poetry run python -m src.orchestration.startup 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
else
    # Fall back to direct python if poetry not available
    python -m src.orchestration.startup 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
fi

# Log result
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Startup orchestration SUCCESS" | tee -a "$LOG_FILE"
elif [ $EXIT_CODE -eq 2 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Startup orchestration PARTIAL SUCCESS (Strategy C deployed)" | tee -a "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Startup orchestration FAILED (exit code: $EXIT_CODE)" | tee -a "$LOG_FILE"
fi

exit $EXIT_CODE
