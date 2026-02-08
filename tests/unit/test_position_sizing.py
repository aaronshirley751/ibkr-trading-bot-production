"""
Unit tests for position sizing and affordability checks.

Tests cover:
- Max position size enforcement (20% of capital = $120)
- Max risk per trade enforcement (3% of capital = $18)
- Contract affordability checks
- Position size multiplier application
- PDT compliance validation (3 trades / 5 rolling business days)
- Multi-position aggregate limit enforcement
- Edge cases: zero balance, minimum trade, exact boundaries

Coverage target: 98%
CRO MANDATE: Every boundary tested at [limit-ε, limit, limit+ε]

Threat model references: T-01, T-02, T-03, T-04, T-09, T-12
"""

import pytest
from datetime import date, timedelta
from typing import Any, Dict, List

# =============================================================================
# FIXTURES (Local to this module)
# =============================================================================


@pytest.fixture
def position_sizer():
    """
    Create a PositionSizer instance with default account parameters.

    The PositionSizer is the primary class under test. It enforces:
    - Max position size (20% of capital)
    - Max risk per trade (3% of capital)
    - PDT compliance
    - Contract affordability
    """
    from src.risk.position_sizer import PositionSizer

    return PositionSizer(
        account_balance=600.00,
        max_position_pct=0.20,
        max_risk_pct=0.03,
        pdt_limit=3,
    )


@pytest.fixture
def pdt_tracker():
    """
    Create a PDTTracker instance for day trade compliance testing.
    """
    from src.risk.pdt_tracker import PDTTracker

    return PDTTracker(trade_limit=3, window_days=5)


@pytest.fixture
def sample_option_contract():
    """Standard SPY call option for testing."""
    return {
        "symbol": "SPY",
        "secType": "OPT",
        "right": "C",
        "strike": 590.0,
        "multiplier": 100,
        "premium": 3.50,  # $350 per contract
    }


@pytest.fixture
def cheap_option_contract():
    """Cheap option that fits within position limits."""
    return {
        "symbol": "SPY",
        "secType": "OPT",
        "right": "C",
        "strike": 600.0,
        "multiplier": 100,
        "premium": 0.85,  # $85 per contract
    }


@pytest.fixture
def expensive_option_contract():
    """Expensive option that exceeds position limits."""
    return {
        "symbol": "SPY",
        "secType": "OPT",
        "right": "C",
        "strike": 580.0,
        "multiplier": 100,
        "premium": 5.00,  # $500 per contract
    }


# =============================================================================
# MAX POSITION SIZE TESTS — CRO Boundary: $120 (20% of $600)
# Threat: T-01 (boundary arithmetic), T-02 (float drift)
# =============================================================================


class TestMaxPositionSize:
    """Tests for max position size enforcement ($120 = 20% of $600)."""

    def test_position_under_limit_passes(self, position_sizer):
        """Position at $119.99 should be allowed."""
        assert position_sizer.validate_position_size(119.99) is True

    def test_position_at_exact_limit_passes(self, position_sizer):
        """Position at exactly $120.00 should be allowed (boundary inclusive)."""
        assert position_sizer.validate_position_size(120.00) is True

    def test_position_over_limit_rejected(self, position_sizer):
        """Position at $120.01 should be rejected."""
        assert position_sizer.validate_position_size(120.01) is False

    def test_position_far_over_limit_rejected(self, position_sizer):
        """Position at $500 should be rejected."""
        assert position_sizer.validate_position_size(500.00) is False

    def test_position_zero_passes(self, position_sizer):
        """Zero-dollar position should pass (no risk)."""
        assert position_sizer.validate_position_size(0.00) is True

    def test_negative_position_rejected(self, position_sizer):
        """Negative position size should be rejected (invalid input)."""
        assert position_sizer.validate_position_size(-10.00) is False

    def test_position_size_scales_with_balance(self):
        """Position limit should scale with account balance."""
        from src.risk.position_sizer import PositionSizer

        sizer = PositionSizer(
            account_balance=1000.00,
            max_position_pct=0.20,
            max_risk_pct=0.03,
            pdt_limit=3,
        )
        # 20% of $1000 = $200
        assert sizer.validate_position_size(200.00) is True
        assert sizer.validate_position_size(200.01) is False

    def test_position_size_with_zero_balance(self):
        """Zero balance should reject all non-zero positions."""
        from src.risk.position_sizer import PositionSizer

        sizer = PositionSizer(
            account_balance=0.00,
            max_position_pct=0.20,
            max_risk_pct=0.03,
            pdt_limit=3,
        )
        assert sizer.validate_position_size(0.01) is False
        assert sizer.validate_position_size(0.00) is True

    def test_floating_point_boundary_precision(self, position_sizer):
        """
        Verify floating-point arithmetic doesn't create boundary errors.
        Threat T-02: IEEE 754 can make 0.1 + 0.2 != 0.3
        """
        # This tests that the implementation handles float comparison correctly
        # 120.00 should always be treated consistently
        result_at_limit = position_sizer.validate_position_size(120.00)
        result_penny_over = position_sizer.validate_position_size(120.00 + 0.01)
        assert result_at_limit is True
        assert result_penny_over is False


# =============================================================================
# MAX RISK PER TRADE TESTS — CRO Boundary: $18 (3% of $600)
# Threat: T-01, T-02
# =============================================================================


class TestMaxRiskPerTrade:
    """Tests for max risk per trade enforcement ($18 = 3% of $600)."""

    def test_risk_under_limit_passes(self, position_sizer):
        """Risk at $17.99 should be allowed."""
        assert position_sizer.validate_trade_risk(17.99) is True

    def test_risk_at_exact_limit_passes(self, position_sizer):
        """Risk at exactly $18.00 should be allowed (boundary inclusive)."""
        assert position_sizer.validate_trade_risk(18.00) is True

    def test_risk_over_limit_rejected(self, position_sizer):
        """Risk at $18.01 should be rejected."""
        assert position_sizer.validate_trade_risk(18.01) is False

    def test_risk_zero_passes(self, position_sizer):
        """Zero risk should pass."""
        assert position_sizer.validate_trade_risk(0.00) is True

    def test_negative_risk_rejected(self, position_sizer):
        """Negative risk should be rejected (invalid input)."""
        assert position_sizer.validate_trade_risk(-5.00) is False

    def test_risk_calculation_from_stop_loss(self, position_sizer):
        """
        Risk = (entry_price - stop_price) * multiplier * quantity.
        Verify the calculation produces correct risk amount.
        """
        # Entry at $3.50, stop at $2.625 (25% stop for Strategy A)
        # Risk = ($3.50 - $2.625) * 100 * 1 = $87.50
        risk = position_sizer.calculate_trade_risk(
            entry_price=3.50,
            stop_price=2.625,
            multiplier=100,
            quantity=1,
        )
        assert risk == pytest.approx(87.50, abs=0.01)

    def test_risk_calculation_strategy_a_stop(self, position_sizer):
        """Strategy A: 25% stop-loss on premium."""
        # Premium $1.00, stop at $0.75 (25% loss)
        # Risk = $0.25 * 100 * 1 = $25 — exceeds $18
        risk = position_sizer.calculate_trade_risk(
            entry_price=1.00,
            stop_price=0.75,
            multiplier=100,
            quantity=1,
        )
        assert risk == pytest.approx(25.00, abs=0.01)

    def test_risk_calculation_strategy_b_stop(self, position_sizer):
        """Strategy B: 15% stop-loss on premium."""
        # Premium $1.00, stop at $0.85 (15% loss)
        # Risk = $0.15 * 100 * 1 = $15 — under $18 limit
        risk = position_sizer.calculate_trade_risk(
            entry_price=1.00,
            stop_price=0.85,
            multiplier=100,
            quantity=1,
        )
        assert risk == pytest.approx(15.00, abs=0.01)


# =============================================================================
# CONTRACT AFFORDABILITY TESTS
# Threat: T-09 (stale balance)
# =============================================================================


class TestContractAffordability:
    """Tests for contract premium affordability within position limits."""

    def test_affordable_contract_passes(self, position_sizer, cheap_option_contract):
        """$85 contract fits within $120 limit."""
        result = position_sizer.check_affordability(cheap_option_contract)
        assert result["affordable"] is True
        assert result["max_contracts"] >= 1

    def test_expensive_contract_rejected(self, position_sizer, expensive_option_contract):
        """$500 contract exceeds $120 limit — zero contracts affordable."""
        result = position_sizer.check_affordability(expensive_option_contract)
        assert result["affordable"] is False
        assert result["max_contracts"] == 0

    def test_max_contracts_calculation(self, position_sizer, cheap_option_contract):
        """With $120 limit and $85 premium, max 1 contract (floor division)."""
        result = position_sizer.check_affordability(cheap_option_contract)
        assert result["max_contracts"] == 1  # floor(120 / 85) = 1

    def test_exact_fit_contract(self, position_sizer):
        """Contract premium exactly equals position limit."""
        contract = {
            "symbol": "SPY",
            "secType": "OPT",
            "right": "C",
            "strike": 595.0,
            "multiplier": 100,
            "premium": 1.20,  # $120 per contract = exactly at limit
        }
        result = position_sizer.check_affordability(contract)
        assert result["affordable"] is True
        assert result["max_contracts"] == 1

    def test_zero_premium_contract(self, position_sizer):
        """Zero premium should be rejected (suspicious data)."""
        contract = {
            "symbol": "SPY",
            "secType": "OPT",
            "right": "C",
            "strike": 700.0,
            "multiplier": 100,
            "premium": 0.00,
        }
        result = position_sizer.check_affordability(contract)
        assert result["affordable"] is False  # Zero premium = bad data

    def test_negative_premium_rejected(self, position_sizer):
        """Negative premium should be rejected (invalid data)."""
        contract = {
            "symbol": "SPY",
            "secType": "OPT",
            "right": "C",
            "strike": 700.0,
            "multiplier": 100,
            "premium": -1.00,
        }
        result = position_sizer.check_affordability(contract)
        assert result["affordable"] is False


# =============================================================================
# POSITION SIZE MULTIPLIER TESTS
# =============================================================================


class TestPositionSizeMultiplier:
    """Tests for position size multiplier from gameplan."""

    def test_full_multiplier(self, position_sizer):
        """Multiplier 1.0 = full position size ($120)."""
        effective = position_sizer.apply_multiplier(120.00, multiplier=1.0)
        assert effective == pytest.approx(120.00)

    def test_reduced_multiplier(self, position_sizer):
        """Multiplier 0.5 = half position size ($60)."""
        effective = position_sizer.apply_multiplier(120.00, multiplier=0.5)
        assert effective == pytest.approx(60.00)

    def test_zero_multiplier_blocks_trading(self, position_sizer):
        """Multiplier 0.0 = no trading allowed."""
        effective = position_sizer.apply_multiplier(120.00, multiplier=0.0)
        assert effective == pytest.approx(0.00)

    def test_multiplier_above_one_clamped(self, position_sizer):
        """Multiplier > 1.0 should be clamped to 1.0 (never exceed base limit)."""
        effective = position_sizer.apply_multiplier(120.00, multiplier=1.5)
        assert effective == pytest.approx(120.00)

    def test_negative_multiplier_rejected(self, position_sizer):
        """Negative multiplier should raise ValueError."""
        with pytest.raises(ValueError):
            position_sizer.apply_multiplier(120.00, multiplier=-0.5)


# =============================================================================
# PDT COMPLIANCE TESTS — CRO Boundary: 3 trades / 5 rolling business days
# Threat: T-03 (rolling window miscalculation)
# =============================================================================


class TestPDTCompliance:
    """Tests for Pattern Day Trader rule compliance."""

    def test_zero_trades_allows_entry(self, pdt_tracker):
        """No trades used = entry allowed."""
        assert pdt_tracker.can_open_day_trade(trades_in_window=[]) is True
        assert pdt_tracker.trades_remaining(trades_in_window=[]) == 3

    def test_one_trade_allows_entry(self, pdt_tracker):
        """1 trade used = entry allowed."""
        trades = [date.today()]
        assert pdt_tracker.can_open_day_trade(trades_in_window=trades) is True
        assert pdt_tracker.trades_remaining(trades_in_window=trades) == 2

    def test_two_trades_allows_entry(self, pdt_tracker):
        """2 trades used = entry allowed."""
        trades = [date.today(), date.today()]
        assert pdt_tracker.can_open_day_trade(trades_in_window=trades) is True
        assert pdt_tracker.trades_remaining(trades_in_window=trades) == 1

    def test_three_trades_blocks_entry(self, pdt_tracker):
        """3 trades used = entry BLOCKED (at limit)."""
        trades = [date.today(), date.today(), date.today()]
        assert pdt_tracker.can_open_day_trade(trades_in_window=trades) is False
        assert pdt_tracker.trades_remaining(trades_in_window=trades) == 0

    def test_four_trades_blocks_entry(self, pdt_tracker):
        """4+ trades = definitely blocked (should never happen but defensive)."""
        trades = [date.today()] * 4
        assert pdt_tracker.can_open_day_trade(trades_in_window=trades) is False

    def test_rolling_window_drops_old_trades(self, pdt_tracker):
        """Trades older than 5 business days should not count."""
        today = date.today()
        old_trade = today - timedelta(days=8)  # Beyond 5 business days
        trades = [old_trade, old_trade, old_trade, today]
        # Only 1 trade in window (today), 3 old trades dropped
        assert pdt_tracker.trades_remaining(trades_in_window=trades) == 2

    def test_rolling_window_friday_to_monday(self, pdt_tracker):
        """
        Friday trade + Monday trade = both within 5 business days.
        Threat T-03: Weekend handling.
        """
        # Simulate: 3 trades on Friday, check if Monday is blocked
        friday = date(2026, 2, 6)  # Friday
        monday = date(2026, 2, 9)  # Following Monday
        trades = [friday, friday, friday]  # 3 Friday trades
        # Monday is within 5 business days of Friday
        remaining = pdt_tracker.trades_remaining(trades_in_window=trades, as_of_date=monday)
        assert remaining == 0  # Still blocked on Monday

    def test_rolling_window_holiday_handling(self, pdt_tracker):
        """
        Market holidays don't count as business days.
        Threat T-03: Holiday edge case.
        """
        # Presidents' Day 2026 is Feb 16 (Monday)
        # Trade on Feb 12 (Thursday before)
        # Feb 17 (Tuesday after) should still see Thursday's trades in window
        thursday = date(2026, 2, 12)
        tuesday = date(2026, 2, 17)
        trades = [thursday, thursday, thursday]
        remaining = pdt_tracker.trades_remaining(trades_in_window=trades, as_of_date=tuesday)
        assert remaining == 0  # Thursday trades still in window

    def test_pdt_state_persistence(self, pdt_tracker):
        """
        PDT count must survive serialization/deserialization.
        Threat T-06: State corruption.
        """
        trades = [date.today(), date.today()]
        state = pdt_tracker.to_state_dict(trades_in_window=trades)
        restored = pdt_tracker.from_state_dict(state)
        assert restored["trades_remaining"] == 1


# =============================================================================
# AGGREGATE POSITION LIMIT TESTS
# Threat: T-04 (concurrent overflow)
# =============================================================================


class TestAggregatePositionLimits:
    """Tests for aggregate exposure across multiple open positions."""

    def test_single_position_within_limit(self, position_sizer):
        """One position at $100 with $120 limit = allowed."""
        open_positions: List[Dict[str, Any]] = [{"cost_basis": 100.00}]
        assert (
            position_sizer.validate_aggregate_exposure(open_positions, new_position_cost=0.00)
            is True
        )

    def test_new_position_would_exceed_aggregate(self, position_sizer):
        """Existing $80 + new $50 = $130 > $120 limit."""
        open_positions: List[Dict[str, Any]] = [{"cost_basis": 80.00}]
        assert (
            position_sizer.validate_aggregate_exposure(open_positions, new_position_cost=50.00)
            is False
        )

    def test_multiple_positions_at_aggregate_limit(self, position_sizer):
        """Three positions totaling exactly $120 = allowed."""
        open_positions: List[Dict[str, Any]] = [
            {"cost_basis": 40.00},
            {"cost_basis": 40.00},
            {"cost_basis": 40.00},
        ]
        assert (
            position_sizer.validate_aggregate_exposure(open_positions, new_position_cost=0.00)
            is True
        )

    def test_no_open_positions_allows_full_limit(self, position_sizer):
        """No existing positions = full $120 available."""
        assert position_sizer.validate_aggregate_exposure([], new_position_cost=120.00) is True

    def test_aggregate_with_penny_overflow(self, position_sizer):
        """
        Existing $119.99 + new $0.02 = $120.01 > $120 limit.
        Threat T-01: Exact boundary.
        """
        open_positions: List[Dict[str, Any]] = [{"cost_basis": 119.99}]
        assert (
            position_sizer.validate_aggregate_exposure(open_positions, new_position_cost=0.02)
            is False
        )
