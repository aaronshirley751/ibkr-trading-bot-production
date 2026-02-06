# VSC HANDOFF: Runtime Validation Execution — IMMEDIATE

**URGENT:** Markets close in ~100 minutes. Execute NOW.

---

## MISSION BRIEF

Execute Phase 4 supervised runtime validation of IBKR snapshot capture script to verify safety mechanisms and data collection functionality with live Gateway connection.

**Success Criteria:**
- Account type verification triggers and displays "PAPER"
- Data captured for all 3 symbols (SPY, QQQ, IWM)
- Snapshot file created with valid structure
- No safety violations

**Duration:** 15-20 minutes

---

## EXECUTION SEQUENCE

### STEP 1: Pre-Flight Verification (30 seconds)

```powershell
# Navigate to project root
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production

# Verify Gateway is connected
# CHECK: IBKR Gateway window shows "Connected" status on port 4002

# Verify script exists
ls scripts\capture_ibkr_snapshot.py
```

**Expected Output:** Script file listed

---

### STEP 2: Execute Supervised Test (10-15 minutes)

```powershell
# Run snapshot capture with validation scenario
python scripts\capture_ibkr_snapshot.py --scenario validation_test
```

**CRITICAL CHECKPOINTS — Monitor Console Output:**

✅ **Checkpoint 1:** Safety banner displays
✅ **Checkpoint 2:** Prompt: "Continue with snapshot capture? (yes/no):"
   - **ACTION:** Type `yes` and press Enter
✅ **Checkpoint 3:** "Connecting to IBKR Gateway on port 4002..."
✅ **Checkpoint 4:** "✓ Connected successfully"
✅ **Checkpoint 5:** "SAFETY CHECK: Verifying account type..."
✅ **Checkpoint 6:** **CRITICAL** — Must display: "Account Type: PAPER"
✅ **Checkpoint 7:** **CRITICAL** — Must display: "✓ VERIFIED: Paper trading account confirmed"
✅ **Checkpoint 8:** Data capture begins for SPY, QQQ, IWM
✅ **Checkpoint 9:** Progress updates for each symbol
✅ **Checkpoint 10:** "Snapshot saved to: tests/fixtures/ibkr_snapshots/..."

**If ANY checkpoint fails:** Stop immediately, capture error message, report to @QA_Lead

---

### STEP 3: Verify Snapshot File Created (1 minute)

```powershell
# List snapshot directory
ls tests\fixtures\ibkr_snapshots\

# Expected files:
# - snapshot_validation_test_YYYYMMDD_HHMMSS.json (timestamped)
# - snapshot_validation_test_latest.json (symlink/copy)
```

**Expected Output:** Two JSON files listed with today's date

---

### STEP 4: Validate Snapshot Structure (2 minutes)

```powershell
# Run validation utility
python scripts\validate_snapshot.py tests\fixtures\ibkr_snapshots\snapshot_validation_test_latest.json
```

**Expected Output:**
```
✓ JSON structure valid
✓ Scenario: validation_test
✓ Symbols present: SPY, QQQ, IWM
✓ SPY: current_price present, 20+ historical bars, 10+ option contracts
✓ QQQ: current_price present, 20+ historical bars, 10+ option contracts
✓ IWM: current_price present, 20+ historical bars, 10+ option contracts
✓ Snapshot validation PASSED
```

---

### STEP 5: Quick Visual Inspection (1 minute)

```powershell
# Display snapshot summary
python -c "import json; data = json.load(open('tests/fixtures/ibkr_snapshots/snapshot_validation_test_latest.json')); print(f'Scenario: {data[\"scenario\"]}'); print(f'Timestamp: {data[\"timestamp\"]}'); [print(f'{sym}: Price=${data[\"symbols\"][sym][\"currentPrice\"]}, Bars={len(data[\"symbols\"][sym][\"historicalBars\"])}, Options={len(data[\"symbols\"][sym][\"optionChain\"])}') for sym in data['symbols']]"
```

**Expected Output:**
```
Scenario: validation_test
Timestamp: 2026-02-06T14:xx:xx
SPY: Price=$xxx.xx, Bars=60, Options=10+
QQQ: Price=$xxx.xx, Bars=60, Options=10+
IWM: Price=$xxx.xx, Bars=60, Options=10+
```

---

## SUCCESS VALIDATION CHECKLIST

**All checkpoints must PASS:**
- [ ] Safety banner displayed
- [ ] User confirmation required
- [ ] Connection established to port 4002
- [ ] Account type verification ran automatically
- [ ] Console displayed "Account Type: PAPER"
- [ ] Console displayed "✓ VERIFIED: Paper trading account confirmed"
- [ ] Data captured for SPY, QQQ, IWM
- [ ] Snapshot file created
- [ ] Validation utility passed
- [ ] Visual inspection shows valid prices and data

**If ALL PASS:** Report SUCCESS to @QA_Lead for final sign-off

**If ANY FAIL:** Capture exact error message and report immediately

---

## EMERGENCY ABORT CONDITIONS

**If you see ANY of these messages, STOP IMMEDIATELY:**

🔴 "SAFETY VIOLATION: Account type is LIVE"
🔴 "Connection failed"
🔴 "Gateway not responding"
🔴 "Timeout waiting for account verification"

**Emergency Contact:** Report to @Chief_of_Staff with exact error

---

## POST-EXECUTION REPORT

**After successful completion:**

### 1. Capture Results

```powershell
# Verify snapshot files exist
ls tests\fixtures\ibkr_snapshots\snapshot_validation_test_*

# Expected: Two files with today's timestamp
```

### 2. Report Template

Copy and paste this to report back:

```
RUNTIME VALIDATION PHASE 4 - EXECUTION REPORT

Execution Time: [HH:MM AM/PM ET]
Duration: [X minutes]

CHECKPOINT RESULTS:
✅/❌ Safety banner displayed
✅/❌ User confirmation required
✅/❌ Connection established
✅/❌ Account type: PAPER verified
✅/❌ Data captured: SPY, QQQ, IWM
✅/❌ Snapshot file created
✅/❌ Validation utility passed

SNAPSHOT FILES CREATED:
- snapshot_validation_test_[TIMESTAMP].json
- snapshot_validation_test_latest.json

SAMPLE DATA:
SPY: Price=$XXX.XX, Bars=XX, Options=XX
QQQ: Price=$XXX.XX, Bars=XX, Options=XX
IWM: Price=$XXX.XX, Bars=XX, Options=XX

OVERALL STATUS: ✅ SUCCESS / ❌ FAILED

[Any errors or issues encountered:]
[None / Error details here]
```

### 3. Await Team Sign-Off

- @QA_Lead: Final validation approval
- @CRO: Safety mechanism confirmation
- @PM: Board update (Chunk 5 → 100% complete, Chunk 6 unblocked)

---

## TIMING CRITICAL

**Current Time:** ~2:20 PM ET
**Market Close:** 4:00 PM ET
**Available Window:** ~100 minutes
**Required Time:** 15-20 minutes

## 🚀 GO NOW — EXECUTE IMMEDIATELY

---

**Document Version:** 1.0 - URGENT EXECUTION
**Created:** 2026-02-06 14:20 ET
**Reference:** Task 1.1.2 Chunk 5 Runtime Validation
**Commit:** 1bd71e0 (snapshot script), c8829fc (validation utility)
