# VSC HANDOFF: Coverage-1.1.3 — Broker Layer Tests

**Date:** 2026-02-06
**Requested By:** Sprint Plan (Phase 1.1 Test Build-Out)
**Target Completion:** 2026-02-14 (Week 1 Milestone)
**Coverage Target:** ≥92%
**Priority:** Important (Foundation for all other test layers)

---

## 1. OBJECTIVE

Build comprehensive test suite for the broker integration layer, validating IBKR Gateway communication patterns, connection lifecycle management, market data retrieval, and historical data handling. This test suite **must encode alpha learnings as assertions** to prevent regression of solved issues (buffer overflow, timeout propagation, contract qualification).

The broker layer is the **foundational dependency** for all higher layers (strategy, risk, execution). Robust mocking here enables pure unit testing in subsequent phases without live Gateway dependencies.

---

## 2. FILE STRUCTURE

Create three new test files in the repository:

```
tests/
├── unit/
│   ├── test_broker_connection.py       # NEW — Connection lifecycle, retry, cleanup
│   └── test_broker_market_data.py      # NEW — Market data requests, snapshot enforcement
└── integration/
    └── test_gateway_communication.py   # NEW — Full Gateway comm cycle with mocks
```

**Existing Infrastructure (from Coverage-1.1.2):**
- `tests/conftest.py` — Pytest fixtures, mock Gateway helpers
- `tests/fixtures/` — Mock response data, test contracts
- `pyproject.toml` — Pytest async configuration

---

## 3. LOGIC FLOW (Pseudo-code)

### File 1: `test_broker_connection.py`

**Purpose:** Unit tests for connection establishment, retry logic, ClientId management, and cleanup.

```python
# Setup: Mock IB Gateway client, patch connection methods

class TestBrokerConnection:

    def test_connection_establishment_success():
        # GIVEN: Gateway is available at localhost:4002
        # WHEN: Broker connects with valid ClientId
        # THEN: Connection succeeds, isConnected() returns True
        # AND: ClientId is timestamp-based (validate format)

    def test_connection_retry_on_failure():
        # GIVEN: Gateway initially unavailable
        # WHEN: Connection attempted with retry policy
        # THEN: Exponential backoff occurs (validate timing)
        # AND: Connection succeeds on Nth retry
        # AND: Max retry limit respected (fail after N attempts)

    def test_client_id_uniqueness():
        # GIVEN: Multiple connection instances
        # WHEN: Each requests a ClientId
        # THEN: All ClientIds are unique (timestamp-based)
        # AND: Format is integer derived from Unix timestamp

    def test_connection_cleanup_on_disconnect():
        # GIVEN: Active connection to Gateway
        # WHEN: Disconnect method called
        # THEN: Connection closed cleanly
        # AND: No lingering subscriptions or callbacks
        # AND: Resources released (thread cleanup)

    def test_connection_timeout_handling():
        # GIVEN: Gateway hangs during connection attempt
        # WHEN: Timeout threshold exceeded
        # THEN: Connection attempt aborted
        # AND: Appropriate exception raised
        # AND: System does not hang indefinitely
```

### File 2: `test_broker_market_data.py`

**Purpose:** Unit tests for market data requests with **critical alpha learnings encoded**.

```python
# Setup: Mock market data response patterns

class TestMarketDataRetrieval:

    def test_snapshot_mode_enforcement():
        # CRITICAL ALPHA LEARNING: Snapshot=True required
        # GIVEN: Request for real-time market data (SPY, QQQ)
        # WHEN: reqMktData() called
        # THEN: snapshot parameter MUST be True
        # AND: Test FAILS if snapshot=False (prevent buffer overflow regression)

    def test_market_data_validation():
        # GIVEN: Mock market data response (price, volume, timestamp)
        # WHEN: Data received from Gateway
        # THEN: All required fields present (bid, ask, last, volume)
        # AND: Prices are positive floats
        # AND: Timestamp is recent (within last 60 seconds)

    def test_stale_data_detection():
        # GIVEN: Market data with old timestamp (>5 minutes)
        # WHEN: Stale check performed
        # THEN: Data flagged as stale
        # AND: Strategy layer notified to use Strategy C

    def test_contract_qualification_before_data_request():
        # CRITICAL ALPHA LEARNING: Must qualify contracts first
        # GIVEN: Unqualified contract object (symbol='SPY')
        # WHEN: Attempting market data request
        # THEN: Contract qualification occurs FIRST
        # AND: Only qualified contracts proceed to data request
        # AND: Unqualified contracts raise appropriate error

    def test_market_data_error_handling():
        # GIVEN: Gateway returns error code (invalid symbol, no permission)
        # WHEN: Error callback triggered
        # THEN: Error logged with code and description
        # AND: System degrades gracefully (no crash)
        # AND: Strategy C activated on critical errors
```

### File 3: `test_gateway_communication.py`

**Purpose:** Integration tests for full communication cycle including historical data.

```python
# Setup: Mock Gateway with realistic response timing

class TestGatewayIntegration:

    def test_historical_data_request_rth_only():
        # CRITICAL ALPHA LEARNING: 1-hour RTH windows only
        # GIVEN: Request for historical bars (SPY, 1-hour, RTH)
        # WHEN: reqHistoricalData() called
        # THEN: Duration parameter = "3600 S" (1 hour)
        # AND: useRTH parameter = True
        # AND: Timeout parameter threaded through entire call chain
        # AND: Response contains bars with OHLCV data

    def test_historical_data_timeout_propagation():
        # CRITICAL ALPHA LEARNING: Timeout must propagate through stack
        # GIVEN: Historical data request with timeout=30s
        # WHEN: Gateway response delayed
        # THEN: Timeout enforced at every layer (request → callback → processing)
        # AND: Timeout exception raised if exceeded
        # AND: No silent hang conditions

    def test_concurrent_requests_handling():
        # GIVEN: Multiple simultaneous requests (SPY data + QQQ data)
        # WHEN: Requests submitted in parallel
        # THEN: Each tracked with unique reqId
        # AND: Responses correctly matched to requests
        # AND: No cross-contamination of data streams

    def test_gateway_disconnection_recovery():
        # GIVEN: Active data stream from Gateway
        # WHEN: Gateway connection lost
        # THEN: Disconnection detected immediately
        # AND: Pending requests cancelled
        # AND: Reconnection attempted with exponential backoff
        # AND: Data streams re-established on reconnection

    def test_full_workflow_mock_gateway():
        # GIVEN: Mock Gateway simulating realistic response patterns
        # WHEN: Complete workflow executed:
        #       1. Connect to Gateway
        #       2. Qualify contract (SPY)
        #       3. Request market data (snapshot=True)
        #       4. Request historical data (1-hour RTH)
        #       5. Disconnect cleanly
        # THEN: All steps succeed in sequence
        # AND: No errors or warnings logged
        # AND: All alpha learnings respected (snapshot, timeout, qualification)
```

---

## 4. DEPENDENCIES

### External Libraries (Already in pyproject.toml)
```python
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from ib_insync import IB, Contract, Stock
```

### Internal Modules (Broker Layer Code)
```python
from src.broker.connection import IBKRConnection
from src.broker.market_data import MarketDataProvider
from src.broker.contracts import ContractManager
```

### Test Infrastructure (from Coverage-1.1.2)
```python
from tests.conftest import mock_gateway, test_contracts
from tests.fixtures.mock_responses import (
    MOCK_MARKET_DATA_RESPONSE,
    MOCK_HISTORICAL_DATA_RESPONSE,
    MOCK_CONTRACT_DETAILS
)
```

### Environment Variables
```bash
# Required for integration tests (mocked, not real Gateway)
IBKR_GATEWAY_HOST=localhost
IBKR_GATEWAY_PORT=4002
IBKR_CLIENT_ID_BASE=1000
```

---

## 5. INPUT/OUTPUT CONTRACT

### Input (Test Fixtures)
```python
# Mock Gateway client with configurable behavior
@pytest.fixture
def mock_ib_client():
    """Returns a mock IB client with predefined responses."""
    client = Mock(spec=IB)
    client.isConnected.return_value = True
    client.reqId = 1000  # Starting request ID
    return client

# Test contract definitions
@pytest.fixture
def spy_contract():
    """Returns a qualified SPY contract for testing."""
    return Stock('SPY', 'SMART', 'USD')

# Mock market data response
@pytest.fixture
def mock_market_data():
    """Returns realistic market data structure."""
    return {
        'symbol': 'SPY',
        'bid': 685.50,
        'ask': 685.52,
        'last': 685.51,
        'volume': 1250000,
        'timestamp': datetime.now(timezone.utc)
    }
```

### Output (Test Assertions)
```python
# All tests should validate:
# 1. Function returns expected data structure
# 2. Side effects occur correctly (logging, callbacks)
# 3. Error conditions handled gracefully
# 4. Alpha learnings enforced (snapshot=True, timeout propagation, etc.)

# Example assertion patterns:
assert result.snapshot == True, "CRITICAL: snapshot mode must be enforced"
assert result.timeout <= 30, "Timeout must be respected"
assert contract.qualified == True, "Contract must be qualified before data request"
```

---

## 6. INTEGRATION POINTS

### Broker Layer Code Structure (Expected)
```
src/broker/
├── __init__.py
├── connection.py          # IBKRConnection class
├── market_data.py         # MarketDataProvider class
├── contracts.py           # ContractManager class
└── exceptions.py          # Custom broker exceptions
```

### Mock Gateway Interface (from Coverage-1.1.2)
```python
# tests/conftest.py should provide:
@pytest.fixture
def mock_gateway():
    """Full mock Gateway with realistic response patterns."""
    # Should simulate:
    # - Connection handshake
    # - Request/response cycles with reqId tracking
    # - Async callbacks
    # - Error conditions (timeouts, invalid symbols)
    # - Disconnection scenarios
```

### Test Execution Integration
```bash
# Run broker layer tests only:
pytest tests/unit/test_broker_connection.py -v
pytest tests/unit/test_broker_market_data.py -v
pytest tests/integration/test_gateway_communication.py -v

# Run with coverage report:
pytest tests/unit/test_broker*.py tests/integration/test_gateway*.py \
    --cov=src/broker --cov-report=term-missing
```

---

## 7. DEFINITION OF DONE

### Coverage Gate
- [ ] **≥92% coverage** of `src/broker/` module
- [ ] Coverage report generated: `pytest --cov=src/broker --cov-report=html`
- [ ] No uncovered critical paths (connection retry, error handling)

### Code Quality Gates
- [ ] `ruff check` passes with zero errors
- [ ] `black --check` formatting verified
- [ ] `mypy` type checking passes (strict mode)
- [ ] All tests pass: `pytest tests/unit/test_broker*.py tests/integration/test_gateway*.py`

### Alpha Learning Validation
- [ ] ✅ **CRITICAL:** Test explicitly asserts `snapshot=True` on all market data requests
- [ ] ✅ **CRITICAL:** Test validates timeout parameter propagation through call stack
- [ ] ✅ **CRITICAL:** Test enforces contract qualification before data requests
- [ ] Historical data requests use 1-hour RTH-only windows
- [ ] ClientId rotation uses timestamp-based generation

### Functional Validation
- [ ] Connection lifecycle: establish → use → disconnect
- [ ] Retry logic with exponential backoff verified
- [ ] Stale data detection working correctly
- [ ] Error handling degrades gracefully (no crashes)
- [ ] Concurrent request handling validated

### Documentation
- [ ] Docstrings added to all test functions explaining purpose
- [ ] Complex test scenarios have inline comments
- [ ] Edge cases documented in test names (use descriptive naming)

### QA Review Readiness
- [ ] Test output is clean (no warnings, deprecations)
- [ ] Test execution time is reasonable (<30 seconds total for broker layer)
- [ ] No flaky tests (run 3 times, all passes)
- [ ] Ready for @QA_Lead review session

---

## 8. EDGE CASES TO TEST

### Connection Edge Cases
- **Scenario:** Gateway not running at connection attempt
  - **Expected:** Retry with exponential backoff, eventually fail with clear error
- **Scenario:** Gateway disconnects mid-session (network glitch)
  - **Expected:** Detect disconnection, attempt reconnection, preserve state
- **Scenario:** Multiple simultaneous connection attempts (race condition)
  - **Expected:** Only one connection succeeds, others get unique ClientIds or fail gracefully

### Market Data Edge Cases
- **Scenario:** Market data request for invalid symbol (INVALID_TICKER)
  - **Expected:** Gateway returns error code, system logs and degrades to Strategy C
- **Scenario:** Market data arrives with missing fields (e.g., no volume)
  - **Expected:** Validation catches incomplete data, flags as invalid
- **Scenario:** Timestamp on market data is >5 minutes old
  - **Expected:** Stale data flag raised, Strategy C activated
- **Scenario:** Concurrent market data requests for 10+ symbols
  - **Expected:** Each tracked with unique reqId, no cross-contamination

### Historical Data Edge Cases
- **Scenario:** Historical data request times out (Gateway overloaded)
  - **Expected:** Timeout exception raised at correct layer, request cancelled
- **Scenario:** Historical data request for extended hours (should be RTH only)
  - **Expected:** Test FAILS if useRTH != True (enforce alpha learning)
- **Scenario:** Request duration exceeds maximum allowed (e.g., 1 year of 1-min bars)
  - **Expected:** Gateway error returned, system handles gracefully

### Contract Qualification Edge Cases
- **Scenario:** Contract qualification fails (symbol not found on exchange)
  - **Expected:** Error logged, contract marked as invalid, no data request attempted
- **Scenario:** Contract already qualified, re-qualification attempted
  - **Expected:** No duplicate qualification, use cached result

### Cleanup Edge Cases
- **Scenario:** Disconnect called while active data streams running
  - **Expected:** All streams cancelled, callbacks unregistered, clean shutdown
- **Scenario:** Unhandled exception during connection attempt
  - **Expected:** Exception logged, resources cleaned up, no memory leaks

---

## 9. ROLLBACK PLAN

If Coverage-1.1.3 implementation introduces regressions or blocks progress:

### Immediate Rollback
1. **Identify failing test(s):** Run full test suite to isolate failures
2. **Check if blocker is in test or production code:**
   - If test is incorrect: Fix test, do not modify production code
   - If production code has regression: Revert recent broker layer changes
3. **Use git bisect to find breaking commit:**
   ```bash
   git bisect start
   git bisect bad HEAD
   git bisect good [last-known-good-commit]
   # Git will checkout commits for testing
   pytest tests/unit/test_broker*.py
   git bisect good/bad  # Based on test result
   ```

### Disable Feature Without Breaking
- Broker layer is foundational — cannot "disable" entirely
- Instead: **Mock out failing component** for downstream testing:
  ```python
  # In conftest.py, temporarily bypass failing broker code:
  @pytest.fixture
  def mock_broken_broker_component():
      return Mock()  # Returns safe mock until issue resolved
  ```

### Escalation Path
- If rollback required: Notify @PM, update board status to BLOCKED
- If issue is in test infrastructure (Coverage-1.1.2): May need to revisit foundation
- If issue is in alpha learnings interpretation: Consult @Lead_Quant for clarification

---

## 10. IMPLEMENTATION GUIDANCE

### Recommended VSCode Copilot Workflow

**Step 1: Create test file stubs**
```bash
# In VSCode terminal:
mkdir -p tests/unit tests/integration
touch tests/unit/test_broker_connection.py
touch tests/unit/test_broker_market_data.py
touch tests/integration/test_gateway_communication.py
```

**Step 2: Start with `test_broker_connection.py`**
- Open file in VSCode
- Use Copilot Chat: "Generate pytest unit tests for IBKR connection lifecycle based on the blueprint in [this file path]"
- Implement tests one by one, running after each:
  ```bash
  pytest tests/unit/test_broker_connection.py::TestBrokerConnection::test_connection_establishment_success -v
  ```

**Step 3: Implement `test_broker_market_data.py`**
- **CRITICAL:** Start with `test_snapshot_mode_enforcement` first — this is the highest-priority alpha learning
- Copilot prompt: "Generate test that asserts snapshot=True on all reqMktData calls, per alpha learnings"
- Validate each test individually before moving to next

**Step 4: Implement `test_gateway_communication.py`**
- These are integration tests — use the mock Gateway fixture from Coverage-1.1.2
- Test full workflows end-to-end
- Expect longer execution times (async operations)

**Step 5: Coverage validation**
```bash
# Generate coverage report:
pytest tests/unit/test_broker*.py tests/integration/test_gateway*.py \
    --cov=src/broker --cov-report=term-missing --cov-report=html

# Open HTML report:
open htmlcov/index.html  # macOS
# Review lines NOT covered, add tests if needed to reach ≥92%
```

**Step 6: Quality gates**
```bash
# Run all quality checks:
ruff check tests/unit/test_broker*.py tests/integration/test_gateway*.py
black --check tests/unit/test_broker*.py tests/integration/test_gateway*.py
mypy tests/unit/test_broker*.py tests/integration/test_gateway*.py

# Fix any issues before proceeding to QA review
```

---

## 11. ACCEPTANCE CRITERIA CHECKLIST

Before submitting for QA review, operator should verify:

### Functional Criteria
- [ ] All 15+ test functions implemented and passing
- [ ] Connection retry logic validated with timing assertions
- [ ] Market data snapshot mode enforcement working
- [ ] Historical data timeout propagation confirmed
- [ ] Contract qualification sequence enforced
- [ ] Error handling degrades gracefully (no crashes on bad input)

### Alpha Learning Criteria (Non-Negotiable)
- [ ] ✅ `snapshot=True` assertion present in market data tests
- [ ] ✅ Timeout parameter threading validated in historical data tests
- [ ] ✅ Contract qualification enforced before data requests
- [ ] ✅ 1-hour RTH-only historical data pattern used
- [ ] ✅ ClientId uniqueness validated (timestamp-based)

### Coverage Criteria
- [ ] ≥92% coverage of `src/broker/` module achieved
- [ ] All critical paths covered (connection, retry, data retrieval, errors)
- [ ] No untested error handlers or exception paths

### Code Quality Criteria
- [ ] Ruff: Zero errors, zero warnings
- [ ] Black: Formatting compliant
- [ ] Mypy: Type checking passes (strict mode)
- [ ] Pytest: All tests green, no flaky tests

### Documentation Criteria
- [ ] Every test function has docstring explaining purpose
- [ ] Complex assertions have inline comments
- [ ] Edge cases clearly labeled in test names

### Readiness Criteria
- [ ] Test suite runs in <30 seconds
- [ ] No external dependencies required (all mocked)
- [ ] Tests can run in CI/CD environment (no manual setup)
- [ ] Ready for @QA_Lead formal review

---

## 12. NOTES FOR FACTORY FLOOR

### Time Estimate
- **Connection tests (file 1):** 3–4 hours
- **Market data tests (file 2):** 3–4 hours (includes critical alpha assertions)
- **Integration tests (file 3):** 2–4 hours (async complexity)
- **Coverage gap filling:** 1–2 hours (iterate to reach ≥92%)
- **Quality gates + documentation:** 1–2 hours
- **Total:** 10–16 hours over 2–3 days

### Common Pitfalls to Avoid
1. **Forgetting `snapshot=True` assertion** — This is the #1 priority from alpha learnings
2. **Not propagating timeout through full call stack** — Easy to miss intermediate layers
3. **Using live Gateway instead of mocks** — All tests should use fixtures from Coverage-1.1.2
4. **Flaky async tests** — Use `pytest.mark.asyncio` and proper awaits
5. **Incomplete error handling tests** — Every exception path needs coverage

### When to Ask for Help
- If mock Gateway fixture from Coverage-1.1.2 is insufficient → Consult @Systems_Architect
- If alpha learnings are ambiguous → Consult @Lead_Quant for clarification
- If coverage target unreachable → Identify untestable code paths, document why
- If tests are flaky (pass/fail inconsistently) → Consult @QA_Lead for debugging strategy

---

**Blueprint Status:** COMPLETE
**Ready for Factory Floor:** YES
**Next Steps:** Operator implements in VSCode with Copilot, targets Feb 14 completion
**QA Review Trigger:** When operator believes Definition of Done is met

---

*Blueprint Version: 1.0*
*Author: @Systems_Architect, Charter & Stone Capital Workshop*
*Sprint: Phase 1.1 Test Build-Out, Week 1 Milestone*
*Reviewed By: (Pending operator implementation)*
