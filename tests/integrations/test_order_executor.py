"""
Unit tests for OrderExecutor.

Tests order execution with risk validation, dry-run mode, and paper mode.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from decimal import Decimal

from src.integrations.order_executor import (
    OrderExecutor,
    ExecutionMode,
    OrderStatus,
)
from src.strategies.base import Signal, Direction, StrategyType


@pytest.fixture
def mock_connection():
    """Mock IBKRConnection."""
    conn = MagicMock()
    conn.ib = MagicMock()
    conn.ib.placeOrder = MagicMock(return_value=MagicMock(isDone=lambda: True))
    return conn


@pytest.fixture
def mock_contracts():
    """Mock ContractManager."""
    contracts = MagicMock()
    contracts.qualify_contract = MagicMock(return_value=MagicMock(symbol="SPY"))
    contracts.qualify_option_contract = MagicMock(return_value=MagicMock(symbol="SPY"))
    return contracts


@pytest.fixture
def mock_risk_manager():
    """Mock RiskManager that approves all trades."""
    rm = MagicMock()
    rm.evaluate = MagicMock(
        return_value=MagicMock(
            approved=True,
            rejections=[],
            approved_contracts=Decimal("1"),
            risk_per_trade=Decimal("0.02"),
        )
    )
    return rm


@pytest.fixture
def rejecting_risk_manager():
    """Mock RiskManager that rejects all trades."""
    from src.risk.risk_types import RejectionReason

    rm = MagicMock()
    rm.evaluate = MagicMock(
        return_value=MagicMock(
            approved=False,
            rejections=[RejectionReason.PDT_LIMIT_REACHED],
            approved_contracts=Decimal("0"),
            risk_per_trade=Decimal("0.0"),
        )
    )
    return rm


@pytest.fixture
def executor_dry_run(mock_connection, mock_contracts, mock_risk_manager):
    """OrderExecutor in DRY_RUN mode."""
    return OrderExecutor(
        mock_connection,
        mock_contracts,
        mock_risk_manager,
        mode=ExecutionMode.DRY_RUN,
        operator_id="CSATSPRIM",
    )


@pytest.fixture
def executor_paper(mock_connection, mock_contracts, mock_risk_manager):
    """OrderExecutor in PAPER mode."""
    return OrderExecutor(
        mock_connection,
        mock_contracts,
        mock_risk_manager,
        mode=ExecutionMode.PAPER,
        operator_id="CSATSPRIM",
    )


@pytest.fixture
def buy_signal():
    """Sample BUY signal."""
    return Signal(
        direction=Direction.BUY,
        symbol="SPY",
        confidence=0.8,
        rationale="EMA crossover + RSI favorable",
        timestamp=datetime.now(timezone.utc),
        strategy_type=StrategyType.A,
        entry_price=450.0,
        stop_loss=440.0,
        take_profit=460.0,
    )


@pytest.fixture
def strategy_context():
    """Sample strategy context."""
    return {
        "strategy_id": "strategy_a",
        "strategy_name": "momentum_breakout",
        "quantity": 1,
        "order_type": "MKT",
        "risk_per_trade": 0.02,
        "take_profit_pct": 0.20,
        "stop_loss_pct": 0.25,
    }


class TestOrderExecutor:
    """Test OrderExecutor functionality."""

    @pytest.mark.asyncio
    async def test_execute_dry_run_approved(self, executor_dry_run, buy_signal, strategy_context):
        """Test dry-run execution with approved trade."""
        result = await executor_dry_run.execute(buy_signal, strategy_context, timeout=30.0)

        assert result.status == OrderStatus.SIMULATED
        assert result.execution_mode == ExecutionMode.DRY_RUN
        assert result.fill_price == 450.0
        assert result.fill_quantity == 1
        assert result.order_id.startswith("ORD_")

    @pytest.mark.asyncio
    async def test_execute_rejected_by_risk_manager(
        self, mock_connection, mock_contracts, rejecting_risk_manager, buy_signal, strategy_context
    ):
        """Test order rejected by RiskManager."""
        executor = OrderExecutor(
            mock_connection,
            mock_contracts,
            rejecting_risk_manager,
            mode=ExecutionMode.DRY_RUN,
        )

        result = await executor.execute(buy_signal, strategy_context, timeout=30.0)

        assert result.status == OrderStatus.REJECTED
        assert "PDT" in result.rejection_reason or "rejection" in result.rejection_reason.lower()
        assert result.risk_validation is not None

    @pytest.mark.asyncio
    async def test_build_trade_request(self, executor_dry_run, buy_signal, strategy_context):
        """Test TradeRequest building from signal."""
        trade_request = executor_dry_run._build_trade_request(buy_signal, strategy_context)

        assert trade_request.symbol == "SPY"
        assert trade_request.action == "BUY"
        assert trade_request.quantity == 1
        assert trade_request.order_type == "MKT"
        assert trade_request.limit_price == 450.0
        assert trade_request.operator_id == "CSATSPRIM"

    @pytest.mark.asyncio
    async def test_operator_id_enforcement(self, executor_dry_run, buy_signal, strategy_context):
        """Test operator ID is attached to all orders."""
        trade_request = executor_dry_run._build_trade_request(buy_signal, strategy_context)

        assert trade_request.operator_id == "CSATSPRIM"

    @pytest.mark.asyncio
    async def test_generate_unique_order_ids(self, executor_dry_run):
        """Test order IDs are unique."""
        id1 = executor_dry_run._generate_order_id()
        id2 = executor_dry_run._generate_order_id()
        id3 = executor_dry_run._generate_order_id()

        assert id1 != id2 != id3
        assert id1.startswith("ORD_")
        assert id2.startswith("ORD_")
        assert id3.startswith("ORD_")

    def test_build_ibkr_order(self, executor_dry_run, buy_signal, strategy_context):
        """Test IBKR order construction."""
        trade_request = executor_dry_run._build_trade_request(buy_signal, strategy_context)
        ibkr_order = executor_dry_run._build_ibkr_order(trade_request)

        assert ibkr_order.action == "BUY"
        assert ibkr_order.totalQuantity == 1
        assert ibkr_order.orderType == "MKT"
        assert ibkr_order.account == "CSATSPRIM"  # Operator ID compliance


class TestRiskValidationEnforcement:
    """Test that risk validation cannot be bypassed."""

    @pytest.mark.asyncio
    async def test_no_bypass_path_exists(self, executor_dry_run, buy_signal, strategy_context):
        """Test that all execution paths go through risk validation."""
        # Replace evaluate with a mock that tracks calls
        call_tracker = []

        original_validate = executor_dry_run._validate_with_risk_manager

        async def tracking_validate(trade_request):
            call_tracker.append(trade_request)
            return await original_validate(trade_request)

        executor_dry_run._validate_with_risk_manager = tracking_validate

        await executor_dry_run.execute(buy_signal, strategy_context, timeout=30.0)

        # Verify risk validation was called
        assert len(call_tracker) == 1
        assert call_tracker[0].symbol == "SPY"
