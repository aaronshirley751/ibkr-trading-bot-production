# VSC HANDOFF: IBC Controller Configuration Schema (Docker)

## Header Block

| Field | Value |
|-------|-------|
| **Task ID** | 3.1 (luDzPijHOkGm924LZp-4GmUAARKb) |
| **Date** | 2026-02-09 |
| **Revision** | 2.0 — Docker-based deployment |
| **Requested By** | Operator / Phase 3 Kickoff |
| **Lead Personas** | @Systems_Architect, @DevOps |
| **Model Routing** | Sonnet (structured implementation) |
| **Context Budget** | Moderate (~6K input + 2K output) |
| **Board** | IBKR Project Management |

---

> **Implementation Note (2026-02-10):** This document reflects the original v2 design.
> The actual implementation differs slightly due to container image behavior discovered
> during deployment (CUSTOM_CONFIG disabled, environment-based credential injection).
> See [docker/gateway/README.md](../docker/gateway/README.md) for the authoritative
> deployment guide.

---

## Deployment Strategy

| Phase | Platform | Runtime | Notes |
|-------|----------|---------|-------|
| **Now** | Windows 11 Desktop | Docker Desktop (WSL2) | Initial development, paper trading |
| **POC/Validation** | Windows 11 Desktop | Docker Desktop (WSL2) | Paper trading stability test |
| **Production** | Ubuntu Server 24.04 (Rackmount) | Docker Engine | Live trading after CRO approval |

**Key Principle:** Same `docker-compose.yml` and configuration files work on both platforms. Migration = copy files + `docker compose up`.

---

# AGENT EXECUTION BLOCK

---

## 1. Objective

Deploy IBKR Gateway via Docker container with IBC Controller for automated lifecycle management. This configuration enables:

- Zero-touch Gateway startup via `docker compose up -d`
- Automated authentication without manual intervention
- Container health checks with automatic restart on failure
- Scheduled daily restart (4:30 PM ET) for memory leak mitigation
- Portable configuration between Windows Desktop and Ubuntu rackmount

**Container Image:** `ghcr.io/gnzsnz/ib-gateway-docker` — well-maintained, actively developed, supports both Gateway and TWS modes.

---

## 2. File Structure

Create these files in the project repository:

```
crucible/
├── docker/
│   └── gateway/
│       ├── docker-compose.yml      # Container orchestration
│       ├── .env                    # Credentials (gitignored)
│       ├── .env.example            # Template for .env
│       ├── config.ini              # IBC configuration
│       └── scripts/
│           ├── health-check.sh     # Container health validation
│           └── scheduled-restart.sh # Daily restart trigger (host-side)
├── .gitignore                      # Must include docker/gateway/.env
```

**Files to Create (this task):**
1. `docker/gateway/docker-compose.yml` — Container definition
2. `docker/gateway/.env.example` — Credential template
3. `docker/gateway/config.ini` — IBC settings
4. `docker/gateway/scripts/health-check.sh` — Health check script
5. `docker/gateway/scripts/scheduled-restart.sh` — Restart script

**NOT tracked in git:**
- `docker/gateway/.env` — Contains real credentials

---

## 3. Logic Flow (Pseudo-code)

### 3.1 Container Startup Sequence

```
docker compose up -d
    │
    ├─► Docker creates container from ghcr.io/gnzsnz/ib-gateway-docker
    │
    ├─► Container entrypoint:
    │       └─► Starts Xvfb (virtual display :1)
    │       └─► Starts x11vnc (optional VNC access for debugging)
    │       └─► Reads environment variables (credentials, trading mode)
    │       └─► Reads mounted config.ini
    │       └─► Starts IBC Controller
    │
    ├─► IBC launches Gateway:
    │       └─► Gateway initializes Java process
    │       └─► IBC fills login credentials
    │       └─► Gateway authenticates with IBKR servers
    │       └─► Gateway opens API port 4002 (mapped to host)
    │
    ├─► Container health check (every 30s):
    │       └─► Check: API port 4002 responding?
    │       └─► If unhealthy 3x: container restarts automatically
    │
    └─► Trading bot connects to localhost:4002
```

### 3.2 Daily Scheduled Restart (4:30 PM ET)

```
Host scheduled task triggers at 4:30 PM ET
    │
    ├─► Windows: Task Scheduler runs scheduled-restart.sh via WSL
    │   Ubuntu: Cron job runs scheduled-restart.sh
    │
    ├─► Script executes:
    │       └─► docker compose restart gateway
    │       └─► Container stops gracefully (SIGTERM → IBC shutdown)
    │       └─► Container starts fresh (clean memory state)
    │       └─► Health check validates restart success
    │       └─► Discord notification sent
    │
    └─► Gateway running with fresh memory allocation
```

### 3.3 Crash Recovery (Container Restart Policy)

```
Gateway process crashes inside container
    │
    ├─► Container health check fails (API port not responding)
    │
    ├─► After 3 consecutive failures (90 seconds):
    │       └─► Docker marks container "unhealthy"
    │       └─► restart: unless-stopped policy triggers
    │       └─► Container restarts automatically
    │
    ├─► If restart succeeds:
    │       └─► Health check passes
    │       └─► Normal operation resumes
    │
    └─► If restart fails repeatedly:
            └─► Docker stops restarting (backoff)
            └─► Manual intervention required
            └─► Discord notification: CRITICAL
```

---

## 4. Dependencies

### 4.1 Windows Desktop (Current Target)

```powershell
# Prerequisites:
# 1. Docker Desktop for Windows (with WSL2 backend)
#    Download: https://www.docker.com/products/docker-desktop/
#
# 2. WSL2 with Ubuntu (for running bash scripts)
#    wsl --install -d Ubuntu
#
# 3. Git Bash or WSL for running shell scripts

# Verify Docker is running:
docker --version
docker compose version
```

### 4.2 Ubuntu Rackmount (Future Target)

```bash
# Install Docker Engine (not Docker Desktop)
sudo apt update
sudo apt install -y docker.io docker-compose-v2

# Add user to docker group
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```

### 4.3 Container Image

```yaml
# Image: ghcr.io/gnzsnz/ib-gateway-docker
# Tags:
#   - latest: Most recent Gateway version
#   - stable: Stable Gateway version (recommended)
#   - 10.30.1t: Specific version pinning

# Image includes:
#   - IBKR Gateway (offline version)
#   - IBC Controller
#   - Xvfb (virtual framebuffer)
#   - x11vnc (optional VNC access)
#   - socat (for API port relay)
```

---

## 5. Input/Output Contract

### 5.1 Inputs

| Input | Source | Format | Required |
|-------|--------|--------|----------|
| `TWS_USERID` | `.env` file | String | Yes |
| `TWS_PASSWORD` | `.env` file | String | Yes |
| `TRADING_MODE` | `.env` file | `paper` or `live` | Yes |
| `TWS_SETTINGS_PATH` | `.env` file | Container path | No (optional persistence) |
| `DISCORD_WEBHOOK_URL` | `.env` file | URL | No (for notifications) |
| `config.ini` | Mounted volume | IBC INI format | Yes |

### 5.2 Outputs

| Output | Location | Format | Success Criteria |
|--------|----------|--------|------------------|
| Gateway API | `localhost:4002` | TCP socket | Accepting connections |
| VNC Access | `localhost:5900` | VNC protocol | Optional, for debugging |
| noVNC Web | `localhost:6080` | HTTP | Optional, browser-based VNC |
| Container Logs | `docker logs gateway` | Text stream | No ERROR entries |
| Health Status | Docker health check | healthy/unhealthy | `healthy` |

### 5.3 Health Check Exit Codes

| Code | Meaning | Docker Action |
|------|---------|---------------|
| 0 | Healthy | Container stays running |
| 1 | Unhealthy | After 3 failures, restart container |

---

## 6. Integration Points

### 6.1 Trading Bot Connection

```python
# Bot connects to Gateway via localhost (port mapped from container)
from ib_insync import IB

ib = IB()
ib.connect(
    host='127.0.0.1',
    port=4002,          # Mapped from container port 4002
    clientId=1,
    readonly=False
)
```

**Note:** Bot runs on host, Gateway runs in container. Port 4002 is mapped from container to host.

### 6.2 Health Monitoring (Task 3.3)

```bash
# Check container health from host
docker inspect --format='{{.State.Health.Status}}' gateway
# Returns: "healthy" or "unhealthy"

# Detailed health check
docker inspect --format='{{json .State.Health}}' gateway | jq
```

### 6.3 VNC Debugging Access

```bash
# Connect via VNC client to localhost:5900
# Or open browser to http://localhost:6080 for noVNC

# Useful for:
# - Watching Gateway login process
# - Debugging authentication issues
# - Manual Gateway configuration
```

### 6.4 Migration to Rackmount

```bash
# On Ubuntu rackmount server:

# 1. Clone repository
git clone <repo-url>
cd crucible/docker/gateway

# 2. Create .env from template
cp .env.example .env
nano .env  # Fill in credentials

# 3. Start Gateway
docker compose up -d

# 4. Verify
docker ps
docker logs gateway
curl -s localhost:4002  # Should connect (may get protocol error, that's OK)
```

**That's it.** Same files, different host.

---

## 7. Definition of Done

### 7.1 Configuration Files

- [ ] `docker-compose.yml` created and valid (`docker compose config`)
- [ ] `.env.example` created with all required variables documented
- [ ] `.env` created locally with real credentials (NOT committed)
- [ ] `config.ini` created with IBC settings
- [ ] `.gitignore` includes `docker/gateway/.env`

### 7.2 Container Operation

- [ ] Container starts: `docker compose up -d`
- [ ] Container running: `docker ps` shows `gateway` with status `Up`
- [ ] Container healthy: `docker inspect` shows `"Status": "healthy"`
- [ ] Logs clean: `docker logs gateway` shows successful login
- [ ] API responds: `nc -zv localhost 4002` succeeds

### 7.3 Gateway Authentication

- [ ] IBC logs show "Login dialog  detected"
- [ ] IBC logs show "Credentials entered"
- [ ] IBC logs show "Login successful" or equivalent
- [ ] Paper trading mode confirmed (for initial deployment)

### 7.4 Scheduled Restart

- [ ] Restart script works: `./scripts/scheduled-restart.sh`
- [ ] Container restarts cleanly
- [ ] Gateway reconnects after restart
- [ ] Windows Task Scheduler configured (or cron on Linux)

### 7.5 Crash Recovery

- [ ] Simulate crash: `docker exec gateway pkill -9 java`
- [ ] Health check detects failure (within 90 seconds)
- [ ] Container auto-restarts
- [ ] Gateway recovers and API responds

### 7.6 Security Validation

- [ ] `.env` file not tracked in git: `git status` shows untracked
- [ ] Credentials not in `docker compose config` output
- [ ] Credentials not visible in `docker inspect gateway`

### 7.7 Review Sign-off

- [ ] @DevOps review: Docker patterns, health checks, restart policy
- [ ] @CRO review: No capital risk during container failures

---

## 8. Edge Cases to Test

### 8.1 Container Already Running

```bash
# Try to start when already running
docker compose up -d
# Expected: "Container gateway is up-to-date" (no-op)
```

### 8.2 Wrong Credentials

```bash
# Edit .env with wrong password, restart
docker compose down
docker compose up -d
docker logs -f gateway
# Expected: Authentication failure in logs, container may restart repeatedly
# Recovery: Fix .env, restart
```

### 8.3 Docker Desktop Not Running (Windows)

```powershell
# If Docker Desktop is stopped
docker compose up -d
# Expected: Error "Cannot connect to Docker daemon"
# Recovery: Start Docker Desktop, retry
```

### 8.4 Port 4002 Already in Use

```bash
# If another process uses 4002
docker compose up -d
# Expected: Error "port is already allocated"
# Recovery: Stop conflicting process, or change port mapping in compose file
```

### 8.5 Network Connectivity Lost

```bash
# If network drops during operation
# Expected: Gateway disconnects from IBKR, may attempt reconnect
# IBC handles reconnection automatically
# If persistent: container health check fails, restart triggered
```

### 8.6 Container Disk Full

```bash
# If Docker disk fills up
# Expected: Container may fail to write logs, potential crash
# Prevention: Docker Desktop → Settings → Resources → Disk limit
# Recovery: docker system prune -a
```

### 8.7 WSL2 Shutdown (Windows)

```powershell
# If WSL2 restarts (Windows update, manual shutdown)
# Expected: Container stops with WSL2
# Recovery: Containers auto-start when Docker Desktop restarts (restart policy)
```

### 8.8 Two-Factor Authentication Timeout

```bash
# If 2FA not completed in time (180 seconds)
# Expected: IBC exits, container restarts, fresh login attempt
# Config setting: TWOFA_TIMEOUT_ACTION=restart
```

---

## 9. Rollback Plan

### 9.1 Stop Container

```bash
cd crucible/docker/gateway
docker compose down
```

### 9.2 Remove Container and Image

```bash
docker compose down --rmi all --volumes
```

### 9.3 Manual Gateway Launch (Fallback)

```bash
# If Docker approach fails, install Gateway natively:
# 1. Download Gateway from IBKR website
# 2. Install normally
# 3. Run Gateway manually, login via GUI
# 4. Bot connects to localhost:4002

# This bypasses all automation but allows trading to continue
```

### 9.4 Revert to Previous Configuration

```bash
git checkout HEAD -- docker/gateway/
docker compose up -d
```

---

# CONTEXT BLOCK

---

## Alpha Learnings Integration

| Learning | Docker Implementation |
|----------|----------------------|
| Gateway memory leak | Scheduled container restart at 4:30 PM ET |
| Gateway requires 1.3-1.7GB RAM | Container has no memory limit (uses host resources) |
| x86_64 native support | Container image is x86_64, runs natively |
| Port 4002 for Gateway | Mapped from container to host |
| Paper vs Live credentials | Controlled via `TRADING_MODE` env var |

---

## CRO Safety Requirements

| Scenario | Container Behavior | Risk Exposure |
|----------|-------------------|---------------|
| Container stops | Bot loses connection, enters Strategy C | Zero new risk |
| Container crash | Auto-restart via policy | Brief interruption |
| Authentication failure | Container restarts, retries login | Zero new risk |
| Docker Desktop stops | All containers stop | Bot cannot trade |

**CRO Directive:** Container infrastructure failures trigger trading bot's Strategy C mode. Defense-in-depth maintained.

---

## Container Image Details

**Image:** `ghcr.io/gnzsnz/ib-gateway-docker`

**Key Features:**
- Based on Ubuntu, includes all Gateway dependencies
- IBC pre-configured for headless operation
- Xvfb provides virtual display
- x11vnc allows remote debugging
- socat relays API port from localhost to all interfaces
- Supports secrets via Docker secrets or environment variables
- Active maintenance, regular updates

**Environment Variables (Full List):**

| Variable | Description | Default |
|----------|-------------|---------|
| `TWS_USERID` | IBKR username | (required) |
| `TWS_PASSWORD` | IBKR password | (required) |
| `TRADING_MODE` | `paper` or `live` | `paper` |
| `TWS_SETTINGS_PATH` | Persist Gateway settings | `/home/ibgateway/Jts` |
| `TWOFA_TIMEOUT_ACTION` | On 2FA timeout: `exit` or `restart` | `restart` |
| `AUTO_RESTART_TIME` | Gateway auto-restart time | (disabled) |
| `RELOGIN_AFTER_TWOFA_TIMEOUT` | Retry login after 2FA timeout | `yes` |
| `TIME_ZONE` | Container timezone | `America/New_York` |
| `CUSTOM_CONFIG` | Use mounted config.ini | `yes` |

---

# APPENDIX: FILE CONTENTS

## 10.1 docker-compose.yml

```yaml
# =============================================================================
# IBKR Gateway Docker Compose Configuration
# Charter & Stone Capital — The Crucible
# =============================================================================
#
# Usage:
#   docker compose up -d      # Start Gateway
#   docker compose down       # Stop Gateway
#   docker compose logs -f    # View logs
#   docker compose restart    # Restart Gateway
#
# =============================================================================

services:
  gateway:
    image: ghcr.io/gnzsnz/ib-gateway-docker:stable
    container_name: ibkr-gateway

    # Restart policy: always restart unless explicitly stopped
    restart: unless-stopped

    # Environment variables (loaded from .env file)
    environment:
      # Credentials
      - TWS_USERID=${TWS_USERID}
      - TWS_PASSWORD=${TWS_PASSWORD}
      - TRADING_MODE=${TRADING_MODE:-paper}

      # Timezone (for proper market hours handling)
      - TIME_ZONE=America/New_York

      # 2FA handling: restart on timeout for fresh attempt
      - TWOFA_TIMEOUT_ACTION=restart
      - RELOGIN_AFTER_TWOFA_TIMEOUT=yes

      # Use custom config.ini
      - CUSTOM_CONFIG=yes

      # Disable Gateway's internal auto-restart (we use scheduled restart)
      - AUTO_RESTART_TIME=

      # VNC password for debugging access (optional)
      - VNC_SERVER_PASSWORD=${VNC_PASSWORD:-}

    # Port mappings
    ports:
      # Gateway API port (trading bot connects here)
      - "127.0.0.1:4002:4002"

      # VNC port for debugging (optional, disable in production)
      - "127.0.0.1:5900:5900"

      # noVNC web interface (optional, disable in production)
      - "127.0.0.1:6080:6080"

    # Mount custom IBC configuration
    volumes:
      - ./config.ini:/home/ibgateway/ibc/config.ini:ro

      # Optional: Persist Gateway settings between restarts
      # - ./tws_settings:/home/ibgateway/Jts

    # Container health check
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "4002"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s  # Gateway takes time to start

    # Resource limits (optional, adjust based on host capacity)
    # deploy:
    #   resources:
    #     limits:
    #       memory: 4G
    #     reservations:
    #       memory: 2G

    # Logging configuration
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"

# =============================================================================
# Network configuration (optional, for multi-container setups)
# =============================================================================
# networks:
#   default:
#     name: crucible-network
```

## 10.2 .env.example

```bash
# =============================================================================
# IBKR Gateway Environment Configuration
# Charter & Stone Capital — The Crucible
# =============================================================================
#
# INSTRUCTIONS:
#   1. Copy this file to .env: cp .env.example .env
#   2. Fill in your IBKR credentials
#   3. NEVER commit .env to version control
#
# =============================================================================

# -----------------------------------------------------------------------------
# IBKR Credentials (REQUIRED)
# -----------------------------------------------------------------------------

# Your IBKR account username
TWS_USERID=your_ibkr_username

# Your IBKR account password
# Note: If password contains special characters, wrap in single quotes
TWS_PASSWORD='your_ibkr_password'

# Trading mode: 'paper' or 'live'
# ALWAYS start with 'paper' for testing
# Change to 'live' ONLY after CRO approval and paper trading validation
TRADING_MODE=paper

# -----------------------------------------------------------------------------
# Optional Settings
# -----------------------------------------------------------------------------

# VNC password for debugging access (leave empty to disable auth)
# VNC_PASSWORD=debugging123

# Discord webhook for notifications (optional)
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url

# =============================================================================
# SECURITY REMINDER
# =============================================================================
# This file contains sensitive credentials.
# - Never commit to git
# - Set file permissions: chmod 600 .env
# - Keep backups secure
# =============================================================================
```

## 10.3 config.ini

```ini
# =============================================================================
# IBC Configuration File
# Charter & Stone Capital — The Crucible
# =============================================================================
#
# This file is mounted into the Gateway container.
# Reference: https://github.com/IbcAlpha/IBC/blob/master/resources/config.ini
#
# =============================================================================

# =============================================================================
# 1. Authentication Settings
# =============================================================================

# Credentials are passed via environment variables, not this file
IbLoginId=
IbPassword=

# Trading mode is set via environment variable
TradingMode=

# =============================================================================
# 2. Gateway Behavior Settings
# =============================================================================

# Accept incoming API connections automatically
# Container only exposes to localhost, so this is safe
AcceptIncomingConnectionAction=accept

# Allow trading without market data subscription
AllowBlindTrading=yes

# Auto-dismiss paper trading warning dialog
AcceptNonBrokerageAccountWarning=yes

# If another session exists, take over as primary
ExistingSessionDetectedAction=primary

# Keep Gateway window (not relevant in container, but set anyway)
MinimizeMainWindow=no

# Don't store settings on IBKR servers
StoreSettingsOnServer=no

# =============================================================================
# 3. API Settings
# =============================================================================

# Allow full API access (not read-only)
ReadOnlyLogin=no
ReadOnlyApi=no

# =============================================================================
# 4. Auto-Logoff/Restart Settings
# =============================================================================

# DISABLED: We manage restarts via Docker/scheduled task
# Gateway's internal restart doesn't clear memory as effectively
IbAutoClosedown=no
AutoLogoffTime=
AutoRestartTime=

# =============================================================================
# 5. Two-Factor Authentication Settings
# =============================================================================

# Exit on 2FA timeout (container restart policy handles retry)
ExitAfterSecondFactorAuthenticationTimeout=yes

# 2FA timeout in seconds
SecondFactorAuthenticationTimeout=180

# Attempt re-login after 2FA timeout
ReloginAfterSecondFactorAuthenticationTimeout=yes

# =============================================================================
# 6. Command Server Settings
# =============================================================================

# Disable IBC command server (not needed with Docker management)
CommandServerPort=0
BindAddress=127.0.0.1
ControlFrom=127.0.0.1

# =============================================================================
# END OF CONFIGURATION
# =============================================================================
```

## 10.4 scripts/health-check.sh

```bash
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
```

## 10.5 scripts/scheduled-restart.sh

```bash
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
```

## 10.6 .gitignore Addition

```gitignore
# IBKR Gateway credentials (NEVER commit)
docker/gateway/.env

# Gateway settings persistence (if enabled)
docker/gateway/tws_settings/

# Restart logs
docker/gateway/restart.log
```

---

## 11. Windows Task Scheduler Setup

To schedule daily restart on Windows:

```powershell
# Create scheduled task via PowerShell (run as Administrator)

$action = New-ScheduledTaskAction `
    -Execute "wsl.exe" `
    -Argument "-d Ubuntu /path/to/crucible/docker/gateway/scripts/scheduled-restart.sh"

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "4:30 PM"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd

Register-ScheduledTask `
    -TaskName "IBKR Gateway Daily Restart" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Restarts IBKR Gateway container at 4:30 PM ET to mitigate memory leak"
```

---

## 12. Quick Start Guide

### First-Time Setup

```bash
# 1. Navigate to gateway directory
cd crucible/docker/gateway

# 2. Create environment file from template
cp .env.example .env

# 3. Edit .env with your IBKR credentials
# Use your preferred editor (nano, vim, notepad, etc.)

# 4. Start Gateway
docker compose up -d

# 5. Watch logs (wait for login to complete)
docker compose logs -f

# 6. Verify health (after ~2 minutes)
docker ps  # Should show "healthy"

# 7. Test API connection
nc -zv localhost 4002  # Should succeed
```

### Daily Operations

```bash
# Check status
docker ps
docker compose logs --tail=50

# Manual restart
docker compose restart

# Stop Gateway
docker compose down

# View resource usage
docker stats ibkr-gateway
```

---

# END OF VSC HANDOFF DOCUMENT

**Document Version:** 2.0 (Docker-based)
**Created:** 2026-02-09
**Supersedes:** v1.0 (systemd-based)
**Task:** 3.1 - IBC Controller Configuration Schema
**Status:** Ready for implementation
**Platform:** Windows Docker Desktop (now) → Ubuntu Docker Engine (future)
