"""
Gateway health validation for orchestration.

This module provides lightweight health checking capabilities
for the startup orchestrator. For full Gateway health checking
with authentication validation, see src/utils/gateway_health.py.
"""

import logging
import socket

logger = logging.getLogger(__name__)


class GatewayHealthChecker:
    """
    Gateway health validation for orchestration.

    This is a lightweight checker focused on port availability.
    For full authentication validation, the orchestrator delegates
    to the bot's own health checking logic after launch.
    """

    def __init__(
        self,
        host: str,
        port: int,
        timeout: int = 5,
    ):
        """
        Initialize health checker.

        Args:
            host: Gateway hostname or IP address.
            port: Gateway API port (typically 4002 for paper trading).
            timeout: Socket connection timeout in seconds.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def check_api_port(self) -> bool:
        """
        Check if Gateway API port is responding.

        Returns:
            True if port is reachable, False otherwise.
        """
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout):
                self.logger.debug(f"Gateway API port {self.port} responding")
                return True
        except (socket.timeout, socket.error, OSError) as e:
            self.logger.debug(f"Gateway API port {self.port} not responding: {e}")
            return False

    def get_health_status(self) -> dict[str, bool | str | int]:
        """
        Get comprehensive health status.

        Returns:
            Dictionary with health check results.
        """
        port_available = self.check_api_port()

        return {
            "port_available": port_available,
            "host": self.host,
            "port": self.port,
            "status": "healthy" if port_available else "unhealthy",
        }
