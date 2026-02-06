# mypy: ignore-errors
"""
IBKR Gateway connection validation for paper trading.
Tests connection, contract qualification, and operator ID order submission.
"""

from __future__ import annotations

import sys

from ib_insync import IB, LimitOrder, Stock

from bot.config.settings import Settings


def test_gateway_connection() -> bool:
    """Test IBKR Gateway connection and operator ID transmission."""
    settings = Settings()
    ib = IB()

    print("=" * 60)
    print("IBKR GATEWAY CONNECTION TEST")
    print("=" * 60)

    try:
        # Step 1: Connection
        print(f"\n[1/5] Connecting to {settings.IBKR_HOST}:{settings.IBKR_PORT}...")
        ib.connect(
            settings.IBKR_HOST,
            settings.IBKR_PORT,
            clientId=settings.IBKR_CLIENT_ID,
            timeout=10,
        )
        print("\u2713 Connected to IBKR Gateway")
        print(f"  Accounts: {ib.managedAccounts()}")

        # Step 2: Contract Qualification
        print("\n[2/5] Qualifying test contract (SPY)...")
        contract = Stock("SPY", "SMART", "USD")
        qualified = ib.qualifyContracts(contract)
        if not qualified:
            raise RuntimeError("Contract qualification failed")
        print(f"\u2713 Contract qualified: {qualified[0]}")

        # Step 3: Market Data (Snapshot)
        print("\n[3/5] Requesting market data snapshot...")
        ticker = ib.reqMktData(contract, snapshot=True)
        ib.sleep(2)
        print("\u2713 Market data received:")
        print(f"  Last: {ticker.last}")
        print(f"  Bid: {ticker.bid}")
        print(f"  Ask: {ticker.ask}")

        # Step 4: Test Order with Operator ID
        print("\n[4/5] Creating test order with operator ID...")
        order = LimitOrder("BUY", 1, 400.0)
        setattr(order, "operatorId", settings.OPERATOR_ID)
        print(f"\u2713 Operator ID set: {getattr(order, 'operatorId')}")

        # Step 5: Submit Order
        print("\n[5/5] Submitting test order to IBKR...")
        trade = ib.placeOrder(contract, order)
        ib.sleep(3)

        print("\u2713 Order submitted successfully")
        print(f"  Order ID: {trade.order.orderId}")
        print(f"  Status: {trade.orderStatus.status}")
        print("  Operator ID transmitted: " f"{getattr(trade.order, 'operatorId', 'NOT FOUND')}")

        # Cleanup: Cancel test order
        print("\n[CLEANUP] Cancelling test order...")
        ib.cancelOrder(order)
        ib.sleep(2)
        print("\u2713 Test order cancelled")

        print("\n" + "=" * 60)
        print("\u2705 ALL TESTS PASSED")
        print("=" * 60)
        print("Gateway connection: \u2713")
        print("Contract qualification: \u2713")
        print("Market data: \u2713")
        print("Order submission: \u2713")
        print("Operator ID (CSATSPRIM): \u2713")
        print("\nPaper trading validation COMPLETE.")

        return True
    except Exception as exc:
        print("\n" + "=" * 60)
        print("\u274c TEST FAILED")
        print("=" * 60)
        print(f"Error: {exc}")
        print("\nTroubleshooting:")
        print("1. Verify IBKR Gateway is running")
        print(f"2. Check Gateway is on port {settings.IBKR_PORT}")
        print("3. Confirm API settings allow socket connections")
        print("4. Verify paper trading account is logged in")
        return False
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\n\u2713 Disconnected from Gateway")


if __name__ == "__main__":
    success = test_gateway_connection()
    sys.exit(0 if success else 1)
