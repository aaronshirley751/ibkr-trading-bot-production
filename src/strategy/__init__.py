"""
Strategy layer for Charter & Stone Capital trading bot.

This module provides:
- Technical signal generation (EMA, RSI, VWAP, Bollinger Bands)
- VIX-based regime detection and strategy selection
- Gameplan validation and execution pipeline
- Catalyst override processing

Strategy Library:
    A (Momentum Breakout): VIX < 18, trending markets
    B (Mean Reversion Fade): VIX 18-25, choppy markets
    C (Cash Preservation): VIX > 25, crisis, or any safety trigger

Safety Principle: All failure modes default to Strategy C (no trading).

Usage:
    >>> from src.strategy.selection import detect_regime, select_strategy
    >>> from src.strategy.signals import evaluate_strategy_a_signal
    >>> from src.strategy.execution import load_gameplan, evaluate_signals
"""

from .selection import detect_regime, select_strategy
from .signals import (
    calculate_ema_crossover,
    calculate_rsi,
    check_bollinger_touch,
    check_vwap_confirmation,
    evaluate_strategy_a_signal,
    evaluate_strategy_b_signal,
)
from .execution import evaluate_signals, load_gameplan
from .exceptions import (
    GameplanValidationError,
    InsufficientDataError,
    RegimeDetectionError,
    SignalCalculationError,
    StrategyError,
    StrategySelectionError,
)

__all__ = [
    # Selection
    "detect_regime",
    "select_strategy",
    # Signals
    "calculate_ema_crossover",
    "calculate_rsi",
    "check_vwap_confirmation",
    "check_bollinger_touch",
    "evaluate_strategy_a_signal",
    "evaluate_strategy_b_signal",
    # Execution
    "load_gameplan",
    "evaluate_signals",
    # Exceptions
    "StrategyError",
    "SignalCalculationError",
    "InsufficientDataError",
    "RegimeDetectionError",
    "GameplanValidationError",
    "StrategySelectionError",
]

__version__ = "0.1.0"
