# VSC HANDOFF: Task 2.7 — Daily Gameplan JSON Ingestion

**Date:** 2025-02-09
**Task ID:** 2.7
**Project:** IBKR Trading Bot — Phase 2 Core Implementation
**Sprint:** 2C (Strategies, Risk, Gateway Integration)
**Requested By:** Human Operator
**Blueprint Author:** @Systems_Architect
**Model Recommendation:** Sonnet (medium complexity, well-defined schema, existing code enhancement)
**Estimated Context Budget:** Moderate (600-800 lines, integration-focused)

---

## CONTEXT BLOCK

### Why This Task Exists

The **Daily Gameplan JSON Ingestion** module is the **configuration control center** for the IBKR trading bot. Every trading day, the Crucible Investment Committee (running in Claude Desktop) conducts a Morning Gauntlet protocol that produces a `daily_gameplan.json` file containing:

- **Strategy selection** (A: Momentum, B: Mean Reversion, C: Cash Preservation)
- **Market regime assessment** (VIX-based classification)
- **Risk parameters** (position sizing, PDT limits, drawdown status)
- **Market intelligence** (key levels, catalysts, earnings blackouts)
- **Data quality flags** (quarantine status, stale data warnings)
- **Hard compliance limits** (operator ID, daily loss caps, DTE force-close rules)

This JSON file is the **single source of truth** for how the bot behaves on any given day. The gameplan loader must:

1. **Ingest** the file safely (handling missing/malformed files)
2. **Validate** schema compliance (using `jsonschema` library)
3. **Enforce** safety defaults (Strategy C on any validation failure)
4. **Propagate** configuration to all subsystems (strategies, risk controls, Gateway)
5. **Maintain** audit trail (logging all validation decisions)

**Safety Philosophy:** The gameplan loader operates under a **fail-safe, not fail-open** architecture. Any ambiguity, validation error, or data quality concern results in **Strategy C deployment** (cash preservation mode). The bot never defaults to trading when configuration is uncertain.

### What Currently Exists

From **Phase 1 Coverage**, the gameplan infrastructure is **already implemented**:

**File:** `src/bot/gameplan.py`
- `GameplanLoader` class with basic file loading and validation
- Strategy C default on missing/malformed files
- Required field validation (strategy, symbols, regime)
- Safety-first error handling

**File:** `tests/e2e/test_daily_gameplan_ingestion.py`
- 15+ comprehensive tests covering:
  - Valid gameplan loading
  - Missing file handling (defaults to Strategy C)
  - Malformed JSON handling (defaults to Strategy C)
  - Invalid strategy values (defaults to Strategy C)
  - Field validation (required keys)

**File:** `schemas/daily_gameplan_schema.json`
- Minimal JSON schema (strategy, symbols, regime fields)

**Current Coverage:** `gameplan.py` at ~85% coverage (existing tests comprehensive but schema validation is basic)

### What This Task Adds

**Task 2.7** enhances the existing gameplan loader with:

1. **Enhanced Schema Validation:**
   - Upgrade from basic required-field checks to full `jsonschema` validation
   - Implement comprehensive schema matching Crucible v4.1 specification
   - Provide detailed validation error messages (which field failed, why)
   - Maintain Strategy C default on all validation failures

2. **Operator ID Compliance:**
   - Enforce `"operator_id": "CSATSPRIM"` presence in all gameplans
   - Pass operator ID to Gateway order executor (IBKR compliance requirement)
   - Validation failure if operator ID missing or incorrect

3. **Hard Limits Propagation:**
   - Extract `hard_limits` block from gameplan
   - Pass PDT trades remaining to `PDTTracker`
   - Pass weekly drawdown governor status to `DrawdownMonitor`
   - Pass daily loss limit to `DrawdownMonitor`
   - Ensure RiskManager enforces all limits at runtime

4. **Data Quality Enforcement:**
   - Check `data_quality.quarantine_active` flag
   - If `quarantine_active == true` → force Strategy C regardless of strategy field
   - Log quarantine enforcement for audit trail

5. **Integration Points:**
   - Strategy selection → instantiate correct `StrategyA`, `StrategyB`, or `StrategyC` class
   - Risk configuration → initialize `RiskManager` with gameplan limits
   - Gateway configuration → pass operator ID to order placement calls
   - Market data validation → respect data quality flags

6. **Comprehensive Testing:**
   - Maintain all existing tests (15+ passing)
   - Add tests for new `jsonschema` validation
   - Add tests for operator ID enforcement
   - Add tests for hard limits integration with RiskManager
   - Add tests for data quarantine enforcement
   - Target: 90%+ coverage for gameplan module

### Success Criteria

**Definition of Done:**

1. ✅ All existing tests in `test_daily_gameplan_ingestion.py` continue to pass
2. ✅ New tests cover `jsonschema` validation edge cases (invalid regime values, missing required fields, type mismatches)
3. ✅ Operator ID enforcement tested (missing ID, wrong ID, correct ID)
4. ✅ Hard limits propagation tested (verify RiskManager receives correct values)
5. ✅ Data quarantine override tested (quarantine flag forces Strategy C even if strategy="A")
6. ✅ `ruff`, `black`, `mypy` pass with zero warnings
7. ✅ Code coverage for `gameplan.py` reaches 90%+
8. ✅ Integration test demonstrates: load gameplan → select strategy → initialize RiskManager → pass operator ID to Gateway
9. ✅ All validation failures result in Strategy C deployment (no silent failures)
10. ✅ Audit logs capture all validation decisions with timestamps

**Acceptance Test:**

A complete system integration test where:
- Valid `daily_gameplan.json` (Strategy A) → bot initializes with StrategyA, RiskManager enforces PDT/drawdown limits, Gateway receives operator ID
- Gameplan with `quarantine_active=true` → bot deploys Strategy C regardless of strategy field
- Missing gameplan file → bot deploys Strategy C with logged warning
- Malformed JSON → bot deploys Strategy C with detailed error message

---

## AGENT EXECUTION BLOCK

### 1. Objective

Enhance the existing `GameplanLoader` class in `src/bot/gameplan.py` to:

1. Implement full `jsonschema`-based validation against Crucible v4.1 schema
2. Enforce operator ID compliance (`"CSATSPRIM"`)
3. Propagate hard limits to RiskManager
4. Enforce data quality quarantine overrides
5. Integrate with strategy selection, risk controls, and Gateway configuration
6. Maintain comprehensive test coverage (90%+)
7. Preserve fail-safe architecture (all failures → Strategy C)

**Non-Goals:**
- Modifying the Crucible gameplan schema (schema is fixed by Crucible v4.1 system prompt)
- Implementing strategy logic (strategies already exist in Tasks 2.1-2.4)
- Implementing risk controls (RiskManager already exists in Task 2.5)
- Modifying Gateway integration (Gateway client already exists in Task 2.6)

This task is **integration-focused**: connect the gameplan to existing modules.

### 2. File Structure

**Files to Modify:**

```
src/bot/gameplan.py                          # Enhance GameplanLoader class
schemas/daily_gameplan_schema.json           # Expand to full Crucible v4.1 schema
tests/e2e/test_daily_gameplan_ingestion.py  # Add new test cases
```

**Files to Reference (Do Not Modify):**

```
src/bot/strategies/strategy_a.py             # StrategyA class (Task 2.1)
src/bot/strategies/strategy_b.py             # StrategyB class (Task 2.2)
src/bot/strategies/strategy_c.py             # StrategyC class (Task 2.3)
src/bot/risk/risk_manager.py                 # RiskManager class (Task 2.5)
src/bot/risk/pdt_tracker.py                  # PDTTracker class (Task 2.5)
src/bot/risk/drawdown_monitor.py            # DrawdownMonitor class (Task 2.5)
src/bot/gateway/gateway_client.py            # GatewayClient class (Task 2.6)
```

**New Dependencies:**

```toml
# Add to pyproject.toml [tool.poetry.dependencies]
jsonschema = "^4.17.0"  # For schema validation
```

### 3. Logic Flow (Pseudo-code)

#### GameplanLoader.load() Method Enhancement

```python
class GameplanLoader:
    def __init__(self, gameplan_path: str, schema_path: str):
        self.gameplan_path = gameplan_path
        self.schema_path = schema_path
        self.logger = setup_logger()

    def load(self) -> dict:
        """
        Load and validate daily gameplan JSON.
        Returns: Validated gameplan dict OR Strategy C default dict
        """

        # STEP 1: File Loading (Existing Logic)
        try:
            with open(self.gameplan_path, 'r') as f:
                gameplan = json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Gameplan file not found: {self.gameplan_path}")
            return self._strategy_c_default(reason="missing_file")
        except json.JSONDecodeError as e:
            self.logger.error(f"Malformed JSON in gameplan: {e}")
            return self._strategy_c_default(reason="invalid_json")

        # STEP 2: Schema Validation (NEW)
        schema = self._load_schema()
        try:
            jsonschema.validate(instance=gameplan, schema=schema)
        except jsonschema.ValidationError as e:
            self.logger.error(f"Schema validation failed: {e.message}")
            self.logger.error(f"Failed at path: {e.json_path}")
            return self._strategy_c_default(reason=f"schema_violation: {e.message}")

        # STEP 3: Operator ID Enforcement (NEW)
        if not self._validate_operator_id(gameplan):
            self.logger.error("Operator ID missing or invalid")
            return self._strategy_c_default(reason="operator_id_missing")

        # STEP 4: Data Quality Quarantine Check (NEW)
        if gameplan.get("data_quality", {}).get("quarantine_active", False):
            self.logger.warning("Data quarantine active — forcing Strategy C")
            return self._strategy_c_default(reason="data_quarantine")

        # STEP 5: Strategy Validation (Existing Logic)
        if gameplan.get("strategy") not in ["A", "B", "C"]:
            self.logger.error(f"Invalid strategy: {gameplan.get('strategy')}")
            return self._strategy_c_default(reason="invalid_strategy")

        # STEP 6: Log Successful Load
        self.logger.info(f"Gameplan loaded: Strategy {gameplan['strategy']}, Session {gameplan['session_id']}")

        return gameplan

    def _load_schema(self) -> dict:
        """Load JSON schema from schemas/daily_gameplan_schema.json"""
        with open(self.schema_path, 'r') as f:
            return json.load(f)

    def _validate_operator_id(self, gameplan: dict) -> bool:
        """Validate operator ID is present and correct"""
        operator_id = gameplan.get("operator_id")
        if operator_id != "CSATSPRIM":
            return False
        return True

    def _strategy_c_default(self, reason: str) -> dict:
        """
        Generate Strategy C default gameplan.
        Logs the reason for Strategy C deployment.
        """
        self.logger.warning(f"Deploying Strategy C default: {reason}")

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "session_id": f"default_strategy_c_{int(time.time())}",
            "regime": "unknown",
            "strategy": "C",
            "symbols": [],
            "operator_id": "CSATSPRIM",
            "hard_limits": {
                "max_daily_loss_pct": 0.10,
                "max_single_position": 120,
                "pdt_trades_remaining": 0,
                "force_close_at_dte": 1,
                "weekly_drawdown_governor_active": True,
                "max_intraday_pivots": 0
            },
            "data_quality": {
                "quarantine_active": True,
                "stale_fields": [],
                "last_verified": datetime.now().isoformat()
            },
            "_default_reason": reason  # Internal field for debugging
        }
```

#### Integration with Strategy Selection

```python
# In main bot orchestrator (e.g., src/bot/main.py or similar)

from src.bot.gameplan import GameplanLoader
from src.bot.strategies.strategy_a import StrategyA
from src.bot.strategies.strategy_b import StrategyB
from src.bot.strategies.strategy_c import StrategyC

def initialize_bot():
    # Load gameplan
    loader = GameplanLoader(
        gameplan_path="config/daily_gameplan.json",
        schema_path="schemas/daily_gameplan_schema.json"
    )
    gameplan = loader.load()

    # Select strategy based on gameplan
    strategy_map = {
        "A": StrategyA,
        "B": StrategyB,
        "C": StrategyC
    }

    strategy_class = strategy_map[gameplan["strategy"]]
    strategy = strategy_class(config=gameplan)

    # Initialize RiskManager with hard limits
    risk_manager = RiskManager(
        max_daily_loss_pct=gameplan["hard_limits"]["max_daily_loss_pct"],
        max_single_position=gameplan["hard_limits"]["max_single_position"],
        pdt_trades_remaining=gameplan["hard_limits"]["pdt_trades_remaining"],
        weekly_governor_active=gameplan["hard_limits"]["weekly_drawdown_governor_active"]
    )

    # Initialize Gateway with operator ID
    gateway = GatewayClient(operator_id=gameplan["operator_id"])

    return strategy, risk_manager, gateway
```

#### Integration with RiskManager

```python
# In src/bot/risk/risk_manager.py (existing file, may need minor updates)

class RiskManager:
    def __init__(
        self,
        max_daily_loss_pct: float,
        max_single_position: float,
        pdt_trades_remaining: int,
        weekly_governor_active: bool
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_single_position = max_single_position
        self.pdt_tracker = PDTTracker(remaining_trades=pdt_trades_remaining)
        self.drawdown_monitor = DrawdownMonitor(
            max_daily_loss_pct=max_daily_loss_pct,
            weekly_governor_active=weekly_governor_active
        )
        # ... rest of initialization
```

### 4. Dependencies

**Python Libraries:**

```toml
# pyproject.toml [tool.poetry.dependencies]
jsonschema = "^4.17.0"  # Schema validation
```

**Internal Modules:**

```python
# Existing imports in gameplan.py
import json
import logging
from datetime import datetime
from pathlib import Path

# New import for schema validation
import jsonschema
from jsonschema import ValidationError

# Integration imports (for type hints and documentation)
from src.bot.strategies.strategy_a import StrategyA
from src.bot.strategies.strategy_b import StrategyB
from src.bot.strategies.strategy_c import StrategyC
from src.bot.risk.risk_manager import RiskManager
```

**File Dependencies:**

- `schemas/daily_gameplan_schema.json` — JSON schema file (must be expanded to full Crucible v4.1 spec)
- `config/daily_gameplan.json` — Runtime gameplan file (produced by Crucible)

### 5. Input/Output Contract

#### Input: `daily_gameplan.json`

**Source:** Produced by Crucible Morning Gauntlet (Claude Desktop session)

**Schema:** (Full Crucible v4.1 specification)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "date",
    "session_id",
    "regime",
    "strategy",
    "symbols",
    "operator_id",
    "hard_limits",
    "data_quality"
  ],
  "properties": {
    "date": {
      "type": "string",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
      "description": "Trading date in YYYY-MM-DD format"
    },
    "session_id": {
      "type": "string",
      "pattern": "^gauntlet_\\d{8}_\\d{4}$",
      "description": "Unique session identifier from Morning Gauntlet"
    },
    "regime": {
      "type": "string",
      "enum": ["complacency", "normal", "elevated", "high_volatility", "crisis"],
      "description": "Market regime classification based on VIX"
    },
    "strategy": {
      "type": "string",
      "enum": ["A", "B", "C"],
      "description": "Strategy selection: A=Momentum, B=Mean Reversion, C=Cash Preservation"
    },
    "symbols": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["SPY", "QQQ", "IWM"]
      },
      "maxItems": 2,
      "description": "Trading universe for the day"
    },
    "operator_id": {
      "type": "string",
      "const": "CSATSPRIM",
      "description": "IBKR account operator identifier (compliance requirement)"
    },
    "position_size_multiplier": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Position sizing adjustment (0.0-1.0)"
    },
    "vix_at_analysis": {
      "type": "number",
      "minimum": 0,
      "description": "VIX level at time of analysis"
    },
    "vix_source_verified": {
      "type": "boolean",
      "description": "Whether VIX data was cross-verified"
    },
    "bias": {
      "type": "string",
      "enum": ["bullish", "bearish", "neutral"],
      "description": "Market directional bias"
    },
    "expected_behavior": {
      "type": "string",
      "enum": ["trending", "mean_reverting"],
      "description": "Expected market behavior pattern"
    },
    "key_levels": {
      "type": "object",
      "description": "Support/resistance/pivot levels for each symbol"
    },
    "catalysts": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Known market catalysts for the day"
    },
    "earnings_blackout": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Symbols reporting earnings within 24 hours (excluded from trading)"
    },
    "geo_risk": {
      "type": "string",
      "enum": ["low", "medium", "high"],
      "description": "Geopolitical risk assessment"
    },
    "alert_message": {
      "type": "string",
      "description": "Free-text alert for Discord notifications"
    },
    "data_quality": {
      "type": "object",
      "required": ["quarantine_active", "stale_fields", "last_verified"],
      "properties": {
        "quarantine_active": {
          "type": "boolean",
          "description": "If true, forces Strategy C regardless of strategy field"
        },
        "stale_fields": {
          "type": "array",
          "items": {"type": "string"},
          "description": "List of data fields that failed freshness validation"
        },
        "last_verified": {
          "type": "string",
          "format": "date-time",
          "description": "ISO timestamp of last data validation"
        }
      }
    },
    "hard_limits": {
      "type": "object",
      "required": [
        "max_daily_loss_pct",
        "max_single_position",
        "pdt_trades_remaining",
        "force_close_at_dte",
        "weekly_drawdown_governor_active",
        "max_intraday_pivots"
      ],
      "properties": {
        "max_daily_loss_pct": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Maximum daily loss as percentage of capital"
        },
        "max_single_position": {
          "type": "number",
          "minimum": 0,
          "description": "Maximum dollar value for single position"
        },
        "pdt_trades_remaining": {
          "type": "integer",
          "minimum": 0,
          "maximum": 3,
          "description": "Remaining day trades in rolling 5-day window"
        },
        "force_close_at_dte": {
          "type": "integer",
          "minimum": 0,
          "description": "DTE threshold for forced position close"
        },
        "weekly_drawdown_governor_active": {
          "type": "boolean",
          "description": "Whether weekly 15% drawdown governor is engaged"
        },
        "max_intraday_pivots": {
          "type": "integer",
          "minimum": 0,
          "description": "Maximum strategy changes allowed during trading day"
        }
      }
    },
    "scorecard": {
      "type": "object",
      "description": "Performance metrics from previous trading day"
    }
  }
}
```

#### Output: Validated Gameplan Dictionary

**Type:** `dict`

**Success Case:**

```python
{
    "date": "2026-02-09",
    "session_id": "gauntlet_20260209_0712",
    "regime": "normal",
    "strategy": "A",
    "symbols": ["SPY", "QQQ"],
    "operator_id": "CSATSPRIM",
    "hard_limits": {
        "max_daily_loss_pct": 0.10,
        "max_single_position": 120,
        "pdt_trades_remaining": 2,
        # ... etc
    },
    # ... full gameplan
}
```

**Failure Case (All Failures → Strategy C):**

```python
{
    "date": "2026-02-09",
    "session_id": "default_strategy_c_1707489120",
    "regime": "unknown",
    "strategy": "C",
    "symbols": [],
    "operator_id": "CSATSPRIM",
    "hard_limits": {
        "max_daily_loss_pct": 0.10,
        "max_single_position": 120,
        "pdt_trades_remaining": 0,
        "force_close_at_dte": 1,
        "weekly_drawdown_governor_active": True,
        "max_intraday_pivots": 0
    },
    "data_quality": {
        "quarantine_active": True,
        "stale_fields": [],
        "last_verified": "2026-02-09T08:32:00-05:00"
    },
    "_default_reason": "schema_violation: 'operator_id' is a required property"
}
```

### 6. Integration Points

**Integration Point 1: Strategy Selection**

```python
# In bot orchestrator (main.py or equivalent)

gameplan = GameplanLoader(...).load()

strategy_map = {
    "A": StrategyA,
    "B": StrategyB,
    "C": StrategyC
}

strategy = strategy_map[gameplan["strategy"]](config=gameplan)
```

**What Strategies Need from Gameplan:**

- `StrategyA`: symbols, position_size_multiplier, key_levels, bias
- `StrategyB`: symbols, position_size_multiplier, key_levels
- `StrategyC`: Nothing (cash preservation mode)

**Integration Point 2: RiskManager Configuration**

```python
risk_manager = RiskManager(
    max_daily_loss_pct=gameplan["hard_limits"]["max_daily_loss_pct"],
    max_single_position=gameplan["hard_limits"]["max_single_position"],
    pdt_trades_remaining=gameplan["hard_limits"]["pdt_trades_remaining"],
    weekly_governor_active=gameplan["hard_limits"]["weekly_drawdown_governor_active"]
)
```

**What RiskManager Needs:**

- `hard_limits.max_daily_loss_pct` → DrawdownMonitor daily limit
- `hard_limits.max_single_position` → Position sizing validator
- `hard_limits.pdt_trades_remaining` → PDTTracker initialization
- `hard_limits.weekly_drawdown_governor_active` → DrawdownMonitor weekly lock

**Integration Point 3: Gateway Configuration**

```python
gateway = GatewayClient(operator_id=gameplan["operator_id"])
```

**What Gateway Needs:**

- `operator_id` → Passed to IBKR order placement (compliance requirement)

**Integration Point 4: Data Quality Validation**

```python
# In market data fetching logic

if gameplan["data_quality"]["quarantine_active"]:
    logger.warning("Data quarantine active — no new market data requests")
    # Skip market data updates, rely on cached data or halt trading
```

### 7. Definition of Done

**Code Quality:**

- [ ] `ruff src/bot/gameplan.py` — zero warnings
- [ ] `black src/bot/gameplan.py --check` — formatting compliant
- [ ] `mypy src/bot/gameplan.py` — type checking passes

**Test Coverage:**

- [ ] All 15+ existing tests in `test_daily_gameplan_ingestion.py` pass
- [ ] New test: `test_jsonschema_validation_comprehensive()` — tests full schema compliance
- [ ] New test: `test_operator_id_enforcement()` — missing ID, wrong ID, correct ID
- [ ] New test: `test_hard_limits_propagation()` — verify RiskManager receives correct values
- [ ] New test: `test_data_quarantine_override()` — quarantine flag forces Strategy C
- [ ] New test: `test_invalid_regime_enum()` — invalid regime value → Strategy C
- [ ] New test: `test_invalid_strategy_enum()` — invalid strategy value → Strategy C
- [ ] New test: `test_missing_required_field()` — schema validation catches missing fields
- [ ] Coverage: `gameplan.py` reaches 90%+

**Integration Tests:**

- [ ] Integration test: Load valid gameplan → select StrategyA → initialize RiskManager → pass operator ID to Gateway
- [ ] Integration test: Load gameplan with quarantine flag → bot deploys Strategy C
- [ ] Integration test: Missing gameplan file → bot deploys Strategy C with logged warning

**Audit Trail:**

- [ ] All validation decisions logged with timestamps
- [ ] Strategy C deployment reasons logged (missing_file, invalid_json, schema_violation, data_quarantine, etc.)
- [ ] Gameplan session ID logged on successful load

**Deployment Readiness:**

- [ ] `schemas/daily_gameplan_schema.json` expanded to full Crucible v4.1 specification
- [ ] `jsonschema` dependency added to `pyproject.toml`
- [ ] Poetry lock file updated (`poetry lock --no-update`)

### 8. Edge Cases to Test

**Edge Case 1: Missing Gameplan File**

```python
# Test: gameplan file does not exist at expected path
def test_missing_gameplan_file():
    loader = GameplanLoader(
        gameplan_path="nonexistent.json",
        schema_path="schemas/daily_gameplan_schema.json"
    )
    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "_default_reason" in gameplan
    assert "missing_file" in gameplan["_default_reason"]
```

**Edge Case 2: Malformed JSON**

```python
# Test: gameplan file contains invalid JSON
def test_malformed_json():
    # Create temp file with invalid JSON
    with open("temp_gameplan.json", "w") as f:
        f.write("{invalid json")

    loader = GameplanLoader(
        gameplan_path="temp_gameplan.json",
        schema_path="schemas/daily_gameplan_schema.json"
    )
    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "invalid_json" in gameplan["_default_reason"]
```

**Edge Case 3: Schema Validation Failure (Invalid Enum)**

```python
# Test: gameplan contains invalid regime value
def test_invalid_regime_value():
    invalid_gameplan = {
        "date": "2026-02-09",
        "session_id": "gauntlet_20260209_0712",
        "regime": "INVALID_REGIME",  # Not in enum
        "strategy": "A",
        # ... rest of valid fields
    }

    # Write to temp file
    with open("temp_gameplan.json", "w") as f:
        json.dump(invalid_gameplan, f)

    loader = GameplanLoader(
        gameplan_path="temp_gameplan.json",
        schema_path="schemas/daily_gameplan_schema.json"
    )
    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "schema_violation" in gameplan["_default_reason"]
```

**Edge Case 4: Missing Operator ID**

```python
# Test: gameplan missing operator_id field
def test_missing_operator_id():
    gameplan_no_operator = {
        "date": "2026-02-09",
        "session_id": "gauntlet_20260209_0712",
        "regime": "normal",
        "strategy": "A",
        "symbols": ["SPY"],
        # operator_id is missing
        "hard_limits": {...},
        "data_quality": {...}
    }

    with open("temp_gameplan.json", "w") as f:
        json.dump(gameplan_no_operator, f)

    loader = GameplanLoader(
        gameplan_path="temp_gameplan.json",
        schema_path="schemas/daily_gameplan_schema.json"
    )
    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "operator_id_missing" in gameplan["_default_reason"]
```

**Edge Case 5: Wrong Operator ID**

```python
# Test: gameplan has incorrect operator_id value
def test_wrong_operator_id():
    gameplan_wrong_operator = {
        # ... all valid fields ...
        "operator_id": "WRONG_ID",  # Should be "CSATSPRIM"
    }

    # ... write to file ...

    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "operator_id_missing" in gameplan["_default_reason"]
```

**Edge Case 6: Data Quarantine Override**

```python
# Test: quarantine flag forces Strategy C even when strategy="A"
def test_data_quarantine_override():
    gameplan_with_quarantine = {
        "date": "2026-02-09",
        "session_id": "gauntlet_20260209_0712",
        "regime": "normal",
        "strategy": "A",  # Strategy A requested
        "symbols": ["SPY"],
        "operator_id": "CSATSPRIM",
        "data_quality": {
            "quarantine_active": True,  # But quarantine is active
            "stale_fields": ["vix_at_analysis"],
            "last_verified": "2026-02-09T06:00:00-05:00"
        },
        "hard_limits": {...}
    }

    # ... write to file ...

    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "data_quarantine" in gameplan["_default_reason"]
```

**Edge Case 7: Type Mismatch in Hard Limits**

```python
# Test: hard_limits.pdt_trades_remaining is string instead of int
def test_type_mismatch_hard_limits():
    gameplan_type_error = {
        # ... all valid fields ...
        "hard_limits": {
            "max_daily_loss_pct": 0.10,
            "max_single_position": 120,
            "pdt_trades_remaining": "2",  # Should be int, not string
            # ... rest of fields ...
        }
    }

    # ... write to file ...

    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "schema_violation" in gameplan["_default_reason"]
```

**Edge Case 8: Symbols Array Exceeds Max Items**

```python
# Test: symbols array contains 3 items (max is 2)
def test_symbols_exceeds_max_items():
    gameplan_too_many_symbols = {
        # ... all valid fields ...
        "symbols": ["SPY", "QQQ", "IWM"],  # Max is 2
    }

    # ... write to file ...

    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "schema_violation" in gameplan["_default_reason"]
```

**Edge Case 9: Invalid Session ID Format**

```python
# Test: session_id doesn't match expected pattern
def test_invalid_session_id_format():
    gameplan_bad_session_id = {
        # ... all valid fields ...
        "session_id": "invalid_format",  # Should match gauntlet_YYYYMMDD_HHMM
    }

    # ... write to file ...

    gameplan = loader.load()

    assert gameplan["strategy"] == "C"
    assert "schema_violation" in gameplan["_default_reason"]
```

**Edge Case 10: Weekly Drawdown Governor Integration**

```python
# Test: gameplan with weekly_drawdown_governor_active=True
def test_weekly_drawdown_governor_active():
    gameplan_governor_active = {
        # ... all valid fields ...
        "strategy": "A",  # Strategy A requested
        "hard_limits": {
            # ... other limits ...
            "weekly_drawdown_governor_active": True,  # Governor active
        }
    }

    # ... write to file ...

    gameplan = loader.load()

    # Gameplan loads successfully (Strategy A)
    assert gameplan["strategy"] == "A"

    # But RiskManager should enforce governor
    risk_manager = RiskManager(
        weekly_governor_active=gameplan["hard_limits"]["weekly_drawdown_governor_active"]
    )

    # Attempt to place trade should be blocked by RiskManager
    # (This tests integration, not just gameplan loading)
    assert risk_manager.drawdown_monitor.weekly_governor_active == True
```

### 9. Rollback Plan

If Task 2.7 introduces regressions or breaks existing functionality:

**Step 1: Identify Regression**

```bash
# Run full test suite
pytest tests/e2e/test_daily_gameplan_ingestion.py -v

# Check which tests are failing
# Compare against baseline (Phase 1 test results)
```

**Step 2: Revert Code Changes**

```bash
# If gameplan.py changes break existing tests
git diff src/bot/gameplan.py  # Review changes
git checkout HEAD~1 src/bot/gameplan.py  # Revert to previous version

# If schema changes break existing tests
git checkout HEAD~1 schemas/daily_gameplan_schema.json
```

**Step 3: Remove New Dependency**

```bash
# If jsonschema library causes issues
poetry remove jsonschema
poetry lock --no-update
```

**Step 4: Disable New Features**

If only specific features are problematic:

```python
# In src/bot/gameplan.py, add feature flag

class GameplanLoader:
    def __init__(self, ..., use_jsonschema=True):
        self.use_jsonschema = use_jsonschema

    def load(self):
        # ... existing logic ...

        if self.use_jsonschema:
            # New schema validation
            schema = self._load_schema()
            try:
                jsonschema.validate(...)
            except:
                # ...
        else:
            # Fall back to basic validation (Phase 1 behavior)
            self._basic_validation(gameplan)
```

**Step 5: Re-run CI/CD**

```bash
# Verify rollback fixes the issue
pytest tests/e2e/test_daily_gameplan_ingestion.py
pytest tests/unit/test_strategies.py
pytest tests/unit/test_risk_controls.py

# Ensure all existing tests pass
```

**Step 6: Document Rollback**

```markdown
# Create rollback ticket on IBKR board

Task: Rollback Task 2.7 — Gameplan Ingestion
Reason: [Specific regression or failure]
Actions Taken: [Code reverts, dependency removal, feature flags]
Next Steps: [Root cause analysis, fix plan, re-attempt timeline]
```

**Prevention:** All changes must pass existing test suite before merge. CI/CD pipeline should catch regressions before deployment.

---

## IMPLEMENTATION GUIDANCE

### Step-by-Step Implementation Sequence

**Phase 1: Schema Expansion (30 min)**

1. Open `schemas/daily_gameplan_schema.json`
2. Replace minimal schema with full Crucible v4.1 specification (from Section 5)
3. Add all field definitions, type constraints, enum values, required fields
4. Validate JSON schema syntax using online validator or `jsonschema` CLI

**Phase 2: GameplanLoader Enhancement (60 min)**

1. Install `jsonschema` dependency:
   ```bash
   poetry add jsonschema
   ```

2. Update `src/bot/gameplan.py`:
   - Add `import jsonschema`
   - Add `_load_schema()` method
   - Add `_validate_operator_id()` method
   - Update `load()` method with Steps 2-4 from Logic Flow
   - Enhance `_strategy_c_default()` to include `_default_reason`

3. Add logging for all validation decisions

**Phase 3: Test Coverage (90 min)**

1. Run existing tests to establish baseline:
   ```bash
   pytest tests/e2e/test_daily_gameplan_ingestion.py -v
   ```

2. Add new test cases (Section 8 edge cases):
   - Schema validation tests
   - Operator ID enforcement tests
   - Data quarantine tests
   - Type mismatch tests
   - Invalid enum tests

3. Run coverage report:
   ```bash
   pytest tests/e2e/test_daily_gameplan_ingestion.py --cov=src/bot/gameplan --cov-report=term-missing
   ```

4. Target: 90%+ coverage

**Phase 4: Integration Testing (45 min)**

1. Create integration test in `tests/integration/test_gameplan_integration.py`:
   - Load gameplan → select strategy → initialize RiskManager → pass to Gateway
   - Verify hard limits propagate correctly
   - Verify operator ID reaches Gateway

2. Test with sample gameplans:
   - Valid Strategy A gameplan
   - Valid Strategy B gameplan
   - Strategy C default (various failure modes)
   - Quarantine override scenario

**Phase 5: Code Quality (15 min)**

1. Run linters:
   ```bash
   ruff src/bot/gameplan.py
   black src/bot/gameplan.py
   mypy src/bot/gameplan.py
   ```

2. Fix any warnings or errors

3. Final test run:
   ```bash
   pytest tests/ -v
   ```

**Phase 6: Documentation (15 min)**

1. Update module docstring in `src/bot/gameplan.py`
2. Add inline comments for complex validation logic
3. Update `README.md` with gameplan loading process
4. Document Strategy C default reasons

**Total Estimated Time:** 4-5 hours (solo developer with Copilot assistance)

### Testing Strategy

**Unit Tests:**

```python
# In tests/e2e/test_daily_gameplan_ingestion.py

class TestGameplanLoader:
    """Comprehensive gameplan loading tests"""

    def test_valid_gameplan_loads_successfully(self):
        """Valid gameplan should load without errors"""
        # ...

    def test_missing_file_defaults_to_strategy_c(self):
        """Missing gameplan file should return Strategy C default"""
        # ...

    def test_malformed_json_defaults_to_strategy_c(self):
        """Invalid JSON should return Strategy C default"""
        # ...

    def test_schema_validation_catches_invalid_regime(self):
        """Invalid regime enum should fail validation"""
        # ...

    def test_operator_id_enforcement(self):
        """Missing or wrong operator ID should fail validation"""
        # ...

    def test_data_quarantine_forces_strategy_c(self):
        """Quarantine flag should override strategy field"""
        # ...

    def test_hard_limits_extracted_correctly(self):
        """Hard limits should be extracted from gameplan"""
        # ...

    def test_strategy_c_default_includes_reason(self):
        """Strategy C default should document reason"""
        # ...
```

**Integration Tests:**

```python
# In tests/integration/test_gameplan_integration.py

class TestGameplanIntegration:
    """Test gameplan integration with other modules"""

    def test_gameplan_to_strategy_selection(self):
        """Gameplan should correctly select strategy class"""
        gameplan = GameplanLoader(...).load()
        strategy = select_strategy(gameplan)

        if gameplan["strategy"] == "A":
            assert isinstance(strategy, StrategyA)
        # ...

    def test_gameplan_to_risk_manager(self):
        """Gameplan hard limits should configure RiskManager"""
        gameplan = GameplanLoader(...).load()
        risk_manager = RiskManager(
            max_daily_loss_pct=gameplan["hard_limits"]["max_daily_loss_pct"],
            # ...
        )

        assert risk_manager.max_daily_loss_pct == 0.10
        # ...

    def test_gameplan_to_gateway(self):
        """Gameplan operator ID should pass to Gateway"""
        gameplan = GameplanLoader(...).load()
        gateway = GatewayClient(operator_id=gameplan["operator_id"])

        assert gateway.operator_id == "CSATSPRIM"
```

**Coverage Target:**

- `src/bot/gameplan.py`: 90%+ line coverage
- All branches tested (success paths + failure paths)
- All edge cases from Section 8 covered

### Integration Checklist

Before marking Task 2.7 complete, verify:

**Gameplan → Strategy:**

- [ ] Valid gameplan with strategy="A" → StrategyA instantiated
- [ ] Valid gameplan with strategy="B" → StrategyB instantiated
- [ ] Any validation failure → StrategyC instantiated
- [ ] Strategy receives correct config parameters from gameplan

**Gameplan → RiskManager:**

- [ ] `hard_limits.max_daily_loss_pct` → DrawdownMonitor daily limit
- [ ] `hard_limits.max_single_position` → Position validator
- [ ] `hard_limits.pdt_trades_remaining` → PDTTracker initialization
- [ ] `hard_limits.weekly_drawdown_governor_active` → DrawdownMonitor lock
- [ ] RiskManager enforces all limits during runtime

**Gameplan → Gateway:**

- [ ] `operator_id` passed to GatewayClient constructor
- [ ] GatewayClient includes operator ID in all order placements
- [ ] Missing operator ID → validation failure → Strategy C

**Data Quality Integration:**

- [ ] `data_quality.quarantine_active=true` → Strategy C regardless of strategy field
- [ ] Quarantine reason logged for audit trail
- [ ] Non-quarantined gameplans proceed normally

**Audit Trail:**

- [ ] All gameplan loads logged with session ID
- [ ] All validation failures logged with specific reason
- [ ] All Strategy C deployments logged with default reason
- [ ] Timestamps included in all log entries

**End-to-End Flow:**

- [ ] Crucible produces `daily_gameplan.json` → Bot loads it → Strategy selected → RiskManager configured → Gateway initialized → Trading begins (or Strategy C holds cash)

---

## FINAL NOTES

**Critical Success Factors:**

1. **Schema compliance is non-negotiable.** The gameplan schema is defined by Crucible v4.1 — any deviation breaks the contract between Boardroom and Factory Floor.

2. **Fail-safe architecture.** When in doubt, default to Strategy C. Better to miss a trading opportunity than to risk capital on uncertain configuration.

3. **Operator ID compliance.** IBKR requires operator identification on all orders. Missing operator ID is a compliance violation, not just a validation error.

4. **Integration testing is critical.** The gameplan loader is the **glue** between modules. Integration tests verify that the glue holds.

5. **Audit trail matters.** Every validation decision must be logged. In a regulated environment, "why did the bot do X?" must be answerable from logs.

**Common Pitfalls to Avoid:**

- **Silent failures:** Never fail validation without logging why.
- **Partial defaults:** Strategy C default must be complete — don't mix default values with loaded values.
- **Bypassing validation:** Never skip schema validation even if "the file looks okay."
- **Ignoring quarantine:** Data quality flags exist for a reason — respect them.
- **Hardcoded values:** All hard limits come from gameplan, not from code constants.

**Post-Implementation:**

After Task 2.7 is complete and QA-approved:

1. Update project documentation with gameplan loading process
2. Create sample gameplans for different scenarios (Strategy A/B/C, quarantine, etc.)
3. Document troubleshooting steps for common validation failures
4. Add gameplan loading to deployment runbook

**Dependencies for Next Task:**

Task 2.8 (QA Review) depends on complete gameplan integration. The QA review will test:

- End-to-end flow: Crucible → Gameplan → Strategy → RiskManager → Gateway → IBKR
- All safety mechanisms functioning
- All validation paths tested
- Audit logs complete

**Success Metric:**

Task 2.7 is complete when:

1. All tests pass (existing + new)
2. Code coverage ≥ 90% for `gameplan.py`
3. Integration tests verify gameplan propagates to all modules
4. Strategy C defaults correctly in all failure scenarios
5. Audit logs capture all validation decisions

**This is the final configuration layer before full system integration. Precision matters.**

---

**END OF VSC HANDOFF DOCUMENT**
