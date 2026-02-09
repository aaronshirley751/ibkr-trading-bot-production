"""
Drawdown monitoring and circuit breakers.

Monitors:
1. Daily loss limit (10% of account) — halts trading for the day
2. Weekly drawdown governor (15%) — locks Strategy C for the week

State persists across restarts. Weekly governor resets Sunday at midnight.
All limits are pre-trade enforcement, not post-trade detection.
"""

import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.risk.risk_types import DrawdownState

logger = logging.getLogger(__name__)


class DrawdownMonitor:
    """
    Monitors account drawdown at daily and weekly levels.

    This class enforces two circuit breakers:

    1. Daily Loss Limit (10%):
       - If today's losses exceed 10% of day-start equity
       - Trading halts for remainder of day
       - Resets at market open next day

    2. Weekly Drawdown Governor (15%):
       - If week's losses exceed 15% of week-start equity
       - Strategy C locks for remainder of week
       - Resets Sunday at midnight (before Monday open)

    Both limits are enforced PRE-TRADE. The system will not
    enter a trade that could exceed these limits.
    """

    # Daily loss limit as fraction of day-start equity
    DAILY_LOSS_LIMIT_PCT = Decimal("0.10")

    # Weekly drawdown governor trigger level
    WEEKLY_GOVERNOR_PCT = Decimal("0.15")

    def __init__(
        self,
        starting_equity: Decimal,
        state_file: Optional[Path] = None,
        daily_loss_limit_pct: Optional[Decimal] = None,
        weekly_governor_pct: Optional[Decimal] = None,
    ) -> None:
        """
        Initialize drawdown monitor.

        Args:
            starting_equity: Initial account equity
            state_file: Path to persist drawdown state
            daily_loss_limit_pct: Optional override for daily limit (default 0.10)
            weekly_governor_pct: Optional override for weekly governor (default 0.15)
        """
        self._state_file = state_file
        self._starting_equity = starting_equity

        if daily_loss_limit_pct is not None:
            self.DAILY_LOSS_LIMIT_PCT = daily_loss_limit_pct
        if weekly_governor_pct is not None:
            self.WEEKLY_GOVERNOR_PCT = weekly_governor_pct

        self._state = self._load_or_initialize_state()

    # =========================================================================
    # EQUITY UPDATES
    # =========================================================================

    def update_equity(self, current_equity: Decimal) -> None:
        """
        Update current equity and check circuit breakers.

        Call this after any position change or P&L update.

        Args:
            current_equity: Current account equity
        """
        self._state.current_equity = current_equity
        self._state.last_updated = datetime.now()

        # Check if weekly governor should trigger
        if not self._state.governor_active:
            if self._state.weekly_drawdown_pct >= self.WEEKLY_GOVERNOR_PCT:
                self._state.governor_active = True
                self._state.governor_triggered_at = datetime.now()
                logger.warning(
                    f"Weekly drawdown governor ACTIVATED at "
                    f"{float(self._state.weekly_drawdown_pct):.1%}"
                )

        self._save_state()

    def record_realized_pnl(self, pnl: Decimal) -> None:
        """
        Record realized P&L from a closed position.

        Args:
            pnl: Realized profit (positive) or loss (negative)
        """
        self._state.realized_pnl_today += pnl
        self._state.realized_pnl_week += pnl
        self._state.last_updated = datetime.now()
        self._save_state()

    # =========================================================================
    # TRADING PERMISSION CHECKS
    # =========================================================================

    def can_trade(self) -> Tuple[bool, Optional[str]]:
        """
        Check if trading is allowed under drawdown limits.

        Returns:
            Tuple of (can_trade, reason_if_blocked)
        """
        # Check daily limit first
        if self.is_daily_limit_reached():
            return False, "daily_loss_limit"

        # Check weekly governor
        if self.is_governor_active():
            return False, "weekly_governor"

        return True, None

    def is_daily_limit_reached(self) -> bool:
        """
        Check if daily loss limit has been reached.

        Returns:
            True if today's drawdown >= 10%, False otherwise
        """
        return self._state.daily_drawdown_pct >= self.DAILY_LOSS_LIMIT_PCT

    def is_governor_active(self) -> bool:
        """
        Check if weekly drawdown governor is active.

        Returns:
            True if Strategy C is locked for the week
        """
        # Check for weekly reset first
        self._check_weekly_reset()
        return self._state.governor_active

    def daily_loss_remaining(self) -> Decimal:
        """
        Calculate how much more loss is allowed today.

        Returns:
            Dollars remaining before daily limit triggers
        """
        max_loss = self._state.daily_start_equity * self.DAILY_LOSS_LIMIT_PCT
        current_loss = self._state.daily_start_equity - self._state.current_equity

        # Handle negative current_loss (i.e., profit)
        if current_loss < 0:
            return max_loss

        remaining = max_loss - current_loss
        return max(Decimal("0"), remaining)

    def weekly_drawdown_pct(self) -> Decimal:
        """
        Get current weekly drawdown percentage.

        Returns:
            Drawdown as decimal (e.g., 0.08 for 8%)
        """
        return self._state.weekly_drawdown_pct

    # =========================================================================
    # STATE ACCESS
    # =========================================================================

    def get_state_snapshot(self) -> DrawdownState:
        """
        Get a snapshot of current drawdown state.

        Returns:
            Copy of current DrawdownState
        """
        return DrawdownState(
            week_start=self._state.week_start,
            week_start_equity=self._state.week_start_equity,
            daily_start_equity=self._state.daily_start_equity,
            current_equity=self._state.current_equity,
            realized_pnl_today=self._state.realized_pnl_today,
            realized_pnl_week=self._state.realized_pnl_week,
            governor_active=self._state.governor_active,
            governor_triggered_at=self._state.governor_triggered_at,
            last_updated=self._state.last_updated,
        )

    # =========================================================================
    # PERIOD RESETS
    # =========================================================================

    def reset_daily(self, new_day_equity: Decimal) -> None:
        """
        Reset daily tracking for a new trading day.

        Call this at market open.

        Args:
            new_day_equity: Account equity at start of new day
        """
        self._state.daily_start_equity = new_day_equity
        self._state.current_equity = new_day_equity
        self._state.realized_pnl_today = Decimal("0")
        self._state.last_updated = datetime.now()
        self._save_state()

    def reset_weekly(self, new_week_equity: Decimal) -> None:
        """
        Reset weekly tracking for a new trading week.

        Call this at Sunday midnight or Monday market open.

        Args:
            new_week_equity: Account equity at start of new week
        """
        today = date.today()
        self._state.week_start = today - timedelta(days=today.weekday())
        self._state.week_start_equity = new_week_equity
        self._state.daily_start_equity = new_week_equity
        self._state.current_equity = new_week_equity
        self._state.realized_pnl_today = Decimal("0")
        self._state.realized_pnl_week = Decimal("0")
        self._state.governor_active = False
        self._state.governor_triggered_at = None
        self._state.last_updated = datetime.now()
        self._save_state()

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _check_weekly_reset(self) -> None:
        """
        Check if we've crossed into a new week and auto-reset if needed.

        Weekly reset happens when the current date's week start differs
        from the stored week start.
        """
        current_week_start = self._get_current_week_start()

        if self._state.week_start < current_week_start:
            # New week has started — reset governor
            logger.info(
                f"New week detected (was {self._state.week_start}, "
                f"now {current_week_start}). Resetting weekly state."
            )
            # Keep current equity values but clear governor
            self._state.week_start = current_week_start
            self._state.week_start_equity = self._state.current_equity
            self._state.realized_pnl_week = Decimal("0")
            self._state.governor_active = False
            self._state.governor_triggered_at = None
            self._state.last_updated = datetime.now()
            self._save_state()

    def _get_current_week_start(self) -> date:
        """
        Get the Monday of the current week.

        Returns:
            Date of Monday for current week
        """
        today = date.today()
        return today - timedelta(days=today.weekday())

    def _load_or_initialize_state(self) -> DrawdownState:
        """Load persisted state or initialize fresh."""
        if self._state_file and self._state_file.exists():
            try:
                return self._load_state()
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Corrupted drawdown state, reinitializing: {e}")

        # Initialize fresh state
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        return DrawdownState(
            week_start=week_start,
            week_start_equity=self._starting_equity,
            daily_start_equity=self._starting_equity,
            current_equity=self._starting_equity,
        )

    def _load_state(self) -> DrawdownState:
        """Load state from disk."""
        if self._state_file is None:
            raise ValueError("No state file configured")

        with open(self._state_file, "r") as f:
            data = json.load(f)

        return DrawdownState(
            week_start=date.fromisoformat(data["week_start"]),
            week_start_equity=Decimal(data["week_start_equity"]),
            daily_start_equity=Decimal(data["daily_start_equity"]),
            current_equity=Decimal(data["current_equity"]),
            realized_pnl_today=Decimal(data.get("realized_pnl_today", "0")),
            realized_pnl_week=Decimal(data.get("realized_pnl_week", "0")),
            governor_active=data.get("governor_active", False),
            governor_triggered_at=(
                datetime.fromisoformat(data["governor_triggered_at"])
                if data.get("governor_triggered_at")
                else None
            ),
            last_updated=datetime.fromisoformat(
                data.get("last_updated", datetime.now().isoformat())
            ),
        )

    def _save_state(self) -> None:
        """Persist state to disk."""
        if self._state_file is None:
            return

        data: Dict[str, Any] = {
            "version": "1.0.0",
            "week_start": self._state.week_start.isoformat(),
            "week_start_equity": str(self._state.week_start_equity),
            "daily_start_equity": str(self._state.daily_start_equity),
            "current_equity": str(self._state.current_equity),
            "realized_pnl_today": str(self._state.realized_pnl_today),
            "realized_pnl_week": str(self._state.realized_pnl_week),
            "governor_active": self._state.governor_active,
            "governor_triggered_at": (
                self._state.governor_triggered_at.isoformat()
                if self._state.governor_triggered_at
                else None
            ),
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
