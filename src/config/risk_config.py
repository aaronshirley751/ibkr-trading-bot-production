"""
Risk configuration parameters.

This file extends the existing config module with risk-specific
parameters. All values are derived from the Account Parameters
in the Crucible system prompt.

CRITICAL: These values are the source of truth for all risk
calculations. Changes here affect the entire system.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskConfig:
    """
    Immutable risk configuration parameters.

    All monetary values are in USD.
    All percentages are as decimals (e.g., 0.03 for 3%).

    Attributes:
        starting_capital: Initial account capital ($600)
        max_risk_per_trade_pct: Maximum risk per trade (3% = 0.03)
        max_position_pct_strategy_a: Position limit for Strategy A (20%)
        max_position_pct_strategy_b: Position limit for Strategy B (10%)
        max_position_pct_strategy_c: Position limit for Strategy C (0%)
        max_daily_loss_pct: Daily loss halt threshold (10%)
        weekly_drawdown_governor_pct: Weekly governor trigger (15%)
        pdt_limit: Max day trades per rolling window (3)
        pdt_window_days: Rolling window for PDT (5 business days)
        confidence_threshold: Minimum signal confidence (0.5)
        options_contract_multiplier: Standard options multiplier (100)
        stop_loss_pct_strategy_a: Stop-loss for Strategy A (25%)
        stop_loss_pct_strategy_b: Stop-loss for Strategy B (15%)
        force_close_dte: DTE threshold for force close (3)
    """

    # Account parameters
    starting_capital: Decimal = Decimal("600")

    # Per-trade risk limit (3% of capital = $18)
    max_risk_per_trade_pct: Decimal = Decimal("0.03")

    # Strategy-specific position limits
    max_position_pct_strategy_a: Decimal = Decimal("0.20")  # 20% = $120
    max_position_pct_strategy_b: Decimal = Decimal("0.10")  # 10% = $60
    max_position_pct_strategy_c: Decimal = Decimal("0.00")  # 0% (no trading)

    # Daily loss limit (10% of capital = $60)
    max_daily_loss_pct: Decimal = Decimal("0.10")

    # Weekly drawdown governor (15% triggers Strategy C)
    weekly_drawdown_governor_pct: Decimal = Decimal("0.15")

    # PDT constraints
    pdt_limit: int = 3  # Max 3 day trades per rolling window
    pdt_window_days: int = 5  # 5 business day rolling window

    # Signal quality gate
    confidence_threshold: Decimal = Decimal("0.5")

    # Options standard
    options_contract_multiplier: int = 100

    # Strategy-specific stop-loss percentages
    stop_loss_pct_strategy_a: Decimal = Decimal("0.25")  # 25%
    stop_loss_pct_strategy_b: Decimal = Decimal("0.15")  # 15%

    # DTE force-close threshold
    force_close_dte: int = 3

    @property
    def max_risk_per_trade(self) -> Decimal:
        """Calculate max risk in dollars."""
        return self.starting_capital * self.max_risk_per_trade_pct

    @property
    def max_daily_loss(self) -> Decimal:
        """Calculate max daily loss in dollars."""
        return self.starting_capital * self.max_daily_loss_pct

    @property
    def max_position_strategy_a(self) -> Decimal:
        """Calculate max position size for Strategy A."""
        return self.starting_capital * self.max_position_pct_strategy_a

    @property
    def max_position_strategy_b(self) -> Decimal:
        """Calculate max position size for Strategy B."""
        return self.starting_capital * self.max_position_pct_strategy_b

    def get_stop_loss_pct(self, strategy: str) -> Decimal:
        """Get stop-loss percentage for a given strategy."""
        if strategy == "A":
            return self.stop_loss_pct_strategy_a
        elif strategy == "B":
            return self.stop_loss_pct_strategy_b
        else:
            raise ValueError(f"Strategy {strategy} does not trade (no stop-loss)")

    def get_position_limit_pct(self, strategy: str) -> Decimal:
        """Get position limit percentage for a given strategy."""
        if strategy == "A":
            return self.max_position_pct_strategy_a
        elif strategy == "B":
            return self.max_position_pct_strategy_b
        else:
            return self.max_position_pct_strategy_c


# Default configuration instance
DEFAULT_RISK_CONFIG = RiskConfig()
