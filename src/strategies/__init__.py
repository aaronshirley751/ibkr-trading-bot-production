"""
Strategy layer for the Crucible trading system.

This package provides:
- StrategyBase: Abstract base class for all strategies
- Signal: Trading signal dataclass
- Direction, StrategyType: Core enums
- MarketData: Input contract for strategy evaluation
- Configuration classes for each strategy

USAGE:
    from src.strategies import StrategyBase, Signal, Direction, MarketData

    class MyStrategy(StrategyBase):
        def evaluate(self, market_data: MarketData) -> Signal:
            # Implementation here
            pass
"""

from .base import Direction, MarketData, Signal, StrategyBase, StrategyType
from .config import (
    StrategyAConfig,
    StrategyBConfig,
    StrategyCConfig,
    StrategyConfig,
)
from .strategy_a import StrategyA
from .strategy_b import StrategyB
from .strategy_c import StrategyC

__all__ = [
    # Core classes
    "StrategyBase",
    "Signal",
    "MarketData",
    # Enums
    "Direction",
    "StrategyType",
    # Configuration
    "StrategyConfig",
    "StrategyAConfig",
    "StrategyBConfig",
    "StrategyCConfig",
    # Concrete strategies
    "StrategyA",
    "StrategyB",
    "StrategyC",
]
