# VSC HANDOFF: Task 1.1.6 — Execution Layer Test Suite

**Date**: 2025-02-07
**Requested By**: Phase 1 Sprint (Task 1.1.6)
**Model Recommendation**: Sonnet
**Context Budget**: Light (focused test implementation, dependencies already validated)

---

## 1. OBJECTIVE

Implement comprehensive test suite for the execution layer (`src/execution/`) with ≥90% code coverage. Validate order lifecycle management, position tracking, P&L calculation, confidence gating, error handling, and fail-safe behavior. Ensure seamless integration with broker, strategy, and risk layers already validated in Tasks 1.1.3–1.1.5.

---

## 2. FILE STRUCTURE

**Create**:
- `tests/execution/__init__.py` (empty marker file)
- `tests/execution/conftest.py` (execution-specific fixtures)
- `tests/execution/test_execution_unit.py` (order lifecycle, position tracking, P&L)
- `tests/execution/test_execution_integration.py` (multi-component orchestration)
- `tests/execution/test_execution_edge_cases.py` (error handling, fail-safe validation)

**Modify**:
- None (execution layer tests are additive)

---

## 3. LOGIC FLOW (PSEUDO-CODE)

### 3.1 Unit Tests (`test_execution_unit.py`)

```python
# Order Lifecycle Tests
def test_order_creation_from_signal():
    # Given: Strategy signal with confidence > 0.5
    # When: ExecutionEngine.process_signal(signal)
    # Then: Order object created with correct parameters (symbol, side, quantity, type)

def test_order_submission_to_broker():
    # Given: Valid order created from signal
    # When: ExecutionEngine.submit_order(order)
    # Then: Broker.submit_order called with correct contract/order params

def test_order_fill_confirmation():
    # Given: Submitted order
    # When: Broker returns fill confirmation
    # Then: Position tracking updated, P&L basis established

def test_order_rejection_handling():
    # Given: Submitted order
    # When: Broker rejects (insufficient funds, invalid contract, etc.)
    # Then: Order marked REJECTED, no position created, error logged

# Position Tracking Tests
def test_position_creation_on_fill():
    # Given: Order filled
    # Then: Position object created (symbol, quantity, cost_basis, entry_time)

def test_position_pnl_calculation_unrealized():
    # Given: Open position
    # When: Market price changes
    # Then: Unrealized P&L = (current_price - cost_basis) * quantity

def test_position_pnl_calculation_realized():
    # Given: Position closed via exit signal
    # Then: Realized P&L = (exit_price - entry_price) * quantity

def test_position_partial_fill_tracking():
    # Given: Order partially filled (e.g., 5 of 10 contracts)
    # Then: Position reflects partial quantity, remaining order status tracked

# Confidence Gating Tests
def test_confidence_gate_enforcement():
    # Given: Signal with confidence < 0.5
    # When: ExecutionEngine.process_signal(signal)
    # Then: NO order created, log "Signal below confidence threshold"

def test_confidence_gate_boundary():
    # Given: Signal with confidence = 0.5 (exact boundary)
    # Then: Order IS created (>= threshold)

def test_confidence_gate_high_confidence():
    # Given: Signal with confidence = 0.95
    # Then: Order created, no size adjustment based on confidence
```

### 3.2 Integration Tests (`test_execution_integration.py`)

```python
# Full Workflow Tests
def test_full_entry_workflow():
    # Given: Strategy generates BUY signal (confidence 0.85)
    # When: ExecutionEngine orchestrates: risk check → broker submission → fill → position tracking
    # Then: All components called in correct sequence, position opened

def test_full_exit_workflow():
    # Given: Open position + Strategy generates SELL signal
    # When: ExecutionEngine orchestrates: position lookup → broker submission → fill → P&L calculation
    # Then: Position closed, realized P&L recorded

def test_multi_position_management():
    # Given: Two open positions (SPY, QQQ)
    # When: Strategy signals exit for SPY only
    # Then: SPY position closed, QQQ remains open, P&L calculated for SPY only

def test_risk_gate_blocks_execution():
    # Given: Strategy signal (confidence 0.9) + Risk manager rejects (position size exceeds limit)
    # When: ExecutionEngine.process_signal(signal)
    # Then: Risk check fails → NO order submitted → log "Risk check failed"

def test_broker_disconnect_during_submission():
    # Given: Valid order ready for submission
    # When: Broker raises ConnectionError during submit_order
    # Then: ExecutionEngine catches exception → order marked FAILED → no position created

def test_concurrent_signal_processing():
    # Given: Two signals arrive simultaneously (SPY BUY, QQQ SELL)
    # When: ExecutionEngine processes both
    # Then: No race condition, both orders processed independently, correct positions tracked
```

### 3.3 Edge Case Tests (`test_execution_edge_cases.py`)

```python
# Error Handling Tests
def test_invalid_signal_structure():
    # Given: Signal missing required fields (e.g., no 'symbol')
    # When: ExecutionEngine.process_signal(signal)
    # Then: ValidationError raised, NO order created, error logged

def test_broker_timeout_during_fill_check():
    # Given: Order submitted, waiting for fill confirmation
    # When: Broker timeout during status check
    # Then: Order marked PENDING_TIMEOUT, retry logic triggered

def test_position_tracking_data_corruption():
    # Given: Open position
    # When: Position data becomes invalid (e.g., negative quantity)
    # Then: ExecutionEngine detects corruption → position quarantined → alert raised

def test_pnl_calculation_with_missing_market_data():
    # Given: Open position
    # When: Market data unavailable (broker returns None)
    # Then: Unrealized P&L = last known value, log "Stale market data"

# Fail-Safe Behavior Tests
def test_fail_safe_on_strategy_failure():
    # Given: Strategy.generate_signal() raises exception
    # When: ExecutionEngine attempts signal generation
    # Then: Exception caught → NO order created → Strategy C (cash preservation) implied

def test_fail_safe_on_risk_manager_failure():
    # Given: Risk manager unavailable (returns None)
    # When: ExecutionEngine checks risk
    # Then: Assume risk check FAILS → no order submitted → log "Risk manager unavailable"

def test_fail_safe_on_broker_unavailable():
    # Given: Broker connection lost
    # When: ExecutionEngine attempts order submission
    # Then: No orders submitted → existing positions monitored only → log "Broker offline"

def test_default_to_no_action():
    # Given: Any component in orchestration fails
    # When: ExecutionEngine evaluates next action
    # Then: Default behavior = NO new orders, existing positions managed conservatively
```

---

## 4. DEPENDENCIES

**Python Libraries**:
- `pytest` (test framework)
- `pytest-mock` (mocking/patching)
- `pytest-cov` (coverage reporting)
- `hypothesis` (property-based testing for P&L calculations)

**Internal Modules** (all validated in prior tasks):
- `src.broker` (Task 1.1.3 — 99% coverage)
- `src.strategy` (Task 1.1.4 — 99% coverage)
- `src.risk` (Task 1.1.5 — 97% coverage)
- `src.execution` (under test — implementation pending Phase 2)

**Test Utilities**:
- `tests.broker.conftest` (broker mocks)
- `tests.strategy.conftest` (strategy fixtures)
- `tests.risk.conftest` (risk manager fixtures)

---

## 5. INPUT/OUTPUT CONTRACT

### Input (Test Fixtures):

**`mock_broker`** (from `tests/broker/conftest.py`):
```python
{
    'submit_order': Mock(return_value={'orderId': 12345, 'status': 'Submitted'}),
    'get_order_status': Mock(return_value={'status': 'Filled', 'filled': 10}),
    'get_contract': Mock(return_value=Contract(...)),
    'get_market_data': Mock(return_value={'last': 695.50})
}
```

**`mock_strategy`** (new fixture in `tests/execution/conftest.py`):
```python
{
    'generate_signal': Mock(return_value={'action': 'BUY', 'symbol': 'SPY', 'confidence': 0.85}),
    'calculate_confidence': Mock(return_value=0.75)
}
```

**`mock_risk`** (from `tests/risk/conftest.py`):
```python
{
    'check_position_size': Mock(return_value=True),
    'calculate_position_size': Mock(return_value=10),
    'check_daily_loss_limit': Mock(return_value=True)
}
```

**`sample_signals`** (new fixture):
```python
[
    {'action': 'BUY', 'symbol': 'SPY', 'confidence': 0.85, 'timestamp': '2026-02-07T09:30:00'},
    {'action': 'SELL', 'symbol': 'SPY', 'confidence': 0.45, 'timestamp': '2026-02-07T10:15:00'},  # Below threshold
    {'action': 'BUY', 'symbol': 'QQQ', 'confidence': 0.95, 'timestamp': '2026-02-07T11:00:00'}
]
```

**`sample_positions`** (new fixture):
```python
[
    {'symbol': 'SPY', 'quantity': 10, 'cost_basis': 695.00, 'entry_time': '2026-02-07T09:35:00', 'status': 'OPEN'},
    {'symbol': 'QQQ', 'quantity': 5, 'cost_basis': 622.00, 'entry_time': '2026-02-07T10:00:00', 'status': 'OPEN'}
]
```

### Output (Test Assertions):

**Order Lifecycle**:
- Order object created with correct parameters
- Broker API called with expected contract/order details
- Position tracking updated on fill confirmation
- Error handling logs for rejected orders

**Position Tracking**:
- Position created with accurate cost basis
- P&L calculations match expected values (unrealized/realized)
- Partial fill quantities tracked correctly

**Confidence Gating**:
- Signals below 0.5 threshold blocked
- Signals at/above threshold processed
- Logs confirm gating decisions

**Integration**:
- Full entry/exit workflows complete without errors
- Multi-position management maintains state integrity
- Risk gate blocks execution when appropriate

**Fail-Safe**:
- Component failures do not create orders
- Default behavior = no action when in doubt
- Logs confirm fail-safe activation

---

## 6. INTEGRATION POINTS

**Execution Engine** (implementation in Phase 2):
```python
class ExecutionEngine:
    def __init__(self, broker, strategy, risk_manager):
        self.broker = broker
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.positions = {}  # Track open positions

    def process_signal(self, signal):
        # Validate signal
        # Check confidence gate (>= 0.5)
        # Check risk manager approval
        # Submit order to broker
        # Track position on fill
        pass

    def calculate_pnl(self, position):
        # Fetch current market price
        # Calculate unrealized P&L
        pass

    def close_position(self, symbol):
        # Generate exit order
        # Submit to broker
        # Calculate realized P&L
        pass
```

**Test Integration**:
- Tests import mocked components from `tests/broker/conftest`, `tests/risk/conftest`
- Tests create `ExecutionEngine` instances with mocked dependencies
- Tests validate orchestration logic without touching real IBKR Gateway

---

## 7. DEFINITION OF DONE

### Must Pass:
- [ ] All existing tests pass (currently 204/322)
- [ ] `tests/execution/` added to pytest discovery
- [ ] Execution layer unit tests pass (order lifecycle, position tracking, P&L, confidence gating)
- [ ] Execution layer integration tests pass (full workflows, risk gate integration)
- [ ] Execution layer edge case tests pass (error handling, fail-safe behavior)
- [ ] Coverage report shows ≥90% for `src/execution/` module
- [ ] `ruff` + `black` pass with zero warnings
- [ ] `mypy` type checking passes
- [ ] No new test failures introduced in other layers

### Quality Gates:
- [ ] Fixtures properly isolated (no cross-test state leakage)
- [ ] Error handling validates both exception catching AND logging
- [ ] P&L calculations validated with property-based tests (Hypothesis)
- [ ] Integration tests cover all component interaction paths
- [ ] Fail-safe behavior explicitly tested (not just inferred)

---

## 8. EDGE CASES TO TEST

### Data Validation:
- **Signal missing required fields** → ValidationError raised, no order created
- **Signal with invalid confidence** (e.g., confidence = 1.5) → ValueError raised
- **Position data corruption** → Quarantine position, raise alert

### Broker Interactions:
- **Broker timeout during submission** → Retry logic triggered, order marked PENDING
- **Broker rejection** (insufficient funds, invalid contract) → Order marked REJECTED, logged
- **Broker disconnect during fill check** → Order status unknown, safe assumption = NOT filled

### Risk Manager Interactions:
- **Risk manager returns None** (unavailable) → Assume risk check FAILS, no order submitted
- **Risk manager approves but broker rejects** → Order attempt logged, no position created
- **Risk manager sizing exceeds broker affordability** → Order downsized or blocked

### Confidence Gating:
- **Confidence = 0.49** → Blocked (below threshold)
- **Confidence = 0.50** → Allowed (at threshold)
- **Confidence = None** → ValidationError raised

### Position Tracking:
- **Partial fill** (5 of 10 contracts) → Position reflects 5 contracts, remaining 5 tracked separately
- **Fill confirmation delayed** → Position not created until confirmation received
- **Duplicate fill notification** → Idempotent handling, no double-counting

### P&L Calculation:
- **Market data unavailable** → Use last known price, log staleness
- **Market data returns NaN/None** → P&L calculation deferred, log error
- **Negative quantity** (data corruption) → Quarantine position, raise alert

### Orchestration:
- **Strategy generates signal → Risk rejects → Broker never called** → Correct sequence validated
- **Concurrent signals** (SPY BUY + QQQ SELL) → No race condition, both processed independently
- **Signal arrives while broker offline** → Signal queued or discarded (depending on implementation)

---

## 9. ROLLBACK PLAN

**If tests fail to reach 90% coverage**:
1. Identify uncovered code paths via `pytest --cov-report=html`
2. Add targeted tests for specific branches/conditions
3. Do NOT lower coverage target — execution layer is orchestration-critical

**If integration tests reveal design flaws**:
1. Document findings in `docs/phase1_findings.md`
2. Create Phase 2 remediation tasks on IBKR board (bucket: Phase 2 Implementation)
3. Tests remain pending with `@pytest.mark.skip(reason="Phase 2 implementation required")`

**If fail-safe behavior tests fail**:
1. This is a CRITICAL finding — execution layer MUST default to safety
2. Escalate to @CRO for risk assessment
3. Consider Red Team review if fail-safe gaps are systemic

---

## 10. CONTEXT & NOTES

### Why 90% Coverage?
- Execution layer is the orchestrator — any uncovered paths represent unvalidated orchestration logic
- Matches coverage targets for broker (99%), strategy (99%), risk (97%) layers
- Orchestration logic has high branch complexity → coverage target ensures all paths tested

### Why Separate Unit/Integration/Edge Case Files?
- **Unit tests** → Fast, isolated, validate individual components (order creation, P&L calculation)
- **Integration tests** → Validate multi-component workflows (entry/exit, risk gating)
- **Edge case tests** → Validate error handling and fail-safe behavior explicitly

### Fixture Reuse Strategy:
- Broker, strategy, and risk fixtures already exist from prior tasks → import and reuse
- Execution-specific fixtures (`sample_signals`, `sample_positions`) defined in `tests/execution/conftest.py`
- No duplication — fixtures are shared across test files via `conftest.py` hierarchy

### Property-Based Testing:
- P&L calculations should be validated with Hypothesis for edge cases (extreme prices, large quantities, fractional shares)
- Example: `@given(st.floats(min_value=0.01, max_value=10000.0))` for price ranges

---

**END OF BLUEPRINT**
