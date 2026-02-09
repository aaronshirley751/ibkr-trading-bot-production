"""
Risk module type definitions.

All risk-related dataclasses, enums, and type aliases.
These types are used throughout the risk control system for:
- Position sizing calculations
- PDT tracking
- Drawdown monitoring
- Risk check results

CRITICAL: All monetary types use Decimal for financial precision.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class RiskDecision(Enum):
    """Possible outcomes from risk evaluation."""

    APPROVED = auto()  # Trade may proceed as requested
    REDUCED = auto()  # Trade approved with reduced size
    REJECTED = auto()  # Trade rejected — specific limit violated
    STRATEGY_C_LOCKED = auto()  # All trading halted — governor active


class RejectionReason(Enum):
    """Specific reasons for trade rejection."""

    EXCEEDS_POSITION_LIMIT = auto()
    EXCEEDS_RISK_LIMIT = auto()
    PDT_LIMIT_REACHED = auto()
    DAILY_LOSS_LIMIT_REACHED = auto()
    WEEKLY_DRAWDOWN_GOVERNOR = auto()
    STRATEGY_C_ACTIVE = auto()
    INSUFFICIENT_BUYING_POWER = auto()
    CONFIDENCE_BELOW_THRESHOLD = auto()
    PREMIUM_UNAFFORDABLE = auto()
    INVALID_INPUT = auto()
    DATA_QUARANTINE = auto()


@dataclass(frozen=True)
class PositionSizeRequest:
    """
    Input to position sizer.

    Attributes:
        symbol: Underlying symbol (SPY, QQQ, IWM)
        strategy: Strategy identifier (A, B, or C)
        signal_confidence: Strategy's confidence score (0.0-1.0)
        entry_price: Expected option premium per contract
        stop_loss_pct: Stop loss percentage (e.g., 0.25 for 25%)
        account_cash: Current available cash in account
        current_positions_value: Total value of open positions
    """

    symbol: str
    strategy: str
    signal_confidence: float
    entry_price: Decimal
    stop_loss_pct: Decimal
    account_cash: Decimal
    current_positions_value: Decimal


@dataclass(frozen=True)
class PositionSizeResult:
    """
    Output from position sizer.

    Attributes:
        approved_contracts: Number of contracts approved (0 if rejected)
        max_contracts_by_risk: Contracts allowed by 1% risk rule
        max_contracts_by_position: Contracts allowed by position size rule
        max_contracts_by_cash: Contracts allowed by available cash
        limiting_factor: Which constraint was binding
        position_value: Total position value at approved size
        risk_amount: Dollar risk at approved size
    """

    approved_contracts: int
    max_contracts_by_risk: int
    max_contracts_by_position: int
    max_contracts_by_cash: int
    limiting_factor: str
    position_value: Decimal
    risk_amount: Decimal


@dataclass
class DayTrade:
    """
    Record of a single day trade.

    A day trade occurs when a position is opened and closed
    on the same trading day.

    Attributes:
        symbol: The traded symbol
        trade_date: Date the round-trip occurred
        entry_time: Timestamp of position entry
        exit_time: Timestamp of position exit
        contracts: Number of contracts traded
    """

    symbol: str
    trade_date: date
    entry_time: datetime
    exit_time: datetime
    contracts: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON persistence."""
        return {
            "symbol": self.symbol,
            "trade_date": self.trade_date.isoformat(),
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "contracts": self.contracts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DayTrade":
        """Deserialize from dictionary."""
        return cls(
            symbol=data["symbol"],
            trade_date=date.fromisoformat(data["trade_date"]),
            entry_time=datetime.fromisoformat(data["entry_time"]),
            exit_time=datetime.fromisoformat(data["exit_time"]),
            contracts=data["contracts"],
        )


@dataclass
class PDTState:
    """
    Persisted PDT tracking state.

    Attributes:
        day_trades: List of day trades in rolling window
        last_updated: When state was last modified
    """

    day_trades: List[DayTrade] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def trades_in_window(self, window_days: int = 5) -> int:
        """Count day trades in rolling window."""
        cutoff = date.today() - timedelta(days=window_days)
        return sum(1 for t in self.day_trades if t.trade_date > cutoff)


@dataclass
class DrawdownState:
    """
    Persisted drawdown tracking state.

    Attributes:
        week_start: Start date of current tracking week (Monday)
        week_start_equity: Account equity at week start
        daily_start_equity: Account equity at day start
        current_equity: Current account equity
        realized_pnl_today: Today's realized P&L
        realized_pnl_week: This week's realized P&L
        governor_active: Whether weekly governor has triggered
        governor_triggered_at: When governor was triggered
        last_updated: When state was last modified
    """

    week_start: date
    week_start_equity: Decimal
    daily_start_equity: Decimal
    current_equity: Decimal
    realized_pnl_today: Decimal = Decimal("0")
    realized_pnl_week: Decimal = Decimal("0")
    governor_active: bool = False
    governor_triggered_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def daily_drawdown_pct(self) -> Decimal:
        """Calculate today's drawdown percentage."""
        if self.daily_start_equity == 0:
            return Decimal("0")
        return (self.daily_start_equity - self.current_equity) / self.daily_start_equity

    @property
    def weekly_drawdown_pct(self) -> Decimal:
        """Calculate this week's drawdown percentage."""
        if self.week_start_equity == 0:
            return Decimal("0")
        return (self.week_start_equity - self.current_equity) / self.week_start_equity


@dataclass(frozen=True)
class RiskCheckResult:
    """
    Comprehensive result from risk manager evaluation.

    Attributes:
        decision: The risk decision (APPROVED, REJECTED, etc.)
        rejection_reason: Specific reason if rejected (None if approved)
        approved_contracts: Number of contracts approved
        original_request: The original position size request
        position_size_result: Detailed position sizing breakdown
        pdt_trades_remaining: Day trades remaining in window
        daily_loss_remaining: Dollars remaining before daily limit
        weekly_drawdown_pct: Current weekly drawdown percentage
        governor_active: Whether Strategy C is locked
        warnings: Non-blocking warnings (e.g., approaching limits)
        timestamp: When this check was performed
    """

    decision: RiskDecision
    rejection_reason: Optional[RejectionReason]
    approved_contracts: int
    original_request: Optional[PositionSizeRequest]
    position_size_result: Optional[PositionSizeResult]
    pdt_trades_remaining: int
    daily_loss_remaining: Decimal
    weekly_drawdown_pct: Decimal
    governor_active: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=datetime.now)
