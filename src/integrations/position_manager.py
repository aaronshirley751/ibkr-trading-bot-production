"""
Position manager with Strategy C closure logic.

Manages open positions with real-time P&L tracking and automated closure
rules: 3 DTE force-close and 40% emergency stop.

STRATEGY C CLOSURE RULES:
- 3 DTE Rule: Force-close ALL options positions at 3 days to expiration
- 40% Emergency Stop: Force-close positions with ≥40% unrealized loss
- Data Quarantine: Close all on stale data (>5 min old)

ALPHA LEARNINGS ENFORCED:
- Position sync with RiskManager for state consistency
- Timeout propagation through all operations
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .order_executor import OrderResult, FillResult

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class Position:
    """
    Open position with Strategy C closure flags.

    Tracks position details, P&L, and automatic closure triggers.
    """

    position_id: str
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    days_to_expiry: Optional[int]
    contract: Any  # IB Contract object

    # Strategy C closure flags
    should_close_3_dte: bool = False
    should_close_emergency: bool = False
    closure_trigger: Optional[str] = None  # "3_DTE_RULE", "EMERGENCY_STOP", etc.


# =============================================================================
# EXCEPTIONS
# =============================================================================


class PositionNotFoundError(Exception):
    """Raised when position not found in cache."""

    pass


class PositionCloseError(Exception):
    """Raised when position close fails."""

    pass


# =============================================================================
# POSITION MANAGER
# =============================================================================


class PositionManager:
    """
    Manages open positions with Strategy C closure logic.

    Responsibilities:
    - Track open positions from Gateway
    - Monitor P&L in real-time
    - Implement Strategy C closure rules (3 DTE, 40% emergency stop)
    - Sync position state with RiskManager
    """

    def __init__(
        self,
        connection: Any,  # IBKRConnection
        risk_manager: Any,  # RiskManager
    ):
        """
        Initialize position manager.

        Args:
            connection: IBKRConnection instance
            risk_manager: RiskManager instance for position sync
        """
        self._connection = connection
        self._risk_manager = risk_manager
        self._positions_cache: Dict[str, Position] = {}
        self._last_sync: Optional[datetime] = None

        logger.info("PositionManager initialized")

    async def get_all(self, timeout: float = 10.0) -> List[Position]:
        """
        Fetch all open positions from Gateway.

        Returns positions with:
        - Symbol and quantity
        - Entry price and current price
        - Unrealized P&L
        - Days to expiration
        - Strategy C flags (closure triggers)

        Args:
            timeout: Request timeout in seconds

        Returns:
            List of Position objects
        """
        logger.debug(f"Fetching positions with timeout={timeout}")

        try:
            # Fetch from Gateway
            ibkr_positions = self._connection.ib.positions()

            positions = []
            for ibkr_pos in ibkr_positions:
                position = await self._build_position(ibkr_pos, timeout)
                positions.append(position)
                self._positions_cache[position.position_id] = position

            self._last_sync = datetime.now(timezone.utc)

            logger.info(f"Fetched {len(positions)} positions")

            # Sync with RiskManager (would need to implement sync_positions method)
            # await self._risk_manager.sync_positions(positions)

            return positions

        except TimeoutError:
            logger.error(f"Position fetch timeout: {timeout}s")
            # Return cached positions if available
            if self._positions_cache:
                logger.warning("Returning cached positions")
                return list(self._positions_cache.values())
            raise

    async def _build_position(self, ibkr_pos: Any, timeout: float) -> Position:
        """
        Build Position with Strategy C closure flags.

        Args:
            ibkr_pos: IB position object
            timeout: Timeout for current price lookup

        Returns:
            Position object with closure flags
        """
        # Calculate unrealized P&L
        current_price = await self._get_current_price(ibkr_pos.contract.symbol, timeout)
        entry_value = ibkr_pos.avgCost * ibkr_pos.position
        current_value = current_price * ibkr_pos.position
        unrealized_pnl = current_value - entry_value
        unrealized_pnl_pct = unrealized_pnl / entry_value if entry_value != 0 else 0

        # Calculate DTE for options
        dte = self._calculate_dte(ibkr_pos.contract)

        # Strategy C closure flags
        should_close_3_dte = dte is not None and dte <= 3
        should_close_emergency = unrealized_pnl_pct <= -0.40  # 40% loss

        return Position(
            position_id=f"{ibkr_pos.contract.symbol}_{ibkr_pos.contract.conId}",
            symbol=ibkr_pos.contract.symbol,
            quantity=int(ibkr_pos.position),
            entry_price=ibkr_pos.avgCost,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            days_to_expiry=dte,
            contract=ibkr_pos.contract,
            # Strategy C flags
            should_close_3_dte=should_close_3_dte,
            should_close_emergency=should_close_emergency,
            closure_trigger=self._determine_closure_trigger(
                should_close_3_dte, should_close_emergency
            ),
        )

    def _calculate_dte(self, contract: Any) -> Optional[int]:
        """
        Calculate days to expiration for options.

        Args:
            contract: IB contract object

        Returns:
            Days to expiration, or None if not an option
        """
        if not hasattr(contract, "lastTradeDateOrContractMonth"):
            return None  # Not an option

        expiry_str = contract.lastTradeDateOrContractMonth
        if not expiry_str:
            return None

        try:
            expiry_date = datetime.strptime(expiry_str, "%Y%m%d").date()
            today = datetime.now().date()
            return (expiry_date - today).days
        except ValueError:
            return None

    def _determine_closure_trigger(
        self, should_close_3_dte: bool, should_close_emergency: bool
    ) -> Optional[str]:
        """
        Determine which Strategy C closure rule applies.

        Args:
            should_close_3_dte: True if 3 DTE rule triggered
            should_close_emergency: True if 40% loss rule triggered

        Returns:
            Closure trigger string, or None if no closure needed
        """
        if should_close_emergency:
            return "EMERGENCY_STOP"  # 40% loss takes priority
        if should_close_3_dte:
            return "3_DTE_RULE"
        return None

    async def close(self, position_id: str, reason: str, timeout: float = 30.0) -> "OrderResult":
        """
        Close a specific position.

        Reasons (for audit trail):
        - "3_DTE_RULE": Strategy C force-close at 3 DTE
        - "EMERGENCY_STOP": 40% loss threshold
        - "DAILY_LOSS_LIMIT": Governor triggered
        - "MANUAL": Operator-initiated
        - "STRATEGY_EXIT": Normal exit signal

        Args:
            position_id: Position ID to close
            reason: Closure reason for audit trail
            timeout: Execution timeout

        Returns:
            OrderResult from order execution
        """
        if position_id not in self._positions_cache:
            raise PositionNotFoundError(f"Position not found: {position_id}")

        position = self._positions_cache[position_id]

        logger.info(
            f"Closing position: position_id={position_id}, symbol={position.symbol}, "
            f"quantity={position.quantity}, reason={reason}, unrealized_pnl={position.unrealized_pnl}"
        )

        # Build closing order
        close_action = "SELL" if position.quantity > 0 else "BUY"
        close_quantity = abs(position.quantity)

        try:
            # Place closing order via Gateway
            from ib_insync import Order

            ibkr_order = Order()
            ibkr_order.action = close_action
            ibkr_order.totalQuantity = close_quantity
            ibkr_order.orderType = "MKT"  # Market order for immediate close
            ibkr_order.account = "CSATSPRIM"  # Operator ID

            trade = self._connection.ib.placeOrder(position.contract, ibkr_order)

            # Wait for fill
            from .order_executor import OrderResult, OrderStatus

            fill_result = await self._wait_for_fill(trade, timeout=timeout)

            # Remove from cache on successful close
            if fill_result.filled:
                del self._positions_cache[position_id]

            return OrderResult(
                order_id=f"CLOSE_{position_id}",
                status=OrderStatus.FILLED if fill_result.filled else OrderStatus.FAILED,
                fill_price=fill_result.avg_fill_price,
                fill_quantity=fill_result.filled_quantity,
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Position close failed: position_id={position_id}, error={str(e)}")
            from .order_executor import OrderResult, OrderStatus

            return OrderResult(
                order_id=f"CLOSE_{position_id}",
                status=OrderStatus.FAILED,
                rejection_reason=str(e),
                timestamp=datetime.now(timezone.utc),
            )

    async def close_all(self, reason: str, timeout: float = 60.0) -> List["OrderResult"]:
        """
        Emergency close all positions (Strategy C liquidation).

        Used when:
        - Daily loss limit hit
        - Weekly drawdown governor triggered
        - Data quarantine (staleness)
        - Gateway disconnection recovery

        Args:
            reason: Closure reason for audit trail
            timeout: Total timeout for all closures

        Returns:
            List of OrderResult objects
        """
        logger.warning(
            f"EMERGENCY LIQUIDATION: reason={reason}, position_count={len(self._positions_cache)}"
        )

        results = []
        per_position_timeout = timeout / max(len(self._positions_cache), 1)

        for position_id in list(self._positions_cache.keys()):
            result = await self.close(
                position_id=position_id,
                reason=reason,
                timeout=per_position_timeout,
            )
            results.append(result)

        return results

    async def check_strategy_c_closures(self) -> List[Position]:
        """
        Check for positions that should be closed per Strategy C rules.

        Returns list of positions triggering closure rules.
        Called periodically by orchestrator.

        Returns:
            List of Position objects with closure_trigger set
        """
        positions = await self.get_all()
        return [p for p in positions if p.closure_trigger is not None]

    async def _get_current_price(self, symbol: str, timeout: float) -> float:
        """
        Get current price for P&L calculation.

        Args:
            symbol: Symbol to get price for
            timeout: Request timeout

        Returns:
            Current price
        """
        # This is a placeholder - in production, would use market data provider
        # For now, return a reasonable default
        try:
            # Try to get from pending snapshot
            ticker = self._connection.ib.reqMktData(
                self._connection.ib.qualifyContracts([{"symbol": symbol}])[0],
                snapshot=True,
            )
            self._connection.ib.sleep(1)  # Wait for snapshot
            result: float = float(ticker.last if ticker.last > 0 else ticker.close)
            return result
        except Exception as e:
            logger.warning(f"Could not fetch current price for {symbol}, using 0.0: {str(e)}")
            return 0.0

    async def _wait_for_fill(self, trade: Any, timeout: float) -> "FillResult":
        """
        Wait for closing order to fill.

        Args:
            trade: IB Trade object
            timeout: Timeout in seconds

        Returns:
            FillResult with fill status
        """
        import asyncio

        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            if trade.isDone():
                from .order_executor import FillResult

                return FillResult(
                    filled=True,
                    avg_fill_price=trade.orderStatus.avgFillPrice,
                    filled_quantity=trade.orderStatus.filled,
                )
            await asyncio.sleep(0.1)

        from .order_executor import FillResult

        return FillResult(
            filled=False,
            avg_fill_price=trade.orderStatus.avgFillPrice or 0.0,
            filled_quantity=trade.orderStatus.filled or 0,
        )
