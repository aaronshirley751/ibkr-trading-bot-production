"""
Trading loop — Market Data → Signal → Risk → Order execution pipeline.

Implements the full gate-aware evaluation cycle that connects every upstream
Phase 2 module (strategies, risk engine, broker layer) into a single runnable
loop.

Pipeline (per symbol, per evaluation cycle):
    1. Entry-window gate                           — time-of-day check
    2. Fetch historical bars + live quote          — MarketDataProvider
    3. Compute indicators & build MarketData       — indicators.build_market_data()
    4. Evaluate strategy signal                    — StrategyA / StrategyB
    5. Confidence gate                             — signal.passes_confidence_gate
    6. Affordability gate                          — AffordabilityGate
    7. Risk engine pre-trade check                 — RiskEngine.pre_trade_check()
    8. Order submission (or dry-run log)           — OrderManager.submit_order()
    9. Record decision                             — TradeLog

Safety:
  - Strategy C bypasses all gates and never enters the pipeline (monitoring only).
  - VIX gate failure overrides to Strategy C for the entire session.
  - If market_data_provider / contract_manager / risk_engine are absent, the loop
    falls back to monitoring-only mode and emits a warning each cycle.
  - dry_run=True (default) prevents any order from reaching the broker.
  - Every recoverable error is caught, logged, and recorded; the loop
    continues to the next symbol / the next cycle.

Lifecycle:
    1. __init__: Validate config, instantiate strategy objects, init trade log.
    2. run(): Log startup, check VIX gate, enter evaluation or monitoring loop.
    3. _run_evaluation_loop(): Entry-window gate → _execute_pipeline_for_symbol().
    4. stop(): Set _running=False for clean shutdown.
"""

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.bot.gates import (
    AffordabilityGate,
    EntryWindowGate,
    VIXConfirmationGate,
)
from src.bot.indicators import build_market_data
from src.bot.position_monitor import ExitSignal, OpenPosition, PositionMonitor
from src.bot.trade_log import TradeDecision, TradeLog
from src.broker.contracts import ContractManager
from src.broker.exceptions import MarketDataError, StaleDataError
from src.broker.market_data import MarketDataProvider
from src.bot.execution.order_manager import OrderManager, OrderParams
from src.config.risk_config import RiskConfig
from src.notifications.discord import DiscordNotifier
from src.risk.engine import RiskEngine
from src.strategies.base import Direction, MarketData, Signal
from src.strategies.strategy_a import StrategyA
from src.strategies.strategy_b import StrategyB
from src.utils.gateway_health import GatewayHealthChecker

logger = logging.getLogger(__name__)


class TradingLoop:
    """
    Gate-aware trading loop that connects the full Strategy A/B execution
    pipeline.

    The constructor accepts optional execution dependencies so that the existing
    main.py / test harness can construct the loop in monitoring-only mode while
    the full pipeline activates automatically when all providers are supplied.

    Attributes:
        EVAL_INTERVAL: Seconds between evaluation cycles (default 30).
        HEALTH_CHECK_INTERVAL: Seconds between periodic Gateway health checks
            (default 300).
    """

    EVAL_INTERVAL: int = 30
    HEALTH_CHECK_INTERVAL: int = 300

    def __init__(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        health_checker: GatewayHealthChecker,
        discord_notifier: Optional[DiscordNotifier] = None,
        # --- Execution pipeline dependencies (all optional) ---
        market_data_provider: Optional[MarketDataProvider] = None,
        contract_manager: Optional[ContractManager] = None,
        risk_engine: Optional[RiskEngine] = None,
        order_manager: Optional[OrderManager] = None,
        dry_run: bool = True,
        log_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize the trading loop.

        Args:
            gameplan: Daily gameplan dictionary loaded from JSON.
            risk_config: Immutable risk parameters from RiskConfig.
            health_checker: GatewayHealthChecker for periodic Gateway checks.
            discord_notifier: Optional Discord notification sender.
            market_data_provider: Provides live quotes and historical bars.
                If None the loop runs in monitoring-only mode.
            contract_manager: Qualifies IB contracts before data requests.
                Required when market_data_provider is supplied.
            risk_engine: Central risk engine for pre-trade checks.
                Required when market_data_provider is supplied.
            order_manager: Broker order submission layer.
                Required when market_data_provider is supplied and dry_run=False.
            dry_run: When True (default) pipeline decisions are logged but no
                orders are sent to the broker.
            log_dir: Directory for trade log files (default: Path("logs")).
        """
        self.gameplan = gameplan
        self.risk_config = risk_config
        self.health_checker = health_checker
        self.discord = discord_notifier

        # Execution pipeline
        self._market_data_provider = market_data_provider
        self._contract_manager = contract_manager
        self._risk_engine = risk_engine
        self._order_manager = order_manager
        self._dry_run = dry_run

        # Gameplan fields
        self.strategy = gameplan.get("strategy", "C")
        self.symbols: List[str] = gameplan.get("symbols", [])

        # Pre-trade gates
        self.vix_gate = VIXConfirmationGate()
        self.affordability_gate = AffordabilityGate(default_max_risk=risk_config.max_risk_per_trade)
        self.entry_window_gate = EntryWindowGate()

        # Strategy instances (created once to preserve EMA crossover state)
        self._strategy_a = StrategyA()
        self._strategy_b = StrategyB()

        # Trade log
        resolved_log_dir = log_dir or Path(os.getenv("LOG_DIR", "logs"))
        self._trade_log = TradeLog(resolved_log_dir)

        # Position monitor (created internally — always available)
        self._position_monitor = PositionMonitor()

        # Session state
        self._vix_checked = False
        self._strategy_overridden = False
        self._running = False
        self._eval_cycle_count = 0
        self._session_exits: List[Dict[str, Any]] = []

    # =========================================================================
    # Public API
    # =========================================================================

    def run(self) -> None:
        """
        Execute the main trading loop.

        Runs synchronously until stop() is called or a KeyboardInterrupt is
        raised.  An end-of-session Discord summary is always posted on exit,
        regardless of how the loop terminates.
        """
        self._running = True
        self._log_startup()

        try:
            if self.strategy == "C":
                self._run_strategy_c_loop()
                return

            if not self._check_vix_gate():
                self._run_strategy_c_loop()
                return

            self._run_evaluation_loop()
        finally:
            self._post_session_summary()

    def stop(self) -> None:
        """Request a graceful loop shutdown."""
        self._running = False
        logger.info("Trading loop stop requested")

    # =========================================================================
    # Startup / logging helpers
    # =========================================================================

    def _log_startup(self) -> None:
        """Log session parameters and send Discord notification."""
        logger.info("=" * 60)
        logger.info("Trading Loop Started")
        logger.info("Strategy: %s", self.strategy)
        logger.info("Symbols: %s", self.symbols)
        logger.info(
            "Position size multiplier: %s",
            self.gameplan.get("position_size_multiplier", "N/A"),
        )
        logger.info("Regime: %s", self.gameplan.get("regime", "unknown"))
        logger.info("Bias: %s", self.gameplan.get("bias", "N/A"))

        entry_start = self.gameplan.get("entry_window_start", "09:30")
        entry_end = self.gameplan.get("entry_window_end", "16:00")
        logger.info("Entry window: %s - %s ET", entry_start, entry_end)

        vix_gate = self.gameplan.get("vix_gate")
        if vix_gate:
            logger.info(
                "VIX gate: threshold=%.1f, check_time=%s",
                vix_gate.get("threshold", 0),
                vix_gate.get("check_time", "N/A"),
            )

        max_risk = self.gameplan.get("max_risk_per_trade", "N/A")
        ceiling = self.gameplan.get("max_risk_ceiling", "N/A")
        logger.info("Risk per trade: $%s (ceiling: $%s)", max_risk, ceiling)

        pipeline_mode = "FULL PIPELINE" if self._pipeline_ready() else "MONITORING-ONLY"
        dry_label = " [DRY-RUN]" if self._dry_run else " [LIVE]"
        logger.info("Execution mode: %s%s", pipeline_mode, dry_label)
        logger.info("=" * 60)

        if self.discord:
            self.discord.send_info(
                f"Trading loop started — Strategy {self.strategy}\n"
                f"Symbols: {', '.join(self.symbols)}\n"
                f"Entry window: {entry_start}-{entry_end} ET\n"
                f"Regime: {self.gameplan.get('regime', 'unknown')}\n"
                f"Mode: {pipeline_mode}{dry_label}"
            )

    def _check_vix_gate(self) -> bool:
        """
        Run VIX confirmation gate.

        Returns:
            True if gate passes (strategy unchanged), False if overriding to C.
        """
        result = self.vix_gate.evaluate(self.gameplan)
        self._vix_checked = True

        if not result.passed:
            logger.warning("VIX gate failed — overriding to Strategy C: %s", result.reason)
            self.strategy = "C"
            self._strategy_overridden = True
            if self.discord:
                self.discord.send_warning(f"VIX gate override to Strategy C: {result.reason}")
            return False

        logger.info("VIX gate passed: %s", result.reason)
        return True

    # =========================================================================
    # Loop bodies
    # =========================================================================

    def _run_strategy_c_loop(self) -> None:
        """Strategy C — cash preservation. Position monitoring + health checks only."""
        if self._strategy_overridden:
            logger.info("Strategy C active (VIX gate override) — monitoring only")
        else:
            logger.info("Strategy C active — cash preservation, monitoring only")

        last_health_check = 0.0
        while self._running:
            try:
                now = time.monotonic()
                if now - last_health_check >= self.HEALTH_CHECK_INTERVAL:
                    self._periodic_health_check()
                    last_health_check = now
                # Strategy C still monitors residual positions for DTE force-close
                self._monitor_open_positions()
                time.sleep(min(60, self.HEALTH_CHECK_INTERVAL))
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                raise

    def _run_evaluation_loop(self) -> None:
        """
        Strategy A/B evaluation cycle.

        Each cycle:
          1. Periodic Gateway health check.
          2. Entry-window gate.
          3. Full execution pipeline for each symbol.
          4. Sleep EVAL_INTERVAL.
        """
        logger.info("Entering Strategy %s evaluation cycle", self.strategy)

        last_health_check = 0.0

        while self._running:
            try:
                now = time.monotonic()

                # Periodic health check
                if now - last_health_check >= self.HEALTH_CHECK_INTERVAL:
                    self._periodic_health_check()
                    last_health_check = now

                # Monitor open positions each cycle (exit conditions run regardless
                # of the entry window — we must exit positions even outside entry hours)
                self._monitor_open_positions()

                # Emergency halt check — triggers Strategy C override and breaks loop
                if self._check_emergency_halt():
                    break

                # Gate 1: Entry-window check
                window_result = self.entry_window_gate.evaluate(self.gameplan)
                if not window_result.passed:
                    logger.debug("Entry window closed: %s", window_result.reason)
                    time.sleep(self.EVAL_INTERVAL)
                    continue

                # Guard: without providers, downgrade to monitoring-only each cycle
                if not self._pipeline_ready():
                    logger.warning(
                        "Pipeline dependencies unavailable — monitoring-only this cycle. "
                        "Provide market_data_provider, contract_manager, and risk_engine "
                        "to enable full execution."
                    )
                    time.sleep(self.EVAL_INTERVAL)
                    continue

                # Full pipeline for each symbol
                for symbol in self.symbols:
                    self._execute_pipeline_for_symbol(symbol)

                time.sleep(self.EVAL_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                raise

    # =========================================================================
    # Execution pipeline
    # =========================================================================

    def _pipeline_ready(self) -> bool:
        """Return True when all required execution dependencies are present."""
        return (
            self._market_data_provider is not None
            and self._contract_manager is not None
            and self._risk_engine is not None
        )

    def _execute_pipeline_for_symbol(self, symbol: str) -> None:
        """
        Run the full Market Data → Signal → Risk → Order pipeline for one symbol.

        All recoverable errors are caught and recorded so that a failure for
        one symbol never blocks evaluation of subsequent symbols.

        Args:
            symbol: Ticker symbol to evaluate (e.g. "QQQ").
        """
        self._eval_cycle_count += 1
        cycle = self._eval_cycle_count

        # --- Step 1: Fetch market data and compute indicators ---
        try:
            assert self._market_data_provider is not None  # guaranteed by _pipeline_ready
            assert self._contract_manager is not None
            market_data = self._fetch_and_build_market_data(symbol)
        except (StaleDataError, MarketDataError) as exc:
            logger.warning("Market data issue for %s: %s — skipping cycle", symbol, exc)
            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=None,
                    outcome="error",
                    signal_direction="hold",
                    signal_confidence=0.0,
                    signal_rationale=f"market_data_error: {exc}",
                )
            )
            return
        except Exception as exc:
            logger.error(
                "Unexpected error fetching market data for %s: %s",
                symbol,
                exc,
                exc_info=True,
            )
            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=None,
                    outcome="error",
                    signal_direction="hold",
                    signal_confidence=0.0,
                    signal_rationale=f"unexpected_error: {type(exc).__name__}: {exc}",
                )
            )
            return

        if market_data is None:
            logger.warning("No usable market data for %s — skipping cycle", symbol)
            return

        # --- Step 2: Strategy signal evaluation ---
        try:
            active_strategy = self._strategy_a if self.strategy == "A" else self._strategy_b
            signal: Signal = active_strategy.evaluate(market_data)
        except Exception as exc:
            logger.error("Strategy evaluation error for %s: %s", symbol, exc, exc_info=True)
            return

        logger.info(
            "[%s] Signal: direction=%s confidence=%.2f — %s",
            symbol,
            signal.direction.value,
            signal.confidence,
            signal.rationale,
        )

        # --- Step 3: HOLD or inactionable signal — exit early ---
        if not signal.is_actionable:
            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=signal,
                    outcome="hold",
                )
            )
            return

        # --- Step 4: Confidence gate ---
        if not signal.passes_confidence_gate:
            logger.info(
                "[%s] Confidence %.2f < 0.5 — rejected_confidence", symbol, signal.confidence
            )
            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=signal,
                    outcome="rejected_confidence",
                )
            )
            return

        # --- Step 5: Affordability gate ---
        # Use ask price as proxy for option premium
        premium = market_data.ask
        affordability = self.affordability_gate.evaluate(premium, self.gameplan)

        if not affordability.passed:
            logger.info("[%s] Affordability gate blocked: %s", symbol, affordability.reason)
            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=signal,
                    outcome="rejected_affordability",
                    affordability_passed=False,
                    affordability_reason=affordability.reason,
                )
            )
            return

        # --- Step 6: Compute position size and risk engine check ---
        action = "BUY" if signal.direction == Direction.BUY else "SELL"
        stop_loss_pct = self._get_stop_loss_pct()
        quantity = self._compute_quantity(premium)

        assert self._risk_engine is not None  # guaranteed by _pipeline_ready
        risk_result = self._risk_engine.pre_trade_check(
            symbol=symbol,
            action=action,
            premium=premium,
            stop_loss_pct=stop_loss_pct,
            quantity=quantity,
        )

        if not risk_result["approved"]:
            logger.warning(
                "[%s] Risk engine rejected: %s", symbol, risk_result["rejection_reasons"]
            )
            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=signal,
                    outcome="rejected_risk",
                    affordability_passed=True,
                    affordability_reason=affordability.reason,
                    reduce_size=affordability.reduce_size,
                    risk_approved=False,
                    risk_rejections=risk_result["rejection_reasons"],
                    premium_used=premium,
                    quantity=quantity,
                )
            )
            return

        # --- Step 7: Submit order (or dry-run) ---
        if self._dry_run:
            logger.info(
                "[%s] [DRY-RUN] Would submit %s x%d @ premium=%.4f stop_loss=%.0f%%",
                symbol,
                action,
                quantity,
                premium,
                stop_loss_pct * 100,
            )
            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=signal,
                    outcome="dry_run",
                    affordability_passed=True,
                    affordability_reason=affordability.reason,
                    reduce_size=affordability.reduce_size,
                    risk_approved=True,
                    premium_used=premium,
                    quantity=quantity,
                )
            )
            return

        # Live order path
        if self._order_manager is None:
            logger.error(
                "[%s] Cannot submit live order: order_manager not provided. "
                "Set dry_run=True or supply an OrderManager.",
                symbol,
            )
            return

        try:
            assert self._contract_manager is not None
            contract = self._contract_manager.qualify_contract(symbol)
            order_id = self._order_manager.submit_order(
                contract, OrderParams(action=action, quantity=quantity, order_type="MKT")
            )
            logger.info(
                "[%s] Order submitted: order_id=%d %s x%d @ premium=%.4f",
                symbol,
                order_id,
                action,
                quantity,
                premium,
            )

            # Record PDT day trade
            self._risk_engine.record_day_trades(1)

            # Register position for monitoring (exit conditions evaluated each cycle)
            exit_params = self._get_exit_params()
            self._position_monitor.add_position(
                OpenPosition(
                    symbol=symbol,
                    entry_price=premium,
                    entry_time=datetime.now(timezone.utc),
                    quantity=quantity,
                    order_id=order_id,
                    take_profit_pct=exit_params["take_profit_pct"],
                    stop_loss_pct=exit_params["stop_loss_pct"],
                    time_stop_minutes=exit_params["time_stop_minutes"],
                    force_close_dte=exit_params["force_close_dte"],
                )
            )

            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=signal,
                    outcome="submitted",
                    affordability_passed=True,
                    affordability_reason=affordability.reason,
                    reduce_size=affordability.reduce_size,
                    risk_approved=True,
                    order_id=order_id,
                    premium_used=premium,
                    quantity=quantity,
                )
            )

            if self.discord:
                self.discord.send_info(
                    f"Order submitted — {action} {symbol} x{quantity} @ ${premium:.4f}\n"
                    f"Strategy {self.strategy} | cycle #{cycle} | order_id={order_id}"
                )

        except Exception as exc:
            logger.error("[%s] Order submission failed: %s", symbol, exc, exc_info=True)
            self._record(
                self._make_decision(
                    symbol=symbol,
                    cycle=cycle,
                    signal=signal,
                    outcome="error",
                    affordability_passed=True,
                    affordability_reason=affordability.reason,
                    risk_approved=True,
                    signal_rationale=f"order_error: {exc}",
                    premium_used=premium,
                    quantity=quantity,
                )
            )

    # =========================================================================
    # Market data helpers
    # =========================================================================

    def _fetch_and_build_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Qualify the contract, fetch historical bars and live quote, and build
        a MarketData instance with computed technical indicators.

        Args:
            symbol: Ticker symbol.

        Returns:
            Populated MarketData, or None if quote data is unusable.

        Raises:
            StaleDataError: Propagated from MarketDataProvider.
            MarketDataError: Propagated from MarketDataProvider.
        """
        assert self._contract_manager is not None
        assert self._market_data_provider is not None

        contract = self._contract_manager.qualify_contract(symbol)

        # Historical bars for indicator computation (1-hour RTH window)
        bars = self._market_data_provider.request_historical_data(
            contract,
            duration="3600 S",
            bar_size="5 mins",
            use_rth=True,
        )

        # Live snapshot quote
        quote = self._market_data_provider.request_market_data(contract)

        return build_market_data(symbol, quote, bars)

    # =========================================================================
    # Position sizing helpers
    # =========================================================================

    def _get_stop_loss_pct(self) -> float:
        """Return strategy-appropriate stop-loss as a decimal (e.g. 0.25)."""
        if self.strategy == "A":
            return float(self.risk_config.stop_loss_pct_strategy_a)
        if self.strategy == "B":
            return float(self.risk_config.stop_loss_pct_strategy_b)
        return 0.25  # safe default

    def _compute_quantity(self, premium: float) -> int:
        """
        Calculate the number of contracts within the max-risk budget.

        Risk formula: stop_loss_pct * premium_per_share * 100 * qty <= max_risk
        Minimum quantity: 1 contract.

        Args:
            premium: Per-share option premium (ask price).

        Returns:
            Number of contracts to trade (>= 1).
        """
        max_risk = float(
            self.gameplan.get("max_risk_per_trade", float(self.risk_config.max_risk_per_trade))
        )
        stop_loss_pct = self._get_stop_loss_pct()

        if premium <= 0 or stop_loss_pct <= 0:
            return 1

        # Each contract is 100 shares; solve for qty
        max_qty = max_risk / (premium * 100.0 * stop_loss_pct)
        return max(1, int(max_qty))

    # =========================================================================
    # Health check
    # =========================================================================

    def _periodic_health_check(self) -> None:
        """Run a lightweight Gateway health check."""
        try:
            is_healthy = self.health_checker.check_port(timeout=10.0)
            if is_healthy:
                logger.debug("Gateway health check passed")
            else:
                logger.warning("Gateway health check FAILED")
                if self.discord:
                    self.discord.send_warning("Gateway health check failed during trading loop")
        except Exception as exc:
            logger.error("Health check error: %s", exc)

    # =========================================================================
    # Trade log helpers
    # =========================================================================

    def _make_decision(
        self,
        *,
        symbol: str,
        cycle: int,
        signal: Optional[Signal],
        outcome: str,
        signal_direction: Optional[str] = None,
        signal_confidence: Optional[float] = None,
        signal_rationale: Optional[str] = None,
        affordability_passed: Optional[bool] = None,
        affordability_reason: Optional[str] = None,
        reduce_size: bool = False,
        risk_approved: Optional[bool] = None,
        risk_rejections: Optional[List[str]] = None,
        order_id: Optional[int] = None,
        premium_used: Optional[float] = None,
        quantity: Optional[int] = None,
    ) -> TradeDecision:
        """Construct a TradeDecision from pipeline state."""
        return TradeDecision(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            strategy=self.strategy,
            cycle_count=cycle,
            signal_direction=(
                signal.direction.value if signal is not None else (signal_direction or "hold")
            ),
            signal_confidence=(
                signal.confidence if signal is not None else (signal_confidence or 0.0)
            ),
            signal_rationale=(signal.rationale if signal is not None else (signal_rationale or "")),
            signal_metadata=signal.metadata if signal is not None else {},
            affordability_passed=affordability_passed,
            affordability_reason=affordability_reason,
            reduce_size=reduce_size,
            risk_approved=risk_approved,
            risk_rejections=risk_rejections or [],
            outcome=outcome,
            order_id=order_id,
            premium_used=premium_used,
            quantity=quantity,
        )

    def _record(self, decision: TradeDecision) -> None:
        """Write decision to trade log and emit structured log line."""
        logger.info(
            "DECISION cycle=%d symbol=%s outcome=%s direction=%s confidence=%.2f",
            decision.cycle_count,
            decision.symbol,
            decision.outcome,
            decision.signal_direction,
            decision.signal_confidence,
        )
        self._trade_log.record(decision)

    # =========================================================================
    # Position monitoring
    # =========================================================================

    def _get_exit_params(self) -> Dict[str, Any]:
        """Extract exit condition parameters from the gameplan strategy_parameters."""
        sp = self.gameplan.get("strategy_parameters", {})
        hl = self.gameplan.get("hard_limits", {})
        return {
            "take_profit_pct": float(sp.get("take_profit_pct", 0.15)),
            "stop_loss_pct": float(sp.get("stop_loss_pct", 0.25)),
            "time_stop_minutes": int(sp.get("time_stop_minutes", 90)),
            "force_close_dte": int(hl.get("force_close_at_dte", 1)),
        }

    def _monitor_open_positions(self) -> None:
        """
        Evaluate all tracked positions against exit conditions.

        Fetches the current bid price for each open position and calls the
        PositionMonitor.  When an exit signal fires, a closing order is
        submitted (or logged as dry-run) and the position is deregistered.
        """
        positions = self._position_monitor.get_positions()
        if not positions:
            return

        for position in positions:
            try:
                current_price = self._fetch_current_price(position.symbol)
                if current_price is None:
                    logger.warning(
                        "PositionMonitor: could not fetch price for %s — skipping exit check",
                        position.symbol,
                    )
                    continue

                signal = self._position_monitor.evaluate(position.symbol, current_price)
                if signal.should_exit:
                    self._close_position(position, signal, current_price)

            except Exception as exc:
                logger.error(
                    "PositionMonitor: error evaluating %s: %s",
                    position.symbol,
                    exc,
                    exc_info=True,
                )

    def _fetch_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch the current bid price for an open position.

        Returns None when market data is unavailable or stale.
        """
        if self._market_data_provider is None or self._contract_manager is None:
            return None
        try:
            contract = self._contract_manager.qualify_contract(symbol)
            quote = self._market_data_provider.request_market_data(contract)
            bid = quote.get("bid")
            return float(bid) if bid is not None and bid > 0 else None
        except Exception as exc:
            logger.warning("Could not fetch price for %s: %s", symbol, exc)
            return None

    def _close_position(
        self,
        position: OpenPosition,
        exit_signal: ExitSignal,
        current_price: float,
    ) -> None:
        """
        Submit a closing order for an open position.

        Closing is always attempted even when the circuit breaker is OPEN
        (CRO mandate — exits must NEVER be gated).

        Args:
            position: The position to close.
            exit_signal: The exit signal that triggered the close.
            current_price: Current bid price (used for logging).
        """
        logger.info(
            "[%s] EXIT triggered — reason=%s  entry=%.4f  current=%.4f  %s",
            position.symbol,
            exit_signal.reason,
            position.entry_price,
            current_price,
            exit_signal.details,
        )

        if self._dry_run:
            logger.info(
                "[%s] [DRY-RUN] Would submit SELL x%d to close position (reason=%s)",
                position.symbol,
                position.quantity,
                exit_signal.reason,
            )
        elif self._order_manager is not None and self._contract_manager is not None:
            try:
                contract = self._contract_manager.qualify_contract(position.symbol)
                close_order_id = self._order_manager.submit_order(
                    contract,
                    OrderParams(action="SELL", quantity=position.quantity, order_type="MKT"),
                )
                logger.info(
                    "[%s] Close order submitted: order_id=%d  reason=%s",
                    position.symbol,
                    close_order_id,
                    exit_signal.reason,
                )
            except Exception as exc:
                logger.error(
                    "[%s] Failed to submit close order: %s",
                    position.symbol,
                    exc,
                    exc_info=True,
                )
                # Do NOT re-raise — still deregister the position so we
                # don't loop attempting to close every cycle.
        else:
            logger.warning(
                "[%s] Cannot close live position: no order_manager available",
                position.symbol,
            )

        # Deregister regardless of whether the order succeeded
        self._position_monitor.remove_position(position.symbol)

        # Track for session summary
        self._session_exits.append(
            {
                "symbol": position.symbol,
                "reason": exit_signal.reason,
                "entry_price": position.entry_price,
                "exit_price": current_price,
                "quantity": position.quantity,
                "pnl_per_share": current_price - position.entry_price,
            }
        )

        if self.discord:
            pnl = (current_price - position.entry_price) * position.quantity * 100
            self.discord.send_info(
                f"Position closed — {position.symbol} x{position.quantity}\n"
                f"Reason: {exit_signal.reason}  {exit_signal.details}\n"
                f"Entry: ${position.entry_price:.4f}  Exit: ${current_price:.4f}  "
                f"PnL: ${pnl:+.2f}{'  [DRY-RUN]' if self._dry_run else ''}"
            )

    # =========================================================================
    # Emergency halt
    # =========================================================================

    def _check_emergency_halt(self) -> bool:
        """
        Check whether the risk engine has halted trading.

        When triggered, closes all open positions, switches strategy to C,
        sends a Discord critical alert, and signals the evaluation loop to
        break.

        Returns:
            True if an emergency halt is active (loop should break).
        """
        if self._risk_engine is None:
            return False
        if not self._risk_engine.trading_halted():
            return False

        logger.critical(
            "EMERGENCY HALT — circuit breaker OPEN. "
            "Switching to Strategy C. Closing all positions."
        )

        # Force-close all tracked positions before switching to monitoring-only
        for position in self._position_monitor.get_positions():
            try:
                current_price = self._fetch_current_price(position.symbol) or 0.0
                self._close_position(
                    position,
                    ExitSignal(
                        should_exit=True,
                        reason="emergency_halt",
                        details="circuit breaker OPEN — daily loss limit hit",
                    ),
                    current_price,
                )
            except Exception as exc:
                logger.error("Emergency close failed for %s: %s", position.symbol, exc)

        # Override strategy to C for the remainder of the session
        self.strategy = "C"
        self._strategy_overridden = True
        self._running = False

        if self.discord:
            self.discord.send_critical(
                "EMERGENCY HALT — circuit breaker OPEN\n"
                "Daily loss limit reached. Strategy overridden to C.\n"
                "All positions closed. No new entries until next session."
            )

        return True

    # =========================================================================
    # End-of-session summary
    # =========================================================================

    def _post_session_summary(self) -> None:
        """
        Post an end-of-session summary to Discord and the log.

        Called automatically from run() via try/finally so it always fires
        whether the loop exits normally, via stop(), or via emergency halt.
        """
        # Count outcomes from trade log buffer
        from collections import Counter

        outcomes: Counter[str] = Counter()
        for decision in self._trade_log.get_buffer():
            outcomes[decision.outcome] += 1

        submitted = outcomes.get("submitted", 0)
        dry_run = outcomes.get("dry_run", 0)
        holds = outcomes.get("hold", 0)
        rejections = sum(
            outcomes.get(k, 0)
            for k in ("rejected_confidence", "rejected_affordability", "rejected_risk")
        )
        errors = outcomes.get("error", 0)
        total_cycles = self._eval_cycle_count

        # PnL from closed positions this session
        total_pnl = sum(e["pnl_per_share"] * e["quantity"] * 100 for e in self._session_exits)
        exits_count = len(self._session_exits)
        exits_summary = ""
        for ex in self._session_exits:
            pnl = ex["pnl_per_share"] * ex["quantity"] * 100
            exits_summary += f"  • {ex['symbol']} — {ex['reason']:15s}  PnL: ${pnl:+.2f}\n"

        dry_label = " [DRY-RUN]" if self._dry_run else ""
        summary_lines = [
            f"Session complete — Strategy {self.strategy}{dry_label}",
            f"Eval cycles: {total_cycles}  |  Submitted: {submitted}  "
            f"Dry-run: {dry_run}  |  Hold: {holds}  |  Rejected: {rejections}  "
            f"Errors: {errors}",
        ]
        if exits_count > 0:
            summary_lines.append(f"Exits: {exits_count}  |  Session PnL: ${total_pnl:+.2f}")
            summary_lines.append(exits_summary.rstrip())
        elif total_cycles == 0:
            summary_lines.append("No evaluation cycles ran this session.")

        summary = "\n".join(summary_lines)
        logger.info("SESSION SUMMARY:\n%s", summary)

        if self.discord:
            self.discord.send_info(summary)
