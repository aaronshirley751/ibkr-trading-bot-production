# TASK-3.4.1 Handoff — Resolve Bot-Gateway TWS API Authentication Timeout

**Session:** TASK-3.4.1 Remediation
**Model:** Sonnet
**Extended Thinking:** Optional (straightforward parameter tuning)
**Estimated Duration:** 30-60 minutes
**Date:** 2026-02-10 (or next day after log review)

---

## Copy and paste this into a fresh Sonnet chat or continue in VSC session:

```
TASK-3.4.1: Resolve Bot-Gateway TWS API Authentication Timeout

**Context:**
Task 3.4 migration complete (95%). All infrastructure operational: Gateway healthy, Bot running, Health Monitor active. Bot successfully reaches Gateway port 4002 (TCP connection works) but TWS API handshake times out after 10 seconds. Bot auto-retries correctly but never completes authentication.

**Current Behavior:**
- Bot logs: "Gateway check attempt X/30" → "Connected" → "Disconnected" → "TimeoutError: API connection failed"
- Gateway logs: No incoming connection attempts visible at API level
- Network connectivity: ✅ Verified (ping and TCP socket work)
- Gateway health: ✅ Healthy (port 4002 responding)

**Root Cause Hypothesis:**
Gateway health check verifies port 4002 is open but does NOT verify TWS API is authenticated and ready. Bot attempts connection before TWS API initialization completes. Additionally, default ib-insync timeout (10s) may be too short for Gateway API handshake.

**Your Mission:**
1. Review overnight logs (did bot eventually connect?)
2. If not connected: Implement connection parameter fixes
3. Validate bot successfully connects to Gateway
4. Verify bot enters Strategy C (Cash Preservation) mode
5. Git commit solution

---

## STEP 0: REVIEW OVERNIGHT LOGS (Do This First)

**Before implementing any fixes, check if the issue self-resolved:**

```powershell
# Check bot logs from last night
docker logs trading-bot --since 8h | Select-String "Gateway.*connected|Account:|Strategy|DRY_RUN"

# If you see "IBKR Gateway connected successfully" → ISSUE RESOLVED
# If still seeing "TimeoutError" → PROCEED WITH FIXES BELOW
```

**Possible Outcomes:**

**Scenario A: Bot Connected Overnight** ✅
- Gateway TWS API eventually initialized
- Bot's retry logic succeeded
- **Action:** Skip to Step 5 (Validation & Documentation)

**Scenario B: Still Timing Out** ⚠️
- Bot still failing after 8+ hours of retries
- **Action:** Proceed with Step 1-4 (Implement Fixes)

---

## STEP 1: IMPLEMENT CONNECTION PARAMETER FIXES

**Primary Fix: Increase Timeout + Unique Client ID**

### File: `src/broker/connection.py` (or `src/config/gateway_config.py`)

**Locate the connection code:**

```python
# Current (default values):
ib.connect(
    host=gateway_host,        # "gateway"
    port=gateway_port,        # 4002
    clientId=0,              # DEFAULT (may conflict)
    timeout=10               # DEFAULT (may be too short)
)
```

**Replace with:**

```python
# Fixed values:
ib.connect(
    host=gateway_host,        # "gateway"
    port=gateway_port,        # 4002
    clientId=100,            # CHANGED: Unique ID to avoid conflicts
    timeout=60               # CHANGED: 60s timeout for slow Gateway initialization
)
```

**Rationale:**
- **clientId=100** — Avoids conflicts with health monitor (if using 0) or other clients
- **timeout=60** — Gives Gateway TWS API 60 seconds to respond (was 10s)

**Alternative (if connection code uses kwargs):**

```python
connection_params = {
    'host': gateway_host,
    'port': gateway_port,
    'clientId': 100,       # Added explicit clientId
    'timeout': 60          # Added explicit timeout
}
ib.connect(**connection_params)
```

### File: Check if timeout is configured elsewhere

**Search for timeout configuration:**

```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production
grep -r "timeout.*=.*10" src/
grep -r "clientId.*=.*0" src/
```

**If found in multiple places, update all occurrences.**

---

## STEP 2: ADD PRE-CONNECTION DELAY (Optional Secondary Fix)

**If timeout increase alone doesn't work, add explicit delay:**

### File: `src/broker/connection.py` or bot startup logic

**Add delay after Gateway health check passes:**

```python
import time
import logging

logger = logging.getLogger(__name__)

# After Gateway health check passes...
logger.info("Gateway health check passed. Waiting 2 minutes for TWS API initialization...")
time.sleep(120)  # Wait 2 minutes before first connection attempt

logger.info("Attempting Gateway connection...")
ib.connect(gateway_host, gateway_port, clientId=100, timeout=60)
```

**Rationale:**
- Gateway health check confirms port 4002 open
- TWS API may need additional 1-2 minutes to authenticate with IBKR servers
- Explicit delay ensures API is ready before first connection attempt

**Trade-off:** Slower bot startup (2 min delay) but more reliable connection

---

## STEP 3: TEST CONNECTION MANUALLY (Validation)

**Before restarting bot, test connection from bot container:**

```powershell
# Test 1: Quick connection test with new parameters
docker exec trading-bot python -c "
from ib_insync import IB
import time

ib = IB()
print('Testing connection with clientId=100, timeout=60...')
try:
    result = ib.connect('gateway', 4002, clientId=100, timeout=60)
    print(f'✓ Connected: {result}')
    print(f'✓ Accounts: {ib.managedAccounts()}')
    ib.disconnect()
    print('✓ Connection successful!')
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

**Expected Output if Fixed:**
```
Testing connection with clientId=100, timeout=60...
✓ Connected: True
✓ Accounts: ['DU1234567']
✓ Connection successful!
```

**If still fails:**
- Try clientId=101, 102 (check if 100 is also in use)
- Try timeout=90 or 120 (even longer)
- Check Gateway logs during attempt: `docker logs ibkr-gateway --tail 50`

---

## STEP 4: RESTART BOT WITH FIXES

**Rebuild bot container with code changes:**

```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production\docker

# Rebuild bot image (picks up code changes)
docker compose build trading-bot

# Restart bot with new image
docker compose up -d trading-bot

# Watch bot logs for successful connection
docker logs -f trading-bot
```

**Expected Log Output (Success):**

```
[2026-02-10 XX:XX:XX] INFO - Bot startup initiated
[2026-02-10 XX:XX:XX] INFO - Environment: DRY_RUN=true
[2026-02-10 XX:XX:XX] INFO - Gateway connection config: gateway:4002 (clientId=100, timeout=60s)
[2026-02-10 XX:XX:XX] INFO - Waiting for Gateway readiness...
[2026-02-10 XX:XX:XX] INFO - Gateway health check passed
[2026-02-10 XX:XX:XX] INFO - Gateway check attempt 1/30
[2026-02-10 XX:XX:XX] INFO - Gateway responding on port 4002
[2026-02-10 XX:XX:XX] INFO - Attempting connection with extended timeout...
[2026-02-10 XX:XX:XX] INFO - IBKR Gateway connected successfully ✓
[2026-02-10 XX:XX:XX] INFO - Account: DU1234567 (Paper Trading) ✓
[2026-02-10 XX:XX:XX] INFO - Connection established, client ID: 100
[2026-02-10 XX:XX:XX] INFO - No gameplan file found at /data/gameplan.json
[2026-02-10 XX:XX:XX] INFO - Defaulting to Strategy C (Cash Preservation) ✓
[2026-02-10 XX:XX:XX] INFO - Strategy C active: No trading, monitoring only
[2026-02-10 XX:XX:XX] INFO - Bot operational in safe mode
```

**Critical Success Indicators:**
- ✅ "IBKR Gateway connected successfully"
- ✅ "Account: DU[XXXXXX] (Paper Trading)"
- ✅ "Defaulting to Strategy C"
- ✅ "DRY_RUN=true"

**If Still Fails:**
- Review Gateway logs: `docker logs ibkr-gateway --tail 50`
- Try even longer timeout (90s or 120s)
- Check if Gateway needs longer initialization (wait 5 minutes after Gateway start, then retry bot)
- Consider enhanced Gateway health check (verify API ready, not just port)

---

## STEP 5: VALIDATION & DOCUMENTATION

### Validation Checklist

```powershell
# 1. Verify bot connected
docker logs trading-bot --tail 50 | Select-String "connected successfully|Account:"

# 2. Verify Strategy C active
docker logs trading-bot --tail 50 | Select-String "Strategy C"

# 3. Verify DRY_RUN mode
docker logs trading-bot --tail 50 | Select-String "DRY_RUN=true"

# 4. Verify bot stays connected (check after 5 minutes)
Start-Sleep -Seconds 300
docker logs trading-bot --tail 20 | Select-String "connected|disconnect|error"
# Should show "connected" with no disconnection messages

# 5. Verify all containers healthy
docker ps --format "table {{.Names}}\t{{.Status}}"
# All should show "Up" and Gateway should show "healthy"

# 6. Test restart resilience
docker compose restart trading-bot
Start-Sleep -Seconds 60
docker logs trading-bot --tail 30 | Select-String "connected successfully"
# Should reconnect successfully after restart
```

**All checks must pass before proceeding.**

---

### Git Commit

```powershell
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production

# Stage modified files
git add src/broker/connection.py  # Or wherever connection code changed
git add src/config/gateway_config.py  # If config changed

# Commit with detailed notes
git commit -m "TASK-3.4.1: Fix Bot-Gateway TWS API authentication timeout

Root Cause: ib-insync default timeout (10s) too short for Gateway TWS API
initialization. Default clientId=0 may have conflicted with other clients.

Changes:
- Increased connection timeout: 10s → 60s
- Changed clientId: 0 → 100 (unique ID, avoid conflicts)
- [Optional: Added 2-minute pre-connection delay for TWS API readiness]

Validation:
✅ Bot successfully connects to Gateway TWS API
✅ Connection logs show 'IBKR Gateway connected successfully'
✅ Bot displays paper trading account: DU[XXXXXX]
✅ Bot enters Strategy C (Cash Preservation) default mode
✅ Connection survives bot restart (reconnect successful)
✅ Bot logs show DRY_RUN=true (safe mode confirmed)

Task 3.4.1 COMPLETE
Task 3.4 NOW 100% COMPLETE (unified Docker stack fully operational)

Next: Task 3.5 (zero-touch startup sequence)"

# Push to remote
git push origin main
```

---

## STEP 6: UPDATE BOARD

**Mark TASK-3.4.1 complete:**

```
Status: COMPLETE
Resolution: Increased connection timeout (10s → 60s) and changed clientId (0 → 100)
Validation: Bot successfully connects to Gateway, Strategy C active, DRY_RUN=true
Commit: [commit hash]
```

**Mark Task 3.4 as 100% complete:**

```
Task 3.4 status: ✅ COMPLETE (100%)
All objectives achieved:
- Unified Docker stack operational
- Single-command startup validated
- Bot successfully connects to Gateway
- Health monitoring with Discord alerts
- Documentation complete

Commits: d50fbaa (migration), [new commit] (API fix)
```

---

## TROUBLESHOOTING GUIDE

### Issue 1: Still Timing Out After Timeout Increase

**Symptom:** Bot still fails after increasing timeout to 60s

**Diagnosis:**
```powershell
# Check Gateway TWS API initialization timing
docker logs ibkr-gateway --since 5m | Select-String "TWS|API|Ready|Authenticated"
```

**Solution A: Increase timeout further**
```python
timeout=120  # Try 2 minutes
```

**Solution B: Add longer pre-connection delay**
```python
time.sleep(180)  # Wait 3 minutes after health check
```

**Solution C: Enhanced Gateway health check** (see below)

---

### Issue 2: Connection Works Once, Then Fails on Restart

**Symptom:** First connection succeeds, but bot can't reconnect after restart

**Diagnosis:**
```powershell
# Check if Gateway is holding previous connection
docker logs ibkr-gateway | Select-String "client|session|disconnect"
```

**Solution:** Use unique clientId that increments or is session-based
```python
import random
clientId = random.randint(100, 200)  # Random ID each startup
```

---

### Issue 3: Gateway Logs Show "Client [X] attempted connection but rejected"

**Symptom:** Gateway explicitly rejecting connection

**Diagnosis:** TrustedIPs or configuration issue

**Solution:**
```powershell
# Verify TrustedIPs is empty (allows all)
docker exec ibkr-gateway cat /home/ibgateway/Jts/jts.ini | Select-String "TrustedIPs"
# Should show: TrustedIPs= (empty)

# If not empty, fix:
docker exec ibkr-gateway sed -i 's/TrustedIPs=.*/TrustedIPs=/' /home/ibgateway/Jts/jts.ini
docker compose restart gateway
```

---

## ALTERNATIVE SOLUTION: Enhanced Gateway Health Check (If Timeout Fix Doesn't Work)

**This is a more robust but more complex solution.**

### Modify Gateway Health Check to Verify TWS API Ready

**File:** `docker/docker-compose.yml`

**Current Gateway health check (verifies port only):**
```yaml
healthcheck:
  test: ["CMD", "bash", "-c", "echo > /dev/tcp/localhost/4002"]
  interval: 30s
  timeout: 5s
  retries: 10
```

**Enhanced health check (verifies TWS API connection):**

```yaml
healthcheck:
  test: |
    python3 -c "
    from ib_insync import IB
    import sys
    ib = IB()
    try:
        # Test actual TWS API connection
        ib.connect('localhost', 4002, clientId=999, timeout=5)
        ib.disconnect()
        sys.exit(0)  # Success
    except:
        sys.exit(1)  # Failure
    "
  interval: 30s
  timeout: 10s
  retries: 10
  start_period: 120s  # Give Gateway 2 minutes before first health check
```

**Impact:**
- Gateway won't be marked "healthy" until TWS API actually works
- Bot startup delayed until API confirmed ready
- More reliable but slower startup

**To implement:**
1. Update docker-compose.yml with enhanced health check
2. Install ib-insync in Gateway container OR use curl with API endpoint test
3. Restart Gateway: `docker compose up -d gateway`
4. Wait for health check to pass (may take 2-3 minutes)
5. Bot will now start only when API is ready

---

## SUCCESS CRITERIA

**TASK-3.4.1 is complete when:**

- [ ] Bot successfully connects to Gateway TWS API
- [ ] Connection logs show "IBKR Gateway connected successfully"
- [ ] Bot displays paper trading account: DU[XXXXXX]
- [ ] Bot enters Strategy C (Cash Preservation) mode
- [ ] Bot logs show DRY_RUN=true (safe mode)
- [ ] Connection survives bot restart (reconnect works)
- [ ] Connection survives Gateway restart (bot reconnects automatically)
- [ ] Git commit created documenting fix
- [ ] TASK-3.4.1 marked complete on board
- [ ] Task 3.4 marked 100% complete on board

**At that point, Task 3.4 is fully complete and Task 3.5 can proceed.**

---

## NEXT STEPS AFTER TASK-3.4.1 COMPLETE

**Immediate:**
1. Monitor system for 30 minutes post-fix
2. Verify bot remains connected (no disconnections in logs)
3. Check Discord for any health alerts

**Next Session: Task 3.5 (Zero-Touch Startup)**
- Duration: 2-3 hours
- Goal: System boot → Docker Compose auto-starts → All containers operational
- Test: Reboot desktop → verify everything starts without manual intervention

---

## CRITICAL SAFETY REMINDERS

**Before Any Code Changes:**
1. Verify DRY_RUN=true in environment (check `docker exec trading-bot env | grep DRY_RUN`)
2. Verify TRADING_MODE=paper (check docker/.env)
3. No gameplan JSON should exist in /data/ (bot should default to Strategy C)

**After Connection Success:**
1. Do NOT load gameplan JSON without CRO approval
2. Do NOT change DRY_RUN to false
3. Do NOT switch to live trading mode

**The fix should ONLY change connection parameters (timeout, clientId). No trading logic changes.**

---

**Ready to execute. Report back with connection test results.**
```

---

## Operator Instructions

**Model Selection:** Sonnet (straightforward parameter tuning)
**Session Type:** Remediation/debugging session
**Estimated Duration:** 30-60 minutes

**Before Starting:**
1. Review overnight logs first (bot may have already connected)
2. If still failing, proceed with timeout + clientId fixes
3. Test connection manually before restarting bot
4. Monitor logs during bot restart

**Expected Outcome:**
- Bot successfully connects to Gateway
- Strategy C active (safe default)
- Git commit documenting fix
- TASK-3.4.1 complete → Task 3.4 100% complete

---

**Document:** TASK-3.4.1_Bot_Gateway_API_Authentication_Fix.md
**Date:** 2026-02-10
**Task:** TASK-3.4.1 — Resolve TWS API authentication timeout
**Estimated Effort:** 30-60 minutes
**Priority:** Important (does not block Task 3.5)
