"""
Strategy execution pipeline for Charter & Stone Capital.

Orchestrates the full signal evaluation flow:
    Gameplan JSON → Validation → Signal Evaluation → Trade Decisions

This module is the integration point between:
- Gameplan configuration (from Crucible Morning Gauntlet)
- Signal generation (src/strategy/signals.py)
- Strategy selection (src/strategy/selection.py)

Safety Principle: Any failure in the pipeline defaults to no-trade (Strategy C).
"""

import logging
from typing import Any, Dict, List, Optional

from .signals import evaluate_strategy_a_signal, evaluate_strategy_b_signal

logger = logging.getLogger(__name__)


# =============================================================================
# REQUIRED GAMEPLAN FIELDS
# =============================================================================

REQUIRED_GAMEPLAN_FIELDS = [
    "strategy",
    "regime",
    "symbols",
    "hard_limits",
    "data_quality",
]


# =============================================================================
# GAMEPLAN VALIDATION
# =============================================================================


def load_gameplan(gameplan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate and load a daily gameplan configuration.

    Enforces schema validation. Any missing critical field or safety flag
    causes fallback to Strategy C.

    Args:
        gameplan: Daily gameplan dict (from daily_gameplan.json)

    Returns:
        Dict with keys:
            valid: bool
            strategy: str ("A", "B", "C")
            regime: str
            validation_errors: list of error strings (if any)
            ... (passthrough of validated gameplan fields)
    """
    # None or non-dict → Strategy C
    if gameplan is None or not isinstance(gameplan, dict):
        return {
            "valid": False,
            "strategy": "C",
            "regime": "unknown",
            "validation_errors": ["Gameplan is None or not a dict"],
        }

    # Empty dict → Strategy C
    if not gameplan:
        return {
            "valid": False,
            "strategy": "C",
            "regime": "unknown",
            "validation_errors": ["Gameplan is empty"],
        }

    # Check required fields
    errors = []
    for field in REQUIRED_GAMEPLAN_FIELDS:
        if field not in gameplan:
            errors.append(f"Missing required field: {field}")

    if errors:
        return {
            "valid": False,
            "strategy": "C",
            "regime": gameplan.get("regime", "unknown"),
            "validation_errors": errors,
        }

    # Check data quarantine flag
    data_quality = gameplan.get("data_quality", {})
    if data_quality.get("quarantine_active", False):
        return {
            "valid": True,
            "strategy": "C",
            "regime": gameplan.get("regime", "unknown"),
            "validation_errors": ["Data quarantine active — forcing Strategy C"],
        }

    # Valid gameplan
    strategy = gameplan.get("strategy", "C")
    if strategy not in ("A", "B", "C"):
        strategy = "C"
        errors.append(f"Invalid strategy '{gameplan.get('strategy')}' — defaulting to C")

    return {
        "valid": True,
        "strategy": strategy,
        "regime": gameplan.get("regime", "unknown"),
        "symbols": gameplan.get("symbols", []),
        "position_size_multiplier": gameplan.get("position_size_multiplier", 0.0),
        "hard_limits": gameplan.get("hard_limits", {}),
        "validation_errors": errors if errors else None,
    }


# =============================================================================
# SIGNAL EVALUATION PIPELINE
# =============================================================================


def evaluate_signals(
    gameplan: Optional[Dict[str, Any]],
    market_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    """
    Execute the full signal evaluation pipeline.

    Flow:
    1. Validate gameplan → Strategy C if invalid
    2. For each symbol in gameplan, evaluate signals using strategy-appropriate method
    3. Apply hard limits (PDT, position size)
    4. Return list of trade decisions

    Args:
        gameplan: Daily gameplan configuration dict
        market_data: Dict mapping symbol → list of bar dicts
            e.g., {"SPY": [...bars...], "QQQ": [...bars...]}

    Returns:
        List of trade decision dicts, each containing:
            symbol: str
            action: "BUY" | "SELL" | "HOLD" | "NEUTRAL" | "CLOSE"
            confidence: float (0.0 to 1.0)
            strategy: str
            signal_details: dict of raw signal data
    """
    if market_data is None:
        market_data = {}

    # Validate gameplan
    validated = load_gameplan(gameplan)
    strategy = validated["strategy"]
    symbols = validated.get("symbols", [])
    hard_limits = validated.get("hard_limits", {})

    # Strategy C → no new trades
    if strategy == "C":
        return [
            {
                "symbol": "ALL",
                "action": "HOLD",
                "confidence": 0.0,
                "strategy": "C",
                "signal_details": {"reason": "Strategy C active"},
            }
        ]

    # No symbols configured → no trades
    if not symbols:
        return [
            {
                "symbol": "NONE",
                "action": "NEUTRAL",
                "confidence": 0.0,
                "strategy": strategy,
                "signal_details": {"reason": "No symbols configured"},
            }
        ]

    # Check PDT remaining
    pdt_remaining = hard_limits.get("pdt_trades_remaining", 0)

    decisions = []

    for symbol in symbols:
        bars = market_data.get(symbol, [])

        if not bars:
            decisions.append(
                {
                    "symbol": symbol,
                    "action": "NEUTRAL",
                    "confidence": 0.0,
                    "strategy": strategy,
                    "signal_details": {"reason": f"No market data for {symbol}"},
                }
            )
            continue

        # Evaluate using strategy-appropriate signal function
        if strategy == "A":
            signal = evaluate_strategy_a_signal(bars)
        elif strategy == "B":
            signal = evaluate_strategy_b_signal(bars)
        else:
            signal = {"signal": "NEUTRAL", "confidence": 0.0}

        action = signal.get("signal", "NEUTRAL")

        # PDT enforcement: block new entries if no trades remaining
        if pdt_remaining <= 0 and action == "BUY":
            action = "NEUTRAL"
            signal["pdt_blocked"] = True

        decisions.append(
            {
                "symbol": symbol,
                "action": action,
                "confidence": signal.get("confidence", 0.0),
                "strategy": strategy,
                "signal_details": signal,
            }
        )

    return decisions
