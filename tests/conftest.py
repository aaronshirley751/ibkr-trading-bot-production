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
from typing import Any, Dict, List, NoReturn

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
        data: Dict[str, Any] = json.load(f)
        return data


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
        data: Dict[str, Any] = json.load(f)
        return data


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
        data: Dict[str, Any] = json.load(f)
        return data


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
# SCENARIO-BASED SNAPSHOT FIXTURES (Session-scoped)
# =============================================================================


@pytest.fixture(scope="session")
def snapshot_normal_market(snapshots_dir: Path) -> Dict[str, Any]:
    """
    Load normal market conditions snapshot.

    Scenario: Normal VIX (~16), uptrend, moderate volume
    Use for: Strategy A (Momentum) validation

    Returns:
        Full snapshot with SPY, QQQ, IWM data (60 bars, 10 options each)
    """
    snapshot_path = snapshots_dir / "snapshot_normal_market.json"
    with open(snapshot_path) as f:
        data: Dict[str, Any] = json.load(f)
        return data


@pytest.fixture(scope="session")
def snapshot_high_volatility(snapshots_dir: Path) -> Dict[str, Any]:
    """
    Load high volatility market snapshot.

    Scenario: High VIX (~28), choppy/mean-reverting, high volume
    Use for: Strategy B (Mean Reversion) validation

    Returns:
        Full snapshot with SPY, QQQ, IWM data (60 bars, 10 options each)
    """
    snapshot_path = snapshots_dir / "snapshot_high_volatility.json"
    with open(snapshot_path) as f:
        data: Dict[str, Any] = json.load(f)
        return data


@pytest.fixture(scope="session")
def snapshot_low_volatility(snapshots_dir: Path) -> Dict[str, Any]:
    """
    Load low volatility market snapshot.

    Scenario: Low VIX (~12), range-bound/grinding, low volume
    Use for: Edge case testing (neither strategy should trigger)

    Returns:
        Full snapshot with SPY, QQQ, IWM data (60 bars, 10 options each)
    """
    snapshot_path = snapshots_dir / "snapshot_low_volatility.json"
    with open(snapshot_path) as f:
        data: Dict[str, Any] = json.load(f)
        return data


@pytest.fixture(scope="session")
def snapshot_market_open(snapshots_dir: Path) -> Dict[str, Any]:
    """
    Load market open snapshot.

    Scenario: Opening volatility spike, high volume, first 30 minutes
    Use for: Execution testing during high-volume periods

    Returns:
        Full snapshot with SPY, QQQ, IWM data (30 bars, 10 options each)
    """
    snapshot_path = snapshots_dir / "snapshot_market_open.json"
    with open(snapshot_path) as f:
        data: Dict[str, Any] = json.load(f)
        return data


@pytest.fixture(scope="session")
def snapshot_end_of_day(snapshots_dir: Path) -> Dict[str, Any]:
    """
    Load end of day snapshot.

    Scenario: Closing activity, diminishing volume, time-based exit testing
    Use for: Position closing logic (0 DTE options)

    Returns:
        Full snapshot with SPY, QQQ, IWM data (15 bars, 10 options each)
    """
    snapshot_path = snapshots_dir / "snapshot_end_of_day.json"
    with open(snapshot_path) as f:
        data: Dict[str, Any] = json.load(f)
        return data


@pytest.fixture(scope="session")
def all_scenario_snapshots(
    snapshot_normal_market: Dict[str, Any],
    snapshot_high_volatility: Dict[str, Any],
    snapshot_low_volatility: Dict[str, Any],
    snapshot_market_open: Dict[str, Any],
    snapshot_end_of_day: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    All scenario snapshots in a single dictionary.

    Returns:
        Dictionary mapping scenario name -> snapshot data
    """
    return {
        "normal_market": snapshot_normal_market,
        "high_volatility": snapshot_high_volatility,
        "low_volatility": snapshot_low_volatility,
        "market_open": snapshot_market_open,
        "end_of_day": snapshot_end_of_day,
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
        data: Dict[str, Any] = json.load(f)
        return data


@pytest.fixture(scope="session")
def gameplan_samples(fixtures_dir: Path) -> Dict[str, Any]:
    """
    Load daily gameplan configuration samples.

    Returns:
        Dictionary with Strategy A/B/C gameplan configurations
    """
    samples_path = fixtures_dir / "gameplan_samples.json"

    with open(samples_path, "r") as f:
        data: Dict[str, Any] = json.load(f)
        return data


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
    result: Dict[str, Any] = gameplan_samples["strategy_a_normal"]
    return result


@pytest.fixture(scope="session")
def strategy_b_gameplan(gameplan_samples: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strategy B (Mean Reversion) gameplan configuration.

    Returns:
        Gameplan dict for elevated VIX regime, neutral bias
    """
    result: Dict[str, Any] = gameplan_samples["strategy_b_elevated"]
    return result


@pytest.fixture(scope="session")
def strategy_c_gameplan(gameplan_samples: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strategy C (Cash Preservation) gameplan configuration.

    Returns:
        Gameplan dict for crisis regime, no trading
    """
    result: Dict[str, Any] = gameplan_samples["strategy_c_crisis"]
    return result


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
    price: float = spy_snapshot["underlying"]["price"]
    return price


@pytest.fixture
def spy_option_chain(spy_snapshot: Dict[str, Any]) -> List[Any]:
    """
    Extract SPY option chain from snapshot.

    Returns:
        List of option contract dictionaries
    """
    chain: List[Any] = spy_snapshot["option_chain"]
    return chain


@pytest.fixture
def spy_historical_bars(spy_snapshot: Dict[str, Any]) -> List[Any]:
    """
    Extract SPY historical bars from snapshot.

    Returns:
        List of OHLCV bar dictionaries
    """
    bars: List[Any] = spy_snapshot["historical_bars"]
    return bars


@pytest.fixture
def vix_level(spy_snapshot: Dict[str, Any]) -> float:
    """
    Extract VIX level from snapshot metadata.

    Returns:
        VIX level at snapshot capture time
    """
    vix: float = spy_snapshot["metadata"]["vix_level"]
    return vix


@pytest.fixture
def market_regime(spy_snapshot: Dict[str, Any]) -> str:
    """
    Extract market regime from snapshot metadata.

    Returns:
        Regime string (complacency/normal/elevated/crisis)
    """
    regime: str = spy_snapshot["metadata"]["regime"]
    return regime


# =============================================================================
# MOCK BROKER FIXTURES (Function-scoped - Fresh per Test)
# =============================================================================


@pytest.fixture
def mock_broker() -> NoReturn:
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
def mock_broker_with_spy_data(mock_broker: Any, spy_snapshot: Dict[str, Any]) -> NoReturn:
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
def mock_broker_with_all_data(
    mock_broker: Any, all_snapshots: Dict[str, Dict[str, Any]]
) -> NoReturn:
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
def contract_builder() -> NoReturn:
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
def order_builder() -> NoReturn:
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
def position_builder() -> NoReturn:
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


def pytest_configure(config: Any) -> None:
    """
    Pytest configuration hook.

    Registers custom markers for test organization.
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (component interaction)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full workflows)")
    config.addinivalue_line("markers", "live: Live validation tests (manual, requires Gateway)")
    config.addinivalue_line("markers", "slow: Slow tests (>5 seconds)")


def pytest_collection_modifyitems(config: Any, items: List[Any]) -> None:
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
