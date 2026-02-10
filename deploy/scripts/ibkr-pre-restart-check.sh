#!/bin/bash
# =============================================================================
# IBKR Gateway Pre-Restart Check Script
# =============================================================================
#
# Run before scheduled restart to check for potential issues.
# Logs warnings but does not block restart (market is closed at 4:30 PM).
#
# =============================================================================

set -euo pipefail

LOG_FILE="/var/log/ibkr/restart.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

log "Pre-restart check initiated"

# Check 1: Is Gateway running?
if pgrep -f "ibgateway" > /dev/null; then
    log "INFO: Gateway process is running"
else
    log "WARNING: Gateway process not found (will start fresh)"
fi

# Check 2: Is API port active?
if nc -z -w 5 127.0.0.1 4002 2>/dev/null; then
    log "INFO: API port 4002 is active"
else
    log "WARNING: API port 4002 not responding"
fi

# Check 3: Log warning about potential open positions
# Note: We cannot check actual positions from here (bot responsibility)
CURRENT_HOUR=$(date '+%H')
if [ "$CURRENT_HOUR" -lt "16" ]; then
    log "WARNING: Restart triggered before market close - positions may be open"
fi

# Check 4: Memory usage of Gateway process
if pgrep -f "ibgateway" > /dev/null; then
    GATEWAY_PID=$(pgrep -f "ibgateway" | head -1)
    if [ -n "$GATEWAY_PID" ]; then
        GATEWAY_MEM=$(ps -o rss= -p "$GATEWAY_PID" 2>/dev/null | awk '{print $1/1024}')
        log "INFO: Gateway memory usage: ${GATEWAY_MEM:-unknown} MB"
    fi
fi

log "Pre-restart check complete - proceeding with restart"
exit 0
