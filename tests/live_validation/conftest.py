"""
Live Validation Test Fixtures

Provides Gateway connection fixture for live validation testing against paper trading account.
"""

from pathlib import Path
from typing import Any, Generator, cast

import pytest
import yaml

# Note: These imports will need to be adjusted based on actual broker implementation
# Placeholder imports for handoff implementation
# from src.broker.ibkr_gateway import IBKRGateway
# from src.broker.exceptions import ConnectionError, AuthenticationError


@pytest.fixture(scope="session")
def live_validation_config() -> dict[str, Any]:
    """
    Load live validation configuration from config file.

    Returns:
        dict: Configuration parameters for live validation testing

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is malformed
    """
    config_path = Path("config/live_validation_config.yaml")

    if not config_path.exists():
        raise FileNotFoundError(
            f"Live validation config not found at {config_path}. "
            "Please create config/live_validation_config.yaml before running live tests."
        )

    with open(config_path, "r") as f:
        config = cast(dict[str, Any], yaml.safe_load(f))

    return config


@pytest.fixture(scope="session")
def live_gateway_connection(live_validation_config: dict[str, Any]) -> Generator[Any, None, None]:
    """
    Establishes connection to IBKR Gateway for live validation testing.

    Preconditions:
    - IBKR Gateway must be running (manual startup required)
    - Paper trading credentials configured in live_validation_config.yaml
    - Market hours: 9:30 AM - 4:00 PM ET (or extended hours if configured)

    Args:
        live_validation_config: Configuration dictionary from config file

    Yields:
        Gateway connection object for test session

    Raises:
        ConnectionError: If Gateway unreachable after 30 seconds
        RuntimeError: If not using paper trading account (SAFETY VIOLATION)

    Note:
        This fixture is session-scoped to maintain a single Gateway connection
        across all live validation tests for efficiency.
    """
    # TODO: Implement actual Gateway connection once broker layer is complete
    # This is a placeholder implementation for handoff documentation

    pytest.skip(
        "Live validation tests require actual IBKR Gateway connection. "
        "Implementation pending completion of broker layer (Phase 2). "
        "These tests are designed for manual execution during market hours "
        "as the final Phase 1 gate before source code implementation."
    )

    # Placeholder implementation structure (to be completed in Phase 2):
    """
    config = live_validation_config
    gateway_config = config.get("gateway", {})
    paper_config = config.get("paper_trading", {})

    # Connect to Gateway with extended timeout for live environment
    gateway = IBKRGateway(
        host=gateway_config.get("host", "127.0.0.1"),
        port=gateway_config.get("port", 4002),
        client_id=gateway_config.get("client_id", 1),
        timeout=gateway_config.get("timeout", 30)
    )

    # Authenticate and validate connection
    max_retries = 3
    connected = False

    for attempt in range(max_retries):
        try:
            gateway.connect()
            if gateway.is_connected():
                connected = True
                break
        except ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
            else:
                raise

    if not connected:
        raise ConnectionError(
            f"Gateway connection failed after {max_retries} attempts. "
            f"Verify Gateway is running on {gateway_config.get('host')}:{gateway_config.get('port')}"
        )

    # CRITICAL SAFETY CHECK: Verify paper trading mode
    account_type = gateway.get_account_type()
    expected_account_type = paper_config.get("account_type", "PAPER")

    if account_type != expected_account_type:
        gateway.disconnect()
        raise RuntimeError(
            f"SAFETY VIOLATION: Live validation must use paper trading account. "
            f"Found account type: {account_type}, expected: {expected_account_type}. "
            f"NEVER execute live validation against live trading accounts."
        )

    # Yield connection for test session
    yield gateway

    # Cleanup: Cancel all open orders, disconnect gracefully
    try:
        gateway.cancel_all_orders()
    except Exception as e:
        pytest.fail(f"Failed to cancel orders during cleanup: {e}")
    finally:
        gateway.disconnect()
    """


@pytest.fixture(scope="function")
def market_hours_check(live_validation_config: dict[str, Any]) -> None:
    """
    Verify current time is within market hours before executing test.

    Args:
        live_validation_config: Configuration dictionary

    Raises:
        pytest.skip: If executed outside market hours and enforcement enabled

    Note:
        Can be disabled via config: validation.market_hours_required = false
    """
    validation_config = live_validation_config.get("validation", {})

    if not validation_config.get("market_hours_required", True):
        return  # Market hours check disabled in config

    # TODO: Implement actual market hours check using timezone-aware datetime
    # Placeholder implementation:
    """
    from datetime import datetime
    import pytz

    et_tz = pytz.timezone("America/New_York")
    current_time = datetime.now(et_tz)

    # Standard market hours: 9:30 AM - 4:00 PM ET
    market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)

    # Check if weekday (Mon-Fri)
    if current_time.weekday() >= 5:  # Saturday=5, Sunday=6
        pytest.skip(
            f"Market closed (weekend). Live validation requires market hours. "
            f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )

    # Check if within market hours
    if not (market_open <= current_time <= market_close):
        pytest.skip(
            f"Outside market hours (9:30 AM - 4:00 PM ET). "
            f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )
    """

    # For now, just log a warning
    # In production, this should enforce market hours or skip tests
    pass


# Pytest markers for live validation
def pytest_configure(config):
    """Register custom markers for live validation tests."""
    config.addinivalue_line(
        "markers",
        "live: mark test as requiring live IBKR Gateway connection (manual execution only)",
    )
