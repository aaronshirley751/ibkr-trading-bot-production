# TEST ADAPTATION GUIDE: Coverage-1.1.3 Phase 1a → Phase 1b Integration

**Date:** 2026-02-06
**Purpose:** Adapt Phase 1a test suite to test broker layer production code (Phase 1b)
**Scope:** 28 tests requiring adaptation (26 failing + 2 skipped)
**Time Estimate:** 1-2 hours
**Critical Principle:** PRESERVE TEST INTENT — Change targets, NOT assertions

---

## 1. OBJECTIVE

Phase 1a tests were written to test `ib_insync.IB` directly before our broker classes existed. Now that `IBKRConnection`, `MarketDataProvider`, and `ContractManager` are implemented, we must adapt the tests to target these classes while **preserving all behavioral assertions**.

**What Changes:**
- Import statements (add `from src.broker import ...`)
- Test setup (replace `IB()` with `IBKRConnection()`, etc.)
- Method calls (replace `ib.reqMktData()` with `provider.request_market_data()`, etc.)

**What Does NOT Change:**
- Test assertions (the behavioral contract)
- Expected exceptions and error conditions
- Alpha learning validations
- Edge case scenarios

---

## 2. ADAPTATION PATTERNS

### Pattern A: Connection Tests

**BEFORE (tests ib_insync directly):**
```python
def test_connection_establishment_success():
    ib = IB()
    ib.connect('localhost', 4002, clientId=1)
    assert ib.isConnected()
```

**AFTER (tests IBKRConnection):**
```python
def test_connection_establishment_success():
    connection = IBKRConnection(host='localhost', port=4002, client_id=1)
    with patch.object(connection, '_ib') as mock_ib:
        mock_ib.isConnected.return_value = True
        success = connection.connect()
        assert success
        assert connection.is_connected()
```

---

### Pattern B: Market Data Tests with Snapshot Enforcement

**BEFORE:**
```python
def test_snapshot_mode_enforcement():
    ib = IB()
    contract = Stock('SPY', 'SMART', 'USD')
    # Test expects snapshot=True
    ib.reqMktData(contract, '', snapshot=True)
```

**AFTER:**
```python
def test_snapshot_mode_enforcement():
    connection = IBKRConnection()
    provider = MarketDataProvider(connection, snapshot_mode=True)
    contract = Stock('SPY', 'SMART', 'USD')

    with patch.object(provider, '_connection') as mock_conn:
        mock_conn.is_connected.return_value = True
        with patch.object(provider, '_ib') as mock_ib:
            # Mock the contract as qualified
            contract.conId = 123456
            mock_ib.qualifyContracts.return_value = [contract]
            mock_ib.reqMktData.return_value = Mock()

            result = provider.request_market_data(contract)

            # CRITICAL: Assert snapshot=True was passed
            call_args = mock_ib.reqMktData.call_args
            assert call_args.kwargs.get('snapshot', False) == True
```

---

### Pattern C: Snapshot Mode Violation (ValueError Expected)

**BEFORE:**
```python
def test_snapshot_false_is_forbidden():
    ib = IB()
    with pytest.raises(ValueError, match="snapshot.*forbidden"):
        # Some hypothetical validation
        pass
```

**AFTER:**
```python
def test_snapshot_false_is_forbidden():
    connection = IBKRConnection()
    # CRITICAL: This should raise ValueError at initialization
    with pytest.raises(ValueError, match="snapshot.*FORBIDDEN"):
        provider = MarketDataProvider(connection, snapshot_mode=False)
```

---

### Pattern D: Contract Qualification Tests

**BEFORE:**
```python
def test_contract_qualification_before_data_request():
    ib = IB()
    contract = Stock('SPY', 'SMART', 'USD')
    # Test that unqualified contracts are rejected
    with pytest.raises(Exception):
        ib.reqMktData(contract)
```

**AFTER:**
```python
def test_contract_qualification_before_data_request():
    connection = IBKRConnection()
    provider = MarketDataProvider(connection)
    contract = Stock('SPY', 'SMART', 'USD')
    # Contract NOT qualified (no conId)

    with patch.object(provider, '_connection') as mock_conn:
        mock_conn.is_connected.return_value = True

        # CRITICAL: Should raise ContractNotQualifiedError
        with pytest.raises(ContractNotQualifiedError):
            provider.request_market_data(contract)
```

---

### Pattern E: Historical Data with Timeout Propagation

**BEFORE:**
```python
def test_historical_data_timeout_propagation():
    ib = IB()
    contract = Stock('SPY', 'SMART', 'USD')
    # Test timeout parameter
    with pytest.raises(TimeoutError):
        ib.reqHistoricalData(contract, '', '3600 S', '1 min', 'TRADES', 1, 1, False, [])
```

**AFTER:**
```python
def test_historical_data_timeout_propagation():
    connection = IBKRConnection()
    provider = MarketDataProvider(connection)
    contract = Stock('SPY', 'SMART', 'USD')
    contract.conId = 123456  # Qualified

    with patch.object(provider, '_connection') as mock_conn:
        mock_conn.is_connected.return_value = True
        with patch.object(provider, '_ib') as mock_ib:
            # Simulate timeout
            mock_ib.reqHistoricalData.side_effect = TimeoutError("Request timed out")

            # CRITICAL: TimeoutError should propagate up
            with pytest.raises(TimeoutError):
                provider.request_historical_data(contract, timeout=5)
```

---

### Pattern F: ClientId Uniqueness (Already Passing — Preserve As-Is)

**CURRENT (already correct):**
```python
def test_client_id_uniqueness():
    id1 = IBKRConnection.generate_client_id()
    time.sleep(0.01)
    id2 = IBKRConnection.generate_client_id()
    assert id1 != id2
```

**ACTION:** Leave unchanged — this test is already correct and passing.

---

### Pattern G: Data Validation Logic (Already Passing — Preserve As-Is)

**CURRENT (already correct):**
```python
def test_market_data_validation():
    data = {
        'symbol': 'SPY',
        'bid': 685.50,
        'ask': 685.52,
        'last': 685.51,
        'volume': 1250000,
        'timestamp': datetime.now(timezone.utc)
    }
    # Validation logic test
    assert data['bid'] > 0
    assert data['ask'] >= data['bid']
```

**ACTION:** Leave unchanged — these are pure logic tests already passing.

---

## 3. FILE-BY-FILE ADAPTATION INSTRUCTIONS

### File 1: `tests/unit/test_broker_connection.py`

**Tests Requiring Adaptation:** 6 tests (lines vary)

**Import Changes:**
```python
# ADD these imports:
from src.broker import IBKRConnection
from src.broker.exceptions import (
    ConnectionTimeoutError,
    MaxRetriesExceededError
)
from unittest.mock import Mock, patch, MagicMock
```

**Tests to Adapt:**

1. **`test_connection_establishment_success`**
   - Replace: `ib = IB()` → `connection = IBKRConnection()`
   - Replace: `ib.connect()` → `connection.connect()`
   - Replace: `ib.isConnected()` → `connection.is_connected()`
   - Preserve assertion: Connection succeeds

2. **`test_connection_retry_on_failure`**
   - Replace: `ib = IB()` → `connection = IBKRConnection(max_retries=3)`
   - Mock connection failures, verify exponential backoff
   - Preserve assertion: Retry logic executes correctly

3. **`test_connection_timeout_handling`**
   - Replace: `ib.connect()` → `connection.connect()`
   - Simulate timeout, verify TimeoutError raised
   - Preserve assertion: Timeout is respected

4. **`test_connection_cleanup_on_disconnect`**
   - Replace: `ib.disconnect()` → `connection.disconnect()`
   - Preserve assertion: Resources cleaned up properly

**Tests Already Correct (No Changes):**
- `test_client_id_uniqueness()` ✅
- `test_client_id_uniqueness_across_connections()` ✅

---

### File 2: `tests/unit/test_market_data.py`

**Tests Requiring Adaptation:** 15 tests

**Import Changes:**
```python
# ADD these imports:
from src.broker import IBKRConnection, MarketDataProvider
from src.broker.exceptions import (
    ContractNotQualifiedError,
    StaleDataError,
    SnapshotModeViolationError
)
```

**Critical Tests (Alpha Learnings):**

1. **`test_snapshot_mode_enforcement`** (CRITICAL)
   - Setup: `provider = MarketDataProvider(connection, snapshot_mode=True)`
   - Mock `provider._ib.reqMktData()`
   - Assert: `snapshot=True` in call arguments
   - **This is the #1 priority alpha learning test**

2. **`test_snapshot_false_is_forbidden`** (CRITICAL)
   - Assert: `MarketDataProvider(connection, snapshot_mode=False)` raises `SnapshotModeViolationError`
   - Preserve error message check: "FORBIDDEN"

3. **`test_contract_qualification_before_data_request`** (CRITICAL)
   - Setup unqualified contract (no conId)
   - Assert: `provider.request_market_data(contract)` raises `ContractNotQualifiedError`

4. **`test_historical_data_timeout_propagation`** (CRITICAL)
   - Mock timeout in `provider._ib.reqHistoricalData()`
   - Assert: `TimeoutError` propagates through `provider.request_historical_data()`

5. **`test_historical_data_rth_only`** (CRITICAL)
   - Assert: `provider.request_historical_data(contract, use_rth=False)` raises `ValueError`
   - Preserve error message check: "RTH"

**Standard Tests:**

6. **`test_market_data_validation`**
   - Create `provider = MarketDataProvider(connection)`
   - Call `provider.validate_market_data(data)`
   - Preserve all validation assertions (bid ≤ ask, positive prices, etc.)

7. **`test_stale_data_detection`**
   - Create `provider = MarketDataProvider(connection, stale_threshold_seconds=300)`
   - Call `provider.is_data_stale(old_timestamp)`
   - Assert: Returns True for timestamps >5 minutes old

**Tests Already Correct (No Changes):**
- `test_market_data_validation()` ✅ (pure logic)
- Any test that just validates data structures without making API calls

---

### File 3: `tests/integration/test_gateway_communication.py`

**Tests Requiring Adaptation:** 8 tests

**Import Changes:**
```python
# ADD these imports:
from src.broker import IBKRConnection, MarketDataProvider, ContractManager
from src.broker.exceptions import ContractQualificationError
```

**Tests to Adapt:**

1. **`test_full_workflow_mock_gateway`**
   - Setup: Create `connection`, `manager`, `provider`
   - Mock entire Gateway interaction chain
   - Execute workflow:
     ```python
     connection.connect()
     contract = manager.qualify_contract('SPY')
     data = provider.request_market_data(contract)
     bars = provider.request_historical_data(contract)
     connection.disconnect()
     ```
   - Preserve assertion: All steps succeed, alpha learnings respected

2. **`test_gateway_disconnection_recovery`**
   - Setup: `connection = IBKRConnection()`
   - Simulate disconnection: `connection._ib.isConnected.return_value = False`
   - Call `connection.reconnect()`
   - Preserve assertion: Reconnection succeeds

3. **`test_concurrent_requests_handling`**
   - Setup: Multiple `provider.request_market_data()` calls
   - Verify each has unique reqId
   - Preserve assertion: No cross-contamination

**Tests with Skip Decorators:**
- Remove `@pytest.mark.skip` decorators after adaptation
- These tests were skipped because they needed broker classes to exist

---

## 4. MOCK STRATEGY

All tests should use mocks — **do not connect to real Gateway**.

### Standard Mock Setup Pattern

```python
def test_example():
    # Create our broker instances
    connection = IBKRConnection()
    provider = MarketDataProvider(connection)

    # Mock the underlying ib_insync client
    with patch.object(connection, '_ib') as mock_ib:
        mock_ib.isConnected.return_value = True

        # Mock the provider's connection check
        with patch.object(provider, '_connection') as mock_conn:
            mock_conn.is_connected.return_value = True

            # Test code here
            result = provider.request_market_data(contract)

            # Assertions
            assert result is not None
```

### Qualified Contract Mock

```python
# To mock a qualified contract:
contract = Stock('SPY', 'SMART', 'USD')
contract.conId = 123456  # This marks it as qualified
```

### Mock Market Data Response

```python
# To mock market data response:
mock_data = {
    'symbol': 'SPY',
    'bid': 685.50,
    'ask': 685.52,
    'last': 685.51,
    'volume': 1250000,
    'timestamp': datetime.now(timezone.utc),
    'snapshot': True
}
mock_ib.reqMktData.return_value = mock_data
```

---

## 5. VALIDATION CHECKLIST

After adaptation, verify:

### Test Execution
- [ ] All 35 tests pass (0 failed, 0 skipped)
- [ ] No tests marked with `@pytest.mark.skip`
- [ ] Test execution time <60 seconds
- [ ] Run 3 times: All passes each time (no flaky tests)

### Alpha Learning Validations
- [ ] `test_snapshot_mode_enforcement` ✅ PASS
- [ ] `test_snapshot_false_is_forbidden` ✅ PASS (raises SnapshotModeViolationError)
- [ ] `test_contract_qualification_before_data_request` ✅ PASS (raises ContractNotQualifiedError)
- [ ] `test_historical_data_timeout_propagation` ✅ PASS (TimeoutError propagates)
- [ ] `test_historical_data_rth_only` ✅ PASS (ValueError if use_rth=False)

### Coverage Validation (Phase 1c)
- [ ] Run: `pytest --cov=src/broker --cov-report=html`
- [ ] Coverage: ≥92% of `src/broker/` module
- [ ] HTML report generated: `htmlcov/index.html`
- [ ] Critical paths covered: snapshot enforcement, timeout, retry logic

### Quality Gates
- [ ] `ruff check tests/` — zero errors
- [ ] `black --check tests/` — formatting compliant
- [ ] `mypy tests/` — type checking passes

---

## 6. DEFINITION OF DONE

Before marking Coverage-1.1.3 Phase 1c complete:

**Test Results:**
- [x] Phase 1a: Test suite authored (35 tests) ✅ Complete 2/6
- [x] Phase 1b: Broker implementation (885 lines) ✅ Complete 2/6
- [ ] Phase 1c: Tests adapted to target broker classes
- [ ] Phase 1c: All 35 tests passing (0 pending, 0 skipped, 0 failed)
- [ ] Phase 1c: ≥92% coverage of `src/broker/` module validated

**Commit Message Template:**
```
Coverage-1.1.3 Phase 1c: Test adaptation & validation complete

Adapted Phase 1a tests to target broker layer production code:
- Updated 28 tests to test IBKRConnection, MarketDataProvider, ContractManager
- Preserved all behavioral assertions (test intent unchanged)
- Removed @pytest.mark.skip decorators (tests now executable)

Test Results: 35/35 passing (0 failed, 0 skipped)
Coverage: XX% of src/broker/ module (target ≥92%)

Alpha Learning Validations:
- snapshot=True enforcement ✅ PASS
- Contract qualification check ✅ PASS
- Timeout propagation ✅ PASS
- RTH-only historical data ✅ PASS
- ClientId uniqueness ✅ PASS

Quality Gates: ruff ✅ black ✅ mypy ✅

Closes Coverage-1.1.3 (Phase 1a+1b+1c complete)
```

---

## 7. TROUBLESHOOTING

### Issue: Tests still fail after adaptation

**Check:**
1. Are imports correct? (`from src.broker import ...`)
2. Are mocks patching the right objects? (Use `patch.object()` not `patch()`)
3. Is the contract marked as qualified? (`contract.conId = 123456`)
4. Is the connection mocked as connected? (`mock_conn.is_connected.return_value = True`)

### Issue: Coverage <92%

**Actions:**
1. Run: `pytest --cov=src/broker --cov-report=term-missing`
2. Review "Missing" column — which lines aren't covered?
3. Check if uncovered lines are:
   - Error handlers (may need error injection tests)
   - Edge cases (may need additional test scenarios)
   - Logging statements (acceptable to exclude from coverage)
4. Add tests to cover critical uncovered paths

### Issue: Alpha learning test fails

**Priority:** CRITICAL — Do not proceed until fixed

**Actions:**
1. Verify production code enforces the alpha learning (check `src/broker/`)
2. Verify test asserts the enforcement (check test assertions)
3. If production code missing enforcement: Fix production code first
4. If test assertion incorrect: Verify test adaptation pattern

---

## 8. TIME ESTIMATE

**By Task:**
- File 1 (test_broker_connection.py): 20-30 minutes (6 tests)
- File 2 (test_market_data.py): 40-50 minutes (15 tests, includes critical alpha tests)
- File 3 (test_gateway_communication.py): 30-40 minutes (8 tests, integration complexity)
- Validation & Coverage: 20-30 minutes
- Quality gates & commit: 10-15 minutes

**Total: 2-2.5 hours**

---

## 9. CRITICAL REMINDERS

**PRESERVE TEST INTENT:**
- If a test asserted `ValueError` should be raised → Still assert `ValueError`
- If a test checked for exponential backoff → Still check exponential backoff
- If a test validated data fields → Still validate same fields

**CHANGE ONLY TARGETS:**
- Replace `IB()` → `IBKRConnection()`
- Replace `ib.reqMktData()` → `provider.request_market_data()`
- Replace `ib.connect()` → `connection.connect()`

**DO NOT:**
- Remove test assertions
- Weaken test requirements
- Skip tests that are "too hard" to adapt
- Modify alpha learning validations

**SUCCESS CRITERIA:**
- 35/35 tests passing
- ≥92% coverage
- All alpha learning tests passing
- Zero quality gate violations

---

**Blueprint Status:** COMPLETE
**Ready for Factory Floor:** YES
**Target Completion:** 2-2.5 hours
**Validation:** Run full test suite + coverage report
**Task Closure:** After all checklists verified

---

*Test Adaptation Guide Version: 1.0*
*Author: @QA_Lead, Charter & Stone Capital Workshop*
*Sprint: Coverage-1.1.3 Phase 1c (Test Adaptation & Validation)*
*Reviewed By: (Pending operator approval)*
