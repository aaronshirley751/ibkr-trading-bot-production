"""
Live Validation: IBKR Gateway Broker Connectivity

Tests basic connection, authentication, account data retrieval, and reconnection resilience.
Validates the bot can establish and maintain stable connection to IBKR Gateway.

Requirements:
- IBKR Gateway running on localhost:4002
- Paper trading account
- Manual execution during market hours
"""

import time
from typing import Any

import pytest

# Note: These imports will be updated once broker layer is implemented
# from src.broker.ibkr_gateway import IBKRGateway


@pytest.mark.live
def test_gateway_authentication(live_gateway_connection: Any) -> None:
    """
    Verify Gateway authentication succeeds with paper trading credentials.

    Validates:
    - Gateway connection is active
    - Authentication completed successfully
    - Connection state is stable

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - is_connected() returns True
        - is_authenticated() returns True
    """
    gateway = live_gateway_connection

    assert gateway.is_connected() is True, "Gateway should be connected"
    assert gateway.is_authenticated() is True, "Gateway should be authenticated"

    # Note: This test currently skipped via conftest.py fixture
    # Will be activated once broker layer implementation is complete


@pytest.mark.live
def test_account_info_retrieval(live_gateway_connection: Any) -> None:
    """
    Verify account information is retrievable and valid.

    Validates:
    - Account details accessible via API
    - Account ID is present
    - Account type is PAPER (safety check)

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - account_info is not None
        - account_info.account_id is not None
        - account_info.account_type == "PAPER"
    """
    gateway = live_gateway_connection

    account_info = gateway.get_account_info()

    assert account_info is not None, "Account info should be retrievable"
    assert account_info.account_id is not None, "Account ID should be present"
    assert (
        account_info.account_type == "PAPER"
    ), f"SAFETY CHECK: Account type must be PAPER, found: {account_info.account_type}"


@pytest.mark.live
def test_account_balance_retrieval(live_gateway_connection: Any) -> None:
    """
    Verify account balance and buying power are accessible.

    Validates:
    - Balance data structure is valid
    - Total cash value is non-negative
    - Buying power is non-negative

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - balance is not None
        - balance.total_cash_value >= 0
        - balance.buying_power >= 0

    Note:
        Paper accounts start with virtual capital (typically $100k+)
    """
    gateway = live_gateway_connection

    balance = gateway.get_account_balance()

    assert balance is not None, "Balance should be retrievable"
    assert (
        balance.total_cash_value >= 0
    ), f"Total cash value should be non-negative, found: {balance.total_cash_value}"
    assert (
        balance.buying_power >= 0
    ), f"Buying power should be non-negative, found: {balance.buying_power}"


@pytest.mark.live
def test_position_retrieval_empty_account(live_gateway_connection: Any) -> None:
    """
    Verify position tracking works correctly.

    Validates:
    - Position data structure is valid
    - If positions exist, all required fields are present
    - Position quantities are non-zero
    - Average costs are positive

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - positions list is not None
        - Each position has valid symbol, quantity, avg_cost

    Note:
        Fresh paper account should have no positions.
        If positions exist from prior testing, verify data structure only.
    """
    gateway = live_gateway_connection

    positions = gateway.get_positions()

    assert positions is not None, "Positions should be retrievable (can be empty list)"

    # If positions exist from prior testing, verify data structure is valid
    for position in positions:
        assert position.symbol is not None, f"Position symbol should not be None: {position}"
        assert position.quantity != 0, f"Position quantity should be non-zero: {position}"
        assert position.avg_cost > 0, f"Position average cost should be positive: {position}"


@pytest.mark.live
def test_gateway_reconnection_resilience(live_gateway_connection: Any) -> None:
    """
    Verify Gateway can recover from transient disconnection.

    Validates:
    - Gateway handles forced disconnect gracefully
    - Reconnection succeeds with exponential backoff
    - Authentication persists after reconnection
    - Connection state is stable after recovery

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - Disconnect reduces is_connected() to False
        - Reconnect restores is_connected() to True
        - Authentication remains valid after reconnection

    Note:
        This test validates resilience critical for production deployment.
        Network interruptions should not require bot restart.
    """
    gateway = live_gateway_connection

    # Verify initial connection state
    assert gateway.is_connected() is True, "Gateway should be connected initially"

    # Force disconnect
    gateway.disconnect()
    assert gateway.is_connected() is False, "Gateway should be disconnected after disconnect()"

    # Reconnect with exponential backoff (max 3 retries)
    max_retries = 3
    connected = False

    for attempt in range(max_retries):
        wait_time = 2**attempt  # 1s, 2s, 4s
        time.sleep(wait_time)

        gateway.connect()
        if gateway.is_connected():
            connected = True
            break

    assert connected is True, f"Gateway should reconnect within {max_retries} attempts"
    assert gateway.is_connected() is True, "Gateway should be connected after reconnection"
    assert gateway.is_authenticated() is True, "Gateway should be authenticated after reconnection"


@pytest.mark.live
def test_gateway_connection_stability(live_gateway_connection: Any) -> None:
    """
    Verify Gateway connection remains stable over extended duration.

    Validates:
    - Connection persists for minimum 60 seconds
    - No spontaneous disconnections
    - Authentication remains valid throughout

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - is_connected() returns True after 60 seconds
        - No connection errors during wait period

    Note:
        This test ensures Gateway connection is production-ready for
        multi-hour trading sessions.
    """
    gateway = live_gateway_connection

    # Verify initial state
    assert gateway.is_connected() is True
    assert gateway.is_authenticated() is True

    # Monitor connection for 60 seconds
    duration = 60  # seconds
    check_interval = 5  # seconds

    for elapsed in range(0, duration, check_interval):
        time.sleep(check_interval)

        assert (
            gateway.is_connected() is True
        ), f"Gateway disconnected unexpectedly after {elapsed + check_interval}s"

    # Final verification
    assert gateway.is_connected() is True
    assert gateway.is_authenticated() is True
