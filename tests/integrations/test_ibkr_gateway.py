"""
Unit tests for IBKRGateway.

Tests gateway initialization, connection management, and orchestration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.ibkr_gateway import (
    IBKRGateway,
    GatewayConfig,
    ExecutionMode,
    GatewayError,
    GatewayNotConnectedError,
)


@pytest.fixture
def mock_risk_manager():
    """Mock RiskManager."""
    rm = MagicMock()
    rm.evaluate = MagicMock(return_value=MagicMock(approved=True, rejections=[]))
    return rm


@pytest.fixture
def gateway_config():
    """Paper trading gateway configuration."""
    return GatewayConfig.paper_trading()


class TestGatewayConfig:
    """Test GatewayConfig factories."""

    def test_paper_trading_config(self):
        """Test paper trading configuration."""
        config = GatewayConfig.paper_trading()

        assert config.port == 4002
        assert config.host == "127.0.0.1"

    def test_live_trading_config(self):
        """Test live trading configuration."""
        config = GatewayConfig.live_trading()

        assert config.port == 4001
        assert config.host == "127.0.0.1"


class TestGatewayInitialization:
    """Test gateway initialization and mode enforcement."""

    def test_dry_run_mode_allowed(self, gateway_config, mock_risk_manager):
        """Test DRY_RUN mode is allowed."""
        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.DRY_RUN)

        assert gateway.execution_mode == ExecutionMode.DRY_RUN
        assert not gateway.is_connected

    def test_paper_mode_allowed(self, gateway_config, mock_risk_manager):
        """Test PAPER mode is allowed."""
        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.PAPER)

        assert gateway.execution_mode == ExecutionMode.PAPER
        assert not gateway.is_connected

    def test_live_mode_blocked(self, gateway_config, mock_risk_manager):
        """Test LIVE mode is blocked until Phase 4."""
        with pytest.raises(GatewayError) as exc_info:
            IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.LIVE)

        assert "Phase 4" in str(exc_info.value)
        assert "blocked" in str(exc_info.value).lower()

    def test_operator_id_set(self, gateway_config, mock_risk_manager):
        """Test operator ID is properly set."""
        gateway = IBKRGateway(
            gateway_config,
            mock_risk_manager,
            mode=ExecutionMode.DRY_RUN,
            operator_id="CSATSPRIM",
        )

        assert gateway.operator_id == "CSATSPRIM"


class TestGatewayConnection:
    """Test gateway connection management."""

    @pytest.mark.asyncio
    @patch("src.integrations.ibkr_gateway.IBKRConnection")
    async def test_connect_success(self, mock_connection_class, gateway_config, mock_risk_manager):
        """Test successful connection."""
        # Mock connection
        mock_conn_instance = MagicMock()
        mock_conn_instance.connect = AsyncMock(return_value=True)
        mock_conn_instance.health_check = AsyncMock(return_value={"market_data_available": True})
        mock_connection_class.return_value = mock_conn_instance

        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.DRY_RUN)
        gateway._connection = mock_conn_instance

        result = await gateway.connect(timeout=30.0)

        assert result is True
        assert gateway.is_connected
        mock_conn_instance.connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.integrations.ibkr_gateway.IBKRConnection")
    async def test_disconnect(self, mock_connection_class, gateway_config, mock_risk_manager):
        """Test graceful disconnection."""
        # Mock connection
        mock_conn_instance = MagicMock()
        mock_conn_instance.connect = AsyncMock(return_value=True)
        mock_conn_instance.disconnect = AsyncMock()
        mock_conn_instance.health_check = AsyncMock(return_value={"market_data_available": True})
        mock_connection_class.return_value = mock_conn_instance

        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.DRY_RUN)
        gateway._connection = mock_conn_instance

        await gateway.connect()
        await gateway.disconnect()

        assert not gateway.is_connected
        mock_conn_instance.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_operations_require_connection(self, gateway_config, mock_risk_manager):
        """Test that operations fail when not connected."""
        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.DRY_RUN)

        # Not connected yet
        with pytest.raises(GatewayNotConnectedError):
            await gateway.get_market_data("SPY")

        with pytest.raises(GatewayNotConnectedError):
            await gateway.get_positions()

        with pytest.raises(GatewayNotConnectedError):
            await gateway.get_historical_data("SPY")


class TestAlphaLearningEnforcement:
    """Test alpha learning enforcement at gateway level."""

    @pytest.mark.asyncio
    @patch("src.integrations.ibkr_gateway.IBKRConnection")
    async def test_historical_data_1_hour_limit_enforced(
        self, mock_connection_class, gateway_config, mock_risk_manager
    ):
        """Test 1-hour historical data limit is enforced."""
        # Mock connection as connected
        mock_conn_instance = MagicMock()
        mock_conn_instance.connect = AsyncMock(return_value=True)
        mock_conn_instance.health_check = AsyncMock(return_value={"market_data_available": True})
        mock_connection_class.return_value = mock_conn_instance

        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.DRY_RUN)
        gateway._connection = mock_conn_instance
        await gateway.connect()

        from src.integrations.market_data_pipeline import AlphaLearningViolationError

        # Attempt to request >60 minutes
        with pytest.raises(AlphaLearningViolationError) as exc_info:
            await gateway.get_historical_data("SPY", duration_minutes=120)

        assert "1-hour" in str(exc_info.value) or "60 minutes" in str(exc_info.value)


class TestGatewayOrchestration:
    """Test that gateway properly orchestrates all components."""

    @pytest.mark.asyncio
    @patch("src.integrations.ibkr_gateway.IBKRConnection")
    async def test_gateway_delegates_to_pipeline(
        self, mock_connection_class, gateway_config, mock_risk_manager
    ):
        """Test that market data requests delegate to pipeline."""
        # Mock connection
        mock_conn_instance = MagicMock()
        mock_conn_instance.connect = AsyncMock(return_value=True)
        mock_conn_instance.health_check = AsyncMock(return_value={"market_data_available": True})
        mock_connection_class.return_value = mock_conn_instance

        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.DRY_RUN)
        gateway._connection = mock_conn_instance

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.fetch_market_data = AsyncMock(
            return_value=MagicMock(symbol="SPY", last_price=450.0)
        )
        gateway._pipeline = mock_pipeline

        await gateway.connect()
        market_data = await gateway.get_market_data("SPY")

        # Verify pipeline was called
        mock_pipeline.fetch_market_data.assert_called_once_with("SPY", timeout=30.0)
        assert market_data.symbol == "SPY"

    @pytest.mark.asyncio
    @patch("src.integrations.ibkr_gateway.IBKRConnection")
    async def test_gateway_delegates_to_executor(
        self, mock_connection_class, gateway_config, mock_risk_manager
    ):
        """Test that order submission delegates to executor."""
        from src.strategies.base import Signal, Direction, StrategyType
        from datetime import datetime, timezone

        # Mock connection
        mock_conn_instance = MagicMock()
        mock_conn_instance.connect = AsyncMock(return_value=True)
        mock_conn_instance.health_check = AsyncMock(return_value={"market_data_available": True})
        mock_connection_class.return_value = mock_conn_instance

        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.DRY_RUN)
        gateway._connection = mock_conn_instance

        # Mock executor
        from src.integrations.order_executor import OrderResult, OrderStatus

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(
            return_value=OrderResult(
                order_id="ORD_001",
                status=OrderStatus.SIMULATED,
                timestamp=datetime.now(timezone.utc),
            )
        )
        gateway._executor = mock_executor

        await gateway.connect()

        signal = Signal(
            direction=Direction.BUY,
            symbol="SPY",
            confidence=0.8,
            rationale="Test",
            timestamp=datetime.now(timezone.utc),
            strategy_type=StrategyType.A,
        )
        context = {"strategy_id": "test", "strategy_name": "test"}

        result = await gateway.submit_order(signal, context)

        # Verify executor was called
        mock_executor.execute.assert_called_once()
        assert result.status == OrderStatus.SIMULATED

    @pytest.mark.asyncio
    @patch("src.integrations.ibkr_gateway.IBKRConnection")
    async def test_gateway_delegates_to_position_manager(
        self, mock_connection_class, gateway_config, mock_risk_manager
    ):
        """Test that position queries delegate to position manager."""
        # Mock connection
        mock_conn_instance = MagicMock()
        mock_conn_instance.connect = AsyncMock(return_value=True)
        mock_conn_instance.health_check = AsyncMock(return_value={"market_data_available": True})
        mock_connection_class.return_value = mock_conn_instance

        gateway = IBKRGateway(gateway_config, mock_risk_manager, mode=ExecutionMode.DRY_RUN)
        gateway._connection = mock_conn_instance

        # Mock position manager
        mock_pos_manager = MagicMock()
        mock_pos_manager.get_all = AsyncMock(return_value=[])
        gateway._positions = mock_pos_manager

        await gateway.connect()
        positions = await gateway.get_positions()

        # Verify position manager was called
        mock_pos_manager.get_all.assert_called_once_with(timeout=10.0)
        assert positions == []
