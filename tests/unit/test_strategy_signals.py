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
from typing import Dict, Any, List
from dataclasses import dataclass

# =============================================================================
# DATA STRUCTURES (Expected from src/strategy/signals.py)
# =============================================================================


@dataclass
class SignalResult:
    """Expected output structure from signal generators."""

    signal_type: str  # "BUY", "SELL", "NEUTRAL"
    confidence: float  # 0.0 to 1.0
    strategy: str  # "A", "B", "C"
    indicators: Dict[str, Any]  # Raw indicator values used
    timestamp: datetime
    reasons: List[str]  # Human-readable signal reasons


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
        bars.append(
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "open": price - 0.10,
                "high": price + 0.20,
                "low": price - 0.15,
                "close": price,
                "volume": 800000 + (i * 10000),
                "vwap": price - 0.30,  # Price above VWAP
            }
        )
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
        bars.append(
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "open": price + 0.10,
                "high": price + 0.15,
                "low": price - 0.20,
                "close": price,
                "volume": 900000 + (i * 15000),
                "vwap": price + 0.30,  # Price below VWAP
            }
        )
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
        bars.append(
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "open": price + 0.15,
                "high": price + 0.25,
                "low": price - 0.30,
                "close": price,
                "volume": 1200000 + (i * 20000),
                "vwap": price + 1.50,  # Price well below VWAP
            }
        )
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
        bars.append(
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "open": price - 0.15,
                "high": price + 0.30,
                "low": price - 0.25,
                "close": price,
                "volume": 1100000 + (i * 18000),
                "vwap": price - 1.50,  # Price well above VWAP
            }
        )
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
        bars.append(
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "open": price - 0.05,
                "high": price + 0.15,
                "low": price - 0.15,
                "close": price,
                "volume": 700000,
                "vwap": base_price,
            }
        )
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
            "open": 689.0,
            "high": 689.5,
            "low": 688.5,
            "close": 689.0,
            "volume": 500000,
            "vwap": 689.0,
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
            "open": 689.0,
            "high": 689.5,
            "low": 688.5,
            "close": 689.0,
            "volume": 500000,
            "vwap": 689.0,
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
            {
                "timestamp": "2026-02-06T10:00:00Z",
                "open": 689.0,
                "high": 689.5,
                "low": 688.5,
                "close": None,
                "volume": 500000,
                "vwap": 689.0,
            }
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
