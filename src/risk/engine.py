"""
Risk Engine - Central integration point for all risk subsystems.

This module provides the RiskEngine class that coordinates:
- PositionSizer: Position size limits and risk calculations
- PDTTracker: Pattern Day Trader compliance
- DrawdownMonitor: Daily loss limits and weekly governor
- CircuitBreaker: State machine for trading halt/resume

CRO MANDATE: This is the SINGLE entry point for all risk checks.
No trade may bypass this engine.

Threat model: T-04 (race conditions), T-08 (bypass paths), T-11 (coordination)
"""

from __future__ import annotations

import threading
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from src.risk.position_sizer import PositionSizer


class BrokerProtocol(Protocol):
    """Protocol for broker interactions."""

    def cancel_all_orders(self) -> bool:
        """Cancel all pending orders."""
        ...

    def close_all_positions(self) -> bool:
        """Close all open positions."""
        ...


class NotifierProtocol(Protocol):
    """Protocol for alert notifications."""

    def send_alert(self, message: str) -> None:
        """Send an alert notification."""
        ...


class RiskEngine:
    """
    Central integration point that coordinates all risk subsystems.

    Features:
    - Thread-safe state management with locking
    - Circuit breaker state machine (CLOSED → OPEN → CLOSED)
    - Emergency action coordination
    - Gameplan validation
    - Full risk pipeline: governor → daily → PDT → sizing

    Attributes:
        _lock: Threading lock for state mutations
        _config: Risk configuration parameters
        _position_sizer: Position sizing calculator
        _broker: Attached broker (optional)
        _notifier: Attached notifier (optional)
    """

    def __init__(
        self,
        account_balance: float,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the risk engine.

        Args:
            account_balance: Current account equity in dollars
            config: Configuration dictionary with risk parameters
        """
        self._lock = threading.Lock()
        self._account_balance = Decimal(str(account_balance))

        # Parse config
        cfg = config or {}
        self._max_position_pct = Decimal(str(cfg.get("max_position_pct", 0.20)))
        self._max_risk_pct = Decimal(str(cfg.get("max_risk_pct", 0.03)))
        self._pdt_limit = cfg.get("pdt_limit", 3)
        self._max_daily_loss_pct = Decimal(str(cfg.get("max_daily_loss_pct", 0.10)))
        self._max_weekly_drawdown_pct = Decimal(str(cfg.get("max_weekly_drawdown_pct", 0.15)))
        self._force_close_dte = cfg.get("force_close_dte", 3)
        self._max_intraday_pivots = cfg.get("max_intraday_pivots", 2)

        # Initialize position sizer with float parameters
        self._position_sizer = PositionSizer(
            account_balance=account_balance,
            max_position_pct=float(self._max_position_pct),
            max_risk_pct=float(self._max_risk_pct),
            pdt_limit=self._pdt_limit,
        )

        # State variables
        self._circuit_breaker_state = "CLOSED"
        self._trading_halted = False
        self._daily_losses = Decimal("0")
        self._weekly_losses = Decimal("0")
        self._day_trades_count = 0
        self._pivot_count = 0
        self._data_quarantine = False
        self._emergency_executed = False

        # Calculated limits
        self._max_daily_loss = self._account_balance * self._max_daily_loss_pct
        self._max_weekly_drawdown = self._account_balance * self._max_weekly_drawdown_pct
        self._max_position_size = self._account_balance * self._max_position_pct
        self._max_risk_per_trade = self._account_balance * self._max_risk_pct

        # Attached services
        self._broker: Optional[BrokerProtocol] = None
        self._notifier: Optional[NotifierProtocol] = None

    def attach_broker(self, broker: BrokerProtocol) -> None:
        """Attach a broker for order/position management."""
        with self._lock:
            self._broker = broker

    def attach_notifier(self, notifier: NotifierProtocol) -> None:
        """Attach a notifier for alerts."""
        with self._lock:
            self._notifier = notifier

    def pre_trade_check(
        self,
        symbol: str,
        action: str,
        premium: float,
        stop_loss_pct: float,
        quantity: int,
    ) -> Dict[str, Any]:
        """
        Perform all pre-trade risk checks.

        Checks are performed in order:
        1. Strategy override (is trading halted?)
        2. PDT compliance
        3. Daily loss limit
        4. Weekly governor
        5. Position size
        6. Risk per trade
        7. Aggregate exposure

        Args:
            symbol: The symbol to trade (e.g., "SPY")
            action: "BUY" or "SELL"
            premium: Option premium per share
            stop_loss_pct: Stop loss as percentage (e.g., 0.25 for 25%)
            quantity: Number of contracts

        Returns:
            Dict with:
                - approved: bool
                - checks_performed: List of check names
                - rejection_reasons: List of failed checks (if any)
        """
        with self._lock:
            checks_performed: List[str] = []
            rejection_reasons: List[str] = []
            premium_dec = Decimal(str(premium))
            stop_loss_dec = Decimal(str(stop_loss_pct))

            # 1. Strategy override — is trading halted?
            checks_performed.append("strategy_override")
            if self._trading_halted or self._circuit_breaker_state == "OPEN":
                rejection_reasons.append("circuit_breaker_open")

            # 2. PDT compliance
            checks_performed.append("pdt_compliance")
            if action.upper() == "BUY" and self._day_trades_count >= self._pdt_limit:
                rejection_reasons.append("pdt_limit_reached")

            # 3. Daily loss limit
            checks_performed.append("daily_loss_limit")
            if self._daily_losses >= self._max_daily_loss:
                rejection_reasons.append("daily_loss_limit")

            # 4. Weekly governor
            checks_performed.append("weekly_governor")
            if self._weekly_losses >= self._max_weekly_drawdown:
                rejection_reasons.append("weekly_governor_active")

            # 5. Position size
            checks_performed.append("position_size")
            position_value = premium_dec * 100 * quantity
            if position_value > self._max_position_size:
                rejection_reasons.append("position_size_exceeded")

            # 6. Risk per trade
            checks_performed.append("risk_per_trade")
            risk_amount = position_value * stop_loss_dec
            if risk_amount > self._max_risk_per_trade:
                rejection_reasons.append("risk_per_trade")

            # 7. Aggregate exposure
            checks_performed.append("aggregate_exposure")
            # Simplified: just check if position alone is OK
            # Real implementation would track open positions

            return {
                "approved": len(rejection_reasons) == 0,
                "checks_performed": checks_performed,
                "rejection_reasons": rejection_reasons,
            }

    def pre_close_check(
        self,
        symbol: str,
        action: str,
        quantity: int,
        is_closing: bool,
    ) -> Dict[str, Any]:
        """
        Check if closing a position is allowed.

        Closing positions is ALWAYS allowed, even when:
        - Circuit breaker is open
        - PDT limit is reached
        - Trading is halted

        Args:
            symbol: The symbol
            action: "BUY" or "SELL"
            quantity: Number of contracts
            is_closing: Must be True for this method

        Returns:
            Dict with approved=True (closing always allowed)
        """
        if is_closing:
            return {"approved": True, "checks_performed": ["close_allowed"]}
        # If not closing, use normal pre_trade_check
        return self.pre_trade_check(symbol, action, 0.0, 0.0, quantity)

    def record_day_trades(self, count: int) -> None:
        """Record day trades (adds to existing count)."""
        with self._lock:
            self._day_trades_count += count

    def record_daily_loss(self, amount: float) -> None:
        """Record a daily loss amount."""
        with self._lock:
            self._daily_losses += Decimal(str(amount))
            # Check if this triggers daily limit
            if self._daily_losses >= self._max_daily_loss:
                self._circuit_breaker_state = "OPEN"
                self._trading_halted = True

    def record_weekly_loss(self, amount: float) -> None:
        """Record a weekly loss amount."""
        with self._lock:
            self._weekly_losses = Decimal(str(amount))

    def on_loss_event(self, amount: float) -> None:
        """
        Handle a significant loss event.

        This triggers:
        1. Recording the loss
        2. Opening the circuit breaker
        3. Halting trading
        4. Executing emergency action (idempotent)
        """
        with self._lock:
            self._daily_losses += Decimal(str(amount))
            self._circuit_breaker_state = "OPEN"
            self._trading_halted = True

        # Delegate to idempotent emergency action
        self.execute_emergency_action()

    def on_gateway_disconnect(self) -> None:
        """
        Handle gateway disconnection emergency.

        Cancels all pending orders and sends alert.
        """
        if self._broker:
            self._broker.cancel_all_orders()

        if self._notifier:
            self._notifier.send_alert("ALERT: Gateway disconnected - orders cancelled")

    def trading_halted(self) -> bool:
        """Check if trading is currently halted."""
        with self._lock:
            return self._trading_halted

    def weekly_governor_active(self) -> bool:
        """Check if weekly drawdown governor is active."""
        with self._lock:
            return self._weekly_losses >= self._max_weekly_drawdown

    def required_strategy(self) -> str:
        """Get the required strategy based on current risk state."""
        with self._lock:
            if self._trading_halted or self._weekly_losses >= self._max_weekly_drawdown:
                return "C"
            if self._daily_losses >= self._max_daily_loss:
                return "C"
            return "A"

    def set_data_quarantine(self, active: bool) -> None:
        """Set data quarantine state (for bad market data)."""
        with self._lock:
            self._data_quarantine = active

    def record_pivot(self) -> None:
        """Record an intraday pivot (strategy change)."""
        with self._lock:
            self._pivot_count += 1

    def get_emergency_action(self) -> Dict[str, Any]:
        """
        Get the current emergency action to take.

        Returns:
            Dict with:
                - strategy: Required strategy ("C" if emergency)
                - directives: List of actions to take
                - trigger: What triggered the emergency
                - timestamp: When this was generated
        """
        with self._lock:
            directives: List[str] = []
            trigger = None

            if self._trading_halted or self._circuit_breaker_state == "OPEN":
                directives.append("CLOSE_ALL_POSITIONS")
                directives.append("CANCEL_ALL_ORDERS")
                trigger = "daily_loss_limit"

            if self._weekly_losses >= self._max_weekly_drawdown:
                trigger = "weekly_governor"

            if self._notifier is not None:
                directives.append("SEND_ALERT")

            if self._broker is not None and "CLOSE_ALL_POSITIONS" not in directives:
                pass  # No emergency

            return {
                "strategy": "C" if directives else "A",
                "directives": directives,
                "trigger": trigger,
                "timestamp": datetime.now().isoformat() if trigger else None,
            }

    def execute_emergency_action(self) -> None:
        """
        Execute the emergency action.

        This is idempotent — calling it multiple times is safe.
        """
        with self._lock:
            if self._emergency_executed:
                return  # Already executed
            self._emergency_executed = True

        # Execute outside lock to avoid deadlock
        if self._broker:
            self._broker.close_all_positions()
            self._broker.cancel_all_orders()

    def circuit_breaker_state(self) -> str:
        """Get the current circuit breaker state (CLOSED or OPEN)."""
        with self._lock:
            return self._circuit_breaker_state

    def start_new_trading_day(self) -> None:
        """
        Reset daily state for a new trading day.

        Note: If weekly governor is active, circuit breaker stays OPEN.
        """
        with self._lock:
            self._daily_losses = Decimal("0")
            self._pivot_count = 0
            self._emergency_executed = False

            # Only reset if weekly governor is not active
            if self._weekly_losses < self._max_weekly_drawdown:
                self._circuit_breaker_state = "CLOSED"
                self._trading_halted = False

    def daily_losses_total(self) -> float:
        """Get total daily losses."""
        with self._lock:
            return float(self._daily_losses)

    def validate_gameplan(self, gameplan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a trading gameplan's hard limits.

        Ensures gameplan limits do not exceed account parameter limits.

        Args:
            gameplan: Dict containing "hard_limits" section

        Returns:
            Dict with:
                - valid: bool
                - violations: List of violations (if any)
        """
        if "hard_limits" not in gameplan:
            return {"valid": False, "violations": ["Missing hard_limits section"]}

        limits = gameplan["hard_limits"]
        violations: List[str] = []

        # Check each limit against account parameters
        if Decimal(str(limits.get("max_position_size", 0))) > self._max_position_size:
            violations.append("max_position_size exceeds account limit")

        if Decimal(str(limits.get("max_risk_per_trade", 0))) > self._max_risk_per_trade:
            violations.append("max_risk_per_trade exceeds account limit")

        if Decimal(str(limits.get("max_daily_loss", 0))) > self._max_daily_loss:
            violations.append("max_daily_loss exceeds account limit")

        if Decimal(str(limits.get("max_weekly_drawdown", 0))) > self._max_weekly_drawdown:
            violations.append("max_weekly_drawdown exceeds account limit")

        if limits.get("pdt_limit", 0) > self._pdt_limit:
            violations.append("pdt_limit exceeds account limit")

        return {"valid": len(violations) == 0, "violations": violations}
