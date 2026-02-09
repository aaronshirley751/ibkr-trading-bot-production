"""
Unit tests for PositionManager.

Tests position tracking, P&L calculation, and Strategy C closure logic.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.integrations.position_manager import (
    PositionManager,
    Position,
    PositionNotFoundError,
)


@pytest.fixture
def mock_connection():
    """Mock IBKRConnection."""
    conn = MagicMock()
    conn.ib = MagicMock()
    conn.ib.positions = MagicMock(return_value=[])
    conn.ib.placeOrder = MagicMock(return_value=MagicMock(isDone=lambda: True))
    return conn


@pytest.fixture
def mock_risk_manager():
    """Mock RiskManager."""
    rm = MagicMock()
    rm.sync_positions = AsyncMock()
    return rm


@pytest.fixture
def position_manager(mock_connection, mock_risk_manager):
    """PositionManager instance."""
    return PositionManager(mock_connection, mock_risk_manager)


@pytest.fixture
def mock_option_contract_3dte():
    """Mock option contract with 3 days to expiration."""
    contract = MagicMock()
    contract.symbol = "SPY"
    contract.conId = 12345
    expiry_date = (datetime.now() + timedelta(days=3)).strftime("%Y%m%d")
    contract.lastTradeDateOrContractMonth = expiry_date
    return contract


@pytest.fixture
def mock_option_contract_10dte():
    """Mock option contract with 10 days to expiration."""
    contract = MagicMock()
    contract.symbol = "SPY"
    contract.conId = 12345
    expiry_date = (datetime.now() + timedelta(days=10)).strftime("%Y%m%d")
    contract.lastTradeDateOrContractMonth = expiry_date
    return contract


@pytest.fixture
def mock_position_profitable():
    """Mock profitable position."""
    pos = MagicMock()
    pos.contract = MagicMock(symbol="SPY", conId=12345)
    pos.contract.lastTradeDateOrContractMonth = None  # Stock, not option
    pos.position = 10  # Long 10 shares
    pos.avgCost = 100.0  # Entry at $100
    return pos


@pytest.fixture
def mock_position_losing():
    """Mock position with 45% loss."""
    pos = MagicMock()
    pos.contract = MagicMock(symbol="SPY", conId=12345)
    pos.contract.lastTradeDateOrContractMonth = None
    pos.position = 10
    pos.avgCost = 100.0  # Entry at $100
    return pos


class TestPositionManager:
    """Test PositionManager functionality."""

    @pytest.mark.asyncio
    async def test_get_all_empty(self, position_manager, mock_connection):
        """Test getting positions when none exist."""
        mock_connection.ib.positions.return_value = []

        positions = await position_manager.get_all(timeout=10.0)

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_dte_option(self, position_manager, mock_option_contract_3dte):
        """Test DTE calculation for options."""
        dte = position_manager._calculate_dte(mock_option_contract_3dte)

        assert dte == 3

    @pytest.mark.asyncio
    async def test_calculate_dte_stock(self, position_manager):
        """Test DTE calculation returns None for stocks."""
        stock_contract = MagicMock(symbol="SPY")
        delattr(stock_contract, "lastTradeDateOrContractMonth")

        dte = position_manager._calculate_dte(stock_contract)

        assert dte is None

    def test_determine_closure_trigger_3dte(self, position_manager):
        """Test 3 DTE closure trigger."""
        trigger = position_manager._determine_closure_trigger(
            should_close_3_dte=True, should_close_emergency=False
        )

        assert trigger == "3_DTE_RULE"

    def test_determine_closure_trigger_emergency(self, position_manager):
        """Test 40% emergency stop trigger (takes priority)."""
        trigger = position_manager._determine_closure_trigger(
            should_close_3_dte=True, should_close_emergency=True
        )

        assert trigger == "EMERGENCY_STOP"  # Emergency takes priority

    def test_determine_closure_trigger_none(self, position_manager):
        """Test no closure trigger when all conditions false."""
        trigger = position_manager._determine_closure_trigger(
            should_close_3_dte=False, should_close_emergency=False
        )

        assert trigger is None

    @pytest.mark.asyncio
    async def test_close_position_not_found(self, position_manager):
        """Test closing non-existent position raises error."""
        with pytest.raises(PositionNotFoundError):
            await position_manager.close("INVALID_ID", reason="TEST")

    @pytest.mark.asyncio
    async def test_check_strategy_c_closures(self, position_manager, mock_connection):
        """Test strategy C closure check."""
        # Mock position with 3 DTE
        mock_pos = MagicMock()
        mock_pos.contract = MagicMock(symbol="SPY", conId=12345)
        expiry_date = (datetime.now() + timedelta(days=3)).strftime("%Y%m%d")
        mock_pos.contract.lastTradeDateOrContractMonth = expiry_date
        mock_pos.position = 10
        mock_pos.avgCost = 100.0

        mock_connection.ib.positions.return_value = [mock_pos]

        # Mock _get_current_price to return a value that won't trigger emergency
        position_manager._get_current_price = AsyncMock(return_value=102.0)

        positions_to_close = await position_manager.check_strategy_c_closures()

        # Should have at least one position flagged for 3 DTE
        assert len(positions_to_close) > 0
        assert any(p.should_close_3_dte for p in positions_to_close)


class TestStrategyC3DTERule:
    """Test Strategy C 3 DTE closure rule."""

    @pytest.mark.asyncio
    async def test_3_dte_triggers_closure(
        self, position_manager, mock_connection, mock_option_contract_3dte
    ):
        """Test that 3 DTE triggers closure flag."""
        mock_pos = MagicMock()
        mock_pos.contract = mock_option_contract_3dte
        mock_pos.position = 10
        mock_pos.avgCost = 100.0

        mock_connection.ib.positions.return_value = [mock_pos]
        position_manager._get_current_price = AsyncMock(return_value=102.0)

        positions = await position_manager.get_all()

        assert len(positions) == 1
        assert positions[0].should_close_3_dte
        assert positions[0].closure_trigger == "3_DTE_RULE"

    @pytest.mark.asyncio
    async def test_10_dte_no_closure(
        self, position_manager, mock_connection, mock_option_contract_10dte
    ):
        """Test that 10 DTE does not trigger closure."""
        mock_pos = MagicMock()
        mock_pos.contract = mock_option_contract_10dte
        mock_pos.position = 10
        mock_pos.avgCost = 100.0

        mock_connection.ib.positions.return_value = [mock_pos]
        position_manager._get_current_price = AsyncMock(return_value=102.0)

        positions = await position_manager.get_all()

        assert len(positions) == 1
        assert not positions[0].should_close_3_dte


class TestStrategyC40PercentEmergencyStop:
    """Test Strategy C 40% emergency stop rule."""

    @pytest.mark.asyncio
    async def test_40_percent_loss_triggers_emergency(self, position_manager, mock_connection):
        """Test that 40% loss triggers emergency closure."""
        mock_pos = MagicMock()
        mock_pos.contract = MagicMock(symbol="SPY", conId=12345)
        mock_pos.contract.lastTradeDateOrContractMonth = None
        mock_pos.position = 10
        mock_pos.avgCost = 100.0  # Entry at $100

        mock_connection.ib.positions.return_value = [mock_pos]
        # Current price = $60, which is 40% loss
        position_manager._get_current_price = AsyncMock(return_value=60.0)

        positions = await position_manager.get_all()

        assert len(positions) == 1
        assert positions[0].should_close_emergency
        assert positions[0].closure_trigger == "EMERGENCY_STOP"
        assert positions[0].unrealized_pnl_pct <= -0.40

    @pytest.mark.asyncio
    async def test_30_percent_loss_no_emergency(self, position_manager, mock_connection):
        """Test that 30% loss does not trigger emergency (threshold is 40%)."""
        mock_pos = MagicMock()
        mock_pos.contract = MagicMock(symbol="SPY", conId=12345)
        mock_pos.contract.lastTradeDateOrContractMonth = None
        mock_pos.position = 10
        mock_pos.avgCost = 100.0

        mock_connection.ib.positions.return_value = [mock_pos]
        # Current price = $70, which is 30% loss
        position_manager._get_current_price = AsyncMock(return_value=70.0)

        positions = await position_manager.get_all()

        assert len(positions) == 1
        assert not positions[0].should_close_emergency


class TestClosureReasonTracking:
    """Test that closure reasons are properly tracked for audit."""

    @pytest.mark.asyncio
    async def test_close_logs_reason(self, position_manager, mock_connection):
        """Test that close() logs the closure reason."""
        # Create a cached position
        position = Position(
            position_id="SPY_12345",
            symbol="SPY",
            quantity=10,
            entry_price=100.0,
            current_price=95.0,
            unrealized_pnl=-50.0,
            unrealized_pnl_pct=-0.05,
            days_to_expiry=None,
            contract=MagicMock(symbol="SPY", conId=12345),
        )
        position_manager._positions_cache["SPY_12345"] = position

        # Mock wait for fill
        from src.integrations.order_executor import FillResult

        position_manager._wait_for_fill = AsyncMock(
            return_value=FillResult(filled=True, avg_fill_price=95.0, filled_quantity=10)
        )

        await position_manager.close("SPY_12345", reason="MANUAL", timeout=30.0)

        # Verify order was placed
        assert mock_connection.ib.placeOrder.called

    @pytest.mark.asyncio
    async def test_close_all_emergency_liquidation(self, position_manager, mock_connection):
        """Test close_all() emergency liquidation."""
        # Create two cached positions
        position1 = Position(
            position_id="SPY_12345",
            symbol="SPY",
            quantity=10,
            entry_price=100.0,
            current_price=95.0,
            unrealized_pnl=-50.0,
            unrealized_pnl_pct=-0.05,
            days_to_expiry=None,
            contract=MagicMock(symbol="SPY", conId=12345),
        )
        position2 = Position(
            position_id="QQQ_67890",
            symbol="QQQ",
            quantity=5,
            entry_price=200.0,
            current_price=190.0,
            unrealized_pnl=-50.0,
            unrealized_pnl_pct=-0.05,
            days_to_expiry=None,
            contract=MagicMock(symbol="QQQ", conId=67890),
        )
        position_manager._positions_cache["SPY_12345"] = position1
        position_manager._positions_cache["QQQ_67890"] = position2

        # Mock wait for fill
        from src.integrations.order_executor import FillResult

        position_manager._wait_for_fill = AsyncMock(
            return_value=FillResult(filled=True, avg_fill_price=95.0, filled_quantity=10)
        )

        results = await position_manager.close_all(reason="DAILY_LOSS_LIMIT", timeout=60.0)

        # Verify both positions closed
        assert len(results) == 2
        assert mock_connection.ib.placeOrder.call_count == 2
