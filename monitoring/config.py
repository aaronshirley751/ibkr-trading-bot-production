"""
Configuration module for health monitoring system.
Loads settings from environment variables with validation.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MonitorConfig(BaseSettings):
    """Health monitoring system configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Discord Integration
    discord_webhook_url: str = Field(..., description="Discord webhook URL for alerts")
    discord_operator_mention: str | None = Field(
        None, description="Discord user ID for @mentions in CRITICAL alerts"
    )

    # Gateway Configuration
    gateway_container_name: str = Field(
        default="gateway", description="Docker container name for IBKR Gateway"
    )
    gateway_host: str = Field(
        default="gateway",
        description="Hostname or IP for Gateway (use 'gateway' for Docker network)",
    )
    gateway_port: int = Field(default=4002, description="IBKR Gateway API port")
    gateway_restart_timeout_seconds: int = Field(
        default=30, description="Timeout for Gateway container restart command"
    )
    gateway_ready_max_attempts: int = Field(
        default=12, description="Max attempts to check if Gateway port responds after restart"
    )
    gateway_ready_check_interval_seconds: int = Field(
        default=5, description="Interval between port checks after restart"
    )

    # Health Check Configuration
    health_check_interval_seconds: int = Field(
        default=60, description="How often to check Gateway health"
    )
    port_check_timeout_seconds: int = Field(
        default=3, description="Timeout for port connection test"
    )
    error_recovery_interval_seconds: int = Field(
        default=120, description="Sleep duration after monitoring errors"
    )

    # Memory Thresholds
    memory_warning_mb: int = Field(default=1536, description="Memory usage warning threshold (MB)")
    memory_critical_mb: int = Field(
        default=1740, description="Memory usage critical threshold (MB)"
    )

    # Alert Throttling
    alert_cooldown_seconds: int = Field(
        default=300, description="Minimum time between duplicate alerts"
    )

    # Bot Monitoring (Optional - MVP defaults to disabled)
    monitor_bot_health: bool = Field(default=False, description="Enable bot health checks")
    bot_deployment_mode: str = Field(
        default="none", description="Bot deployment type: none | container | heartbeat"
    )
    bot_container_name: str = Field(
        default="trading-bot", description="Docker container name for bot"
    )
    bot_heartbeat_file: str = Field(
        default="/data/bot_heartbeat.json", description="Path to bot heartbeat file"
    )

    # System Monitoring (Optional)
    monitor_system_health: bool = Field(
        default=False, description="Enable system resource monitoring"
    )
    disk_warning_percent: int = Field(
        default=80, description="Disk usage warning threshold (percent)"
    )

    @field_validator("discord_webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        """Validate Discord webhook URL format."""
        if not v.startswith("https://discord.com/api/webhooks/"):
            raise ValueError(
                "discord_webhook_url must be a valid Discord webhook URL "
                "(https://discord.com/api/webhooks/...)"
            )
        return v

    @field_validator("bot_deployment_mode")
    @classmethod
    def validate_bot_deployment_mode(cls, v: str) -> str:
        """Validate bot deployment mode."""
        valid_modes = {"none", "container", "heartbeat"}
        if v not in valid_modes:
            raise ValueError(f"bot_deployment_mode must be one of {valid_modes}, got: {v}")
        return v


# Global config instance (loaded once at startup)
config: MonitorConfig | None = None


def load_config() -> MonitorConfig:
    """
    Load configuration from environment variables.

    Returns:
        MonitorConfig instance

    Raises:
        ValidationError: If required config is missing or invalid
    """
    global config
    if config is None:
        config = MonitorConfig()  # type: ignore[call-arg]
    return config
