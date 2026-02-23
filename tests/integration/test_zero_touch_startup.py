"""
Integration tests for zero-touch startup flow.

Tests cover:
- Full startup sequence with mocked Docker
- Gateway health validation
- Bot launch integration
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.orchestration.config import OrchestrationConfig
from src.orchestration.startup import StartupOrchestrator, StartupState

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def valid_gameplan(tmp_path: Path) -> Path:
    """Create a valid gameplan file."""
    gameplan_path = tmp_path / "gameplan.json"
    gameplan = {
        "date": "2026-02-10",
        "strategy": "A",
        "regime": "trending",
        "symbols": ["SPY"],
        "hard_limits": {
            "max_daily_loss_pct": 2.0,
            "max_single_position": 5,
        },
        "data_quality": {
            "quarantine_active": False,
            "min_volume": 1000,
            "max_spread_pct": 0.5,
        },
    }
    gameplan_path.write_text(json.dumps(gameplan))
    return gameplan_path


@pytest.fixture
def integration_config(tmp_path: Path, valid_gameplan: Path) -> OrchestrationConfig:
    """Create configuration for integration tests."""
    return OrchestrationConfig(
        gateway_host="localhost",
        gateway_port=4002,
        docker_compose_dir=tmp_path / "docker",
        gateway_health_timeout=5,
        gateway_health_retry_interval=1,
        health_check_timeout=1,
        gameplan_path=valid_gameplan,
        emergency_gameplan_path=tmp_path / "state" / "emergency_gameplan.json",
        discord_webhook_url=None,
        bot_log_level="DEBUG",
        gateway_container_name="test-gateway",
    )


# =============================================================================
# FULL STARTUP SEQUENCE
# =============================================================================


@pytest.mark.integration
class TestFullStartupSequence:
    """Test complete startup flow with mocked Docker."""

    @patch("src.orchestration.startup.GatewayHealthChecker.check_api_port", return_value=True)
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_successful_startup_with_valid_gameplan(
        self,
        mock_sleep: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        mock_health: MagicMock,
        integration_config: OrchestrationConfig,
    ) -> None:
        """Complete startup succeeds with valid gameplan."""
        # Mock Docker responses
        mock_run.side_effect = [
            # _docker_available
            MagicMock(returncode=0),
            # _start_gateway (check if running)
            MagicMock(returncode=0, stdout="Up 5 minutes"),
            # _check_docker_health (first call)
            MagicMock(returncode=0, stdout="healthy"),
            # _check_docker_health (validation)
            MagicMock(returncode=0, stdout="healthy"),
        ]

        # Mock bot process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        orchestrator = StartupOrchestrator(integration_config)
        exit_code = orchestrator.run()

        assert exit_code == 0
        assert orchestrator.context.state == StartupState.SUCCESS
        assert orchestrator.context.strategy_c_deployed is False

    @patch("src.orchestration.startup.GatewayHealthChecker.check_api_port", return_value=True)
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_startup_with_missing_gameplan_deploys_strategy_c(
        self,
        mock_sleep: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        mock_health: MagicMock,
        integration_config: OrchestrationConfig,
        tmp_path: Path,
    ) -> None:
        """Startup with missing gameplan deploys Strategy C."""
        integration_config.gameplan_path = tmp_path / "nonexistent.json"

        # Mock Docker responses
        mock_run.side_effect = [
            MagicMock(returncode=0),  # _docker_available
            MagicMock(returncode=0, stdout="Up 5 minutes"),  # _start_gateway
            MagicMock(returncode=0, stdout="healthy"),  # _check_docker_health
            MagicMock(returncode=0, stdout="healthy"),  # _check_docker_health
        ]

        # Mock bot process
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        orchestrator = StartupOrchestrator(integration_config)
        exit_code = orchestrator.run()

        assert exit_code == 2  # Partial success
        assert orchestrator.context.strategy_c_deployed is True

    @patch("subprocess.run")
    def test_startup_fails_with_docker_unavailable(
        self,
        mock_run: MagicMock,
        integration_config: OrchestrationConfig,
    ) -> None:
        """Startup fails when Docker is unavailable."""
        mock_run.return_value = MagicMock(returncode=1)

        orchestrator = StartupOrchestrator(integration_config)
        exit_code = orchestrator.run()

        assert exit_code == 1
        assert orchestrator.context.state == StartupState.FAILURE


# =============================================================================
# GATEWAY HEALTH VALIDATION
# =============================================================================


@pytest.mark.integration
class TestGatewayHealthValidation:
    """Test Gateway health validation flow."""

    @patch("src.orchestration.startup.GatewayHealthChecker.check_api_port")
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_gateway_startup_and_health_check(
        self,
        mock_sleep: MagicMock,
        mock_run: MagicMock,
        mock_health: MagicMock,
        integration_config: OrchestrationConfig,
    ) -> None:
        """Gateway startup includes health validation."""
        # Mock Docker responses - need enough for loop iterations
        mock_run.return_value = MagicMock(returncode=0, stdout="healthy")

        # Mock health checker to fail initially, then succeed
        mock_health.side_effect = [False, False, True]

        orchestrator = StartupOrchestrator(integration_config)
        orchestrator._initialize()
        orchestrator._start_gateway()
        orchestrator._wait_for_gateway()

        # After retries, should succeed
        assert orchestrator.context.state == StartupState.GATEWAY_VALIDATED

    @patch("src.orchestration.startup.GatewayHealthChecker.check_api_port", return_value=False)
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_gateway_restart_on_timeout(
        self,
        mock_sleep: MagicMock,
        mock_run: MagicMock,
        mock_health: MagicMock,
        integration_config: OrchestrationConfig,
    ) -> None:
        """Gateway restart is attempted on health timeout."""
        integration_config.gateway_health_timeout = 2
        integration_config.gateway_health_retry_interval = 1
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        orchestrator = StartupOrchestrator(integration_config)
        orchestrator._wait_for_gateway()

        assert orchestrator.context.gateway_restart_attempted is True


# =============================================================================
# BOT LAUNCH INTEGRATION
# =============================================================================


@pytest.mark.integration
class TestBotLaunchIntegration:
    """Test bot launch integration."""

    @patch("subprocess.Popen")
    @patch("time.sleep")
    def test_bot_launched_with_correct_environment(
        self,
        mock_sleep: MagicMock,
        mock_popen: MagicMock,
        integration_config: OrchestrationConfig,
    ) -> None:
        """Bot is launched with correct environment variables."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        orchestrator = StartupOrchestrator(integration_config)
        orchestrator.context.gameplan_path = integration_config.gameplan_path
        orchestrator._start_bot()

        # Verify Popen was called
        mock_popen.assert_called_once()

        # Check environment variables passed
        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs.get("env", {})
        assert env.get("GATEWAY_HOST") == "localhost"
        assert env.get("GATEWAY_PORT") == "4002"
        assert env.get("LOG_LEVEL") == "DEBUG"

    @patch("subprocess.Popen")
    @patch("time.sleep")
    def test_bot_crash_detection(
        self,
        mock_sleep: MagicMock,
        mock_popen: MagicMock,
        integration_config: OrchestrationConfig,
    ) -> None:
        """Bot crash within 5 seconds is detected."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Exited with error
        mock_process.stderr.read.return_value = "Fatal error"
        mock_process.stdout.read.return_value = ""
        mock_popen.return_value = mock_process

        orchestrator = StartupOrchestrator(integration_config)
        orchestrator.context.gameplan_path = integration_config.gameplan_path
        orchestrator._start_bot()

        assert orchestrator.context.state == StartupState.FAILURE
        assert "startup failed" in (orchestrator.context.error_message or "").lower()


# =============================================================================
# STRATEGY C GENERATION
# =============================================================================


@pytest.mark.integration
class TestStrategyCGeneration:
    """Test Strategy C gameplan generation."""

    @patch("src.orchestration.startup.GatewayHealthChecker.check_api_port", return_value=True)
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_strategy_c_gameplan_created_and_used(
        self,
        mock_sleep: MagicMock,
        mock_run: MagicMock,
        mock_popen: MagicMock,
        mock_health: MagicMock,
        integration_config: OrchestrationConfig,
        tmp_path: Path,
    ) -> None:
        """Strategy C gameplan is created and passed to bot."""
        # No gameplan configured
        integration_config.gameplan_path = None
        emergency_path = tmp_path / "state" / "emergency.json"
        integration_config.emergency_gameplan_path = emergency_path

        # Mock Docker responses
        mock_run.side_effect = [
            MagicMock(returncode=0),  # _docker_available
            MagicMock(returncode=0, stdout="Up 5 minutes"),  # _start_gateway
            MagicMock(returncode=0, stdout="healthy"),  # _check_docker_health
            MagicMock(returncode=0, stdout="healthy"),  # _check_docker_health
        ]

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        orchestrator = StartupOrchestrator(integration_config)
        exit_code = orchestrator.run()

        # Verify Strategy C was generated
        assert emergency_path.exists()

        # Verify exit code indicates Strategy C deployed
        assert exit_code == 2

        # Verify gameplan content
        with open(emergency_path) as f:
            gameplan = json.load(f)
        assert gameplan["strategy"] == "C"
        assert gameplan["data_quality"]["quarantine_active"] is True
