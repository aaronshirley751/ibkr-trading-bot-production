"""
Live Validation: Market Data Quality and Reliability

Tests real-time market data subscriptions, historical data retrieval, quote freshness,
and stream quality under live market conditions.

Requirements:
- IBKR Gateway running on localhost:4002
- Paper trading account
- Market hours: 9:30 AM - 4:00 PM ET (for real-time data)
- Manual execution required
"""

import time
from datetime import datetime, timezone
from typing import Any

import pytest

# Note: These imports will be updated once broker layer is implemented
# from src.broker.ibkr_gateway import Contract


@pytest.mark.live
def test_market_data_subscription_spy(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify real-time market data subscription for SPY.

    Validates:
    - Contract qualification succeeds
    - Real-time quote retrieval works with snapshot=True (buffer overflow fix)
    - Quote data structure is complete (last, bid, ask, timestamp)
    - Quote freshness (< 5 seconds old)
    - Bid-ask spread is valid (ask > bid)

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - qualified_contract.conId > 0
        - quote is not None
        - quote.last_price > 0
        - quote.ask > quote.bid
        - quote.timestamp age < 5 seconds

    Critical:
        ALWAYS use snapshot=True to prevent Gateway buffer overflow
    """
    gateway = live_gateway_connection

    # Qualify contract first (critical: prevents buffer overflow)
    contract = gateway.create_contract(
        symbol="SPY", sec_type="STK", exchange="SMART", currency="USD"
    )

    qualified_contract = gateway.qualify_contract(contract)
    assert qualified_contract.conId > 0, "Valid contract ID should be assigned"

    # Subscribe to real-time quotes with snapshot=True (buffer overflow fix)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    assert quote is not None, "Quote should be retrievable"
    assert quote.last_price > 0, f"Last price should be positive: {quote.last_price}"
    assert quote.bid > 0, f"Bid should be positive: {quote.bid}"
    assert quote.ask > 0, f"Ask should be positive: {quote.ask}"
    assert quote.ask > quote.bid, f"Ask ({quote.ask}) should be greater than bid ({quote.bid})"
    assert quote.timestamp is not None, "Quote timestamp should be present"

    # Verify quote freshness (< 5 seconds old)
    quote_age = datetime.now(timezone.utc) - quote.timestamp
    assert (
        quote_age.total_seconds() < 5
    ), f"Quote should be fresh (< 5s old), found: {quote_age.total_seconds():.2f}s"


@pytest.mark.live
def test_historical_data_retrieval_spy(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify historical data retrieval for backtesting/strategy logic.

    Validates:
    - Historical bars can be retrieved
    - Bar count is reasonable for requested duration
    - OHLCV data is complete and valid
    - Bars are in chronological order
    - Volume data is non-negative

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - len(bars) > 0
        - All bars have close > 0
        - All bars have volume >= 0
        - Timestamps are sorted chronologically

    Note:
        Uses 1 day / 5-minute bars to stay within IBKR limits
        (max 1-hour RTH-only windows, max 1000 bars)
    """
    gateway = live_gateway_connection

    contract = gateway.create_contract(
        symbol="SPY", sec_type="STK", exchange="SMART", currency="USD"
    )

    qualified_contract = gateway.qualify_contract(contract)

    # Request 1 day of 5-minute bars (standard intraday data)
    bars = gateway.get_historical_data(
        contract=qualified_contract, duration="1 D", bar_size="5 mins", what_to_show="TRADES"
    )

    assert len(bars) > 0, "Historical bars should be returned"

    # Verify all bars have valid OHLCV data
    for i, bar in enumerate(bars):
        assert bar.close > 0, f"Bar {i} close should be positive: {bar.close}"
        assert bar.volume >= 0, f"Bar {i} volume should be non-negative: {bar.volume}"
        assert bar.timestamp is not None, f"Bar {i} should have timestamp"

    # Verify bars are in chronological order
    timestamps = [bar.timestamp for bar in bars]
    assert timestamps == sorted(timestamps), "Bars should be in chronological order"


@pytest.mark.live
def test_market_data_multiple_symbols(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify concurrent market data subscriptions (SPY, QQQ, IWM).

    Validates:
    - Multiple contracts can be qualified simultaneously
    - Multiple quotes can be retrieved without interference
    - All symbols return valid quote data
    - No race conditions or subscription conflicts

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - All symbols qualify successfully
        - All quotes retrieved with valid prices

    Note:
        This test validates the bot can monitor multiple symbols
        as required by Strategy A/B implementations.
    """
    gateway = live_gateway_connection
    symbols = ["SPY", "QQQ", "IWM"]

    quotes = {}
    for symbol in symbols:
        contract = gateway.create_contract(
            symbol=symbol, sec_type="STK", exchange="SMART", currency="USD"
        )

        qualified_contract = gateway.qualify_contract(contract)
        quotes[symbol] = gateway.get_market_data(qualified_contract, snapshot=True)

    # Verify all quotes retrieved successfully
    for symbol in symbols:
        assert quotes[symbol] is not None, f"{symbol} quote should be retrievable"
        assert (
            quotes[symbol].last_price > 0
        ), f"{symbol} last price should be positive: {quotes[symbol].last_price}"


@pytest.mark.live
def test_market_data_stream_quality(live_gateway_connection: Any, market_hours_check: None) -> None:
    """
    Verify market data stream remains stable over 60 seconds.

    Validates:
    - Streaming subscription works without interruption
    - Quote updates are frequent (target: ~1 per second)
    - No stale quotes (all timestamps within window)
    - Stream cleanup works correctly

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - Receive >= 50 quotes in 60 seconds (~83% success rate)
        - All quote timestamps within 2x tolerance (120s)
        - Stream unsubscribe completes without errors

    Note:
        This test validates Gateway connection stability for
        extended trading sessions (multi-hour endurance).
    """
    gateway = live_gateway_connection

    contract = gateway.create_contract(
        symbol="SPY", sec_type="STK", exchange="SMART", currency="USD"
    )

    qualified_contract = gateway.qualify_contract(contract)

    # Subscribe to streaming data
    gateway.subscribe_market_data(qualified_contract)

    # Collect quotes for 60 seconds
    quotes_received = []
    start_time = time.time()
    check_interval = 1  # Check every second

    while time.time() - start_time < 60:
        quote = gateway.get_latest_quote(qualified_contract)
        if quote is not None:
            quotes_received.append(quote)
        time.sleep(check_interval)

    # Cleanup: Unsubscribe from streaming data
    gateway.unsubscribe_market_data(qualified_contract)

    # Verify stream quality
    assert (
        len(quotes_received) >= 50
    ), f"Should receive ~60 quotes (1/sec), found: {len(quotes_received)}"

    # Verify no stale quotes (all timestamps within 60-second window + tolerance)
    for i, quote in enumerate(quotes_received):
        quote_age = datetime.now(timezone.utc) - quote.timestamp
        assert (
            quote_age.total_seconds() < 120
        ), f"Quote {i} is stale (age: {quote_age.total_seconds():.2f}s)"


@pytest.mark.live
def test_market_data_quote_freshness_validation(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify bot can detect and reject stale market data.

    Validates:
    - Quote timestamp is populated correctly
    - Timestamp comparison logic works
    - Freshness threshold is enforced (< 5 seconds)

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - Quote timestamp age < 5 seconds during market hours

    Note:
        Outside market hours, this test would skip or expect stale data.
        Bot should NEVER trade on stale quotes (> 5s old).
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
    assert quote_age.total_seconds() < 5, (
        f"Quote should be fresh during market hours (< 5s), "
        f"found: {quote_age.total_seconds():.2f}s"
    )


@pytest.mark.live
def test_option_contract_qualification(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify option contract qualification for weekly options.

    Validates:
    - Option contracts can be qualified via symbol lookup
    - Required option parameters are populated (strike, expiry, right)
    - Contract ID is assigned correctly

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - qualified_contract.conId > 0
        - Strike, expiry, right are preserved

    Note:
        This test validates the core contract qualification logic
        required for Strategy A (momentum) and Strategy B (mean-reversion)
        options trading on SPY/QQQ weeklies.
    """
    gateway = live_gateway_connection

    # Create option contract for SPY weekly (parameters from config)
    contract = gateway.create_contract(
        symbol="SPY",
        sec_type="OPT",
        exchange="SMART",
        currency="USD",
        last_trade_date="20260220",  # Weekly expiry (update as needed)
        strike=600.0,  # Deep OTM for safety
        right="CALL",
    )

    qualified_contract = gateway.qualify_contract(contract)

    assert qualified_contract.conId > 0, "Option contract should be qualified"
    assert qualified_contract.strike == 600.0, "Strike should be preserved"
    assert qualified_contract.right == "CALL", "Right should be preserved"
    assert (
        qualified_contract.lastTradeDateOrContractMonth == "20260220"
    ), "Expiry should be preserved"
