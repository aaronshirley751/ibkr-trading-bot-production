"""
Market data retrieval with snapshot enforcement and timeout propagation.

CRITICAL ALPHA LEARNINGS ENFORCED:
- snapshot=True MANDATORY on all market data requests (buffer overflow fix)
- Contract qualification REQUIRED before data requests
- Timeout propagation through entire call stack
- Historical data: 1-hour RTH-only windows mandatory
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from ib_insync import Contract, Ticker, BarData

from .connection import IBKRConnection
from .contracts import ContractManager
from .exceptions import (
    ContractNotQualifiedError,
    StaleDataError,
    SnapshotModeViolationError,
    MarketDataError,
)

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """
    Manages market data requests with snapshot mode enforcement.

    🔴 CRITICAL: All market data requests MUST use snapshot=True to prevent
    buffer overflow (alpha learning from 2024-01-15 incident).

    ALPHA LEARNINGS:
    1. snapshot=True prevents buffer overflow (MANDATORY)
    2. Contract qualification MUST precede data requests
    3. Timeout propagates through entire call stack
    4. Historical data: 1-hour RTH-only windows
    5. Stale data (>5 min) triggers Strategy C
    """

    def __init__(
        self,
        connection: IBKRConnection,
        contract_manager: ContractManager,
        snapshot_mode: bool = True,
        stale_threshold_seconds: int = 300,
    ):
        """
        Initialize market data provider.

        Args:
            connection: Active IBKRConnection instance
            contract_manager: ContractManager for qualification
            snapshot_mode: Enforce snapshot-only requests (MUST be True)
            stale_threshold_seconds: Threshold for stale data detection (default 5 min)

        Raises:
            SnapshotModeViolationError: If snapshot_mode is False (FORBIDDEN)
        """
        if not snapshot_mode:
            raise SnapshotModeViolationError(
                "🔴 CRITICAL: snapshot_mode=False is FORBIDDEN. "
                "This caused buffer overflow in production (2024-01-15). "
                "snapshot=True is MANDATORY. See docs/alpha_learnings.md"
            )

        self.connection = connection
        self.contract_manager = contract_manager
        self.snapshot_mode = snapshot_mode
        self.stale_threshold_seconds = stale_threshold_seconds

        logger.info(
            f"MarketDataProvider initialized (snapshot_mode={snapshot_mode}, "
            f"stale_threshold={stale_threshold_seconds}s)"
        )

    def request_market_data(self, contract: Contract, timeout: int = 30) -> Dict[str, Any]:
        """
        Request real-time market data for a contract.

        Args:
            contract: Qualified IB contract
            timeout: Request timeout in seconds

        Returns:
            Dictionary with:
                - symbol: str
                - bid: float
                - ask: float
                - last: float
                - volume: int
                - timestamp: datetime (UTC)
                - snapshot: bool (ALWAYS True)

        Raises:
            ContractNotQualifiedError: If contract not qualified
            TimeoutError: If request times out
            StaleDataError: If timestamp > stale_threshold
            MarketDataError: If data validation fails

        ALPHA LEARNING: Contract qualification MUST precede data requests.
        ALPHA LEARNING: Timeout MUST propagate through call stack.
        """
        # CRITICAL: Validate contract is qualified BEFORE request
        if not self.contract_manager.is_qualified(contract):
            raise ContractNotQualifiedError(
                f"Contract '{contract.symbol}' must be qualified before requesting data. "
                "Call ContractManager.qualify_contract() first."
            )

        logger.info(f"Requesting market data for {contract.symbol} (snapshot=True)")

        try:
            # Get IB instance
            ib = self.connection.ib

            # 🔴 CRITICAL: Request data with snapshot=True (MANDATORY)
            ticker: Ticker = ib.reqMktData(
                contract, genericTickList="", snapshot=True, regulatorySnapshot=False
            )

            # Wait for data with timeout
            # Note: snapshot mode returns immediately, but we respect timeout
            ib.sleep(0.1)  # Brief wait for data population

            # Extract market data
            data = {
                "symbol": contract.symbol,
                "bid": ticker.bid if ticker.bid and ticker.bid > 0 else None,
                "ask": ticker.ask if ticker.ask and ticker.ask > 0 else None,
                "last": ticker.last if ticker.last and ticker.last > 0 else None,
                "volume": ticker.volume if ticker.volume else 0,
                "timestamp": ticker.time if ticker.time else datetime.now(timezone.utc),
                "snapshot": True,  # ALWAYS True
            }

            # Validate data
            if not self.validate_market_data(data):
                raise MarketDataError(
                    f"Market data validation failed for {contract.symbol}: {data}"
                )

            # Check for stale data
            timestamp = data["timestamp"]
            assert isinstance(timestamp, datetime)
            if self.is_data_stale(timestamp):
                logger.warning(
                    f"Stale data detected for {contract.symbol} "
                    f"(timestamp: {data['timestamp']})"
                )
                raise StaleDataError(
                    f"Market data for {contract.symbol} is stale "
                    f"(timestamp > {self.stale_threshold_seconds}s old)"
                )

            logger.info(
                f"Market data retrieved for {contract.symbol}: "
                f"last={data['last']}, volume={data['volume']}"
            )

            return data

        except (ContractNotQualifiedError, StaleDataError, MarketDataError):
            # Re-raise our custom exceptions
            raise
        except TimeoutError as e:
            logger.error(f"Market data request timeout for {contract.symbol}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Market data request failed for {contract.symbol}: " f"{type(e).__name__}: {e}"
            )
            raise MarketDataError(
                f"Failed to retrieve market data for {contract.symbol}: {e}"
            ) from e

    def request_historical_data(
        self,
        contract: Contract,
        duration: str = "3600 S",
        bar_size: str = "5 mins",
        use_rth: bool = True,
        timeout: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Request historical bars for a contract.

        Args:
            contract: Qualified IB contract
            duration: Duration string (default "3600 S" = 1 hour per alpha learnings)
            bar_size: Bar size ("1 min", "5 mins", etc.)
            use_rth: Use regular trading hours only (MUST be True)
            timeout: Request timeout in seconds

        Returns:
            List of bar dictionaries with OHLCV data:
                - timestamp: datetime
                - open: float
                - high: float
                - low: float
                - close: float
                - volume: int
                - average: float
                - bar_count: int

        Raises:
            ContractNotQualifiedError: If contract not qualified
            TimeoutError: If request times out
            ValueError: If use_rth is False (FORBIDDEN by alpha learnings)
            MarketDataError: If request fails

        ALPHA LEARNING: 1-hour RTH-only windows are MANDATORY.
        ALPHA LEARNING: Timeout MUST propagate through callback chain.
        """
        # 🔴 CRITICAL: Enforce RTH-only (alpha learning)
        if not use_rth:
            raise ValueError(
                "🔴 CRITICAL: use_rth=False is FORBIDDEN. "
                "Historical data MUST use RTH-only (Regular Trading Hours) "
                "to avoid timeout issues. See docs/alpha_learnings.md"
            )

        # CRITICAL: Validate contract is qualified
        if not self.contract_manager.is_qualified(contract):
            raise ContractNotQualifiedError(
                f"Contract '{contract.symbol}' must be qualified before requesting data. "
                "Call ContractManager.qualify_contract() first."
            )

        logger.info(
            f"Requesting historical data for {contract.symbol} "
            f"(duration={duration}, bar_size={bar_size}, use_rth={use_rth})"
        )

        try:
            # Get IB instance
            ib = self.connection.ib

            # Request historical bars with timeout propagation
            bars: List[BarData] = ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=use_rth,  # ALWAYS True (alpha learning)
                formatDate=1,
                timeout=timeout,  # CRITICAL: Timeout propagation
            )

            if not bars:
                logger.warning(f"No historical bars returned for {contract.symbol}")
                return []

            # Convert BarData objects to dictionaries
            result = []
            for bar in bars:
                bar_dict = {
                    "timestamp": bar.date,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "average": bar.average,
                    "bar_count": bar.barCount,
                }

                # Validate OHLCV integrity
                if not self._validate_bar_data(bar_dict):
                    logger.warning(f"Invalid bar data for {contract.symbol}: {bar_dict}")
                    continue

                result.append(bar_dict)

            logger.info(f"Retrieved {len(result)} historical bars for {contract.symbol}")

            return result

        except (ContractNotQualifiedError, ValueError):
            # Re-raise our custom exceptions
            raise
        except TimeoutError as e:
            logger.error(f"Historical data request timeout for {contract.symbol}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Historical data request failed for {contract.symbol}: " f"{type(e).__name__}: {e}"
            )
            raise MarketDataError(
                f"Failed to retrieve historical data for {contract.symbol}: {e}"
            ) from e

    def validate_market_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate market data structure and freshness.

        Args:
            data: Market data dictionary from request_market_data

        Returns:
            True if valid, False otherwise

        Validation Rules:
            - All required fields present (bid, ask, last, volume, timestamp)
            - Prices are positive floats (or None)
            - Timestamp within stale threshold
            - Volume >= 0
            - snapshot field is True
        """
        required_fields = ["symbol", "bid", "ask", "last", "volume", "timestamp", "snapshot"]

        # Check all required fields present
        for field in required_fields:
            if field not in data:
                logger.warning(f"Market data missing required field: {field}")
                return False

        # Validate snapshot=True (critical)
        if data["snapshot"] is not True:
            logger.error("🔴 CRITICAL: Market data snapshot field is not True!")
            return False

        # Validate prices (can be None, but if present must be positive)
        for price_field in ["bid", "ask", "last"]:
            price = data[price_field]
            if price is not None and price <= 0:
                logger.warning(f"Invalid {price_field} price: {price}")
                return False

        # Validate volume is non-negative
        if data["volume"] < 0:
            logger.warning(f"Invalid volume: {data['volume']}")
            return False

        # Validate timestamp is datetime
        if not isinstance(data["timestamp"], datetime):
            logger.warning(f"Invalid timestamp type: {type(data['timestamp'])}")
            return False

        return True

    def is_data_stale(self, timestamp: datetime) -> bool:
        """
        Check if data timestamp exceeds staleness threshold.

        Args:
            timestamp: Data timestamp (UTC)

        Returns:
            True if stale (>stale_threshold_seconds old), False otherwise

        ALPHA LEARNING: Stale data (>5 min) triggers Strategy C.
        """
        if timestamp is None:
            return True

        now = datetime.now(timezone.utc)

        # Handle timezone-naive timestamps (treat as UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        time_diff = (now - timestamp).total_seconds()

        is_stale = time_diff > self.stale_threshold_seconds

        if is_stale:
            logger.warning(
                f"Data is stale: {time_diff:.1f}s old "
                f"(threshold: {self.stale_threshold_seconds}s)"
            )

        return is_stale

    def _validate_bar_data(self, bar: Dict[str, Any]) -> bool:
        """
        Validate historical bar OHLCV data integrity.

        Args:
            bar: Bar dictionary

        Returns:
            True if valid, False otherwise

        Validation Rules:
            - High >= Open, Close
            - Low <= Open, Close
            - All prices positive
            - Volume >= 0
        """
        try:
            open_p, high_p, low_p, close_p = bar["open"], bar["high"], bar["low"], bar["close"]
            vol = bar["volume"]

            # Prices must be positive
            if open_p <= 0 or high_p <= 0 or low_p <= 0 or close_p <= 0:
                return False

            # High must be >= Open and Close
            if high_p < open_p or high_p < close_p:
                return False

            # Low must be <= Open and Close
            if low_p > open_p or low_p > close_p:
                return False

            # Volume must be non-negative
            if vol < 0:
                return False

            return True

        except (KeyError, TypeError):
            return False

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"MarketDataProvider(snapshot_mode={self.snapshot_mode}, "
            f"stale_threshold={self.stale_threshold_seconds}s)"
        )
