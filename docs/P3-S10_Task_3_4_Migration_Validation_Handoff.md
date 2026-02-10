# Task 3.4 Migration & Validation — Unified Docker Stack Activation

**Session:** P3-S10 (Phase 3, Sprint 1, Session 10)
**Path:** A+ (Quick Migration + First Bot Start)
**Model:** Sonnet
**Extended Thinking:** Optional (migration is straightforward)
**Estimated Duration:** 60-90 minutes
**Date:** 2026-02-10

---

## Copy and paste this into a fresh Sonnet chat (or continue in current VSC session):

```
TASK 3.4 MIGRATION & VALIDATION — Path A+ Execution

**Context:**
Task 3.4 infrastructure is 95% complete. A unified docker-compose.yml exists with all services (Gateway, Bot, Health Monitor), but the system is currently running from the legacy standalone Gateway compose file. The bot container has never been started in production. This session migrates to the unified stack and validates first bot startup.

**Discovery Summary from Engineer Investigation:**
- ✅ Unified docker/docker-compose.yml exists with proper dependency graph
- ✅ Bot Dockerfile working (docker/bot/Dockerfile + entrypoint.sh)
- ✅ Shared Docker network configured (docker_trading-network)
- ✅ All services have restart policies (unless-stopped)
- ❌ Gateway currently runs from docker/gateway/docker-compose.yml (standalone)
- ❌ Bot container never started in production
- ❌ Unified stack never fully activated

**Your Mission:**
1. Migrate Gateway from standalone to unified stack
2. Start bot container for first time in production
3. Validate all services communicate correctly
4. Document success criteria
5. Mark Task 3.4 complete

---

## PRE-MIGRATION CHECKLIST

**Before making any changes, capture current state:**

### Step 1: Document Current Running Containers
```powershell
# Check what's currently running
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

# Expected output:
# health-monitor    docker-health-monitor       Up X hours
# ibkr-gateway      gnzsnz/ib-gateway:stable    Up X hours (healthy)
```

**Action:** Screenshot or copy this output for rollback reference.

### Step 2: Verify Gateway Health Pre-Migration
```powershell
# Check Gateway is healthy before migration
docker inspect ibkr-gateway --format='{{.State.Health.Status}}'
# Should output: healthy

# Check Gateway logs for any errors
docker logs ibkr-gateway --tail 20
# Should show normal operation, no errors
```

### Step 3: Backup Current Configuration
```powershell
# Create backup of current running state
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker\gateway
docker compose config > docker-compose.backup.yml

# Note current network attachments
docker inspect ibkr-gateway --format='{{json .NetworkSettings.Networks}}' > gateway-networks-backup.json
```

**Action:** Verify backup files created successfully.

---

## MIGRATION PROCEDURE

### Phase 1: Graceful Shutdown of Standalone Gateway

**Step 1.1: Stop Health Monitor First**
```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
docker compose stop health-monitor

# Verify stopped
docker ps | grep health-monitor
# Should return nothing
```

**Rationale:** Health monitor will try to restart Gateway if it detects failure. Stop it first to prevent interference.

**Step 1.2: Stop Standalone Gateway**
```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker\gateway
docker compose down

# Verify Gateway stopped
docker ps | grep ibkr-gateway
# Should return nothing

# Verify network cleaned up
docker network ls | grep gateway_default
# Should still exist (network persists until removed)
```

**Checkpoint:** At this point, NO containers should be running. Verify:
```powershell
docker ps
# Should show NAMES column empty or only unrelated containers
```

---

### Phase 2: Start Unified Stack

**Step 2.1: Verify Unified Compose File**
```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker

# Verify compose file syntax
docker compose config

# Should output valid YAML with 3 services:
# - gateway
# - trading-bot
# - health-monitor
```

**If errors occur:** Fix syntax issues before proceeding.

**Step 2.2: Start Unified Stack (Gateway First)**
```powershell
# Start only Gateway first (to verify migration works)
docker compose up -d gateway

# Watch Gateway startup
docker logs -f ibkr-gateway
```

**Expected Log Output:**
```
Starting IBC...
IB Gateway starting...
Gateway TWS API ready on port 4002
Authentication successful
Gateway ready
```

**Wait for Gateway Health Check to Pass:**
```powershell
# Check health status (may take 30-60 seconds)
docker inspect ibkr-gateway --format='{{.State.Health.Status}}'

# Keep checking until output is: healthy
# Retry every 10 seconds until healthy
```

**Checkpoint:** Gateway must be **healthy** before proceeding. If Gateway fails to start or authenticate:
- Check logs: `docker logs ibkr-gateway --tail 50`
- Verify .env file credentials correct
- Check network connectivity
- **DO NOT PROCEED** until Gateway is healthy

---

**Step 2.3: Start Health Monitor**
```powershell
# Start health monitor (should connect to Gateway)
docker compose up -d health-monitor

# Watch health monitor logs
docker logs -f health-monitor --tail 20
```

**Expected Log Output:**
```json
{"timestamp": "...", "component": "gateway", "status": "healthy", "port_responding": true}
{"timestamp": "...", "level": "INFO", "message": "Gateway health check passed"}
```

**Verify Discord Alert:**
- Check Discord channel for "🟢 Gateway healthy" or similar notification
- If no alert, check health monitor logs for webhook errors

**Checkpoint:** Health monitor must successfully detect Gateway before proceeding.

---

**Step 2.4: First Bot Startup (CRITICAL)**
```powershell
# Start bot container for the first time in production
docker compose up -d trading-bot

# IMMEDIATELY watch bot logs
docker logs -f trading-bot
```

**Expected Log Output (First 60 seconds):**

```
[2026-02-10 XX:XX:XX] INFO - Bot startup initiated
[2026-02-10 XX:XX:XX] INFO - Environment: DRY_RUN=true
[2026-02-10 XX:XX:XX] INFO - Gateway connection config: gateway:4002
[2026-02-10 XX:XX:XX] INFO - Waiting for Gateway readiness...
[2026-02-10 XX:XX:XX] INFO - Gateway health check attempt 1/30
[2026-02-10 XX:XX:XX] INFO - Gateway responding on port 4002
[2026-02-10 XX:XX:XX] INFO - Gateway authenticated: True
[2026-02-10 XX:XX:XX] INFO - Initializing broker connection...
[2026-02-10 XX:XX:XX] INFO - IBKR Gateway connected successfully
[2026-02-10 XX:XX:XX] INFO - Account: DU[XXXXXX] (Paper Trading)
[2026-02-10 XX:XX:XX] INFO - No gameplan file found at /data/gameplan.json
[2026-02-10 XX:XX:XX] INFO - Defaulting to Strategy C (Cash Preservation)
[2026-02-10 XX:XX:XX] INFO - Strategy C active: No trading, monitoring only
[2026-02-10 XX:XX:XX] INFO - Bot operational in safe mode
```

**CRITICAL SUCCESS INDICATORS:**
- ✅ "Gateway connected successfully"
- ✅ "Account: DU[XXXXXX] (Paper Trading)" — confirms IBKR connection
- ✅ "Defaulting to Strategy C" — confirms safe mode (no gameplan = no trading)
- ✅ "DRY_RUN=true" — confirms no real orders will be placed

**FAILURE INDICATORS (Require Investigation):**
- ❌ "Gateway connection timeout" → Gateway not accessible from bot container
- ❌ "Authentication failed" → Credentials issue
- ❌ "Port 4002 unreachable" → Network configuration issue
- ❌ Bot container exits/crashes → Check logs: `docker logs trading-bot`

**If Bot Fails to Start:**
1. Check network connectivity:
   ```powershell
   docker exec trading-bot ping gateway
   # Should respond successfully
   ```

2. Check environment variables:
   ```powershell
   docker exec trading-bot env | grep GATEWAY
   # Should show GATEWAY_HOST=gateway, GATEWAY_PORT=4002
   ```

3. Check Gateway is on same network:
   ```powershell
   docker inspect ibkr-gateway --format='{{json .NetworkSettings.Networks}}'
   docker inspect trading-bot --format='{{json .NetworkSettings.Networks}}'
   # Both should show "docker_trading-network"
   ```

**DO NOT PROCEED** until bot successfully connects to Gateway.

---

### Phase 3: Validation

**Step 3.1: Verify All Containers Running and Healthy**
```powershell
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Output:**
```
NAMES           IMAGE                        STATUS              PORTS
trading-bot     docker-trading-bot           Up X seconds
ibkr-gateway    gnzsnz/ib-gateway:stable    Up X minutes (healthy)   0.0.0.0:4002->4002/tcp
health-monitor  docker-health-monitor       Up X minutes
```

**All 3 containers must be "Up".**

**Step 3.2: Verify Network Connectivity**
```powershell
# Check all containers on same network
docker network inspect docker_trading-network --format='{{json .Containers}}' | ConvertFrom-Json

# Should show 3 containers:
# - ibkr-gateway (IP: 172.20.0.X)
# - trading-bot (IP: 172.20.0.X)
# - health-monitor (IP: 172.20.0.X)
```

**Step 3.3: Verify Bot Can Query Gateway API**
```powershell
# Check bot logs for API activity (should see market data queries in dry-run mode)
docker logs trading-bot --tail 50 | Select-String "market data|API|Gateway"

# Expected: Log entries showing Gateway API interactions
```

**Step 3.4: Verify Health Monitor Detects Bot**
```powershell
docker logs health-monitor --tail 50 | Select-String "trading-bot|bot health"

# Expected: Health check logs showing bot status monitoring
```

**Step 3.5: Verify Discord Alerts Operational**
- Check Discord channel for recent alerts
- Should see:
  - 🟢 "Gateway healthy" (from health monitor)
  - 🟢 "Bot started" or "Bot connected" (if configured)

**Step 3.6: Test Restart Behavior**
```powershell
# Restart entire stack to verify restart policies work
docker compose restart

# Watch logs during restart
docker compose logs -f

# After ~60-90 seconds, verify all 3 containers healthy again
docker ps
```

**Step 3.7: Test Single-Command Startup**
```powershell
# Stop entire stack
docker compose down

# Verify all stopped
docker ps
# Should show no containers (or only unrelated ones)

# Start entire stack with single command
docker compose up -d

# Verify all 3 containers start and become healthy
docker ps
docker logs ibkr-gateway --tail 20
docker logs trading-bot --tail 20
docker logs health-monitor --tail 20
```

**SUCCESS CRITERIA:**
- ✅ Single command `docker compose up -d` starts all services
- ✅ Gateway becomes healthy within 60-90 seconds
- ✅ Bot waits for Gateway, then connects successfully
- ✅ Health monitor detects both Gateway and Bot
- ✅ All services survive restart
- ✅ Discord alerts working

---

## POST-MIGRATION DOCUMENTATION

**Step 4.1: Update docker/README.md**

Create or update `docker/README.md` with:

```markdown
# Docker Deployment — Unified Stack

## Quick Start

```bash
cd docker
docker compose up -d
```

This starts all services:
- **gateway** — IBKR Gateway (port 4002)
- **trading-bot** — Trading bot (connects to Gateway)
- **health-monitor** — Health monitoring system

## Verify Status

```bash
docker ps
docker logs ibkr-gateway
docker logs trading-bot
docker logs health-monitor
```

## Stop All Services

```bash
docker compose down
```

## Restart Services

```bash
docker compose restart
```

## Configuration

Environment variables in `docker/.env`:
- `IBKR_USERNAME` — IBKR account username
- `IBKR_PASSWORD` — IBKR account password
- `TRADING_MODE` — "paper" or "live"
- `GATEWAY_PORT` — Default 4002 (paper), 4001 (live)
- `DRY_RUN` — Default "true" (safe mode)
- `DISCORD_WEBHOOK_URL` — Discord alerts webhook

## Troubleshooting

**Gateway not starting:**
```bash
docker logs ibkr-gateway --tail 50
# Check for authentication errors, port conflicts
```

**Bot not connecting:**
```bash
docker logs trading-bot --tail 50
# Verify GATEWAY_HOST=gateway in environment
# Check network: docker network inspect docker_trading-network
```

**Health monitor not alerting:**
```bash
docker logs health-monitor --tail 50
# Verify DISCORD_WEBHOOK_URL in .env
```

## Architecture

```
┌─────────────────┐
│  trading-bot    │────┐
└─────────────────┘    │
                       ▼
┌─────────────────┐  ┌─────────────────┐
│ health-monitor  │◄─┤  ibkr-gateway   │
└─────────────────┘  └─────────────────┘
         │                    │
         ▼                    ▼
   Discord Alerts        IBKR Servers
```

All services on shared network: `docker_trading-network`

## Migration Notes (2026-02-10)

- Migrated from standalone docker/gateway/docker-compose.yml to unified stack
- First bot container startup validated successfully
- Legacy standalone Gateway config preserved at docker/gateway/docker-compose.backup.yml
```

**Step 4.2: Mark Legacy File as Deprecated**

Add to top of `docker/gateway/docker-compose.yml`:

```yaml
# DEPRECATED: This file is no longer used.
# Migrated to unified stack: docker/docker-compose.yml
# Preserved for reference only.
# Date deprecated: 2026-02-10
# Reason: Task 3.4 migration to unified orchestration
```

**Step 4.3: Git Commit**

```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production

git add docker/docker-compose.yml docker/README.md docker/gateway/docker-compose.yml
git commit -m "Task 3.4: Migrate to unified Docker stack

- Migrated Gateway from standalone to unified docker-compose.yml
- First successful bot container startup in production
- Bot connects to Gateway successfully (Strategy C default)
- All services communicate on docker_trading-network
- Single-command startup validated: docker compose up -d
- Deprecated docker/gateway/docker-compose.yml (preserved for reference)
- Updated docker/README.md with unified stack usage

Task 3.4 COMPLETE
Validated: Gateway healthy, Bot connected, Health Monitor operational
Next: Task 3.5 (zero-touch startup on system boot)"

git push origin main
```

---

## SUCCESS VALIDATION CHECKLIST

Before marking Task 3.4 complete, verify ALL criteria met:

- [ ] **Migration Complete:**
  - [ ] Standalone Gateway stopped cleanly
  - [ ] Unified stack started successfully
  - [ ] All 3 containers running

- [ ] **Bot First Startup:**
  - [ ] Bot container started for first time in production
  - [ ] Bot logs show "Gateway connected successfully"
  - [ ] Bot enters Strategy C (Cash Preservation) mode
  - [ ] Bot confirms DRY_RUN=true (no real orders)
  - [ ] Bot displays paper trading account: DU[XXXXXX]

- [ ] **Network Validation:**
  - [ ] All containers on docker_trading-network
  - [ ] Bot can ping Gateway container by name
  - [ ] Health monitor can reach both Gateway and Bot

- [ ] **Health Monitoring:**
  - [ ] Health monitor detects Gateway healthy
  - [ ] Health monitor detects Bot running
  - [ ] Discord alerts operational (verified manually)

- [ ] **Restart Behavior:**
  - [ ] `docker compose restart` works correctly
  - [ ] All containers restart and become healthy
  - [ ] Bot reconnects to Gateway after restart

- [ ] **Single-Command Startup:**
  - [ ] `docker compose down` stops all services
  - [ ] `docker compose up -d` starts all services
  - [ ] No manual intervention required

- [ ] **Documentation:**
  - [ ] docker/README.md updated with unified stack usage
  - [ ] Legacy docker/gateway/docker-compose.yml marked deprecated
  - [ ] Git commit created and pushed

**If ALL checkboxes are ✅, Task 3.4 is COMPLETE.**

---

## ROLLBACK PROCEDURE (If Migration Fails)

**Only use if critical failure prevents forward progress:**

```powershell
# Stop unified stack
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
docker compose down

# Restart standalone Gateway
cd docker/gateway
docker compose up -d

# Restart health monitor from unified stack
cd ..
docker compose up -d health-monitor

# Verify rollback successful
docker ps
docker logs ibkr-gateway
docker logs health-monitor
```

**Rollback triggers:**
- Gateway fails to authenticate after migration
- Bot cannot connect to Gateway despite network verification
- Critical Discord alert integration broken
- Data loss or corruption detected

**DO NOT ROLLBACK** for minor issues like:
- Temporary network timeouts (retry)
- Bot log formatting differences
- Non-critical health monitor warnings

**If rollback required, document:**
1. What failed
2. Error messages/logs
3. Steps attempted before rollback
4. Contact @PM for revised migration strategy

---

## NEXT STEPS AFTER TASK 3.4 COMPLETE

**Immediate:**
1. Monitor system for 30 minutes post-migration
   - Watch Discord for any unexpected alerts
   - Check all container logs for errors
   - Verify bot remains connected to Gateway

2. Optional: Test with gameplan JSON
   - Create test gameplan: `/data/gameplan.json` (Strategy C override)
   - Restart bot: `docker compose restart trading-bot`
   - Verify bot loads gameplan (logs should show "Gameplan loaded")

**Next Session: Task 3.5 (Zero-Touch Startup)**
- Verify Docker Desktop auto-starts on Windows boot
- (Future) Configure systemd on Linux rackmount server
- Test: Reboot system → all services start automatically
- Duration: 2-3 hours

---

## CRITICAL SAFETY REMINDERS

**Before Any Action:**
1. Verify DRY_RUN=true in docker/.env (NEVER set to false without CRO approval)
2. Verify TRADING_MODE=paper (NEVER set to "live" without explicit authorization)
3. Backup current state before migration (already done in pre-migration checklist)

**During Bot Startup:**
1. Watch logs for "DRY_RUN=true" confirmation
2. Watch logs for "Paper Trading" account type
3. If logs show "live" or "production", IMMEDIATELY stop bot: `docker compose stop trading-bot`

**After Migration:**
1. Do NOT modify .env file without review
2. Do NOT start bot with gameplan JSON without validation
3. Do NOT disable DRY_RUN mode

**CRO Approval Required For:**
- Disabling DRY_RUN mode
- Switching to live trading
- Deploying real gameplan JSON
- Any configuration that could submit real orders

---

## TROUBLESHOOTING GUIDE

**Issue: Gateway won't start after migration**
```powershell
# Check if port 4002 is in use
netstat -ano | findstr :4002

# Check Gateway logs
docker logs ibkr-gateway --tail 50

# Verify .env credentials
docker exec ibkr-gateway env | grep IBKR
```

**Issue: Bot can't connect to Gateway**
```powershell
# Test network connectivity
docker exec trading-bot ping gateway

# Check environment variables
docker exec trading-bot env | grep GATEWAY

# Verify both on same network
docker network inspect docker_trading-network
```

**Issue: Health monitor not detecting services**
```powershell
# Check health monitor logs
docker logs health-monitor --tail 50

# Verify Discord webhook
docker exec health-monitor env | grep DISCORD

# Test manual health check
docker exec health-monitor python -c "import requests; print(requests.get('http://gateway:4002').status_code)"
```

**Issue: Discord alerts not working**
```powershell
# Verify webhook URL format
docker exec health-monitor env | grep DISCORD_WEBHOOK_URL
# Should be: https://discord.com/api/webhooks/...

# Test webhook manually
# (Send test alert from health monitor container)
docker exec health-monitor python monitoring/discord_alerts.py
```

---

**Ready to execute. Good luck! Report back with results.**
```

---

## Operator Instructions for Factory Floor

**Model Selection:** Sonnet (or continue in current VSC session if preferred)
**Session Type:** Implementation session (Factory Floor work)
**Estimated Duration:** 60-90 minutes

**Before Starting:**
1. Close any applications accessing Docker containers
2. Ensure Discord channel is open (to monitor alerts)
3. Have rollback procedure handy (in case of critical failure)
4. Backup current .env file: `copy docker\.env docker\.env.backup`

**During Execution:**
- Follow checklist sequentially (don't skip steps)
- Capture screenshots of critical outputs (Gateway health, bot startup logs)
- Monitor Discord for alerts throughout migration
- Document any deviations from expected outputs

**After Completion:**
1. Download commit hash and save for records
2. Report back to @PM with:
   - ✅ Success (all containers running)
   - ⏸️ Partial success (some issues to resolve)
   - ❌ Failure (rollback executed)

**Expected Output:**
- All 3 containers running and healthy
- Bot successfully connected to Gateway
- Single-command startup validated
- Git commit pushed
- Task 3.4 ready to mark complete

---

**Document:** P3-S10_Task_3_4_Migration_Validation_Handoff.md
**Date:** 2026-02-10
**Session:** Task 3.4 Migration & Validation (Path A+)
**Estimated Effort:** 60-90 minutes
