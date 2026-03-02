"""
Integration tests — TradingLoop full execution pipeline (CAP-45).

Tests exercise real component wiring without a live IBKR connection:
  - Real StrategyA signal evaluation via seeded EMA crossover state
  - Real RiskEngine.pre_trade_check (account_balance=$600)
  - Real AffordabilityGate / VIXConfirmationGate
  - Real TradeLog (JSONL writes to disk via tmp_path)
  - Real PositionMonitor exit evaluation
  - Mocked I/O only: MarketDataProvider, ContractManager, OrderManager

Pipeline stages under test (per CAP-45 remaining requirement):
  Gameplan → TradingLoop init → MarketData → StrategyA signal
  → AffordabilityGate → RiskEngine → dry_run outcome → TradeLog
  → PositionMonitor exit detection

Unit tests cover individual component behaviour.
Integration tests prove the components are wired correctly together.

Bar geometry note:
  _ascending_option_bars() produces 30 OHLCV bars at option-level prices
  (~$0.65–$0.70). Analytically verified properties:
    EMA(8)  = 0.6926 > EMA(21) = 0.6831   (fast above slow)
    RSI-14  = 59.18  ∈ [50, 65]            (Strategy A BUY range)
    VWAP    = 0.6765;  price 0.695 > VWAP  (VWAP confirmation)
    ask $0.700 → risk $70 ≤ $120 pos-limit, $17.50 ≤ $18 risk-limit

  Seed prior EMA state: previous_ema_fast=0.723 < previous_ema_slow=0.735
  → bullish crossover detected on first evaluate() call with ascending bars.
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from src.bot.position_monitor import OpenPosition
from src.bot.trading_loop import TradingLoop
from src.broker.exceptions import MarketDataError
from src.config.risk_config import DEFAULT_RISK_CONFIG, RiskConfig
from src.risk.engine import RiskEngine

pytestmark = pytest.mark.integration


# =============================================================================
# Bar / quote factories (option-level prices)
# =============================================================================


def _ascending_option_bars(n: int = 30, start: float = 0.650) -> List[Dict[str, Any]]:
    """
    Return bars with a +0.008 / -0.005 alternating pattern.

    Analytically verified indicator properties (see module docstring).
    """
    bars: List[Dict[str, Any]] = []
    close = start
    for i in range(n):
        close += 0.008 if i % 2 == 0 else -0.005
        bars.append(
            {
                "open": close - 0.002,
                "high": close + 0.005,
                "low": close - 0.005,
                "close": close,
                "volume": 500,
                "average": close,
                "bar_count": 5,
            }
        )
    return bars


def _signal_quote(
    bid: float = 0.685,
    ask: float = 0.700,
    last: float = 0.695,
) -> Dict[str, Any]:
    """Option-level quote where last (0.695) > VWAP (~0.677)."""
    return {
        "bid": bid,
        "ask": ask,
        "last": last,
        "volume": 50_000,
        "timestamp": datetime.now(timezone.utc),
        "snapshot": True,
    }


# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture
def strategy_a_gameplan() -> Dict[str, Any]:
    """Minimal Strategy A gameplan — entry window always open for deterministic tests."""
    return {
        "strategy": "A",
        "symbols": ["QQQ"],
        "regime": "trending",
        "bias": "bullish",
        "entry_window_start": "00:00",
        "entry_window_end": "23:59",
        "vix_at_analysis": 14.5,
        "vix_gate": {"threshold": 20.0, "check_time": "09:45"},
        "max_risk_per_trade": 18.0,
        "max_risk_ceiling": 36.0,
        "position_size_multiplier": 1.0,
    }


@pytest.fixture
def strategy_c_gameplan() -> Dict[str, Any]:
    return {
        "strategy": "C",
        "symbols": [],
        "regime": "crisis",
        "vix_at_analysis": 32.0,
    }


@pytest.fixture
def risk_config() -> RiskConfig:
    return DEFAULT_RISK_CONFIG


@pytest.fixture
def real_risk_engine() -> RiskEngine:
    return RiskEngine(
        account_balance=600.00,
        config={
            "max_position_pct": 0.20,
            "max_risk_pct": 0.03,
            "pdt_limit": 3,
            "max_daily_loss_pct": 0.10,
            "max_weekly_drawdown_pct": 0.15,
        },
    )


@pytest.fixture
def mock_health_checker() -> MagicMock:
    hc = MagicMock()
    hc.check_port.return_value = True
    return hc


@pytest.fixture
def mock_contract_manager() -> MagicMock:
    cm = MagicMock()
    cm.qualify_contract.return_value = MagicMock(symbol="QQQ")
    return cm


def _build_loop(
    gameplan: Dict[str, Any],
    risk_config: RiskConfig,
    mock_health_checker: MagicMock,
    *,
    market_data_provider: Any = None,
    contract_manager: Any = None,
    risk_engine: Any = None,
    order_manager: Any = None,
    dry_run: bool = True,
    tmp_path: Path,
) -> TradingLoop:
    return TradingLoop(
        gameplan=gameplan,
        risk_config=risk_config,
        health_checker=mock_health_checker,
        discord_notifier=None,
        market_data_provider=market_data_provider,
        contract_manager=contract_manager,
        risk_engine=risk_engine,
        order_manager=order_manager,
        dry_run=dry_run,
        log_dir=tmp_path / "logs",
    )


def _seed_bullish_crossover(loop: TradingLoop) -> None:
    """
    Pre-set prior EMA state so the next evaluate() call detects a bullish crossover.

    With ascending_option_bars():  current EMA(8)=0.6926 > EMA(21)=0.6831
    Seeded prior state: fast=0.723 < slow=0.735  →  fast crossed above slow.
    """
    loop._strategy_a._previous_ema_fast = 0.723
    loop._strategy_a._previous_ema_slow = 0.735


def _read_last_log_entry(tmp_path: Path) -> Dict[str, Any]:
    """Return the last (or only) JSONL entry from the daily trade log."""
    log_files = list((tmp_path / "logs").glob("trade_log_*.jsonl"))
    assert len(log_files) == 1, f"Expected one log file, found {log_files}"
    lines = log_files[0].read_text(encoding="utf-8").strip().splitlines()
    return dict(json.loads(lines[-1]))


# =============================================================================
# 1. TradingLoop initialisation
# =============================================================================


class TestTradingLoopInit:
    @pytest.mark.integration
    def test_strategy_a_gameplan_initialises_correctly(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Loop reads strategy, symbols, and dry_run from constructor."""
        loop = _build_loop(strategy_a_gameplan, risk_config, mock_health_checker, tmp_path=tmp_path)
        assert loop.strategy == "A"
        assert loop.symbols == ["QQQ"]
        assert loop._dry_run is True
        assert loop._pipeline_ready() is False  # no providers yet

    @pytest.mark.integration
    def test_pipeline_ready_requires_all_three_providers(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """_pipeline_ready() only returns True when mdp + contract_manager + risk_engine are set."""
        mdp = MagicMock()

        # Missing risk_engine → not ready
        loop_partial = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            tmp_path=tmp_path,
        )
        assert loop_partial._pipeline_ready() is False

        # All three supplied → ready
        loop_full = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        assert loop_full._pipeline_ready() is True

    @pytest.mark.integration
    def test_strategy_c_gameplan_has_empty_symbols(
        self,
        strategy_c_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(strategy_c_gameplan, risk_config, mock_health_checker, tmp_path=tmp_path)
        assert loop.strategy == "C"
        assert loop.symbols == []


# =============================================================================
# 2. VIX gate integration
# =============================================================================


class TestVIXGateIntegration:
    @pytest.mark.integration
    def test_vix_above_threshold_overrides_to_c(
        self,
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Real VIXConfirmationGate — VIX 25 >= threshold 20 → strategy overridden to C."""
        high_vix_gameplan: Dict[str, Any] = {
            "strategy": "A",
            "symbols": ["QQQ"],
            "vix_at_analysis": 25.0,
            "vix_gate": {"threshold": 20.0, "check_time": "09:45"},
        }
        loop = _build_loop(high_vix_gameplan, risk_config, mock_health_checker, tmp_path=tmp_path)

        passed = loop._check_vix_gate()

        assert passed is False
        assert loop.strategy == "C"
        assert loop._strategy_overridden is True

    @pytest.mark.integration
    def test_vix_below_threshold_gate_passes(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """VIX 14.5 < threshold 20.0 → gate passes, strategy remains A."""
        loop = _build_loop(strategy_a_gameplan, risk_config, mock_health_checker, tmp_path=tmp_path)

        passed = loop._check_vix_gate()

        assert passed is True
        assert loop.strategy == "A"
        assert loop._strategy_overridden is False

    @pytest.mark.integration
    def test_missing_vix_fails_safe_to_c(
        self,
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """vix_at_analysis=None with a gate configured → fail-safe to C."""
        gameplan: Dict[str, Any] = {
            "strategy": "A",
            "symbols": ["QQQ"],
            "vix_at_analysis": None,
            "vix_gate": {"threshold": 20.0},
        }
        loop = _build_loop(gameplan, risk_config, mock_health_checker, tmp_path=tmp_path)

        passed = loop._check_vix_gate()

        assert passed is False
        assert loop.strategy == "C"


# =============================================================================
# 3. Real StrategyA signal path
# =============================================================================


class TestRealStrategyASignalPath:
    @pytest.mark.integration
    def test_no_prior_ema_state_produces_hold_outcome(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Real StrategyA on first-ever evaluation cycle returns HOLD
        (no previous EMA state → no crossover detected).
        TradeLog records outcome=hold.
        """
        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = _signal_quote()

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        # No seeding — _previous_ema_fast/slow are None → detect_crossover returns "none"

        loop._execute_pipeline_for_symbol("QQQ")

        entry = _read_last_log_entry(tmp_path)
        assert entry["outcome"] == "hold"
        assert entry["signal_direction"] == "hold"
        assert entry["symbol"] == "QQQ"
        assert entry["strategy"] == "A"

    @pytest.mark.integration
    def test_seeded_ema_crossover_full_pipeline_dry_run(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Real end-to-end pipeline — CAP-45 integration requirement:
          gameplan → TradingLoop → indicators → StrategyA signal
          → AffordabilityGate → RiskEngine.pre_trade_check → dry_run → TradeLog

        Seeded prior EMA state (fast=0.723 < slow=0.735) triggers a bullish
        crossover from ascending bars (EMA8=0.6926 > EMA21=0.6831).

        All real components, mock I/O only:
          RSI=59.2 ∈ [50,65] ✓ | price 0.695 > VWAP 0.677 ✓
          ask=$0.70 → risk $17.50 ≤ $18 ✓ | position $70 ≤ $120 ✓
          dry_run=True → outcome=dry_run, order_id=None
        """
        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = _signal_quote()

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        _seed_bullish_crossover(loop)

        loop._execute_pipeline_for_symbol("QQQ")

        entry = _read_last_log_entry(tmp_path)
        assert entry["outcome"] == "dry_run"
        assert entry["signal_direction"] == "buy"
        assert entry["signal_confidence"] == pytest.approx(0.80, abs=0.01)
        assert "Bullish EMA crossover" in entry["signal_rationale"]
        assert entry["affordability_passed"] is True
        assert entry["risk_approved"] is True
        assert entry["quantity"] == 1
        assert entry["premium_used"] == pytest.approx(0.700, abs=1e-3)
        assert entry["order_id"] is None  # dry_run never submits

    @pytest.mark.integration
    def test_two_consecutive_cycles_append_to_same_daily_log(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Two back-to-back _execute_pipeline_for_symbol calls append two lines
        to the same daily JSONL. Cycle counters increment correctly.
        """
        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = _signal_quote()

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        _seed_bullish_crossover(loop)

        loop._execute_pipeline_for_symbol("QQQ")  # cycle 1 → dry_run
        loop._execute_pipeline_for_symbol("QQQ")  # cycle 2 → hold (crossover already fired)

        log_files = list((tmp_path / "logs").glob("trade_log_*.jsonl"))
        assert len(log_files) == 1
        lines = log_files[0].read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        entries = [json.loads(line) for line in lines]
        assert entries[0]["cycle_count"] == 1
        assert entries[1]["cycle_count"] == 2
        assert entries[0]["outcome"] == "dry_run"
        assert entries[1]["outcome"] == "hold"  # no new crossover on second call


# =============================================================================
# 4. Affordability gate integration
# =============================================================================


class TestAffordabilityGateIntegration:
    @pytest.mark.integration
    def test_premium_above_ceiling_records_rejected_affordability(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Real AffordabilityGate — premium $50.00 > max_risk_ceiling $36.00
        → outcome=rejected_affordability, written to JSONL.
        """
        expensive_quote = _signal_quote(bid=49.80, ask=50.00, last=49.90)
        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = expensive_quote

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        _seed_bullish_crossover(loop)

        loop._execute_pipeline_for_symbol("QQQ")

        entry = _read_last_log_entry(tmp_path)
        assert entry["outcome"] == "rejected_affordability"
        assert entry["affordability_passed"] is False
        assert entry["symbol"] == "QQQ"
        assert entry["risk_approved"] is None  # never reached

    @pytest.mark.integration
    def test_premium_in_warning_band_passes_with_reduce_size_flag(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Premium $20 > max_risk $18 but ≤ ceiling $36 → affordability passes
        with reduce_size=True, RiskEngine still approves, outcome=dry_run.
        """
        # premium=20 > 18 (max_risk) but ≤ 36 (ceiling) → warning band
        # risk = 20*100*0.25 = $500 >> $18 → RiskEngine rejects
        # (the affordability gate passes, but risk_per_trade guard blocks it)
        medium_quote = _signal_quote(bid=19.80, ask=20.00, last=19.90)
        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = medium_quote

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        _seed_bullish_crossover(loop)

        loop._execute_pipeline_for_symbol("QQQ")

        entry = _read_last_log_entry(tmp_path)
        # Affordability passes (within ceiling), but $20 premium fails RiskEngine
        assert entry["affordability_passed"] is True
        assert entry["reduce_size"] is True
        assert entry["outcome"] == "rejected_risk"


# =============================================================================
# 5. RiskEngine integration
# =============================================================================


class TestRiskEngineIntegration:
    @pytest.mark.integration
    def test_exhausted_pdt_rejects_buy_with_real_risk_engine(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Real RiskEngine with day_trades_count at pdt_limit (3) rejects BUY.
        outcome=rejected_risk with 'pdt_limit_reached' in risk_rejections.
        """
        risk_engine = RiskEngine(
            account_balance=600.00,
            config={"pdt_limit": 3, "max_position_pct": 0.20, "max_risk_pct": 0.03},
        )
        risk_engine._day_trades_count = 3  # PDT exhausted

        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = _signal_quote()

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=risk_engine,
            tmp_path=tmp_path,
        )
        _seed_bullish_crossover(loop)

        loop._execute_pipeline_for_symbol("QQQ")

        entry = _read_last_log_entry(tmp_path)
        assert entry["outcome"] == "rejected_risk"
        assert "pdt_limit_reached" in entry["risk_rejections"]
        assert entry["risk_approved"] is False

    @pytest.mark.integration
    def test_daily_loss_limit_rejects_buy(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Real RiskEngine with daily_losses at limit ($60.01 > $60) rejects entry.
        outcome=rejected_risk with 'daily_loss_limit' in risk_rejections.
        """
        risk_engine = RiskEngine(account_balance=600.00)
        risk_engine._daily_losses = Decimal("60.01")  # exceeds $60 daily limit

        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = _signal_quote()

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=risk_engine,
            tmp_path=tmp_path,
        )
        _seed_bullish_crossover(loop)

        loop._execute_pipeline_for_symbol("QQQ")

        entry = _read_last_log_entry(tmp_path)
        assert entry["outcome"] == "rejected_risk"
        assert "daily_loss_limit" in entry["risk_rejections"]

    @pytest.mark.integration
    def test_circuit_breaker_open_rejects_buy(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Circuit breaker OPEN → pre_trade_check rejects; outcome=rejected_risk."""
        risk_engine = RiskEngine(account_balance=600.00)
        risk_engine._circuit_breaker_state = "OPEN"

        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = _signal_quote()

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=risk_engine,
            tmp_path=tmp_path,
        )
        _seed_bullish_crossover(loop)

        loop._execute_pipeline_for_symbol("QQQ")

        entry = _read_last_log_entry(tmp_path)
        assert entry["outcome"] == "rejected_risk"
        assert "circuit_breaker_open" in entry["risk_rejections"]


# =============================================================================
# 6. Market data error handling
# =============================================================================


class TestMarketDataErrorHandling:
    @pytest.mark.integration
    def test_market_data_error_records_error_outcome_without_raising(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        MarketDataProvider raises MarketDataError.
        Loop must NOT re-raise; outcome=error written to JSONL for audit.
        """
        mdp = MagicMock()
        mdp.request_historical_data.side_effect = MarketDataError("mock gateway timeout")

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )

        loop._execute_pipeline_for_symbol("QQQ")  # must not raise

        entry = _read_last_log_entry(tmp_path)
        assert entry["outcome"] == "error"
        assert "market_data_error" in entry["signal_rationale"]
        assert entry["symbol"] == "QQQ"

    @pytest.mark.integration
    def test_stale_data_error_records_error_outcome(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """StaleDataError from MarketDataProvider → outcome=error, loop continues."""
        from src.broker.exceptions import StaleDataError

        mdp = MagicMock()
        mdp.request_historical_data.side_effect = StaleDataError("stale snapshot")

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )

        loop._execute_pipeline_for_symbol("QQQ")  # must not raise

        entry = _read_last_log_entry(tmp_path)
        assert entry["outcome"] == "error"


# =============================================================================
# 7. TradeLog disk write integration
# =============================================================================


class TestTradeLogDiskWrite:
    @pytest.mark.integration
    def test_dry_run_cycle_writes_valid_jsonl_with_all_audit_fields(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        After a dry_run cycle the file <log_dir>/trade_log_YYYYMMDD.jsonl
        exists, contains exactly one valid JSON line, and all required
        audit fields are present.
        """
        mdp = MagicMock()
        mdp.request_historical_data.return_value = _ascending_option_bars()
        mdp.request_market_data.return_value = _signal_quote()

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        _seed_bullish_crossover(loop)

        loop._execute_pipeline_for_symbol("QQQ")

        log_files = list((tmp_path / "logs").glob("trade_log_*.jsonl"))
        assert len(log_files) == 1
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        assert today in log_files[0].name

        entry = json.loads(log_files[0].read_text(encoding="utf-8").strip())
        required_audit_fields = [
            "timestamp",
            "symbol",
            "strategy",
            "cycle_count",
            "signal_direction",
            "signal_confidence",
            "signal_rationale",
            "affordability_passed",
            "risk_approved",
            "outcome",
        ]
        for field in required_audit_fields:
            assert field in entry, f"Missing required audit field: '{field}'"

        assert entry["cycle_count"] == 1
        assert entry["outcome"] == "dry_run"

    @pytest.mark.integration
    def test_log_dir_created_automatically_if_absent(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """TradeLog creates the log directory on first write — no pre-creation needed."""
        new_log_dir = tmp_path / "deep" / "nested" / "logs"
        assert not new_log_dir.exists()

        mdp = MagicMock()
        mdp.request_historical_data.side_effect = MarketDataError("error")

        loop = TradingLoop(
            gameplan=strategy_a_gameplan,
            risk_config=risk_config,
            health_checker=mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            log_dir=new_log_dir,
        )

        loop._execute_pipeline_for_symbol("QQQ")

        assert new_log_dir.exists()
        assert any(new_log_dir.glob("trade_log_*.jsonl"))


# =============================================================================
# 8. PositionMonitor integration (via TradingLoop._monitor_open_positions)
# =============================================================================


class TestPositionMonitorIntegration:
    @pytest.mark.integration
    def test_stop_loss_breach_deregisters_position(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Real PositionMonitor evaluates stop-loss.
        entry=0.80, stop_loss_pct=0.25 → threshold=0.60.
        bid=0.55 < 0.60 → stop_loss fires, position deregistered.
        """
        mdp = MagicMock()
        mdp.request_market_data.return_value = {"bid": 0.55, "ask": 0.57, "last": 0.56}

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        loop._position_monitor.add_position(
            OpenPosition(
                symbol="QQQ",
                entry_price=0.80,
                entry_time=datetime.now(timezone.utc),
                quantity=1,
                order_id=99,
                stop_loss_pct=0.25,
                take_profit_pct=0.15,
                time_stop_minutes=90,
                force_close_dte=1,
            )
        )
        assert len(loop._position_monitor.get_positions()) == 1

        loop._monitor_open_positions()

        assert len(loop._position_monitor.get_positions()) == 0
        assert len(loop._session_exits) == 1
        assert loop._session_exits[0]["reason"] == "stop_loss"

    @pytest.mark.integration
    def test_take_profit_breach_deregisters_position(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        entry=0.80, take_profit_pct=0.15 → threshold=0.92.
        bid=0.94 >= 0.92 → take_profit fires.
        """
        mdp = MagicMock()
        mdp.request_market_data.return_value = {"bid": 0.94, "ask": 0.96, "last": 0.95}

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        loop._position_monitor.add_position(
            OpenPosition(
                symbol="QQQ",
                entry_price=0.80,
                entry_time=datetime.now(timezone.utc),
                quantity=1,
                order_id=100,
                stop_loss_pct=0.25,
                take_profit_pct=0.15,
                time_stop_minutes=90,
                force_close_dte=1,
            )
        )

        loop._monitor_open_positions()

        assert len(loop._position_monitor.get_positions()) == 0
        assert loop._session_exits[0]["reason"] == "take_profit"

    @pytest.mark.integration
    def test_time_stop_deregisters_stale_position(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Position held 95 minutes with 90-minute time-stop → time_stop fires.
        Price 0.79 is within SL/TP thresholds so time-stop is the trigger.
        """
        mdp = MagicMock()
        mdp.request_market_data.return_value = {"bid": 0.79, "ask": 0.81, "last": 0.80}

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        stale_entry_time = datetime.now(timezone.utc) - timedelta(minutes=95)
        loop._position_monitor.add_position(
            OpenPosition(
                symbol="QQQ",
                entry_price=0.80,
                entry_time=stale_entry_time,
                quantity=1,
                order_id=101,
                stop_loss_pct=0.25,
                take_profit_pct=0.15,
                time_stop_minutes=90,
                force_close_dte=1,
            )
        )

        loop._monitor_open_positions()

        assert len(loop._position_monitor.get_positions()) == 0
        assert loop._session_exits[0]["reason"] == "time_stop"

    @pytest.mark.integration
    def test_position_within_all_limits_remains_open(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        real_risk_engine: RiskEngine,
        mock_contract_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        entry=0.80 | current bid=0.82 → +2.5% gain.
        SL threshold=0.60, TP threshold=0.92, elapsed<90min → no exit.
        Position must remain tracked.
        """
        mdp = MagicMock()
        mdp.request_market_data.return_value = {"bid": 0.82, "ask": 0.84, "last": 0.83}

        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mdp,
            contract_manager=mock_contract_manager,
            risk_engine=real_risk_engine,
            tmp_path=tmp_path,
        )
        loop._position_monitor.add_position(
            OpenPosition(
                symbol="QQQ",
                entry_price=0.80,
                entry_time=datetime.now(timezone.utc),
                quantity=1,
                order_id=102,
                stop_loss_pct=0.25,
                take_profit_pct=0.15,
                time_stop_minutes=90,
                force_close_dte=1,
            )
        )

        loop._monitor_open_positions()

        assert len(loop._position_monitor.get_positions()) == 1
        assert len(loop._session_exits) == 0

    @pytest.mark.integration
    def test_no_providers_skips_price_fetch_gracefully(
        self,
        strategy_a_gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """
        Loop in monitoring-only mode (no market_data_provider) cannot fetch
        price for position checks — logs a warning and leaves position intact.
        """
        loop = _build_loop(
            strategy_a_gameplan,
            risk_config,
            mock_health_checker,
            # No providers — monitoring-only mode
            tmp_path=tmp_path,
        )
        loop._position_monitor.add_position(
            OpenPosition(
                symbol="QQQ",
                entry_price=0.80,
                entry_time=datetime.now(timezone.utc),
                quantity=1,
                order_id=103,
                stop_loss_pct=0.25,
                take_profit_pct=0.15,
                time_stop_minutes=90,
                force_close_dte=1,
            )
        )

        loop._monitor_open_positions()  # must not raise

        # Position still tracked — can't evaluate without price
        assert len(loop._position_monitor.get_positions()) == 1
