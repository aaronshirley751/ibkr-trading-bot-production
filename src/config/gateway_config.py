"""
Gateway configuration module.

Provides configuration for IBKR Gateway connection and orchestration.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GatewayConfig:
    """
    Configuration for IBKR Gateway connection.

    Attributes:
        host: Gateway hostname (e.g., 'gateway', 'localhost')
        port: Gateway API port (4002 for paper, 4001 for live)
        client_id: IB API client ID (must be unique per connection)
        startup_timeout: Maximum seconds to wait for Gateway at startup
        max_retries: Maximum retry attempts before giving up
        retry_interval: Initial delay between retries (seconds)
        discord_webhook_url: Optional Discord webhook for alerts
    """

    host: str
    port: int
    client_id: int = 1
    startup_timeout: float = 300.0
    max_retries: int = 30
    retry_interval: float = 5.0
    discord_webhook_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """
        Load Gateway configuration from environment variables.

        Environment Variables:
            GATEWAY_HOST: Gateway hostname (required)
            GATEWAY_PORT: Gateway API port (required)
            CLIENT_ID: IB API client ID (default: 1)
            GATEWAY_STARTUP_TIMEOUT: Max startup wait time (default: 300)
            GATEWAY_MAX_RETRIES: Max retry attempts (default: 30)
            GATEWAY_RETRY_INTERVAL: Initial retry delay (default: 5.0)
            DISCORD_WEBHOOK_URL: Discord webhook URL (optional)

        Returns:
            GatewayConfig instance loaded from environment.

        Raises:
            ValueError: If required environment variables are missing.
        """
        host = os.getenv("GATEWAY_HOST")
        port_str = os.getenv("GATEWAY_PORT")

        if not host:
            raise ValueError("GATEWAY_HOST environment variable is required")
        if not port_str:
            raise ValueError("GATEWAY_PORT environment variable is required")

        try:
            port = int(port_str)
        except ValueError as e:
            raise ValueError(f"GATEWAY_PORT must be an integer: {port_str}") from e

        return cls(
            host=host,
            port=port,
            client_id=int(os.getenv("CLIENT_ID", "1")),
            startup_timeout=float(os.getenv("GATEWAY_STARTUP_TIMEOUT", "300.0")),
            max_retries=int(os.getenv("GATEWAY_MAX_RETRIES", "30")),
            retry_interval=float(os.getenv("GATEWAY_RETRY_INTERVAL", "5.0")),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        )


# Default configuration for local development
DEFAULT_GATEWAY_CONFIG = GatewayConfig(
    host="localhost",
    port=4002,
    client_id=1,
    startup_timeout=300.0,
    max_retries=30,
    retry_interval=5.0,
    discord_webhook_url=None,
)
