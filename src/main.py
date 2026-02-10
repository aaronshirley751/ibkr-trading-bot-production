"""
Bot main entry point with Gateway orchestration.

This module implements the bot startup sequence:
1. Load configuration from environment
2. Wait for Gateway readiness (with retries)
3. Validate Gateway authentication
4. Initialize trading modules
5. Load daily gameplan
6. Execute trading loop

Safety Constraint: Bot NEVER attempts to trade without validated Gateway.
All failure paths result in Strategy C activation or startup failure with alerts.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import GatewayConfig, RiskConfig, DEFAULT_RISK_CONFIG
from src.utils.gateway_health import GatewayHealthChecker

logger = logging.getLogger(__name__)

# Bot version
BOT_VERSION = "3.2.0"


def setup_logging(level: str = "INFO") -> None:
    """
    Configure structured logging for the bot.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def load_gateway_config() -> GatewayConfig:
    """
    Load Gateway configuration from environment.

    Returns:
        GatewayConfig instance.

    Raises:
        ValueError: If required configuration is missing.
    """
    try:
        return GatewayConfig.from_env()
    except ValueError as e:
        logger.critical(f"Configuration error: {e}")
        raise


def create_strategy_c_gameplan() -> Dict[str, Any]:
    """
    Create a Strategy C (cash preservation) gameplan.

    This is the default safe state when no gameplan exists
    or Gateway validation fails.

    Returns:
        Dictionary representing Strategy C gameplan.
    """
    return {
        "date": "auto-generated",
        "strategy": "C",
        "regime": "safe",
        "symbols": [],
        "hard_limits": {
            "max_daily_loss_pct": 0.0,
            "max_single_position": 0,
        },
        "data_quality": {"quarantine_active": False},
    }


def load_gameplan(gameplan_path: Optional[Path]) -> Dict[str, Any]:
    """
    Load daily gameplan from JSON file.

    Args:
        gameplan_path: Path to gameplan JSON file.

    Returns:
        Gameplan dictionary, or Strategy C gameplan if file doesn't exist.
    """
    if gameplan_path is None or not gameplan_path.exists():
        logger.warning(f"No gameplan found at {gameplan_path}, using Strategy C")
        return create_strategy_c_gameplan()

    try:
        import json

        with open(gameplan_path, "r") as f:
            gameplan: Dict[str, Any] = json.load(f)
        logger.info(f"Loaded gameplan from {gameplan_path}")
        return gameplan
    except Exception as e:
        logger.error(f"Failed to load gameplan: {e}, using Strategy C")
        return create_strategy_c_gameplan()


def run_trading_loop(
    gateway_config: GatewayConfig,
    risk_config: RiskConfig,
    gameplan: Dict[str, Any],
    health_checker: GatewayHealthChecker,
) -> None:
    """
    Execute main trading loop.

    This is a placeholder for the full trading implementation.
    Future iterations will integrate with:
    - IBKRGateway (src.integrations.ibkr_gateway)
    - Strategy execution (src.strategy.execution)
    - Risk management (src.risk)

    Args:
        gateway_config: Gateway configuration.
        risk_config: Risk management configuration.
        gameplan: Daily gameplan dictionary.
        health_checker: Gateway health checker instance.
    """
    import time

    logger.info("Trading loop started")
    logger.info(f"Active strategy: {gameplan.get('strategy', 'unknown')}")
    logger.info(f"Target symbols: {gameplan.get('symbols', [])}")

    strategy = gameplan.get("strategy", "C")

    # Strategy C: Cash preservation mode - keep bot alive with periodic health checks
    if strategy == "C":
        logger.info("Strategy C active: Cash preservation mode - monitoring only")
        logger.info("Bot initialized successfully and ready for trading logic")
        health_check_interval = 300  # 5 minutes

        while True:
            try:
                # Periodic health check (lightweight port check)
                logger.debug("Performing periodic Gateway health check...")
                is_healthy = health_checker.check_port(timeout=10.0)
                if is_healthy:
                    logger.debug("Gateway health check passed")
                else:
                    logger.warning("Gateway health check failed, will retry")
                time.sleep(health_check_interval)
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                raise
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    else:
        # TODO: Implement full trading loop integration for Strategies A and B
        # This will be expanded in future tasks to include:
        # 1. IBKRGateway initialization
        # 2. Market data fetching
        # 3. Signal evaluation
        # 4. Order execution
        # 5. Position management
        # 6. Periodic Gateway health checks
        logger.info("Trading loop placeholder - full implementation pending")
        logger.info("Bot initialized successfully and ready for trading logic")

        # Keep alive for non-Strategy-C modes as well (placeholder)
        while True:
            time.sleep(60)
            logger.debug("Trading loop heartbeat (placeholder mode)")


def main() -> None:
    """
    Bot entry point with Gateway orchestration.

    Startup Sequence:
    1. Parse configuration from environment
    2. Initialize logging
    3. Wait for Gateway readiness (with retries)
    4. Validate Gateway authentication
    5. Load gameplan
    6. Start trading loop
    """
    # Phase 1: Configuration and Logging
    import os

    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    logger.info("=" * 60)
    logger.info(f"Charter & Stone Capital Trading Bot v{BOT_VERSION}")
    logger.info("Task 3.2: Gateway Orchestration")
    logger.info("=" * 60)

    try:
        gateway_config = load_gateway_config()
    except ValueError:
        logger.critical("Failed to load configuration, cannot start bot")
        sys.exit(1)

    logger.info(f"Configuration loaded: Gateway at {gateway_config.host}:{gateway_config.port}")
    logger.info(f"Dry-run mode: {os.getenv('DRY_RUN', 'true')}")

    # Phase 2: Gateway Readiness Validation (Bot-side)
    health_checker = GatewayHealthChecker(
        host=gateway_config.host,
        port=gateway_config.port,
        discord_webhook=gateway_config.discord_webhook_url,
        client_id=100,  # TASK-3.4.1: Use unique client ID to avoid conflicts
    )

    logger.info("Beginning Gateway validation...")

    if not health_checker.wait_for_gateway(
        max_retries=gateway_config.max_retries,
        initial_delay=gateway_config.retry_interval,
        timeout=gateway_config.startup_timeout,
    ):
        logger.critical("Gateway validation failed, cannot start bot")
        sys.exit(1)

    logger.info("✓ Gateway validated successfully")

    # Phase 3: Load Risk Configuration
    risk_config = DEFAULT_RISK_CONFIG
    logger.info("Risk configuration loaded")

    # Phase 4: Load Gameplan
    gameplan_path_str = os.getenv("GAMEPLAN_PATH", "/data/gameplan.json")
    gameplan_path = Path(gameplan_path_str)
    gameplan = load_gameplan(gameplan_path)

    if gameplan.get("strategy") == "C":
        logger.warning("⚠️  Strategy C active - cash preservation mode")
    else:
        logger.info(f"✓ Strategy {gameplan.get('strategy')} active")

    # Phase 5: Trading Loop
    try:
        run_trading_loop(
            gateway_config=gateway_config,
            risk_config=risk_config,
            gameplan=gameplan,
            health_checker=health_checker,
        )
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.critical(f"Unexpected error in trading loop: {e}", exc_info=True)
        if gateway_config.discord_webhook_url:
            health_checker._send_alert("CRITICAL", f"Bot crashed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
