#!/usr/bin/env python3
# mypy: ignore-errors
"""
IBKR Snapshot Capture Script
Charter & Stone Capital - Test Data Collection

Purpose: Connect to IBKR Gateway during market hours and capture real market data
for use as deterministic test fixtures.

Usage:
    poetry run python scripts/capture_ibkr_snapshot.py --symbols SPY QQQ IWM

Requirements:
    - IBKR Gateway must be running (localhost:4002)
    - Market hours: 9:30 AM - 4:00 PM ET
    - Paper trading account

Author: @Systems_Architect
Date: 2026-02-06
"""

import argparse
import json
import logging
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ib_insync import IB, Index, Option, Stock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result):
        return None
    return result


def _safe_int(value) -> int:
    if value is None:
        return 0
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0
    if math.isnan(result):
        return 0
    return int(result)


class IBKRSnapshotCapture:
    """Capture market data snapshots from IBKR Gateway for test fixtures."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4002,
        client_id: int = 999,  # High ID to avoid conflicts
        timeout: int = 30,
    ):
        """
        Initialize snapshot capture client.

        Args:
            host: Gateway hostname
            port: Gateway port (4002 for paper trading)
            client_id: Unique client ID
            timeout: Request timeout in seconds
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self.connected = False

    def connect(self) -> bool:
        """
        Connect to IBKR Gateway.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(
                f"Connecting to IBKR Gateway at {self.host}:{self.port} "
                f"(clientId={self.client_id})..."
            )
            self.ib.connect(
                self.host,
                self.port,
                clientId=self.client_id,
                timeout=self.timeout,
            )
            self.connected = True
            logger.info("✅ Connected to IBKR Gateway successfully")
            # 1 = live, 2 = frozen, 3 = delayed, 4 = delayed frozen
            self.ib.reqMarketDataType(3)
            logger.info("📊 Using delayed market data (15-min delayed, free)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to IBKR Gateway: {e}")
            return False

    def disconnect(self):
        """Disconnect from IBKR Gateway."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR Gateway")

    def _wait_for(self, predicate, timeout: int) -> bool:
        """Wait for a predicate to become true within timeout seconds."""
        start = datetime.now(timezone.utc)
        while (datetime.now(timezone.utc) - start).total_seconds() < timeout:
            if predicate():
                return True
            self.ib.sleep(0.2)
        return False

    def get_vix_level(self) -> Optional[float]:
        """
        Fetch current VIX level for regime classification.

        Returns:
            VIX level or None if fetch fails
        """
        try:
            logger.info("Fetching VIX level...")
            vix_contract = Index("VIX", "CBOE")
            self.ib.qualifyContracts(vix_contract)

            # Use snapshot mode to avoid buffer overflow
            ticker = self.ib.reqMktData(vix_contract, snapshot=True)
            if not self._wait_for(lambda: ticker.last or ticker.close, timeout=10):
                raise RuntimeError("Timed out waiting for VIX snapshot")

            vix_level = float(ticker.last or ticker.close or 0)
            logger.info(f"✅ VIX level: {vix_level:.2f}")
            return vix_level
        except Exception as e:
            logger.warning(f"⚠️  Failed to fetch VIX: {e}, assuming 20.0")
            return 20.0  # Default assumption

    def classify_regime(self, vix_level: float) -> str:
        """
        Classify market regime based on VIX level.

        Args:
            vix_level: Current VIX value

        Returns:
            Regime label: complacency, normal, elevated, high_volatility, crisis
        """
        if vix_level > 30:
            return "crisis"
        elif vix_level > 25:
            return "high_volatility"
        elif vix_level > 18:
            return "elevated"
        elif vix_level > 15:
            return "normal"
        else:
            return "complacency"

    def capture_underlying_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Capture underlying stock data.

        Args:
            symbol: Stock symbol (SPY, QQQ, IWM)

        Returns:
            Dictionary with underlying data or None if failed
        """
        try:
            logger.info(f"Fetching underlying data for {symbol}...")
            stock = Stock(symbol, "SMART", "USD")
            self.ib.qualifyContracts(stock)

            # Get current market data (snapshot mode)
            ticker = self.ib.reqMktData(stock, snapshot=True)
            if not self._wait_for(lambda: ticker.last or ticker.close, timeout=20):
                logger.warning(
                    "Market data timeout for %s (type=%s last=%s close=%s bid=%s ask=%s)",
                    symbol,
                    getattr(ticker, "marketDataType", None),
                    ticker.last,
                    ticker.close,
                    ticker.bid,
                    ticker.ask,
                )
                raise RuntimeError("Timed out waiting for underlying snapshot")

            logger.info(
                "Market data for %s (type=%s last=%s close=%s bid=%s ask=%s)",
                symbol,
                getattr(ticker, "marketDataType", None),
                ticker.last,
                ticker.close,
                ticker.bid,
                ticker.ask,
            )

            underlying_price = _safe_float(ticker.last) or _safe_float(ticker.close)
            if not underlying_price:
                logger.error(f"❌ Failed to get valid price for {symbol}")
                return None

            logger.info(f"✅ {symbol} price: ${underlying_price:.2f}")
            return {
                "symbol": symbol,
                "price": underlying_price,
                "bid": _safe_float(ticker.bid),
                "ask": _safe_float(ticker.ask),
                "last": _safe_float(ticker.last),
                "volume": _safe_int(ticker.volume),
            }
        except Exception as e:
            logger.error(f"❌ Failed to capture underlying data for {symbol}: {e}")
            return None

    def capture_option_chain(
        self,
        symbol: str,
        underlying_price: float,
        strikes_count: int = 5,
        expiries_dte: List[int] = [2, 5, 7],
    ) -> List[Dict[str, Any]]:
        """
        Capture option chain data around ATM.

        Args:
            symbol: Underlying symbol
            underlying_price: Current stock price
            strikes_count: Number of strikes to capture (centered on ATM)
            expiries_dte: List of DTE values to capture

        Returns:
            List of option contract data dictionaries
        """
        options_data = []

        try:
            logger.info(
                f"Capturing option chain for {symbol} "
                f"({strikes_count} strikes, DTE: {expiries_dte})..."
            )

            # Find strikes around ATM
            strike_interval = 5 if symbol == "SPY" else (5 if symbol == "QQQ" else 1)
            atm_strike = round(underlying_price / strike_interval) * strike_interval

            strikes_offset = strikes_count // 2
            strikes = [
                atm_strike + (i - strikes_offset) * strike_interval for i in range(strikes_count)
            ]

            # Get expiry dates (approximate DTE)
            today = datetime.now()
            expiries = []
            for dte in expiries_dte:
                # Simplified: just add days (real impl would check trading calendar)
                target_date = today + timedelta(days=dte)
                expiry_str = target_date.strftime("%Y%m%d")
                expiries.append(expiry_str)

            # Request option contracts
            for expiry in expiries:
                for strike in strikes:
                    for right in ["C", "P"]:
                        option = Option(symbol, expiry, strike, right, "SMART")

                        try:
                            # Qualify contract
                            qualified = self.ib.qualifyContracts(option)
                            if not qualified:
                                logger.debug(
                                    f"⚠️  Could not qualify {symbol} {expiry} " f"{strike}{right}"
                                )
                                continue

                            option = qualified[0]

                            # Get market data (snapshot mode - CRITICAL for buffer mgmt)
                            ticker = self.ib.reqMktData(option, snapshot=True)
                            if not self._wait_for(lambda: ticker.last or ticker.close, timeout=5):
                                logger.debug(
                                    f"  ⚠️  Timeout waiting for {symbol} {expiry} "
                                    f"{strike}{right}"
                                )
                                continue

                            # Extract Greeks if available
                            greeks = {}
                            if ticker.modelGreeks:
                                greeks = {
                                    "delta": ticker.modelGreeks.delta,
                                    "gamma": ticker.modelGreeks.gamma,
                                    "theta": ticker.modelGreeks.theta,
                                    "vega": ticker.modelGreeks.vega,
                                    "implied_vol": ticker.modelGreeks.impliedVol,
                                }

                            options_data.append(
                                {
                                    "contract": {
                                        "symbol": symbol,
                                        "expiry": expiry,
                                        "strike": strike,
                                        "right": right,
                                        "exchange": "SMART",
                                    },
                                    "market_data": {
                                        "last": _safe_float(ticker.last),
                                        "bid": _safe_float(ticker.bid),
                                        "ask": _safe_float(ticker.ask),
                                        "bid_size": _safe_int(ticker.bidSize),
                                        "ask_size": _safe_int(ticker.askSize),
                                        "volume": _safe_int(ticker.volume),
                                        "open_interest": _safe_int(ticker.openInterest),
                                    },
                                    "greeks": greeks,
                                }
                            )

                            logger.debug(f"  ✅ Captured {symbol} {expiry} {strike}{right}")

                        except Exception as e:
                            logger.debug(
                                f"  ⚠️  Failed to capture {symbol} {expiry} "
                                f"{strike}{right}: {e}"
                            )
                            continue

            logger.info(f"✅ Captured {len(options_data)} option contracts for {symbol}")
            return options_data

        except Exception as e:
            logger.error(f"❌ Failed to capture option chain for {symbol}: {e}")
            return []

    def capture_historical_bars(
        self, symbol: str, bar_count: int = 60, bar_size: str = "1 min"
    ) -> List[Dict[str, Any]]:
        """
        Capture historical intraday bars.

        Args:
            symbol: Stock symbol
            bar_count: Number of bars to retrieve
            bar_size: Bar size (e.g., "1 min", "5 mins")

        Returns:
            List of OHLCV bar dictionaries
        """
        try:
            logger.info(f"Fetching historical bars for {symbol}...")
            stock = Stock(symbol, "SMART", "USD")
            self.ib.qualifyContracts(stock)

            # Request historical data (RTH only, critical for avoiding timeouts)
            bars = self.ib.reqHistoricalData(
                stock,
                endDateTime="",
                durationStr=f"{bar_count * 60} S",  # Seconds
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=True,  # Regular trading hours only
                formatDate=1,
                timeout=self.timeout,
            )

            historical_data = []
            for bar in bars:
                historical_data.append(
                    {
                        "timestamp": bar.date.isoformat(),
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": int(bar.volume),
                        "vwap": float(bar.average) if bar.average > 0 else None,
                    }
                )

            logger.info(f"✅ Captured {len(historical_data)} bars for {symbol}")
            return historical_data

        except Exception as e:
            logger.error(f"❌ Failed to capture historical bars for {symbol}: {e}")
            return []

    def capture_symbol(
        self,
        symbol: str,
        strikes_count: int = 5,
        expiries_dte: List[int] = [2, 5, 7],
    ) -> Optional[Dict[str, Any]]:
        """
        Capture complete snapshot for one symbol.

        Args:
            symbol: Stock symbol (SPY, QQQ, IWM)
            strikes_count: Number of strikes to capture
            expiries_dte: List of DTE values

        Returns:
            Complete snapshot dictionary or None if failed
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"CAPTURING SNAPSHOT: {symbol}")
        logger.info(f"{'=' * 60}")

        # 1. Capture underlying data
        underlying_data = self.capture_underlying_data(symbol)
        if not underlying_data:
            return None

        underlying_price = underlying_data["price"]

        # 2. Capture option chain
        option_chain = self.capture_option_chain(
            symbol, underlying_price, strikes_count, expiries_dte
        )

        # 3. Capture historical bars
        historical_bars = self.capture_historical_bars(symbol)

        # 4. Get VIX for regime classification
        vix_level = self.get_vix_level()
        regime = self.classify_regime(vix_level)

        # 5. Assemble complete snapshot
        snapshot = {
            "metadata": {
                "capture_script_version": "1.0",
                "capture_timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "underlying_price": underlying_price,
                "vix_level": vix_level,
                "regime": regime,
                "market_session": "RTH",  # TODO: Detect session
                "strikes_captured": strikes_count,
                "expiries_captured": len(expiries_dte),
                "contracts_total": len(option_chain),
            },
            "underlying": underlying_data,
            "option_chain": option_chain,
            "historical_bars": historical_bars,
        }

        logger.info(f"✅ Complete snapshot captured for {symbol}")
        return snapshot

    def save_snapshot(self, snapshot: Dict[str, Any], output_dir: Path):
        """
        Save snapshot to JSON file.

        Args:
            snapshot: Snapshot data dictionary
            output_dir: Output directory path
        """
        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        metadata = snapshot["metadata"]
        timestamp = datetime.fromisoformat(metadata["capture_timestamp"])
        filename = (
            f"{metadata['symbol'].lower()}_"
            f"{timestamp.strftime('%Y%m%d_%H%M')}_"
            f"{metadata['regime']}_vix.json"
        )

        filepath = output_dir / filename

        # Save JSON
        with open(filepath, "w") as f:
            json.dump(snapshot, f, indent=2)

        logger.info(f"💾 Snapshot saved to: {filepath}")


def main():
    """Main entry point for snapshot capture script."""
    parser = argparse.ArgumentParser(
        description="Capture IBKR market data snapshots for test fixtures"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["SPY", "QQQ", "IWM"],
        help="Symbols to capture (default: SPY QQQ IWM)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/fixtures/ibkr_snapshots"),
        help="Output directory (default: tests/fixtures/ibkr_snapshots)",
    )
    parser.add_argument(
        "--strikes",
        type=int,
        default=5,
        help="Number of strikes to capture around ATM (default: 5)",
    )
    parser.add_argument(
        "--expiries",
        type=int,
        nargs="+",
        default=[2, 5, 7],
        help="DTE values to capture (default: 2 5 7)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Gateway host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=4002, help="Gateway port (default: 4002)")
    parser.add_argument("--client-id", type=int, default=999, help="Client ID (default: 999)")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("IBKR SNAPSHOT CAPTURE UTILITY")
    logger.info("Charter & Stone Capital - Test Data Collection")
    logger.info("=" * 60)
    logger.info(f"Symbols: {args.symbols}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Strikes: {args.strikes}")
    logger.info(f"Expiries (DTE): {args.expiries}")
    logger.info("=" * 60)

    # Initialize capture client
    capturer = IBKRSnapshotCapture(host=args.host, port=args.port, client_id=args.client_id)

    # Connect to Gateway
    if not capturer.connect():
        logger.error("❌ Cannot proceed without Gateway connection")
        sys.exit(1)

    try:
        # Capture each symbol
        for symbol in args.symbols:
            snapshot = capturer.capture_symbol(
                symbol, strikes_count=args.strikes, expiries_dte=args.expiries
            )

            if snapshot:
                capturer.save_snapshot(snapshot, args.output)
            else:
                logger.warning(f"⚠️  Failed to capture complete snapshot for {symbol}")

    finally:
        # Always disconnect
        capturer.disconnect()

    logger.info("\n" + "=" * 60)
    logger.info("✅ SNAPSHOT CAPTURE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Output directory: {args.output}")
    logger.info("Next steps: Review captured files and commit to git for test fixtures")


if __name__ == "__main__":
    main()
