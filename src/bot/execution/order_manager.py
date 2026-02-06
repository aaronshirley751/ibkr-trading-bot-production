from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ib_insync import Order

from src.bot.config.settings import Settings


class ContractLike(Protocol):
    symbol: str


class IBClientLike(Protocol):
    def placeOrder(self, order_id: int, contract: ContractLike, order: Order) -> None: ...


@dataclass
class OrderParams:
    action: str
    quantity: float
    order_type: str


class OrderManager:
    def __init__(self, ib_client: IBClientLike, settings: Settings | None = None) -> None:
        self._ib_client = ib_client
        self._settings = settings or Settings()
        self._logger = logging.getLogger(__name__)
        self._next_order_id = 1

    def next_order_id(self) -> int:
        order_id = self._next_order_id
        self._next_order_id += 1
        return order_id

    def submit_order(self, contract: ContractLike, params: OrderParams) -> int:
        order = Order()
        order.action = params.action
        order.totalQuantity = params.quantity
        order.orderType = params.order_type
        operator_id = self._settings.OPERATOR_ID
        setattr(order, "operatorId", operator_id)

        self._logger.info(
            "Submitting order with operator ID: %s",
            operator_id,
            extra={
                "operator_id": operator_id,
                "symbol": contract.symbol,
                "action": order.action,
                "quantity": order.totalQuantity,
            },
        )

        order_id = self.next_order_id()
        self._ib_client.placeOrder(order_id, contract, order)
        return order_id
