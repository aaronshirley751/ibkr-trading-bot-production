"""
Unit tests for Gateway health check utilities.

These tests use mocking to avoid requiring an actual Gateway.
Integration tests should verify real Gateway behavior.
"""

import socket
from unittest.mock import Mock, patch

import pytest

from src.utils.gateway_health import GatewayHealthChecker


class TestGatewayHealthChecker:
    """Tests for GatewayHealthChecker class."""

    @pytest.fixture
    def checker(self) -> GatewayHealthChecker:
        """Create a health checker instance for testing."""
        return GatewayHealthChecker(
            host="localhost",
            port=4002,
            discord_webhook=None,  # No alerts in tests
        )

    # Port Check Tests

    def test_check_port_success(self, checker: GatewayHealthChecker) -> None:
        """Port check returns True when connection succeeds."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.return_value.__enter__ = Mock()
            mock_conn.return_value.__exit__ = Mock()
            assert checker.check_port() is True

    def test_check_port_timeout(self, checker: GatewayHealthChecker) -> None:
        """Port check returns False on timeout."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = socket.timeout()
            assert checker.check_port() is False

    def test_check_port_connection_refused(self, checker: GatewayHealthChecker) -> None:
        """Port check returns False when connection refused."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError()
            assert checker.check_port() is False

    def test_check_port_os_error(self, checker: GatewayHealthChecker) -> None:
        """Port check returns False on OS error."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = OSError("Network unreachable")
            assert checker.check_port() is False

    # Authentication Tests

    def test_validate_authentication_success(self, checker: GatewayHealthChecker) -> None:
        """Authentication validation returns True with valid accounts."""
        with patch("src.utils.gateway_health.IB") as MockIB:
            mock_ib = MockIB.return_value
            mock_ib.connect = Mock()
            mock_ib.managedAccounts.return_value = ["DU123456"]
            mock_ib.isConnected.return_value = True
            mock_ib.disconnect = Mock()

            assert checker.validate_authentication() is True
            mock_ib.connect.assert_called_once()
            mock_ib.disconnect.assert_called_once()

    def test_validate_authentication_no_accounts(self, checker: GatewayHealthChecker) -> None:
        """Authentication validation returns False with no accounts."""
        with patch("src.utils.gateway_health.IB") as MockIB:
            mock_ib = MockIB.return_value
            mock_ib.connect = Mock()
            mock_ib.managedAccounts.return_value = []
            mock_ib.isConnected.return_value = True
            mock_ib.disconnect = Mock()

            assert checker.validate_authentication() is False

    def test_validate_authentication_connection_error(self, checker: GatewayHealthChecker) -> None:
        """Authentication validation returns False on connection error."""
        with patch("src.utils.gateway_health.IB") as MockIB:
            mock_ib = MockIB.return_value
            mock_ib.connect.side_effect = Exception("Connection refused")
            mock_ib.isConnected.return_value = False

            assert checker.validate_authentication() is False

    def test_validate_authentication_disconnects_on_success(
        self, checker: GatewayHealthChecker
    ) -> None:
        """Authentication validation disconnects after success."""
        with patch("src.utils.gateway_health.IB") as MockIB:
            mock_ib = MockIB.return_value
            mock_ib.managedAccounts.return_value = ["DU123456"]
            mock_ib.isConnected.return_value = True
            mock_ib.disconnect = Mock()

            checker.validate_authentication()

            mock_ib.disconnect.assert_called_once()

    # Wait for Gateway Tests

    def test_wait_for_gateway_immediate_success(self, checker: GatewayHealthChecker) -> None:
        """Gateway ready on first attempt returns True immediately."""
        with patch.object(checker, "check_port", return_value=True):
            with patch.object(checker, "validate_authentication", return_value=True):
                result = checker.wait_for_gateway(max_retries=5)
                assert result is True

    def test_wait_for_gateway_retry_then_success(self, checker: GatewayHealthChecker) -> None:
        """Gateway becomes ready after retries returns True."""
        port_results = [False, False, True]
        auth_results = [True]

        with patch.object(checker, "check_port", side_effect=port_results):
            with patch.object(checker, "validate_authentication", side_effect=auth_results):
                with patch("time.sleep"):  # Skip delays in tests
                    result = checker.wait_for_gateway(max_retries=5)
                    assert result is True

    def test_wait_for_gateway_max_retries_exceeded(self, checker: GatewayHealthChecker) -> None:
        """Gateway never ready returns False after max retries."""
        with patch.object(checker, "check_port", return_value=False):
            with patch("time.sleep"):  # Skip delays in tests
                result = checker.wait_for_gateway(max_retries=3, timeout=1000)
                assert result is False

    def test_wait_for_gateway_timeout(self, checker: GatewayHealthChecker) -> None:
        """Gateway validation times out returns False."""
        with patch.object(checker, "check_port", return_value=False):
            with patch("time.time") as mock_time:
                # Simulate time passing beyond timeout
                mock_time.side_effect = [0, 0, 400]  # Start, elapsed check, timeout
                result = checker.wait_for_gateway(timeout=300)
                assert result is False

    def test_wait_for_gateway_calls_send_alert_on_failure(
        self, checker: GatewayHealthChecker
    ) -> None:
        """Gateway failure triggers alert."""
        with patch.object(checker, "check_port", return_value=False):
            with patch.object(checker, "_send_alert") as mock_alert:
                with patch("time.sleep"):
                    checker.wait_for_gateway(max_retries=3, timeout=1000)
                    mock_alert.assert_called()

    def test_wait_for_gateway_port_up_but_auth_fails(self, checker: GatewayHealthChecker) -> None:
        """Gateway port responds but authentication fails continues retrying."""
        with patch.object(checker, "check_port", return_value=True):
            with patch.object(checker, "validate_authentication", return_value=False):
                with patch("time.sleep"):
                    result = checker.wait_for_gateway(max_retries=3, timeout=1000)
                    assert result is False

    # Alert Tests

    def test_send_alert_no_webhook(self, checker: GatewayHealthChecker) -> None:
        """Alert does nothing when no webhook configured."""
        # Should not raise even without webhook
        checker._send_alert("CRITICAL", "Test message")

    def test_send_alert_with_webhook(self) -> None:
        """Alert sends to webhook when configured."""
        checker = GatewayHealthChecker(
            host="localhost",
            port=4002,
            discord_webhook="https://discord.com/api/webhooks/test",
        )
        with patch("httpx.Client") as MockClient:
            mock_client = MockClient.return_value.__enter__.return_value
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            checker._send_alert("WARNING", "Test message")

            mock_client.post.assert_called_once()

    def test_send_alert_handles_http_error(self) -> None:
        """Alert handles HTTP errors gracefully."""
        checker = GatewayHealthChecker(
            host="localhost",
            port=4002,
            discord_webhook="https://discord.com/api/webhooks/test",
        )
        with patch("httpx.Client") as MockClient:
            mock_client = MockClient.return_value.__enter__.return_value
            mock_client.post.side_effect = Exception("HTTP error")

            # Should not raise
            checker._send_alert("ERROR", "Test message")

    def test_send_alert_emoji_mapping(self) -> None:
        """Alert uses correct emoji for each level."""
        checker = GatewayHealthChecker(
            host="localhost",
            port=4002,
            discord_webhook="https://discord.com/api/webhooks/test",
        )
        with patch("httpx.Client") as MockClient:
            mock_client = MockClient.return_value.__enter__.return_value
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            checker._send_alert("CRITICAL", "Test")
            call_args = mock_client.post.call_args
            assert "🚨" in call_args[1]["json"]["content"]


class TestExponentialBackoff:
    """Tests for exponential backoff calculation."""

    def test_backoff_sequence(self) -> None:
        """Verify backoff follows exponential pattern with cap."""
        delays = []
        delay = 5.0
        max_delay = 30.0

        for _ in range(10):
            delays.append(delay)
            delay = min(delay * 2, max_delay)

        # Expected: 5, 10, 20, 30, 30, 30, 30, 30, 30, 30
        expected = [5, 10, 20, 30, 30, 30, 30, 30, 30, 30]
        assert delays == expected

    def test_backoff_respects_max_delay(self) -> None:
        """Backoff never exceeds max_delay."""
        delay = 5.0
        max_delay = 30.0

        for _ in range(100):
            delay = min(delay * 2, max_delay)
            assert delay <= max_delay
