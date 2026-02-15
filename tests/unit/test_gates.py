"""
Unit tests for pre-trade gates (VIX, Affordability, Entry Window).

Each gate is tested in isolation with deterministic inputs.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from src.bot.gates import (
    AffordabilityGate,
    EntryWindowGate,
    VIXConfirmationGate,
)

from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


# =============================================================================
# VIX CONFIRMATION GATE
# =============================================================================


class TestVIXConfirmationGate:
    """Tests for VIXConfirmationGate."""

    def setup_method(self) -> None:
        self.gate = VIXConfirmationGate()

    def test_vix_below_threshold_passes(self) -> None:
        """VIX below threshold should pass the gate."""
        gameplan = {
            "vix_at_analysis": 15.5,
            "vix_gate": {"check_time": "09:45", "threshold": 18.0},
        }
        result = self.gate.evaluate(gameplan)
        assert result.passed is True
        assert result.gate_name == "vix"
        assert "below_threshold" in result.reason

    def test_vix_at_threshold_fails(self) -> None:
        """VIX exactly at threshold should fail (>= check)."""
        gameplan = {
            "vix_at_analysis": 18.0,
            "vix_gate": {"check_time": "09:45", "threshold": 18.0},
        }
        result = self.gate.evaluate(gameplan)
        assert result.passed is False
        assert "above_threshold" in result.reason

    def test_vix_above_threshold_fails(self) -> None:
        """VIX above threshold should fail."""
        gameplan = {
            "vix_at_analysis": 22.5,
            "vix_gate": {"check_time": "09:45", "threshold": 18.0},
        }
        result = self.gate.evaluate(gameplan)
        assert result.passed is False
        assert "above_threshold" in result.reason

    def test_vix_none_fails(self) -> None:
        """VIX is None should fail-safe to Strategy C."""
        gameplan = {
            "vix_at_analysis": None,
            "vix_gate": {"check_time": "09:45", "threshold": 18.0},
        }
        result = self.gate.evaluate(gameplan)
        assert result.passed is False
        assert "vix_is_none" in result.reason

    def test_no_vix_gate_configured_passes(self) -> None:
        """If no vix_gate in gameplan, gate passes by default."""
        gameplan = {"vix_at_analysis": 25.0}
        result = self.gate.evaluate(gameplan)
        assert result.passed is True
        assert "no_vix_gate_configured" in result.reason

    def test_vix_just_below_threshold_passes(self) -> None:
        """VIX just below threshold (17.99 vs 18.0) should pass."""
        gameplan = {
            "vix_at_analysis": 17.99,
            "vix_gate": {"check_time": "09:45", "threshold": 18.0},
        }
        result = self.gate.evaluate(gameplan)
        assert result.passed is True

    def test_vix_missing_from_gameplan_fails(self) -> None:
        """VIX field missing entirely should fail (resolves to None)."""
        gameplan = {
            "vix_gate": {"check_time": "09:45", "threshold": 18.0},
        }
        result = self.gate.evaluate(gameplan)
        assert result.passed is False
        assert "vix_is_none" in result.reason


# =============================================================================
# AFFORDABILITY GATE
# =============================================================================


class TestAffordabilityGate:
    """Tests for AffordabilityGate."""

    def setup_method(self) -> None:
        self.gate = AffordabilityGate(default_max_risk=Decimal("18"))

    def test_premium_within_budget_passes(self) -> None:
        """Premium at or below max_risk_per_trade passes with full size."""
        gameplan = {"max_risk_per_trade": 12.0, "max_risk_ceiling": 18.0}
        result = self.gate.evaluate(10.0, gameplan)
        assert result.passed is True
        assert result.reduce_size is False
        assert "within_budget" in result.reason

    def test_premium_exactly_at_max_risk_passes(self) -> None:
        """Premium exactly at max_risk_per_trade passes."""
        gameplan = {"max_risk_per_trade": 12.0, "max_risk_ceiling": 18.0}
        result = self.gate.evaluate(12.0, gameplan)
        assert result.passed is True
        assert result.reduce_size is False

    def test_premium_between_max_risk_and_ceiling_warns(self) -> None:
        """Premium > max_risk but <= ceiling passes with reduced size."""
        gameplan = {"max_risk_per_trade": 12.0, "max_risk_ceiling": 18.0}
        result = self.gate.evaluate(15.0, gameplan)
        assert result.passed is True
        assert result.reduce_size is True
        assert "affordability_warn" in result.reason

    def test_premium_at_ceiling_warns(self) -> None:
        """Premium exactly at ceiling passes with reduced size."""
        gameplan = {"max_risk_per_trade": 12.0, "max_risk_ceiling": 18.0}
        result = self.gate.evaluate(18.0, gameplan)
        assert result.passed is True
        assert result.reduce_size is True

    def test_premium_above_ceiling_rejects(self) -> None:
        """Premium above ceiling is rejected."""
        gameplan = {"max_risk_per_trade": 12.0, "max_risk_ceiling": 18.0}
        result = self.gate.evaluate(20.0, gameplan)
        assert result.passed is False
        assert "affordability_skip" in result.reason

    def test_uses_default_max_risk_when_missing(self) -> None:
        """When gameplan has no risk fields, uses default from RiskConfig."""
        gameplan: Dict[str, Any] = {}
        result = self.gate.evaluate(15.0, gameplan)
        # Default is $18 for both max_risk and ceiling
        assert result.passed is True
        assert result.reduce_size is False

    def test_zero_premium_passes(self) -> None:
        """Zero premium always passes."""
        gameplan = {"max_risk_per_trade": 12.0, "max_risk_ceiling": 18.0}
        result = self.gate.evaluate(0.0, gameplan)
        assert result.passed is True
        assert result.reduce_size is False


# =============================================================================
# ENTRY WINDOW GATE
# =============================================================================


class TestEntryWindowGate:
    """Tests for EntryWindowGate."""

    def setup_method(self) -> None:
        self.gate = EntryWindowGate()
        self.gameplan = {
            "entry_window_start": "10:00",
            "entry_window_end": "15:00",
        }

    def test_within_window_passes(self) -> None:
        """Time inside the entry window passes."""
        now = datetime(2026, 2, 17, 12, 0, tzinfo=ET)
        result = self.gate.evaluate(self.gameplan, now=now)
        assert result.passed is True
        assert result.gate_name == "entry_window"
        assert "within_window" in result.reason

    def test_before_window_rejects(self) -> None:
        """Time before entry window start is rejected."""
        now = datetime(2026, 2, 17, 9, 30, tzinfo=ET)
        result = self.gate.evaluate(self.gameplan, now=now)
        assert result.passed is False
        assert "outside_window" in result.reason

    def test_after_window_rejects(self) -> None:
        """Time after entry window end is rejected."""
        now = datetime(2026, 2, 17, 15, 30, tzinfo=ET)
        result = self.gate.evaluate(self.gameplan, now=now)
        assert result.passed is False
        assert "outside_window" in result.reason

    def test_at_window_start_passes(self) -> None:
        """Time exactly at window start passes (inclusive)."""
        now = datetime(2026, 2, 17, 10, 0, tzinfo=ET)
        result = self.gate.evaluate(self.gameplan, now=now)
        assert result.passed is True

    def test_at_window_end_passes(self) -> None:
        """Time exactly at window end passes (inclusive)."""
        now = datetime(2026, 2, 17, 15, 0, tzinfo=ET)
        result = self.gate.evaluate(self.gameplan, now=now)
        assert result.passed is True

    def test_default_window_when_fields_missing(self) -> None:
        """Uses 09:30-16:00 default when entry window fields missing."""
        gameplan: Dict[str, Any] = {}
        now = datetime(2026, 2, 17, 10, 0, tzinfo=ET)
        result = self.gate.evaluate(gameplan, now=now)
        assert result.passed is True

    def test_default_window_rejects_before_930(self) -> None:
        """Default window rejects entries before 09:30 ET."""
        gameplan: Dict[str, Any] = {}
        now = datetime(2026, 2, 17, 9, 0, tzinfo=ET)
        result = self.gate.evaluate(gameplan, now=now)
        assert result.passed is False

    def test_invalid_time_format_uses_defaults(self) -> None:
        """Invalid time format falls back to defaults."""
        gameplan = {"entry_window_start": "invalid", "entry_window_end": "15:00"}
        now = datetime(2026, 2, 17, 10, 0, tzinfo=ET)
        result = self.gate.evaluate(gameplan, now=now)
        # Falls back to default 09:30-16:00
        assert result.passed is True

    def test_one_minute_before_window_start(self) -> None:
        """One minute before window start is rejected."""
        now = datetime(2026, 2, 17, 9, 59, tzinfo=ET)
        result = self.gate.evaluate(self.gameplan, now=now)
        assert result.passed is False

    def test_one_minute_after_window_end(self) -> None:
        """One minute after window end is rejected."""
        now = datetime(2026, 2, 17, 15, 1, tzinfo=ET)
        result = self.gate.evaluate(self.gameplan, now=now)
        assert result.passed is False
