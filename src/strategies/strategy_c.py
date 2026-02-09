"""
Strategy C: Cash Preservation (Crisis Response / Default Fallback).

Deployed when VIX > 25, during crisis conditions, when data quality fails,
or when the Morning Gauntlet misses deadline. Strategy C's sole purpose is
capital preservation — it does not generate new trade signals, only manages
the safe exit of existing positions.

CRITICAL: Strategy C NEVER initiates new positions.
It only monitors and triggers closure of existing positions under two conditions:
1. Position at or below 3 DTE (Days To Expiry) — force close before expiry
2. Position loss >= 40% (emergency stop)

ENTRY CONDITIONS:
- None. Strategy C does not enter positions.

EXIT CONDITIONS (for existing positions):
- Force close: Position DTE <= 3 days
- Emergency stop: Position loss >= 40%

CONFIDENCE CALCULATION:
- Always 0.0 (never passes confidence gate)

SIGNAL GENERATION:
- Always returns HOLD (NEUTRAL) with confidence 0.0
- Never returns BUY or SELL signals

INTEGRATION:
- Orchestrator must reject all new entry signals when Strategy C is active
- Orchestrator calls should_close_position() to determine position closure
- Risk layer enforces max_risk_pct=0 and max_position_pct=0 when Strategy C is active

FAIL-SAFE DESIGN:
- evaluate() never raises exceptions (always returns HOLD on error)
- should_close_position() never raises exceptions (returns False on invalid input)
- This is the system-wide safety net — it must always work
"""

from typing import Optional

from .base import MarketData, Signal, StrategyBase, StrategyType
from .config import StrategyCConfig


class StrategyC(StrategyBase):
    """
    Strategy C: Cash Preservation for crisis conditions and system fallback.

    This is the fail-safe default strategy for the Crucible system. It is
    activated during crisis conditions (VIX > 25), when data quality fails,
    when the Morning Gauntlet misses deadline, or when any system component
    cannot determine a safe trading posture.

    Strategy C does not generate trade entry signals. It only manages the
    safe exit of existing positions via closure rules.

    Attributes:
        strategy_config: StrategyCConfig with force_close_dte and emergency_stop_pct
    """

    def __init__(self, config: Optional[StrategyCConfig] = None):
        """
        Initialize Strategy C with configuration.

        Args:
            config: StrategyCConfig instance. Uses defaults if not provided.
                Default values:
                - force_close_dte: 3 (close positions at 3 days to expiry)
                - emergency_stop_pct: 0.40 (40% loss triggers immediate close)
                - max_risk_pct: 0.0 (no new risk allowed)
                - max_position_pct: 0.0 (no new positions allowed)
        """
        super().__init__(strategy_type=StrategyType.C, config=None)
        self.strategy_config: StrategyCConfig = config or StrategyCConfig()

    def evaluate(self, market_data: MarketData) -> Signal:
        """
        Evaluate market data and return HOLD signal.

        Strategy C never generates BUY or SELL signals. This method always
        returns HOLD (NEUTRAL) with confidence 0.0, ensuring the signal
        fails the confidence gate (threshold 0.5).

        The orchestrator is responsible for:
        1. Closing existing positions at 3 DTE (config.force_close_dte)
        2. Applying emergency stop (40% loss) on any position
        3. Rejecting any new entry signals when Strategy C is active

        This method exists only to satisfy the StrategyBase interface.
        All position management happens at the orchestrator/risk layer.

        Args:
            market_data: Current market snapshot (ignored by Strategy C)

        Returns:
            Signal with direction=HOLD, confidence=0.0, and no price levels

        Error Handling:
            Never raises exceptions. If market_data is None or invalid,
            returns HOLD signal with current timestamp (fail-safe).
        """
        try:
            symbol = market_data.symbol if market_data else "UNKNOWN"
        except (AttributeError, TypeError):
            # Defensive: market_data is malformed
            symbol = "UNKNOWN"

        return self._create_hold_signal(
            symbol=symbol,
            rationale=(
                "Strategy C active: Cash Preservation mode. "
                "No new positions allowed. Monitoring existing positions only."
            ),
            confidence=0.0,
            metadata={
                "strategy": "C",
                "mode": "cash_preservation",
                "force_close_dte": self.strategy_config.force_close_dte,
                "emergency_stop_pct": self.strategy_config.emergency_stop_pct,
            },
        )

    def should_close_position(
        self, position_dte: Optional[int], position_pnl_pct: Optional[float]
    ) -> bool:
        """
        Determine if an existing position should be closed under Strategy C rules.

        This helper method is called by the orchestrator/risk layer to decide
        whether to close an existing position. Strategy C forces position closure
        under two conditions:

        1. Position is at or below force_close_dte (default 3 days to expiry)
        2. Position loss exceeds emergency_stop_pct (default 40% loss)

        Args:
            position_dte: Days to expiry for the position (e.g., 3, 2, 1, 0).
                None or negative values are treated as invalid (safe default: don't close).
            position_pnl_pct: Current profit/loss as percentage.
                Positive = profit (e.g., 0.20 for +20%).
                Negative = loss (e.g., -0.15 for -15% loss).
                None or NaN values are treated as invalid (safe default: don't close).

        Returns:
            True if position should be closed (either DTE or loss threshold met).
            False if position should remain open (or inputs are invalid).

        Closure Logic:
            - position_dte <= force_close_dte → Close (force close at 3 DTE)
            - position_pnl_pct <= -emergency_stop_pct → Close (40% loss stop)
            - Otherwise → Don't close

        Error Handling:
            Never raises exceptions. Invalid inputs return False (safe default).

        Examples:
            >>> config = StrategyCConfig()  # force_close_dte=3, emergency_stop_pct=0.40
            >>> strategy = StrategyC(config)
            >>> strategy.should_close_position(dte=3, pnl_pct=0.0)
            True  # At 3 DTE threshold, close
            >>> strategy.should_close_position(dte=4, pnl_pct=-0.10)
            False  # Above threshold and loss < 40%, don't close
            >>> strategy.should_close_position(dte=10, pnl_pct=-0.50)
            True  # Loss exceeds 40% emergency stop, close immediately
            >>> strategy.should_close_position(dte=None, pnl_pct=0.0)
            False  # Invalid DTE, fail-safe: don't close
        """
        # Validate inputs (fail-safe: return False if invalid)
        if position_dte is None or position_pnl_pct is None:
            return False

        # Check for NaN (floating point comparison edge case)
        try:
            if position_pnl_pct != position_pnl_pct:  # NaN check
                return False
        except (TypeError, ValueError):
            return False

        # Validate DTE is non-negative (negative DTE is invalid)
        # Note: DTE=0 is valid (at expiry) and should trigger closure
        if position_dte < 0:
            return False

        # Condition 1: Force close at or below DTE threshold
        # Use <= to include the threshold (e.g., 3 DTE triggers close)
        if position_dte <= self.strategy_config.force_close_dte:
            return True

        # Condition 2: Emergency stop on large losses
        # Note: Position loss is negative (e.g., -0.40 for -40% loss)
        # Use <= to include the threshold (e.g., exactly -40% triggers close)
        if position_pnl_pct <= -self.strategy_config.emergency_stop_pct:
            return True

        # Neither condition met: monitor but don't close
        return False
