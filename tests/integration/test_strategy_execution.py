"""
Integration tests for strategy signal → execution flow.

Tests the full pipeline:
  Gameplan JSON → Strategy Selection → Signal Evaluation → Trade Decision

Tests cover:
- Gameplan ingestion and strategy activation
- Signal evaluation with real-ish market data fixtures
- Strategy transition scenarios (A→C on VIX spike, A→B on regime change)
- Multi-symbol signal evaluation (SPY + QQQ)
- Full decision pipeline with all safety checks
- Strategy C default on malformed/missing gameplan

Coverage Target: Component of ≥85% aggregate for src/strategy/
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# =============================================================================
# GAMEPLAN FIXTURES
# =============================================================================


@pytest.fixture
def strategy_a_gameplan() -> Dict[str, Any]:
    """Full Strategy A gameplan matching daily_gameplan.json schema."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0900",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY", "QQQ"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 16.5,
        "vix_source_verified": True,
        "bias": "bullish",
        "expected_behavior": "trending",
        "key_levels": {
            "spy_support": 685.50,
            "spy_resistance": 696.09,
            "spy_pivot": 690.00,
        },
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "low",
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:00:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 3,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2,
        },
    }


@pytest.fixture
def strategy_b_gameplan() -> Dict[str, Any]:
    """Full Strategy B gameplan."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0900",
        "regime": "elevated",
        "strategy": "B",
        "symbols": ["SPY"],
        "position_size_multiplier": 0.5,
        "vix_at_analysis": 23.5,
        "vix_source_verified": True,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "key_levels": {
            "spy_support": 680.00,
            "spy_resistance": 690.00,
            "spy_pivot": 685.00,
        },
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "medium",
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:00:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 2,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2,
        },
    }


@pytest.fixture
def strategy_c_gameplan() -> Dict[str, Any]:
    """Full Strategy C gameplan (cash preservation)."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0900",
        "regime": "crisis",
        "strategy": "C",
        "symbols": [],
        "position_size_multiplier": 0.0,
        "vix_at_analysis": 31.0,
        "vix_source_verified": True,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "high",
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:00:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 0,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": True,
            "max_intraday_pivots": 2,
        },
    }


@pytest.fixture
def malformed_gameplan() -> Dict[str, Any]:
    """Gameplan missing critical fields — must trigger Strategy C fallback."""
    return {
        "date": "2026-02-07",
        "strategy": "A",
        # Missing: regime, symbols, hard_limits, data_quality
    }


@pytest.fixture
def trending_market_data() -> Dict[str, List[Dict[str, Any]]]:
    """Market data suitable for Strategy A — trending conditions."""
    base_time = datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
    spy_bars = []
    qqq_bars = []

    for i in range(30):
        spy_bars.append(
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "open": 688.00 + (i * 0.15),
                "high": 688.50 + (i * 0.15),
                "low": 687.50 + (i * 0.15),
                "close": 688.20 + (i * 0.15),
                "volume": 900000 + (i * 10000),
                "vwap": 687.80 + (i * 0.12),
            }
        )
        qqq_bars.append(
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "open": 620.00 + (i * 0.12),
                "high": 620.40 + (i * 0.12),
                "low": 619.60 + (i * 0.12),
                "close": 620.15 + (i * 0.12),
                "volume": 600000 + (i * 8000),
                "vwap": 619.80 + (i * 0.10),
            }
        )

    return {"SPY": spy_bars, "QQQ": qqq_bars}


@pytest.fixture
def mean_reverting_market_data() -> Dict[str, List[Dict[str, Any]]]:
    """Market data suitable for Strategy B — mean reverting conditions."""
    base_time = datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
    spy_bars = []
    base_price = 685.00

    for i in range(30):
        if i < 20:
            price = base_price - (i * 0.35)  # Sharp decline
        else:
            price = base_price - (20 * 0.35) + ((i - 20) * 0.05)  # Stabilizing
        spy_bars.append(
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "open": price + 0.10,
                "high": price + 0.25,
                "low": price - 0.30,
                "close": price,
                "volume": 1100000 + (i * 15000),
                "vwap": price + 1.20,
            }
        )

    return {"SPY": spy_bars}


# =============================================================================
# GAMEPLAN VALIDATION TESTS
# =============================================================================


class TestGameplanValidation:
    """Tests for gameplan JSON parsing and validation."""

    def test_valid_gameplan_a_loads_correctly(self, strategy_a_gameplan):
        """Valid Strategy A gameplan parses without error."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan(strategy_a_gameplan)

        assert result["valid"] is True
        assert result["strategy"] == "A"
        assert result["regime"] == "normal"

    def test_valid_gameplan_b_loads_correctly(self, strategy_b_gameplan):
        """Valid Strategy B gameplan parses without error."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan(strategy_b_gameplan)

        assert result["valid"] is True
        assert result["strategy"] == "B"

    def test_valid_gameplan_c_loads_correctly(self, strategy_c_gameplan):
        """Valid Strategy C gameplan parses without error."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan(strategy_c_gameplan)

        assert result["valid"] is True
        assert result["strategy"] == "C"

    def test_malformed_gameplan_defaults_to_strategy_c(self, malformed_gameplan):
        """
        CRITICAL SAFETY: Malformed gameplan → Strategy C.
        Never trade with invalid configuration.
        """
        from src.strategy.execution import load_gameplan

        result = load_gameplan(malformed_gameplan)

        assert result["strategy"] == "C"
        assert result.get("validation_errors") is not None

    def test_none_gameplan_defaults_to_strategy_c(self):
        """None gameplan → Strategy C."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan(None)

        assert result["strategy"] == "C"

    def test_empty_dict_gameplan_defaults_to_strategy_c(self):
        """Empty dict gameplan → Strategy C."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan({})

        assert result["strategy"] == "C"

    def test_gameplan_with_quarantine_active_forces_c(self, strategy_a_gameplan):
        """Gameplan where data_quality.quarantine_active=True → Strategy C."""
        from src.strategy.execution import load_gameplan

        strategy_a_gameplan["data_quality"]["quarantine_active"] = True
        result = load_gameplan(strategy_a_gameplan)

        assert result["strategy"] == "C"


# =============================================================================
# STRATEGY EXECUTION PIPELINE TESTS
# =============================================================================


class TestStrategyExecutionPipeline:
    """Integration tests for the full signal → decision pipeline."""

    def test_strategy_a_pipeline_with_trending_data(
        self, strategy_a_gameplan, trending_market_data
    ):
        """
        GIVEN: Strategy A gameplan + trending market data
        WHEN: Full pipeline executes
        THEN: Produces actionable trade decision for SPY and/or QQQ
        """
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_a_gameplan, trending_market_data)

        assert isinstance(decisions, list)
        assert len(decisions) >= 1
        for decision in decisions:
            assert decision["symbol"] in ("SPY", "QQQ")
            assert decision["action"] in ("BUY", "SELL", "HOLD", "NEUTRAL")
            assert "confidence" in decision

    def test_strategy_b_pipeline_with_mean_reverting_data(
        self, strategy_b_gameplan, mean_reverting_market_data
    ):
        """
        GIVEN: Strategy B gameplan + oversold market data
        WHEN: Full pipeline executes
        THEN: Produces mean reversion trade decision for SPY
        """
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_b_gameplan, mean_reverting_market_data)

        assert isinstance(decisions, list)
        assert len(decisions) == 1
        assert decisions[0]["symbol"] == "SPY"

    def test_strategy_c_produces_no_trade_decisions(
        self, strategy_c_gameplan, trending_market_data
    ):
        """
        GIVEN: Strategy C gameplan
        WHEN: Pipeline executes
        THEN: No trade decisions produced (alert-only mode)
        """
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_c_gameplan, trending_market_data)

        # Strategy C = no new trades
        for decision in decisions:
            assert decision["action"] in ("HOLD", "CLOSE", "NEUTRAL")

    def test_pipeline_with_no_market_data_defaults_safe(self, strategy_a_gameplan):
        """
        GIVEN: Strategy A gameplan but no market data available
        WHEN: Pipeline executes
        THEN: No trades (can't generate signals without data)
        """
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_a_gameplan, {})

        for decision in decisions:
            assert decision["action"] in ("HOLD", "NEUTRAL")

    def test_pipeline_respects_pdt_remaining(self, strategy_a_gameplan, trending_market_data):
        """
        GIVEN: Strategy A gameplan with pdt_trades_remaining=0
        WHEN: Pipeline executes
        THEN: No new entry decisions (PDT exhausted)
        """
        from src.strategy.execution import evaluate_signals

        strategy_a_gameplan["hard_limits"]["pdt_trades_remaining"] = 0
        decisions = evaluate_signals(strategy_a_gameplan, trending_market_data)

        for decision in decisions:
            assert (
                decision["action"] != "BUY"
            ), "Cannot open new positions with 0 PDT trades remaining"


# =============================================================================
# STRATEGY TRANSITION TESTS
# =============================================================================


class TestStrategyTransitions:
    """Tests for mid-session strategy changes based on regime shifts."""

    def test_vix_spike_transitions_a_to_c(self):
        """
        GIVEN: Currently running Strategy A
        WHEN: VIX spikes above 25 (regime shift to crisis)
        THEN: Strategy transitions to C
        """
        from src.strategy.selection import select_strategy

        # Before spike: Strategy A
        before = select_strategy(16.5, catalysts=[])
        assert before["strategy"] == "A"

        # After spike: Strategy C
        after = select_strategy(26.0, catalysts=[])
        assert after["strategy"] == "C"

    def test_vix_rise_transitions_a_to_b(self):
        """
        GIVEN: Currently running Strategy A (VIX 16.5)
        WHEN: VIX rises to elevated (22.0)
        THEN: Strategy transitions to B
        """
        from src.strategy.selection import select_strategy

        before = select_strategy(16.5, catalysts=[])
        assert before["strategy"] == "A"

        after = select_strategy(22.0, catalysts=[])
        assert after["strategy"] == "B"

    def test_vix_drop_transitions_b_to_a(self):
        """
        GIVEN: Currently running Strategy B (VIX 22.0)
        WHEN: VIX drops to normal (16.0)
        THEN: Strategy transitions to A
        """
        from src.strategy.selection import select_strategy

        before = select_strategy(22.0, catalysts=[])
        assert before["strategy"] == "B"

        after = select_strategy(16.0, catalysts=[])
        assert after["strategy"] == "A"

    def test_strategy_c_never_transitions_up_within_session(self):
        """
        DESIGN NOTE: Once Strategy C is locked for the session
        (via governor, data quarantine, or pivot limit), it should
        remain locked. VIX improvement alone shouldn't unlock it.

        This test validates the concept — the actual enforcement
        is in the execution engine's session state.
        """
        from src.strategy.selection import select_strategy

        # Strategy C due to governor
        locked = select_strategy(16.5, catalysts=[], weekly_governor_active=True)
        assert locked["strategy"] == "C"

        # Even with great VIX, governor keeps it locked
        still_locked = select_strategy(12.0, catalysts=[], weekly_governor_active=True)
        assert still_locked["strategy"] == "C"


# =============================================================================
# OUTPUT CONTRACT VALIDATION TESTS
# =============================================================================


class TestOutputContracts:
    """Tests that strategy layer outputs match expected data contracts."""

    def test_strategy_selection_output_schema(self):
        """Strategy selection output has all required fields."""
        from src.strategy.selection import select_strategy

        result = select_strategy(16.5, catalysts=[])

        required_fields = ["strategy", "regime", "symbols", "position_size_multiplier"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_signal_evaluation_output_schema(self, strategy_a_gameplan, trending_market_data):
        """Signal evaluation output has all required fields per decision."""
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_a_gameplan, trending_market_data)

        for decision in decisions:
            assert "symbol" in decision
            assert "action" in decision
            assert "confidence" in decision
            assert isinstance(decision["confidence"], (int, float))
            assert 0.0 <= decision["confidence"] <= 1.0
