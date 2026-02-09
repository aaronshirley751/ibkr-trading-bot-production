"""
Execution layer test fixtures.

Provides reusable fixtures for execution engine testing:
- Mock strategy objects
- Sample signals
- Sample positions
- Mock risk manager objects

These fixtures integrate with existing broker, strategy, and risk layer fixtures
from tests/conftest.py.
"""

from typing import Any, Dict, List
from unittest.mock import Mock

import pytest

# =============================================================================
# MOCK STRATEGY FIXTURES
# =============================================================================


@pytest.fixture
def mock_strategy() -> Mock:
    """
    Mock strategy object for execution testing.

    Returns:
        Mock with generate_signal and calculate_confidence methods
    """
    strategy = Mock()
    strategy.generate_signal.return_value = {
        "action": "BUY",
        "symbol": "SPY",
        "confidence": 0.85,
        "timestamp": "2026-02-07T09:30:00",
    }
    strategy.calculate_confidence.return_value = 0.75
    return strategy


@pytest.fixture
def mock_strategy_low_confidence() -> Mock:
    """
    Mock strategy that generates low-confidence signals.

    Returns:
        Mock that returns signals below confidence threshold (0.45)
    """
    strategy = Mock()
    strategy.generate_signal.return_value = {
        "action": "BUY",
        "symbol": "SPY",
        "confidence": 0.45,
        "timestamp": "2026-02-07T10:15:00",
    }
    strategy.calculate_confidence.return_value = 0.45
    return strategy


@pytest.fixture
def mock_strategy_high_confidence() -> Mock:
    """
    Mock strategy that generates high-confidence signals.

    Returns:
        Mock that returns signals with confidence >= 0.90
    """
    strategy = Mock()
    strategy.generate_signal.return_value = {
        "action": "BUY",
        "symbol": "QQQ",
        "confidence": 0.95,
        "timestamp": "2026-02-07T11:00:00",
    }
    strategy.calculate_confidence.return_value = 0.95
    return strategy


@pytest.fixture
def mock_strategy_failing() -> Mock:
    """
    Mock strategy that raises exceptions (fail-safe testing).

    Returns:
        Mock that raises RuntimeError when generate_signal is called
    """
    strategy = Mock()
    strategy.generate_signal.side_effect = RuntimeError("Strategy failure")
    return strategy


# =============================================================================
# MOCK RISK MANAGER FIXTURES
# =============================================================================


@pytest.fixture
def mock_risk_manager() -> Mock:
    """
    Mock risk manager for execution testing.

    Returns:
        Mock with check_position_size, calculate_position_size, check_daily_loss_limit
    """
    risk_mgr = Mock()
    risk_mgr.check_position_size.return_value = True
    risk_mgr.calculate_position_size.return_value = 10
    risk_mgr.check_daily_loss_limit.return_value = True
    risk_mgr.check_weekly_drawdown.return_value = True
    return risk_mgr


@pytest.fixture
def mock_risk_manager_rejecting() -> Mock:
    """
    Mock risk manager that rejects all trades.

    Returns:
        Mock that returns False for all risk checks
    """
    risk_mgr = Mock()
    risk_mgr.check_position_size.return_value = False
    risk_mgr.calculate_position_size.return_value = 0
    risk_mgr.check_daily_loss_limit.return_value = False
    return risk_mgr


@pytest.fixture
def mock_risk_manager_unavailable() -> Mock:
    """
    Mock risk manager that is unavailable (returns None).

    Returns:
        Mock that returns None for all methods (simulates unavailable service)
    """
    risk_mgr = Mock()
    risk_mgr.check_position_size.return_value = None
    risk_mgr.calculate_position_size.return_value = None
    risk_mgr.check_daily_loss_limit.return_value = None
    return risk_mgr


# =============================================================================
# MOCK BROKER FIXTURES
# =============================================================================


@pytest.fixture
def mock_broker_for_execution() -> Mock:
    """
    Mock broker for execution testing.

    Returns:
        Mock with submit_order, get_order_status, get_market_data methods
    """
    broker = Mock()
    broker.submit_order.return_value = {"orderId": 12345, "status": "Submitted"}
    broker.get_order_status.return_value = {"status": "Filled", "filled": 10}
    broker.get_market_data.return_value = {"last": 695.50, "bid": 695.45, "ask": 695.55}
    broker.get_contract.return_value = Mock(symbol="SPY")
    return broker


@pytest.fixture
def mock_broker_rejecting() -> Mock:
    """
    Mock broker that rejects orders.

    Returns:
        Mock that returns rejection status
    """
    broker = Mock()
    broker.submit_order.return_value = {
        "orderId": 12345,
        "status": "Rejected",
        "reason": "Insufficient funds",
    }
    return broker


@pytest.fixture
def mock_broker_disconnected() -> Mock:
    """
    Mock broker that simulates connection errors.

    Returns:
        Mock that raises ConnectionError on submit_order
    """
    broker = Mock()
    broker.submit_order.side_effect = ConnectionError("Broker offline")
    return broker


@pytest.fixture
def mock_broker_timeout() -> Mock:
    """
    Mock broker that simulates timeouts.

    Returns:
        Mock that raises TimeoutError on order status checks
    """
    broker = Mock()
    broker.submit_order.return_value = {"orderId": 12345, "status": "Submitted"}
    broker.get_order_status.side_effect = TimeoutError("Order status check timeout")
    return broker


# =============================================================================
# SAMPLE SIGNALS
# =============================================================================


@pytest.fixture
def sample_signal_buy_high_confidence() -> Dict[str, Any]:
    """
    Sample BUY signal with high confidence (0.85).

    Returns:
        Signal dict suitable for ExecutionEngine.process_signal
    """
    return {
        "action": "BUY",
        "symbol": "SPY",
        "confidence": 0.85,
        "timestamp": "2026-02-07T09:30:00",
        "strategy": "A",
        "signal_details": {
            "reason": "Momentum breakout",
            "indicators": {"rsi": 65, "macd": "bullish"},
        },
    }


@pytest.fixture
def sample_signal_sell_high_confidence() -> Dict[str, Any]:
    """
    Sample SELL signal with high confidence (0.80).

    Returns:
        Signal dict for exit/close position
    """
    return {
        "action": "SELL",
        "symbol": "SPY",
        "confidence": 0.80,
        "timestamp": "2026-02-07T14:30:00",
        "strategy": "A",
        "signal_details": {
            "reason": "Target reached",
            "indicators": {"rsi": 72, "macd": "bearish_divergence"},
        },
    }


@pytest.fixture
def sample_signal_low_confidence() -> Dict[str, Any]:
    """
    Sample signal with confidence below threshold (0.45).

    Returns:
        Signal that should be blocked by confidence gate
    """
    return {
        "action": "BUY",
        "symbol": "SPY",
        "confidence": 0.45,
        "timestamp": "2026-02-07T10:15:00",
        "strategy": "B",
        "signal_details": {"reason": "Weak mean reversion signal"},
    }


@pytest.fixture
def sample_signal_boundary_confidence() -> Dict[str, Any]:
    """
    Sample signal with confidence exactly at threshold (0.50).

    Returns:
        Signal at confidence boundary (should be allowed)
    """
    return {
        "action": "BUY",
        "symbol": "QQQ",
        "confidence": 0.50,
        "timestamp": "2026-02-07T11:00:00",
        "strategy": "A",
        "signal_details": {"reason": "Boundary case"},
    }


@pytest.fixture
def sample_signals_multiple() -> List[Dict[str, Any]]:
    """
    Multiple signals for concurrent processing tests.

    Returns:
        List of signals for SPY and QQQ
    """
    return [
        {
            "action": "BUY",
            "symbol": "SPY",
            "confidence": 0.85,
            "timestamp": "2026-02-07T09:30:00",
            "strategy": "A",
        },
        {
            "action": "SELL",
            "symbol": "SPY",
            "confidence": 0.45,
            "timestamp": "2026-02-07T10:15:00",
            "strategy": "B",
        },
        {
            "action": "BUY",
            "symbol": "QQQ",
            "confidence": 0.95,
            "timestamp": "2026-02-07T11:00:00",
            "strategy": "A",
        },
    ]


@pytest.fixture
def sample_signal_invalid() -> Dict[str, Any]:
    """
    Invalid signal missing required fields.

    Returns:
        Signal dict missing 'symbol' field
    """
    return {
        "action": "BUY",
        # Missing 'symbol'
        "confidence": 0.75,
        "timestamp": "2026-02-07T12:00:00",
    }


# =============================================================================
# SAMPLE POSITIONS
# =============================================================================


@pytest.fixture
def sample_position_spy_open() -> Dict[str, Any]:
    """
    Sample open SPY position.

    Returns:
        Position dict with SPY details
    """
    return {
        "symbol": "SPY",
        "quantity": 10,
        "cost_basis": 695.00,
        "entry_time": "2026-02-07T09:35:00",
        "status": "OPEN",
        "order_id": 12345,
    }


@pytest.fixture
def sample_position_qqq_open() -> Dict[str, Any]:
    """
    Sample open QQQ position.

    Returns:
        Position dict with QQQ details
    """
    return {
        "symbol": "QQQ",
        "quantity": 5,
        "cost_basis": 622.00,
        "entry_time": "2026-02-07T10:00:00",
        "status": "OPEN",
        "order_id": 12346,
    }


@pytest.fixture
def sample_positions_multiple() -> List[Dict[str, Any]]:
    """
    Multiple open positions for multi-position tests.

    Returns:
        List of open positions (SPY and QQQ)
    """
    return [
        {
            "symbol": "SPY",
            "quantity": 10,
            "cost_basis": 695.00,
            "entry_time": "2026-02-07T09:35:00",
            "status": "OPEN",
            "order_id": 12345,
        },
        {
            "symbol": "QQQ",
            "quantity": 5,
            "cost_basis": 622.00,
            "entry_time": "2026-02-07T10:00:00",
            "status": "OPEN",
            "order_id": 12346,
        },
    ]


@pytest.fixture
def sample_position_partial_fill() -> Dict[str, Any]:
    """
    Position from partially filled order.

    Returns:
        Position dict with partial quantity (5 of 10 contracts)
    """
    return {
        "symbol": "SPY",
        "quantity": 5,  # Partial fill
        "cost_basis": 695.00,
        "entry_time": "2026-02-07T09:35:00",
        "status": "PARTIAL",
        "order_id": 12345,
        "requested_quantity": 10,
        "filled_quantity": 5,
    }


@pytest.fixture
def sample_position_invalid() -> Dict[str, Any]:
    """
    Invalid position with data corruption (negative quantity).

    Returns:
        Position dict with invalid data
    """
    return {
        "symbol": "SPY",
        "quantity": -10,  # Invalid negative quantity
        "cost_basis": 695.00,
        "entry_time": "2026-02-07T09:35:00",
        "status": "OPEN",
        "order_id": 12345,
    }


# =============================================================================
# SAMPLE ORDERS
# =============================================================================


@pytest.fixture
def sample_order_buy() -> Dict[str, Any]:
    """
    Sample BUY order for testing.

    Returns:
        Order dict with BUY parameters
    """
    return {
        "symbol": "SPY",
        "action": "BUY",
        "quantity": 10,
        "order_type": "MKT",
        "time_in_force": "DAY",
    }


@pytest.fixture
def sample_order_sell() -> Dict[str, Any]:
    """
    Sample SELL order for testing.

    Returns:
        Order dict with SELL parameters
    """
    return {
        "symbol": "SPY",
        "action": "SELL",
        "quantity": 10,
        "order_type": "MKT",
        "time_in_force": "DAY",
    }
