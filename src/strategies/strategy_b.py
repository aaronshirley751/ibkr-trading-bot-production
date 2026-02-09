"""
Strategy B: Mean Reversion Fade (Choppy Markets).

Deployed when VIX 18-25 for choppy, elevated-volatility market conditions.
Uses RSI extremes with Bollinger Band confirmation to fade overextended moves.

ENTRY CONDITIONS (LONG - Fade Oversold):
- RSI ≤ 30 — deeply oversold
- Price touches or breaches lower Bollinger Band (close ≤ BB_lower)
- Both conditions must be true simultaneously

ENTRY CONDITIONS (SHORT - Fade Overbought):
- RSI ≥ 70 — deeply overbought
- Price touches or breaches upper Bollinger Band (close ≥ BB_upper)
- Both conditions must be true simultaneously

CONFIDENCE CALCULATION:
- Base: 0.5 (mean reversion less reliable than momentum)
- Bonus: +0.15 if RSI extreme (≤25 for LONG, ≥75 for SHORT)
- Bonus: +0.1 if price breaches BB (not just touches)
- Penalty: -0.15 if VIX outside Strategy B range [18, 25]
- Clamped to [0.0, 1.0]

EXIT STRATEGY:
- Take profit: 8% gain (quick scalp)
- Stop loss: 15% loss (tighter than Strategy A)
- Time stop: 45 minutes (enforced at execution layer)

NOTE: This strategy calculates RSI and Bollinger Bands from historical price data.
If historical data is insufficient, the strategy returns HOLD signal.
"""

from typing import List, Optional, Tuple

from .base import MarketData, Signal, StrategyBase, StrategyType
from .config import StrategyBConfig


class StrategyB(StrategyBase):
    """
    Strategy B: Mean Reversion Fade for choppy markets.

    Uses RSI oversold/overbought extremes with Bollinger Band touch confirmation
    to identify high-probability mean reversion opportunities. Designed for
    VIX 18-25 conditions.

    Attributes:
        strategy_config: StrategyBConfig with RSI/BB parameters
    """

    def __init__(self, config: Optional[StrategyBConfig] = None):
        """
        Initialize Strategy B with configuration.

        Args:
            config: StrategyBConfig instance. Uses defaults if not provided.
        """
        super().__init__(strategy_type=StrategyType.B, config=None)
        self.strategy_config: StrategyBConfig = config or StrategyBConfig()

    def evaluate(self, market_data: MarketData) -> Signal:
        """
        Evaluate market data and generate mean reversion signal.

        Args:
            market_data: Current market snapshot with historical price data

        Returns:
            Signal with direction (BUY/SELL/HOLD), confidence, and exit levels

        Logic:
            1. Extract historical data and validate sufficiency
            2. Calculate RSI from historical prices
            3. Calculate Bollinger Bands from historical prices
            4. Check for oversold condition (LONG signal)
            5. Check for overbought condition (SHORT signal)
            6. Calculate confidence based on signal strength and VIX regime
            7. Return Signal with entry/stop/target prices
        """
        symbol = market_data.symbol
        price = market_data.price

        # Strategy B uses pre-computed indicators if available, otherwise needs historical data
        # Check if we can use pre-computed indicators
        if (
            market_data.rsi is not None
            and market_data.bollinger_upper is not None
            and market_data.bollinger_lower is not None
        ):
            rsi = market_data.rsi
            bb_upper = market_data.bollinger_upper
            bb_lower = market_data.bollinger_lower
            bb_middle = (
                market_data.bollinger_middle
                if market_data.bollinger_middle is not None
                else (bb_upper + bb_lower) / 2
            )
        else:
            # Need to calculate from historical data (not available in current MarketData)
            # For now, return HOLD if indicators not pre-computed
            return self._create_hold_signal(
                symbol=symbol,
                rationale="Insufficient data: RSI and Bollinger Bands not pre-computed",
                confidence=0.0,
                metadata={"reason": "missing_indicators"},
            )

        # Get VIX for regime validation (optional - won't fail if missing)
        vix: Optional[float] = getattr(market_data, "vix", None)

        # Check for LONG signal (fade oversold)
        if rsi <= self.strategy_config.rsi_oversold:
            if price <= bb_lower:
                # All conditions met - generate LONG signal
                confidence = self._calculate_confidence_long(
                    rsi=rsi, price=price, bb_lower=bb_lower, vix=vix
                )

                stop_loss = price * (1.0 - self.strategy_config.stop_loss_pct)
                take_profit = price * (1.0 + self.strategy_config.take_profit_pct)

                return self._create_buy_signal(
                    symbol=symbol,
                    confidence=confidence,
                    rationale=(
                        f"Oversold mean reversion: RSI {rsi:.1f} ≤ {self.strategy_config.rsi_oversold}, "
                        f"price {price:.2f} ≤ BB_lower {bb_lower:.2f}"
                    ),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        "rsi": rsi,
                        "bb_upper": bb_upper,
                        "bb_middle": bb_middle,
                        "bb_lower": bb_lower,
                        "vix": vix,
                        "signal_type": "fade_oversold",
                    },
                )

        # Check for SHORT signal (fade overbought)
        if rsi >= self.strategy_config.rsi_overbought:
            if price >= bb_upper:
                # All conditions met - generate SHORT signal
                confidence = self._calculate_confidence_short(
                    rsi=rsi, price=price, bb_upper=bb_upper, vix=vix
                )

                # For SHORT: stop loss is ABOVE entry, take profit is BELOW entry
                stop_loss = price * (1.0 + self.strategy_config.stop_loss_pct)
                take_profit = price * (1.0 - self.strategy_config.take_profit_pct)

                return self._create_sell_signal(
                    symbol=symbol,
                    confidence=confidence,
                    rationale=(
                        f"Overbought mean reversion: RSI {rsi:.1f} ≥ {self.strategy_config.rsi_overbought}, "
                        f"price {price:.2f} ≥ BB_upper {bb_upper:.2f}"
                    ),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    metadata={
                        "rsi": rsi,
                        "bb_upper": bb_upper,
                        "bb_middle": bb_middle,
                        "bb_lower": bb_lower,
                        "vix": vix,
                        "signal_type": "fade_overbought",
                    },
                )

        # No signal conditions met
        return self._create_hold_signal(
            symbol=symbol,
            rationale=f"No mean reversion setup: RSI {rsi:.1f}, price {price:.2f} not at BB extremes",
            confidence=0.0,
            metadata={
                "rsi": rsi,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "reason": "conditions_not_met",
            },
        )

    # =========================================================================
    # INDICATOR CALCULATION HELPERS
    # =========================================================================

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            prices: List of historical closing prices
            period: RSI period (default 14)

        Returns:
            RSI value between 0 and 100

        Formula:
            RSI = 100 - (100 / (1 + RS))
            where RS = Average Gain / Average Loss over period

        Raises:
            ValueError: If insufficient data points (need at least period + 1)
        """
        if len(prices) < period + 1:
            raise ValueError(
                f"Insufficient data for RSI calculation: need {period + 1} points, got {len(prices)}"
            )

        gains: List[float] = []
        losses: List[float] = []

        # Calculate price changes
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))

        # Calculate average gain and loss over period
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        # Handle edge case: all gains (no losses)
        if avg_loss == 0:
            return 100.0

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi

    def calculate_bollinger_bands(
        self, prices: List[float], period: int = 20, std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """
        Calculate Bollinger Bands.

        Args:
            prices: List of historical closing prices
            period: Moving average period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)

        Returns:
            Tuple of (upper_band, middle_band, lower_band)

        Formula:
            BB_middle = Simple Moving Average (SMA) over period
            BB_upper = SMA + (std_dev * standard_deviation)
            BB_lower = SMA - (std_dev * standard_deviation)

        Raises:
            ValueError: If insufficient data points (need at least period)
        """
        if len(prices) < period:
            raise ValueError(
                f"Insufficient data for Bollinger Bands: need {period} points, got {len(prices)}"
            )

        # Calculate SMA (middle band) using most recent period prices
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period

        # Calculate standard deviation
        variance = sum((p - sma) ** 2 for p in recent_prices) / period
        std = variance**0.5

        # Handle edge case: all prices identical (std = 0)
        if std == 0:
            # Bands collapse to SMA
            return (sma, sma, sma)

        # Calculate upper and lower bands
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)

        return (upper_band, sma, lower_band)

    # =========================================================================
    # CONFIDENCE CALCULATION HELPERS
    # =========================================================================

    def _calculate_confidence_long(
        self, rsi: float, price: float, bb_lower: float, vix: Optional[float]
    ) -> float:
        """
        Calculate signal confidence for LONG positions (fade oversold).

        Args:
            rsi: RSI value
            price: Current price
            bb_lower: Lower Bollinger Band
            vix: Current VIX level (optional)

        Returns:
            Confidence score between 0.0 and 1.0

        Logic:
            - Base: 0.5 (mean reversion baseline)
            - Bonus: +0.15 if RSI extreme (≤25)
            - Bonus: +0.1 if price breaches BB (< bb_lower)
            - Penalty: -0.15 if VIX outside [18, 25]
            - Clamped to [0.0, 1.0]
        """
        confidence = 0.5

        # Extreme oversold bonus (RSI ≤ 25)
        if rsi <= 25.0:
            confidence += 0.15

        # Bollinger Band breach bonus (price < lower band, not just touching)
        if price < bb_lower:
            confidence += 0.1

        # VIX regime penalty (Strategy B expects VIX 18-25)
        if vix is not None:
            if vix < 18.0 or vix > 25.0:
                confidence -= 0.15

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def _calculate_confidence_short(
        self, rsi: float, price: float, bb_upper: float, vix: Optional[float]
    ) -> float:
        """
        Calculate signal confidence for SHORT positions (fade overbought).

        Args:
            rsi: RSI value
            price: Current price
            bb_upper: Upper Bollinger Band
            vix: Current VIX level (optional)

        Returns:
            Confidence score between 0.0 and 1.0

        Logic:
            - Base: 0.5 (mean reversion baseline)
            - Bonus: +0.15 if RSI extreme (≥75)
            - Bonus: +0.1 if price breaches BB (> bb_upper)
            - Penalty: -0.15 if VIX outside [18, 25]
            - Clamped to [0.0, 1.0]
        """
        confidence = 0.5

        # Extreme overbought bonus (RSI ≥ 75)
        if rsi >= 75.0:
            confidence += 0.15

        # Bollinger Band breach bonus (price > upper band, not just touching)
        if price > bb_upper:
            confidence += 0.1

        # VIX regime penalty (Strategy B expects VIX 18-25)
        if vix is not None:
            if vix < 18.0 or vix > 25.0:
                confidence -= 0.15

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def __repr__(self) -> str:
        """String representation of Strategy B instance."""
        return f"StrategyB(config={self.strategy_config})"
