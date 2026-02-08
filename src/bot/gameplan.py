"""
Gameplan loading, validation, and default safety deployment.

The GameplanLoader class handles:
- Loading daily_gameplan.json from the filesystem
- Validating all required fields against the Crucible schema
- Returning Strategy C default on any failure

Safety Philosophy: Any failure in loading or validation results in
Strategy C (cash preservation). There are no exceptions to this rule.
"""

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict

from src.strategy.exceptions import GameplanValidationError  # noqa: F401 — re-export

logger = logging.getLogger(__name__)

# Required top-level fields for any gameplan
REQUIRED_FIELDS = ["strategy", "regime", "symbols", "hard_limits", "data_quality"]

# Valid strategy identifiers
VALID_STRATEGIES = {"A", "B", "C"}

# Default Strategy C gameplan returned on any failure
DEFAULT_STRATEGY_C: Dict[str, Any] = {
    "date": "",
    "session_id": "",
    "regime": "unknown",
    "strategy": "C",
    "symbols": [],
    "position_size_multiplier": 0.0,
    "vix_at_analysis": None,
    "vix_source_verified": False,
    "bias": "neutral",
    "expected_behavior": "cash_preservation",
    "key_levels": {},
    "catalysts": [],
    "earnings_blackout": [],
    "geo_risk": "high",
    "alert_message": "Strategy C DEFAULT — gameplan load/validation failure",
    "data_quality": {
        "quarantine_active": True,
        "last_verified": None,
    },
    "hard_limits": {
        "max_daily_loss_pct": 0.10,
        "pdt_trades_remaining": 0,
        "weekly_drawdown_governor_active": True,
        "max_intraday_pivots": 0,
    },
    "scorecard": {
        "yesterday_pnl": 0.0,
        "weekly_cumulative_pnl": 0.0,
    },
}


class GameplanLoader:
    """
    Loads, validates, and provides daily gameplan configuration.

    Safety invariant: Any failure in load() or validate() results in
    a Strategy C (cash preservation) gameplan being returned.
    """

    def load(self, path: Path) -> Dict[str, Any]:
        """
        Load a daily gameplan from a JSON file.

        Returns Strategy C default on:
        - Missing file
        - Invalid/corrupted JSON
        - Empty file
        - Any I/O error

        Args:
            path: Path to the daily_gameplan.json file.

        Returns:
            Parsed gameplan dict, or Strategy C default on failure.
        """
        try:
            if not path.exists():
                logger.warning("Gameplan file not found: %s", path)
                return self._default_strategy_c()

            # utf-8-sig handles optional BOM (Windows Notepad edge case)
            content = path.read_text(encoding="utf-8-sig")

            if not content.strip():
                logger.warning("Gameplan file is empty: %s", path)
                return self._default_strategy_c()

            gameplan = json.loads(content)

            if not isinstance(gameplan, dict):
                logger.error("Gameplan root is not a dict: %s", type(gameplan).__name__)
                return self._default_strategy_c()

            logger.info(
                "Gameplan loaded from %s: strategy=%s",
                path,
                gameplan.get("strategy"),
            )
            return gameplan

        except json.JSONDecodeError as exc:
            logger.error("Gameplan JSON parse failed: %s", exc)
            return self._default_strategy_c()
        except Exception as exc:
            logger.error("Gameplan load failed: %s: %s", type(exc).__name__, exc)
            return self._default_strategy_c()

    def validate(self, gameplan: Dict[str, Any]) -> bool:
        """
        Validate a gameplan against the Crucible schema.

        Raises GameplanValidationError on any validation failure.
        Returns True on success.

        Args:
            gameplan: The parsed gameplan dict.

        Returns:
            True if validation succeeds.

        Raises:
            GameplanValidationError: If any required field is missing or invalid.
        """
        if not isinstance(gameplan, dict):
            raise GameplanValidationError("Gameplan must be a dict")

        # Check required top-level fields
        for field in REQUIRED_FIELDS:
            if field not in gameplan:
                raise GameplanValidationError(f"Missing required field: {field}")

        # Validate strategy value
        strategy = gameplan["strategy"]
        if strategy not in VALID_STRATEGIES:
            raise GameplanValidationError(
                f"Invalid strategy '{strategy}': must be one of {VALID_STRATEGIES}"
            )

        # Validate symbols for non-C strategies
        if strategy in ("A", "B"):
            symbols = gameplan.get("symbols", [])
            if not symbols:
                raise GameplanValidationError(
                    f"Strategy {strategy} requires at least one symbol in 'symbols'"
                )

        # Validate hard_limits section
        hard_limits = gameplan.get("hard_limits", {})
        if not isinstance(hard_limits, dict):
            raise GameplanValidationError("hard_limits must be a dict")

        # Validate PDT trades remaining (must be non-negative)
        pdt = hard_limits.get("pdt_trades_remaining")
        if pdt is not None and pdt < 0:
            raise GameplanValidationError(f"pdt_trades_remaining cannot be negative: {pdt}")

        # Validate max_daily_loss_pct (must be 0..1)
        max_loss = hard_limits.get("max_daily_loss_pct")
        if max_loss is not None and (max_loss < 0 or max_loss > 1.0):
            raise GameplanValidationError(
                f"max_daily_loss_pct must be between 0 and 1.0: {max_loss}"
            )

        # Validate data_quality section
        data_quality = gameplan.get("data_quality", {})
        if not isinstance(data_quality, dict):
            raise GameplanValidationError("data_quality must be a dict")

        logger.debug("Gameplan validation passed: strategy=%s", strategy)
        return True

    def _default_strategy_c(self) -> Dict[str, Any]:
        """Return a deep copy of the default Strategy C gameplan."""
        return copy.deepcopy(DEFAULT_STRATEGY_C)
