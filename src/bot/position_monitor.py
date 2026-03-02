"""
Position monitor — tracks open positions and evaluates automated exit conditions.

Exit triggers (evaluated in priority order each cycle):
  1. Stop-loss      — current_price <= entry_price * (1 - stop_loss_pct)
  2. Take-profit    — current_price >= entry_price * (1 + take_profit_pct)
  3. Time-stop      — elapsed minutes since entry >= time_stop_minutes
  4. DTE force-close — options DTE <= force_close_dte (Strategy C path)

Design principles:
  - Closing positions is ALWAYS allowed — CRO mandate, even with circuit
    breaker OPEN.
  - Thread-hostile: must be accessed from a single thread (the trading loop).
  - Pure evaluation logic; no I/O.  Callers (TradingLoop) are responsible for
    fetching current prices and submitting closing orders.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class OpenPosition:
    """Represents a single tracked open position."""

    symbol: str
    entry_price: float  # per-share premium at fill
    entry_time: datetime
    quantity: int
    order_id: int
    take_profit_pct: float = 0.15
    stop_loss_pct: float = 0.25
    time_stop_minutes: int = 90
    force_close_dte: int = 1
    expiry_date: Optional[datetime] = field(default=None)
    """Options expiry as a timezone-aware datetime; None for non-option underlyings."""


@dataclass
class ExitSignal:
    """Result of evaluating a position against all exit conditions."""

    should_exit: bool
    reason: Optional[str]
    """One of: 'stop_loss' | 'take_profit' | 'time_stop' | 'dte_force_close' | None"""
    details: str = ""


# ---------------------------------------------------------------------------
# PositionMonitor
# ---------------------------------------------------------------------------


class PositionMonitor:
    """
    Tracks open positions and evaluates exit conditions each cycle.

    Usage::

        monitor = PositionMonitor()

        # Register a position after a fill
        monitor.add_position(OpenPosition(
            symbol="QQQ",
            entry_price=1.42,
            entry_time=datetime.now(timezone.utc),
            quantity=1,
            order_id=7,
            take_profit_pct=0.15,
            stop_loss_pct=0.25,
            time_stop_minutes=90,
        ))

        # Each evaluation cycle
        signal = monitor.evaluate("QQQ", current_price=1.18)
        if signal.should_exit:
            # ... submit closing order, then:
            monitor.remove_position("QQQ")
    """

    def __init__(self) -> None:
        self._positions: Dict[str, OpenPosition] = {}

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def add_position(self, position: OpenPosition) -> None:
        """Register a newly filled position for monitoring."""
        self._positions[position.symbol] = position
        logger.info(
            "PositionMonitor: tracking %s  entry=%.4f  qty=%d  order_id=%d",
            position.symbol,
            position.entry_price,
            position.quantity,
            position.order_id,
        )

    def remove_position(self, symbol: str) -> None:
        """Deregister a position after it has been closed."""
        removed = self._positions.pop(symbol, None)
        if removed is not None:
            logger.info("PositionMonitor: removed %s (was order_id=%d)", symbol, removed.order_id)

    def has_open_positions(self) -> bool:
        """Return True if at least one position is currently tracked."""
        return bool(self._positions)

    def get_positions(self) -> List[OpenPosition]:
        """Return a snapshot list of all tracked positions."""
        return list(self._positions.values())

    def get_position(self, symbol: str) -> Optional[OpenPosition]:
        """Return the tracked position for a symbol, or None if not found."""
        return self._positions.get(symbol)

    # ------------------------------------------------------------------
    # Exit evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        symbol: str,
        current_price: float,
        now: Optional[datetime] = None,
    ) -> ExitSignal:
        """
        Evaluate all exit conditions for a tracked position.

        Conditions are tested in priority order (stop-loss before take-profit
        so that a gap-down past both thresholds always records the stop-loss).

        Args:
            symbol: Symbol to evaluate.
            current_price: Current bid price (what the position can be sold for).
            now: Override current UTC time (for testing); defaults to
                ``datetime.now(timezone.utc)``.

        Returns:
            ExitSignal — ``should_exit=True`` when any condition is met, along
            with the exit reason and human-readable details.
        """
        position = self._positions.get(symbol)
        if position is None:
            return ExitSignal(should_exit=False, reason=None, details="no_position_tracked")

        effective_now = now if now is not None else datetime.now(timezone.utc)

        # 1. Stop-loss -------------------------------------------------------
        stop_price = position.entry_price * (1.0 - position.stop_loss_pct)
        if current_price <= stop_price:
            pct = (current_price - position.entry_price) / position.entry_price * 100.0
            return ExitSignal(
                should_exit=True,
                reason="stop_loss",
                details=(
                    f"current={current_price:.4f}  " f"stop={stop_price:.4f}  " f"change={pct:.1f}%"
                ),
            )

        # 2. Take-profit -----------------------------------------------------
        tp_price = position.entry_price * (1.0 + position.take_profit_pct)
        if current_price >= tp_price:
            pct = (current_price - position.entry_price) / position.entry_price * 100.0
            return ExitSignal(
                should_exit=True,
                reason="take_profit",
                details=(
                    f"current={current_price:.4f}  "
                    f"target={tp_price:.4f}  "
                    f"change=+{pct:.1f}%"
                ),
            )

        # 3. Time-stop -------------------------------------------------------
        elapsed_minutes = (effective_now - position.entry_time).total_seconds() / 60.0
        if elapsed_minutes >= position.time_stop_minutes:
            return ExitSignal(
                should_exit=True,
                reason="time_stop",
                details=(
                    f"elapsed={elapsed_minutes:.0f}m  " f"limit={position.time_stop_minutes}m"
                ),
            )

        # 4. DTE force-close -------------------------------------------------
        if position.expiry_date is not None:
            expiry = position.expiry_date
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            dte = (expiry.date() - effective_now.date()).days
            if dte <= position.force_close_dte:
                return ExitSignal(
                    should_exit=True,
                    reason="dte_force_close",
                    details=(f"dte={dte}  " f"threshold={position.force_close_dte}"),
                )

        return ExitSignal(should_exit=False, reason=None, details="hold")
