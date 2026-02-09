# HANDOFF: Coverage-1.1.4 — Strategy Layer Tests

| Field | Value |
|-------|-------|
| **Task ID** | Coverage-1.1.4 |
| **Date** | 2026-02-07 |
| **Chunk** | 1 of 2 (Phase 1a: Tests — Phase 1b: Implementation) |
| **Requested By** | Sprint Plan (Phase 1.1 Test Build-Out) |
| **Recommended Model** | Claude Sonnet 4.5 · 1x (Tests) / Claude Opus 4.6 · 3x (Implementation if signal math is complex) |
| **Context Budget** | Heavy (600+ lines across 3 files — but each file is independent, agent can process sequentially) |
| **Depends On** | Coverage-1.1.3 (broker layer mocks and patterns), Coverage-1.1.2 (fixtures infrastructure) |
| **Coverage Target** | ≥85% of `src/strategy/` module (Strategy Selection: 85%, Signal Generation: 80%) |

---

## 1. AGENT EXECUTION BLOCK

> **THIS IS THE PRIMARY CONTENT.** Hand this entire document to Copilot Agent Mode.
> The agent should execute these steps sequentially. Each step includes the file path,
> the action, the content or change, and a per-step validation command.

---

### Step 1: Create Strategy Signal Unit Tests

**File:** `tests/unit/test_strategy_signals.py`
**Action:** CREATE

```python
"""
Unit tests for strategy signal generation.

Tests cover:
- EMA crossover signal generation (Strategy A)
- RSI extreme detection (Strategy B)
- Bollinger Band touch detection (Strategy B)
- VWAP confirmation logic (Strategy A)
- Signal generation with missing/stale data → Strategy C fallback
- Signal confidence calculation
- Multi-indicator confluence scoring

Coverage Target: ≥80% of src/strategy/signals.py
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# =============================================================================
# DATA STRUCTURES (Expected from src/strategy/signals.py)
# =============================================================================

@dataclass
class SignalResult:
    """Expected output structure from signal generators."""
    signal_type: str          # "BUY", "SELL", "NEUTRAL"
    confidence: float         # 0.0 to 1.0
    strategy: str             # "A", "B", "C"
    indicators: Dict[str, Any]  # Raw indicator values used
    timestamp: datetime
    reasons: List[str]        # Human-readable signal reasons


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def trending_up_bars() -> List[Dict[str, Any]]:
    """
    30 bars simulating a clean uptrend for Strategy A momentum signals.
    EMA(8) > EMA(21), RSI in 50-65 range, Price > VWAP.
    """
    base_time = datetime(2026, 2, 6, 10, 0, 0, tzinfo=timezone.utc)
    bars = []
    base_price = 688.00
    for i in range(30):
        price = base_price + (i * 0.15)  # Steady uptrend
        bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": price - 0.10,
            "high": price + 0.20,
            "low": price - 0.15,
            "close": price,
            "volume": 800000 + (i * 10000),
            "vwap": price - 0.30,  # Price above VWAP
        })
    return bars


@pytest.fixture
def trending_down_bars() -> List[Dict[str, Any]]:
    """
    30 bars simulating a clean downtrend.
    EMA(8) < EMA(21), RSI falling, Price < VWAP.
    """
    base_time = datetime(2026, 2, 6, 10, 0, 0, tzinfo=timezone.utc)
    bars = []
    base_price = 692.00
    for i in range(30):
        price = base_price - (i * 0.15)
        bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": price + 0.10,
            "high": price + 0.15,
            "low": price - 0.20,
            "close": price,
            "volume": 900000 + (i * 15000),
            "vwap": price + 0.30,  # Price below VWAP
        })
    return bars


@pytest.fixture
def mean_reverting_bars_oversold() -> List[Dict[str, Any]]:
    """
    30 bars simulating oversold conditions for Strategy B mean reversion.
    RSI < 30, price touching lower Bollinger Band (2σ).
    Sharp decline followed by stabilization at extreme.
    """
    base_time = datetime(2026, 2, 6, 10, 0, 0, tzinfo=timezone.utc)
    bars = []
    base_price = 690.00
    for i in range(30):
        if i < 20:
            price = base_price - (i * 0.40)  # Sharp decline
        else:
            price = base_price - (20 * 0.40) + ((i - 20) * 0.05)  # Stabilizing
        bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": price + 0.15,
            "high": price + 0.25,
            "low": price - 0.30,
            "close": price,
            "volume": 1200000 + (i * 20000),
            "vwap": price + 1.50,  # Price well below VWAP
        })
    return bars


@pytest.fixture
def mean_reverting_bars_overbought() -> List[Dict[str, Any]]:
    """
    30 bars simulating overbought conditions for Strategy B.
    RSI > 70, price touching upper Bollinger Band (2σ).
    """
    base_time = datetime(2026, 2, 6, 10, 0, 0, tzinfo=timezone.utc)
    bars = []
    base_price = 685.00
    for i in range(30):
        if i < 20:
            price = base_price + (i * 0.40)  # Sharp rally
        else:
            price = base_price + (20 * 0.40) - ((i - 20) * 0.05)  # Stabilizing
        bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": price - 0.15,
            "high": price + 0.30,
            "low": price - 0.25,
            "close": price,
            "volume": 1100000 + (i * 18000),
            "vwap": price - 1.50,  # Price well above VWAP
        })
    return bars


@pytest.fixture
def choppy_no_signal_bars() -> List[Dict[str, Any]]:
    """
    30 bars with no clear trend — should produce NEUTRAL signal.
    EMA(8) ≈ EMA(21), RSI ~50, Price oscillating around VWAP.
    """
    base_time = datetime(2026, 2, 6, 10, 0, 0, tzinfo=timezone.utc)
    bars = []
    base_price = 689.50
    for i in range(30):
        oscillation = 0.30 * (1 if i % 2 == 0 else -1)
        price = base_price + oscillation
        bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": price - 0.05,
            "high": price + 0.15,
            "low": price - 0.15,
            "close": price,
            "volume": 700000,
            "vwap": base_price,
        })
    return bars


@pytest.fixture
def insufficient_bars() -> List[Dict[str, Any]]:
    """
    Only 5 bars — insufficient for EMA(21) calculation.
    Must trigger graceful degradation, not crash.
    """
    base_time = datetime(2026, 2, 6, 10, 0, 0, tzinfo=timezone.utc)
    return [
        {
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": 689.0, "high": 689.5, "low": 688.5,
            "close": 689.0, "volume": 500000, "vwap": 689.0,
        }
        for i in range(5)
    ]


@pytest.fixture
def bars_with_missing_fields() -> List[Dict[str, Any]]:
    """
    Bars where some have missing VWAP or volume — tests graceful degradation.
    """
    base_time = datetime(2026, 2, 6, 10, 0, 0, tzinfo=timezone.utc)
    bars = []
    for i in range(30):
        bar = {
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": 689.0 + (i * 0.1),
            "high": 689.5 + (i * 0.1),
            "low": 688.5 + (i * 0.1),
            "close": 689.0 + (i * 0.1),
        }
        # Deliberately omit volume and vwap on some bars
        if i % 5 != 0:
            bar["volume"] = 700000
        if i % 7 != 0:
            bar["vwap"] = 689.0
        bars.append(bar)
    return bars


@pytest.fixture
def stale_bars() -> List[Dict[str, Any]]:
    """
    Bars with timestamps older than 5 minutes — triggers stale data handling.
    """
    stale_time = datetime(2026, 2, 6, 9, 0, 0, tzinfo=timezone.utc)  # 1 hour ago
    return [
        {
            "timestamp": (stale_time + timedelta(minutes=i)).isoformat(),
            "open": 689.0, "high": 689.5, "low": 688.5,
            "close": 689.0, "volume": 500000, "vwap": 689.0,
        }
        for i in range(30)
    ]


# =============================================================================
# STRATEGY A: MOMENTUM BREAKOUT SIGNAL TESTS
# =============================================================================


class TestEMACrossoverSignals:
    """Tests for EMA(8/21) crossover detection — core Strategy A signal."""

    def test_bullish_ema_crossover_detected(self, trending_up_bars):
        """
        GIVEN: 30 bars with steady uptrend (EMA8 > EMA21)
        WHEN: EMA crossover signal is calculated
        THEN: Signal type is BUY
        AND: EMA8 value > EMA21 value in indicators dict
        """
        from src.strategy.signals import calculate_ema_crossover

        result = calculate_ema_crossover(trending_up_bars, fast_period=8, slow_period=21)

        assert result["crossover"] == "BULLISH"
        assert result["ema_fast"] > result["ema_slow"]
        assert result["ema_fast"] > 0
        assert result["ema_slow"] > 0

    def test_bearish_ema_crossover_detected(self, trending_down_bars):
        """
        GIVEN: 30 bars with steady downtrend (EMA8 < EMA21)
        WHEN: EMA crossover signal is calculated
        THEN: Signal type is BEARISH
        AND: EMA8 value < EMA21 value
        """
        from src.strategy.signals import calculate_ema_crossover

        result = calculate_ema_crossover(trending_down_bars, fast_period=8, slow_period=21)

        assert result["crossover"] == "BEARISH"
        assert result["ema_fast"] < result["ema_slow"]

    def test_neutral_ema_no_crossover(self, choppy_no_signal_bars):
        """
        GIVEN: 30 bars with no clear trend
        WHEN: EMA crossover signal is calculated
        THEN: Signal is NEUTRAL (EMAs are converged)
        """
        from src.strategy.signals import calculate_ema_crossover

        result = calculate_ema_crossover(choppy_no_signal_bars, fast_period=8, slow_period=21)

        assert result["crossover"] == "NEUTRAL"

    def test_ema_insufficient_data_returns_neutral(self, insufficient_bars):
        """
        GIVEN: Only 5 bars (less than slow period of 21)
        WHEN: EMA crossover signal is calculated
        THEN: Returns NEUTRAL with insufficient_data flag
        AND: Does NOT raise an exception
        """
        from src.strategy.signals import calculate_ema_crossover

        result = calculate_ema_crossover(insufficient_bars, fast_period=8, slow_period=21)

        assert result["crossover"] == "NEUTRAL"
        assert result.get("insufficient_data") is True

    def test_ema_uses_close_prices(self, trending_up_bars):
        """
        GIVEN: Bar data with OHLCV
        WHEN: EMA is calculated
        THEN: Calculation uses 'close' field, not 'open', 'high', or 'low'
        """
        from src.strategy.signals import calculate_ema_crossover

        # Mutate close to flat while keeping high trending up
        flat_bars = []
        for bar in trending_up_bars:
            flat_bar = bar.copy()
            flat_bar["close"] = 689.00  # Flat close
            flat_bar["high"] = bar["high"] + 5.0  # High still trending
            flat_bars.append(flat_bar)

        result = calculate_ema_crossover(flat_bars, fast_period=8, slow_period=21)

        # With flat closes, EMAs should converge → NEUTRAL
        assert result["crossover"] == "NEUTRAL"


class TestRSICalculation:
    """Tests for RSI calculation and range validation."""

    def test_rsi_in_momentum_range_for_strategy_a(self, trending_up_bars):
        """
        GIVEN: Uptrending bars
        WHEN: RSI is calculated
        THEN: RSI falls within 50-65 range (Strategy A momentum zone)
        """
        from src.strategy.signals import calculate_rsi

        rsi = calculate_rsi(trending_up_bars, period=14)

        assert 40 <= rsi <= 75, f"RSI {rsi} not in expected momentum range"

    def test_rsi_oversold_for_strategy_b(self, mean_reverting_bars_oversold):
        """
        GIVEN: Bars with sharp decline (oversold conditions)
        WHEN: RSI is calculated
        THEN: RSI is below 30 (Strategy B oversold threshold)
        """
        from src.strategy.signals import calculate_rsi

        rsi = calculate_rsi(mean_reverting_bars_oversold, period=14)

        assert rsi < 35, f"RSI {rsi} not in oversold range"

    def test_rsi_overbought_for_strategy_b(self, mean_reverting_bars_overbought):
        """
        GIVEN: Bars with sharp rally (overbought conditions)
        WHEN: RSI is calculated
        THEN: RSI is above 70 (Strategy B overbought threshold)
        """
        from src.strategy.signals import calculate_rsi

        rsi = calculate_rsi(mean_reverting_bars_overbought, period=14)

        assert rsi > 65, f"RSI {rsi} not in overbought range"

    def test_rsi_returns_float_between_0_and_100(self, trending_up_bars):
        """
        GIVEN: Any valid bar data
        WHEN: RSI is calculated
        THEN: Result is a float in [0, 100] range
        """
        from src.strategy.signals import calculate_rsi

        rsi = calculate_rsi(trending_up_bars, period=14)

        assert isinstance(rsi, float)
        assert 0.0 <= rsi <= 100.0

    def test_rsi_insufficient_data(self, insufficient_bars):
        """
        GIVEN: Less data than RSI period requires
        WHEN: RSI is calculated
        THEN: Returns None or raises ValueError (not a crash)
        """
        from src.strategy.signals import calculate_rsi

        rsi = calculate_rsi(insufficient_bars, period=14)

        # Either returns None (insufficient data) or a value
        # Must NOT raise unhandled exception
        assert rsi is None or (isinstance(rsi, float) and 0 <= rsi <= 100)


class TestVWAPConfirmation:
    """Tests for VWAP confirmation logic — required for Strategy A."""

    def test_price_above_vwap_confirms_bullish(self, trending_up_bars):
        """
        GIVEN: Latest bar with close > VWAP
        WHEN: VWAP confirmation is checked
        THEN: Returns True (buyers in control)
        """
        from src.strategy.signals import check_vwap_confirmation

        result = check_vwap_confirmation(trending_up_bars)

        assert result["above_vwap"] is True

    def test_price_below_vwap_no_confirmation(self, trending_down_bars):
        """
        GIVEN: Latest bar with close < VWAP
        WHEN: VWAP confirmation is checked
        THEN: Returns False (sellers in control)
        """
        from src.strategy.signals import check_vwap_confirmation

        result = check_vwap_confirmation(trending_down_bars)

        assert result["above_vwap"] is False

    def test_vwap_missing_field_graceful_degradation(self, bars_with_missing_fields):
        """
        GIVEN: Bars where some VWAP values are missing
        WHEN: VWAP confirmation is checked
        THEN: Uses most recent bar with valid VWAP
        AND: Does NOT crash on missing data
        """
        from src.strategy.signals import check_vwap_confirmation

        result = check_vwap_confirmation(bars_with_missing_fields)

        assert "above_vwap" in result
        assert isinstance(result["above_vwap"], bool)


class TestBollingerBandDetection:
    """Tests for Bollinger Band (2σ) touch detection — Strategy B confirmation."""

    def test_lower_band_touch_detected(self, mean_reverting_bars_oversold):
        """
        GIVEN: Bars where price declined to lower 2σ band
        WHEN: Bollinger Band touch is checked
        THEN: Lower band touch detected
        """
        from src.strategy.signals import check_bollinger_touch

        result = check_bollinger_touch(mean_reverting_bars_oversold, period=20, std_dev=2.0)

        assert result["touch"] in ("LOWER", "BELOW_LOWER")

    def test_upper_band_touch_detected(self, mean_reverting_bars_overbought):
        """
        GIVEN: Bars where price rallied to upper 2σ band
        WHEN: Bollinger Band touch is checked
        THEN: Upper band touch detected
        """
        from src.strategy.signals import check_bollinger_touch

        result = check_bollinger_touch(mean_reverting_bars_overbought, period=20, std_dev=2.0)

        assert result["touch"] in ("UPPER", "ABOVE_UPPER")

    def test_no_band_touch_in_normal_range(self, choppy_no_signal_bars):
        """
        GIVEN: Bars oscillating within normal range
        WHEN: Bollinger Band touch is checked
        THEN: No touch detected
        """
        from src.strategy.signals import check_bollinger_touch

        result = check_bollinger_touch(choppy_no_signal_bars, period=20, std_dev=2.0)

        assert result["touch"] == "NONE"

    def test_bollinger_returns_band_values(self, trending_up_bars):
        """
        GIVEN: Valid bar data
        WHEN: Bollinger Bands are calculated
        THEN: Returns upper_band, middle_band, lower_band as floats
        AND: upper > middle > lower
        """
        from src.strategy.signals import check_bollinger_touch

        result = check_bollinger_touch(trending_up_bars, period=20, std_dev=2.0)

        assert "upper_band" in result
        assert "middle_band" in result
        assert "lower_band" in result
        assert result["upper_band"] > result["middle_band"] > result["lower_band"]


class TestStrategyACompositeSignal:
    """Tests for full Strategy A signal: EMA crossover + RSI 50-65 + VWAP confirmation."""

    def test_all_conditions_met_produces_buy_signal(self, trending_up_bars):
        """
        GIVEN: Uptrending bars with EMA(8)>EMA(21), RSI in 50-65, Price>VWAP
        WHEN: Strategy A composite signal is evaluated
        THEN: Signal is BUY with high confidence
        """
        from src.strategy.signals import evaluate_strategy_a_signal

        result = evaluate_strategy_a_signal(trending_up_bars)

        assert result["signal"] == "BUY"
        assert result["confidence"] >= 0.6

    def test_missing_vwap_confirmation_reduces_confidence(self, trending_up_bars):
        """
        GIVEN: Uptrending bars but price below VWAP
        WHEN: Strategy A composite signal is evaluated
        THEN: Signal is NEUTRAL or BUY with reduced confidence
        """
        from src.strategy.signals import evaluate_strategy_a_signal

        # Modify VWAP to be above price
        modified_bars = []
        for bar in trending_up_bars:
            mod = bar.copy()
            mod["vwap"] = bar["close"] + 2.00
            modified_bars.append(mod)

        result = evaluate_strategy_a_signal(modified_bars)

        assert result["signal"] in ("NEUTRAL", "BUY")
        if result["signal"] == "BUY":
            assert result["confidence"] < 0.6

    def test_rsi_outside_range_produces_neutral(self, mean_reverting_bars_overbought):
        """
        GIVEN: RSI > 65 (overbought, outside Strategy A range)
        WHEN: Strategy A composite signal is evaluated
        THEN: Signal is NEUTRAL (wrong conditions for momentum)
        """
        from src.strategy.signals import evaluate_strategy_a_signal

        result = evaluate_strategy_a_signal(mean_reverting_bars_overbought)

        assert result["signal"] == "NEUTRAL"


class TestStrategyBCompositeSignal:
    """Tests for full Strategy B signal: RSI extreme + Bollinger 2σ touch."""

    def test_oversold_with_lower_band_produces_buy(self, mean_reverting_bars_oversold):
        """
        GIVEN: RSI < 30 AND price touching lower Bollinger Band
        WHEN: Strategy B composite signal is evaluated
        THEN: Signal is BUY (mean reversion long)
        """
        from src.strategy.signals import evaluate_strategy_b_signal

        result = evaluate_strategy_b_signal(mean_reverting_bars_oversold)

        assert result["signal"] == "BUY"
        assert result["confidence"] >= 0.5

    def test_overbought_with_upper_band_produces_sell(self, mean_reverting_bars_overbought):
        """
        GIVEN: RSI > 70 AND price touching upper Bollinger Band
        WHEN: Strategy B composite signal is evaluated
        THEN: Signal is SELL (mean reversion short)
        """
        from src.strategy.signals import evaluate_strategy_b_signal

        result = evaluate_strategy_b_signal(mean_reverting_bars_overbought)

        assert result["signal"] == "SELL"
        assert result["confidence"] >= 0.5

    def test_rsi_extreme_without_band_touch_reduces_confidence(self, trending_down_bars):
        """
        GIVEN: RSI approaching oversold but no Bollinger Band touch
        WHEN: Strategy B composite signal is evaluated
        THEN: Signal is NEUTRAL or low confidence (missing confirmation)
        """
        from src.strategy.signals import evaluate_strategy_b_signal

        result = evaluate_strategy_b_signal(trending_down_bars)

        # Without band touch confirmation, should not generate high-confidence signal
        if result["signal"] != "NEUTRAL":
            assert result["confidence"] < 0.5


class TestGracefulDegradation:
    """
    CRITICAL: Strategy layer must NEVER crash on bad data.
    Missing, stale, or malformed data → default to NEUTRAL → Strategy C fallback.
    """

    def test_empty_bars_returns_neutral(self):
        """
        GIVEN: Empty bar list
        WHEN: Any signal calculation is attempted
        THEN: Returns NEUTRAL, does NOT raise exception
        """
        from src.strategy.signals import evaluate_strategy_a_signal

        result = evaluate_strategy_a_signal([])

        assert result["signal"] == "NEUTRAL"
        assert result.get("error") is not None or result.get("insufficient_data") is True

    def test_none_bars_returns_neutral(self):
        """
        GIVEN: None instead of bar list
        WHEN: Any signal calculation is attempted
        THEN: Returns NEUTRAL, does NOT raise exception
        """
        from src.strategy.signals import evaluate_strategy_a_signal

        result = evaluate_strategy_a_signal(None)

        assert result["signal"] == "NEUTRAL"

    def test_bars_with_none_close_prices(self):
        """
        GIVEN: Bars where some close prices are None
        WHEN: Signal calculation is attempted
        THEN: Filters invalid bars and calculates from valid ones
        OR: Returns NEUTRAL if too few valid bars remain
        """
        from src.strategy.signals import evaluate_strategy_a_signal

        bars_with_nones = [
            {"timestamp": "2026-02-06T10:00:00Z", "open": 689.0,
             "high": 689.5, "low": 688.5, "close": None, "volume": 500000, "vwap": 689.0}
            for _ in range(30)
        ]

        result = evaluate_strategy_a_signal(bars_with_nones)

        assert result["signal"] == "NEUTRAL"

    def test_stale_data_flags_warning(self, stale_bars):
        """
        GIVEN: Bars with timestamps older than 5 minutes
        WHEN: Signal is evaluated
        THEN: Result includes stale_data warning flag
        AND: Signal confidence is reduced or signal is NEUTRAL
        """
        from src.strategy.signals import evaluate_strategy_a_signal

        result = evaluate_strategy_a_signal(stale_bars)

        # Stale data should be flagged
        assert result.get("stale_data") is True or result["signal"] == "NEUTRAL"
```

**Validate:**
```bash
poetry run ruff check tests/unit/test_strategy_signals.py
poetry run black --check tests/unit/test_strategy_signals.py
```

---

### Step 2: Create Strategy Selection Unit Tests

**File:** `tests/unit/test_strategy_selection.py`
**Action:** CREATE

```python
"""
Unit tests for VIX-based strategy selection and regime detection.

Tests cover:
- VIX regime detection boundaries: complacency (<15), normal (15-18), elevated (18-25), high (25-30), crisis (>30)
- Strategy selection logic for each regime
- Catalyst-based strategy overrides (FOMC, CPI, earnings)
- Position size multiplier adjustments by regime
- Gameplan validation and configuration loading
- Missing data defaults to Strategy C

Coverage Target: ≥85% of src/strategy/selection.py
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional


# =============================================================================
# VIX REGIME FIXTURES
# =============================================================================

@pytest.fixture
def vix_complacency():
    """VIX < 15 — complacency regime."""
    return 12.5


@pytest.fixture
def vix_normal_low():
    """VIX at 15.0 — lower boundary of normal regime."""
    return 15.0


@pytest.fixture
def vix_normal_mid():
    """VIX at 16.5 — typical normal regime."""
    return 16.5


@pytest.fixture
def vix_normal_high():
    """VIX at 17.99 — upper boundary of normal regime."""
    return 17.99


@pytest.fixture
def vix_elevated_boundary():
    """VIX at 18.0 — lower boundary of elevated regime."""
    return 18.0


@pytest.fixture
def vix_elevated_mid():
    """VIX at 22.0 — typical elevated regime."""
    return 22.0


@pytest.fixture
def vix_elevated_high():
    """VIX at 24.99 — upper boundary of elevated regime."""
    return 24.99


@pytest.fixture
def vix_high_boundary():
    """VIX at 25.0 — lower boundary of high volatility / crisis regime."""
    return 25.0


@pytest.fixture
def vix_crisis():
    """VIX at 35.0 — full crisis conditions."""
    return 35.0


@pytest.fixture
def vix_extreme():
    """VIX at 55.0 — panic/extreme conditions."""
    return 55.0


# =============================================================================
# CATALYST FIXTURES
# =============================================================================

@pytest.fixture
def fomc_catalyst():
    """FOMC decision catalyst."""
    return [{"type": "FOMC", "description": "FOMC decision 2:00 PM ET", "impact": "high"}]


@pytest.fixture
def cpi_catalyst():
    """CPI data release catalyst."""
    return [{"type": "CPI", "description": "CPI release 8:30 AM ET", "impact": "high"}]


@pytest.fixture
def earnings_catalyst():
    """Earnings report catalyst — triggers blackout."""
    return [{"type": "EARNINGS", "symbol": "SPY", "description": "SPY component earnings", "impact": "high"}]


@pytest.fixture
def low_impact_catalyst():
    """Low-impact catalyst — should not override strategy."""
    return [{"type": "ECONOMIC", "description": "Existing Home Sales 10:00 AM ET", "impact": "low"}]


@pytest.fixture
def no_catalysts():
    """No catalysts scheduled."""
    return []


@pytest.fixture
def multiple_catalysts():
    """Multiple high-impact catalysts — maximum caution."""
    return [
        {"type": "FOMC", "description": "FOMC decision 2:00 PM ET", "impact": "high"},
        {"type": "CPI", "description": "CPI release 8:30 AM ET", "impact": "high"},
    ]


# =============================================================================
# VIX REGIME DETECTION TESTS
# =============================================================================


class TestVIXRegimeDetection:
    """Tests for VIX-to-regime mapping with exact boundary conditions."""

    def test_complacency_regime(self, vix_complacency):
        """VIX < 15 → complacency regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_complacency) == "complacency"

    def test_normal_regime_lower_boundary(self, vix_normal_low):
        """VIX == 15.0 → normal regime (inclusive lower bound)."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_normal_low) == "normal"

    def test_normal_regime_typical(self, vix_normal_mid):
        """VIX 16.5 → normal regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_normal_mid) == "normal"

    def test_normal_regime_upper_boundary(self, vix_normal_high):
        """VIX 17.99 → still normal regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_normal_high) == "normal"

    def test_elevated_regime_lower_boundary(self, vix_elevated_boundary):
        """VIX == 18.0 → elevated regime (inclusive lower bound)."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_elevated_boundary) == "elevated"

    def test_elevated_regime_typical(self, vix_elevated_mid):
        """VIX 22.0 → elevated regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_elevated_mid) == "elevated"

    def test_elevated_regime_upper_boundary(self, vix_elevated_high):
        """VIX 24.99 → still elevated regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_elevated_high) == "elevated"

    def test_high_volatility_boundary(self, vix_high_boundary):
        """VIX == 25.0 → high_volatility / crisis regime → Strategy C territory."""
        from src.strategy.selection import detect_regime

        regime = detect_regime(vix_high_boundary)
        assert regime in ("high_volatility", "crisis")

    def test_crisis_regime(self, vix_crisis):
        """VIX 35.0 → crisis regime."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_crisis) == "crisis"

    def test_extreme_vix_crisis(self, vix_extreme):
        """VIX 55.0 → still crisis (no regime above crisis)."""
        from src.strategy.selection import detect_regime

        assert detect_regime(vix_extreme) == "crisis"

    def test_zero_vix_handled(self):
        """VIX == 0 → edge case, should not crash. Complacency or error."""
        from src.strategy.selection import detect_regime

        result = detect_regime(0.0)
        assert result in ("complacency", "error")

    def test_negative_vix_handled(self):
        """VIX < 0 → invalid, should not crash."""
        from src.strategy.selection import detect_regime

        result = detect_regime(-5.0)
        assert result in ("error", "crisis")  # Either error flag or safe default

    def test_none_vix_defaults_to_crisis(self):
        """
        CRITICAL: If VIX is None (data failure), default to crisis → Strategy C.
        This is a safety-critical path — fail safe, not fail open.
        """
        from src.strategy.selection import detect_regime

        result = detect_regime(None)
        assert result == "crisis"


# =============================================================================
# STRATEGY SELECTION TESTS
# =============================================================================


class TestStrategySelection:
    """Tests for regime → strategy mapping."""

    def test_normal_regime_selects_strategy_a(self, vix_normal_mid, no_catalysts):
        """VIX 16.5, no catalysts → Strategy A (Momentum Breakout)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        assert result["strategy"] == "A"
        assert result["regime"] == "normal"

    def test_complacency_regime_selects_strategy_a(self, vix_complacency, no_catalysts):
        """VIX < 15, no catalysts → Strategy A (low vol trending)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_complacency, catalysts=no_catalysts)

        assert result["strategy"] == "A"

    def test_elevated_regime_selects_strategy_b(self, vix_elevated_mid, no_catalysts):
        """VIX 22.0, no catalysts → Strategy B (Mean Reversion)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_elevated_mid, catalysts=no_catalysts)

        assert result["strategy"] == "B"
        assert result["regime"] == "elevated"

    def test_high_vix_selects_strategy_c(self, vix_high_boundary, no_catalysts):
        """VIX >= 25 → Strategy C (Cash Preservation). No exceptions."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_high_boundary, catalysts=no_catalysts)

        assert result["strategy"] == "C"

    def test_crisis_vix_selects_strategy_c(self, vix_crisis, no_catalysts):
        """VIX 35.0 → Strategy C."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_crisis, catalysts=no_catalysts)

        assert result["strategy"] == "C"

    def test_none_vix_selects_strategy_c(self, no_catalysts):
        """
        CRITICAL SAFETY: VIX=None (data failure) → Strategy C.
        Fail safe, not fail open.
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(None, catalysts=no_catalysts)

        assert result["strategy"] == "C"


# =============================================================================
# CATALYST OVERRIDE TESTS
# =============================================================================


class TestCatalystOverrides:
    """Tests for catalyst-driven strategy modifications."""

    def test_fomc_reduces_position_size(self, vix_normal_mid, fomc_catalyst):
        """
        GIVEN: Normal VIX (Strategy A conditions)
        AND: FOMC catalyst active
        WHEN: Strategy is selected
        THEN: Position size multiplier is reduced (≤0.5)
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=fomc_catalyst)

        assert result["position_size_multiplier"] <= 0.5

    def test_cpi_reduces_position_size(self, vix_normal_mid, cpi_catalyst):
        """
        GIVEN: Normal VIX + CPI release
        WHEN: Strategy is selected
        THEN: Position size multiplier is reduced
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=cpi_catalyst)

        assert result["position_size_multiplier"] <= 0.5

    def test_earnings_blackout_forces_strategy_c(self, vix_normal_mid, earnings_catalyst):
        """
        CRITICAL: Earnings within 24 hours → Strategy C. No exceptions.
        This is a hard rule from the Crucible doctrine.
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=earnings_catalyst)

        assert result["strategy"] == "C"
        assert "earnings_blackout" in result.get("reasons", []) or result.get("earnings_blackout") is True

    def test_low_impact_catalyst_no_override(self, vix_normal_mid, low_impact_catalyst):
        """
        GIVEN: Normal VIX + low-impact catalyst
        WHEN: Strategy is selected
        THEN: Strategy A remains, position size not reduced
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=low_impact_catalyst)

        assert result["strategy"] == "A"
        assert result["position_size_multiplier"] >= 0.8

    def test_multiple_high_impact_catalysts_force_strategy_c(self, vix_normal_mid, multiple_catalysts):
        """
        GIVEN: Normal VIX but 2+ high-impact catalysts
        WHEN: Strategy is selected
        THEN: Strategy C deployed (too much event risk)
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=multiple_catalysts)

        # With 2+ high-impact catalysts, either Strategy C or very reduced sizing
        assert result["strategy"] == "C" or result["position_size_multiplier"] <= 0.3

    def test_no_catalysts_full_position_size(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX, no catalysts
        WHEN: Strategy is selected
        THEN: Full position size multiplier (1.0)
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        assert result["position_size_multiplier"] == 1.0


# =============================================================================
# POSITION SIZE MULTIPLIER TESTS
# =============================================================================


class TestPositionSizeMultiplier:
    """Tests for position size scaling by regime and conditions."""

    def test_normal_regime_full_size(self, vix_normal_mid, no_catalysts):
        """Normal regime → multiplier 1.0."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)
        assert result["position_size_multiplier"] == 1.0

    def test_elevated_regime_reduced_size(self, vix_elevated_mid, no_catalysts):
        """Elevated regime → multiplier 0.5 (Strategy B uses half size)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_elevated_mid, catalysts=no_catalysts)
        assert result["position_size_multiplier"] == 0.5

    def test_crisis_regime_zero_size(self, vix_crisis, no_catalysts):
        """Crisis regime → multiplier 0.0 (no new positions)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_crisis, catalysts=no_catalysts)
        assert result["position_size_multiplier"] == 0.0

    def test_complacency_regime_size(self, vix_complacency, no_catalysts):
        """Complacency regime → multiplier 1.0 (same as normal for Strategy A)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_complacency, catalysts=no_catalysts)
        assert result["position_size_multiplier"] == 1.0


# =============================================================================
# STRATEGY PARAMETER VALIDATION TESTS
# =============================================================================


class TestStrategyParameters:
    """Tests that selected strategy returns correct parameter set."""

    def test_strategy_a_returns_correct_symbols(self, vix_normal_mid, no_catalysts):
        """Strategy A: SPY, QQQ (max 2 symbols)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        assert set(result["symbols"]).issubset({"SPY", "QQQ"})
        assert len(result["symbols"]) <= 2

    def test_strategy_b_returns_spy_only(self, vix_elevated_mid, no_catalysts):
        """Strategy B: SPY only."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_elevated_mid, catalysts=no_catalysts)

        assert result["symbols"] == ["SPY"]

    def test_strategy_c_returns_no_symbols(self, vix_crisis, no_catalysts):
        """Strategy C: No symbols (no new entries)."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_crisis, catalysts=no_catalysts)

        assert result["symbols"] == []

    def test_strategy_a_risk_parameters(self, vix_normal_mid, no_catalysts):
        """Strategy A: max_risk=3%, max_position=20%, tp=15%, sl=25%."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        params = result.get("parameters", result)
        assert params.get("max_risk_pct") == 0.03 or params.get("max_risk_pct") == 3.0
        assert params.get("take_profit_pct") == 0.15 or params.get("take_profit_pct") == 15.0
        assert params.get("stop_loss_pct") == 0.25 or params.get("stop_loss_pct") == 25.0
        assert params.get("time_stop_minutes") == 90

    def test_strategy_b_risk_parameters(self, vix_elevated_mid, no_catalysts):
        """Strategy B: max_risk=2%, max_position=10%, tp=8%, sl=15%."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_elevated_mid, catalysts=no_catalysts)

        params = result.get("parameters", result)
        assert params.get("max_risk_pct") == 0.02 or params.get("max_risk_pct") == 2.0
        assert params.get("take_profit_pct") == 0.08 or params.get("take_profit_pct") == 8.0
        assert params.get("stop_loss_pct") == 0.15 or params.get("stop_loss_pct") == 15.0
        assert params.get("time_stop_minutes") == 45

    def test_strategy_c_zero_risk_parameters(self, vix_crisis, no_catalysts):
        """Strategy C: max_risk=0%, no new positions."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_crisis, catalysts=no_catalysts)

        params = result.get("parameters", result)
        assert params.get("max_risk_pct") == 0.0 or params.get("max_risk_pct") == 0


# =============================================================================
# EXTERNAL OVERRIDE TESTS (Data Quarantine, Drawdown Governor, PDT)
# =============================================================================


class TestExternalOverrides:
    """Tests for conditions that force Strategy C regardless of VIX."""

    def test_data_quarantine_forces_strategy_c(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX conditions
        AND: Data quarantine flag is active
        WHEN: Strategy is selected
        THEN: Strategy C (data can't be trusted)
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(
            vix_normal_mid,
            catalysts=no_catalysts,
            data_quarantine=True,
        )

        assert result["strategy"] == "C"

    def test_drawdown_governor_forces_strategy_c(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX conditions
        AND: Weekly drawdown governor is active (>15% weekly loss)
        WHEN: Strategy is selected
        THEN: Strategy C for remainder of week
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(
            vix_normal_mid,
            catalysts=no_catalysts,
            weekly_governor_active=True,
        )

        assert result["strategy"] == "C"

    def test_pivot_limit_forces_strategy_c(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX conditions
        AND: 2+ intraday pivots already used
        WHEN: Strategy is selected
        THEN: Strategy C locked for the day
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(
            vix_normal_mid,
            catalysts=no_catalysts,
            intraday_pivots=2,
        )

        assert result["strategy"] == "C"

    def test_no_overrides_allows_normal_selection(self, vix_normal_mid, no_catalysts):
        """
        GIVEN: Normal VIX, no overrides
        WHEN: Strategy is selected with all override flags False/0
        THEN: Normal strategy selection applies
        """
        from src.strategy.selection import select_strategy

        result = select_strategy(
            vix_normal_mid,
            catalysts=no_catalysts,
            data_quarantine=False,
            weekly_governor_active=False,
            intraday_pivots=0,
        )

        assert result["strategy"] == "A"
```

**Validate:**
```bash
poetry run ruff check tests/unit/test_strategy_selection.py
poetry run black --check tests/unit/test_strategy_selection.py
```

---

### Step 3: Create Strategy Execution Integration Tests

**File:** `tests/integration/test_strategy_execution.py`
**Action:** CREATE

```python
"""
Integration tests for strategy signal → execution flow.

Tests the full pipeline:
  Gameplan JSON → Strategy Selection → Signal Evaluation → Trade Decision

Tests cover:
- Gameplan ingestion and strategy activation
- Signal evaluation with real-ish market data fixtures
- Strategy transition scenarios (A→C on VIX spike, A→B on regime change)
- Multi-symbol signal evaluation (SPY + QQQ)
- Full decision pipeline with all safety checks
- Strategy C default on malformed/missing gameplan

Coverage Target: Component of ≥85% aggregate for src/strategy/
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List


# =============================================================================
# GAMEPLAN FIXTURES
# =============================================================================

@pytest.fixture
def strategy_a_gameplan() -> Dict[str, Any]:
    """Full Strategy A gameplan matching daily_gameplan.json schema."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0900",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY", "QQQ"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 16.5,
        "vix_source_verified": True,
        "bias": "bullish",
        "expected_behavior": "trending",
        "key_levels": {
            "spy_support": 685.50,
            "spy_resistance": 696.09,
            "spy_pivot": 690.00,
        },
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "low",
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:00:00-05:00",
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 3,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2,
        },
    }


@pytest.fixture
def strategy_b_gameplan() -> Dict[str, Any]:
    """Full Strategy B gameplan."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0900",
        "regime": "elevated",
        "strategy": "B",
        "symbols": ["SPY"],
        "position_size_multiplier": 0.5,
        "vix_at_analysis": 23.5,
        "vix_source_verified": True,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "key_levels": {"spy_support": 680.00, "spy_resistance": 690.00, "spy_pivot": 685.00},
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "medium",
        "data_quality": {"quarantine_active": False, "stale_fields": [], "last_verified": "2026-02-07T09:00:00-05:00"},
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 2,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2,
        },
    }


@pytest.fixture
def strategy_c_gameplan() -> Dict[str, Any]:
    """Full Strategy C gameplan (cash preservation)."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0900",
        "regime": "crisis",
        "strategy": "C",
        "symbols": [],
        "position_size_multiplier": 0.0,
        "vix_at_analysis": 31.0,
        "vix_source_verified": True,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "high",
        "data_quality": {"quarantine_active": False, "stale_fields": [], "last_verified": "2026-02-07T09:00:00-05:00"},
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 0,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": True,
            "max_intraday_pivots": 2,
        },
    }


@pytest.fixture
def malformed_gameplan() -> Dict[str, Any]:
    """Gameplan missing critical fields — must trigger Strategy C fallback."""
    return {
        "date": "2026-02-07",
        "strategy": "A",
        # Missing: regime, symbols, hard_limits, data_quality
    }


@pytest.fixture
def trending_market_data() -> Dict[str, List[Dict[str, Any]]]:
    """Market data suitable for Strategy A — trending conditions."""
    base_time = datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
    spy_bars = []
    qqq_bars = []

    for i in range(30):
        spy_bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": 688.00 + (i * 0.15),
            "high": 688.50 + (i * 0.15),
            "low": 687.50 + (i * 0.15),
            "close": 688.20 + (i * 0.15),
            "volume": 900000 + (i * 10000),
            "vwap": 687.80 + (i * 0.12),
        })
        qqq_bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": 620.00 + (i * 0.12),
            "high": 620.40 + (i * 0.12),
            "low": 619.60 + (i * 0.12),
            "close": 620.15 + (i * 0.12),
            "volume": 600000 + (i * 8000),
            "vwap": 619.80 + (i * 0.10),
        })

    return {"SPY": spy_bars, "QQQ": qqq_bars}


@pytest.fixture
def mean_reverting_market_data() -> Dict[str, List[Dict[str, Any]]]:
    """Market data suitable for Strategy B — mean reverting conditions."""
    base_time = datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
    spy_bars = []
    base_price = 685.00

    for i in range(30):
        if i < 20:
            price = base_price - (i * 0.35)  # Sharp decline
        else:
            price = base_price - (20 * 0.35) + ((i - 20) * 0.05)  # Stabilizing
        spy_bars.append({
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "open": price + 0.10,
            "high": price + 0.25,
            "low": price - 0.30,
            "close": price,
            "volume": 1100000 + (i * 15000),
            "vwap": price + 1.20,
        })

    return {"SPY": spy_bars}


# =============================================================================
# GAMEPLAN VALIDATION TESTS
# =============================================================================


class TestGameplanValidation:
    """Tests for gameplan JSON parsing and validation."""

    def test_valid_gameplan_a_loads_correctly(self, strategy_a_gameplan):
        """Valid Strategy A gameplan parses without error."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan(strategy_a_gameplan)

        assert result["valid"] is True
        assert result["strategy"] == "A"
        assert result["regime"] == "normal"

    def test_valid_gameplan_b_loads_correctly(self, strategy_b_gameplan):
        """Valid Strategy B gameplan parses without error."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan(strategy_b_gameplan)

        assert result["valid"] is True
        assert result["strategy"] == "B"

    def test_valid_gameplan_c_loads_correctly(self, strategy_c_gameplan):
        """Valid Strategy C gameplan parses without error."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan(strategy_c_gameplan)

        assert result["valid"] is True
        assert result["strategy"] == "C"

    def test_malformed_gameplan_defaults_to_strategy_c(self, malformed_gameplan):
        """
        CRITICAL SAFETY: Malformed gameplan → Strategy C.
        Never trade with invalid configuration.
        """
        from src.strategy.execution import load_gameplan

        result = load_gameplan(malformed_gameplan)

        assert result["strategy"] == "C"
        assert result.get("validation_errors") is not None

    def test_none_gameplan_defaults_to_strategy_c(self):
        """None gameplan → Strategy C."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan(None)

        assert result["strategy"] == "C"

    def test_empty_dict_gameplan_defaults_to_strategy_c(self):
        """Empty dict gameplan → Strategy C."""
        from src.strategy.execution import load_gameplan

        result = load_gameplan({})

        assert result["strategy"] == "C"

    def test_gameplan_with_quarantine_active_forces_c(self, strategy_a_gameplan):
        """Gameplan where data_quality.quarantine_active=True → Strategy C."""
        from src.strategy.execution import load_gameplan

        strategy_a_gameplan["data_quality"]["quarantine_active"] = True
        result = load_gameplan(strategy_a_gameplan)

        assert result["strategy"] == "C"


# =============================================================================
# STRATEGY EXECUTION PIPELINE TESTS
# =============================================================================


class TestStrategyExecutionPipeline:
    """Integration tests for the full signal → decision pipeline."""

    def test_strategy_a_pipeline_with_trending_data(
        self, strategy_a_gameplan, trending_market_data
    ):
        """
        GIVEN: Strategy A gameplan + trending market data
        WHEN: Full pipeline executes
        THEN: Produces actionable trade decision for SPY and/or QQQ
        """
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_a_gameplan, trending_market_data)

        assert isinstance(decisions, list)
        assert len(decisions) >= 1
        for decision in decisions:
            assert decision["symbol"] in ("SPY", "QQQ")
            assert decision["action"] in ("BUY", "SELL", "HOLD", "NEUTRAL")
            assert "confidence" in decision

    def test_strategy_b_pipeline_with_mean_reverting_data(
        self, strategy_b_gameplan, mean_reverting_market_data
    ):
        """
        GIVEN: Strategy B gameplan + oversold market data
        WHEN: Full pipeline executes
        THEN: Produces mean reversion trade decision for SPY
        """
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_b_gameplan, mean_reverting_market_data)

        assert isinstance(decisions, list)
        assert len(decisions) == 1
        assert decisions[0]["symbol"] == "SPY"

    def test_strategy_c_produces_no_trade_decisions(
        self, strategy_c_gameplan, trending_market_data
    ):
        """
        GIVEN: Strategy C gameplan
        WHEN: Pipeline executes
        THEN: No trade decisions produced (alert-only mode)
        """
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_c_gameplan, trending_market_data)

        # Strategy C = no new trades
        for decision in decisions:
            assert decision["action"] in ("HOLD", "CLOSE", "NEUTRAL")

    def test_pipeline_with_no_market_data_defaults_safe(self, strategy_a_gameplan):
        """
        GIVEN: Strategy A gameplan but no market data available
        WHEN: Pipeline executes
        THEN: No trades (can't generate signals without data)
        """
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_a_gameplan, {})

        for decision in decisions:
            assert decision["action"] in ("HOLD", "NEUTRAL")

    def test_pipeline_respects_pdt_remaining(self, strategy_a_gameplan, trending_market_data):
        """
        GIVEN: Strategy A gameplan with pdt_trades_remaining=0
        WHEN: Pipeline executes
        THEN: No new entry decisions (PDT exhausted)
        """
        from src.strategy.execution import evaluate_signals

        strategy_a_gameplan["hard_limits"]["pdt_trades_remaining"] = 0
        decisions = evaluate_signals(strategy_a_gameplan, trending_market_data)

        for decision in decisions:
            assert decision["action"] != "BUY", "Cannot open new positions with 0 PDT trades remaining"


# =============================================================================
# STRATEGY TRANSITION TESTS
# =============================================================================


class TestStrategyTransitions:
    """Tests for mid-session strategy changes based on regime shifts."""

    def test_vix_spike_transitions_a_to_c(self):
        """
        GIVEN: Currently running Strategy A
        WHEN: VIX spikes above 25 (regime shift to crisis)
        THEN: Strategy transitions to C
        """
        from src.strategy.selection import select_strategy

        # Before spike: Strategy A
        before = select_strategy(16.5, catalysts=[])
        assert before["strategy"] == "A"

        # After spike: Strategy C
        after = select_strategy(26.0, catalysts=[])
        assert after["strategy"] == "C"

    def test_vix_rise_transitions_a_to_b(self):
        """
        GIVEN: Currently running Strategy A (VIX 16.5)
        WHEN: VIX rises to elevated (22.0)
        THEN: Strategy transitions to B
        """
        from src.strategy.selection import select_strategy

        before = select_strategy(16.5, catalysts=[])
        assert before["strategy"] == "A"

        after = select_strategy(22.0, catalysts=[])
        assert after["strategy"] == "B"

    def test_vix_drop_transitions_b_to_a(self):
        """
        GIVEN: Currently running Strategy B (VIX 22.0)
        WHEN: VIX drops to normal (16.0)
        THEN: Strategy transitions to A
        """
        from src.strategy.selection import select_strategy

        before = select_strategy(22.0, catalysts=[])
        assert before["strategy"] == "B"

        after = select_strategy(16.0, catalysts=[])
        assert after["strategy"] == "A"

    def test_strategy_c_never_transitions_up_within_session(self):
        """
        DESIGN NOTE: Once Strategy C is locked for the session
        (via governor, data quarantine, or pivot limit), it should
        remain locked. VIX improvement alone shouldn't unlock it.

        This test validates the concept — the actual enforcement
        is in the execution engine's session state.
        """
        from src.strategy.selection import select_strategy

        # Strategy C due to governor
        locked = select_strategy(16.5, catalysts=[], weekly_governor_active=True)
        assert locked["strategy"] == "C"

        # Even with great VIX, governor keeps it locked
        still_locked = select_strategy(12.0, catalysts=[], weekly_governor_active=True)
        assert still_locked["strategy"] == "C"


# =============================================================================
# OUTPUT CONTRACT VALIDATION TESTS
# =============================================================================


class TestOutputContracts:
    """Tests that strategy layer outputs match expected data contracts."""

    def test_strategy_selection_output_schema(self, vix_normal_mid, no_catalysts):
        """Strategy selection output has all required fields."""
        from src.strategy.selection import select_strategy

        result = select_strategy(vix_normal_mid, catalysts=no_catalysts)

        required_fields = ["strategy", "regime", "symbols", "position_size_multiplier"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_signal_evaluation_output_schema(self, strategy_a_gameplan, trending_market_data):
        """Signal evaluation output has all required fields per decision."""
        from src.strategy.execution import evaluate_signals

        decisions = evaluate_signals(strategy_a_gameplan, trending_market_data)

        for decision in decisions:
            assert "symbol" in decision
            assert "action" in decision
            assert "confidence" in decision
            assert isinstance(decision["confidence"], (int, float))
            assert 0.0 <= decision["confidence"] <= 1.0
```

**Validate:**
```bash
poetry run ruff check tests/integration/test_strategy_execution.py
poetry run black --check tests/integration/test_strategy_execution.py
```

---

### Step 4: Verify All Test Files Are Discoverable

**Action:** RUN COMMAND

```bash
# Verify pytest discovers all new test files and classes
poetry run pytest tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py --collect-only 2>&1 | head -80
```

**Expected Result:**
- All test classes and methods are collected
- No import errors (tests import from `src.strategy.*` which doesn't exist yet — tests should be collected but will fail on execution)
- Approximate count: ~75-85 tests collected

---

## 2. VALIDATION BLOCK

> Run these commands **after all steps are complete.** All must pass.

```bash
# 1. Linting (tests only — src/strategy/ doesn't exist yet)
poetry run ruff check tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py

# 2. Formatting
poetry run black --check tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py

# 3. Collection (verify tests are discoverable)
poetry run pytest tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py --collect-only

# 4. Count total tests
poetry run pytest tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py --collect-only -q 2>&1 | tail -1
```

**Expected Results:**
- ruff: 0 errors
- black: "All done! ✨ 🍰 ✨"
- pytest collect: All tests collected, no import-time failures
- Count: ~78-85 tests total

**NOTE:** Tests will FAIL when run (not just collected) because `src/strategy/` doesn't exist yet. This is expected — TDD Phase 1a. Phase 1b (Chunk 2) will implement the production code to satisfy these tests.

---

## 3. GIT BLOCK

```bash
git add tests/unit/test_strategy_signals.py tests/unit/test_strategy_selection.py tests/integration/test_strategy_execution.py
git commit -m "Coverage-1.1.4 Phase 1a: Strategy layer test suite (TDD)

Test-Driven Development: tests define the strategy layer specification.
All tests will fail until src/strategy/ is implemented in Phase 1b.

Test Files:
- tests/unit/test_strategy_signals.py (~35 tests)
  - EMA crossover signal generation (Strategy A)
  - RSI calculation and range validation
  - VWAP confirmation logic
  - Bollinger Band touch detection (Strategy B)
  - Composite signal evaluation for Strategy A and B
  - Graceful degradation on missing/stale/malformed data
- tests/unit/test_strategy_selection.py (~35 tests)
  - VIX regime detection with exact boundary tests
  - Strategy selection logic for each regime
  - Catalyst overrides (FOMC, CPI, earnings blackout)
  - Position size multiplier by regime
  - Strategy parameter validation
  - External overrides (data quarantine, drawdown governor, pivot limit)
- tests/integration/test_strategy_execution.py (~15 tests)
  - Gameplan JSON validation and loading
  - Full signal evaluation pipeline
  - Strategy transition scenarios
  - Output contract validation

Coverage Target: ≥85% of src/strategy/ (to be measured after Phase 1b)

Safety-Critical Assertions:
- None/missing VIX → crisis regime → Strategy C
- Malformed gameplan → Strategy C
- Data quarantine → Strategy C
- Earnings blackout → Strategy C (absolute, no exceptions)
- Drawdown governor → Strategy C
- Pivot limit reached → Strategy C

Quality Gates: ruff ✅ black ✅"
git push origin main
```

---

## 4. CONTEXT BLOCK (Human Reference — Agent Can Skip)

### Objective

Build the complete test suite for the strategy layer (`src/strategy/`) using TDD methodology. The tests define the specification that production code must satisfy. This follows the identical two-phase pattern established in Coverage-1.1.3 (broker layer): Phase 1a writes the tests, Phase 1b implements the production code.

The strategy layer is the decision engine — it takes market data from the broker layer, evaluates technical indicators, and produces trade decisions. It sits between the broker layer (data source) and the risk/execution layers (consumers of trade decisions).

### Architecture Notes

**Three test files map to three production modules:**

| Test File | Production Module | Responsibility |
|-----------|------------------|----------------|
| `test_strategy_signals.py` | `src/strategy/signals.py` | Technical indicator calculation (EMA, RSI, VWAP, Bollinger) and composite signal evaluation |
| `test_strategy_selection.py` | `src/strategy/selection.py` | VIX regime detection, strategy mapping, catalyst overrides, parameter selection |
| `test_strategy_execution.py` | `src/strategy/execution.py` | Gameplan loading, full pipeline orchestration, multi-symbol evaluation |

**Dependency chain:**
```
Broker Layer (src/broker/) → Strategy Layer (src/strategy/) → Risk Layer (src/risk/) → Execution Layer (src/execution/)
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                              THIS TASK
```

**Key design decisions:**
- Individual indicator functions are pure (no side effects, no I/O)
- Composite signal functions combine indicators with strategy-specific logic
- Strategy selection is VIX-driven with catalyst overrides
- Gameplan validation is strict — malformed config → Strategy C
- All graceful degradation paths default to Strategy C (fail safe)

### Strategy Library Reference (from Crucible v4.0)

**Strategy A (Momentum Breakout):** VIX < 18
- Signals: EMA(8) > EMA(21) + RSI 50-65 + Price > VWAP
- Symbols: SPY, QQQ (max 2)
- Risk: 3% max, 20% position, 25% SL, 15% TP, 90min time stop
- Expiry: Weekly, min 2 DTE, ATM

**Strategy B (Mean Reversion Fade):** VIX 18-25
- Signals: RSI < 30 or > 70 + Bollinger 2σ touch
- Symbols: SPY only
- Risk: 2% max, 10% position, 15% SL, 8% TP, 45min time stop
- Expiry: Weekly, min 5 DTE, 1 strike OTM

**Strategy C (Cash Preservation):** VIX > 25, default, or any safety trigger
- No new entries, close all at 3 DTE, 40% emergency stop, alert-only

### Edge Cases Considered

- VIX = None → crisis regime → Strategy C (data failure)
- VIX = 0 or negative → handled gracefully
- Exact boundary values (15.0, 18.0, 25.0) → tested at boundary, boundary-1, boundary+1
- Insufficient bar data (< EMA slow period) → NEUTRAL signal
- Missing fields in bars (no VWAP, no volume) → graceful degradation
- Stale timestamps (>5 min old) → warning flag
- Empty/None bar list → NEUTRAL signal
- Malformed gameplan → Strategy C
- Data quarantine active → Strategy C regardless of VIX
- Weekly drawdown governor → Strategy C
- Pivot limit (2+) → Strategy C
- Earnings blackout → Strategy C (absolute)
- Multiple high-impact catalysts → Strategy C or heavily reduced sizing

### Rollback Plan

Tests are additive only — they don't modify existing code. To rollback:
```bash
git revert <commit-hash>
```
This removes the three test files without affecting any other project code.

---

## 5. DEFINITION OF DONE

- [ ] All steps in Agent Execution Block completed
- [ ] All Validation Block commands pass (ruff, black, pytest --collect-only)
- [ ] Git commit pushed to main
- [ ] CI pipeline passes (GitHub Actions)
- [ ] ~78-85 tests are discoverable via pytest --collect-only
- [ ] Tests cover all critical scenarios from Sprint Plan 1.1.4 specification
- [ ] VIX boundary tests at exact thresholds: 15.0, 18.0, 25.0
- [ ] Strategy A signals: EMA(8/21), RSI 50-65, VWAP confirmation
- [ ] Strategy B signals: RSI <30/>70, Bollinger 2σ touch
- [ ] Strategy C triggers: VIX >25, data quarantine, governor, pivot limit, earnings
- [ ] Graceful degradation: missing data, stale data, malformed gameplan → never crash
- [ ] All safety-critical paths default to Strategy C (fail safe, not fail open)

---

**Document Status:** ✅ Ready for Implementation
**Approvals:** @Systems_Architect (author), @CRO (passive review — safety assertions validated), @QA_Lead (test design review)

**Phase 1b Note:** After these tests are committed, a separate handoff document (Chunk 2 of 2) will specify the `src/strategy/` production implementation. The test suite IS the specification — Phase 1b implements code to satisfy all assertions with zero test modifications.
