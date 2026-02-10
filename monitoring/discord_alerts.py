"""
Discord webhook integration with severity-based formatting.
Sends formatted alerts to Discord channel.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import requests  # type: ignore[import-untyped]

from config import MonitorConfig  # type: ignore[attr-defined]
from models import AlertSeverity

logger = logging.getLogger(__name__)


def send_discord_alert(
    config: MonitorConfig,
    severity: AlertSeverity,
    title: str,
    message: str,
    fields: dict[str, Any] | None = None,
    ping_operator: bool = False,
) -> bool:
    """
    Send formatted Discord webhook alert with severity-based styling.

    Args:
        config: Monitoring configuration
        severity: Alert severity level (INFO, WARNING, ERROR, CRITICAL)
        title: Alert title
        message: Alert message body
        fields: Optional key-value pairs to display as embed fields
        ping_operator: Whether to @mention operator (CRITICAL alerts)

    Returns:
        True if alert sent successfully, False otherwise
    """
    # Severity color mapping (Discord embed colors)
    colors = {
        AlertSeverity.INFO: 0x00FF00,  # Green
        AlertSeverity.WARNING: 0xFFFF00,  # Yellow
        AlertSeverity.ERROR: 0xFF0000,  # Red
        AlertSeverity.CRITICAL: 0xFF0000,  # Red
    }

    # Severity emoji mapping
    emojis = {
        AlertSeverity.INFO: "🟢",
        AlertSeverity.WARNING: "🟡",
        AlertSeverity.ERROR: "🔴",
        AlertSeverity.CRITICAL: "🚨",
    }

    # Build embed
    embed = {
        "title": f"{emojis.get(severity, '')} {title}",
        "description": message,
        "color": colors.get(severity, 0x808080),  # Gray for unknown severity
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": f"Charter & Stone Health Monitor | {severity.value}"},
    }

    # Add optional fields
    if fields:
        embed["fields"] = [
            {"name": str(k), "value": str(v), "inline": True} for k, v in fields.items()
        ]

    # Build content (for @mentions)
    content = ""
    if ping_operator and config.discord_operator_mention:
        content = f"<@{config.discord_operator_mention}>"

    # Build payload
    payload = {"content": content, "embeds": [embed]}

    # Send webhook
    try:
        response = requests.post(config.discord_webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"Discord alert sent: {severity.value} - {title}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Discord alert: {e}")
        # Don't fail monitoring if Discord is down - just log
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending Discord alert: {e}")
        return False


def send_startup_alert(config: MonitorConfig) -> None:
    """
    Send startup notification to Discord.

    Args:
        config: Monitoring configuration
    """
    send_discord_alert(
        config=config,
        severity=AlertSeverity.INFO,
        title="Health Monitoring Started",
        message="Health monitoring system started and watching Gateway.",
        fields={
            "Gateway Container": config.gateway_container_name,
            "Gateway Port": config.gateway_port,
            "Check Interval": f"{config.health_check_interval_seconds}s",
        },
    )


def send_gateway_down_alert(config: MonitorConfig, container_name: str, port: int) -> None:
    """
    Send Gateway down alert.

    Args:
        config: Monitoring configuration
        container_name: Gateway container name
        port: Gateway port
    """
    send_discord_alert(
        config=config,
        severity=AlertSeverity.ERROR,
        title="Gateway Down",
        message="IBKR Gateway container is not running or port is unresponsive.",
        fields={
            "Container": container_name,
            "Expected Port": port,
            "Action": "Attempting auto-recovery...",
        },
    )


def send_gateway_recovery_success_alert(config: MonitorConfig, container_name: str) -> None:
    """
    Send Gateway recovery success alert.

    Args:
        config: Monitoring configuration
        container_name: Gateway container name
    """
    send_discord_alert(
        config=config,
        severity=AlertSeverity.INFO,
        title="Gateway Recovery Successful",
        message="Gateway container restarted and port is now responding.",
        fields={
            "Container": container_name,
            "Recovery Time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
    )


def send_gateway_recovery_failed_alert(config: MonitorConfig, container_name: str) -> None:
    """
    Send Gateway recovery failure alert with operator ping.

    Args:
        config: Monitoring configuration
        container_name: Gateway container name
    """
    send_discord_alert(
        config=config,
        severity=AlertSeverity.CRITICAL,
        title="Gateway Recovery Failed",
        message="Automatic Gateway restart failed. Manual intervention required.",
        fields={
            "Container": container_name,
            "Action Required": "Operator must investigate Gateway logs and restart manually",
        },
        ping_operator=True,
    )


def send_gateway_degraded_alert(
    config: MonitorConfig,
    memory_mb: float,
    warning_threshold: int,
    critical_threshold: int,
) -> None:
    """
    Send Gateway memory usage warning alert.

    Args:
        config: Monitoring configuration
        memory_mb: Current memory usage in MB
        warning_threshold: Warning threshold in MB
        critical_threshold: Critical threshold in MB
    """
    send_discord_alert(
        config=config,
        severity=AlertSeverity.WARNING,
        title="Gateway Memory Usage High",
        message="Gateway container memory usage approaching leak threshold.",
        fields={
            "Memory Usage": f"{memory_mb:.1f} MB",
            "Warning Threshold": f"{warning_threshold} MB",
            "Critical Threshold": f"{critical_threshold} MB",
            "Recommended Action": "Monitor closely. Gateway will auto-restart at scheduled time (4:30 PM).",
        },
    )


def send_monitoring_error_alert(config: MonitorConfig, error_message: str) -> None:
    """
    Send monitoring system error alert.

    Args:
        config: Monitoring configuration
        error_message: Error description
    """
    send_discord_alert(
        config=config,
        severity=AlertSeverity.ERROR,
        title="Monitoring System Error",
        message=f"Health monitoring system encountered an error: {error_message}",
        fields={
            "Action": "Monitoring will continue checking after recovery interval.",
        },
    )
