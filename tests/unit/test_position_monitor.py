"""
Unit tests for src/bot/position_monitor.py

Coverage:
    - OpenPosition dataclass defaults
    - PositionMonitor add / remove / query
    - ExitSignal evaluation: stop-loss, take-profit, time-stop, DTE force-close
    - Hold (no exit condition met)
    - Priority ordering: stop-loss beats take-profit on extreme gaps
    - Edge: evaluate with no tracked position
    - Edge: current_price exactly at threshold boundaries
    - Edge: DTE = 0 (expiry today)
    - Edge: non-UTC timezone-aware expiry date
    - TradeLog.get_buffer() smoke test
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict


from src.bot.position_monitor import OpenPosition, PositionMonitor
from src.bot.trade_log import TradeDecision, TradeLog

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_position(**kwargs: Any) -> OpenPosition:
    defaults: Dict[str, Any] = dict(
        symbol="QQQ",
        entry_price=1.50,
        entry_time=datetime(2026, 3, 2, 14, 0, 0, tzinfo=timezone.utc),
        quantity=1,
        order_id=1,
        take_profit_pct=0.15,
        stop_loss_pct=0.25,
        time_stop_minutes=90,
        force_close_dte=1,
        expiry_date=None,
    )
    defaults.update(kwargs)
    return OpenPosition(**defaults)


def _now(offset_minutes: int = 0) -> datetime:
    return datetime(2026, 3, 2, 14, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=offset_minutes)


# ---------------------------------------------------------------------------
# TestOpenPosition
# ---------------------------------------------------------------------------


class TestOpenPosition:
    def test_defaults(self) -> None:
        pos = OpenPosition(
            symbol="SPY",
            entry_price=2.00,
            entry_time=datetime.now(timezone.utc),
            quantity=2,
            order_id=5,
        )
        assert pos.take_profit_pct == 0.15
        assert pos.stop_loss_pct == 0.25
        assert pos.time_stop_minutes == 90
        assert pos.force_close_dte == 1
        assert pos.expiry_date is None

    def test_custom_params(self) -> None:
        pos = _make_position(take_profit_pct=0.20, stop_loss_pct=0.10, time_stop_minutes=60)
        assert pos.take_profit_pct == 0.20
        assert pos.stop_loss_pct == 0.10
        assert pos.time_stop_minutes == 60


# ---------------------------------------------------------------------------
# TestPositionMonitorManagement
# ---------------------------------------------------------------------------


class TestPositionMonitorManagement:
    def test_empty_on_init(self) -> None:
        monitor = PositionMonitor()
        assert not monitor.has_open_positions()
        assert monitor.get_positions() == []

    def test_add_and_get(self) -> None:
        monitor = PositionMonitor()
        pos = _make_position(symbol="QQQ")
        monitor.add_position(pos)
        assert monitor.has_open_positions()
        assert monitor.get_position("QQQ") is pos

    def test_remove(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(symbol="QQQ"))
        monitor.remove_position("QQQ")
        assert not monitor.has_open_positions()
        assert monitor.get_position("QQQ") is None

    def test_remove_nonexistent_is_noop(self) -> None:
        monitor = PositionMonitor()
        monitor.remove_position("MISSING")  # must not raise

    def test_multiple_positions(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(symbol="QQQ"))
        monitor.add_position(_make_position(symbol="SPY"))
        assert len(monitor.get_positions()) == 2

    def test_overwrite_existing_symbol(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(symbol="QQQ", entry_price=1.00))
        monitor.add_position(_make_position(symbol="QQQ", entry_price=2.00))
        assert monitor.get_position("QQQ").entry_price == 2.00  # type: ignore[union-attr]

    def test_get_positions_is_snapshot(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(symbol="QQQ"))
        snapshot = monitor.get_positions()
        monitor.add_position(_make_position(symbol="SPY"))
        # Original snapshot should not grow
        assert len(snapshot) == 1


# ---------------------------------------------------------------------------
# TestExitEvaluation — Hold
# ---------------------------------------------------------------------------


class TestExitEvaluationHold:
    def test_no_position_tracked(self) -> None:
        monitor = PositionMonitor()
        signal = monitor.evaluate("QQQ", current_price=1.50)
        assert not signal.should_exit
        assert signal.details == "no_position_tracked"

    def test_hold_midpoint(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(entry_price=1.50))
        # Neither TP (>=1.725) nor SL (<=1.125)
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(45))
        assert not signal.should_exit
        assert signal.reason is None
        assert signal.details == "hold"


# ---------------------------------------------------------------------------
# TestExitEvaluation — Stop-Loss
# ---------------------------------------------------------------------------


class TestExitEvaluationStopLoss:
    def test_stop_loss_at_exact_threshold(self) -> None:
        monitor = PositionMonitor()
        # entry=1.50, SL=25% → stop_price=1.125
        monitor.add_position(_make_position(entry_price=1.50, stop_loss_pct=0.25))
        signal = monitor.evaluate("QQQ", current_price=1.125, now=_now(10))
        assert signal.should_exit
        assert signal.reason == "stop_loss"

    def test_stop_loss_below_threshold(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(entry_price=1.50, stop_loss_pct=0.25))
        signal = monitor.evaluate("QQQ", current_price=0.50, now=_now(10))
        assert signal.should_exit
        assert signal.reason == "stop_loss"

    def test_stop_loss_one_cent_above_is_hold(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(entry_price=1.50, stop_loss_pct=0.25))
        # stop_price=1.125; current=1.126 — just above threshold
        signal = monitor.evaluate("QQQ", current_price=1.126, now=_now(10))
        assert not signal.should_exit

    def test_stop_loss_priority_over_take_profit(self) -> None:
        """A gap-down to zero triggers stop-loss, not take-profit."""
        monitor = PositionMonitor()
        monitor.add_position(
            _make_position(entry_price=1.50, stop_loss_pct=0.01, take_profit_pct=0.01)
        )
        # Price went to 0: below both thresholds, but stop-loss evaluated first
        signal = monitor.evaluate("QQQ", current_price=0.0, now=_now(5))
        assert signal.reason == "stop_loss"


# ---------------------------------------------------------------------------
# TestExitEvaluation — Take-Profit
# ---------------------------------------------------------------------------


class TestExitEvaluationTakeProfit:
    def test_take_profit_at_exact_threshold(self) -> None:
        monitor = PositionMonitor()
        # entry=1.50, TP=15% → tp_price=1.725
        monitor.add_position(_make_position(entry_price=1.50, take_profit_pct=0.15))
        signal = monitor.evaluate("QQQ", current_price=1.725, now=_now(10))
        assert signal.should_exit
        assert signal.reason == "take_profit"

    def test_take_profit_above_threshold(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(entry_price=1.50, take_profit_pct=0.15))
        signal = monitor.evaluate("QQQ", current_price=2.50, now=_now(10))
        assert signal.should_exit
        assert signal.reason == "take_profit"

    def test_take_profit_one_cent_below_is_hold(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(entry_price=1.50, take_profit_pct=0.15))
        # tp_price=1.725; current=1.724
        signal = monitor.evaluate("QQQ", current_price=1.724, now=_now(10))
        assert not signal.should_exit


# ---------------------------------------------------------------------------
# TestExitEvaluation — Time-Stop
# ---------------------------------------------------------------------------


class TestExitEvaluationTimeStop:
    def test_time_stop_at_exact_limit(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(entry_price=1.50, time_stop_minutes=90))
        # 90 minutes after entry
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(90))
        assert signal.should_exit
        assert signal.reason == "time_stop"

    def test_time_stop_one_minute_before_is_hold(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(entry_price=1.50, time_stop_minutes=90))
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(89))
        assert not signal.should_exit

    def test_time_stop_priority_below_sl_tp(self) -> None:
        """Time-stop fires only if SL and TP did not trigger first."""
        monitor = PositionMonitor()
        # Tight TP at 5% — price is below TP but time expired
        monitor.add_position(
            _make_position(entry_price=1.50, time_stop_minutes=10, take_profit_pct=0.05)
        )
        # current=1.40 is below both SL and TP, time elapsed=120 minutes
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(120))
        # SL at 1.125 — price 1.40 is above; TP at 1.575 — price 1.40 is below → time-stop
        assert signal.reason == "time_stop"


# ---------------------------------------------------------------------------
# TestExitEvaluation — DTE Force-Close
# ---------------------------------------------------------------------------


class TestExitEvaluationDTE:
    def test_dte_force_close_at_threshold(self) -> None:
        monitor = PositionMonitor()
        # Expiry is tomorrow (DTE=1 which equals force_close_dte=1)
        tomorrow = datetime(2026, 3, 3, 21, 0, 0, tzinfo=timezone.utc)
        monitor.add_position(
            _make_position(entry_price=1.50, force_close_dte=1, expiry_date=tomorrow)
        )
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(0))
        assert signal.should_exit
        assert signal.reason == "dte_force_close"
        assert "dte=1" in signal.details

    def test_dte_zero_triggers_force_close(self) -> None:
        monitor = PositionMonitor()
        today = datetime(2026, 3, 2, 21, 0, 0, tzinfo=timezone.utc)
        monitor.add_position(_make_position(entry_price=1.50, force_close_dte=1, expiry_date=today))
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(0))
        assert signal.should_exit
        assert signal.reason == "dte_force_close"

    def test_dte_two_days_is_hold(self) -> None:
        monitor = PositionMonitor()
        day_after_tomorrow = datetime(2026, 3, 4, 21, 0, 0, tzinfo=timezone.utc)
        monitor.add_position(
            _make_position(entry_price=1.50, force_close_dte=1, expiry_date=day_after_tomorrow)
        )
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(0))
        assert not signal.should_exit

    def test_no_expiry_date_skips_dte_check(self) -> None:
        monitor = PositionMonitor()
        monitor.add_position(_make_position(entry_price=1.50, expiry_date=None))
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(10))
        assert not signal.should_exit

    def test_naive_expiry_treated_as_utc(self) -> None:
        """Naive expiry datetime should not crash — treated as UTC."""
        monitor = PositionMonitor()
        naive_expiry = datetime(2026, 3, 2, 21, 0, 0)  # no tzinfo
        monitor.add_position(
            _make_position(entry_price=1.50, force_close_dte=1, expiry_date=naive_expiry)
        )
        signal = monitor.evaluate("QQQ", current_price=1.40, now=_now(0))
        assert signal.should_exit
        assert signal.reason == "dte_force_close"


# ---------------------------------------------------------------------------
# TestTradeLogBuffer
# ---------------------------------------------------------------------------


class TestTradeLogBuffer:
    def _make_decision(self, outcome: str) -> TradeDecision:
        return TradeDecision(
            timestamp="2026-03-02T14:00:00+00:00",
            symbol="QQQ",
            strategy="A",
            cycle_count=1,
            signal_direction="buy",
            signal_confidence=0.75,
            signal_rationale="test",
            outcome=outcome,
        )

    def test_get_buffer_empty(self, tmp_path) -> None:
        log = TradeLog(tmp_path)
        assert log.get_buffer() == []

    def test_get_buffer_after_records(self, tmp_path) -> None:
        log = TradeLog(tmp_path)
        log.record(self._make_decision("hold"))
        log.record(self._make_decision("submitted"))
        log.record(self._make_decision("dry_run"))
        buf = log.get_buffer()
        assert len(buf) == 3
        assert [d.outcome for d in buf] == ["hold", "submitted", "dry_run"]

    def test_get_buffer_returns_copy(self, tmp_path) -> None:
        log = TradeLog(tmp_path)
        log.record(self._make_decision("hold"))
        buf1 = log.get_buffer()
        log.record(self._make_decision("submitted"))
        buf2 = log.get_buffer()
        # buf1 should not have grown
        assert len(buf1) == 1
        assert len(buf2) == 2
