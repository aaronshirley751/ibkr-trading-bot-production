"""
E2E tests for gameplan-driven strategy switching.

Tests the integration between gameplan loading, gate evaluation,
and strategy selection/override behavior.
"""

import copy
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from src.bot.gameplan import GameplanLoader
from src.bot.gates import (
    AffordabilityGate,
    EntryWindowGate,
)
from src.bot.trading_loop import TradingLoop
from src.config.risk_config import DEFAULT_RISK_CONFIG

from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


# =============================================================================
# STRATEGY LOADING FROM GAMEPLAN
# =============================================================================


class TestGameplanStrategyLoading:
    """Verify that gameplan strategy field drives active strategy."""

    def test_gameplan_says_a_loads_strategy_a(
        self, valid_strategy_a_gameplan: Dict[str, Any]
    ) -> None:
        """When gameplan says Strategy A, TradingLoop activates A."""
        health_checker = MagicMock()
        loop = TradingLoop(
            gameplan=valid_strategy_a_gameplan,
            risk_config=DEFAULT_RISK_CONFIG,
            health_checker=health_checker,
        )
        assert loop.strategy == "A"
        assert loop.symbols == ["SPY"]

    def test_gameplan_says_b_loads_strategy_b(
        self, valid_strategy_b_gameplan: Dict[str, Any]
    ) -> None:
        """When gameplan says Strategy B, TradingLoop activates B."""
        health_checker = MagicMock()
        loop = TradingLoop(
            gameplan=valid_strategy_b_gameplan,
            risk_config=DEFAULT_RISK_CONFIG,
            health_checker=health_checker,
        )
        assert loop.strategy == "B"

    def test_gameplan_says_c_loads_strategy_c(
        self, valid_strategy_c_gameplan: Dict[str, Any]
    ) -> None:
        """When gameplan says Strategy C, TradingLoop activates C."""
        health_checker = MagicMock()
        loop = TradingLoop(
            gameplan=valid_strategy_c_gameplan,
            risk_config=DEFAULT_RISK_CONFIG,
            health_checker=health_checker,
        )
        assert loop.strategy == "C"

    def test_missing_strategy_defaults_to_c(self) -> None:
        """When strategy field missing, defaults to C."""
        health_checker = MagicMock()
        loop = TradingLoop(
            gameplan={"symbols": []},
            risk_config=DEFAULT_RISK_CONFIG,
            health_checker=health_checker,
        )
        assert loop.strategy == "C"


# =============================================================================
# VIX GATE → STRATEGY C OVERRIDE
# =============================================================================


class TestVIXGateStrategyOverride:
    """Verify VIX gate overrides strategy to C when triggered."""

    def test_vix_gate_override_switches_to_c(
        self, valid_strategy_a_gameplan: Dict[str, Any]
    ) -> None:
        """When VIX >= threshold, strategy is overridden to C."""
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["vix_at_analysis"] = 20.0  # Above 18.0 threshold

        health_checker = MagicMock()
        loop = TradingLoop(
            gameplan=gameplan,
            risk_config=DEFAULT_RISK_CONFIG,
            health_checker=health_checker,
        )

        assert loop.strategy == "A"  # Before gate check
        passed = loop._check_vix_gate()
        assert passed is False
        assert loop.strategy == "C"
        assert loop._strategy_overridden is True

    def test_vix_gate_pass_keeps_strategy_a(
        self, valid_strategy_a_gameplan: Dict[str, Any]
    ) -> None:
        """When VIX < threshold, strategy remains A."""
        health_checker = MagicMock()
        loop = TradingLoop(
            gameplan=valid_strategy_a_gameplan,
            risk_config=DEFAULT_RISK_CONFIG,
            health_checker=health_checker,
        )
        passed = loop._check_vix_gate()
        assert passed is True
        assert loop.strategy == "A"

    def test_vix_gate_none_overrides_to_c(self, valid_strategy_a_gameplan: Dict[str, Any]) -> None:
        """When VIX is None, strategy is overridden to C (fail-safe)."""
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["vix_at_analysis"] = None

        health_checker = MagicMock()
        loop = TradingLoop(
            gameplan=gameplan,
            risk_config=DEFAULT_RISK_CONFIG,
            health_checker=health_checker,
        )
        passed = loop._check_vix_gate()
        assert passed is False
        assert loop.strategy == "C"

    def test_vix_gate_discord_alert_on_override(
        self, valid_strategy_a_gameplan: Dict[str, Any]
    ) -> None:
        """VIX gate override sends Discord warning."""
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["vix_at_analysis"] = 20.0

        discord = MagicMock()
        health_checker = MagicMock()
        loop = TradingLoop(
            gameplan=gameplan,
            risk_config=DEFAULT_RISK_CONFIG,
            health_checker=health_checker,
            discord_notifier=discord,
        )
        loop._check_vix_gate()
        discord.send_warning.assert_called_once()
        assert "Strategy C" in discord.send_warning.call_args[0][0]


# =============================================================================
# ENTRY WINDOW ENFORCEMENT
# =============================================================================


class TestEntryWindowEnforcement:
    """Verify entry window gate blocks entries outside window."""

    def test_entry_blocked_before_window(self, valid_strategy_a_gameplan: Dict[str, Any]) -> None:
        """Entries before window start are blocked."""
        gate = EntryWindowGate()
        now = datetime(2026, 2, 17, 9, 30, tzinfo=ET)
        result = gate.evaluate(valid_strategy_a_gameplan, now=now)
        assert result.passed is False

    def test_entry_allowed_during_window(self, valid_strategy_a_gameplan: Dict[str, Any]) -> None:
        """Entries during window are allowed."""
        gate = EntryWindowGate()
        now = datetime(2026, 2, 17, 12, 0, tzinfo=ET)
        result = gate.evaluate(valid_strategy_a_gameplan, now=now)
        assert result.passed is True

    def test_entry_blocked_after_window(self, valid_strategy_a_gameplan: Dict[str, Any]) -> None:
        """Entries after window end are blocked."""
        gate = EntryWindowGate()
        now = datetime(2026, 2, 17, 15, 30, tzinfo=ET)
        result = gate.evaluate(valid_strategy_a_gameplan, now=now)
        assert result.passed is False


# =============================================================================
# AFFORDABILITY GATE LOGGING
# =============================================================================


class TestAffordabilityLogging:
    """Verify affordability gate logs correctly for different outcomes."""

    def test_affordability_skip_logged(
        self, valid_strategy_a_gameplan: Dict[str, Any], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Affordability rejection is logged as affordability_skip."""
        gate = AffordabilityGate(default_max_risk=Decimal("18"))
        with caplog.at_level(logging.WARNING):
            result = gate.evaluate(25.0, valid_strategy_a_gameplan)
        assert result.passed is False
        assert "affordability_skip" in result.reason
        assert "REJECTED" in caplog.text

    def test_affordability_warn_logged(
        self, valid_strategy_a_gameplan: Dict[str, Any], caplog: pytest.LogCaptureFixture
    ) -> None:
        """Affordability warning is logged for reduced size."""
        gate = AffordabilityGate(default_max_risk=Decimal("18"))
        with caplog.at_level(logging.WARNING):
            result = gate.evaluate(15.0, valid_strategy_a_gameplan)
        assert result.passed is True
        assert result.reduce_size is True
        assert "WARNING" in caplog.text


# =============================================================================
# FULL GAMEPLAN FILE → SCHEMA VALIDATION
# =============================================================================


class TestGameplanFileValidation:
    """Verify the deployed gameplan file validates against schema."""

    def test_daily_gameplan_validates_against_schema(self, tmp_path: Path) -> None:
        """data/daily_gameplan.json validates against the extended schema."""
        gameplan_path = Path("data/daily_gameplan.json")
        if not gameplan_path.exists():
            pytest.skip("data/daily_gameplan.json not found (CI or clean checkout)")

        loader = GameplanLoader(schema_path=Path("schemas/daily_gameplan_schema.json"))
        gameplan = loader.load(gameplan_path)

        # Should NOT have fallen back to Strategy C default
        assert (
            gameplan.get("_default_reason") is None
        ), f"Gameplan validation failed: {gameplan.get('_default_reason')}"
        assert gameplan["strategy"] == "A"
        assert gameplan["symbols"] == ["SPY"]
        assert gameplan["operator_id"] == "CSATSPRIM"
        assert gameplan["entry_window_start"] == "10:00"
        assert gameplan["entry_window_end"] == "15:00"
        assert gameplan["vix_gate"]["threshold"] == 18.0
        assert gameplan["max_risk_per_trade"] == 12.0
        assert gameplan["max_risk_ceiling"] == 18.0
