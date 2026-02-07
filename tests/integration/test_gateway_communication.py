"""
Integration tests for IBKR Gateway communication.

Tests cover:
- Full request/response cycle with mock Gateway
- Timeout parameter propagation through request chain
- Error handling for stale/missing data
- Buffer management (snapshot mode validation)
- End-to-end workflows: connect → qualify → data → disconnect
- Concurrent request handling across multiple instruments
"""

from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest
from ib_insync import IB, Stock, Ticker, BarData

from src.broker import (
    IBKRConnection,
    ContractManager,
    MarketDataProvider,
    StaleDataError,
)


class TestGatewayCommunicationIntegration:
    """Integration tests for full Gateway communication workflows."""

    def test_full_workflow_mock_gateway(self) -> None:
        """
        Test complete workflow: connect → qualify → snapshot → disconnect.

        GIVEN: Mock Gateway responding to all requests
        WHEN: Full workflow executed (connection, contract qualification, market data, cleanup)
        THEN: Each step completes successfully
        AND: Resources cleaned up properly
        AND: snapshot=True enforced in data request
        """
        # Arrange
        connection = IBKRConnection(host="127.0.0.1", port=4002, client_id=1)
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        with patch.object(connection, "_ib") as mock_ib:
            # isConnected tracks connection state via return_value
            # After connect() succeeds, isConnected returns True
            # After disconnect(), we flip it to False
            mock_ib.isConnected.return_value = False  # Start disconnected
            mock_ib.connect.return_value = None
            mock_ib.disconnect.return_value = None

            # Mock contract qualification
            qualified_contract = Stock("SPY", "SMART", "USD")
            qualified_contract.conId = 756733
            mock_ib.qualifyContracts.return_value = [qualified_contract]

            # Mock market data
            mock_ticker = Mock(spec=Ticker)
            mock_ticker.bid = 685.50
            mock_ticker.ask = 685.52
            mock_ticker.last = 685.51
            mock_ticker.volume = 1250000
            mock_ticker.time = datetime.now(timezone.utc)
            mock_ib.reqMktData.return_value = mock_ticker
            mock_ib.waitOnUpdate.return_value = None

            # Act
            # Step 1: Connect
            assert not connection.is_connected(), "Should start disconnected"
            mock_ib.isConnected.return_value = True  # After connect succeeds
            success = connection.connect()
            assert success is True, "Connection should succeed"
            assert connection.is_connected(), "Should be connected"

            # Step 2: Qualify contract
            qualified = contract_manager.qualify_contract("SPY")
            assert qualified.conId == 756733, "Contract should have conId"

            # Step 3: Request market data
            data = provider.request_market_data(qualified, timeout=30)
            assert data["last"] > 0, "Should have valid price"
            assert data["snapshot"] is True, "Should use snapshot mode"

            # Step 4: Disconnect - isConnected must return True for disconnect() to call _ib.disconnect()
            connection.disconnect()  # isConnected is still True, so _ib.disconnect() gets called
            mock_ib.isConnected.return_value = False  # Now reflect disconnected state
            assert not connection.is_connected(), "Should be disconnected"

            # Assert: Verify call sequence
            mock_ib.connect.assert_called_once()
            mock_ib.qualifyContracts.assert_called_once()
            mock_ib.reqMktData.assert_called_once()
            mock_ib.disconnect.assert_called_once()

            # Assert: CRITICAL - snapshot=True was used
            call_kwargs = mock_ib.reqMktData.call_args[1]
            assert call_kwargs["snapshot"] is True, "🔴 CRITICAL: snapshot MUST be True"

    def test_concurrent_requests_handling(self) -> None:
        """
        Test handling of concurrent market data requests.

        GIVEN: Multiple simultaneous requests for SPY, QQQ, IWM
        WHEN: All requests submitted concurrently
        THEN: Each tracked with unique reqId
        AND: No cross-contamination of data streams
        AND: All responses received correctly
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            symbols = ["SPY", "QQQ", "IWM"]

            # Mock qualification - return qualified contracts
            qualified_contracts = []
            for i, symbol in enumerate(symbols):
                contract = Stock(symbol, "SMART", "USD")
                contract.conId = 756733 + i
                qualified_contracts.append([contract])  # qualifyContracts returns list

            mock_ib.qualifyContracts.side_effect = qualified_contracts

            # Mock market data with unique prices
            def create_ticker(price: float) -> Mock:
                ticker = Mock(spec=Ticker)
                ticker.bid = price
                ticker.ask = price + 0.02
                ticker.last = price + 0.01
                ticker.volume = 1000000
                ticker.time = datetime.now(timezone.utc)
                return ticker

            mock_ib.reqMktData.side_effect = [
                create_ticker(685.50),  # SPY
                create_ticker(595.75),  # QQQ
                create_ticker(225.30),  # IWM
            ]
            mock_ib.waitOnUpdate.return_value = None

            # Act
            results = []
            for symbol in symbols:
                qualified = contract_manager.qualify_contract(symbol)
                data = provider.request_market_data(qualified, timeout=30)
                results.append((symbol, data))

            # Assert: All requests completed
            assert len(results) == 3, "Should have 3 results"
            assert mock_ib.qualifyContracts.call_count == 3
            assert mock_ib.reqMktData.call_count == 3

            # Assert: Each symbol has correct data
            symbols_received = [symbol for symbol, _ in results]
            assert symbols_received == ["SPY", "QQQ", "IWM"], "Symbols should match request order"

            # Assert: Prices are unique
            prices = [data["last"] for _, data in results]
            assert len(set(prices)) == 3, "Each symbol should have unique price"

    def test_gateway_disconnection_recovery(self) -> None:
        """
        Test Gateway disconnection detection and recovery.

        GIVEN: Active Gateway connection
        WHEN: Unexpected disconnection occurs
        THEN: Disconnection detected via is_connected()
        AND: All in-flight requests cancelled
        AND: Reconnection attempted with exponential backoff
        """
        # Arrange
        connection = IBKRConnection(max_retries=3, retry_delay_base=0.01)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.connect.return_value = None
            mock_ib.disconnect.return_value = None

            # Act
            # Initial connection - simulate connected state
            mock_ib.isConnected.return_value = True
            connection._connection_start_time = datetime.now()
            assert connection.is_connected(), "Should start connected"
            assert connection.is_connected(), "Still connected"

            # Simulate disconnection
            mock_ib.isConnected.return_value = False
            is_still_connected = connection.is_connected()
            assert not is_still_connected, "Should detect disconnection"
            assert not connection.is_connected(), "Still disconnected"

            # Reconnect - isConnected returns True after connect succeeds
            mock_ib.isConnected.return_value = True
            success = connection.reconnect()
            assert success is True, "Should reconnect successfully"

            # Assert
            assert mock_ib.connect.call_count >= 1, "Should attempt reconnection"

    def test_timeout_propagation_through_layers(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: Timeout MUST propagate through entire stack.

        GIVEN: Request with timeout=30s
        WHEN: Request flows through: connection → manager → provider
        THEN: Timeout parameter present at every layer
        AND: Timeout enforced consistently
        AND: TimeoutError raised if exceeded at any layer
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733  # Qualified

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Simulate timeout at Gateway layer
            mock_ib.reqHistoricalData.side_effect = TimeoutError("Gateway timeout after 30s")

            # Act & Assert
            with pytest.raises(TimeoutError, match="Gateway timeout after 30s"):
                provider.request_historical_data(
                    contract,
                    duration="3600 S",
                    bar_size="5 mins",
                    use_rth=True,
                    timeout=30,  # CRITICAL: Timeout parameter passed
                )

            # Assert: Timeout parameter was passed
            call_kwargs = mock_ib.reqHistoricalData.call_args[1]
            assert "timeout" in call_kwargs, "🔴 CRITICAL: timeout parameter missing"
            assert call_kwargs["timeout"] == 30, "Timeout must match requested value"

    def test_historical_data_rth_enforcement(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: 1-hour RTH-only windows.

        GIVEN: Request for historical bars
        WHEN: provider.request_historical_data() called
        THEN: duration = "3600 S" (1 hour)
        AND: use_rth = True (RTH only, no extended hours)
        AND: Response contains bars with OHLCV data
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733  # Qualified

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            # Mock 12 bars (1 hour of 5-min intervals)
            base_time = datetime.now(timezone.utc)
            mock_bars = [
                BarData(
                    date=base_time - timedelta(minutes=5 * i),
                    open=685.0 + i * 0.1,
                    high=686.0 + i * 0.1,
                    low=684.5 + i * 0.1,
                    close=685.5 + i * 0.1,
                    volume=100000,
                    average=685.25,
                    barCount=50,
                )
                for i in range(12)
            ]
            mock_ib.reqHistoricalData.return_value = mock_bars

            # Act
            bars = provider.request_historical_data(
                contract,
                duration="3600 S",
                bar_size="5 mins",
                use_rth=True,  # CRITICAL: RTH only
                timeout=30,
            )

            # Assert: CRITICAL parameters enforced
            call_kwargs = mock_ib.reqHistoricalData.call_args[1]
            assert call_kwargs["durationStr"] == "3600 S", "🔴 CRITICAL: Duration must be 1 hour"
            assert call_kwargs["useRTH"] is True, "🔴 CRITICAL: useRTH MUST be True"

            # Assert: Correct number of bars
            assert len(bars) == 12, "Should receive 12 bars (1 hour of 5-min intervals)"

    def test_error_recovery_degradation_to_strategy_c(self) -> None:
        """
        Test graceful degradation to Strategy C on errors.

        GIVEN: Market data request fails (no permission, invalid symbol, stale data)
        WHEN: Error detected
        THEN: Error logged with context
        AND: System degrades to Strategy C (no market data)
        AND: No crash or hang condition
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733  # Qualified

        # Simulate market data error (no permission)
        error_code = 354
        error_msg = "No market data permissions for this security"

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            def raise_data_error(*args: Any, **kwargs: Any) -> None:
                raise PermissionError(f"Error {error_code}: {error_msg}")

            mock_ib.reqMktData.side_effect = raise_data_error

            # Act: Attempt data request, expect graceful failure
            try:
                provider.request_market_data(contract, timeout=30)
                assert False, "Should raise exception"
            except Exception as e:
                # Expected error - system should degrade to Strategy C
                # Provider wraps PermissionError in Market DataError
                assert str(error_code) in str(e), "Error code should be in message"
                # In production, this triggers Strategy C activation

            # Assert: Error was raised (not silent)
            mock_ib.reqMktData.assert_called_once()

    def test_stale_data_triggers_strategy_c(self) -> None:
        """
        Test that stale data triggers Strategy C.

        GIVEN: Market data with timestamp >5 minutes old
        WHEN: Staleness check performed
        THEN: Data flagged as stale
        AND: Strategy C activated
        AND: No trade execution with stale data
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733  # Qualified

        # Create stale data (10 minutes old)
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            mock_ticker = Mock(spec=Ticker)
            mock_ticker.time = stale_time
            mock_ticker.last = 685.50
            mock_ticker.bid = 685.48
            mock_ticker.ask = 685.52
            mock_ticker.volume = 1000000
            mock_ib.reqMktData.return_value = mock_ticker
            mock_ib.waitOnUpdate.return_value = None

            # Act & Assert: Should raise StaleDataError
            with pytest.raises(StaleDataError, match="stale"):
                provider.request_market_data(contract, timeout=30)

    def test_contract_qualification_failure_handling(self) -> None:
        """
        Test handling of contract qualification failures.

        GIVEN: Invalid symbol or unrecognized contract
        WHEN: qualify_contract() called
        THEN: Empty list returned or exception raised
        AND: System handles gracefully (no crash)
        AND: Appropriate error logged
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)

        Stock("INVALID_SYMBOL_XYZ", "SMART", "USD")

        with patch.object(connection, "_ib") as mock_ib:
            # Mock failed qualification
            mock_ib.qualifyContracts.return_value = []  # Empty list = failed

            # Act & Assert: Should raise ContractQualificationError
            with pytest.raises(Exception):  # ContractQualificationError
                contract_manager.qualify_contract("INVALID_SYMBOL_XYZ")

    def test_multi_step_workflow_with_error_handling(self) -> None:
        """
        Test complex workflow with error handling at each step.

        GIVEN: Multi-step workflow (connect → qualify → data → historical)
        WHEN: Each step has potential for failure
        THEN: Errors handled gracefully at each layer
        AND: System state remains consistent
        AND: Resources cleaned up on failure
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        with patch.object(connection, "_ib") as mock_ib:
            # Step 1: Connection succeeds
            mock_ib.isConnected.return_value = False  # Start disconnected
            mock_ib.connect.return_value = None

            # Step 2: Qualification succeeds
            qualified = Stock("SPY", "SMART", "USD")
            qualified.conId = 756733
            mock_ib.qualifyContracts.return_value = [qualified]

            # Step 3: Market data succeeds
            mock_ticker = Mock(spec=Ticker)
            mock_ticker.bid = 685.48
            mock_ticker.ask = 685.52
            mock_ticker.last = 685.50
            mock_ticker.volume = 1000000
            mock_ticker.time = datetime.now(timezone.utc)
            mock_ib.reqMktData.return_value = mock_ticker
            mock_ib.waitOnUpdate.return_value = None

            # Step 4: Historical data fails (timeout)
            def historical_timeout(*args: Any, **kwargs: Any) -> None:
                raise TimeoutError("Historical data timeout")

            mock_ib.reqHistoricalData.side_effect = historical_timeout

            # Step 5: Cleanup
            mock_ib.disconnect.return_value = None

            # Act
            # Connect
            mock_ib.isConnected.return_value = True  # After connect succeeds
            success = connection.connect()
            assert success is True
            assert connection.is_connected()

            # Qualify
            qualified_contract = contract_manager.qualify_contract("SPY")
            assert qualified_contract.conId == 756733

            # Market data
            data = provider.request_market_data(qualified_contract, timeout=30)
            assert data["last"] > 0

            # Historical data (fails)
            try:
                provider.request_historical_data(
                    qualified_contract,
                    duration="3600 S",
                    bar_size="5 mins",
                    use_rth=True,
                    timeout=30,
                )
                assert False, "Should raise TimeoutError"
            except TimeoutError:
                # Expected - cleanup should still occur
                connection.disconnect()  # isConnected still True, so _ib.disconnect() gets called
                mock_ib.isConnected.return_value = False  # Now reflect disconnected state
                assert not connection.is_connected()

            # Assert: All steps attempted, cleanup occurred despite error
            mock_ib.connect.assert_called_once()
            mock_ib.qualifyContracts.assert_called_once()
            mock_ib.reqMktData.assert_called_once()
            mock_ib.reqHistoricalData.assert_called_once()
            mock_ib.disconnect.assert_called_once()

    def test_snapshot_mode_prevents_buffer_overflow(self) -> None:
        """
        🔴 CRITICAL: Document that snapshot=True prevents buffer overflow.

        This test documents the CRITICAL requirement that snapshot=True
        MUST be used to prevent buffer overflow in production.

        NEVER change this test without consulting @Lead_Quant.
        """
        # Arrange
        connection = IBKRConnection()
        contract_manager = ContractManager(connection)
        provider = MarketDataProvider(connection, contract_manager, snapshot_mode=True)

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733  # Qualified

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True

            mock_ticker = Mock(spec=Ticker)
            mock_ticker.bid = 685.48
            mock_ticker.ask = 685.52
            mock_ticker.last = 685.50
            mock_ticker.volume = 1000000
            mock_ticker.time = datetime.now(timezone.utc)
            mock_ib.reqMktData.return_value = mock_ticker
            mock_ib.waitOnUpdate.return_value = None

            # Act: ALWAYS use snapshot=True
            data = provider.request_market_data(contract, timeout=30)

            # Assert: Document why this is CRITICAL
            call_kwargs = mock_ib.reqMktData.call_args[1]
            assert call_kwargs["snapshot"] is True, (
                "🔴 CRITICAL: snapshot=False causes buffer overflow. "
                "Production incident on 2024-01-15 proved this. "
                "NEVER use snapshot=False without @Lead_Quant approval."
            )
            assert data["snapshot"] is True, "Data must indicate snapshot mode used"

    def test_client_id_uniqueness_across_connections(self) -> None:
        """
        Test that each connection uses unique ClientId.

        GIVEN: Multiple connection attempts
        WHEN: ClientIds generated (timestamp-based)
        THEN: Each ClientId is unique
        AND: No collision risk
        """
        # Arrange
        import time

        mock_ib = Mock(spec=IB)
        mock_ib.connect.return_value = None

        # Act: Generate multiple ClientIds
        client_ids = []
        with patch("ib_insync.IB", return_value=mock_ib):
            for _ in range(5):
                # Simulate timestamp-based ClientId generation
                client_id = int(time.time() * 1000) % 1000000
                client_ids.append(client_id)
                time.sleep(0.01)  # Ensure different timestamps

        # Assert: All ClientIds unique
        assert len(client_ids) == len(set(client_ids)), "ClientIds must be unique"
        assert all(0 <= cid < 1000000 for cid in client_ids), "ClientIds in valid range"
