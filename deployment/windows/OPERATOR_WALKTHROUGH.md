# Task 4.1 Validation — Interactive Operator Walkthrough

**Date:** 2026-02-10
**Estimated Time:** 1-2 hours (includes testing and waiting)
**Current Status:** Services running, Task Scheduler setup needed

---

## ✅ Quick Status Check

Before starting, verify baseline:

```powershell
# Check Docker services (should see 3 containers)
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check Discord webhook works
$WebhookUrl = (Get-Content docker\.env | Select-String "DISCORD_WEBHOOK_URL").Line.Split('=')[1]
$Payload = @{ content = "🚀 Task 4.1 Validation Starting — Testing webhook" } | ConvertTo-Json
Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $Payload -ContentType "application/json"
```

**Expected Results:**
- ✅ 3 containers running: `ibkr-gateway`, `trading-bot`, `health-monitor`
- ✅ Discord message received: "🚀 Task 4.1 Validation Starting"

---

## 📋 Phase 1: Docker Desktop Auto-Start (2 minutes)

### Step 1.1: Configure Docker Desktop

1. **Locate Docker Desktop icon** in system tray (bottom-right corner)
2. **Right-click** Docker icon → **Settings**
3. Navigate to **General** tab
4. Find setting: **"Start Docker Desktop when you log in"**
5. ✅ **Enable** this checkbox
6. Click **"Apply & Restart"**
7. Wait 30 seconds for Docker to restart

### Step 1.2: Verify Services Restarted

After Docker Desktop restarts:

```powershell
# Wait 30-60 seconds, then check services
docker ps

# Expected: All 3 services running again
# - ibkr-gateway (Status: Up X seconds)
# - trading-bot (Status: Up X seconds)
# - health-monitor (Status: Up X seconds)
```

**✅ Phase 1 Complete if:**
- Docker Desktop setting enabled
- All 3 services running after restart

---

## 📋 Phase 2: Task Scheduler Setup (20-30 minutes)

### Step 2.1: Open Task Scheduler

```powershell
# Open Task Scheduler
taskschd.msc
```

Or: Press **Windows + R**, type `taskschd.msc`, press Enter

### Step 2.2: Import Auto-Start Task

1. In Task Scheduler, click **Action** menu (top)
2. Click **Import Task...**
3. Navigate to:
   ```
   C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\deployment\windows\task_scheduler_startup.xml
   ```
4. Click **Open**

#### Review Task Settings

Task Scheduler loads the task definition. You should see:

- **Name:** `IBKR Trading Bot - Auto-Start`
- **Trigger:** Daily at 6:00 AM
- **Action:** Run PowerShell script `startup_script.ps1`

#### Security Options for Microsoft Accounts

**⚠️ Important for Microsoft Accounts:**
If you're using a Microsoft account (not a local Windows account), the task will show:
- Security option: **"Run only when user is logged on"** (no password required)

This is correct! Microsoft accounts work best with this setting. The task will run automatically as long as you're logged into Windows.

#### Save Task

1. Click **OK** (bottom right)
2. **For Microsoft accounts:** Task saves immediately (no password prompt)
3. **For local accounts:** Windows Security prompt appears — enter your Windows password
4. Task now appears in Task Scheduler list

**⚠️ Troubleshooting:** If you get "Access Denied":
- Right-click Task Scheduler → "Run as Administrator"
- Try importing again

### Step 2.3: Import Gateway Restart Task

Repeat the import process for Gateway restart:

1. Click **Action** → **Import Task...**
2. Navigate to:
   ```
   C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\deployment\windows\task_scheduler_gateway_restart.xml
   ```
3. Click **Open**
4. Review settings (Name: `IBKR Gateway - Daily Restart`, Trigger: Daily at 4:30 PM)
5. Click **OK**
6. **For Microsoft accounts:** Saves immediately (no password prompt)
7. **For local accounts:** Enter Windows password when prompted, then click **OK**

### Step 2.4: Verify Both Tasks Imported

```powershell
# Check both tasks exist and are enabled
Get-ScheduledTask -TaskName "*IBKR*" | Select-Object TaskName, State

# Expected output:
# TaskName                          State
# --------                          -----
# IBKR Trading Bot - Auto-Start     Ready
# IBKR Gateway - Daily Restart      Ready
```

**✅ Phase 2 Complete if:**
- Both tasks show `State: Ready`
- Both tasks visible in Task Scheduler UI

---

## 📋 Phase 3: System Configuration (10 minutes)

### Step 3.1: Power Settings

1. Open **Settings** (Windows + I)
2. Navigate to **System** → **Power & sleep**
3. When plugged in, PC goes to sleep after: **Never**
4. When plugged in, turn off display after: **30 minutes** (optional)

### Step 3.2: Active Hours (Prevent Updates During Trading)

1. Open **Settings** → **Windows Update**
2. Click **Advanced options**
3. Scroll down to **Active hours**
4. Click **Active hours**
5. Set custom active hours:
   - **Start time:** 6:00 AM
   - **End time:** 6:00 PM
6. Click **Save**

### Step 3.3: Verify Power Configuration

```powershell
# Check power settings (should show no sleep on AC power)
powercfg /query | Select-String -Pattern "Sleep"

# Expected: Standby timeout shows 0 (never) when plugged in
```

**✅ Phase 3 Complete if:**
- Sleep set to "Never" when plugged in
- Active hours: 6:00 AM - 6:00 PM

---

## 📋 Phase 4: Manual Testing (30-45 minutes)

### Test 1: Bot Auto-Start (Manual Trigger)

#### Step 4.1: Stop Services

```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
docker compose down

# Verify all stopped
docker ps
# Expected: ibkr-gateway, trading-bot, health-monitor NOT in list
```

#### Step 4.2: Run Auto-Start Task Manually

1. Open Task Scheduler
2. Find task: **IBKR Trading Bot - Auto-Start**
3. **Right-click** → **Run**
4. Watch Task Status in bottom panel (shows "Running")
5. Wait 1-2 minutes for task to complete

#### Step 4.3: Verify Startup Succeeded

```powershell
# Check services restarted
docker ps

# Expected: All 3 services running
# - ibkr-gateway (Status: Up <1 minute)
# - trading-bot (Status: Up <1 minute)
# - health-monitor (Status: Up <1 minute)

# Check startup logs
Get-Content "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\logs\startup_$(Get-Date -Format 'yyyyMMdd').log"

# Expected log entries:
# - "Docker Desktop is running"
# - "Docker Compose services started successfully"
# - "Gateway health status: healthy"
# - "Discord notification sent successfully"
```

#### Step 4.4: Verify Discord Notification

Check Discord channel — you should see:

**🤖 IBKR Trading Bot - Startup**

> **Startup Successful** ✅
>
> **Services Status:**
> - Gateway: healthy
> - Trading Bot: running
> - Health Monitor: running
>
> **Configuration:**
> - Mode: DRY-RUN (Task 4.1 validation)
> - Platform: Windows 11 Desktop
> - Startup Time: 2026-02-10 HH:MM:SS ET
>
> Bot is operational. Monitoring active.

**✅ Test 1 Complete if:**
- All 3 services restarted
- Startup log shows no errors
- Discord notification received
- Task Scheduler shows "Last Run Result: The operation completed successfully. (0x0)"

---

### Test 2: Gateway Restart (Manual Trigger)

**⚠️ Important:** Only test this **outside market hours** (after 4:00 PM ET)

#### Step 4.5: Run Gateway Restart Task

1. In Task Scheduler, find task: **IBKR Gateway - Daily Restart**
2. **Right-click** → **Run**
3. Watch Task Status (shows "Running")
4. Wait 2-3 minutes for Gateway to restart and become healthy

#### Step 4.6: Verify Gateway Restarted

```powershell
# Check Gateway uptime (should be recent)
docker ps --filter "name=ibkr-gateway" --format "{{.Names}}\t{{.Status}}"

# Expected: ibkr-gateway Up 1-3 minutes (healthy)

# Check Gateway health
docker inspect ibkr-gateway --format='{{.State.Health.Status}}'
# Expected: healthy

# Check bot reconnected
docker logs trading-bot --tail 20
# Look for recent connection logs (timestamps within last 3 minutes)
```

#### Step 4.7: Check Gateway Restart Logs

```powershell
Get-Content "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\logs\gateway_restart_$(Get-Date -Format 'yyyyMMdd').log"

# Expected log entries:
# - "Gateway restart command completed successfully"
# - "Gateway is healthy and ready"
# - "Trading Bot status after Gateway restart: running"
# - "Discord notification sent successfully"
```

#### Step 4.8: Verify Discord Notification

Check Discord — you should see:

**🔄 IBKR Gateway - Daily Restart**

> **Gateway Restart Complete** ✅
>
> **Post-Restart Status:**
> - Gateway: healthy
> - Trading Bot: running
>
> **Restart Time:** 2026-02-10 HH:MM:SS ET
>
> Bot reconnection verified. System operational for next trading day.

**✅ Test 2 Complete if:**
- Gateway restarted successfully
- Gateway health check passed
- Trading Bot reconnected automatically (no manual intervention)
- Discord notification received
- Task Scheduler shows "Last Run Result: (0x0)"

---

## 📋 Phase 5: Full System Test (Reboot)

### Step 5.1: Pre-Reboot Checklist

Before rebooting, verify:

```powershell
# Check both tasks are Ready
Get-ScheduledTask -TaskName "*IBKR*" | Select-Object TaskName, State

# Check next scheduled run times
Get-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start" | Get-ScheduledTaskInfo | Select-Object NextRunTime
Get-ScheduledTask -TaskName "IBKR Gateway - Daily Restart" | Get-ScheduledTaskInfo | Select-Object NextRunTime

# Expected:
# - Auto-Start NextRunTime: Tomorrow 6:00 AM
# - Gateway Restart NextRunTime: Today or Tomorrow 4:30 PM
```

### Step 5.2: Reboot Windows

```powershell
# Save all work, close apps, then reboot
Restart-Computer
```

### Step 5.3: Post-Reboot Verification (After Login)

**Wait 1-2 minutes** after logging in, then:

```powershell
# 1. Verify Docker Desktop auto-started
# Look for Docker icon in system tray (should be visible)

# 2. Test Docker daemon
docker info
# Expected: No errors, Docker daemon accessible

# 3. Check services (may auto-start due to "unless-stopped" policy)
docker ps

# Expected: Services may be running OR stopped (Task Scheduler will start at 6 AM)
# If stopped, that's normal — they'll auto-start at next 6:00 AM ET

# 4. Verify Task Scheduler tasks survived reboot
Get-ScheduledTask -TaskName "*IBKR*" | Select-Object TaskName, State

# Expected: Both tasks still show "Ready" state
```

**✅ Phase 5 Complete if:**
- Docker Desktop auto-started after reboot
- Task Scheduler tasks still enabled (State: Ready)
- No errors accessing Docker daemon

---

## 📋 Phase 6: Live Validation (Wait for Scheduled Run)

### Option A: Wait for Actual 6:00 AM Trigger (Recommended)

**Next morning at 6:00 AM ET:**

1. Check Discord for startup notification (should arrive within 2 minutes of 6:00 AM)
2. Verify services running:
   ```powershell
   docker ps
   ```
3. Check startup logs:
   ```powershell
   Get-Content "logs\startup_$(Get-Date -Format 'yyyyMMdd').log"
   ```

### Option B: Test Immediately (Adjust Trigger Time)

If you can't wait until tomorrow morning:

1. Open Task Scheduler
2. Right-click **IBKR Trading Bot - Auto-Start** → **Properties**
3. Go to **Triggers** tab
4. Double-click the daily trigger
5. Change start time to **current time + 2 minutes**
6. Click **OK** → **OK**
7. Stop services manually:
   ```powershell
   docker compose down
   ```
8. Wait for trigger time
9. Verify services auto-start and Discord notification received
10. **IMPORTANT:** Reset trigger back to **6:00 AM** after test

---

## 📋 Phase 7: Final Validation Checklist

Work through the comprehensive checklist:

```
deployment/windows/DEPLOYMENT_VALIDATION_CHECKLIST.md
```

**Use this command to track progress:**

```powershell
# Open checklist in VS Code
code deployment\windows\DEPLOYMENT_VALIDATION_CHECKLIST.md
```

**Key items to verify:**

- [ ] Docker Desktop auto-starts on boot
- [ ] Bot auto-starts at 6:00 AM ET (tested manually OR actual scheduled run)
- [ ] Gateway restarts at 4:30 PM ET (tested manually outside market hours)
- [ ] Bot reconnects after Gateway restart (zero-touch, no manual intervention)
- [ ] Discord notifications working (startup + restart)
- [ ] `DRY_RUN=true` confirmed in logs
- [ ] No actual orders in IBKR portal (verify paper account shows no new trades)
- [ ] All deployment docs committed to Git

---

## ✅ Task 4.1 Complete — Declaration

When **ALL** checklist items are complete, post to Discord:

```
🎉 Task 4.1: Desktop Deployment — OPERATIONAL

**Validation Complete:**
✅ Docker Desktop auto-start configured and tested
✅ Task Scheduler tasks imported and tested (manual runs successful)
✅ Bot auto-start at 6:00 AM ET verified
✅ Gateway restart at 4:30 PM ET verified
✅ Bot handles Gateway restart gracefully (zero-touch reconnection)
✅ Discord notifications operational
✅ DRY_RUN mode active (no actual trades)
✅ Full system test (reboot) passed
✅ All deployment documentation complete

**System Status:**
- Platform: Windows 11 Desktop
- Services: All healthy
- Mode: DRY-RUN (Task 4.1 validation phase)

**Ready for Task 4.2** — Live Paper Trading Transition
```

---

## Troubleshooting Quick Reference

### Task Scheduler task fails

```powershell
# Check task history for errors
# In Task Scheduler UI: Select task → History tab (enable if disabled)

# Check execution policy
Get-ExecutionPolicy
# If "Restricted", run as Admin:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

### Docker not accessible

```powershell
# Restart Docker Desktop manually
# System tray → Right-click Docker → Restart Docker Desktop

# Wait 30-60 seconds, then test
docker info
```

### Discord webhook not working

```powershell
# Test webhook manually
$WebhookUrl = (Get-Content docker\.env | Select-String "DISCORD_WEBHOOK_URL").Line.Split('=')[1]
$Payload = @{ content = "Manual test message" } | ConvertTo-Json
Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $Payload -ContentType "application/json"

# If fails: Check webhook URL in Discord settings (Server → Integrations → Webhooks)
```

### Services won't start

```powershell
# Check Docker Compose config
cd docker
docker compose config

# Check container logs for errors
docker logs ibkr-gateway
docker logs trading-bot
docker logs health-monitor

# Nuclear option: Full restart
docker compose down
docker compose up -d
```

---

**Estimated Total Time:** 1-2 hours
**Current Status:** Ready to begin Phase 1
**Next Action:** Configure Docker Desktop auto-start
