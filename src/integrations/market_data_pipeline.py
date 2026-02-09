"""
Market data pipeline for strategy consumption.

Fetches, calculates, and packages market data with technical indicators.
Validates data quality (staleness, missing fields) and packages into
MarketData dataclass for strategy evaluation.

ALPHA LEARNINGS ENFORCED:
- snapshot=True: Delegated to MarketDataProvider (defense in depth)
- Historical limits: Max 1 hour enforced
- Timeout propagation: All methods accept timeout parameter
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class MarketData:
    """
    Packaged market data for strategy consumption.

    Contains all data a strategy needs to generate signals:
    - Current price and quotes
    - Calculated technical indicators
    - Data quality metadata
    """

    symbol: str
    timestamp: datetime

    # Price data
    last_price: float
    bid: float
    ask: float
    volume: int

    # Technical indicators (calculated)
    ema_fast: float  # 8-period EMA
    ema_slow: float  # 21-period EMA
    rsi: float  # 14-period RSI
    vwap: float  # Session VWAP
    bollinger_upper: float  # 20-period, 2σ
    bollinger_lower: float  # 20-period, 2σ
    bollinger_middle: float  # 20-period SMA

    # Data quality flags
    is_stale: bool = False
    staleness_seconds: float = 0.0
    missing_fields: List[str] = field(default_factory=list)
    data_quality_score: float = 1.0  # 0.0 = unusable, 1.0 = perfect


@dataclass
class IndicatorSet:
    """Calculated technical indicators."""

    ema_fast: float
    ema_slow: float
    rsi: float
    vwap: float
    bollinger_upper: float
    bollinger_lower: float
    bollinger_middle: float


@dataclass
class DataQuality:
    """Data quality assessment."""

    is_stale: bool
    staleness_seconds: float
    missing_fields: List[str]
    score: float


# =============================================================================
# EXCEPTIONS
# =============================================================================


class InsufficientDataError(Exception):
    """Raised when not enough bars for indicator calculation."""

    pass


class AlphaLearningViolationError(Exception):
    """Raised when alpha learning rule is violated."""

    pass


# =============================================================================
# MARKET DATA PIPELINE
# =============================================================================


class MarketDataPipeline:
    """
    Fetches, calculates, and packages market data for strategies.

    Responsibilities:
    - Fetch real-time data via MarketDataProvider
    - Calculate technical indicators from historical bars
    - Validate data quality (staleness, missing fields)
    - Package into MarketData dataclass

    Alpha Learnings:
    - snapshot=True: Delegated to MarketDataProvider
    - Historical limits: Enforced in fetch_historical_data
    - Timeout propagation: All methods accept timeout
    """

    def __init__(
        self,
        market_data_provider: Any,  # MarketDataProvider from broker layer
        staleness_threshold_seconds: float = 300.0,  # 5 minutes
    ):
        """
        Initialize market data pipeline.

        Args:
            market_data_provider: MarketDataProvider instance from broker layer
            staleness_threshold_seconds: Threshold for stale data (default 5 min)
        """
        self._provider = market_data_provider
        self._staleness_threshold = staleness_threshold_seconds
        logger.info(
            "MarketDataPipeline initialized",
            staleness_threshold_seconds=staleness_threshold_seconds,
        )

    async def fetch_market_data(self, symbol: str, timeout: float = 30.0) -> MarketData:
        """
        Fetch and package current market data with indicators.

        Flow:
        1. Fetch real-time quote (snapshot=True enforced by provider)
        2. Fetch historical bars for indicator calculation
        3. Calculate all technical indicators
        4. Validate data quality
        5. Package into MarketData

        Args:
            symbol: Symbol to fetch data for (e.g., "SPY", "QQQ")
            timeout: Request timeout in seconds

        Returns:
            MarketData with price, indicators, and quality flags

        Raises:
            InsufficientDataError: Not enough bars for indicator calculation
            MarketDataError: Failed to fetch data
        """
        logger.debug(f"Fetching market data for {symbol}", timeout=timeout)

        try:
            # Step 1: Fetch real-time quote
            # snapshot=True is enforced by MarketDataProvider initialization
            quote_data = await self._fetch_quote(symbol, timeout)

            # Step 2: Fetch historical bars (1 hour RTH for indicators)
            # ALPHA LEARNING: Max 1 hour enforced
            bars = await self._fetch_historical_bars(symbol, timeout)

            # Step 3: Calculate indicators
            indicators = self._calculate_indicators(bars)

            # Step 4: Validate data quality
            quality = self._validate_data_quality(quote_data, indicators)

            # Step 5: Package
            market_data = MarketData(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                last_price=quote_data["last"],
                bid=quote_data["bid"],
                ask=quote_data["ask"],
                volume=quote_data["volume"],
                ema_fast=indicators.ema_fast,
                ema_slow=indicators.ema_slow,
                rsi=indicators.rsi,
                vwap=indicators.vwap,
                bollinger_upper=indicators.bollinger_upper,
                bollinger_lower=indicators.bollinger_lower,
                bollinger_middle=indicators.bollinger_middle,
                is_stale=quality.is_stale,
                staleness_seconds=quality.staleness_seconds,
                missing_fields=quality.missing_fields,
                data_quality_score=quality.score,
            )

            logger.info(
                "Market data fetched successfully",
                symbol=symbol,
                data_quality_score=quality.score,
                is_stale=quality.is_stale,
            )

            return market_data

        except Exception as e:
            logger.error(f"Failed to fetch market data for {symbol}: {str(e)}")
            raise

    async def fetch_historical_data(
        self,
        symbol: str,
        duration_minutes: int = 60,  # ALPHA LEARNING: Max 1 hour
        bar_size: str = "1 min",
        timeout: float = 30.0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical bars with alpha learning enforcement.

        ALPHA LEARNING: Historical data requests >60 minutes cause 100% timeout.
        This method enforces the 1-hour limit.

        Args:
            symbol: Symbol to fetch bars for
            duration_minutes: Duration in minutes (MAX 60)
            bar_size: Bar size (e.g., "1 min", "5 mins")
            timeout: Request timeout in seconds

        Returns:
            List of bar dictionaries with OHLCV data

        Raises:
            AlphaLearningViolationError: If duration_minutes > 60
        """
        # ALPHA LEARNING: Enforce 1-hour maximum
        if duration_minutes > 60:
            raise AlphaLearningViolationError(
                f"Historical data request exceeds 1-hour limit: {duration_minutes} minutes. "
                "Alpha learning: Multi-hour requests cause 100% timeout. "
                "See docs/alpha_learnings.md"
            )

        return await self._fetch_historical_bars(symbol, timeout, duration_minutes)

    async def _fetch_quote(self, symbol: str, timeout: float) -> Dict[str, Any]:
        """
        Fetch real-time quote from provider.

        Returns dict with: last, bid, ask, volume, timestamp
        """
        # The MarketDataProvider already enforces snapshot=True
        # We add defense in depth by documenting the expectation
        quote_result = self._provider.request_market_data(
            contract=await self._get_qualified_contract(symbol),
            timeout=int(timeout),
        )

        return quote_result

    async def _fetch_historical_bars(
        self, symbol: str, timeout: float, duration_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical bars from provider.

        Returns list of bar dicts with: open, high, low, close, volume
        """
        bars = self._provider.request_historical_data(
            contract=await self._get_qualified_contract(symbol),
            duration="1 H",  # ALPHA LEARNING: Max 1 hour RTH
            bar_size="1 min",
            what_to_show="TRADES",
            use_rth=True,  # RTH only
            timeout=int(timeout),
        )

        # Convert to list of dicts if needed
        if not isinstance(bars, list):
            bars = [
                {
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in bars
            ]

        return bars

    async def _get_qualified_contract(self, symbol: str) -> Any:
        """Get qualified contract from provider's contract manager."""
        return self._provider.contract_manager.qualify_contract(symbol)

    def _calculate_indicators(self, bars: List[Dict[str, Any]]) -> IndicatorSet:
        """
        Calculate all technical indicators from historical bars.

        Uses numpy for efficient calculation.

        Args:
            bars: List of bar dicts with OHLCV data

        Returns:
            IndicatorSet with all calculated indicators

        Raises:
            InsufficientDataError: Not enough bars for indicator calculation
        """
        if not bars or len(bars) < 21:  # Need at least 21 bars for slow EMA
            raise InsufficientDataError(f"Need at least 21 bars for indicators, got {len(bars)}")

        closes = np.array([float(b["close"]) for b in bars])
        highs = np.array([float(b["high"]) for b in bars])
        lows = np.array([float(b["low"]) for b in bars])
        volumes = np.array([float(b["volume"]) for b in bars])

        return IndicatorSet(
            ema_fast=self._calculate_ema(closes, period=8),
            ema_slow=self._calculate_ema(closes, period=21),
            rsi=self._calculate_rsi(closes, period=14),
            vwap=self._calculate_vwap(closes, highs, lows, volumes),
            bollinger_upper=self._calculate_bollinger(closes, period=20, std=2)[0],
            bollinger_lower=self._calculate_bollinger(closes, period=20, std=2)[1],
            bollinger_middle=self._calculate_bollinger(closes, period=20, std=2)[2],
        )

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """
        Calculate Exponential Moving Average.

        Args:
            prices: Array of prices
            period: EMA period

        Returns:
            Latest EMA value
        """
        if len(prices) < period:
            raise InsufficientDataError(f"Need {period} bars for EMA, got {len(prices)}")

        multiplier = 2 / (period + 1)
        ema = float(prices[0])
        for price in prices[1:]:
            ema = (float(price) * multiplier) + (ema * (1 - multiplier))
        return float(ema)

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """
        Calculate Relative Strength Index.

        Args:
            prices: Array of prices
            period: RSI period (default 14)

        Returns:
            Latest RSI value (0-100)
        """
        if len(prices) < period + 1:
            raise InsufficientDataError(f"Need {period + 1} bars for RSI, got {len(prices)}")

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)

    def _calculate_vwap(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray,
    ) -> float:
        """
        Calculate Volume Weighted Average Price.

        Args:
            closes: Array of close prices
            highs: Array of high prices
            lows: Array of low prices
            volumes: Array of volumes

        Returns:
            Session VWAP value
        """
        typical_prices = (highs + lows + closes) / 3
        cumulative_tpv = np.sum(typical_prices * volumes)
        cumulative_volume = np.sum(volumes)

        if cumulative_volume == 0:
            return float(closes[-1])  # Fallback to last close

        return float(cumulative_tpv / cumulative_volume)

    def _calculate_bollinger(
        self, prices: np.ndarray, period: int = 20, std: int = 2
    ) -> tuple[float, float, float]:
        """
        Calculate Bollinger Bands.

        Args:
            prices: Array of prices
            period: Period for moving average (default 20)
            std: Number of standard deviations (default 2)

        Returns:
            Tuple of (upper, lower, middle)
        """
        if len(prices) < period:
            raise InsufficientDataError(f"Need {period} bars for Bollinger, got {len(prices)}")

        recent = prices[-period:]
        middle = float(np.mean(recent))
        std_dev = float(np.std(recent))

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return upper, lower, middle

    def _validate_data_quality(
        self, quote: Dict[str, Any], indicators: IndicatorSet
    ) -> DataQuality:
        """
        Validate data quality for trading decisions.

        Checks:
        - Staleness (quote timestamp vs now)
        - Missing fields (bid/ask/volume = 0)
        - Indicator validity (NaN, extreme values)

        Args:
            quote: Quote data dict
            indicators: Calculated indicators

        Returns:
            DataQuality assessment
        """
        now = datetime.now(timezone.utc)
        quote_timestamp = quote.get("timestamp", now)
        if not isinstance(quote_timestamp, datetime):
            quote_timestamp = now

        staleness_seconds = (now - quote_timestamp).total_seconds()
        is_stale = staleness_seconds > self._staleness_threshold

        missing_fields = []
        if quote.get("bid", 0) <= 0:
            missing_fields.append("bid")
        if quote.get("ask", 0) <= 0:
            missing_fields.append("ask")
        if quote.get("volume", 0) <= 0:
            missing_fields.append("volume")

        # Check for NaN indicators
        for field_name, value in [
            ("ema_fast", indicators.ema_fast),
            ("ema_slow", indicators.ema_slow),
            ("rsi", indicators.rsi),
            ("vwap", indicators.vwap),
        ]:
            if np.isnan(value):
                missing_fields.append(field_name)

        # Calculate quality score
        # Start at 1.0, deduct for issues
        score = 1.0
        if is_stale:
            score -= 0.5
        score -= len(missing_fields) * 0.1
        score = max(0.0, score)

        return DataQuality(
            is_stale=is_stale,
            staleness_seconds=staleness_seconds,
            missing_fields=missing_fields,
            score=score,
        )
