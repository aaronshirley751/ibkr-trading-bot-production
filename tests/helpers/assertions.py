"""Custom assertion helpers for trading bot tests."""

from typing import Dict, Optional


def assert_price_within_tolerance(
    actual: float,
    expected: float,
    tolerance: float = 0.01,
    msg: Optional[str] = None,
) -> None:
    """Assert that actual price is within tolerance of expected price.

    Args:
        actual: The actual price value
        expected: The expected price value
        tolerance: Acceptable difference (default 1 cent)
        msg: Optional custom error message

    Raises:
        AssertionError: If prices differ by more than tolerance
    """
    diff = abs(actual - expected)
    if diff > tolerance:
        error_msg = (
            f"Price {actual} not within tolerance {tolerance} of expected {expected}. "
            f"Difference: {diff}"
        )
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)


def assert_position_exists(
    portfolio: Dict[str, int],
    symbol: str,
    expected_quantity: int,
    msg: Optional[str] = None,
) -> None:
    """Assert that a position exists with the expected quantity.

    Args:
        portfolio: Dictionary mapping symbols to quantities
        symbol: The symbol to check
        expected_quantity: The expected position quantity
        msg: Optional custom error message

    Raises:
        AssertionError: If position doesn't exist or quantity doesn't match
    """
    if symbol not in portfolio:
        error_msg = f"Position for {symbol} not found in portfolio. Portfolio: {portfolio}"
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)

    actual_quantity = portfolio[symbol]
    if actual_quantity != expected_quantity:
        error_msg = (
            f"Position quantity for {symbol} is {actual_quantity}, " f"expected {expected_quantity}"
        )
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)


def assert_no_position(portfolio: Dict[str, int], symbol: str, msg: Optional[str] = None) -> None:
    """Assert that no position exists for the given symbol.

    Args:
        portfolio: Dictionary mapping symbols to quantities
        symbol: The symbol to check
        msg: Optional custom error message

    Raises:
        AssertionError: If position exists for the symbol
    """
    if symbol in portfolio and portfolio[symbol] != 0:
        error_msg = (
            f"Unexpected position for {symbol}: {portfolio[symbol]} shares. "
            f"Expected no position."
        )
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)
