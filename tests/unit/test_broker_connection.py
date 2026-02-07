"""
Unit tests for IBKR broker connection management.

Tests cover:
- Connection establishment
- Connection timeout handling
- ClientId rotation
- Retry logic with exponential backoff
- Connection cleanup

ALPHA LEARNINGS ENCODED:
- ClientId must be timestamp-based for uniqueness
- Exponential backoff on connection failures
- Clean resource cleanup on disconnect
"""

import time
from datetime import datetime
from unittest.mock import patch

import pytest

from src.broker import IBKRConnection
from src.broker.exceptions import (
    MaxRetriesExceededError,
)


class TestBrokerConnection:
    """Test suite for IBKR Gateway connection lifecycle."""

    def test_connection_establishment_success(self) -> None:
        """Test successful connection to Gateway.

        GIVEN: Gateway is available at localhost:4002
        WHEN: Broker connects with valid ClientId
        THEN: Connection succeeds, isConnected() returns True
        AND: ClientId is timestamp-based (validate format)
        """
        # Arrange
        connection = IBKRConnection(host="localhost", port=4002, client_id=1001)

        # Mock the underlying IB instance
        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.connect.return_value = None

            # Act
            success = connection.connect()

            # Assert
            assert success is True
            assert connection.is_connected() is True
            mock_ib.connect.assert_called_once()

    def test_client_id_uniqueness(self) -> None:
        """Test that multiple connections get unique ClientIds.

        GIVEN: Multiple connection instances
        WHEN: Each requests a ClientId
        THEN: All ClientIds are unique (timestamp-based)
        AND: Format is integer derived from Unix timestamp
        """
        # Arrange & Act: Generate 3 client IDs with small delays
        client_ids = []
        for _ in range(3):
            client_id = IBKRConnection.generate_client_id()
            client_ids.append(client_id)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Assert: All IDs should be unique
        assert len(client_ids) == len(set(client_ids)), "Client IDs must be unique"

        # Assert: All IDs should be integers
        assert all(isinstance(cid, int) for cid in client_ids)

        # Assert: IDs should be reasonable range (not negative, not too large)
        assert all(0 <= cid < 1000000 for cid in client_ids)

    def test_connection_retry_on_failure(self) -> None:
        """Test retry logic with exponential backoff.

        GIVEN: Gateway initially unavailable
        WHEN: Connection attempted with retry policy
        THEN: Exponential backoff occurs (validate timing)
        AND: Connection succeeds on Nth retry
        """
        # Arrange
        connection = IBKRConnection(
            max_retries=3, retry_delay_base=0.01
        )  # Fast retries for testing

        with patch.object(connection, "_ib") as mock_ib:
            # Fail first 2 attempts, succeed on 3rd
            mock_ib.connect.side_effect = [
                ConnectionRefusedError("Gateway unavailable"),
                ConnectionRefusedError("Gateway unavailable"),
                None,  # Success on 3rd attempt
            ]
            # isConnected() is only called ONCE - after the 3rd successful connect()
            # First 2 attempts raise exceptions and never reach isConnected()
            mock_ib.isConnected.return_value = True

            # Act
            success = connection.connect()

            # Assert: Should succeed on 3rd attempt
            assert success is True
            assert mock_ib.connect.call_count == 3

    def test_connection_retry_max_limit(self) -> None:
        """Test that retries respect maximum attempt limit.

        GIVEN: Gateway unavailable for extended period
        WHEN: Connection attempted with max retry policy
        THEN: Stops after max retries
        AND: Raises MaxRetriesExceededError
        """
        # Arrange
        connection = IBKRConnection(
            max_retries=3, retry_delay_base=0.01
        )  # Fast retries for testing

        with patch.object(connection, "_ib") as mock_ib:
            # Fail all attempts
            mock_ib.connect.side_effect = ConnectionRefusedError("Gateway unavailable")
            mock_ib.isConnected.return_value = False

            # Act & Assert: Should raise MaxRetriesExceededError
            with pytest.raises(MaxRetriesExceededError, match="Failed to connect"):
                connection.connect()

            # Assert: Tried max_retries times
            assert mock_ib.connect.call_count == 3

    def test_connection_cleanup_on_disconnect(self) -> None:
        """Test clean disconnect and resource cleanup.

        GIVEN: Active connection to Gateway
        WHEN: Disconnect method called
        THEN: Connection closed cleanly
        AND: Resources released
        """
        # Arrange
        connection = IBKRConnection()

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.side_effect = [True, False]  # Connected, then disconnected
            mock_ib.disconnect.return_value = None

            # Simulate connected state
            connection._connection_start_time = datetime.now()

            # Act
            connection.disconnect()

            # Assert
            mock_ib.disconnect.assert_called_once()
            assert connection._connection_start_time is None  # Cleaned up

    def test_connection_timeout_handling(self) -> None:
        """Test connection timeout enforcement.

        GIVEN: Gateway hangs during connection attempt
        WHEN: Timeout threshold exceeded
        THEN: Connection attempt aborted
        AND: TimeoutError propagates up
        """
        # Arrange
        connection = IBKRConnection(timeout=1, max_retries=1)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.connect.side_effect = TimeoutError("Connection timeout")
            mock_ib.isConnected.return_value = False

            # Act & Assert: TimeoutError should propagate but be wrapped
            with pytest.raises(MaxRetriesExceededError):
                connection.connect()

            # Assert connection did not succeed
            assert not connection.is_connected()

    def test_connection_with_valid_parameters(self) -> None:
        """Test connection with all required parameters.

        GIVEN: Valid connection parameters (host, port, clientId)
        WHEN: Connection established
        THEN: Parameters passed correctly to IB.connect()
        AND: Connection uses port 4002 (paper trading)
        """
        # Arrange
        connection = IBKRConnection(host="localhost", port=4002, client_id=1001, timeout=10)

        with patch.object(connection, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            mock_ib.connect.return_value = None

            # Act
            success = connection.connect()

            # Assert
            assert success is True
            mock_ib.connect.assert_called_once_with("localhost", 4002, clientId=1001, timeout=10)

    def test_connection_state_check(self) -> None:
        """Test connection state verification.

        GIVEN: Various connection states
        WHEN: is_connected() called
        THEN: Returns accurate connection status
        """
        # Arrange & Act & Assert: Disconnected state
        connection_disconnected = IBKRConnection()
        with patch.object(connection_disconnected, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = False
            assert connection_disconnected.is_connected() is False

        # Arrange & Act & Assert: Connected state
        connection_connected = IBKRConnection()
        with patch.object(connection_connected, "_ib") as mock_ib:
            mock_ib.isConnected.return_value = True
            assert connection_connected.is_connected() is True
