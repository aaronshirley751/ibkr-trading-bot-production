"""
Gateway health check utilities for bot startup orchestration.

This module provides:
- Port availability checking
- Gateway authentication validation
- Retry logic with exponential backoff
- Discord alerting integration
"""

import logging
import socket
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx  # type: ignore
from ib_insync import IB

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check attempt."""

    success: bool
    timestamp: datetime
    attempt: int
    message: str
    port_available: bool = False
    authenticated: bool = False


class GatewayHealthChecker:
    """
    Gateway health checker with retry logic and alerting.

    Usage:
        checker = GatewayHealthChecker(
            host="gateway",
            port=4002,
            discord_webhook="https://discord.com/api/webhooks/..."
        )
        if checker.wait_for_gateway():
            # Gateway is ready, proceed with trading
            ...
        else:
            # Gateway validation failed
            sys.exit(1)
    """

    def __init__(
        self,
        host: str,
        port: int,
        discord_webhook: Optional[str] = None,
        client_id: int = 100,  # TASK-3.4.1: Use unique client ID to avoid conflicts
    ):
        self.host = host
        self.port = port
        self.discord_webhook = discord_webhook
        self.client_id = client_id
        # Timeout increased from 10s to 60s for TWS API initialization
        self.connection_timeout = 60.0
        self._alert_thresholds = {3: "WARNING", 10: "ERROR"}

    def check_port(self, timeout: float = 5.0) -> bool:
        """
        Check if Gateway port is accepting connections.

        Args:
            timeout: Socket connection timeout in seconds.

        Returns:
            True if port is reachable, False otherwise.
        """
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout):
                return True
        except (socket.timeout, socket.error, OSError) as e:
            logger.debug(f"Port check failed: {e}")
            return False

    def validate_authentication(self, timeout: float = 60.0) -> bool:
        """
        Validate that Gateway is authenticated to IBKR.

        Connects via IB API and checks for accessible managed accounts.

        Args:
            timeout: IB API connection timeout in seconds (increased for Gateway TWS API init).

        Returns:
            True if authenticated, False otherwise.
        """
        ib = IB()  # type: ignore[no-untyped-call]
        try:
            ib.connect(
                self.host,
                self.port,
                clientId=self.client_id,
                timeout=timeout,
            )
            accounts = ib.managedAccounts()
            if accounts and len(accounts) > 0:
                logger.debug(f"Authentication validated, accounts: {accounts}")
                return True
            logger.warning("Connected but no managed accounts found")
            return False
        except Exception as e:
            logger.debug(f"Authentication validation failed: {e}")
            return False
        finally:
            if ib.isConnected():
                ib.disconnect()  # type: ignore

    def wait_for_gateway(
        self,
        max_retries: int = 30,
        initial_delay: float = 5.0,
        max_delay: float = 30.0,
        timeout: float = 300.0,
    ) -> bool:
        """
        Wait for Gateway to become ready with retry logic.

        Implements exponential backoff with configurable parameters.
        Sends Discord alerts at configured thresholds.

        Args:
            max_retries: Maximum number of retry attempts.
            initial_delay: Initial delay between retries (seconds).
            max_delay: Maximum delay between retries (seconds).
            timeout: Total timeout for all retries (seconds).

        Returns:
            True if Gateway became ready, False if validation failed.
        """
        start_time = time.time()
        attempt = 0
        delay = initial_delay

        while attempt < max_retries:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.error(f"Gateway validation timed out after {elapsed:.1f}s")
                self._send_alert(
                    "CRITICAL",
                    f"Gateway startup failed: timeout after {elapsed:.1f} seconds",
                )
                return False

            attempt += 1
            logger.info(
                f"Gateway check attempt {attempt}/{max_retries} " f"(elapsed: {elapsed:.1f}s)"
            )

            # Check port availability
            if self.check_port():
                logger.debug("Port check passed, validating authentication...")

                # Validate authentication
                if self.validate_authentication():
                    logger.info(
                        f"Gateway ready after {attempt} attempts " f"({elapsed:.1f}s elapsed)"
                    )
                    return True
                else:
                    logger.warning("Gateway port responding but authentication failed")
            else:
                logger.debug("Port check failed, Gateway not yet available")

            # Check alert thresholds
            if attempt in self._alert_thresholds:
                level = self._alert_thresholds[attempt]
                self._send_alert(
                    level,
                    f"Gateway startup delayed, attempt {attempt}/{max_retries}",
                )

            # Wait before next attempt (exponential backoff)
            actual_delay = min(delay, timeout - elapsed)
            if actual_delay > 0:
                logger.debug(f"Waiting {actual_delay:.1f}s before next attempt")
                time.sleep(actual_delay)
            delay = min(delay * 2, max_delay)

        # Max retries exceeded
        logger.critical(f"Gateway validation failed after {max_retries} attempts")
        self._send_alert("CRITICAL", f"Gateway startup failed after {max_retries} attempts")
        return False

    def _send_alert(self, level: str, message: str) -> None:
        """
        Send alert to Discord webhook.

        Args:
            level: Alert level (WARNING, ERROR, CRITICAL).
            message: Alert message content.
        """
        if not self.discord_webhook:
            logger.debug(f"Alert not sent (no webhook configured): [{level}] {message}")
            return

        emoji_map = {
            "WARNING": "⚠️",
            "ERROR": "🔴",
            "CRITICAL": "🚨",
            "INFO": "✅",
        }
        emoji = emoji_map.get(level, "ℹ️")

        payload = {
            "content": (
                f"{emoji} **{level}: Gateway Health Alert**\n\n"
                f"{message}\n\n"
                f"*Timestamp: {datetime.now().isoformat()}*"
            )
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.discord_webhook, json=payload)
                response.raise_for_status()
                logger.debug(f"Alert sent successfully: [{level}] {message}")
        except Exception as e:
            # Don't crash if alerting fails
            logger.error(f"Failed to send Discord alert: {e}")


def quick_check() -> bool:
    """
    Quick health check for Docker HEALTHCHECK command.

    Returns True if the bot considers itself healthy.
    This is a lightweight check, not a full Gateway validation.
    """
    # In a real implementation, this would check internal state
    # For now, just return True if the module loads
    return True
