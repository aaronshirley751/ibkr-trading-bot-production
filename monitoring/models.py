"""
Data models for health monitoring system.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class AlertSeverity(str, Enum):
    """Alert severity levels for Discord notifications."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class GatewayHealthDetails:
    """Gateway health check details."""

    container_running: bool
    port_responding: bool
    memory_usage_mb: float | None
    container_status: str
    uptime_seconds: int
    memory_warning: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "container_running": self.container_running,
            "port_responding": self.port_responding,
            "memory_usage_mb": self.memory_usage_mb,
            "container_status": self.container_status,
            "uptime_seconds": self.uptime_seconds,
            "memory_warning": self.memory_warning,
        }


@dataclass
class BotHealthDetails:
    """Bot health check details."""

    process_running: bool
    last_heartbeat: datetime | None
    gateway_connected: bool | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "process_running": self.process_running,
            "last_heartbeat": (self.last_heartbeat.isoformat() if self.last_heartbeat else None),
            "gateway_connected": self.gateway_connected,
        }


@dataclass
class SystemHealthDetails:
    """System resource health details."""

    disk_usage_percent: float
    disk_free_gb: float
    docker_accessible: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "disk_usage_percent": self.disk_usage_percent,
            "disk_free_gb": self.disk_free_gb,
            "docker_accessible": self.docker_accessible,
        }
