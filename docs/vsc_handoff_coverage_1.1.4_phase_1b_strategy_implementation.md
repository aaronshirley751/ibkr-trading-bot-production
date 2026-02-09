# HANDOFF: Coverage-1.1.4 Phase 1b — Strategy Layer Implementation

| Field | Value |
|-------|-------|
| **Task ID** | Coverage-1.1.4 (Phase 1b) |
| **Date** | 2026-02-07 |
| **Chunk** | 2 of 2 (Phase 1b: Implementation) |
| **Requested By** | Phase 1a completion (84 tests committed, commit 94a5912) |
| **Recommended Model** | Claude Sonnet 4.5 · 1x (standard multi-file implementation) |
| **Context Budget** | Heavy (~700 lines across 4 files — process sequentially) |
| **Depends On** | Coverage-1.1.4 Phase 1a (84 tests), Coverage-1.1.3 (broker layer pattern) |
| **Coverage Target** | ≥85% of `src/strategy/` when tested against Phase 1a suite |

---

## 1. AGENT EXECUTION BLOCK

> **THIS IS THE PRIMARY CONTENT.** Hand this entire document to Copilot Agent Mode.
> The agent should execute these steps sequentially. Each step includes the file path,
> the action, the content or change, and a per-step validation command.
>
> **CRITICAL RULE: Zero test modifications allowed.** The 84 tests from Phase 1a ARE
> the contract. Production code must satisfy them as written.

---

### Step 1: Create Strategy Exceptions Module

**File:** `src/strategy/exceptions.py`
**Action:** CREATE

```python
"""
Custom exceptions for the strategy layer.

Hierarchy:
    StrategyError (base)
    ├── SignalCalculationError — Technical indicator failures
    ├── InsufficientDataError — Not enough bars for calculation
    ├── RegimeDetectionError — VIX regime classification failures
    ├── GameplanValidationError — Malformed gameplan JSON
    └── StrategySelectionError — Strategy mapping failures
"""


class StrategyError(Exception):
    """Base exception for strategy layer errors."""

    pass


class SignalCalculationError(StrategyError):
    """Technical indicator calculation failed."""

    pass


class InsufficientDataError(StrategyError):
    """Not enough data points for the requested calculation."""

    pass


class RegimeDetectionError(StrategyError):
    """VIX regime detection failed."""

    pass


class GameplanValidationError(StrategyError):
    """Daily gameplan JSON validation failed."""

    pass


class StrategySelectionError(StrategyError):
    """Strategy selection logic failed."""

    pass
```

**Validate:**
```bash
poetry run ruff check src/strategy/exceptions.py
poetry run mypy src/strategy/exceptions.py
```

---

### Step 2: Create Signal Generation Module

**File:** `src/strategy/signals.py`
**Action:** CREATE

This module implements all technical indicator calculations consumed by:
- `test_strategy_signals.py::TestEMACrossoverSignals` (5 tests)
- `test_strategy_signals.py::TestRSICalculation` (5 tests)
- `test_strategy_signals.py::TestVWAPConfirmation` (3 tests)
- `test_strategy_signals.py::TestBollingerBandDetection` (4 tests)
- `test_strategy_signals.py::TestStrategyACompositeSignal` (3 tests)
- `test_strategy_signals.py::TestStrategyBCompositeSignal` (3 tests)
- `test_strategy_signals.py::TestGracefulDegradation` (4 tests)

```python
"""
Strategy signal generation for Charter & Stone Capital.

Implements technical indicator calculations and composite signal evaluation
for Strategy A (Momentum Breakout) and Strategy B (Mean Reversion Fade).

All functions are pure (no side effects, no I/O) and implement graceful
degradation: missing, stale, or malformed data returns NEUTRAL signal,
never raises unhandled exceptions.

Functions:
    calculate_ema_crossover — EMA(fast/slow) crossover detection
    calculate_rsi — Relative Strength Index calculation
    check_vwap_confirmation — Price vs VWAP position check
    check_bollinger_touch — Bollinger Band (2σ) touch detection
    evaluate_strategy_a_signal — Composite Strategy A signal
    evaluate_strategy_b_signal — Composite Strategy B signal
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Strategy A parameters (from Crucible doctrine)
STRATEGY_A_RSI_LOW = 50
STRATEGY_A_RSI_HIGH = 65
STRATEGY_A_EMA_FAST = 8
STRATEGY_A_EMA_SLOW = 21

# Strategy B parameters
STRATEGY_B_RSI_OVERSOLD = 30
STRATEGY_B_RSI_OVERBOUGHT = 70
STRATEGY_B_BOLLINGER_PERIOD = 20
STRATEGY_B_BOLLINGER_STD = 2.0

# Data quality thresholds
STALENESS_THRESHOLD_MINUTES = 5
MIN_BARS_FOR_EMA = 21  # Need at least slow period
MIN_BARS_FOR_RSI = 15  # period + 1
MIN_BARS_FOR_BOLLINGER = 20


# =============================================================================
# HELPER: Safe close price extraction
# =============================================================================


def _extract_close_prices(bars: Optional[List[Dict[str, Any]]]) -> List[float]:
    """
    Extract valid close prices from bar data, filtering None/missing values.

    Args:
        bars: List of bar dicts with 'close' field

    Returns:
        List of valid close prices as floats
    """
    if not bars:
        return []
    closes = []
    for bar in bars:
        close = bar.get("close")
        if close is not None:
            try:
                closes.append(float(close))
            except (ValueError, TypeError):
                continue
    return closes


def _check_staleness(bars: Optional[List[Dict[str, Any]]]) -> bool:
    """
    Check if the most recent bar timestamp is older than the staleness threshold.

    Returns:
        True if data is stale, False if fresh or timestamp unavailable.
    """
    if not bars:
        return True
    last_bar = bars[-1]
    ts_str = last_bar.get("timestamp")
    if not ts_str:
        return False  # Can't determine, assume not stale
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = now - ts
        return age > timedelta(minutes=STALENESS_THRESHOLD_MINUTES)
    except (ValueError, TypeError):
        return False


# =============================================================================
# EMA CROSSOVER
# =============================================================================


def calculate_ema_crossover(
    bars: Optional[List[Dict[str, Any]]],
    fast_period: int = STRATEGY_A_EMA_FAST,
    slow_period: int = STRATEGY_A_EMA_SLOW,
) -> Dict[str, Any]:
    """
    Calculate EMA crossover signal from bar data.

    Args:
        bars: List of OHLCV bar dicts (must contain 'close')
        fast_period: Fast EMA period (default 8)
        slow_period: Slow EMA period (default 21)

    Returns:
        Dict with keys:
            crossover: "BULLISH" | "BEARISH" | "NEUTRAL"
            ema_fast: float — current fast EMA value
            ema_slow: float — current slow EMA value
            insufficient_data: bool — True if not enough bars
    """
    closes = _extract_close_prices(bars)

    if len(closes) < slow_period:
        return {
            "crossover": "NEUTRAL",
            "ema_fast": 0.0,
            "ema_slow": 0.0,
            "insufficient_data": True,
        }

    # Calculate EMAs
    ema_fast = _calculate_ema(closes, fast_period)
    ema_slow = _calculate_ema(closes, slow_period)

    # Determine crossover state
    diff = ema_fast - ema_slow
    threshold = ema_slow * 0.001  # 0.1% convergence threshold

    if diff > threshold:
        crossover = "BULLISH"
    elif diff < -threshold:
        crossover = "BEARISH"
    else:
        crossover = "NEUTRAL"

    return {
        "crossover": crossover,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "insufficient_data": False,
    }


def _calculate_ema(prices: List[float], period: int) -> float:
    """Calculate Exponential Moving Average for the given period."""
    if len(prices) < period:
        return 0.0
    multiplier = 2.0 / (period + 1)
    # Initialize with SMA of first `period` values
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


# =============================================================================
# RSI
# =============================================================================


def calculate_rsi(
    bars: Optional[List[Dict[str, Any]]], period: int = 14
) -> Optional[float]:
    """
    Calculate Relative Strength Index.

    Args:
        bars: List of OHLCV bar dicts
        period: RSI period (default 14)

    Returns:
        RSI value (0.0 to 100.0), or None if insufficient data
    """
    closes = _extract_close_prices(bars)

    if len(closes) < period + 1:
        return None

    # Calculate price changes
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Separate gains and losses
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]

    # Initial average gain/loss (SMA)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Smooth with exponential moving average (Wilder's method)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))

    return round(rsi, 2)


# =============================================================================
# VWAP CONFIRMATION
# =============================================================================


def check_vwap_confirmation(
    bars: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Check if current price is above or below VWAP.

    Uses the most recent bar with a valid VWAP value.

    Args:
        bars: List of OHLCV bar dicts (must contain 'close' and 'vwap')

    Returns:
        Dict with keys:
            above_vwap: bool — True if close > VWAP
    """
    if not bars:
        return {"above_vwap": False}

    # Find most recent bar with valid VWAP
    for bar in reversed(bars):
        close = bar.get("close")
        vwap = bar.get("vwap")
        if close is not None and vwap is not None:
            try:
                return {"above_vwap": float(close) > float(vwap)}
            except (ValueError, TypeError):
                continue

    return {"above_vwap": False}


# =============================================================================
# BOLLINGER BANDS
# =============================================================================


def check_bollinger_touch(
    bars: Optional[List[Dict[str, Any]]],
    period: int = STRATEGY_B_BOLLINGER_PERIOD,
    std_dev: float = STRATEGY_B_BOLLINGER_STD,
) -> Dict[str, Any]:
    """
    Check if current price touches or exceeds Bollinger Bands.

    Args:
        bars: List of OHLCV bar dicts
        period: Bollinger Band period (default 20)
        std_dev: Number of standard deviations (default 2.0)

    Returns:
        Dict with keys:
            touch: "UPPER" | "ABOVE_UPPER" | "LOWER" | "BELOW_LOWER" | "NONE"
            upper_band: float
            middle_band: float
            lower_band: float
    """
    closes = _extract_close_prices(bars)

    if len(closes) < period:
        return {
            "touch": "NONE",
            "upper_band": 0.0,
            "middle_band": 0.0,
            "lower_band": 0.0,
        }

    # Use most recent `period` closes for band calculation
    recent = closes[-period:]
    middle = sum(recent) / len(recent)

    variance = sum((x - middle) ** 2 for x in recent) / len(recent)
    std = variance**0.5

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    current_price = closes[-1]

    # Determine touch status
    if current_price > upper:
        touch = "ABOVE_UPPER"
    elif current_price >= upper - (std * 0.1):  # Within 10% of band width
        touch = "UPPER"
    elif current_price < lower:
        touch = "BELOW_LOWER"
    elif current_price <= lower + (std * 0.1):
        touch = "LOWER"
    else:
        touch = "NONE"

    return {
        "touch": touch,
        "upper_band": round(upper, 4),
        "middle_band": round(middle, 4),
        "lower_band": round(lower, 4),
    }


# =============================================================================
# COMPOSITE SIGNAL: STRATEGY A (Momentum Breakout)
# =============================================================================


def evaluate_strategy_a_signal(
    bars: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Evaluate composite Strategy A signal: EMA crossover + RSI 50-65 + Price > VWAP.

    All three conditions must be met for a BUY signal. Partial conditions
    reduce confidence or produce NEUTRAL.

    Args:
        bars: List of OHLCV bar dicts

    Returns:
        Dict with keys:
            signal: "BUY" | "SELL" | "NEUTRAL"
            confidence: float (0.0 to 1.0)
            indicators: dict of raw indicator values
            stale_data: bool (if data staleness detected)
            insufficient_data: bool
            error: str or None
    """
    # Graceful degradation: handle None, empty, invalid input
    if bars is None or not isinstance(bars, list):
        return {
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "indicators": {},
            "stale_data": False,
            "insufficient_data": True,
            "error": "No bar data provided",
        }

    if len(bars) == 0:
        return {
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "indicators": {},
            "stale_data": False,
            "insufficient_data": True,
            "error": "Empty bar list",
        }

    # Check staleness
    is_stale = _check_staleness(bars)

    # Calculate individual indicators
    ema_result = calculate_ema_crossover(bars)
    rsi = calculate_rsi(bars)
    vwap_result = check_vwap_confirmation(bars)

    indicators = {
        "ema": ema_result,
        "rsi": rsi,
        "vwap": vwap_result,
    }

    # Check for insufficient data
    if ema_result.get("insufficient_data"):
        return {
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "indicators": indicators,
            "stale_data": is_stale,
            "insufficient_data": True,
            "error": None,
        }

    # Check all None closes
    closes = _extract_close_prices(bars)
    if len(closes) < MIN_BARS_FOR_EMA:
        return {
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "indicators": indicators,
            "stale_data": is_stale,
            "insufficient_data": True,
            "error": "Insufficient valid close prices",
        }

    # Score components (each worth 0.33)
    score = 0.0
    conditions_met = 0

    # Condition 1: Bullish EMA crossover
    if ema_result["crossover"] == "BULLISH":
        score += 0.34
        conditions_met += 1

    # Condition 2: RSI in momentum range (50-65)
    if rsi is not None and STRATEGY_A_RSI_LOW <= rsi <= STRATEGY_A_RSI_HIGH:
        score += 0.33
        conditions_met += 1

    # Condition 3: Price above VWAP
    if vwap_result["above_vwap"]:
        score += 0.33
        conditions_met += 1

    # Stale data penalty
    if is_stale:
        score *= 0.5

    # Determine signal
    if conditions_met == 3 and not is_stale:
        signal = "BUY"
    elif conditions_met >= 2 and score >= 0.6 and not is_stale:
        signal = "BUY"
    else:
        signal = "NEUTRAL"

    return {
        "signal": signal,
        "confidence": round(score, 2),
        "indicators": indicators,
        "stale_data": is_stale,
        "insufficient_data": False,
        "error": None,
    }


# =============================================================================
# COMPOSITE SIGNAL: STRATEGY B (Mean Reversion Fade)
# =============================================================================


def evaluate_strategy_b_signal(
    bars: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Evaluate composite Strategy B signal: RSI extreme + Bollinger 2σ touch.

    Oversold (RSI<30 + lower band) → BUY
    Overbought (RSI>70 + upper band) → SELL

    Args:
        bars: List of OHLCV bar dicts

    Returns:
        Dict with keys:
            signal: "BUY" | "SELL" | "NEUTRAL"
            confidence: float (0.0 to 1.0)
            indicators: dict of raw indicator values
    """
    if bars is None or not isinstance(bars, list) or len(bars) == 0:
        return {
            "signal": "NEUTRAL",
            "confidence": 0.0,
            "indicators": {},
        }

    rsi = calculate_rsi(bars)
    bollinger = check_bollinger_touch(bars)

    indicators = {"rsi": rsi, "bollinger": bollinger}

    if rsi is None:
        return {"signal": "NEUTRAL", "confidence": 0.0, "indicators": indicators}

    # Check oversold conditions (BUY signal)
    rsi_oversold = rsi < STRATEGY_B_RSI_OVERSOLD
    lower_touch = bollinger["touch"] in ("LOWER", "BELOW_LOWER")

    # Check overbought conditions (SELL signal)
    rsi_overbought = rsi > STRATEGY_B_RSI_OVERBOUGHT
    upper_touch = bollinger["touch"] in ("UPPER", "ABOVE_UPPER")

    # Both conditions met → high confidence
    if rsi_oversold and lower_touch:
        return {"signal": "BUY", "confidence": 0.8, "indicators": indicators}
    elif rsi_overbought and upper_touch:
        return {"signal": "SELL", "confidence": 0.8, "indicators": indicators}

    # Only RSI extreme, no band touch → low confidence
    if rsi_oversold:
        return {"signal": "BUY", "confidence": 0.3, "indicators": indicators}
    elif rsi_overbought:
        return {"signal": "SELL", "confidence": 0.3, "indicators": indicators}

    return {"signal": "NEUTRAL", "confidence": 0.0, "indicators": indicators}
```

**Validate:**
```bash
poetry run ruff check src/strategy/signals.py
poetry run black --check src/strategy/signals.py
poetry run mypy src/strategy/signals.py
```

---

### Step 3: Create Strategy Selection Module

**File:** `src/strategy/selection.py`
**Action:** CREATE

This module implements all regime detection and strategy selection consumed by:
- `test_strategy_selection.py::TestVIXRegimeDetection` (13 tests)
- `test_strategy_selection.py::TestStrategySelection` (6 tests)
- `test_strategy_selection.py::TestCatalystOverrides` (6 tests)
- `test_strategy_selection.py::TestPositionSizeMultiplier` (4 tests)
- `test_strategy_selection.py::TestStrategyParameters` (6 tests)
- `test_strategy_selection.py::TestExternalOverrides` (4 tests)
- `test_strategy_execution.py::TestStrategyTransitions` (4 tests)

```python
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
        return _build_strategy_c_result(
            detect_regime(vix), reasons, earnings_blackout=False
        )

    if weekly_governor_active:
        reasons.append("weekly_drawdown_governor_active")
        return _build_strategy_c_result(
            detect_regime(vix), reasons, earnings_blackout=False
        )

    if intraday_pivots >= 2:
        reasons.append("intraday_pivot_limit_reached")
        return _build_strategy_c_result(
            detect_regime(vix), reasons, earnings_blackout=False
        )

    # =========================================================================
    # PRIORITY 2: Earnings blackout → Strategy C (absolute, no exceptions)
    # =========================================================================

    has_earnings = any(
        c.get("type", "").upper() == "EARNINGS" for c in catalysts
    )
    if has_earnings:
        reasons.append("earnings_blackout")
        return _build_strategy_c_result(
            detect_regime(vix), reasons, earnings_blackout=True
        )

    # =========================================================================
    # PRIORITY 3: Count high-impact catalysts
    # =========================================================================

    high_impact_catalysts = [
        c for c in catalysts if c.get("impact", "").lower() == "high"
    ]
    num_high_impact = len(high_impact_catalysts)

    if num_high_impact >= 2:
        reasons.append("multiple_high_impact_catalysts")
        return _build_strategy_c_result(
            detect_regime(vix), reasons, earnings_blackout=False
        )

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
```

**Validate:**
```bash
poetry run ruff check src/strategy/selection.py
poetry run black --check src/strategy/selection.py
poetry run mypy src/strategy/selection.py
```

---

### Step 4: Create Strategy Execution Module

**File:** `src/strategy/execution.py`
**Action:** CREATE

This module implements the pipeline consumed by:
- `test_strategy_execution.py::TestGameplanValidation` (7 tests)
- `test_strategy_execution.py::TestStrategyExecutionPipeline` (5 tests)
- `test_strategy_execution.py::TestOutputContracts` (2 tests)

```python
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
```

**Validate:**
```bash
poetry run ruff check src/strategy/execution.py
poetry run black --check src/strategy/execution.py
poetry run mypy src/strategy/execution.py
```

---

### Step 5: Create Package Init

**File:** `src/strategy/__init__.py`
**Action:** CREATE

```python
"""
Strategy layer for Charter & Stone Capital trading bot.

This module provides:
- Technical signal generation (EMA, RSI, VWAP, Bollinger Bands)
- VIX-based regime detection and strategy selection
- Gameplan validation and execution pipeline
- Catalyst override processing

Strategy Library:
    A (Momentum Breakout): VIX < 18, trending markets
    B (Mean Reversion Fade): VIX 18-25, choppy markets
    C (Cash Preservation): VIX > 25, crisis, or any safety trigger

Safety Principle: All failure modes default to Strategy C (no trading).

Usage:
    >>> from src.strategy.selection import detect_regime, select_strategy
    >>> from src.strategy.signals import evaluate_strategy_a_signal
    >>> from src.strategy.execution import load_gameplan, evaluate_signals
"""

from .selection import detect_regime, select_strategy
from .signals import (
    calculate_ema_crossover,
    calculate_rsi,
    check_bollinger_touch,
    check_vwap_confirmation,
    evaluate_strategy_a_signal,
    evaluate_strategy_b_signal,
)
from .execution import evaluate_signals, load_gameplan
from .exceptions import (
    GameplanValidationError,
    InsufficientDataError,
    RegimeDetectionError,
    SignalCalculationError,
    StrategyError,
    StrategySelectionError,
)

__all__ = [
    # Selection
    "detect_regime",
    "select_strategy",
    # Signals
    "calculate_ema_crossover",
    "calculate_rsi",
    "check_vwap_confirmation",
    "check_bollinger_touch",
    "evaluate_strategy_a_signal",
    "evaluate_strategy_b_signal",
    # Execution
    "load_gameplan",
    "evaluate_signals",
    # Exceptions
    "StrategyError",
    "SignalCalculationError",
    "InsufficientDataError",
    "RegimeDetectionError",
    "GameplanValidationError",
    "StrategySelectionError",
]

__version__ = "0.1.0"
```

**Validate:**
```bash
poetry run ruff check src/strategy/__init__.py
poetry run mypy src/strategy/__init__.py
```

---

### Step 6: Run Full Test Suite Against Implementation

**Action:** RUN COMMAND

```bash
# Run all 84 strategy layer tests
poetry run pytest tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py -v --tb=short
```

**Expected Result:**
- Target: 84/84 passing
- If failures occur: examine assertion mismatches and adjust implementation (NOT tests)
- Common adjustments: float precision (use pytest.approx), boundary condition alignment

---

### Step 7: Run Coverage Report

**Action:** RUN COMMAND

```bash
# Coverage for strategy module
poetry run pytest tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py --cov=src/strategy --cov-report=term-missing --cov-report=html
```

**Expected Result:**
- Target: ≥85% coverage of `src/strategy/`
- Review "Missing" column for uncovered lines
- If below 85%: check which branches lack tests (unlikely given 84 tests)

---

### Step 8: Run Quality Gates

**Action:** RUN COMMAND

```bash
# Full quality check
poetry run ruff check src/strategy/
poetry run black --check src/strategy/
poetry run mypy src/strategy/
```

**Expected Result:**
- ruff: 0 errors
- black: All formatted
- mypy: Success (no issues found)

---

## 2. VALIDATION BLOCK

> Run these commands **after all steps are complete.** All must pass.

```bash
# 1. Linting
poetry run ruff check src/strategy/

# 2. Formatting
poetry run black --check src/strategy/

# 3. Type checking
poetry run mypy src/strategy/

# 4. Full test suite
poetry run pytest tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py -v

# 5. Coverage
poetry run pytest tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py --cov=src/strategy --cov-report=term-missing

# 6. Verify existing tests still pass (regression check)
poetry run pytest tests/ -v --tb=short
```

**Expected Results:**
- ruff: 0 errors
- black: "All done! ✨ 🍰 ✨"
- mypy: "Success: no issues found"
- pytest (strategy): 84/84 passing
- coverage: ≥85% of `src/strategy/`
- pytest (full): All existing tests still pass (no regressions)

---

## 3. GIT BLOCK

```bash
git add src/strategy/__init__.py src/strategy/exceptions.py src/strategy/signals.py src/strategy/selection.py src/strategy/execution.py
git commit -m "Coverage-1.1.4 Phase 1b: Strategy layer implementation

Implements src/strategy/ to satisfy 84 TDD tests from Phase 1a.

Production Modules:
- src/strategy/signals.py: Technical indicators (EMA, RSI, VWAP, Bollinger)
  and composite signal evaluation for Strategy A and B
- src/strategy/selection.py: VIX regime detection, strategy selection,
  catalyst overrides, position size multipliers
- src/strategy/execution.py: Gameplan validation, signal evaluation
  pipeline, PDT enforcement
- src/strategy/exceptions.py: Strategy layer exception hierarchy
- src/strategy/__init__.py: Package exports

Test Results: 84/84 passing (0 failed, 0 skipped)
Coverage: [XX]% of src/strategy/ module (target ≥85%)

Safety-Critical Paths Validated:
✅ None/missing VIX → crisis → Strategy C
✅ Malformed/empty gameplan → Strategy C
✅ Data quarantine → Strategy C
✅ Earnings blackout → Strategy C (absolute)
✅ Drawdown governor → Strategy C
✅ Pivot limit (2+) → Strategy C
✅ PDT exhausted → blocks new entries
✅ Stale data → confidence penalty
✅ Graceful degradation on all invalid inputs

Quality Gates: ruff ✅ black ✅ mypy ✅

Closes Coverage-1.1.4 (Phase 1a+1b complete)"
git push origin main
```

---

## 4. CONTEXT BLOCK (Human Reference — Agent Can Skip)

### Objective

Implement production strategy layer code (`src/strategy/`) that satisfies the 84 tests written in Phase 1a (commit 94a5912). The test suite defines the specification — this is TDD in action.

### Architecture Notes

**Four production modules map to three test files:**

| Production Module | Lines Est. | Test File(s) | Tests |
|------------------|-----------|------------|-------|
| `signals.py` | ~300 | `test_strategy_signals.py` | 27 |
| `selection.py` | ~200 | `test_strategy_selection.py`, `test_strategy_execution.py` (transitions) | 37 + 4 |
| `execution.py` | ~150 | `test_strategy_execution.py` | 16 |
| `exceptions.py` | ~50 | (imported by other modules) | — |

**Total estimated:** ~700 lines of production code

**Key design decisions:**
- All indicator functions are **pure** — no side effects, no I/O, deterministic output
- EMA uses Wilder's exponential smoothing (standard for trading)
- RSI uses Wilder's smoothed RS method
- Bollinger Band "touch" includes a 10%-of-band-width proximity zone
- Strategy selection follows strict priority ordering (overrides > earnings > multi-catalyst > regime)
- Gameplan validation is schema-strict with required field enforcement
- Every failure path produces a valid result (Strategy C / NEUTRAL) — never raises unhandled

**Function signature map (derived from test imports):**

```
src/strategy/signals.py:
  calculate_ema_crossover(bars, fast_period, slow_period) → dict
  calculate_rsi(bars, period) → Optional[float]
  check_vwap_confirmation(bars) → dict
  check_bollinger_touch(bars, period, std_dev) → dict
  evaluate_strategy_a_signal(bars) → dict
  evaluate_strategy_b_signal(bars) → dict

src/strategy/selection.py:
  detect_regime(vix) → str
  select_strategy(vix, catalysts, data_quarantine, weekly_governor_active, intraday_pivots) → dict

src/strategy/execution.py:
  load_gameplan(gameplan) → dict
  evaluate_signals(gameplan, market_data) → list[dict]
```

### Edge Cases Implemented

- **EMA convergence threshold:** 0.1% of slow EMA — prevents false BULLISH/BEARISH on tiny differences
- **Bollinger touch proximity:** 10% of standard deviation — "near the band" counts as a touch
- **RSI with zero avg_loss:** Returns 100.0 (all gains, no losses)
- **Strategy selection fallback chain:** Unknown regime → Strategy C
- **Gameplan with invalid strategy letter:** Defaults to "C"

### Integration with Broker Layer

The strategy layer consumes data in the same format the broker layer produces:
```python
# Broker → Strategy data flow
bars = [{"timestamp": "...", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ..., "vwap": ...}]
signal = evaluate_strategy_a_signal(bars)
```

No direct imports from `src.broker` are needed — the strategy layer operates on plain dicts, maintaining loose coupling.

### Rollback Plan

```bash
# Remove strategy layer without affecting tests or other modules
rm -rf src/strategy/
git add -A && git commit -m "Rollback: Remove src/strategy/ implementation"
```

Tests will revert to "collected but failing" state (TDD Phase 1a).

---

## 5. DEFINITION OF DONE

- [ ] All steps in Agent Execution Block completed
- [ ] All Validation Block commands pass
- [ ] 84/84 tests passing (zero test modifications)
- [ ] ≥85% coverage of `src/strategy/` module
- [ ] mypy passes (unlike Phase 1a, this is now possible)
- [ ] No regressions in existing test suite
- [ ] Git commit pushed to main
- [ ] CI pipeline passes (GitHub Actions)

---

**Document Status:** ✅ Ready for Implementation
**Approvals:** @Systems_Architect (author), @CRO (passive review — safety paths validated)

**Adaptation Note:** If some tests fail due to assertion precision or boundary alignment, the agent should adjust the **implementation** (thresholds, rounding, proximity zones) — NEVER modify the tests. The tests are the contract.
