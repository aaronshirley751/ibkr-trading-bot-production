"""
Pre-trade gates for Strategy A/B execution.

Three independent gate checks that must pass before any trade entry:
- VIXConfirmationGate: VIX level vs threshold
- AffordabilityGate: Contract premium vs risk budget
- EntryWindowGate: Current time vs allowed trading window

Safety Philosophy: Any gate failure blocks entry. VIX gate failure
forces full Strategy C override. All failures are logged with reasons.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from typing import Any, Dict, Optional

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class GateResult:
    """Result of a gate evaluation."""

    passed: bool
    reason: str
    gate_name: str


class VIXConfirmationGate:
    """
    Check VIX level against gameplan threshold.

    If VIX >= threshold: override to Strategy C.
    If VIX is None: fail-safe to Strategy C.
    If VIX < threshold: proceed with gameplan strategy.

    Uses vix_at_analysis from gameplan until live IBKR fetch is available.
    """

    def evaluate(self, gameplan: Dict[str, Any]) -> GateResult:
        """
        Evaluate VIX against the gate threshold.

        Args:
            gameplan: Daily gameplan dictionary.

        Returns:
            GateResult with pass/fail and reason.
        """
        vix = gameplan.get("vix_at_analysis")
        vix_gate = gameplan.get("vix_gate")

        if vix_gate is None:
            logger.debug("No vix_gate configured, gate passes by default")
            return GateResult(passed=True, reason="no_vix_gate_configured", gate_name="vix")

        threshold = vix_gate.get("threshold", 18.0)

        if vix is None:
            logger.warning("VIX is None — fail-safe to Strategy C")
            return GateResult(
                passed=False,
                reason=f"vix_is_none (threshold={threshold})",
                gate_name="vix",
            )

        if vix >= threshold:
            logger.warning(
                "VIX gate FAILED: VIX=%.2f >= threshold=%.2f — override to Strategy C",
                vix,
                threshold,
            )
            return GateResult(
                passed=False,
                reason=f"vix_above_threshold (vix={vix}, threshold={threshold})",
                gate_name="vix",
            )

        logger.info(
            "VIX gate passed: VIX=%.2f < threshold=%.2f",
            vix,
            threshold,
        )
        return GateResult(
            passed=True,
            reason=f"vix_below_threshold (vix={vix}, threshold={threshold})",
            gate_name="vix",
        )


@dataclass(frozen=True)
class AffordabilityResult:
    """Extended gate result with sizing guidance."""

    passed: bool
    reason: str
    gate_name: str
    reduce_size: bool = False


class AffordabilityGate:
    """
    Check contract premium against risk budget.

    Three outcomes:
    - premium <= max_risk_per_trade: full size, pass
    - max_risk_per_trade < premium <= max_risk_ceiling: reduced size, pass with warning
    - premium > max_risk_ceiling: reject entry
    """

    def __init__(self, default_max_risk: Decimal = Decimal("18")):
        """
        Args:
            default_max_risk: Default max risk per trade from RiskConfig.
        """
        self.default_max_risk = default_max_risk

    def evaluate(self, premium: float, gameplan: Dict[str, Any]) -> AffordabilityResult:
        """
        Evaluate whether a contract premium is within risk budget.

        Args:
            premium: Contract premium in dollars.
            gameplan: Daily gameplan dictionary.

        Returns:
            AffordabilityResult with pass/fail, reason, and size guidance.
        """
        max_risk = gameplan.get("max_risk_per_trade", float(self.default_max_risk))
        ceiling = gameplan.get("max_risk_ceiling", float(self.default_max_risk))

        if premium > ceiling:
            logger.warning(
                "Affordability gate REJECTED: premium=$%.2f > ceiling=$%.2f",
                premium,
                ceiling,
            )
            return AffordabilityResult(
                passed=False,
                reason=f"affordability_skip (premium={premium}, ceiling={ceiling})",
                gate_name="affordability",
            )

        if premium > max_risk:
            logger.warning(
                "Affordability gate WARNING: premium=$%.2f > max_risk=$%.2f "
                "(within ceiling=$%.2f) — reduced size",
                premium,
                max_risk,
                ceiling,
            )
            return AffordabilityResult(
                passed=True,
                reason=f"affordability_warn (premium={premium}, max_risk={max_risk}, ceiling={ceiling})",
                gate_name="affordability",
                reduce_size=True,
            )

        logger.info(
            "Affordability gate passed: premium=$%.2f <= max_risk=$%.2f",
            premium,
            max_risk,
        )
        return AffordabilityResult(
            passed=True,
            reason=f"within_budget (premium={premium}, max_risk={max_risk})",
            gate_name="affordability",
        )


class EntryWindowGate:
    """
    Check whether current time falls within allowed entry window.

    Window is defined in HH:MM ET format in the gameplan.
    Default window: 09:30-16:00 ET if fields are missing.
    """

    DEFAULT_START = time(9, 30)
    DEFAULT_END = time(16, 0)

    def evaluate(
        self,
        gameplan: Dict[str, Any],
        now: Optional[datetime] = None,
    ) -> GateResult:
        """
        Evaluate whether the current time is within the entry window.

        Args:
            gameplan: Daily gameplan dictionary.
            now: Override current time for testing. Must be timezone-aware.

        Returns:
            GateResult with pass/fail and reason.
        """
        if now is None:
            now = datetime.now(ET)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=ET)
        else:
            now = now.astimezone(ET)

        current_time = now.time()

        start_str = gameplan.get("entry_window_start")
        end_str = gameplan.get("entry_window_end")

        try:
            start = self._parse_time(start_str) if start_str else self.DEFAULT_START
            end = self._parse_time(end_str) if end_str else self.DEFAULT_END
        except ValueError as e:
            logger.error("Invalid entry window format: %s — using defaults", e)
            start = self.DEFAULT_START
            end = self.DEFAULT_END

        if start <= current_time <= end:
            logger.debug(
                "Entry window gate passed: %s is within %s-%s ET",
                current_time.strftime("%H:%M"),
                start.strftime("%H:%M"),
                end.strftime("%H:%M"),
            )
            return GateResult(
                passed=True,
                reason=f"within_window ({current_time.strftime('%H:%M')} in {start.strftime('%H:%M')}-{end.strftime('%H:%M')})",
                gate_name="entry_window",
            )

        logger.info(
            "Entry window gate BLOCKED: %s outside %s-%s ET",
            current_time.strftime("%H:%M"),
            start.strftime("%H:%M"),
            end.strftime("%H:%M"),
        )
        return GateResult(
            passed=False,
            reason=f"outside_window ({current_time.strftime('%H:%M')} not in {start.strftime('%H:%M')}-{end.strftime('%H:%M')})",
            gate_name="entry_window",
        )

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """Parse HH:MM string to time object."""
        parts = time_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid time format: {time_str}")
        return time(int(parts[0]), int(parts[1]))
