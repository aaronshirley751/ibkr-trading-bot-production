# RUNTIME VALIDATION: Task 1.1.2 Chunk 5 - IBKR Snapshot Script

**Document ID:** `RUNTIME_VALIDATION_chunk_5_snapshot_script.md`
**Created:** 2026-02-06
**Author:** @Systems_Architect
**Validation Lead:** @QA_Lead
**Safety Oversight:** @CRO
**Implementation Reference:** Commit [1bd71e0](https://github.com/aaronshirley751/ibkr-trading-bot-production/commit/1bd71e0)

---

## 1. VALIDATION OBJECTIVE

Execute supervised runtime testing of the IBKR snapshot capture script to verify that all CRO-mandated safety mechanisms function correctly when connected to a live IBKR Gateway instance. This validation must be completed before Chunk 6 (snapshot data collection) can proceed.

**Critical Safety Requirements Being Validated:**
1. Account type verification triggers and validates PAPER account
2. Script aborts if non-PAPER account detected
3. Connection metadata logging provides audit trail
4. Snapshot completeness validation detects incomplete data
5. Script operates in read-only mode with no order placement

**Validation Status:** Static analysis COMPLETE ✅ | Runtime validation PENDING 🟡

---

## 2. PREREQUISITES

### Required Infrastructure

**IBKR Gateway Configuration:**
- [ ] IBKR Gateway installed and running
- [ ] Gateway configured for **PAPER TRADING** mode (CRITICAL)
- [ ] Gateway connected to paper trading account
- [ ] Gateway listening on port 4002
- [ ] Gateway shows "Connected" status

**Timing Requirements:**
- [ ] Market hours: 9:30 AM - 4:00 PM ET (Monday-Friday)
- [ ] Active trading session (not pre-market or after-hours)

**Environment Setup:**
- [ ] Project repository: `ibkr-trading-bot-production`
- [ ] Working directory: Project root
- [ ] Python environment: Poetry activated
- [ ] Git status: Clean (no uncommitted changes)

**Personnel:**
- [ ] Operator present and supervising
- [ ] @QA_Lead available for immediate review
- [ ] @CRO notified of validation session

---

## 3. PRE-VALIDATION CHECKLIST

### Step 1: Verify IBKR Gateway Status

**Open IBKR Gateway Application:**
```
Check the following indicators in the Gateway window:
✓ Status: "Connected"
✓ Mode: "Paper Trading" (NOT "Live Trading")
✓ Port: 4002 (NOT 7496 or 7497)
✓ Connection: Green indicator
```

**If Gateway shows "Live Trading":**
```
🔴 STOP - DO NOT PROCEED
Gateway is in LIVE mode. Must be reconfigured to PAPER mode.
See Gateway configuration documentation.
```

---

### Step 2: Verify Script Implementation

**Navigate to project directory:**
```bash
cd /path/to/ibkr-trading-bot-production
```

**Verify script exists and is latest version:**
```bash
# Check file exists
ls -la scripts/capture_ibkr_snapshot.py

# Verify it's the correct commit
git log -1 --oneline scripts/capture_ibkr_snapshot.py
# Expected: 1bd71e0 Task 1.1.2 Chunk 5: Implement IBKR snapshot capture script...
```

**Verify directory structure:**
```bash
# Check snapshot directory exists
ls -la tests/fixtures/ibkr_snapshots/

# Expected output:
# drwxr-xr-x  tests/fixtures/ibkr_snapshots/
# -rw-r--r--  tests/fixtures/ibkr_snapshots/.gitkeep
```

---

### Step 3: Safety Pre-Check

**Verify CRO safety mechanisms are present in code:**
```bash
# Check account type verification
grep -n "AccountType" scripts/capture_ibkr_snapshot.py
# Expected: Multiple matches including callback and validation logic

# Check PAPER validation
grep -n "PAPER" scripts/capture_ibkr_snapshot.py
# Expected: Multiple matches in safety checks

# Check hardcoded port
grep -n "4002" scripts/capture_ibkr_snapshot.py
# Expected: Exactly 1 match in connect() call

# Verify no order placement
grep -n "placeOrder" scripts/capture_ibkr_snapshot.py
# Expected: No matches
```

**All checks must pass before proceeding.**

---

## 4. PHASE 4: SUPERVISED LIVE TEST

**Duration:** 10-15 minutes
**Purpose:** Verify script connects, validates account type, captures data, and saves snapshot

---

### Step 4.1: Execute Script

**Run the snapshot capture script:**
```bash
python scripts/capture_ibkr_snapshot.py --scenario validation_test
```

**Expected Initial Output:**
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
SAFETY CHECK: This script connects to port 4002 (paper trading)
Ensure IBKR Gateway is running in PAPER TRADING mode
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Continue with snapshot capture? (yes/no):
```

**Action:** Type `yes` and press Enter

---

### Step 4.2: Validation Checkpoint 1 - Connection

**Expected Output:**
```
Connecting to IBKR Gateway on port 4002 (paper trading)...
ℹ Info [2104]: Market data farm connection is OK:usfarm
ℹ Info [2106]: HMDS data farm connection is OK:ushmds
✓ Connected to IBKR Gateway. Next Order ID: 1
  Connected accounts: DU1234567
✓ Connected successfully
```

**Validation Checklist:**
- [ ] Connection establishes without timeout
- [ ] Port 4002 explicitly mentioned
- [ ] "Connected accounts" logged (audit trail)
- [ ] No error messages

**If connection fails:**
```
Troubleshooting:
1. Verify Gateway is running and shows "Connected"
2. Check Gateway port configuration (must be 4002)
3. Verify no firewall blocking localhost:4002
4. Check Gateway connection status in application
```

---

### Step 4.3: Validation Checkpoint 2 - Account Type Verification (CRITICAL)

**Expected Output:**
```
============================================================
SAFETY CHECK: Verifying account type...
============================================================
  Account Type: PAPER
✓ VERIFIED: Paper trading account confirmed
✓ Safe to proceed with snapshot capture
```

**Validation Checklist:**
- [ ] "SAFETY CHECK: Verifying account type..." banner appears
- [ ] "Account Type: PAPER" displays (CRITICAL)
- [ ] "✓ VERIFIED: Paper trading account confirmed" displays
- [ ] Script proceeds to next phase

**🔴 CRITICAL FAILURE SCENARIO:**

If output shows:
```
🔴 SAFETY VIOLATION: Account type is 'LIVE' not 'PAPER'
🔴 This script ONLY runs on paper trading accounts
🔴 ABORTING to prevent live account access
```

**Action:** This is CORRECT behavior for safety abort. However, this means Gateway was misconfigured.
- **DO NOT** attempt to bypass this check
- **STOP** validation session immediately
- **RECONFIGURE** Gateway to paper trading mode
- **RESTART** validation from Step 4.1

---

### Step 4.4: Validation Checkpoint 3 - Data Capture

**Expected Output (for each symbol SPY, QQQ, IWM):**
```
Capturing data for SPY...
  Requesting market data (reqId 1000)...
  ✓ Current price: $580.25
  Requesting historical data (reqId 1001)...
  ✓ Retrieved 38 historical bars
  ✓ Captured 20 option contracts

Capturing data for QQQ...
  [similar output]

Capturing data for IWM...
  [similar output]

✓ Snapshot capture complete
```

**Validation Checklist:**
- [ ] Data captured for all 3 symbols (SPY, QQQ, IWM)
- [ ] Current price retrieved for each symbol
- [ ] Historical bars retrieved (expect 30-40 bars)
- [ ] Option contracts retrieved (expect 15-25 contracts per symbol)
- [ ] No timeout errors or API rejections

**If data capture fails:**
```
Common issues:
- Market closed: Must run during 9:30 AM - 4:00 PM ET
- Market data subscription: Paper account may lack market data permissions
- Rate limiting: Script includes delays, but IBKR may throttle requests
- Network issues: Check Gateway connection stability
```

---

### Step 4.5: Validation Checkpoint 4 - Completeness Validation

**Expected Output:**
```
✓ Snapshot completeness validation passed

✓ Snapshot saved to: tests/fixtures/ibkr_snapshots/snapshot_validation_test_20260206_143022.json
  File size: 125.3 KB
✓ Latest snapshot: tests/fixtures/ibkr_snapshots/snapshot_validation_test_latest.json

============================================================
SNAPSHOT CAPTURE COMPLETE
============================================================
```

**Validation Checklist:**
- [ ] Completeness validation runs
- [ ] Validation passes (no warnings about incomplete data)
- [ ] Snapshot file saved with timestamp in filename
- [ ] Latest symlink created
- [ ] File size reasonable (expect 50-200 KB)

**If completeness validation shows warnings:**
```
⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠
WARNING: Snapshot incomplete - may not be suitable for testing
⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠
  ⚠ SPY: Insufficient historical bars (15, expected 20+)
  ⚠ QQQ: No options have valid Greeks data
```

**Action:** This is expected behavior (warning, not failure). Note issues for investigation:
- Insufficient historical bars: May be end of day with fewer bars available
- No Greeks: May be far OTM options or low liquidity
- Snapshot is still saved but may not be ideal for testing
```

---

### Step 4.6: Post-Capture Validation

**Verify snapshot file structure:**
```bash
# Check file exists
ls -la tests/fixtures/ibkr_snapshots/snapshot_validation_test_latest.json

# Validate JSON structure
python -c "
import json
from pathlib import Path

snapshot_path = Path('tests/fixtures/ibkr_snapshots/snapshot_validation_test_latest.json')

with open(snapshot_path) as f:
    data = json.load(f)

print('Snapshot Validation Report:')
print('=' * 60)
print(f'Scenario: {data[\"scenario\"]}')
print(f'Timestamp: {data[\"timestamp\"]}')
print(f'Symbols: {list(data[\"symbols\"].keys())}')
print()

for symbol, sym_data in data['symbols'].items():
    print(f'{symbol}:')
    print(f'  Current Price: \${sym_data[\"currentPrice\"]:.2f}')
    print(f'  Historical Bars: {len(sym_data[\"historicalBars\"])}')
    print(f'  Option Contracts: {len(sym_data[\"optionChain\"])}')

    # Check Greeks presence
    options_with_greeks = sum(
        1 for opt in sym_data['optionChain']
        if opt.get('greeks') and opt['greeks'].get('delta') is not None
    )
    print(f'  Options with Greeks: {options_with_greeks}/{len(sym_data[\"optionChain\"])}')
    print()

print('✅ Snapshot structure validated')
"
```

**Expected Output:**
```
Snapshot Validation Report:
============================================================
Scenario: validation_test
Timestamp: 2026-02-06T14:30:22.123456
Symbols: ['SPY', 'QQQ', 'IWM']

SPY:
  Current Price: $580.25
  Historical Bars: 38
  Option Contracts: 20
  Options with Greeks: 18/20

QQQ:
  Current Price: $499.80
  Historical Bars: 38
  Option Contracts: 20
  Options with Greeks: 19/20

IWM:
  Current Price: $219.50
  Historical Bars: 38
  Option Contracts: 20
  Options with Greeks: 17/20

✅ Snapshot structure validated
```

**Validation Checklist:**
- [ ] JSON file is valid (no parse errors)
- [ ] All 3 symbols present (SPY, QQQ, IWM)
- [ ] Each symbol has current price > 0
- [ ] Each symbol has 20+ historical bars
- [ ] Each symbol has 10+ option contracts
- [ ] Most options have Greeks data (some may be missing for far OTM)

---

## 5. PHASE 5: SAFETY VIOLATION TEST

**Duration:** 5 minutes
**Purpose:** Verify script aborts correctly if non-PAPER account detected

---

### Step 5.1: Create Safety Test Script

**Create test file:**
```bash
cat > scripts/test_safety_abort.py << 'EOF'
#!/usr/bin/env python3
"""Test safety abort behavior - simulates LIVE account detection."""
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the snapshot capture class
from capture_ibkr_snapshot import SnapshotCapture

print("Safety Violation Test: Simulating LIVE account detection")
print("=" * 60)

# Create instance
app = SnapshotCapture()
app.account_type = None

print("Simulating accountSummary callback with AccountType='LIVE'...")

# Simulate receiving LIVE account type
# This should trigger sys.exit(1) in the callback
try:
    app.accountSummary(9999, "TEST123", "AccountType", "LIVE", "USD")

    # If we reach this point, the test FAILED
    print("\n❌ TEST FAILED: Script did not abort on LIVE account")
    print("Expected: Script should call sys.exit(1) in accountSummary callback")
    sys.exit(1)

except SystemExit as e:
    if e.code == 1:
        print("\n✅ TEST PASSED: Script correctly aborted on LIVE account detection")
        print(f"Exit code: {e.code}")
        sys.exit(0)
    else:
        print(f"\n⚠ UNEXPECTED: Script exited with code {e.code}, expected 1")
        sys.exit(1)
EOF

chmod +x scripts/test_safety_abort.py
```

---

### Step 5.2: Execute Safety Test

**Run the safety violation test:**
```bash
python scripts/test_safety_abort.py
```

**Expected Output:**
```
Safety Violation Test: Simulating LIVE account detection
============================================================
Simulating accountSummary callback with AccountType='LIVE'...
  Account Type: LIVE

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
🔴 SAFETY VIOLATION: Account type is 'LIVE' not 'PAPER'
🔴 This script ONLY runs on paper trading accounts
🔴 ABORTING to prevent live account access
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


✅ TEST PASSED: Script correctly aborted on LIVE account detection
Exit code: 1
```

**Validation Checklist:**
- [ ] Safety violation banner displays with 🔴 indicators
- [ ] Clear message explains the violation
- [ ] Script calls `sys.exit(1)`
- [ ] Test script reports "TEST PASSED"

**If test shows "TEST FAILED":**
```
🔴 CRITICAL SAFETY FAILURE
The script did not abort when LIVE account was detected.
This is a CRO veto-level issue.

Actions:
1. STOP all validation immediately
2. DO NOT proceed to Chunk 6
3. Notify @CRO and @QA_Lead immediately
4. Review accountSummary callback implementation
5. Fix safety mechanism
6. Restart validation from beginning
```

---

### Step 5.3: Cleanup

**Remove test script:**
```bash
rm scripts/test_safety_abort.py
```

---

## 6. VALIDATION RESULTS

### Phase 4: Supervised Live Test

**Date/Time:** _______________
**Operator:** _______________
**Market Conditions:** Open / Mid-day / Close (circle one)

**Results:**
- [ ] ✅ PASS - All checkpoints completed successfully
- [ ] ⚠️ PARTIAL PASS - Some warnings but functional
- [ ] ❌ FAIL - Critical issues encountered

**Checkpoint Results:**
- [ ] Connection established to port 4002
- [ ] Account type verification triggered
- [ ] "Account Type: PAPER" confirmed
- [ ] Data captured for all 3 symbols
- [ ] Snapshot file created with valid structure
- [ ] Completeness validation ran

**Issues Encountered (if any):**
```
[Document any warnings, errors, or unexpected behavior]
```

**Snapshot Files Created:**
```
[List filenames and sizes]
```

---

### Phase 5: Safety Violation Test

**Results:**
- [ ] ✅ PASS - Script correctly aborted on LIVE account simulation
- [ ] ❌ FAIL - Script did not abort (CRITICAL SAFETY ISSUE)

**Safety Abort Behavior:**
- [ ] Violation banner displayed
- [ ] Clear error messaging
- [ ] Exit code 1 returned

**Issues Encountered (if any):**
```
[Document any safety mechanism failures]
```

---

## 7. SIGN-OFF

### @QA_Lead Final Validation

**Static Analysis:** ✅ COMPLETE (verified in code review)

**Runtime Validation:**
- [ ] ✅ Phase 4 PASSED - Supervised live test successful
- [ ] ✅ Phase 5 PASSED - Safety abort verified
- [ ] ⚠️ CONDITIONAL PASS - Minor issues documented
- [ ] ❌ FAIL - Critical issues require rework

**Final Verdict:**
- [ ] ✅ **APPROVED** - Chunk 5 complete, Chunk 6 UNBLOCKED
- [ ] ⚠️ **CONDITIONAL APPROVAL** - Approved with noted limitations
- [ ] ❌ **REJECTED** - Requires rework and re-validation

**Comments:**
```
[QA_Lead assessment and any conditions for approval]
```

**Signature:** _______________ **Date:** _______________

---

### @CRO Safety Confirmation

**CRO-Mandated Safety Mechanisms:**
- [ ] ✅ Condition 1: Account type verification functional
- [ ] ✅ Condition 2: Connection metadata logging operational
- [ ] ✅ Condition 3: Snapshot completeness validation working

**Safety Posture Assessment:**
- [ ] ✅ All defense-in-depth layers operational
- [ ] ✅ Script correctly aborts on safety violations
- [ ] ✅ Audit trail maintained
- [ ] ✅ Risk posture acceptable for production use

**Final Safety Clearance:**
- [ ] ✅ **APPROVED** - Safe for production use
- [ ] ⚠️ **CONDITIONAL** - Approved with usage restrictions
- [ ] ❌ **SAFETY VETO** - Not safe for use

**Comments:**
```
[CRO safety assessment]
```

**Signature:** _______________ **Date:** _______________

---

## 8. NEXT STEPS

### If Validation PASSES

1. **@PM:** Update Task 1.1.2 on board
   - Mark Chunk 5 as COMPLETE
   - Remove "Runtime Validation Pending" blocker
   - Unblock Chunk 6

2. **@Systems_Architect:** Prepare Chunk 6 handoff document
   - Task: Capture multiple snapshot scenarios
   - Depends on: Chunk 5 script now validated

3. **Operator:** Plan snapshot collection sessions
   - Scenario 1: Normal market conditions
   - Scenario 2: High VIX day
   - Scenario 3: Tight spreads (low volatility)

4. **Documentation:** Archive validation results
   - Save this document with completed checklist
   - Save snapshot files for reference
   - Update project documentation

---

### If Validation FAILS

1. **Document Failure:**
   - Record specific failures in Section 6
   - Capture error logs and console output
   - Take screenshots if relevant

2. **Root Cause Analysis:**
   - @Systems_Architect reviews implementation
   - @QA_Lead analyzes failure mode
   - @CRO assesses safety implications

3. **Remediation:**
   - Create fix specification
   - Implement corrections
   - Re-run validation from beginning

4. **Escalation (if needed):**
   - Critical safety failures → @CRO immediate review
   - Blocking technical issues → @DevOps engagement
   - Architecture concerns → Design review session

---

## 9. APPENDIX

### A. Troubleshooting Guide

**Issue: Connection Timeout**
```
Symptom: "Connection timeout" after 10 seconds
Causes:
- Gateway not running
- Gateway on wrong port
- Firewall blocking connection

Solutions:
1. Verify Gateway application is running
2. Check Gateway port configuration (must be 4002)
3. Disable firewall temporarily for testing
4. Check Gateway logs for connection rejections
```

**Issue: No Market Data**
```
Symptom: Current price shows $0.00 or no data
Causes:
- Market closed
- Paper account lacks market data subscription
- Symbol not found

Solutions:
1. Verify market hours (9:30 AM - 4:00 PM ET)
2. Check Gateway market data status
3. Verify symbols are correct (SPY, QQQ, IWM)
4. Check Gateway subscription status
```

**Issue: Account Type Not Verified**
```
Symptom: "Account type verification timeout"
Causes:
- reqAccountSummary() not returning data
- Gateway not providing account summary
- Callback not receiving data

Solutions:
1. Check Gateway connection status
2. Verify account is logged in to Gateway
3. Increase timeout from 5 to 10 seconds
4. Check Gateway logs for account summary requests
```

**Issue: Incomplete Snapshot**
```
Symptom: Completeness validation warnings
Causes:
- End of day (fewer bars available)
- Low liquidity symbols
- Far OTM options (no Greeks)

Solutions:
1. Run earlier in trading day (10:00 AM - 2:00 PM)
2. Accept warnings if data mostly complete
3. Re-run during more active market period
4. Adjust strike selection for better liquidity
```

---

### B. IBKR Gateway Configuration Reference

**Paper Trading Configuration:**
```
1. Open IBKR Gateway application
2. Click "Configure" → "Settings"
3. Select "Trading Mode" → "Paper Trading"
4. Set "Socket Port" → 4002
5. Enable "Read-Only API" (recommended)
6. Save and restart Gateway
```

**Verification:**
```
Gateway window should display:
- "Paper Trading" in title bar or status
- "Port: 4002" in connection info
- Green connection indicator
```

---

### C. Snapshot File Specification

**Expected JSON Structure:**
```json
{
  "scenario": "validation_test",
  "timestamp": "2026-02-06T14:30:22.123456",
  "symbols": {
    "SPY": {
      "currentPrice": 580.25,
      "historicalBars": [
        {
          "date": "20260206  09:30:00",
          "open": 578.50,
          "high": 579.00,
          "low": 578.25,
          "close": 578.75,
          "volume": 1250000,
          "wap": 578.65,
          "barCount": 15234
        }
      ],
      "optionChain": [
        {
          "contract": {
            "symbol": "SPY",
            "right": "C",
            "strike": 580.0,
            "expiry": "20260214"
          },
          "marketData": {
            "bid": 5.20,
            "ask": 5.30,
            "last": 5.25,
            "bidSize": 50,
            "askSize": 75,
            "volume": 12500
          },
          "greeks": {
            "impliedVolatility": 0.18,
            "delta": 0.52,
            "gamma": 0.03,
            "vega": 0.15,
            "theta": -0.08,
            "optionPrice": 5.25,
            "underlyingPrice": 580.25
          }
        }
      ]
    }
  }
}
```

---

**Document Status:** ✅ Ready for Runtime Validation
**Implementation Status:** Code Complete (Commit 1bd71e0)
**Validation Status:** Awaiting Supervised Test (Market Hours Required)

---

*@Systems_Architect signing off. Runtime validation procedure complete and ready for execution during next market hours.*
