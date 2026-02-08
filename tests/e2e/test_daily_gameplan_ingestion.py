"""
E2E tests for daily gameplan ingestion.

Tests cover:
- Loading daily_gameplan.json from file system
- Validating all required fields against schema
- Applying gameplan parameters to runtime configuration
- Strategy C default on missing/malformed gameplan
- Data quality quarantine enforcement
- Hard limit propagation to risk engine

All tests in this file are FUNCTIONAL — they exercise the real
GameplanLoader implementation against the Crucible schema.
"""

import copy
import json

import pytest

from src.bot.gameplan import GameplanLoader
from src.strategy.exceptions import GameplanValidationError
from src.strategy.execution import evaluate_signals, load_gameplan
from src.strategy.selection import select_strategy

pytestmark = pytest.mark.e2e


# =================================================================
# GAMEPLAN LOADING — File I/O and Basic Parsing
# =================================================================


class TestGameplanFileLoading:
    """Tests for gameplan file discovery and JSON parsing."""

    def test_load_valid_gameplan_from_file(self, valid_strategy_a_gameplan, tmp_path):
        """
        GIVEN: Valid daily_gameplan.json exists at expected path
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns parsed gameplan dict with all fields intact
        """
        filepath = tmp_path / "daily_gameplan.json"
        filepath.write_text(json.dumps(valid_strategy_a_gameplan))

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "A"
        assert result["regime"] == "normal"
        assert result["date"] == "2026-02-07"
        assert result["hard_limits"]["pdt_trades_remaining"] == 3

    def test_load_missing_gameplan_file_returns_strategy_c(self, tmp_path):
        """
        GIVEN: No daily_gameplan.json exists at expected path
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns Strategy C default gameplan

        @CRO: CRITICAL — missing gameplan MUST default to cash preservation.
        """
        filepath = tmp_path / "nonexistent_gameplan.json"

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "C"
        assert result["symbols"] == []

    def test_load_corrupted_json_returns_strategy_c(self, tmp_path):
        """
        GIVEN: Gameplan file exists but contains invalid JSON
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns Strategy C default gameplan
        """
        filepath = tmp_path / "daily_gameplan.json"
        filepath.write_text("{invalid json content: broken,,,")

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "C"

    def test_load_empty_file_returns_strategy_c(self, tmp_path):
        """
        GIVEN: Gameplan file exists but is empty (0 bytes)
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns Strategy C default
        """
        filepath = tmp_path / "daily_gameplan.json"
        filepath.write_text("")

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "C"

    def test_load_gameplan_with_unicode_bom(self, valid_strategy_a_gameplan, tmp_path):
        """
        GIVEN: Gameplan file has UTF-8 BOM prefix
        WHEN: GameplanLoader.load(path) is called
        THEN: Parses correctly despite BOM

        Edge case: Windows Notepad saves with BOM by default.
        """
        filepath = tmp_path / "daily_gameplan.json"
        content = "\ufeff" + json.dumps(valid_strategy_a_gameplan)
        filepath.write_text(content, encoding="utf-8")

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "A"

    def test_load_json_array_returns_strategy_c(self, tmp_path):
        """
        GIVEN: Gameplan file contains a JSON array (not an object)
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns Strategy C default (root must be a dict)
        """
        filepath = tmp_path / "daily_gameplan.json"
        filepath.write_text('[{"strategy": "A"}]')

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "C"

    def test_load_whitespace_only_file_returns_strategy_c(self, tmp_path):
        """
        GIVEN: Gameplan file contains only whitespace
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns Strategy C default
        """
        filepath = tmp_path / "daily_gameplan.json"
        filepath.write_text("   \n\t  \n")

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "C"


# =================================================================
# GAMEPLAN VALIDATION — Schema Compliance
# =================================================================


class TestGameplanValidation:
    """Tests for gameplan structural and semantic validation."""

    def test_valid_strategy_a_passes_validation(self, valid_strategy_a_gameplan):
        """
        GIVEN: Complete, valid Strategy A gameplan
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Returns True (validation passes)
        """
        loader = GameplanLoader()
        assert loader.validate(valid_strategy_a_gameplan) is True

    def test_valid_strategy_b_passes_validation(self, valid_strategy_b_gameplan):
        """
        GIVEN: Complete, valid Strategy B gameplan
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Returns True
        """
        loader = GameplanLoader()
        assert loader.validate(valid_strategy_b_gameplan) is True

    def test_valid_strategy_c_passes_validation(self, valid_strategy_c_gameplan):
        """
        GIVEN: Complete, valid Strategy C gameplan
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Returns True
        """
        loader = GameplanLoader()
        assert loader.validate(valid_strategy_c_gameplan) is True

    def test_missing_strategy_field_fails_validation(self, malformed_gameplan_missing_strategy):
        """
        GIVEN: Gameplan missing the 'strategy' field
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Raises GameplanValidationError
        """
        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="strategy"):
            loader.validate(malformed_gameplan_missing_strategy)

    def test_invalid_strategy_value_fails_validation(self, malformed_gameplan_invalid_strategy):
        """
        GIVEN: Gameplan with strategy="D" (not in {A, B, C})
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Raises GameplanValidationError
        """
        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="strategy"):
            loader.validate(malformed_gameplan_invalid_strategy)

    def test_missing_hard_limits_fails_validation(self, malformed_gameplan_missing_hard_limits):
        """
        GIVEN: Gameplan missing the 'hard_limits' section
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Raises GameplanValidationError

        @CRO: CRITICAL — hard limits are non-negotiable.
        """
        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="hard_limits"):
            loader.validate(malformed_gameplan_missing_hard_limits)

    def test_missing_data_quality_fails_validation(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan missing 'data_quality' section
        WHEN: Validated
        THEN: Fails — data quality is required for safety decisions
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        del gameplan["data_quality"]

        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="data_quality"):
            loader.validate(gameplan)

    def test_negative_pdt_remaining_fails_validation(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan with pdt_trades_remaining = -1
        WHEN: Validated
        THEN: Fails — negative PDT count is invalid
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["hard_limits"]["pdt_trades_remaining"] = -1

        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="pdt"):
            loader.validate(gameplan)

    def test_max_daily_loss_exceeds_100_percent_fails(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan with max_daily_loss_pct = 1.5 (150%)
        WHEN: Validated
        THEN: Fails — cannot lose more than 100% in a day
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["hard_limits"]["max_daily_loss_pct"] = 1.5

        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError):
            loader.validate(gameplan)

    def test_strategy_a_with_empty_symbols_fails(self, valid_strategy_a_gameplan):
        """
        GIVEN: Strategy A gameplan but symbols list is empty
        WHEN: Validated
        THEN: Fails — Strategy A requires at least one symbol
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["symbols"] = []

        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="symbols"):
            loader.validate(gameplan)

    def test_strategy_c_with_empty_symbols_passes(self, valid_strategy_c_gameplan):
        """
        GIVEN: Strategy C gameplan with empty symbols list
        WHEN: Validated
        THEN: Passes — Strategy C explicitly has no symbols
        """
        loader = GameplanLoader()
        assert loader.validate(valid_strategy_c_gameplan) is True


# =================================================================
# GAMEPLAN PARAMETER APPLICATION — Runtime Config
# =================================================================


class TestGameplanParameterApplication:
    """
    Tests for applying gameplan parameters to the strategy pipeline.

    Uses the real strategy selection and signal evaluation functions
    to verify that gameplan parameters correctly drive trading decisions.
    """

    def test_strategy_a_gameplan_selects_strategy_a(self, valid_strategy_a_gameplan):
        """
        GIVEN: Strategy A gameplan with VIX 15.44 (normal regime)
        WHEN: select_strategy is called with gameplan VIX
        THEN: Returns Strategy A result
        """
        vix = valid_strategy_a_gameplan["vix_at_analysis"]
        result = select_strategy(vix)

        assert result["strategy"] == "A"
        assert result["regime"] == "normal"

    def test_strategy_b_gameplan_selects_strategy_b(self, valid_strategy_b_gameplan):
        """
        GIVEN: Strategy B gameplan with VIX 22.0 (elevated regime)
        WHEN: select_strategy is called with gameplan VIX
        THEN: Returns Strategy B result
        """
        vix = valid_strategy_b_gameplan["vix_at_analysis"]
        result = select_strategy(vix)

        assert result["strategy"] == "B"
        assert result["regime"] == "elevated"

    def test_hard_limits_propagate_to_signal_evaluation(
        self, valid_strategy_a_gameplan, trending_spy_market_data
    ):
        """
        GIVEN: Strategy A gameplan with hard_limits including PDT=3
        WHEN: evaluate_signals processes the gameplan with market data
        THEN: PDT remaining is respected in signal evaluation
        """
        decisions = evaluate_signals(valid_strategy_a_gameplan, trending_spy_market_data)

        # With PDT=3, signals should not be blocked
        assert len(decisions) >= 1
        for d in decisions:
            assert d["strategy"] == "A"
            # PDT=3 should not block any signals
            signal = d.get("signal_details", {})
            assert signal.get("pdt_blocked") is not True

    def test_position_size_multiplier_present_in_gameplan(self, valid_strategy_a_gameplan):
        """
        GIVEN: Strategy A gameplan with position_size_multiplier=1.0
        WHEN: Gameplan is loaded via load_gameplan
        THEN: Multiplier is preserved in validated output
        """
        result = load_gameplan(valid_strategy_a_gameplan)

        assert result["valid"] is True
        assert result.get("position_size_multiplier") == 1.0


# =================================================================
# SAFETY OVERRIDES — Gameplan Fields That Force Strategy C
# =================================================================


class TestGameplanSafetyOverrides:
    """
    Tests for gameplan conditions that MUST force Strategy C
    regardless of what the 'strategy' field says.

    @CRO: Every one of these is a CRITICAL safety assertion.
    """

    def test_quarantine_active_forces_strategy_c(
        self, gameplan_with_quarantine, trending_spy_market_data
    ):
        """
        GIVEN: Gameplan with data_quality.quarantine_active = True
        WHEN: evaluate_signals processes the gameplan
        THEN: Strategy C is enforced — no trades executed

        @CRO: Quarantine means data integrity is compromised.
        """
        decisions = evaluate_signals(gameplan_with_quarantine, trending_spy_market_data)

        assert len(decisions) >= 1
        for d in decisions:
            assert d["strategy"] == "C"
            assert d["action"] == "HOLD"

    def test_zero_pdt_remaining_blocks_new_entries(
        self, gameplan_with_zero_pdt, trending_spy_market_data
    ):
        """
        GIVEN: Gameplan with pdt_trades_remaining = 0
        WHEN: Strategy A signal evaluation produces BUY signals
        THEN: BUY signals are blocked (converted to NEUTRAL)
        """
        decisions = evaluate_signals(gameplan_with_zero_pdt, trending_spy_market_data)

        # With PDT=0, any BUY should be blocked
        for d in decisions:
            if d["strategy"] == "A":
                assert d["action"] != "BUY" or d["signal_details"].get("pdt_blocked")

    def test_select_strategy_quarantine_forces_c(self):
        """
        GIVEN: data_quarantine=True in select_strategy parameters
        WHEN: select_strategy is called with normal VIX
        THEN: Returns Strategy C regardless of VIX regime
        """
        result = select_strategy(vix=15.0, data_quarantine=True)

        assert result["strategy"] == "C"
        assert "data_quarantine_active" in result["reasons"]

    def test_select_strategy_weekly_governor_forces_c(self):
        """
        GIVEN: weekly_governor_active=True in select_strategy parameters
        WHEN: select_strategy is called with normal VIX
        THEN: Returns Strategy C regardless of VIX regime
        """
        result = select_strategy(vix=15.0, weekly_governor_active=True)

        assert result["strategy"] == "C"
        assert "weekly_drawdown_governor_active" in result["reasons"]

    def test_select_strategy_pivot_limit_forces_c(self):
        """
        GIVEN: intraday_pivots >= 2 in select_strategy parameters
        WHEN: select_strategy is called with normal VIX
        THEN: Returns Strategy C — pivot limit reached
        """
        result = select_strategy(vix=15.0, intraday_pivots=2)

        assert result["strategy"] == "C"
        assert "intraday_pivot_limit_reached" in result["reasons"]

    def test_load_gameplan_quarantine_defaults_to_c(self, gameplan_with_quarantine):
        """
        GIVEN: Gameplan dict with quarantine_active=True
        WHEN: load_gameplan processes it
        THEN: Returns strategy=C even though field says A
        """
        result = load_gameplan(gameplan_with_quarantine)

        assert result["strategy"] == "C"

    def test_load_gameplan_missing_fields_defaults_to_c(self):
        """
        GIVEN: Gameplan dict missing required fields
        WHEN: load_gameplan processes it
        THEN: Returns strategy=C and valid=False
        """
        partial_gameplan = {"strategy": "A", "symbols": ["SPY"]}
        result = load_gameplan(partial_gameplan)

        assert result["strategy"] == "C"
        assert result["valid"] is False
