"""
Zero-touch startup orchestrator for production trading operations.

This module implements a state machine that coordinates:
1. Prerequisite validation (Docker, environment)
2. Gateway container lifecycle management
3. Gateway health validation
4. Gameplan loading and validation
5. Bot process launch
6. Failure recovery and alerting

Usage:
    poetry run python -m src.orchestration.startup

Exit Codes:
    0 - Success (bot running)
    1 - Failure (manual intervention required)
    2 - Partial success (Strategy C deployed, operator alerted)
"""

import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from src.notifications.discord import DiscordNotifier
from src.orchestration.config import OrchestrationConfig
from src.orchestration.gameplan import (
    generate_strategy_c,
    load_gameplan_json,
    validate_gameplan_schema,
)
from src.orchestration.health import GatewayHealthChecker

logger = logging.getLogger(__name__)


class StartupState(Enum):
    """Startup orchestration state machine states."""

    INITIALIZING = "initializing"
    GATEWAY_STARTING = "gateway_starting"
    GATEWAY_WAITING = "gateway_waiting"
    GATEWAY_VALIDATED = "gateway_validated"
    GAMEPLAN_LOADING = "gameplan_loading"
    BOT_STARTING = "bot_starting"
    BOT_RUNNING = "bot_running"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class StartupContext:
    """Tracks orchestration state across transitions."""

    state: StartupState
    gateway_healthy: bool = False
    gateway_restart_attempted: bool = False
    gameplan_path: Optional[Path] = None
    gameplan_valid: bool = False
    strategy_c_deployed: bool = False
    error_message: Optional[str] = None
    bot_pid: Optional[int] = None


class StartupOrchestrator:
    """
    Zero-touch startup coordinator for production trading operations.

    Responsibilities:
    - Gateway lifecycle management
    - Health validation
    - Gameplan validation
    - Bot initialization
    - Failure recovery
    - Operator notifications
    """

    def __init__(self, config: OrchestrationConfig):
        """
        Initialize orchestrator.

        Args:
            config: Orchestration configuration.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.notifier = DiscordNotifier(config.discord_webhook_url)
        self.health_checker = GatewayHealthChecker(
            host=config.gateway_host,
            port=config.gateway_port,
            timeout=config.health_check_timeout,
        )
        self.context = StartupContext(state=StartupState.INITIALIZING)

    def run(self) -> int:
        """
        Execute complete startup sequence.

        Returns:
            Exit code: 0 = success, 1 = failure, 2 = partial success (Strategy C)
        """
        try:
            self.logger.info("Starting zero-touch orchestration")
            self.notifier.send_info("🚀 Starting trading system startup")

            # State machine execution
            while self.context.state not in [
                StartupState.SUCCESS,
                StartupState.FAILURE,
            ]:
                self._transition()

            if self.context.state == StartupState.SUCCESS:
                self.logger.info("Startup orchestration complete — bot running")
                if self.context.strategy_c_deployed:
                    self.notifier.send_warning(
                        "⚠️ Trading system operational (Strategy C deployed)"
                    )
                    return 2  # Partial success
                else:
                    self.notifier.send_info("✅ Trading system operational")
                    return 0
            else:
                self.logger.error(f"Startup failed: {self.context.error_message}")
                self.notifier.send_critical(f"❌ Startup failed: {self.context.error_message}")
                return 1

        except Exception as e:
            self.logger.exception("Unexpected orchestration failure")
            self.notifier.send_critical(f"💥 Orchestrator crashed: {str(e)}")
            return 1

    def _transition(self) -> None:
        """Execute next state transition."""
        transitions = {
            StartupState.INITIALIZING: self._initialize,
            StartupState.GATEWAY_STARTING: self._start_gateway,
            StartupState.GATEWAY_WAITING: self._wait_for_gateway,
            StartupState.GATEWAY_VALIDATED: self._validate_gateway,
            StartupState.GAMEPLAN_LOADING: self._load_gameplan,
            StartupState.BOT_STARTING: self._start_bot,
            StartupState.BOT_RUNNING: self._finalize,
        }

        handler = transitions.get(self.context.state)
        if handler:
            handler()
        else:
            raise RuntimeError(f"No handler for state: {self.context.state}")

    def _initialize(self) -> None:
        """Validate prerequisites before attempting startup."""
        self.logger.info("Validating startup prerequisites")

        # Check 1: Docker available?
        if not self._docker_available():
            self.context.state = StartupState.FAILURE
            self.context.error_message = "Docker not available (is Docker Desktop running?)"
            return

        # Check 2: Gameplan path configured?
        if self.config.gameplan_path and self.config.gameplan_path.exists():
            self.context.gameplan_path = self.config.gameplan_path
        else:
            self.logger.warning(
                f"Gameplan not found at {self.config.gameplan_path} — " "will deploy Strategy C"
            )
            # Don't fail — we can proceed with Strategy C

        # Check 3: Discord webhook configured?
        if not self.config.discord_webhook_url:
            self.logger.warning("Discord webhook not configured — alerts will be logged only")

        # Check 4: Already running?
        if self._bot_already_running():
            self.context.state = StartupState.FAILURE
            self.context.error_message = "Bot already running (check process list)"
            return

        self.logger.info("Prerequisites validated — proceeding to Gateway startup")
        self.context.state = StartupState.GATEWAY_STARTING

    def _docker_available(self) -> bool:
        """Check if Docker CLI is available and responding."""
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            self.logger.error("Docker command timed out")
            return False
        except FileNotFoundError:
            self.logger.error("Docker CLI not found")
            return False

    def _bot_already_running(self) -> bool:
        """
        Check if bot process already exists.

        Uses psutil if available, falls back to basic check.
        """
        try:
            import psutil

            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline and "src.main" in " ".join(cmdline or []):
                        self.logger.warning(f"Bot already running (PID {proc.info['pid']})")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except ImportError:
            # psutil not available, skip this check
            self.logger.debug("psutil not available, skipping process check")
            return False

    def _start_gateway(self) -> None:
        """Ensure Gateway container is running."""
        self.logger.info("Checking Gateway container status")

        # Check if container exists and is running
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={self.config.gateway_container_name}",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if "Up" in result.stdout:
                self.logger.info("Gateway container already running")
                self.context.state = StartupState.GATEWAY_WAITING
                return
        except subprocess.TimeoutExpired:
            self.context.state = StartupState.FAILURE
            self.context.error_message = "Docker command timed out"
            return

        # Container not running — start it
        self.logger.info("Starting Gateway container")
        self.notifier.send_info("🔧 Starting IBKR Gateway")

        try:
            result = subprocess.run(
                ["docker", "compose", "up", "-d", "gateway"],
                cwd=self.config.docker_compose_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                self.context.state = StartupState.FAILURE
                self.context.error_message = f"Gateway container start failed: {result.stderr}"
                return

            self.logger.info("Gateway container started — waiting for health")
            self.context.state = StartupState.GATEWAY_WAITING

        except subprocess.TimeoutExpired:
            self.context.state = StartupState.FAILURE
            self.context.error_message = "Gateway container start timed out (>60s)"

    def _wait_for_gateway(self) -> None:
        """Poll Gateway until healthy or timeout."""
        self.logger.info("Waiting for Gateway to become healthy")

        timeout = self.config.gateway_health_timeout
        retry_interval = self.config.gateway_health_retry_interval
        max_attempts = timeout // retry_interval

        for attempt in range(1, max_attempts + 1):
            self.logger.debug(f"Gateway health check attempt {attempt}/{max_attempts}")

            # Check 1: Docker health status
            docker_healthy = self._check_docker_health()

            # Check 2: API port responding
            api_responsive = self.health_checker.check_api_port()

            if docker_healthy and api_responsive:
                self.logger.info(f"Gateway healthy after {attempt * retry_interval}s")
                self.context.gateway_healthy = True
                self.context.state = StartupState.GATEWAY_VALIDATED
                return

            if attempt < max_attempts:
                time.sleep(retry_interval)

        # Timeout reached — attempt recovery
        self.logger.warning("Gateway health timeout — attempting recovery")
        if not self.context.gateway_restart_attempted:
            self.context.gateway_restart_attempted = True
            self._restart_gateway()
            # Reset to waiting state to retry the wait loop
            self.context.state = StartupState.GATEWAY_WAITING
        else:
            self.context.state = StartupState.FAILURE
            self.context.error_message = (
                "Gateway failed to become healthy (timeout + restart failed)"
            )

    def _check_docker_health(self) -> bool:
        """Check Docker container health status."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}}",
                    self.config.gateway_container_name,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            health = result.stdout.strip()
            return health == "healthy"
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False

    def _restart_gateway(self) -> None:
        """Attempt Gateway container restart (one-time recovery)."""
        self.logger.warning("Attempting Gateway restart (auto-recovery)")
        self.notifier.send_warning("⚠️ Gateway not responding — attempting restart")

        try:
            result = subprocess.run(
                ["docker", "compose", "restart", "gateway"],
                cwd=self.config.docker_compose_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info("Gateway restart command succeeded — waiting for health")
            else:
                self.logger.error(f"Gateway restart failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            self.logger.error("Gateway restart timed out")

    def _validate_gateway(self) -> None:
        """Final Gateway validation before bot startup."""
        self.logger.info("Performing final Gateway validation")

        # Validation 1: API port responding
        if not self.health_checker.check_api_port():
            self.context.state = StartupState.FAILURE
            self.context.error_message = "Gateway API port not responding (validation failed)"
            return

        # Validation 2: Docker health check
        if not self._check_docker_health():
            self.context.state = StartupState.FAILURE
            self.context.error_message = "Gateway Docker health check failed (validation failed)"
            return

        self.logger.info("Gateway validation passed — proceeding to gameplan")
        self.context.state = StartupState.GAMEPLAN_LOADING

    def _load_gameplan(self) -> None:
        """Load and validate daily gameplan JSON."""
        self.logger.info("Loading daily gameplan")

        # Case 1: No gameplan path configured
        if not self.context.gameplan_path:
            self.logger.warning("No gameplan configured — deploying Strategy C")
            self.notifier.send_warning("⚠️ No gameplan found — Strategy C deployed")
            self._deploy_strategy_c()
            return

        # Case 2: Gameplan file missing
        if not self.context.gameplan_path.exists():
            self.logger.warning(f"Gameplan file not found: {self.context.gameplan_path}")
            self.notifier.send_warning("⚠️ Gameplan missing — Strategy C deployed")
            self._deploy_strategy_c()
            return

        # Case 3: Load and validate gameplan
        gameplan = load_gameplan_json(self.context.gameplan_path)

        if gameplan is None:
            self.logger.error("Failed to load gameplan JSON")
            self.notifier.send_error("❌ Failed to load gameplan — Strategy C deployed")
            self._deploy_strategy_c()
            return

        # Schema validation
        if not validate_gameplan_schema(gameplan):
            self.logger.error("Gameplan schema validation failed")
            self.notifier.send_error("❌ Invalid gameplan schema — Strategy C deployed")
            self._deploy_strategy_c()
            return

        # Data quarantine check
        data_quality = gameplan.get("data_quality", {})
        if data_quality.get("quarantine_active", False):
            self.logger.warning("Data quarantine active — forcing Strategy C")
            self.notifier.send_warning("⚠️ Data quarantine — Strategy C enforced")
            self._deploy_strategy_c()
            return

        self.logger.info(f"Gameplan loaded: Strategy {gameplan.get('strategy', '?')}")
        self.context.gameplan_valid = True
        self.context.state = StartupState.BOT_STARTING

    def _deploy_strategy_c(self) -> None:
        """Create emergency Strategy C gameplan."""
        strategy_c_path = self.config.emergency_gameplan_path
        generate_strategy_c(output_path=strategy_c_path)

        self.logger.info(f"Strategy C gameplan generated: {strategy_c_path}")
        self.context.gameplan_path = strategy_c_path
        self.context.gameplan_valid = True
        self.context.strategy_c_deployed = True
        self.context.state = StartupState.BOT_STARTING

    def _start_bot(self) -> None:
        """Launch bot process with validated configuration."""
        self.logger.info("Starting trading bot")
        self.notifier.send_info("🤖 Starting trading bot")

        # Build bot command
        cmd = [
            sys.executable,
            "-m",
            "src.main",
        ]

        # Set environment for the bot process
        import os

        env = os.environ.copy()
        env["GATEWAY_HOST"] = self.config.gateway_host
        env["GATEWAY_PORT"] = str(self.config.gateway_port)
        env["LOG_LEVEL"] = self.config.bot_log_level
        if self.context.gameplan_path:
            env["GAMEPLAN_PATH"] = str(self.context.gameplan_path)
        if self.config.discord_webhook_url:
            env["DISCORD_WEBHOOK_URL"] = self.config.discord_webhook_url

        try:
            # Start bot as background process
            # Orchestrator does NOT wait for bot to finish — it hands off control
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )

            # Give bot 5 seconds to crash on startup errors
            time.sleep(5)

            if process.poll() is not None:
                # Bot exited immediately — startup failed
                stderr = process.stderr.read() if process.stderr else ""
                stdout = process.stdout.read() if process.stdout else ""
                self.context.state = StartupState.FAILURE
                self.context.error_message = f"Bot startup failed: {stderr or stdout}"
                return

            self.logger.info(f"Bot started successfully (PID {process.pid})")
            self.context.bot_pid = process.pid
            self.context.state = StartupState.BOT_RUNNING

        except Exception as e:
            self.context.state = StartupState.FAILURE
            self.context.error_message = f"Bot start failed: {str(e)}"

    def _finalize(self) -> None:
        """Final state — orchestrator hands off to bot."""
        self.logger.info("Orchestration complete — bot operational")
        self.context.state = StartupState.SUCCESS


def main() -> None:
    """CLI entry point for orchestrator."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("=" * 60)
    logger.info("Charter & Stone Capital — Zero-Touch Startup Orchestrator")
    logger.info("Task 3.5: Production Automation")
    logger.info("=" * 60)

    config = OrchestrationConfig.from_env()
    orchestrator = StartupOrchestrator(config)
    exit_code = orchestrator.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
