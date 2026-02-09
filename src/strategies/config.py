"""
Strategy configuration dataclasses.

Each strategy (A, B, C) has configurable parameters within defined ranges.
This module provides the configuration structure.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StrategyAConfig:
    """
    Configuration for Strategy A: Momentum Breakout.

    Deployed when: VIX < 18, trending markets
    """

    # Symbol selection
    symbols: List[str] = field(default_factory=lambda: ["SPY", "QQQ"])
    max_symbols: int = 2

    # EMA parameters
    ema_fast_period: int = 8
    ema_slow_period: int = 21

    # RSI parameters
    rsi_period: int = 14
    rsi_min: float = 50.0  # Must be above this
    rsi_max: float = 65.0  # Must be below this

    # VWAP condition
    require_above_vwap: bool = True

    # Risk parameters (defaults from account parameters)
    max_risk_pct: float = 0.03  # 3% of capital ($18 on $600)
    max_position_pct: float = 0.20  # 20% of capital ($120 on $600)

    # Exit parameters
    take_profit_pct: float = 0.15  # 15%
    stop_loss_pct: float = 0.25  # 25%
    time_stop_minutes: int = 90

    # Options parameters
    min_dte: int = 2  # Never 0DTE
    moneyness: str = "ATM"  # At-the-money


@dataclass
class StrategyBConfig:
    """
    Configuration for Strategy B: Mean Reversion Fade.

    Deployed when: VIX 18-25, choppy markets
    """

    # Symbol selection
    symbols: List[str] = field(default_factory=lambda: ["SPY"])
    max_symbols: int = 1

    # RSI parameters
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0

    # Bollinger Band parameters
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    require_band_touch: bool = True

    # Risk parameters (more conservative than A)
    max_risk_pct: float = 0.02  # 2% of capital ($12 on $600)
    max_position_pct: float = 0.10  # 10% of capital ($60 on $600)

    # Exit parameters
    take_profit_pct: float = 0.08  # 8% (quick scalp)
    stop_loss_pct: float = 0.15  # 15% (tighter)
    time_stop_minutes: int = 45

    # Options parameters
    min_dte: int = 5  # More time for reversion
    moneyness: str = "OTM1"  # 1 strike out-of-the-money


@dataclass
class StrategyCConfig:
    """
    Configuration for Strategy C: Cash Preservation.

    Deployed when: VIX > 25, crisis, or default fallback

    CRITICAL: Strategy C NEVER initiates new positions.
    It only manages existing positions (force-close at 3 DTE).
    """

    # Symbol selection (none - no new entries)
    symbols: List[str] = field(default_factory=list)
    max_symbols: int = 0

    # Risk parameters
    max_risk_pct: float = 0.0  # Zero new risk
    max_position_pct: float = 0.0  # Zero new positions

    # Position management
    force_close_dte: int = 3  # Close all at 3 DTE
    emergency_stop_pct: float = 0.40  # 40% loss hard stop

    # Mode
    mode: str = "alert_only"  # Monitor and report, do not trade


@dataclass
class StrategyConfig:
    """
    Unified strategy configuration container.

    Holds configuration for whichever strategy is active.
    """

    strategy_a: Optional[StrategyAConfig] = None
    strategy_b: Optional[StrategyBConfig] = None
    strategy_c: Optional[StrategyCConfig] = None

    @classmethod
    def default_for_a(cls) -> "StrategyConfig":
        """Create config with Strategy A defaults."""
        return cls(strategy_a=StrategyAConfig())

    @classmethod
    def default_for_b(cls) -> "StrategyConfig":
        """Create config with Strategy B defaults."""
        return cls(strategy_b=StrategyBConfig())

    @classmethod
    def default_for_c(cls) -> "StrategyConfig":
        """Create config with Strategy C defaults."""
        return cls(strategy_c=StrategyCConfig())
