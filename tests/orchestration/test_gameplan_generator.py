"""
Unit tests for gameplan generation utilities.

Tests cover:
- Strategy C gameplan generation
- Gameplan schema validation
- Gameplan loading
"""

import json
from pathlib import Path


from src.orchestration.gameplan import (
    generate_strategy_c,
    load_gameplan_json,
    validate_gameplan_schema,
)

# =============================================================================
# STRATEGY C GENERATION
# =============================================================================


class TestStrategyCGeneration:
    """Test Strategy C gameplan generation."""

    def test_generates_valid_json(self, tmp_path: Path) -> None:
        """Generated gameplan is valid JSON."""
        output_path = tmp_path / "strategy_c.json"

        generate_strategy_c(output_path)

        assert output_path.exists()
        with open(output_path) as f:
            gameplan = json.load(f)
        assert isinstance(gameplan, dict)

    def test_strategy_is_c(self, tmp_path: Path) -> None:
        """Generated gameplan has strategy 'C'."""
        output_path = tmp_path / "strategy_c.json"

        gameplan = generate_strategy_c(output_path)

        assert gameplan["strategy"] == "C"

    def test_quarantine_is_active(self, tmp_path: Path) -> None:
        """Generated gameplan has quarantine_active True."""
        output_path = tmp_path / "strategy_c.json"

        gameplan = generate_strategy_c(output_path)

        assert gameplan["data_quality"]["quarantine_active"] is True

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Parent directories are created if missing."""
        output_path = tmp_path / "deep" / "nested" / "path" / "gameplan.json"

        generate_strategy_c(output_path)

        assert output_path.exists()

    def test_returns_generated_gameplan(self, tmp_path: Path) -> None:
        """Function returns the generated gameplan dict."""
        output_path = tmp_path / "strategy_c.json"

        gameplan = generate_strategy_c(output_path)

        assert isinstance(gameplan, dict)
        assert "strategy" in gameplan

    def test_includes_required_fields(self, tmp_path: Path) -> None:
        """Generated gameplan includes all required fields."""
        output_path = tmp_path / "strategy_c.json"

        gameplan = generate_strategy_c(output_path)

        assert "date" in gameplan
        assert "strategy" in gameplan
        assert "regime" in gameplan
        assert "hard_limits" in gameplan
        assert "data_quality" in gameplan
        assert "scorecard" in gameplan

    def test_hard_limits_all_zero(self, tmp_path: Path) -> None:
        """Strategy C hard limits prevent all trading."""
        output_path = tmp_path / "strategy_c.json"

        gameplan = generate_strategy_c(output_path)

        hard_limits = gameplan["hard_limits"]
        assert hard_limits["max_daily_loss_pct"] == 0.0
        assert hard_limits["max_single_position"] == 0
        assert hard_limits["pdt_trades_remaining"] == 0


# =============================================================================
# SCHEMA VALIDATION
# =============================================================================


class TestSchemaValidation:
    """Test gameplan schema validation."""

    def test_valid_gameplan_passes(self) -> None:
        """Valid gameplan passes validation."""
        gameplan = {
            "strategy": "A",
            "regime": "trending",
            "hard_limits": {"max_daily_loss_pct": 2.0},
            "data_quality": {"quarantine_active": False},
        }

        assert validate_gameplan_schema(gameplan) is True

    def test_missing_strategy_fails(self) -> None:
        """Missing strategy fails validation."""
        gameplan = {
            "regime": "trending",
            "hard_limits": {},
            "data_quality": {},
        }

        assert validate_gameplan_schema(gameplan) is False

    def test_missing_regime_fails(self) -> None:
        """Missing regime fails validation."""
        gameplan = {
            "strategy": "A",
            "hard_limits": {},
            "data_quality": {},
        }

        assert validate_gameplan_schema(gameplan) is False

    def test_missing_hard_limits_fails(self) -> None:
        """Missing hard_limits fails validation."""
        gameplan = {
            "strategy": "A",
            "regime": "trending",
            "data_quality": {},
        }

        assert validate_gameplan_schema(gameplan) is False

    def test_missing_data_quality_fails(self) -> None:
        """Missing data_quality fails validation."""
        gameplan = {
            "strategy": "A",
            "regime": "trending",
            "hard_limits": {},
        }

        assert validate_gameplan_schema(gameplan) is False

    def test_invalid_strategy_value_fails(self) -> None:
        """Invalid strategy value fails validation."""
        gameplan = {
            "strategy": "X",  # Invalid
            "regime": "trending",
            "hard_limits": {},
            "data_quality": {},
        }

        assert validate_gameplan_schema(gameplan) is False

    def test_strategy_a_passes(self) -> None:
        """Strategy A is valid."""
        gameplan = {
            "strategy": "A",
            "regime": "trending",
            "hard_limits": {},
            "data_quality": {},
        }

        assert validate_gameplan_schema(gameplan) is True

    def test_strategy_b_passes(self) -> None:
        """Strategy B is valid."""
        gameplan = {
            "strategy": "B",
            "regime": "ranging",
            "hard_limits": {},
            "data_quality": {},
        }

        assert validate_gameplan_schema(gameplan) is True

    def test_strategy_c_passes(self) -> None:
        """Strategy C is valid."""
        gameplan = {
            "strategy": "C",
            "regime": "crisis",
            "hard_limits": {},
            "data_quality": {},
        }

        assert validate_gameplan_schema(gameplan) is True

    def test_hard_limits_not_dict_fails(self) -> None:
        """hard_limits not a dict fails validation."""
        gameplan = {
            "strategy": "A",
            "regime": "trending",
            "hard_limits": "not a dict",
            "data_quality": {},
        }

        assert validate_gameplan_schema(gameplan) is False

    def test_data_quality_not_dict_fails(self) -> None:
        """data_quality not a dict fails validation."""
        gameplan = {
            "strategy": "A",
            "regime": "trending",
            "hard_limits": {},
            "data_quality": "not a dict",
        }

        assert validate_gameplan_schema(gameplan) is False


# =============================================================================
# GAMEPLAN LOADING
# =============================================================================


class TestGameplanLoading:
    """Test gameplan JSON loading."""

    def test_loads_valid_json(self, tmp_path: Path) -> None:
        """Valid JSON file loads successfully."""
        gameplan_path = tmp_path / "gameplan.json"
        gameplan = {"strategy": "A", "regime": "trending"}
        gameplan_path.write_text(json.dumps(gameplan))

        result = load_gameplan_json(gameplan_path)

        assert result == gameplan

    def test_nonexistent_file_returns_none(self, tmp_path: Path) -> None:
        """Non-existent file returns None."""
        gameplan_path = tmp_path / "nonexistent.json"

        result = load_gameplan_json(gameplan_path)

        assert result is None

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        """Invalid JSON returns None."""
        gameplan_path = tmp_path / "invalid.json"
        gameplan_path.write_text("{ not valid json }")

        result = load_gameplan_json(gameplan_path)

        assert result is None

    def test_empty_file_returns_none(self, tmp_path: Path) -> None:
        """Empty file returns None."""
        gameplan_path = tmp_path / "empty.json"
        gameplan_path.write_text("")

        result = load_gameplan_json(gameplan_path)

        assert result is None

    def test_preserves_all_fields(self, tmp_path: Path) -> None:
        """All fields in JSON are preserved."""
        gameplan_path = tmp_path / "gameplan.json"
        gameplan = {
            "strategy": "B",
            "regime": "ranging",
            "symbols": ["SPY", "QQQ"],
            "hard_limits": {"max_daily_loss_pct": 2.5},
            "data_quality": {"quarantine_active": False},
            "custom_field": "custom_value",
        }
        gameplan_path.write_text(json.dumps(gameplan))

        result = load_gameplan_json(gameplan_path)

        assert result == gameplan
