# IBKR Trading Bot — Desktop Deployment (Task 4.1)

**Platform:** Windows 11 Pro
**Deployment Mode:** Docker Compose (Gateway + Bot + Health Monitor)
**Status:** Task 4.1 — Initial Deployment & Validation
**Date:** 2026-02-10

---

## Quick Start (Operator)

### Prerequisites
- ✅ Docker Desktop installed and running
- ✅ IBKR Paper Trading account credentials
- ✅ Discord webhook configured
- ✅ Windows 11 Pro with Administrator access

### Initial Setup (One-Time)

1. **Configure Docker Desktop Auto-Start:**
   - Open Docker Desktop → Settings → General
   - Enable "Start Docker Desktop when you log in"
   - Apply & Restart

2. **Verify Environment Configuration:**
   ```powershell
   cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
   Get-Content .env | Select-String -Pattern "DRY_RUN|IBKR_USERNAME|DISCORD_WEBHOOK"
   ```
   - Verify `DRY_RUN=true` is set
   - Verify IBKR credentials are present
   - Verify Discord webhook URL is configured

3. **Import Task Scheduler Tasks:**
   - Follow detailed instructions in: `deployment/windows/TASK_SCHEDULER_SETUP_GUIDE.md`
   - Import `task_scheduler_startup.xml` (6:00 AM ET auto-start)
   - Import `task_scheduler_gateway_restart.xml` (4:30 PM ET daily restart)

4. **Test Manual Startup:**
   ```powershell
   # Ensure services are stopped
   docker compose down

   # Run startup script manually
   PowerShell.exe -ExecutionPolicy Bypass -File "deployment\windows\startup_script.ps1"

   # Verify services running
   docker ps
   ```

5. **Verify Discord Notifications:**
   - Check Discord for bot startup notification
   - Confirm DRY-RUN mode is active

---

## Daily Operations (Zero-Touch)

### Automated Schedule

| Time | Event | Description |
|------|-------|-------------|
| 6:00 AM ET | **Bot Auto-Start** | Task Scheduler launches Docker Compose services |
| 9:30 AM ET | **Market Open** | Bot begins monitoring market signals (DRY-RUN) |
| 4:00 PM ET | **Market Close** | Bot enters idle state (no active strategies) |
| 4:30 PM ET | **Gateway Restart** | Task Scheduler restarts Gateway (memory leak mitigation) |
| Overnight | **Services Running** | Docker Compose `unless-stopped` keeps services alive |

### Operator Intervention (Minimal)

**Normal Days:**
- No intervention required — fully automated
- Monitor Discord for health alerts

**2FA Required:**
- IBKR may prompt for 2FA approval on first Gateway start after reboot
- Approve via IBKR mobile app notification
- Frequency: Varies (typically once per week if "trusted device" configured)

**After Windows Updates:**
- System may reboot overnight
- Docker Desktop auto-starts on login
- Task Scheduler launches bot at next 6:00 AM ET

---

## File Structure

```
ibkr-trading-bot-production/
├── deployment/
│   └── windows/
│       ├── deployment_notes.md                    # Deployment state documentation
│       ├── startup_script.ps1                     # Bot auto-start script (6:00 AM ET)
│       ├── gateway_restart_script.ps1             # Gateway daily restart (4:30 PM ET)
│       ├── task_scheduler_startup.xml             # Task Scheduler import (auto-start)
│       ├── task_scheduler_gateway_restart.xml     # Task Scheduler import (restart)
│       └── TASK_SCHEDULER_SETUP_GUIDE.md          # Step-by-step setup instructions
├── docker/
│   ├── docker-compose.yml                         # Service orchestration
│   ├── .env                                       # Environment variables (credentials)
│   └── data/                                      # Gameplan JSON files
├── logs/
│   ├── startup_YYYYMMDD.log                       # Auto-start execution logs
│   └── gateway_restart_YYYYMMDD.log               # Gateway restart logs
├── src/                                           # Bot source code
└── README_DEPLOYMENT.md                           # This file
```

---

## Health Monitoring

### Discord Notifications

Bot sends notifications for:
- ✅ **Startup Success** — Bot auto-started, services healthy
- ⚠️ **Startup Warning** — Docker slow to start, services delayed
- ❌ **Startup Failure** — Critical error, operator intervention required
- 🔄 **Gateway Restart** — Daily 4:30 PM restart initiated
- ✅ **Gateway Restart Complete** — Gateway healthy, bot reconnected
- 🚨 **Gateway Unhealthy** — Memory threshold exceeded, connection lost

### Log Monitoring

Real-time log tailing:

```powershell
# Bot logs (Docker container)
docker logs trading-bot -f

# Gateway logs
docker logs ibkr-gateway -f

# Health Monitor logs
docker logs health-monitor -f

# Startup script logs (today's date)
Get-Content "logs\startup_$(Get-Date -Format 'yyyyMMdd').log" -Wait

# Gateway restart logs
Get-Content "logs\gateway_restart_$(Get-Date -Format 'yyyyMMdd').log" -Wait
```

---

## Manual Operations

### Start Services Manually

```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
docker compose up -d
docker ps  # Verify all 3 services running
```

### Stop Services

```powershell
docker compose down
```

### Restart Services

```powershell
docker compose restart
```

### Restart Gateway Only (Memory Leak Mitigation)

```powershell
docker restart ibkr-gateway

# Wait 30-60 seconds, then verify health
docker inspect ibkr-gateway --format='{{.State.Health.Status}}'
# Expected: "healthy"
```

### View Service Status

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected output:
```
NAMES            STATUS                    PORTS
health-monitor   Up X hours
trading-bot      Up X hours
ibkr-gateway     Up X hours (healthy)      127.0.0.1:4001->4001/tcp, ...
```

---

## Configuration Management

### Update Environment Variables

1. Edit `.env` file:
   ```powershell
   cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
   notepad .env
   ```

2. Restart services to apply changes:
   ```powershell
   docker compose down
   docker compose up -d
   ```

### Critical Settings (Task 4.1)

**DO NOT CHANGE during Task 4.1 validation:**
- `DRY_RUN=true` — Must remain true until Task 4.2
- `IBKR_USERNAME` / `IBKR_PASSWORD` — Paper trading credentials
- `GATEWAY_HOST=ibkr-gateway` — Docker network communication

**Safe to Modify:**
- `DISCORD_WEBHOOK_URL` — If webhook changed or recreated
- `LOG_LEVEL` — Adjust verbosity (DEBUG, INFO, WARNING, ERROR)
- `HEALTH_CHECK_INTERVAL_SECONDS` — Adjust monitoring frequency

---

## Troubleshooting

### Services Won't Start

**Check Docker Desktop:**
```powershell
docker info
```
If error: Start Docker Desktop manually, wait 30 seconds, retry.

**Check Docker Compose Configuration:**
```powershell
cd docker
docker compose config
```
Verify no syntax errors in `docker-compose.yml` or `.env`.

### Gateway Unhealthy

**Check Gateway Health:**
```powershell
docker exec ibkr-gateway curl -s http://localhost:4004
```
Expected: Response with no errors.

**Check Gateway Logs:**
```powershell
docker logs ibkr-gateway --tail 50
```
Look for authentication errors, 2FA prompts, or API errors.

**Manual Restart:**
```powershell
docker restart ibkr-gateway
```

### Bot Won't Connect to Gateway

**Verify Gateway Port:**
```powershell
Test-NetConnection -ComputerName localhost -Port 4002
```
Expected: `TcpTestSucceeded: True`

**Check Bot Logs:**
```powershell
docker logs trading-bot --tail 50
```
Look for connection errors, authentication failures, or timeout messages.

### Discord Notifications Not Received

**Test Webhook Manually:**
```powershell
$WebhookUrl = "YOUR_WEBHOOK_URL"  # From .env file
$Payload = @{ content = "Test from PowerShell" } | ConvertTo-Json
Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $Payload -ContentType "application/json"
```

Check Discord for test message. If no message:
- Verify webhook URL in `.env` is correct
- Check webhook still exists in Discord (Server Settings → Integrations)
- Verify no firewall/antivirus blocking outbound HTTPS

### Task Scheduler Not Executing

**Check Task Status:**
```powershell
Get-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start" | Select-Object State, LastRunTime, LastTaskResult, NextRunTime
```

Expected:
- `State: Ready`
- `LastTaskResult: 0` (success)
- `NextRunTime: <future date>`

**Check Task Execution History:**
1. Open Task Scheduler (`taskschd.msc`)
2. Navigate to task: `IBKR Trading Bot - Auto-Start`
3. View **History** tab (enable if disabled)
4. Look for errors or failures

**Run Task Manually:**
1. Right-click task → **Run**
2. Monitor logs: `logs\startup_YYYYMMDD.log`

---

## Security Notes

### Credentials Storage

- **IBKR Username/Password:** Stored in `docker/.env` (local filesystem only)
- **Discord Webhook URL:** Stored in `docker/.env`
- **⚠️ CRITICAL:** `.env` file is in `.gitignore` — NEVER commit credentials to repository
- **Backup:** Maintain secure backup of `.env` file (password manager or encrypted storage)

### Network Exposure

- **Gateway Ports:** Bound to `127.0.0.1` only (not exposed to network)
- **Docker Network:** Services communicate via internal `trading-network`
- **VNC Access:** Port 5900 bound to localhost (use SSH tunnel for remote access)

### Access Control

- **Windows User:** Administrator privileges required for Docker and Task Scheduler
- **Docker Access:** Requires Docker Desktop running
- **IBKR Account:** Paper trading account only (Task 4.1)

---

## Rollback Plan

If deployment fails or creates instability:

### Step 1: Disable Auto-Start
```powershell
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
docker compose up -d
docker compose logs -f trading-bot
```

### Step 4: Re-Enable After Fix Validated
```powershell
Enable-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start"
Enable-ScheduledTask -TaskName "IBKR Gateway - Daily Restart"
```

---

## Next Steps (After Task 4.1)

1. **Task 4.2:** Transition to live paper trading (`DRY_RUN=false`)
2. **Task 4.3:** Implement Strategy A/B execution with live market data
3. **Task 4.4:** Monitor performance metrics for 5-7 trading days
4. **Task 4.5:** Evaluate Raspberry Pi migration (if desktop proves unstable)

---

## Support & Documentation

- **Task Scheduler Setup:** `deployment/windows/TASK_SCHEDULER_SETUP_GUIDE.md`
- **Deployment Notes:** `deployment/windows/deployment_notes.md`
- **Docker Configuration:** `docker/docker-compose.yml`, `docker/.env`
- **Project Documentation:** `docs/` directory

---

**Last Updated:** 2026-02-10
**Operator:** @tasms
**Status:** Task 4.1 — Deployment Configuration Complete, Awaiting Validation
