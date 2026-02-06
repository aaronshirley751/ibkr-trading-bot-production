# Test Architecture Blueprint
## Charter & Stone Capital Trading Bot - Production Test Suite
### Version: 1.0 | Date: February 6, 2026 | Authors: @Systems_Architect + @QA_Lead

---

## Executive Summary

This document defines the comprehensive test architecture for the Charter & Stone Capital automated options trading system. The architecture supports a **hybrid testing approach** combining deterministic snapshot-based tests (95% of suite) with manual live validation tests (5% of suite) to achieve **88% overall coverage** while maintaining fast, reliable CI/CD pipelines.

**Key Principles:**
1. **Safety First** - 98% coverage on risk management code (highest standard)
2. **Deterministic Testing** - Real IBKR data snapshots enable reproducible tests
3. **Fast Feedback** - Core test suite runs in <60 seconds
4. **Parallel Development** - Independent test modules enable concurrent work
5. **Production Validation** - Manual live validation suite catches API changes

---

## 1. Test Directory Structure

### 1.1 Overview

```
tests/
├── conftest.py                      # Shared fixtures and test configuration
├── __init__.py
│
├── fixtures/                        # Test data and snapshots
│   ├── __init__.py
│   ├── ibkr_snapshots/             # Real IBKR market data (captured during market hours)
│   │   ├── spy_20260206_0930_normal_vix.json
│   │   ├── spy_20260206_1400_elevated_vix.json
│   │   ├── qqq_20260206_0930_normal_vix.json
│   │   ├── iwm_20260206_0930_normal_vix.json
│   │   └── README.md               # Snapshot capture documentation
│   ├── market_data_samples.json    # Synthetic variations for edge cases
│   └── gameplan_samples.json       # Daily gameplan configurations (A/B/C)
│
├── helpers/                         # Test utilities and builders
│   ├── __init__.py
│   ├── assertions.py               # Custom assertions for options trading
│   ├── builders.py                 # Test data builders (contracts, orders, positions)
│   └── mocks.py                    # Mock implementations (Gateway, IB connection)
│
├── unit/                           # Fast, isolated, deterministic unit tests
│   ├── __init__.py
│   ├── test_broker_connection.py
│   ├── test_market_data.py
│   ├── test_strategy_signals.py
│   ├── test_strategy_selection.py
│   ├── test_position_sizing.py
│   ├── test_risk_guards.py
│   ├── test_order_creation.py
│   └── test_order_lifecycle.py
│
├── integration/                    # Component interaction tests
│   ├── __init__.py
│   ├── test_gateway_communication.py
│   ├── test_strategy_execution.py
│   ├── test_circuit_breakers.py
│   └── test_position_tracking.py
│
├── e2e/                            # End-to-end workflow tests
│   ├── __init__.py
│   ├── test_daily_gameplan_ingestion.py
│   ├── test_full_trade_cycle.py
│   └── test_safety_scenarios.py
│
└── live_validation/                # Manual pre-deployment tests (NOT in CI)
    ├── __init__.py
    ├── README.md                   # Manual execution instructions
    ├── test_gateway_connectivity.py
    ├── test_real_market_data.py
    └── test_real_order_submission.py  # Paper trading only
```

### 1.2 Directory Responsibilities

#### **tests/conftest.py**
- Pytest configuration and shared fixtures
- Session-scoped fixtures (expensive setup, reused across tests)
- Module-scoped fixtures (test file level reuse)
- Function-scoped fixtures (fresh state per test)

**Key fixtures:**
```python
@pytest.fixture
def mock_broker():
    """Mock IB connection for unit tests"""

@pytest.fixture
def sample_market_data():
    """Load IBKR snapshot data"""

@pytest.fixture
def sample_daily_gameplan():
    """Load gameplan configuration"""

@pytest.fixture
def mock_gateway():
    """Mock Gateway responses"""
```

#### **tests/fixtures/**
- **ibkr_snapshots/**: Real market data captured from IBKR Gateway
  - Naming convention: `{symbol}_{date}_{time}_{regime}.json`
  - Contains: option chains, historical bars, Greeks, bid/ask spreads
  - Captured during market hours, committed to git
  - Refreshed quarterly or when market structure changes significantly

- **market_data_samples.json**: Synthetic edge case data
  - Missing fields (test graceful degradation)
  - Extreme values (test boundary conditions)
  - Stale timestamps (test data quality checks)

- **gameplan_samples.json**: Daily gameplan configurations
  - Strategy A (normal regime)
  - Strategy B (elevated regime)
  - Strategy C (crisis/default)
  - Catalyst overrides (FOMC, CPI, earnings)

#### **tests/helpers/**
- **assertions.py**: Domain-specific assertions
  - `assert_contract_valid(contract)` - Validates IBKR contract structure
  - `assert_order_parameters_valid(order)` - Validates order construction
  - `assert_within_risk_limits(position, limits)` - Risk compliance
  - `assert_pnl_calculation_correct(position, expected)` - P&L validation

- **builders.py**: Test data construction
  - `ContractBuilder().spy().call().atm().dte(5).build()`
  - `OrderBuilder().buy().limit_price(3.50).build()`
  - `PositionBuilder().open().pnl(150).build()`

- **mocks.py**: Mock implementations
  - `MockIBConnection` - Simulates IB() connection
  - `MockGateway` - Simulates Gateway API responses
  - `MockMarketData` - Provides deterministic market data

#### **tests/unit/**
Unit tests are:
- **Fast** (<1 second per test)
- **Isolated** (no external dependencies)
- **Deterministic** (same input = same output)
- **Focused** (test one function/method)

#### **tests/integration/**
Integration tests are:
- **Component interaction** (2-3 modules working together)
- **Still fast** (<5 seconds per test)
- **Mock external systems** (Gateway, IBKR API)
- **Validate data flow** (contracts → orders → positions)

#### **tests/e2e/**
End-to-end tests are:
- **Complete workflows** (gameplan → signal → order → execution → tracking)
- **Realistic scenarios** (multi-symbol, strategy transitions, safety triggers)
- **Moderate speed** (<30 seconds per test)
- **Use IBKR snapshots** (real market data, mocked execution)

#### **tests/live_validation/**
Live validation tests are:
- **Manual execution only** (not in GitHub Actions CI)
- **Require IBKR Gateway running** (localhost:4002)
- **Require market hours** (for market data tests)
- **Paper trading only** (no live orders)
- **Pre-deployment safety check** (validates API compatibility)

---

## 2. Fixture Strategy

### 2.1 IBKR Snapshot Capture

**Purpose:** Provide real, deterministic market data for all automated tests.

**Capture Process:**
1. Run `scripts/capture_ibkr_snapshot.py` during market hours
2. Script connects to IBKR Gateway (paper trading mode)
3. Script requests data for SPY, QQQ, IWM
4. Script saves responses to `tests/fixtures/ibkr_snapshots/`

**Data Captured Per Symbol:**
- **Option Chain**: 5 strikes centered on ATM (2 OTM, ATM, 2 ITM)
- **Expiries**: 2 DTE, 5 DTE, 7 DTE (weekly options)
- **Greeks**: Delta, Gamma, Theta, Vega, Implied Volatility
- **Market Data**: Last price, bid, ask, bid size, ask size, volume
- **Historical Bars**: 60 bars, 1-minute interval, RTH only
- **Metadata**: Capture timestamp, VIX level, market regime

**Snapshot Scenarios:**
1. **Normal Regime** (VIX 15-18): Standard conditions, tight spreads
2. **Elevated Regime** (VIX 22-25): Increased volatility, wider spreads
3. **High Volatility** (VIX 28-32): Crisis conditions, very wide spreads
4. **Pre-Market** (8:00 AM ET): Limited liquidity, wider spreads
5. **Mid-Day** (12:00 PM ET): Peak liquidity, tightest spreads
6. **Close Approach** (3:45 PM ET): Gamma pinning, unusual flow

**Refresh Cadence:**
- **Quarterly** (or after major market structure changes)
- **After IBKR API updates** (validate compatibility)
- **When adding new symbols** (capture initial data)

**Storage Format:**
```json
{
  "metadata": {
    "symbol": "SPY",
    "capture_timestamp": "2026-02-06T09:30:00-05:00",
    "vix_level": 16.42,
    "regime": "normal",
    "spy_price": 690.45,
    "market_session": "RTH"
  },
  "option_chain": [
    {
      "contract": {
        "symbol": "SPY",
        "expiry": "20260213",
        "strike": 690.0,
        "right": "C",
        "exchange": "SMART"
      },
      "market_data": {
        "last": 3.85,
        "bid": 3.80,
        "ask": 3.90,
        "bid_size": 150,
        "ask_size": 200,
        "volume": 15420,
        "open_interest": 42500
      },
      "greeks": {
        "delta": 0.52,
        "gamma": 0.08,
        "theta": -0.15,
        "vega": 0.12,
        "implied_vol": 0.18
      }
    }
  ],
  "historical_bars": [
    {
      "timestamp": "2026-02-06T09:30:00-05:00",
      "open": 689.50,
      "high": 690.75,
      "low": 689.25,
      "close": 690.45,
      "volume": 1250000,
      "vwap": 690.12
    }
  ]
}
```

### 2.2 Synthetic Test Data

**Purpose:** Test edge cases that are difficult to capture from live market.

**Use Cases:**
- **Missing fields**: Test graceful degradation (e.g., missing Greeks)
- **Stale data**: Test data quality validation (old timestamps)
- **Extreme values**: Test boundary conditions (VIX > 50, spreads > 50%)
- **Error conditions**: Test error handling (invalid contracts, timeouts)

**Generation Strategy:**
- Base on real IBKR snapshot structure
- Modify specific fields for test scenarios
- Store in `market_data_samples.json` with clear labeling

### 2.3 Fixture Reuse Patterns

**Session-scoped** (expensive setup, shared across entire test run):
```python
@pytest.fixture(scope="session")
def all_ibkr_snapshots():
    """Load all IBKR snapshots once, reuse across tests"""
    return load_all_snapshots()
```

**Module-scoped** (shared within one test file):
```python
@pytest.fixture(scope="module")
def spy_normal_regime_data():
    """SPY data in normal VIX regime"""
    return load_snapshot("spy_20260206_0930_normal_vix.json")
```

**Function-scoped** (fresh state per test):
```python
@pytest.fixture
def fresh_mock_broker():
    """New mock broker for each test"""
    broker = MockIBConnection()
    yield broker
    broker.disconnect()  # Cleanup
```

---

## 3. Mocking Strategy

### 3.1 Mock Hierarchy

**Level 1: IB Connection Mock** (Unit Tests)
- Mock the `IB()` class from `ib_insync`
- Provides deterministic responses without Gateway
- Fast (no network I/O), reliable (no external dependencies)

**Level 2: Gateway API Mock** (Integration Tests)
- Mock Gateway HTTP/TCP responses
- Simulates realistic latency (10-50ms)
- Tests timeout handling, retry logic

**Level 3: No Mocks** (Live Validation Tests)
- Real IBKR Gateway connection
- Real API responses (paper trading account)
- Manual execution, not in CI

### 3.2 IB Connection Mock Implementation

**Location:** `tests/helpers/mocks.py`

**Responsibilities:**
- Simulate `connect()`, `disconnect()`, `isConnected()`
- Return snapshot data for `reqMktData()`, `reqHistoricalData()`
- Track `placeOrder()` calls (validate order parameters, no actual submission)
- Provide `positions()`, `portfolio()` state tracking

**Key Methods:**
```python
class MockIBConnection:
    def __init__(self, snapshot_data=None):
        self._connected = False
        self._snapshot_data = snapshot_data or {}
        self._orders = []
        self._positions = []

    def connect(self, host, port, clientId):
        """Simulate connection (always succeeds in mock)"""
        self._connected = True

    def reqMktData(self, contract, snapshot=True):
        """Return snapshot data for contract"""
        symbol = contract.symbol
        return self._snapshot_data.get(symbol, {})

    def placeOrder(self, contract, order):
        """Record order (do not submit)"""
        self._orders.append((contract, order))
```

### 3.3 Gateway Mock Implementation

**Location:** `tests/helpers/mocks.py`

**Responsibilities:**
- Simulate Gateway TCP responses
- Inject delays (test timeout handling)
- Inject errors (test retry logic)
- Track request/response pairs

**Use Cases:**
- Test exponential backoff on connection failures
- Test timeout parameter propagation
- Test buffer overflow prevention (snapshot=True enforcement)

### 3.4 Mocking Boundaries

**What we mock:**
- ✅ IBKR Gateway API (external system)
- ✅ IB connection layer (network I/O)
- ✅ Market data responses (deterministic testing)

**What we do NOT mock:**
- ❌ Strategy logic (core business logic, must test real code)
- ❌ Risk management (safety-critical, must test real code)
- ❌ Order creation logic (must validate actual parameters)
- ❌ P&L calculation (must validate actual arithmetic)

**Principle:** Mock external dependencies, test our code.

---

## 4. Coverage Targets by Module

### 4.1 Overall Target: 88% Weighted Average

**Rationale:**
- Higher than typical small quant funds (70-85%)
- Lower than Tier 1 firms (95%+)
- Aligned with "high-reliability systems" standard
- Accounts for solo developer time constraints
- Emphasizes safety-critical modules (risk: 98%)

### 4.2 Module-Specific Targets

| Module | Target | Industry Standard | Justification |
|--------|--------|-------------------|---------------|
| **Risk Management** | **98%** | 95-100% (Tier 1) | Capital preservation critical. ONE bug = account blown. Includes PDT guards, daily loss limits, weekly drawdown governor. |
| **Broker Integration** | **92%** | 80-90% (High-reliability) | Gateway communication failures = missed exits, stuck positions. Covers connection, market data, contract qualification. |
| **Data Processing** | **88%** | 85-95% (FinTech) | Stale data = bad signals. Data_Ops quarantine logic must be bulletproof. Covers validation, timestamp checks, cross-verification. |
| **Execution Logic** | **90%** | 85-95% (FinTech) | Order creation bugs = wrong strikes, wrong expiry, wrong side. Covers order construction, submission, tracking. |
| **Strategy Selection** | **85%** | 70-85% (Industry standard) | VIX regime bugs = trading in wrong conditions, but position sizing protects. Covers regime detection, strategy selection, catalyst overrides. |
| **Signal Generation** | **80%** | 70-85% (Industry standard) | EMA/RSI bugs = bad entries, but risk limits cap damage. Covers technical indicators, signal logic, confirmation. |
| **Configuration/Utils** | **75%** | 60-70% (Supporting code) | Lower risk - mostly parsing and validation. Covers config loading, JSON parsing, environment variable handling. |

### 4.3 Coverage Measurement

**Tools:**
- `pytest-cov` for coverage reporting
- `coverage.py` for detailed analysis

**Commands:**
```bash
# Run tests with coverage
poetry run pytest --cov=src --cov-report=html --cov-report=term

# Generate detailed HTML report
open htmlcov/index.html

# Check coverage thresholds (fail if below target)
poetry run pytest --cov=src --cov-fail-under=88
```

**CI/CD Integration:**
- GitHub Actions runs coverage on every commit
- Coverage report posted as PR comment
- Failing coverage blocks merge

### 4.4 Coverage Exclusions

**What to exclude from coverage:**
- Debug/logging statements (informational only)
- Type checking branches (handled by Mypy)
- Unreachable defensive code (e.g., `if False` guards)
- Abstract base class methods (implemented in subclasses)

**Exclusion markers:**
```python
# pragma: no cover
def debug_only_function():  # pragma: no cover
    """Only used in debugging, not production"""
    pass
```

---

## 5. Test Data Requirements

### 5.1 IBKR Snapshot Requirements

**Minimum Snapshots Needed:**

| Scenario | Symbol | VIX Regime | Market Session | Priority |
|----------|--------|------------|----------------|----------|
| Normal conditions | SPY | 15-18 | Mid-day (12:00 PM) | P0 (Critical) |
| Normal conditions | QQQ | 15-18 | Mid-day (12:00 PM) | P0 (Critical) |
| Normal conditions | IWM | 15-18 | Mid-day (12:00 PM) | P0 (Critical) |
| Elevated volatility | SPY | 22-25 | Mid-day (12:00 PM) | P0 (Critical) |
| High volatility | SPY | 28-32 | Any | P1 (Important) |
| Pre-market | SPY | Any | 8:00 AM | P2 (Nice-to-have) |
| Close approach | SPY | Any | 3:45 PM | P2 (Nice-to-have) |

**P0 snapshots block test development. P1/P2 can be added iteratively.**

### 5.2 Synthetic Data Requirements

**Edge Cases to Generate:**

1. **Missing Fields**
   - Option contract with missing Greeks (delta=None)
   - Historical bar with missing VWAP
   - Market data with missing bid/ask

2. **Stale Data**
   - Timestamp > 5 minutes old
   - VIX data from previous session
   - Option chain from yesterday

3. **Extreme Values**
   - VIX > 50 (panic conditions)
   - Bid/ask spread > 50% (illiquid contract)
   - Volume = 0 (untradeable)
   - Delta > 1.0 (invalid Greek)

4. **Error Conditions**
   - Invalid contract symbol (INVALID)
   - Expired option contract
   - Non-existent strike
   - Gateway timeout response

### 5.3 Gameplan Configuration Samples

**Required Samples:**

1. **Strategy A (Momentum)** - Normal regime
   ```json
   {
     "strategy": "A",
     "regime": "normal",
     "vix_at_analysis": 16.5,
     "symbols": ["SPY", "QQQ"],
     "position_size_multiplier": 1.0,
     "bias": "bullish"
   }
   ```

2. **Strategy B (Mean Reversion)** - Elevated regime
   ```json
   {
     "strategy": "B",
     "regime": "elevated",
     "vix_at_analysis": 23.5,
     "symbols": ["SPY"],
     "position_size_multiplier": 0.5,
     "bias": "neutral"
   }
   ```

3. **Strategy C (Cash Preservation)** - Crisis/Default
   ```json
   {
     "strategy": "C",
     "regime": "crisis",
     "vix_at_analysis": 31.0,
     "symbols": [],
     "position_size_multiplier": 0.0,
     "bias": "neutral"
   }
   ```

4. **Catalyst Override** - FOMC day
   ```json
   {
     "strategy": "A",
     "regime": "normal",
     "vix_at_analysis": 17.0,
     "symbols": ["SPY"],
     "position_size_multiplier": 0.5,
     "catalysts": ["FOMC decision 2:00 PM ET"],
     "bias": "neutral"
   }
   ```

---

## 6. Test Execution Strategy

### 6.1 Local Development

**Daily Development Cycle:**
```bash
# Run fast unit tests (watch mode)
poetry run pytest tests/unit/ -v

# Run integration tests
poetry run pytest tests/integration/ -v

# Run full suite with coverage
poetry run pytest --cov=src --cov-report=term

# Run specific test file
poetry run pytest tests/unit/test_risk_guards.py -v

# Run tests matching pattern
poetry run pytest -k "test_pdt" -v
```

### 6.2 CI/CD Pipeline

**GitHub Actions Workflow** (`.github/workflows/ci.yml`):
```yaml
- name: Run Test Suite
  run: |
    poetry run pytest tests/unit/ tests/integration/ tests/e2e/ \
      --cov=src \
      --cov-report=term \
      --cov-report=html \
      --cov-fail-under=88 \
      --verbose
```

**What runs in CI:**
- ✅ Unit tests (`tests/unit/`)
- ✅ Integration tests (`tests/integration/`)
- ✅ E2E tests (`tests/e2e/`)
- ❌ Live validation tests (`tests/live_validation/`) - EXCLUDED

**CI Success Criteria:**
- All tests pass
- Coverage ≥88%
- Ruff linting passes
- Black formatting passes
- Mypy type checking passes

### 6.3 Pre-Deployment Validation

**Manual Checklist** (before paper → live transition):
```bash
# 1. Ensure IBKR Gateway running
systemctl status ibkr-gateway

# 2. Run live validation suite
poetry run pytest tests/live_validation/ -v

# 3. Verify paper trading orders appear in TWS
# (Manual verification in IBKR Trader Workstation)

# 4. Check Discord notifications working
# (Manual check of webhook delivery)

# 5. Validate Raspberry Pi deployment
ssh pi@trading-bot
cd ~/ibkr-trading-bot-production
poetry run pytest tests/live_validation/ -v
```

---

## 7. Test Development Workflow

### 7.1 Test-Driven Development (TDD)

**For new features:**
1. **Write test first** (defines expected behavior)
2. **Run test (fails)** (confirms test works)
3. **Write minimal code** (make test pass)
4. **Refactor** (improve code quality)
5. **Repeat** (next test case)

**Example:**
```python
# Step 1: Write test
def test_pdt_compliance_blocks_fourth_trade():
    """PDT rule: cannot exceed 3 day trades in 5 business days"""
    risk_manager = RiskManager(account_value=600)

    # Simulate 3 day trades already executed
    risk_manager.record_trade("2026-02-03")
    risk_manager.record_trade("2026-02-04")
    risk_manager.record_trade("2026-02-05")

    # 4th trade should be blocked
    assert risk_manager.check_pdt_compliance() == False

# Step 2: Run test (fails - RiskManager doesn't exist yet)
# Step 3: Implement RiskManager.check_pdt_compliance()
# Step 4: Test passes
```

### 7.2 Regression Testing

**When to add regression tests:**
- After fixing a bug (prevent reoccurrence)
- After discovering an edge case in production
- After IBKR API changes
- After strategy modifications

**Naming convention:**
```python
def test_regression_issue_42_gateway_buffer_overflow():
    """
    Regression test for Issue #42.

    Bug: reqMktData(snapshot=False) caused buffer overflow.
    Fix: Enforce snapshot=True for all market data requests.
    """
    broker = MockIBConnection()

    # Verify snapshot=True is enforced
    market_data = broker.reqMktData(contract, snapshot=False)
    assert broker.last_request_used_snapshot == True
```

### 7.3 Parallel Test Development

**After Task 1.1.2 completes, these can run in parallel:**

**Developer Session Plan:**
```
Monday:
  AM (2h): Broker tests (1.1.3)
  PM (2h): Strategy tests (1.1.4)

Tuesday:
  AM (2h): Risk tests (1.1.5)
  PM (2h): Execution tests (1.1.6)

Wednesday:
  AM (2h): Continue Broker tests
  PM (2h): Continue Strategy tests

Thursday:
  AM (2h): Continue Risk tests
  PM (2h): Continue Execution tests

Friday:
  AM (2h): QA review cycles
  PM (2h): Fix issues, retest
```

**Git Branch Strategy:**
```bash
# Create feature branches from main
git checkout -b test/broker-layer
git checkout -b test/strategy-layer
git checkout -b test/risk-layer
git checkout -b test/execution-layer

# Work on each independently
# Merge to main when QA approved
```

---

## 8. Quality Gates

### 8.1 Definition of Done (Test Implementation)

For each test module to be considered "complete":

- [ ] **All test files created** (unit, integration as specified)
- [ ] **Coverage target met** (module-specific threshold)
- [ ] **All tests pass** (0 failures, 0 errors)
- [ ] **Code quality passes** (Ruff + Black + Mypy clean)
- [ ] **QA review completed** (@QA_Lead sign-off)
- [ ] **Risk review completed** (@CRO sign-off for risk module only)
- [ ] **Documentation updated** (docstrings, comments, README if applicable)
- [ ] **Edge cases tested** (documented in test names/docstrings)
- [ ] **Regression tests added** (if fixing bugs)

### 8.2 Test Quality Standards

**Good test characteristics:**
- **Descriptive names** - `test_pdt_compliance_blocks_fourth_trade()` not `test_pdt()`
- **Single assertion focus** - One logical concept per test
- **Arrange-Act-Assert pattern** - Clear setup, execution, verification
- **No test interdependence** - Tests run in any order
- **Fast execution** - Unit tests <1s, integration <5s, E2E <30s

**Bad test anti-patterns:**
- ❌ Generic names (`test_strategy()`, `test_risk()`)
- ❌ Multiple unrelated assertions (`assert A and B and C`)
- ❌ Hidden setup (global state, side effects)
- ❌ Flaky tests (random failures, timing-dependent)
- ❌ Slow tests (network I/O in unit tests)

### 8.3 CI/CD Quality Gates

**Pre-merge requirements:**
```yaml
# .github/workflows/ci.yml
jobs:
  quality-checks:
    steps:
      - name: Run Ruff
        run: poetry run ruff check src/ tests/

      - name: Run Black
        run: poetry run black --check src/ tests/

      - name: Run Mypy
        run: poetry run mypy src/

      - name: Run Tests with Coverage
        run: |
          poetry run pytest tests/unit/ tests/integration/ tests/e2e/ \
            --cov=src \
            --cov-fail-under=88 \
            --verbose

      # All must pass for PR merge approval
```

---

## 9. Snapshot Capture Script Specification

### 9.1 Script Location and Purpose

**File:** `scripts/capture_ibkr_snapshot.py`

**Purpose:** Connect to IBKR Gateway during market hours and capture real market data for test fixtures.

**Usage:**
```bash
# Run during market hours (9:30 AM - 4:00 PM ET)
poetry run python scripts/capture_ibkr_snapshot.py \
  --symbols SPY QQQ IWM \
  --output tests/fixtures/ibkr_snapshots/
```

### 9.2 Script Requirements

**Inputs:**
- `--symbols`: List of symbols to capture (SPY, QQQ, IWM)
- `--output`: Output directory for JSON files
- `--strikes`: Number of strikes to capture around ATM (default: 5)
- `--expiries`: DTE values to capture (default: 2, 5, 7)
- `--regime`: Label for VIX regime (optional, auto-detected if not provided)

**Outputs:**
- One JSON file per symbol: `{symbol}_{date}_{time}_{regime}.json`
- Summary log: `capture_log_{date}.txt`

**Error Handling:**
- Validate Gateway connection before capturing
- Retry failed requests (3 attempts with exponential backoff)
- Log errors but continue with remaining symbols
- Validate captured data completeness before saving

**Data Validation:**
- Check all required fields present (bid, ask, Greeks, etc.)
- Verify timestamps are current (<5 minutes old)
- Confirm contract counts match expected (5 strikes × 3 expiries = 15 contracts)
- Flag warnings for missing data (log but don't fail)

### 9.3 Example Output

**File:** `tests/fixtures/ibkr_snapshots/spy_20260206_1200_normal_vix.json`

```json
{
  "metadata": {
    "capture_script_version": "1.0",
    "capture_timestamp": "2026-02-06T12:00:15-05:00",
    "symbol": "SPY",
    "underlying_price": 690.45,
    "vix_level": 16.42,
    "regime": "normal",
    "market_session": "RTH",
    "gateway_version": "10.31",
    "strikes_captured": 5,
    "expiries_captured": 3,
    "contracts_total": 30
  },
  "option_chain": [ /* ... */ ],
  "historical_bars": [ /* ... */ ]
}
```

---

## 10. Appendix: Test Examples

### 10.1 Unit Test Example

```python
# tests/unit/test_risk_guards.py

import pytest
from src.risk.guards import RiskManager

def test_daily_loss_limit_enforcement():
    """
    Daily loss limit of 10% ($60) triggers trading halt.

    Given: Account with $600 starting balance
    When: Daily loss exceeds $60
    Then: check_daily_loss_limit() returns False (trading blocked)
    """
    # Arrange
    risk_manager = RiskManager(
        account_balance=600.0,
        max_daily_loss_pct=0.10
    )

    # Simulate losses
    risk_manager.record_loss(30.0)  # -$30
    risk_manager.record_loss(35.0)  # -$35, total -$65

    # Act
    can_trade = risk_manager.check_daily_loss_limit()

    # Assert
    assert can_trade == False
    assert risk_manager.daily_loss_total == 65.0
    assert risk_manager.daily_loss_pct == 0.108  # 10.8% > 10% limit
```

### 10.2 Integration Test Example

```python
# tests/integration/test_strategy_execution.py

import pytest
from tests.helpers.mocks import MockIBConnection
from tests.helpers.builders import ContractBuilder
from src.strategy.momentum import MomentumStrategy
from src.execution.order_manager import OrderManager

def test_full_signal_to_order_flow(sample_market_data):
    """
    Integration test: Strategy generates signal → Order manager creates order.

    Given: Normal VIX regime, SPY showing bullish EMA crossover
    When: Strategy generates BUY signal
    Then: Order manager creates valid call option order
    """
    # Arrange
    broker = MockIBConnection(snapshot_data=sample_market_data)
    strategy = MomentumStrategy(broker=broker)
    order_manager = OrderManager(broker=broker)

    # Act
    signal = strategy.generate_signal(symbol="SPY")
    order = order_manager.create_order_from_signal(signal)

    # Assert
    assert signal.direction == "BUY"
    assert signal.confidence > 0.7
    assert order.action == "BUY"
    assert order.orderType == "LMT"
    assert order.totalQuantity == 1
    assert order.lmtPrice > 0
```

### 10.3 E2E Test Example

```python
# tests/e2e/test_full_trade_cycle.py

import pytest
from tests.helpers.mocks import MockIBConnection
from src.bot.orchestrator import TradingOrchestrator

def test_complete_trade_cycle_strategy_a(sample_daily_gameplan, sample_market_data):
    """
    E2E test: Complete trade cycle from gameplan to position closure.

    Given: Daily gameplan specifies Strategy A (Momentum)
    When: Bot runs one cycle (signal → entry → monitoring → exit)
    Then: Trade executes according to Strategy A parameters
    """
    # Arrange
    broker = MockIBConnection(snapshot_data=sample_market_data)
    orchestrator = TradingOrchestrator(
        broker=broker,
        gameplan=sample_daily_gameplan["strategy_a"]
    )

    # Act - Simulate one complete trade cycle
    orchestrator.run_cycle()

    # Assert
    trades = orchestrator.get_completed_trades()
    assert len(trades) == 1

    trade = trades[0]
    assert trade.symbol == "SPY"
    assert trade.strategy == "A"
    assert trade.entry_price > 0
    assert trade.exit_price > 0
    assert trade.pnl != 0  # Either profit or loss
    assert abs(trade.pnl) <= 18.0  # Max risk per trade
```

---

## 11. Success Metrics

### 11.1 Test Suite Health Indicators

**Green Flags (Healthy Test Suite):**
- ✅ All tests pass in <60 seconds (fast feedback)
- ✅ Coverage ≥88% (high confidence in code quality)
- ✅ 0 flaky tests (deterministic, reliable)
- ✅ CI passes on every commit (no surprises)
- ✅ Test failures immediately pinpoint root cause (good test names/assertions)

**Red Flags (Unhealthy Test Suite):**
- ❌ Tests take >5 minutes (developers avoid running tests)
- ❌ Random test failures (flaky tests, timing issues)
- ❌ Coverage dropping (code added without tests)
- ❌ CI frequently fails (broken tests checked in)
- ❌ Unclear test failures (generic assertions, poor naming)

### 11.2 Coverage Trending

**Track over time:**
```bash
# Generate coverage badge for README
poetry run pytest --cov=src --cov-report=term | grep TOTAL
# Example output: TOTAL    1234   92   92%

# Historical tracking (commit to git)
echo "$(date),92%" >> docs/coverage_history.csv
```

**Coverage goals:**
- **Phase 1 completion:** 88% overall (current target)
- **Phase 2 (Core Bot):** Maintain 88%+ as new code added
- **Phase 3 (Deployment):** Add live validation tests (no coverage impact)
- **Ongoing:** Quarterly review, adjust targets if needed

---

## 12. Maintenance and Evolution

### 12.1 Test Maintenance

**Quarterly reviews:**
- Refresh IBKR snapshots (capture new market data)
- Update coverage targets if warranted
- Remove obsolete tests (if features deprecated)
- Add regression tests for production bugs

**After IBKR API changes:**
- Run live validation suite first
- Update mocks to match new API behavior
- Refresh snapshots if data structures changed
- Update integration tests if necessary

### 12.2 Test Suite Evolution

**As bot evolves:**
- **New strategies added:** Create new test modules (test_strategy_c.py)
- **New symbols added:** Capture new IBKR snapshots
- **New risk guards added:** Update test_risk_guards.py (maintain 98% coverage)
- **New integrations added:** Add integration tests

**Continuous improvement:**
- Refactor slow tests (identify bottlenecks with `pytest --durations=10`)
- Improve test clarity (better names, better assertions)
- Add property-based tests for complex logic (use Hypothesis library)
- Reduce test duplication (extract common patterns to helpers)

---

## 13. Conclusion

This test architecture provides:
1. **Comprehensive coverage** (88% overall, 98% on risk-critical code)
2. **Fast feedback** (core tests <60s)
3. **Deterministic testing** (IBKR snapshots eliminate flakiness)
4. **Parallel development** (independent modules enable concurrent work)
5. **Production safety** (live validation suite catches API changes)

**Next Steps:**
1. ✅ **Complete Task 1.1.1** (this document approved)
2. ⏭️ **Start Task 1.1.2** (implement test infrastructure)
3. ⏭️ **Capture IBKR snapshots** (run script during market hours today)
4. ⏭️ **Begin parallel test development** (1.1.3-1.1.6)
5. ⏭️ **Complete E2E tests** (1.1.7)
6. ⏭️ **Add live validation** (1.1.8)

**Approval Required:** @CRO must review Section 4.2 (coverage targets) and Section 10.1 (risk test example) before proceeding.

---

*Document Version: 1.0*
*Authors: @Systems_Architect + @QA_Lead*
*Review Status: PENDING APPROVAL*
*Next Review: After Task 1.1.2 completion*
