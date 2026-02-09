"""
Order executor with mandatory RiskManager validation.

Executes orders with full risk validation pipeline. Every order MUST flow
through RiskManager.validate_trade() before any execution path.

CRITICAL SAFETY INVARIANT:
No order can bypass RiskManager validation. No "quick" path. No exceptions.

ALPHA LEARNINGS ENFORCED:
- Operator ID attached to all orders (compliance requirement)
- Contract qualification before execution
- Timeout propagation through execution stack
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

from ib_insync import Order, Trade

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class ExecutionMode(Enum):
    """Execution mode for orders."""

    DRY_RUN = "dry_run"  # Log only, no execution
    PAPER = "paper"  # Execute via paper trading Gateway
    LIVE = "live"  # BLOCKED until Phase 4


class OrderStatus(Enum):
    """Order execution status."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SIMULATED = "simulated"  # Dry-run only
    CANCELLED = "cancelled"


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class TradeRequest:
    """Trade request for risk validation and execution."""

    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: int
    order_type: str  # "MKT", "LMT", etc.
    limit_price: Optional[float]
    strategy_id: str
    strategy_name: str
    risk_per_trade: float
    take_profit_pct: float
    stop_loss_pct: float
    expiry: Optional[str] = None  # YYYYMMDD format for options
    strike: Optional[float] = None  # Strike price for options
    right: Optional[str] = None  # "C" or "P" for options
    operator_id: str = "CSATSPRIM"  # Compliance requirement


@dataclass
class OrderResult:
    """Result of order execution attempt."""

    order_id: str
    status: OrderStatus
    timestamp: datetime
    ibkr_order_id: Optional[int] = None
    fill_price: Optional[float] = None
    fill_quantity: Optional[int] = None
    rejection_reason: Optional[str] = None
    execution_mode: Optional[ExecutionMode] = None
    risk_validation: Optional[Dict[str, Any]] = None


@dataclass
class FillResult:
    """Fill status from order execution."""

    filled: bool
    avg_fill_price: float
    filled_quantity: int


# =============================================================================
# EXCEPTIONS
# =============================================================================


class OrderExecutionError(Exception):
    """Base exception for order execution errors."""

    pass


# =============================================================================
# ORDER EXECUTOR
# =============================================================================


class OrderExecutor:
    """
    Executes orders with mandatory RiskManager validation.

    CRITICAL SAFETY INVARIANT:
    Every order MUST flow through RiskManager.validate_trade()
    before any execution path (dry-run, paper, or live).

    There is NO bypass. No "quick" path. No exceptions.

    Responsibilities:
    - Validate all orders through RiskManager
    - Enforce operator ID on all orders
    - Route to appropriate execution mode
    - Track order results for position management
    """

    def __init__(
        self,
        connection: Any,  # IBKRConnection
        contracts: Any,  # ContractManager
        risk_manager: Any,  # RiskManager
        mode: ExecutionMode,
        operator_id: str = "CSATSPRIM",
    ):
        """
        Initialize order executor.

        Args:
            connection: IBKRConnection instance
            contracts: ContractManager instance
            risk_manager: RiskManager instance
            mode: Execution mode (DRY_RUN, PAPER, or LIVE-blocked)
            operator_id: Operator ID for compliance (default "CSATSPRIM")
        """
        self._connection = connection
        self._contracts = contracts
        self._risk_manager = risk_manager
        self._mode = mode
        self._operator_id = operator_id

        # Order tracking
        self._pending_orders: Dict[str, Any] = {}
        self._order_counter = 0

        logger.info(f"OrderExecutor initialized: mode={mode.value}, operator_id={operator_id}")

    async def execute(
        self,
        signal: Any,  # Signal from strategy layer
        strategy_context: Dict[str, Any],
        timeout: float = 30.0,
    ) -> OrderResult:
        """
        Execute trading signal with full risk validation.

        Flow:
        1. Build TradeRequest from signal
        2. RiskManager.validate_trade() — MANDATORY
        3. If rejected: Return rejection result
        4. If approved: Route to execution mode
        5. Track result

        Args:
            signal: Trading signal from strategy layer
            strategy_context: Strategy context (strategy_id, name, risk params)
            timeout: Execution timeout in seconds

        Returns:
            OrderResult with execution details or rejection reason
        """
        # Step 1: Build trade request
        trade_request = self._build_trade_request(signal, strategy_context)

        logger.info(
            f"Executing order: symbol={trade_request.symbol}, action={trade_request.action}, "
            f"quantity={trade_request.quantity}, strategy={trade_request.strategy_name}, mode={self._mode.value}"
        )

        # Step 2: MANDATORY RISK VALIDATION
        # This is the critical safety gate. No bypass allowed.
        validation_result = await self._validate_with_risk_manager(trade_request)

        if not validation_result.get("approved", False):
            # Risk validation failed — return rejection
            rejection_reasons = validation_result.get("rejection_reasons", [])
            logger.warning(
                f"Order rejected by RiskManager: symbol={trade_request.symbol}, "
                f"action={trade_request.action}, rejection_reasons={rejection_reasons}"
            )
            return OrderResult(
                order_id=self._generate_order_id(),
                status=OrderStatus.REJECTED,
                rejection_reason="; ".join(str(r) for r in rejection_reasons),
                risk_validation=validation_result,
                timestamp=datetime.now(timezone.utc),
            )

        # Step 3: Route to execution mode
        if self._mode == ExecutionMode.DRY_RUN:
            return await self._execute_dry_run(trade_request, validation_result)
        elif self._mode == ExecutionMode.PAPER:
            return await self._execute_paper(trade_request, validation_result, timeout)
        else:
            # ExecutionMode.LIVE blocked in IBKRGateway.__init__
            # This should never be reached
            raise OrderExecutionError("Live execution blocked — this should be unreachable")

    def _build_trade_request(self, signal: Any, context: Dict[str, Any]) -> TradeRequest:
        """
        Build TradeRequest from signal and strategy context.

        Args:
            signal: Signal object from strategy layer
            context: Strategy context dict

        Returns:
            TradeRequest for risk validation
        """
        # Determine action from signal direction
        action = "BUY" if signal.direction.value == "buy" else "SELL"

        # Get quantity from context or default to 1
        quantity = context.get("quantity", 1)

        # Get order type from signal or default to MKT
        order_type = context.get("order_type", "MKT")

        # Get limit price from signal if available
        limit_price = signal.entry_price if hasattr(signal, "entry_price") else None

        return TradeRequest(
            symbol=signal.symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            strategy_id=context.get("strategy_id", "unknown"),
            strategy_name=context.get("strategy_name", signal.strategy_type.value),
            risk_per_trade=context.get("risk_per_trade", 0.02),
            take_profit_pct=context.get("take_profit_pct", 0.20),
            stop_loss_pct=context.get("stop_loss_pct", 0.25),
            expiry=context.get("expiry"),
            strike=context.get("strike"),
            right=context.get("right"),
            operator_id=self._operator_id,
        )

    async def _validate_with_risk_manager(self, trade_request: TradeRequest) -> Dict[str, Any]:
        """
        Validate trade request with RiskManager.

        This is the critical safety gate. Every order must pass through here.

        Args:
            trade_request: Trade request to validate

        Returns:
            Validation result dict with: approved, rejection_reasons, risk_metrics
        """
        # Build position size request for risk manager
        from src.risk.risk_types import PositionSizeRequest

        position_request = PositionSizeRequest(
            symbol=trade_request.symbol,
            strategy=trade_request.strategy_id,
            signal_confidence=0.8,  # Default confidence
            entry_price=Decimal(str(trade_request.limit_price or 1.0)),
            stop_loss_pct=Decimal(str(trade_request.stop_loss_pct)),
            account_cash=Decimal("25000.0"),  # Placeholder - should come from account
            current_positions_value=Decimal("0.0"),  # Placeholder
        )

        # Call risk manager evaluation
        risk_result = self._risk_manager.evaluate(position_request)

        # Convert risk result to dict for logging
        return {
            "approved": risk_result.approved,
            "rejection_reasons": [r.name for r in risk_result.rejections],
            "risk_metrics": {
                "approved_contracts": str(risk_result.approved_contracts),
                "risk_per_trade": str(risk_result.risk_per_trade),
            },
        }

    async def _execute_dry_run(
        self, trade_request: TradeRequest, validation: Dict[str, Any]
    ) -> OrderResult:
        """
        Dry-run execution: Log only, no actual order.

        Used for:
        - Development and testing
        - Strategy validation
        - Pre-deployment verification

        Args:
            trade_request: Trade request to simulate
            validation: Risk validation result

        Returns:
            OrderResult with SIMULATED status
        """
        order_id = self._generate_order_id()

        logger.info(
            f"DRY-RUN ORDER: order_id={order_id}, symbol={trade_request.symbol}, "
            f"action={trade_request.action}, quantity={trade_request.quantity}, "
            f"order_type={trade_request.order_type}, limit_price={trade_request.limit_price}, "
            f"strategy={trade_request.strategy_name}, operator_id={trade_request.operator_id}, "
            f"risk_metrics={validation.get('risk_metrics', {})}"
        )

        # Simulate fill for testing purposes
        simulated_fill_price = trade_request.limit_price or 100.0

        return OrderResult(
            order_id=order_id,
            status=OrderStatus.SIMULATED,
            fill_price=simulated_fill_price,
            fill_quantity=trade_request.quantity,
            execution_mode=ExecutionMode.DRY_RUN,
            risk_validation=validation,
            timestamp=datetime.now(timezone.utc),
        )

    async def _execute_paper(
        self,
        trade_request: TradeRequest,
        validation: Dict[str, Any],
        timeout: float,
    ) -> OrderResult:
        """
        Paper trading execution: Execute via Gateway paper account.

        Flow:
        1. Qualify contract
        2. Build IBKR order
        3. Place via Gateway
        4. Wait for fill or timeout
        5. Return result

        Args:
            trade_request: Trade request to execute
            validation: Risk validation result
            timeout: Execution timeout

        Returns:
            OrderResult with execution details
        """
        order_id = self._generate_order_id()

        try:
            # Step 1: Qualify contract
            # ALPHA LEARNING: Contract must be qualified before order
            if trade_request.expiry and trade_request.strike and trade_request.right:
                # Options contract
                contract = self._contracts.qualify_option_contract(
                    symbol=trade_request.symbol,
                    expiry=trade_request.expiry,
                    strike=trade_request.strike,
                    right=trade_request.right,
                    timeout=int(timeout),
                )
            else:
                # Stock contract
                contract = self._contracts.qualify_contract(
                    symbol=trade_request.symbol, timeout=int(timeout)
                )

            # Step 2: Build IBKR order
            ibkr_order = self._build_ibkr_order(trade_request)

            # Step 3: Place order via Gateway
            trade = self._connection.ib.placeOrder(contract, ibkr_order)

            # Step 4: Wait for fill
            fill_result = await self._wait_for_fill(trade, timeout=timeout)

            logger.info(
                f"PAPER ORDER EXECUTED: order_id={order_id}, symbol={trade_request.symbol}, "
                f"action={trade_request.action}, fill_price={fill_result.avg_fill_price}, "
                f"filled_quantity={fill_result.filled_quantity}, operator_id={trade_request.operator_id}"
            )

            return OrderResult(
                order_id=order_id,
                status=OrderStatus.FILLED if fill_result.filled else OrderStatus.PARTIAL,
                ibkr_order_id=ibkr_order.orderId,
                fill_price=fill_result.avg_fill_price,
                fill_quantity=fill_result.filled_quantity,
                execution_mode=ExecutionMode.PAPER,
                risk_validation=validation,
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(
                f"Order execution failed: order_id={order_id}, symbol={trade_request.symbol}, error={str(e)}"
            )
            return OrderResult(
                order_id=order_id,
                status=OrderStatus.FAILED,
                rejection_reason=str(e),
                timestamp=datetime.now(timezone.utc),
            )

    def _build_ibkr_order(self, trade_request: TradeRequest) -> Order:
        """
        Build ib_insync Order from TradeRequest.

        Args:
            trade_request: Trade request

        Returns:
            ib_insync Order object
        """
        order = Order()
        order.action = trade_request.action
        order.totalQuantity = trade_request.quantity
        order.orderType = trade_request.order_type

        if trade_request.limit_price:
            order.lmtPrice = trade_request.limit_price

        # COMPLIANCE REQUIREMENT: Operator ID on all orders
        order.account = trade_request.operator_id

        return order

    async def _wait_for_fill(self, trade: Trade, timeout: float) -> FillResult:
        """
        Wait for order to fill with timeout.

        Args:
            trade: ib_insync Trade object
            timeout: Timeout in seconds

        Returns:
            FillResult with fill status
        """
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            if trade.isDone():
                return FillResult(
                    filled=True,
                    avg_fill_price=trade.orderStatus.avgFillPrice,
                    filled_quantity=trade.orderStatus.filled,
                )
            await asyncio.sleep(0.1)

        # Timeout — return partial fill status
        return FillResult(
            filled=False,
            avg_fill_price=trade.orderStatus.avgFillPrice or 0.0,
            filled_quantity=trade.orderStatus.filled or 0,
        )

    def _generate_order_id(self) -> str:
        """
        Generate unique order ID for tracking.

        Returns:
            Unique order ID string
        """
        self._order_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"ORD_{timestamp}_{self._order_counter:04d}"
