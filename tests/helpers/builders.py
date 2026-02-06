"""Test data builders for trading domain objects.

Provides fluent, chainable interfaces for constructing realistic test data
with sensible defaults and domain constraint enforcement.

Example usage:
    contract = ContractBuilder().spy().call().strike(580).expiry("2026-02-14").build()
    order = OrderBuilder().buy().quantity(1).limit_price(5.25).build()
    position = PositionBuilder().spy().quantity(100).avg_cost(580.50).build()
"""

from datetime import datetime, timedelta
from typing import Any, Dict


class ContractBuilder:
    """Builder for IBKR Contract objects with realistic defaults.

    Supports options, stocks, and futures with domain-aware defaults
    for strikes, expiries, and contract specifications.
    """

    def __init__(self) -> None:
        self._symbol = "SPY"
        self._sec_type = "OPT"
        self._currency = "USD"
        self._exchange = "SMART"
        self._primary_exchange = ""
        self._right = "C"  # Call
        self._strike = 580.0
        self._expiry = ""
        self._multiplier = "100"
        self._local_symbol = ""
        self._trading_class = ""

    def spy(self) -> "ContractBuilder":
        """Set symbol to SPY with appropriate defaults."""
        self._symbol = "SPY"
        self._strike = 580.0
        return self

    def qqq(self) -> "ContractBuilder":
        """Set symbol to QQQ with appropriate defaults."""
        self._symbol = "QQQ"
        self._strike = 500.0
        return self

    def iwm(self) -> "ContractBuilder":
        """Set symbol to IWM with appropriate defaults."""
        self._symbol = "IWM"
        self._strike = 220.0
        return self

    def stock(self) -> "ContractBuilder":
        """Set security type to stock (STK)."""
        self._sec_type = "STK"
        self._strike = 0.0
        self._expiry = ""
        self._right = ""
        self._multiplier = "1"
        return self

    def option(self) -> "ContractBuilder":
        """Set security type to option (OPT)."""
        self._sec_type = "OPT"
        self._multiplier = "100"
        return self

    def call(self) -> "ContractBuilder":
        """Set option right to Call."""
        self._right = "C"
        return self

    def put(self) -> "ContractBuilder":
        """Set option right to Put."""
        self._right = "P"
        return self

    def strike(self, price: float) -> "ContractBuilder":
        """Set strike price."""
        self._strike = price
        return self

    def expiry(self, date_str: str) -> "ContractBuilder":
        """Set expiry date in YYYYMMDD format.

        Args:
            date_str: Expiry date as "YYYY-MM-DD" or "YYYYMMDD"
        """
        # Convert YYYY-MM-DD to YYYYMMDD if needed
        if "-" in date_str:
            date_str = date_str.replace("-", "")
        self._expiry = date_str
        return self

    def dte(self, days: int) -> "ContractBuilder":
        """Set expiry to N days from today.

        Args:
            days: Days until expiry (e.g., 2 for 2DTE)
        """
        expiry_date = datetime.now() + timedelta(days=days)
        self._expiry = expiry_date.strftime("%Y%m%d")
        return self

    def exchange(self, exch: str) -> "ContractBuilder":
        """Set exchange."""
        self._exchange = exch
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the contract dictionary.

        Returns:
            Dictionary representation of IBKR Contract
        """
        contract: Dict[str, Any] = {
            "symbol": self._symbol,
            "secType": self._sec_type,
            "currency": self._currency,
            "exchange": self._exchange,
        }

        if self._sec_type == "OPT":
            contract.update(
                {
                    "right": self._right,
                    "strike": self._strike,
                    "lastTradeDateOrContractMonth": self._expiry,
                    "multiplier": self._multiplier,
                }
            )

        return contract


class OrderBuilder:
    """Builder for IBKR Order objects with realistic defaults."""

    def __init__(self) -> None:
        self._action = "BUY"
        self._order_type = "LMT"
        self._total_quantity = 1
        self._lmt_price = 0.0
        self._aux_price = 0.0
        self._tif = "DAY"
        self._account = "DU123456"
        self._order_id = 0
        self._perm_id = 0
        self._client_id = 0

    def buy(self) -> "OrderBuilder":
        """Set action to BUY."""
        self._action = "BUY"
        return self

    def sell(self) -> "OrderBuilder":
        """Set action to SELL."""
        self._action = "SELL"
        return self

    def quantity(self, qty: int) -> "OrderBuilder":
        """Set order quantity."""
        self._total_quantity = qty
        return self

    def limit_price(self, price: float) -> "OrderBuilder":
        """Set limit price and order type to LMT."""
        self._order_type = "LMT"
        self._lmt_price = price
        return self

    def market(self) -> "OrderBuilder":
        """Set order type to market (MKT)."""
        self._order_type = "MKT"
        self._lmt_price = 0.0
        return self

    def stop(self, stop_price: float) -> "OrderBuilder":
        """Set order type to stop (STP)."""
        self._order_type = "STP"
        self._aux_price = stop_price
        return self

    def order_id(self, oid: int) -> "OrderBuilder":
        """Set order ID."""
        self._order_id = oid
        return self

    def account(self, acct: str) -> "OrderBuilder":
        """Set account identifier."""
        self._account = acct
        return self

    def tif(self, time_in_force: str) -> "OrderBuilder":
        """Set time in force (DAY, GTC, IOC, etc.)."""
        self._tif = time_in_force
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the order dictionary.

        Returns:
            Dictionary representation of IBKR Order
        """
        order = {
            "action": self._action,
            "orderType": self._order_type,
            "totalQuantity": self._total_quantity,
            "account": self._account,
            "tif": self._tif,
            "orderId": self._order_id,
            "permId": self._perm_id,
            "clientId": self._client_id,
        }

        if self._order_type == "LMT":
            order["lmtPrice"] = self._lmt_price

        if self._order_type == "STP":
            order["auxPrice"] = self._aux_price

        return order


class PositionBuilder:
    """Builder for position tracking objects."""

    def __init__(self) -> None:
        self._symbol = "SPY"
        self._quantity = 100
        self._avg_cost = 0.0
        self._realized_pnl = 0.0
        self._unrealized_pnl = 0.0
        self._market_value = 0.0

    def symbol(self, sym: str) -> "PositionBuilder":
        """Set position symbol."""
        self._symbol = sym
        return self

    def spy(self) -> "PositionBuilder":
        """Set symbol to SPY with default strike."""
        self._symbol = "SPY"
        return self

    def qqq(self) -> "PositionBuilder":
        """Set symbol to QQQ with default strike."""
        self._symbol = "QQQ"
        return self

    def quantity(self, qty: int) -> "PositionBuilder":
        """Set position quantity (positive=long, negative=short)."""
        self._quantity = qty
        return self

    def avg_cost(self, cost: float) -> "PositionBuilder":
        """Set average cost per share/contract."""
        self._avg_cost = cost
        return self

    def realized_pnl(self, pnl: float) -> "PositionBuilder":
        """Set realized P&L."""
        self._realized_pnl = pnl
        return self

    def unrealized_pnl(self, pnl: float) -> "PositionBuilder":
        """Set unrealized P&L."""
        self._unrealized_pnl = pnl
        return self

    def market_value(self, value: float) -> "PositionBuilder":
        """Set current market value."""
        self._market_value = value
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the position dictionary.

        Returns:
            Dictionary representation of position
        """
        return {
            "symbol": self._symbol,
            "quantity": self._quantity,
            "avgCost": self._avg_cost,
            "realizedPNL": self._realized_pnl,
            "unrealizedPNL": self._unrealized_pnl,
            "marketValue": self._market_value,
        }


class FillBuilder:
    """Builder for order fill/execution objects."""

    def __init__(self) -> None:
        self._order_id = 0
        self._exec_id = ""
        self._time = datetime.now().isoformat()
        self._account = "DU123456"
        self._exchange = "SMART"
        self._side = "BOT"  # BOT or SLD
        self._shares = 1
        self._price = 0.0
        self._perm_id = 0
        self._client_id = 0
        self._liquidation = 0
        self._cum_qty = 1
        self._avg_price = 0.0

    def order_id(self, oid: int) -> "FillBuilder":
        """Set order ID."""
        self._order_id = oid
        return self

    def exec_id(self, eid: str) -> "FillBuilder":
        """Set execution ID."""
        self._exec_id = eid
        return self

    def buy(self) -> "FillBuilder":
        """Set side to bought (BOT)."""
        self._side = "BOT"
        return self

    def sell(self) -> "FillBuilder":
        """Set side to sold (SLD)."""
        self._side = "SLD"
        return self

    def quantity(self, qty: int) -> "FillBuilder":
        """Set fill quantity."""
        self._shares = qty
        self._cum_qty = qty
        return self

    def price(self, px: float) -> "FillBuilder":
        """Set fill price."""
        self._price = px
        self._avg_price = px
        return self

    def timestamp(self, ts: str) -> "FillBuilder":
        """Set execution timestamp (ISO format)."""
        self._time = ts
        return self

    def account(self, acct: str) -> "FillBuilder":
        """Set account identifier."""
        self._account = acct
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the fill dictionary.

        Returns:
            Dictionary representation of execution/fill
        """
        return {
            "orderId": self._order_id,
            "execId": self._exec_id,
            "time": self._time,
            "account": self._account,
            "exchange": self._exchange,
            "side": self._side,
            "shares": self._shares,
            "price": self._price,
            "permId": self._perm_id,
            "clientId": self._client_id,
            "liquidation": self._liquidation,
            "cumQty": self._cum_qty,
            "avgPrice": self._avg_price,
        }
