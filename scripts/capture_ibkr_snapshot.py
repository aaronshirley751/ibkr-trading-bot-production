#!/usr/bin/env python3
# mypy: ignore-errors
"""IBKR Market Data Snapshot Capture Script.

Connects to IBKR Gateway (paper trading) and captures real market data
for use in test fixtures. Captures option chains, historical bars, and
Greeks for SPY, QQQ, and IWM.

IMPORTANT: This script ONLY connects to paper trading. Never use with live account.

Usage:
    python scripts/capture_ibkr_snapshot.py [--scenario SCENARIO_NAME]

Examples:
    python scripts/capture_ibkr_snapshot.py
    python scripts/capture_ibkr_snapshot.py --scenario high_vix
    python scripts/capture_ibkr_snapshot.py --scenario tight_spreads

Requirements:
    - IBKR Gateway running and connected (paper trading)
    - Market hours (9:30 AM - 4:00 PM ET)
    - Gateway port 4002 (paper trading port)
"""

import argparse
import json
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper


class SnapshotCapture(EWrapper, EClient):
    """Captures IBKR market data snapshots for test fixtures."""

    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id: Optional[int] = None
        self.contract_details: Dict[int, List] = {}
        self.option_chains: Dict[str, List] = {}
        self.historical_bars: Dict[int, List] = {}
        self.market_data: Dict[int, Dict] = {}
        self.greeks_data: Dict[int, Dict] = {}
        self.current_request_id = 1000
        self.account_type: Optional[str] = None
        self.accounts: str = ""

    def nextValidId(self, orderId: int):
        """Callback when connection established."""
        print(f"✓ Connected to IBKR Gateway. Next Order ID: {orderId}")
        self.next_order_id = orderId

    def managedAccounts(self, accountsList: str):
        """Callback for connected accounts - provides audit trail."""
        print(f"  Connected accounts: {accountsList}")
        self.accounts = accountsList

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary - CRITICAL SAFETY CHECK."""
        if tag == "AccountType":
            self.account_type = value
            print(f"  Account Type: {value}")

            # CRITICAL SAFETY CHECK - ABORT if not paper trading
            if value != "PAPER":
                print(f"\n{'!' * 60}")
                print(f"🔴 SAFETY VIOLATION: Account type is '{value}' not 'PAPER'")
                print("🔴 This script ONLY runs on paper trading accounts")
                print("🔴 ABORTING to prevent live account access")
                print(f"{'!' * 60}\n")
                self.disconnect()
                sys.exit(1)

    def accountSummaryEnd(self, reqId: int):
        """Callback when account summary complete."""
        pass

    def error(self, reqId: int, errorCode: int, errorString: str):
        """Error handler."""
        # Filter out informational messages
        if errorCode in [2104, 2106, 2158]:  # Market data farm connection messages
            print(f"ℹ Info [{errorCode}]: {errorString}")
        elif errorCode == 200:  # No security definition found
            print(f"⚠ Warning: Contract not found (reqId {reqId})")
        else:
            print(f"✗ Error [{errorCode}] (reqId {reqId}): {errorString}")

    def contractDetails(self, reqId: int, contractDetails):
        """Callback for contract details."""
        if reqId not in self.contract_details:
            self.contract_details[reqId] = []
        self.contract_details[reqId].append(contractDetails)

    def contractDetailsEnd(self, reqId: int):
        """Callback when all contract details received."""
        count = len(self.contract_details.get(reqId, []))
        print(f"✓ Received {count} contract details for reqId {reqId}")

    def historicalData(self, reqId: int, bar):
        """Callback for historical data bars."""
        if reqId not in self.historical_bars:
            self.historical_bars[reqId] = []

        bar_data = {
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "wap": bar.wap,  # Weighted average price
            "barCount": bar.barCount,
        }
        self.historical_bars[reqId].append(bar_data)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback when historical data complete."""
        count = len(self.historical_bars.get(reqId, []))
        print(f"✓ Received {count} historical bars for reqId {reqId}")

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Callback for market data price ticks."""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}

        tick_names = {
            1: "bid",
            2: "ask",
            4: "last",
            6: "high",
            7: "low",
            9: "close",
        }

        if tickType in tick_names:
            self.market_data[reqId][tick_names[tickType]] = price

    def tickSize(self, reqId: int, tickType: int, size: int):
        """Callback for market data size ticks."""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}

        tick_names = {
            0: "bidSize",
            3: "askSize",
            5: "lastSize",
            8: "volume",
        }

        if tickType in tick_names:
            self.market_data[reqId][tick_names[tickType]] = size

    def tickOptionComputation(
        self,
        reqId: int,
        tickType: int,
        tickAttrib: int,
        impliedVol: float,
        delta: float,
        optPrice: float,
        pvDividend: float,
        gamma: float,
        vega: float,
        theta: float,
        undPrice: float,
    ):
        """Callback for option Greeks."""
        if reqId not in self.greeks_data:
            self.greeks_data[reqId] = {}

        # Only store model Greeks (tickType 13)
        if tickType == 13:
            self.greeks_data[reqId] = {
                "impliedVolatility": impliedVol if impliedVol != -1 else None,
                "delta": delta if delta != -2 else None,
                "gamma": gamma if gamma != -2 else None,
                "vega": vega if vega != -2 else None,
                "theta": theta if theta != -2 else None,
                "optionPrice": optPrice if optPrice != -1 else None,
                "underlyingPrice": undPrice if undPrice != -1 else None,
            }


def create_stock_contract(symbol: str) -> Contract:
    """Create a stock contract."""
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.primaryExchange = "NASDAQ" if symbol in ["QQQ"] else "ARCA"
    return contract


def create_option_contract(symbol: str, right: str, strike: float, expiry: str) -> Contract:
    """Create an option contract.

    Args:
        symbol: Underlying symbol (SPY, QQQ, IWM)
        right: Call (C) or Put (P)
        strike: Strike price
        expiry: Expiry date in YYYYMMDD format
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.right = right
    contract.strike = strike
    contract.lastTradeDateOrContractMonth = expiry
    contract.multiplier = "100"
    return contract


def get_atm_strike(price: float, symbol: str) -> float:
    """Calculate ATM strike based on current price.

    Args:
        price: Current underlying price
        symbol: Symbol (for strike increment logic)

    Returns:
        ATM strike price rounded to nearest valid strike
    """
    # SPY/QQQ typically have $1 strikes, IWM has $1 strikes
    increment = 1.0

    # Round to nearest increment
    atm = round(price / increment) * increment
    return atm


def get_expiry_dates(days_out: List[int]) -> List[str]:
    """Get expiry dates for options.

    Args:
        days_out: List of days from today (e.g., [2, 7, 14])

    Returns:
        List of expiry dates in YYYYMMDD format
    """
    expiries = []
    for days in days_out:
        expiry = datetime.now() + timedelta(days=days)
        # Find next Friday (options typically expire on Friday)
        days_until_friday = (4 - expiry.weekday()) % 7
        if days_until_friday == 0 and expiry.weekday() != 4:
            days_until_friday = 7
        expiry = expiry + timedelta(days=days_until_friday)
        expiries.append(expiry.strftime("%Y%m%d"))
    return expiries


def validate_snapshot_completeness(data: Dict) -> bool:
    """Validate snapshot has minimum required data.

    Args:
        data: Snapshot data dictionary

    Returns:
        True if snapshot meets minimum completeness criteria
    """
    issues = []

    for symbol, symbol_data in data["symbols"].items():
        # Check current price
        if not symbol_data.get("currentPrice") or symbol_data.get("currentPrice") == 0:
            issues.append(f"{symbol}: Missing or zero current price")

        # Check historical bars (expect ~30-40 bars for 5 days)
        hist_bars = symbol_data.get("historicalBars", [])
        if len(hist_bars) < 20:
            issues.append(
                f"{symbol}: Insufficient historical bars ({len(hist_bars)}, expected 20+)"
            )

        # Check option chain (expect 20 contracts: 5 strikes × 2 expiries × 2 rights)
        option_chain = symbol_data.get("optionChain", [])
        if len(option_chain) < 10:
            issues.append(f"{symbol}: Insufficient option data ({len(option_chain)}, expected 10+)")

        # Check that at least some options have Greeks
        options_with_greeks = sum(
            1
            for opt in option_chain
            if opt.get("greeks") and opt["greeks"].get("delta") is not None
        )
        if options_with_greeks == 0 and len(option_chain) > 0:
            issues.append(f"{symbol}: No options have valid Greeks data")

    if issues:
        print("\n" + "⚠" * 60)
        print("WARNING: Snapshot incomplete - may not be suitable for testing")
        print("⚠" * 60)
        for issue in issues:
            print(f"  ⚠ {issue}")
        print()
        return False

    print("✓ Snapshot completeness validation passed")
    return True


def capture_snapshot(scenario_name: str = "normal") -> Dict[str, Any]:
    """Capture market data snapshot.

    Args:
        scenario_name: Scenario identifier (normal, high_vix, tight_spreads, etc.)

    Returns:
        Dictionary containing all captured data
    """
    print(f"\n{'=' * 60}")
    print(f"IBKR Snapshot Capture - Scenario: {scenario_name}")
    print(f"{'=' * 60}\n")

    # Connect to IBKR Gateway (paper trading port 4002)
    app = SnapshotCapture()
    print("Connecting to IBKR Gateway on port 4002 (paper trading)...")
    app.connect("127.0.0.1", 4002, clientId=1)

    # Start message processing thread
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    # Wait for connection
    timeout = 10
    start_time = time.time()
    while app.next_order_id is None:
        if time.time() - start_time > timeout:
            print("✗ Connection timeout")
            sys.exit(1)
        time.sleep(0.1)

    print("✓ Connected successfully\n")

    # CRITICAL SAFETY: Verify account type is PAPER
    print("=" * 60)
    print("SAFETY CHECK: Verifying account type...")
    print("=" * 60)
    app.reqAccountSummary(9999, "All", "AccountType")

    # Wait for account type verification
    timeout_check = 5
    start_time = time.time()
    while app.account_type is None:
        if time.time() - start_time > timeout_check:
            print("✗ Account type verification timeout")
            app.disconnect()
            sys.exit(1)
        time.sleep(0.1)

    if app.account_type != "PAPER":
        print(f"✗ SAFETY FAILURE: Account type '{app.account_type}' is not PAPER")
        app.disconnect()
        sys.exit(1)

    print("✓ VERIFIED: Paper trading account confirmed")
    print("✓ Safe to proceed with snapshot capture\n")
    app.cancelAccountSummary(9999)

    snapshot_data: Dict[str, Any] = {
        "scenario": scenario_name,
        "timestamp": datetime.now().isoformat(),
        "symbols": {},
    }

    symbols = ["SPY", "QQQ", "IWM"]

    for symbol in symbols:
        print(f"\nCapturing data for {symbol}...")

        # 1. Get current stock price
        stock_contract = create_stock_contract(symbol)
        req_id = app.current_request_id
        app.current_request_id += 1

        print(f"  Requesting market data (reqId {req_id})...")
        app.reqMktData(req_id, stock_contract, "", True, False, [])
        time.sleep(2)  # Wait for data

        stock_price = app.market_data.get(req_id, {}).get("last", 0)
        if stock_price == 0:
            print(f"  ⚠ Warning: No price data for {symbol}, using fallback")
            stock_price = {"SPY": 580, "QQQ": 500, "IWM": 220}.get(symbol, 100)

        print(f"  ✓ Current price: ${stock_price:.2f}")

        # Cancel market data
        app.cancelMktData(req_id)

        # 2. Get historical data (1-hour bars, last 5 days RTH only)
        req_id = app.current_request_id
        app.current_request_id += 1

        print(f"  Requesting historical data (reqId {req_id})...")
        app.reqHistoricalData(
            req_id,
            stock_contract,
            "",  # End date (now)
            "5 D",  # Duration
            "1 hour",  # Bar size
            "TRADES",  # What to show
            1,  # RTH only
            1,  # Date format (1 = string)
            False,  # Keep up to date
            [],  # Chart options
        )
        time.sleep(3)  # Wait for data

        historical_data = app.historical_bars.get(req_id, [])
        print(f"  ✓ Retrieved {len(historical_data)} historical bars")

        # 3. Get option chain for ATM strikes
        atm_strike = get_atm_strike(stock_price, symbol)
        strikes = [
            atm_strike - 2,
            atm_strike - 1,
            atm_strike,
            atm_strike + 1,
            atm_strike + 2,
        ]

        # Get expiries (2, 7 DTE approximations)
        expiries = get_expiry_dates([2, 7])

        option_data = []

        for expiry in expiries:
            for strike in strikes:
                for right in ["C", "P"]:
                    option_contract = create_option_contract(symbol, right, strike, expiry)

                    # Request market data
                    req_id = app.current_request_id
                    app.current_request_id += 1

                    app.reqMktData(req_id, option_contract, "", True, False, [])
                    time.sleep(0.5)  # Rate limit

                    # Get data
                    market_data = app.market_data.get(req_id, {})
                    greeks = app.greeks_data.get(req_id, {})

                    if market_data:
                        option_data.append(
                            {
                                "contract": {
                                    "symbol": symbol,
                                    "right": right,
                                    "strike": strike,
                                    "expiry": expiry,
                                },
                                "marketData": market_data,
                                "greeks": greeks,
                            }
                        )

                    # Cancel market data
                    app.cancelMktData(req_id)

        print(f"  ✓ Captured {len(option_data)} option contracts")

        # Store symbol data
        snapshot_data["symbols"][symbol] = {
            "currentPrice": stock_price,
            "historicalBars": historical_data,
            "optionChain": option_data,
        }

    # Disconnect
    app.disconnect()
    print("\n✓ Snapshot capture complete\n")

    # Validate snapshot completeness
    validate_snapshot_completeness(snapshot_data)

    return snapshot_data


def save_snapshot(data: Dict[str, Any], scenario_name: str):
    """Save snapshot data to JSON file.

    Args:
        data: Snapshot data dictionary
        scenario_name: Scenario identifier for filename
    """
    # Create output directory
    output_dir = Path("tests/fixtures/ibkr_snapshots")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{scenario_name}_{timestamp}.json"
    filepath = output_dir / filename

    # Save to file
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Snapshot saved to: {filepath}")
    print(f"  File size: {filepath.stat().st_size / 1024:.1f} KB")

    # Also create a "latest" symlink-equivalent for this scenario
    latest_path = output_dir / f"snapshot_{scenario_name}_latest.json"
    with open(latest_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Latest snapshot: {latest_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Capture IBKR market data snapshots for test fixtures"
    )
    parser.add_argument(
        "--scenario",
        default="normal",
        help="Scenario name (normal, high_vix, tight_spreads, etc.)",
    )

    args = parser.parse_args()

    # Safety check - verify we're using paper trading port
    print("\n" + "!" * 60)
    print("SAFETY CHECK: This script connects to port 4002 (paper trading)")
    print("Ensure IBKR Gateway is running in PAPER TRADING mode")
    print("!" * 60 + "\n")

    response = input("Continue with snapshot capture? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Aborted.")
        sys.exit(0)

    try:
        # Capture snapshot
        data = capture_snapshot(args.scenario)

        # Save snapshot
        save_snapshot(data, args.scenario)

        print("\n" + "=" * 60)
        print("SNAPSHOT CAPTURE COMPLETE")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
