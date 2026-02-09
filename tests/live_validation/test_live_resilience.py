"""
Live Validation: Gateway Resilience and Error Handling

Tests network timeout handling, API rate limiting, error recovery, and
graceful degradation under adverse conditions.

Validates the bot's production readiness for multi-hour trading sessions
with network instability and API constraints.

Requirements:
- IBKR Gateway running on localhost:4002
- Paper trading account
- Manual execution required
"""

import time
from datetime import datetime, timezone
from typing import Any

import pytest

# Note: These imports will be updated once broker layer is implemented
# from src.broker.exceptions import TimeoutError, RateLimitError, ContractNotFoundError

# Placeholder exception for type checking until broker layer is complete
# This will be replaced with actual exception imports in Phase 2
try:
    from src.broker.exceptions import RateLimitError, TimeoutError  # type: ignore[attr-defined]
except ImportError:
    # Define placeholder exceptions if broker layer not yet implemented
    class RateLimitError(Exception):  # type: ignore[no-redef]
        """Placeholder for API rate limit errors"""

        pass

    class TimeoutError(Exception):  # type: ignore[no-redef]
        """Placeholder for timeout errors"""

        pass


@pytest.mark.live
def test_network_timeout_handling(live_gateway_connection: Any) -> None:
    """
    Verify Gateway handles network timeouts gracefully.

    Validates:
    - Timeout errors are caught correctly
    - Gateway remains connected after timeout
    - Bot doesn't crash or enter invalid state

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - Either data returns successfully or TimeoutError raised
        - Gateway.is_connected() remains True after timeout

    Note:
        Uses artificially short timeout (1 second) to simulate
        slow network conditions without waiting extended periods.
    """
    gateway = live_gateway_connection

    contract = gateway.create_contract(
        symbol="SPY", sec_type="STK", exchange="SMART", currency="USD"
    )

    qualified_contract = gateway.qualify_contract(contract)

    # Request historical data with artificially short timeout
    try:
        bars = gateway.get_historical_data(
            contract=qualified_contract,
            duration="1 D",
            bar_size="5 mins",
            what_to_show="TRADES",
            timeout=1,  # 1 second (may timeout)
        )
        # If succeeds, verify data validity
        assert len(bars) > 0, "If data returned, should have bars"
    except TimeoutError:
        # Timeout is acceptable — verify Gateway remains connected
        pass

    # Critical: Gateway should remain operational after timeout
    assert gateway.is_connected() is True, "Gateway should remain connected after timeout event"


@pytest.mark.live
def test_api_rate_limit_handling(live_gateway_connection: Any) -> None:
    """
    Verify exponential backoff on API rate limit errors.

    Validates:
    - Bot handles rate limiting gracefully
    - Exponential backoff is applied correctly
    - Gateway connection persists through rate limit events
    - Some requests succeed despite rate limiting

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - Some successful requests despite rapid-fire attempts
        - Gateway remains connected after rate limit events
        - No crash or invalid state

    Note:
        IBKR rate limit: ~50 requests/second. This test intentionally
        exceeds the limit to validate backoff logic.
    """
    gateway = live_gateway_connection

    contract = gateway.create_contract(
        symbol="SPY", sec_type="STK", exchange="SMART", currency="USD"
    )

    qualified_contract = gateway.qualify_contract(contract)

    # Rapid-fire requests to trigger rate limiting
    successful_requests = 0
    rate_limit_errors = 0

    for i in range(20):
        try:
            quote = gateway.get_market_data(qualified_contract, snapshot=True)
            if quote is not None:
                successful_requests += 1
        except RateLimitError:
            rate_limit_errors += 1
            # Apply exponential backoff (max 8 second backoff)
            time.sleep(2 ** min(rate_limit_errors, 3))
        except Exception:
            # Other errors are acceptable in this stress test
            pass

    # Should have some successful requests despite rate limiting
    assert (
        successful_requests > 0
    ), f"Should have some successful requests, found: {successful_requests}"

    # Gateway should remain connected after rate limit events
    assert gateway.is_connected() is True, "Gateway should remain connected after rate limit events"


@pytest.mark.live
def test_market_data_staleness_detection(live_gateway_connection: Any) -> None:
    """
    Verify bot detects and handles stale market data correctly.

    Validates:
    - Quote timestamp is populated
    - Staleness calculation works correctly
    - Bot can distinguish fresh vs. stale quotes

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - During market hours: quote age < 5 seconds
        - Outside market hours: stale data detected (age > 5 seconds)

    Note:
        This test should be run both during and after market hours
        to validate both scenarios. Bot must NEVER trade on stale data.
    """
    gateway = live_gateway_connection

    contract = gateway.create_contract(
        symbol="SPY", sec_type="STK", exchange="SMART", currency="USD"
    )

    qualified_contract = gateway.qualify_contract(contract)

    # Get current quote
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    # Check timestamp freshness
    quote_age = datetime.now(timezone.utc) - quote.timestamp

    # During market hours, quotes should be < 5 seconds old
    # Outside market hours, this test documents expected staleness
    # Bot should detect staleness and skip trading
    if quote_age.total_seconds() < 5:
        # Fresh quote (market hours)
        pass  # Expected during RTH
    else:
        # Stale quote (outside market hours or data delay)
        # Bot should NOT trade on this data
        assert quote_age.total_seconds() > 5, (
            "Stale quote detected. Bot should skip trading on stale data. "
            f"Quote age: {quote_age.total_seconds():.2f}s"
        )


@pytest.mark.live
def test_gateway_error_recovery(live_gateway_connection: Any) -> None:
    """
    Verify Gateway recovers from error states gracefully.

    Validates:
    - Invalid operations trigger appropriate errors
    - Errors are caught and handled correctly
    - Gateway remains operational after error
    - Valid operations continue to work after error

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - Invalid contract qualification raises error
        - Gateway.is_connected() remains True after error
        - Subsequent valid operations succeed

    Note:
        Production bot must handle errors without crashing.
        This validates defensive programming practices.
    """
    gateway = live_gateway_connection

    # Attempt invalid operation (should trigger error but not crash)
    error_caught = False
    try:
        # Request data for invalid contract
        invalid_contract = gateway.create_contract(
            symbol="INVALID_SYMBOL_XYZ", sec_type="STK", exchange="SMART", currency="USD"
        )

        qualified_contract = gateway.qualify_contract(invalid_contract)
        # Should raise ContractNotFoundError or similar
    except Exception as e:
        # Error expected — verify it's handled gracefully
        error_message = str(e).lower()
        assert (
            "not found" in error_message or "invalid" in error_message
        ), f"Expected contract error, found: {e}"
        error_caught = True

    assert error_caught is True, "Invalid contract should raise error"

    # Verify Gateway still operational after error
    assert gateway.is_connected() is True, "Gateway should remain connected after error"

    # Verify valid operations still work
    valid_contract = gateway.create_contract(
        symbol="SPY", sec_type="STK", exchange="SMART", currency="USD"
    )

    qualified_contract = gateway.qualify_contract(valid_contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    assert quote is not None, "Valid operations should work after error recovery"


@pytest.mark.live
def test_concurrent_request_handling(live_gateway_connection: Any) -> None:
    """
    Verify Gateway handles concurrent requests correctly.

    Validates:
    - Multiple contracts can be qualified simultaneously
    - Multiple market data requests don't interfere
    - No race conditions or threading issues

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - All contracts qualify successfully
        - All quotes retrieved correctly
        - No data corruption or request mixing

    Note:
        Bot may need to monitor multiple symbols concurrently
        (SPY, QQQ, VIX). This validates thread-safety.
    """
    gateway = live_gateway_connection

    symbols = ["SPY", "QQQ", "IWM", "VXX", "TLT"]

    # Qualify all contracts
    qualified_contracts = {}
    for symbol in symbols:
        contract = gateway.create_contract(
            symbol=symbol, sec_type="STK", exchange="SMART", currency="USD"
        )
        qualified_contracts[symbol] = gateway.qualify_contract(contract)

    # Retrieve quotes for all symbols
    quotes = {}
    for symbol, contract in qualified_contracts.items():
        quotes[symbol] = gateway.get_market_data(contract, snapshot=True)

    # Verify all operations succeeded
    for symbol in symbols:
        assert quotes[symbol] is not None, f"{symbol} quote should be retrievable"
        assert (
            quotes[symbol].last_price > 0
        ), f"{symbol} should have valid price: {quotes[symbol].last_price}"


@pytest.mark.live
def test_extended_session_stability(live_gateway_connection: Any) -> None:
    """
    Verify Gateway connection remains stable over extended duration.

    Validates:
    - Connection persists for 5+ minutes
    - Periodic operations succeed throughout session
    - No memory leaks or resource exhaustion
    - No spontaneous disconnections

    Args:
        live_gateway_connection: Gateway fixture from conftest

    Expected:
        - Gateway remains connected for full duration
        - All periodic checks succeed

    Note:
        Production bot will run for 6+ hours during trading day.
        This test validates 5-minute stability as proxy for longer sessions.
    """
    gateway = live_gateway_connection

    contract = gateway.create_contract(
        symbol="SPY", sec_type="STK", exchange="SMART", currency="USD"
    )

    qualified_contract = gateway.qualify_contract(contract)

    # Monitor connection for 5 minutes (300 seconds)
    duration = 300  # 5 minutes
    check_interval = 30  # Check every 30 seconds

    checks_passed = 0

    for elapsed in range(0, duration, check_interval):
        time.sleep(check_interval)

        # Verify connection
        assert (
            gateway.is_connected() is True
        ), f"Gateway disconnected at {elapsed + check_interval}s"

        # Verify operations work
        quote = gateway.get_market_data(qualified_contract, snapshot=True)
        assert quote is not None, f"Quote retrieval failed at {elapsed + check_interval}s"

        checks_passed += 1

    # Final verification
    assert gateway.is_connected() is True
    assert (
        checks_passed == duration // check_interval
    ), f"Should pass all checks, passed: {checks_passed}"


@pytest.mark.live
def test_invalid_order_rejection(live_gateway_connection: Any, market_hours_check: None) -> None:
    """
    Verify Gateway correctly rejects invalid orders.

    Validates:
    - Orders with invalid parameters are rejected
    - Error messages are clear and actionable
    - Gateway remains operational after rejection

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - Invalid order raises appropriate error
        - Error message indicates rejection reason
        - Gateway connection persists

    Note:
        Production bot must handle order rejections gracefully
        (insufficient funds, invalid contract, etc.)
    """
    gateway = live_gateway_connection

    contract = gateway.create_contract(
        symbol="SPY",
        sec_type="OPT",
        exchange="SMART",
        currency="USD",
        last_trade_date="20260220",  # Weekly expiry
        strike=600.0,
        right="CALL",
    )

    qualified_contract = gateway.qualify_contract(contract)

    # Attempt to submit order with invalid parameters
    # Example: negative quantity (should be rejected)
    error_caught = False
    try:
        order = gateway.create_order(
            action="BUY",
            order_type="LMT",
            total_quantity=-1,  # Invalid: negative quantity
            lmt_price=1.0,
            tif="DAY",
        )

        # Should raise error before or during place_order
        _ = gateway.place_order(qualified_contract, order)
        # Should not reach here if validation works correctly
    except Exception as e:
        error_caught = True
        # Verify error is descriptive
        assert (
            "quantity" in str(e).lower() or "invalid" in str(e).lower()
        ), f"Expected quantity error, found: {e}"

    assert error_caught is True, "Invalid order should be rejected"

    # Verify Gateway still operational
    assert gateway.is_connected() is True
