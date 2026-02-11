# Desktop Deployment Notes — Task 4.1

**Date:** 2026-02-10
**Platform:** Windows 11 Pro (Operator's Desktop)
**Deployment Model:** Docker-based (Gateway + Bot + Health Monitor)

---

## Deployment Architecture

### Gateway Configuration
- **Container:** `ibkr-gateway` (gnzsnz/ib-gateway:stable)
- **Container Status:** Running (5+ hours uptime)
- **Health Status:** Healthy
- **Ports:**
  - 4001 → Live trading (not used)
  - 4002 → Paper trading API (mapped to container port 4004 via SOCAT)
  - 5900 → VNC debugging
  - 6080 → noVNC web interface
- **IBC Built-in:** Container image includes IBC Controller
- **Restart Policy:** `unless-stopped` (auto-restart on failure)

### Trading Bot Configuration
- **Container:** `trading-bot`
- **Connection:** `gateway:4004` (Docker network)
- **Dry-Run Mode:** `DRY_RUN=true` (configured in `.env`)
- **Dependencies:** Waits for Gateway health check before starting
- **Restart Policy:** `unless-stopped`

### Health Monitor Configuration
- **Container:** `health-monitor`
- **Discord Webhook:** Configured (credentials in `.env`)
- **Check Interval:** 60 seconds
- **Restart Policy:** `unless-stopped`

---

## Current State Assessment

### ✅ Already Configured
- [x] Gateway running and accessible on localhost:4002
- [x] Docker Compose stack operational (gateway, trading-bot, health-monitor)
- [x] Environment variables configured (`.env` in docker/ directory)
- [x] Discord webhook configured for notifications
- [x] IBKR credentials stored in `.env` (paper trading account)
- [x] Health checks configured and passing
- [x] Log directories created (`bot-logs` volume)

### ⚠️ Needs Configuration (Task 4.1 Deliverables)
- [ ] Docker Desktop auto-start on Windows boot
- [ ] Docker Compose services auto-start at 6:00 AM ET (Task Scheduler)
- [ ] Gateway daily restart scheduled (4:30 PM ET via Task Scheduler)
- [ ] Windows power management configured (prevent sleep during market hours)
- [ ] Deployment validation checklist completed
- [ ] Documentation updated (README_DEPLOYMENT.md)

---

## Deployment Paths

### Project Root
`C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production`

### Docker Compose Directory
`C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker`

### Environment Configuration
`C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker\.env`

### Log Locations
- **Bot Logs:** Docker volume `bot-logs` (accessible via `docker volume inspect bot-logs`)
- **Gateway Logs:** Docker volume `gateway-data`
- **Health Monitor Logs:** Container stdout (view via `docker logs health-monitor`)

---

## Zero-Touch Automation Requirements

### Boot Sequence
1. **Windows boots** → Docker Desktop auto-starts (configure in Docker Desktop settings)
2. **Docker Desktop ready** → Wait 30 seconds for Docker daemon initialization
3. **6:00 AM ET** → Task Scheduler triggers `docker compose up -d` in project directory
4. **Gateway starts** → IBC authenticates with IBKR (2FA may require manual approval)
5. **Bot starts** → Connects to Gateway, sends Discord notification
6. **Health Monitor starts** → Begins monitoring, sends startup notification

### Daily Operations
- **6:00 AM ET:** Bot auto-starts via Task Scheduler
- **9:30 AM ET:** Market opens, bot begins strategy execution (dry-run mode)
- **4:00 PM ET:** Market closes, bot enters idle state
- **4:30 PM ET:** Gateway daily restart (Task Scheduler triggers `docker restart ibkr-gateway`)
- **4:35 PM ET:** Bot reconnects to Gateway automatically
- **Overnight:** Docker containers remain running (unless-stopped policy)

---

## Known Issues & Mitigations

### Issue 1: Docker Desktop Not Auto-Starting
**Symptom:** Services don't start after Windows reboot
**Cause:** Docker Desktop not configured to start on login
**Mitigation:**
1. Open Docker Desktop settings
2. General → Enable "Start Docker Desktop when you log in"
3. Test: Reboot Windows, verify Docker Desktop starts automatically

### Issue 2: 2FA Manual Approval Required
**Symptom:** Gateway fails to authenticate after restart
**Cause:** IBKR requires 2FA approval via mobile app
**Mitigation:**
1. Short-term: Operator receives IBKR mobile notification, approves manually
2. Long-term: Configure "trusted device" in IBKR portal to reduce 2FA frequency
3. Monitor Discord for Gateway health alerts (Health Monitor will detect failure)

### Issue 3: Windows Sleep/Hibernate During Market Hours
**Symptom:** Services stop responding after period of inactivity
**Cause:** Windows power settings put system to sleep
**Mitigation:**
1. Open Windows Power Settings
2. Set "Sleep" to "Never" when plugged in
3. Set "Turn off display" to 30 minutes (but don't sleep system)
4. Test: Leave system idle for 1 hour, verify services still accessible

### Issue 4: Windows Updates Force Reboot
**Symptom:** Unexpected downtime during market hours
**Cause:** Windows automatic updates install and reboot
**Mitigation:**
1. Configure Windows Update to install outside market hours (overnight)
2. Settings → Windows Update → Advanced Options → Active Hours (set 6:00 AM - 6:00 PM ET)
3. Monitor Discord for health alerts if unexpected reboot occurs

### Issue 5: Gateway Memory Leak
**Symptom:** Gateway becomes unresponsive after extended runtime
**Cause:** Known IBKR Gateway memory leak issue
**Mitigation:**
1. Daily Gateway restart at 4:30 PM ET (Task Scheduler, see Phase E)
2. Health Monitor detects unresponsive Gateway, sends Discord alert
3. Operator can manually restart: `docker restart ibkr-gateway`

---

## Rollback Procedure

If deployment fails or creates instability:

### Step 1: Disable Auto-Start
```powershell
# Disable Task Scheduler tasks
Disable-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start"
Disable-ScheduledTask -TaskName "IBKR Gateway - Daily Restart"
```

### Step 2: Stop Running Services
```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
docker compose down
```

### Step 3: Manual Launch for Debugging
```powershell
# Start services manually for testing
docker compose up -d

# View logs in real-time
docker compose logs -f trading-bot
```

### Step 4: Document Failure
- Capture error logs: `docker logs trading-bot > failure_logs.txt`
- Note timestamp and trigger event
- Create GitHub issue with logs and reproduction steps
- Escalate to Boardroom if systemic issue

### Step 5: Re-Enable After Fix Validated
```powershell
# Re-enable Task Scheduler tasks after fix confirmed
Enable-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start"
Enable-ScheduledTask -TaskName "IBKR Gateway - Daily Restart"
```

---

## Security Notes

### Credentials Storage
- **IBKR Username/Password:** Stored in `.env` file (local filesystem only)
- **Discord Webhook URL:** Stored in `.env` file
- **⚠️ CRITICAL:** `.env` file is in `.gitignore` — NEVER commit credentials to repository
- **Backup:** Operator maintains secure backup of `.env` file (password manager or encrypted storage)

### Network Security
- **Gateway Ports:** Bound to 127.0.0.1 only (not exposed to network)
- **Docker Network:** Services communicate via internal `trading-network` (no external access)
- **VNC Access:** Port 5900 bound to localhost only (use SSH tunnel for remote access)

### Access Control
- **Windows User:** Operator's account (Administrator privileges for Docker)
- **Docker Access:** Requires Windows Docker Desktop running
- **IBKR Account:** Paper trading account only (Task 4.1 dry-run deployment)

---

## Next Steps (Task 4.2+)

After Task 4.1 validation complete:
1. **Task 4.2:** Transition to live paper trading (`DRY_RUN=false`)
2. **Task 4.3:** Implement Strategy A/B execution with live market data
3. **Task 4.4:** Monitor performance metrics for 5-7 trading days
4. **Task 4.5:** Evaluate Raspberry Pi migration (if desktop unstable)

---

**Last Updated:** 2026-02-10
**Operator:** @tasms
**Status:** In Progress (Phase B-G)
