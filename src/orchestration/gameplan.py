"""
Gameplan generation utilities.

Provides functions to generate emergency and Strategy C gameplans
for failsafe operation when regular gameplans are unavailable or invalid.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def generate_strategy_c(output_path: Path) -> dict[str, Any]:
    """
    Generate emergency Strategy C gameplan.

    Strategy C is the cash preservation mode - no trading authorized.
    This gameplan is used when:
    - No gameplan file exists
    - Gameplan schema validation fails
    - Data quarantine is active
    - System must default to safe state

    Args:
        output_path: Path where gameplan JSON will be written.

    Returns:
        The generated gameplan dictionary.
    """
    now = datetime.now(timezone.utc)

    gameplan: dict[str, Any] = {
        "date": now.strftime("%Y-%m-%d"),
        "session_id": f"emergency_{now.strftime('%Y%m%d_%H%M%S')}",
        "regime": "crisis",
        "strategy": "C",
        "symbols": [],
        "position_size_multiplier": 0.0,
        "vix_at_analysis": 0.0,
        "vix_source_verified": False,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "key_levels": {
            "support": 0.0,
            "resistance": 0.0,
        },
        "catalysts": ["Emergency deployment — no trading authorized"],
        "earnings_blackout": [],
        "geo_risk": "high",
        "alert_message": (
            "⚠️ EMERGENCY STRATEGY C — No trading. " "Operator intervention required."
        ),
        "data_quality": {
            "quarantine_active": True,
            "stale_fields": ["all"],
            "last_verified": now.isoformat(),
            "min_volume": 0,
            "max_spread_pct": 0.0,
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.0,
            "max_single_position": 0,
            "pdt_trades_remaining": 0,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": True,
            "max_intraday_pivots": 0,
        },
        "scorecard": {
            "yesterday_pnl": 0.0,
            "yesterday_hit_rate": 0.0,
            "regime_accuracy": False,
            "weekly_cumulative_pnl": 0.0,
        },
    }

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(gameplan, f, indent=2)

    logger.info(f"Strategy C gameplan generated: {output_path}")
    return gameplan


def validate_gameplan_schema(gameplan: dict[str, Any]) -> bool:
    """
    Validate gameplan has required fields for safe operation.

    This is a lightweight validation focused on safety-critical fields.
    For full schema validation, see src/utils/validation.py.

    Args:
        gameplan: Gameplan dictionary to validate.

    Returns:
        True if gameplan passes validation, False otherwise.
    """
    required_fields = [
        "strategy",
        "regime",
        "hard_limits",
        "data_quality",
    ]

    for field in required_fields:
        if field not in gameplan:
            logger.warning(f"Gameplan missing required field: {field}")
            return False

    # Validate strategy is valid
    strategy = gameplan.get("strategy")
    if strategy not in ["A", "B", "C"]:
        logger.warning(f"Invalid strategy value: {strategy}")
        return False

    # Validate hard_limits is a dict
    hard_limits = gameplan.get("hard_limits")
    if not isinstance(hard_limits, dict):
        logger.warning("hard_limits must be a dictionary")
        return False

    # Validate data_quality is a dict
    data_quality = gameplan.get("data_quality")
    if not isinstance(data_quality, dict):
        logger.warning("data_quality must be a dictionary")
        return False

    return True


def load_gameplan_json(path: Path) -> dict[str, Any] | None:
    """
    Load gameplan from JSON file.

    Args:
        path: Path to gameplan JSON file.

    Returns:
        Gameplan dictionary, or None if loading fails.
    """
    if not path.exists():
        logger.warning(f"Gameplan file not found: {path}")
        return None

    try:
        with open(path, "r") as f:
            gameplan: dict[str, Any] = json.load(f)
            return gameplan
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in gameplan file: {e}")
        return None
    except OSError as e:
        logger.error(f"Failed to read gameplan file: {e}")
        return None
