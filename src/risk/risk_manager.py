"""
Risk Manager — Central orchestrator for all risk controls.

This is the SINGLE ENTRY POINT for all pre-trade risk validation.
No order may be sent to the broker without passing through this
module first.

Architecture:
- Aggregates PositionSizer, PDTTracker, and DrawdownMonitor
- Provides a single evaluate() method for all risk checks
- Returns comprehensive RiskCheckResult with decision and details
- Enforces all limits as hard stops

CRITICAL DESIGN PRINCIPLE:
The RiskManager is the gatekeeper between the strategy layer
and the broker API. ALL trade requests flow through here.
There is no bypass path.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.risk.risk_types import (
    PositionSizeRequest,
    PositionSizeResult,
    RiskCheckResult,
    RiskDecision,
    RejectionReason,
)
from src.risk.position_sizer import PositionSizer, AccountProvider
from src.risk.pdt_tracker import PDTTracker
from src.risk.drawdown_monitor import DrawdownMonitor
from src.config.risk_config import RiskConfig, DEFAULT_RISK_CONFIG


class RiskManager:
    """
    Central risk control orchestrator.

    This class coordinates all risk checks and provides a single
    point of entry for trade validation. It is designed to be
    impossible to bypass — all broker API calls must go through
    methods that check with this manager first.

    Risk Check Sequence (order matters):
    1. Weekly drawdown governor — if active, reject immediately
    2. Daily loss limit — if reached, reject immediately
    3. PDT limit — if no trades remaining and is day trade, reject
    4. Position sizing — calculate safe size within all limits

    The sequence ensures we fail fast on the most severe
    restrictions before doing expensive calculations.
    """

    def __init__(
        self,
        config: Optional[RiskConfig] = None,
        account_provider: Optional[AccountProvider] = None,
        state_dir: Optional[Path] = None,
        starting_equity: Optional[Decimal] = None,
    ) -> None:
        """
        Initialize risk manager with all sub-components.

        Args:
            config: Risk configuration (uses defaults if not provided)
            account_provider: Protocol for account data access
            state_dir: Directory for state persistence (defaults to ./state)
            starting_equity: Initial account equity (defaults to config value)
        """
        self._config = config or DEFAULT_RISK_CONFIG
        self._account_provider = account_provider

        if state_dir is None:
            state_dir = Path("state")

        if starting_equity is None:
            starting_equity = self._config.starting_capital

        # Initialize sub-components
        self._position_sizer = PositionSizer(
            account_balance=float(starting_equity),
            max_position_pct=float(self._config.max_position_pct_strategy_a),
            max_risk_pct=float(self._config.max_risk_per_trade_pct),
            pdt_limit=self._config.pdt_limit,
            account_provider=account_provider,
        )

        self._pdt_tracker = PDTTracker(
            trade_limit=self._config.pdt_limit,
            window_days=self._config.pdt_window_days,
            state_file=state_dir / "pdt_state.json",
        )

        self._drawdown_monitor = DrawdownMonitor(
            starting_equity=starting_equity,
            state_file=state_dir / "drawdown_state.json",
            daily_loss_limit_pct=self._config.max_daily_loss_pct,
            weekly_governor_pct=self._config.weekly_drawdown_governor_pct,
        )

        # Track open positions for entry/exit recording
        self._open_positions: Dict[str, Dict[str, Any]] = {}

    # =========================================================================
    # MAIN EVALUATION METHOD
    # =========================================================================

    def evaluate(
        self,
        request: PositionSizeRequest,
        is_day_trade: bool = False,
    ) -> RiskCheckResult:
        """
        Evaluate a trading request against all risk controls.

        This is the primary entry point. It checks all risk gates
        in sequence and returns a comprehensive result.

        Args:
            request: Position sizing request with trade details
            is_day_trade: Whether this will be a same-day round-trip

        Returns:
            RiskCheckResult with decision and all relevant details
        """
        warnings: List[str] = []

        # Gate 1: Weekly drawdown governor
        if self._drawdown_monitor.is_governor_active():
            return self._reject(
                request,
                RiskDecision.STRATEGY_C_LOCKED,
                RejectionReason.WEEKLY_DRAWDOWN_GOVERNOR,
            )

        # Gate 2: Daily loss limit
        if self._drawdown_monitor.is_daily_limit_reached():
            return self._reject(
                request,
                RiskDecision.REJECTED,
                RejectionReason.DAILY_LOSS_LIMIT_REACHED,
            )

        # Gate 3: PDT limit (only if this is a day trade)
        if is_day_trade and not self._pdt_tracker.can_day_trade():
            return self._reject(
                request,
                RiskDecision.REJECTED,
                RejectionReason.PDT_LIMIT_REACHED,
            )

        # Gate 4: Position sizing
        position_result, rejection_reason = self._position_sizer.calculate_position_size(request)

        if rejection_reason is not None:
            decision = (
                RiskDecision.STRATEGY_C_LOCKED
                if rejection_reason == RejectionReason.STRATEGY_C_ACTIVE
                else RiskDecision.REJECTED
            )
            return RiskCheckResult(
                decision=decision,
                rejection_reason=rejection_reason,
                approved_contracts=0,
                original_request=request,
                position_size_result=position_result,
                pdt_trades_remaining=self._pdt_tracker.trades_remaining(),
                daily_loss_remaining=self._drawdown_monitor.daily_loss_remaining(),
                weekly_drawdown_pct=self._drawdown_monitor.weekly_drawdown_pct(),
                governor_active=self._drawdown_monitor.is_governor_active(),
                warnings=tuple(warnings),
                timestamp=datetime.now(),
            )

        # Add warnings for approaching limits
        if self._pdt_tracker.trades_remaining() <= 1:
            warnings.append(f"WARNING: Only {self._pdt_tracker.trades_remaining()} PDT remaining")

        daily_remaining = self._drawdown_monitor.daily_loss_remaining()
        if daily_remaining < self._config.max_daily_loss * Decimal("0.25"):
            warnings.append(f"WARNING: Only ${float(daily_remaining):.2f} daily loss remaining")

        # Determine if position was reduced
        decision = RiskDecision.APPROVED
        if position_result.approved_contracts < position_result.max_contracts_by_cash:
            # Position was constrained by some limit
            if position_result.limiting_factor in ("risk_limit", "position_limit"):
                decision = RiskDecision.REDUCED

        return RiskCheckResult(
            decision=decision,
            rejection_reason=None,
            approved_contracts=position_result.approved_contracts,
            original_request=request,
            position_size_result=position_result,
            pdt_trades_remaining=self._pdt_tracker.trades_remaining(),
            daily_loss_remaining=self._drawdown_monitor.daily_loss_remaining(),
            weekly_drawdown_pct=self._drawdown_monitor.weekly_drawdown_pct(),
            governor_active=self._drawdown_monitor.is_governor_active(),
            warnings=tuple(warnings),
            timestamp=datetime.now(),
        )

    # =========================================================================
    # TRADE LIFECYCLE TRACKING
    # =========================================================================

    def record_trade_entry(
        self,
        symbol: str,
        contracts: int,
        entry_price: Decimal,
        entry_time: datetime,
    ) -> None:
        """
        Record a trade entry for tracking.

        Call this when a position is opened.

        Args:
            symbol: Trading symbol
            contracts: Number of contracts
            entry_price: Entry price
            entry_time: Time of entry
        """
        self._open_positions[symbol] = {
            "contracts": contracts,
            "entry_price": entry_price,
            "entry_time": entry_time,
        }

    def record_trade_exit(
        self,
        symbol: str,
        contracts: int,
        exit_price: Decimal,
        exit_time: datetime,
        realized_pnl: Decimal,
    ) -> None:
        """
        Record a trade exit and update state.

        Call this when a position is closed.

        Args:
            symbol: Trading symbol
            contracts: Number of contracts closed
            exit_price: Exit price
            exit_time: Time of exit
            realized_pnl: Realized P&L from the trade
        """
        # Record P&L in drawdown monitor
        self._drawdown_monitor.record_realized_pnl(realized_pnl)

        # Check if this was a day trade
        if symbol in self._open_positions:
            position = self._open_positions[symbol]
            entry_time = position["entry_time"]

            # Same day = day trade
            if entry_time.date() == exit_time.date():
                self._pdt_tracker.record_day_trade(
                    symbol=symbol,
                    entry_time=entry_time,
                    exit_time=exit_time,
                    contracts=contracts,
                )

            # Remove from tracking
            del self._open_positions[symbol]

    # =========================================================================
    # EQUITY MANAGEMENT
    # =========================================================================

    def update_equity(self, current_equity: Decimal) -> None:
        """
        Update current account equity.

        Call this periodically or after significant equity changes.

        Args:
            current_equity: Current account equity
        """
        self._drawdown_monitor.update_equity(current_equity)

    def start_new_trading_day(self, day_start_equity: Decimal) -> None:
        """
        Initialize a new trading day.

        Call this at market open.

        Args:
            day_start_equity: Account equity at start of day
        """
        self._drawdown_monitor.reset_daily(day_start_equity)

    def start_new_trading_week(self, week_start_equity: Decimal) -> None:
        """
        Initialize a new trading week.

        Call this at Sunday midnight or Monday market open.

        Args:
            week_start_equity: Account equity at start of week
        """
        self._drawdown_monitor.reset_weekly(week_start_equity)

    # =========================================================================
    # STATUS REPORTING
    # =========================================================================

    def get_risk_status(self) -> Dict[str, Any]:
        """
        Get comprehensive risk status for monitoring.

        Returns:
            Dictionary with all risk metrics and states
        """
        drawdown_state = self._drawdown_monitor.get_state_snapshot()

        return {
            "pdt": {
                "trades_used": self._pdt_tracker.trades_used(),
                "trades_remaining": self._pdt_tracker.trades_remaining(),
                "limit": self._config.pdt_limit,
                "can_day_trade": self._pdt_tracker.can_day_trade(),
            },
            "daily": {
                "loss_remaining": float(self._drawdown_monitor.daily_loss_remaining()),
                "drawdown_pct": float(drawdown_state.daily_drawdown_pct),
                "limit_pct": float(self._config.max_daily_loss_pct),
                "limit_reached": self._drawdown_monitor.is_daily_limit_reached(),
            },
            "weekly": {
                "drawdown_pct": float(self._drawdown_monitor.weekly_drawdown_pct()),
                "governor_limit_pct": float(self._config.weekly_drawdown_governor_pct),
                "governor_active": self._drawdown_monitor.is_governor_active(),
                "governor_triggered_at": (
                    drawdown_state.governor_triggered_at.isoformat()
                    if drawdown_state.governor_triggered_at
                    else None
                ),
            },
            "equity": {
                "current": float(drawdown_state.current_equity),
                "daily_start": float(drawdown_state.daily_start_equity),
                "week_start": float(drawdown_state.week_start_equity),
            },
            "position_limits": {
                "strategy_a_pct": float(self._config.max_position_pct_strategy_a),
                "strategy_b_pct": float(self._config.max_position_pct_strategy_b),
                "max_risk_per_trade_pct": float(self._config.max_risk_per_trade_pct),
            },
            "last_updated": drawdown_state.last_updated.isoformat(),
        }

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _reject(
        self,
        request: PositionSizeRequest,
        decision: RiskDecision,
        reason: RejectionReason,
        warnings: Optional[List[str]] = None,
    ) -> RiskCheckResult:
        """Create a rejection result."""
        return RiskCheckResult(
            decision=decision,
            rejection_reason=reason,
            approved_contracts=0,
            original_request=request,
            position_size_result=PositionSizeResult(
                approved_contracts=0,
                max_contracts_by_risk=0,
                max_contracts_by_position=0,
                max_contracts_by_cash=0,
                limiting_factor=reason.name.lower(),
                position_value=Decimal("0"),
                risk_amount=Decimal("0"),
            ),
            pdt_trades_remaining=self._pdt_tracker.trades_remaining(),
            daily_loss_remaining=self._drawdown_monitor.daily_loss_remaining(),
            weekly_drawdown_pct=self._drawdown_monitor.weekly_drawdown_pct(),
            governor_active=self._drawdown_monitor.is_governor_active(),
            warnings=tuple(warnings or []),
            timestamp=datetime.now(),
        )


# =========================================================================
# FACTORY FUNCTION
# =========================================================================


def create_risk_manager(
    config: Optional[RiskConfig] = None,
    account_provider: Optional[AccountProvider] = None,
    state_dir: Optional[Path] = None,
    starting_equity: Optional[Decimal] = None,
) -> RiskManager:
    """
    Factory function to create a properly configured RiskManager.

    Args:
        config: Risk configuration (uses defaults if not provided)
        account_provider: Protocol for account equity/buying power
        state_dir: Optional state directory (defaults to ./state)
        starting_equity: Initial account equity

    Returns:
        Configured RiskManager instance
    """
    return RiskManager(
        config=config,
        account_provider=account_provider,
        state_dir=state_dir,
        starting_equity=starting_equity,
    )
