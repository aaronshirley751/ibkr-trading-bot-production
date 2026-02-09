"""
Risk bypass prevention tests (adversarial tests).

These tests verify that risk controls cannot be bypassed through:
- Direct manipulation of internal state
- Invalid inputs that might confuse validation
- Edge cases that might slip through

Coverage target: 98%
CRO MANDATE: Zero bypass paths allowed.

Threat model references: T-08 (bypass via direct order)
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.risk import (
    RiskManager,
    RiskDecision,
    RejectionReason,
    PositionSizeRequest,
    PositionSizer,
    PDTTracker,
    DrawdownMonitor,
)
from src.config.risk_config import RiskConfig

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def risk_manager(tmp_path: Path) -> RiskManager:
    """Create a RiskManager with temporary state files."""
    return RiskManager(
        config=RiskConfig(),
        state_dir=tmp_path,
        starting_equity=Decimal("600"),
    )


@pytest.fixture
def position_sizer() -> PositionSizer:
    """Create a PositionSizer for testing."""
    return PositionSizer(
        account_balance=600.00,
        max_position_pct=0.20,
        max_risk_pct=0.03,
        pdt_limit=3,
    )


@pytest.fixture
def pdt_tracker(tmp_path: Path) -> PDTTracker:
    """Create a PDTTracker with temporary state file."""
    return PDTTracker(
        trade_limit=3,
        window_days=5,
        state_file=tmp_path / "pdt_state.json",
    )


@pytest.fixture
def drawdown_monitor(tmp_path: Path) -> DrawdownMonitor:
    """Create a DrawdownMonitor with temporary state file."""
    return DrawdownMonitor(
        starting_equity=Decimal("600"),
        state_file=tmp_path / "drawdown_state.json",
    )


@pytest.fixture
def valid_request() -> PositionSizeRequest:
    """Create a valid position size request."""
    return PositionSizeRequest(
        symbol="SPY",
        strategy="A",
        signal_confidence=0.75,
        entry_price=Decimal("1.50"),
        stop_loss_pct=Decimal("0.25"),
        account_cash=Decimal("600"),
        current_positions_value=Decimal("0"),
    )


# =============================================================================
# FROZEN DATACLASS IMMUTABILITY TESTS
# =============================================================================


class TestDataclassImmutability:
    """Verify frozen dataclasses cannot be mutated after creation."""

    def test_position_size_request_is_immutable(self, valid_request):
        """PositionSizeRequest should be frozen (immutable)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            valid_request.symbol = "QQQ"

    def test_position_size_result_is_immutable(self, position_sizer, valid_request):
        """PositionSizeResult should be frozen (immutable)."""
        result, _ = position_sizer.calculate_position_size(valid_request)
        with pytest.raises(Exception):  # FrozenInstanceError
            result.approved_contracts = 999

    def test_risk_check_result_is_immutable(self, risk_manager, valid_request):
        """RiskCheckResult should be frozen (immutable)."""
        result = risk_manager.evaluate(valid_request)
        with pytest.raises(Exception):  # FrozenInstanceError
            result.approved_contracts = 999


# =============================================================================
# INVALID INPUT REJECTION TESTS
# =============================================================================


class TestInvalidInputRejection:
    """Verify invalid inputs are properly rejected."""

    def test_negative_confidence_rejected(self, risk_manager):
        """Negative confidence should be rejected."""
        request = PositionSizeRequest(
            symbol="SPY",
            strategy="A",
            signal_confidence=-0.5,  # Invalid negative
            entry_price=Decimal("1.50"),
            stop_loss_pct=Decimal("0.25"),
            account_cash=Decimal("600"),
            current_positions_value=Decimal("0"),
        )
        result = risk_manager.evaluate(request)
        assert result.decision == RiskDecision.REJECTED
        assert result.rejection_reason == RejectionReason.CONFIDENCE_BELOW_THRESHOLD

    def test_confidence_above_one_treated_as_max(self, risk_manager):
        """Confidence > 1.0 should still work (confidence is valid if >= threshold)."""
        request = PositionSizeRequest(
            symbol="SPY",
            strategy="A",
            signal_confidence=1.5,  # Above 1.0 but still passes threshold
            entry_price=Decimal("1.50"),
            stop_loss_pct=Decimal("0.25"),
            account_cash=Decimal("600"),
            current_positions_value=Decimal("0"),
        )
        result = risk_manager.evaluate(request)
        # Should not reject due to confidence (might reject due to other limits)
        assert result.rejection_reason != RejectionReason.CONFIDENCE_BELOW_THRESHOLD

    def test_zero_entry_price_rejected(self, risk_manager):
        """Zero entry price should be rejected."""
        request = PositionSizeRequest(
            symbol="SPY",
            strategy="A",
            signal_confidence=0.75,
            entry_price=Decimal("0"),  # Invalid
            stop_loss_pct=Decimal("0.25"),
            account_cash=Decimal("600"),
            current_positions_value=Decimal("0"),
        )
        result = risk_manager.evaluate(request)
        assert result.decision == RiskDecision.REJECTED
        assert result.rejection_reason == RejectionReason.PREMIUM_UNAFFORDABLE

    def test_negative_entry_price_rejected(self, risk_manager):
        """Negative entry price should be rejected."""
        request = PositionSizeRequest(
            symbol="SPY",
            strategy="A",
            signal_confidence=0.75,
            entry_price=Decimal("-1.50"),  # Invalid
            stop_loss_pct=Decimal("0.25"),
            account_cash=Decimal("600"),
            current_positions_value=Decimal("0"),
        )
        result = risk_manager.evaluate(request)
        assert result.decision == RiskDecision.REJECTED
        assert result.rejection_reason == RejectionReason.PREMIUM_UNAFFORDABLE

    def test_strategy_c_always_rejected(self, risk_manager):
        """Strategy C should always reject new positions."""
        request = PositionSizeRequest(
            symbol="SPY",
            strategy="C",  # No trading in Strategy C
            signal_confidence=0.99,
            entry_price=Decimal("0.50"),
            stop_loss_pct=Decimal("0.25"),
            account_cash=Decimal("600"),
            current_positions_value=Decimal("0"),
        )
        result = risk_manager.evaluate(request)
        assert result.decision == RiskDecision.STRATEGY_C_LOCKED
        assert result.rejection_reason == RejectionReason.STRATEGY_C_ACTIVE


# =============================================================================
# POSITION SIZE LIMIT BYPASS TESTS
# =============================================================================


class TestPositionSizeLimitBypass:
    """Verify position size limits cannot be bypassed."""

    def test_cannot_exceed_20_percent_strategy_a(self, position_sizer):
        """Strategy A cannot exceed 20% position size."""
        # With $600 balance, max position = $120
        # Premium $3.00 * 100 multiplier = $300 per contract
        # Should allow 0 contracts (exceeds limit)
        assert position_sizer.validate_position_size(300.00) is False
        assert position_sizer.validate_position_size(120.00) is True
        assert position_sizer.validate_position_size(120.01) is False

    def test_cannot_exceed_risk_limit(self, position_sizer):
        """Cannot exceed 3% risk per trade ($18)."""
        assert position_sizer.validate_trade_risk(18.00) is True
        assert position_sizer.validate_trade_risk(18.01) is False

    def test_large_numbers_dont_overflow(self, position_sizer):
        """Very large position sizes are still rejected properly."""
        # Test with extremely large number
        assert position_sizer.validate_position_size(1_000_000.00) is False
        assert position_sizer.validate_trade_risk(1_000_000.00) is False


# =============================================================================
# PDT BYPASS TESTS
# =============================================================================


class TestPDTBypass:
    """Verify PDT limits cannot be bypassed."""

    def test_cannot_exceed_3_day_trades(self, risk_manager, valid_request, tmp_path):
        """Cannot execute 4th day trade in window."""
        # Record 3 day trades
        now = datetime.now()
        for i in range(3):
            risk_manager._pdt_tracker.record_day_trade(
                symbol=f"SPY{i}",
                entry_time=now,
                exit_time=now,
                contracts=1,
            )

        # 4th day trade should be blocked
        assert risk_manager._pdt_tracker.can_day_trade() is False
        assert risk_manager._pdt_tracker.trades_remaining() == 0

    def test_pdt_state_persists_after_reload(self, tmp_path):
        """PDT state survives tracker recreation."""
        state_file = tmp_path / "pdt_test.json"

        # Create tracker and record trades
        tracker1 = PDTTracker(state_file=state_file)
        now = datetime.now()
        tracker1.record_day_trade("SPY", now, now, 1)
        tracker1.record_day_trade("QQQ", now, now, 1)

        # Create new tracker with same state file
        tracker2 = PDTTracker(state_file=state_file)
        assert tracker2.trades_used() == 2
        assert tracker2.trades_remaining() == 1


# =============================================================================
# DRAWDOWN BYPASS TESTS
# =============================================================================


class TestDrawdownBypass:
    """Verify drawdown limits cannot be bypassed."""

    def test_daily_limit_blocks_all_trading(self, drawdown_monitor):
        """Once daily limit hit, all trading should be blocked."""
        # Simulate 10% loss (daily limit)
        new_equity = Decimal("540")  # 10% loss from 600
        drawdown_monitor.update_equity(new_equity)

        can_trade, reason = drawdown_monitor.can_trade()
        assert can_trade is False
        assert reason == "daily_loss_limit"

    def test_weekly_governor_blocks_all_trading(self, tmp_path):
        """Once weekly governor triggers, all trading should be blocked."""
        # Create a fresh monitor with no prior daily state
        monitor = DrawdownMonitor(
            starting_equity=Decimal("600"),
            state_file=tmp_path / "drawdown_weekly.json",
        )
        # First, reset daily to same as weekly start (simulating start of week)
        monitor.reset_daily(Decimal("600"))
        # Now simulate losses over multiple days that exceed 15% weekly
        # but stay under 10% daily
        # Day 1: lose 8% daily
        monitor.update_equity(Decimal("552"))  # 8% loss today
        can_trade, reason = monitor.can_trade()
        assert can_trade is True  # Still under daily limit

        # Simulate new day start at current equity
        monitor.reset_daily(Decimal("552"))
        # Day 2: lose another 8% of remaining (~7.4% weekly additional)
        monitor.update_equity(Decimal("508"))  # Total ~15.3% weekly loss

        # Now governor should trigger (weekly > 15%)
        assert monitor.is_governor_active() is True
        can_trade, reason = monitor.can_trade()
        assert can_trade is False

    def test_drawdown_state_persists(self, tmp_path):
        """Drawdown state survives monitor recreation."""
        state_file = tmp_path / "drawdown_test.json"

        # Create monitor and trigger governor
        monitor1 = DrawdownMonitor(
            starting_equity=Decimal("600"),
            state_file=state_file,
        )
        monitor1.update_equity(Decimal("510"))  # 15% loss = governor
        assert monitor1.is_governor_active() is True

        # Create new monitor with same state file
        monitor2 = DrawdownMonitor(
            starting_equity=Decimal("600"),
            state_file=state_file,
        )
        assert monitor2.is_governor_active() is True


# =============================================================================
# RISK MANAGER INTEGRATION BYPASS TESTS
# =============================================================================


class TestRiskManagerBypass:
    """Verify RiskManager cannot be bypassed."""

    def test_governor_blocks_before_position_sizing(self, risk_manager, valid_request):
        """Governor check happens before expensive position sizing."""
        # Trigger governor
        risk_manager._drawdown_monitor.update_equity(Decimal("510"))  # 15% loss

        result = risk_manager.evaluate(valid_request)
        assert result.decision == RiskDecision.STRATEGY_C_LOCKED
        assert result.rejection_reason == RejectionReason.WEEKLY_DRAWDOWN_GOVERNOR

    def test_daily_limit_blocks_before_pdt(self, risk_manager, valid_request):
        """Daily limit check happens before PDT check."""
        # Trigger daily limit
        risk_manager._drawdown_monitor.update_equity(Decimal("540"))  # 10% loss

        result = risk_manager.evaluate(valid_request, is_day_trade=True)
        assert result.decision == RiskDecision.REJECTED
        assert result.rejection_reason == RejectionReason.DAILY_LOSS_LIMIT_REACHED

    def test_check_sequence_is_correct(self, tmp_path):
        """Verify checks happen in correct order: governor -> daily -> pdt -> sizing."""
        # Create fresh risk manager for this test
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "sequence_test",
            starting_equity=Decimal("600"),
        )

        # 1. First, governor should block (even with valid request)
        manager._drawdown_monitor.reset_daily(Decimal("600"))
        manager._drawdown_monitor.update_equity(Decimal("560"))  # 6.6% daily
        manager._drawdown_monitor.reset_daily(Decimal("560"))
        manager._drawdown_monitor.update_equity(Decimal("505"))  # ~15.8% weekly total

        request = PositionSizeRequest(
            symbol="SPY",
            strategy="A",
            signal_confidence=0.99,
            entry_price=Decimal("0.50"),
            stop_loss_pct=Decimal("0.25"),
            account_cash=Decimal("600"),
            current_positions_value=Decimal("0"),
        )
        result = manager.evaluate(request)
        assert result.rejection_reason == RejectionReason.WEEKLY_DRAWDOWN_GOVERNOR

        # 2. Create fresh manager for daily limit test
        manager2 = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "sequence_test2",
            starting_equity=Decimal("600"),
        )
        manager2._drawdown_monitor.update_equity(Decimal("540"))  # 10% daily loss
        result = manager2.evaluate(request)
        assert result.rejection_reason == RejectionReason.DAILY_LOSS_LIMIT_REACHED


# =============================================================================
# DECIMAL PRECISION TESTS
# =============================================================================


class TestDecimalPrecision:
    """Verify financial calculations maintain precision."""

    def test_no_floating_point_errors_at_boundary(self, position_sizer):
        """Boundary calculations don't suffer from floating-point errors."""
        # Classic floating-point issue: 0.1 + 0.2 != 0.3
        # Our code should handle this correctly
        result = position_sizer.validate_position_size(120.00)
        assert result is True

        # Very small amounts above limit should be rejected
        result = position_sizer.validate_position_size(120.0000001)
        assert result is False

    def test_decimal_calculations_are_exact(self, tmp_path):
        """Decimal arithmetic should be exact, not approximate."""
        # Create fresh monitor
        monitor = DrawdownMonitor(
            starting_equity=Decimal("600"),
            state_file=tmp_path / "decimal_test.json",
        )
        monitor.reset_weekly(Decimal("600"))
        monitor.update_equity(Decimal("540"))  # Exactly 10%

        # Verify exact calculation
        assert monitor._state.daily_drawdown_pct == Decimal("0.1")

    def test_risk_amount_calculation_precision(self, position_sizer):
        """Risk calculations maintain decimal precision."""
        # Entry $1.00, stop $0.75 = 25% loss
        # Risk = $0.25 * 100 * 1 = $25.00 exactly
        risk = position_sizer.calculate_trade_risk(
            entry_price=1.00,
            stop_price=0.75,
            multiplier=100,
            quantity=1,
        )
        assert risk == pytest.approx(25.00, abs=0.001)


# =============================================================================
# RISK MANAGER HELPER METHOD COVERAGE
# =============================================================================


class TestRiskManagerCoverage:
    """Tests for RiskManager methods not covered by bypass tests."""

    def test_record_trade_entry_tracks_position(self, tmp_path):
        """record_trade_entry should track position for day trade detection."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "entry_test",
            starting_equity=Decimal("600"),
        )
        entry_time = datetime.now()

        manager.record_trade_entry("SPY", 1, Decimal("0.50"), entry_time)

        assert "SPY" in manager._open_positions
        assert manager._open_positions["SPY"]["contracts"] == 1
        assert manager._open_positions["SPY"]["entry_time"] == entry_time

    def test_record_trade_exit_same_day_is_day_trade(self, tmp_path):
        """Exit on same day as entry should count as day trade."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "exit_test",
            starting_equity=Decimal("600"),
        )
        entry_time = datetime.now()
        exit_time = entry_time + timedelta(hours=2)  # Same day

        manager.record_trade_entry("SPY", 1, Decimal("0.50"), entry_time)
        manager.record_trade_exit(
            symbol="SPY",
            contracts=1,
            exit_price=Decimal("0.60"),
            exit_time=exit_time,
            realized_pnl=Decimal("10.00"),
        )

        assert manager._pdt_tracker.trades_used() == 1
        assert "SPY" not in manager._open_positions

    def test_record_trade_exit_next_day_not_day_trade(self, tmp_path):
        """Exit on next day should NOT count as day trade."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "exit_next_test",
            starting_equity=Decimal("600"),
        )
        entry_time = datetime.now()
        exit_time = entry_time + timedelta(days=1)  # Next day

        manager.record_trade_entry("SPY", 1, Decimal("0.50"), entry_time)
        manager.record_trade_exit(
            symbol="SPY",
            contracts=1,
            exit_price=Decimal("0.60"),
            exit_time=exit_time,
            realized_pnl=Decimal("10.00"),
        )

        # Not a day trade, so PDT count stays 0
        assert manager._pdt_tracker.trades_used() == 0

    def test_update_equity_updates_drawdown_monitor(self, tmp_path):
        """update_equity should propagate to drawdown monitor."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "equity_test",
            starting_equity=Decimal("600"),
        )

        manager.update_equity(Decimal("580"))

        assert manager._drawdown_monitor._state.current_equity == Decimal("580")

    def test_start_new_trading_day_resets_daily(self, tmp_path):
        """start_new_trading_day should reset daily drawdown."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "day_test",
            starting_equity=Decimal("600"),
        )
        manager._drawdown_monitor.update_equity(Decimal("550"))  # Drawdown

        manager.start_new_trading_day(Decimal("550"))

        assert manager._drawdown_monitor._state.daily_drawdown_pct == Decimal("0")

    def test_start_new_trading_week_resets_weekly(self, tmp_path):
        """start_new_trading_week should reset weekly drawdown."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "week_test",
            starting_equity=Decimal("600"),
        )
        manager._drawdown_monitor.update_equity(Decimal("550"))

        manager.start_new_trading_week(Decimal("550"))

        assert manager._drawdown_monitor._state.weekly_drawdown_pct == Decimal("0")

    def test_get_risk_status_returns_all_metrics(self, tmp_path):
        """get_risk_status should return comprehensive status dict."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=tmp_path / "status_test",
            starting_equity=Decimal("600"),
        )

        status = manager.get_risk_status()

        assert "pdt" in status
        assert "daily" in status
        assert "weekly" in status
        assert status["pdt"]["limit"] == 3
        assert status["pdt"]["trades_remaining"] == 3

    def test_default_state_dir_used_when_none(self):
        """When state_dir is None, default './state' should be used."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=None,
            starting_equity=Decimal("600"),
        )

        # Should not raise - default state dir used
        assert manager._pdt_tracker is not None

    def test_default_starting_equity_from_config(self):
        """When starting_equity is None, config value should be used."""
        manager = RiskManager(
            config=RiskConfig(),
            state_dir=Path("state"),
            starting_equity=None,
        )

        # Should use config's starting_capital ($600)
        assert manager._drawdown_monitor._state.daily_start_equity == Decimal("600")
