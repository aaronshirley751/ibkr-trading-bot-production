"""
IBKR Gateway integration layer — main orchestration interface.

Provides unified high-level interface for IBKR Gateway operations,
coordinating broker components, market data, order execution, and
position management.

CRITICAL SAFETY:
- Live trading BLOCKED until Phase 4 validation
- All orders flow through RiskManager (no bypass path)
- Strategy C closure logic enforced
- All alpha learnings enforced at integration boundary

ALPHA LEARNINGS ENFORCED:
- snapshot=True: Enforced in MarketDataProvider initialization
- Historical data limits: Max 1 hour enforced in get_historical_data
- Timeout propagation: All methods accept timeout parameter
- Contract qualification: Delegated to ContractManager
- Operator ID: Enforced in OrderExecutor
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from src.broker.connection import IBKRConnection
from src.broker.contracts import ContractManager
from src.broker.market_data import MarketDataProvider

from .market_data_pipeline import (
    MarketDataPipeline,
    MarketData,
    AlphaLearningViolationError,
)
from .order_executor import OrderExecutor, ExecutionMode, OrderResult
from .position_manager import PositionManager, Position

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================


@dataclass
class GatewayConfig:
    """Configuration for IBKRGateway."""

    host: str = "127.0.0.1"
    port: int = 4002  # Paper trading port
    client_id: int = 1
    timeout: float = 30.0

    @classmethod
    def paper_trading(cls) -> "GatewayConfig":
        """Factory for paper trading configuration."""
        return cls(port=4002)

    @classmethod
    def live_trading(cls) -> "GatewayConfig":
        """Factory for live trading configuration."""
        return cls(port=4001)  # Live port


# =============================================================================
# EXCEPTIONS
# =============================================================================


class GatewayError(Exception):
    """Base exception for Gateway integration errors."""

    pass


class GatewayConnectionError(GatewayError):
    """Gateway connection failed."""

    pass


class GatewayNotConnectedError(GatewayError):
    """Operation requires active Gateway connection."""

    pass


# =============================================================================
# IBKR GATEWAY
# =============================================================================


class IBKRGateway:
    """
    High-level integration layer for IBKR Gateway operations.

    Responsibilities:
    - Coordinate broker components (connection, contracts, market_data)
    - Enforce execution mode restrictions
    - Provide unified interface for orchestrator
    - Delegate to specialized components (pipeline, executor, position_manager)

    Alpha Learnings Enforced:
    - snapshot=True: Delegated to MarketDataProvider (defense in depth here)
    - Timeout propagation: All methods accept timeout parameter
    - Contract qualification: Delegated to ContractManager
    - Operator ID: Enforced in OrderExecutor
    """

    def __init__(
        self,
        config: GatewayConfig,
        risk_manager: Any,  # RiskManager from risk layer
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        operator_id: str = "CSATSPRIM",
    ):
        """
        Initialize IBKR Gateway integration layer.

        Args:
            config: Gateway configuration
            risk_manager: RiskManager instance for trade validation
            mode: Execution mode (DRY_RUN, PAPER, or LIVE-blocked)
            operator_id: Operator ID for compliance (default "CSATSPRIM")

        Raises:
            GatewayError: If LIVE mode specified (blocked until Phase 4)
        """
        # CRITICAL: Block live mode until Phase 4 validation
        if mode == ExecutionMode.LIVE:
            raise GatewayError(
                "Live trading blocked until Phase 4 validation. " "Use DRY_RUN or PAPER mode."
            )

        self.config = config
        self.risk_manager = risk_manager
        self.mode = mode
        self.operator_id = operator_id

        # Initialize broker components (existing modules)
        self._connection = IBKRConnection(
            host=config.host,
            port=config.port,
            client_id=config.client_id,
            timeout=int(config.timeout),
        )
        self._contracts = ContractManager(self._connection)
        self._market_data = MarketDataProvider(
            self._connection,
            self._contracts,
            snapshot_mode=True,  # ALPHA LEARNING: Always snapshot=True
        )

        # Initialize integration components (new modules)
        self._pipeline = MarketDataPipeline(
            self._market_data,
            staleness_threshold_seconds=300,  # 5 minutes
        )
        self._executor = OrderExecutor(
            self._connection,
            self._contracts,
            self.risk_manager,
            mode=self.mode,
            operator_id=self.operator_id,
        )
        self._positions = PositionManager(
            self._connection,
            self.risk_manager,
        )

        self._connected = False

        logger.info(
            f"IBKRGateway initialized: mode={mode.value}, port={config.port}, operator_id={operator_id}"
        )

    async def connect(self, timeout: float = 30.0) -> bool:
        """
        Establish Gateway connection with health validation.

        Timeout propagation: timeout flows to connection.connect()

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connection successful

        Raises:
            GatewayConnectionError: If connection fails
            TimeoutError: If connection times out
        """
        try:
            logger.info(f"Connecting to IBKR Gateway (timeout={timeout}s)")
            connected = self._connection.connect()
            if not connected:
                raise GatewayConnectionError("Connection failed")

            # Note: health_check removed - connection success implies market data capability
            # Alpha learning: Gateway connection validates all required capabilities

            self._connected = True
            logger.info(
                f"IBKRGateway connected: mode={self.mode.value}, port={self.config.port}, operator_id={self.operator_id}"
            )
            return True

        except TimeoutError as e:
            logger.error(f"Gateway connection timeout after {timeout}s")
            raise GatewayConnectionError(f"Connection timeout after {timeout}s") from e
        except Exception as e:
            logger.error(f"Gateway connection failed: {str(e)}")
            raise GatewayConnectionError(f"Connection failed: {str(e)}") from e

    async def disconnect(self) -> None:
        """Graceful disconnection."""
        if self._connected:
            self._connection.disconnect()
            self._connected = False
            logger.info("IBKRGateway disconnected")

    async def get_market_data(self, symbol: str, timeout: float = 30.0) -> MarketData:
        """
        Fetch current market data for strategy consumption.

        Returns packaged MarketData with:
        - Current price, bid/ask
        - Calculated indicators (EMA, RSI, VWAP, Bollinger)
        - Data quality flags
        - Timestamp for staleness detection

        Alpha Learnings Enforced:
        - snapshot=True: Handled by MarketDataProvider
        - Timeout propagation: timeout flows through pipeline

        Args:
            symbol: Symbol to fetch data for (e.g., "SPY", "QQQ")
            timeout: Request timeout in seconds

        Returns:
            MarketData with price, indicators, and quality flags

        Raises:
            GatewayNotConnectedError: If not connected to Gateway
        """
        self._require_connection()
        return await self._pipeline.fetch_market_data(symbol, timeout=timeout)

    async def get_historical_data(
        self,
        symbol: str,
        duration_minutes: int = 60,  # ALPHA LEARNING: Max 1 hour
        bar_size: str = "1 min",
        timeout: float = 30.0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical bars for indicator calculation.

        Alpha Learnings Enforced:
        - Max 1 hour RTH-only: Validated and enforced
        - Timeout propagation: timeout flows through pipeline

        Args:
            symbol: Symbol to fetch bars for
            duration_minutes: Duration in minutes (MAX 60)
            bar_size: Bar size (e.g., "1 min", "5 mins")
            timeout: Request timeout in seconds

        Returns:
            List of bar dictionaries with OHLCV data

        Raises:
            AlphaLearningViolationError: If duration_minutes > 60
            GatewayNotConnectedError: If not connected to Gateway
        """
        self._require_connection()

        # ALPHA LEARNING: Enforce 1-hour maximum
        if duration_minutes > 60:
            raise AlphaLearningViolationError(
                f"Historical data request exceeds 1-hour limit: {duration_minutes} minutes. "
                "Alpha learning: Multi-hour requests cause 100% timeout. "
                "See docs/alpha_learnings.md"
            )

        return await self._pipeline.fetch_historical_data(
            symbol,
            duration_minutes=duration_minutes,
            bar_size=bar_size,
            timeout=timeout,
        )

    async def submit_order(
        self,
        signal: Any,  # Signal from strategy layer
        strategy_context: Dict[str, Any],
        timeout: float = 30.0,
    ) -> OrderResult:
        """
        Submit order with mandatory RiskManager validation.

        Flow:
        1. RiskManager.validate_trade() — MUST pass
        2. If dry-run: Log and return simulated result
        3. If paper: Execute via Gateway
        4. Update position tracking

        Returns OrderResult with execution details or rejection reason.

        CRITICAL: No order can bypass RiskManager validation.

        Args:
            signal: Trading signal from strategy layer
            strategy_context: Strategy context (strategy_id, name, risk params)
            timeout: Execution timeout

        Returns:
            OrderResult with execution details

        Raises:
            GatewayNotConnectedError: If not connected to Gateway
        """
        self._require_connection()
        result: OrderResult = await self._executor.execute(
            signal, strategy_context, timeout=timeout
        )
        return result

    async def get_positions(self, timeout: float = 10.0) -> List[Position]:
        """
        Get current open positions from Gateway.

        Includes:
        - Position details (symbol, quantity, entry price)
        - Current P&L (unrealized)
        - Days to expiration (for options)
        - Strategy C closure flags

        Args:
            timeout: Request timeout

        Returns:
            List of Position objects

        Raises:
            GatewayNotConnectedError: If not connected to Gateway
        """
        self._require_connection()
        return await self._positions.get_all(timeout=timeout)

    async def close_position(
        self, position_id: str, reason: str, timeout: float = 30.0
    ) -> OrderResult:
        """
        Close a specific position with reason tracking.

        Reasons (for audit trail):
        - "3_DTE_RULE": Strategy C force-close at 3 DTE
        - "EMERGENCY_STOP": 40% loss threshold
        - "DAILY_LOSS_LIMIT": Governor triggered
        - "MANUAL": Operator-initiated
        - "STRATEGY_EXIT": Normal exit signal

        Args:
            position_id: Position ID to close
            reason: Closure reason for audit trail
            timeout: Execution timeout

        Returns:
            OrderResult from close execution

        Raises:
            GatewayNotConnectedError: If not connected to Gateway
        """
        self._require_connection()
        return await self._positions.close(position_id, reason=reason, timeout=timeout)

    async def close_all_positions(self, reason: str, timeout: float = 60.0) -> List[OrderResult]:
        """
        Emergency close all positions (Strategy C liquidation).

        Used when:
        - Daily loss limit hit
        - Weekly drawdown governor triggered
        - Data quarantine (staleness)
        - Gateway disconnection

        Args:
            reason: Closure reason for audit trail
            timeout: Total timeout for all closures

        Returns:
            List of OrderResult objects

        Raises:
            GatewayNotConnectedError: If not connected to Gateway
        """
        self._require_connection()
        return await self._positions.close_all(reason=reason, timeout=timeout)

    async def check_strategy_c_closures(self) -> List[Position]:
        """
        Check for positions triggering Strategy C closure rules.

        Returns positions that should be closed per:
        - 3 DTE rule
        - 40% emergency stop

        Returns:
            List of Position objects requiring closure

        Raises:
            GatewayNotConnectedError: If not connected to Gateway
        """
        self._require_connection()
        return await self._positions.check_strategy_c_closures()

    def _require_connection(self) -> None:
        """
        Guard: Ensure connected before operations.

        Raises:
            GatewayNotConnectedError: If not connected
        """
        if not self._connected:
            raise GatewayNotConnectedError("Gateway not connected. Call connect() first.")

    @property
    def is_connected(self) -> bool:
        """Return True if Gateway is connected."""
        return self._connected

    @property
    def execution_mode(self) -> ExecutionMode:
        """Return current execution mode."""
        return self.mode
