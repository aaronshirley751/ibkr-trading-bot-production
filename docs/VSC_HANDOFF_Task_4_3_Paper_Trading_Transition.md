# VSC HANDOFF: Task 4.3 — Transition to Paper Trading

**Date:** 2026-02-10
**Phase:** Phase 4 Sprint — Desktop-First Deployment
**Requested By:** @PM, @CRO
**Model Recommendation:** Haiku (simple configuration change, low complexity)
**Context Budget:** Light (minimal code changes, primarily configuration)
**VSC Template Version:** v2.0

---

## CONTEXT BLOCK

### Strategic Purpose

Task 4.3 transitions the bot from dry-run mode (signal generation only) to paper trading mode (actual order execution on IBKR paper account). This is a **configuration change task**, not a feature development task. The bot's core functionality remains unchanged — only the execution mode switches.

**Critical Safety Gate:** This transition is authorized ONLY when Task 4.2 stability criteria are met. Paper trading provides superior stress testing but requires proven desktop deployment stability first.

### Related Documents

- `PHASE_4_SPRINT_PLAN_Desktop_First_Deployment.md` — Full sprint plan and transition criteria
- `VSC_HANDOFF_Task_4_1_Desktop_Deployment.md` — Desktop deployment baseline
- `VSC_HANDOFF_Task_4_2_Dry_Run_Validation.md` — Stability validation prerequisites
- Task 4.2 completion REQUIRED before Task 4.3

### Deployment State Assumptions

**Prerequisites (Task 4.2 Complete):**
- Desktop deployment stable (5+ days dry-run validation passed)
- Zero-touch automation proven (auto-start, reconnection, health checks)
- Bot operates reliably without crashes or manual interventions
- Operator has reviewed Task 4.2 stability summary and authorized transition

**Transition Objective:** Switch from dry-run mode to paper trading mode with minimal configuration changes and zero code modifications.

---

## AGENT EXECUTION BLOCK

### 1. Objective

Reconfigure the bot to execute trades on IBKR paper trading account instead of logging signals without execution. Verify that the transition is clean, that paper trading mode is correctly activated, and that no unintended changes (e.g., accidental live trading mode) are introduced.

**This is a configuration task, not a coding task.** The bot code already supports paper trading mode (Phase 3 implementation). This task modifies environment configuration and verifies the mode switch.

### 2. File Structure

**Files to Modify:**

```
project_root/
├── .env                          # MODIFY: Change DRY_RUN and PAPER_TRADING settings
└── docs/
    └── Task_4_3_Transition_Log.md    # CREATE: Document transition and verification
```

**No Code Changes Expected.**

### 3. Logic Flow (Transition Procedure)

**Pre-Transition Checklist:**

```
Step 0: Verify Task 4.2 Completion
-----------------------------------
- [ ] Task 4.2 stability summary reviewed and approved by operator
- [ ] All 6 stability criteria met (zero crashes, zero interventions, etc.)
- [ ] Operator explicitly authorizes transition to paper trading
- [ ] IBKR paper trading account accessible (verify credentials)

If any checklist item fails, DO NOT proceed. Return to Task 4.2 or remediate blocker.
```

**Transition Sequence (4 Steps):**

```
Step 1: Halt Bot (Controlled Shutdown)
---------------------------------------
1. Wait for non-market hours (after 4:00 PM ET or before 9:30 AM ET)
   - Transition during market hours risks incomplete order handling
   - Non-market hours ensures no active positions

2. Manually stop bot process:
   - Option A: Wait for 4:30 PM ET Gateway restart (bot shuts down)
   - Option B: Manually stop via Task Manager (End Task on Python process)
   - Verify bot shutdown in logs (clean shutdown, no errors)

3. Verify no open positions in IBKR account:
   - Log into IBKR paper account (web portal or TWS)
   - Navigate to Portfolio → Positions
   - Confirm: ZERO open positions (dry-run mode should have none anyway)
   - If positions exist, close manually before proceeding

4. Document shutdown:
   - Note timestamp of shutdown
   - Verify last log entry shows clean shutdown
   - Create docs/Task_4_3_Transition_Log.md and document shutdown

Step 2: Update Configuration (.env File)
-----------------------------------------
1. Open .env file in project root (use text editor or VSC)

2. Modify execution mode settings:

   BEFORE (Dry-Run Mode):
   ----------------------
   DRY_RUN=true
   PAPER_TRADING=false

   AFTER (Paper Trading Mode):
   ---------------------------
   DRY_RUN=false          # CRITICAL: Switch to false to enable execution
   PAPER_TRADING=true     # CRITICAL: Switch to true for paper account

3. Verify IBKR connection settings unchanged:

   IBKR_HOST=localhost    # Should remain localhost (Gateway on desktop)
   IBKR_PORT=4002         # Should remain 4002 (paper trading port)
   IBKR_CLIENT_ID=1       # Should remain 1 (or existing client ID)

4. Verify all other settings unchanged:
   - Discord webhook URL
   - Log settings
   - Risk controls (MAX_DAILY_LOSS_PCT, MAX_POSITION_PCT, PDT_ENABLED)
   - Strategy configuration paths

5. Save .env file

6. CRITICAL VERIFICATION:
   - Re-open .env file and visually confirm:
     - DRY_RUN=false
     - PAPER_TRADING=true
     - No other changes made
   - DO NOT proceed if verification fails

Step 3: Restart Bot (Paper Trading Mode)
-----------------------------------------
1. Launch bot manually (do NOT rely on Task Scheduler for first paper trading run):
   - Open command prompt in project root
   - Activate Poetry environment: poetry shell
   - Run bot: python -m src.main

2. Monitor startup logs closely:
   - Expected log entries:
     - "Configuration loaded: DRY_RUN=false, PAPER_TRADING=true"
     - "Connecting to IBKR Gateway at localhost:4002"
     - "Gateway connection established"
     - "Paper trading mode ACTIVE"
     - "Bot initialized successfully"

   - CRITICAL: Verify "Paper trading mode ACTIVE" appears in logs
   - CRITICAL: Verify NO "Live trading mode" messages (if such logs exist)

3. Check Discord for startup notification:
   - Expected message: "Bot started in PAPER TRADING mode at [timestamp]"
   - If notification says "DRY-RUN mode" or "LIVE mode", HALT IMMEDIATELY

4. If startup fails or logs show dry-run mode still active:
   - Shutdown bot (Ctrl+C)
   - Re-verify .env file settings
   - Check bot code for configuration loading logic (ensure it reads .env correctly)
   - Diagnose and remediate before re-attempting

Step 4: Verify Paper Trading Mode Active
-----------------------------------------
1. Test order submission (if bot submits orders on startup):
   - Check bot logs for order submission attempts
   - Expected: Orders sent to IBKR Gateway (not just logged)
   - Check IBKR paper account (web portal) for pending or filled orders
   - If orders appear in IBKR portal, paper trading mode confirmed

2. If bot does not submit orders on startup (waiting for gameplan):
   - Provide a test gameplan (Strategy A or B with valid parameters)
   - Verify bot ingests gameplan and generates signals
   - Verify signals result in order submission (check IBKR portal)
   - If orders appear in IBKR portal, paper trading mode confirmed

3. Verify NO orders appear in live IBKR account:
   - CRITICAL: Log into LIVE IBKR account (NOT paper account)
   - Verify: ZERO pending or filled orders
   - If ANY orders appear in live account, EMERGENCY HALT:
     - Shutdown bot immediately
     - Cancel all live orders manually
     - Close all live positions manually
     - Escalate to CRO / Red Team for incident review
     - DO NOT resume until root cause identified and fixed

4. Document verification:
   - Update docs/Task_4_3_Transition_Log.md:
     - Timestamp of bot restart
     - Log excerpts confirming paper trading mode
     - Screenshot of IBKR paper account showing test order (if applicable)
     - Confirmation that NO live orders were placed

5. Monitor first hour of operation:
   - Keep bot running manually for 1 hour
   - Monitor logs continuously
   - Verify no unexpected errors or mode switches
   - Verify paper account activity reflects bot behavior

6. Transition to auto-start (Task Scheduler):
   - After 1 hour of stable manual operation, shutdown bot
   - Enable Task Scheduler task (if previously disabled)
   - Wait for next 6:00 AM ET auto-start
   - Verify bot starts in paper trading mode via Task Scheduler
   - Verify Discord notification confirms paper trading mode
```

**Post-Transition Monitoring (First 24 Hours):**

```
After transition, monitor closely for 24 hours:

1. Verify auto-start at 6:00 AM ET:
   - Check Discord for startup notification (paper trading mode)
   - Review logs for successful startup

2. Monitor order execution:
   - Check IBKR paper account for executed trades
   - Verify orders match bot strategy signals (log comparison)
   - Verify NO orders in live IBKR account

3. Monitor bot stability:
   - No crashes or unexpected shutdowns
   - Gateway reconnection after 4:30 PM ET restart (same as dry-run)
   - No error patterns in logs

4. Document first day of paper trading:
   - Update Task_4_3_Transition_Log.md with summary
   - Note any issues or anomalies
   - Confirm transition successful and stable
```

### 4. Dependencies

**Task 4.2 Completion Required:**
- Desktop deployment stability proven (5+ days dry-run validation)
- Zero-touch automation operational
- Operator authorization for transition

**IBKR Paper Trading Account:**
- Paper account must be accessible via Gateway (port 4002)
- Paper account credentials configured in Gateway
- Paper account funded (sufficient virtual capital for testing)

**No Code Changes Required:**
- Bot code already supports paper trading mode (Phase 3 implementation)

### 5. Input/Output Contract

**Input (Configuration Change):**
- .env file modification:
  - DRY_RUN: true → false
  - PAPER_TRADING: false → true

**Output (Paper Trading Mode Active):**
- Bot submits orders to IBKR paper account
- Orders visible in IBKR paper account portal
- NO orders in IBKR live account
- Discord notifications confirm paper trading mode
- Logs confirm paper trading mode activation

### 6. Integration Points

**IBKR Gateway Integration:**
- Gateway already configured for paper trading (port 4002)
- Bot connects to same Gateway, but now executes orders instead of logging signals

**IBKR Paper Account Integration:**
- Orders submitted via Gateway API to paper account
- Order status updates received via Gateway
- Portfolio positions tracked in paper account

**Discord Notifications Integration:**
- Startup notification must reflect paper trading mode
- Order execution notifications (if implemented) sent to Discord

**Task Scheduler Integration:**
- Bot continues to auto-start at 6:00 AM ET
- No changes to Task Scheduler configuration required

### 7. Definition of Done

Task 4.3 is complete when:

**Configuration Verified:**
- [ ] .env file modified: DRY_RUN=false, PAPER_TRADING=true
- [ ] No other .env settings changed unintentionally
- [ ] Configuration change committed to version control (with appropriate .gitignore for secrets)

**Paper Trading Mode Confirmed:**
- [ ] Bot logs show "Paper trading mode ACTIVE" on startup
- [ ] Discord notification confirms "PAPER TRADING mode"
- [ ] Orders submitted to IBKR paper account (verified in IBKR portal)
- [ ] NO orders submitted to IBKR live account (verified in IBKR portal)

**Stability Maintained:**
- [ ] Bot auto-starts at 6:00 AM ET via Task Scheduler (first day after transition)
- [ ] Bot reconnects to Gateway after 4:30 PM ET restart (first day after transition)
- [ ] No crashes or unexpected shutdowns in first 24 hours

**Documentation Complete:**
- [ ] docs/Task_4_3_Transition_Log.md created with transition details
- [ ] Screenshot of IBKR paper account showing test order (optional but recommended)
- [ ] Confirmation that live account has ZERO orders

**Operator Confirmation:**
- [ ] Operator reviews transition log and confirms paper trading mode active
- [ ] Operator declares: **"Paper trading transition successful, ready for Task 4.4"**
- [ ] IBKR Project Management board updated: Task 4.3 → Complete

### 8. Edge Cases to Test

**Accidental Live Trading Mode Activation:**
- **Scenario:** Configuration error results in orders sent to live IBKR account instead of paper account.
- **Detection:** Check live IBKR account for orders after bot startup.
- **Remediation (EMERGENCY):**
  1. Shutdown bot immediately (Task Manager → End Task)
  2. Cancel all live orders in IBKR portal
  3. Close all live positions in IBKR portal
  4. Verify .env settings (DRY_RUN=false, PAPER_TRADING=true)
  5. Verify Gateway configured for paper trading (port 4002)
  6. Escalate to CRO / Red Team for incident review
  7. Do NOT resume until root cause identified and verified fixed

**Configuration Not Loaded (Bot Still in Dry-Run Mode):**
- **Scenario:** Bot restarts but logs show "DRY_RUN mode active" despite .env changes.
- **Detection:** Bot logs or Discord notification still reference dry-run mode.
- **Diagnosis:**
  - Verify .env file saved correctly (no typos, correct syntax)
  - Verify bot reads .env file on startup (check configuration loading logic)
  - Verify environment variables not overridden elsewhere (system env vars, etc.)
- **Remediation:** Fix configuration loading logic, re-test transition.

**Gateway Connection to Wrong Account:**
- **Scenario:** Gateway configured for live account, bot connects and submits orders to live account.
- **Detection:** Orders appear in live IBKR account instead of paper account.
- **Prevention:** Verify Gateway configuration BEFORE transition (Gateway should be on port 4002 for paper).
- **Remediation:** Same as "Accidental Live Trading Mode Activation" above.

**Paper Account Insufficient Funds:**
- **Scenario:** Paper account has insufficient virtual capital for bot's position sizing.
- **Detection:** Orders rejected by IBKR (insufficient funds error in logs).
- **Diagnosis:** Check paper account balance in IBKR portal.
- **Remediation:** Reset paper account to higher virtual capital (IBKR portal settings).

**Bot Submits Orders During Non-Market Hours:**
- **Scenario:** Bot auto-starts at 6:00 AM ET (pre-market), submits orders before market open.
- **Expected Behavior:** Orders queued as "pending" until market opens at 9:30 AM ET.
- **Verification:** Check IBKR paper account for pending orders. Orders should fill at market open.
- **If Unexpected:** Review bot strategy logic (should it wait for market open before submitting?).

**Discord Notification Incorrect:**
- **Scenario:** Discord notification says "DRY-RUN mode" or "LIVE mode" after transition.
- **Detection:** Discord message does not match expected "PAPER TRADING mode" text.
- **Diagnosis:** Check bot code for Discord notification logic (ensure it reads PAPER_TRADING env var).
- **Remediation:** Fix notification logic, restart bot, verify corrected message.

**Task Scheduler Auto-Start After Transition:**
- **Scenario:** Bot auto-starts at 6:00 AM ET (first day after transition), but mode reverts to dry-run.
- **Detection:** Discord notification or logs show dry-run mode instead of paper trading.
- **Diagnosis:** .env file not persisted correctly, or Task Scheduler using cached configuration.
- **Remediation:** Re-verify .env file saved, restart bot manually to confirm mode, then re-enable Task Scheduler.

### 9. Rollback Plan

**If Task 4.3 Transition Fails or Issues Discovered:**

1. **Immediate Rollback to Dry-Run Mode:**
   - Shutdown bot (Task Manager → End Task)
   - Edit .env file:
     - DRY_RUN=true (revert to dry-run)
     - PAPER_TRADING=false (disable paper trading)
   - Save .env file and verify changes
   - Restart bot manually, verify dry-run mode active
   - Re-enable Task Scheduler auto-start (if disabled)

2. **Close All Paper Trading Positions:**
   - Log into IBKR paper account portal
   - Navigate to Portfolio → Positions
   - Close all open positions manually
   - Cancel all pending orders

3. **Document Rollback:**
   - Update docs/Task_4_3_Transition_Log.md with rollback details
   - Note reason for rollback (what issue was discovered)
   - Create GitHub issue or project board task for remediation

4. **Diagnose and Remediate:**
   - Identify root cause of transition failure
   - Fix configuration, code, or process issue
   - Re-test in dry-run mode if code changes made
   - Re-attempt Task 4.3 transition after fix validated

**If Accidental Live Trading Detected:**
- Follow emergency halt procedure (see Edge Cases above)
- Escalate to CRO / Red Team for incident review
- Do NOT resume trading until Red Team approves remediation plan

---

## IMPLEMENTATION NOTES

### For the Factory Floor Engineer (VSC Copilot User)

**This is a configuration change task.** The transition from dry-run to paper trading is controlled entirely by environment variables. No code changes are required unless configuration loading logic is broken.

**Critical Safety Checks:**

1. **ALWAYS verify .env file after editing:**
   - Re-open .env file and visually confirm DRY_RUN=false, PAPER_TRADING=true
   - Do NOT rely on memory — verify visually every time

2. **ALWAYS verify paper account before assuming success:**
   - Log into IBKR paper account portal after bot startup
   - Confirm orders appear in paper account (if bot submits orders)
   - Confirm NO orders appear in live account

3. **ALWAYS monitor first hour of operation:**
   - Do not walk away after transition — stay at desk, monitor logs
   - If anything unexpected happens, shutdown immediately and diagnose

**Task_4_3_Transition_Log.md Template:**

```markdown
# Task 4.3 Transition Log — Paper Trading Mode Activation

**Transition Date:** [YYYY-MM-DD]
**Task 4.2 Completion:** [Date Task 4.2 approved]
**Operator Authorization:** [Operator Name, Date]

---

## Pre-Transition Checklist

- [ ] Task 4.2 stability summary reviewed and approved
- [ ] All 6 stability criteria met
- [ ] Operator explicitly authorized transition
- [ ] IBKR paper trading account accessible

---

## Step 1: Controlled Shutdown

**Shutdown Timestamp:** [HH:MM ET, YYYY-MM-DD]
**Shutdown Method:** [Manual Task Manager / Wait for 4:30 PM Gateway restart]
**Last Log Entry:** [Paste final log entry showing clean shutdown]
**Open Positions in IBKR Paper Account:** [ZERO expected]

---

## Step 2: Configuration Update

**Before (Dry-Run Mode):**
```
DRY_RUN=true
PAPER_TRADING=false
```

**After (Paper Trading Mode):**
```
DRY_RUN=false
PAPER_TRADING=true
```

**Verification:**
- [✅ / ❌] .env file re-opened and visually confirmed
- [✅ / ❌] No other settings changed unintentionally

---

## Step 3: Bot Restart (Manual)

**Restart Timestamp:** [HH:MM ET, YYYY-MM-DD]
**Startup Logs (Excerpt):**
```
[Paste key log entries showing paper trading mode activation]
```

**Discord Notification:**
- Expected: "Bot started in PAPER TRADING mode at [timestamp]"
- Actual: [Paste actual message]
- [✅ / ❌] Notification confirms paper trading mode

---

## Step 4: Paper Trading Mode Verification

**Test Order Submission:**
- [✅ / ❌] Orders submitted to IBKR paper account (verified in portal)
- [✅ / ❌] NO orders submitted to IBKR live account (verified in portal)

**IBKR Paper Account Screenshot:**
[Insert screenshot showing test order or position, if applicable]

**IBKR Live Account Verification:**
- [✅ / ❌] ZERO orders in live account (verified in portal)

**First Hour Monitoring:**
- [✅ / ❌] No crashes or unexpected shutdowns
- [✅ / ❌] No mode switches or errors in logs
- [✅ / ❌] Paper account activity reflects bot behavior

---

## First 24 Hours Post-Transition

**Auto-Start (6:00 AM ET):**
- [✅ / ❌] Bot auto-started via Task Scheduler
- [✅ / ❌] Discord notification confirmed paper trading mode
- [✅ / ❌] Logs show successful startup

**Order Execution:**
- [✅ / ❌] Orders executed in paper account (if market open)
- [✅ / ❌] NO orders in live account

**Stability:**
- [✅ / ❌] Gateway reconnection after 4:30 PM ET restart
- [✅ / ❌] No crashes or unexpected shutdowns
- [✅ / ❌] No error patterns in logs

**Summary:** [Brief summary of first 24 hours]

---

## Transition Verdict

**Status:** [SUCCESS / NEEDS REMEDIATION]
**Operator Confirmation:** [Operator Name, Date]
**Next Step:** [Proceed to Task 4.4 / Address issues and retry]

---

**END OF TRANSITION LOG**
```

**Emergency Contacts (If Issues Occur):**
- @CRO (risk/capital concerns)
- @DevOps (technical issues)
- @PM (project escalation)

---

## VSC COPILOT PROMPTS (OPTIONAL ASSISTANCE)

If you need Copilot's help with verification or troubleshooting, here are some example prompts:

**Prompt 1: .env File Verification**
```
Review this .env file and verify that paper trading mode is correctly configured. Check for:
1. DRY_RUN=false
2. PAPER_TRADING=true
3. No other settings changed from dry-run configuration

[paste .env contents]
```

**Prompt 2: Log Analysis for Mode Confirmation**
```
Analyze these bot startup logs and confirm whether paper trading mode is active. Look for:
1. "Paper trading mode ACTIVE" or similar confirmation
2. NO "DRY_RUN mode" or "Live trading mode" messages
3. Gateway connection successful
4. Configuration loaded correctly

[paste startup logs]
```

**Prompt 3: Order Submission Verification**
```
I need to verify that orders are being submitted to the paper account, not the live account. Help me:
1. Check IBKR paper account portal for pending/filled orders
2. Verify IBKR live account has ZERO orders
3. Compare bot logs (order IDs) with IBKR portal (confirm match)

[provide access to IBKR portal or describe what you see]
```

---

**END OF VSC HANDOFF: Task 4.3**
