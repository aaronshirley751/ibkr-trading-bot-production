"""
Enhanced trading loop for Strategy A/B execution.

Replaces the placeholder loop in main.py with a gate-aware
evaluation cycle that enforces VIX confirmation, entry windows,
and affordability checks before any trade entry.

Lifecycle:
1. Startup: load gameplan, log parameters, Discord notification
2. VIX confirmation gate evaluation
3. Evaluation cycle (every N seconds):
   a. Entry window gate check
   b. Market data fetch (placeholder)
   c. Strategy signal evaluation (placeholder)
   d. Affordability gate before order
   e. PDT/drawdown checks (existing risk engine)
   f. Log decisions
4. Periodic health checks
5. Graceful shutdown
"""

import logging
import time
from typing import Any, Dict, Optional

from src.bot.gates import (
    AffordabilityGate,
    EntryWindowGate,
    VIXConfirmationGate,
)
from src.config.risk_config import RiskConfig
from src.notifications.discord import DiscordNotifier
from src.utils.gateway_health import GatewayHealthChecker

logger = logging.getLogger(__name__)


class TradingLoop:
    """
    Gate-aware trading loop for Strategy A/B execution.

    Integrates pre-trade gates with the evaluation cycle.
    Strategy C bypasses gates and runs monitoring-only mode.
    """

    # How often to run the evaluation cycle (seconds)
    EVAL_INTERVAL = 30

    # Health check interval (seconds)
    HEALTH_CHECK_INTERVAL = 300

    def __init__(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        health_checker: GatewayHealthChecker,
        discord_notifier: Optional[DiscordNotifier] = None,
    ):
        self.gameplan = gameplan
        self.risk_config = risk_config
        self.health_checker = health_checker
        self.discord = discord_notifier

        self.strategy = gameplan.get("strategy", "C")
        self.symbols = gameplan.get("symbols", [])

        # Initialize gates
        self.vix_gate = VIXConfirmationGate()
        self.affordability_gate = AffordabilityGate(default_max_risk=risk_config.max_risk_per_trade)
        self.entry_window_gate = EntryWindowGate()

        # State
        self._vix_checked = False
        self._strategy_overridden = False
        self._running = False

    def run(self) -> None:
        """Execute the main trading loop."""
        self._running = True
        self._log_startup()

        if self.strategy == "C":
            self._run_strategy_c_loop()
            return

        # Run VIX confirmation gate
        if not self._check_vix_gate():
            self._run_strategy_c_loop()
            return

        # Strategy A/B evaluation cycle
        self._run_evaluation_loop()

    def stop(self) -> None:
        """Signal the loop to stop."""
        self._running = False
        logger.info("Trading loop stop requested")

    def _log_startup(self) -> None:
        """Log startup parameters and send Discord notification."""
        logger.info("=" * 50)
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
        logger.info("=" * 50)

        if self.discord:
            self.discord.send_info(
                f"Trading loop started — Strategy {self.strategy}\n"
                f"Symbols: {', '.join(self.symbols)}\n"
                f"Entry window: {entry_start}-{entry_end} ET\n"
                f"Regime: {self.gameplan.get('regime', 'unknown')}"
            )

    def _check_vix_gate(self) -> bool:
        """
        Run VIX confirmation gate.

        Returns:
            True if VIX gate passes, False if Strategy C override needed.
        """
        result = self.vix_gate.evaluate(self.gameplan)
        self._vix_checked = True

        if not result.passed:
            logger.warning("VIX gate failed — overriding to Strategy C")
            self.strategy = "C"
            self._strategy_overridden = True

            if self.discord:
                self.discord.send_warning(f"VIX gate override to Strategy C: {result.reason}")
            return False

        logger.info("VIX gate passed: %s", result.reason)
        return True

    def _run_strategy_c_loop(self) -> None:
        """Strategy C monitoring loop — health checks only."""
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

                time.sleep(min(60, self.HEALTH_CHECK_INTERVAL))
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                raise

    def _run_evaluation_loop(self) -> None:
        """Strategy A/B evaluation cycle with gate enforcement."""
        logger.info("Entering Strategy %s evaluation cycle", self.strategy)

        last_health_check = 0.0
        eval_count = 0

        while self._running:
            try:
                now = time.monotonic()

                # Periodic health check
                if now - last_health_check >= self.HEALTH_CHECK_INTERVAL:
                    self._periodic_health_check()
                    last_health_check = now

                # Gate 1: Entry window check
                window_result = self.entry_window_gate.evaluate(self.gameplan)
                if not window_result.passed:
                    logger.debug("Entry window closed: %s", window_result.reason)
                    time.sleep(self.EVAL_INTERVAL)
                    continue

                eval_count += 1
                logger.debug("Evaluation cycle #%d", eval_count)

                # Placeholder: Fetch market data
                # TODO: Connect to IBKR Gateway for live data
                logger.debug("Market data fetch (placeholder)")

                # Placeholder: Evaluate strategy signals
                # TODO: Run Strategy A momentum or Strategy B mean-reversion
                logger.debug("Signal evaluation (placeholder)")

                # Placeholder: If signal fires, check affordability gate
                # premium = get_contract_premium()  # Future implementation
                # affordability = self.affordability_gate.evaluate(premium, self.gameplan)
                # if not affordability.passed:
                #     logger.info("Affordability gate rejected: %s", affordability.reason)
                #     continue

                # Placeholder: PDT/drawdown checks via risk engine
                # TODO: Wire RiskEngine pre-trade checks

                time.sleep(self.EVAL_INTERVAL)
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                raise

    def _periodic_health_check(self) -> None:
        """Run a lightweight Gateway health check."""
        try:
            is_healthy = self.health_checker.check_port(timeout=10.0)
            if is_healthy:
                logger.debug("Gateway health check passed")
            else:
                logger.warning("Gateway health check failed")
                if self.discord:
                    self.discord.send_warning("Gateway health check failed during trading loop")
        except Exception as e:
            logger.error("Health check error: %s", e)
