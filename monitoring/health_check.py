"""
Main health monitoring loop for IBKR Gateway.
Continuously validates Gateway health and sends Discord alerts.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Any

from docker.errors import DockerException

from alert_throttle import AlertThrottle
from config import MonitorConfig, load_config  # type: ignore[attr-defined]
from discord_alerts import (
    send_gateway_degraded_alert,
    send_gateway_down_alert,
    send_gateway_recovery_failed_alert,
    send_gateway_recovery_success_alert,
    send_monitoring_error_alert,
    send_startup_alert,
)
from docker_utils import (
    attempt_gateway_restart,
    check_gateway_health,
    initialize_docker_client,
)
from models import HealthStatus

# Configure structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "component": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)


def log_health_check(status: HealthStatus, details: dict[str, Any]) -> None:
    """
    Log health check result as structured JSON.

    Args:
        status: Health status
        details: Health check details
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "INFO",
        "component": "health_monitor",
        "message": "Gateway health check completed",
        "details": {"status": status.value, **details},
    }
    print(json.dumps(log_entry))


def handle_gateway_failure(
    docker_client: Any,
    config: MonitorConfig,
    alert_throttle: AlertThrottle,
) -> None:
    """
    Gateway is down - attempt auto-recovery, send alerts.

    Args:
        docker_client: Docker SDK client
        config: Monitoring configuration
        alert_throttle: Alert throttle instance
    """
    alert_key = "gateway_down"

    # Check if we've already alerted and attempted recovery recently
    if alert_throttle.should_throttle(alert_key):
        logger.info("Gateway down, but alert throttled (recently sent)")
        return

    # Send initial failure alert
    send_gateway_down_alert(
        config=config,
        container_name=config.gateway_container_name,
        port=config.gateway_port,
    )

    # Attempt Gateway restart (max 1 attempt per failure)
    recovery_success = attempt_gateway_restart(docker_client, config)

    if recovery_success:
        send_gateway_recovery_success_alert(
            config=config, container_name=config.gateway_container_name
        )
        alert_throttle.record_alert(alert_key)  # Throttle future alerts
    else:
        send_gateway_recovery_failed_alert(
            config=config, container_name=config.gateway_container_name
        )
        alert_throttle.record_alert(alert_key)


def handle_gateway_degradation(
    config: MonitorConfig, details: dict[str, Any], alert_throttle: AlertThrottle
) -> None:
    """
    Gateway is running but showing warning signs (high memory).

    Args:
        config: Monitoring configuration
        details: Gateway health details
        alert_throttle: Alert throttle instance
    """
    alert_key = "gateway_degraded"

    if alert_throttle.should_throttle(alert_key):
        return

    memory_mb = details.get("memory_usage_mb")
    if memory_mb is None:
        return

    send_gateway_degraded_alert(
        config=config,
        memory_mb=memory_mb,
        warning_threshold=config.memory_warning_mb,
        critical_threshold=config.memory_critical_mb,
    )

    alert_throttle.record_alert(alert_key)


def handle_gateway_recovery(alert_throttle: AlertThrottle) -> None:
    """
    Gateway recovered - clear alert throttles.

    Args:
        alert_throttle: Alert throttle instance
    """
    # Clear throttles so next failure triggers immediate alert
    alert_throttle.clear_alert("gateway_down")
    alert_throttle.clear_alert("gateway_degraded")


def main() -> None:
    """
    Main monitoring loop - runs continuously in container.
    """
    try:
        # Load configuration
        logger.info("Loading configuration from environment...")
        config = load_config()
        logger.info(
            f"Configuration loaded: gateway={config.gateway_container_name}, "
            f"port={config.gateway_port}, interval={config.health_check_interval_seconds}s"
        )
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    try:
        # Initialize Docker client
        logger.info("Initializing Docker client...")
        docker_client = initialize_docker_client()
    except DockerException as e:
        logger.error(f"Failed to initialize Docker client: {e}")
        send_monitoring_error_alert(config, f"Cannot access Docker API: {e}")
        sys.exit(1)

    # Initialize alert throttle
    alert_throttle = AlertThrottle(cooldown_seconds=config.alert_cooldown_seconds)

    # Send startup notification
    logger.info("Health monitoring system started")
    send_startup_alert(config)

    # Track previous status for state change detection
    previous_status = None

    # Main monitoring loop
    while True:
        try:
            # Phase 1: Check Gateway health
            status, details = check_gateway_health(docker_client, config)

            # Log health check result
            log_health_check(status, details.to_dict())

            # Phase 2: Handle Gateway status
            if status == HealthStatus.DOWN:
                if previous_status != HealthStatus.DOWN:
                    # State change: healthy/degraded -> down
                    logger.error("Gateway status changed to DOWN")
                handle_gateway_failure(docker_client, config, alert_throttle)
            elif status == HealthStatus.DEGRADED:
                if previous_status != HealthStatus.DEGRADED:
                    # State change: healthy -> degraded
                    logger.warning("Gateway status changed to DEGRADED")
                handle_gateway_degradation(config, details.to_dict(), alert_throttle)
            elif status == HealthStatus.HEALTHY:
                if previous_status in (HealthStatus.DOWN, HealthStatus.DEGRADED):
                    # State change: down/degraded -> healthy (recovery)
                    logger.info("Gateway status changed to HEALTHY (recovered)")
                    handle_gateway_recovery(alert_throttle)

            # Update previous status
            previous_status = status

            # Phase 3: Sleep until next check
            time.sleep(config.health_check_interval_seconds)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by operator (SIGINT)")
            sys.exit(0)
        except DockerException as e:
            logger.error(f"Docker API error during monitoring: {e}")
            send_monitoring_error_alert(config, f"Docker API error: {e}")
            time.sleep(config.error_recovery_interval_seconds)
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}", exc_info=True)
            send_monitoring_error_alert(config, str(e))
            time.sleep(config.error_recovery_interval_seconds)


if __name__ == "__main__":
    main()
