"""
E2E test fixtures — composite fixtures wiring all layers together.

These fixtures provide:
- Complete gameplan dicts (Strategy A, B, C, malformed variants)
- Realistic bar data arrays (trending, oversold, flat, stale)
- Market data dicts mapping symbol → bars for evaluate_signals()
- Safety-scenario gameplans (quarantine, governor, PDT, blackout)

Design principle: Only the IBKR Gateway is mocked. All internal
components use real implementations to maximize integration confidence.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

# =============================================================================
# BAR DATA HELPERS
# =============================================================================


def _make_ascending_bars(
    count: int = 30, start: float = 580.0, step: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Create ascending price bars for bullish momentum (Strategy A).

    Produces bars where:
    - EMA(8) > EMA(21) → BULLISH crossover
    - RSI = 65 (all positive deltas, boundary of 50-65 range)
    - VWAP below close → VWAP confirmation
    """
    bars: List[Dict[str, Any]] = []
    for i in range(count):
        close = start + i * step
        bars.append(
            {
                "close": round(close, 2),
                "open": round(close - 0.10, 2),
                "high": round(close + 0.30, 2),
                "low": round(close - 0.30, 2),
                "volume": 1_000_000,
                "vwap": round(close - 0.50, 2),
            }
        )
    return bars


def _make_descending_bars(
    count: int = 30, start: float = 595.0, step: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Create descending price bars for mean-reversion entry (Strategy B).

    Produces bars where:
    - RSI = 5.0 (all negative deltas → oversold)
    - Price near/below lower Bollinger band
    """
    bars: List[Dict[str, Any]] = []
    for i in range(count):
        close = start - i * step
        bars.append(
            {
                "close": round(close, 2),
                "open": round(close + 0.10, 2),
                "high": round(close + 0.30, 2),
                "low": round(close - 0.30, 2),
                "volume": 1_500_000,
            }
        )
    return bars


def _make_flat_bars(count: int = 30, price: float = 590.0) -> List[Dict[str, Any]]:
    """
    Create flat price bars — no signal should be generated.

    Produces bars where:
    - EMA crossover: NEUTRAL
    - RSI: 50.0
    - VWAP above price → no confirmation
    """
    bars: List[Dict[str, Any]] = []
    for _ in range(count):
        bars.append(
            {
                "close": price,
                "open": price,
                "high": round(price + 0.20, 2),
                "low": round(price - 0.20, 2),
                "volume": 800_000,
                "vwap": round(price + 0.50, 2),  # Above close → no VWAP confirm
            }
        )
    return bars


# =============================================================================
# GAMEPLAN FIXTURES
# =============================================================================


@pytest.fixture
def valid_strategy_a_gameplan() -> Dict[str, Any]:
    """
    Complete, valid Strategy A gameplan matching daily_gameplan.json schema.
    All fields populated with realistic values for a normal VIX regime.
    """
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        "operator_id": "CSATSPRIM",
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "bias": "bullish",
        "expected_behavior": "trending",
        "key_levels": {
            "spy_support": 585.50,
            "spy_resistance": 598.00,
            "spy_pivot": 591.00,
            "qqq_support": 518.00,
            "qqq_resistance": 528.00,
            "qqq_pivot": 522.00,
        },
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "low",
        "alert_message": "Strategy A — SPY momentum, normal regime",
        "data_quality": {
            "quarantine_active": False,
            "discrepancy_count": 0,
            "last_verified": "2026-02-07T09:10:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
            "weekly_drawdown_governor_active": False,
            "pdt_trades_remaining": 3,
            "max_intraday_pivots": 2,
        },
        "scorecard": {
            "yesterday_pnl": 0.0,
            "streak": 0,
            "weekly_cumulative_pnl": 0.0,
        },
    }


@pytest.fixture
def valid_strategy_b_gameplan() -> Dict[str, Any]:
    """Complete, valid Strategy B gameplan for elevated VIX regime."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "elevated",
        "strategy": "B",
        "symbols": ["SPY"],
        "operator_id": "CSATSPRIM",
        "position_size_multiplier": 0.5,
        "vix_at_analysis": 22.0,
        "vix_source_verified": True,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "key_levels": {
            "spy_support": 575.00,
            "spy_resistance": 588.00,
            "spy_pivot": 581.00,
            "qqq_support": 510.00,
            "qqq_resistance": 522.00,
            "qqq_pivot": 517.00,
        },
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "medium",
        "alert_message": "Strategy B — SPY mean reversion, elevated regime",
        "data_quality": {
            "quarantine_active": False,
            "discrepancy_count": 0,
            "last_verified": "2026-02-07T09:10:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
            "weekly_drawdown_governor_active": False,
            "pdt_trades_remaining": 3,
            "max_intraday_pivots": 2,
        },
        "scorecard": {
            "yesterday_pnl": -12.50,
            "streak": -1,
            "weekly_cumulative_pnl": -12.50,
        },
    }


@pytest.fixture
def valid_strategy_c_gameplan() -> Dict[str, Any]:
    """Strategy C gameplan — cash preservation / no-trade mode."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "crisis",
        "strategy": "C",
        "symbols": [],
        "operator_id": "CSATSPRIM",
        "position_size_multiplier": 0.0,
        "vix_at_analysis": 28.5,
        "vix_source_verified": True,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "key_levels": {
            "spy_support": 560.00,
            "spy_resistance": 580.00,
            "spy_pivot": 570.00,
            "qqq_support": 495.00,
            "qqq_resistance": 510.00,
            "qqq_pivot": 500.00,
        },
        "catalysts": ["VIX > 25 — crisis regime"],
        "earnings_blackout": [],
        "geo_risk": "high",
        "alert_message": "Strategy C LOCKED — crisis regime, cash preservation only",
        "data_quality": {
            "quarantine_active": False,
            "discrepancy_count": 0,
            "last_verified": "2026-02-07T09:10:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
            "weekly_drawdown_governor_active": False,
            "pdt_trades_remaining": 3,
            "max_intraday_pivots": 2,
        },
        "scorecard": {
            "yesterday_pnl": -45.00,
            "streak": -3,
            "weekly_cumulative_pnl": -72.00,
        },
    }


# =============================================================================
# MALFORMED GAMEPLAN FIXTURES
# =============================================================================


@pytest.fixture
def malformed_gameplan_missing_strategy() -> Dict[str, Any]:
    """Gameplan with 'strategy' field missing entirely."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        # "strategy" key intentionally missing
        "symbols": ["SPY"],
        "data_quality": {"quarantine_active": False},
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "pdt_trades_remaining": 2,
        },
    }


@pytest.fixture
def malformed_gameplan_invalid_strategy() -> Dict[str, Any]:
    """Gameplan with invalid strategy value."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "D",  # Invalid — only A, B, C are valid
        "symbols": ["SPY"],
        "data_quality": {"quarantine_active": False},
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "pdt_trades_remaining": 2,
        },
    }


@pytest.fixture
def malformed_gameplan_missing_hard_limits() -> Dict[str, Any]:
    """Gameplan with hard_limits section missing entirely."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        "data_quality": {"quarantine_active": False},
        # "hard_limits" key intentionally missing
    }


# =============================================================================
# SAFETY-SCENARIO GAMEPLAN FIXTURES
# =============================================================================


@pytest.fixture
def gameplan_with_quarantine() -> Dict[str, Any]:
    """Gameplan where data_quality.quarantine_active is True."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "data_quality": {
            "quarantine_active": True,
            "discrepancy_count": 3,
            "last_verified": "2026-02-07T08:30:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
            "weekly_drawdown_governor_active": False,
            "pdt_trades_remaining": 3,
            "max_intraday_pivots": 2,
        },
    }


@pytest.fixture
def gameplan_with_weekly_governor() -> Dict[str, Any]:
    """Gameplan where weekly drawdown governor is active."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",  # Says A but governor should force C
        "symbols": ["SPY"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "data_quality": {
            "quarantine_active": False,
            "discrepancy_count": 0,
            "last_verified": "2026-02-07T09:10:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
            "weekly_drawdown_governor_active": True,
            "pdt_trades_remaining": 3,
            "max_intraday_pivots": 2,
        },
        "scorecard": {
            "yesterday_pnl": -50.00,
            "streak": -4,
            "weekly_cumulative_pnl": -95.00,
        },
    }


@pytest.fixture
def gameplan_with_zero_pdt() -> Dict[str, Any]:
    """Gameplan where all PDT trades are exhausted."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "data_quality": {
            "quarantine_active": False,
            "discrepancy_count": 0,
            "last_verified": "2026-02-07T09:10:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
            "weekly_drawdown_governor_active": False,
            "pdt_trades_remaining": 0,
            "max_intraday_pivots": 2,
        },
    }


@pytest.fixture
def gameplan_with_earnings_blackout() -> Dict[str, Any]:
    """Gameplan where SPY is in earnings blackout."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY", "QQQ"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "earnings_blackout": ["SPY"],  # SPY blacklisted
        "data_quality": {
            "quarantine_active": False,
            "discrepancy_count": 0,
            "last_verified": "2026-02-07T09:10:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
            "weekly_drawdown_governor_active": False,
            "pdt_trades_remaining": 3,
            "max_intraday_pivots": 2,
        },
    }


# =============================================================================
# BAR DATA FIXTURES
# =============================================================================


@pytest.fixture
def trending_spy_bars() -> List[Dict[str, Any]]:
    """
    30 ascending SPY bars for bullish momentum (Strategy A).
    Prices: 580.0 → 594.5, VWAP below close.
    Expected signals: EMA BULLISH, RSI 65, VWAP confirmed → BUY.
    """
    return _make_ascending_bars(count=30, start=580.0, step=0.5)


@pytest.fixture
def oversold_spy_bars() -> List[Dict[str, Any]]:
    """
    30 descending SPY bars for mean-reversion entry (Strategy B).
    Prices: 595.0 → 574.7, no VWAP field.
    Expected signals: RSI 5.0 (oversold) → BUY with low confidence.
    """
    return _make_descending_bars(count=30, start=595.0, step=0.7)


@pytest.fixture
def flat_spy_bars() -> List[Dict[str, Any]]:
    """
    30 flat SPY bars — no signal should be generated.
    All prices at 590.0, VWAP above close.
    Expected signals: NEUTRAL.
    """
    return _make_flat_bars(count=30, price=590.0)


@pytest.fixture
def stale_spy_bars() -> List[Dict[str, Any]]:
    """
    Bars with a stale timestamp (> 5 minutes old, < 1 day).
    Should trigger staleness check in strategy signal evaluation.
    """
    stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    bars = _make_ascending_bars(count=30, start=580.0, step=0.5)
    # Only set timestamp on the last bar (staleness checks last bar)
    bars[-1]["timestamp"] = stale_ts
    return bars


# =============================================================================
# MARKET DATA DICT FIXTURES (for evaluate_signals)
# =============================================================================


@pytest.fixture
def trending_spy_market_data(
    trending_spy_bars: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Market data dict with SPY trending bars, keyed by symbol."""
    return {"SPY": trending_spy_bars}


@pytest.fixture
def oversold_spy_market_data(
    oversold_spy_bars: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Market data dict with SPY oversold bars, keyed by symbol."""
    return {"SPY": oversold_spy_bars}


@pytest.fixture
def flat_spy_market_data(
    flat_spy_bars: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Market data dict with SPY flat bars, keyed by symbol."""
    return {"SPY": flat_spy_bars}


@pytest.fixture
def stale_spy_market_data(
    stale_spy_bars: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Market data dict with stale SPY bars, keyed by symbol."""
    return {"SPY": stale_spy_bars}
