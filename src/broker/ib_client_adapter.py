"""
Adapter that wraps ib_insync.IB to implement the IBClientLike protocol
expected by OrderManager.

ib_insync.IB.placeOrder signature:
    placeOrder(contract: Contract, order: Order) -> Trade

IBClientLike.placeOrder protocol:
    placeOrder(order_id: int, contract: ContractLike, order: Order) -> None

The adapter bridges this mismatch. The order_id parameter is accepted but
not forwarded — ib_insync manages order IDs internally via TWS/Gateway.
"""

import logging

from ib_insync import IB, Order

from src.bot.execution.order_manager import ContractLike

logger = logging.getLogger(__name__)


class IbClientAdapter:
    """
    Thin adapter that conforms ib_insync.IB to the IBClientLike protocol.

    Usage::

        connection = IBKRConnection(...)
        connection.connect()
        adapter = IbClientAdapter(connection.ib)
        order_manager = OrderManager(ib_client=adapter)
    """

    def __init__(self, ib: IB) -> None:
        """
        Args:
            ib: Connected ib_insync.IB instance.
        """
        self._ib = ib

    def placeOrder(self, order_id: int, contract: ContractLike, order: Order) -> None:
        """
        Delegate to IB.placeOrder, discarding the order_id.

        ib_insync assigns its own internal order ID and does not accept one
        from the caller. The order_id parameter is accepted to satisfy
        IBClientLike but is not forwarded.

        Args:
            order_id: Caller-assigned order ID (unused by ib_insync).
            contract: Qualified IB contract.
            order: ib_insync Order object with action, quantity, type, etc.
        """
        logger.debug(
            "IbClientAdapter.placeOrder: caller_order_id=%d symbol=%s action=%s qty=%s",
            order_id,
            getattr(contract, "symbol", "?"),
            getattr(order, "action", "?"),
            getattr(order, "totalQuantity", "?"),
        )
        self._ib.placeOrder(contract, order)  # type: ignore[arg-type]
