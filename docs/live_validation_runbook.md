# Live Validation Runbook — Task 1.1.8

**Purpose:** Step-by-step operator guide for executing live validation of IBKR trading bot against paper trading account during market hours.

**Audience:** DevOps, QA Lead, System Operator
**Prerequisites:** Phase 1 automated tests (Tasks 1.1.1–1.1.7) passing
**Duration:** ~2-3 hours (including setup, execution, cleanup)
**Market Hours Required:** 9:30 AM - 4:00 PM ET

---

## OVERVIEW

This runbook guides manual execution of the live validation suite, the **final Phase 1 gate** before transitioning to Phase 2 (source code implementation). You will:

1. **Setup:** Start IBKR Gateway, verify paper trading mode, prepare environment
2. **Execute:** Run automated test suite against live Gateway connection
3. **Validate:** Manually verify positions, orders, and Gateway logs
4. **Cleanup:** Close positions, archive logs, update project board
5. **Sign-Off:** Complete validation checklist and obtain approvals

**Safety Note:** All validation uses **PAPER TRADING ONLY**. Never execute against live trading accounts.

---

## STEP 1: PRE-VALIDATION SETUP (15 minutes)

### 1.1 Start IBKR Gateway

**On Raspberry Pi (or local machine):**

```bash
# SSH into Pi (if remote)
ssh pi@crucible-pi.local

# Navigate to Gateway installation
cd ~/ibkr_gateway

# Start Gateway manually (NOT automated for validation)
./gateway.sh
```

**Expected Output:**
```
Starting IB Gateway...
IB Gateway started on port 4002
```

**Verify Gateway is Running:**

```bash
# Check port 4002 is listening
netstat -an | grep 4002
```

**Expected Output:**
```
tcp        0      0 0.0.0.0:4002            0.0.0.0:*               LISTEN
```

**Troubleshooting:**
- If port not listening: Check Gateway logs at `~/ibkr_gateway/logs/ibgateway.log`
- If Gateway won't start: Verify IBKR credentials in `~/ibkr_gateway/jts.ini`
- If port blocked: Check firewall rules (`sudo ufw status`)

---

### 1.2 Verify Paper Trading Mode

**Open IBKR Trader Workstation (TWS) on Desktop:**

1. Launch TWS application
2. Log in with paper trading credentials
3. **Verify "PAPER" label** appears in top-right corner of TWS window
4. Navigate to Account → Account Window
5. Confirm account balance is virtual capital (~$100,000)

**CRITICAL SAFETY CHECK:**
- If TWS shows "LIVE" instead of "PAPER", **STOP IMMEDIATELY**
- Do NOT proceed with validation
- Switch to paper trading mode in TWS settings
- Restart Gateway and verify again

---

### 1.3 Activate Python Environment

```bash
# Navigate to project root
cd ~/crucible  # Or wherever project is located

# Activate Poetry environment
poetry shell

# Install all dependencies (including dev/test)
poetry install --with dev

# Verify pytest is available
pytest --version
```

**Expected Output:**
```
pytest 7.4.0
```

---

### 1.4 Update Test Configuration

**Edit configuration file:**

```bash
nano config/live_validation_config.yaml
```

**Update weekly option expiry date:**

Find the `spy_weekly_call` section and update `lastTradeDateOrContractMonth`:

```yaml
spy_weekly_call:
  symbol: "SPY"
  secType: "OPT"
  exchange: "SMART"
  currency: "USD"
  lastTradeDateOrContractMonth: "20260213"  # UPDATE THIS TO NEXT FRIDAY
  strike: 600.0
  right: "CALL"
```

**How to determine next Friday:**
- If today is Monday-Thursday: Use this week's Friday
- If today is Friday: Use next week's Friday
- Format: YYYYMMDD (e.g., February 13, 2026 = 20260213)

**Save and exit:** `Ctrl+X`, `Y`, `Enter`

---

### 1.5 Run Pre-Flight Checks

**Verify Gateway Connectivity:**

```bash
# Check Gateway connection (if script exists)
python scripts/check_gateway_connection.py
```

**Expected Output:**
```
✓ Gateway connected on port 4002
✓ Account type: PAPER
✓ Ready for validation
```

**If script doesn't exist, skip this step.** The test suite will verify connectivity.

**Verify System Time Sync:**

```bash
# Linux/Mac
timedatectl status

# Windows (PowerShell)
w32tm /query /status
```

**Expected Output (Linux):**
```
System clock synchronized: yes
NTP service: active
```

**Check Network Latency:**

```bash
# Ping IBKR servers (5 attempts)
ping -c 5 gateway.interactivebrokers.com
```

**Expected Output:**
```
5 packets transmitted, 5 received, 0% packet loss
rtt min/avg/max = 20.5/35.2/50.1 ms
```

**Target:** Average latency < 50ms. If higher, validation may experience timeouts.

---

### 1.6 Verify Market Hours

**Check current time is within market hours (9:30 AM - 4:00 PM ET):**

```bash
# Display current time in Eastern timezone
TZ='America/New_York' date
```

**Expected Output:**
```
Mon Feb  9 10:15:32 EST 2026
```

**If outside market hours:**
- Market data tests will fail (expected)
- Reschedule validation for next trading day during RTH
- Or disable `market_hours_required` in config (not recommended)

---

## STEP 2: EXECUTE LIVE VALIDATION (30-60 minutes)

### 2.1 Run Full Test Suite

**Execute all live validation tests:**

```bash
pytest tests/live_validation/ -v --tb=short
```

**What to Expect:**
- Tests will run in sequence
- Some tests take 60+ seconds (e.g., stream quality test)
- Real-time output shows pass/fail for each test
- Total execution time: ~10-15 minutes

**Example Output:**
```
tests/live_validation/test_live_broker_connectivity.py::test_gateway_authentication PASSED
tests/live_validation/test_live_broker_connectivity.py::test_account_info_retrieval PASSED
tests/live_validation/test_live_market_data.py::test_market_data_subscription_spy PASSED
...
======================== 25 passed in 12.5 minutes ========================
```

**If Tests Are Skipped:**

Some tests may be skipped if broker layer implementation is incomplete (Phase 2). This is expected during Phase 1 handoff execution. Example:

```
SKIPPED [1] conftest.py:35: Live validation requires actual IBKR Gateway connection
```

**This is acceptable during handoff delivery.** Mark test files as "implementation pending" and proceed to documentation review.

---

### 2.2 Monitor Test Execution

**While tests run, monitor for:**

1. **Failures or Errors:**
   - If any test fails, note the failure in checklist
   - Review error message and traceback
   - STOP execution if > 20% of tests fail (critical failure threshold)

2. **Warnings:**
   - Yellow warnings are typically non-critical
   - Document warnings for review

3. **Long-Running Tests:**
   - `test_extended_session_stability`: 5 minutes (expected)
   - `test_market_data_stream_quality`: 60 seconds (expected)
   - `test_gateway_connection_stability`: 60 seconds (expected)

**If Tests Hang:**
- Wait 2x expected duration before interrupting
- Check Gateway logs for errors
- Check network connectivity
- Interrupt with `Ctrl+C`, review logs, restart validation

---

### 2.3 Review Test Output

**After execution completes, check pass rate:**

```bash
# Count passed tests
pytest tests/live_validation/ -v | grep -c "PASSED"

# Count failed tests
pytest tests/live_validation/ -v | grep -c "FAILED"

# Count skipped tests
pytest tests/live_validation/ -v | grep -c "SKIPPED"
```

**Target:** 100% pass rate (zero failures). Skipped tests are acceptable if broker layer incomplete.

**Save Test Report:**

```bash
# Generate JUnit XML report
pytest tests/live_validation/ -v --junit-xml=pytest_report.xml

# Generate text report
pytest tests/live_validation/ -v > pytest_report.txt
```

---

## STEP 3: MANUAL VALIDATION STEPS (30 minutes)

### 3.1 Verify Position Tracking via TWS

**Open TWS on Desktop:**

1. Navigate to **Portfolio → Positions**
2. Review open positions (if any from test execution)
3. Verify positions match test orders:
   - Symbol: SPY
   - Sec Type: OPT
   - Right: CALL
   - Strike: 600
   - Quantity: May vary based on test execution

**Expected State:**
- Fresh paper account: No positions
- After order execution tests: 0-2 open SPY CALL positions

**Action Required:**
- Manually close any open test positions:
  - Right-click position → Create Closing Order
  - Submit market order to close
  - Verify position removed from portfolio

---

### 3.2 Review Order History

**In TWS:**

1. Navigate to **Trade → Trade Log**
2. Review orders from validation session
3. Verify all test orders are visible
4. Check order status:
   - **Filled:** Order executed successfully (expected for most)
   - **Cancelled:** Order cancelled by test (expected for cancellation tests)
   - **Pending:** Order still open (**NOT expected — investigate**)

**Verify Order Timestamps:**
- Orders should match test execution time
- All orders should be from today's session

**Document Anomalies:**
- Unexpected orders (not from validation)
- Orders with errors or rejections
- Duplicate orders

---

### 3.3 Check Gateway Logs

**Review Gateway logs for errors:**

```bash
# View last 100 log lines
tail -n 100 ~/ibkr_gateway/logs/ibgateway.log
```

**Look For:**
- **Errors:** Lines with "ERROR" or "EXCEPTION"
- **Warnings:** Lines with "WARN"
- **Disconnections:** Lines with "disconnected" or "connection lost"
- **Rate Limiting:** Lines with "rate limit" or "pacing violation"

**Expected Log Entries:**
```
[INFO] Client 1 connected
[INFO] Market data request for SPY
[INFO] Order submitted: OrderId=123
[INFO] Order filled: OrderId=123
```

**Anomalies to Document:**
```
[ERROR] Request timeout
[WARN] Pacing violation - request throttled
[ERROR] Connection lost - reconnecting
```

**Save Logs:**

```bash
# Copy logs to validation archive
cp ~/ibkr_gateway/logs/ibgateway.log logs/live_validation/ibgateway_$(date +%Y%m%d).log
```

---

### 3.4 Record Performance Metrics

**From Test Output and TWS, Record:**

1. **Average Order Fill Time:**
   - Review test output from order execution tests
   - Target: < 30 seconds (paper trading should be faster)

2. **Average Quote Freshness:**
   - Review test output from market data tests
   - Target: < 5 seconds during market hours

3. **Gateway Uptime:**
   - Check Gateway logs for disconnection events
   - Target: 100% uptime during validation session

4. **Connection Latency:**
   - From ping test results
   - Target: < 100ms average

**Document in Checklist:**
```
Average order fill time: 2.3 seconds
Average quote freshness: 1.8 seconds
Gateway uptime: 100%
Connection latency: 35ms avg
```

---

## STEP 4: POST-VALIDATION CLEANUP (10 minutes)

### 4.1 Close All Test Positions

**If script exists:**

```bash
python scripts/close_all_positions.py --paper-trading
```

**Manual Alternative (via TWS):**
1. Portfolio → Positions
2. Select all positions
3. Right-click → Close All Positions
4. Submit market orders
5. Verify all positions closed

**Verify Paper Account Balance:**
- Note starting balance: $100,000 (typical)
- Note ending balance: Should be close to starting (minus test trade costs)
- Small losses expected from bid-ask spread on test trades

---

### 4.2 Archive Test Logs

```bash
# Create archive directory
mkdir -p logs/live_validation/$(date +%Y%m%d)

# Copy pytest report
cp pytest_report.txt logs/live_validation/$(date +%Y%m%d)/

# Copy Gateway logs
cp ~/ibkr_gateway/logs/ibgateway.log logs/live_validation/$(date +%Y%m%d)/

# Verify archive
ls -lh logs/live_validation/$(date +%Y%m%d)/
```

**Expected Output:**
```
-rw-r--r-- 1 user user  45K Feb  9 14:32 pytest_report.txt
-rw-r--r-- 1 user user 120K Feb  9 14:32 ibgateway.log
```

---

### 4.3 Update Project Board

**On IBKR Project Management Board:**

1. Navigate to Task 1.1.8 (Live Validation Suite)
2. Add comment with validation results:
   ```
   Live validation completed successfully.
   - Test Pass Rate: 100% (25/25 passed)
   - Session Duration: 2.5 hours
   - Gateway Uptime: 100%
   - No critical issues found
   - Logs archived: logs/live_validation/20260209/
   ```
3. Upload archived logs as attachments
4. Tag @QA_Lead and @CRO for review
5. Move task to "Awaiting Approval" status

---

### 4.4 Gateway Shutdown (Optional)

**If not proceeding to bot testing immediately:**

```bash
# Graceful Gateway shutdown
pkill -f "ibgateway"

# Verify process terminated
ps aux | grep ibgateway
```

**Expected Output:**
```
(no processes found)
```

**If continuing to bot testing:**
- Leave Gateway running
- Proceed to Phase 2 source code implementation
- Gateway will be reused for development testing

---

## STEP 5: VALIDATION SIGN-OFF

### 5.1 Complete Deployment Validation Checklist

**Open checklist document:**

```bash
nano docs/deployment_validation_checklist.md
```

**Complete all sections:**
- Section 1: Pre-Validation Setup (mark all checkboxes)
- Section 2: Automated Test Execution (record pass/fail for each test)
- Section 3: Manual Validation Steps (document findings)
- Section 4: Post-Validation Cleanup (confirm completion)
- Section 5: Validation Sign-Off (record test results summary)

**Save completed checklist:**
```bash
cp docs/deployment_validation_checklist.md logs/live_validation/$(date +%Y%m%d)/checklist_completed.md
```

---

### 5.2 Create Validation Report

**Create summary document:**

```bash
nano docs/live_validation_report_$(date +%Y%m%d).md
```

**Include:**
1. **Executive Summary:** One-paragraph validation results
2. **Test Results Table:** Pass/fail breakdown by category
3. **Performance Metrics:** Latency, uptime, fill times
4. **Known Issues:** Any anomalies or exceptions
5. **Recommendations:** Proceed to Phase 2 or remediate

**Example Template:**
```markdown
# Live Validation Report — February 9, 2026

## Executive Summary
Live validation of IBKR trading bot completed successfully. All 25
automated tests passed with 100% success rate. Gateway demonstrated
stable operation for 2.5-hour session with zero critical failures.

## Test Results
| Category | Tests | Pass | Fail | Pass Rate |
|----------|-------|------|------|-----------|
| Broker Connectivity | 6 | 6 | 0 | 100% |
| Market Data | 6 | 6 | 0 | 100% |
| Order Execution | 5 | 5 | 0 | 100% |
| Resilience | 8 | 8 | 0 | 100% |
| **TOTAL** | 25 | 25 | 0 | 100% |

## Performance Metrics
- Average order fill time: 2.3 seconds
- Average quote freshness: 1.8 seconds
- Gateway uptime: 100%
- Connection latency: 35ms avg

## Known Issues
No critical issues identified.

## Recommendation
✅ **APPROVED:** Proceed to Phase 2 (source code implementation)
```

**Save report:**
```bash
cp docs/live_validation_report_$(date +%Y%m%d).md logs/live_validation/$(date +%Y%m%d)/
```

---

### 5.3 Obtain Approvals

**Share validation report with:**
- @QA_Lead (test quality review)
- @CRO (safety sign-off)
- @PM (Phase 2 authorization)

**Request approvals via:**
- Email with report attached
- Project board comments
- Slack/Teams message with link to archived logs

**Required Approvals:**
1. ✅ QA Lead: Test execution and results validation
2. ✅ CRO: Safety checks and risk assessment
3. ✅ PM: Phase 2 kickoff authorization

**Timeline:**
- Target: Same-day approvals (if completed before 2 PM ET)
- Fallback: Next business day if late submission

---

## STEP 6: PHASE 2 TRANSITION

### 6.1 Mark Task Complete

**On Project Board:**
1. Move Task 1.1.8 to "Done" column
2. Add completion date in task description
3. Link to validation report and logs

**In Git:**
```bash
# Tag Phase 1 completion
git tag phase1-validation-passed-$(date +%Y%m%d)

# Push tag
git push origin phase1-validation-passed-$(date +%Y%m%d)
```

---

### 6.2 Schedule Phase 2 Kickoff

**Next Steps:**
1. Review Phase 2 sprint plan ([Phase_1_Sprint_Plan_2026-02-06.md](Phase_1_Sprint_Plan_2026-02-06.md))
2. Schedule Phase 2 kickoff session (Chunk 2)
3. Begin Task 2.1: Implement strategy base classes

**Phase 2 Start Date:** ________________

**Phase 2 Lead:** ________________

---

## TROUBLESHOOTING

### Problem: Tests Fail with "Gateway Not Connected"

**Symptoms:**
```
ConnectionError: Gateway connection failed after 3 attempts
```

**Solutions:**
1. Verify Gateway is running: `netstat -an | grep 4002`
2. Check Gateway logs for errors
3. Restart Gateway: `pkill -f ibgateway && ./gateway.sh`
4. Verify firewall allows port 4002
5. Try manual telnet: `telnet 127.0.0.1 4002`

---

### Problem: Tests Fail with "Market Closed"

**Symptoms:**
```
pytest.skip: Outside market hours (9:30 AM - 4:00 PM ET)
```

**Solutions:**
1. Verify current time in ET: `TZ='America/New_York' date`
2. Reschedule validation for market hours
3. Temporary workaround (not recommended): Edit `config/live_validation_config.yaml`:
   ```yaml
   validation:
     market_hours_required: false
   ```

---

### Problem: Quote Data is Stale (> 5 seconds old)

**Symptoms:**
```
AssertionError: Quote should be fresh (< 5s old), found: 45.2s
```

**Solutions:**
1. Verify you're running during market hours
2. Check IBKR market data subscriptions are active
3. Verify Gateway has market data permissions
4. Check for IBKR system status issues: https://www.interactivebrokers.com/en/software/systemStatus.php

---

### Problem: Orders Not Filling in Paper Trading

**Symptoms:**
```
AssertionError: Order should fill in paper trading, found status: Submitted
```

**Solutions:**
1. Verify limit price is reasonable (close to market)
2. Check order is submitted to correct account (PAPER)
3. Review TWS order status for rejection reason
4. Increase order fill timeout in config (current: 30s)

---

### Problem: Gateway Logs Show "Pacing Violation"

**Symptoms:**
```
[WARN] Pacing violation - request throttled
```

**This is expected during rate limit tests.**

**Solutions:**
1. If in `test_api_rate_limit_handling`: Normal behavior, test should pass
2. If in other tests: Reduce request frequency in test implementation
3. Add delays between requests (0.5-1.0 seconds)

---

### Problem: Python Import Errors

**Symptoms:**
```
ImportError: No module named 'yaml'
```

**Solutions:**
1. Verify Poetry environment is activated: `poetry shell`
2. Install dependencies: `poetry install --with dev`
3. Verify Python version: `python --version` (should be 3.12+)

---

## APPENDIX

### A. Useful Commands

**Check Gateway Status:**
```bash
netstat -an | grep 4002  # Linux/Mac
netstat -an | findstr "4002"  # Windows
```

**View Real-Time Logs:**
```bash
tail -f ~/ibkr_gateway/logs/ibgateway.log
```

**Kill Gateway (if hung):**
```bash
pkill -9 -f "ibgateway"
```

**Run Single Test:**
```bash
pytest tests/live_validation/test_live_broker_connectivity.py::test_gateway_authentication -v
```

**Run Tests with Verbose Output:**
```bash
pytest tests/live_validation/ -vv --tb=long
```

---

### B. Configuration File Reference

**Location:** `config/live_validation_config.yaml`

**Key Parameters:**
- `gateway.port`: 4002 (paper trading) | 7497 (live trading)
- `validation.market_hours_required`: true (enforce RTH) | false (allow anytime)
- `thresholds.quote_freshness_seconds`: 5 (max quote age)
- `thresholds.order_fill_timeout_seconds`: 30 (max fill wait time)

---

### C. Contact Information

**Technical Support:**
- Project Lead: ________________
- DevOps: ________________
- QA Lead: ________________

**Escalation:**
- CRO (Safety Issues): ________________
- PM (Timeline Issues): ________________

**IBKR Support:**
- Paper Trading Help: https://www.interactivebrokers.com/en/support/
- Gateway Documentation: https://www.interactivebrokers.com/en/trading/ib-api.php

---

*End of Live Validation Runbook*

**Version:** 1.0
**Last Updated:** February 8, 2026
**Owner:** @DevOps + @QA_Lead
