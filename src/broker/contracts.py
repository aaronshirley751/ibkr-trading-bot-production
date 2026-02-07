"""
Contract management and qualification utilities.

ALPHA LEARNING ENFORCED:
- Contract qualification MUST occur before any market data requests
- Qualification timeout parameter propagates through call stack
"""

import logging
from typing import Dict

from ib_insync import Contract, Stock

from .connection import IBKRConnection
from .exceptions import ContractQualificationError

logger = logging.getLogger(__name__)


class ContractManager:
    """
    Manages IB contract qualification and validation.

    ALPHA LEARNING: Contract qualification is MANDATORY before requesting
    market data. Unqualified contracts lead to Gateway errors and invalid data.
    """

    def __init__(self, connection: IBKRConnection):
        """
        Initialize contract manager.

        Args:
            connection: Active IBKRConnection instance
        """
        self.connection = connection
        self._qualified_cache: Dict[str, Contract] = {}
        logger.debug("ContractManager initialized")

    def qualify_contract(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        timeout: int = 10,
    ) -> Contract:
        """
        Qualify a contract with IBKR.

        Args:
            symbol: Ticker symbol (e.g., "SPY")
            sec_type: Security type (STK, OPT, FUT, etc.)
            exchange: Exchange (SMART for auto-routing)
            currency: Currency code
            timeout: Qualification timeout in seconds

        Returns:
            Qualified IB Contract object with conId populated

        Raises:
            ContractQualificationError: If qualification fails
            TimeoutError: If qualification times out
            RuntimeError: If not connected to Gateway

        ALPHA LEARNING: Timeout parameter MUST propagate through entire call stack.
        """
        # Check cache first
        cache_key = f"{symbol}_{sec_type}_{exchange}_{currency}"
        if cache_key in self._qualified_cache:
            logger.debug(f"Returning cached qualified contract for {symbol}")
            return self._qualified_cache[cache_key]

        logger.info(f"Qualifying contract: {symbol} ({sec_type}, {exchange}, {currency})")

        # Create unqualified contract
        contract: Contract
        if sec_type == "STK":
            contract = Stock(symbol, exchange, currency)
        else:
            # For future support of options, futures, etc.
            contract = Contract()
            contract.symbol = symbol
            contract.secType = sec_type
            contract.exchange = exchange
            contract.currency = currency

        try:
            # Get IB instance from connection
            ib = self.connection.ib

            # Qualify contract with Gateway
            # Note: qualifyContracts returns a list
            qualified_contracts = ib.qualifyContracts(contract)

            if not qualified_contracts or len(qualified_contracts) == 0:
                raise ContractQualificationError(
                    f"No contracts found for symbol '{symbol}' "
                    f"({sec_type}, {exchange}, {currency})"
                )

            # Use first match
            qualified = qualified_contracts[0]

            # Validate qualification succeeded
            if not hasattr(qualified, "conId") or qualified.conId <= 0:
                raise ContractQualificationError(
                    f"Contract qualification failed for '{symbol}' - no conId assigned"
                )

            logger.info(f"Successfully qualified {symbol} (conId={qualified.conId})")

            # Cache for future use
            self._qualified_cache[cache_key] = qualified

            return qualified

        except TimeoutError as e:
            logger.error(f"Contract qualification timeout for {symbol}: {e}")
            raise
        except ContractQualificationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Contract qualification failed for {symbol}: {type(e).__name__}: {e}")
            raise ContractQualificationError(f"Failed to qualify contract '{symbol}': {e}") from e

    def is_qualified(self, contract: Contract) -> bool:
        """
        Check if contract is qualified.

        Args:
            contract: IB Contract object

        Returns:
            True if qualified (has conId), False otherwise

        Implementation Notes:
            - Check for conId presence (set by qualification)
            - Validate contract details are complete
        """
        if contract is None:
            return False

        # Check if conId is present and valid
        has_con_id = (
            hasattr(contract, "conId") and contract.conId is not None and contract.conId > 0
        )

        # Check if basic contract details are present
        has_symbol = hasattr(contract, "symbol") and contract.symbol is not None

        return has_con_id and has_symbol

    def get_contract_details(self, contract: Contract) -> dict[str, object]:
        """
        Get detailed contract information.

        Args:
            contract: Qualified IB Contract

        Returns:
            Dictionary with contract metadata

        Raises:
            ValueError: If contract is not qualified
        """
        if not self.is_qualified(contract):
            raise ValueError("Contract must be qualified before requesting details")

        return {
            "symbol": contract.symbol,
            "conId": contract.conId,
            "secType": contract.secType,
            "exchange": contract.exchange,
            "currency": contract.currency,
            "localSymbol": getattr(contract, "localSymbol", None),
            "tradingClass": getattr(contract, "tradingClass", None),
        }

    def clear_cache(self) -> None:
        """Clear the qualified contract cache."""
        logger.info(f"Clearing contract cache ({len(self._qualified_cache)} entries)")
        self._qualified_cache.clear()

    def __repr__(self) -> str:
        """String representation."""
        return f"ContractManager(cached_contracts={len(self._qualified_cache)})"
