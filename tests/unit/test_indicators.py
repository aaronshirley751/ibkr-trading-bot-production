"""
Unit tests for src/bot/indicators.py

Covers:
- compute_ema: normal, insufficient data, single period
- compute_rsi: overbought, oversold, insufficient data
- compute_vwap: normal, zero volume fallback, empty bars
- compute_bollinger_bands: normal, insufficient data
- build_market_data: full path, missing bid/ask, empty bars

All tests are deterministic — no IBKR connection required.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from src.bot.indicators import (
    build_market_data,
    compute_bollinger_bands,
    compute_ema,
    compute_rsi,
    compute_vwap,
)
from src.strategies.base import MarketData

# =============================================================================
# Helpers
# =============================================================================


def _rising_prices(n: int = 30, start: float = 100.0, step: float = 0.5) -> List[float]:
    """Generate n monotonically rising closing prices."""
    return [start + i * step for i in range(n)]


def _falling_prices(n: int = 30, start: float = 115.0, step: float = 0.5) -> List[float]:
    """Generate n monotonically falling closing prices."""
    return [start - i * step for i in range(n)]


def _flat_prices(n: int = 30, price: float = 100.0) -> List[float]:
    return [price] * n


def _make_bars(closes: List[float], volume: int = 100_000) -> List[Dict[str, Any]]:
    """Wrap a list of closing prices into OHLCV bar dicts."""
    bars = []
    for c in closes:
        bars.append(
            {
                "open": c - 0.10,
                "high": c + 0.20,
                "low": c - 0.15,
                "close": c,
                "volume": volume,
                "average": c,
                "bar_count": 10,
            }
        )
    return bars


def _make_quote(
    bid: float = 100.0,
    ask: float = 100.10,
    last: float = 100.05,
    volume: int = 1_000_000,
) -> Dict[str, Any]:
    return {
        "bid": bid,
        "ask": ask,
        "last": last,
        "volume": volume,
        "timestamp": datetime.now(timezone.utc),
        "snapshot": True,
    }


# =============================================================================
# compute_ema
# =============================================================================


class TestComputeEMA:
    """Tests for compute_ema."""

    def test_returns_value_with_sufficient_data(self) -> None:
        prices = _rising_prices(30)
        ema = compute_ema(prices, period=8)
        assert ema is not None
        assert isinstance(ema, float)

    def test_ema_follows_trend_for_rising_prices(self) -> None:
        """EMA of rising series should be close to the most recent prices."""
        prices = _rising_prices(40, start=100.0, step=1.0)
        ema = compute_ema(prices, period=8)
        assert ema is not None
        # EMA should lag but be near the recent end of the series
        assert ema > 110.0

    def test_slow_ema_lags_behind_fast_ema(self) -> None:
        """On a rising series, fast EMA > slow EMA."""
        prices = _rising_prices(40)
        fast = compute_ema(prices, period=8)
        slow = compute_ema(prices, period=21)
        assert fast is not None
        assert slow is not None
        assert fast > slow

    def test_returns_none_when_insufficient_data(self) -> None:
        prices = _rising_prices(5)
        ema = compute_ema(prices, period=8)
        assert ema is None

    def test_returns_value_at_exactly_period_length(self) -> None:
        prices = _flat_prices(8, price=50.0)
        ema = compute_ema(prices, period=8)
        assert ema is not None
        assert abs(ema - 50.0) < 1e-9  # flat series → EMA = price


# =============================================================================
# compute_rsi
# =============================================================================


class TestComputeRSI:
    """Tests for compute_rsi."""

    def test_returns_value_with_sufficient_data(self) -> None:
        prices = _rising_prices(30)
        rsi = compute_rsi(prices, period=14)
        assert rsi is not None
        assert 0.0 <= rsi <= 100.0

    def test_overbought_on_strong_uptrend(self) -> None:
        """Monotonic rise should produce high RSI."""
        prices = _rising_prices(30, step=1.0)
        rsi = compute_rsi(prices, period=14)
        assert rsi is not None
        assert rsi > 70.0

    def test_oversold_on_strong_downtrend(self) -> None:
        """Monotonic fall should produce low RSI."""
        prices = _falling_prices(30, step=1.0)
        rsi = compute_rsi(prices, period=14)
        assert rsi is not None
        assert rsi < 30.0

    def test_returns_100_when_no_losses(self) -> None:
        """Pure rising closes → avg_loss=0 → RSI=100."""
        prices = _rising_prices(20, step=0.5)
        rsi = compute_rsi(prices, period=14)
        assert rsi == 100.0

    def test_returns_none_when_insufficient_data(self) -> None:
        prices = _rising_prices(10)
        rsi = compute_rsi(prices, period=14)
        assert rsi is None

    def test_neutral_on_flat_prices(self) -> None:
        """All identical closes → all deltas are zero → RSI should not crash."""
        prices = _flat_prices(20)
        rsi = compute_rsi(prices, period=14)
        # All gains and losses are zero; result should be 100 (avg_loss=0)
        assert rsi == 100.0


# =============================================================================
# compute_vwap
# =============================================================================


class TestComputeVWAP:
    """Tests for compute_vwap."""

    def test_returns_float_for_normal_bars(self) -> None:
        bars = _make_bars(_flat_prices(10, 100.0))
        vwap = compute_vwap(bars)
        assert vwap is not None
        assert isinstance(vwap, float)

    def test_vwap_of_flat_series_equals_price(self) -> None:
        closes = _flat_prices(10, 100.0)
        bars = _make_bars(closes)
        vwap = compute_vwap(bars)
        assert vwap is not None
        # typical price for flat bar with high+0.20, low-0.15 → (100.20 + 99.85 + 100) / 3
        expected_tp = (100.20 + 99.85 + 100.0) / 3.0
        assert abs(vwap - expected_tp) < 0.01

    def test_returns_none_for_empty_bars(self) -> None:
        vwap = compute_vwap([])
        assert vwap is None

    def test_falls_back_to_simple_average_on_zero_volume(self) -> None:
        bars = _make_bars(_flat_prices(5, 50.0), volume=0)
        vwap = compute_vwap(bars)
        # All bars have zero volume → should fall back to simple avg of typical prices
        assert vwap is not None
        assert isinstance(vwap, float)


# =============================================================================
# compute_bollinger_bands
# =============================================================================


class TestComputeBollingerBands:
    """Tests for compute_bollinger_bands."""

    def test_returns_triple_for_sufficient_data(self) -> None:
        prices = _flat_prices(25, 100.0)
        result = compute_bollinger_bands(prices, period=20, std_devs=2.0)
        assert result is not None
        upper, middle, lower = result
        assert isinstance(upper, float)
        assert isinstance(middle, float)
        assert isinstance(lower, float)

    def test_bands_ordering(self) -> None:
        """upper > middle > lower for any non-constant series."""
        prices = _rising_prices(30, step=0.5)
        result = compute_bollinger_bands(prices, period=20)
        assert result is not None
        upper, middle, lower = result
        assert upper > middle > lower

    def test_flat_series_has_zero_bandwidth(self) -> None:
        """Constant prices → std=0 → upper == middle == lower."""
        prices = _flat_prices(25, 50.0)
        result = compute_bollinger_bands(prices, period=20)
        assert result is not None
        upper, middle, lower = result
        assert abs(upper - lower) < 1e-9

    def test_returns_none_when_insufficient_data(self) -> None:
        prices = _flat_prices(10)
        result = compute_bollinger_bands(prices, period=20)
        assert result is None


# =============================================================================
# build_market_data
# =============================================================================


class TestBuildMarketData:
    """Tests for build_market_data."""

    def test_returns_market_data_for_valid_inputs(self) -> None:
        closes = _rising_prices(35)
        bars = _make_bars(closes)
        quote = _make_quote(bid=115.0, ask=115.10, last=115.05)
        md = build_market_data("QQQ", quote, bars)
        assert md is not None
        assert isinstance(md, MarketData)
        assert md.symbol == "QQQ"

    def test_price_uses_last_when_valid(self) -> None:
        bars = _make_bars(_flat_prices(30, 100.0))
        quote = _make_quote(bid=99.0, ask=101.0, last=100.50)
        md = build_market_data("SPY", quote, bars)
        assert md is not None
        assert md.price == 100.50

    def test_price_falls_back_to_midpoint_when_last_absent(self) -> None:
        bars = _make_bars(_flat_prices(30, 100.0))
        quote = _make_quote(bid=99.0, ask=101.0, last=0.0)  # last=0 → fallback
        md = build_market_data("SPY", quote, bars)
        assert md is not None
        assert abs(md.price - 100.0) < 1e-9

    def test_returns_none_for_missing_bid(self) -> None:
        quote: Dict[str, Any] = {
            "bid": None,
            "ask": 101.0,
            "last": 100.0,
            "volume": 1000,
            "timestamp": datetime.now(timezone.utc),
        }
        md = build_market_data("QQQ", quote, [])
        assert md is None

    def test_returns_none_for_zero_ask(self) -> None:
        quote = _make_quote(bid=0.0, ask=0.0)
        md = build_market_data("QQQ", quote, [])
        assert md is None

    def test_indicators_populated_with_sufficient_bars(self) -> None:
        closes = _rising_prices(35)
        bars = _make_bars(closes)
        quote = _make_quote(bid=115.0, ask=115.10, last=115.05)
        md = build_market_data("QQQ", quote, bars)
        assert md is not None
        assert md.ema_fast is not None
        assert md.ema_slow is not None
        assert md.rsi is not None
        assert md.vwap is not None

    def test_indicators_none_with_empty_bars(self) -> None:
        quote = _make_quote()
        md = build_market_data("QQQ", quote, [])
        assert md is not None  # quote is valid, so MarketData is returned
        assert md.ema_fast is None
        assert md.ema_slow is None
        assert md.rsi is None
        assert md.vwap is None

    def test_bollinger_bands_populated_with_sufficient_bars(self) -> None:
        closes = _rising_prices(30)
        bars = _make_bars(closes)
        quote = _make_quote(bid=114.0, ask=114.10, last=114.05)
        md = build_market_data("QQQ", quote, bars)
        assert md is not None
        assert md.bollinger_upper is not None
        assert md.bollinger_middle is not None
        assert md.bollinger_lower is not None
