"""
VIX-based strategy selection for Charter & Stone Capital.

Implements:
- VIX regime detection with defined boundaries
- Strategy A/B/C mapping based on regime
- Catalyst-driven overrides (FOMC, CPI, earnings blackout)
- External override processing (data quarantine, drawdown governor, pivot limit)
- Position size multiplier calculation
- Strategy parameter packaging

Regime Boundaries (from Crucible v4.0 doctrine):
    VIX < 15       → complacency (Strategy A)
    VIX 15-17.99   → normal (Strategy A)
    VIX 18-24.99   → elevated (Strategy B)
    VIX >= 25      → high_volatility/crisis (Strategy C)

Safety Principle: When in doubt, deploy Strategy C. Fail safe, not fail open.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# STRATEGY PARAMETER DEFINITIONS (from Crucible doctrine)
# =============================================================================

STRATEGY_A_PARAMS = {
    "max_risk_pct": 0.03,
    "max_position_pct": 0.20,
    "take_profit_pct": 0.15,
    "stop_loss_pct": 0.25,
    "time_stop_minutes": 90,
    "min_dte": 2,
    "moneyness": "ATM",
}

STRATEGY_B_PARAMS = {
    "max_risk_pct": 0.02,
    "max_position_pct": 0.10,
    "take_profit_pct": 0.08,
    "stop_loss_pct": 0.15,
    "time_stop_minutes": 45,
    "min_dte": 5,
    "moneyness": "1_OTM",
}

STRATEGY_C_PARAMS = {
    "max_risk_pct": 0.0,
    "max_position_pct": 0.0,
    "take_profit_pct": 0.0,
    "stop_loss_pct": 0.0,
    "time_stop_minutes": 0,
    "min_dte": 0,
    "moneyness": "NONE",
}

# VIX regime boundaries
VIX_COMPLACENCY_UPPER = 15.0
VIX_NORMAL_UPPER = 18.0
VIX_ELEVATED_UPPER = 25.0


# =============================================================================
# REGIME DETECTION
# =============================================================================


def detect_regime(vix: Optional[float]) -> str:
    """
    Map VIX level to market regime.

    Args:
        vix: Current VIX level. None triggers crisis (fail safe).

    Returns:
        One of: "complacency", "normal", "elevated", "crisis", "error"

    Boundaries:
        VIX < 0         → "error" or "crisis" (invalid)
        VIX < 15        → "complacency"
        15 <= VIX < 18  → "normal"
        18 <= VIX < 25  → "elevated"
        VIX >= 25       → "crisis"
        VIX is None     → "crisis" (SAFETY: fail safe)
    """
    # SAFETY: None VIX = data failure → crisis
    if vix is None:
        logger.warning("VIX is None — defaulting to crisis regime (fail safe)")
        return "crisis"

    try:
        vix_val = float(vix)
    except (ValueError, TypeError):
        logger.error(f"Invalid VIX value: {vix}")
        return "crisis"

    # Negative or zero VIX is invalid
    if vix_val < 0:
        logger.error(f"Negative VIX value: {vix_val}")
        return "error"

    if vix_val == 0:
        return "complacency"

    # Regime classification
    if vix_val < VIX_COMPLACENCY_UPPER:
        return "complacency"
    elif vix_val < VIX_NORMAL_UPPER:
        return "normal"
    elif vix_val < VIX_ELEVATED_UPPER:
        return "elevated"
    else:
        return "crisis"


# =============================================================================
# STRATEGY SELECTION
# =============================================================================


def select_strategy(
    vix: Optional[float],
    catalysts: Optional[List[Dict[str, Any]]] = None,
    data_quarantine: bool = False,
    weekly_governor_active: bool = False,
    intraday_pivots: int = 0,
) -> Dict[str, Any]:
    """
    Select trading strategy based on VIX regime, catalysts, and override conditions.

    Priority order (highest to lowest):
    1. External overrides (data quarantine, governor, pivot limit) → Strategy C
    2. Earnings blackout catalyst → Strategy C
    3. Multiple high-impact catalysts → Strategy C
    4. VIX regime → Strategy A, B, or C
    5. Single high-impact catalyst → reduce position size

    Args:
        vix: Current VIX level
        catalysts: List of catalyst dicts with 'type', 'impact', 'description'
        data_quarantine: True if data quality quarantine is active
        weekly_governor_active: True if 15% weekly drawdown governor triggered
        intraday_pivots: Number of intraday pivots already used (max 2)

    Returns:
        Dict with keys:
            strategy: "A" | "B" | "C"
            regime: str — detected VIX regime
            symbols: list of tradeable symbols
            position_size_multiplier: float (0.0 to 1.0)
            parameters: dict of strategy-specific parameters
            reasons: list of human-readable selection reasons
            earnings_blackout: bool (if earnings override active)
    """
    if catalysts is None:
        catalysts = []

    reasons = []

    # =========================================================================
    # PRIORITY 1: External overrides → Strategy C (absolute)
    # =========================================================================

    if data_quarantine:
        reasons.append("data_quarantine_active")
        return _build_strategy_c_result(detect_regime(vix), reasons, earnings_blackout=False)

    if weekly_governor_active:
        reasons.append("weekly_drawdown_governor_active")
        return _build_strategy_c_result(detect_regime(vix), reasons, earnings_blackout=False)

    if intraday_pivots >= 2:
        reasons.append("intraday_pivot_limit_reached")
        return _build_strategy_c_result(detect_regime(vix), reasons, earnings_blackout=False)

    # =========================================================================
    # PRIORITY 2: Earnings blackout → Strategy C (absolute, no exceptions)
    # =========================================================================

    has_earnings = any(c.get("type", "").upper() == "EARNINGS" for c in catalysts)
    if has_earnings:
        reasons.append("earnings_blackout")
        return _build_strategy_c_result(detect_regime(vix), reasons, earnings_blackout=True)

    # =========================================================================
    # PRIORITY 3: Count high-impact catalysts
    # =========================================================================

    high_impact_catalysts = [c for c in catalysts if c.get("impact", "").lower() == "high"]
    num_high_impact = len(high_impact_catalysts)

    if num_high_impact >= 2:
        reasons.append("multiple_high_impact_catalysts")
        return _build_strategy_c_result(detect_regime(vix), reasons, earnings_blackout=False)

    # =========================================================================
    # PRIORITY 4: VIX regime → Strategy selection
    # =========================================================================

    regime = detect_regime(vix)

    if regime in ("crisis", "high_volatility", "error"):
        reasons.append(f"regime_{regime}")
        return _build_strategy_c_result(regime, reasons, earnings_blackout=False)

    # =========================================================================
    # PRIORITY 5: Apply catalyst position size adjustments
    # =========================================================================

    if regime in ("complacency", "normal"):
        # Strategy A
        base_multiplier = 1.0
        if num_high_impact == 1:
            base_multiplier = 0.5
            reasons.append("high_impact_catalyst_size_reduction")

        return {
            "strategy": "A",
            "regime": regime,
            "symbols": ["SPY", "QQQ"],
            "position_size_multiplier": base_multiplier,
            "parameters": STRATEGY_A_PARAMS.copy(),
            "reasons": reasons,
            "earnings_blackout": False,
        }

    elif regime == "elevated":
        # Strategy B
        base_multiplier = 0.5
        if num_high_impact == 1:
            base_multiplier = 0.25
            reasons.append("high_impact_catalyst_size_reduction")

        return {
            "strategy": "B",
            "regime": regime,
            "symbols": ["SPY"],
            "position_size_multiplier": base_multiplier,
            "parameters": STRATEGY_B_PARAMS.copy(),
            "reasons": reasons,
            "earnings_blackout": False,
        }

    # Fallback: anything unexpected → Strategy C
    reasons.append("unknown_regime_fallback")
    return _build_strategy_c_result(regime, reasons, earnings_blackout=False)


# =============================================================================
# HELPER: Build Strategy C result
# =============================================================================


def _build_strategy_c_result(
    regime: str, reasons: List[str], earnings_blackout: bool
) -> Dict[str, Any]:
    """Build a standardized Strategy C result dict."""
    return {
        "strategy": "C",
        "regime": regime,
        "symbols": [],
        "position_size_multiplier": 0.0,
        "parameters": STRATEGY_C_PARAMS.copy(),
        "reasons": reasons,
        "earnings_blackout": earnings_blackout,
    }
