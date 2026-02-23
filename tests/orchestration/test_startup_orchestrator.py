"""
Unit tests for the startup orchestrator.

Tests cover:
- State machine transitions
- Timeout logic
- Restart recovery
- Strategy C fallback
- Error handling
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.orchestration.config import OrchestrationConfig
from src.orchestration.startup import (
    StartupOrchestrator,
    StartupState,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_config(tmp_path: Path) -> OrchestrationConfig:
    """Create a test configuration."""
    return OrchestrationConfig(
        gateway_host="localhost",
        gateway_port=4002,
        docker_compose_dir=tmp_path / "docker",
        gateway_health_timeout=10,  # Short timeout for tests
        gateway_health_retry_interval=1,
        health_check_timeout=1,
        gameplan_path=tmp_path / "gameplan.json",
        emergency_gameplan_path=tmp_path / "state" / "emergency_gameplan.json",
        discord_webhook_url=None,
        bot_log_level="DEBUG",
        gateway_container_name="test-gateway",
    )


@pytest.fixture
def orchestrator(mock_config: OrchestrationConfig) -> StartupOrchestrator:
    """Create orchestrator instance with mocked dependencies."""
    return StartupOrchestrator(mock_config)


# =============================================================================
# STATE TRANSITIONS
# =============================================================================


class TestStateTransitions:
    """Test state machine transitions."""

    def test_initial_state_is_initializing(self, orchestrator: StartupOrchestrator) -> None:
        """Orchestrator starts in INITIALIZING state."""
        assert orchestrator.context.state == StartupState.INITIALIZING

    @patch.object(StartupOrchestrator, "_docker_available", return_value=False)
    def test_docker_unavailable_transitions_to_failure(
        self,
        mock_docker: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Missing Docker causes FAILURE state."""
        orchestrator._initialize()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "Docker not available" in (orchestrator.context.error_message or "")

    @patch.object(StartupOrchestrator, "_docker_available", return_value=True)
    @patch.object(StartupOrchestrator, "_bot_already_running", return_value=False)
    def test_valid_prerequisites_transition_to_gateway_starting(
        self,
        mock_bot: MagicMock,
        mock_docker: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Valid prerequisites transition to GATEWAY_STARTING."""
        orchestrator._initialize()

        assert orchestrator.context.state == StartupState.GATEWAY_STARTING

    @patch.object(StartupOrchestrator, "_docker_available", return_value=True)
    @patch.object(StartupOrchestrator, "_bot_already_running", return_value=True)
    def test_bot_already_running_transitions_to_failure(
        self,
        mock_bot: MagicMock,
        mock_docker: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Bot already running causes FAILURE state."""
        orchestrator._initialize()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "already running" in (orchestrator.context.error_message or "")


# =============================================================================
# GATEWAY STARTUP
# =============================================================================


class TestGatewayStartup:
    """Test Gateway container startup logic."""

    @patch("subprocess.run")
    def test_gateway_already_running_skips_startup(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Gateway already running skips to GATEWAY_WAITING."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Up 5 minutes",
        )

        orchestrator._start_gateway()

        assert orchestrator.context.state == StartupState.GATEWAY_WAITING

    @patch("subprocess.run")
    def test_gateway_start_success(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Successful Gateway startup transitions to GATEWAY_WAITING."""
        # First call: check if running (not running)
        # Second call: docker compose up -d
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        orchestrator._start_gateway()

        assert orchestrator.context.state == StartupState.GATEWAY_WAITING

    @patch("subprocess.run")
    def test_gateway_start_failure(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Failed Gateway startup transitions to FAILURE."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # Not running
            MagicMock(returncode=1, stdout="", stderr="Error starting"),
        ]

        orchestrator._start_gateway()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "start failed" in (orchestrator.context.error_message or "")

    @patch("subprocess.run")
    def test_docker_timeout_transitions_to_failure(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Docker command timeout transitions to FAILURE."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=10)

        orchestrator._start_gateway()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "timed out" in (orchestrator.context.error_message or "")


# =============================================================================
# GATEWAY WAITING & HEALTH
# =============================================================================


class TestGatewayWaiting:
    """Test Gateway health waiting logic."""

    @patch.object(StartupOrchestrator, "_check_docker_health", return_value=True)
    @patch(
        "src.orchestration.startup.GatewayHealthChecker.check_api_port",
        return_value=True,
    )
    def test_gateway_becomes_healthy(
        self,
        mock_port: MagicMock,
        mock_docker: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Healthy Gateway transitions to GATEWAY_VALIDATED."""
        orchestrator._wait_for_gateway()

        assert orchestrator.context.state == StartupState.GATEWAY_VALIDATED
        assert orchestrator.context.gateway_healthy is True

    @patch("time.sleep")
    @patch.object(StartupOrchestrator, "_check_docker_health", return_value=False)
    @patch.object(StartupOrchestrator, "_restart_gateway")
    @patch(
        "src.orchestration.startup.GatewayHealthChecker.check_api_port",
        return_value=False,
    )
    def test_gateway_timeout_triggers_restart(
        self,
        mock_port: MagicMock,
        mock_restart: MagicMock,
        mock_docker: MagicMock,
        mock_sleep: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Gateway timeout triggers restart attempt."""
        orchestrator._wait_for_gateway()

        assert orchestrator.context.gateway_restart_attempted is True
        mock_restart.assert_called_once()

    @patch("time.sleep")
    @patch.object(StartupOrchestrator, "_check_docker_health", return_value=False)
    @patch.object(StartupOrchestrator, "_restart_gateway")
    @patch(
        "src.orchestration.startup.GatewayHealthChecker.check_api_port",
        return_value=False,
    )
    def test_gateway_timeout_after_restart_fails(
        self,
        mock_port: MagicMock,
        mock_restart: MagicMock,
        mock_docker: MagicMock,
        mock_sleep: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Gateway timeout after restart transitions to FAILURE."""
        orchestrator.context.gateway_restart_attempted = True

        orchestrator._wait_for_gateway()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "restart failed" in (orchestrator.context.error_message or "")


# =============================================================================
# GATEWAY VALIDATION
# =============================================================================


class TestGatewayValidation:
    """Test final Gateway validation."""

    @patch.object(StartupOrchestrator, "_check_docker_health", return_value=True)
    @patch(
        "src.orchestration.startup.GatewayHealthChecker.check_api_port",
        return_value=True,
    )
    def test_validation_success(
        self,
        mock_port: MagicMock,
        mock_docker: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Successful validation transitions to GAMEPLAN_LOADING."""
        orchestrator._validate_gateway()

        assert orchestrator.context.state == StartupState.GAMEPLAN_LOADING

    @patch(
        "src.orchestration.startup.GatewayHealthChecker.check_api_port",
        return_value=False,
    )
    def test_validation_fails_port_not_responding(
        self,
        mock_port: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Port not responding causes FAILURE."""
        orchestrator._validate_gateway()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "not responding" in (orchestrator.context.error_message or "")

    @patch.object(StartupOrchestrator, "_check_docker_health", return_value=False)
    @patch(
        "src.orchestration.startup.GatewayHealthChecker.check_api_port",
        return_value=True,
    )
    def test_validation_fails_docker_health(
        self,
        mock_port: MagicMock,
        mock_docker: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Docker health check failure causes FAILURE."""
        orchestrator._validate_gateway()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "health check failed" in (orchestrator.context.error_message or "")


# =============================================================================
# GAMEPLAN LOADING
# =============================================================================


class TestGameplanLoading:
    """Test gameplan loading and validation."""

    def test_missing_gameplan_deploys_strategy_c(
        self,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Missing gameplan deploys Strategy C."""
        orchestrator.context.gameplan_path = None

        orchestrator._load_gameplan()

        assert orchestrator.context.state == StartupState.BOT_STARTING
        assert orchestrator.context.strategy_c_deployed is True

    def test_nonexistent_gameplan_file_deploys_strategy_c(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Non-existent gameplan file deploys Strategy C."""
        orchestrator.context.gameplan_path = tmp_path / "nonexistent.json"

        orchestrator._load_gameplan()

        assert orchestrator.context.state == StartupState.BOT_STARTING
        assert orchestrator.context.strategy_c_deployed is True

    def test_valid_gameplan_loads_successfully(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Valid gameplan loads and transitions to BOT_STARTING."""
        import json

        gameplan_path = tmp_path / "valid_gameplan.json"
        gameplan = {
            "strategy": "A",
            "regime": "trending",
            "symbols": ["SPY"],
            "hard_limits": {"max_daily_loss_pct": 2.0},
            "data_quality": {"quarantine_active": False},
        }
        gameplan_path.write_text(json.dumps(gameplan))

        orchestrator.context.gameplan_path = gameplan_path

        orchestrator._load_gameplan()

        assert orchestrator.context.state == StartupState.BOT_STARTING
        assert orchestrator.context.gameplan_valid is True
        assert orchestrator.context.strategy_c_deployed is False

    def test_quarantined_gameplan_deploys_strategy_c(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Gameplan with quarantine_active deploys Strategy C."""
        import json

        gameplan_path = tmp_path / "quarantined_gameplan.json"
        gameplan = {
            "strategy": "A",
            "regime": "trending",
            "hard_limits": {"max_daily_loss_pct": 2.0},
            "data_quality": {"quarantine_active": True},
        }
        gameplan_path.write_text(json.dumps(gameplan))

        orchestrator.context.gameplan_path = gameplan_path

        orchestrator._load_gameplan()

        assert orchestrator.context.state == StartupState.BOT_STARTING
        assert orchestrator.context.strategy_c_deployed is True

    def test_invalid_json_deploys_strategy_c(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Invalid JSON deploys Strategy C."""
        gameplan_path = tmp_path / "invalid.json"
        gameplan_path.write_text("{ invalid json }")

        orchestrator.context.gameplan_path = gameplan_path

        orchestrator._load_gameplan()

        assert orchestrator.context.state == StartupState.BOT_STARTING
        assert orchestrator.context.strategy_c_deployed is True


# =============================================================================
# BOT STARTING
# =============================================================================


class TestBotStarting:
    """Test bot process launch."""

    @patch("subprocess.Popen")
    @patch("time.sleep")
    def test_bot_starts_successfully(
        self,
        mock_sleep: MagicMock,
        mock_popen: MagicMock,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Successful bot start transitions to BOT_RUNNING."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        orchestrator.context.gameplan_path = tmp_path / "gameplan.json"

        orchestrator._start_bot()

        assert orchestrator.context.state == StartupState.BOT_RUNNING
        assert orchestrator.context.bot_pid == 12345

    @patch("subprocess.Popen")
    @patch("time.sleep")
    def test_bot_crashes_immediately(
        self,
        mock_sleep: MagicMock,
        mock_popen: MagicMock,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Bot crashing immediately transitions to FAILURE."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Exited with error
        mock_process.stderr.read.return_value = "Import error"
        mock_process.stdout.read.return_value = ""
        mock_popen.return_value = mock_process

        orchestrator.context.gameplan_path = tmp_path / "gameplan.json"

        orchestrator._start_bot()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "startup failed" in (orchestrator.context.error_message or "")


# =============================================================================
# FINALIZATION
# =============================================================================


class TestFinalization:
    """Test orchestration finalization."""

    def test_finalize_sets_success_state(self, orchestrator: StartupOrchestrator) -> None:
        """Finalize transitions to SUCCESS."""
        orchestrator._finalize()

        assert orchestrator.context.state == StartupState.SUCCESS


# =============================================================================
# FULL RUN TESTS
# =============================================================================


class TestFullRun:
    """Test full orchestration run."""

    @patch.object(StartupOrchestrator, "_start_bot")
    @patch.object(StartupOrchestrator, "_load_gameplan")
    @patch.object(StartupOrchestrator, "_validate_gateway")
    @patch.object(StartupOrchestrator, "_wait_for_gateway")
    @patch.object(StartupOrchestrator, "_start_gateway")
    @patch.object(StartupOrchestrator, "_initialize")
    def test_successful_run_returns_zero(
        self,
        mock_init: MagicMock,
        mock_start_gw: MagicMock,
        mock_wait_gw: MagicMock,
        mock_validate_gw: MagicMock,
        mock_load_gp: MagicMock,
        mock_start_bot: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Successful run returns exit code 0."""

        def advance_init() -> None:
            orchestrator.context.state = StartupState.GATEWAY_STARTING

        def advance_start_gw() -> None:
            orchestrator.context.state = StartupState.GATEWAY_WAITING

        def advance_wait_gw() -> None:
            orchestrator.context.state = StartupState.GATEWAY_VALIDATED

        def advance_validate_gw() -> None:
            orchestrator.context.state = StartupState.GAMEPLAN_LOADING

        def advance_load_gp() -> None:
            orchestrator.context.state = StartupState.BOT_STARTING

        def advance_start_bot() -> None:
            orchestrator.context.state = StartupState.BOT_RUNNING

        mock_init.side_effect = advance_init
        mock_start_gw.side_effect = advance_start_gw
        mock_wait_gw.side_effect = advance_wait_gw
        mock_validate_gw.side_effect = advance_validate_gw
        mock_load_gp.side_effect = advance_load_gp
        mock_start_bot.side_effect = advance_start_bot

        exit_code = orchestrator.run()

        assert exit_code == 0

    @patch.object(StartupOrchestrator, "_initialize")
    def test_failure_returns_one(
        self,
        mock_init: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Failed run returns exit code 1."""

        def fail_init() -> None:
            orchestrator.context.state = StartupState.FAILURE
            orchestrator.context.error_message = "Test failure"

        mock_init.side_effect = fail_init

        exit_code = orchestrator.run()

        assert exit_code == 1

    @patch.object(StartupOrchestrator, "_start_bot")
    @patch.object(StartupOrchestrator, "_load_gameplan")
    @patch.object(StartupOrchestrator, "_validate_gateway")
    @patch.object(StartupOrchestrator, "_wait_for_gateway")
    @patch.object(StartupOrchestrator, "_start_gateway")
    @patch.object(StartupOrchestrator, "_initialize")
    def test_strategy_c_deployed_returns_two(
        self,
        mock_init: MagicMock,
        mock_start_gw: MagicMock,
        mock_wait_gw: MagicMock,
        mock_validate_gw: MagicMock,
        mock_load_gp: MagicMock,
        mock_start_bot: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Strategy C deployment returns exit code 2."""

        def advance_init() -> None:
            orchestrator.context.state = StartupState.GATEWAY_STARTING

        def advance_start_gw() -> None:
            orchestrator.context.state = StartupState.GATEWAY_WAITING

        def advance_wait_gw() -> None:
            orchestrator.context.state = StartupState.GATEWAY_VALIDATED

        def advance_validate_gw() -> None:
            orchestrator.context.state = StartupState.GAMEPLAN_LOADING

        def advance_load_gp() -> None:
            orchestrator.context.state = StartupState.BOT_STARTING
            orchestrator.context.strategy_c_deployed = True

        def advance_start_bot() -> None:
            orchestrator.context.state = StartupState.BOT_RUNNING

        mock_init.side_effect = advance_init
        mock_start_gw.side_effect = advance_start_gw
        mock_wait_gw.side_effect = advance_wait_gw
        mock_validate_gw.side_effect = advance_validate_gw
        mock_load_gp.side_effect = advance_load_gp
        mock_start_bot.side_effect = advance_start_bot

        exit_code = orchestrator.run()

        assert exit_code == 2
