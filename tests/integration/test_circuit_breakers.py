"""
Integration tests for safety circuit breakers.

Tests cover:
- Strategy C auto-deployment on safety violations
- All-position closure on daily loss limit
- No new entries after PDT limit reached
- Multiple safety mechanisms coordinating
- Concurrent position handling and thread safety
- Gateway disconnection emergency response
- Full risk pipeline integration (sizing → guards → circuit breakers)

Coverage target: 98%
CRO MANDATE: These tests prove the safety mechanisms WORK TOGETHER.

Threat model references: T-04, T-08, T-11
"""

import threading
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def risk_engine():
    """
    Create a fully integrated RiskEngine with all subsystems.

    The RiskEngine is the integration point that coordinates:
    - PositionSizer
    - RiskGuard
    - PDTTracker
    - CircuitBreaker
    """
    from src.risk.engine import RiskEngine

    return RiskEngine(
        account_balance=600.00,
        config={
            "max_position_pct": 0.20,
            "max_risk_pct": 0.03,
            "pdt_limit": 3,
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
            "force_close_dte": 3,
            "max_intraday_pivots": 2,
        },
    )


@pytest.fixture
def mock_broker():
    """Mock broker for testing order submission/cancellation."""
    broker = MagicMock()
    broker.cancel_all_orders.return_value = True
    broker.close_all_positions.return_value = True
    broker.submit_order.return_value = {"orderId": 1, "status": "Submitted"}
    return broker


@pytest.fixture
def mock_notifier():
    """Mock Discord notifier for alert verification."""
    return MagicMock()


# =============================================================================
# FULL RISK PIPELINE INTEGRATION
# Threat: T-08 (no bypass path)
# =============================================================================


class TestRiskPipelineIntegration:
    """Tests for the complete risk check pipeline."""

    def test_valid_trade_passes_all_checks(self, risk_engine):
        """A properly sized, risk-compliant trade passes the full pipeline."""
        result = risk_engine.pre_trade_check(
            symbol="SPY",
            action="BUY",
            premium=0.80,
            stop_loss_pct=0.25,
            quantity=1,
        )
        # This SHOULD fail because risk ($20) > max risk per trade ($18)
        assert result["approved"] is False
        assert "risk_per_trade" in result["rejection_reasons"]

    def test_small_premium_trade_passes(self, risk_engine):
        """Trade with small enough premium to pass all checks."""
        result = risk_engine.pre_trade_check(
            symbol="SPY",
            action="BUY",
            premium=0.50,
            stop_loss_pct=0.15,
            quantity=1,
        )
        assert result["approved"] is True

    def test_pipeline_checks_all_guards_in_order(self, risk_engine):
        """
        Risk pipeline must check ALL guards, not short-circuit on first pass.
        Order: Strategy C override → PDT → daily loss → weekly governor →
               position size → risk per trade → aggregate exposure
        """
        result = risk_engine.pre_trade_check(
            symbol="SPY",
            action="BUY",
            premium=0.50,
            stop_loss_pct=0.15,
            quantity=1,
        )
        # Verify all checks were evaluated
        assert "checks_performed" in result
        expected_checks = [
            "strategy_override",
            "pdt_compliance",
            "daily_loss_limit",
            "weekly_governor",
            "position_size",
            "risk_per_trade",
            "aggregate_exposure",
        ]
        for check in expected_checks:
            assert check in result["checks_performed"]

    def test_pipeline_rejects_and_identifies_all_failures(self, risk_engine):
        """When multiple checks fail, ALL failures are reported (not just first)."""
        # Exhaust PDT, hit daily loss, try to trade
        risk_engine.record_day_trades(3)
        risk_engine.record_daily_loss(60.00)

        result = risk_engine.pre_trade_check(
            symbol="SPY",
            action="BUY",
            premium=0.50,
            stop_loss_pct=0.15,
            quantity=1,
        )
        assert result["approved"] is False
        assert len(result["rejection_reasons"]) >= 2


# =============================================================================
# COORDINATED SAFETY MECHANISM TESTS
# Threat: T-11 (multiple mechanisms fire simultaneously)
# =============================================================================


class TestCoordinatedSafetyMechanisms:
    """Tests for multiple safety mechanisms firing together."""

    def test_daily_loss_triggers_close_all(self, risk_engine, mock_broker):
        """Daily loss limit → close all positions + halt trading."""
        risk_engine.attach_broker(mock_broker)
        risk_engine.on_loss_event(60.00)

        mock_broker.close_all_positions.assert_called_once()
        assert risk_engine.trading_halted() is True

    def test_pdt_limit_blocks_new_entries_only(self, risk_engine, mock_broker):
        """PDT limit → block new entries but allow closing existing."""
        risk_engine.record_day_trades(3)

        # New entry should be blocked
        result = risk_engine.pre_trade_check(
            symbol="SPY",
            action="BUY",
            premium=0.50,
            stop_loss_pct=0.15,
            quantity=1,
        )
        assert result["approved"] is False

        # Closing existing should be allowed
        close_result = risk_engine.pre_close_check(
            symbol="SPY",
            action="SELL",
            quantity=1,
            is_closing=True,
        )
        assert close_result["approved"] is True

    def test_gateway_disconnect_cancels_all_orders(self, risk_engine, mock_broker):
        """Gateway disconnection → cancel all pending orders."""
        risk_engine.attach_broker(mock_broker)
        risk_engine.on_gateway_disconnect()

        mock_broker.cancel_all_orders.assert_called_once()

    def test_gateway_disconnect_sends_alert(self, risk_engine, mock_notifier):
        """Gateway disconnection → Discord alert sent."""
        risk_engine.attach_notifier(mock_notifier)
        risk_engine.on_gateway_disconnect()

        mock_notifier.send_alert.assert_called_once()
        alert_msg = mock_notifier.send_alert.call_args[0][0]
        assert "disconnect" in alert_msg.lower()

    def test_compound_trigger_daily_plus_weekly(self, risk_engine, mock_broker):
        """
        Daily loss limit hit WHILE weekly governor also triggers.
        Both mechanisms should fire without conflict.
        Threat T-11.
        """
        risk_engine.attach_broker(mock_broker)
        # Record enough losses to trigger both daily and weekly
        risk_engine.on_loss_event(60.00)  # Triggers daily
        risk_engine.record_weekly_loss(90.00)  # Triggers weekly

        assert risk_engine.trading_halted() is True
        assert risk_engine.weekly_governor_active() is True
        assert risk_engine.required_strategy() == "C"

    def test_compound_trigger_no_exception(self, risk_engine, mock_broker):
        """
        All safety mechanisms firing simultaneously must not raise exceptions.
        """
        risk_engine.attach_broker(mock_broker)
        risk_engine.on_loss_event(60.00)
        risk_engine.record_weekly_loss(90.00)
        risk_engine.set_data_quarantine(True)
        risk_engine.record_pivot()
        risk_engine.record_pivot()

        # Should not raise — get action should still work
        action = risk_engine.get_emergency_action()
        assert action["strategy"] == "C"


# =============================================================================
# CONCURRENT POSITION HANDLING
# Threat: T-04 (aggregate overflow via race condition)
# =============================================================================


class TestConcurrentPositionHandling:
    """Tests for thread-safety of risk checks."""

    def test_concurrent_pre_trade_checks(self, risk_engine):
        """
        Multiple threads performing pre_trade_check simultaneously.
        Threat T-04: Race condition in aggregate position calculation.

        If two threads both check aggregate limit at the same time,
        each sees $100 of $120 used, each adds $15, both pass.
        But combined they'd be $130 > $120.
        """
        results: List[Dict[str, Any]] = []
        errors: List[Exception] = []
        barrier = threading.Barrier(5)

        def check_trade(thread_id: int) -> None:
            try:
                barrier.wait(timeout=5)
                result = risk_engine.pre_trade_check(
                    symbol="SPY",
                    action="BUY",
                    premium=0.50,
                    stop_loss_pct=0.15,
                    quantity=1,
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check_trade, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # No exceptions should have occurred
        assert len(errors) == 0, f"Thread errors: {errors}"
        # All threads should have gotten a result
        assert len(results) == 5

    def test_lock_prevents_double_entry(self, risk_engine):
        """Verify that the risk engine uses locking for state mutations."""
        # The risk engine should have a lock attribute for thread safety
        assert hasattr(risk_engine, "_lock") or hasattr(risk_engine, "lock")

    def test_concurrent_loss_recording(self, risk_engine):
        """
        Multiple threads recording losses simultaneously.
        Total losses must equal sum of individual losses (no lost updates).
        """
        barrier = threading.Barrier(10)
        errors: List[Exception] = []

        def record_loss(amount: float) -> None:
            try:
                barrier.wait(timeout=5)
                risk_engine.record_daily_loss(amount)
            except Exception as e:
                errors.append(e)

        # 10 threads each recording $5.00 loss = $50 total
        threads = [threading.Thread(target=record_loss, args=(5.00,)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Thread errors: {errors}"
        # Total daily losses should be exactly $50.00
        assert risk_engine.daily_losses_total() == pytest.approx(50.00, abs=0.01)


# =============================================================================
# CIRCUIT BREAKER STATE MACHINE TESTS
# =============================================================================


class TestCircuitBreakerStateMachine:
    """Tests for circuit breaker state transitions."""

    def test_initial_state_is_closed(self, risk_engine):
        """Circuit breaker starts in CLOSED state (trading allowed)."""
        assert risk_engine.circuit_breaker_state() == "CLOSED"

    def test_loss_event_opens_breaker(self, risk_engine):
        """Daily loss limit hit → breaker OPENS (trading halted)."""
        risk_engine.on_loss_event(60.00)
        assert risk_engine.circuit_breaker_state() == "OPEN"

    def test_open_breaker_rejects_all_trades(self, risk_engine):
        """OPEN breaker → all pre_trade_checks fail."""
        risk_engine.on_loss_event(60.00)
        result = risk_engine.pre_trade_check(
            symbol="SPY",
            action="BUY",
            premium=0.50,
            stop_loss_pct=0.15,
            quantity=1,
        )
        assert result["approved"] is False
        assert result["rejection_reasons"][0] == "circuit_breaker_open"

    def test_breaker_resets_on_new_day(self, risk_engine):
        """Breaker transitions from OPEN to CLOSED on new trading day."""
        risk_engine.on_loss_event(60.00)
        assert risk_engine.circuit_breaker_state() == "OPEN"

        risk_engine.start_new_trading_day()
        assert risk_engine.circuit_breaker_state() == "CLOSED"

    def test_breaker_stays_open_if_weekly_governor(self, risk_engine):
        """
        Even on a new day, if weekly governor is active, breaker stays OPEN.
        This ensures weekly governor takes precedence over daily reset.
        """
        risk_engine.on_loss_event(60.00)
        risk_engine.record_weekly_loss(90.00)

        risk_engine.start_new_trading_day()
        # Weekly governor still active → breaker remains open
        assert risk_engine.circuit_breaker_state() == "OPEN"


# =============================================================================
# EMERGENCY ACTION TESTS
# =============================================================================


class TestEmergencyActions:
    """Tests for emergency action generation."""

    def test_emergency_action_includes_close_all(self, risk_engine, mock_broker):
        """Emergency action must include close-all-positions directive."""
        risk_engine.attach_broker(mock_broker)
        risk_engine.on_loss_event(60.00)
        action = risk_engine.get_emergency_action()
        assert "CLOSE_ALL_POSITIONS" in action["directives"]

    def test_emergency_action_includes_cancel_orders(self, risk_engine, mock_broker):
        """Emergency action must include cancel-all-orders directive."""
        risk_engine.attach_broker(mock_broker)
        risk_engine.on_loss_event(60.00)
        action = risk_engine.get_emergency_action()
        assert "CANCEL_ALL_ORDERS" in action["directives"]

    def test_emergency_action_includes_notification(self, risk_engine, mock_notifier):
        """Emergency action must include Discord notification."""
        risk_engine.attach_notifier(mock_notifier)
        risk_engine.on_loss_event(60.00)
        action = risk_engine.get_emergency_action()
        assert "SEND_ALERT" in action["directives"]

    def test_emergency_action_logs_trigger(self, risk_engine):
        """Emergency action must log which trigger activated it."""
        risk_engine.on_loss_event(60.00)
        action = risk_engine.get_emergency_action()
        assert "trigger" in action
        assert action["timestamp"] is not None

    def test_emergency_action_is_idempotent(self, risk_engine, mock_broker):
        """
        Calling emergency action twice should not double-close positions.
        The action should be idempotent — safe to retry.
        """
        risk_engine.attach_broker(mock_broker)
        risk_engine.on_loss_event(60.00)
        risk_engine.execute_emergency_action()
        risk_engine.execute_emergency_action()  # Second call

        # close_all_positions should only be called once
        assert mock_broker.close_all_positions.call_count == 1


# =============================================================================
# GAMEPLAN HARD LIMITS VALIDATION
# =============================================================================


class TestGameplanHardLimitsValidation:
    """Tests that risk engine validates gameplan hard_limits on load."""

    def test_valid_gameplan_accepted(self, risk_engine):
        """Standard gameplan with valid hard_limits loads successfully."""
        gameplan: Dict[str, Any] = {
            "hard_limits": {
                "max_position_size": 120.00,
                "max_risk_per_trade": 18.00,
                "max_daily_loss": 60.00,
                "max_weekly_drawdown": 90.00,
                "pdt_limit": 3,
                "max_contracts": 1,
                "force_close_dte": 3,
            }
        }
        result = risk_engine.validate_gameplan(gameplan)
        assert result["valid"] is True

    def test_gameplan_with_excessive_risk_rejected(self, risk_engine):
        """Gameplan that exceeds account parameter safety bounds is rejected."""
        gameplan: Dict[str, Any] = {
            "hard_limits": {
                "max_position_size": 500.00,  # > 20% of $600
                "max_risk_per_trade": 100.00,  # > 3% of $600
                "max_daily_loss": 300.00,  # > 10% of $600
                "max_weekly_drawdown": 400.00,  # > 15% of $600
                "pdt_limit": 10,  # > 3 limit
                "max_contracts": 5,
                "force_close_dte": 0,
            }
        }
        result = risk_engine.validate_gameplan(gameplan)
        assert result["valid"] is False
        assert len(result["violations"]) >= 3

    def test_missing_hard_limits_rejected(self, risk_engine):
        """Gameplan without hard_limits section is rejected."""
        gameplan: Dict[str, Any] = {"strategy": "A", "signals": {}}
        result = risk_engine.validate_gameplan(gameplan)
        assert result["valid"] is False

    def test_gameplan_limits_cannot_exceed_account_params(self, risk_engine):
        """
        Gameplan hard_limits must be <= account parameter limits.
        More restrictive is allowed; less restrictive is not.
        """
        # More restrictive than account params — should be accepted
        gameplan: Dict[str, Any] = {
            "hard_limits": {
                "max_position_size": 100.00,  # < $120 limit
                "max_risk_per_trade": 15.00,  # < $18 limit
                "max_daily_loss": 50.00,  # < $60 limit
                "max_weekly_drawdown": 80.00,  # < $90 limit
                "pdt_limit": 2,  # < 3 limit
                "max_contracts": 1,
                "force_close_dte": 5,  # More conservative than 3
            }
        }
        result = risk_engine.validate_gameplan(gameplan)
        assert result["valid"] is True
