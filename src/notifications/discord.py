"""
Discord webhook notification sender.

Provides structured alerts for trading system events with
proper formatting and severity-based color coding.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """
    Discord webhook notification sender.

    Sends embeds with severity-based colors and structured formatting.
    Gracefully degrades if webhook is not configured (log-only mode).
    """

    # Discord embed colors (decimal RGB values)
    COLORS = {
        "info": 3447003,  # Blue
        "warning": 16776960,  # Yellow
        "error": 16711680,  # Red
        "critical": 10038562,  # Dark red
    }

    def __init__(self, webhook_url: Optional[str], timeout: float = 10.0):
        """
        Initialize Discord notifier.

        Args:
            webhook_url: Discord webhook URL. If None, alerts are logged only.
            timeout: HTTP request timeout in seconds.
        """
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def send_info(self, message: str) -> bool:
        """
        Send info-level notification.

        Args:
            message: Notification message content.

        Returns:
            True if sent successfully, False otherwise.
        """
        return self._send("info", "ℹ️ Info", message)

    def send_warning(self, message: str) -> bool:
        """
        Send warning-level notification.

        Args:
            message: Notification message content.

        Returns:
            True if sent successfully, False otherwise.
        """
        return self._send("warning", "⚠️ Warning", message)

    def send_error(self, message: str) -> bool:
        """
        Send error-level notification.

        Args:
            message: Notification message content.

        Returns:
            True if sent successfully, False otherwise.
        """
        return self._send("error", "❌ Error", message)

    def send_critical(self, message: str) -> bool:
        """
        Send critical-level notification.

        Args:
            message: Notification message content.

        Returns:
            True if sent successfully, False otherwise.
        """
        return self._send("critical", "🚨 Critical", message)

    def _send(self, level: str, title: str, message: str) -> bool:
        """
        Send Discord webhook notification.

        Args:
            level: Alert level key (info, warning, error, critical).
            title: Embed title.
            message: Embed description.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.webhook_url:
            self.logger.warning(f"Discord webhook not configured — alert not sent: {message}")
            return False

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": self.COLORS.get(level, self.COLORS["info"]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "Charter & Stone Capital — The Crucible"},
                }
            ]
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                self.logger.debug(f"Discord alert sent: {message}")
                return True
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Discord webhook returned error: {e.response.status_code}")
            return False
        except httpx.RequestError as e:
            self.logger.error(f"Failed to send Discord alert: {e}")
            return False
