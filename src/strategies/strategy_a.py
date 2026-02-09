"""
Strategy A: Momentum Breakout (Trending Markets).

Deployed when VIX < 18 for trending, complacent market conditions.
Uses EMA 8/21 crossover as primary signal with RSI 50-65 and VWAP confirmation.

ENTRY CONDITIONS (LONG):
- EMA(8) crosses above EMA(21) — bullish momentum
- RSI in range [50, 65] — momentum without overbought
- Price > VWAP — buyers dominating

ENTRY CONDITIONS (SHORT):
- EMA(8) crosses below EMA(21) — bearish momentum
- RSI in range [35, 50] — momentum without oversold
- Price < VWAP — sellers dominating

CONFIDENCE CALCULATION:
- Base: 0.6 (directional strategy)
- Bonus: +0.1 for RSI sweet spot (55-60 LONG, 40-45 SHORT)
- Bonus: +0.1 for strong VWAP distance (>0.2% LONG, <-0.2% SHORT)
- Penalty: -0.2 for low volume (<50% of average)
- Clamped to [0.0, 1.0]

EXIT STRATEGY:
- Take profit: 15% gain
- Stop loss: 25% loss
- Time stop: 90 minutes (enforced at execution layer)

CRITICAL: Indicators (EMA, RSI, VWAP) are pre-computed in MarketData by data layer.
Strategy A evaluates these indicators but does not calculate them from scratch.
"""

from typing import Optional

from .base import MarketData, Signal, StrategyBase, StrategyType
from .config import StrategyAConfig


class StrategyA(StrategyBase):
    """
    Strategy A: Momentum Breakout for trending markets.

    Uses EMA crossover with RSI and VWAP filters to identify high-probability
    trending opportunities. Designed for VIX < 18 conditions.

    Attributes:
        strategy_config: StrategyAConfig with EMA/RSI parameters
        _previous_ema_fast: Tracks EMA(8) from previous evaluation (for crossover detection)
        _previous_ema_slow: Tracks EMA(21) from previous evaluation (for crossover detection)
    """

    def __init__(self, config: Optional[StrategyAConfig] = None):
        """
        Initialize Strategy A with configuration.

        Args:
            config: StrategyAConfig instance. Uses defaults if not provided.
        """
        super().__init__(strategy_type=StrategyType.A, config=None)
        self.strategy_config: StrategyAConfig = config or StrategyAConfig()

        # Track previous EMAs for crossover detection
        self._previous_ema_fast: Optional[float] = None
        self._previous_ema_slow: Optional[float] = None

    def evaluate(self, market_data: MarketData) -> Signal:
        """
        Evaluate market data and generate momentum breakout signal.

        Args:
            market_data: Current market snapshot with pre-computed indicators

        Returns:
            Signal with direction (BUY/SELL/HOLD), confidence, and exit levels

        Logic:
            1. Validate required indicators are present
            2. Detect EMA crossover (bullish or bearish)
            3. Apply RSI filter (50-65 for LONG, 35-50 for SHORT)
            4. Apply VWAP confirmation (price > VWAP for LONG, < VWAP for SHORT)
            5. Calculate confidence based on signal strength
            6. Return Signal with entry/stop/target prices
        """
        symbol = market_data.symbol

        # Validate required indicators are present
        if not self._validate_indicators(market_data):
            return self._create_hold_signal(
                symbol=symbol,
                rationale="Missing required indicators (EMA, RSI, or VWAP)",
                confidence=0.0,
                metadata={"reason": "missing_indicators"},
            )

        # Extract indicators (guaranteed non-None by validation)
        # Type assertions safe because _validate_indicators confirmed they're not None
        assert market_data.ema_fast is not None
        assert market_data.ema_slow is not None
        assert market_data.rsi is not None
        assert market_data.vwap is not None

        ema_fast = market_data.ema_fast
        ema_slow = market_data.ema_slow
        rsi = market_data.rsi
        vwap = market_data.vwap
        price = market_data.price

        # Detect crossover (requires previous EMA values)
        crossover_direction = self._detect_crossover(ema_fast, ema_slow)

        # Update previous EMAs for next evaluation
        self._previous_ema_fast = ema_fast
        self._previous_ema_slow = ema_slow

        # No crossover detected
        if crossover_direction == "none":
            return self._create_hold_signal(
                symbol=symbol,
                rationale="No EMA crossover detected",
                confidence=0.0,
                metadata={"ema_fast": ema_fast, "ema_slow": ema_slow},
            )

        # Check for LONG signal
        if crossover_direction == "bullish":
            # Apply RSI filter (50-65 for LONG)
            if not (self.strategy_config.rsi_min <= rsi <= self.strategy_config.rsi_max):
                return self._create_hold_signal(
                    symbol=symbol,
                    rationale=f"RSI {rsi:.1f} outside LONG range [{self.strategy_config.rsi_min}, {self.strategy_config.rsi_max}]",
                    confidence=0.2,
                    metadata={"rsi": rsi, "crossover": "bullish"},
                )

            # Apply VWAP confirmation (price > VWAP)
            if self.strategy_config.require_above_vwap and price <= vwap:
                return self._create_hold_signal(
                    symbol=symbol,
                    rationale=f"Price {price:.2f} not above VWAP {vwap:.2f}",
                    confidence=0.3,
                    metadata={"price": price, "vwap": vwap, "crossover": "bullish"},
                )

            # All conditions met - generate LONG signal
            confidence = self._calculate_confidence_long(
                rsi=rsi, price=price, vwap=vwap, volume=market_data.volume
            )

            stop_loss = price * (1.0 - self.strategy_config.stop_loss_pct)
            take_profit = price * (1.0 + self.strategy_config.take_profit_pct)

            return self._create_buy_signal(
                symbol=symbol,
                confidence=confidence,
                rationale=(
                    f"Bullish EMA crossover (EMA8={ema_fast:.2f} > EMA21={ema_slow:.2f}), "
                    f"RSI {rsi:.1f} in momentum range, price {price:.2f} > VWAP {vwap:.2f}"
                ),
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "ema_fast": ema_fast,
                    "ema_slow": ema_slow,
                    "rsi": rsi,
                    "vwap": vwap,
                    "vwap_distance_pct": ((price - vwap) / vwap) * 100,
                },
            )

        # Check for SHORT signal
        if crossover_direction == "bearish":
            # RSI range for SHORT: 35-50
            rsi_min_short = 35.0
            rsi_max_short = 50.0

            if not (rsi_min_short <= rsi <= rsi_max_short):
                return self._create_hold_signal(
                    symbol=symbol,
                    rationale=f"RSI {rsi:.1f} outside SHORT range [{rsi_min_short}, {rsi_max_short}]",
                    confidence=0.2,
                    metadata={"rsi": rsi, "crossover": "bearish"},
                )

            # Apply VWAP confirmation (price < VWAP for SHORT)
            if price >= vwap:
                return self._create_hold_signal(
                    symbol=symbol,
                    rationale=f"Price {price:.2f} not below VWAP {vwap:.2f}",
                    confidence=0.3,
                    metadata={"price": price, "vwap": vwap, "crossover": "bearish"},
                )

            # All conditions met - generate SHORT signal
            confidence = self._calculate_confidence_short(
                rsi=rsi, price=price, vwap=vwap, volume=market_data.volume
            )

            # For SHORT: stop loss is ABOVE entry, take profit is BELOW entry
            stop_loss = price * (1.0 + self.strategy_config.stop_loss_pct)
            take_profit = price * (1.0 - self.strategy_config.take_profit_pct)

            return self._create_sell_signal(
                symbol=symbol,
                confidence=confidence,
                rationale=(
                    f"Bearish EMA crossover (EMA8={ema_fast:.2f} < EMA21={ema_slow:.2f}), "
                    f"RSI {rsi:.1f} in bearish momentum range, price {price:.2f} < VWAP {vwap:.2f}"
                ),
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "ema_fast": ema_fast,
                    "ema_slow": ema_slow,
                    "rsi": rsi,
                    "vwap": vwap,
                    "vwap_distance_pct": ((price - vwap) / vwap) * 100,
                },
            )

        # Should never reach here, but safety fallback
        return self._create_hold_signal(
            symbol=symbol,
            rationale="Unknown crossover direction",
            confidence=0.0,
            metadata={"crossover": crossover_direction},
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _validate_indicators(self, market_data: MarketData) -> bool:
        """
        Validate that all required indicators are present in market data.

        Args:
            market_data: Market data snapshot

        Returns:
            True if all required indicators are non-None, False otherwise
        """
        required = [
            market_data.ema_fast,
            market_data.ema_slow,
            market_data.rsi,
            market_data.vwap,
        ]
        return all(ind is not None for ind in required)

    def _detect_crossover(self, current_fast: float, current_slow: float) -> str:
        """
        Detect EMA crossover based on current and previous values.

        Args:
            current_fast: Current EMA(8) value
            current_slow: Current EMA(21) value

        Returns:
            "bullish" if fast crossed above slow
            "bearish" if fast crossed below slow
            "none" if no crossover or first evaluation

        Logic:
            - Bullish: previous_fast <= previous_slow AND current_fast > current_slow
            - Bearish: previous_fast >= previous_slow AND current_fast < current_slow
            - None: First evaluation (no previous) or EMAs didn't cross
        """
        # First evaluation - no previous data
        if self._previous_ema_fast is None or self._previous_ema_slow is None:
            return "none"

        # Bullish crossover: fast crosses above slow
        if self._previous_ema_fast <= self._previous_ema_slow and current_fast > current_slow:
            return "bullish"

        # Bearish crossover: fast crosses below slow
        if self._previous_ema_fast >= self._previous_ema_slow and current_fast < current_slow:
            return "bearish"

        # No crossover
        return "none"

    def _calculate_confidence_long(
        self, rsi: float, price: float, vwap: float, volume: int
    ) -> float:
        """
        Calculate signal confidence for LONG positions.

        Args:
            rsi: RSI value (14-period)
            price: Current price
            vwap: Volume-weighted average price
            volume: Current volume

        Returns:
            Confidence score between 0.0 and 1.0

        Logic:
            - Base: 0.6 (Strategy A is directional)
            - Bonus: +0.1 if RSI in "sweet spot" (55-60)
            - Bonus: +0.1 if price significantly above VWAP (>0.2%)
            - Penalty: -0.2 if volume low (placeholder - needs volume average)
            - Clamped to [0.0, 1.0]
        """
        confidence = 0.6

        # RSI sweet spot bonus (55-60 is ideal momentum)
        if 55.0 <= rsi <= 60.0:
            confidence += 0.1

        # Strong price > VWAP bonus (>0.2% above)
        vwap_distance_pct = ((price - vwap) / vwap) * 100
        if vwap_distance_pct > 0.2:
            confidence += 0.1

        # Volume penalty (placeholder - would need 20-day average from data layer)
        # If volume < 50% of average, apply penalty
        # For now, skip this penalty since we don't have historical volume

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def _calculate_confidence_short(
        self, rsi: float, price: float, vwap: float, volume: int
    ) -> float:
        """
        Calculate signal confidence for SHORT positions.

        Args:
            rsi: RSI value (14-period)
            price: Current price
            vwap: Volume-weighted average price
            volume: Current volume

        Returns:
            Confidence score between 0.0 and 1.0

        Logic:
            - Base: 0.6 (Strategy A is directional)
            - Bonus: +0.1 if RSI in "sweet spot" (40-45)
            - Bonus: +0.1 if price significantly below VWAP (<-0.2%)
            - Penalty: -0.2 if volume low (placeholder)
            - Clamped to [0.0, 1.0]
        """
        confidence = 0.6

        # RSI sweet spot bonus (40-45 is ideal for shorts)
        if 40.0 <= rsi <= 45.0:
            confidence += 0.1

        # Strong price < VWAP bonus (<-0.2% below)
        vwap_distance_pct = ((price - vwap) / vwap) * 100
        if vwap_distance_pct < -0.2:
            confidence += 0.1

        # Volume penalty (placeholder - same as LONG)
        # Skip for now since we don't have historical volume average

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def __repr__(self) -> str:
        """String representation of Strategy A instance."""
        return f"StrategyA(config={self.strategy_config})"
