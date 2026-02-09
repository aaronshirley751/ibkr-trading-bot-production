# VSC HANDOFF: Task 1.1.7 — End-to-End System Tests

**Date**: 2026-02-07
**Requested By**: Phase 1 Sprint (Task 1.1.7)
**Model Recommendation**: Opus (complex multi-layer integration design)
**Context Budget**: Heavy (three test files, cross-layer orchestration, extensive safety scenarios)
**Extended Thinking**: Recommended for failure scenario modeling
**Lead Personas**: @Systems_Architect + @QA_Lead + @CRO

---

## Agent Execution Block

### Preamble

This blueprint specifies the End-to-End (E2E) system test suite — the integration gate between individual layer testing (Tasks 1.1.3–1.1.6) and live validation (Task 1.1.8). E2E tests validate that all layers compose correctly into a functioning trading system with proper safety guarantees.

**Critical Distinction from Layer Tests:**
- Layer tests validate individual components in isolation with mocked dependencies
- E2E tests validate the *full orchestration path* with all real components wired together (except the actual IBKR Gateway, which remains mocked)
- E2E tests are the closest approximation to production behavior before live validation

**Dependency Gate:** All four layer test suites must pass before E2E tests are meaningful:
- ✅ 1.1.3 — Broker Layer (92%+ coverage)
- ✅ 1.1.4 — Strategy Layer (85%+ coverage)
- ✅ 1.1.5 — Risk Layer (98%+ coverage, @CRO signed off)
- ✅ 1.1.6 — Execution Layer (90%+ coverage)

---

## 1. OBJECTIVE

Implement the E2E system test suite validating complete trading workflows from gameplan ingestion through position closure. Three test files cover: (1) daily gameplan loading and configuration application, (2) full trade cycle orchestration across all layers, and (3) safety mechanism enforcement under realistic failure scenarios. Tests must prove that the system defaults to Strategy C (cash preservation) on *any* component failure, data quality issue, or risk limit breach — with no exceptions and no inference.

---

## 2. FILE STRUCTURE

**Create:**
```
tests/e2e/conftest.py                          # E2E-specific fixtures (orchestrator, full gameplan, multi-layer mocks)
tests/e2e/test_daily_gameplan_ingestion.py      # Gameplan loading, validation, parameter application
tests/e2e/test_full_trade_cycle.py              # Complete trade lifecycle across all layers
tests/e2e/test_safety_scenarios.py              # Safety mechanism enforcement under failure conditions
```

**Modify:**
- `tests/e2e/__init__.py` — Update docstring to reflect implemented status (remove TODO)

**Existing Infrastructure (consumed, not modified):**
- `tests/conftest.py` — Root fixtures (account params, snapshot data, gameplan samples)
- `tests/broker/conftest.py` — Broker mocks (MockIBConnection, MockGateway)
- `tests/strategy/conftest.py` — Strategy fixtures (signal factories, market data builders)
- `tests/risk/conftest.py` — Risk fixtures (RiskEngine factory, mock broker/notifier)
- `tests/execution/conftest.py` — Execution fixtures (sample signals, sample positions)
- `tests/helpers/` — Assertions, builders, mocks

---

## 3. LOGIC FLOW (PSEUDO-CODE)

### 3.0 E2E Fixtures (`conftest.py`)

The E2E conftest provides composite fixtures that wire all layers together — broker, strategy, risk, and execution — into a complete orchestrator. These are *not* mocks of individual components; they are the real component implementations connected via mocked external dependencies (IBKR Gateway).

```python
# ============================================================
# E2E CONFTEST — Composite Fixtures
# ============================================================

import pytest
import json
import copy
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import real components (not mocks — that's the point of E2E)
from src.broker import IBKRConnection, ContractManager, MarketDataProvider
from src.strategy.selection import select_strategy
from src.strategy.momentum import MomentumStrategy
from src.strategy.mean_reversion import MeanReversionStrategy
from src.risk.position_sizer import PositionSizer
from src.risk.guards import RiskManager
from src.execution.engine import ExecutionEngine
from src.bot.orchestrator import TradingOrchestrator
from src.bot.gameplan import GameplanLoader


# --- Gameplan Fixtures ---

@pytest.fixture
def valid_strategy_a_gameplan():
    """
    Complete, valid Strategy A gameplan matching daily_gameplan.json schema.
    All fields populated with realistic values for a normal VIX regime.
    """
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "bias": "bullish",
        "expected_behavior": "trending",
        "key_levels": {
            "spy_support": 585.50,
            "spy_resistance": 596.09,
            "spy_pivot": 590.00,
            "qqq_support": 518.88,
            "qqq_resistance": 537.01,
            "qqq_pivot": 522.00
        },
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "low",
        "alert_message": "Strategy A — SPY momentum, normal regime",
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:10:00-05:00"
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 3,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2
        },
        "scorecard": {
            "yesterday_pnl": 0.0,
            "yesterday_hit_rate": 0.0,
            "regime_accuracy": True,
            "weekly_cumulative_pnl": 0.0
        }
    }


@pytest.fixture
def valid_strategy_b_gameplan():
    """
    Complete, valid Strategy B gameplan for elevated VIX regime.
    """
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "elevated",
        "strategy": "B",
        "symbols": ["SPY"],
        "position_size_multiplier": 0.5,
        "vix_at_analysis": 22.0,
        "vix_source_verified": True,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "key_levels": {
            "spy_support": 575.00,
            "spy_resistance": 590.00,
            "spy_pivot": 582.00,
            "qqq_support": 510.00,
            "qqq_resistance": 525.00,
            "qqq_pivot": 517.00
        },
        "catalysts": [],
        "earnings_blackout": [],
        "geo_risk": "medium",
        "alert_message": "Strategy B — SPY mean reversion, elevated regime",
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:10:00-05:00"
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 2,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2
        },
        "scorecard": {
            "yesterday_pnl": -12.50,
            "yesterday_hit_rate": 0.0,
            "regime_accuracy": True,
            "weekly_cumulative_pnl": -12.50
        }
    }


@pytest.fixture
def valid_strategy_c_gameplan():
    """
    Strategy C gameplan — cash preservation / no-trade mode.
    This is what the system should produce when ANY safety condition triggers.
    """
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "crisis",
        "strategy": "C",
        "symbols": [],
        "position_size_multiplier": 0.0,
        "vix_at_analysis": 28.5,
        "vix_source_verified": True,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "key_levels": {
            "spy_support": 560.00,
            "spy_resistance": 580.00,
            "spy_pivot": 570.00,
            "qqq_support": 490.00,
            "qqq_resistance": 510.00,
            "qqq_pivot": 500.00
        },
        "catalysts": ["VIX > 25 — crisis regime"],
        "earnings_blackout": [],
        "geo_risk": "high",
        "alert_message": "Strategy C LOCKED — crisis regime, cash preservation only",
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:10:00-05:00"
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 1,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2
        },
        "scorecard": {
            "yesterday_pnl": -45.00,
            "yesterday_hit_rate": 0.25,
            "regime_accuracy": False,
            "weekly_cumulative_pnl": -72.00
        }
    }


@pytest.fixture
def malformed_gameplan_missing_strategy():
    """Gameplan with 'strategy' field missing entirely."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        # "strategy" key intentionally missing
        "symbols": ["SPY"],
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 2,
        }
    }


@pytest.fixture
def malformed_gameplan_invalid_strategy():
    """Gameplan with invalid strategy value."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "D",  # Invalid — only A, B, C are valid
        "symbols": ["SPY"],
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 2,
        }
    }


@pytest.fixture
def malformed_gameplan_missing_hard_limits():
    """Gameplan with hard_limits section missing entirely."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        # "hard_limits" key intentionally missing
    }


@pytest.fixture
def gameplan_with_quarantine():
    """Gameplan where data_quality.quarantine_active is True."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "data_quality": {
            "quarantine_active": True,
            "stale_fields": ["vix", "spy_price"],
            "last_verified": "2026-02-07T08:30:00-05:00"
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 3,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2
        }
    }


@pytest.fixture
def gameplan_with_weekly_governor():
    """Gameplan where weekly drawdown governor is active."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",  # Note: strategy says A but governor should force C
        "symbols": ["SPY"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:10:00-05:00"
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 3,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": True,  # GOVERNOR ACTIVE
            "max_intraday_pivots": 2
        },
        "scorecard": {
            "yesterday_pnl": -50.00,
            "yesterday_hit_rate": 0.0,
            "regime_accuracy": False,
            "weekly_cumulative_pnl": -95.00  # 15.8% drawdown — past 15% threshold
        }
    }


@pytest.fixture
def gameplan_with_zero_pdt():
    """Gameplan where all PDT trades are exhausted."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:10:00-05:00"
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 0,  # EXHAUSTED
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2
        }
    }


@pytest.fixture
def gameplan_with_earnings_blackout():
    """Gameplan where SPY is in earnings blackout (for ETF rebalancing scenario)."""
    return {
        "date": "2026-02-07",
        "session_id": "gauntlet_20260207_0910",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY", "QQQ"],
        "position_size_multiplier": 1.0,
        "vix_at_analysis": 15.44,
        "vix_source_verified": True,
        "earnings_blackout": ["SPY"],  # SPY blacklisted
        "data_quality": {
            "quarantine_active": False,
            "stale_fields": [],
            "last_verified": "2026-02-07T09:10:00-05:00"
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": 3,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": False,
            "max_intraday_pivots": 2
        }
    }


# --- Market Data Fixtures ---

@pytest.fixture
def trending_spy_market_data():
    """
    SPY market data showing bullish momentum:
    - Price above VWAP
    - EMA(8) > EMA(21) (bullish crossover)
    - RSI at 58 (momentum without overbought)
    """
    return {
        "symbol": "SPY",
        "last": 592.50,
        "bid": 592.45,
        "ask": 592.55,
        "volume": 45_000_000,
        "vwap": 590.00,
        "ema_8": 591.80,
        "ema_21": 589.50,
        "rsi": 58.0,
        "bollinger_upper": 598.00,
        "bollinger_lower": 582.00,
        "high": 594.00,
        "low": 588.00,
        "open": 589.00,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def mean_reverting_spy_market_data():
    """
    SPY market data showing oversold conditions:
    - RSI at 28 (deep oversold)
    - Price touching lower Bollinger band
    """
    return {
        "symbol": "SPY",
        "last": 578.00,
        "bid": 577.90,
        "ask": 578.10,
        "volume": 65_000_000,
        "vwap": 582.00,
        "ema_8": 579.50,
        "ema_21": 583.00,
        "rsi": 28.0,
        "bollinger_upper": 592.00,
        "bollinger_lower": 578.20,
        "high": 584.00,
        "low": 577.50,
        "open": 583.00,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def flat_spy_market_data():
    """
    SPY market data showing no clear signal:
    - RSI neutral (50)
    - Price near VWAP
    - No EMA crossover
    """
    return {
        "symbol": "SPY",
        "last": 590.00,
        "bid": 589.95,
        "ask": 590.05,
        "volume": 30_000_000,
        "vwap": 590.10,
        "ema_8": 590.00,
        "ema_21": 590.00,
        "rsi": 50.0,
        "bollinger_upper": 596.00,
        "bollinger_lower": 584.00,
        "high": 591.50,
        "low": 588.50,
        "open": 589.50,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def stale_market_data():
    """
    Market data with a stale timestamp (> 5 minutes old).
    Should trigger data quality concerns.
    """
    return {
        "symbol": "SPY",
        "last": 590.00,
        "bid": 589.90,
        "ask": 590.10,
        "volume": 30_000_000,
        "vwap": 590.00,
        "ema_8": 590.00,
        "ema_21": 590.00,
        "rsi": 50.0,
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    }


# --- Orchestrator Fixtures ---

@pytest.fixture
def mock_gateway():
    """
    Fully mocked IBKR Gateway that simulates realistic responses.
    This is the ONLY mock in E2E tests — everything else is real components.
    """
    gateway = MagicMock()
    gateway.isConnected.return_value = True
    gateway.connect.return_value = None
    gateway.disconnect.return_value = None

    # Mock contract qualification
    from ib_insync import Stock
    qualified = Stock("SPY", "SMART", "USD")
    qualified.conId = 756733
    gateway.qualifyContracts.return_value = [qualified]

    # Default market data response (normal conditions)
    ticker = MagicMock()
    ticker.last = 592.50
    ticker.bid = 592.45
    ticker.ask = 592.55
    ticker.volume = 45_000_000
    ticker.time = datetime.now(timezone.utc)
    gateway.reqMktData.return_value = ticker

    # Order submission response
    gateway.placeOrder.return_value = Mock(
        orderId=10001,
        status="Submitted"
    )

    return gateway


@pytest.fixture
def mock_notifier():
    """Mock Discord webhook notifier."""
    notifier = MagicMock()
    notifier.send_alert.return_value = True
    notifier.send_trade_notification.return_value = True
    notifier.send_daily_summary.return_value = True
    return notifier


@pytest.fixture
def trading_orchestrator(mock_gateway, mock_notifier, valid_strategy_a_gameplan):
    """
    Full TradingOrchestrator wired with real components and mocked Gateway.
    This is the primary E2E test subject.
    """
    # Wire real components with mocked external dependency
    connection = IBKRConnection(host="127.0.0.1", port=4002, client_id=1)

    with patch.object(connection, "_ib", mock_gateway):
        contract_mgr = ContractManager(connection)
        market_data = MarketDataProvider(connection, contract_mgr, snapshot_mode=True)
        risk_mgr = RiskManager(
            account_balance=600.0,
            max_daily_loss_pct=0.10,
            max_weekly_drawdown_pct=0.15,
            pdt_limit=3
        )
        position_sizer = PositionSizer(
            account_balance=600.0,
            max_position_pct=0.20,
            max_risk_pct=0.03,
            pdt_limit=3
        )
        execution = ExecutionEngine(
            broker=connection,
            strategy=None,  # Set per-cycle based on gameplan
            risk_manager=risk_mgr
        )

        orchestrator = TradingOrchestrator(
            broker=connection,
            contract_manager=contract_mgr,
            market_data=market_data,
            risk_manager=risk_mgr,
            position_sizer=position_sizer,
            execution_engine=execution,
            notifier=mock_notifier,
            gameplan=valid_strategy_a_gameplan
        )

        yield orchestrator
```

### 3.1 Gameplan Ingestion Tests (`test_daily_gameplan_ingestion.py`)

```python
# ============================================================
# FILE: tests/e2e/test_daily_gameplan_ingestion.py
# PURPOSE: Validate gameplan loading, parsing, validation,
#          and configuration application across all layers
# ============================================================

"""
E2E tests for daily gameplan ingestion.

Tests cover:
- Loading daily_gameplan.json from file system
- Validating all required fields against schema
- Applying gameplan parameters to runtime configuration
- Strategy C default on missing/malformed gameplan
- Data quality quarantine enforcement
- Hard limit propagation to risk engine
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.bot.gameplan import GameplanLoader, GameplanValidationError
from src.bot.orchestrator import TradingOrchestrator


# =================================================================
# GAMEPLAN LOADING — File I/O and Basic Parsing
# =================================================================


class TestGameplanFileLoading:
    """Tests for gameplan file discovery and JSON parsing."""

    def test_load_valid_gameplan_from_file(self, valid_strategy_a_gameplan, tmp_path):
        """
        GIVEN: Valid daily_gameplan.json exists at expected path
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns parsed gameplan dict with all fields intact
        """
        filepath = tmp_path / "daily_gameplan.json"
        filepath.write_text(json.dumps(valid_strategy_a_gameplan))

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "A"
        assert result["regime"] == "normal"
        assert result["date"] == "2026-02-07"
        assert result["hard_limits"]["pdt_trades_remaining"] == 3

    def test_load_missing_gameplan_file_returns_strategy_c(self, tmp_path):
        """
        GIVEN: No daily_gameplan.json exists at expected path
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns Strategy C default gameplan
        AND: Logs warning about missing gameplan

        @CRO: CRITICAL — missing gameplan MUST default to cash preservation.
        """
        filepath = tmp_path / "nonexistent_gameplan.json"

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "C"
        assert result["symbols"] == []

    def test_load_corrupted_json_returns_strategy_c(self, tmp_path):
        """
        GIVEN: Gameplan file exists but contains invalid JSON
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns Strategy C default gameplan
        AND: Logs error about JSON parse failure
        """
        filepath = tmp_path / "daily_gameplan.json"
        filepath.write_text("{invalid json content: broken,,,")

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "C"

    def test_load_empty_file_returns_strategy_c(self, tmp_path):
        """
        GIVEN: Gameplan file exists but is empty (0 bytes)
        WHEN: GameplanLoader.load(path) is called
        THEN: Returns Strategy C default
        """
        filepath = tmp_path / "daily_gameplan.json"
        filepath.write_text("")

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "C"

    def test_load_gameplan_with_unicode_bom(self, valid_strategy_a_gameplan, tmp_path):
        """
        GIVEN: Gameplan file has UTF-8 BOM prefix (\ufeff)
        WHEN: GameplanLoader.load(path) is called
        THEN: Parses correctly despite BOM

        Edge case: Windows Notepad saves with BOM by default.
        """
        filepath = tmp_path / "daily_gameplan.json"
        content = "\ufeff" + json.dumps(valid_strategy_a_gameplan)
        filepath.write_text(content, encoding="utf-8-sig")

        loader = GameplanLoader()
        result = loader.load(filepath)

        assert result["strategy"] == "A"


# =================================================================
# GAMEPLAN VALIDATION — Schema Compliance
# =================================================================


class TestGameplanValidation:
    """Tests for gameplan structural and semantic validation."""

    def test_valid_strategy_a_passes_validation(self, valid_strategy_a_gameplan):
        """
        GIVEN: Complete, valid Strategy A gameplan
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Returns True (validation passes)
        """
        loader = GameplanLoader()
        assert loader.validate(valid_strategy_a_gameplan) is True

    def test_valid_strategy_b_passes_validation(self, valid_strategy_b_gameplan):
        """
        GIVEN: Complete, valid Strategy B gameplan
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Returns True
        """
        loader = GameplanLoader()
        assert loader.validate(valid_strategy_b_gameplan) is True

    def test_valid_strategy_c_passes_validation(self, valid_strategy_c_gameplan):
        """
        GIVEN: Complete, valid Strategy C gameplan
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Returns True
        """
        loader = GameplanLoader()
        assert loader.validate(valid_strategy_c_gameplan) is True

    def test_missing_strategy_field_fails_validation(self, malformed_gameplan_missing_strategy):
        """
        GIVEN: Gameplan missing the 'strategy' field
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Raises GameplanValidationError
        """
        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="strategy"):
            loader.validate(malformed_gameplan_missing_strategy)

    def test_invalid_strategy_value_fails_validation(self, malformed_gameplan_invalid_strategy):
        """
        GIVEN: Gameplan with strategy="D" (not in {A, B, C})
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Raises GameplanValidationError
        """
        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="strategy"):
            loader.validate(malformed_gameplan_invalid_strategy)

    def test_missing_hard_limits_fails_validation(self, malformed_gameplan_missing_hard_limits):
        """
        GIVEN: Gameplan missing the 'hard_limits' section
        WHEN: GameplanLoader.validate(gameplan) is called
        THEN: Raises GameplanValidationError

        @CRO: CRITICAL — hard limits are non-negotiable. A gameplan without
        them is structurally unsafe.
        """
        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="hard_limits"):
            loader.validate(malformed_gameplan_missing_hard_limits)

    def test_missing_data_quality_fails_validation(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan missing 'data_quality' section
        WHEN: Validated
        THEN: Fails — data quality is required for safety decisions
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        del gameplan["data_quality"]

        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="data_quality"):
            loader.validate(gameplan)

    def test_negative_pdt_remaining_fails_validation(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan with pdt_trades_remaining = -1
        WHEN: Validated
        THEN: Fails — negative PDT count is invalid
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["hard_limits"]["pdt_trades_remaining"] = -1

        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="pdt"):
            loader.validate(gameplan)

    def test_max_daily_loss_exceeds_100_percent_fails(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan with max_daily_loss_pct = 1.5 (150%)
        WHEN: Validated
        THEN: Fails — cannot lose more than 100% in a day
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["hard_limits"]["max_daily_loss_pct"] = 1.5

        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError):
            loader.validate(gameplan)

    def test_strategy_a_with_empty_symbols_fails(self, valid_strategy_a_gameplan):
        """
        GIVEN: Strategy A gameplan but symbols list is empty
        WHEN: Validated
        THEN: Fails — Strategy A requires at least one symbol
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["symbols"] = []

        loader = GameplanLoader()
        with pytest.raises(GameplanValidationError, match="symbols"):
            loader.validate(gameplan)

    def test_strategy_c_with_empty_symbols_passes(self, valid_strategy_c_gameplan):
        """
        GIVEN: Strategy C gameplan with empty symbols list
        WHEN: Validated
        THEN: Passes — Strategy C explicitly has no symbols
        """
        loader = GameplanLoader()
        assert loader.validate(valid_strategy_c_gameplan) is True


# =================================================================
# GAMEPLAN PARAMETER APPLICATION — Runtime Config
# =================================================================


class TestGameplanParameterApplication:
    """Tests for applying gameplan parameters to the orchestrator."""

    def test_strategy_a_params_applied_to_risk_engine(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Valid Strategy A gameplan loaded
        WHEN: Orchestrator.apply_gameplan(gameplan) is called
        THEN: Risk engine configured with Strategy A limits:
              - max_risk_pct = 0.03 (3%)
              - max_position_pct = 0.20 (20%)
              - take_profit = 0.15 (15%)
              - stop_loss = 0.25 (25%)
        """
        # Build orchestrator and apply gameplan
        # Assert risk_manager has correct params from Strategy A library
        pass  # Implementation follows pattern — detailed pseudo-code here

    def test_strategy_b_params_differ_from_strategy_a(
        self, valid_strategy_b_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Valid Strategy B gameplan loaded
        WHEN: Orchestrator.apply_gameplan(gameplan) is called
        THEN: Risk engine configured with Strategy B limits:
              - max_risk_pct = 0.02 (2% — stricter than A)
              - max_position_pct = 0.10 (10% — half of A)
              - take_profit = 0.08 (8% — quicker scalp)
              - stop_loss = 0.15 (15% — tighter than A)
        """
        pass

    def test_hard_limits_propagate_to_risk_engine(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan with hard_limits.max_daily_loss_pct = 0.10
        WHEN: Applied to orchestrator
        THEN: risk_manager.max_daily_loss_pct == 0.10
        AND: risk_manager.max_single_position == 120
        AND: risk_manager.pdt_trades_remaining == 3
        """
        pass

    def test_pdt_remaining_passed_to_risk_engine(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan with pdt_trades_remaining = 2
        WHEN: Applied to orchestrator
        THEN: Risk engine tracks exactly 2 remaining day trades
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["hard_limits"]["pdt_trades_remaining"] = 2
        pass

    def test_position_size_multiplier_scales_max_position(
        self, valid_strategy_a_gameplan
    ):
        """
        GIVEN: Gameplan with position_size_multiplier = 0.5
        WHEN: Applied to orchestrator
        THEN: Effective max position = $120 * 0.5 = $60
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["position_size_multiplier"] = 0.5
        pass

    def test_key_levels_available_to_strategy_engine(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan with key_levels populated
        WHEN: Applied to orchestrator
        THEN: Strategy engine can access support/resistance/pivot levels
        """
        pass


# =================================================================
# SAFETY OVERRIDES — Gameplan Fields That Force Strategy C
# =================================================================


class TestGameplanSafetyOverrides:
    """
    Tests for gameplan conditions that MUST force Strategy C
    regardless of what the 'strategy' field says.

    @CRO: Every one of these is a CRITICAL safety assertion.
    """

    def test_quarantine_active_forces_strategy_c(self, gameplan_with_quarantine):
        """
        GIVEN: Gameplan with data_quality.quarantine_active = True
        WHEN: Orchestrator processes gameplan
        THEN: Strategy forced to C regardless of gameplan.strategy field
        AND: No orders are submitted
        AND: Alert sent via notifier

        @CRO: Data quarantine is an absolute gate. Strategy A in the gameplan
        is irrelevant — quarantine = cash preservation, no exceptions.
        """
        pass

    def test_weekly_governor_active_forces_strategy_c(self, gameplan_with_weekly_governor):
        """
        GIVEN: Gameplan with hard_limits.weekly_drawdown_governor_active = True
        WHEN: Orchestrator processes gameplan
        THEN: Strategy forced to C for remainder of week
        AND: No new entries permitted
        """
        pass

    def test_zero_pdt_remaining_blocks_new_entries(self, gameplan_with_zero_pdt):
        """
        GIVEN: Gameplan with pdt_trades_remaining = 0
        WHEN: Orchestrator attempts to open new position
        THEN: Entry blocked (no new day trades allowed)
        AND: Closing existing positions still permitted
        """
        pass

    def test_earnings_blackout_excludes_symbol(self, gameplan_with_earnings_blackout):
        """
        GIVEN: Gameplan with earnings_blackout = ["SPY"]
        AND: Strategy targets SPY and QQQ
        WHEN: Orchestrator generates signals
        THEN: SPY signals are suppressed
        AND: QQQ signals may proceed (if not blacklisted)
        """
        pass

    def test_vix_source_unverified_triggers_caution(self, valid_strategy_a_gameplan):
        """
        GIVEN: Gameplan with vix_source_verified = False
        WHEN: Orchestrator processes gameplan
        THEN: Position size multiplier reduced OR strategy downgraded
        AND: Warning logged
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["vix_source_verified"] = False
        pass
```

### 3.2 Full Trade Cycle Tests (`test_full_trade_cycle.py`)

```python
# ============================================================
# FILE: tests/e2e/test_full_trade_cycle.py
# PURPOSE: Validate complete trading lifecycle from signal
#          generation through position closure, across all layers
# ============================================================

"""
E2E tests for complete trading cycle.

Tests cover:
- Full workflow: gameplan → signal → risk check → order → fill → tracking → exit
- Strategy A cycle (momentum breakout)
- Strategy B cycle (mean reversion fade)
- Strategy C behavior (cash preservation — no trades)
- Multi-symbol sessions (SPY + QQQ)
- Strategy transitions (A → B → C based on regime changes)
- Exit path validation (take-profit, stop-loss, time-stop)
- State persistence across cycles within a session
"""

import pytest
import copy
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, call

from src.bot.orchestrator import TradingOrchestrator
from src.bot.gameplan import GameplanLoader


# =================================================================
# STRATEGY A — COMPLETE MOMENTUM BREAKOUT CYCLE
# =================================================================


class TestStrategyAFullCycle:
    """Full trade cycle tests for Strategy A (momentum breakout)."""

    def test_strategy_a_entry_to_exit_profitable(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy A gameplan, bullish SPY data (EMA8 > EMA21, RSI 58, Price > VWAP)
        WHEN: Orchestrator runs one complete cycle
        THEN:
          1. Strategy generates BUY signal with confidence > 0.5
          2. Risk manager approves (position size within limits)
          3. Order submitted to broker (LMT order, ATM call)
          4. Fill confirmed → position opened
          5. Take-profit hit (15%) → position closed
          6. Realized P&L recorded (positive)
          7. PDT count incremented by 1
        """
        pass

    def test_strategy_a_entry_to_stop_loss(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy A gameplan, initial bullish signal
        WHEN: Position opened, then price drops 25% (stop-loss level)
        THEN:
          1. Stop-loss triggers position closure
          2. Realized P&L recorded (negative, max $18)
          3. Daily loss tracked in risk engine
          4. PDT count incremented

        @CRO: Max loss MUST NOT exceed $18 (3% of $600).
        """
        pass

    def test_strategy_a_entry_to_time_stop(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy A gameplan, position opened
        WHEN: 90 minutes elapse without take-profit or stop-loss
        THEN:
          1. Time stop triggers position closure at market
          2. P&L recorded (may be positive or negative)
          3. Position closed regardless of current price
        """
        pass

    def test_strategy_a_no_signal_generated(
        self, valid_strategy_a_gameplan, flat_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy A gameplan, but SPY shows no momentum
              (RSI 50, no EMA crossover, price at VWAP)
        WHEN: Orchestrator runs cycle
        THEN:
          1. Strategy evaluates data → no signal (confidence < threshold)
          2. No order submitted
          3. No position opened
          4. PDT count unchanged
        """
        pass

    def test_strategy_a_risk_rejects_oversized_position(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy A signal generated, but premium exceeds max position ($120)
        WHEN: Risk manager evaluates position size
        THEN:
          1. Risk check fails (position too large)
          2. No order submitted
          3. Log: "Risk check failed: position exceeds max"
        """
        pass

    def test_strategy_a_multi_symbol_spy_and_qqq(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy A gameplan with symbols = ["SPY", "QQQ"]
        AND: Both symbols showing momentum
        WHEN: Orchestrator evaluates both symbols
        THEN:
          1. Signals generated for each independently
          2. Risk checks account for aggregate position
          3. Total exposure does not exceed account limits
          4. PDT count tracks both trades
        """
        gameplan = copy.deepcopy(valid_strategy_a_gameplan)
        gameplan["symbols"] = ["SPY", "QQQ"]
        pass


# =================================================================
# STRATEGY B — COMPLETE MEAN REVERSION CYCLE
# =================================================================


class TestStrategyBFullCycle:
    """Full trade cycle tests for Strategy B (mean reversion fade)."""

    def test_strategy_b_entry_to_exit_profitable(
        self, valid_strategy_b_gameplan, mean_reverting_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy B gameplan, oversold SPY (RSI 28, touching lower BB)
        WHEN: Orchestrator runs complete cycle
        THEN:
          1. Strategy generates BUY signal (oversold fade)
          2. Risk check: position max 10% ($60), risk max 2% ($12)
          3. Order: 1 strike OTM, min 5 DTE
          4. Take-profit at 8% → position closed
          5. Realized P&L positive

        @CRO: Strategy B uses tighter limits than A — verify 10%/$60 cap.
        """
        pass

    def test_strategy_b_tighter_stop_loss_than_a(
        self, valid_strategy_b_gameplan, mean_reverting_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy B position opened
        WHEN: Price moves against position by 15% (Strategy B stop)
        THEN: Stop-loss triggers at 15% (not 25% which is Strategy A's level)

        @CRO: Strategy B stop-loss is 15%, not 25%. Cross-contamination
        between strategy parameters would be a critical bug.
        """
        pass

    def test_strategy_b_shorter_time_stop(
        self, valid_strategy_b_gameplan, mean_reverting_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy B position opened
        WHEN: 45 minutes elapse (Strategy B time stop)
        THEN: Position closed (time stop at 45 min, not 90 min like A)
        """
        pass

    def test_strategy_b_spy_only_symbol_restriction(
        self, valid_strategy_b_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy B gameplan
        WHEN: symbols contains QQQ
        THEN: QQQ is filtered out — Strategy B trades SPY only
        """
        gameplan = copy.deepcopy(valid_strategy_b_gameplan)
        gameplan["symbols"] = ["SPY", "QQQ"]
        # After applying, only SPY should be in active symbols
        pass


# =================================================================
# STRATEGY C — CASH PRESERVATION BEHAVIOR
# =================================================================


class TestStrategyCBehavior:
    """Tests for Strategy C (no trading) behavior."""

    def test_strategy_c_no_new_orders(
        self, valid_strategy_c_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy C gameplan loaded
        WHEN: Orchestrator runs cycle
        THEN: NO orders submitted to broker
        AND: broker.placeOrder() never called
        """
        pass

    def test_strategy_c_closes_existing_positions_at_3dte(
        self, valid_strategy_c_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy C active, existing position with 3 DTE
        WHEN: Orchestrator evaluates open positions
        THEN: Position closed (force-close at DTE threshold)
        """
        pass

    def test_strategy_c_emergency_stop_at_40pct(
        self, valid_strategy_c_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy C active, existing position showing -40% loss
        WHEN: Orchestrator evaluates open positions
        THEN: Emergency stop triggers immediate closure
        AND: Alert sent via notifier

        @CRO: 40% emergency stop is the absolute last line of defense.
        """
        pass

    def test_strategy_c_alert_only_mode(
        self, valid_strategy_c_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy C active
        WHEN: Market data processed
        THEN: Monitoring continues (data logged)
        AND: No orders placed
        AND: Status alerts sent to Discord
        """
        pass


# =================================================================
# STRATEGY TRANSITIONS — Regime Changes Mid-Session
# =================================================================


class TestStrategyTransitions:
    """Tests for mid-session strategy changes based on VIX regime shifts."""

    def test_transition_a_to_c_on_vix_spike(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Running Strategy A (VIX 15.44)
        WHEN: VIX spikes to 28 (crisis regime)
        THEN:
          1. Strategy transitions to C
          2. No new orders
          3. Existing positions managed per Strategy C rules
          4. Pivot count incremented
          5. Alert sent via notifier
        """
        pass

    def test_transition_a_to_b_on_vix_rise(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Running Strategy A (VIX 15.44)
        WHEN: VIX rises to 22 (elevated regime)
        THEN:
          1. Strategy transitions to B
          2. Position limits tighten (20% → 10%)
          3. Risk limits tighten (3% → 2%)
          4. Pivot count incremented
        """
        pass

    def test_two_pivots_locks_strategy_c(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy A → pivot to B (VIX rise) → pivot to A (VIX drop)
        WHEN: Third regime change occurs
        THEN: Strategy C locked for remainder of day (2-pivot limit exceeded)

        @CRO: 2-pivot limit is hard-coded. After 2 pivots, no more transitions.
        """
        pass

    def test_strategy_c_lock_is_sticky(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy C locked via governor/quarantine/pivot-limit
        WHEN: Conditions improve (VIX drops, data quality restored)
        THEN: Strategy C remains locked for the session
        AND: No automatic upgrade to A or B
        """
        pass


# =================================================================
# EXIT PATH VALIDATION — All Three Exit Mechanisms
# =================================================================


class TestExitPaths:
    """Tests for all exit path mechanics."""

    def test_take_profit_exit_calculates_correct_pnl(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Position opened at premium $3.00
        WHEN: Premium rises to $3.45 (15% take-profit for Strategy A)
        THEN: Position closed, realized P&L = ($3.45 - $3.00) * 100 * 1 = $45.00
        """
        pass

    def test_stop_loss_exit_limits_damage(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Position opened at premium $3.00
        WHEN: Premium drops to $2.25 (25% stop-loss for Strategy A)
        THEN: Position closed, realized P&L = ($2.25 - $3.00) * 100 * 1 = -$75.00
        WAIT: But max risk per trade is $18. HOW?

        NOTE: Position sizing should ensure that even a full stop-loss hit
        stays within the $18 risk budget. If premium=$3.00 and stop=25%,
        max quantity = $18 / ($3.00 * 0.25 * 100) = 0.24 contracts → 0.
        This test validates that position sizing PREVENTS opening a position
        where a stop-loss would exceed the risk budget.

        @CRO: This is the fundamental position sizing constraint.
        """
        pass

    def test_time_stop_exit_at_market_price(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy A position, 90 minutes elapsed
        WHEN: Time stop triggers
        THEN: Market order placed to close position
        AND: P&L calculated at current market price (not limit)
        """
        pass

    def test_force_close_at_dte_threshold(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Open position with contract at 1 DTE (force_close_at_dte = 1)
        WHEN: Orchestrator checks position DTE
        THEN: Position force-closed regardless of P&L
        AND: Log: "Force close: contract at DTE threshold"
        """
        pass


# =================================================================
# STATE PERSISTENCE — Within-Session Tracking
# =================================================================


class TestSessionStatePersistence:
    """Tests for state tracking across multiple cycles within a session."""

    def test_pdt_count_increments_across_trades(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Gameplan with pdt_trades_remaining = 3
        WHEN: Two round-trip trades completed (open + close each)
        THEN: PDT count = 2, remaining = 1
        """
        pass

    def test_pdt_exhaustion_blocks_third_trade(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: PDT count at 3 (limit reached)
        WHEN: New signal generated
        THEN: Entry blocked, log: "PDT limit reached"
        AND: Closing existing positions still allowed
        """
        pass

    def test_daily_loss_accumulates_across_trades(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Two losing trades: -$15 and -$20
        WHEN: Third signal generated
        THEN: Risk engine reports daily_loss_total = $35
        AND: Remaining daily risk budget = $25 ($60 - $35)
        """
        pass

    def test_daily_loss_limit_halts_all_trading(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Cumulative daily losses reach $60 (10% of $600)
        WHEN: Loss event recorded
        THEN:
          1. Circuit breaker opens
          2. All positions closed
          3. Trading halted for remainder of day
          4. Alert sent via notifier
          5. No further orders accepted

        @CRO: This is the daily loss hard stop. Non-negotiable.
        """
        pass

    def test_pivot_count_persists_within_session(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: One pivot already recorded in session
        WHEN: Second regime change occurs
        THEN: Pivot count = 2 → triggers Strategy C lock
        """
        pass

    def test_position_tracking_survives_multiple_cycles(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Position opened in cycle 1
        WHEN: Cycle 2 begins (new market data)
        THEN: Open position is tracked, unrealized P&L updated
        """
        pass
```

### 3.3 Safety Scenario Tests (`test_safety_scenarios.py`)

```python
# ============================================================
# FILE: tests/e2e/test_safety_scenarios.py
# PURPOSE: Validate safety mechanisms under realistic failure
#          scenarios. Every test answers: "Does the system
#          default to safety when something goes wrong?"
# ============================================================

"""
E2E tests for safety mechanisms in realistic scenarios.

@CRO MANDATE: Every test in this file validates a safety guarantee.
Fail-safe behavior is NOT inferred from other tests — it is
EXPLICITLY tested here. A failure in this file is a CRITICAL
finding that blocks deployment.

Tests cover:
- Gateway failure scenarios (disconnect, timeout, reconnect)
- Data quality degradation (stale data, missing fields, quarantine)
- Risk limit cascade (daily → weekly → circuit breaker)
- PDT enforcement across multi-trade sessions
- Gap-down scenario modeling (widowmaker scenario)
- Compound failure scenarios (multiple systems failing simultaneously)
- Dry-run mode safety (never submits real orders)
"""

import pytest
import copy
import threading
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, PropertyMock

from src.bot.orchestrator import TradingOrchestrator
from src.risk.guards import RiskManager


# =================================================================
# GATEWAY FAILURE SCENARIOS
# =================================================================


class TestGatewayFailures:
    """Tests for IBKR Gateway failure handling."""

    def test_gateway_disconnect_cancels_all_orders(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Active trading session with pending orders
        WHEN: Gateway disconnects (isConnected returns False)
        THEN:
          1. All pending orders cancelled
          2. Trading halted
          3. Alert sent to Discord
          4. System enters monitoring-only mode
          5. No new orders attempted until reconnection
        """
        pass

    def test_gateway_disconnect_during_order_submission(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Order being submitted to broker
        WHEN: Gateway disconnects MID-SUBMISSION (placeOrder raises ConnectionError)
        THEN:
          1. Order marked as FAILED (not PENDING — we don't know if it went through)
          2. No position created (assume order did NOT execute)
          3. Alert sent: "Order submission failed — Gateway disconnect"
          4. On reconnection, order status must be explicitly verified

        @CRO: Fail-safe assumption: if we don't have confirmation, assume NOT filled.
        Never assume a fill without explicit confirmation.
        """
        mock_gateway.placeOrder.side_effect = ConnectionError("Gateway disconnected")
        pass

    def test_gateway_timeout_during_market_data(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Market data request in progress
        WHEN: Gateway times out (no response within timeout period)
        THEN:
          1. Market data request returns None/empty
          2. Strategy engine receives no data → no signal generated
          3. System uses last known data for monitoring only
          4. Log: "Market data timeout — using stale data for monitoring"
        """
        mock_gateway.reqMktData.return_value = None
        pass

    def test_gateway_reconnection_does_not_auto_resume_trading(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Gateway disconnected → trading halted
        WHEN: Gateway reconnects
        THEN:
          1. Connection confirmed
          2. Position state reconciled (verify open positions match expected)
          3. Trading does NOT auto-resume — requires new gameplan cycle
          4. Log: "Gateway reconnected — awaiting new cycle"

        @CRO: After a disconnect, we need to verify state before resuming.
        Auto-resume risks acting on stale state.
        """
        pass


# =================================================================
# DATA QUALITY DEGRADATION SCENARIOS
# =================================================================


class TestDataQualityFailures:
    """Tests for data quality issues triggering safety responses."""

    def test_stale_data_triggers_strategy_c(
        self, valid_strategy_a_gameplan, stale_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Market data with timestamp > 5 minutes old
        WHEN: Data quality check runs
        THEN:
          1. Data flagged as stale
          2. Strategy forced to C (or signal suppressed)
          3. Log: "Stale market data detected"
          4. Alert sent to Discord
        """
        pass

    def test_missing_vix_data_forces_strategy_c(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: VIX data unavailable (API returns None)
        WHEN: Strategy selection attempted
        THEN:
          1. Cannot determine regime → default to crisis assumption
          2. Strategy C deployed
          3. Log: "VIX data unavailable — defaulting to Strategy C"

        @CRO: Without VIX, we cannot assess regime. No regime = no trading.
        """
        pass

    def test_partial_market_data_handled_gracefully(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Market data returned but missing RSI field
        WHEN: Strategy A evaluates signals
        THEN:
          1. Strategy cannot confirm momentum → no signal generated
          2. System does not crash (KeyError caught)
          3. Log: "Incomplete market data: missing RSI"
        """
        pass

    def test_conflicting_data_sources_trigger_quarantine(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Primary VIX source says 15.5, secondary says 28.0
        WHEN: Data quality audit runs
        THEN:
          1. Quarantine activated (conflict > acceptable threshold)
          2. Strategy C deployed
          3. Both values logged for manual review
        """
        pass

    def test_nan_values_in_market_data_caught(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Market data contains NaN values (e.g., last = float('nan'))
        WHEN: Strategy processes data
        THEN:
          1. NaN detected before calculation
          2. Signal generation skipped
          3. No division-by-zero or NaN propagation
        """
        pass


# =================================================================
# RISK LIMIT CASCADE SCENARIOS
# =================================================================


class TestRiskLimitCascade:
    """Tests for cascading risk limit enforcement."""

    def test_daily_loss_to_circuit_breaker_cascade(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Three losing trades: $20, $20, $20 = $60 total
        WHEN: Third loss recorded
        THEN:
          1. Daily loss limit hit ($60 = 10%)
          2. Circuit breaker opens
          3. All open positions force-closed
          4. All pending orders cancelled
          5. Trading halted for day
          6. Alert: "CIRCUIT BREAKER — daily loss limit reached"

        @CRO: This is the complete cascade path. Every step must execute.
        """
        pass

    def test_weekly_drawdown_governor_activates(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Weekly cumulative P&L reaches -$90 (15% of $600)
        WHEN: Loss threshold crossed
        THEN:
          1. Weekly governor activates
          2. Strategy C locked for remainder of week
          3. Governor persists across daily resets
          4. Alert: "WEEKLY GOVERNOR — 15% drawdown limit reached"

        @CRO: Weekly governor supersedes daily reset. Even on a new day,
        governor stays active until the week resets.
        """
        pass

    def test_daily_breaker_resets_but_weekly_governor_persists(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Daily breaker OPEN + Weekly governor ACTIVE
        WHEN: New trading day starts
        THEN:
          1. Daily breaker resets to CLOSED
          2. Weekly governor stays ACTIVE
          3. Net result: still Strategy C (governor overrides daily reset)
        """
        pass

    def test_compound_failure_daily_plus_weekly_plus_gateway(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Daily loss limit hit + Weekly governor active + Gateway disconnects
        WHEN: All three conditions simultaneously true
        THEN:
          1. System does not crash (no exception from compound state)
          2. Strategy C locked via multiple overlapping mechanisms
          3. Emergency action executes once (idempotent, not triple-executed)
          4. Single composite alert sent (not three separate alerts)
        """
        pass


# =================================================================
# PDT ENFORCEMENT — Multi-Trade Session Scenarios
# =================================================================


class TestPDTEnforcement:
    """Tests for Pattern Day Trader rule enforcement."""

    def test_pdt_count_tracks_round_trips(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: pdt_trades_remaining = 3
        WHEN: Buy SPY call → Sell SPY call (one round trip)
        THEN: pdt_trades_remaining = 2
        """
        pass

    def test_pdt_blocks_fourth_day_trade(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Three round-trip trades completed today
        WHEN: Fourth trade signal generated
        THEN:
          1. Entry blocked
          2. Log: "PDT limit reached — no new entries"
          3. Closing existing positions still permitted
        """
        pass

    def test_pdt_allows_closing_positions(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: PDT limit reached (0 remaining)
        AND: Open position exists
        WHEN: Exit signal generated (take-profit, stop-loss, or time-stop)
        THEN: Position closure allowed (closing is not a day trade)

        @CRO: PDT blocks entries, not exits. Blocking exits would
        leave positions unmanaged — that's MORE dangerous.
        """
        pass

    def test_pdt_state_from_gameplan_matches_risk_engine(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Gameplan says pdt_trades_remaining = 2
        WHEN: Orchestrator initializes
        THEN: Risk engine.pdt_trades_remaining == 2
        AND: After one trade, risk engine reports 1 remaining
        """
        pass


# =================================================================
# GAP-DOWN / WIDOWMAKER SCENARIOS
# =================================================================


class TestWidowmakerScenarios:
    """
    Tests for catastrophic market moves.

    @CRO: These scenarios model extreme events. The system must survive
    them without operator intervention. If any of these fail, deployment
    is blocked pending redesign.
    """

    def test_50pct_gap_down_impact(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Open position at premium $3.00
        WHEN: Market opens with 50% gap-down (premium now $1.50)
        THEN:
          1. Position value recalculated at $1.50
          2. Stop-loss already breached → immediate close at market
          3. Actual loss recorded (may exceed stop-loss target due to gap)
          4. Daily loss limit checked → may trigger circuit breaker
          5. Alert: "GAP DOWN — position closed below stop"

        NOTE: Gap-down losses CAN exceed the stop-loss target because
        the market opened below the stop price. This is unavoidable
        in options trading. The position sizing should ensure that even
        a complete loss of premium stays within the max risk budget.
        """
        pass

    def test_position_sizing_limits_gap_risk(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: $600 account, max risk $18
        WHEN: Position sizing calculates max quantity
        THEN: Max premium * 100 * quantity <= $120 (max position)
        AND: Even at total premium loss, loss <= $120 (20% of capital)

        @CRO: Position sizing is the FIRST line of defense against gaps.
        """
        pass


# =================================================================
# DRY-RUN MODE SAFETY
# =================================================================


class TestDryRunMode:
    """Tests for dry-run mode (no real orders ever submitted)."""

    def test_dry_run_never_calls_broker_place_order(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Orchestrator configured in dry-run mode
        WHEN: Full trade cycle runs (signal → risk → order attempt)
        THEN:
          1. broker.placeOrder() is NEVER called
          2. All other logic executes normally (signal, risk check, sizing)
          3. Simulated fill logged for validation
          4. P&L calculated from simulated fill

        @CRO: CRITICAL — dry-run is the paper trading safety net.
        If placeOrder leaks through in dry-run, real money is at risk.
        """
        pass

    def test_dry_run_logs_what_would_have_been_submitted(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Dry-run mode active
        WHEN: Signal generated and approved
        THEN: Log contains: "DRY RUN: Would submit BUY SPY call @ $X.XX"
        AND: Log contains simulated order parameters
        """
        pass

    def test_dry_run_flag_cannot_be_toggled_mid_session(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Orchestrator started in dry-run mode
        WHEN: Attempt to switch to live mode during session
        THEN: Switch rejected (requires session restart)
        AND: Log: "Cannot toggle dry-run mode during active session"
        """
        pass


# =================================================================
# NOTIFICATION INTEGRATION
# =================================================================


class TestNotificationIntegration:
    """Tests for Discord webhook notification firing."""

    def test_trade_entry_sends_notification(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Successful trade entry
        WHEN: Position opened
        THEN: Discord notification sent with trade details
        """
        pass

    def test_trade_exit_sends_notification_with_pnl(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Position closed (any exit path)
        WHEN: P&L calculated
        THEN: Discord notification includes: symbol, strategy, entry, exit, P&L
        """
        pass

    def test_circuit_breaker_sends_urgent_alert(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Circuit breaker opens
        WHEN: Emergency action executes
        THEN: Urgent Discord alert sent with: trigger reason, total daily loss, action taken
        """
        pass

    def test_notification_failure_does_not_block_trading(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: Discord webhook returns error (500 / timeout)
        WHEN: Trade notification attempted
        THEN:
          1. Notification failure logged
          2. Trading continues unaffected
          3. Trade is NOT rolled back due to notification failure

        NOTE: Notifications are fire-and-forget. They must never
        block or affect trading logic.
        """
        mock_notifier.send_trade_notification.side_effect = Exception("Webhook failed")
        pass


# =================================================================
# COMPONENT FAILURE ISOLATION
# =================================================================


class TestComponentFailureIsolation:
    """
    Tests that individual component failures don't cascade into
    unexpected behavior in other components.
    """

    def test_strategy_exception_does_not_affect_risk_engine(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy.generate_signal() raises RuntimeError
        WHEN: Orchestrator catches exception
        THEN:
          1. Risk engine state unchanged
          2. Existing positions still monitored
          3. No phantom orders created
          4. Strategy C implied for remainder of cycle
        """
        pass

    def test_risk_engine_exception_blocks_all_orders(
        self, valid_strategy_a_gameplan, trending_spy_market_data,
        mock_gateway, mock_notifier
    ):
        """
        GIVEN: RiskManager.pre_trade_check() raises exception
        WHEN: Orchestrator attempts risk validation
        THEN:
          1. Order NOT submitted (fail-safe: no risk check = no trade)
          2. Exception logged
          3. Alert sent

        @CRO: If the risk engine itself fails, we assume MAXIMUM risk.
        No risk check = no trading, period.
        """
        pass

    def test_position_tracker_corruption_quarantines(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Position tracker reports negative quantity
        WHEN: P&L calculation attempted
        THEN:
          1. Position quarantined (removed from active tracking)
          2. Alert: "POSITION CORRUPTION DETECTED"
          3. Manual review required before position is un-quarantined
        """
        pass

    def test_all_components_failing_results_in_safe_state(
        self, valid_strategy_a_gameplan, mock_gateway, mock_notifier
    ):
        """
        GIVEN: Strategy raises error + Risk engine raises error + Broker offline
        WHEN: Orchestrator attempts full cycle
        THEN:
          1. No orders submitted
          2. No positions modified
          3. System in monitoring-only mode
          4. Alert sent (if notifier is available)
          5. System can be gracefully shut down

        @CRO: The absolute worst case: everything breaks at once.
        The ONLY acceptable outcome is inaction. Never trade when
        you can't verify safety.
        """
        pass
```

---

## 4. DEPENDENCIES

**Python Libraries:**
- `pytest` (test framework)
- `pytest-mock` (mocking/patching)
- `pytest-cov` (coverage reporting)
- `hypothesis` (property-based testing for P&L edge cases)

**Internal Modules (all validated in prior tasks):**
- `src.broker` (Task 1.1.3 — 92%+ coverage)
  - `IBKRConnection`, `ContractManager`, `MarketDataProvider`, `StaleDataError`
- `src.strategy` (Task 1.1.4 — 85%+ coverage)
  - `select_strategy`, `MomentumStrategy`, `MeanReversionStrategy`
- `src.risk` (Task 1.1.5 — 98%+ coverage, @CRO signed off)
  - `RiskManager`, `PositionSizer`
- `src.execution` (Task 1.1.6 — 90%+ coverage)
  - `ExecutionEngine`
- `src.bot` (Phase 2 implementation target — stubs/interfaces expected)
  - `TradingOrchestrator`, `GameplanLoader`, `GameplanValidationError`

**Test Utilities (from Task 1.1.2):**
- `tests/helpers/assertions.py` — Domain-specific assertions
- `tests/helpers/builders.py` — Test data builders (ContractBuilder, OrderBuilder)
- `tests/helpers/mocks.py` — MockIBConnection, MockGateway

**External (mocked in all E2E tests):**
- IBKR Gateway API (via `MagicMock`)
- Discord Webhooks (via `MagicMock`)

---

## 5. INPUT/OUTPUT CONTRACT

### Input: Gameplan JSON (daily_gameplan.json)

The primary input to E2E tests is the daily gameplan JSON, which follows the schema defined in Crucible v4.1. Key fields consumed by E2E tests:

| Field | Type | E2E Usage |
|-------|------|-----------|
| `strategy` | `"A" \| "B" \| "C"` | Determines which strategy engine is instantiated |
| `symbols` | `string[]` | Symbols eligible for trading |
| `hard_limits.pdt_trades_remaining` | `int` | Fed to RiskManager for PDT enforcement |
| `hard_limits.max_daily_loss_pct` | `float` | Fed to RiskManager for circuit breaker |
| `hard_limits.weekly_drawdown_governor_active` | `bool` | Force Strategy C if true |
| `data_quality.quarantine_active` | `bool` | Force Strategy C if true |
| `position_size_multiplier` | `float` | Scales max position size |
| `earnings_blackout` | `string[]` | Symbols excluded from trading |
| `key_levels` | `object` | Support/resistance/pivot for strategy logic |

### Input: Market Data (from mocked Gateway)

| Field | Type | Range | Usage |
|-------|------|-------|-------|
| `last` | `float` | `> 0` | Current price |
| `bid`/`ask` | `float` | `> 0` | Spread calculation |
| `volume` | `int` | `>= 0` | Liquidity check |
| `vwap` | `float` | `> 0` | Strategy A confirmation |
| `ema_8`/`ema_21` | `float` | `> 0` | Momentum crossover |
| `rsi` | `float` | `0–100` | Momentum / mean reversion |
| `bollinger_upper`/`lower` | `float` | `> 0` | Strategy B confirmation |
| `timestamp` | `ISO8601` | Recent | Staleness check |

### Output: Test Assertions

E2E test assertions validate:

1. **Order correctness** — right symbol, right side (BUY/SELL), right order type, right quantity
2. **Risk compliance** — position size ≤ max, risk ≤ max, PDT count ≤ limit
3. **P&L accuracy** — realized P&L matches (exit - entry) * quantity * multiplier
4. **State transitions** — strategy changes recorded, pivot count tracked, breakers fire correctly
5. **Safety defaults** — every failure path results in no-trade or Strategy C
6. **Notification firing** — Discord alerts sent for entries, exits, breakers, errors

---

## 6. INTEGRATION POINTS

### Orchestrator Architecture (Phase 2 implementation, E2E tests define the contract)

```
┌──────────────────────────────────────────────────────┐
│                TradingOrchestrator                     │
│                                                        │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────┐ │
│  │ Gameplan     │   │ Strategy     │   │ Risk       │ │
│  │ Loader       │──▶│ Engine       │──▶│ Manager    │ │
│  │              │   │ (A/B/C)      │   │            │ │
│  └─────────────┘   └──────┬───────┘   └─────┬──────┘ │
│                           │                   │        │
│                           ▼                   ▼        │
│                    ┌──────────────┐   ┌────────────┐  │
│                    │ Execution    │──▶│ Broker     │  │
│                    │ Engine       │   │ (Gateway)  │  │
│                    └──────┬───────┘   └────────────┘  │
│                           │                            │
│                           ▼                            │
│                    ┌──────────────┐                    │
│                    │ Position     │                    │
│                    │ Tracker      │                    │
│                    └──────┬───────┘                    │
│                           │                            │
│                           ▼                            │
│                    ┌──────────────┐                    │
│                    │ Notifier     │                    │
│                    │ (Discord)    │                    │
│                    └──────────────┘                    │
└──────────────────────────────────────────────────────┘
```

### Data Flow (Normal Cycle):
```
1. GameplanLoader.load(path) → gameplan dict
2. GameplanLoader.validate(gameplan) → True or GameplanValidationError
3. Orchestrator.apply_gameplan(gameplan) → configures all components
4. MarketDataProvider.get_data(symbol) → market data dict
5. StrategyEngine.evaluate(market_data, gameplan) → signal or None
6. RiskManager.pre_trade_check(signal) → approved/rejected
7. ExecutionEngine.submit_order(signal, contract) → order confirmation
8. PositionTracker.open_position(fill) → position record
9. [Monitor loop: check exits, update P&L]
10. ExecutionEngine.close_position(exit_signal) → close confirmation
11. PositionTracker.close_position(fill) → realized P&L
12. Notifier.send_trade_notification(trade_summary)
```

### Data Flow (Failure Cascade):
```
1. ANY component raises exception or returns invalid data
2. Orchestrator catches at the appropriate level
3. Default action: NO new orders
4. If positions exist: managed conservatively (existing stops honored)
5. Alert sent via Notifier (if Notifier is available)
6. System enters monitoring-only mode
```

---

## 7. DEFINITION OF DONE

### Must Pass:
- [ ] All existing tests pass (400+ tests from Tasks 1.1.3–1.1.6)
- [ ] `tests/e2e/conftest.py` created with composite fixtures
- [ ] `tests/e2e/__init__.py` updated (TODO removed)
- [ ] **Gameplan ingestion tests** pass:
  - [ ] File loading (valid, missing, corrupted, empty, BOM)
  - [ ] Schema validation (all required fields, boundary values)
  - [ ] Parameter application (risk limits, PDT, position sizing)
  - [ ] Safety overrides (quarantine, governor, PDT exhaustion, blackout)
- [ ] **Full trade cycle tests** pass:
  - [ ] Strategy A complete cycle (entry → exit via TP, SL, time-stop)
  - [ ] Strategy B complete cycle (different params than A)
  - [ ] Strategy C behavior (no trades, manage existing)
  - [ ] Multi-symbol sessions
  - [ ] Strategy transitions (A→B, A→C, 2-pivot lock)
  - [ ] All three exit paths validated
  - [ ] State persistence within session (PDT, daily loss, pivots)
- [ ] **Safety scenario tests** pass:
  - [ ] Gateway failures (disconnect, timeout, mid-submission)
  - [ ] Data quality degradation (stale, missing, NaN, conflict)
  - [ ] Risk limit cascade (daily → weekly → compound)
  - [ ] PDT enforcement (block entry, allow exit)
  - [ ] Widowmaker scenario (gap-down handling)
  - [ ] Dry-run mode (never calls placeOrder)
  - [ ] Notification failure isolation
  - [ ] Component failure isolation
  - [ ] All-components-failing results in safe state
- [ ] `ruff` + `black` pass with zero warnings
- [ ] `mypy` type checking passes
- [ ] No new test failures introduced in layer test suites
- [ ] @CRO sign-off on all safety scenario tests

### Quality Gates:
- [ ] Every safety test explicitly validates fail-safe behavior (no inference)
- [ ] No test relies on mock behavior that wouldn't occur in production
- [ ] All fixtures provide realistic data shapes matching production schemas
- [ ] Gateway mock faithfully simulates disconnect/timeout/error scenarios
- [ ] P&L calculations cross-validated with manual examples
- [ ] Strategy parameter isolation validated (A params ≠ B params)

### Coverage Target:
- E2E tests do not have a traditional code coverage target (they test orchestration, not individual lines)
- **Behavioral coverage** target: every path through the orchestrator architecture diagram above must have at least one test
- **Safety coverage** target: every Strategy C trigger condition from Crucible v4.1 must have an explicit test

---

## 8. EDGE CASES TO TEST

### Gameplan Edge Cases:
- **Gameplan file has correct JSON but wrong schema version** → validation catches
- **Gameplan date doesn't match today** → warning logged, proceed with caution
- **Strategy field says "A" but governor is active** → governor overrides to C
- **Position size multiplier = 0.0** → effectively Strategy C (zero sizing)
- **Earnings blackout list contains all symbols** → no tradeable symbols → Strategy C

### Market Data Edge Cases:
- **Bid > Ask (crossed market)** → data quality flag, no trading
- **Volume = 0 (pre-market / illiquid)** → liquidity check fails, no entry
- **RSI returns None (calculation error)** → strategy cannot confirm signal
- **VWAP = 0 (pre-market)** → Strategy A VWAP confirmation fails

### Risk Engine Edge Cases:
- **Account balance at exactly $0** → all risk checks fail
- **Max risk exactly $18.00** → boundary inclusive (trade allowed)
- **Max risk at $18.01** → boundary exclusive (trade rejected)
- **Floating-point arithmetic** → $59.99 + $0.02 = $60.01 (triggers breaker)
- **Negative P&L reporting** → risk engine accepts only non-negative loss values

### Execution Edge Cases:
- **Signal generated at 3:59 PM ET** → too close to market close, time-stop likely
- **Multiple signals in same second** → sequential processing, no race condition
- **Partial fill** → position sized to partial, not full, fill quantity
- **Order rejected by broker** → no position created, PDT count NOT incremented

### State Edge Cases:
- **Session state corrupted** → defaults to conservative state (Strategy C)
- **Pivot count = 2 at session start** → Strategy C locked immediately
- **PDT trades remaining calculated wrong from gameplan** → risk engine reconciles

---

## 9. ROLLBACK PLAN

**If E2E tests cannot reach behavioral coverage target:**
1. Identify which orchestrator paths are untested
2. Create additional test scenarios targeting those paths
3. Do NOT reduce coverage expectations — E2E is the integration gate

**If E2E tests reveal design flaws in the orchestrator contract:**
1. Document findings as Phase 2 design requirements
2. Tests remain with `@pytest.mark.skip(reason="Orchestrator redesign needed — Phase 2")`
3. Create IBKR board task: "Phase 2 Redesign: [specific flaw]"
4. Do NOT proceed to Task 1.1.8 until design is resolved

**If safety scenario tests fail:**
1. This is a **CRITICAL** finding — escalate to @CRO immediately
2. Deployment is BLOCKED until all safety tests pass
3. Consider Red Team review (Protocol R1) of the safety architecture
4. Root cause analysis required: why did layer tests pass but E2E safety fails?

**If fixtures or mocks prove unrealistic:**
1. Document the mock-reality gap
2. Create targeted live validation scenarios in Task 1.1.8
3. Add mock improvement task to IBKR board

---

## 10. CONTEXT & NOTES

### Why Three Separate Test Files?

The three files map to distinct concerns and different personas' review requirements:

1. **test_daily_gameplan_ingestion.py** — @Systems_Architect primary reviewer
   - Tests the data contract between Boardroom and Factory Floor
   - Validates that the gameplan JSON schema is enforced
   - Ensures parameter propagation is correct

2. **test_full_trade_cycle.py** — @Lead_Quant + @Systems_Architect reviewers
   - Tests the happy-path trading logic
   - Validates strategy-specific parameters don't cross-contaminate
   - Ensures state tracking is correct within sessions

3. **test_safety_scenarios.py** — @CRO is the MANDATORY reviewer
   - Tests every failure mode and safety guarantee
   - @CRO sign-off required before deployment proceeds
   - Any failure here is a deployment blocker

### Relationship to Phase 2

These E2E tests define the **behavioral contract** that the Phase 2 TradingOrchestrator implementation must satisfy. The tests are written first (TDD) — the implementation follows. Some tests may initially be marked `@pytest.mark.skip` if the orchestrator interface isn't fully defined yet. As Phase 2 progresses, skipped tests are un-skipped and must pass.

### Relationship to Task 1.1.8 (Live Validation)

E2E tests use mocked Gateway responses. Task 1.1.8 tests use the **real** IBKR Gateway. The gap between E2E and Live is:
- E2E: "Does the orchestration logic work correctly with simulated data?"
- Live: "Does the real Gateway respond the way our mocks assume?"

E2E passing + Live failing indicates a mock-reality gap. This is expected and manageable.

### Test Execution Performance

E2E tests should complete in **< 30 seconds total** (per the test architecture spec). Since all external dependencies are mocked, the primary cost is object instantiation and orchestrator logic. If any individual test exceeds 5 seconds, flag it as a potential design issue.

### Estimated Effort

- **conftest.py (composite fixtures):** 3–4 hours
- **test_daily_gameplan_ingestion.py:** 3–4 hours
- **test_full_trade_cycle.py:** 4–5 hours
- **test_safety_scenarios.py:** 5–6 hours (most complex, most critical)
- **QA review + @CRO sign-off:** 2–3 hours
- **Total: 17–22 hours**

---

## Context Block

### Session Lineage
- **Predecessor Tasks:** 1.1.3 (Broker), 1.1.4 (Strategy), 1.1.5 (Risk), 1.1.6 (Execution)
- **This Task:** 1.1.7 (E2E System Tests)
- **Successor Task:** 1.1.8 (Live Validation Suite)
- **Phase:** 1 (Test Suite Migration) — 75% → 87.5% completion with this task

### Key Design Decisions
1. **Single mock point:** Only the IBKR Gateway is mocked. All internal components use real implementations. This maximizes integration confidence.
2. **TDD contract:** Tests define the orchestrator interface. Phase 2 implements to satisfy these tests.
3. **Safety-first testing:** Every failure mode has an explicit test. No safety behavior is inferred from other tests.
4. **@CRO mandatory review:** `test_safety_scenarios.py` cannot be considered complete without @CRO sign-off.

### Account Parameters Encoded in Tests
| Parameter | Value | Test Reference |
|-----------|-------|----------------|
| Starting Capital | $600 | All fixture account_balance values |
| Max Position Size | $120 (20%) | Position sizing tests |
| Max Risk Per Trade | $18 (3%) | Stop-loss calculation tests |
| Max Daily Loss | $60 (10%) | Circuit breaker tests |
| Weekly Drawdown Governor | 15% ($90) | Governor cascade tests |
| PDT Limit | 3 day trades / 5 days | PDT enforcement tests |

---

**END OF BLUEPRINT**
