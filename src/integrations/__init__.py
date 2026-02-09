"""
Integration layer for IBKR Gateway operations.

This package provides:
- IBKRGateway: Main orchestration interface
- GatewayConfig: Configuration dataclass
- ExecutionMode: Execution mode enum (DRY_RUN, PAPER, LIVE-blocked)
- MarketDataPipeline: Data fetching and indicator calculation
- MarketData: Packaged market data for strategies
- OrderExecutor: Order execution with risk validation
- OrderResult: Order execution result
- PositionManager: Position tracking and closure
- Position: Position tracking dataclass

USAGE:
    from src.integrations import IBKRGateway, GatewayConfig, ExecutionMode

    config = GatewayConfig.paper_trading()
    gateway = IBKRGateway(config, risk_manager, mode=ExecutionMode.DRY_RUN)
    await gateway.connect()
    market_data = await gateway.get_market_data("SPY")
"""

from .ibkr_gateway import (
    IBKRGateway,
    GatewayConfig,
    GatewayError,
    GatewayConnectionError,
    GatewayNotConnectedError,
)
from .market_data_pipeline import (
    MarketDataPipeline,
    MarketData,
    DataQuality,
    IndicatorSet,
    InsufficientDataError,
    AlphaLearningViolationError,
)
from .order_executor import (
    OrderExecutor,
    ExecutionMode,
    OrderResult,
    OrderStatus,
    TradeRequest,
    FillResult,
    OrderExecutionError,
)
from .position_manager import (
    PositionManager,
    Position,
    PositionNotFoundError,
    PositionCloseError,
)

__all__ = [
    # Main gateway
    "IBKRGateway",
    "GatewayConfig",
    "GatewayError",
    "GatewayConnectionError",
    "GatewayNotConnectedError",
    # Market data
    "MarketDataPipeline",
    "MarketData",
    "DataQuality",
    "IndicatorSet",
    "InsufficientDataError",
    "AlphaLearningViolationError",
    # Order execution
    "OrderExecutor",
    "ExecutionMode",
    "OrderResult",
    "OrderStatus",
    "TradeRequest",
    "FillResult",
    "OrderExecutionError",
    # Position management
    "PositionManager",
    "Position",
    "PositionNotFoundError",
    "PositionCloseError",
]
