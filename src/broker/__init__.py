"""
Broker integration layer for IBKR Gateway.

This module provides production-ready interfaces for:
- Connection management with retry logic
- Market data retrieval with snapshot enforcement
- Contract qualification and management

CRITICAL ALPHA LEARNINGS ENFORCED:
1. snapshot=True REQUIRED on all market data requests (buffer overflow fix)
2. Contract qualification REQUIRED before data requests
3. Timeout propagation enforced through entire call stack
4. Historical data: 1-hour RTH-only windows mandatory
5. ClientId: Timestamp-based for uniqueness

Usage Example:
    >>> from src.broker import IBKRConnection, MarketDataProvider, ContractManager
    >>>
    >>> # Connect to Gateway
    >>> connection = IBKRConnection(host="localhost", port=4002)
    >>> connection.connect()
    >>>
    >>> # Set up contract and data providers
    >>> contract_mgr = ContractManager(connection)
    >>> data_provider = MarketDataProvider(connection, contract_mgr)
    >>>
    >>> # Qualify contract and request data
    >>> contract = contract_mgr.qualify_contract("SPY")
    >>> data = data_provider.request_market_data(contract)
    >>> print(data)
    >>>
    >>> # Clean up
    >>> connection.disconnect()

See docs/alpha_learnings.md for details on critical production requirements.
"""

from .connection import IBKRConnection
from .contracts import ContractManager
from .market_data import MarketDataProvider
from .exceptions import (
    BrokerError,
    ConnectionError,
    ConnectionTimeoutError,
    MaxRetriesExceededError,
    MarketDataError,
    ContractNotQualifiedError,
    StaleDataError,
    SnapshotModeViolationError,
    ContractQualificationError,
)

__all__ = [
    # Core classes
    "IBKRConnection",
    "ContractManager",
    "MarketDataProvider",
    # Exceptions
    "BrokerError",
    "ConnectionError",
    "ConnectionTimeoutError",
    "MaxRetriesExceededError",
    "MarketDataError",
    "ContractNotQualifiedError",
    "StaleDataError",
    "SnapshotModeViolationError",
    "ContractQualificationError",
]

__version__ = "0.1.0"
