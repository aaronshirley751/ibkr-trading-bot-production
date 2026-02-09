"""
Risk control module.

Provides comprehensive pre-trade risk validation including:
- Position sizing with risk and strategy-specific limits
- Pattern day trader (PDT) tracking with persistence
- Daily loss limit monitoring
- Weekly drawdown governor with Strategy C lock

Usage:
    # Modern API (preferred)
    from src.risk import RiskManager, create_risk_manager
    from src.risk import RiskCheckResult, RiskDecision

    manager = create_risk_manager(config, account_provider)
    result = manager.evaluate(position_request)

    if result.decision == RiskDecision.APPROVED:
        # Proceed with trade
        pass
    else:
        # Handle rejection
        print(f"Rejected: {result.rejection_reason}")

    # Legacy API (for backward compatibility)
    from src.risk.guards import RiskGuard

    guard = RiskGuard(account_balance=600.00)
    if not guard.daily_loss_limit_hit():
        # Trading allowed
        pass
"""

from src.risk.risk_types import (
    RiskDecision,
    RejectionReason,
    PositionSizeRequest,
    PositionSizeResult,
    DayTrade,
    PDTState,
    DrawdownState,
    RiskCheckResult,
)

from src.risk.position_sizer import PositionSizer, AccountProvider
from src.risk.pdt_tracker import PDTTracker, MarketCalendar
from src.risk.drawdown_monitor import DrawdownMonitor
from src.risk.risk_manager import RiskManager, create_risk_manager
from src.risk.guards import RiskGuard
from src.risk.engine import RiskEngine

__all__ = [
    # Enums
    "RiskDecision",
    "RejectionReason",
    # Types
    "PositionSizeRequest",
    "PositionSizeResult",
    "DayTrade",
    "PDTState",
    "DrawdownState",
    "RiskCheckResult",
    # Classes
    "PositionSizer",
    "AccountProvider",
    "PDTTracker",
    "MarketCalendar",
    "DrawdownMonitor",
    "RiskManager",
    "RiskGuard",
    "RiskEngine",
    # Factory
    "create_risk_manager",
]
