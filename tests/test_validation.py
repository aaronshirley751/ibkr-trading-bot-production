"""Tests for gameplan validation."""

from typing import Any, Dict

import pytest

from src.utils.validation import validate_gameplan


# Valid gameplan fixture
@pytest.fixture
def valid_gameplan() -> Dict[str, Any]:
    """Return a valid gameplan for testing."""
    return {
        "strategy": "A",
        "symbol": "SPY",
        "key_levels": {"support": 580.0, "resistance": 590.0},
        "data_quality": {"min_volume": 1000000, "max_spread_pct": 0.05},
        "hard_limits": {"max_loss": 1000.0, "max_position_size": 10000.0},
        "scorecard": {"win_rate": 65.5, "avg_profit": 250.0, "total_trades": 100},
    }


def test_validate_gameplan_valid(valid_gameplan: Dict[str, Any]) -> None:
    """Valid gameplan should pass validation."""
    # Should not raise
    validate_gameplan(valid_gameplan)


def test_validate_gameplan_missing_field(valid_gameplan: Dict[str, Any]) -> None:
    """Missing required field should fail."""
    del valid_gameplan["strategy"]

    with pytest.raises(ValueError, match="Missing required field: strategy"):
        validate_gameplan(valid_gameplan)


def test_validate_gameplan_invalid_strategy(valid_gameplan: Dict[str, Any]) -> None:
    """Invalid strategy value should fail."""
    valid_gameplan["strategy"] = "X"

    with pytest.raises(ValueError, match="Invalid strategy: X"):
        validate_gameplan(valid_gameplan)


def test_validate_gameplan_invalid_symbol(valid_gameplan: Dict[str, Any]) -> None:
    """Invalid symbol value should fail."""
    valid_gameplan["symbol"] = "AAPL"

    with pytest.raises(ValueError, match="Invalid symbol: AAPL"):
        validate_gameplan(valid_gameplan)


def test_validate_gameplan_empty_string_enum(valid_gameplan: Dict[str, Any]) -> None:
    """Empty string in enum field should fail."""
    valid_gameplan["strategy"] = ""

    with pytest.raises(ValueError, match="strategy cannot be empty"):
        validate_gameplan(valid_gameplan)


def test_validate_gameplan_whitespace_only_enum(valid_gameplan: Dict[str, Any]) -> None:
    """Whitespace-only string in enum field should fail."""
    valid_gameplan["strategy"] = "   "

    with pytest.raises(ValueError, match="strategy cannot be empty"):
        validate_gameplan(valid_gameplan)


def test_validate_gameplan_nested_type_mismatch(valid_gameplan: Dict[str, Any]) -> None:
    """key_levels as list instead of dict should fail with clear error."""
    valid_gameplan["key_levels"] = ["not", "a", "dict"]

    with pytest.raises(ValueError, match="key_levels must be a dictionary"):
        validate_gameplan(valid_gameplan)


def test_validate_gameplan_data_quality_type_mismatch(valid_gameplan: Dict[str, Any]) -> None:
    """data_quality as string should fail with clear error."""
    valid_gameplan["data_quality"] = "not a dict"

    with pytest.raises(ValueError, match="data_quality must be a dictionary"):
        validate_gameplan(valid_gameplan)


def test_validate_gameplan_hard_limits_type_mismatch(valid_gameplan: Dict[str, Any]) -> None:
    """hard_limits as integer should fail with clear error."""
    valid_gameplan["hard_limits"] = 12345

    with pytest.raises(ValueError, match="hard_limits must be a dictionary"):
        validate_gameplan(valid_gameplan)


def test_validate_gameplan_scorecard_type_mismatch(valid_gameplan: Dict[str, Any]) -> None:
    """scorecard as list should fail with clear error."""
    valid_gameplan["scorecard"] = [1, 2, 3]

    with pytest.raises(ValueError, match="scorecard must be a dictionary"):
        validate_gameplan(valid_gameplan)


def test_validate_key_levels_missing_field(valid_gameplan: Dict[str, Any]) -> None:
    """Missing support level should fail."""
    del valid_gameplan["key_levels"]["support"]

    with pytest.raises(ValueError, match="key_levels missing required field: support"):
        validate_gameplan(valid_gameplan)


def test_validate_key_levels_non_numeric(valid_gameplan: Dict[str, Any]) -> None:
    """Non-numeric support level should fail."""
    valid_gameplan["key_levels"]["support"] = "not a number"

    with pytest.raises(ValueError, match="key_levels.support must be a number"):
        validate_gameplan(valid_gameplan)


def test_validate_data_quality_non_positive(valid_gameplan: Dict[str, Any]) -> None:
    """Zero min_volume should fail."""
    valid_gameplan["data_quality"]["min_volume"] = 0

    with pytest.raises(ValueError, match="data_quality.min_volume must be positive"):
        validate_gameplan(valid_gameplan)


def test_validate_data_quality_negative(valid_gameplan: Dict[str, Any]) -> None:
    """Negative max_spread_pct should fail."""
    valid_gameplan["data_quality"]["max_spread_pct"] = -0.05

    with pytest.raises(ValueError, match="data_quality.max_spread_pct must be positive"):
        validate_gameplan(valid_gameplan)


def test_validate_hard_limits_non_positive(valid_gameplan: Dict[str, Any]) -> None:
    """Zero max_loss should fail."""
    valid_gameplan["hard_limits"]["max_loss"] = 0

    with pytest.raises(ValueError, match="hard_limits.max_loss must be positive"):
        validate_gameplan(valid_gameplan)


def test_validate_scorecard_win_rate_out_of_range(valid_gameplan: Dict[str, Any]) -> None:
    """Win rate > 100 should fail."""
    valid_gameplan["scorecard"]["win_rate"] = 150.0

    with pytest.raises(ValueError, match="scorecard.win_rate must be between 0 and 100"):
        validate_gameplan(valid_gameplan)


def test_validate_scorecard_negative_trades(valid_gameplan: Dict[str, Any]) -> None:
    """Negative total_trades should fail."""
    valid_gameplan["scorecard"]["total_trades"] = -5

    with pytest.raises(ValueError, match="scorecard.total_trades must be non-negative"):
        validate_gameplan(valid_gameplan)
