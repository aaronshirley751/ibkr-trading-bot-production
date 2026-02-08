"""
Unit tests for risk management guards and circuit breakers.

Tests cover:
- Daily loss limit enforcement (10% / $60)
- Weekly drawdown governor (15% / $90 triggers Strategy C)
- Stop-loss calculation (25% for Strategy A, 15% for Strategy B)
- Force-close logic at DTE threshold
- Gap-down scenario handling
- Strategy C auto-deployment triggers
- State persistence and recovery

Coverage target: 98%
CRO MANDATE: Every boundary tested at [limit-ε, limit, limit+ε]

Threat model references: T-01, T-02, T-05, T-06, T-07, T-09, T-10, T-12
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def risk_guard():
    """
    Create a RiskGuard instance with default account parameters.
    """
    from src.risk.guards import RiskGuard

    return RiskGuard(
        account_balance=600.00,
        max_daily_loss_pct=0.10,  # 10% = $60
        max_weekly_drawdown_pct=0.15,  # 15% = $90
        force_close_dte=3,  # Close at 3 DTE
    )


@pytest.fixture
def risk_guard_with_losses(risk_guard):
    """RiskGuard with some accumulated daily losses."""
    risk_guard.record_loss(30.00)  # $30 of $60 daily limit used
    return risk_guard


@pytest.fixture
def risk_guard_near_daily_limit(risk_guard):
    """RiskGuard at $59.99 daily loss (one penny under limit)."""
    risk_guard.record_loss(59.99)
    return risk_guard


@pytest.fixture
def weekly_state_mid_week():
    """Weekly drawdown state partway through the week."""
    return {
        "week_start": "2026-02-02",
        "realized_pnl": -45.00,  # $45 of $90 weekly limit used
        "drawdown_pct": 0.075,
        "governor_active": False,
    }


# =============================================================================
# DAILY LOSS LIMIT TESTS — CRO Boundary: $60 (10% of $600)
# Threat: T-01, T-02
# =============================================================================


class TestDailyLossLimit:
    """Tests for daily loss limit enforcement ($60 = 10% of $600)."""

    def test_no_losses_allows_trading(self, risk_guard):
        """Fresh day with zero losses = trading allowed."""
        assert risk_guard.daily_loss_limit_hit() is False
        assert risk_guard.daily_loss_remaining() == pytest.approx(60.00)

    def test_partial_loss_allows_trading(self, risk_guard_with_losses):
        """$30 in losses, $30 remaining = trading allowed."""
        assert risk_guard_with_losses.daily_loss_limit_hit() is False
        assert risk_guard_with_losses.daily_loss_remaining() == pytest.approx(30.00)

    def test_loss_at_59_99_allows_trading(self, risk_guard_near_daily_limit):
        """$59.99 loss = still allowed (one penny under)."""
        assert risk_guard_near_daily_limit.daily_loss_limit_hit() is False

    def test_loss_at_60_00_triggers_halt(self, risk_guard):
        """$60.00 loss = HALT (at exact limit)."""
        risk_guard.record_loss(60.00)
        assert risk_guard.daily_loss_limit_hit() is True

    def test_loss_at_60_01_triggers_halt(self, risk_guard):
        """$60.01 loss = HALT (over limit)."""
        risk_guard.record_loss(60.01)
        assert risk_guard.daily_loss_limit_hit() is True

    def test_incremental_losses_accumulate(self, risk_guard):
        """Multiple small losses that cumulatively hit the limit."""
        risk_guard.record_loss(20.00)
        assert risk_guard.daily_loss_limit_hit() is False
        risk_guard.record_loss(20.00)
        assert risk_guard.daily_loss_limit_hit() is False
        risk_guard.record_loss(20.00)
        assert risk_guard.daily_loss_limit_hit() is True  # $60 total

    def test_loss_then_gain_still_tracks_losses(self, risk_guard):
        """
        Gains do NOT reduce the daily loss counter.
        If you lose $40, then gain $20, daily loss is still $40 (not $20).
        This prevents the 'churn and burn' pattern.
        """
        risk_guard.record_loss(40.00)
        risk_guard.record_gain(20.00)
        assert risk_guard.daily_losses_total() == pytest.approx(40.00)

    def test_daily_limit_resets_next_day(self, risk_guard):
        """Daily loss counter resets at start of new trading day."""
        risk_guard.record_loss(60.00)
        assert risk_guard.daily_loss_limit_hit() is True

        risk_guard.reset_daily()
        assert risk_guard.daily_loss_limit_hit() is False
        assert risk_guard.daily_loss_remaining() == pytest.approx(60.00)

    def test_daily_limit_with_zero_balance(self):
        """Zero account balance = zero daily loss limit = immediate halt."""
        from src.risk.guards import RiskGuard

        guard = RiskGuard(
            account_balance=0.00,
            max_daily_loss_pct=0.10,
            max_weekly_drawdown_pct=0.15,
            force_close_dte=3,
        )
        assert guard.daily_loss_limit_hit() is True  # Can't lose what you don't have

    def test_daily_limit_with_negative_balance(self):
        """
        Negative account balance should trigger immediate halt.
        Threat T-12: Negative balance handling.
        """
        from src.risk.guards import RiskGuard

        guard = RiskGuard(
            account_balance=-100.00,
            max_daily_loss_pct=0.10,
            max_weekly_drawdown_pct=0.15,
            force_close_dte=3,
        )
        assert guard.daily_loss_limit_hit() is True

    def test_halt_action_closes_all_positions(self, risk_guard):
        """When daily limit hit, the guard's action should be CLOSE_ALL."""
        risk_guard.record_loss(60.00)
        action = risk_guard.get_required_action()
        assert action["type"] == "CLOSE_ALL"
        assert action["reason"] == "daily_loss_limit"


# =============================================================================
# WEEKLY DRAWDOWN GOVERNOR TESTS — CRO Boundary: $90 (15% of $600)
# Threat: T-01, T-10
# =============================================================================


class TestWeeklyDrawdownGovernor:
    """Tests for weekly drawdown governor ($90 = 15% of $600)."""

    def test_no_weekly_losses_allows_trading(self, risk_guard):
        """Fresh week = trading allowed."""
        assert risk_guard.weekly_governor_active() is False

    def test_weekly_loss_under_limit_allows_trading(self, risk_guard):
        """$89.99 weekly loss = still allowed."""
        risk_guard.record_weekly_loss(89.99)
        assert risk_guard.weekly_governor_active() is False

    def test_weekly_loss_at_limit_activates_governor(self, risk_guard):
        """$90.00 weekly loss = governor ACTIVATED."""
        risk_guard.record_weekly_loss(90.00)
        assert risk_guard.weekly_governor_active() is True

    def test_weekly_loss_over_limit_activates_governor(self, risk_guard):
        """$90.01 weekly loss = governor ACTIVATED."""
        risk_guard.record_weekly_loss(90.01)
        assert risk_guard.weekly_governor_active() is True

    def test_governor_persists_through_week(self, risk_guard):
        """
        Once activated, governor stays active for remainder of week.
        Threat T-10: Should NOT reset mid-week.
        """
        risk_guard.record_weekly_loss(90.00)
        assert risk_guard.weekly_governor_active() is True

        # Simulate subsequent days in same week — should remain active
        risk_guard.advance_day()  # Tuesday
        assert risk_guard.weekly_governor_active() is True
        risk_guard.advance_day()  # Wednesday
        assert risk_guard.weekly_governor_active() is True

    def test_governor_resets_on_new_week(self, risk_guard):
        """Governor resets when a new trading week begins (Monday)."""
        risk_guard.record_weekly_loss(90.00)
        assert risk_guard.weekly_governor_active() is True

        risk_guard.start_new_week()
        assert risk_guard.weekly_governor_active() is False

    def test_governor_forces_strategy_c(self, risk_guard):
        """When governor is active, required strategy must be C."""
        risk_guard.record_weekly_loss(90.00)
        assert risk_guard.required_strategy() == "C"

    def test_governor_blocks_all_new_entries(self, risk_guard):
        """Governor active = no new positions can be opened."""
        risk_guard.record_weekly_loss(90.00)
        assert risk_guard.can_open_new_position() is False

    def test_weekly_losses_accumulate_across_days(self, risk_guard):
        """Daily losses contribute to weekly total."""
        risk_guard.record_loss(30.00)
        risk_guard.record_weekly_loss(30.00)
        risk_guard.advance_day()
        risk_guard.record_loss(30.00)
        risk_guard.record_weekly_loss(30.00)
        risk_guard.advance_day()
        risk_guard.record_loss(30.00)
        risk_guard.record_weekly_loss(30.00)
        # $90 total weekly = governor should activate
        assert risk_guard.weekly_governor_active() is True

    def test_governor_state_survives_restart(self, risk_guard):
        """
        Governor state must persist across process restarts.
        Threat T-06: State corruption.
        """
        risk_guard.record_weekly_loss(90.00)
        state = risk_guard.to_state_dict()

        from src.risk.guards import RiskGuard

        restored = RiskGuard.from_state_dict(state)
        assert restored.weekly_governor_active() is True


# =============================================================================
# STOP-LOSS CALCULATION TESTS
# Threat: T-05 (gap-down), T-01
# =============================================================================


class TestStopLossCalculation:
    """Tests for stop-loss price calculation per strategy."""

    def test_strategy_a_stop_loss_25_percent(self, risk_guard):
        """Strategy A: 25% stop-loss on premium."""
        stop = risk_guard.calculate_stop_loss(entry_price=4.00, strategy="A")
        assert stop == pytest.approx(3.00)  # 4.00 * 0.75 = 3.00

    def test_strategy_b_stop_loss_15_percent(self, risk_guard):
        """Strategy B: 15% stop-loss on premium."""
        stop = risk_guard.calculate_stop_loss(entry_price=4.00, strategy="B")
        assert stop == pytest.approx(3.40)  # 4.00 * 0.85 = 3.40

    def test_strategy_c_no_stop_loss(self, risk_guard):
        """Strategy C: No stop-loss (no positions allowed)."""
        with pytest.raises(ValueError, match="Strategy C does not trade"):
            risk_guard.calculate_stop_loss(entry_price=4.00, strategy="C")

    def test_stop_loss_on_penny_options(self, risk_guard):
        """Very cheap options: stop-loss should still be calculated."""
        stop = risk_guard.calculate_stop_loss(entry_price=0.10, strategy="A")
        assert stop == pytest.approx(0.075)

    def test_gap_down_max_loss_calculation(self, risk_guard):
        """
        Gap-down scenario: fill price far below stop level.
        Threat T-05: Actual loss exceeds calculated max.
        """
        actual_loss = risk_guard.calculate_gap_loss(
            entry_price=4.00,
            stop_price=3.00,
            fill_price=1.50,
            multiplier=100,
            quantity=1,
        )
        # Actual loss = (4.00 - 1.50) * 100 * 1 = $250
        assert actual_loss == pytest.approx(250.00)
        # This should be flagged as exceeding the stop-loss expected loss
        assert actual_loss > risk_guard.calculate_expected_loss(
            entry_price=4.00, stop_price=3.00, multiplier=100, quantity=1
        )

    def test_gap_down_to_zero(self, risk_guard):
        """Worst case: option goes to zero (total loss of premium)."""
        actual_loss = risk_guard.calculate_gap_loss(
            entry_price=4.00,
            stop_price=3.00,
            fill_price=0.00,
            multiplier=100,
            quantity=1,
        )
        assert actual_loss == pytest.approx(400.00)


# =============================================================================
# DTE FORCE-CLOSE TESTS — CRO Boundary: 3 DTE
# Threat: T-07 (timezone error)
# =============================================================================


class TestDTEForceClose:
    """Tests for force-close logic at DTE threshold."""

    def test_position_at_5_dte_not_forced(self, risk_guard):
        """5 DTE = no force-close required."""
        assert risk_guard.should_force_close(dte=5) is False

    def test_position_at_4_dte_not_forced(self, risk_guard):
        """4 DTE = no force-close required."""
        assert risk_guard.should_force_close(dte=4) is False

    def test_position_at_3_dte_forced(self, risk_guard):
        """3 DTE = FORCE CLOSE (at threshold)."""
        assert risk_guard.should_force_close(dte=3) is True

    def test_position_at_2_dte_forced(self, risk_guard):
        """2 DTE = FORCE CLOSE."""
        assert risk_guard.should_force_close(dte=2) is True

    def test_position_at_1_dte_forced(self, risk_guard):
        """1 DTE = FORCE CLOSE (urgent)."""
        assert risk_guard.should_force_close(dte=1) is True

    def test_position_at_0_dte_forced_emergency(self, risk_guard):
        """0 DTE = EMERGENCY FORCE CLOSE."""
        assert risk_guard.should_force_close(dte=0) is True

    def test_dte_calculation_from_expiry_date(self, risk_guard):
        """Calculate DTE from expiry date string."""
        # Expiry 5 days from now
        expiry = (date.today() + timedelta(days=5)).strftime("%Y%m%d")
        dte = risk_guard.calculate_dte(expiry_date=expiry)
        assert dte == 5

    def test_dte_calculation_timezone_awareness(self, risk_guard):
        """
        DTE must be calculated in ET (exchange timezone), not UTC.
        Threat T-07: A position expiring "tomorrow" in UTC might still be
        "today" in ET after market close.
        """
        # This tests that the implementation uses ET for DTE calculation
        from zoneinfo import ZoneInfo

        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)
        expiry = (now_et.date() + timedelta(days=3)).strftime("%Y%m%d")
        dte = risk_guard.calculate_dte(expiry_date=expiry)
        assert dte == 3

    def test_expired_option_immediate_close(self, risk_guard):
        """Already-expired option (negative DTE) = immediate action."""
        assert risk_guard.should_force_close(dte=-1) is True

    def test_force_close_action_type(self, risk_guard):
        """Force-close action should specify MARKET order (not limit)."""
        action = risk_guard.get_force_close_action(dte=2)
        assert action["order_type"] == "MARKET"
        assert action["reason"] == "dte_force_close"
        assert action["urgency"] == "high"


# =============================================================================
# STRATEGY C AUTO-DEPLOYMENT TRIGGERS
# Threat: T-08 (bypass via direct order)
# =============================================================================


class TestStrategyCTriggers:
    """Tests for all conditions that force Strategy C deployment."""

    def test_daily_loss_triggers_strategy_c(self, risk_guard):
        """Daily loss limit hit → Strategy C."""
        risk_guard.record_loss(60.00)
        assert risk_guard.required_strategy() == "C"

    def test_weekly_governor_triggers_strategy_c(self, risk_guard):
        """Weekly drawdown governor → Strategy C."""
        risk_guard.record_weekly_loss(90.00)
        assert risk_guard.required_strategy() == "C"

    def test_data_quarantine_triggers_strategy_c(self, risk_guard):
        """Data quarantine flag → Strategy C."""
        risk_guard.set_data_quarantine(True)
        assert risk_guard.required_strategy() == "C"

    def test_pivot_limit_triggers_strategy_c(self, risk_guard):
        """2+ intraday pivots → Strategy C."""
        risk_guard.record_pivot()
        risk_guard.record_pivot()
        assert risk_guard.required_strategy() == "C"

    def test_no_triggers_allows_strategy_a_or_b(self, risk_guard):
        """No triggers active → strategy determined by market conditions."""
        assert risk_guard.required_strategy() is None  # None = no override

    def test_multiple_triggers_still_strategy_c(self, risk_guard):
        """Multiple simultaneous triggers → still Strategy C (not crash)."""
        risk_guard.record_loss(60.00)
        risk_guard.record_weekly_loss(90.00)
        risk_guard.set_data_quarantine(True)
        risk_guard.record_pivot()
        risk_guard.record_pivot()
        assert risk_guard.required_strategy() == "C"

    def test_strategy_c_blocks_order_submission(self, risk_guard):
        """
        When Strategy C is required, no order can pass the risk gate.
        Threat T-08: Verify there is no bypass path.
        """
        risk_guard.record_loss(60.00)
        result = risk_guard.pre_order_check(order={"action": "BUY", "totalQuantity": 1})
        assert result["allowed"] is False
        assert result["reason"] == "strategy_c_active"

    def test_strategy_c_allows_close_orders(self, risk_guard):
        """Strategy C blocks NEW entries but allows CLOSING existing positions."""
        risk_guard.record_loss(60.00)
        result = risk_guard.pre_order_check(
            order={"action": "SELL", "totalQuantity": 1, "is_closing": True}
        )
        assert result["allowed"] is True


# =============================================================================
# STATE PERSISTENCE TESTS
# Threat: T-06 (state corruption across sessions)
# =============================================================================


class TestStatePersistence:
    """Tests for risk state serialization and recovery."""

    def test_state_roundtrip(self, risk_guard):
        """Full state serialization and deserialization."""
        risk_guard.record_loss(25.00)
        risk_guard.record_weekly_loss(45.00)
        risk_guard.record_pivot()

        state = risk_guard.to_state_dict()

        from src.risk.guards import RiskGuard

        restored = RiskGuard.from_state_dict(state)
        assert restored.daily_losses_total() == pytest.approx(25.00)
        assert restored.weekly_governor_active() is False
        assert restored.pivot_count() == 1

    def test_corrupt_state_defaults_to_safe(self):
        """
        Corrupted state file → default to safe state (Strategy C).
        Threat T-06: Never start trading with unknown state.
        """
        from src.risk.guards import RiskGuard

        corrupt_state: Dict[str, str] = {"garbage": "data", "missing": "fields"}
        restored = RiskGuard.from_state_dict(corrupt_state)
        assert restored.required_strategy() == "C"

    def test_missing_state_defaults_to_safe(self):
        """No state file → default to safe state."""
        from src.risk.guards import RiskGuard

        restored = RiskGuard.from_state_dict(None)
        assert restored.required_strategy() == "C"

    def test_state_includes_all_critical_fields(self, risk_guard):
        """State dict must include all fields needed for safety."""
        risk_guard.record_loss(10.00)
        state = risk_guard.to_state_dict()

        required_fields = [
            "daily_losses",
            "weekly_losses",
            "governor_active",
            "pivot_count",
            "data_quarantine",
            "last_updated",
        ]
        for field in required_fields:
            assert field in state, f"Missing critical field: {field}"
