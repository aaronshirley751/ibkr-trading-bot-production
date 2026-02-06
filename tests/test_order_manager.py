from __future__ import annotations

from dataclasses import dataclass

import pytest
from ib_insync import Order
from pydantic import ValidationError

from src.bot.execution.order_manager import ContractLike, IBClientLike, OrderManager, OrderParams
from src.bot.config.settings import Settings


@dataclass
class DummyContract:
    symbol: str = "ES"


class DummyIBClient(IBClientLike):
    def __init__(self) -> None:
        self.last_order_id: int | None = None
        self.last_order: Order | None = None
        self.last_contract: ContractLike | None = None

    def placeOrder(self, order_id: int, contract: ContractLike, order: Order) -> None:
        self.last_order_id = order_id
        self.last_contract = contract
        self.last_order = order


def test_submit_order_sets_operator_id() -> None:
    ib_client = DummyIBClient()
    settings = Settings(OPERATOR_ID="CSATSPRIM")
    manager = OrderManager(ib_client, settings)

    order_id = manager.submit_order(
        DummyContract(),
        OrderParams(action="BUY", quantity=1, order_type="MKT"),
    )

    assert order_id == 1
    assert ib_client.last_order is not None
    assert getattr(ib_client.last_order, "operatorId") == "CSATSPRIM"


def test_settings_rejects_empty_operator_id() -> None:
    with pytest.raises(ValidationError):
        Settings(OPERATOR_ID="")
