# VSC HANDOFF: Coverage-1.1.3 Phase 1b — Broker Layer Implementation

**Date:** 2026-02-06
**Requested By:** Option 1 Remediation (Two-Phase Task Structure)
**Target Completion:** 2026-02-18 (Week 1 Extended Milestone)
**Coverage Target:** ≥92% when combined with Phase 1a test suite
**Priority:** Urgent (Blocks all subsequent Coverage-1.1.x tasks)

---

## 1. OBJECTIVE

Implement production broker layer code (`src/broker/`) that satisfies the 35 tests written in Phase 1a. The test suite **defines the specification** — this is Test-Driven Development (TDD) in action. All tests must pass, all alpha learnings must be enforced in production code, and coverage must reach ≥92%.

**Critical Success Criteria:**
1. All 35 tests pass (currently 9 passing, 26 pending)
2. Zero test modifications allowed (tests are the contract)
3. Alpha learnings enforced in production code (not just tests)
4. ≥92% coverage of `src/broker/` module achieved
5. Quality gates pass (ruff, black, mypy)

---

## 2. FILE STRUCTURE

Create three new production modules in `src/broker/`:

```
src/broker/
├── __init__.py                    # NEW — Package exports
├── connection.py                  # NEW — IBKRConnection class (200-250 lines est.)
├── market_data.py                 # NEW — MarketDataProvider class (150-200 lines est.)
├── contracts.py                   # NEW — ContractManager utilities (100-150 lines est.)
└── exceptions.py                  # NEW — Custom broker exceptions (50-75 lines est.)
```

**Total Estimated:** 500-675 lines of production code

**Existing Test Suite (Phase 1a):**
- `tests/unit/test_broker_connection.py` — 8 tests, 241 lines
- `tests/unit/test_broker_market_data.py` — 17 tests, 484 lines
- `tests/integration/test_gateway_communication.py` — 10 tests, 549 lines

---

## 3. IMPLEMENTATION SPECIFICATIONS

### File 1: `src/broker/connection.py`

**Purpose:** Connection lifecycle management with retry logic and ClientId generation.

**Class:** `IBKRConnection`

**Required Methods (derived from test expectations):**

```python
class IBKRConnection:
    """Manages IBKR Gateway connection with retry logic and health monitoring."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4002,
        client_id: Optional[int] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay_base: float = 2.0  # Exponential backoff base
    ):
        """
        Initialize connection parameters.

        Args:
            host: Gateway host (default localhost)
            port: Gateway port (default 4002 for paper trading)
            client_id: Unique client ID (auto-generated if None)
            timeout: Connection timeout in seconds
            max_retries: Maximum retry attempts on failure
            retry_delay_base: Base delay for exponential backoff (2^n * base)
        """
        pass

    def connect(self) -> bool:
        """
        Establish connection to IBKR Gateway with retry logic.

        Returns:
            True if connected successfully, False otherwise

        Raises:
            ConnectionTimeoutError: If connection times out
            MaxRetriesExceededError: If max retries reached

        Implementation Notes:
            - Generate unique ClientId if not provided (timestamp-based)
            - Implement exponential backoff: delay = retry_delay_base ** attempt
            - Track connection attempts for monitoring
            - Validate Gateway version compatibility
        """
        pass

    def disconnect(self) -> None:
        """
        Cleanly disconnect from Gateway.

        Implementation Notes:
            - Cancel all active subscriptions
            - Flush pending callbacks
            - Close socket connection
            - Release resources (threads, event loops)
            - Log disconnection with timestamp
        """
        pass

    def is_connected(self) -> bool:
        """
        Check if connection is active and healthy.

        Returns:
            True if connected and responsive, False otherwise

        Implementation Notes:
            - Don't just check socket state
            - Validate Gateway is responding (heartbeat check)
            - Return False if connection is stale
        """
        pass

    def reconnect(self) -> bool:
        """
        Attempt to reconnect after disconnection.

        Returns:
            True if reconnected successfully, False otherwise

        Implementation Notes:
            - Preserve original ClientId
            - Reset retry counter
            - Re-establish subscriptions if any were active
        """
        pass

    @staticmethod
    def generate_client_id() -> int:
        """
        Generate unique timestamp-based ClientId.

        Returns:
            Integer ClientId derived from Unix timestamp

        Implementation Notes:
            - Use current Unix timestamp (seconds since epoch)
            - Convert to integer
            - Ensure uniqueness across rapid successive calls
            - Must match test expectations in test_client_id_uniqueness()
        """
        pass

    @property
    def connection_metrics(self) -> dict:
        """
        Return connection health metrics for monitoring.

        Returns:
            Dictionary with:
                - connected: bool
                - uptime_seconds: float
                - reconnect_count: int
                - last_heartbeat: datetime
        """
        pass
```

**Critical Alpha Learning Enforcement:**
- ClientId generation MUST be timestamp-based (test: `test_client_id_uniqueness`)
- Exponential backoff MUST be implemented correctly (test: `test_connection_retry_on_failure`)
- Timeout MUST be respected (test: `test_connection_timeout_handling`)

---

### File 2: `src/broker/market_data.py`

**Purpose:** Market data retrieval with snapshot enforcement and timeout propagation.

**Class:** `MarketDataProvider`

**Required Methods (derived from test expectations):**

```python
class MarketDataProvider:
    """
    Manages market data requests with snapshot mode enforcement.

    CRITICAL: All market data requests MUST use snapshot=True to prevent
    buffer overflow (alpha learning from 2024-01-15 incident).
    """

    def __init__(
        self,
        connection: IBKRConnection,
        snapshot_mode: bool = True,  # MUST default to True
        stale_threshold_seconds: int = 300  # 5 minutes
    ):
        """
        Initialize market data provider.

        Args:
            connection: Active IBKRConnection instance
            snapshot_mode: Enforce snapshot-only requests (MUST be True)
            stale_threshold_seconds: Threshold for stale data detection

        Raises:
            ValueError: If snapshot_mode is False (forbidden by alpha learnings)
        """
        if not snapshot_mode:
            raise ValueError(
                "snapshot_mode=False is FORBIDDEN. This caused buffer overflow "
                "in production (2024-01-15). See alpha_learnings.md."
            )
        pass

    def request_market_data(
        self,
        contract: Contract,
        timeout: int = 30
    ) -> dict:
        """
        Request real-time market data for a contract.

        Args:
            contract: Qualified IB contract
            timeout: Request timeout in seconds

        Returns:
            Dictionary with:
                - symbol: str
                - bid: float
                - ask: float
                - last: float
                - volume: int
                - timestamp: datetime (UTC)
                - snapshot: bool (MUST be True)

        Raises:
            ContractNotQualifiedError: If contract not qualified
            TimeoutError: If request times out
            StaleDataError: If timestamp > stale_threshold

        Implementation Notes:
            - CRITICAL: Call reqMktData with snapshot=True
            - Validate contract is qualified BEFORE request
            - Propagate timeout through entire call stack
            - Validate all required fields present
            - Check timestamp freshness
        """
        pass

    def request_historical_data(
        self,
        contract: Contract,
        duration: str = "3600 S",  # 1 hour (alpha learning)
        bar_size: str = "1 min",
        use_rth: bool = True,  # MUST be True (alpha learning)
        timeout: int = 30
    ) -> List[dict]:
        """
        Request historical bars for a contract.

        Args:
            contract: Qualified IB contract
            duration: Duration string (default 1 hour per alpha learnings)
            bar_size: Bar size (1 min, 5 mins, etc.)
            use_rth: Use regular trading hours only (MUST be True)
            timeout: Request timeout in seconds

        Returns:
            List of bar dictionaries with OHLCV data:
                - timestamp: datetime
                - open: float
                - high: float
                - low: float
                - close: float
                - volume: int

        Raises:
            ContractNotQualifiedError: If contract not qualified
            TimeoutError: If request times out
            ValueError: If use_rth is False (forbidden by alpha learnings)

        Implementation Notes:
            - CRITICAL: Enforce 1-hour RTH-only windows (alpha learning)
            - Timeout MUST propagate through callback chain
            - Validate OHLCV data integrity (O ≤ H, L ≤ C, etc.)
            - Handle empty results gracefully
        """
        if not use_rth:
            raise ValueError(
                "use_rth=False is FORBIDDEN. Historical data MUST use "
                "RTH-only to avoid timeout issues. See alpha_learnings.md."
            )
        pass

    def validate_market_data(self, data: dict) -> bool:
        """
        Validate market data structure and freshness.

        Args:
            data: Market data dictionary from request_market_data

        Returns:
            True if valid, False otherwise

        Validation Rules:
            - All required fields present (bid, ask, last, volume, timestamp)
            - Prices are positive floats
            - Timestamp within stale threshold
            - Bid ≤ Ask (no crossed market)
            - Volume ≥ 0
        """
        pass

    def is_data_stale(self, timestamp: datetime) -> bool:
        """
        Check if data timestamp exceeds staleness threshold.

        Args:
            timestamp: Data timestamp (UTC)

        Returns:
            True if stale (>5 minutes old), False otherwise
        """
        pass
```

**Critical Alpha Learning Enforcement:**
- `snapshot=True` MUST be enforced at runtime (test: `test_snapshot_mode_enforcement`)
- Contract qualification MUST precede data requests (test: `test_contract_qualification_before_data_request`)
- Timeout MUST propagate through callback chain (test: `test_historical_data_timeout_propagation`)
- Historical data MUST use RTH-only (test: `test_historical_data_rth_only`)

---

### File 3: `src/broker/contracts.py`

**Purpose:** Contract management and qualification utilities.

**Class:** `ContractManager`

**Required Methods:**

```python
class ContractManager:
    """Manages IB contract qualification and validation."""

    def __init__(self, connection: IBKRConnection):
        """
        Initialize contract manager.

        Args:
            connection: Active IBKRConnection instance
        """
        pass

    def qualify_contract(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        timeout: int = 10
    ) -> Contract:
        """
        Qualify a contract with IBKR.

        Args:
            symbol: Ticker symbol (e.g., "SPY")
            sec_type: Security type (STK, OPT, FUT, etc.)
            exchange: Exchange (SMART for auto-routing)
            currency: Currency code
            timeout: Qualification timeout

        Returns:
            Qualified IB Contract object

        Raises:
            ContractQualificationError: If qualification fails
            TimeoutError: If qualification times out

        Implementation Notes:
            - Use IB's qualifyContracts() method
            - Cache qualified contracts (avoid redundant lookups)
            - Mark contract as qualified (add flag)
            - Validate contract details returned
        """
        pass

    def is_qualified(self, contract: Contract) -> bool:
        """
        Check if contract is qualified.

        Args:
            contract: IB Contract object

        Returns:
            True if qualified, False otherwise

        Implementation Notes:
            - Check for conId presence (set by qualification)
            - Validate contract details are complete
        """
        pass

    def get_contract_details(self, contract: Contract) -> dict:
        """
        Get detailed contract information.

        Args:
            contract: Qualified IB Contract

        Returns:
            Dictionary with contract metadata
        """
        pass
```

---

### File 4: `src/broker/exceptions.py`

**Purpose:** Custom exception classes for broker layer.

```python
class BrokerError(Exception):
    """Base exception for broker layer errors."""
    pass

class ConnectionError(BrokerError):
    """Connection-related errors."""
    pass

class ConnectionTimeoutError(ConnectionError):
    """Connection attempt timed out."""
    pass

class MaxRetriesExceededError(ConnectionError):
    """Maximum retry attempts exceeded."""
    pass

class MarketDataError(BrokerError):
    """Market data request errors."""
    pass

class ContractNotQualifiedError(MarketDataError):
    """Contract must be qualified before data request."""
    pass

class StaleDataError(MarketDataError):
    """Market data timestamp exceeds staleness threshold."""
    pass

class SnapshotModeViolationError(MarketDataError):
    """CRITICAL: Attempt to use non-snapshot mode (forbidden)."""
    pass

class ContractQualificationError(BrokerError):
    """Contract qualification failed."""
    pass
```

---

### File 5: `src/broker/__init__.py`

**Purpose:** Package-level exports.

```python
"""
Broker integration layer for IBKR Gateway.

This module provides production-ready interfaces for:
- Connection management with retry logic
- Market data retrieval with snapshot enforcement
- Contract qualification and management

CRITICAL ALPHA LEARNINGS ENFORCED:
1. snapshot=True REQUIRED on all market data requests (buffer overflow fix)
2. Contract qualification REQUIRED before data requests
3. Timeout propagation enforced through entire call stack
4. Historical data: 1-hour RTH-only windows mandatory
5. ClientId: Timestamp-based for uniqueness
"""

from .connection import IBKRConnection
from .market_data import MarketDataProvider
from .contracts import ContractManager
from .exceptions import (
    BrokerError,
    ConnectionError,
    ConnectionTimeoutError,
    MaxRetriesExceededError,
    MarketDataError,
    ContractNotQualifiedError,
    StaleDataError,
    SnapshotModeViolationError,
    ContractQualificationError
)

__all__ = [
    "IBKRConnection",
    "MarketDataProvider",
    "ContractManager",
    "BrokerError",
    "ConnectionError",
    "ConnectionTimeoutError",
    "MaxRetriesExceededError",
    "MarketDataError",
    "ContractNotQualifiedError",
    "StaleDataError",
    "SnapshotModeViolationError",
    "ContractQualificationError",
]
```

---

## 4. DEPENDENCIES

### External Libraries (Already in pyproject.toml)
```python
from ib_insync import IB, Contract, Stock
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import time
import logging
```

### Internal Modules
```python
# None yet — broker layer is foundational
# Future: Will be imported by strategy, risk, execution layers
```

---

## 5. INPUT/OUTPUT CONTRACTS

### IBKRConnection

**Input (Constructor):**
```python
connection = IBKRConnection(
    host="localhost",
    port=4002,
    client_id=None,  # Auto-generated if None
    timeout=30,
    max_retries=3,
    retry_delay_base=2.0
)
```

**Output (connect):**
```python
success: bool = connection.connect()
# Returns True if connected, False if failed after retries
```

**Output (generate_client_id):**
```python
client_id: int = IBKRConnection.generate_client_id()
# Example: 1738800000 (Unix timestamp as integer)
```

---

### MarketDataProvider

**Input (request_market_data):**
```python
contract = Stock('SPY', 'SMART', 'USD')
data: dict = provider.request_market_data(contract, timeout=30)
```

**Output (request_market_data):**
```python
{
    'symbol': 'SPY',
    'bid': 685.50,
    'ask': 685.52,
    'last': 685.51,
    'volume': 1250000,
    'timestamp': datetime(2026, 2, 6, 14, 30, 0, tzinfo=timezone.utc),
    'snapshot': True  # ALWAYS True
}
```

**Input (request_historical_data):**
```python
bars: List[dict] = provider.request_historical_data(
    contract=contract,
    duration="3600 S",  # 1 hour
    bar_size="1 min",
    use_rth=True,  # MUST be True
    timeout=30
)
```

**Output (request_historical_data):**
```python
[
    {
        'timestamp': datetime(2026, 2, 6, 13, 30, 0, tzinfo=timezone.utc),
        'open': 685.00,
        'high': 685.50,
        'low': 684.80,
        'close': 685.20,
        'volume': 50000
    },
    # ... more bars
]
```

---

### ContractManager

**Input (qualify_contract):**
```python
contract: Contract = manager.qualify_contract(
    symbol="SPY",
    sec_type="STK",
    exchange="SMART",
    currency="USD",
    timeout=10
)
```

**Output (qualify_contract):**
```python
# Returns ib_insync.Contract with:
# - conId set (unique contract identifier)
# - All details populated
# - Marked as qualified
```

---

## 6. INTEGRATION POINTS

### With Test Suite (Phase 1a)

**The test suite IS the specification.** Implementation must satisfy all test assertions:

**Connection Tests (test_broker_connection.py):**
- `test_connection_establishment_success()` → `IBKRConnection.connect()` returns True
- `test_client_id_uniqueness()` → `generate_client_id()` returns unique timestamps
- `test_connection_retry_on_failure()` → Exponential backoff implemented
- `test_connection_timeout_handling()` → Timeout respected, TimeoutError raised

**Market Data Tests (test_broker_market_data.py):**
- `test_snapshot_mode_enforcement()` → `snapshot=True` enforced at runtime
- `test_contract_qualification_before_data_request()` → ContractNotQualifiedError raised
- `test_historical_data_timeout_propagation()` → Timeout threads through call stack
- `test_market_data_validation()` → All OHLCV fields validated
- `test_stale_data_detection()` → Timestamps >5min flagged as stale

**Integration Tests (test_gateway_communication.py):**
- `test_full_workflow_mock_gateway()` → Complete workflow passes
- `test_gateway_disconnection_recovery()` → Reconnect logic works
- `test_concurrent_requests_handling()` → No cross-contamination

### With Future Layers

**Strategy Layer (Coverage-1.1.4):**
```python
# Strategy layer will consume broker data:
from src.broker import MarketDataProvider, ContractManager

provider = MarketDataProvider(connection)
data = provider.request_market_data(contract)
# Strategy analyzes data for signals
```

**Risk Layer (Coverage-1.1.5):**
```python
# Risk layer validates data freshness:
from src.broker import MarketDataProvider

if provider.is_data_stale(data['timestamp']):
    # Activate Strategy C
```

---

## 7. DEFINITION OF DONE

### Phase 1b Completion Criteria

**Code Implementation:**
- [ ] `src/broker/__init__.py` created with exports
- [ ] `src/broker/connection.py` implemented (200-250 lines)
- [ ] `src/broker/market_data.py` implemented (150-200 lines)
- [ ] `src/broker/contracts.py` implemented (100-150 lines)
- [ ] `src/broker/exceptions.py` implemented (50-75 lines)

**Test Suite Validation:**
- [ ] All 35 tests passing (0 pending, 0 skipped)
- [ ] `test_snapshot_mode_enforcement` ✅ PASS
- [ ] `test_contract_qualification_before_data_request` ✅ PASS
- [ ] `test_historical_data_timeout_propagation` ✅ PASS
- [ ] `test_client_id_uniqueness` ✅ PASS (already passing, must stay passing)
- [ ] No test modifications made (tests are the contract)

**Coverage Validation (Phase 1c):**
- [ ] ≥92% coverage of `src/broker/` module
- [ ] Coverage report generated: `pytest --cov=src/broker --cov-report=html`
- [ ] Critical paths covered: retry logic, timeout handling, snapshot enforcement

**Quality Gates:**
- [ ] `ruff check src/broker/` — zero errors
- [ ] `black --check src/broker/` — formatting compliant
- [ ] `mypy src/broker/` — type checking passes (strict mode)
- [ ] No new warnings introduced

**Alpha Learning Enforcement (Non-Negotiable):**
- [ ] ✅ `snapshot=True` enforced at runtime in `MarketDataProvider.__init__`
- [ ] ✅ Contract qualification validated before data requests
- [ ] ✅ Timeout parameter propagates through entire call stack
- [ ] ✅ Historical data uses 1-hour RTH-only windows (enforced)
- [ ] ✅ ClientId generation is timestamp-based

**Documentation:**
- [ ] Docstrings on all public methods
- [ ] Alpha learnings referenced in code comments
- [ ] Critical safety checks have inline explanations

---

## 8. EDGE CASES TO HANDLE

### Connection Edge Cases
- Gateway not running → Retry with exponential backoff, log each attempt
- Gateway disconnects mid-session → Detect via heartbeat, auto-reconnect
- ClientId collision (unlikely) → Timestamp should be unique, but log if collision detected

### Market Data Edge Cases
- Empty response from Gateway → Raise MarketDataError with context
- Missing fields (e.g., no volume) → Validation catches, raises MarketDataError
- Timestamp >5 minutes old → Flag as stale, raise StaleDataError
- Bid > Ask (crossed market) → Validation catches, log warning, accept data (may be valid in fast markets)

### Historical Data Edge Cases
- No bars returned (illiquid symbol) → Return empty list, log info message
- Timeout during callback → TimeoutError must propagate up
- Request for extended hours (use_rth=False) → ValueError raised immediately

### Contract Qualification Edge Cases
- Symbol not found → ContractQualificationError with symbol in message
- Multiple matches (ambiguous contract) → Use first match, log warning
- Qualification times out → TimeoutError raised

---

## 9. ROLLBACK PLAN

If Phase 1b implementation breaks existing tests or introduces regressions:

### Immediate Rollback
1. **Identify failing test(s):**
   ```bash
   pytest tests/unit/test_broker*.py tests/integration/test_gateway*.py -v
   ```
2. **Check if regression is in production code or test:**
   - If production code: Revert commit, review implementation
   - If test code: DO NOT MODIFY TESTS — they are the contract
3. **Use git bisect if needed:**
   ```bash
   git bisect start
   git bisect bad HEAD
   git bisect good [last-known-good-commit]
   ```

### Disable Feature Without Breaking
- Cannot disable broker layer — it's foundational
- If specific method fails: Comment out implementation, raise NotImplementedError temporarily
- Mark related tests as `@pytest.skip` with reason until fixed

### Escalation Path
- If tests fail: Notify @QA_Lead, debug with test output
- If coverage <92%: Identify uncovered paths, add implementation
- If alpha learning violated: CRITICAL — notify @CRO, fix immediately

---

## 10. IMPLEMENTATION GUIDANCE

### Recommended VSCode Copilot Workflow

**Step 1: Create module structure**
```bash
# In VSCode terminal:
mkdir -p src/broker
touch src/broker/__init__.py
touch src/broker/connection.py
touch src/broker/market_data.py
touch src/broker/contracts.py
touch src/broker/exceptions.py
```

**Step 2: Implement exceptions.py first**
- Start with exception classes (simplest, no dependencies)
- Copilot prompt: "Implement custom exception classes per blueprint specifications"

**Step 3: Implement connection.py**
- Focus on `generate_client_id()` first (already has passing test)
- Then `connect()` with retry logic
- Then `disconnect()` and `is_connected()`
- Copilot prompt: "Implement IBKRConnection.connect() with exponential backoff retry logic per blueprint"
- Run tests after each method:
  ```bash
  pytest tests/unit/test_broker_connection.py::TestBrokerConnection::test_client_id_uniqueness -v
  ```

**Step 4: Implement contracts.py**
- Implement `qualify_contract()` to unblock market data tests
- Contract qualification is a prerequisite for data requests

**Step 5: Implement market_data.py**
- **CRITICAL:** Enforce `snapshot=True` in `__init__` (ValueError if False)
- Implement `request_market_data()` with contract qualification check
- Implement `request_historical_data()` with RTH enforcement
- Implement validation methods
- Run critical tests:
  ```bash
  pytest tests/unit/test_broker_market_data.py::TestMarketDataRetrieval::test_snapshot_mode_enforcement -v
  pytest tests/unit/test_broker_market_data.py::TestMarketDataRetrieval::test_contract_qualification_before_data_request -v
  ```

**Step 6: Integration validation**
- Run full test suite:
  ```bash
  pytest tests/unit/test_broker*.py tests/integration/test_gateway*.py -v
  ```
- Check for pending tests:
  ```bash
  pytest tests/unit/test_broker*.py tests/integration/test_gateway*.py --collect-only | grep "PENDING"
  ```
- All should show as passing (not pending, not skipped)

**Step 7: Coverage validation (Phase 1c)**
```bash
# Generate coverage report:
pytest tests/unit/test_broker*.py tests/integration/test_gateway*.py \
    --cov=src/broker --cov-report=term-missing --cov-report=html

# Open HTML report:
open htmlcov/index.html  # macOS

# Target: ≥92% coverage
# If below target: Identify uncovered lines, add implementation
```

**Step 8: Quality gates**
```bash
# Run all quality checks:
ruff check src/broker/
black --check src/broker/
mypy src/broker/ --strict

# Fix any issues before proceeding to QA review
```

---

## 11. ACCEPTANCE CRITERIA CHECKLIST

Before submitting for Phase 1c validation and QA review:

### Implementation Criteria
- [ ] All 5 files created in `src/broker/`
- [ ] All classes and methods from blueprint implemented
- [ ] No placeholder `pass` statements in production code
- [ ] Alpha learnings enforced with runtime checks (ValueError, etc.)

### Test Criteria
- [ ] All 35 tests passing (9 that were passing + 26 that were pending)
- [ ] Zero pending tests (`@pytest.mark.skip` removed)
- [ ] Zero skipped tests
- [ ] Test execution time <60 seconds total
- [ ] No flaky tests (run 3 times, all passes each time)

### Coverage Criteria
- [ ] ≥92% coverage of `src/broker/` module
- [ ] All critical paths covered (retry, timeout, snapshot enforcement)
- [ ] HTML coverage report generated and reviewed

### Quality Criteria
- [ ] Ruff: Zero errors, zero warnings
- [ ] Black: Formatting compliant
- [ ] Mypy: Type checking passes (strict mode)
- [ ] No new linting issues introduced

### Documentation Criteria
- [ ] Docstrings on all public methods
- [ ] Alpha learnings referenced in code comments where relevant
- [ ] Complex logic has inline explanations

### Alpha Learning Criteria (Mandatory)
- [ ] ✅ `snapshot=True` enforced with ValueError if violated
- [ ] ✅ Contract qualification enforced with ContractNotQualifiedError
- [ ] ✅ Timeout propagates through call stack (validated by tests)
- [ ] ✅ Historical data uses RTH-only (ValueError if use_rth=False)
- [ ] ✅ ClientId is timestamp-based (test already validates)

---

## 12. NOTES FOR FACTORY FLOOR

### Time Estimate
- **exceptions.py:** 30 minutes
- **connection.py:** 3-4 hours (retry logic, ClientId, timeout handling)
- **contracts.py:** 2-3 hours (qualification, caching)
- **market_data.py:** 4-5 hours (snapshot enforcement, validation, timeout propagation)
- **__init__.py:** 15 minutes
- **Integration testing:** 2-3 hours (run tests, fix failures, validate coverage)
- **Quality gates + documentation:** 1-2 hours
- **Total:** 13-18 hours over 2-3 days

### Common Pitfalls to Avoid
1. **Modifying tests to make them pass** — Tests are the contract, do not change them
2. **Not enforcing alpha learnings at runtime** — Add `raise ValueError` for violations
3. **Forgetting timeout propagation** — Thread timeout through all async calls
4. **Using live Gateway** — Tests use mocks, implementation should too during dev
5. **Incomplete error handling** — Every exception path must be covered

### When to Ask for Help
- If tests still fail after implementation → Consult @QA_Lead for debugging
- If coverage <92% after full implementation → Identify gaps with @Systems_Architect
- If alpha learning enforcement unclear → Consult @CRO for clarification
- If time estimate exceeds 18 hours → Escalate to @PM for timeline adjustment

### Success Indicators
- Run `pytest tests/unit/test_broker*.py tests/integration/test_gateway*.py -v`
- Output shows: `35 passed` (no pending, no skipped, no failed)
- Run `pytest --cov=src/broker --cov-report=term`
- Output shows: `TOTAL ... 92%` or higher

---

**Blueprint Status:** COMPLETE
**Ready for Factory Floor:** YES
**Target Completion:** Feb 17-18 (2-3 days implementation)
**Validation Trigger:** When all 35 tests pass and coverage ≥92%
**QA Review:** After Phase 1c validation complete

---

*Blueprint Version: 1.0*
*Author: @Systems_Architect, Charter & Stone Capital Workshop*
*Sprint: Phase 1.1 Test Build-Out, Phase 1b (Implementation)*
*Reviewed By: (Pending operator approval)*
