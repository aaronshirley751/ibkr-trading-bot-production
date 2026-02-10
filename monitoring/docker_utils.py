"""
Docker SDK interactions for container health checks and management.
"""

import socket
import logging
import time
from datetime import datetime, timezone
from typing import Any

import docker
import docker.errors
from docker.errors import DockerException, NotFound
from dateutil import parser  # type: ignore[import-untyped]

from config import MonitorConfig  # type: ignore[attr-defined]
from models import GatewayHealthDetails, HealthStatus

logger = logging.getLogger(__name__)


def initialize_docker_client() -> Any:
    """
    Initialize Docker client from environment.

    Returns:
        Docker client instance

    Raises:
        DockerException: If Docker daemon is not accessible
    """
    try:
        client = docker.from_env()  # type: ignore[attr-defined]
        # Verify connection
        client.ping()
        logger.info("Docker client initialized successfully")
        return client
    except DockerException as e:
        logger.error(f"Failed to initialize Docker client: {e}")
        raise


def check_gateway_health(
    docker_client: Any, config: MonitorConfig
) -> tuple[HealthStatus, GatewayHealthDetails]:
    """
    Check Gateway container health via multiple validators.

    Args:
        docker_client: Docker SDK client
        config: Monitoring configuration

    Returns:
        Tuple of (status, details) where:
        - status: "healthy" | "degraded" | "down"
        - details: GatewayHealthDetails with check results
    """
    # Initialize details
    details = GatewayHealthDetails(
        container_running=False,
        port_responding=False,
        memory_usage_mb=None,
        container_status="unknown",
        uptime_seconds=0,
    )

    # Check 1: Container exists and is running
    try:
        # Use list(all=True) to find stopped containers too
        containers = docker_client.containers.list(
            all=True, filters={"name": config.gateway_container_name}
        )
        if not containers:
            logger.warning(f"Gateway container '{config.gateway_container_name}' not found")
            details.container_status = "not_found"
            return HealthStatus.DOWN, details

        container = containers[0]
        details.container_running = container.status == "running"
        details.container_status = container.status
        if details.container_running:
            details.uptime_seconds = calculate_uptime(container)
    except Exception as e:
        logger.error(f"Docker API error checking Gateway container: {e}")
        details.container_status = "error"
        return HealthStatus.DOWN, details

    # If container not running, Gateway is down
    if not details.container_running:
        logger.warning(f"Gateway container status: {details.container_status} (not running)")
        return HealthStatus.DOWN, details

    # Check 2: Port 4002 responding
    details.port_responding = check_port_connection(
        host=config.gateway_host,
        port=config.gateway_port,
        timeout=config.port_check_timeout_seconds,
    )

    # Check 3: Memory usage
    try:
        stats = container.stats(stream=False)
        memory_usage_bytes = stats["memory_stats"]["usage"]
        details.memory_usage_mb = memory_usage_bytes / (1024 * 1024)
        logger.debug(
            f"Gateway memory usage: {details.memory_usage_mb:.1f} MB "
            f"(uptime: {details.uptime_seconds}s)"
        )
    except Exception as e:
        logger.warning(f"Failed to get Gateway memory stats: {e}")
        details.memory_usage_mb = None

    # Determine status from checks
    if not details.port_responding:
        logger.error(
            f"Gateway port {config.gateway_port} not responding "
            f"(container running: {details.container_running})"
        )
        return HealthStatus.DOWN, details

    # Gateway is up, check if degraded (high memory)
    if details.memory_usage_mb is not None:
        if details.memory_usage_mb > config.memory_critical_mb:
            logger.warning(
                f"Gateway memory CRITICAL: {details.memory_usage_mb:.1f} MB "
                f"(threshold: {config.memory_critical_mb} MB)"
            )
            return HealthStatus.DEGRADED, details
        elif details.memory_usage_mb > config.memory_warning_mb:
            logger.warning(
                f"Gateway memory WARNING: {details.memory_usage_mb:.1f} MB "
                f"(threshold: {config.memory_warning_mb} MB)"
            )
            details.memory_warning = True

    logger.debug(
        f"Gateway health: HEALTHY (port: {config.gateway_port}, "
        f"memory: {details.memory_usage_mb:.1f} MB)"
    )
    return HealthStatus.HEALTHY, details


def check_port_connection(host: str, port: int, timeout: int) -> bool:
    """
    Test if Gateway port is accepting connections.

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        True if port is responding, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        success = result == 0
        if success:
            logger.debug(f"Port check: {host}:{port} responding")
        else:
            logger.warning(f"Port check: {host}:{port} not responding (code: {result})")
        return success
    except Exception as e:
        logger.error(f"Port check error for {host}:{port}: {e}")
        return False


def calculate_uptime(container: Any) -> int:
    """
    Calculate container uptime in seconds.

    Args:
        container: Docker container object

    Returns:
        Uptime in seconds
    """
    try:
        started_at = container.attrs["State"]["StartedAt"]
        started_time = parser.isoparse(started_at)
        now = datetime.now(timezone.utc)
        uptime = (now - started_time).total_seconds()
        return int(uptime)
    except Exception as e:
        logger.warning(f"Failed to calculate container uptime: {e}")
        return 0


def attempt_gateway_restart(docker_client: Any, config: MonitorConfig) -> bool:
    """
    Attempt to restart Gateway container.

    Args:
        docker_client: Docker SDK client
        config: Monitoring configuration

    Returns:
        True if restart successful and port responding
        False if restart failed or port still unresponsive
    """
    try:
        # Find container even if stopped
        containers = docker_client.containers.list(
            all=True, filters={"name": config.gateway_container_name}
        )
        if not containers:
            logger.error(
                f"Gateway container '{config.gateway_container_name}' not found - cannot restart"
            )
            return False

        container = containers[0]

        # If stopped, start it; if running, restart it
        if container.status == "running":
            logger.info(f"Restarting Gateway container '{config.gateway_container_name}'")
            container.restart(timeout=config.gateway_restart_timeout_seconds)
        else:
            logger.info(
                f"Starting stopped Gateway container '{config.gateway_container_name}' "
                f"(current status: {container.status})"
            )
            container.start()

        # Wait for Gateway to be ready (give it time to initialize)
        for attempt in range(config.gateway_ready_max_attempts):
            logger.info(
                f"Waiting for Gateway to be ready (attempt {attempt + 1}/"
                f"{config.gateway_ready_max_attempts})..."
            )
            time.sleep(config.gateway_ready_check_interval_seconds)

            if check_port_connection(
                host=config.gateway_host,
                port=config.gateway_port,
                timeout=config.port_check_timeout_seconds,
            ):
                logger.info(f"Gateway restart successful - port {config.gateway_port} responding")
                return True

        logger.error(
            f"Gateway restarted but port {config.gateway_port} not responding after "
            f"{config.gateway_ready_max_attempts * config.gateway_ready_check_interval_seconds}s timeout"
        )
        return False

    except Exception as e:
        logger.error(f"Gateway restart/start failed: {e}")
        return False


def check_bot_container(docker_client: Any, config: MonitorConfig) -> tuple[str, dict[str, Any]]:
    """
    Check bot health via Docker container status.

    Args:
        docker_client: Docker SDK client
        config: Monitoring configuration

    Returns:
        Tuple of (status, details) where status is "running" | "stopped" | "unknown"
    """
    try:
        container = docker_client.containers.get(config.bot_container_name)
        status = "running" if container.status == "running" else "stopped"
        details = {
            "container_status": container.status,
            "uptime_seconds": calculate_uptime(container) if status == "running" else 0,
        }
        return status, details
    except NotFound:
        logger.warning(f"Bot container '{config.bot_container_name}' not found")
        return "unknown", {"container_status": "not_found"}
    except Exception as e:
        logger.error(f"Error checking bot container: {e}")
        return "unknown", {"error": str(e)}
