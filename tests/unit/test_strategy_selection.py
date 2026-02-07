"""
Unit tests for VIX-based strategy selection and regime detection.

Tests cover:
- VIX regime detection boundaries: complacency (<15), normal (15-18), elevated (18-25), high (25-30), crisis (>30)
- Strategy selection logic for each regime
- Catalyst-based strategy overrides (FOMC, CPI, earnings)
- Position size multiplier adjustments by regime
- Gameplan validation and configuration loading
- Missing data defaults to Strategy C

Coverage Target: ≥85% of src/strategy/selection.py
"""

import pytest

# =============================================================================
# VIX REGIME FIXTURES
# =============================================================================


@pytest.fixture
def vix_complacency():
    """VIX < 15 — complacency regime."""
    return 12.5


@pytest.fixture
def vix_normal_low():
    """VIX at 15.0 — lower boundary of normal regime."""
    return 15.0


@pytest.fixture
def vix_normal_mid():
    """VIX at 16.5 — typical normal regime."""
    return 16.5


@pytest.fixture
def vix_normal_high():
    """VIX at 17.99 — upper boundary of normal regime."""
    return 17.99


@pytest.fixture
def vix_elevated_boundary():
    """VIX at 18.0 — lower boundary of elevated regime."""
    return 18.0


@pytest.fixture
def vix_elevated_mid():
    """VIX at 22.0 — typical elevated regime."""
    return 22.0


@pytest.fixture
def vix_elevated_high():
    """VIX at 24.99 — upper boundary of elevated regime."""
    return 24.99


@pytest.fixture
def vix_high_boundary():
    """VIX at 25.0 — lower boundary of high volatility / crisis regime."""
    return 25.0


@pytest.fixture
def vix_crisis():
    """VIX at 35.0 — full crisis conditions."""
    return 35.0


@pytest.fixture
def vix_extreme():
    """VIX at 55.0 — panic/extreme conditions."""
    return 55.0


# =============================================================================
# CATALYST FIXTURES
# =============================================================================


@pytest.fixture
def fomc_catalyst():
    """FOMC decision catalyst."""
    return [{"type": "FOMC", "description": "FOMC decision 2:00 PM ET", "impact": "high"}]


@pytest.fixture
def cpi_catalyst():
    """CPI data release catalyst."""
    return [{"type": "CPI", "description": "CPI release 8:30 AM ET", "impact": "high"}]


@pytest.fixture
def earnings_catalyst():
    """Earnings report catalyst — triggers blackout."""
    return [
        {
            "type": "EARNINGS",
            "symbol": "SPY",
            "description": "SPY component earnings",
            "impact": "high",
        }
    ]


@pytest.fixture
def low_impact_catalyst():
    """Low-impact catalyst — should not override strategy."""
    return [
        {
            "type": "ECONOMIC",
            "description": "Existing Home Sales 10:00 AM ET",
            "impact": "low",
        }
    ]


@pytest.fixture
def no_catalysts():
    """No catalysts scheduled."""
    return []


@pytest.fixture
def multiple_catalysts():
    """Multiple high-impact catalysts — maximum caution."""
    return [
        {"type": "FOMC", "description": "FOMC decision 2:00 PM ET", "impact": "high"},
        {"type": "CPI", "description": "CPI release 8:30 AM ET", "impact": "high"},
    ]


# =============================================================================
# VIX REGIME DETECTION TESTS
# =============================================================================


class TestVIXRegimeDetection:
    """Tests for VIX-to-regime mapping with exact boundary conditions."""

    def test_complacency_regime(self, vix_complacency):
        """VIX < 15 → complacency regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_complacency) == "complacency"

    def test_normal_regime_lower_boundary(self, vix_normal_low):
        """VIX == 15.0 → normal regime (inclusive lower bound)."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_normal_low) == "normal"

    def test_normal_regime_typical(self, vix_normal_mid):
        """VIX 16.5 → normal regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_normal_mid) == "normal"

    def test_normal_regime_upper_boundary(self, vix_normal_high):
        """VIX 17.99 → still normal regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_normal_high) == "normal"

    def test_elevated_regime_lower_boundary(self, vix_elevated_boundary):
        """VIX == 18.0 → elevated regime (inclusive lower bound)."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_elevated_boundary) == "elevated"

    def test_elevated_regime_typical(self, vix_elevated_mid):
        """VIX 22.0 → elevated regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_elevated_mid) == "elevated"

    def test_elevated_regime_upper_boundary(self, vix_elevated_high):
        """VIX 24.99 → still elevated regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_elevated_high) == "elevated"

    def test_high_volatility_boundary(self, vix_high_boundary):
        """VIX == 25.0 → high_volatility / crisis regime → Strategy C territory."""
        from src.strategy.selection import detect_regime

        regime = detect_regime(vix_high_boundary)
        assert regime in ("high_volatility", "crisis")

    def test_crisis_regime(self, vix_crisis):
        """VIX 35.0 → crisis regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_crisis) == "crisis"

    def test_extreme_vix_crisis(self, vix_extreme):
        """VIX 55.0 → still crisis (no regime above crisis)."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_extreme) == "crisis"

    def test_zero_vix_handled(self):
        """VIX == 0 → edge case, should not crash. Complacency or error."""
        from src.strategy.selection import detect_regime

        result = detect_regime(0.0)
        assert result in ("complacency", "error")

    def test_negative_vix_handled(self):
        """VIX < 0 → invalid, should not crash."""
        from src.strategy.selection import detect_regime

        result = detect_regime(-5.0)
        assert result in ("error", "crisis")  # Either error flag or safe default

    def test_none_vix_defaults_to_crisis(self):
        """
        CRITICAL: If VIX is None (data failure), default to crisis → Strategy C.
        This is a safety-critical path — fail safe, not fail open.
        """
        from src.strategy.selection import detect_regime

        result = detect_regime(None)
        assert result == "crisis"


# =============================================================================
# STRATEGY SELECTION TESTS
# =============================================================================


class TestStrategySelection:
    """Tests for regime → strategy mapping."""

    def test_normal_regime_selects_strategy_a(self, vix_normal_mid, no_catalysts):
        """VIX 16.5, no catalysts → Strategy A (Momentum Breakout)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        assert result["strategy"] == "A"
        assert result["regime"] == "normal"

    def test_complacency_regime_selects_strategy_a(self, vix_complacency, no_catalysts):
        """VIX < 15, no catalysts → Strategy A (low vol trending)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_complacency, catalysts=no_catalysts)

        assert result["strategy"] == "A"

    def test_elevated_regime_selects_strategy_b(self, vix_elevated_mid, no_catalysts):
        """VIX 22.0, no catalysts → Strategy B (Mean Reversion)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_elevated_mid, catalysts=no_catalysts)

        assert result["strategy"] == "B"
        assert result["regime"] == "elevated"

    def test_high_vix_selects_strategy_c(self, vix_high_boundary, no_catalysts):
        """VIX >= 25 → Strategy C (Cash Preservation). No exceptions."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_high_boundary, catalysts=no_catalysts)

        assert result["strategy"] == "C"

    def test_crisis_vix_selects_strategy_c(self, vix_crisis, no_catalysts):
        """VIX 35.0 → Strategy C."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_crisis, catalysts=no_catalysts)

        assert result["strategy"] == "C"

    def test_none_vix_selects_strategy_c(self, no_catalysts):
        """
        CRITICAL SAFETY: VIX=None (data failure) → Strategy C.
        Fail safe, not fail open.
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(None, catalysts=no_catalysts)

        assert result["strategy"] == "C"


# =============================================================================
# CATALYST OVERRIDE TESTS
# =============================================================================


class TestCatalystOverrides:
    """Tests for catalyst-driven strategy modifications."""

    def test_fomc_reduces_position_size(self, vix_normal_mid, fomc_catalyst):
        """
        GIVEN: Normal VIX (Strategy A conditions)
        AND: FOMC catalyst active
        WHEN: Strategy is selected
        THEN: Position size multiplier is reduced (≤0.5)
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=fomc_catalyst)

        assert result["position_size_multiplier"] <= 0.5

    def test_cpi_reduces_position_size(self, vix_normal_mid, cpi_catalyst):
        """
        GIVEN: Normal VIX + CPI release
        WHEN: Strategy is selected
        THEN: Position size multiplier is reduced
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=cpi_catalyst)

        assert result["position_size_multiplier"] <= 0.5

    def test_earnings_blackout_forces_strategy_c(self, vix_normal_mid, earnings_catalyst):
        """
        CRITICAL: Earnings within 24 hours → Strategy C. No exceptions.
        This is a hard rule from the Crucible doctrine.
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=earnings_catalyst)

        assert result["strategy"] == "C"
        assert (
            "earnings_blackout" in result.get("reasons", [])
            or result.get("earnings_blackout") is True
        )

    def test_low_impact_catalyst_no_override(self, vix_normal_mid, low_impact_catalyst):
        """
        GIVEN: Normal VIX + low-impact catalyst
        WHEN: Strategy is selected
        THEN: Strategy A remains, position size not reduced
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=low_impact_catalyst)

        assert result["strategy"] == "A"
        assert result["position_size_multiplier"] >= 0.8

    def test_multiple_high_impact_catalysts_force_strategy_c(
        self, vix_normal_mid, multiple_catalysts
    ):
        """
        GIVEN: Normal VIX but 2+ high-impact catalysts
        WHEN: Strategy is selected
        THEN: Strategy C deployed (too much event risk)
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=multiple_catalysts)

        # With 2+ high-impact catalysts, either Strategy C or very reduced sizing
        assert result["strategy"] == "C" or result["position_size_multiplier"] <= 0.3

    def test_no_catalysts_full_position_size(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX, no catalysts
        WHEN: Strategy is selected
        THEN: Full position size multiplier (1.0)
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        assert result["position_size_multiplier"] == 1.0


# =============================================================================
# POSITION SIZE MULTIPLIER TESTS
# =============================================================================


class TestPositionSizeMultiplier:
    """Tests for position size scaling by regime and conditions."""

    def test_normal_regime_full_size(self, vix_normal_mid, no_catalysts):
        """Normal regime → multiplier 1.0."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)
        assert result["position_size_multiplier"] == 1.0

    def test_elevated_regime_reduced_size(self, vix_elevated_mid, no_catalysts):
        """Elevated regime → multiplier 0.5 (Strategy B uses half size)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_elevated_mid, catalysts=no_catalysts)
        assert result["position_size_multiplier"] == 0.5

    def test_crisis_regime_zero_size(self, vix_crisis, no_catalysts):
        """Crisis regime → multiplier 0.0 (no new positions)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_crisis, catalysts=no_catalysts)
        assert result["position_size_multiplier"] == 0.0

    def test_complacency_regime_size(self, vix_complacency, no_catalysts):
        """Complacency regime → multiplier 1.0 (same as normal for Strategy A)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_complacency, catalysts=no_catalysts)
        assert result["position_size_multiplier"] == 1.0


# =============================================================================
# STRATEGY PARAMETER VALIDATION TESTS
# =============================================================================


class TestStrategyParameters:
    """Tests that selected strategy returns correct parameter set."""

    def test_strategy_a_returns_correct_symbols(self, vix_normal_mid, no_catalysts):
        """Strategy A: SPY, QQQ (max 2 symbols)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        assert set(result["symbols"]).issubset({"SPY", "QQQ"})
        assert len(result["symbols"]) <= 2

    def test_strategy_b_returns_spy_only(self, vix_elevated_mid, no_catalysts):
        """Strategy B: SPY only."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_elevated_mid, catalysts=no_catalysts)

        assert result["symbols"] == ["SPY"]

    def test_strategy_c_returns_no_symbols(self, vix_crisis, no_catalysts):
        """Strategy C: No symbols (no new entries)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_crisis, catalysts=no_catalysts)

        assert result["symbols"] == []

    def test_strategy_a_risk_parameters(self, vix_normal_mid, no_catalysts):
        """Strategy A: max_risk=3%, max_position=20%, tp=15%, sl=25%."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        params = result.get("parameters", result)
        assert params.get("max_risk_pct") == 0.03 or params.get("max_risk_pct") == 3.0
        assert params.get("take_profit_pct") == 0.15 or params.get("take_profit_pct") == 15.0
        assert params.get("stop_loss_pct") == 0.25 or params.get("stop_loss_pct") == 25.0
        assert params.get("time_stop_minutes") == 90

    def test_strategy_b_risk_parameters(self, vix_elevated_mid, no_catalysts):
        """Strategy B: max_risk=2%, max_position=10%, tp=8%, sl=15%."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_elevated_mid, catalysts=no_catalysts)

        params = result.get("parameters", result)
        assert params.get("max_risk_pct") == 0.02 or params.get("max_risk_pct") == 2.0
        assert params.get("take_profit_pct") == 0.08 or params.get("take_profit_pct") == 8.0
        assert params.get("stop_loss_pct") == 0.15 or params.get("stop_loss_pct") == 15.0
        assert params.get("time_stop_minutes") == 45

    def test_strategy_c_zero_risk_parameters(self, vix_crisis, no_catalysts):
        """Strategy C: max_risk=0%, no new positions."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_crisis, catalysts=no_catalysts)

        params = result.get("parameters", result)
        assert params.get("max_risk_pct") == 0.0 or params.get("max_risk_pct") == 0


# =============================================================================
# EXTERNAL OVERRIDE TESTS (Data Quarantine, Drawdown Governor, PDT)
# =============================================================================


class TestExternalOverrides:
    """Tests for conditions that force Strategy C regardless of VIX."""

    def test_data_quarantine_forces_strategy_c(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX conditions
        AND: Data quarantine flag is active
        WHEN: Strategy is selected
        THEN: Strategy C (data can't be trusted)
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(
            vix_normal_mid,
            catalysts=no_catalysts,
            data_quarantine=True,
        )

        assert result["strategy"] == "C"

    def test_drawdown_governor_forces_strategy_c(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX conditions
        AND: Weekly drawdown governor is active (>15% weekly loss)
        WHEN: Strategy is selected
        THEN: Strategy C for remainder of week
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(
            vix_normal_mid,
            catalysts=no_catalysts,
            weekly_governor_active=True,
        )

        assert result["strategy"] == "C"

    def test_pivot_limit_forces_strategy_c(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX conditions
        AND: 2+ intraday pivots already used
        WHEN: Strategy is selected
        THEN: Strategy C locked for the day
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(
            vix_normal_mid,
            catalysts=no_catalysts,
            intraday_pivots=2,
        )

        assert result["strategy"] == "C"

    def test_no_overrides_allows_normal_selection(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX, no overrides
        WHEN: Strategy is selected with all override flags False/0
        THEN: Normal strategy selection applies
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(
            vix_normal_mid,
            catalysts=no_catalysts,
            data_quarantine=False,
            weekly_governor_active=False,
            intraday_pivots=0,
        )

        assert result["strategy"] == "A"
