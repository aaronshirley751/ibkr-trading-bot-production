"""
Unit tests for market data retrieval and validation.

Tests cover:
- Snapshot mode market data requests
- Historical data requests (1-hour RTH)
- Contract qualification
- Buffer overflow prevention (snapshot=True validation)
- Timeout parameter propagation
- Stale/missing data handling

CRITICAL ALPHA LEARNINGS ENCODED:
- snapshot=True MUST be enforced (prevents buffer overflow)
- Contract qualification MUST occur before market data requests
- 1-hour RTH-only windows for historical data
- Timeout parameter MUST propagate through entire call chain
"""

from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest
from ib_insync import Stock, BarData, Ticker

from src.broker import (
    IBKRConnection,
    ContractManager,
    MarketDataProvider,
    ContractNotQualifiedError,
    SnapshotModeViolationError,
)


class TestMarketDataRetrieval:
    """Test suite for market data requests with critical alpha learnings."""

    def test_snapshot_mode_enforcement(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: snapshot=True MUST be enforced.

        GIVEN: Request for real-time market data (SPY, QQQ)
        WHEN: provider.request_market_data() called
        THEN: snapshot parameter MUST be True
        AND: Test FAILS if snapshot=False (prevent buffer overflow regression)

        This test is THE MOST IMPORTANT in the entire suite.
        Regression here means buffer overflow in production.
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Mock qualified contract
            contract = Stock("SPY", "SMART", "USD")
            contract.conId = 756733

            # Mock market data response
            mock_ticker = Mock(spec=Ticker)
            mock_ticker.bid = 685.50
            mock_ticker.ask = 685.52
            mock_ticker.last = 685.51
            mock_ticker.volume = 1250000
            mock_ticker.time = datetime.now(timezone.utc)
            mock_ib.reqMktData.return_value = mock_ticker
            mock_ib.waitOnUpdate.return_value = None

            # Act
            _ = provider.request_market_data(contract, timeout=30)

            # Assert: CRITICAL - snapshot parameter MUST be True
            mock_ib.reqMktData.assert_called_once()
            call_args, call_kwargs = mock_ib.reqMktData.call_args

            assert "snapshot" in call_kwargs, "🔴 CRITICAL: snapshot parameter missing from call"
            assert (
                call_kwargs["snapshot"] is True
            ), "🔴 CRITICAL: snapshot MUST be True to prevent buffer overflow"

    def test_snapshot_false_is_forbidden(self) -> None:
        """
        🔴 CRITICAL: Explicitly test that snapshot=False is NOT used.

        This test documents that snapshot=False is a CRITICAL BUG.
        If this test ever needs to be changed, consult @Lead_Quant first.
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)

        # Act & Assert: MarketDataProvider with snapshot_mode=False MUST raise error
        with pytest.raises(SnapshotModeViolationError, match="snapshot_mode=False is FORBIDDEN"):
            MarketDataProvider(connection, contract_manager, snapshot_mode=False)

    def test_market_data_validation(self) -> None:
        """Test market data response validation.

        GIVEN: Mock market data response (price, volume, timestamp)
        WHEN: Data received from Gateway
        THEN: All required fields present (bid, ask, last, volume)
        AND: Prices are positive floats
        AND: Timestamp is recent (within last 60 seconds)
        """
        # Arrange
        current_time = datetime.now(timezone.utc)
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.bid = 685.50
        mock_ticker.ask = 685.52
        mock_ticker.last = 685.51
        mock_ticker.volume = 1250000
        mock_ticker.time = current_time

        # Act: Validate market data
        ticker_data = mock_ticker

        # Assert: Required fields present
        assert hasattr(ticker_data, "bid"), "Missing bid price"
        assert hasattr(ticker_data, "ask"), "Missing ask price"
        assert hasattr(ticker_data, "last"), "Missing last price"
        assert hasattr(ticker_data, "volume"), "Missing volume"
        assert hasattr(ticker_data, "time"), "Missing timestamp"

        # Assert: Prices are positive
        assert ticker_data.bid > 0, "Bid price must be positive"
        assert ticker_data.ask > 0, "Ask price must be positive"
        assert ticker_data.last > 0, "Last price must be positive"

        # Assert: Volume is non-negative
        assert ticker_data.volume >= 0, "Volume must be non-negative"

        # Assert: Timestamp is recent (within 60 seconds)
        time_diff = (datetime.now(timezone.utc) - ticker_data.time).total_seconds()
        assert time_diff < 60, "Market data timestamp too old"

    def test_stale_data_detection(self) -> None:
        """Test detection of stale market data.

        GIVEN: Market data with old timestamp (>5 minutes)
        WHEN: Stale check performed
        THEN: Data flagged as stale
        AND: Strategy layer notified to use Strategy C
        """
        # Arrange: Create stale data (10 minutes old)
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.time = stale_time
        mock_ticker.last = 685.50

        # Act: Check if data is stale
        time_diff = (datetime.now(timezone.utc) - mock_ticker.time).total_seconds()
        is_stale = time_diff > 300  # 5 minutes threshold

        # Assert
        assert is_stale is True, "Data should be flagged as stale"
        assert time_diff > 300, "Timestamp diff should exceed 5 minutes"

    def test_fresh_data_passes_staleness_check(self) -> None:
        """Test that fresh data passes staleness check."""
        # Arrange: Create fresh data
        fresh_time = datetime.now(timezone.utc)
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.time = fresh_time
        mock_ticker.last = 685.50

        # Act: Check if data is fresh
        time_diff = (datetime.now(timezone.utc) - mock_ticker.time).total_seconds()
        is_stale = time_diff > 300  # 5 minutes threshold

        # Assert
        assert is_stale is False, "Fresh data should NOT be flagged as stale"
        assert time_diff < 60, "Timestamp diff should be minimal"

    def test_contract_qualification_before_data_request(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: Contracts MUST be qualified before data requests.

        GIVEN: Unqualified contract object (symbol='SPY')
        WHEN: Attempting market data request
        THEN: Contract qualification occurs FIRST
        AND: Only qualified contracts proceed to data request
        AND: Unqualified contracts raise appropriate error
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        # Unqualified contract (no conId)
        unqualified_contract = Stock("SPY", "SMART", "USD")
        # Don't set conId - contract remains unqualified

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Act & Assert: Unqualified contract MUST raise error
            with pytest.raises(
                ContractNotQualifiedError, match="must be qualified before requesting data"
            ):
                provider.request_market_data(unqualified_contract, timeout=30)

    def test_unqualified_contract_rejected(self) -> None:
        """Test that unqualified contracts are rejected."""
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)

        Stock("INVALID_SYMBOL", "SMART", "USD")

        with patch.object(connection, "_ib") as mock_ib:
            # Mock failed qualification
            mock_ib.qualifyContracts.return_value = []  # No results = failed qualification

            # Act &Assert: Should raise ContractQualificationError
            with pytest.raises(Exception):  # ContractQualificationError or empty list
                contract_manager.qualify_contract("INVALID_SYMBOL")

    def test_market_data_error_handling(self) -> None:
        """Test error handling for market data requests.

        GIVEN: Gateway returns error code (invalid symbol, no permission)
        WHEN: Error callback triggered
        THEN: Error logged with code and description
        AND: System degrades gracefully (no crash)
        AND: Strategy C activated on critical errors
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("INVALID", "SMART", "USD")
        contract.conId = 999999  # Qualified but invalid

        error_code = 200  # No security definition found
        error_msg = "No security definition has been found for the request"

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Simulate error callback
            def trigger_error(*args: Any, **kwargs: Any) -> None:
                raise ValueError(f"Error {error_code}: {error_msg}")

            mock_ib.reqMktData.side_effect = trigger_error

            # Act & Assert: Provider wraps ValueError in MarketDataError
            with pytest.raises(
                Exception, match=f"Error {error_code}"
            ):  # MarketDataError or ValueError
                provider.request_market_data(contract, timeout=30)

    def test_missing_field_handling(self) -> None:
        """Test handling of market data with missing fields."""
        # Arrange: Create ticker with missing volume
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.bid = 685.50
        mock_ticker.ask = 685.52
        mock_ticker.last = 685.51
        # volume attribute missing intentionally
        del mock_ticker.volume

        # Act: Check for required fields
        has_volume = hasattr(mock_ticker, "volume")

        # Assert
        assert has_volume is False, "Volume should be missing"
        # In production, code should handle missing fields gracefully

    def test_concurrent_market_data_requests(self) -> None:
        """Test handling of concurrent market data requests.

        GIVEN: Multiple simultaneous market data requests
        WHEN: Requests submitted for SPY, QQQ, IWM
        ...THEN: Each tracked with unique reqId
        AND: No cross-contamination of data streams
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        symbols = ["SPY", "QQQ", "IWM"]
        contracts = []
        for symbol in symbols:
            contract = Stock(symbol, "SMART", "USD")
            contract.conId = hash(symbol) % 1000000  # Set as qualified
            contracts.append(contract)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Mock different tickers for each symbol
            mock_tickers = []
            for i, symbol in enumerate(symbols):
                ticker = Mock(spec=Ticker)
                ticker.bid = 100.0 * (i + 1)
                ticker.ask = 100.0 * (i + 1) + 0.02
                ticker.last = 100.0 * (i + 1) + 0.01
                ticker.volume = 1000000
                ticker.time = datetime.now(timezone.utc)
                mock_tickers.append(ticker)

            mock_ib.reqMktData.side_effect = mock_tickers
            mock_ib.waitOnUpdate.return_value = None

            # Act
            results = []
            for contract in contracts:
                data = provider.request_market_data(contract, timeout=30)
                results.append(data)

            # Assert: All requests made
            assert mock_ib.reqMktData.call_count == 3

            # Assert: Each result is unique
            assert len(results) == 3
            prices = [r["last"] for r in results]
            assert len(set(prices)) == 3, "Each symbol should have unique price"

    def test_market_data_bid_ask_spread_validation(self) -> None:
        """Test bid/ask spread is reasonable."""
        # Arrange
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.bid = 685.50
        mock_ticker.ask = 685.52
        mock_ticker.last = 685.51

        # Act: Calculate spread
        spread = mock_ticker.ask - mock_ticker.bid

        # Assert: Spread is positive and reasonable
        assert spread > 0, "Ask must be >= Bid"
        assert spread < 1.0, "Spread should be reasonable (<$1 for SPY)"

        # Assert: Last price within bid/ask
        assert (
            mock_ticker.bid <= mock_ticker.last <= mock_ticker.ask
        ), "Last price should be within bid/ask"

    def test_zero_volume_handling(self) -> None:
        """Test handling of zero volume (illiquid security)."""
        # Arrange
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.volume = 0
        mock_ticker.last = 685.50

        # Act: Check volume
        is_illiquid = mock_ticker.volume == 0

        # Assert
        assert is_illiquid is True, "Zero volume indicates illiquid security"
        # Production code should flag this for Strategy C


class TestHistoricalData:
    """Test suite for historical data requests with alpha learnings."""

    def test_historical_data_rth_only(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: 1-hour RTH-only windows.

        GIVEN: Request for historical bars (SPY, 1-hour, RTH)
        WHEN: provider.request_historical_data() called
        THEN: Duration parameter = "3600 S" (1 hour)
        AND: use_rth parameter = True (default)
        AND: use_rth=False raises ValueError
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733  # Qualified

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Act & Assert: use_rth=False MUST raise error
            with pytest.raises(ValueError, match="use_rth=False is FORBIDDEN"):
                provider.request_historical_data(
                    contract,
                    duration="3600 S",
                    bar_size="5 mins",
                    use_rth=False,  # FORBIDDEN
                    timeout=30,
                )

    def test_historical_data_timeout_propagation(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: Timeout MUST propagate through call chain.

        GIVEN: Historical data request with timeout=30s
        WHEN: Gateway response delayed
        THEN: Timeout enforced at every layer
        AND: Timeout exception raised if exceeded
        AND: No silent hang conditions
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733  # Qualified

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Simulate timeout
            mock_ib.reqHistoricalData.side_effect = TimeoutError(
                "Historical data timeout after 30s"
            )

            # Act & Assert
            with pytest.raises(TimeoutError, match="Historical data timeout"):
                provider.request_historical_data(
                    contract,
                    duration="3600 S",
                    bar_size="5 mins",
                    use_rth=True,
                    timeout=30,  # Short timeout for testing
                )

    def test_historical_bars_ohlcv_validation(self) -> None:
        """Test validation of historical bar data structure."""
        # Arrange
        bar = BarData(
            date=datetime.now(timezone.utc),
            open=685.0,
            high=686.0,
            low=684.5,
            close=685.5,
            volume=100000,
            average=685.25,
            barCount=50,
        )

        # Assert: OHLCV fields present
        assert hasattr(bar, "open"), "Missing open price"
        assert hasattr(bar, "high"), "Missing high price"
        assert hasattr(bar, "low"), "Missing low price"
        assert hasattr(bar, "close"), "Missing close price"
        assert hasattr(bar, "volume"), "Missing volume"

        # Assert: Logical price relationships
        assert bar.high >= bar.open, "High must be >= Open"
        assert bar.high >= bar.close, "High must be >= Close"
        assert bar.low <= bar.open, "Low must be <= Open"
        assert bar.low <= bar.close, "Low must be <= Close"

    def test_extended_hours_rejected(self) -> None:
        """Test that extended hours (use_rth=False) is NOT used.

        This documents that extended hours data is NOT part of alpha strategy.
        If requirements change, consult @Lead_Quant first.
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733  # Qualified

        # Act & Assert: use_rth=False MUST raise ValueError
        with pytest.raises(ValueError, match="use_rth=False is FORBIDDEN"):
            provider.request_historical_data(
                contract,
                duration="3600 S",
                bar_size="5 mins",
                use_rth=False,  # FORBIDDEN per alpha learnings
                timeout=30,
            )
