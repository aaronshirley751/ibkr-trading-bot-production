"""
Unit tests for Gateway health validation.

Tests cover:
- Port checking
- Health status reporting
"""

from unittest.mock import MagicMock, patch

import pytest

from src.orchestration.health import GatewayHealthChecker

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def health_checker() -> GatewayHealthChecker:
    """Create health checker instance."""
    return GatewayHealthChecker(
        host="localhost",
        port=4002,
        timeout=5,
    )


# =============================================================================
# PORT CHECKING
# =============================================================================


class TestPortChecking:
    """Test API port checking."""

    @patch("socket.create_connection")
    def test_port_available_returns_true(
        self,
        mock_socket: MagicMock,
        health_checker: GatewayHealthChecker,
    ) -> None:
        """Available port returns True."""
        mock_socket.return_value.__enter__ = MagicMock()
        mock_socket.return_value.__exit__ = MagicMock()

        result = health_checker.check_api_port()

        assert result is True

    @patch("socket.create_connection")
    def test_port_unavailable_returns_false(
        self,
        mock_socket: MagicMock,
        health_checker: GatewayHealthChecker,
    ) -> None:
        """Unavailable port returns False."""
        import socket

        mock_socket.side_effect = socket.error("Connection refused")

        result = health_checker.check_api_port()

        assert result is False

    @patch("socket.create_connection")
    def test_port_timeout_returns_false(
        self,
        mock_socket: MagicMock,
        health_checker: GatewayHealthChecker,
    ) -> None:
        """Port timeout returns False."""
        import socket

        mock_socket.side_effect = socket.timeout("Connection timed out")

        result = health_checker.check_api_port()

        assert result is False

    @patch("socket.create_connection")
    def test_os_error_returns_false(
        self,
        mock_socket: MagicMock,
        health_checker: GatewayHealthChecker,
    ) -> None:
        """OSError returns False."""
        mock_socket.side_effect = OSError("Network unreachable")

        result = health_checker.check_api_port()

        assert result is False


# =============================================================================
# HEALTH STATUS
# =============================================================================


class TestHealthStatus:
    """Test comprehensive health status."""

    @patch.object(GatewayHealthChecker, "check_api_port", return_value=True)
    def test_healthy_status(
        self,
        mock_port: MagicMock,
        health_checker: GatewayHealthChecker,
    ) -> None:
        """Healthy status when port available."""
        status = health_checker.get_health_status()

        assert status["port_available"] is True
        assert status["status"] == "healthy"
        assert status["host"] == "localhost"
        assert status["port"] == 4002

    @patch.object(GatewayHealthChecker, "check_api_port", return_value=False)
    def test_unhealthy_status(
        self,
        mock_port: MagicMock,
        health_checker: GatewayHealthChecker,
    ) -> None:
        """Unhealthy status when port unavailable."""
        status = health_checker.get_health_status()

        assert status["port_available"] is False
        assert status["status"] == "unhealthy"


# =============================================================================
# CONSTRUCTOR
# =============================================================================


class TestConstructor:
    """Test health checker initialization."""

    def test_default_timeout(self) -> None:
        """Default timeout is applied."""
        checker = GatewayHealthChecker(host="test", port=1234)

        assert checker.timeout == 5

    def test_custom_timeout(self) -> None:
        """Custom timeout is applied."""
        checker = GatewayHealthChecker(host="test", port=1234, timeout=30)

        assert checker.timeout == 30

    def test_host_and_port_stored(self) -> None:
        """Host and port are stored correctly."""
        checker = GatewayHealthChecker(host="gateway.local", port=8080)

        assert checker.host == "gateway.local"
        assert checker.port == 8080
