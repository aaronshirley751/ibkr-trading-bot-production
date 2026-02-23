# VSC HANDOFF: Task 4.2 — Extended Dry-Run Validation (5+ Days)

**Date:** 2026-02-10
**Phase:** Phase 4 Sprint — Desktop-First Deployment
**Requested By:** @PM, @QA_Lead, @CRO
**Model Recommendation:** Sonnet (monitoring and validation work, moderate complexity)
**Context Budget:** Light (primarily monitoring, minimal code changes expected)
**VSC Template Version:** v2.0

---

## CONTEXT BLOCK

### Strategic Purpose

Task 4.2 validates desktop deployment stability through extended dry-run operation (5+ days, performance-based transition criteria). This is a **monitoring and validation task**, not a feature development task. The bot must demonstrate zero-touch automation, zero crashes, and stable resource usage before transitioning to paper trading.

**Key Success Criteria:** Stability quality, not arbitrary time gates. If the bot demonstrates rock-solid operation after 3 days, early transition to paper trading is authorized.

### Related Documents

- `PHASE_4_SPRINT_PLAN_Desktop_First_Deployment.md` — Full sprint plan and stability criteria
- `VSC_HANDOFF_Task_4_1_Desktop_Deployment.md` — Desktop deployment prerequisites
- Task 4.1 completion required before starting Task 4.2

### Deployment State Assumptions

**Prerequisites (Task 4.1 Complete):**
- Bot auto-starts at 6:00 AM ET via Task Scheduler
- Bot connects to Gateway (localhost:4002) successfully
- Discord notifications operational
- Gateway restarts at 4:30 PM ET via IBC Controller
- Bot operates in dry-run mode (`DRY_RUN=true`)

**Monitoring Objective:** Prove the bot can operate continuously for 5+ days (or fewer if stability criteria met) without manual intervention, crashes, or degradation.

---

## AGENT EXECUTION BLOCK

### 1. Objective

Validate desktop deployment stability through extended dry-run operation. Monitor bot behavior, log quality, resource usage, and automation reliability over a multi-day period. Identify and remediate any instability patterns before transitioning to paper trading.

**This is NOT a coding task.** The bot code is already operational (Phase 3 complete). This task focuses on:
1. **Monitoring:** Daily log reviews, resource usage tracking, Discord notification verification
2. **Logging Enhancements (Optional):** Improve log output for better validation visibility (if current logs insufficient)
3. **Validation:** Confirm all stability criteria met before declaring Task 4.2 complete

### 2. File Structure

**No new application code expected.** Monitoring enhancements only if needed.

**Potential Files to Create/Modify (Optional):**

```
project_root/
├── scripts/
│   ├── log_analysis.py              # Optional: Script to parse logs and extract metrics
│   ├── resource_monitor.py          # Optional: Script to track CPU/memory usage
│   └── stability_report.py          # Optional: Script to generate daily stability summary
├── logs/                             # Log directory (monitor for rotation, disk usage)
│   └── crucible_bot.log              # Primary bot log (review daily)
├── monitoring/
│   └── daily_reports/                # Optional: Store daily stability summaries
│       ├── 2026-02-10_report.md
│       ├── 2026-02-11_report.md
│       └── ...
└── docs/
    └── Task_4_2_Validation_Log.md    # Daily monitoring log (REQUIRED — create this)
```

**REQUIRED File:**
- `docs/Task_4_2_Validation_Log.md` — Daily log of stability observations, issues, and progress toward stability criteria

### 3. Logic Flow (Monitoring Protocol)

**Daily Monitoring Routine (6 Steps):**

```
Step 1: Verify Auto-Start (6:00 AM ET Daily)
-------------------------------------------
- Check Discord for bot startup notification
- Expected message: "Bot started in DRY-RUN mode at [timestamp]"
- If no notification received:
  - Check Task Scheduler "Last Run Result" for errors
  - Check bot logs for startup failures
  - Diagnose and remediate issue
  - Document in Task_4_2_Validation_Log.md

Step 2: Review Overnight Logs (9:00 AM ET Daily)
-------------------------------------------------
- Open logs/crucible_bot.log
- Scan for errors, warnings, or exceptions since last review
- Key checks:
  - [ ] No Python tracebacks or exceptions
  - [ ] Gateway connection stable (no repeated reconnection attempts)
  - [ ] No "CRITICAL" or "ERROR" level log entries (warnings acceptable if non-blocking)
  - [ ] Dry-run mode confirmed in logs
- If issues found:
  - Document in Task_4_2_Validation_Log.md
  - Classify severity (CRITICAL / MAJOR / MODERATE / ADVISORY)
  - Remediate if CRITICAL or MAJOR (may require code fix)

Step 3: Verify Strategy Signals (If Market Open Day)
-----------------------------------------------------
- Check logs for strategy signal generation
- Expected behavior:
  - Bot ingests gameplan (if gameplan provided)
  - RSI, EMA, VWAP calculations logged
  - Strategy signals generated (Strategy A, B, or C selected)
  - NO actual orders sent (dry-run mode)
- Verify no logic errors in strategy execution paths
- Document any anomalies in Task_4_2_Validation_Log.md

Step 4: Verify Gateway Restart & Reconnection (4:30 PM ET Daily)
-----------------------------------------------------------------
- Gateway restarts at 4:30 PM ET via IBC Controller
- Verify bot reconnects WITHOUT manual intervention:
  - Check bot logs for disconnection detection
  - Check bot logs for reconnection attempts
  - Check bot logs for successful reconnection
  - Expected timeline: Disconnection at 4:30 PM, reconnection within 2-5 minutes
- If reconnection fails or requires manual intervention:
  - Document in Task_4_2_Validation_Log.md as CRITICAL issue
  - Remediate reconnection logic (may require code fix)

Step 5: End-of-Day Log Review (5:00 PM ET Daily)
-------------------------------------------------
- Review full day's logs (6:00 AM - 5:00 PM ET)
- Check for:
  - Resource usage warnings (CPU, memory, disk)
  - Any error patterns (repeated errors suggesting systemic issue)
  - Log rotation status (logs not exceeding 100 MB total)
- Review Discord notifications (all expected notifications received?)
- Document daily summary in Task_4_2_Validation_Log.md

Step 6: Resource Usage Tracking (Daily)
----------------------------------------
- Check Windows Task Manager or Resource Monitor:
  - Bot process CPU usage (should be low — < 5% on average)
  - Bot process memory usage (should be stable — no memory leak)
  - Disk usage in logs/ directory (should rotate, not grow indefinitely)
- If resource usage abnormal:
  - Document in Task_4_2_Validation_Log.md
  - Investigate cause (inefficient polling? memory leak? log rotation failure?)
  - Remediate if necessary (code optimization or configuration fix)
```

**Weekly Summary (End of 5-Day Validation):**

```
After 5 days (or fewer if stability proven):
1. Review all daily entries in Task_4_2_Validation_Log.md
2. Verify all 6 stability criteria met (see Acceptance Criteria below)
3. Generate stability summary report:
   - Total days monitored
   - Total bot uptime (hours)
   - Total manual interventions required (should be ZERO)
   - Total crashes or unexpected shutdowns (should be ZERO)
   - Total error patterns identified (should be ZERO)
   - Resource usage trends (CPU, memory, disk — all stable)
4. Declare Task 4.2 complete if all criteria met
5. If criteria not met, extend monitoring period or remediate issues
```

### 4. Dependencies

**Task 4.1 Completion Required:**
- Bot must be deployed to desktop and auto-starting successfully
- Gateway must be operational and stable
- Discord notifications must be functional

**External Tools (Optional):**
- **Windows Task Manager / Resource Monitor:** For resource usage tracking
- **Windows Event Viewer:** For system-level diagnostics (if needed)
- **Log analysis tools (optional):** grep, awk, or Python scripts for log parsing

**No Additional Python Dependencies:**
- Monitoring uses existing bot logs and system tools

### 5. Input/Output Contract

**Input (Daily Monitoring Data):**
- Bot logs (logs/crucible_bot.log)
- Discord notification history
- Task Scheduler execution history
- Windows Task Manager resource usage data
- Operator observations (manual checks)

**Output (Validation Artifacts):**
- `docs/Task_4_2_Validation_Log.md` — Daily monitoring log with entries for each day
- Stability summary report (at end of validation period)
- List of issues identified and remediated (if any)
- GO / NO-GO recommendation for Task 4.3 (paper trading transition)

### 6. Integration Points

**Bot Logs Integration:**
- Daily log review is primary validation method
- Logs must provide sufficient visibility into bot behavior
- If logs insufficient, logging enhancements may be required (see Edge Cases)

**Discord Notifications Integration:**
- Discord serves as secondary validation channel
- Notifications confirm bot startup, errors, and key events
- Missing notifications indicate bot failure or configuration issue

**Task Scheduler Integration:**
- Task Scheduler execution history confirms auto-start reliability
- Task Scheduler "Last Run Result" provides diagnostic info if auto-start fails

**IBC Controller Integration:**
- Gateway restart at 4:30 PM ET must be reliable
- Bot reconnection logic must handle Gateway restart gracefully

### 7. Definition of Done

Task 4.2 is complete when **ALL** of the following stability criteria are met:

**Stability Criteria (All Required):**

1. **Zero Unexpected Shutdowns or Crashes**
   - [ ] Bot runs continuously without manual restarts
   - [ ] No Python exceptions causing process termination
   - [ ] No unhandled errors in logs requiring intervention

2. **Zero Manual Interventions Required (True Zero-Touch)**
   - [ ] Bot auto-starts every morning at 6:00 AM ET (Task Scheduler)
   - [ ] Bot reconnects to Gateway after 4:30 PM ET restart (no manual help)
   - [ ] No operator intervention needed to maintain operation

3. **Health Checks Functioning Correctly**
   - [ ] Discord notifications sent on bot startup (every day)
   - [ ] Discord notifications sent on errors or warnings (if applicable)
   - [ ] Health check endpoint responsive (if implemented)

4. **Strategy Signals Generating Correctly**
   - [ ] Dry-run mode confirms strategy logic executing (if market open days)
   - [ ] Gameplan ingestion operational (if implemented)
   - [ ] RSI, EMA, VWAP calculations producing expected signals (log review)
   - [ ] No logic errors in strategy execution paths

5. **Resource Usage Stable**
   - [ ] CPU usage within acceptable range (< 5% average)
   - [ ] Memory usage stable (no memory leaks over multi-day operation)
   - [ ] Disk usage stable (log rotation functioning correctly, logs < 100 MB total)

6. **Log Analysis Shows No Error Patterns or Degradation**
   - [ ] No repeated error messages indicating systemic issues
   - [ ] No warning patterns suggesting degradation over time
   - [ ] Logs show consistent, predictable operation

**Minimum Duration:**
- 5 consecutive days preferred
- **May be shortened if all stability criteria are met sooner** (e.g., 3 days if rock-solid)

**Documentation Complete:**
- [ ] `docs/Task_4_2_Validation_Log.md` contains daily entries for each monitoring day
- [ ] Stability summary report generated (can be in Task_4_2_Validation_Log.md or separate file)
- [ ] All issues identified and remediated (or documented as acceptable)

**Operator Confirmation:**
- [ ] Operator reviews stability summary and confirms all criteria met
- [ ] Operator declares: **"Dry-run validation complete, ready for Task 4.3 (paper trading)"**
- [ ] IBKR Project Management board updated: Task 4.2 → Complete

### 8. Edge Cases to Test

**Insufficient Log Visibility:**
- **Scenario:** Bot logs do not provide enough detail to validate strategy signals or resource usage.
- **Action:** Enhance logging (increase LOG_LEVEL to DEBUG, add specific log statements for key events).
- **Code Change Required:** Minimal (add log statements in strategy execution paths).

**Weekend / Non-Market Days:**
- **Scenario:** Monitoring period includes weekends when market is closed.
- **Action:** Bot should remain operational on weekends (idle state). Verify auto-start and Gateway connection on weekend days.
- **Expected Behavior:** Bot starts, connects, idles (no strategy signals on non-market days), shuts down cleanly.

**Market Holidays:**
- **Scenario:** Monitoring period includes market holiday (e.g., President's Day).
- **Action:** Same as weekend behavior — bot operational but idle.

**Gateway Unexpected Restart (Outside 4:30 PM ET Schedule):**
- **Scenario:** Gateway crashes or is manually restarted by operator during market hours.
- **Action:** Bot should detect disconnection and auto-reconnect (same as scheduled restart).
- **Expected Behavior:** Bot reconnects within 2-5 minutes, logs reconnection, continues operation.

**Bot Process Killed Manually (Operator Test):**
- **Scenario:** Operator manually kills bot process (Task Manager → End Task) during monitoring period.
- **Action:** Bot does NOT auto-restart until next 6:00 AM ET scheduled start.
- **Expected Behavior:** Bot remains down until next Task Scheduler trigger. Task Scheduler does not restart on manual termination.
- **Note:** This is expected behavior — Task Scheduler only restarts on failure, not manual termination.

**Disk Space Low:**
- **Scenario:** Logs/ directory grows, disk space approaches limit.
- **Action:** Log rotation should prevent this. If disk space warning appears, verify log rotation working correctly.
- **Remediation:** Increase LOG_BACKUP_COUNT in .env, or manually delete old logs if rotation failed.

**Windows Update / Forced Reboot:**
- **Scenario:** Windows forces update and reboot during monitoring period (likely overnight).
- **Action:** Desktop reboots, Task Scheduler auto-starts bot at next 6:00 AM ET.
- **Expected Behavior:** Bot starts successfully after reboot, no manual intervention.
- **If This Occurs:** Document in Task_4_2_Validation_Log.md as "Reboot during monitoring — bot recovered successfully."

**Error Pattern Detection (Repeated Warnings):**
- **Scenario:** Logs show repeated warning messages (e.g., "Gateway connection slow" appearing every 5 minutes).
- **Action:** Investigate root cause. Is this a real issue or benign warning?
- **Severity Classification:**
  - **CRITICAL:** Error prevents bot from operating → remediate immediately.
  - **MAJOR:** Warning indicates potential future failure → remediate before Task 4.3.
  - **MODERATE:** Warning is benign or rare → document, monitor, may remediate later.
  - **ADVISORY:** Informational only → no action required.

**Dry-Run Mode Accidental Deactivation:**
- **Scenario:** .env file modified, DRY_RUN set to false (either intentionally or by mistake).
- **Action:** Verify DRY_RUN=true on every daily log review.
- **If Deactivated:** Immediately shut down bot, revert .env to DRY_RUN=true, restart bot.
- **Severity:** CRITICAL if discovered — dry-run mode is mandatory for Task 4.2.

### 9. Rollback Plan

**If Task 4.2 Validation Fails (Stability Criteria Not Met):**

1. **Identify Failure Mode:**
   - Review Task_4_2_Validation_Log.md for all issues documented
   - Classify issues by severity (CRITICAL / MAJOR / MODERATE / ADVISORY)
   - Determine if issues are systemic (requiring code changes) or environmental (configuration)

2. **Remediate CRITICAL and MAJOR Issues:**
   - If code changes required, return to Factory Floor (VSC) for implementation
   - If configuration changes required, update .env, Task Scheduler, or IBC config
   - Test remediation manually before resuming validation

3. **Restart Validation Period:**
   - After remediation, restart Task 4.2 monitoring from Day 1
   - Document remediation in Task_4_2_Validation_Log.md
   - Proceed with fresh 5-day validation period (or until stability proven)

4. **Escalate to Red Team if Repeated Failures:**
   - If Task 4.2 fails multiple times despite remediation, convene Red Team review
   - Red Team will assess whether desktop deployment strategy is viable
   - Potential outcomes: Architectural redesign, infrastructure change, or process improvement

**If Validation Extended Beyond 5 Days:**
- **Acceptable:** Validation may run 7-10 days if stability takes longer to prove
- **Not Acceptable:** Validation running indefinitely without progress → escalate to Red Team
- **Decision Point:** If no progress toward stability after 10 days, halt and reassess deployment strategy

---

## IMPLEMENTATION NOTES

### For the Factory Floor Engineer (VSC Copilot User)

**This is a monitoring task, not a coding task.** Your primary responsibility is to **observe and document** bot behavior over 5+ days. Code changes are only required if logs are insufficient or if issues are discovered that require remediation.

**Daily Monitoring Workflow:**

1. **Morning (9:00 AM ET):**
   - Check Discord for bot startup notification (6:00 AM ET)
   - Review overnight logs (since last review)
   - Document observations in `docs/Task_4_2_Validation_Log.md`

2. **Afternoon (5:00 PM ET):**
   - Review full day's logs
   - Check resource usage (Task Manager)
   - Verify Gateway restart and bot reconnection (4:30 PM ET)
   - Update Task_4_2_Validation_Log.md with daily summary

3. **End of Week:**
   - Review all daily entries
   - Generate stability summary report
   - Determine if stability criteria met (GO / NO-GO for Task 4.3)

**Task_4_2_Validation_Log.md Template:**

```markdown
# Task 4.2 Validation Log — Extended Dry-Run Monitoring

**Validation Period:** [Start Date] to [End Date]
**Stability Criteria Target:** 5+ consecutive days (or fewer if stability proven)

---

## Day 1: [YYYY-MM-DD]

**Auto-Start (6:00 AM ET):**
- [ ] Discord notification received
- [ ] Task Scheduler execution successful
- [ ] Bot logs show successful startup

**Overnight Logs (6:00 AM - 9:00 AM):**
- [ ] No errors or exceptions
- [ ] Gateway connection stable
- [ ] Dry-run mode confirmed

**Strategy Signals (If Market Open):**
- [ ] Gameplan ingested (if provided)
- [ ] Signals generated correctly
- [ ] No logic errors

**Gateway Restart (4:30 PM ET):**
- [ ] Gateway restarted via IBC Controller
- [ ] Bot reconnected without manual intervention
- [ ] Reconnection logged

**End-of-Day Summary:**
- [ ] No manual interventions required
- [ ] No crashes or unexpected shutdowns
- [ ] Resource usage stable
- [ ] Logs show consistent operation

**Issues Identified:** [None / List issues with severity]

**Notes:** [Any additional observations]

---

## Day 2: [YYYY-MM-DD]

[Same structure as Day 1]

---

[Continue for each day of validation]

---

## Stability Summary Report

**Total Days Monitored:** [N]
**Total Bot Uptime:** [Hours]
**Total Manual Interventions:** [0 expected]
**Total Crashes:** [0 expected]
**Total Error Patterns:** [0 expected]

**Stability Criteria Assessment:**
1. Zero Unexpected Shutdowns: [✅ / ❌]
2. Zero Manual Interventions: [✅ / ❌]
3. Health Checks Functional: [✅ / ❌]
4. Strategy Signals Correct: [✅ / ❌]
5. Resource Usage Stable: [✅ / ❌]
6. No Error Patterns: [✅ / ❌]

**Verdict:** [GO / NO-GO for Task 4.3]

**Operator Approval:** [Operator Name, Date]
```

**Logging Enhancements (If Needed):**

If current logs do not provide sufficient visibility for validation, you may need to enhance logging. Example changes:

```python
# In strategy execution code, add DEBUG-level logs:
logger.debug(f"Strategy A selected: VIX={vix}, RSI={rsi}, EMA_Fast={ema_fast}, EMA_Slow={ema_slow}")
logger.debug(f"DRY_RUN mode active — signal generated but not executed")

# In reconnection logic, add INFO-level logs:
logger.info("Gateway disconnection detected — initiating reconnection...")
logger.info(f"Reconnection attempt {attempt_count}/{max_attempts}")
logger.info("Gateway reconnection successful")

# In resource monitoring (optional), log resource usage periodically:
logger.info(f"Resource check: CPU={cpu_pct}%, Memory={memory_mb}MB, Disk={disk_gb}GB")
```

**When to Escalate:**

- **CRITICAL issue discovered:** Escalate immediately to Boardroom (convene @DevOps or @CRO session)
- **Repeated MAJOR issues:** Document pattern, escalate to Red Team review
- **Validation taking longer than 10 days:** Escalate to Red Team for strategy reassessment

---

## VSC COPILOT PROMPTS (OPTIONAL ASSISTANCE)

If you need Copilot's help with monitoring or log analysis, here are some example prompts:

**Prompt 1: Log Analysis Script**
```
Create a Python script that parses the bot log file (logs/crucible_bot.log) and extracts key metrics:
1. Count of ERROR and WARNING log entries
2. Bot uptime (time between startup and shutdown)
3. Gateway reconnection events (count and timestamps)
4. Dry-run mode confirmations (verify DRY_RUN=true in logs)
5. Output a daily summary report

Save the script as scripts/log_analysis.py and make it runnable from the command line.
```

**Prompt 2: Resource Monitoring Script**
```
Create a Python script that uses psutil to monitor the bot process:
1. CPU usage (percentage)
2. Memory usage (MB)
3. Disk usage for logs/ directory (GB)
4. Log these metrics every 5 minutes to a CSV file (monitoring/resource_usage.csv)

Save the script as scripts/resource_monitor.py and make it runnable in the background.
```

**Prompt 3: Stability Summary Report Generator**
```
Given the Task_4_2_Validation_Log.md file, generate a stability summary report that:
1. Counts total days monitored
2. Verifies all 6 stability criteria met (yes/no for each)
3. Lists any issues identified and their severity
4. Produces a GO / NO-GO recommendation for Task 4.3

Save the output as docs/Task_4_2_Stability_Summary.md
```

---

**END OF VSC HANDOFF: Task 4.2**
