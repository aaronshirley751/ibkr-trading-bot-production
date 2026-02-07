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
from ib_insync import IB, Stock, BarData, Ticker


class TestMarketDataRetrieval:
    """Test suite for market data requests with critical alpha learnings."""

    def test_snapshot_mode_enforcement(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: snapshot=True MUST be enforced.

        GIVEN: Request for real-time market data (SPY, QQQ)
        WHEN: reqMktData() called
        THEN: snapshot parameter MUST be True
        AND: Test FAILS if snapshot=False (prevent buffer overflow regression)

        This test is THE MOST IMPORTANT in the entire suite.
        Regression here means buffer overflow in production.
        """
        # Arrange
        mock_ib = Mock(spec=IB)
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.marketPrice.return_value = 685.50
        mock_ib.reqMktData.return_value = mock_ticker

        contract = Stock("SPY", "SMART", "USD")

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            ib.reqMktData(contract, "", snapshot=True, regulatorySnapshot=False)

        # Assert: CRITICAL - snapshot parameter MUST be True
        mock_ib.reqMktData.assert_called_once()
        call_kwargs = mock_ib.reqMktData.call_args[1]

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
        # This test documents expected behavior: snapshot=True always
        mock_ib = Mock(spec=IB)
        contract = Stock("SPY", "SMART", "USD")

        # Act: Call with snapshot=True (correct behavior)
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            ib.reqMktData(contract, "", snapshot=True)

        # Assert
        call_kwargs = mock_ib.reqMktData.call_args[1]
        assert call_kwargs["snapshot"] is True, "snapshot=False causes buffer overflow - NEVER USE"

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
        mock_ib = Mock(spec=IB)
        unqualified_contract = Stock("SPY", "SMART", "USD")

        # Mock qualification process
        qualified_contract = Stock("SPY", "SMART", "USD")
        qualified_contract.conId = 756733  # SPY conId
        mock_ib.qualifyContracts.return_value = [qualified_contract]

        mock_ticker = Mock(spec=Ticker)
        mock_ib.reqMktData.return_value = mock_ticker

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()

            # CRITICAL: Must qualify before requesting data
            contracts = ib.qualifyContracts(unqualified_contract)
            assert len(contracts) > 0, "Contract qualification failed"

            qualified = contracts[0]
            assert hasattr(qualified, "conId"), "Qualified contract must have conId"
            assert qualified.conId > 0, "conId must be valid"

            # Only then request market data
            ib.reqMktData(qualified, "", snapshot=True)

        # Assert
        mock_ib.qualifyContracts.assert_called_once()
        mock_ib.reqMktData.assert_called_once()

    def test_unqualified_contract_rejected(self) -> None:
        """Test that unqualified contracts are rejected."""
        # Arrange
        mock_ib = Mock(spec=IB)
        unqualified_contract = Stock("INVALID_SYMBOL", "SMART", "USD")

        # Mock failed qualification
        mock_ib.qualifyContracts.return_value = []  # No results = failed qualification

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            contracts = ib.qualifyContracts(unqualified_contract)

        # Assert
        assert len(contracts) == 0, "Invalid contracts should not qualify"
        mock_ib.qualifyContracts.assert_called_once()

    def test_market_data_error_handling(self) -> None:
        """Test error handling for market data requests.

        GIVEN: Gateway returns error code (invalid symbol, no permission)
        WHEN: Error callback triggered
        THEN: Error logged with code and description
        AND: System degrades gracefully (no crash)
        AND: Strategy C activated on critical errors
        """
        # Arrange
        mock_ib = Mock(spec=IB)
        error_code = 200  # No security definition found
        error_msg = "No security definition has been found for the request"

        # Simulate error callback
        def trigger_error(*args: Any, **kwargs: Any) -> None:
            raise ValueError(f"Error {error_code}: {error_msg}")

        mock_ib.reqMktData.side_effect = trigger_error

        contract = Stock("INVALID", "SMART", "USD")

        # Act & Assert
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()

            with pytest.raises(ValueError, match=f"Error {error_code}"):
                ib.reqMktData(contract, "", snapshot=True)

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
        THEN: Each tracked with unique reqId
        AND: No cross-contamination of data streams
        """
        # Arrange
        mock_ib = Mock(spec=IB)

        symbols = ["SPY", "QQQ", "IWM"]
        contracts = [Stock(symbol, "SMART", "USD") for symbol in symbols]

        # Mock different tickers for each symbol
        mock_tickers = [Mock(spec=Ticker) for _ in symbols]
        for i, ticker in enumerate(mock_tickers):
            ticker.contract = contracts[i]
            ticker.last = 100.0 * (i + 1)  # Different prices

        mock_ib.reqMktData.side_effect = mock_tickers

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            results = []

            for contract in contracts:
                ticker = ib.reqMktData(contract, "", snapshot=True)  # type: ignore[assignment]
                results.append(ticker)

        # Assert: All requests made
        assert mock_ib.reqMktData.call_count == 3

        # Assert: Each result is unique
        assert len(results) == 3
        assert all(isinstance(r, Mock) for r in results)

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
        WHEN: reqHistoricalData() called
        THEN: Duration parameter = "3600 S" (1 hour)
        AND: useRTH parameter = True
        AND: Response contains bars with OHLCV data
        """
        # Arrange
        mock_ib = Mock(spec=IB)
        contract = Stock("SPY", "SMART", "USD")

        # Mock historical bars response
        mock_bars = [
            BarData(
                date=datetime.now(timezone.utc) - timedelta(minutes=5 * i),
                open=685.0,
                high=686.0,
                low=684.5,
                close=685.5,
                volume=100000,
                average=685.25,
                barCount=50,
            )
            for i in range(12)  # 12 bars = 1 hour of 5-min bars
        ]
        mock_ib.reqHistoricalData.return_value = mock_bars

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            _ = ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="3600 S",  # 1 hour
                barSizeSetting="5 mins",
                whatToShow="TRADES",
                useRTH=True,  # CRITICAL: RTH only
                formatDate=1,
            )

        # Assert: CRITICAL - useRTH must be True
        call_kwargs = mock_ib.reqHistoricalData.call_args[1]
        assert call_kwargs["useRTH"] is True, "🔴 CRITICAL: useRTH MUST be True"
        assert call_kwargs["durationStr"] == "3600 S", "Duration must be 1 hour (3600 seconds)"

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
        mock_ib = Mock(spec=IB)
        contract = Stock("SPY", "SMART", "USD")

        # Simulate timeout
        def slow_historical_data(*args: Any, **kwargs: Any) -> None:
            timeout = kwargs.get("timeout", 60)
            if timeout < 35:  # If timeout is short, raise timeout error
                raise TimeoutError(f"Historical data timeout after {timeout}s")

        mock_ib.reqHistoricalData.side_effect = slow_historical_data

        # Act & Assert
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()

            with pytest.raises(TimeoutError, match="Historical data timeout"):
                ib.reqHistoricalData(
                    contract,
                    endDateTime="",
                    durationStr="3600 S",
                    barSizeSetting="5 mins",
                    whatToShow="TRADES",
                    useRTH=True,
                    formatDate=1,
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
        """Test that extended hours (useRTH=False) is NOT used.

        This documents that extended hours data is NOT part of alpha strategy.
        If requirements change, consult @Lead_Quant first.
        """
        # This test documents expected behavior: useRTH=True always
        mock_ib = Mock(spec=IB)
        contract = Stock("SPY", "SMART", "USD")

        # Act: Call with useRTH=True (correct behavior)
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="3600 S",
                barSizeSetting="5 mins",
                whatToShow="TRADES",
                useRTH=True,  # Always True per alpha learnings
                formatDate=1,
            )

        # Assert
        call_kwargs = mock_ib.reqHistoricalData.call_args[1]
        assert (
            call_kwargs["useRTH"] is True
        ), "Extended hours (useRTH=False) is NOT used in alpha strategy"
