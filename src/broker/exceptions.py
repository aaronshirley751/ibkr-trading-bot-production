"""
Custom exception classes for broker layer.

These exceptions provide clear error handling for broker operations
and enforce alpha learnings through runtime validation.
"""


class BrokerError(Exception):
    """Base exception for broker layer errors."""

    pass


class ConnectionError(BrokerError):
    """Connection-related errors."""

    pass


class ConnectionTimeoutError(ConnectionError):
    """Connection attempt timed out."""

    pass


class MaxRetriesExceededError(ConnectionError):
    """Maximum retry attempts exceeded."""

    pass


class MarketDataError(BrokerError):
    """Market data request errors."""

    pass


class ContractNotQualifiedError(MarketDataError):
    """
    Contract must be qualified before data request.

    ALPHA LEARNING: Contract qualification MUST occur before any market data
    requests to avoid invalid symbol errors and Gateway rejections.
    """

    pass


class StaleDataError(MarketDataError):
    """
    Market data timestamp exceeds staleness threshold.

    Data older than 5 minutes triggers Strategy C (no market data).
    """

    pass


class SnapshotModeViolationError(MarketDataError):
    """
    CRITICAL: Attempt to use non-snapshot mode (forbidden).

    ALPHA LEARNING: snapshot=False caused buffer overflow in production
    (2024-01-15 incident). snapshot=True is MANDATORY for all market data requests.
    See docs/alpha_learnings.md for details.
    """

    pass


class ContractQualificationError(BrokerError):
    """Contract qualification failed."""

    pass
