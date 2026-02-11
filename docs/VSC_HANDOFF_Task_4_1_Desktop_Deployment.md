# VSC HANDOFF: Task 4.1 — Desktop Deployment (Interim Production Platform)

**Date:** 2026-02-10
**Phase:** Phase 4 Sprint — Desktop-First Deployment
**Requested By:** @PM, @DevOps
**Model Recommendation:** Sonnet (structured configuration work, moderate complexity)
**Context Budget:** Moderate (multi-step deployment with configuration validation)
**VSC Template Version:** v2.0

---

## CONTEXT BLOCK

### Strategic Purpose

Task 4.1 establishes the desktop (Windows 11) as the interim production platform for IBKR Trading Bot validation and early live trading. This deployment enables immediate Phase 4 progression without hardware procurement blockers. The desktop already runs IBKR Gateway in a known-stable configuration daily.

### Related Documents

- `PHASE_4_SPRINT_PLAN_Desktop_First_Deployment.md` — Full sprint plan and task breakdown
- `ARCHITECTURE_Gateway_Deployment_Strategy_Decision_v2.md` — Desktop-first decision rationale
- `Charter_Stone_Operations_Platform_Architecture_v2_0.md` — Phase 2 completion baseline

### Deployment Architecture Overview

**Platform:** Windows 11 Pro (Operator's Daily Driver)
**IBKR Gateway:** Already operational on localhost:4002
**Python:** 3.11+ with Poetry dependency management
**Automation:** Windows Task Scheduler (6:00 AM ET bot auto-start) + IBC Controller (Gateway lifecycle)
**Monitoring:** Discord webhooks for bot notifications
**Mode:** Dry-run validation initially (`DRY_RUN=true`)

### Key Constraints

- **Zero-touch automation required:** Bot must auto-start, connect, and handle Gateway restarts without operator intervention
- **Desktop stability risk:** Windows updates, reboots, sleep mode could disrupt operation — mitigations required
- **Gateway memory leak:** IBKR Gateway known to leak memory over time — daily restart at 4:30 PM ET via IBC Controller
- **Operator availability:** Operator physically present during validation — manual intervention available if needed

---

## AGENT EXECUTION BLOCK

### 1. Objective

Configure the Windows 11 desktop as a production-ready deployment platform with zero-touch automation. The bot must:
1. Auto-start at 6:00 AM ET via Task Scheduler
2. Connect to IBKR Gateway (localhost:4002) and initialize successfully
3. Send Discord notification on startup
4. Handle Gateway restarts gracefully (4:30 PM ET daily via IBC Controller)
5. Operate in dry-run mode for initial validation

### 2. File Structure

**No new application code required.** This task focuses on deployment configuration and system integration.

**Configuration Files to Create/Modify:**

```
project_root/
├── .env                          # Environment configuration (CREATE or UPDATE)
├── deployment/
│   ├── windows/
│   │   ├── ibc_config.ini        # IBC Controller configuration (CREATE)
│   │   ├── task_scheduler.xml    # Windows Task Scheduler export template (CREATE)
│   │   └── deployment_notes.md   # Deployment verification checklist (CREATE)
├── logs/                          # Log directory (ensure exists, configure rotation)
└── README_DEPLOYMENT.md          # Deployment instructions (UPDATE or CREATE)
```

**External Downloads Required:**

- **IBC (Interactive Brokers Controller):** https://github.com/IbcAlpha/IBC/releases
  - Download latest stable release (e.g., `IBC-3.16.2.zip`)
  - Extract to `C:\IBC` or similar location

### 3. Logic Flow (Task Sequence)

This is a **deployment task**, not a coding task. The logic flow is the deployment procedure.

**Phase A: Gateway Health Verification**

```
1. Verify IBKR Gateway currently running:
   - Check Windows Task Manager for "ibgateway" or similar process
   - If not running, launch Gateway manually (use existing launch method)

2. Test Gateway connectivity:
   - Open command prompt
   - Run: `curl http://localhost:4002/v1/api/tickle`
   - Expected response: HTTP 200 or similar handshake confirmation
   - If connection fails, diagnose (firewall, port conflict, credentials)

3. Document Gateway credentials location:
   - IBKR username stored in: [WHERE?]
   - IBKR password stored in: [WHERE?]
   - Ensure IBC Controller will have access to these credentials
```

**Phase B: IBC Controller Installation**

```
1. Download IBC:
   - Visit https://github.com/IbcAlpha/IBC/releases
   - Download latest stable release (verify SHA256 checksum)
   - Extract to C:\IBC (or document chosen location)

2. Configure IBC:
   - Navigate to C:\IBC
   - Copy `IBCWin.ini.sample` → `IBCWin.ini`
   - Edit IBCWin.ini:
     [Authentication]
     IbLoginId=<IBKR_USERNAME>
     IbPassword=<IBKR_PASSWORD>
     PasswordEncrypted=no  # or yes if using encrypted password

     [Paths]
     IbDir=<PATH_TO_IBKR_GATEWAY_INSTALLATION>  # e.g., C:\Jts\ibgateway

     [Scheduling]
     DismissPasswordExpiryWarning=yes
     DismissNSEComplianceNotice=yes

     [Auto-Restart]
     ClosedownAt=16:30  # 4:30 PM ET daily restart
     AutoRestartTime=04:30  # Next day 4:30 AM if overnight needed

   - Verify configuration syntax (IBC documentation: https://ib.insync.io/ibc.html)

3. Test IBC Launch:
   - Open command prompt as Administrator
   - Navigate to C:\IBC
   - Run: `IBCWin.bat` (or `StartIBC.bat` depending on version)
   - Verify Gateway launches and IBC logs show successful start
   - Verify Gateway accessible at localhost:4002
   - Shutdown Gateway cleanly via IBC (test graceful shutdown)

4. Verify IBC handles 2FA (if applicable):
   - If IBKR account uses 2FA, document how IBC handles this
   - Options:
     a. IBKR mobile app notification (manual acceptance required)
     b. Hardware token (less common)
     c. Trusted device exemption (configure in IBKR portal)
   - Test 2FA flow during IBC launch
   - Document any manual steps required
```

**Phase C: Bot Deployment**

```
1. Verify repository state:
   - Repository already cloned to desktop?
     - If yes, pull latest changes: `git pull origin main`
     - If no, clone: `git clone <REPO_URL> <LOCAL_PATH>`
   - Navigate to project root

2. Create Python environment:
   - Verify Poetry installed: `poetry --version`
   - If not installed, install Poetry: https://python-poetry.org/docs/#installation
   - Install dependencies: `poetry install`
   - Verify all dependencies installed without errors

3. Configure environment variables:
   - Create .env file in project root (or update existing):

     # IBKR Connection
     IBKR_HOST=localhost
     IBKR_PORT=4002
     IBKR_CLIENT_ID=1  # or next available ID if multiple clients

     # Execution Mode
     DRY_RUN=true  # CRITICAL: Start in dry-run mode for validation
     PAPER_TRADING=false  # Desktop deployment uses live Gateway in dry-run mode initially

     # Discord Notifications
     DISCORD_WEBHOOK_URL=<OPERATOR_WEBHOOK_URL>

     # Logging
     LOG_LEVEL=INFO
     LOG_FILE=logs/crucible_bot.log
     LOG_MAX_BYTES=10485760  # 10 MB per log file
     LOG_BACKUP_COUNT=10  # Keep 10 rotated logs (100 MB total)

     # Strategy Configuration
     GAMEPLAN_PATH=gameplans/daily_gameplan.json
     STRATEGY_LIBRARY_PATH=strategies/

     # Risk Controls
     MAX_DAILY_LOSS_PCT=0.10
     MAX_POSITION_PCT=0.20
     PDT_ENABLED=true

   - Verify .env file syntax (no extra spaces, proper formatting)
   - Ensure .env is in .gitignore (never commit credentials)

4. Test bot startup (manual):
   - Open command prompt in project root
   - Activate Poetry environment: `poetry shell`
   - Run bot: `python -m src.main` (or equivalent entry point)
   - Expected behavior:
     a. Bot initializes and logs startup
     b. Bot connects to Gateway (localhost:4002)
     c. Discord notification sent: "Bot started in DRY-RUN mode"
     d. Bot enters idle state (waiting for gameplan or market open)
   - Review logs for errors or warnings
   - Shutdown bot cleanly (Ctrl+C or SIGTERM equivalent)

5. Verify dry-run mode:
   - Check logs for "DRY_RUN=true" confirmation
   - Verify no actual orders sent to IBKR (check IBKR portal)
   - Confirm strategy signals generate but do not execute
```

**Phase D: Windows Task Scheduler Configuration**

```
1. Create Task Scheduler task for bot auto-start:
   - Open Task Scheduler (Windows + R, type "taskschd.msc")
   - Create Task (not Basic Task — need advanced options)

   General Tab:
   - Name: "IBKR Crucible Bot - Auto-Start"
   - Description: "Launches IBKR Trading Bot at 6:00 AM ET daily"
   - Security options: "Run whether user is logged on or not"
   - Configure for: Windows 10/11
   - Check "Run with highest privileges" (ensure file access)

   Triggers Tab:
   - New Trigger
   - Begin the task: On a schedule
   - Settings: Daily, 6:00 AM ET (adjust for timezone)
   - Advanced settings:
     - Enabled: Yes
     - Repeat task: No (bot runs continuously)

   Actions Tab:
   - New Action
   - Action: Start a program
   - Program/script: `C:\Users\<USERNAME>\AppData\Local\Programs\Python\Python311\python.exe`
     (or path to Python in Poetry virtualenv — verify exact path)
   - Add arguments: `-m src.main`
   - Start in: `<PROJECT_ROOT_PATH>` (e.g., C:\Users\Aaron\Projects\ibkr-trading-bot)

   Conditions Tab:
   - Uncheck "Start the task only if the computer is on AC power"
   - Check "Wake the computer to run this task" (if desktop sleeps)

   Settings Tab:
   - Check "Allow task to be run on demand"
   - Check "Run task as soon as possible after a scheduled start is missed"
   - If the task fails, restart every: 5 minutes, Attempt to restart up to: 3 times
   - Stop the task if it runs longer than: 23 hours (prevent runaway)

   - Save task (enter operator's Windows password if prompted)

2. Export Task Scheduler task (for version control):
   - Right-click task → Export
   - Save as: deployment/windows/task_scheduler.xml
   - Commit to repository for disaster recovery

3. Test Task Scheduler task:
   - Right-click task → Run
   - Verify bot starts successfully
   - Check Discord for startup notification
   - Review Task Scheduler "Last Run Result" (should show success)
   - Stop bot manually (Task Manager → End Task)
   - Re-run from Task Scheduler to confirm repeatability
```

**Phase E: Gateway Daily Restart Configuration (IBC Controller)**

```
1. Verify IBC configured for daily restart:
   - Review IBCWin.ini:
     ClosedownAt=16:30  # 4:30 PM ET
   - IBC will gracefully shutdown Gateway at 4:30 PM ET daily

2. Configure Task Scheduler for IBC daily restart:
   - Create Task: "IBKR Gateway - Daily Restart via IBC"
   - Trigger: Daily, 4:25 PM ET (5 minutes before shutdown)
   - Action: Start IBC (IBCWin.bat or StartIBC.bat)
   - This ensures Gateway restarts cleanly at 4:30 PM ET

   Alternative (if IBC handles restart automatically):
   - Verify IBC AutoRestartTime setting in IBCWin.ini
   - Test that Gateway restarts automatically after 4:30 PM shutdown
   - If automatic restart works, no additional Task Scheduler task needed

3. Test Gateway restart flow:
   - Manually trigger IBC shutdown at non-market hours
   - Verify Gateway shuts down cleanly (check logs)
   - Verify Gateway restarts automatically (if configured)
   - Verify bot reconnects to Gateway without manual intervention
   - Check bot logs for reconnection logic (should auto-retry)
```

**Phase F: Health Monitoring & Discord Notifications**

```
1. Verify Discord webhook configured:
   - .env contains valid DISCORD_WEBHOOK_URL
   - Test webhook manually:
     - Open command prompt
     - Run test script (or use curl):
       curl -X POST <DISCORD_WEBHOOK_URL> \
         -H "Content-Type: application/json" \
         -d '{"content": "Test message from Crucible Bot deployment"}'
   - Verify message appears in Discord channel

2. Verify bot sends startup notification:
   - Launch bot manually (poetry run python -m src.main)
   - Check Discord for startup message
   - Message should include:
     - Timestamp
     - Mode (DRY-RUN)
     - Gateway connection status
   - Shutdown bot and repeat test

3. Configure log rotation (prevent disk exhaustion):
   - Verify logging configuration in src/ code:
     - Python logging.handlers.RotatingFileHandler configured?
     - Max bytes per log file: 10 MB
     - Backup count: 10 files (100 MB total)
   - Test log rotation:
     - Run bot, generate log output (normal operation or test)
     - Verify logs rotate when 10 MB reached
     - Verify old logs archived (crucible_bot.log.1, .2, etc.)
```

**Phase G: Deployment Validation Checklist**

```
1. Complete manual validation:
   - [ ] Gateway running on localhost:4002
   - [ ] Gateway responds to health check API calls
   - [ ] IBC Controller configured and tested
   - [ ] IBC handles Gateway launch and shutdown cleanly
   - [ ] Bot connects to Gateway successfully (manual test)
   - [ ] Bot logs show initialization and dry-run mode confirmation
   - [ ] Discord webhook sends startup notification
   - [ ] Task Scheduler task configured and tested (manual run)
   - [ ] Task Scheduler task auto-starts bot at 6:00 AM ET (wait for next scheduled run)
   - [ ] Gateway restarts at 4:30 PM ET via IBC Controller (wait for scheduled time)
   - [ ] Bot reconnects to Gateway after restart (no manual intervention)
   - [ ] Log rotation functioning correctly
   - [ ] .env file configured with DRY_RUN=true

2. Document deployment state:
   - Create deployment/windows/deployment_notes.md:
     - IBC installation path
     - Task Scheduler task names and schedules
     - Discord webhook channel
     - Any manual steps required during deployment
     - Known issues or workarounds
     - Rollback procedure (how to disable auto-start if needed)

3. Declare deployment operational:
   - Operator confirms all checklist items complete
   - Operator posts to Discord: "Desktop deployment operational, ready for Task 4.2"
   - Update IBKR Project Management board: Task 4.1 → Complete
```

### 4. Dependencies

**External Tools:**
- **IBC (Interactive Brokers Controller):** https://github.com/IbcAlpha/IBC
- **Windows Task Scheduler:** Built-in Windows feature
- **curl or Postman (optional):** For API testing

**Python Dependencies:**
- Already installed via `poetry install` (from pyproject.toml)
- No additional dependencies required for deployment

**Environment Variables:**
- See `.env` configuration in Phase C, Step 3 above

**IBKR Gateway:**
- Must already be installed on desktop
- Must be configured with operator's IBKR credentials
- Must be accessible on localhost:4002

### 5. Input/Output Contract

**Input (Deployment Configuration):**
- IBKR Gateway installation path (for IBC config)
- IBKR credentials (username, password)
- Discord webhook URL
- Project repository path on desktop
- Operator's Windows username (for Task Scheduler paths)

**Output (Deployed System):**
- Bot auto-starts at 6:00 AM ET daily
- Bot connects to Gateway and initializes successfully
- Discord notifications sent on bot startup
- Gateway restarts at 4:30 PM ET daily via IBC Controller
- Bot reconnects to Gateway after restart (zero-touch)
- Logs rotate to prevent disk exhaustion
- System operates in dry-run mode (no actual trades)

### 6. Integration Points

**IBKR Gateway Integration:**
- Bot connects to Gateway via HTTP API (localhost:4002)
- Health check endpoint: `/v1/api/tickle`
- Order submission endpoint: (dry-run mode does not send orders)
- Reconnection logic: Bot must auto-retry connection if Gateway restarts

**Discord Webhook Integration:**
- Bot sends notifications via HTTP POST to Discord webhook URL
- Notifications include: startup, errors, strategy signals (if configured)

**Windows Task Scheduler Integration:**
- Task Scheduler launches bot at 6:00 AM ET
- Task Scheduler monitors bot process health (optional: configure restart on failure)

**IBC Controller Integration:**
- IBC launches Gateway on system startup (or on-demand)
- IBC shuts down Gateway at 4:30 PM ET daily (memory leak mitigation)
- IBC handles Gateway authentication (credentials in IBCWin.ini)

### 7. Definition of Done

Task 4.1 is complete when:

**Automated Operation Verified:**
- [ ] Bot auto-starts at 6:00 AM ET via Task Scheduler (manual test confirms, then wait for actual scheduled run)
- [ ] Bot connects to Gateway successfully and logs initialization
- [ ] Discord notification received on bot startup
- [ ] Gateway restarts at 4:30 PM ET via IBC Controller (wait for scheduled time)
- [ ] Bot handles Gateway restart gracefully (reconnects without manual intervention)

**Configuration Validated:**
- [ ] `DRY_RUN=true` mode verified in logs
- [ ] No actual orders sent to IBKR (check IBKR portal — no paper or live trades)
- [ ] Log rotation functioning correctly (logs do not exceed 100 MB total)

**Documentation Complete:**
- [ ] deployment/windows/ibc_config.ini committed to repository
- [ ] deployment/windows/task_scheduler.xml exported and committed
- [ ] deployment/windows/deployment_notes.md created with deployment details
- [ ] README_DEPLOYMENT.md updated with desktop deployment instructions

**Operator Confirmation:**
- [ ] Operator declares: **"Desktop deployment operational, ready for Task 4.2"**
- [ ] IBKR Project Management board updated: Task 4.1 → Complete

### 8. Edge Cases to Test

**Gateway Connection Failures:**
- What happens if Gateway is not running when bot starts?
  - Expected: Bot logs error, retries connection (with backoff), sends Discord alert
- What happens if Gateway crashes mid-day?
  - Expected: Bot detects disconnection, retries connection, sends Discord alert
- What happens if Gateway authentication fails (expired credentials)?
  - Expected: Bot logs authentication error, halts (does not retry indefinitely), sends Discord alert

**Task Scheduler Failures:**
- What happens if desktop is shutdown at 6:00 AM ET (bot cannot auto-start)?
  - Expected: Task Scheduler runs task "as soon as possible after missed start" when desktop powers on
- What happens if bot process crashes after auto-start?
  - Expected: Task Scheduler restarts bot (if configured with restart policy)
- What happens if operator manually kills bot process?
  - Expected: Task Scheduler does NOT auto-restart (only restarts on failure, not manual termination)

**IBC Controller Failures:**
- What happens if IBC fails to launch Gateway at 4:25 PM ET?
  - Expected: Gateway does not restart, bot loses connection, Discord alert sent
  - Manual intervention: Operator restarts Gateway manually, bot reconnects
- What happens if IBC 2FA prompt requires manual intervention?
  - Expected: Gateway launch pauses, operator receives notification (via IBKR mobile app), manual acceptance required
  - Mitigation: Configure "trusted device" in IBKR portal to reduce 2FA frequency

**Disk Space Exhaustion:**
- What happens if log directory fills disk (log rotation fails)?
  - Expected: Bot logs errors, may halt if cannot write logs
  - Mitigation: Monitor disk space, verify log rotation working correctly

**Windows Updates / Reboots:**
- What happens if Windows forces update + reboot overnight?
  - Expected: Desktop reboots, Task Scheduler auto-starts bot at next 6:00 AM ET
  - Risk: If reboot occurs during market hours, bot loses connection temporarily
  - Mitigation: Configure Windows Update to install outside market hours (overnight)

**Network Connectivity Loss:**
- What happens if localhost (127.0.0.1) is unreachable (firewall misconfiguration)?
  - Expected: Bot cannot connect to Gateway, logs error, sends Discord alert
  - Diagnosis: Check Windows Firewall settings, verify port 4002 not blocked

**Clock Drift / Timezone Issues:**
- What happens if system clock is incorrect (wrong timezone)?
  - Expected: Task Scheduler runs at wrong time, bot auto-start misaligned with market hours
  - Diagnosis: Verify Windows timezone set to Eastern Time (ET)
  - Mitigation: Enable automatic time sync (Windows settings)

### 9. Rollback Plan

**If Task 4.1 deployment fails:**

1. **Disable Task Scheduler Auto-Start:**
   - Open Task Scheduler
   - Right-click "IBKR Crucible Bot - Auto-Start" → Disable
   - This prevents bot from auto-starting while troubleshooting

2. **Disable IBC Controller Gateway Restart:**
   - Edit IBCWin.ini, comment out `ClosedownAt` line
   - Or disable Task Scheduler task for IBC daily restart

3. **Revert to Manual Bot Launch (Development Mode):**
   - Open command prompt in project root
   - Run: `poetry run python -m src.main`
   - This allows manual testing and debugging without automation

4. **Document Failure Mode:**
   - Capture error logs (bot logs, Task Scheduler logs, IBC logs)
   - Note timestamp of failure
   - Document trigger (what step failed)
   - Create GitHub issue or project board task for remediation

5. **Address Blocker Before Re-Attempting:**
   - Diagnose root cause (connection failure, configuration error, etc.)
   - Implement fix
   - Re-test manually before re-enabling automation

6. **Re-Enable Automation After Fix Validated:**
   - Re-enable Task Scheduler tasks
   - Re-enable IBC Controller gateway restart
   - Monitor next scheduled run (6:00 AM ET) for success

**Rollback to Phase 3 (Development Environment):**
- If desktop deployment proves unstable, revert to development environment
- Document decision rationale and lessons learned
- Escalate to Red Team review for deployment strategy reassessment

---

## IMPLEMENTATION NOTES

### For the Factory Floor Engineer (VSC Copilot User)

**This is a deployment task, not a coding task.** You will be working with system configuration, external tools, and environment setup — not writing Python code.

**Recommended Approach:**

1. **Work through phases sequentially.** Do not skip ahead. Each phase builds on the previous.
2. **Test each phase before proceeding.** Verify Gateway health before installing IBC. Verify IBC before configuring Task Scheduler.
3. **Document everything.** Take notes in `deployment/windows/deployment_notes.md` as you go. Include file paths, configuration values, any issues encountered.
4. **Use VSC terminal for testing.** Open integrated terminal in VSC, run commands from there. This keeps everything in one workspace.
5. **Commit configuration files to repository.** IBC config, Task Scheduler XML, .env template (without secrets) should be version-controlled.
6. **Do NOT commit credentials.** Ensure .env is in .gitignore. IBC config should use environment variables or be documented separately for credential management.

**Troubleshooting Resources:**

- **IBC Documentation:** https://ib.insync.io/ibc.html
- **IBKR Gateway API Documentation:** https://interactivebrokers.github.io/cpwebapi/
- **Windows Task Scheduler Guide:** https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page
- **Poetry Documentation:** https://python-poetry.org/docs/

**If You Get Stuck:**

1. Check logs first (bot logs, IBC logs, Task Scheduler logs)
2. Search error messages online (Stack Overflow, GitHub Issues)
3. Escalate to Boardroom if systemic issue (convene @DevOps session)

**Safety Reminders:**

- **DRY_RUN=true is mandatory** for initial deployment. Do not change this until Task 4.3 (paper trading transition).
- **Never commit IBKR credentials** to repository. Use environment variables or secure credential storage.
- **Test Gateway connection manually** before relying on automation.

---

## VSC COPILOT PROMPTS (OPTIONAL ASSISTANCE)

If you need Copilot's help with specific configuration steps, here are some example prompts:

**Prompt 1: IBC Configuration Review**
```
Review this IBC configuration file (IBCWin.ini) for syntax errors and verify that the Gateway daily restart is configured correctly for 4:30 PM ET shutdown. Highlight any missing required settings.

[paste IBCWin.ini contents]
```

**Prompt 2: Task Scheduler XML Validation**
```
I've exported this Windows Task Scheduler task XML. Verify that the task is configured to:
1. Run at 6:00 AM ET daily
2. Launch the bot with correct Python path and arguments
3. Run with highest privileges
4. Restart on failure (3 attempts, 5-minute intervals)

[paste task_scheduler.xml contents]
```

**Prompt 3: .env Configuration Check**
```
Review this .env file for the IBKR Trading Bot desktop deployment. Verify:
1. DRY_RUN=true is set
2. IBKR_HOST and IBKR_PORT are correct for localhost Gateway
3. Discord webhook URL is properly formatted
4. Log rotation settings are configured

[paste .env contents]
```

**Prompt 4: Bot Startup Test**
```
I'm testing the bot manual startup. Here's the output from `poetry run python -m src.main`. Identify any errors or warnings that indicate connection failures or configuration issues.

[paste bot startup logs]
```

---

**END OF VSC HANDOFF: Task 4.1**
