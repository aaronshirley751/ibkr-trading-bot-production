"""
E2E tests for complete trading cycle.

Tests cover:
- Full workflow: gameplan -> signal -> risk check -> order -> fill -> tracking -> exit
- Strategy A cycle (momentum breakout)
- Strategy B cycle (mean reversion fade)
- Strategy C behavior (cash preservation — no trades)
- Multi-symbol sessions (SPY + QQQ)
- Strategy transitions (A -> B -> C based on regime changes)
- Exit path validation (take-profit, stop-loss, time-stop)
- State persistence across cycles within a session

Tests using existing strategy selection/signal evaluation are FUNCTIONAL.
Tests requiring the Phase 2 TradingOrchestrator are SKIPPED.
"""

import copy

import pytest

from src.strategy.execution import evaluate_signals
from src.strategy.selection import (
    STRATEGY_A_PARAMS,
    STRATEGY_B_PARAMS,
    STRATEGY_C_PARAMS,
    detect_regime,
    select_strategy,
)
from src.strategy.signals import (
    evaluate_strategy_a_signal,
    evaluate_strategy_b_signal,
)

pytestmark = pytest.mark.e2e

ORCHESTRATOR_SKIP = "TradingOrchestrator implementation pending Phase 2"


# =================================================================
# STRATEGY A — COMPLETE MOMENTUM BREAKOUT CYCLE
# =================================================================


class TestStrategyAFullCycle:
    """Full trade cycle tests for Strategy A (momentum breakout)."""

    def test_strategy_a_signal_generated_from_trending_data(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Strategy A gameplan + bullish trending SPY market data
        WHEN: evaluate_signals processes the pipeline
        THEN: BUY signal generated for SPY with strategy A
        """
        decisions = evaluate_signals(valid_strategy_a_gameplan, trending_spy_market_data)

        assert len(decisions) >= 1
        spy_decision = decisions[0]
        assert spy_decision["symbol"] == "SPY"
        assert spy_decision["strategy"] == "A"
        assert spy_decision["action"] == "BUY"
        assert spy_decision["confidence"] > 0

    def test_strategy_a_no_signal_from_flat_data(
        self, valid_strategy_a_gameplan, flat_spy_market_data
    ):
        """
        GIVEN: Strategy A gameplan + flat SPY market data (no trend)
        WHEN: evaluate_signals processes the pipeline
        THEN: NEUTRAL signal — no trade entry
        """
        decisions = evaluate_signals(valid_strategy_a_gameplan, flat_spy_market_data)

        assert len(decisions) >= 1
        spy_decision = decisions[0]
        assert spy_decision["symbol"] == "SPY"
        assert spy_decision["action"] == "NEUTRAL"

    def test_strategy_a_no_data_returns_neutral(self, valid_strategy_a_gameplan):
        """
        GIVEN: Strategy A gameplan but NO market data for SPY
        WHEN: evaluate_signals called with empty market data
        THEN: NEUTRAL decision (can't trade without data)
        """
        decisions = evaluate_signals(valid_strategy_a_gameplan, {})

        assert len(decisions) >= 1
        spy_decision = decisions[0]
        assert spy_decision["action"] == "NEUTRAL"
        assert "No market data" in spy_decision["signal_details"]["reason"]

    def test_strategy_a_raw_signal_evaluation(self, trending_spy_bars):
        """
        GIVEN: 30 ascending SPY bars with VWAP confirmation
        WHEN: evaluate_strategy_a_signal is called directly
        THEN: Returns BUY with all three conditions met
        """
        result = evaluate_strategy_a_signal(trending_spy_bars)

        assert result["signal"] == "BUY"
        assert result["confidence"] > 0.9
        assert result["stale_data"] is False
        assert result["insufficient_data"] is False

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_strategy_a_entry_to_exit_profitable(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Strategy A signal triggers BUY
        WHEN: Full cycle: entry -> price rises -> take-profit exit
        THEN: Positive realized P&L, position closed cleanly
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_strategy_a_entry_to_stop_loss(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Strategy A signal triggers BUY
        WHEN: Price drops below stop-loss level (25% of premium)
        THEN: Stop-loss exit triggered, loss limited to expected max
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_strategy_a_entry_to_time_stop(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Strategy A position open for > 90 minutes
        WHEN: Time-stop threshold crossed
        THEN: Position closed at market regardless of P&L
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_strategy_a_risk_rejects_oversized_position(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Position size exceeds 20% of account ($120)
        WHEN: Risk manager pre-trade check runs
        THEN: Order rejected, no position opened
        """

    def test_strategy_a_multi_symbol_spy_and_qqq(
        self, valid_strategy_a_gameplan, trending_spy_bars
    ):
        """
        GIVEN: Strategy A gameplan with symbols=["SPY", "QQQ"]
        WHEN: evaluate_signals processes both symbols
        THEN: Each symbol evaluated independently
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["symbols"] = ["SPY", "QQQ"]

        market_data = {
            "SPY": trending_spy_bars,
            "QQQ": trending_spy_bars,  # Reuse trending data for both
        }

        decisions = evaluate_signals(gameplan, market_data)

        assert len(decisions) == 2
        symbols_in_decisions = {d["symbol"] for d in decisions}
        assert symbols_in_decisions == {"SPY", "QQQ"}


# =================================================================
# STRATEGY B — COMPLETE MEAN REVERSION CYCLE
# =================================================================


class TestStrategyBFullCycle:
    """Full trade cycle tests for Strategy B (mean reversion fade)."""

    def test_strategy_b_signal_generated_from_oversold_data(
        self, valid_strategy_b_gameplan, oversold_spy_market_data
    ):
        """
        GIVEN: Strategy B gameplan + oversold SPY market data
        WHEN: evaluate_signals processes the pipeline
        THEN: BUY signal generated (oversold condition detected)
        """
        decisions = evaluate_signals(valid_strategy_b_gameplan, oversold_spy_market_data)

        assert len(decisions) >= 1
        spy_decision = decisions[0]
        assert spy_decision["symbol"] == "SPY"
        assert spy_decision["strategy"] == "B"
        assert spy_decision["action"] == "BUY"

    def test_strategy_b_raw_signal_evaluation(self, oversold_spy_bars):
        """
        GIVEN: 30 descending SPY bars (RSI oversold)
        WHEN: evaluate_strategy_b_signal is called directly
        THEN: Returns BUY signal (oversold condition)
        """
        result = evaluate_strategy_b_signal(oversold_spy_bars)

        assert result["signal"] == "BUY"
        assert result["confidence"] > 0
        assert result["indicators"]["rsi"] is not None
        assert result["indicators"]["rsi"] < 30  # Oversold

    def test_strategy_b_params_differ_from_strategy_a(self):
        """
        GIVEN: Strategy A and B parameter constants
        WHEN: Compared directly
        THEN: B has tighter risk parameters (lower risk, shorter hold)
        """
        # Values are float/int but dict is typed Dict[str, object]; cast is safe here
        b_risk = float(STRATEGY_B_PARAMS["max_risk_pct"])  # type: ignore[arg-type]
        a_risk = float(STRATEGY_A_PARAMS["max_risk_pct"])  # type: ignore[arg-type]
        assert b_risk < a_risk

        b_pos = float(STRATEGY_B_PARAMS["max_position_pct"])  # type: ignore[arg-type]
        a_pos = float(STRATEGY_A_PARAMS["max_position_pct"])  # type: ignore[arg-type]
        assert b_pos < a_pos

        b_stop = float(STRATEGY_B_PARAMS["stop_loss_pct"])  # type: ignore[arg-type]
        a_stop = float(STRATEGY_A_PARAMS["stop_loss_pct"])  # type: ignore[arg-type]
        assert b_stop < a_stop

        b_time = float(STRATEGY_B_PARAMS["time_stop_minutes"])  # type: ignore[arg-type]
        a_time = float(STRATEGY_A_PARAMS["time_stop_minutes"])  # type: ignore[arg-type]
        assert b_time < a_time

    def test_strategy_b_spy_only_restriction(self, valid_strategy_b_gameplan):
        """
        GIVEN: Strategy B gameplan with symbols=["SPY"] only
        WHEN: select_strategy selects B from elevated VIX
        THEN: Only SPY is in the eligible symbols list
        """
        result = select_strategy(vix=22.0)

        assert result["strategy"] == "B"
        assert "SPY" in result["symbols"]
        # Strategy B does NOT trade QQQ per Crucible doctrine
        assert "QQQ" not in result["symbols"]

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_strategy_b_entry_to_exit_profitable(
        self, valid_strategy_b_gameplan, oversold_spy_market_data
    ):
        """
        GIVEN: Strategy B signal triggers BUY on oversold
        WHEN: Mean reversion occurs, price returns to VWAP
        THEN: Take-profit exit at 8% gain on premium
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_strategy_b_tighter_stop_loss_than_a(
        self, valid_strategy_b_gameplan, oversold_spy_market_data
    ):
        """
        GIVEN: Strategy B position open
        WHEN: Price drops below 15% stop (vs 25% for A)
        THEN: Stop fires earlier, limiting loss
        """


# =================================================================
# STRATEGY C — CASH PRESERVATION BEHAVIOR
# =================================================================


class TestStrategyCBehavior:
    """Tests for Strategy C (no trading) behavior."""

    def test_strategy_c_returns_hold_decisions(self, valid_strategy_c_gameplan):
        """
        GIVEN: Strategy C gameplan
        WHEN: evaluate_signals is called
        THEN: Returns HOLD for all symbols (cash preservation)
        """
        decisions = evaluate_signals(valid_strategy_c_gameplan, {})

        assert len(decisions) >= 1
        for d in decisions:
            assert d["strategy"] == "C"
            assert d["action"] == "HOLD"

    def test_strategy_c_even_with_market_data(
        self, valid_strategy_c_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Strategy C gameplan but trending market data available
        WHEN: evaluate_signals is called with data
        THEN: Still returns HOLD — Strategy C ignores all data
        """
        decisions = evaluate_signals(valid_strategy_c_gameplan, trending_spy_market_data)

        for d in decisions:
            assert d["strategy"] == "C"
            assert d["action"] == "HOLD"

    def test_strategy_c_params_are_zero(self):
        """
        GIVEN: Strategy C parameter constants
        WHEN: Inspected
        THEN: All risk/position parameters are zero (no trading)
        """
        assert STRATEGY_C_PARAMS["max_risk_pct"] == 0.0
        assert STRATEGY_C_PARAMS["max_position_pct"] == 0.0
        assert STRATEGY_C_PARAMS["take_profit_pct"] == 0.0
        assert STRATEGY_C_PARAMS["time_stop_minutes"] == 0

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_strategy_c_closes_existing_positions_at_3dte(self, valid_strategy_c_gameplan):
        """
        GIVEN: Strategy C active with existing option position at 3 DTE
        WHEN: Orchestrator checks position DTE
        THEN: Force-close triggered at market price
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_strategy_c_emergency_stop_at_40pct(self, valid_strategy_c_gameplan):
        """
        GIVEN: Existing position losing > 40% of premium
        WHEN: Orchestrator monitors position
        THEN: Emergency close regardless of strategy
        """


# =================================================================
# STRATEGY TRANSITIONS — Regime Changes
# =================================================================


class TestStrategyTransitions:
    """Tests for strategy changes based on VIX regime shifts."""

    def test_transition_normal_to_elevated(self):
        """
        GIVEN: VIX rises from 15 (normal) to 22 (elevated)
        WHEN: select_strategy called with new VIX
        THEN: Strategy transitions from A to B
        """
        result_normal = select_strategy(vix=15.0)
        assert result_normal["strategy"] == "A"

        result_elevated = select_strategy(vix=22.0)
        assert result_elevated["strategy"] == "B"

    def test_transition_elevated_to_crisis(self):
        """
        GIVEN: VIX rises from 22 (elevated) to 28 (crisis)
        WHEN: select_strategy called with new VIX
        THEN: Strategy transitions from B to C
        """
        result_elevated = select_strategy(vix=22.0)
        assert result_elevated["strategy"] == "B"

        result_crisis = select_strategy(vix=28.0)
        assert result_crisis["strategy"] == "C"

    def test_transition_normal_to_crisis_skips_b(self):
        """
        GIVEN: VIX spikes from 15 to 30 (skip elevated)
        WHEN: select_strategy called
        THEN: Goes directly to C (no intermediate B)
        """
        result = select_strategy(vix=30.0)
        assert result["strategy"] == "C"

    def test_two_pivots_locks_strategy_c(self):
        """
        GIVEN: 2 intraday pivots have occurred
        WHEN: select_strategy called even with normal VIX
        THEN: Strategy C locked — too many direction changes
        """
        result = select_strategy(vix=15.0, intraday_pivots=2)
        assert result["strategy"] == "C"

    def test_strategy_c_from_pivot_is_sticky(self):
        """
        GIVEN: Strategy C forced by pivot limit
        WHEN: select_strategy called again with more pivots
        THEN: Still C (pivots >= 2 always forces C)
        """
        result = select_strategy(vix=15.0, intraday_pivots=3)
        assert result["strategy"] == "C"

    def test_regime_boundaries_vix_17_99_is_normal(self):
        """
        GIVEN: VIX at 17.99 (just under elevated threshold)
        WHEN: detect_regime and select_strategy called
        THEN: normal regime, Strategy A
        """
        assert detect_regime(17.99) == "normal"
        result = select_strategy(vix=17.99)
        assert result["strategy"] == "A"

    def test_regime_boundaries_vix_18_is_elevated(self):
        """
        GIVEN: VIX at 18.0 (exactly at elevated threshold)
        WHEN: detect_regime and select_strategy called
        THEN: elevated regime, Strategy B
        """
        assert detect_regime(18.0) == "elevated"
        result = select_strategy(vix=18.0)
        assert result["strategy"] == "B"

    def test_regime_boundaries_vix_24_99_is_elevated(self):
        """
        GIVEN: VIX at 24.99 (just under crisis threshold)
        WHEN: detect_regime and select_strategy called
        THEN: elevated regime, Strategy B
        """
        assert detect_regime(24.99) == "elevated"
        result = select_strategy(vix=24.99)
        assert result["strategy"] == "B"

    def test_regime_boundaries_vix_25_is_crisis(self):
        """
        GIVEN: VIX at 25.0 (exactly at crisis threshold)
        WHEN: detect_regime and select_strategy called
        THEN: crisis regime, Strategy C
        """
        assert detect_regime(25.0) == "crisis"
        result = select_strategy(vix=25.0)
        assert result["strategy"] == "C"


# =================================================================
# EXIT PATH VALIDATION
# =================================================================


class TestExitPaths:
    """Tests for all exit path mechanics (require Phase 2 orchestrator)."""

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_take_profit_exit_calculates_correct_pnl(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Position at entry price, target hit
        WHEN: Take-profit triggers
        THEN: P&L = (exit - entry) * quantity * multiplier
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_stop_loss_exit_limits_damage(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Position open, price drops through stop
        WHEN: Stop-loss fires
        THEN: Loss <= max_risk_per_trade ($18)
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_time_stop_exit_at_market_price(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Position held beyond time-stop (90 min for A, 45 min for B)
        WHEN: Time-stop triggers
        THEN: Market order placed, position closed at current price
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_force_close_at_dte_threshold(self, valid_strategy_a_gameplan):
        """
        GIVEN: Position with DTE <= 3
        WHEN: DTE check runs
        THEN: Force-close at market price
        """


# =================================================================
# STATE PERSISTENCE — Within-Session Tracking
# =================================================================


class TestSessionStatePersistence:
    """Tests for state tracking across multiple cycles within a session."""

    def test_pdt_blocking_with_zero_remaining(
        self, gameplan_with_zero_pdt, trending_spy_market_data
    ):
        """
        GIVEN: Gameplan with pdt_trades_remaining=0
        WHEN: Strategy A evaluates and produces a BUY signal
        THEN: BUY is blocked by PDT limit
        """
        decisions = evaluate_signals(gameplan_with_zero_pdt, trending_spy_market_data)

        for d in decisions:
            # BUY actions should be blocked when PDT=0
            if d["signal_details"].get("signal") == "BUY":
                assert d["action"] == "NEUTRAL"
                assert d["signal_details"].get("pdt_blocked") is True

    def test_pdt_allows_trading_with_remaining(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Gameplan with pdt_trades_remaining=3
        WHEN: Strategy A evaluates and produces a BUY signal
        THEN: BUY is NOT blocked by PDT limit
        """
        decisions = evaluate_signals(valid_strategy_a_gameplan, trending_spy_market_data)

        buy_decisions = [d for d in decisions if d["action"] == "BUY"]
        assert len(buy_decisions) >= 1
        for d in buy_decisions:
            assert d["signal_details"].get("pdt_blocked") is not True

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_pdt_count_increments_across_trades(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: PDT limit = 3, start of day
        WHEN: 3 round-trip trades executed
        THEN: PDT count = 3, 4th trade blocked
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_daily_loss_accumulates_across_trades(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Multiple losing trades in a day
        WHEN: Cumulative loss approaches $60
        THEN: Daily limit tracked accurately
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_daily_loss_limit_halts_all_trading(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Cumulative daily loss reaches $60 (10% of $600)
        WHEN: Circuit breaker fires
        THEN: All new trades blocked, existing positions managed
        """

    @pytest.mark.skip(reason=ORCHESTRATOR_SKIP)
    def test_pivot_count_persists_within_session(self, valid_strategy_a_gameplan):
        """
        GIVEN: Strategy transition A->B (pivot 1)
        WHEN: Second transition B->A (pivot 2)
        THEN: Pivot count = 2, Strategy C locked
        """
