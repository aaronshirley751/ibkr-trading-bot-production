"""
Unit tests for the TradingLoop execution pipeline.

Tests cover the full Market Data → Signal → Risk → Order sequence using
mocked dependencies. The _execute_pipeline_for_symbol method is called
directly in all tests to avoid spinning up the blocking run() loop.

Outcomes tested:
  hold                  — strategy returns HOLD direction
  rejected_confidence   — signal fires but confidence < 0.5
  rejected_affordability — affordability gate fails
  rejected_risk         — RiskEngine.pre_trade_check returns approved=False
  dry_run               — all gates pass, dry_run=True
  submitted             — all gates pass, dry_run=False, order placed
  error (market data)   — MarketDataProvider raises MarketDataError
  monitoring-only       — no pipeline providers supplied
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from src.bot.trading_loop import TradingLoop
from src.broker.exceptions import MarketDataError
from src.config.risk_config import DEFAULT_RISK_CONFIG, RiskConfig
from src.strategies.base import Direction, Signal, StrategyType

# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture
def gameplan() -> Dict[str, Any]:
    """Minimal Strategy A gameplan for pipeline tests."""
    return {
        "strategy": "A",
        "symbols": ["QQQ"],
        "regime": "trending",
        "bias": "bullish",
        "entry_window_start": "09:30",
        "entry_window_end": "16:00",
        "vix_at_analysis": 14.5,
        "vix_gate": {"threshold": 18.0, "check_time": "09:45"},
        "max_risk_per_trade": 18.0,
        "max_risk_ceiling": 36.0,
    }


@pytest.fixture
def risk_config() -> RiskConfig:
    return DEFAULT_RISK_CONFIG


@pytest.fixture
def mock_health_checker() -> MagicMock:
    hc = MagicMock()
    hc.check_port.return_value = True
    return hc


@pytest.fixture
def mock_market_data_provider() -> MagicMock:
    """Returns a mock provider with sensible market data defaults."""
    provider = MagicMock()
    provider.request_historical_data.return_value = _make_bars(30)
    provider.request_market_data.return_value = _make_quote()
    return provider


@pytest.fixture
def mock_contract_manager() -> MagicMock:
    cm = MagicMock()
    contract = MagicMock()
    contract.symbol = "QQQ"
    cm.qualify_contract.return_value = contract
    return cm


@pytest.fixture
def mock_risk_engine() -> MagicMock:
    engine = MagicMock()
    engine.pre_trade_check.return_value = {
        "approved": True,
        "checks_performed": ["pdt", "daily_loss", "risk_per_trade"],
        "rejection_reasons": [],
    }
    return engine


@pytest.fixture
def mock_order_manager() -> MagicMock:
    om = MagicMock()
    om.submit_order.return_value = 42  # fake order_id
    return om


# =============================================================================
# Helper builders
# =============================================================================


def _make_bars(n: int = 30, close: float = 480.0) -> List[Dict[str, Any]]:
    return [
        {
            "open": close - 0.10,
            "high": close + 0.20,
            "low": close - 0.15,
            "close": close + i * 0.05,
            "volume": 200_000,
            "average": close,
            "bar_count": 10,
        }
        for i in range(n)
    ]


def _make_quote(bid: float = 1.50, ask: float = 1.60, last: float = 1.55) -> Dict[str, Any]:
    return {
        "bid": bid,
        "ask": ask,
        "last": last,
        "volume": 50_000,
        "timestamp": datetime.now(timezone.utc),
        "snapshot": True,
    }


def _build_signal(
    direction: Direction = Direction.BUY,
    confidence: float = 0.75,
    symbol: str = "QQQ",
    entry_price: float = 480.0,
) -> Signal:
    return Signal(
        direction=direction,
        symbol=symbol,
        confidence=confidence,
        rationale="test signal",
        timestamp=datetime.now(timezone.utc),
        strategy_type=StrategyType.A,
        entry_price=entry_price,
        stop_loss=entry_price * 0.75,
        take_profit=entry_price * 1.15,
    )


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


# =============================================================================
# Pipeline — happy paths
# =============================================================================


class TestPipelineHold:
    """HOLD signal → trade log records outcome=hold."""

    @pytest.mark.unit
    def test_hold_signal_recorded(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            tmp_path=tmp_path,
        )

        hold_signal = _build_signal(direction=Direction.HOLD, confidence=0.0)
        with patch.object(loop._strategy_a, "evaluate", return_value=hold_signal):
            loop._execute_pipeline_for_symbol("QQQ")

        decisions = _read_log(tmp_path)
        assert len(decisions) == 1
        assert decisions[0]["outcome"] == "hold"
        assert decisions[0]["signal_direction"] == "hold"


class TestPipelineRejectedConfidence:
    """Signal fires but confidence < 0.5 → rejected_confidence."""

    @pytest.mark.unit
    def test_low_confidence_rejected(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            tmp_path=tmp_path,
        )

        weak_signal = _build_signal(direction=Direction.BUY, confidence=0.3)
        with patch.object(loop._strategy_a, "evaluate", return_value=weak_signal):
            loop._execute_pipeline_for_symbol("QQQ")

        decisions = _read_log(tmp_path)
        assert len(decisions) == 1
        assert decisions[0]["outcome"] == "rejected_confidence"
        # Risk engine should NOT have been called
        mock_risk_engine.pre_trade_check.assert_not_called()


class TestPipelineRejectedAffordability:
    """Premium exceeds ceiling → rejected_affordability."""

    @pytest.mark.unit
    def test_high_premium_rejected(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        tmp_path: Path,
    ) -> None:
        # Set ask higher than max_risk_ceiling (36.0)
        mock_market_data_provider.request_market_data.return_value = _make_quote(
            bid=40.0, ask=50.0, last=45.0
        )

        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            tmp_path=tmp_path,
        )

        strong_signal = _build_signal(direction=Direction.BUY, confidence=0.8, entry_price=45.0)
        with patch.object(loop._strategy_a, "evaluate", return_value=strong_signal):
            loop._execute_pipeline_for_symbol("QQQ")

        decisions = _read_log(tmp_path)
        assert len(decisions) == 1
        assert decisions[0]["outcome"] == "rejected_affordability"
        mock_risk_engine.pre_trade_check.assert_not_called()


class TestPipelineRejectedRisk:
    """Risk engine rejects → rejected_risk, order not submitted."""

    @pytest.mark.unit
    def test_risk_rejection_recorded(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_order_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        # Risk engine rejects PDT
        blocking_engine = MagicMock()
        blocking_engine.pre_trade_check.return_value = {
            "approved": False,
            "checks_performed": ["pdt_compliance"],
            "rejection_reasons": ["pdt_limit_reached"],
        }

        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=blocking_engine,
            order_manager=mock_order_manager,
            dry_run=False,
            tmp_path=tmp_path,
        )

        signal = _build_signal(direction=Direction.BUY, confidence=0.75)
        with patch.object(loop._strategy_a, "evaluate", return_value=signal):
            loop._execute_pipeline_for_symbol("QQQ")

        decisions = _read_log(tmp_path)
        assert len(decisions) == 1
        d = decisions[0]
        assert d["outcome"] == "rejected_risk"
        assert "pdt_limit_reached" in d["risk_rejections"]
        mock_order_manager.submit_order.assert_not_called()


class TestPipelineDryRun:
    """All gates pass but dry_run=True → outcome=dry_run, no broker call."""

    @pytest.mark.unit
    def test_dry_run_no_order_submitted(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        mock_order_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            order_manager=mock_order_manager,
            dry_run=True,
            tmp_path=tmp_path,
        )

        signal = _build_signal(direction=Direction.BUY, confidence=0.75)
        with patch.object(loop._strategy_a, "evaluate", return_value=signal):
            loop._execute_pipeline_for_symbol("QQQ")

        decisions = _read_log(tmp_path)
        assert len(decisions) == 1
        assert decisions[0]["outcome"] == "dry_run"
        assert decisions[0]["risk_approved"] is True
        mock_order_manager.submit_order.assert_not_called()


class TestPipelineLiveSubmitted:
    """All gates pass, dry_run=False → outcome=submitted, order_id recorded."""

    @pytest.mark.unit
    def test_order_submitted_and_logged(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        mock_order_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_order_manager.submit_order.return_value = 99

        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            order_manager=mock_order_manager,
            dry_run=False,
            tmp_path=tmp_path,
        )

        signal = _build_signal(direction=Direction.BUY, confidence=0.85)
        with patch.object(loop._strategy_a, "evaluate", return_value=signal):
            loop._execute_pipeline_for_symbol("QQQ")

        decisions = _read_log(tmp_path)
        assert len(decisions) == 1
        d = decisions[0]
        assert d["outcome"] == "submitted"
        assert d["order_id"] == 99
        assert d["risk_approved"] is True
        mock_order_manager.submit_order.assert_called_once()

    @pytest.mark.unit
    def test_pdt_recorded_on_submission(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        mock_order_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            order_manager=mock_order_manager,
            dry_run=False,
            tmp_path=tmp_path,
        )

        signal = _build_signal(direction=Direction.BUY, confidence=0.85)
        with patch.object(loop._strategy_a, "evaluate", return_value=signal):
            loop._execute_pipeline_for_symbol("QQQ")

        # Day-trade counter should have been incremented
        mock_risk_engine.record_day_trades.assert_called_once_with(1)


# =============================================================================
# Pipeline — error / edge cases
# =============================================================================


class TestPipelineMarketDataError:
    """MarketDataProvider raises → outcome=error, loop continues."""

    @pytest.mark.unit
    def test_market_data_error_recorded(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        tmp_path: Path,
    ) -> None:
        bad_provider = MagicMock()
        bad_provider.request_historical_data.side_effect = MarketDataError("timeout")

        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=bad_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            tmp_path=tmp_path,
        )

        loop._execute_pipeline_for_symbol("QQQ")

        decisions = _read_log(tmp_path)
        assert len(decisions) == 1
        assert decisions[0]["outcome"] == "error"
        assert "market_data_error" in decisions[0]["signal_rationale"]


class TestPipelineMonitoringOnly:
    """Without providers _pipeline_ready() returns False."""

    @pytest.mark.unit
    def test_pipeline_not_ready_without_providers(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            tmp_path=tmp_path,
        )
        assert loop._pipeline_ready() is False

    @pytest.mark.unit
    def test_pipeline_ready_with_all_providers(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            tmp_path=tmp_path,
        )
        assert loop._pipeline_ready() is True


# =============================================================================
# Position sizing helpers
# =============================================================================


class TestPositionSizing:
    """Unit tests for _compute_quantity and _get_stop_loss_pct."""

    def _loop(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> TradingLoop:
        return _build_loop(gameplan, risk_config, mock_health_checker, tmp_path=tmp_path)

    @pytest.mark.unit
    def test_stop_loss_pct_strategy_a(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = self._loop(gameplan, risk_config, mock_health_checker, tmp_path)
        loop.strategy = "A"
        assert loop._get_stop_loss_pct() == float(risk_config.stop_loss_pct_strategy_a)

    @pytest.mark.unit
    def test_stop_loss_pct_strategy_b(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = self._loop(gameplan, risk_config, mock_health_checker, tmp_path)
        loop.strategy = "B"
        assert loop._get_stop_loss_pct() == float(risk_config.stop_loss_pct_strategy_b)

    @pytest.mark.unit
    def test_compute_quantity_minimum_one(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Very high premium → quantity floored at 1."""
        loop = self._loop(gameplan, risk_config, mock_health_checker, tmp_path)
        qty = loop._compute_quantity(premium=9999.0)
        assert qty == 1

    @pytest.mark.unit
    def test_compute_quantity_scales_with_premium(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Lower premium allows more contracts (up to risk budget)."""
        loop = self._loop(gameplan, risk_config, mock_health_checker, tmp_path)
        qty_low = loop._compute_quantity(premium=0.10)
        qty_high = loop._compute_quantity(premium=5.00)
        assert qty_low > qty_high

    @pytest.mark.unit
    def test_compute_quantity_zero_premium_returns_one(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = self._loop(gameplan, risk_config, mock_health_checker, tmp_path)
        qty = loop._compute_quantity(premium=0.0)
        assert qty == 1


# =============================================================================
# Trade log
# =============================================================================


class TestTradeLogIntegration:
    """Verify the trade log file is written and parseable."""

    @pytest.mark.unit
    def test_log_file_created_on_first_decision(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            tmp_path=tmp_path,
        )

        hold = _build_signal(direction=Direction.HOLD, confidence=0.0)
        with patch.object(loop._strategy_a, "evaluate", return_value=hold):
            loop._execute_pipeline_for_symbol("QQQ")

        log_files = list((tmp_path / "logs").glob("trade_log_*.jsonl"))
        assert len(log_files) == 1

    @pytest.mark.unit
    def test_log_entry_contains_required_fields(
        self,
        gameplan: Dict[str, Any],
        risk_config: RiskConfig,
        mock_health_checker: MagicMock,
        mock_market_data_provider: MagicMock,
        mock_contract_manager: MagicMock,
        mock_risk_engine: MagicMock,
        tmp_path: Path,
    ) -> None:
        loop = _build_loop(
            gameplan,
            risk_config,
            mock_health_checker,
            market_data_provider=mock_market_data_provider,
            contract_manager=mock_contract_manager,
            risk_engine=mock_risk_engine,
            tmp_path=tmp_path,
        )

        hold = _build_signal(direction=Direction.HOLD, confidence=0.0)
        with patch.object(loop._strategy_a, "evaluate", return_value=hold):
            loop._execute_pipeline_for_symbol("QQQ")

        decisions = _read_log(tmp_path)
        d = decisions[0]
        for field in [
            "timestamp",
            "symbol",
            "strategy",
            "cycle_count",
            "signal_direction",
            "signal_confidence",
            "signal_rationale",
            "outcome",
        ]:
            assert field in d, f"Missing field: {field}"


# =============================================================================
# Utility
# =============================================================================


def _read_log(tmp_path: Path) -> List[Dict[str, Any]]:
    """Read all JSONL decision lines from the tmp log directory."""
    log_files = list((tmp_path / "logs").glob("trade_log_*.jsonl"))
    if not log_files:
        return []
    entries = []
    for lf in log_files:
        for line in lf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
