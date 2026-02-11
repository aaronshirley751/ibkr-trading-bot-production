# Task Scheduler Setup Guide — Task 4.1

This guide walks you through importing and configuring the Windows Task Scheduler tasks for zero-touch bot automation.

---

## Prerequisites

✅ **Completed:**
- [x] Docker Desktop installed and running
- [x] Docker Compose stack tested and operational
- [x] Environment variables configured in `docker/.env`
- [x] `DRY_RUN=true` set in `.env`
- [x] Logs directory created: `C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\logs`

⚠️ **Required Before Proceeding:**
- [ ] Administrator access to Windows
- [ ] Discord webhook tested and functional
- [ ] Docker Desktop auto-start on Windows login enabled

---

## Step 1: Enable Docker Desktop Auto-Start

Before configuring Task Scheduler, ensure Docker Desktop starts automatically on Windows login.

### 1.1: Configure Docker Desktop Settings

1. Open **Docker Desktop**
2. Click **Settings** (gear icon in top-right)
3. Navigate to **General** tab
4. ✅ Enable: **"Start Docker Desktop when you log in"**
5. Click **Apply & Restart**

### 1.2: Test Docker Auto-Start

1. **Reboot Windows** (full restart, not sleep/hibernate)
2. Wait 30-60 seconds after login
3. Verify Docker Desktop is running (system tray icon)
4. Open PowerShell and test:
   ```powershell
   docker info
   ```
   Expected: Docker daemon information (no errors)

If Docker doesn't auto-start, troubleshoot:
- Check Windows Startup Apps: Settings → Apps → Startup → Docker Desktop (should be "On")
- Check Docker Desktop logs: `%APPDATA%\Docker\log.txt`

---

## Step 2: Import Task Scheduler Tasks

### 2.1: Open Task Scheduler

1. Press **Windows + R**
2. Type: `taskschd.msc`
3. Press **Enter**
4. Task Scheduler opens

### 2.2: Import Bot Auto-Start Task

1. In Task Scheduler, click **Action** → **Import Task...**
2. Navigate to:
   ```
   C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\deployment\windows\task_scheduler_startup.xml
   ```
3. Click **Open**
4. Task Scheduler loads the task definition

#### 2.2.1: Review Task Settings

- **General Tab:**
  - Name: `IBKR Trading Bot - Auto-Start`
  - Security options: ✅ "Run whether user is logged on or not"
  - Configure for: Windows 10/11
  - ✅ "Run with highest privileges"

- **Triggers Tab:**
  - Trigger: Daily at **6:00 AM**
  - Advanced: ✅ Enabled
  - Verify timezone is **Eastern Time (ET)**

- **Actions Tab:**
  - Action: Start a program
  - Program/script: `PowerShell.exe`
  - Arguments: `-ExecutionPolicy Bypass -File "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\deployment\windows\startup_script.ps1"`
  - Start in: `C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production`

- **Conditions Tab:**
  - ❌ Uncheck: "Start the task only if the computer is on AC power"
  - ✅ Check: "Wake the computer to run this task"

- **Settings Tab:**
  - ✅ "Allow task to be run on demand"
  - ✅ "Run task as soon as possible after a scheduled start is missed"
  - If the task fails, restart every: **5 minutes**, Attempt to restart up to: **3 times**

#### 2.2.2: Set Credentials

1. Click **OK** to save the task
2. Windows prompts for user credentials
3. Enter your **Windows password**
4. Click **OK**

Task is now created and enabled.

### 2.3: Import Gateway Restart Task

Repeat the import process for the Gateway daily restart task:

1. Click **Action** → **Import Task...**
2. Navigate to:
   ```
   C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\deployment\windows\task_scheduler_gateway_restart.xml
   ```
3. Click **Open**

#### 2.3.1: Review Task Settings

- **General Tab:**
  - Name: `IBKR Gateway - Daily Restart`
  - Security options: ✅ "Run whether user is logged on or not"
  - ✅ "Run with highest privileges"

- **Triggers Tab:**
  - Trigger: Daily at **4:30 PM ET**
  - Advanced: ✅ Enabled

- **Actions Tab:**
  - Program/script: `PowerShell.exe`
  - Arguments: `-ExecutionPolicy Bypass -File "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\deployment\windows\gateway_restart_script.ps1"`

- **Conditions Tab:**
  - ❌ Uncheck: "Start the task only if the computer is on AC power"
  - ❌ Uncheck: "Wake the computer to run this task" (system should already be running at 4:30 PM)

- **Settings Tab:**
  - If the task fails, restart every: **5 minutes**, Attempt to restart up to: **2 times**

#### 2.3.2: Set Credentials

1. Click **OK** to save the task
2. Enter your **Windows password**
3. Click **OK**

---

## Step 3: Test Task Scheduler Tasks

### 3.1: Manual Test — Bot Auto-Start

**⚠️ Important:** Ensure Docker services are NOT currently running before testing auto-start.

```powershell
# Stop all Docker Compose services
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker
docker compose down
```

#### 3.1.1: Run Task Manually

1. In Task Scheduler, locate task: `IBKR Trading Bot - Auto-Start`
2. Right-click → **Run**
3. Task Status shows "Running"

#### 3.1.2: Monitor Execution

Open PowerShell and tail the startup log:

```powershell
Get-Content "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\logs\startup_$(Get-Date -Format 'yyyyMMdd').log" -Wait
```

Expected log output:
- ✅ Docker Desktop is running
- ✅ Navigating to Docker Compose directory
- ✅ Starting Docker Compose services
- ✅ Gateway health check passes
- ✅ Trading Bot status: running
- ✅ Health Monitor status: running
- ✅ Discord notification sent

#### 3.1.3: Verify Services Running

```powershell
docker ps
```

Expected output: 3 containers running (ibkr-gateway, trading-bot, health-monitor)

#### 3.1.4: Check Discord Notification

Open Discord and verify:
- ✅ Bot startup notification received
- ✅ Timestamp matches task execution time
- ✅ Services status shown (Gateway, Bot, Monitor)
- ✅ DRY-RUN mode confirmed

#### 3.1.5: Check Task Result

1. Return to Task Scheduler
2. Click task: `IBKR Trading Bot - Auto-Start`
3. View **"Last Run Result"** (bottom panel)
4. Expected: `The operation completed successfully. (0x0)`

If task failed (non-zero exit code), check logs for errors.

### 3.2: Manual Test — Gateway Restart

**⚠️ Note:** Gateway restart task should only be tested outside market hours (after 4:00 PM ET).

#### 3.2.1: Run Task Manually

1. In Task Scheduler, locate task: `IBKR Gateway - Daily Restart`
2. Right-click → **Run**
3. Task Status shows "Running"

#### 3.2.2: Monitor Execution

```powershell
Get-Content "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\logs\gateway_restart_$(Get-Date -Format 'yyyyMMdd').log" -Wait
```

Expected log output:
- ✅ Gateway container found
- ✅ Gateway restart command executed
- ✅ Waiting for Gateway to become healthy (up to 2 minutes)
- ✅ Gateway health check passes
- ✅ Trading Bot reconnected
- ✅ Discord notification sent

#### 3.2.3: Verify Gateway Restarted

```powershell
docker ps --filter "name=ibkr-gateway" --format "table {{.Names}}\t{{.Status}}"
```

Expected: Gateway uptime should be recent (less than 5 minutes)

#### 3.2.4: Check Discord Notification

Verify Discord received Gateway restart notification:
- ✅ Pre-restart notification (optional, if implemented)
- ✅ Post-restart success notification
- ✅ Gateway health status: healthy
- ✅ Bot reconnection confirmed

### 3.3: Verify Scheduled Triggers

After manual tests pass, verify scheduled triggers are properly configured:

```powershell
# Check next scheduled run times
Get-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start" | Get-ScheduledTaskInfo | Select-Object -Property LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns

Get-ScheduledTask -TaskName "IBKR Gateway - Daily Restart" | Get-ScheduledTaskInfo | Select-Object -Property LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns
```

Expected:
- `NextRunTime` for Auto-Start: Tomorrow at 6:00 AM ET
- `NextRunTime` for Gateway Restart: Today or tomorrow at 4:30 PM ET
- `NumberOfMissedRuns`: 0
- `LastTaskResult`: 0 (success)

---

## Step 4: Configure Windows Power Settings

Prevent Windows from sleeping or hibernating during market hours.

### 4.1: Adjust Power Plan

1. Open **Settings** → **System** → **Power & sleep**
2. **Screen:**
   - When plugged in, turn off after: **30 minutes** (or Never)
3. **Sleep:**
   - When plugged in, PC goes to sleep after: **Never**

### 4.2: Configure Active Hours (Prevent Restart During Market Hours)

1. Open **Settings** → **Windows Update** → **Advanced options**
2. Click **Active hours**
3. Set active hours: **6:00 AM - 6:00 PM** (covers pre-market to post-market)
4. Click **Save**

This prevents Windows from forcing updates/restarts during trading hours.

### 4.3: Disable Sleep on Idle (Registry Edit - Optional)

If Windows still sleeps despite settings, use registry edit:

```powershell
# Run PowerShell as Administrator
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

Verify:
```powershell
powercfg /query
```

Expected: `Standby` and `Hibernate` timeouts set to 0 (never sleep) when plugged in.

---

## Step 5: Full System Test (Reboot)

Perform a full end-to-end test by rebooting Windows.

### 5.1: Pre-Reboot Checklist

- [ ] Docker Desktop auto-start enabled
- [ ] Both Task Scheduler tasks imported and enabled
- [ ] `DRY_RUN=true` confirmed in `.env`
- [ ] Power settings configured (no sleep during market hours)
- [ ] Active hours set (6:00 AM - 6:00 PM ET)

### 5.2: Reboot Windows

```powershell
Restart-Computer
```

### 5.3: Post-Reboot Verification

After Windows reboots and you log in:

1. **Wait 1-2 minutes** for Docker Desktop to auto-start
2. Verify Docker Desktop running (system tray icon)
3. Check if services auto-started:
   ```powershell
   docker ps
   ```
   - If services are NOT running, Task Scheduler will start them at 6:00 AM ET
   - If services ARE running, Docker Compose `restart: unless-stopped` policy kept them alive

4. Check Task Scheduler tasks are enabled:
   ```powershell
   Get-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start" | Select-Object State, NextRunTime
   Get-ScheduledTask -TaskName "IBKR Gateway - Daily Restart" | Select-Object State, NextRunTime
   ```
   Expected: Both tasks show `State: Ready`, `NextRunTime: <future date>`

5. **If testing at 6:00 AM ET or later**, check if auto-start executed:
   ```powershell
   Get-Content "C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\logs\startup_$(Get-Date -Format 'yyyyMMdd').log"
   ```

### 5.4: Wait for Actual Scheduled Run

**Important:** Task Scheduler will trigger the auto-start task at **6:00 AM ET tomorrow**. Monitor Discord at that time for startup notification.

If you cannot wait until 6:00 AM ET:
1. Temporarily change task trigger to "current time + 2 minutes"
2. Wait for task to execute
3. Verify startup logs and Discord notification
4. Reset trigger to 6:00 AM ET

---

## Step 6: Deployment Validation (Next Phase)

Once Task Scheduler configuration is complete, proceed to **Phase F: Health Monitoring & Discord Setup** and **Phase G: Deployment Validation Checklist**.

---

## Troubleshooting

### Issue: Task Scheduler task fails with "Task has not yet run"

**Cause:** Task trigger hasn't occurred yet (6:00 AM ET hasn't arrived).

**Solution:** Manually run task (Right-click → Run) to test immediately.

---

### Issue: Task fails with "Access is denied"

**Cause:** Task doesn't have correct permissions or credentials.

**Solution:**
1. Right-click task → **Properties**
2. Go to **General** tab
3. Ensure "Run with highest privileges" is checked
4. Click **OK**, re-enter Windows password when prompted

---

### Issue: PowerShell script doesn't execute (nothing happens)

**Cause:** PowerShell execution policy blocks scripts.

**Solution:**
Verify execution policy allows scripts:
```powershell
Get-ExecutionPolicy
```
Expected: `RemoteSigned` or `Bypass`

If restricted:
```powershell
# Run as Administrator
Set-ExecutionPolicy -Executionolicy RemoteSigned -Scope LocalMachine
```

---

### Issue: Docker not found when task runs

**Cause:** Task runs before Docker Desktop fully initializes.

**Solution:**
The startup script already includes 120-second Docker wait logic. If issue persists:
1. Increase `$MaxDockerWaitSeconds` in `startup_script.ps1` (line 26)
2. Or delay task trigger by 5 minutes (6:05 AM ET instead of 6:00 AM)

---

### Issue: Discord notification not received

**Cause:** Webhook URL not accessible or incorrectly configured.

**Solution:**
Test webhook manually:
```powershell
$WebhookUrl = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
$Payload = @{ content = "Test from PowerShell" } | ConvertTo-Json
Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $Payload -ContentType "application/json"
```

Check Discord for test message. If no message:
- Verify webhook URL is correct (check `.env` file)
- Ensure webhook is not deleted in Discord settings
- Check firewall/antivirus isn't blocking outbound HTTPS requests

---

### Issue: Services don't auto-start even after reboot

**Cause:** Docker Compose `restart: unless-stopped` policy means services stay stopped if explicitly stopped.

**Solution:**
Ensure services are running before reboot:
```powershell
docker compose up -d
```

Or rely on Task Scheduler auto-start at 6:00 AM ET.

---

## Rollback Instructions

If Task Scheduler configuration causes issues:

### Disable Tasks Temporarily

```powershell
Disable-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start"
Disable-ScheduledTask -TaskName "IBKR Gateway - Daily Restart"
```

### Re-Enable After Fix

```powershell
Enable-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start"
Enable-ScheduledTask -TaskName "IBKR Gateway - Daily Restart"
```

### Delete Tasks (Complete Rollback)

```powershell
Unregister-ScheduledTask -TaskName "IBKR Trading Bot - Auto-Start" -Confirm:$false
Unregister-ScheduledTask -TaskName "IBKR Gateway - Daily Restart" -Confirm:$false
```

---

**Next Steps:** After Task Scheduler configuration is complete and tested, proceed to **Phase G: Deployment Validation Checklist** to finalize Task 4.1.
