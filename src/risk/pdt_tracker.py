"""
Pattern Day Trader (PDT) tracking.

Monitors day trades within a rolling 5-business-day window.
FINRA PDT rule: 4+ day trades in 5 business days on a margin
account with < $25,000 triggers pattern day trader status.

This module:
- Tracks actual trade executions (not signals)
- Persists state across bot restarts
- Enforces hard limit of 3 day trades per window
- Uses business days (excludes weekends/holidays)

CRITICAL: PDT limit is 3, not 4. We stop at 3 to prevent
accidental triggering of PDT status.
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.risk.risk_types import DayTrade, PDTState

logger = logging.getLogger(__name__)


class MarketCalendar:
    """
    Simple market calendar that handles business days.

    For production, this can be extended to include market holidays
    using a library like exchange_calendars.
    """

    # Known US market holidays for 2026
    US_MARKET_HOLIDAYS_2026 = {
        date(2026, 1, 1),  # New Year's Day
        date(2026, 1, 19),  # MLK Day
        date(2026, 2, 16),  # Presidents' Day
        date(2026, 4, 3),  # Good Friday
        date(2026, 5, 25),  # Memorial Day
        date(2026, 7, 3),  # Independence Day (observed)
        date(2026, 9, 7),  # Labor Day
        date(2026, 11, 26),  # Thanksgiving
        date(2026, 12, 25),  # Christmas
    }

    def is_trading_day(self, check_date: date) -> bool:
        """Check if a date is a trading day."""
        # Weekend check
        if check_date.weekday() >= 5:
            return False
        # Holiday check
        if check_date in self.US_MARKET_HOLIDAYS_2026:
            return False
        return True

    def subtract_business_days(self, from_date: date, days: int) -> date:
        """Subtract business days from a date."""
        current = from_date
        remaining = days

        while remaining > 0:
            current -= timedelta(days=1)
            if self.is_trading_day(current):
                remaining -= 1

        return current

    def count_business_days_between(self, start_date: date, end_date: date) -> int:
        """Count business days between two dates (exclusive of start, inclusive of end)."""
        count = 0
        current = start_date + timedelta(days=1)
        while current <= end_date:
            if self.is_trading_day(current):
                count += 1
            current += timedelta(days=1)
        return count


class PDTTracker:
    """
    Tracks pattern day trading activity.

    A day trade occurs when a position is opened and closed
    on the same trading day. This class maintains a rolling
    5-business-day window of day trades and enforces the
    PDT limit.

    State is persisted to disk to survive bot restarts.
    """

    # Hard limit: 3 day trades per rolling 5-day window
    # (FINRA triggers at 4, we stay at 3 for safety margin)
    PDT_LIMIT = 3

    # Rolling window in business days
    WINDOW_DAYS = 5

    def __init__(
        self,
        trade_limit: int = 3,
        window_days: int = 5,
        state_file: Optional[Path] = None,
        market_calendar: Optional[MarketCalendar] = None,
    ) -> None:
        """
        Initialize PDT tracker.

        Args:
            trade_limit: Maximum day trades allowed in window (default 3)
            window_days: Rolling window in business days (default 5)
            state_file: Optional path to persist PDT state
            market_calendar: Optional market calendar for business days
        """
        self._trade_limit = trade_limit
        self._window_days = window_days
        self._state_file = state_file
        self._calendar = market_calendar or MarketCalendar()
        self._state = self._load_state() if state_file else PDTState()

    # =========================================================================
    # PRIMARY INTERFACE (Used by existing tests)
    # =========================================================================

    def can_open_day_trade(
        self,
        trades_in_window: Optional[List[date]] = None,
    ) -> bool:
        """
        Check if a day trade is allowed.

        Args:
            trades_in_window: Optional list of trade dates to check against.
                              If None, uses internal state.

        Returns:
            True if day trades remaining > 0, False otherwise
        """
        return self.trades_remaining(trades_in_window) > 0

    def trades_remaining(
        self,
        trades_in_window: Optional[List[date]] = None,
        as_of_date: Optional[date] = None,
    ) -> int:
        """
        Calculate day trades remaining in window.

        Args:
            trades_in_window: Optional list of trade dates.
                              If None, uses internal state.
            as_of_date: Date to calculate from (default: today)

        Returns:
            Number of day trades that can be made (0-3)
        """
        if as_of_date is None:
            as_of_date = date.today()

        if trades_in_window is not None:
            current_count = self._count_trades_in_window(trades_in_window, as_of_date)
        else:
            current_count = self._count_internal_trades_in_window(as_of_date)

        return max(0, self._trade_limit - current_count)

    def trades_used(self, as_of_date: Optional[date] = None) -> int:
        """
        Count day trades used in current window.

        Returns:
            Number of day trades already made (0-3+)
        """
        if as_of_date is None:
            as_of_date = date.today()
        return self._count_internal_trades_in_window(as_of_date)

    # =========================================================================
    # STATE PERSISTENCE
    # =========================================================================

    def to_state_dict(
        self,
        trades_in_window: Optional[List[date]] = None,
    ) -> Dict[str, Any]:
        """
        Serialize current state to dictionary.

        Args:
            trades_in_window: Optional trade dates to include

        Returns:
            Dictionary suitable for JSON serialization
        """
        if trades_in_window is not None:
            # Filter to only trades within window
            cutoff = self._get_window_start()
            valid_trades = [t for t in trades_in_window if t >= cutoff]
            trades_count = len(valid_trades)
        else:
            trades_count = self._count_internal_trades_in_window()

        return {
            "version": "1.0.0",
            "trades_in_window": trades_count,
            "trades_remaining": max(0, self._trade_limit - trades_count),
            "window_days": self._window_days,
            "trade_limit": self._trade_limit,
            "last_updated": datetime.now().isoformat(),
        }

    @classmethod
    def from_state_dict(
        cls,
        state: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Restore state from dictionary.

        Args:
            state: Serialized state dictionary

        Returns:
            Dictionary with restored state info
        """
        if state is None:
            return {"trades_remaining": 0}  # Safe default

        try:
            trades_in_window = state.get("trades_in_window", 0)
            trade_limit = state.get("trade_limit", 3)
            return {
                "trades_remaining": max(0, trade_limit - trades_in_window),
                "trades_in_window": trades_in_window,
            }
        except (KeyError, TypeError):
            # Corrupted state — return safe default
            return {"trades_remaining": 0}

    # =========================================================================
    # INTERNAL TRACKING (For RiskManager integration)
    # =========================================================================

    def can_day_trade(self) -> bool:
        """
        Check if a day trade is allowed using internal state.

        Returns:
            True if day trades remaining > 0, False otherwise
        """
        return self.trades_remaining() > 0

    def record_day_trade(
        self,
        symbol: str,
        entry_time: datetime,
        exit_time: datetime,
        contracts: int,
    ) -> bool:
        """
        Record a completed day trade.

        Call this AFTER a round-trip trade completes (position
        opened and closed same day).

        Args:
            symbol: The traded symbol
            entry_time: Timestamp of position entry
            exit_time: Timestamp of position exit
            contracts: Number of contracts in the round-trip

        Returns:
            True if recorded successfully, False if would exceed limit

        Raises:
            ValueError: If entry and exit are not same trading day
        """
        # Validate same trading day
        if not self._is_same_trading_day(entry_time, exit_time):
            raise ValueError(
                f"Entry ({entry_time.date()}) and exit ({exit_time.date()}) "
                "must be on same trading day"
            )

        # Check if this would exceed limit (should have been caught earlier)
        if not self.can_day_trade():
            return False

        trade = DayTrade(
            symbol=symbol,
            trade_date=entry_time.date(),
            entry_time=entry_time,
            exit_time=exit_time,
            contracts=contracts,
        )

        self._state.day_trades.append(trade)
        self._state.last_updated = datetime.now()
        self._save_state()

        return True

    def get_trades_in_window(self) -> List[DayTrade]:
        """
        Get all day trades in the current rolling window.

        Returns:
            List of DayTrade records within the window
        """
        cutoff = self._get_window_start()
        return [t for t in self._state.day_trades if t.trade_date >= cutoff]

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _count_trades_in_window(
        self,
        trades: List[date],
        as_of_date: date,
    ) -> int:
        """Count day trades within the rolling window."""
        cutoff = self._get_window_start(as_of_date)
        return sum(1 for t in trades if t >= cutoff)

    def _count_internal_trades_in_window(
        self,
        as_of_date: Optional[date] = None,
    ) -> int:
        """Count internal day trades within the rolling window."""
        cutoff = self._get_window_start(as_of_date)
        return sum(1 for t in self._state.day_trades if t.trade_date >= cutoff)

    def _get_window_start(self, as_of_date: Optional[date] = None) -> date:
        """
        Calculate the start of the rolling 5-business-day window.

        Counts back 5 business days from the reference date.
        """
        if as_of_date is None:
            as_of_date = date.today()

        return self._calendar.subtract_business_days(as_of_date, self._window_days)

    def _is_same_trading_day(
        self,
        time1: datetime,
        time2: datetime,
    ) -> bool:
        """
        Check if two timestamps are on the same trading day.

        Note: This considers the calendar date, not the trading
        session. Overnight positions that span midnight are NOT
        day trades.
        """
        return time1.date() == time2.date()

    def _load_state(self) -> PDTState:
        """Load persisted state from disk."""
        if self._state_file is None or not self._state_file.exists():
            return PDTState()

        try:
            with open(self._state_file, "r") as f:
                data = json.load(f)

            day_trades = [DayTrade.from_dict(t) for t in data.get("day_trades", [])]
            last_updated = datetime.fromisoformat(
                data.get("last_updated", datetime.now().isoformat())
            )

            return PDTState(day_trades=day_trades, last_updated=last_updated)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Corrupted state file — start fresh but log warning
            logger.warning(f"Corrupted PDT state file, starting fresh: {e}")
            return PDTState()

    def _save_state(self) -> None:
        """Persist current state to disk."""
        if self._state_file is None:
            return

        # Prune old trades outside the window before saving
        self._prune_old_trades()

        data = {
            "version": "1.0.0",
            "day_trades": [t.to_dict() for t in self._state.day_trades],
            "last_updated": self._state.last_updated.isoformat(),
        }

        # Ensure parent directory exists
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        # On Windows, we need to remove the target first if it exists
        temp_file = self._state_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)

        # Remove target if exists (for Windows compatibility)
        if self._state_file.exists():
            self._state_file.unlink()
        temp_file.rename(self._state_file)

    def _prune_old_trades(self) -> None:
        """Remove trades outside the rolling window."""
        cutoff = self._get_window_start()
        self._state.day_trades = [t for t in self._state.day_trades if t.trade_date >= cutoff]
