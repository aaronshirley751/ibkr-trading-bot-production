"""
Risk Guards — Legacy compatibility facade.

This module provides the RiskGuard class that existing tests expect.
It wraps the newer modular risk components (PositionSizer, PDTTracker,
DrawdownMonitor) while maintaining backward compatibility.

Use this for tests that expect the RiskGuard interface.
For new code, prefer using RiskManager directly.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo


class RiskGuard:
    """
    Risk guard with daily/weekly limits and circuit breakers.

    This class provides the interface expected by existing tests
    while using proper Decimal arithmetic internally for precision.

    Key limits:
    - Daily loss limit: 10% of account balance
    - Weekly drawdown governor: 15% triggers Strategy C
    - Force close DTE: 3 days to expiration
    - Stop-loss: 25% for Strategy A, 15% for Strategy B
    """

    def __init__(
        self,
        account_balance: float = 600.00,
        max_daily_loss_pct: float = 0.10,
        max_weekly_drawdown_pct: float = 0.15,
        force_close_dte: int = 3,
    ) -> None:
        """
        Initialize risk guard.

        Args:
            account_balance: Current account balance in dollars
            max_daily_loss_pct: Daily loss limit as decimal (default 0.10)
            max_weekly_drawdown_pct: Weekly governor trigger (default 0.15)
            force_close_dte: DTE threshold for force close (default 3)
        """
        self._account_balance = Decimal(str(account_balance))
        self._max_daily_loss_pct = Decimal(str(max_daily_loss_pct))
        self._max_weekly_drawdown_pct = Decimal(str(max_weekly_drawdown_pct))
        self._force_close_dte = force_close_dte

        # Daily tracking
        self._daily_losses = Decimal("0")
        self._daily_gains = Decimal("0")

        # Weekly tracking
        self._weekly_losses = Decimal("0")
        self._governor_active = False

        # Other state
        self._data_quarantine = False
        self._pivot_count = 0
        self._current_day = date.today()

    # =========================================================================
    # DAILY LOSS LIMIT
    # =========================================================================

    def daily_loss_limit_hit(self) -> bool:
        """Check if daily loss limit has been reached."""
        max_loss = self._account_balance * self._max_daily_loss_pct
        return self._daily_losses >= max_loss

    def daily_loss_remaining(self) -> float:
        """Calculate how much more loss is allowed today."""
        max_loss = self._account_balance * self._max_daily_loss_pct
        remaining = max_loss - self._daily_losses
        return float(max(Decimal("0"), remaining))

    def daily_losses_total(self) -> float:
        """Return total daily losses accumulated."""
        return float(self._daily_losses)

    def record_loss(self, amount: float) -> None:
        """Record a realized loss."""
        self._daily_losses += Decimal(str(amount))

    def record_gain(self, amount: float) -> None:
        """
        Record a gain.

        Note: Gains do NOT reduce daily loss tracking.
        This prevents the 'churn and burn' pattern.
        """
        self._daily_gains += Decimal(str(amount))

    def reset_daily(self) -> None:
        """Reset daily tracking for a new trading day."""
        self._daily_losses = Decimal("0")
        self._daily_gains = Decimal("0")
        self._current_day = date.today()

    # =========================================================================
    # WEEKLY DRAWDOWN GOVERNOR
    # =========================================================================

    def weekly_governor_active(self) -> bool:
        """Check if weekly drawdown governor is active."""
        return self._governor_active

    def record_weekly_loss(self, amount: float) -> None:
        """Record a loss toward weekly total."""
        self._weekly_losses += Decimal(str(amount))
        max_loss = self._account_balance * self._max_weekly_drawdown_pct
        if self._weekly_losses >= max_loss:
            self._governor_active = True

    def start_new_week(self) -> None:
        """Reset weekly tracking for a new trading week."""
        self._weekly_losses = Decimal("0")
        self._governor_active = False

    def advance_day(self) -> None:
        """Advance to next day within the same week."""
        self.reset_daily()

    # =========================================================================
    # REQUIRED STRATEGY
    # =========================================================================

    def required_strategy(self) -> Optional[str]:
        """
        Determine if a specific strategy is required due to risk limits.

        Returns:
            "C" if any circuit breaker is active, None otherwise
        """
        if self.daily_loss_limit_hit():
            return "C"
        if self._governor_active:
            return "C"
        if self._data_quarantine:
            return "C"
        if self._pivot_count >= 2:
            return "C"
        return None

    def can_open_new_position(self) -> bool:
        """Check if new positions can be opened."""
        return self.required_strategy() is None

    # =========================================================================
    # STOP-LOSS CALCULATION
    # =========================================================================

    def calculate_stop_loss(self, entry_price: float, strategy: str) -> float:
        """
        Calculate stop-loss price based on strategy.

        Strategy A: 25% stop-loss (price * 0.75)
        Strategy B: 15% stop-loss (price * 0.85)
        Strategy C: No trading allowed

        Args:
            entry_price: Entry price per contract
            strategy: Strategy identifier ("A", "B", or "C")

        Returns:
            Stop-loss price

        Raises:
            ValueError: If strategy is "C"
        """
        if strategy == "C":
            raise ValueError("Strategy C does not trade")

        entry = Decimal(str(entry_price))

        if strategy == "A":
            stop_pct = Decimal("0.75")  # 25% loss
        else:  # Strategy B
            stop_pct = Decimal("0.85")  # 15% loss

        return float(entry * stop_pct)

    def calculate_gap_loss(
        self,
        entry_price: float,
        stop_price: float,
        fill_price: float,
        multiplier: int,
        quantity: int,
    ) -> float:
        """
        Calculate actual loss in a gap-down scenario.

        Args:
            entry_price: Original entry price
            stop_price: Stop-loss trigger price (unused in gap scenario)
            fill_price: Actual fill price (may be below stop)
            multiplier: Contract multiplier (e.g., 100)
            quantity: Number of contracts

        Returns:
            Actual dollar loss
        """
        entry = Decimal(str(entry_price))
        fill = Decimal(str(fill_price))
        return float((entry - fill) * multiplier * quantity)

    def calculate_expected_loss(
        self,
        entry_price: float,
        stop_price: float,
        multiplier: int,
        quantity: int,
    ) -> float:
        """
        Calculate expected loss if stop is hit exactly.

        Args:
            entry_price: Original entry price
            stop_price: Stop-loss trigger price
            multiplier: Contract multiplier (e.g., 100)
            quantity: Number of contracts

        Returns:
            Expected dollar loss at stop
        """
        entry = Decimal(str(entry_price))
        stop = Decimal(str(stop_price))
        return float((entry - stop) * multiplier * quantity)

    # =========================================================================
    # DTE FORCE CLOSE
    # =========================================================================

    def should_force_close(self, dte: int) -> bool:
        """
        Check if position should be force-closed based on DTE.

        Args:
            dte: Days to expiration

        Returns:
            True if force close required
        """
        return dte <= self._force_close_dte

    def calculate_dte(self, expiry_date: str) -> int:
        """
        Calculate DTE from expiry date string.

        Args:
            expiry_date: Expiry in YYYYMMDD format

        Returns:
            Days to expiration (in ET timezone)
        """
        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)
        expiry = datetime.strptime(expiry_date, "%Y%m%d").date()
        return (expiry - now_et.date()).days

    def get_force_close_action(self, dte: int) -> Dict[str, Any]:
        """
        Get the action to take for force close.

        Args:
            dte: Days to expiration

        Returns:
            Dictionary with action details
        """
        return {
            "order_type": "MARKET",
            "reason": "dte_force_close",
            "urgency": "high" if dte <= 2 else "normal",
            "dte": dte,
        }

    # =========================================================================
    # DATA QUARANTINE
    # =========================================================================

    def set_data_quarantine(self, active: bool) -> None:
        """Set data quarantine flag."""
        self._data_quarantine = active

    # =========================================================================
    # PIVOT TRACKING
    # =========================================================================

    def record_pivot(self) -> None:
        """Record an intraday pivot."""
        self._pivot_count += 1

    def pivot_count(self) -> int:
        """Get current pivot count."""
        return self._pivot_count

    # =========================================================================
    # PRE-ORDER CHECK
    # =========================================================================

    def pre_order_check(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform pre-order risk check.

        Args:
            order: Order dictionary with action, quantity, etc.

        Returns:
            Dictionary with 'allowed' bool and 'reason' if blocked
        """
        # Closing orders are always allowed
        if order.get("is_closing", False):
            return {"allowed": True}

        # Check if Strategy C is active
        if self.required_strategy() == "C":
            return {"allowed": False, "reason": "strategy_c_active"}

        return {"allowed": True}

    def get_required_action(self) -> Dict[str, str]:
        """
        Get required action when daily limit is hit.

        Returns:
            Dictionary with action type and reason
        """
        if self.daily_loss_limit_hit():
            return {"type": "CLOSE_ALL", "reason": "daily_loss_limit"}
        if self._governor_active:
            return {"type": "CLOSE_ALL", "reason": "weekly_governor"}
        return {"type": "NONE", "reason": ""}

    # =========================================================================
    # STATE SERIALIZATION
    # =========================================================================

    def to_state_dict(self) -> Dict[str, Any]:
        """
        Serialize state for persistence.

        Returns:
            Dictionary with all state fields
        """
        return {
            "daily_losses": float(self._daily_losses),
            "weekly_losses": float(self._weekly_losses),
            "governor_active": self._governor_active,
            "pivot_count": self._pivot_count,
            "data_quarantine": self._data_quarantine,
            "last_updated": datetime.now().isoformat(),
            "account_balance": float(self._account_balance),
            "max_daily_loss_pct": float(self._max_daily_loss_pct),
            "max_weekly_drawdown_pct": float(self._max_weekly_drawdown_pct),
            "force_close_dte": self._force_close_dte,
        }

    @classmethod
    def from_state_dict(cls, state: Optional[Dict[str, Any]]) -> "RiskGuard":
        """
        Restore RiskGuard from saved state.

        If state is None or corrupted, returns a guard in safe mode
        (Strategy C required).

        Args:
            state: Previously saved state dictionary

        Returns:
            RiskGuard instance
        """
        if state is None:
            # No state = unknown risk state = Strategy C
            guard = cls()
            guard._data_quarantine = True  # Forces Strategy C
            return guard

        # Check for required fields to detect corrupted state
        required_fields = ["daily_losses", "weekly_losses", "governor_active"]
        if not any(field in state for field in required_fields):
            # Missing all critical fields = corrupted state = Strategy C
            guard = cls()
            guard._data_quarantine = True
            return guard

        try:
            guard = cls(
                account_balance=state.get("account_balance", 600.00),
                max_daily_loss_pct=state.get("max_daily_loss_pct", 0.10),
                max_weekly_drawdown_pct=state.get("max_weekly_drawdown_pct", 0.15),
                force_close_dte=state.get("force_close_dte", 3),
            )
            guard._daily_losses = Decimal(str(state.get("daily_losses", 0)))
            guard._weekly_losses = Decimal(str(state.get("weekly_losses", 0)))
            guard._governor_active = state.get("governor_active", False)
            guard._pivot_count = state.get("pivot_count", 0)
            guard._data_quarantine = state.get("data_quarantine", False)
            return guard

        except (KeyError, TypeError, ValueError):
            # Corrupted state = Strategy C (set quarantine to force safe mode)
            guard = cls()
            guard._data_quarantine = True
            return guard
