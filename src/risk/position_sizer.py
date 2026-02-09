"""
Position sizing engine.

Calculates maximum safe position size based on:
1. Account risk limit (3% max risk per trade — $18)
2. Strategy position limit (20% for A, 10% for B, 0% for C)
3. Available cash (cannot exceed buying power)
4. Confidence gating (signals below 0.5 rejected)

All calculations use Decimal for financial precision where critical,
with float interface for compatibility with existing tests.

CRITICAL: All limits are HARD STOPS, not warnings. If a position cannot
be sized within limits, it is rejected entirely.
"""

from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Protocol, Tuple

from src.risk.risk_types import (
    PositionSizeRequest,
    PositionSizeResult,
    RejectionReason,
)


class AccountProvider(Protocol):
    """Protocol for account data access."""

    def get_account_equity(self) -> Decimal:
        """Return current account equity."""
        ...

    def get_buying_power(self) -> Decimal:
        """Return available buying power."""
        ...


class PositionSizer:
    """
    Calculates safe position sizes within risk parameters.

    This class enforces:
    - 3% maximum risk per trade (configurable)
    - Strategy-specific position size limits (20%/10%/0%)
    - Cash/buying power constraints
    - Confidence threshold gating

    All limits are HARD STOPS, not warnings. If a position cannot
    be sized within limits, it is rejected entirely.
    """

    # Strategy-specific position limits (fraction of account)
    STRATEGY_POSITION_LIMITS: Dict[str, Decimal] = {
        "A": Decimal("0.20"),  # 20% max for Momentum Breakout
        "B": Decimal("0.10"),  # 10% max for Mean Reversion
        "C": Decimal("0.00"),  # 0% — no new positions in Cash Preservation
    }

    # Minimum confidence threshold for any trade
    CONFIDENCE_THRESHOLD = Decimal("0.5")

    # Options contract multiplier
    CONTRACT_MULTIPLIER = 100

    def __init__(
        self,
        account_balance: float,
        max_position_pct: float = 0.20,
        max_risk_pct: float = 0.03,
        pdt_limit: int = 3,
        account_provider: Optional[AccountProvider] = None,
    ) -> None:
        """
        Initialize position sizer.

        Args:
            account_balance: Current account balance in dollars
            max_position_pct: Maximum position as fraction of account (default 0.20)
            max_risk_pct: Maximum risk per trade as fraction (default 0.03)
            pdt_limit: Maximum day trades in rolling window (default 3)
            account_provider: Optional protocol for dynamic account data
        """
        self._account_balance = Decimal(str(account_balance))
        self._max_position_pct = Decimal(str(max_position_pct))
        self._max_risk_pct = Decimal(str(max_risk_pct))
        self._pdt_limit = pdt_limit
        self._account_provider = account_provider

    @property
    def account_balance(self) -> float:
        """Return current account balance."""
        return float(self._account_balance)

    @property
    def max_position_size(self) -> float:
        """Calculate maximum position size in dollars."""
        return float(self._account_balance * self._max_position_pct)

    @property
    def max_risk_per_trade(self) -> float:
        """Calculate maximum risk per trade in dollars."""
        return float(self._account_balance * self._max_risk_pct)

    # =========================================================================
    # POSITION SIZE VALIDATION (Interface for existing tests)
    # =========================================================================

    def validate_position_size(self, position_value: float) -> bool:
        """
        Validate that a position size is within limits.

        Args:
            position_value: Total position value in dollars

        Returns:
            True if position is within limit, False otherwise
        """
        if position_value < 0:
            return False

        max_position = self._account_balance * self._max_position_pct
        # Use explicit comparison to avoid floating-point issues
        return Decimal(str(position_value)) <= max_position

    def validate_trade_risk(self, risk_amount: float) -> bool:
        """
        Validate that trade risk is within limits.

        Args:
            risk_amount: Trade risk in dollars

        Returns:
            True if risk is within limit, False otherwise
        """
        if risk_amount < 0:
            return False

        max_risk = self._account_balance * self._max_risk_pct
        return Decimal(str(risk_amount)) <= max_risk

    def calculate_trade_risk(
        self,
        entry_price: float,
        stop_price: float,
        multiplier: int = 100,
        quantity: int = 1,
    ) -> float:
        """
        Calculate the dollar risk for a trade.

        Risk = (entry_price - stop_price) * multiplier * quantity

        Args:
            entry_price: Entry price per share/contract
            stop_price: Stop-loss price
            multiplier: Contract multiplier (default 100 for options)
            quantity: Number of contracts

        Returns:
            Dollar risk amount
        """
        price_diff = Decimal(str(entry_price)) - Decimal(str(stop_price))
        risk = price_diff * Decimal(multiplier) * Decimal(quantity)
        return float(risk)

    # =========================================================================
    # CONTRACT AFFORDABILITY
    # =========================================================================

    def check_affordability(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a contract is affordable within position limits.

        Args:
            contract: Contract dictionary with premium and multiplier

        Returns:
            Dictionary with 'affordable' bool and 'max_contracts' int
        """
        premium = contract.get("premium", 0)
        multiplier = contract.get("multiplier", 100)

        # Reject invalid premiums
        if premium is None or premium <= 0:
            return {"affordable": False, "max_contracts": 0, "reason": "invalid_premium"}

        premium_decimal = Decimal(str(premium))
        multiplier_decimal = Decimal(str(multiplier))

        # Cost per contract = premium * multiplier
        cost_per_contract = premium_decimal * multiplier_decimal
        max_position = self._account_balance * self._max_position_pct

        if cost_per_contract > max_position:
            return {"affordable": False, "max_contracts": 0, "reason": "exceeds_limit"}

        # Calculate max contracts (floor division)
        max_contracts = int(
            (max_position / cost_per_contract).quantize(Decimal("1"), rounding=ROUND_DOWN)
        )

        return {
            "affordable": max_contracts >= 1,
            "max_contracts": max_contracts,
            "max_value": float(max_contracts * cost_per_contract),
        }

    # =========================================================================
    # AGGREGATE EXPOSURE VALIDATION
    # =========================================================================

    def validate_aggregate_exposure(
        self,
        open_positions: List[Dict[str, Any]],
        new_position_cost: float,
    ) -> bool:
        """
        Validate that aggregate exposure (all open positions + new) is within limits.

        Args:
            open_positions: List of open position dicts with 'cost_basis' key
            new_position_cost: Cost of the new position to add

        Returns:
            True if total exposure is within limit, False otherwise
        """
        # Sum existing position costs
        existing_total = sum(Decimal(str(pos.get("cost_basis", 0))) for pos in open_positions)

        new_cost = Decimal(str(new_position_cost))
        total_exposure = existing_total + new_cost
        max_position = self._account_balance * self._max_position_pct

        return total_exposure <= max_position

    # =========================================================================
    # POSITION SIZE MULTIPLIER
    # =========================================================================

    def apply_multiplier(self, base_size: float, multiplier: float) -> float:
        """
        Apply a multiplier to adjust position size.

        Args:
            base_size: Base position size in dollars
            multiplier: Multiplier (0.0 to 1.0, clamped if > 1.0)

        Returns:
            Adjusted position size

        Raises:
            ValueError: If multiplier is negative
        """
        if multiplier < 0:
            raise ValueError("Multiplier cannot be negative")

        # Clamp multiplier to max 1.0
        effective_multiplier = min(multiplier, 1.0)
        return base_size * effective_multiplier

    # =========================================================================
    # ADVANCED POSITION SIZING (For RiskManager integration)
    # =========================================================================

    def calculate_position_size(
        self,
        request: PositionSizeRequest,
    ) -> Tuple[PositionSizeResult, Optional[RejectionReason]]:
        """
        Calculate maximum safe position size.

        This method enforces all position sizing rules and returns
        the most conservative (smallest) size that satisfies all
        constraints.

        Args:
            request: Position sizing request with all required inputs

        Returns:
            Tuple of (PositionSizeResult, RejectionReason or None)
            If rejected, approved_contracts will be 0.
        """
        # Gate 1: Confidence threshold
        if request.signal_confidence < float(self.CONFIDENCE_THRESHOLD):
            return self._reject(request, RejectionReason.CONFIDENCE_BELOW_THRESHOLD, "confidence")

        # Gate 2: Strategy C check (no new positions)
        if request.strategy == "C":
            return self._reject(request, RejectionReason.STRATEGY_C_ACTIVE, "strategy_c")

        # Gate 3: Premium affordability
        if request.entry_price <= 0:
            return self._reject(request, RejectionReason.PREMIUM_UNAFFORDABLE, "invalid_premium")

        account_equity = self._get_account_equity()
        buying_power = self._get_buying_power(request.account_cash)

        # Calculate constraint-specific maximums
        max_by_risk = self._max_contracts_by_risk(
            account_equity,
            request.entry_price,
            request.stop_loss_pct,
        )

        max_by_position = self._max_contracts_by_position(
            account_equity,
            request.entry_price,
            request.strategy,
        )

        max_by_cash = self._max_contracts_by_cash(
            buying_power,
            request.entry_price,
        )

        # Take the minimum (most conservative)
        approved = min(max_by_risk, max_by_position, max_by_cash)

        # Determine limiting factor
        limiting_factor = self._determine_limiting_factor(
            approved, max_by_risk, max_by_position, max_by_cash
        )

        # Calculate final values
        position_value = Decimal(approved) * request.entry_price * self.CONTRACT_MULTIPLIER
        risk_amount = position_value * request.stop_loss_pct

        result = PositionSizeResult(
            approved_contracts=approved,
            max_contracts_by_risk=max_by_risk,
            max_contracts_by_position=max_by_position,
            max_contracts_by_cash=max_by_cash,
            limiting_factor=limiting_factor,
            position_value=position_value,
            risk_amount=risk_amount,
        )

        if approved == 0:
            return result, RejectionReason.INSUFFICIENT_BUYING_POWER

        return result, None

    def _get_account_equity(self) -> Decimal:
        """Get account equity from provider or use stored balance."""
        if self._account_provider:
            return self._account_provider.get_account_equity()
        return self._account_balance

    def _get_buying_power(self, account_cash: Decimal) -> Decimal:
        """Get buying power from provider or use provided cash."""
        if self._account_provider:
            return self._account_provider.get_buying_power()
        return account_cash

    def _max_contracts_by_risk(
        self,
        account_equity: Decimal,
        entry_price: Decimal,
        stop_loss_pct: Decimal,
    ) -> int:
        """
        Calculate max contracts by risk rule.

        Formula:
        max_risk = account_equity * max_risk_pct
        risk_per_contract = entry_price * CONTRACT_MULTIPLIER * stop_loss_pct
        max_contracts = max_risk / risk_per_contract

        Uses ROUND_DOWN to ensure we never exceed limit.
        """
        max_risk = account_equity * self._max_risk_pct

        # Risk per contract = premium * multiplier * stop_loss_pct
        contract_cost = entry_price * self.CONTRACT_MULTIPLIER
        risk_per_contract = contract_cost * stop_loss_pct

        if risk_per_contract <= 0:
            return 0

        max_contracts = (max_risk / risk_per_contract).quantize(Decimal("1"), rounding=ROUND_DOWN)

        return int(max_contracts)

    def _max_contracts_by_position(
        self,
        account_equity: Decimal,
        entry_price: Decimal,
        strategy: str,
    ) -> int:
        """
        Calculate max contracts by position size limit.

        Strategy A: 20% of account
        Strategy B: 10% of account
        Strategy C: 0% (no new positions)

        Uses ROUND_DOWN to ensure we never exceed limit.
        """
        position_limit_pct = self.STRATEGY_POSITION_LIMITS.get(strategy, Decimal("0"))

        if position_limit_pct == 0:
            return 0

        max_position_value = account_equity * position_limit_pct
        contract_cost = entry_price * self.CONTRACT_MULTIPLIER

        if contract_cost <= 0:
            return 0

        max_contracts = (max_position_value / contract_cost).quantize(
            Decimal("1"), rounding=ROUND_DOWN
        )

        return int(max_contracts)

    def _max_contracts_by_cash(
        self,
        buying_power: Decimal,
        entry_price: Decimal,
    ) -> int:
        """
        Calculate max contracts by available cash.

        Cannot buy more contracts than we can afford.
        Uses ROUND_DOWN to ensure we never exceed buying power.
        """
        contract_cost = entry_price * self.CONTRACT_MULTIPLIER

        if contract_cost <= 0:
            return 0

        max_contracts = (buying_power / contract_cost).quantize(Decimal("1"), rounding=ROUND_DOWN)

        return int(max_contracts)

    def _determine_limiting_factor(
        self,
        approved: int,
        by_risk: int,
        by_position: int,
        by_cash: int,
    ) -> str:
        """Identify which constraint was binding."""
        if approved == by_risk:
            return "risk_limit"
        elif approved == by_position:
            return "position_limit"
        elif approved == by_cash:
            return "buying_power"
        return "unknown"

    def _reject(
        self,
        request: PositionSizeRequest,
        reason: RejectionReason,
        limiting_factor: str,
    ) -> Tuple[PositionSizeResult, RejectionReason]:
        """Create a rejection result."""
        result = PositionSizeResult(
            approved_contracts=0,
            max_contracts_by_risk=0,
            max_contracts_by_position=0,
            max_contracts_by_cash=0,
            limiting_factor=limiting_factor,
            position_value=Decimal("0"),
            risk_amount=Decimal("0"),
        )
        return result, reason
