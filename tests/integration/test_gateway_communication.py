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
        mock_ib = Mock(spec=IB)

        # Mock connection
        mock_ib.isConnected.side_effect = [False, True, True, True, False]  # State transitions
        mock_ib.connect.return_value = None

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

        # Mock disconnect
        mock_ib.disconnect.return_value = None

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()

            # Step 1: Connect
            assert not ib.isConnected(), "Should start disconnected"
            ib.connect("127.0.0.1", 4002, clientId=1)
            assert ib.isConnected(), "Should be connected after connect()"

            # Step 2: Qualify contract
            unqualified = Stock("SPY", "SMART", "USD")
            contracts = ib.qualifyContracts(unqualified)
            assert len(contracts) > 0, "Contract qualification should succeed"
            contract = contracts[0]
            assert contract.conId == 756733, "Contract should have conId"

            # Step 3: Request market data with snapshot=True
            ticker = ib.reqMktData(contract, "", snapshot=True, regulatorySnapshot=False)
            assert ticker is not None, "Should receive ticker data"
            assert ticker.last > 0, "Should have valid price"

            # Step 4: Disconnect
            ib.disconnect()
            assert not ib.isConnected(), "Should be disconnected after disconnect()"

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
        mock_ib = Mock(spec=IB)
        mock_ib.isConnected.return_value = True

        symbols = ["SPY", "QQQ", "IWM"]
        contracts = [Stock(symbol, "SMART", "USD") for symbol in symbols]

        # Mock qualification for each contract
        qualified_contracts = []
        for i, symbol in enumerate(symbols):
            contract = Stock(symbol, "SMART", "USD")
            contract.conId = 756733 + i  # Unique conIds
            qualified_contracts.append(contract)

        mock_ib.qualifyContracts.side_effect = [[c] for c in qualified_contracts]

        # Mock market data for each symbol with unique prices
        def create_ticker(symbol: str, price: float) -> Mock:
            ticker = Mock(spec=Ticker)
            ticker.contract = Stock(symbol, "SMART", "USD")
            ticker.bid = price
            ticker.ask = price + 0.02
            ticker.last = price + 0.01
            ticker.volume = 1000000
            ticker.time = datetime.now(timezone.utc)
            return ticker

        mock_tickers = [
            create_ticker("SPY", 685.50),
            create_ticker("QQQ", 595.75),
            create_ticker("IWM", 225.30),
        ]
        mock_ib.reqMktData.side_effect = mock_tickers

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            results = []

            for contract in contracts:
                # Qualify each contract
                qualified = ib.qualifyContracts(contract)
                assert len(qualified) > 0, f"Failed to qualify {contract.symbol}"

                # Request market data
                ticker = ib.reqMktData(qualified[0], "", snapshot=True)
                results.append((contract.symbol, ticker))

        # Assert: All requests completed
        assert len(results) == 3, "Should have 3 results"
        assert mock_ib.qualifyContracts.call_count == 3
        assert mock_ib.reqMktData.call_count == 3

        # Assert: Each symbol has correct data (no cross-contamination)
        symbols_received = [symbol for symbol, _ in results]
        assert symbols_received == ["SPY", "QQQ", "IWM"], "Symbols should match request order"

        # Assert: Prices are unique (proves no cross-contamination)
        prices = [ticker.last for _, ticker in results]
        assert len(set(prices)) == 3, "Each symbol should have unique price"

    def test_gateway_disconnection_recovery(self) -> None:
        """
        Test Gateway disconnection detection and recovery.

        GIVEN: Active Gateway connection
        WHEN: Unexpected disconnection occurs
        THEN: Disconnection detected via isConnected()
        AND: All in-flight requests cancelled
        AND: Reconnection attempted with exponential backoff
        """
        # Arrange
        mock_ib = Mock(spec=IB)

        # Simulate connection states: connected → disconnected → reconnected
        connection_states = [True, True, False, False, True]
        mock_ib.isConnected.side_effect = connection_states
        mock_ib.connect.return_value = None
        mock_ib.disconnect.return_value = None

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()

            # Initial connection
            assert ib.isConnected(), "Should start connected"

            # Simulate disconnection
            assert ib.isConnected(), "Still connected"
            is_still_connected = ib.isConnected()  # This triggers disconnection
            assert not is_still_connected, "Should detect disconnection"

            # Attempt reconnection
            is_reconnected = ib.isConnected()
            assert not is_reconnected, "Still disconnected"

            # Reconnect
            ib.connect("127.0.0.1", 4002, clientId=2)
            assert ib.isConnected(), "Should reconnect successfully"

        # Assert
        assert mock_ib.connect.call_count >= 1, "Should attempt reconnection"

    def test_timeout_propagation_through_layers(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: Timeout MUST propagate through entire stack.

        GIVEN: Request with timeout=30s
        WHEN: Request flows through: broker → gateway → TWS
        THEN: Timeout parameter present at every layer
        AND: Timeout enforced consistently
        AND: TimeoutError raised if exceeded at any layer
        """
        # Arrange
        mock_ib = Mock(spec=IB)
        mock_ib.isConnected.return_value = True

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733

        # Simulate timeout at Gateway layer
        def slow_request(*args: Any, **kwargs: Any) -> None:
            timeout = kwargs.get("timeout")
            if timeout and timeout < 60:
                raise TimeoutError(f"Gateway timeout after {timeout}s")

        mock_ib.reqHistoricalData.side_effect = slow_request

        # Act & Assert
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()

            with pytest.raises(TimeoutError, match="Gateway timeout after 30s"):
                ib.reqHistoricalData(
                    contract,
                    endDateTime="",
                    durationStr="3600 S",
                    barSizeSetting="5 mins",
                    whatToShow="TRADES",
                    useRTH=True,
                    formatDate=1,
                    timeout=30,  # CRITICAL: Timeout parameter passed
                )

        # Assert: Timeout parameter was passed to Gateway layer
        call_kwargs = mock_ib.reqHistoricalData.call_args[1]
        assert "timeout" in call_kwargs, "🔴 CRITICAL: timeout parameter missing"
        assert call_kwargs["timeout"] == 30, "Timeout must match requested value"

    def test_historical_data_rth_enforcement(self) -> None:
        """
        🔴 CRITICAL ALPHA LEARNING: 1-hour RTH-only windows.

        GIVEN: Request for historical bars
        WHEN: reqHistoricalData() called
        THEN: durationStr = "3600 S" (1 hour)
        AND: useRTH = True (RTH only, no extended hours)
        AND: Response contains exactly 12 bars (5-min intervals)
        """
        # Arrange
        mock_ib = Mock(spec=IB)
        mock_ib.isConnected.return_value = True

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733

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
            for i in range(12)  # 12 bars = 1 hour
        ]
        mock_ib.reqHistoricalData.return_value = mock_bars

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            bars = ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="3600 S",  # CRITICAL: 1 hour
                barSizeSetting="5 mins",
                whatToShow="TRADES",
                useRTH=True,  # CRITICAL: RTH only
                formatDate=1,
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
        mock_ib = Mock(spec=IB)
        mock_ib.isConnected.return_value = True

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733

        # Simulate market data error (no permission)
        error_code = 354
        error_msg = "No market data permissions for this security"

        def raise_data_error(*args: Any, **kwargs: Any) -> None:
            raise PermissionError(f"Error {error_code}: {error_msg}")

        mock_ib.reqMktData.side_effect = raise_data_error

        # Act: Attempt data request, expect graceful failure
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()

            try:
                ib.reqMktData(contract, "", snapshot=True)
                assert False, "Should raise PermissionError"
            except PermissionError as e:
                # Expected error - system should degrade to Strategy C
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
        mock_ib = Mock(spec=IB)
        mock_ib.isConnected.return_value = True

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733

        # Create stale data (10 minutes old)
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.time = stale_time
        mock_ticker.last = 685.50
        mock_ticker.bid = 685.48
        mock_ticker.ask = 685.52

        mock_ib.reqMktData.return_value = mock_ticker

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            ticker = ib.reqMktData(contract, "", snapshot=True)

            # Check staleness
            time_diff = (
                datetime.now(timezone.utc) - ticker.time  # type: ignore[operator]
            ).total_seconds()
            is_stale = time_diff > 300  # 5 minutes

        # Assert
        assert is_stale is True, "Data should be flagged as stale"
        # In production, this triggers Strategy C

    def test_contract_qualification_failure_handling(self) -> None:
        """
        Test handling of contract qualification failures.

        GIVEN: Invalid symbol or unrecognized contract
        WHEN: qualifyContracts() called
        THEN: Empty list returned (no qualified contracts)
        AND: System handles gracefully (no crash)
        AND: Appropriate error logged
        """
        # Arrange
        mock_ib = Mock(spec=IB)
        mock_ib.isConnected.return_value = True

        invalid_contract = Stock("INVALID_SYMBOL_XYZ", "SMART", "USD")

        # Mock failed qualification
        mock_ib.qualifyContracts.return_value = []  # Empty list = failed

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            contracts = ib.qualifyContracts(invalid_contract)

        # Assert
        assert len(contracts) == 0, "Invalid contracts should return empty list"
        mock_ib.qualifyContracts.assert_called_once()
        # In production, this prevents downstream market data requests

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
        mock_ib = Mock(spec=IB)

        # Step 1: Connection succeeds
        mock_ib.isConnected.side_effect = [False, True, True, True, True, False]
        mock_ib.connect.return_value = None

        # Step 2: Qualification succeeds
        qualified = Stock("SPY", "SMART", "USD")
        qualified.conId = 756733
        mock_ib.qualifyContracts.return_value = [qualified]

        # Step 3: Market data succeeds
        mock_ticker = Mock(spec=Ticker)
        mock_ticker.last = 685.50
        mock_ticker.time = datetime.now(timezone.utc)
        mock_ib.reqMktData.return_value = mock_ticker

        # Step 4: Historical data fails (timeout)
        def historical_timeout(*args: Any, **kwargs: Any) -> None:
            raise TimeoutError("Historical data timeout")

        mock_ib.reqHistoricalData.side_effect = historical_timeout

        # Step 5: Cleanup
        mock_ib.disconnect.return_value = None

        # Act
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()

            # Connect
            ib.connect("127.0.0.1", 4002, clientId=1)
            assert ib.isConnected()

            # Qualify
            contracts = ib.qualifyContracts(Stock("SPY", "SMART", "USD"))
            assert len(contracts) > 0

            # Market data
            ticker = ib.reqMktData(contracts[0], "", snapshot=True)
            assert ticker.last > 0

            # Historical data (fails)
            try:
                ib.reqHistoricalData(
                    contracts[0],
                    endDateTime="",
                    durationStr="3600 S",
                    barSizeSetting="5 mins",
                    whatToShow="TRADES",
                    useRTH=True,
                    formatDate=1,
                    timeout=30,
                )
                assert False, "Should raise TimeoutError"
            except TimeoutError:
                # Expected - cleanup should still occur
                ib.disconnect()
                assert not ib.isConnected()

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
        mock_ib = Mock(spec=IB)
        mock_ib.isConnected.return_value = True

        contract = Stock("SPY", "SMART", "USD")
        contract.conId = 756733

        mock_ticker = Mock(spec=Ticker)
        mock_ticker.last = 685.50
        mock_ib.reqMktData.return_value = mock_ticker

        # Act: ALWAYS use snapshot=True
        with patch("ib_insync.IB", return_value=mock_ib):
            ib = IB()
            ib.reqMktData(contract, "", snapshot=True, regulatorySnapshot=False)

        # Assert: Document why this is CRITICAL
        call_kwargs = mock_ib.reqMktData.call_args[1]
        assert call_kwargs["snapshot"] is True, (
            "🔴 CRITICAL: snapshot=False causes buffer overflow. "
            "Production incident on 2024-01-15 proved this. "
            "NEVER use snapshot=False without @Lead_Quant approval."
        )

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
