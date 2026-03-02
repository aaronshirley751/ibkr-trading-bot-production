"""
Technical indicator computation for Strategy A/B signal evaluation.

Computes EMA, RSI, VWAP, and Bollinger Bands from raw OHLCV bar data
returned by MarketDataProvider.request_historical_data().

Data flow (per evaluation cycle per symbol):
    MarketDataProvider.request_historical_data() -> List[Dict]  # raw bars
    MarketDataProvider.request_market_data()     -> Dict        # live quote
    build_market_data()                          -> MarketData  # strategy input

All indicator math uses pure Python (no numpy/pandas dependencies).
All functions return None when there is insufficient bar history.
"""

import logging
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.strategies.base import MarketData

logger = logging.getLogger(__name__)

# Minimum bar counts before indicators are considered reliable
_MIN_BARS_EMA_FAST = 10  # fast EMA warms up quickly
_MIN_BARS_EMA_SLOW = 25  # slow EMA (21) needs a little extra runway
_MIN_BARS_RSI = 16  # RSI-14 needs 15 deltas → 16 prices
_MIN_BARS_BOLLINGER = 22  # Bollinger-20 needs 20 closes + a couple extra


# ---------------------------------------------------------------------------
# Indicator primitives
# ---------------------------------------------------------------------------


def compute_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Compute Exponential Moving Average using Wilder-style smoothing.

    Seeds with the simple moving average of the first ``period`` values,
    then applies  EMA_t = price_t * k + EMA_{t-1} * (1 - k)
    where k = 2 / (period + 1).

    Args:
        prices: Chronologically ordered closing prices (oldest first).
        period: EMA period (e.g. 8 for fast, 21 for slow).

    Returns:
        Current EMA value, or None if len(prices) < period.
    """
    if len(prices) < period:
        logger.debug("compute_ema: insufficient data (%d < %d)", len(prices), period)
        return None

    k = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period  # seed with SMA
    for price in prices[period:]:
        ema = price * k + ema * (1.0 - k)
    return ema


def compute_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Compute Relative Strength Index (RSI) using Wilder's smoothed moving average.

    Args:
        prices: Chronologically ordered closing prices (oldest first).
        period: RSI period (default 14).

    Returns:
        RSI value in range [0, 100], or None if insufficient data.
    """
    if len(prices) < period + 1:
        logger.debug("compute_rsi: insufficient data (%d < %d)", len(prices), period + 1)
        return None

    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-delta)

    if len(gains) < period:
        return None

    # Seed averages over first period
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Wilder smoothing for subsequent periods
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_vwap(bars: List[Dict[str, Any]]) -> Optional[float]:
    """
    Compute Volume Weighted Average Price across all provided bars.

    Uses typical price = (high + low + close) / 3.
    Falls back to simple average of typical prices if total volume is zero.

    Args:
        bars: List of bar dicts with 'high', 'low', 'close', 'volume' keys.

    Returns:
        VWAP float, or None if bars is empty.
    """
    if not bars:
        return None

    total_pv = 0.0
    total_volume = 0.0
    typical_prices: List[float] = []

    for bar in bars:
        try:
            high = float(bar["high"])
            low = float(bar["low"])
            close = float(bar["close"])
            volume = float(bar.get("volume") or 0)
        except (KeyError, ValueError, TypeError):
            continue

        tp = (high + low + close) / 3.0
        typical_prices.append(tp)
        total_pv += tp * volume
        total_volume += volume

    if not typical_prices:
        return None

    if total_volume == 0.0:
        # Fallback: simple average of typical prices
        return sum(typical_prices) / len(typical_prices)

    return total_pv / total_volume


def compute_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_devs: float = 2.0,
) -> Optional[Tuple[float, float, float]]:
    """
    Compute Bollinger Bands (upper, middle, lower) from closing prices.

    Middle band = SMA(period) of the most recent ``period`` prices.
    Upper band  = middle + std_devs * stdev(recent)
    Lower band  = middle - std_devs * stdev(recent)

    Args:
        prices: Chronologically ordered closing prices (oldest first).
        period: Moving-average period (default 20).
        std_devs: Standard deviation multiplier (default 2.0).

    Returns:
        Tuple (upper, middle, lower), or None if insufficient data.
    """
    if len(prices) < period:
        logger.debug("compute_bollinger_bands: insufficient data (%d < %d)", len(prices), period)
        return None

    recent = prices[-period:]
    middle = sum(recent) / period

    if len(recent) < 2:
        return None

    std = statistics.stdev(recent)
    upper = middle + std_devs * std
    lower = middle - std_devs * std
    return (upper, middle, lower)


# ---------------------------------------------------------------------------
# MarketData builder
# ---------------------------------------------------------------------------


def build_market_data(
    symbol: str,
    quote: Dict[str, Any],
    bars: List[Dict[str, Any]],
    ema_fast_period: int = 8,
    ema_slow_period: int = 21,
    rsi_period: int = 14,
    bollinger_period: int = 20,
    bollinger_std: float = 2.0,
) -> Optional[MarketData]:
    """
    Assemble a MarketData instance from a live quote and historical bars.

    Computes all technical indicators (EMA, RSI, VWAP, Bollinger Bands) from
    the bar history and attaches the live bid/ask/last for gate and risk checks.

    Args:
        symbol: Ticker symbol (e.g. "QQQ").
        quote: Dict returned by MarketDataProvider.request_market_data().
               Expected keys: bid, ask, last, volume, timestamp.
        bars: List of bar dicts returned by
              MarketDataProvider.request_historical_data().
              Required bar keys: high, low, close, volume.
        ema_fast_period: Fast EMA period for Strategy A (default 8).
        ema_slow_period: Slow EMA period for Strategy A (default 21).
        rsi_period: RSI period (default 14).
        bollinger_period: Bollinger Band SMA period (default 20).
        bollinger_std: Bollinger Band standard-deviation multiplier (default 2.0).

    Returns:
        Populated MarketData, or None if the quote lacks usable bid/ask.
    """
    bid: Optional[float] = quote.get("bid")
    ask: Optional[float] = quote.get("ask")
    last: Optional[float] = quote.get("last")
    volume: int = int(quote.get("volume") or 0)
    raw_ts = quote.get("timestamp")
    ts: datetime = raw_ts if isinstance(raw_ts, datetime) else datetime.now(timezone.utc)

    # Guard: need valid bid *and* ask to construct MarketData
    if bid is None or ask is None or bid <= 0 or ask <= 0:
        logger.warning(
            "build_market_data: unusable quote for %s (bid=%s, ask=%s)",
            symbol,
            bid,
            ask,
        )
        return None

    # Mid-price fallback if last is absent
    price = last if (last and last > 0) else (bid + ask) / 2.0

    # Extract closing prices for indicator computation
    closes: List[float] = []
    for bar in bars:
        c = bar.get("close")
        if c and float(c) > 0:
            closes.append(float(c))

    # Compute indicators — each returns None when bars are insufficient
    ema_fast: Optional[float] = compute_ema(closes, ema_fast_period) if closes else None
    ema_slow: Optional[float] = compute_ema(closes, ema_slow_period) if closes else None
    rsi: Optional[float] = compute_rsi(closes, rsi_period) if closes else None
    vwap: Optional[float] = compute_vwap(bars) if bars else None

    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    if closes:
        bb = compute_bollinger_bands(closes, bollinger_period, bollinger_std)
        if bb is not None:
            bollinger_upper, bollinger_middle, bollinger_lower = bb

    logger.debug(
        "build_market_data(%s): price=%.4f bid=%.4f ask=%.4f "
        "ema_fast=%s ema_slow=%s rsi=%s vwap=%s bars=%d",
        symbol,
        price,
        bid,
        ask,
        f"{ema_fast:.4f}" if ema_fast is not None else "None",
        f"{ema_slow:.4f}" if ema_slow is not None else "None",
        f"{rsi:.1f}" if rsi is not None else "None",
        f"{vwap:.4f}" if vwap is not None else "None",
        len(bars),
    )

    return MarketData(
        symbol=symbol,
        timestamp=ts,
        price=price,
        bid=bid,
        ask=ask,
        volume=volume,
        vwap=vwap,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        rsi=rsi,
        bollinger_upper=bollinger_upper,
        bollinger_lower=bollinger_lower,
        bollinger_middle=bollinger_middle,
    )
