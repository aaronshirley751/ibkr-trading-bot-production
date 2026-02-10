"""
Alert throttling to prevent Discord spam.
Tracks recent alerts and enforces cooldown periods.
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AlertThrottle:
    """
    Prevents alert spam by tracking recent alerts and enforcing cooldown periods.
    """

    def __init__(self, cooldown_seconds: int = 300):
        """
        Initialize alert throttle.

        Args:
            cooldown_seconds: Minimum time between identical alerts (default 5 min)
        """
        self.cooldown_seconds = cooldown_seconds
        self.last_alert_time: dict[str, datetime] = {}

    def should_throttle(self, alert_key: str) -> bool:
        """
        Check if this alert should be suppressed (sent recently).

        Args:
            alert_key: Unique identifier for the alert type

        Returns:
            True if alert should be throttled (suppressed)
            False if alert should be sent
        """
        if alert_key not in self.last_alert_time:
            return False

        last_time = self.last_alert_time[alert_key]
        elapsed = (datetime.now() - last_time).total_seconds()

        if elapsed < self.cooldown_seconds:
            logger.info(
                f"Throttling alert '{alert_key}' (sent {elapsed:.0f}s ago, "
                f"cooldown: {self.cooldown_seconds}s)"
            )
            return True

        return False

    def record_alert(self, alert_key: str) -> None:
        """
        Record that an alert was sent.

        Args:
            alert_key: Unique identifier for the alert type
        """
        self.last_alert_time[alert_key] = datetime.now()
        logger.debug(f"Recorded alert: {alert_key}")

    def clear_alert(self, alert_key: str) -> None:
        """
        Clear alert throttle (for recovery notifications).

        Args:
            alert_key: Unique identifier for the alert type
        """
        if alert_key in self.last_alert_time:
            del self.last_alert_time[alert_key]
            logger.debug(f"Cleared alert throttle: {alert_key}")

    def clear_all(self) -> None:
        """Clear all alert throttles (useful for testing)."""
        self.last_alert_time.clear()
        logger.debug("Cleared all alert throttles")

    def get_elapsed_since_last_alert(self, alert_key: str) -> float | None:
        """
        Get elapsed time since last alert of this type.

        Args:
            alert_key: Unique identifier for the alert type

        Returns:
            Elapsed seconds since last alert, or None if never sent
        """
        if alert_key not in self.last_alert_time:
            return None

        last_time = self.last_alert_time[alert_key]
        return (datetime.now() - last_time).total_seconds()
