"""
Unit tests for failure recovery scenarios.

Tests cover:
- Docker unavailable
- Gateway timeout
- Invalid gameplan
- Missing gameplan
- Bot start failure
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.orchestration.config import OrchestrationConfig
from src.orchestration.startup import StartupOrchestrator, StartupState

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
        gateway_health_timeout=5,
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
# DOCKER UNAVAILABLE
# =============================================================================


class TestDockerUnavailable:
    """Test Docker availability failures."""

    @patch("subprocess.run")
    def test_docker_not_installed(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Docker CLI not found causes FAILURE."""
        mock_run.side_effect = FileNotFoundError("docker not found")

        result = orchestrator._docker_available()

        assert result is False

    @patch("subprocess.run")
    def test_docker_daemon_not_running(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Docker daemon not running causes FAILURE."""
        mock_run.return_value = MagicMock(returncode=1)

        result = orchestrator._docker_available()

        assert result is False

    @patch("subprocess.run")
    def test_docker_command_timeout(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Docker command timeout causes FAILURE."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=10)

        result = orchestrator._docker_available()

        assert result is False

    @patch("subprocess.run")
    def test_docker_available_success(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Docker available returns True."""
        mock_run.return_value = MagicMock(returncode=0)

        result = orchestrator._docker_available()

        assert result is True


# =============================================================================
# GATEWAY TIMEOUT
# =============================================================================


class TestGatewayTimeout:
    """Test Gateway timeout scenarios."""

    @patch("time.sleep")
    @patch.object(StartupOrchestrator, "_restart_gateway")
    @patch.object(StartupOrchestrator, "_check_docker_health", return_value=False)
    @patch(
        "src.orchestration.startup.GatewayHealthChecker.check_api_port",
        return_value=False,
    )
    def test_timeout_triggers_restart_once(
        self,
        mock_port: MagicMock,
        mock_docker: MagicMock,
        mock_restart: MagicMock,
        mock_sleep: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Gateway timeout triggers exactly one restart attempt."""
        # First timeout
        orchestrator._wait_for_gateway()
        assert orchestrator.context.gateway_restart_attempted is True
        assert mock_restart.call_count == 1

        # Second timeout (after restart already attempted)
        mock_restart.reset_mock()
        orchestrator._wait_for_gateway()
        assert orchestrator.context.state == StartupState.FAILURE
        assert mock_restart.call_count == 0

    @patch("subprocess.run")
    def test_restart_command_executes(
        self,
        mock_run: MagicMock,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """Restart command is executed correctly."""
        mock_run.return_value = MagicMock(returncode=0)

        orchestrator._restart_gateway()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "docker" in call_args[0][0]
        assert "restart" in call_args[0][0]


# =============================================================================
# INVALID GAMEPLAN
# =============================================================================


class TestInvalidGameplan:
    """Test invalid gameplan scenarios."""

    def test_invalid_json_syntax(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Invalid JSON syntax deploys Strategy C."""
        gameplan_path = tmp_path / "invalid.json"
        gameplan_path.write_text("{ not valid json }")
        orchestrator.context.gameplan_path = gameplan_path

        orchestrator._load_gameplan()

        assert orchestrator.context.strategy_c_deployed is True
        assert orchestrator.context.state == StartupState.BOT_STARTING

    def test_missing_required_fields(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Missing required fields deploys Strategy C."""
        import json

        gameplan_path = tmp_path / "incomplete.json"
        gameplan = {"strategy": "A"}  # Missing regime, hard_limits, data_quality
        gameplan_path.write_text(json.dumps(gameplan))
        orchestrator.context.gameplan_path = gameplan_path

        orchestrator._load_gameplan()

        assert orchestrator.context.strategy_c_deployed is True
        assert orchestrator.context.state == StartupState.BOT_STARTING

    def test_invalid_strategy_value(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Invalid strategy value deploys Strategy C."""
        import json

        gameplan_path = tmp_path / "invalid_strategy.json"
        gameplan = {
            "strategy": "X",  # Invalid
            "regime": "trending",
            "hard_limits": {},
            "data_quality": {},
        }
        gameplan_path.write_text(json.dumps(gameplan))
        orchestrator.context.gameplan_path = gameplan_path

        orchestrator._load_gameplan()

        assert orchestrator.context.strategy_c_deployed is True


# =============================================================================
# MISSING GAMEPLAN
# =============================================================================


class TestMissingGameplan:
    """Test missing gameplan scenarios."""

    def test_no_gameplan_path_configured(
        self,
        orchestrator: StartupOrchestrator,
    ) -> None:
        """No gameplan path deploys Strategy C."""
        orchestrator.context.gameplan_path = None

        orchestrator._load_gameplan()

        assert orchestrator.context.strategy_c_deployed is True
        assert orchestrator.context.state == StartupState.BOT_STARTING

    def test_gameplan_file_not_found(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Missing gameplan file deploys Strategy C."""
        orchestrator.context.gameplan_path = tmp_path / "nonexistent.json"

        orchestrator._load_gameplan()

        assert orchestrator.context.strategy_c_deployed is True

    def test_emergency_gameplan_is_created(
        self,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Emergency gameplan file is created."""
        orchestrator.context.gameplan_path = None
        emergency_path = tmp_path / "state" / "emergency.json"
        orchestrator.config.emergency_gameplan_path = emergency_path

        orchestrator._load_gameplan()

        assert emergency_path.exists()


# =============================================================================
# BOT START FAILURE
# =============================================================================


class TestBotStartFailure:
    """Test bot startup failure scenarios."""

    @patch("subprocess.Popen")
    @patch("time.sleep")
    def test_bot_import_error(
        self,
        mock_sleep: MagicMock,
        mock_popen: MagicMock,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Bot import error is captured and reported."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 1
        mock_process.stderr.read.return_value = "ImportError: No module named 'foo'"
        mock_process.stdout.read.return_value = ""
        mock_popen.return_value = mock_process
        orchestrator.context.gameplan_path = tmp_path / "gameplan.json"

        orchestrator._start_bot()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "ImportError" in (orchestrator.context.error_message or "")

    @patch("subprocess.Popen")
    def test_popen_exception(
        self,
        mock_popen: MagicMock,
        orchestrator: StartupOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Popen exception is captured and reported."""
        mock_popen.side_effect = OSError("Cannot spawn process")
        orchestrator.context.gameplan_path = tmp_path / "gameplan.json"

        orchestrator._start_bot()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "spawn" in (orchestrator.context.error_message or "").lower()


# =============================================================================
# NOTIFICATION FAILURES
# =============================================================================


class TestNotificationFailures:
    """Test notification failure handling (graceful degradation)."""

    @patch.object(StartupOrchestrator, "_docker_available", return_value=False)
    def test_continues_without_webhook(
        self,
        mock_docker: MagicMock,
        mock_config: OrchestrationConfig,
    ) -> None:
        """Orchestrator continues when webhook not configured."""
        mock_config.discord_webhook_url = None
        orchestrator = StartupOrchestrator(mock_config)

        # Should not raise even without webhook
        orchestrator._initialize()

        # Should fail due to docker, not notification
        assert orchestrator.context.state == StartupState.FAILURE
        assert "Docker" in (orchestrator.context.error_message or "")
