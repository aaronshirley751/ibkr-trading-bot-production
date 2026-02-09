# VSC HANDOFF: Task 2.6 — IBKR Gateway Integration Layer

## Document Metadata
| Field | Value |
|-------|-------|
| **Task ID** | 2.6 |
| **Date** | 2026-02-09 |
| **Requested By** | Operator (Phase 2, Sprint 2C) |
| **Lead Persona** | @Systems_Architect |
| **Supporting Personas** | @CRO (risk validation), @QA_Lead (test specifications) |
| **Model Routing** | Opus with Extended Thinking |
| **Estimated Complexity** | High (alpha learnings enforcement, broker integration) |
| **Context Budget** | ~25% of session (fresh context, single deliverable) |
| **Upstream Dependencies** | Task 2.5 (RiskManager) ✅ Complete |
| **Downstream Dependents** | Task 2.7 (Gameplan Ingestion) — BLOCKED until 2.6 complete |

---

# CONTEXT BLOCK

## Why This Task Exists

Task 2.6 creates the **integration layer** that bridges the existing broker modules (`src/broker/*`) with the strategy layer and risk controls. The broker modules (connection, contracts, market_data) are production-ready with 92% coverage from Phase 1, but they operate as isolated components. This integration layer:

1. **Unifies the broker stack** into a single high-level interface for the orchestrator
2. **Enforces the strategy → risk → broker pipeline** ensuring all orders flow through RiskManager
3. **Implements alpha learnings at the integration boundary** where violations are most likely to occur
4. **Provides dry-run simulation** for safe development and testing
5. **Enables market data packaging** for strategy consumption

Without this layer, the orchestrator would need to coordinate multiple broker components directly, increasing complexity and risk of alpha learning violations.

## What Success Looks Like

**Functional Success:**
- Orchestrator can request market data through a single `IBKRGateway` interface
- Orders flow through mandatory RiskManager validation before execution
- Dry-run mode simulates execution without touching the broker
- Paper trading mode executes via Gateway with position tracking
- Position closure logic (Strategy C) works correctly at 3 DTE / 40% emergency stop
- All alpha learnings are enforced with automated tests validating enforcement

**Safety Success:**
- `snapshot=True` violation is impossible at integration layer (defense in depth)
- Operator ID 'CSATSPRIM' attached to every order (compliance requirement)
- Data staleness triggers Strategy C within 5 minutes
- No order can bypass RiskManager validation
- Connection failures trigger graceful degradation, not crashes

**Quality Success:**
- 85% unit test coverage on integration layer
- All alpha learnings have regression tests
- Integration tests validate end-to-end flow
- Dry-run validation demonstrates correct behavior
- All existing tests continue to pass (no regressions)

## Success Criteria (Measurable)

| Criterion | Target | Validation Method |
|-----------|--------|-------------------|
| Unit test coverage | ≥85% | `pytest --cov=src/integrations` |
| Alpha learning tests | 100% coverage | Dedicated test module |
| Existing test suite | 0 regressions | `pytest` full suite |
| Dry-run validation | Pass | Manual dry-run execution |
| Code quality | 0 warnings | `ruff check && black --check && mypy` |
| Integration tests | Pass | Mocked Gateway tests |

---

# AGENT EXECUTION BLOCK

## 1. Objective

Create `src/integrations/ibkr_gateway.py` — a high-level integration layer that:

1. Wraps existing broker modules into a unified `IBKRGateway` class
2. Provides `MarketDataPipeline` for strategy data consumption
3. Implements `OrderExecutor` with mandatory RiskManager validation
4. Manages positions with Strategy C closure logic
5. Enforces all alpha learnings at integration boundary
6. Supports dry-run, paper, and (future) live execution modes

**Primary Interface:**
```python
gateway = IBKRGateway(config, risk_manager, mode="paper")
market_data = await gateway.get_market_data("SPY")
order_result = await gateway.submit_order(signal, strategy_context)
positions = await gateway.get_positions()
await gateway.close_position(position_id, reason="3_DTE_RULE")
```

---

## 2. File Structure

```
src/
├── integrations/
│   ├── __init__.py                    # CREATE: Export IBKRGateway, MarketDataPipeline
│   ├── ibkr_gateway.py                # CREATE: Main integration layer (~450 lines)
│   ├── market_data_pipeline.py        # CREATE: Data packaging for strategies (~200 lines)
│   ├── order_executor.py              # CREATE: Order flow with risk validation (~250 lines)
│   └── position_manager.py            # CREATE: Position tracking and closure (~150 lines)
│
├── broker/                            # EXISTING (no modifications)
│   ├── connection.py                  # IBKRConnection (already has retry logic)
│   ├── contracts.py                   # ContractManager (already has qualification)
│   ├── market_data.py                 # MarketDataProvider (already has snapshot=True)
│   └── exceptions.py                  # BrokerError, etc.
│
├── risk/                              # EXISTING (Task 2.5)
│   └── risk_manager.py                # RiskManager (pre-trade validation)
│
└── strategies/                        # EXISTING (Tasks 2.1-2.4)
    └── ...                            # Strategy A, B, C implementations

tests/
├── integrations/
│   ├── __init__.py                    # CREATE
│   ├── test_ibkr_gateway.py           # CREATE: Gateway unit tests
│   ├── test_market_data_pipeline.py   # CREATE: Pipeline tests
│   ├── test_order_executor.py         # CREATE: Order flow tests
│   ├── test_position_manager.py       # CREATE: Position tests
│   └── test_alpha_learnings.py        # CREATE: Alpha learning regression tests
│
└── integration/                       # EXISTING
    └── test_gateway_integration.py    # CREATE: End-to-end integration tests
```

**File Count:** 5 new source files, 6 new test files

---

## 3. Logic Flow (Pseudo-code)

### 3.1 IBKRGateway — Main Orchestration Interface

```python
class ExecutionMode(Enum):
    DRY_RUN = "dry_run"      # Log only, no execution
    PAPER = "paper"          # Execute via paper trading Gateway
    LIVE = "live"            # BLOCKED until Phase 4

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
        risk_manager: RiskManager,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        operator_id: str = "CSATSPRIM"
    ):
        # CRITICAL: Block live mode until Phase 4 validation
        if mode == ExecutionMode.LIVE:
            raise GatewayError(
                "Live trading blocked until Phase 4 validation. "
                "Use DRY_RUN or PAPER mode."
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
            timeout=config.timeout
        )
        self._contracts = ContractManager(self._connection)
        self._market_data = MarketDataProvider(
            self._connection,
            self._contracts,
            snapshot=True  # ALPHA LEARNING: Always snapshot=True
        )

        # Initialize integration components (new modules)
        self._pipeline = MarketDataPipeline(
            self._market_data,
            staleness_threshold_seconds=300  # 5 minutes
        )
        self._executor = OrderExecutor(
            self._connection,
            self._contracts,
            self.risk_manager,
            mode=self.mode,
            operator_id=self.operator_id
        )
        self._positions = PositionManager(
            self._connection,
            self.risk_manager
        )

        self._connected = False

    async def connect(self, timeout: float = 30.0) -> bool:
        """
        Establish Gateway connection with health validation.

        Timeout propagation: timeout flows to connection.connect()
        """
        try:
            await self._connection.connect(timeout=timeout)

            # Health check: verify market data capability
            health = await self._connection.health_check(timeout=5.0)
            if not health.market_data_available:
                raise GatewayError("Gateway connected but market data unavailable")

            self._connected = True
            logger.info(
                "IBKRGateway connected",
                mode=self.mode.value,
                operator_id=self.operator_id
            )
            return True

        except TimeoutError as e:
            logger.error("Gateway connection timeout", timeout=timeout)
            raise GatewayConnectionError(f"Connection timeout after {timeout}s") from e

    async def disconnect(self):
        """Graceful disconnection."""
        if self._connected:
            await self._connection.disconnect()
            self._connected = False
            logger.info("IBKRGateway disconnected")

    async def get_market_data(
        self,
        symbol: str,
        timeout: float = 30.0
    ) -> MarketData:
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
        """
        self._require_connection()
        return await self._pipeline.fetch_market_data(symbol, timeout=timeout)

    async def get_historical_data(
        self,
        symbol: str,
        duration_minutes: int = 60,  # ALPHA LEARNING: Max 1 hour
        bar_size: str = "1 min",
        timeout: float = 30.0
    ) -> list[BarData]:
        """
        Fetch historical bars for indicator calculation.

        Alpha Learnings Enforced:
        - Max 1 hour RTH-only: Validated and enforced
        - Max 60 bars: Validated and enforced
        - Timeout propagation: timeout flows through pipeline
        """
        self._require_connection()

        # ALPHA LEARNING: Enforce 1-hour maximum
        if duration_minutes > 60:
            raise AlphaLearningViolationError(
                f"Historical data request exceeds 1-hour limit: {duration_minutes} minutes. "
                "Alpha learning: Multi-hour requests cause 100% timeout."
            )

        return await self._pipeline.fetch_historical_data(
            symbol,
            duration_minutes=duration_minutes,
            bar_size=bar_size,
            timeout=timeout
        )

    async def submit_order(
        self,
        signal: TradingSignal,
        strategy_context: StrategyContext,
        timeout: float = 30.0
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
        """
        self._require_connection()
        return await self._executor.execute(
            signal,
            strategy_context,
            timeout=timeout
        )

    async def get_positions(self, timeout: float = 10.0) -> list[Position]:
        """
        Get current open positions from Gateway.

        Includes:
        - Position details (symbol, quantity, entry price)
        - Current P&L (unrealized)
        - Days to expiration (for options)
        - Strategy C closure flags
        """
        self._require_connection()
        return await self._positions.get_all(timeout=timeout)

    async def close_position(
        self,
        position_id: str,
        reason: str,
        timeout: float = 30.0
    ) -> OrderResult:
        """
        Close a specific position with reason tracking.

        Reasons (for audit trail):
        - "3_DTE_RULE": Strategy C force-close at 3 DTE
        - "EMERGENCY_STOP": 40% loss threshold
        - "DAILY_LOSS_LIMIT": Governor triggered
        - "MANUAL": Operator-initiated
        - "STRATEGY_EXIT": Normal exit signal
        """
        self._require_connection()
        return await self._positions.close(
            position_id,
            reason=reason,
            timeout=timeout
        )

    async def close_all_positions(
        self,
        reason: str,
        timeout: float = 60.0
    ) -> list[OrderResult]:
        """
        Emergency close all positions (Strategy C liquidation).

        Used when:
        - Daily loss limit hit
        - Weekly drawdown governor triggered
        - Data quarantine (staleness)
        - Gateway disconnection
        """
        self._require_connection()
        return await self._positions.close_all(reason=reason, timeout=timeout)

    def _require_connection(self):
        """Guard: Ensure connected before operations."""
        if not self._connected:
            raise GatewayNotConnectedError(
                "Gateway not connected. Call connect() first."
            )

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def execution_mode(self) -> ExecutionMode:
        return self.mode


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
```

### 3.2 MarketDataPipeline — Data Packaging for Strategies

```python
@dataclass
class MarketData:
    """
    Packaged market data for strategy consumption.

    Contains all data a strategy needs to generate signals:
    - Current price and quotes
    - Calculated technical indicators
    - Data quality metadata
    """
    symbol: str
    timestamp: datetime

    # Price data
    last_price: float
    bid: float
    ask: float
    volume: int

    # Technical indicators (calculated)
    ema_fast: float          # 8-period EMA
    ema_slow: float          # 21-period EMA
    rsi: float               # 14-period RSI
    vwap: float              # Session VWAP
    bollinger_upper: float   # 20-period, 2σ
    bollinger_lower: float   # 20-period, 2σ
    bollinger_middle: float  # 20-period SMA

    # Data quality flags
    is_stale: bool = False
    staleness_seconds: float = 0.0
    missing_fields: list[str] = field(default_factory=list)
    data_quality_score: float = 1.0  # 0.0 = unusable, 1.0 = perfect


class MarketDataPipeline:
    """
    Fetches, calculates, and packages market data for strategies.

    Responsibilities:
    - Fetch real-time data via MarketDataProvider
    - Calculate technical indicators from historical bars
    - Validate data quality (staleness, missing fields)
    - Package into MarketData dataclass

    Alpha Learnings:
    - snapshot=True: Delegated to MarketDataProvider
    - Historical limits: Enforced in fetch_historical_data
    - Timeout propagation: All methods accept timeout
    """

    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        staleness_threshold_seconds: float = 300.0  # 5 minutes
    ):
        self._provider = market_data_provider
        self._staleness_threshold = staleness_threshold_seconds
        self._indicator_cache: dict[str, IndicatorCache] = {}

    async def fetch_market_data(
        self,
        symbol: str,
        timeout: float = 30.0
    ) -> MarketData:
        """
        Fetch and package current market data with indicators.

        Flow:
        1. Fetch real-time quote (snapshot=True enforced by provider)
        2. Fetch historical bars for indicator calculation
        3. Calculate all technical indicators
        4. Validate data quality
        5. Package into MarketData
        """
        # Step 1: Fetch real-time quote
        quote = await self._provider.get_quote(
            symbol,
            timeout=timeout,
            snapshot=True  # ALPHA LEARNING: Defense in depth
        )

        # Step 2: Fetch historical bars (1 hour RTH for indicators)
        # ALPHA LEARNING: Max 1 hour, enforced here
        bars = await self._provider.get_historical_bars(
            symbol,
            duration="1 hour",
            bar_size="1 min",
            what_to_show="TRADES",
            use_rth=True,  # RTH only
            timeout=timeout
        )

        # Step 3: Calculate indicators
        indicators = self._calculate_indicators(bars)

        # Step 4: Validate data quality
        quality = self._validate_data_quality(quote, indicators)

        # Step 5: Package
        return MarketData(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            last_price=quote.last,
            bid=quote.bid,
            ask=quote.ask,
            volume=quote.volume,
            ema_fast=indicators.ema_fast,
            ema_slow=indicators.ema_slow,
            rsi=indicators.rsi,
            vwap=indicators.vwap,
            bollinger_upper=indicators.bollinger_upper,
            bollinger_lower=indicators.bollinger_lower,
            bollinger_middle=indicators.bollinger_middle,
            is_stale=quality.is_stale,
            staleness_seconds=quality.staleness_seconds,
            missing_fields=quality.missing_fields,
            data_quality_score=quality.score
        )

    def _calculate_indicators(self, bars: list[BarData]) -> IndicatorSet:
        """
        Calculate all technical indicators from historical bars.

        Uses numpy for efficient calculation.
        """
        if not bars or len(bars) < 21:  # Need at least 21 bars for slow EMA
            raise InsufficientDataError(
                f"Need at least 21 bars for indicators, got {len(bars)}"
            )

        closes = np.array([b.close for b in bars])
        highs = np.array([b.high for b in bars])
        lows = np.array([b.low for b in bars])
        volumes = np.array([b.volume for b in bars])

        return IndicatorSet(
            ema_fast=self._calculate_ema(closes, period=8),
            ema_slow=self._calculate_ema(closes, period=21),
            rsi=self._calculate_rsi(closes, period=14),
            vwap=self._calculate_vwap(closes, highs, lows, volumes),
            bollinger_upper=self._calculate_bollinger(closes, period=20, std=2)[0],
            bollinger_lower=self._calculate_bollinger(closes, period=20, std=2)[1],
            bollinger_middle=self._calculate_bollinger(closes, period=20, std=2)[2]
        )

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Exponential Moving Average — return latest value."""
        if len(prices) < period:
            raise InsufficientDataError(f"Need {period} bars for EMA")

        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return float(ema)

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Relative Strength Index — return latest value."""
        if len(prices) < period + 1:
            raise InsufficientDataError(f"Need {period + 1} bars for RSI")

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)

    def _calculate_vwap(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray
    ) -> float:
        """Volume Weighted Average Price — return session value."""
        typical_prices = (highs + lows + closes) / 3
        cumulative_tpv = np.sum(typical_prices * volumes)
        cumulative_volume = np.sum(volumes)

        if cumulative_volume == 0:
            return float(closes[-1])  # Fallback to last close

        return float(cumulative_tpv / cumulative_volume)

    def _calculate_bollinger(
        self,
        prices: np.ndarray,
        period: int = 20,
        std: int = 2
    ) -> tuple[float, float, float]:
        """Bollinger Bands — return (upper, lower, middle)."""
        if len(prices) < period:
            raise InsufficientDataError(f"Need {period} bars for Bollinger")

        recent = prices[-period:]
        middle = float(np.mean(recent))
        std_dev = float(np.std(recent))

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return upper, lower, middle

    def _validate_data_quality(
        self,
        quote: Quote,
        indicators: IndicatorSet
    ) -> DataQuality:
        """
        Validate data quality for trading decisions.

        Checks:
        - Staleness (quote timestamp vs now)
        - Missing fields (bid/ask/volume = 0)
        - Indicator validity (NaN, extreme values)
        """
        now = datetime.now(timezone.utc)
        staleness_seconds = (now - quote.timestamp).total_seconds()
        is_stale = staleness_seconds > self._staleness_threshold

        missing_fields = []
        if quote.bid <= 0:
            missing_fields.append("bid")
        if quote.ask <= 0:
            missing_fields.append("ask")
        if quote.volume <= 0:
            missing_fields.append("volume")

        # Check for NaN indicators
        for field_name, value in [
            ("ema_fast", indicators.ema_fast),
            ("ema_slow", indicators.ema_slow),
            ("rsi", indicators.rsi),
            ("vwap", indicators.vwap),
        ]:
            if np.isnan(value):
                missing_fields.append(field_name)

        # Calculate quality score
        # Start at 1.0, deduct for issues
        score = 1.0
        if is_stale:
            score -= 0.5
        score -= len(missing_fields) * 0.1
        score = max(0.0, score)

        return DataQuality(
            is_stale=is_stale,
            staleness_seconds=staleness_seconds,
            missing_fields=missing_fields,
            score=score
        )


@dataclass
class IndicatorSet:
    """Calculated technical indicators."""
    ema_fast: float
    ema_slow: float
    rsi: float
    vwap: float
    bollinger_upper: float
    bollinger_lower: float
    bollinger_middle: float


@dataclass
class DataQuality:
    """Data quality assessment."""
    is_stale: bool
    staleness_seconds: float
    missing_fields: list[str]
    score: float
```

### 3.3 OrderExecutor — Risk-Validated Order Flow

```python
class OrderExecutor:
    """
    Executes orders with mandatory RiskManager validation.

    CRITICAL SAFETY INVARIANT:
    Every order MUST flow through RiskManager.validate_trade()
    before any execution path (dry-run, paper, or live).

    There is NO bypass. No "quick" path. No exceptions.

    Responsibilities:
    - Validate all orders through RiskManager
    - Enforce operator ID on all orders
    - Route to appropriate execution mode
    - Track order results for position management
    """

    def __init__(
        self,
        connection: IBKRConnection,
        contracts: ContractManager,
        risk_manager: RiskManager,
        mode: ExecutionMode,
        operator_id: str = "CSATSPRIM"
    ):
        self._connection = connection
        self._contracts = contracts
        self._risk_manager = risk_manager
        self._mode = mode
        self._operator_id = operator_id

        # Order tracking
        self._pending_orders: dict[str, PendingOrder] = {}
        self._order_counter = 0

    async def execute(
        self,
        signal: TradingSignal,
        strategy_context: StrategyContext,
        timeout: float = 30.0
    ) -> OrderResult:
        """
        Execute trading signal with full risk validation.

        Flow:
        1. Build TradeRequest from signal
        2. RiskManager.validate_trade() — MANDATORY
        3. If rejected: Return rejection result
        4. If approved: Route to execution mode
        5. Track result

        Returns OrderResult with execution details or rejection reason.
        """
        # Step 1: Build trade request
        trade_request = self._build_trade_request(signal, strategy_context)

        # Step 2: MANDATORY RISK VALIDATION
        # This is the critical safety gate. No bypass allowed.
        validation_result = await self._risk_manager.validate_trade(trade_request)

        if not validation_result.approved:
            # Risk validation failed — return rejection
            logger.warning(
                "Order rejected by RiskManager",
                signal=signal,
                rejection_reasons=validation_result.rejection_reasons
            )
            return OrderResult(
                order_id=self._generate_order_id(),
                status=OrderStatus.REJECTED,
                rejection_reason="; ".join(validation_result.rejection_reasons),
                risk_validation=validation_result,
                timestamp=datetime.now(timezone.utc)
            )

        # Step 3: Route to execution mode
        if self._mode == ExecutionMode.DRY_RUN:
            return await self._execute_dry_run(trade_request, validation_result)
        elif self._mode == ExecutionMode.PAPER:
            return await self._execute_paper(trade_request, validation_result, timeout)
        else:
            # ExecutionMode.LIVE blocked in IBKRGateway.__init__
            # This should never be reached
            raise GatewayError("Live execution blocked — this should be unreachable")

    def _build_trade_request(
        self,
        signal: TradingSignal,
        context: StrategyContext
    ) -> TradeRequest:
        """Build TradeRequest from signal and strategy context."""
        return TradeRequest(
            symbol=signal.symbol,
            action=signal.action,  # BUY or SELL
            quantity=signal.quantity,
            order_type=signal.order_type,  # MARKET, LIMIT, etc.
            limit_price=signal.limit_price,
            strategy_id=context.strategy_id,
            strategy_name=context.strategy_name,
            risk_per_trade=context.risk_per_trade,
            take_profit_pct=context.take_profit_pct,
            stop_loss_pct=context.stop_loss_pct,
            expiry=signal.expiry,
            strike=signal.strike,
            right=signal.right,  # CALL or PUT
            operator_id=self._operator_id  # COMPLIANCE REQUIREMENT
        )

    async def _execute_dry_run(
        self,
        trade_request: TradeRequest,
        validation: ValidationResult
    ) -> OrderResult:
        """
        Dry-run execution: Log only, no actual order.

        Used for:
        - Development and testing
        - Strategy validation
        - Pre-deployment verification
        """
        order_id = self._generate_order_id()

        logger.info(
            "DRY-RUN ORDER",
            order_id=order_id,
            symbol=trade_request.symbol,
            action=trade_request.action,
            quantity=trade_request.quantity,
            order_type=trade_request.order_type,
            limit_price=trade_request.limit_price,
            strategy=trade_request.strategy_name,
            operator_id=trade_request.operator_id,
            risk_metrics=validation.risk_metrics
        )

        # Simulate fill for testing purposes
        simulated_fill_price = trade_request.limit_price or 0.0

        return OrderResult(
            order_id=order_id,
            status=OrderStatus.SIMULATED,
            fill_price=simulated_fill_price,
            fill_quantity=trade_request.quantity,
            execution_mode=ExecutionMode.DRY_RUN,
            risk_validation=validation,
            timestamp=datetime.now(timezone.utc)
        )

    async def _execute_paper(
        self,
        trade_request: TradeRequest,
        validation: ValidationResult,
        timeout: float
    ) -> OrderResult:
        """
        Paper trading execution: Execute via Gateway paper account.

        Flow:
        1. Qualify contract
        2. Build IBKR order
        3. Place via Gateway
        4. Wait for fill or timeout
        5. Return result
        """
        order_id = self._generate_order_id()

        try:
            # Step 1: Qualify contract
            # ALPHA LEARNING: Contract must be qualified before order
            contract = await self._contracts.qualify_option_contract(
                symbol=trade_request.symbol,
                expiry=trade_request.expiry,
                strike=trade_request.strike,
                right=trade_request.right,
                timeout=timeout
            )

            # Step 2: Build IBKR order
            ibkr_order = self._build_ibkr_order(trade_request)

            # Step 3: Place order via Gateway
            trade = await self._connection.place_order(
                contract=contract,
                order=ibkr_order,
                timeout=timeout
            )

            # Step 4: Wait for fill
            fill_result = await self._wait_for_fill(
                trade,
                timeout=timeout
            )

            logger.info(
                "PAPER ORDER EXECUTED",
                order_id=order_id,
                symbol=trade_request.symbol,
                fill_price=fill_result.avg_fill_price,
                fill_quantity=fill_result.filled_quantity,
                operator_id=trade_request.operator_id
            )

            return OrderResult(
                order_id=order_id,
                ibkr_order_id=trade.order.orderId,
                status=OrderStatus.FILLED if fill_result.filled else OrderStatus.PARTIAL,
                fill_price=fill_result.avg_fill_price,
                fill_quantity=fill_result.filled_quantity,
                execution_mode=ExecutionMode.PAPER,
                risk_validation=validation,
                timestamp=datetime.now(timezone.utc)
            )

        except ContractQualificationError as e:
            logger.error("Contract qualification failed", error=str(e))
            return OrderResult(
                order_id=order_id,
                status=OrderStatus.FAILED,
                rejection_reason=f"Contract qualification failed: {e}",
                execution_mode=ExecutionMode.PAPER,
                timestamp=datetime.now(timezone.utc)
            )
        except TimeoutError as e:
            logger.error("Order execution timeout", timeout=timeout)
            return OrderResult(
                order_id=order_id,
                status=OrderStatus.TIMEOUT,
                rejection_reason=f"Execution timeout after {timeout}s",
                execution_mode=ExecutionMode.PAPER,
                timestamp=datetime.now(timezone.utc)
            )
        except BrokerError as e:
            logger.error("Broker error during execution", error=str(e))
            return OrderResult(
                order_id=order_id,
                status=OrderStatus.FAILED,
                rejection_reason=str(e),
                execution_mode=ExecutionMode.PAPER,
                timestamp=datetime.now(timezone.utc)
            )

    def _build_ibkr_order(self, trade_request: TradeRequest) -> Order:
        """Build ib_insync Order from TradeRequest."""
        order = Order()
        order.action = trade_request.action
        order.totalQuantity = trade_request.quantity
        order.orderType = trade_request.order_type

        if trade_request.limit_price:
            order.lmtPrice = trade_request.limit_price

        # COMPLIANCE REQUIREMENT: Operator ID on all orders
        order.account = trade_request.operator_id

        return order

    async def _wait_for_fill(
        self,
        trade: Trade,
        timeout: float
    ) -> FillResult:
        """Wait for order to fill with timeout."""
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            if trade.isDone():
                return FillResult(
                    filled=True,
                    avg_fill_price=trade.orderStatus.avgFillPrice,
                    filled_quantity=trade.orderStatus.filled
                )
            await asyncio.sleep(0.1)

        # Timeout — return partial fill status
        return FillResult(
            filled=False,
            avg_fill_price=trade.orderStatus.avgFillPrice,
            filled_quantity=trade.orderStatus.filled
        )

    def _generate_order_id(self) -> str:
        """Generate unique order ID for tracking."""
        self._order_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"ORD_{timestamp}_{self._order_counter:04d}"


@dataclass
class TradeRequest:
    """Trade request for risk validation and execution."""
    symbol: str
    action: str  # BUY or SELL
    quantity: int
    order_type: str  # MARKET, LIMIT, etc.
    limit_price: float | None
    strategy_id: str
    strategy_name: str
    risk_per_trade: float
    take_profit_pct: float
    stop_loss_pct: float
    expiry: str  # YYYYMMDD format
    strike: float
    right: str  # CALL or PUT
    operator_id: str


@dataclass
class OrderResult:
    """Result of order execution attempt."""
    order_id: str
    status: OrderStatus
    timestamp: datetime
    ibkr_order_id: int | None = None
    fill_price: float | None = None
    fill_quantity: int | None = None
    rejection_reason: str | None = None
    execution_mode: ExecutionMode | None = None
    risk_validation: ValidationResult | None = None


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SIMULATED = "simulated"  # Dry-run only
    CANCELLED = "cancelled"


@dataclass
class FillResult:
    """Fill status from order execution."""
    filled: bool
    avg_fill_price: float
    filled_quantity: int
```

### 3.4 PositionManager — Position Tracking and Closure

```python
class PositionManager:
    """
    Manages open positions with Strategy C closure logic.

    Responsibilities:
    - Track open positions from Gateway
    - Monitor P&L in real-time
    - Implement Strategy C closure rules (3 DTE, 40% emergency stop)
    - Sync position state with RiskManager
    """

    def __init__(
        self,
        connection: IBKRConnection,
        risk_manager: RiskManager
    ):
        self._connection = connection
        self._risk_manager = risk_manager
        self._positions_cache: dict[str, Position] = {}
        self._last_sync: datetime | None = None

    async def get_all(self, timeout: float = 10.0) -> list[Position]:
        """
        Fetch all open positions from Gateway.

        Returns positions with:
        - Symbol and quantity
        - Entry price and current price
        - Unrealized P&L
        - Days to expiration
        - Strategy C flags (closure triggers)
        """
        try:
            # Fetch from Gateway
            ibkr_positions = await self._connection.get_positions(timeout=timeout)

            positions = []
            for ibkr_pos in ibkr_positions:
                position = await self._build_position(ibkr_pos, timeout)
                positions.append(position)
                self._positions_cache[position.position_id] = position

            self._last_sync = datetime.now(timezone.utc)

            # Sync with RiskManager
            await self._risk_manager.sync_positions(positions)

            return positions

        except TimeoutError:
            logger.error("Position fetch timeout")
            # Return cached positions if available
            if self._positions_cache:
                logger.warning("Returning cached positions")
                return list(self._positions_cache.values())
            raise

    async def _build_position(
        self,
        ibkr_pos: IBKRPosition,
        timeout: float
    ) -> Position:
        """Build Position with Strategy C closure flags."""
        # Calculate unrealized P&L
        current_price = await self._get_current_price(
            ibkr_pos.contract.symbol,
            timeout
        )
        entry_value = ibkr_pos.avgCost * ibkr_pos.position
        current_value = current_price * ibkr_pos.position
        unrealized_pnl = current_value - entry_value
        unrealized_pnl_pct = unrealized_pnl / entry_value if entry_value != 0 else 0

        # Calculate DTE for options
        dte = self._calculate_dte(ibkr_pos.contract)

        # Strategy C closure flags
        should_close_3_dte = dte is not None and dte <= 3
        should_close_emergency = unrealized_pnl_pct <= -0.40  # 40% loss

        return Position(
            position_id=f"{ibkr_pos.contract.symbol}_{ibkr_pos.contract.conId}",
            symbol=ibkr_pos.contract.symbol,
            quantity=int(ibkr_pos.position),
            entry_price=ibkr_pos.avgCost,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            days_to_expiry=dte,
            contract=ibkr_pos.contract,
            # Strategy C flags
            should_close_3_dte=should_close_3_dte,
            should_close_emergency=should_close_emergency,
            closure_trigger=self._determine_closure_trigger(
                should_close_3_dte,
                should_close_emergency
            )
        )

    def _calculate_dte(self, contract: Contract) -> int | None:
        """Calculate days to expiration for options."""
        if not hasattr(contract, 'lastTradeDateOrContractMonth'):
            return None  # Not an option

        expiry_str = contract.lastTradeDateOrContractMonth
        if not expiry_str:
            return None

        try:
            expiry_date = datetime.strptime(expiry_str, "%Y%m%d").date()
            today = datetime.now().date()
            return (expiry_date - today).days
        except ValueError:
            return None

    def _determine_closure_trigger(
        self,
        should_close_3_dte: bool,
        should_close_emergency: bool
    ) -> str | None:
        """Determine which Strategy C closure rule applies."""
        if should_close_emergency:
            return "EMERGENCY_STOP"  # 40% loss takes priority
        if should_close_3_dte:
            return "3_DTE_RULE"
        return None

    async def close(
        self,
        position_id: str,
        reason: str,
        timeout: float = 30.0
    ) -> OrderResult:
        """
        Close a specific position.

        Reasons (for audit trail):
        - "3_DTE_RULE": Strategy C force-close at 3 DTE
        - "EMERGENCY_STOP": 40% loss threshold
        - "DAILY_LOSS_LIMIT": Governor triggered
        - "MANUAL": Operator-initiated
        - "STRATEGY_EXIT": Normal exit signal
        """
        if position_id not in self._positions_cache:
            raise PositionNotFoundError(f"Position not found: {position_id}")

        position = self._positions_cache[position_id]

        logger.info(
            "Closing position",
            position_id=position_id,
            symbol=position.symbol,
            quantity=position.quantity,
            reason=reason,
            unrealized_pnl=position.unrealized_pnl
        )

        # Build closing order
        close_action = "SELL" if position.quantity > 0 else "BUY"
        close_quantity = abs(position.quantity)

        try:
            # Place closing order via Gateway
            ibkr_order = Order()
            ibkr_order.action = close_action
            ibkr_order.totalQuantity = close_quantity
            ibkr_order.orderType = "MKT"  # Market order for closures

            trade = await self._connection.place_order(
                contract=position.contract,
                order=ibkr_order,
                timeout=timeout
            )

            # Wait for fill
            fill_result = await self._wait_for_fill(trade, timeout)

            # Remove from cache
            del self._positions_cache[position_id]

            logger.info(
                "Position closed",
                position_id=position_id,
                reason=reason,
                fill_price=fill_result.avg_fill_price
            )

            return OrderResult(
                order_id=f"CLOSE_{position_id}",
                status=OrderStatus.FILLED if fill_result.filled else OrderStatus.PARTIAL,
                fill_price=fill_result.avg_fill_price,
                fill_quantity=fill_result.filled_quantity,
                timestamp=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error("Position close failed", position_id=position_id, error=str(e))
            return OrderResult(
                order_id=f"CLOSE_{position_id}",
                status=OrderStatus.FAILED,
                rejection_reason=str(e),
                timestamp=datetime.now(timezone.utc)
            )

    async def close_all(
        self,
        reason: str,
        timeout: float = 60.0
    ) -> list[OrderResult]:
        """
        Emergency close all positions (Strategy C liquidation).

        Used when:
        - Daily loss limit hit
        - Weekly drawdown governor triggered
        - Data quarantine (staleness)
        - Gateway disconnection recovery
        """
        logger.warning(
            "EMERGENCY LIQUIDATION",
            reason=reason,
            position_count=len(self._positions_cache)
        )

        results = []
        per_position_timeout = timeout / max(len(self._positions_cache), 1)

        for position_id in list(self._positions_cache.keys()):
            result = await self.close(
                position_id,
                reason=reason,
                timeout=per_position_timeout
            )
            results.append(result)

        return results

    async def check_strategy_c_closures(self) -> list[Position]:
        """
        Check for positions that should be closed per Strategy C rules.

        Returns list of positions triggering closure rules.
        Called periodically by orchestrator.
        """
        positions = await self.get_all()
        return [p for p in positions if p.closure_trigger is not None]

    async def _get_current_price(
        self,
        symbol: str,
        timeout: float
    ) -> float:
        """Get current price for P&L calculation."""
        # This would normally use MarketDataProvider
        # For position tracking, we can use last price from positions API
        # Simplified implementation
        return 0.0  # Placeholder — integrate with market data

    async def _wait_for_fill(
        self,
        trade: Trade,
        timeout: float
    ) -> FillResult:
        """Wait for closing order to fill."""
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            if trade.isDone():
                return FillResult(
                    filled=True,
                    avg_fill_price=trade.orderStatus.avgFillPrice,
                    filled_quantity=trade.orderStatus.filled
                )
            await asyncio.sleep(0.1)

        return FillResult(
            filled=False,
            avg_fill_price=trade.orderStatus.avgFillPrice,
            filled_quantity=trade.orderStatus.filled
        )


@dataclass
class Position:
    """Open position with Strategy C closure flags."""
    position_id: str
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    days_to_expiry: int | None
    contract: Contract

    # Strategy C closure flags
    should_close_3_dte: bool = False
    should_close_emergency: bool = False
    closure_trigger: str | None = None  # "3_DTE_RULE", "EMERGENCY_STOP", etc.
```

---

## 4. Dependencies

### 4.1 External Libraries

```toml
# pyproject.toml additions (if not already present)
[tool.poetry.dependencies]
ib_insync = "^0.9.86"      # IBKR API wrapper (already present)
numpy = "^1.26.0"          # Indicator calculations
structlog = "^24.1.0"      # Structured logging (already present)
```

### 4.2 Internal Dependencies

```python
# src/integrations/__init__.py
from src.integrations.ibkr_gateway import (
    IBKRGateway,
    GatewayConfig,
    ExecutionMode,
)
from src.integrations.market_data_pipeline import (
    MarketDataPipeline,
    MarketData,
    DataQuality,
)
from src.integrations.order_executor import (
    OrderExecutor,
    OrderResult,
    OrderStatus,
    TradeRequest,
)
from src.integrations.position_manager import (
    PositionManager,
    Position,
)

__all__ = [
    "IBKRGateway",
    "GatewayConfig",
    "ExecutionMode",
    "MarketDataPipeline",
    "MarketData",
    "DataQuality",
    "OrderExecutor",
    "OrderResult",
    "OrderStatus",
    "TradeRequest",
    "PositionManager",
    "Position",
]
```

### 4.3 Upstream Module Imports

```python
# Existing broker modules (Phase 1)
from src.broker.connection import IBKRConnection
from src.broker.contracts import ContractManager
from src.broker.market_data import MarketDataProvider
from src.broker.exceptions import (
    BrokerError,
    SnapshotModeViolationError,
    ContractQualificationError,
)

# Risk module (Task 2.5)
from src.risk.risk_manager import RiskManager, ValidationResult
```

---

## 5. Input/Output Contract

### 5.1 Configuration Input

```python
@dataclass
class GatewayConfig:
    """Gateway configuration."""
    host: str = "127.0.0.1"
    port: int = 4002  # 4002 = paper, 4001 = live
    client_id: int = 1
    timeout: float = 30.0

# Usage:
config = GatewayConfig.paper_trading()
# or
config = GatewayConfig(port=4002, timeout=45.0)
```

### 5.2 Market Data Output

```python
@dataclass
class MarketData:
    symbol: str
    timestamp: datetime  # UTC

    # Price data
    last_price: float
    bid: float
    ask: float
    volume: int

    # Indicators
    ema_fast: float       # 8-period
    ema_slow: float       # 21-period
    rsi: float            # 14-period
    vwap: float           # Session
    bollinger_upper: float
    bollinger_lower: float
    bollinger_middle: float

    # Quality flags
    is_stale: bool
    staleness_seconds: float
    missing_fields: list[str]
    data_quality_score: float  # 0.0-1.0
```

### 5.3 Order Input (TradingSignal)

```python
@dataclass
class TradingSignal:
    """Signal from strategy layer."""
    symbol: str
    action: str           # "BUY" or "SELL"
    quantity: int
    order_type: str       # "MKT", "LMT", etc.
    limit_price: float | None
    expiry: str           # "YYYYMMDD"
    strike: float
    right: str            # "C" or "P"
    signal_strength: float  # 0.0-1.0
    strategy_id: str
    timestamp: datetime
```

### 5.4 Order Output (OrderResult)

```python
@dataclass
class OrderResult:
    order_id: str
    status: OrderStatus   # FILLED, REJECTED, FAILED, SIMULATED, etc.
    timestamp: datetime

    # Execution details (if filled)
    ibkr_order_id: int | None
    fill_price: float | None
    fill_quantity: int | None

    # Rejection details (if rejected)
    rejection_reason: str | None

    # Metadata
    execution_mode: ExecutionMode | None
    risk_validation: ValidationResult | None
```

### 5.5 Position Output

```python
@dataclass
class Position:
    position_id: str
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    days_to_expiry: int | None
    contract: Contract

    # Strategy C flags
    should_close_3_dte: bool
    should_close_emergency: bool
    closure_trigger: str | None
```

---

## 6. Integration Points

### 6.1 Orchestrator Integration (Downstream — Task 2.8+)

```python
# Future orchestrator usage pattern
class TradingOrchestrator:
    def __init__(self, gateway: IBKRGateway, strategies: list[Strategy]):
        self.gateway = gateway
        self.strategies = strategies

    async def run_cycle(self):
        # 1. Fetch market data
        market_data = await self.gateway.get_market_data("SPY")

        # 2. Check data quality
        if market_data.is_stale:
            logger.warning("Stale data — activating Strategy C")
            await self.gateway.close_all_positions(reason="DATA_QUARANTINE")
            return

        # 3. Generate signals from strategies
        for strategy in self.strategies:
            signal = strategy.evaluate(market_data)
            if signal:
                # 4. Execute with risk validation
                result = await self.gateway.submit_order(signal, strategy.context)
                # Handle result...

        # 5. Check Strategy C closures
        positions = await self.gateway.get_positions()
        for pos in positions:
            if pos.closure_trigger:
                await self.gateway.close_position(
                    pos.position_id,
                    reason=pos.closure_trigger
                )
```

### 6.2 Strategy Layer Integration (Tasks 2.1-2.4)

```python
# Strategies receive MarketData, produce TradingSignal
class StrategyA:  # Momentum Breakout
    def evaluate(self, data: MarketData) -> TradingSignal | None:
        # Check EMA crossover
        if data.ema_fast > data.ema_slow:
            # Check RSI in range
            if 50 <= data.rsi <= 65:
                # Check VWAP condition
                if data.last_price > data.vwap:
                    return self._generate_buy_signal(data)
        return None
```

### 6.3 Risk Layer Integration (Task 2.5)

```python
# All orders flow through RiskManager
# RiskManager.validate_trade() checks:
# - Position sizing limits
# - PDT compliance
# - Daily loss limits
# - Weekly drawdown governor
# - Affordability (premium vs available capital)
```

### 6.4 Gameplan Integration (Task 2.7 — Future)

```python
# Gateway provides data for gameplan ingestion
@dataclass
class DailyGameplan:
    strategy: str  # "A", "B", or "C"
    symbols: list[str]
    vix_at_analysis: float
    key_levels: dict
    hard_limits: dict

# Orchestrator loads gameplan, configures gateway accordingly
```

---

## 7. Definition of Done

### 7.1 Code Quality Gates

- [ ] `ruff check src/integrations/ tests/integrations/` — 0 errors
- [ ] `black --check src/integrations/ tests/integrations/` — 0 changes needed
- [ ] `mypy src/integrations/` — 0 errors (strict mode)
- [ ] All existing tests pass: `pytest` — 0 failures

### 7.2 Test Coverage Gates

- [ ] Unit test coverage ≥85%: `pytest --cov=src/integrations --cov-fail-under=85`
- [ ] Alpha learning tests: 100% coverage of documented learnings
- [ ] Integration tests: End-to-end flow with mocked Gateway

### 7.3 Functional Validation

- [ ] **Dry-run validation:** Execute full cycle in dry-run mode
  ```bash
  python -m src.integrations.ibkr_gateway --mode=dry_run --symbol=SPY
  # Expected: Logs show simulated order flow, no actual execution
  ```

- [ ] **Paper trading validation:** (Requires running Gateway)
  ```bash
  python -m src.integrations.ibkr_gateway --mode=paper --symbol=SPY
  # Expected: Order appears in IBKR paper account
  ```

- [ ] **Risk validation enforcement:** Submit order exceeding limits
  ```python
  # Expected: OrderResult.status == REJECTED
  # Expected: OrderResult.rejection_reason contains limit description
  ```

### 7.4 Alpha Learning Regression Tests

- [ ] **snapshot=True enforcement test:**
  ```python
  def test_snapshot_mode_enforced():
      # Attempt to request data without snapshot
      # Expected: SnapshotModeViolationError raised
  ```

- [ ] **Historical data limit test:**
  ```python
  def test_historical_data_1_hour_limit():
      # Request 2 hours of data
      # Expected: AlphaLearningViolationError raised
  ```

- [ ] **Timeout propagation test:**
  ```python
  def test_timeout_propagation():
      # Request with 5s timeout
      # Verify timeout reaches all layers
      # Expected: TimeoutError after 5s, not hang
  ```

- [ ] **Contract qualification test:**
  ```python
  def test_contract_qualification_required():
      # Attempt order without qualification
      # Expected: ContractQualificationError raised
  ```

- [ ] **Operator ID compliance test:**
  ```python
  def test_operator_id_on_all_orders():
      # Submit order
      # Verify operator_id == "CSATSPRIM" in request
  ```

### 7.5 Documentation

- [ ] Module docstrings complete
- [ ] All public methods have docstrings
- [ ] Alpha learning enforcement documented inline
- [ ] README section for integration layer usage

---

## 8. Edge Cases to Test

### 8.1 Connection Failures

| Scenario | Expected Behavior | Test Method |
|----------|------------------|-------------|
| Gateway not running | `GatewayConnectionError` with clear message | Mock connection failure |
| Gateway disconnects mid-operation | Graceful reconnect attempt, then error | Mock disconnect during request |
| Network timeout | `TimeoutError` after configured timeout | Mock slow response |
| Invalid credentials | `GatewayAuthenticationError` | Mock auth failure |

### 8.2 Data Quality Issues

| Scenario | Expected Behavior | Test Method |
|----------|------------------|-------------|
| Stale data (>5 min old) | `MarketData.is_stale = True` | Mock old timestamp |
| Missing bid/ask | `MarketData.missing_fields = ["bid", "ask"]` | Mock zero values |
| Insufficient bars for indicators | `InsufficientDataError` raised | Mock <21 bars |
| NaN in calculated indicators | Flagged in `missing_fields` | Mock edge case prices |

### 8.3 Order Execution Failures

| Scenario | Expected Behavior | Test Method |
|----------|------------------|-------------|
| RiskManager rejects order | `OrderResult.status = REJECTED` | Configure risk limits to reject |
| Contract qualification fails | `OrderResult.status = FAILED` | Mock qualification error |
| Order timeout (no fill) | `OrderResult.status = TIMEOUT` | Mock slow fill |
| Partial fill | `OrderResult.status = PARTIAL` | Mock partial fill |
| Broker rejects order | `OrderResult.status = FAILED` | Mock broker rejection |

### 8.4 Position Management Edge Cases

| Scenario | Expected Behavior | Test Method |
|----------|------------------|-------------|
| No open positions | Empty list returned | Mock empty response |
| Position not found for close | `PositionNotFoundError` | Invalid position_id |
| Close order fails | `OrderResult.status = FAILED` | Mock close failure |
| Multiple positions to close | All attempted, results collected | Mock multiple positions |
| Option expires today (0 DTE) | `closure_trigger = "3_DTE_RULE"` | Mock 0 DTE position |

### 8.5 Alpha Learning Violations

| Scenario | Expected Behavior | Test Method |
|----------|------------------|-------------|
| Request without `snapshot=True` | `SnapshotModeViolationError` | Bypass wrapper |
| Historical data >1 hour | `AlphaLearningViolationError` | Request 120 minutes |
| Unqualified contract in order | `ContractQualificationError` | Skip qualification |
| Missing operator ID | Never happens (enforced in constructor) | Constructor validation test |

---

## 9. Rollback Plan

### 9.1 Feature Toggle

```python
# src/integrations/feature_flags.py
class IntegrationFeatureFlags:
    """Feature flags for gradual rollout."""

    ENABLE_INTEGRATION_LAYER = True  # Master switch
    ENABLE_PAPER_EXECUTION = True    # Paper trading
    ENABLE_LIVE_EXECUTION = False    # BLOCKED until Phase 4

    # Fallback modes
    FALLBACK_TO_DIRECT_BROKER = False  # Use broker modules directly
```

### 9.2 Rollback Steps

1. **Immediate rollback:** Set `ENABLE_INTEGRATION_LAYER = False`
2. **Orchestrator fallback:** Import broker modules directly (pre-Task 2.6 pattern)
3. **No data migration needed:** Integration layer is stateless
4. **Test rollback:** Run existing broker tests to verify unchanged behavior

### 9.3 Rollback Triggers

- Integration layer introduces regression in broker behavior
- Performance degradation (>2x latency increase)
- Alpha learning violation detected in production
- Risk validation bypass discovered

---

## 10. Implementation Guidance

### 10.1 Recommended Implementation Order

1. **Create directory structure:**
   ```bash
   mkdir -p src/integrations tests/integrations tests/integration
   touch src/integrations/__init__.py tests/integrations/__init__.py
   ```

2. **Implement MarketDataPipeline first:**
   - Simplest component
   - Tests can run without Gateway mock
   - Indicator calculations are pure functions

3. **Implement OrderExecutor second:**
   - Depends on RiskManager (already complete)
   - Dry-run mode works without Gateway
   - Test with mock RiskManager

4. **Implement PositionManager third:**
   - Depends on connection mock
   - Strategy C logic is critical path

5. **Implement IBKRGateway last:**
   - Orchestrates all components
   - Integration tests verify end-to-end

6. **Run alpha learning regression tests:**
   - Must pass before merge

### 10.2 Testing Strategy

```python
# tests/integrations/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_connection():
    """Mock IBKRConnection for unit tests."""
    conn = MagicMock()
    conn.connect = AsyncMock(return_value=True)
    conn.disconnect = AsyncMock()
    conn.health_check = AsyncMock(return_value=MagicMock(market_data_available=True))
    conn.get_positions = AsyncMock(return_value=[])
    conn.place_order = AsyncMock()
    return conn

@pytest.fixture
def mock_market_data_provider():
    """Mock MarketDataProvider with snapshot=True enforcement."""
    provider = MagicMock()
    provider.get_quote = AsyncMock(return_value=MagicMock(
        last=100.0,
        bid=99.95,
        ask=100.05,
        volume=1000000,
        timestamp=datetime.now(timezone.utc)
    ))
    provider.get_historical_bars = AsyncMock(return_value=[
        MagicMock(close=100.0 + i*0.1, high=100.5 + i*0.1, low=99.5 + i*0.1, volume=10000)
        for i in range(60)
    ])
    return provider

@pytest.fixture
def mock_risk_manager():
    """Mock RiskManager that approves all trades."""
    rm = MagicMock()
    rm.validate_trade = AsyncMock(return_value=MagicMock(
        approved=True,
        rejection_reasons=[],
        risk_metrics={}
    ))
    rm.sync_positions = AsyncMock()
    return rm

@pytest.fixture
def rejecting_risk_manager():
    """Mock RiskManager that rejects all trades."""
    rm = MagicMock()
    rm.validate_trade = AsyncMock(return_value=MagicMock(
        approved=False,
        rejection_reasons=["PDT limit exceeded", "Position size too large"],
        risk_metrics={}
    ))
    return rm
```

### 10.3 Copilot Prompts for Implementation

**Prompt 1: MarketDataPipeline**
```
Implement src/integrations/market_data_pipeline.py following the VSC Handoff:
- MarketData dataclass with all fields
- MarketDataPipeline class with fetch_market_data and indicator calculations
- EMA, RSI, VWAP, Bollinger Band calculations using numpy
- Data quality validation (staleness, missing fields)
- All methods accept timeout parameter
- Type hints throughout
```

**Prompt 2: OrderExecutor**
```
Implement src/integrations/order_executor.py following the VSC Handoff:
- OrderExecutor class with mandatory RiskManager validation
- TradeRequest and OrderResult dataclasses
- Dry-run execution mode (logging only)
- Paper execution mode (via connection)
- Operator ID enforcement on all orders
- No bypass path for risk validation
```

**Prompt 3: PositionManager**
```
Implement src/integrations/position_manager.py following the VSC Handoff:
- PositionManager class with get_all, close, close_all
- Position dataclass with Strategy C flags
- 3 DTE closure rule
- 40% emergency stop rule
- Closure reason tracking for audit
```

**Prompt 4: IBKRGateway**
```
Implement src/integrations/ibkr_gateway.py following the VSC Handoff:
- IBKRGateway class orchestrating all components
- ExecutionMode enum (DRY_RUN, PAPER, LIVE-blocked)
- GatewayConfig dataclass
- Live mode blocked with explicit error
- Connection management with health checks
- All alpha learnings enforced at integration boundary
```

**Prompt 5: Alpha Learning Tests**
```
Implement tests/integrations/test_alpha_learnings.py:
- test_snapshot_mode_enforced: Verify snapshot=True required
- test_historical_data_1_hour_limit: Verify >60 min rejected
- test_timeout_propagation: Verify timeout flows through stack
- test_contract_qualification_required: Verify qualification enforced
- test_operator_id_compliance: Verify CSATSPRIM on all orders
- Each test must assert the specific alpha learning violation
```

---

## 11. Alpha Learnings Enforcement Checklist

This checklist must be verified before Task 2.6 can be marked complete.

### 11.1 snapshot=True (CRITICAL)

- [ ] `MarketDataProvider` initialized with `snapshot=True` in `IBKRGateway.__init__`
- [ ] Defense-in-depth: `snapshot=True` passed explicitly in `MarketDataPipeline.fetch_market_data`
- [ ] Test exists: `test_snapshot_mode_enforced` verifies violation raises error
- [ ] No code path exists where `snapshot=False` could be passed

### 11.2 Historical Data Limits

- [ ] `IBKRGateway.get_historical_data` validates `duration_minutes <= 60`
- [ ] `AlphaLearningViolationError` raised for violations
- [ ] Test exists: `test_historical_data_1_hour_limit` verifies rejection
- [ ] RTH-only enforced in `MarketDataPipeline.fetch_market_data`

### 11.3 Timeout Propagation

- [ ] All public methods accept `timeout: float` parameter
- [ ] Timeout propagates to all internal calls
- [ ] `TimeoutError` raised on expiration (no silent hangs)
- [ ] Test exists: `test_timeout_propagation` verifies timeout flows through

### 11.4 Contract Qualification

- [ ] `OrderExecutor._execute_paper` calls `ContractManager.qualify_option_contract`
- [ ] `ContractQualificationError` raised on failure
- [ ] Test exists: `test_contract_qualification_required`
- [ ] No order can be placed with unqualified contract

### 11.5 Operator ID Compliance

- [ ] `IBKRGateway.__init__` accepts `operator_id` parameter (default: "CSATSPRIM")
- [ ] `OrderExecutor` attaches `operator_id` to all `TradeRequest` objects
- [ ] `_build_ibkr_order` sets `order.account = operator_id`
- [ ] Test exists: `test_operator_id_compliance` verifies attachment

### 11.6 Memory/Resource Awareness

- [ ] No persistent subscriptions created (snapshot mode prevents this)
- [ ] Connection cleanup in `IBKRGateway.disconnect`
- [ ] Position cache cleared on disconnect
- [ ] Logging includes memory-relevant context for debugging

---

## 12. CRO Safety Review Sign-Off

**@CRO Review Required Before Merge**

The following safety properties must be verified:

| Property | Verification Method | Status |
|----------|-------------------|--------|
| No order bypasses RiskManager | Code review of OrderExecutor | ⬜ Pending |
| Live mode blocked | Unit test for ExecutionMode.LIVE rejection | ⬜ Pending |
| Strategy C closure logic correct | Unit tests for 3 DTE and 40% rules | ⬜ Pending |
| Data staleness triggers Strategy C | Unit test for staleness handling | ⬜ Pending |
| All alpha learnings enforced | Alpha learning test suite passes | ⬜ Pending |
| Operator ID on all orders | Unit test for CSATSPRIM attachment | ⬜ Pending |
| Graceful degradation on failure | Error handling code review | ⬜ Pending |

**CRO Sign-Off:** ⬜ Pending implementation and test results

---

## 13. Session Handoff Summary

### What Was Accomplished
- Complete VSC Handoff Document for Task 2.6: IBKR Gateway Integration Layer
- Detailed pseudo-code for all 4 components (IBKRGateway, MarketDataPipeline, OrderExecutor, PositionManager)
- Alpha learnings enforcement checklist with specific test requirements
- Integration points documented for orchestrator, strategies, and risk layer
- CRO safety review checklist prepared

### What Remains
- Factory Floor implementation (VSCode + Copilot)
- Unit test implementation (85% coverage target)
- Alpha learning regression test suite
- CRO safety review sign-off
- Paper trading validation (requires running Gateway)

### Recommended Next Steps
1. Start new VSCode session for implementation
2. Create directory structure first
3. Implement in order: Pipeline → Executor → PositionManager → Gateway
4. Run tests after each component
5. Final alpha learning regression suite
6. CRO review before merge

### Context for Next Session
- Task 2.6 blueprint complete
- Upstream: Task 2.5 (RiskManager) available for import
- Downstream: Task 2.7 blocked until 2.6 complete
- Model routing: Sonnet sufficient for implementation (blueprint provides all design decisions)

---

*Document generated: 2026-02-09*
*Lead Persona: @Systems_Architect*
*Supporting: @CRO (safety review), @QA_Lead (test specifications)*
*Delivery: Protocol C compliant — file-first, no inline content*
