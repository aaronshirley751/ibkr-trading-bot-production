#!/bin/bash
# =============================================================================
# IBKR Gateway Health Check Script
# =============================================================================
#
# Exit codes:
#   0 - Gateway healthy
#   1 - Gateway process not running
#   2 - API port not responding
#   3 - Authentication failed (detected in logs)
#   4 - Network unreachable
#
# Usage: /usr/local/bin/ibkr-health-check.sh
# =============================================================================

set -euo pipefail

GATEWAY_PORT="${GATEWAY_PORT:-4002}"
GATEWAY_HOST="127.0.0.1"

# Check 1: Gateway process running
if ! pgrep -f "ibgateway" > /dev/null; then
    echo "UNHEALTHY: Gateway process not running"
    exit 1
fi

# Check 2: API port responding
if ! nc -z -w 5 "$GATEWAY_HOST" "$GATEWAY_PORT" 2>/dev/null; then
    echo "UNHEALTHY: API port $GATEWAY_PORT not responding"
    exit 2
fi

# Check 3: Recent authentication errors in logs (last 5 minutes)
if journalctl -u ibkr-gateway --since "5 minutes ago" 2>/dev/null | grep -qi "authentication.*fail"; then
    echo "UNHEALTHY: Authentication failure detected in recent logs"
    exit 3
fi

# Check 4: Network connectivity to IBKR servers
if ! ping -c 1 -W 5 gw1.ibllc.com > /dev/null 2>&1; then
    echo "UNHEALTHY: Cannot reach IBKR servers (network issue)"
    exit 4
fi

echo "HEALTHY: Gateway running, API responsive, network connected"
exit 0
