"""
Coverage boost tests for src/broker module.

Targets uncovered lines in connection.py, contracts.py, and market_data.py
to achieve ≥92% coverage threshold.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import pytest
from ib_insync import Stock, Contract, Ticker, BarData

from src.broker import (
    IBKRConnection,
    ContractManager,
    MarketDataProvider,
    ContractNotQualifiedError,
    MarketDataError,
)
from src.broker.exceptions import ContractQualificationError

# =============================================================================
# connection.py coverage gaps
# =============================================================================


class TestConnectionCoverageBoost:
    """Tests targeting uncovered lines in connection.py."""

    def test_connect_creates_ib_when_none(self) -> None:
        """Cover: self._ib = IB() branch when _ib is None."""
        connection = IBKRConnection(max_retries=1, retry_delay_base=0.01)
        # _ib starts as None

        with patch("src.broker.connection.IB") as MockIB:
            mock_ib_instance = MockIB.return_value
            mock_ib_instance.connect.return_value = None
            mock_ib_instance.isConnected.return_value = True

            connection._ib = None  # Ensure it's None
            success = connection.connect()

            assert success is True
            MockIB.assert_called_once()  # IB() was called

    def test_connect_returns_false_when_not_connected(self) -> None:
        """Cover: return False at end of connect() loop when isConnected is False."""
        connection = IBKRConnection(max_retries=2, retry_delay_base=0.01)

        with patch.object(connection, "_ib") as mock_ib:
            # connect() succeeds (no exception) but isConnected returns False
            mock_ib.connect.return_value = None
            mock_ib.isConnected.return_value = False

            result = connection.connect()
            assert result is False

    def test_disconnect_when_already_disconnected(self) -> None:
        """Cover: disconnect else branch (already disconnected)."""
        connection = IBKRConnection()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = False

            # Should not call _ib.disconnect()
            connection.disconnect()
            mock_ib.disconnect.assert_not_called()

    def test_disconnect_when_ib_is_none(self) -> None:
        """Cover: disconnect when _ib is None."""
        connection = IBKRConnection()
        connection._ib = None
        # Should not raise
        connection.disconnect()

    def test_is_connected_updates_heartbeat(self) -> None:
        """Cover: heartbeat update in is_connected() when connected."""
        connection = IBKRConnection()
        connection._last_heartbeat = None

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            result = connection.is_connected()
            assert result is True
            assert connection._last_heartbeat is not None

    def test_is_connected_when_ib_is_none(self) -> None:
        """Cover: is_connected returns False when _ib is None."""
        connection = IBKRConnection()
        connection._ib = None
        assert connection.is_connected() is False

    def test_reconnect_disconnects_if_still_connected(self) -> None:
        """Cover: reconnect() disconnects first if still connected."""
        connection = IBKRConnection(max_retries=1, retry_delay_base=0.01)

        with patch.object(connection, "_ib") as mock_ib:
            # First isConnected call (in reconnect guard): True → disconnect
            # After disconnect, connect() calls isConnected: True → success
            mock_ib.isConnected.return_value = True
            mock_ib.connect.return_value = None
            mock_ib.disconnect.return_value = None

            success = connection.reconnect()
            assert success is True
            assert connection._reconnect_count == 1
            mock_ib.disconnect.assert_called_once()

    def test_reconnect_failure_returns_false(self) -> None:
        """Cover: reconnect returns False on connect failure."""
        connection = IBKRConnection(max_retries=1, retry_delay_base=0.01)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = False
            mock_ib.connect.side_effect = ConnectionRefusedError("fail")

            success = connection.reconnect()
            assert success is False

    def test_connection_metrics_connected(self) -> None:
        """Cover: connection_metrics property when connected."""
        connection = IBKRConnection(client_id=42)
        connection._connection_start_time = datetime.now(timezone.utc) - timedelta(seconds=60)
        connection._reconnect_count = 2

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            metrics = connection.connection_metrics
            assert metrics["connected"] is True
            assert metrics["uptime_seconds"] is not None
            uptime = metrics["uptime_seconds"]
            assert isinstance(uptime, (int, float))
            assert uptime >= 59  # ~60 seconds
            assert metrics["reconnect_count"] == 2
            assert metrics["client_id"] == 42
            assert metrics["host"] == "localhost"
            assert metrics["port"] == 4002

    def test_connection_metrics_disconnected(self) -> None:
        """Cover: connection_metrics when disconnected."""
        connection = IBKRConnection()
        connection._ib = None

        metrics = connection.connection_metrics
        assert metrics["connected"] is False
        assert metrics["uptime_seconds"] is None

    def test_ib_property_raises_when_not_connected(self) -> None:
        """Cover: ib property RuntimeError when not connected."""
        connection = IBKRConnection()
        connection._ib = None

        with pytest.raises(RuntimeError, match="Not connected to Gateway"):
            _ = connection.ib

    def test_ib_property_raises_when_disconnected(self) -> None:
        """Cover: ib property RuntimeError when _ib exists but not connected."""
        connection = IBKRConnection()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = False

            with pytest.raises(RuntimeError, match="Not connected"):
                _ = connection.ib

    def test_context_manager(self) -> None:
        """Cover: __enter__ and __exit__ methods."""
        connection = IBKRConnection(max_retries=1, retry_delay_base=0.01)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.connect.return_value = None
            mock_ib.isConnected.return_value = True
            mock_ib.disconnect.return_value = None

            with connection as conn:
                assert conn is connection
                mock_ib.connect.assert_called_once()

            # __exit__ should call disconnect
            mock_ib.disconnect.assert_called_once()

    def test_repr(self) -> None:
        """Cover: __repr__ method."""
        connection = IBKRConnection(host="localhost", port=4002, client_id=999)
        connection._ib = None

        repr_str = repr(connection)
        assert "IBKRConnection" in repr_str
        assert "999" in repr_str
        assert "disconnected" in repr_str

    def test_repr_connected(self) -> None:
        """Cover: __repr__ when connected."""
        connection = IBKRConnection(client_id=42)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            repr_str = repr(connection)
            assert "connected" in repr_str


# =============================================================================
# contracts.py coverage gaps
# =============================================================================


class TestContractsCoverageBoost:
    """Tests targeting uncovered lines in contracts.py."""

    def test_qualify_non_stk_contract(self) -> None:
        """Cover: non-STK contract creation branch (else clause)."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            qualified_contract = Mock(spec=Contract)
            qualified_contract.conId = 12345
            qualified_contract.symbol = "ES"
            mock_ib.qualifyContracts.return_value = [qualified_contract]

            result = manager.qualify_contract("ES", sec_type="FUT", exchange="CME")
            assert result.conId == 12345

    def test_qualify_empty_result(self) -> None:
        """Cover: qualifyContracts returns empty list."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.qualifyContracts.return_value = []

            with pytest.raises(ContractQualificationError, match="No contracts found"):
                manager.qualify_contract("FAKE")

    def test_qualify_invalid_conid(self) -> None:
        """Cover: qualified contract with conId <= 0."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            bad_contract = Mock(spec=Contract)
            bad_contract.conId = 0  # Invalid
            mock_ib.qualifyContracts.return_value = [bad_contract]

            with pytest.raises(ContractQualificationError, match="no conId assigned"):
                manager.qualify_contract("BAD")

    def test_qualify_timeout_error(self) -> None:
        """Cover: TimeoutError re-raise in qualify_contract."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.qualifyContracts.side_effect = TimeoutError("timeout")

            with pytest.raises(TimeoutError, match="timeout"):
                manager.qualify_contract("SPY")

    def test_qualify_generic_exception_wrapping(self) -> None:
        """Cover: generic exception wrapping in ContractQualificationError."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.qualifyContracts.side_effect = RuntimeError("gateway error")

            with pytest.raises(ContractQualificationError, match="Failed to qualify"):
                manager.qualify_contract("SPY")

    def test_qualify_uses_cache(self) -> None:
        """Cover: cache hit path in qualify_contract."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        # Pre-populate cache
        cached_contract = Stock("SPY", "SMART", "USD")
        cached_contract.conId = 756733
        manager._qualified_cache["SPY_STK_SMART_USD"] = cached_contract

        result = manager.qualify_contract("SPY")
        assert result.conId == 756733

    def test_is_qualified_none_contract(self) -> None:
        """Cover: is_qualified with None contract."""
        connection = IBKRConnection()
        manager = ContractManager(connection)
        assert manager.is_qualified(None) is False  # type: ignore[arg-type]

    def test_is_qualified_no_conid(self) -> None:
        """Cover: is_qualified with no conId attribute."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        contract = Mock()
        contract.conId = None
        contract.symbol = "SPY"
        assert manager.is_qualified(contract) is False

    def test_is_qualified_valid(self) -> None:
        """Cover: is_qualified with valid contract."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733
        assert manager.is_qualified(contract) is True

    def test_get_contract_details_success(self) -> None:
        """Cover: get_contract_details with qualified contract."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733

        details = manager.get_contract_details(contract)
        assert details["symbol"] == "SPY"
        assert details["conId"] == 756733

    def test_get_contract_details_unqualified(self) -> None:
        """Cover: get_contract_details raises ValueError for unqualified."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        contract = Stock("SPY", "SMART", "USD")
        # conId not set

        with pytest.raises(ValueError, match="must be qualified"):
            manager.get_contract_details(contract)

    def test_clear_cache(self) -> None:
        """Cover: clear_cache method."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        manager._qualified_cache["test"] = Mock()
        assert len(manager._qualified_cache) == 1

        manager.clear_cache()
        assert len(manager._qualified_cache) == 0

    def test_contract_manager_repr(self) -> None:
        """Cover: __repr__ method."""
        connection = IBKRConnection()
        manager = ContractManager(connection)

        repr_str = repr(manager)
        assert "ContractManager" in repr_str
        assert "0" in repr_str


# =============================================================================
# market_data.py coverage gaps
# =============================================================================


class TestMarketDataCoverageBoost:
    """Tests targeting uncovered lines in market_data.py."""

    def _create_provider(self):
        """Helper to create a configured provider."""
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)
        return connection, contract_manager, provider

    def _qualified_contract(self, symbol="SPY"):
        """Helper to create a qualified contract."""
        contract = Stock(symbol, "SMART", "USD")
        contract.conId = 756733
        return contract

    def test_request_market_data_validation_fails(self) -> None:
        """Cover: validate_market_data returns False → MarketDataError."""
        connection, _, provider = self._create_provider()
        contract = self._qualified_contract()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Ticker with invalid timestamp type (not datetime) to trigger validation failure
            mock_ticker = Mock(spec=Ticker)
            mock_ticker.bid = 685.50
            mock_ticker.ask = 685.52
            mock_ticker.last = 685.51
            mock_ticker.volume = 1000000
            mock_ticker.time = "not-a-datetime"  # Truthy but fails isinstance check
            mock_ib.reqMktData.return_value = mock_ticker

            with pytest.raises(MarketDataError, match="validation failed"):
                provider.request_market_data(contract)

    def test_request_market_data_custom_exception_reraise(self) -> None:
        """Cover: ContractNotQualifiedError re-raise in except block."""
        connection, _, provider = self._create_provider()
        contract = Stock("SPY", "SMART", "USD")
        # NOT qualified (no conId)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            with pytest.raises(ContractNotQualifiedError):
                provider.request_market_data(contract)

    def test_request_market_data_timeout_reraise(self) -> None:
        """Cover: TimeoutError re-raise in request_market_data."""
        connection, _, provider = self._create_provider()
        contract = self._qualified_contract()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.reqMktData.side_effect = TimeoutError("timeout")

            with pytest.raises(TimeoutError, match="timeout"):
                provider.request_market_data(contract)

    def test_request_market_data_generic_exception_wrapping(self) -> None:
        """Cover: generic exception wrapped in MarketDataError."""
        connection, _, provider = self._create_provider()
        contract = self._qualified_contract()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.reqMktData.side_effect = RuntimeError("gateway crash")

            with pytest.raises(MarketDataError, match="Failed to retrieve market data"):
                provider.request_market_data(contract)

    def test_request_historical_data_success(self) -> None:
        """Cover: successful historical data path with bar conversion."""
        connection, _, provider = self._create_provider()
        contract = self._qualified_contract()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            base_time = datetime.now(timezone.utc)
            mock_bars = [
                BarData(
                    date=base_time - timedelta(minutes=5 * i),
                    open=100.0 + i,
                    high=101.0 + i,
                    low=99.0 + i,
                    close=100.5 + i,
                    volume=10000,
                    average=100.25,
                    barCount=50,
                )
                for i in range(3)
            ]
            mock_ib.reqHistoricalData.return_value = mock_bars

            result = provider.request_historical_data(
                contract, duration="3600 S", bar_size="5 mins", use_rth=True, timeout=30
            )

            assert len(result) == 3
            assert result[0]["open"] == 100.0
            assert result[0]["volume"] == 10000

    def test_request_historical_data_empty_bars(self) -> None:
        """Cover: empty bars returned → empty list."""
        connection, _, provider = self._create_provider()
        contract = self._qualified_contract()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.reqHistoricalData.return_value = []

            result = provider.request_historical_data(contract, use_rth=True)
            assert result == []

    def test_request_historical_data_invalid_bar_skipped(self) -> None:
        """Cover: invalid bar data triggers continue (skip bad bar)."""
        connection, _, provider = self._create_provider()
        contract = self._qualified_contract()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # One valid bar, one invalid (high < open violates OHLCV)
            mock_bars = [
                BarData(
                    date=datetime.now(timezone.utc),
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=10000,
                    average=100.0,
                    barCount=50,
                ),
                BarData(
                    date=datetime.now(timezone.utc),
                    open=100.0,
                    high=99.0,
                    low=98.0,
                    close=100.5,  # high < open AND high < close → invalid
                    volume=10000,
                    average=100.0,
                    barCount=50,
                ),
            ]
            mock_ib.reqHistoricalData.return_value = mock_bars

            result = provider.request_historical_data(contract, use_rth=True)
            assert len(result) == 1  # Invalid bar skipped

    def test_request_historical_data_unqualified_contract(self) -> None:
        """Cover: ContractNotQualifiedError in historical data."""
        connection, _, provider = self._create_provider()
        contract = Stock("SPY", "SMART", "USD")
        # NOT qualified

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            with pytest.raises(ContractNotQualifiedError):
                provider.request_historical_data(contract, use_rth=True)

    def test_request_historical_data_generic_exception(self) -> None:
        """Cover: generic exception wrapping in historical data."""
        connection, _, provider = self._create_provider()
        contract = self._qualified_contract()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.reqHistoricalData.side_effect = RuntimeError("gateway error")

            with pytest.raises(MarketDataError, match="Failed to retrieve historical data"):
                provider.request_historical_data(contract, use_rth=True)

    def test_validate_market_data_missing_field(self) -> None:
        """Cover: validate_market_data with missing required field."""
        _, _, provider = self._create_provider()

        data = {"symbol": "SPY", "bid": 100.0}  # Missing most fields
        assert provider.validate_market_data(data) is False

    def test_validate_market_data_snapshot_not_true(self) -> None:
        """Cover: validate_market_data snapshot field check."""
        _, _, provider = self._create_provider()

        data = {
            "symbol": "SPY",
            "bid": 100.0,
            "ask": 100.02,
            "last": 100.01,
            "volume": 1000,
            "timestamp": datetime.now(timezone.utc),
            "snapshot": False,  # CRITICAL violation
        }
        assert provider.validate_market_data(data) is False

    def test_validate_market_data_negative_price(self) -> None:
        """Cover: validate_market_data with negative price."""
        _, _, provider = self._create_provider()

        data = {
            "symbol": "SPY",
            "bid": -1.0,
            "ask": 100.02,
            "last": 100.01,
            "volume": 1000,
            "timestamp": datetime.now(timezone.utc),
            "snapshot": True,
        }
        assert provider.validate_market_data(data) is False

    def test_validate_market_data_negative_volume(self) -> None:
        """Cover: validate_market_data with negative volume."""
        _, _, provider = self._create_provider()

        data = {
            "symbol": "SPY",
            "bid": 100.0,
            "ask": 100.02,
            "last": 100.01,
            "volume": -1,
            "timestamp": datetime.now(timezone.utc),
            "snapshot": True,
        }
        assert provider.validate_market_data(data) is False

    def test_validate_market_data_bad_timestamp_type(self) -> None:
        """Cover: validate_market_data with non-datetime timestamp."""
        _, _, provider = self._create_provider()

        data = {
            "symbol": "SPY",
            "bid": 100.0,
            "ask": 100.02,
            "last": 100.01,
            "volume": 1000,
            "timestamp": "not-a-datetime",
            "snapshot": True,
        }
        assert provider.validate_market_data(data) is False

    def test_validate_market_data_valid(self) -> None:
        """Cover: validate_market_data returns True for valid data."""
        _, _, provider = self._create_provider()

        data = {
            "symbol": "SPY",
            "bid": 100.0,
            "ask": 100.02,
            "last": 100.01,
            "volume": 1000,
            "timestamp": datetime.now(timezone.utc),
            "snapshot": True,
        }
        assert provider.validate_market_data(data) is True

    def test_validate_market_data_none_prices_valid(self) -> None:
        """Cover: None prices pass validation (can be None)."""
        _, _, provider = self._create_provider()

        data = {
            "symbol": "SPY",
            "bid": None,
            "ask": None,
            "last": None,
            "volume": 0,
            "timestamp": datetime.now(timezone.utc),
            "snapshot": True,
        }
        assert provider.validate_market_data(data) is True

    def test_is_data_stale_none_timestamp(self) -> None:
        """Cover: is_data_stale with None timestamp."""
        _, _, provider = self._create_provider()
        assert provider.is_data_stale(None) is True

    def test_is_data_stale_timezone_naive(self) -> None:
        """Cover: is_data_stale with timezone-naive timestamp."""
        _, _, provider = self._create_provider()

        # Old naive timestamp → should be stale
        old_time = datetime.now() - timedelta(minutes=10)
        assert provider.is_data_stale(old_time) is True

    def test_is_data_stale_fresh(self) -> None:
        """Cover: is_data_stale with fresh timestamp."""
        _, _, provider = self._create_provider()

        fresh_time = datetime.now(timezone.utc)
        assert provider.is_data_stale(fresh_time) is False

    def test_validate_bar_data_negative_prices(self) -> None:
        """Cover: _validate_bar_data with negative prices."""
        _, _, provider = self._create_provider()

        bar = {"open": -1, "high": 10, "low": 1, "close": 5, "volume": 100}
        assert provider._validate_bar_data(bar) is False

    def test_validate_bar_data_high_less_than_close(self) -> None:
        """Cover: _validate_bar_data where high < close."""
        _, _, provider = self._create_provider()

        bar = {"open": 5, "high": 6, "low": 4, "close": 7, "volume": 100}
        assert provider._validate_bar_data(bar) is False

    def test_validate_bar_data_low_greater_than_close(self) -> None:
        """Cover: _validate_bar_data where low > close."""
        _, _, provider = self._create_provider()

        bar = {"open": 10, "high": 12, "low": 8, "close": 7, "volume": 100}
        assert provider._validate_bar_data(bar) is False

    def test_validate_bar_data_negative_volume(self) -> None:
        """Cover: _validate_bar_data with negative volume."""
        _, _, provider = self._create_provider()

        bar = {"open": 10, "high": 12, "low": 8, "close": 11, "volume": -1}
        assert provider._validate_bar_data(bar) is False

    def test_validate_bar_data_missing_key(self) -> None:
        """Cover: _validate_bar_data with KeyError (missing key)."""
        _, _, provider = self._create_provider()

        bar = {"open": 10}  # Missing high, low, close, volume
        assert provider._validate_bar_data(bar) is False

    def test_validate_bar_data_valid(self) -> None:
        """Cover: _validate_bar_data returns True for valid bar."""
        _, _, provider = self._create_provider()

        bar = {"open": 10, "high": 12, "low": 9, "close": 11, "volume": 100}
        assert provider._validate_bar_data(bar) is True

    def test_market_data_provider_repr(self) -> None:
        """Cover: __repr__ method."""
        _, _, provider = self._create_provider()
        repr_str = repr(provider)
        assert "MarketDataProvider" in repr_str
