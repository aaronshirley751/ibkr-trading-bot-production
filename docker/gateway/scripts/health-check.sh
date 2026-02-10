#!/bin/bash
# =============================================================================
# IBKR Gateway Health Check (Host-Side)
# =============================================================================
#
# Checks Gateway container health from the host.
# Returns exit code 0 if healthy, non-zero otherwise.
#
# Usage: ./scripts/health-check.sh
#
# =============================================================================

set -euo pipefail

CONTAINER_NAME="ibkr-gateway"
API_PORT=4002

# Check 1: Container running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "UNHEALTHY: Container not running"
    exit 1
fi

# Check 2: Container health status
HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
if [ "$HEALTH_STATUS" != "healthy" ]; then
    echo "UNHEALTHY: Container health status is '$HEALTH_STATUS'"
    exit 2
fi

# Check 3: API port responding (from host)
if ! nc -z -w 5 localhost "$API_PORT" 2>/dev/null; then
    echo "UNHEALTHY: API port $API_PORT not responding"
    exit 3
fi

echo "HEALTHY: Gateway container running and API responsive"
exit 0
