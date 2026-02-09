"""
Live Validation: Paper Trading Order Execution

Tests order submission, fill detection, position tracking, and order lifecycle
management in paper trading environment.

CRITICAL: All tests use PAPER TRADING ONLY. Never execute against live accounts.

Requirements:
- IBKR Gateway running on localhost:4002
- Paper trading account with sufficient virtual capital
- Market hours: 9:30 AM - 4:00 PM ET
- Manual execution required
"""

import time
from typing import Any

import pytest

# Note: These imports will be updated once broker layer is implemented
# from src.broker.ibkr_gateway import Contract, Order


@pytest.mark.live
def test_paper_trading_limit_order_submission(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify limit order submission to paper trading account.

    Validates:
    - Order creation succeeds
    - Order submission returns valid order ID
    - Order status is trackable
    - Order fills in paper trading (instant fill at limit price)

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - order_id > 0
        - Order status transitions to "Filled"
        - Filled quantity matches order quantity (1)

    Note:
        Paper trading provides instant fills at limit price,
        unlike live trading which may experience slippage.
    """
    gateway = live_gateway_connection

    # Qualify contract
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

    # Get current market price
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    # Submit limit order at current bid (should fill immediately in paper trading)
    order = gateway.create_order(
        action="BUY", order_type="LMT", total_quantity=1, lmt_price=quote.bid, tif="DAY"
    )

    order_id = gateway.place_order(qualified_contract, order)
    assert order_id > 0, "Valid order ID should be returned"

    # Wait for order status updates (max 30 seconds)
    order_status = None
    timeout = 30

    for _ in range(timeout):
        order_status = gateway.get_order_status(order_id)
        if order_status.status in ["Filled", "Cancelled"]:
            break
        time.sleep(1)

    # In paper trading, limit orders at bid should fill quickly
    assert order_status is not None, "Order status should be retrievable"
    assert (
        order_status.status == "Filled"
    ), f"Order should fill in paper trading, found status: {order_status.status}"
    assert (
        order_status.filled_quantity == 1
    ), f"Filled quantity should be 1, found: {order_status.filled_quantity}"


@pytest.mark.live
def test_paper_trading_position_tracking(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify position appears in account after order fill.

    Validates:
    - Position tracking updates after order execution
    - Position data structure is complete
    - Position quantity matches order fill
    - Average cost is populated correctly

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - Position exists for SPY CALL option
        - Position quantity == 1
        - Position avg_cost > 0

    Note:
        This test submits an order, waits for fill, then verifies
        position tracking reflects the new position correctly.
    """
    gateway = live_gateway_connection

    # Submit and fill an order
    contract = gateway.create_contract(
        symbol="SPY",
        sec_type="OPT",
        exchange="SMART",
        currency="USD",
        last_trade_date="20260220",  # Weekly expiry
        strike=600.0,  # Deep OTM
        right="CALL",
    )

    qualified_contract = gateway.qualify_contract(contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    order = gateway.create_order(
        action="BUY", order_type="LMT", total_quantity=1, lmt_price=quote.bid, tif="DAY"
    )

    order_id = gateway.place_order(qualified_contract, order)

    # Wait for fill
    for _ in range(30):
        order_status = gateway.get_order_status(order_id)
        if order_status.status == "Filled":
            break
        time.sleep(1)

    assert order_status.status == "Filled", "Order should fill before position check"

    # Retrieve positions
    positions = gateway.get_positions()

    # Verify position exists for SPY CALL
    spy_positions = [
        p for p in positions if p.symbol == "SPY" and p.sec_type == "OPT" and p.right == "CALL"
    ]

    assert len(spy_positions) > 0, "SPY CALL position should exist after fill"

    spy_position = spy_positions[0]
    assert (
        spy_position.quantity == 1
    ), f"Position quantity should be 1, found: {spy_position.quantity}"
    assert (
        spy_position.avg_cost > 0
    ), f"Position avg_cost should be positive, found: {spy_position.avg_cost}"


@pytest.mark.live
def test_paper_trading_order_cancellation(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify order cancellation works correctly.

    Validates:
    - Order can be submitted and remain unfilled (limit far from market)
    - Cancel request succeeds
    - Order status transitions to "Cancelled"
    - No partial fills occur before cancellation

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - Order submits successfully
        - Cancel request succeeds
        - Order status == "Cancelled"

    Note:
        This test uses a limit price far below market (50% of bid)
        to ensure order doesn't fill before cancellation.
    """
    gateway = live_gateway_connection

    # Submit limit order far from market (won't fill)
    contract = gateway.create_contract(
        symbol="SPY",
        sec_type="OPT",
        exchange="SMART",
        currency="USD",
        last_trade_date="20260220",  # Weekly expiry
        strike=600.0,  # Deep OTM
        right="CALL",
    )

    qualified_contract = gateway.qualify_contract(contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    order = gateway.create_order(
        action="BUY",
        order_type="LMT",
        total_quantity=1,
        lmt_price=quote.bid * 0.5,  # 50% below market (won't fill)
        tif="DAY",
    )

    order_id = gateway.place_order(qualified_contract, order)
    time.sleep(2)  # Let order register

    # Cancel order
    gateway.cancel_order(order_id)

    # Verify cancellation (max 10 seconds)
    order_status = None
    for _ in range(10):
        order_status = gateway.get_order_status(order_id)
        if order_status.status == "Cancelled":
            break
        time.sleep(1)

    assert order_status is not None, "Order status should be retrievable"
    assert (
        order_status.status == "Cancelled"
    ), f"Order should be cancelled, found status: {order_status.status}"


@pytest.mark.live
def test_paper_trading_close_position(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify position closing (sell to close) works correctly.

    Validates:
    - Position can be established (buy order)
    - Position can be closed (sell order)
    - Both buy and sell orders fill successfully
    - Position is flat after close (quantity == 0 or removed)

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - Buy order fills successfully
        - Sell order fills successfully
        - Final position is flat (quantity == 0 or not in positions list)

    Note:
        This test validates the complete order lifecycle:
        open position -> hold -> close position
    """
    gateway = live_gateway_connection

    # Step 1: Establish a position (buy order)
    contract = gateway.create_contract(
        symbol="SPY",
        sec_type="OPT",
        exchange="SMART",
        currency="USD",
        last_trade_date="20260220",  # Weekly expiry
        strike=600.0,  # Deep OTM
        right="CALL",
    )

    qualified_contract = gateway.qualify_contract(contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    # Buy order
    buy_order = gateway.create_order(
        action="BUY", order_type="LMT", total_quantity=1, lmt_price=quote.bid, tif="DAY"
    )

    buy_order_id = gateway.place_order(qualified_contract, buy_order)

    # Wait for buy fill
    buy_status = None
    for _ in range(30):
        buy_status = gateway.get_order_status(buy_order_id)
        if buy_status.status == "Filled":
            break
        time.sleep(1)

    assert buy_status is not None, "Buy order status should be retrievable"
    assert buy_status.status == "Filled", "Buy order should fill"

    # Step 2: Close the position (sell order)
    # Get fresh quote for sell price
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    sell_order = gateway.create_order(
        action="SELL",
        order_type="LMT",
        total_quantity=1,
        lmt_price=quote.ask,  # Sell at ask (should fill)
        tif="DAY",
    )

    sell_order_id = gateway.place_order(qualified_contract, sell_order)

    # Wait for sell fill
    sell_status = None
    for _ in range(30):
        sell_status = gateway.get_order_status(sell_order_id)
        if sell_status.status == "Filled":
            break
        time.sleep(1)

    assert sell_status is not None, "Sell order status should be retrievable"
    assert sell_status.status == "Filled", "Sell order should fill"

    # Step 3: Verify position is closed
    positions = gateway.get_positions()
    spy_positions = [
        p for p in positions if p.symbol == "SPY" and p.sec_type == "OPT" and p.right == "CALL"
    ]

    # Position should either be removed or have quantity == 0
    if len(spy_positions) > 0:
        assert (
            spy_positions[0].quantity == 0
        ), f"Position should be flat, found quantity: {spy_positions[0].quantity}"
    # If len == 0, position was removed from list (also acceptable)


@pytest.mark.live
def test_paper_trading_multiple_orders(
    live_gateway_connection: Any, market_hours_check: None
) -> None:
    """
    Verify multiple orders can be placed and tracked simultaneously.

    Validates:
    - Multiple orders can be submitted without interference
    - Each order receives unique order ID
    - Order status tracking works independently for each order

    Args:
        live_gateway_connection: Gateway fixture from conftest
        market_hours_check: Ensures test runs during market hours

    Expected:
        - All order IDs are unique
        - All orders can be tracked independently

    Note:
        This test validates the bot can manage multiple concurrent
        positions as required by portfolio management logic.
    """
    gateway = live_gateway_connection

    contract = gateway.create_contract(
        symbol="SPY",
        sec_type="OPT",
        exchange="SMART",
        currency="USD",
        last_trade_date="20260220",  # Weekly expiry
        strike=600.0,  # Deep OTM
        right="CALL",
    )

    qualified_contract = gateway.qualify_contract(contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    # Submit 3 orders with different prices (test independent tracking)
    order_ids = []

    for i in range(3):
        order = gateway.create_order(
            action="BUY",
            order_type="LMT",
            total_quantity=1,
            lmt_price=quote.bid * (0.5 + i * 0.1),  # Varying prices
            tif="DAY",
        )

        order_id = gateway.place_order(qualified_contract, order)
        order_ids.append(order_id)

    # Verify all order IDs are unique
    assert len(set(order_ids)) == 3, "All order IDs should be unique"

    # Verify all orders are trackable
    for order_id in order_ids:
        order_status = gateway.get_order_status(order_id)
        assert order_status is not None, f"Order {order_id} should be trackable"

    # Cleanup: Cancel all orders
    for order_id in order_ids:
        gateway.cancel_order(order_id)
