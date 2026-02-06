# VSC HANDOFF: Test Directory Structure Creation
## Task 1.1.2 - Chunk 1: Directory Structure & Empty Files
### Date: 2026-02-06 | Est. Time: 15 minutes

---

## OBJECTIVE

Create the complete test directory structure with empty Python files and proper docstrings.

---

## DIRECTORY STRUCTURE TO CREATE

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures (create empty for now)
│
├── fixtures/
│   ├── __init__.py
│   ├── ibkr_snapshots/            # Already exists (has placeholder JSONs)
│   ├── market_data_samples.json   # Edge case synthetic data
│   └── gameplan_samples.json      # Daily gameplan configurations
│
├── helpers/
│   ├── __init__.py
│   ├── assertions.py              # Custom assertions
│   ├── builders.py                # Test data builders
│   └── mocks.py                   # Mock implementations
│
├── unit/
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
├── integration/
│   ├── __init__.py
│   ├── test_gateway_communication.py
│   ├── test_strategy_execution.py
│   ├── test_circuit_breakers.py
│   └── test_position_tracking.py
│
├── e2e/
│   ├── __init__.py
│   ├── test_daily_gameplan_ingestion.py
│   ├── test_full_trade_cycle.py
│   └── test_safety_scenarios.py
│
└── live_validation/               # Manual execution only (not in CI)
    ├── __init__.py
    ├── README.md
    ├── test_gateway_connectivity.py
    ├── test_real_market_data.py
    └── test_real_order_submission.py
```

---

## FILE CONTENTS

### tests/__init__.py
```python
"""
Test suite for Charter & Stone Capital Trading Bot.

This package contains comprehensive tests covering:
- Unit tests: Individual component testing
- Integration tests: Component interaction testing
- E2E tests: Full workflow testing
- Live validation tests: Manual pre-deployment checks

Coverage target: 88% overall weighted average
- Risk: 98%
- Broker: 92%
- Data: 88%
- Execution: 90%
- Strategy: 85%
- Utils: 75%
"""
```

---

### tests/conftest.py
```python
"""
Shared pytest fixtures for the test suite.

This module provides reusable fixtures for all test modules:
- Snapshot data loading
- Mock broker connections
- Sample configurations
- Test data builders

Fixtures are scoped appropriately (session/module/function) for optimal performance.
"""

import pytest

# TODO: Implement fixtures in Chunk 2
```

---

### tests/helpers/__init__.py
```python
"""Test helper utilities for options trading tests."""
```

---

### tests/helpers/assertions.py
```python
"""
Custom assertions for options trading test validation.

Provides domain-specific assertions for:
- Contract validation
- Order parameter validation
- Risk limit compliance
- P&L calculation accuracy
- Position state verification
"""

# TODO: Implement assertions in Chunk 3
```

---

### tests/helpers/builders.py
```python
"""
Test data builders for creating complex test objects.

Provides fluent API builders for:
- Option contracts
- Stock contracts
- Orders (market, limit, stop)
- Positions (open, closed)
- Market data (OHLCV, Greeks)

Example:
    contract = ContractBuilder().spy().call().atm().dte(5).build()
    order = OrderBuilder().buy().limit_price(3.50).build()
"""

# TODO: Implement builders in Chunk 4
```

---

### tests/helpers/mocks.py
```python
"""
Mock implementations for external dependencies.

Provides mock classes for:
- IBKR Gateway API (MockGateway)
- IB connection (MockIBConnection)
- Market data providers
- Order execution simulation

These mocks enable fast, deterministic unit and integration testing
without requiring live IBKR Gateway connections.
"""

# TODO: Implement mocks in Chunk 5
```

---

### tests/unit/__init__.py
```python
"""
Unit tests for individual components.

Unit tests are:
- Fast (<1 second per test)
- Isolated (no external dependencies)
- Deterministic (same input = same output)
- Focused (test one function/method)

Target coverage: 85-98% depending on module criticality
"""
```

---

### tests/integration/__init__.py
```python
"""
Integration tests for component interactions.

Integration tests verify:
- Multiple modules working together
- Data flow between components
- API contract compliance
- Error propagation

Still fast (<5 seconds per test), still use mocks for external systems.
"""
```

---

### tests/e2e/__init__.py
```python
"""
End-to-end tests for complete workflows.

E2E tests validate:
- Full trading cycle (signal → order → execution → tracking)
- Daily gameplan ingestion and application
- Multi-symbol scenarios
- Safety mechanism triggers

Use IBKR snapshot data, moderate speed (<30 seconds per test).
"""
```

---

### tests/live_validation/__init__.py
```python
"""
Live validation tests for pre-deployment checks.

WARNING: These tests connect to real IBKR Gateway.
- NOT run in CI/CD (manual execution only)
- Require IBKR Gateway running (localhost:4002)
- Require market hours for market data tests
- Paper trading only (no live orders)

Run before paper → live deployment transitions.
"""
```

---

### tests/live_validation/README.md
```markdown
# Live Validation Test Suite

## Purpose

Pre-deployment validation tests that connect to real IBKR Gateway to verify:
- API connectivity and authentication
- Market data retrieval (real-time during RTH)
- Order submission (paper trading only)
- Contract qualification
- Position tracking

## Usage

**Prerequisites:**
- IBKR Gateway running (localhost:4002)
- Paper trading mode
- Market hours: 9:30 AM - 4:00 PM ET (for market data tests)

**Run Tests:**
```bash
# All live validation tests
poetry run pytest tests/live_validation/ -v

# Specific test file
poetry run pytest tests/live_validation/test_gateway_connectivity.py -v
```

## Important Notes

- **NOT run in CI/CD** - These tests are excluded from automated pipelines
- **Manual execution only** - Run before deployments
- **Paper trading only** - Never submit live orders
- **Market hours required** - Some tests need RTH for market data

## Test Files

- `test_gateway_connectivity.py` - Basic connection and authentication
- `test_real_market_data.py` - Real-time market data retrieval
- `test_real_order_submission.py` - Paper trading order submission

## Troubleshooting

**If tests fail:**
1. Verify Gateway running: `netstat -an | findstr "4002"` (Windows) or `ss -tln | grep 4002` (Linux)
2. Check paper trading mode in TWS
3. Verify market hours (9:30-4:00 PM ET) for data tests
4. Check IBKR Gateway logs for errors

## Deployment Checklist

Before paper → live transition:
- [ ] All live validation tests pass
- [ ] Paper trading orders execute correctly
- [ ] Position tracking accurate
- [ ] Discord notifications working
- [ ] Raspberry Pi deployment validated
```

---

### tests/unit/test_broker_connection.py
```python
"""
Unit tests for IBKR broker connection management.

Tests cover:
- Connection establishment
- Connection timeout handling
- ClientId rotation
- Retry logic with exponential backoff
- Connection cleanup
"""

import pytest

# TODO: Implement tests in Task 1.1.3
```

---

### tests/unit/test_market_data.py
```python
"""
Unit tests for market data retrieval and validation.

Tests cover:
- Snapshot mode market data requests
- Historical data requests (1-hour RTH)
- Contract qualification
- Buffer overflow prevention (snapshot=True validation)
- Timeout parameter propagation
- Stale/missing data handling
"""

import pytest

# TODO: Implement tests in Task 1.1.3
```

---

### tests/unit/test_strategy_signals.py
```python
"""
Unit tests for strategy signal generation.

Tests cover:
- EMA crossover signal generation (Strategy A)
- RSI extreme detection (Strategy B)
- VWAP confirmation logic
- Signal generation with missing/stale data
- Signal confidence calculation
"""

import pytest

# TODO: Implement tests in Task 1.1.4
```

---

### tests/unit/test_strategy_selection.py
```python
"""
Unit tests for VIX-based strategy selection.

Tests cover:
- VIX regime detection (complacency/normal/elevated/crisis)
- Strategy selection logic for each regime
- Catalyst-based strategy overrides (FOMC, CPI, earnings)
- Position size multiplier adjustments
"""

import pytest

# TODO: Implement tests in Task 1.1.4
```

---

### tests/unit/test_position_sizing.py
```python
"""
Unit tests for position sizing and affordability checks.

Tests cover:
- Max position size enforcement (20% of capital)
- Affordability checks (IWM contract pricing)
- PDT compliance validation (3 trades / 5 business days)
- Contract quantity calculation
"""

import pytest

# TODO: Implement tests in Task 1.1.5
```

---

### tests/unit/test_risk_guards.py
```python
"""
Unit tests for risk management guards and circuit breakers.

Tests cover:
- Daily loss limit enforcement (10% / $60)
- Weekly drawdown governor (15% triggers Strategy C)
- Stop-loss calculation (25% for A, 15% for B)
- Force-close logic at 3 DTE
- Gap-down scenario handling

CRITICAL: This module requires @CRO sign-off before deployment.
Coverage target: 98% (highest standard)
"""

import pytest

# TODO: Implement tests in Task 1.1.5
```

---

### tests/unit/test_order_creation.py
```python
"""
Unit tests for order parameter construction.

Tests cover:
- Order parameter construction (strike, expiry, moneyness)
- Order validation before submission
- Dry-run mode (no orders submitted)
- Order parameter validation
"""

import pytest

# TODO: Implement tests in Task 1.1.6
```

---

### tests/unit/test_order_lifecycle.py
```python
"""
Unit tests for order lifecycle management.

Tests cover:
- Order submission flow
- Order status tracking (submitted → filled → closed)
- Partial fill handling
- Order cancellation flow
"""

import pytest

# TODO: Implement tests in Task 1.1.6
```

---

### tests/integration/test_gateway_communication.py
```python
"""
Integration tests for IBKR Gateway communication.

Tests cover:
- Full request/response cycle with mock Gateway
- Timeout parameter propagation through request chain
- Error handling for stale/missing data
- Buffer management (snapshot mode validation)
"""

import pytest

# TODO: Implement tests in Task 1.1.3
```

---

### tests/integration/test_strategy_execution.py
```python
"""
Integration tests for strategy signal execution flow.

Tests cover:
- Full signal → order flow integration
- Position sizing calculations
- Stop-loss and take-profit level setting
- Multi-step workflow validation
"""

import pytest

# TODO: Implement tests in Task 1.1.4
```

---

### tests/integration/test_circuit_breakers.py
```python
"""
Integration tests for safety circuit breakers.

Tests cover:
- Strategy C auto-deployment on safety violations
- All position closure on daily loss limit
- No new entries after PDT limit reached
- Multiple safety mechanisms coordinating
"""

import pytest

# TODO: Implement tests in Task 1.1.5
```

---

### tests/integration/test_position_tracking.py
```python
"""
Integration tests for position tracking and P&L calculation.

Tests cover:
- Open position tracking (multiple concurrent positions)
- P&L calculation (realized + unrealized)
- Position closure flow (take-profit, stop-loss, time-stop)
"""

import pytest

# TODO: Implement tests in Task 1.1.6
```

---

### tests/e2e/test_daily_gameplan_ingestion.py
```python
"""
E2E tests for daily gameplan loading and application.

Tests cover:
- Loading daily_gameplan.json
- Applying parameters to runtime config
- Strategy C default on missing gameplan
- Invalid gameplan error handling
"""

import pytest

# TODO: Implement tests in Task 1.1.7
```

---

### tests/e2e/test_full_trade_cycle.py
```python
"""
E2E tests for complete trading cycle.

Tests cover:
- Full workflow: signal → order → execution → tracking → closure
- Multiple symbols (SPY, QQQ, IWM) in single session
- Strategy transitions (A → B → C based on regime changes)
"""

import pytest

# TODO: Implement tests in Task 1.1.7
```

---

### tests/e2e/test_safety_scenarios.py
```python
"""
E2E tests for safety mechanisms in realistic scenarios.

Tests cover:
- Gap-down scenario with stop-loss execution
- PDT violation prevention (3rd trade blocks 4th)
- Weekly drawdown governor activation
- Multi-day scenario testing
"""

import pytest

# TODO: Implement tests in Task 1.1.7
```

---

### tests/live_validation/test_gateway_connectivity.py
```python
"""
Live validation: IBKR Gateway connectivity.

Tests basic connection, authentication, and API availability.
"""

import pytest

# TODO: Implement in Task 1.1.8
```

---

### tests/live_validation/test_real_market_data.py
```python
"""
Live validation: Real market data retrieval.

Tests real-time market data requests during RTH.
Requires market hours: 9:30 AM - 4:00 PM ET.
"""

import pytest

# TODO: Implement in Task 1.1.8
```

---

### tests/live_validation/test_real_order_submission.py
```python
"""
Live validation: Paper trading order submission.

Tests order submission to IBKR paper trading account.
WARNING: Paper trading only - never submit live orders.
"""

import pytest

# TODO: Implement in Task 1.1.8
```

---

## EXECUTION STEPS

### Step 1: Create Directory Structure

```bash
# From repository root
mkdir -p tests/helpers
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/e2e
mkdir -p tests/live_validation
```

### Step 2: Create Empty Python Files

**Copy each file content from above and save to the corresponding path.**

You can use VSCode Copilot with this prompt:

```
Create all test directory files with the docstrings provided in the handoff document.
Use the file paths and contents exactly as specified.
```

### Step 3: Create JSON Fixture Templates

**tests/fixtures/market_data_samples.json:**
```json
{
  "edge_cases": {
    "missing_greeks": {
      "note": "Option contract with missing Greeks (test graceful degradation)",
      "contract": {
        "symbol": "SPY",
        "expiry": "20260213",
        "strike": 690.0,
        "right": "C"
      },
      "market_data": {
        "last": 3.85,
        "bid": 3.80,
        "ask": 3.90
      },
      "greeks": null
    },
    "stale_timestamp": {
      "note": "Market data with old timestamp (test data quality validation)",
      "timestamp": "2026-02-05T09:30:00-05:00",
      "symbol": "SPY",
      "price": 689.45
    },
    "extreme_vix": {
      "note": "VIX > 50 panic conditions",
      "vix_level": 52.3,
      "regime": "crisis"
    }
  }
}
```

**tests/fixtures/gameplan_samples.json:**
```json
{
  "strategy_a_normal": {
    "strategy": "A",
    "regime": "normal",
    "vix_at_analysis": 16.5,
    "symbols": ["SPY", "QQQ"],
    "position_size_multiplier": 1.0,
    "bias": "bullish"
  },
  "strategy_b_elevated": {
    "strategy": "B",
    "regime": "elevated",
    "vix_at_analysis": 23.5,
    "symbols": ["SPY"],
    "position_size_multiplier": 0.5,
    "bias": "neutral"
  },
  "strategy_c_crisis": {
    "strategy": "C",
    "regime": "crisis",
    "vix_at_analysis": 31.0,
    "symbols": [],
    "position_size_multiplier": 0.0,
    "bias": "neutral"
  }
}
```

### Step 4: Validate Structure

```bash
# Check all directories created
ls -la tests/

# Check all Python files created
find tests/ -name "*.py" | wc -l
# Expected: 29 files

# Check all JSON files created
find tests/ -name "*.json" | wc -l
# Expected: 5 files (3 placeholders + 2 fixtures)
```

### Step 5: Run Pytest Discovery

```bash
# Verify pytest can discover test structure
poetry run pytest --collect-only tests/

# Expected output: Collection successful (0 tests found is OK - not written yet)
```

---

## VALIDATION CHECKLIST

- [ ] All directories created under `tests/`
- [ ] All `__init__.py` files created with docstrings
- [ ] All test file stubs created with docstrings
- [ ] `market_data_samples.json` created
- [ ] `gameplan_samples.json` created
- [ ] Pytest collection runs without errors
- [ ] No syntax errors in any Python files

---

## GIT COMMIT

```bash
git add tests/
git commit -m "Task 1.1.2 Chunk 1: Create test directory structure and empty test files

- Add test directory structure (unit/integration/e2e/live_validation)
- Add test file stubs with docstrings (29 Python files)
- Add fixture templates (market_data_samples.json, gameplan_samples.json)
- Add live_validation README with usage instructions

Test infrastructure foundation ready for fixture and helper implementation."
git push origin main
```

---

**Expected Duration:** 15 minutes
**Next Chunk:** Chunk 2 - Fixture Loading (`conftest.py` implementation)

---

**End of Handoff - Chunk 1**
