"""
Orchestration configuration management.

Provides centralized configuration for the startup orchestrator,
loading values from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class OrchestrationConfig:
    """Configuration for startup orchestrator."""

    # Gateway connection
    gateway_host: str = "localhost"
    gateway_port: int = 4002

    # Docker paths
    docker_compose_dir: Path = field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "docker"
    )

    # Gateway health check
    gateway_health_timeout: int = 120  # seconds
    gateway_health_retry_interval: int = 5  # seconds
    health_check_timeout: int = 5  # seconds per check

    # Gameplan
    gameplan_path: Optional[Path] = None
    emergency_gameplan_path: Path = field(
        default_factory=lambda: Path(__file__).parent.parent.parent
        / "state"
        / "emergency_gameplan.json"
    )

    # Bot configuration
    bot_log_level: str = "INFO"

    # Notifications
    discord_webhook_url: Optional[str] = None

    # Container name
    gateway_container_name: str = "ibkr-gateway"

    @classmethod
    def from_env(cls) -> "OrchestrationConfig":
        """Load configuration from environment variables."""
        # Resolve docker_compose_dir
        default_docker_dir = Path(__file__).parent.parent.parent / "docker"
        docker_compose_dir_str = os.getenv("DOCKER_COMPOSE_DIR")
        docker_compose_dir = (
            Path(docker_compose_dir_str) if docker_compose_dir_str else default_docker_dir
        )

        # Resolve gameplan_path
        gameplan_path_str = os.getenv("GAMEPLAN_PATH")
        gameplan_path = Path(gameplan_path_str) if gameplan_path_str else None

        # Resolve emergency_gameplan_path
        default_emergency_path = (
            Path(__file__).parent.parent.parent / "state" / "emergency_gameplan.json"
        )
        emergency_path_str = os.getenv("EMERGENCY_GAMEPLAN_PATH")
        emergency_gameplan_path = (
            Path(emergency_path_str) if emergency_path_str else default_emergency_path
        )

        return cls(
            gateway_host=os.getenv("GATEWAY_HOST", "localhost"),
            gateway_port=int(os.getenv("GATEWAY_PORT", "4002")),
            docker_compose_dir=docker_compose_dir,
            gateway_health_timeout=int(os.getenv("GATEWAY_HEALTH_TIMEOUT", "120")),
            gateway_health_retry_interval=int(os.getenv("GATEWAY_HEALTH_RETRY_INTERVAL", "5")),
            health_check_timeout=int(os.getenv("HEALTH_CHECK_TIMEOUT", "5")),
            gameplan_path=gameplan_path,
            emergency_gameplan_path=emergency_gameplan_path,
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
            bot_log_level=os.getenv("BOT_LOG_LEVEL", "INFO"),
            gateway_container_name=os.getenv("GATEWAY_CONTAINER_NAME", "ibkr-gateway"),
        )
