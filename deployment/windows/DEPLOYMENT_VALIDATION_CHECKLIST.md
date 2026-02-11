# Deployment Validation Checklist — Task 4.1

**Date:** 2026-02-10
**Task:** 4.1 — Desktop Deployment (Interim Production Platform)
**Operator:** @tasms
**Status:** Awaiting Operator Validation

---

## Purpose

This checklist ensures all Task 4.1 deliverables are complete and the desktop deployment is operational for zero-touch automation. Operator must verify each item before declaring Task 4.1 complete.

---

## Pre-Deployment Configuration

### ✅ Environment Setup

- [ ] **Docker Desktop installed and running**
  - Version: Docker Desktop 4.x or later
  - Docker daemon accessible: `docker info` returns no errors

- [ ] **Docker Desktop auto-start enabled**
  - Settings → General → "Start Docker Desktop when you log in" ✅
  - Tested: Reboot Windows, verify Docker Desktop starts automatically

- [ ] **Repository cloned and up-to-date**
  - Location: `C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production`
  - Git status: On branch `main`, no uncommitted changes
  - Latest commit includes Task 4.1 deployment files

- [ ] **Poetry environment configured**
  - Poetry version: 2.3.2 or later (`poetry --version`)
  - Python version: 3.13.1 (`poetry env info`)
  - Dependencies installed: `poetry install` completed without errors

- [ ] **Logs directory created**
  - Path: `C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\logs`
  - Permissions: Write access for operator user

---

### ✅ Environment Variables (.env)

- [ ] **`.env` file exists**
  - Location: `C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker\.env`
  - Not committed to Git (verify in `.gitignore`)

- [ ] **Critical settings configured:**
  ```powershell
  cd docker
  Get-Content .env | Select-String -Pattern "DRY_RUN|IBKR_USERNAME|IBKR_PASSWORD|DISCORD_WEBHOOK_URL|GATEWAY_HOST|GATEWAY_PORT"
  ```
  - ✅ `DRY_RUN=true` (CRITICAL for Task 4.1)
  - ✅ `IBKR_USERNAME=<paper_trading_username>`
  - ✅ `IBKR_PASSWORD=<paper_trading_password>`
  - ✅ `DISCORD_WEBHOOK_URL=<valid_webhook_url>`
  - ✅ `GATEWAY_HOST=ibkr-gateway`
  - ✅ `GATEWAY_PORT=4002`

- [ ] **Discord webhook tested**
  ```powershell
  $WebhookUrl = "<WEBHOOK_URL_FROM_ENV>"
  $Payload = @{ content = "Test from Task 4.1 validation" } | ConvertTo-Json
  Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $Payload -ContentType "application/json"
  ```
  - ✅ Test message received in Discord channel

---

### ✅ Docker Compose Services

- [ ] **Docker Compose configuration validated**
  ```powershell
  cd docker
  docker compose config
  ```
  - No syntax errors
  - All services defined: `gateway`, `trading-bot`, `health-monitor`

- [ ] **Services start successfully (manual test)**
  ```powershell
  docker compose down
  docker compose up -d
  docker ps
  ```
  - ✅ `ibkr-gateway` — Status: Running, Health: healthy
  - ✅ `trading-bot` — Status: Running
  - ✅ `health-monitor` — Status: Running
  - All services started within 2 minutes

- [ ] **Gateway connectivity verified**
  ```powershell
  Test-NetConnection -ComputerName localhost -Port 4002
  ```
  - ✅ `TcpTestSucceeded: True`

- [ ] **Gateway health check passes**
  ```powershell
  docker inspect ibkr-gateway --format='{{.State.Health.Status}}'
  ```
  - ✅ Health status: `healthy`

---

## Deployment Files Created

- [ ] **`deployment/windows/deployment_notes.md`** — Deployment state documentation
- [ ] **`deployment/windows/startup_script.ps1`** — Bot auto-start script (6:00 AM ET)
- [ ] **`deployment/windows/gateway_restart_script.ps1`** — Gateway daily restart (4:30 PM ET)
- [ ] **`deployment/windows/task_scheduler_startup.xml`** — Task Scheduler import template (auto-start)
- [ ] **`deployment/windows/task_scheduler_gateway_restart.xml`** — Task Scheduler import template (restart)
- [ ] **`deployment/windows/TASK_SCHEDULER_SETUP_GUIDE.md`** — Step-by-step setup instructions
- [ ] **`README_DEPLOYMENT.md`** — Deployment README for operator

---

## Task Scheduler Configuration

### ✅ Task 1: Bot Auto-Start (6:00 AM ET)

- [ ] **Task imported from XML**
  - File: `deployment/windows/task_scheduler_startup.xml`
  - Method: Task Scheduler → Action → Import Task

- [ ] **Task settings verified:**
  - Name: `IBKR Trading Bot - Auto-Start`
  - Trigger: Daily at 6:00 AM ET
  - Action: Run PowerShell script `startup_script.ps1`
  - Security: "Run whether user is logged on or not", "Run with highest privileges"
  - Conditions: Power settings configured (no AC-only restriction, wake to run enabled)

- [ ] **Task credentials set:**
  - Windows password entered during task creation
  - Task shows "Ready" state in Task Scheduler

- [ ] **Manual test executed:**
  ```powershell
  # Stop services first
  cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
  docker compose down

  # Manually trigger task via Task Scheduler UI (Right-click → Run)
  ```
  - ✅ Task Status: "Running" during execution
  - ✅ Task completes with exit code 0 (success)
  - ✅ Services started: `docker ps` shows all 3 containers
  - ✅ Discord notification received: "Bot started in DRY-RUN mode"

- [ ] **Startup logs reviewed:**
  ```powershell
  Get-Content "logs\startup_$(Get-Date -Format 'yyyyMMdd').log"
  ```
  - ✅ Docker Desktop detected as running
  - ✅ Docker Compose services started successfully
  - ✅ Gateway health check passed
  - ✅ Discord notification sent
  - ✅ No errors or warnings (or errors resolved)

- [ ] **Next scheduled run confirmed:**
  ```powershell
  Get-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start" | Get-ScheduledTaskInfo | Select-Object NextRunTime
  ```
  - ✅ NextRunTime: Tomorrow at 6:00 AM ET (or as configured)

---

### ✅ Task 2: Gateway Daily Restart (4:30 PM ET)

- [ ] **Task imported from XML**
  - File: `deployment/windows/task_scheduler_gateway_restart.xml`
  - Method: Task Scheduler → Action → Import Task

- [ ] **Task settings verified:**
  - Name: `IBKR Gateway - Daily Restart`
  - Trigger: Daily at 4:30 PM ET
  - Action: Run PowerShell script `gateway_restart_script.ps1`
  - Security: "Run whether user is logged on or not", "Run with highest privileges"

- [ ] **Manual test executed (outside market hours):**
  ```powershell
  # Manually trigger task via Task Scheduler UI (Right-click → Run)
  ```
  - ✅ Task Status: "Running" during execution
  - ✅ Task completes with exit code 0 (success)
  - ✅ Gateway restarted: `docker ps` shows recent uptime for `ibkr-gateway`
  - ✅ Gateway health check passed after restart
  - ✅ Discord notification received: "Gateway restart complete"

- [ ] **Gateway restart logs reviewed:**
  ```powershell
  Get-Content "logs\gateway_restart_$(Get-Date -Format 'yyyyMMdd').log"
  ```
  - ✅ Gateway container found and restarted
  - ✅ Gateway became healthy within 2 minutes
  - ✅ Trading Bot reconnected automatically
  - ✅ Discord notification sent
  - ✅ No errors or warnings

- [ ] **Next scheduled run confirmed:**
  ```powershell
  Get-ScheduledTask -TaskName "IBKR Gateway - Daily Restart" | Get-ScheduledTaskInfo | Select-Object NextRunTime
  ```
  - ✅ NextRunTime: Today or tomorrow at 4:30 PM ET

---

## Windows System Configuration

- [ ] **Power settings configured (no sleep during market hours):**
  - Settings → System → Power & sleep
  - Sleep (when plugged in): **Never**
  - Display (when plugged in): 30 minutes or Never

- [ ] **Active hours set (prevent updates during market hours):**
  - Settings → Windows Update → Advanced Options → Active Hours
  - Active hours: **6:00 AM - 6:00 PM ET**

- [ ] **Windows Update deferred (if applicable):**
  - Automatic updates scheduled outside market hours (overnight preferred)

---

## Full System Test (Reboot)

- [ ] **Pre-reboot preparations:**
  - All configuration complete
  - Task Scheduler tasks tested manually
  - Docker Compose services operational

- [ ] **Reboot executed:**
  ```powershell
  Restart-Computer
  ```

- [ ] **Post-reboot verification (within 2-3 minutes of login):**
  - ✅ Docker Desktop auto-started (system tray icon visible)
  - ✅ Docker daemon accessible: `docker info` returns no errors
  - ✅ Services running (if kept alive by `unless-stopped` policy):
    ```powershell
    docker ps
    ```
    - ✅ `ibkr-gateway` running and healthy
    - ✅ `trading-bot` running
    - ✅ `health-monitor` running

- [ ] **Task Scheduler tasks enabled after reboot:**
  ```powershell
  Get-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start" | Select-Object State, NextRunTime
  Get-ScheduledTask -TaskName "IBKR Gateway - Daily Restart" | Select-Object State, NextRunTime
  ```
  - ✅ Both tasks show `State: Ready`
  - ✅ Both tasks show valid `NextRunTime`

---

## Live Validation (Next Scheduled Run)

- [ ] **Wait for actual scheduled run at 6:00 AM ET:**
  - Monitor Discord at 6:00 AM ET for startup notification
  - If not testing at actual time, temporarily adjust trigger to current time + 2 minutes

- [ ] **Verify auto-start executed at scheduled time:**
  - ✅ Discord notification received at 6:00 AM ET (or adjusted time)
  - ✅ Services running: `docker ps`
  - ✅ Startup logs created: `logs\startup_YYYYMMDD.log`
  - ✅ No errors in startup logs

- [ ] **Verify Gateway restart at 4:30 PM ET:**
  - Monitor Discord at 4:30 PM ET for restart notification
  - ✅ Discord notification received at 4:30 PM ET
  - ✅ Gateway restarted successfully
  - ✅ Trading Bot reconnected automatically
  - ✅ No errors in restart logs

---

## Definition of Done (Task 4.1)

Task 4.1 is **COMPLETE** when all of the following are verified:

### ✅ Automated Operation Verified

- [ ] **Bot auto-starts at 6:00 AM ET via Task Scheduler**
  - Manual test passed (task runs without errors)
  - Actual scheduled run at 6:00 AM ET confirmed (wait for next morning, or adjust trigger for immediate test)

- [ ] **Bot connects to Gateway successfully and logs initialization**
  - Docker logs show bot connected: `docker logs trading-bot`
  - No connection errors or authentication failures

- [ ] **Discord notification received on bot startup**
  - Notification includes: timestamp, mode (DRY-RUN), services status
  - Notification received within 2 minutes of startup

- [ ] **Gateway restarts at 4:30 PM ET via Task Scheduler**
  - Manual test passed (task runs without errors)
  - Actual scheduled run at 4:30 PM ET confirmed (wait for scheduled time, or test manually outside market hours)

- [ ] **Bot handles Gateway restart gracefully (reconnects without manual intervention)**
  - Bot logs show reconnection attempt after Gateway restart
  - Bot reconnects within 2 minutes of Gateway becoming healthy
  - No manual intervention required

### ✅ Configuration Validated

- [ ] **`DRY_RUN=true` mode verified in logs**
  - Bot logs confirm dry-run mode active
  - Search logs for "DRY_RUN" or "dry-run mode" confirmation

- [ ] **No actual orders sent to IBKR**
  - Check IBKR portal (Paper Trading account) — no new orders or positions
  - Bot logs show strategy signals generated but not submitted

- [ ] **Log rotation functioning correctly (logs do not exceed 100 MB total)**
  - Check log file sizes: `Get-ChildItem logs\ | Measure-Object -Property Length -Sum`
  - Verify total < 100 MB (or log rotation configured)

### ✅ Documentation Complete

- [ ] **`deployment/windows/` directory contains all required files:**
  - `deployment_notes.md`
  - `startup_script.ps1`
  - `gateway_restart_script.ps1`
  - `task_scheduler_startup.xml`
  - `task_scheduler_gateway_restart.xml`
  - `TASK_SCHEDULER_SETUP_GUIDE.md`

- [ ] **`README_DEPLOYMENT.md` created in project root**
  - Contains quick start guide
  - Contains daily operations schedule
  - Contains troubleshooting section

- [ ] **Task 4.1 deployment files committed to Git:**
  ```powershell
  git add deployment/ README_DEPLOYMENT.md docker/.env.template
  git commit -m "Task 4.1: Desktop Deployment Configuration Complete"
  git push origin main
  ```
  - ⚠️ **CRITICAL:** Verify `.env` is NOT committed (credentials)

### ✅ Operator Confirmation

- [ ] **Operator declares:** "Desktop deployment operational, ready for Task 4.2"
  - Post to Discord: "#deployment-validation" channel
  - Include: Screenshot of `docker ps` showing all services healthy
  - Include: Screenshot of Task Scheduler showing both tasks "Ready"

- [ ] **IBKR Project Management board updated:**
  - Task 4.1 → Status: **Complete**
  - Task 4.2 → Status: **Ready to Start**

---

## Acceptance Criteria Summary

| Criterion | Status | Notes |
|-----------|--------|-------|
| Docker Desktop auto-starts on Windows boot | ⬜ | Test via full reboot |
| Bot auto-starts at 6:00 AM ET (Task Scheduler) | ⬜ | Wait for actual scheduled run OR adjust trigger for immediate test |
| Gateway restarts at 4:30 PM ET (Task Scheduler) | ⬜ | Wait for actual scheduled run OR test manually outside market hours |
| Bot reconnects after Gateway restart (zero-touch) | ⬜ | Test via manual Gateway restart, verify bot logs |
| Discord notifications functional | ⬜ | Startup + Gateway restart notifications received |
| DRY_RUN=true mode active | ⬜ | Verify in logs, no actual orders in IBKR portal |
| All deployment docs created and committed | ⬜ | Verify Git commit includes all files |
| Operator declares operational | ⬜ | Final approval by @tasms |

---

## Troubleshooting Reference

If any checklist item fails, refer to:
- **Task Scheduler Issues:** `deployment/windows/TASK_SCHEDULER_SETUP_GUIDE.md` → Troubleshooting section
- **Docker Issues:** `README_DEPLOYMENT.md` → Troubleshooting section
- **Discord Notifications:** `README_DEPLOYMENT.md` → "Discord Notifications Not Received"
- **Gateway Connection:** `deployment/windows/deployment_notes.md` → Known Issues & Mitigations

---

## Next Steps After Task 4.1 Complete

1. **Task 4.2:** Transition to live paper trading (`DRY_RUN=false`)
2. **Task 4.3:** Implement Strategy A/B execution with live market data
3. **Task 4.4:** Monitor performance metrics for 5-7 trading days
4. **Task 4.5:** Evaluate Raspberry Pi migration (if desktop proves unstable)

---

**Last Updated:** 2026-02-10
**Operator:** @tasms
**Status:** ⚠️ Awaiting Operator Validation — Work through checklist line-by-line
