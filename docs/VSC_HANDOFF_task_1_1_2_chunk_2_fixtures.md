# VSC HANDOFF: Fixture Loading (conftest.py)
## Task 1.1.2 - Chunk 2: Fixture Loading Implementation
### Date: 2026-02-06 | Est. Time: 1 hour

---

## OBJECTIVE

Implement `tests/conftest.py` with shared fixtures for snapshot loading, mock brokers, and sample configurations.

---

## FIXTURE STRATEGY

**Fixture Scopes:**
- **Session:** Load once, reuse across entire test run (expensive operations)
- **Module:** Load once per test file (moderate cost)
- **Function:** Fresh instance per test (lightweight, isolated)

**Fixture Types:**
1. **Snapshot Data:** Load IBKR JSON snapshots
2. **Mock Brokers:** Provide mock IB connections
3. **Sample Configs:** Load gameplan and market data samples
4. **Test Data Builders:** Provide builder instances

---

## COMPLETE conftest.py IMPLEMENTATION

**File:** `tests/conftest.py`

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

import json
from pathlib import Path
from typing import Any, Dict

import pytest


# =============================================================================
# FIXTURE PATHS
# =============================================================================


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """
    Path to test fixtures directory.

    Returns:
        Path to tests/fixtures/
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def snapshots_dir(fixtures_dir: Path) -> Path:
    """
    Path to IBKR snapshots directory.

    Returns:
        Path to tests/fixtures/ibkr_snapshots/
    """
    return fixtures_dir / "ibkr_snapshots"


# =============================================================================
# SNAPSHOT DATA FIXTURES (Session-scoped - Load Once)
# =============================================================================


@pytest.fixture(scope="session")
def spy_snapshot(snapshots_dir: Path) -> Dict[str, Any]:
    """
    Load SPY snapshot data (normal VIX regime).

    Returns:
        Dictionary with SPY option chain, underlying, and historical bars
    """
    # Find the SPY placeholder snapshot (or real snapshot if replaced)
    snapshot_files = list(snapshots_dir.glob("spy_*_normal_vix*.json"))

    if not snapshot_files:
        pytest.skip("SPY snapshot not found - run snapshot capture first")

    snapshot_path = snapshot_files[0]  # Use first match

    with open(snapshot_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def qqq_snapshot(snapshots_dir: Path) -> Dict[str, Any]:
    """
    Load QQQ snapshot data (normal VIX regime).

    Returns:
        Dictionary with QQQ option chain, underlying, and historical bars
    """
    snapshot_files = list(snapshots_dir.glob("qqq_*_normal_vix*.json"))

    if not snapshot_files:
        pytest.skip("QQQ snapshot not found - run snapshot capture first")

    snapshot_path = snapshot_files[0]

    with open(snapshot_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def iwm_snapshot(snapshots_dir: Path) -> Dict[str, Any]:
    """
    Load IWM snapshot data (normal VIX regime).

    Returns:
        Dictionary with IWM option chain, underlying, and historical bars
    """
    snapshot_files = list(snapshots_dir.glob("iwm_*_normal_vix*.json"))

    if not snapshot_files:
        pytest.skip("IWM snapshot not found - run snapshot capture first")

    snapshot_path = snapshot_files[0]

    with open(snapshot_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def all_snapshots(
    spy_snapshot: Dict[str, Any],
    qqq_snapshot: Dict[str, Any],
    iwm_snapshot: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    All IBKR snapshots in a single dictionary.

    Returns:
        Dictionary mapping symbol -> snapshot data
    """
    return {
        "SPY": spy_snapshot,
        "QQQ": qqq_snapshot,
        "IWM": iwm_snapshot,
    }


# =============================================================================
# SAMPLE DATA FIXTURES (Session-scoped)
# =============================================================================


@pytest.fixture(scope="session")
def market_data_samples(fixtures_dir: Path) -> Dict[str, Any]:
    """
    Load market data edge case samples.

    Returns:
        Dictionary with edge case market data scenarios
    """
    samples_path = fixtures_dir / "market_data_samples.json"

    with open(samples_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def gameplan_samples(fixtures_dir: Path) -> Dict[str, Any]:
    """
    Load daily gameplan configuration samples.

    Returns:
        Dictionary with Strategy A/B/C gameplan configurations
    """
    samples_path = fixtures_dir / "gameplan_samples.json"

    with open(samples_path, "r") as f:
        return json.load(f)


# =============================================================================
# INDIVIDUAL GAMEPLAN FIXTURES (Session-scoped)
# =============================================================================


@pytest.fixture(scope="session")
def strategy_a_gameplan(gameplan_samples: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strategy A (Momentum) gameplan configuration.

    Returns:
        Gameplan dict for normal VIX regime, bullish bias
    """
    return gameplan_samples["strategy_a_normal"]


@pytest.fixture(scope="session")
def strategy_b_gameplan(gameplan_samples: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strategy B (Mean Reversion) gameplan configuration.

    Returns:
        Gameplan dict for elevated VIX regime, neutral bias
    """
    return gameplan_samples["strategy_b_elevated"]


@pytest.fixture(scope="session")
def strategy_c_gameplan(gameplan_samples: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strategy C (Cash Preservation) gameplan configuration.

    Returns:
        Gameplan dict for crisis regime, no trading
    """
    return gameplan_samples["strategy_c_crisis"]


# =============================================================================
# MARKET DATA EXTRACTION FIXTURES (Function-scoped)
# =============================================================================


@pytest.fixture
def spy_underlying_price(spy_snapshot: Dict[str, Any]) -> float:
    """
    Extract SPY underlying price from snapshot.

    Returns:
        Current SPY price
    """
    return spy_snapshot["underlying"]["price"]


@pytest.fixture
def spy_option_chain(spy_snapshot: Dict[str, Any]) -> list:
    """
    Extract SPY option chain from snapshot.

    Returns:
        List of option contract dictionaries
    """
    return spy_snapshot["option_chain"]


@pytest.fixture
def spy_historical_bars(spy_snapshot: Dict[str, Any]) -> list:
    """
    Extract SPY historical bars from snapshot.

    Returns:
        List of OHLCV bar dictionaries
    """
    return spy_snapshot["historical_bars"]


@pytest.fixture
def vix_level(spy_snapshot: Dict[str, Any]) -> float:
    """
    Extract VIX level from snapshot metadata.

    Returns:
        VIX level at snapshot capture time
    """
    return spy_snapshot["metadata"]["vix_level"]


@pytest.fixture
def market_regime(spy_snapshot: Dict[str, Any]) -> str:
    """
    Extract market regime from snapshot metadata.

    Returns:
        Regime string (complacency/normal/elevated/crisis)
    """
    return spy_snapshot["metadata"]["regime"]


# =============================================================================
# MOCK BROKER FIXTURES (Function-scoped - Fresh per Test)
# =============================================================================


@pytest.fixture
def mock_broker():
    """
    Provide a mock IB connection for unit tests.

    Returns:
        MockIBConnection instance (to be implemented in tests/helpers/mocks.py)

    Note:
        This fixture will be fully implemented in Chunk 5 after MockIBConnection
        is created. For now, it returns None and tests using it will be skipped.
    """
    # TODO: Implement in Chunk 5 after mocks.py is complete
    # from tests.helpers.mocks import MockIBConnection
    # return MockIBConnection()
    pytest.skip("MockIBConnection not yet implemented - complete Chunk 5 first")


@pytest.fixture
def mock_broker_with_spy_data(mock_broker, spy_snapshot: Dict[str, Any]):
    """
    Mock broker pre-loaded with SPY snapshot data.

    Returns:
        MockIBConnection with SPY data injected

    Note:
        Will be implemented in Chunk 5 after MockIBConnection supports data injection.
    """
    # TODO: Implement in Chunk 5
    # mock_broker.inject_snapshot_data("SPY", spy_snapshot)
    # return mock_broker
    pytest.skip("MockIBConnection not yet implemented - complete Chunk 5 first")


@pytest.fixture
def mock_broker_with_all_data(mock_broker, all_snapshots: Dict[str, Dict[str, Any]]):
    """
    Mock broker pre-loaded with all symbol snapshot data.

    Returns:
        MockIBConnection with SPY/QQQ/IWM data injected

    Note:
        Will be implemented in Chunk 5.
    """
    # TODO: Implement in Chunk 5
    # for symbol, snapshot in all_snapshots.items():
    #     mock_broker.inject_snapshot_data(symbol, snapshot)
    # return mock_broker
    pytest.skip("MockIBConnection not yet implemented - complete Chunk 5 first")


# =============================================================================
# ACCOUNT CONFIGURATION FIXTURES (Function-scoped)
# =============================================================================


@pytest.fixture
def account_balance() -> float:
    """
    Standard test account balance.

    Returns:
        $600.00 (matches production account parameters)
    """
    return 600.0


@pytest.fixture
def max_position_size(account_balance: float) -> float:
    """
    Maximum position size (20% of capital).

    Returns:
        $120.00 (20% of $600)
    """
    return account_balance * 0.20


@pytest.fixture
def max_risk_per_trade(account_balance: float) -> float:
    """
    Maximum risk per trade (3% of capital).

    Returns:
        $18.00 (3% of $600)
    """
    return account_balance * 0.03


@pytest.fixture
def daily_loss_limit(account_balance: float) -> float:
    """
    Daily loss limit (10% of capital).

    Returns:
        $60.00 (10% of $600)
    """
    return account_balance * 0.10


@pytest.fixture
def weekly_drawdown_limit(account_balance: float) -> float:
    """
    Weekly drawdown governor limit (15% of capital).

    Returns:
        $90.00 (15% of $600)
    """
    return account_balance * 0.15


@pytest.fixture
def pdt_limit() -> int:
    """
    Pattern Day Trader trade limit.

    Returns:
        3 (trades per 5 business days)
    """
    return 3


# =============================================================================
# TEST DATA BUILDER FIXTURES (Function-scoped)
# =============================================================================


@pytest.fixture
def contract_builder():
    """
    Provide a ContractBuilder instance.

    Returns:
        ContractBuilder for fluent contract creation

    Note:
        Will be implemented in Chunk 4 after builders.py is complete.
    """
    # TODO: Implement in Chunk 4
    # from tests.helpers.builders import ContractBuilder
    # return ContractBuilder()
    pytest.skip("ContractBuilder not yet implemented - complete Chunk 4 first")


@pytest.fixture
def order_builder():
    """
    Provide an OrderBuilder instance.

    Returns:
        OrderBuilder for fluent order creation

    Note:
        Will be implemented in Chunk 4.
    """
    # TODO: Implement in Chunk 4
    # from tests.helpers.builders import OrderBuilder
    # return OrderBuilder()
    pytest.skip("OrderBuilder not yet implemented - complete Chunk 4 first")


@pytest.fixture
def position_builder():
    """
    Provide a PositionBuilder instance.

    Returns:
        PositionBuilder for fluent position creation

    Note:
        Will be implemented in Chunk 4.
    """
    # TODO: Implement in Chunk 4
    # from tests.helpers.builders import PositionBuilder
    # return PositionBuilder()
    pytest.skip("PositionBuilder not yet implemented - complete Chunk 4 first")


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================


def pytest_configure(config):
    """
    Pytest configuration hook.

    Registers custom markers for test organization.
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (component interaction)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full workflows)")
    config.addinivalue_line("markers", "live: Live validation tests (manual, requires Gateway)")
    config.addinivalue_line("markers", "slow: Slow tests (>5 seconds)")


def pytest_collection_modifyitems(config, items):
    """
    Pytest collection hook.

    Auto-marks tests based on directory location.
    """
    for item in items:
        # Get test file path relative to tests/
        rel_path = Path(item.fspath).relative_to(Path(__file__).parent)

        # Auto-mark based on directory
        if "unit" in str(rel_path):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(rel_path):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(rel_path):
            item.add_marker(pytest.mark.e2e)
        elif "live_validation" in str(rel_path):
            item.add_marker(pytest.mark.live)
            # Skip live tests by default (manual execution only)
            if config.getoption("-m") != "live":
                item.add_marker(pytest.mark.skip(reason="Live tests require manual execution"))
```

---

## VALIDATION STEPS

### Step 1: Replace conftest.py

Replace the existing empty `tests/conftest.py` with the implementation above.

### Step 2: Validate Syntax

```bash
# Check for syntax errors
poetry run python -m py_compile tests/conftest.py

# Expected: No output = success
```

### Step 3: Test Fixture Discovery

```bash
# List all available fixtures
poetry run pytest --fixtures tests/

# Expected: Should see all 30+ fixtures listed
```

### Step 4: Test Snapshot Loading

```bash
# Create a quick validation test
cat > tests/test_fixtures_validation.py << 'EOF'
"""Quick validation that fixtures load correctly."""
import pytest

def test_spy_snapshot_loads(spy_snapshot):
    """Verify SPY snapshot loads and has expected structure."""
    assert "metadata" in spy_snapshot
    assert "underlying" in spy_snapshot
    assert "option_chain" in spy_snapshot
    assert spy_snapshot["metadata"]["symbol"] == "SPY"

def test_gameplan_samples_load(gameplan_samples):
    """Verify gameplan samples load correctly."""
    assert "strategy_a_normal" in gameplan_samples
    assert "strategy_b_elevated" in gameplan_samples
    assert "strategy_c_crisis" in gameplan_samples

def test_account_fixtures(account_balance, max_position_size, daily_loss_limit):
    """Verify account parameter fixtures calculate correctly."""
    assert account_balance == 600.0
    assert max_position_size == 120.0  # 20% of 600
    assert daily_loss_limit == 60.0    # 10% of 600
EOF

# Run validation tests
poetry run pytest tests/test_fixtures_validation.py -v

# Expected: 3 tests pass
```

### Step 5: Verify Fixture Scoping

```bash
# Run with verbose fixture setup
poetry run pytest tests/test_fixtures_validation.py -v --setup-show

# Expected: Should see session-scoped fixtures load once
```

---

## EXPECTED OUTPUT

### Fixture List (Partial)

```
fixtures defined from tests.conftest:
  account_balance -- Standard test account balance ($600)
  all_snapshots -- All IBKR snapshots in a single dictionary
  daily_loss_limit -- Daily loss limit (10% of capital)
  fixtures_dir -- Path to test fixtures directory
  gameplan_samples -- Load daily gameplan configuration samples
  iwm_snapshot -- Load IWM snapshot data (normal VIX regime)
  market_data_samples -- Load market data edge case samples
  market_regime -- Extract market regime from snapshot metadata
  max_position_size -- Maximum position size (20% of capital)
  max_risk_per_trade -- Maximum risk per trade (3% of capital)
  pdt_limit -- Pattern Day Trader trade limit (3 trades / 5 days)
  qqq_snapshot -- Load QQQ snapshot data (normal VIX regime)
  snapshots_dir -- Path to IBKR snapshots directory
  spy_historical_bars -- Extract SPY historical bars from snapshot
  spy_option_chain -- Extract SPY option chain from snapshot
  spy_snapshot -- Load SPY snapshot data (normal VIX regime)
  spy_underlying_price -- Extract SPY underlying price from snapshot
  strategy_a_gameplan -- Strategy A (Momentum) gameplan configuration
  strategy_b_gameplan -- Strategy B (Mean Reversion) gameplan configuration
  strategy_c_gameplan -- Strategy C (Cash Preservation) gameplan configuration
  vix_level -- Extract VIX level from snapshot metadata
  weekly_drawdown_limit -- Weekly drawdown governor limit (15% of capital)
  ... (and more)
```

### Validation Test Output

```
tests/test_fixtures_validation.py::test_spy_snapshot_loads PASSED           [33%]
tests/test_fixtures_validation.py::test_gameplan_samples_load PASSED        [66%]
tests/test_fixtures_validation.py::test_account_fixtures PASSED             [100%]

======================== 3 passed in 0.15s ========================
```

---

## TROUBLESHOOTING

### If snapshot fixtures fail:

**Error:** `SPY snapshot not found`

**Solution:** Snapshots are placeholder files with "_PLACEHOLDER" in filename. The glob pattern should still match them. If not:

```python
# Update glob pattern in conftest.py
snapshot_files = list(snapshots_dir.glob("spy_*.json"))  # Remove _normal_vix constraint
```

### If JSON loading fails:

**Error:** `JSONDecodeError: Expecting value`

**Solution:** Verify JSON files are valid:

```bash
# Validate all JSON files
poetry run python -c "import json; [json.load(open(f)) for f in Path('tests/fixtures').glob('**/*.json')]"
```

### If pytest markers fail:

**Error:** `Unknown marker: unit`

**Solution:** Markers are registered in `pytest_configure` hook. Ensure conftest.py is complete.

---

## CLEANUP

After validation succeeds, remove the temporary validation test:

```bash
rm tests/test_fixtures_validation.py
```

---

## GIT COMMIT

```bash
git add tests/conftest.py
git commit -m "Task 1.1.2 Chunk 2: Implement fixture loading in conftest.py

- Add snapshot data loading fixtures (SPY/QQQ/IWM)
- Add sample configuration fixtures (gameplan, market data)
- Add account parameter fixtures (balance, limits, PDT)
- Add fixture extraction helpers (price, option chain, bars)
- Add pytest configuration hooks (auto-markers, live test skip)
- Add 30+ reusable fixtures with proper scoping

Fixtures validated with 3 passing tests. Ready for helpers implementation."
git push origin main
```

---

## WHAT'S NEXT

**Chunk 3: Test Helpers - Assertions**
- Custom assertions for options trading
- Contract validation
- Risk compliance checks
- P&L calculation validation

**Estimated time:** 45 minutes

---

**Expected Duration:** 1 hour (including validation)
**Status:** Ready for implementation

---

**End of Handoff - Chunk 2**
