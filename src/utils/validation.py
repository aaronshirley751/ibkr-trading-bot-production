"""Gameplan validation utilities.

This module provides validation functions for trading gameplans,
ensuring all required fields are present and properly formatted.
"""

from typing import Any, Dict


def validate_gameplan(gameplan: Dict[str, Any]) -> None:
    """Validate a trading gameplan configuration.

    Args:
        gameplan: Dictionary containing gameplan configuration

    Raises:
        ValueError: If validation fails
    """
    # Required fields
    required_fields = [
        "strategy",
        "symbol",
        "key_levels",
        "data_quality",
        "hard_limits",
        "scorecard",
    ]

    for field in required_fields:
        if field not in gameplan:
            raise ValueError(f"Missing required field: {field}")

    # Enum validations
    enums = {
        "strategy": ["A", "B", "C"],
        "symbol": ["SPY", "QQQ", "IWM"],
    }

    for field, valid_values in enums.items():
        if field in gameplan:
            value = gameplan[field]
            if not value or (isinstance(value, str) and value.strip() == ""):
                raise ValueError(f"{field} cannot be empty")
            if value not in valid_values:
                raise ValueError(f"Invalid {field}: {value}")

    # Validate nested structures
    _validate_key_levels(gameplan["key_levels"])
    _validate_data_quality(gameplan["data_quality"])
    _validate_hard_limits(gameplan["hard_limits"])
    _validate_scorecard(gameplan["scorecard"])


def _validate_key_levels(levels: Any) -> None:
    """Validate key_levels structure.

    Args:
        levels: Key levels configuration

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(levels, dict):
        raise ValueError("key_levels must be a dictionary")

    required_keys = ["support", "resistance"]
    for key in required_keys:
        if key not in levels:
            raise ValueError(f"key_levels missing required field: {key}")

        # Validate numeric values
        if not isinstance(levels[key], (int, float)):
            raise ValueError(f"key_levels.{key} must be a number")


def _validate_data_quality(quality: Any) -> None:
    """Validate data_quality structure.

    Args:
        quality: Data quality configuration

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(quality, dict):
        raise ValueError("data_quality must be a dictionary")

    required_keys = ["min_volume", "max_spread_pct"]
    for key in required_keys:
        if key not in quality:
            raise ValueError(f"data_quality missing required field: {key}")

        # Validate numeric values
        if not isinstance(quality[key], (int, float)):
            raise ValueError(f"data_quality.{key} must be a number")

        # Validate positive values
        if quality[key] <= 0:
            raise ValueError(f"data_quality.{key} must be positive")


def _validate_hard_limits(limits: Any) -> None:
    """Validate hard_limits structure.

    Args:
        limits: Hard limits configuration

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(limits, dict):
        raise ValueError("hard_limits must be a dictionary")

    required_keys = ["max_loss", "max_position_size"]
    for key in required_keys:
        if key not in limits:
            raise ValueError(f"hard_limits missing required field: {key}")

        # Validate numeric values
        if not isinstance(limits[key], (int, float)):
            raise ValueError(f"hard_limits.{key} must be a number")

        # Validate positive values
        if limits[key] <= 0:
            raise ValueError(f"hard_limits.{key} must be positive")


def _validate_scorecard(scorecard: Any) -> None:
    """Validate scorecard structure.

    Args:
        scorecard: Scorecard configuration

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(scorecard, dict):
        raise ValueError("scorecard must be a dictionary")

    required_keys = ["win_rate", "avg_profit", "total_trades"]
    for key in required_keys:
        if key not in scorecard:
            raise ValueError(f"scorecard missing required field: {key}")

        # Validate numeric values
        if not isinstance(scorecard[key], (int, float)):
            raise ValueError(f"scorecard.{key} must be a number")

    # Validate win_rate is a percentage
    if not 0 <= scorecard["win_rate"] <= 100:
        raise ValueError("scorecard.win_rate must be between 0 and 100")

    # Validate total_trades is non-negative
    if scorecard["total_trades"] < 0:
        raise ValueError("scorecard.total_trades must be non-negative")
