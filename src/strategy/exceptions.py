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
