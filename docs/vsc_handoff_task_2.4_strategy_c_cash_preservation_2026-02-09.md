# VSC HANDOFF: Task 2.4 — Strategy C (Cash Preservation)

**Date:** 2026-02-09
**Task ID:** TTyjiYMHbkmW_-zyERtvRmUANLbm
**Requested By:** Phase 2 Implementation Sprint
**Model Routing:** Sonnet (implementation complexity: low)
**Estimated Context Budget:** Low (~250-350 lines of code)

---

## CONTEXT BLOCK

### Why This Task Exists

Strategy C is the **fail-safe default strategy** for the Crucible system. It is activated during crisis conditions (VIX > 25), when data quality fails, when the Morning Gauntlet misses deadline, or when any system component cannot determine a safe trading posture. Strategy C's sole purpose is **capital preservation** — it does not generate new trade signals, only manages the safe exit of existing positions.

### What Was Already Built (Dependencies)

**Task 2.1 (Base Strategy) — COMPLETE ✅**
- `StrategyBase` abstract class with `analyze()` method
- `Signal` dataclass with confidence validation
- `Direction` enum (LONG, SHORT, NEUTRAL)
- `MarketData` input contract
- `StrategyCConfig` configuration dataclass

**Tasks 2.2 & 2.3 (Strategies A & B) — COMPLETE ✅**
- Provide architectural pattern for concrete strategy implementation
- Demonstrate signal generation and confidence scoring
- Show how strategies integrate with `StrategyBase`

All base infrastructure is in place. Strategy C is the **simplest strategy** — it does not trade, it only protects capital.

### Architectural Context

**Module Location:** `src/strategies/strategy_c.py`

**Integration Points:**
- Inherits from `src.strategies.base.StrategyBase`
- Uses `src.strategies.config.StrategyCConfig` for parameters
- Accepts `src.strategies.base.MarketData` as input
- Returns `src.strategies.base.Signal` as output (always NEUTRAL/HOLD)

**Critical Role:** Strategy C is the **system-wide safety fallback**. When any component is uncertain, Strategy C is deployed. This is not a trading strategy — it is a **risk management protocol**.

### What Success Looks Like

When complete, the orchestrator can instantiate `StrategyC` and it will:
1. **Never generate BUY or SELL signals** (always returns HOLD/NEUTRAL)
2. **Signal position closure** when existing positions approach expiry (3 DTE threshold)
3. **Monitor market conditions** and report status without trading
4. Pass all existing Strategy C tests (Coverage 1.1.4, subset of strategy tests)

---

## AGENT EXECUTION BLOCK

### 1. OBJECTIVE

Implement Strategy C (Cash Preservation) as a concrete class inheriting from `StrategyBase`. Strategy C is the defensive fallback that **never initiates new trades**. It only manages safe exit of existing positions and monitors market conditions.

---

### 2. FILE STRUCTURE

**Files to Create:**
```
src/strategies/strategy_c.py
```

**Files to Modify:**
```
src/strategies/__init__.py  (add StrategyC export)
```

**No files to delete.**

---

### 3. LOGIC FLOW (Pseudo-code)

```
CLASS StrategyC extends StrategyBase:

    CONSTRUCTOR(config: StrategyCConfig):
        self.config = config
        # Strategy C has minimal configuration:
        # - force_close_dte: 3 (close positions at 3 days to expiry)
        # - emergency_stop_pct: 0.40 (40% loss triggers immediate close)

    METHOD analyze(data: MarketData) -> Signal:
        """
        Strategy C never generates BUY or SELL signals.

        Always returns HOLD (NEUTRAL) with confidence 0.0.

        The orchestrator is responsible for:
        1. Closing existing positions at 3 DTE (config.force_close_dte)
        2. Applying emergency stop (40% loss) on any position
        3. Rejecting any new entry signals when Strategy C is active

        This method exists only to satisfy the StrategyBase interface.
        All position management happens at the orchestrator/risk layer.
        """

        # Strategy C always returns NEUTRAL (HOLD)
        RETURN Signal(
            direction=Direction.HOLD,
            confidence=0.0,  # Always fails confidence gate
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            timestamp=data.timestamp
        )

    METHOD should_close_position(position_dte: int, position_pnl_pct: float) -> bool:
        """
        Helper method for orchestrator to determine if an existing position
        should be closed under Strategy C rules.

        Args:
            position_dte: Days to expiry for the position
            position_pnl_pct: Current P&L as percentage (e.g., -0.15 for -15%)

        Returns:
            True if position should be closed, False otherwise

        Closure Conditions:
        1. Position is at or below force_close_dte (default 3 days)
        2. Position loss exceeds emergency_stop_pct (default 40%)
        """

        # Condition 1: Force close at DTE threshold
        IF position_dte <= self.config.force_close_dte:
            RETURN True

        # Condition 2: Emergency stop on large losses
        IF position_pnl_pct <= -self.config.emergency_stop_pct:
            RETURN True

        # Otherwise, monitor but don't close
        RETURN False
```

---

### 4. DEPENDENCIES

**Required Imports:**
```python
from dataclasses import dataclass
from datetime import datetime

from src.strategies.base import StrategyBase, Signal, Direction, MarketData
from src.strategies.config import StrategyCConfig
```

**External Libraries:**
- None required (Strategy C has no calculations)

**Configuration Schema (already defined in Task 2.1):**
```python
@dataclass
class StrategyCConfig:
    force_close_dte: int = 3          # Close positions at 3 DTE
    emergency_stop_pct: float = 0.40  # 40% loss triggers immediate close
    max_risk_pct: float = 0.0         # No new risk allowed
    max_position_pct: float = 0.0     # No new positions allowed
```

---

### 5. INPUT/OUTPUT CONTRACT

**Input:**
- `MarketData` dataclass instance (same contract as Strategies A & B)
- For `should_close_position()` helper:
  - `position_dte: int` — Days to expiry
  - `position_pnl_pct: float` — P&L percentage (negative for loss)

**Output:**
- `Signal` dataclass instance:
  - `direction: Direction` — Always `Direction.HOLD`
  - `confidence: float` — Always `0.0`
  - `entry_price: Optional[float]` — Always `None`
  - `stop_loss: Optional[float]` — Always `None`
  - `take_profit: Optional[float]` — Always `None`
  - `timestamp: datetime` — From input `MarketData`

**Error Handling:**
- Strategy C is **fail-safe** — it never raises exceptions
- If `MarketData` is malformed, return HOLD signal with current timestamp
- `should_close_position()` returns `False` if inputs are invalid (safe default: don't close)

---

### 6. INTEGRATION POINTS

**How This Connects to Existing Codebase:**

1. **Base Class Inheritance:**
   - `StrategyC` inherits from `StrategyBase` (implemented in Task 2.1)
   - Must implement `analyze(data: MarketData) -> Signal` abstract method
   - Always returns HOLD signal (never BUY/SELL)

2. **Configuration:**
   - Uses `StrategyCConfig` from `src.strategies.config` (Task 2.1)
   - Config is passed to constructor and stored as instance variable

3. **Orchestrator Integration (Future Task 2.6+):**
   - Orchestrator instantiates `StrategyC(config)` when gameplan specifies Strategy C
   - Orchestrator calls `strategy.analyze(market_data)` — always receives HOLD
   - Orchestrator uses `strategy.should_close_position(dte, pnl)` to manage existing positions
   - **Critical:** Orchestrator must reject any new trade entry when Strategy C is active

4. **Crucible Protocol Integration:**
   - Strategy C is deployed automatically when:
     - VIX > 25 (crisis mode)
     - Morning Gauntlet misses 9:15 AM deadline
     - Data quarantine flag is active
     - 2+ intraday pivots already occurred
     - Weekly drawdown governor triggered (15% loss)

---

### 7. DEFINITION OF DONE

**Acceptance Criteria (from Task 2.4 board description):**

- [ ] `StrategyC` class created in `src/strategies/strategy_c.py`
- [ ] `analyze()` method always returns HOLD signal with confidence 0.0
- [ ] `should_close_position()` helper method implemented
- [ ] Force close at 3 DTE logic implemented
- [ ] Emergency stop at 40% loss logic implemented
- [ ] Config parameters enforced (max_risk_pct = 0, max_position_pct = 0)
- [ ] All Strategy C unit tests pass (from Coverage 1.1.4)
- [ ] Integration tests confirm Strategy C never generates BUY/SELL
- [ ] `StrategyC` is importable from `src.strategies` module

**Quality Gates:**
- [ ] `ruff .` passes with zero warnings
- [ ] `black .` formatting applied
- [ ] `mypy src/strategies/strategy_c.py` passes with zero errors
- [ ] `pytest tests/unit/test_strategies.py -k StrategyC` passes 100%

**Code Quality Standards:**
- Type hints on all methods and parameters
- Docstrings on class and public methods (Google style)
- No magic numbers (all parameters from `StrategyCConfig`)
- Fail-safe error handling (never raise exceptions)

---

### 8. EDGE CASES TO TEST

**Test Scenarios (from Coverage 1.1.4):**

1. **Signal Generation:**
   - What happens when `analyze()` is called with valid MarketData? (should return HOLD)
   - What happens when `analyze()` is called with minimal/incomplete MarketData? (should return HOLD)
   - What happens if MarketData is None? (should return HOLD with current timestamp)

2. **Position Closure Logic:**
   - What happens if position DTE is exactly 3 (at threshold)? (should close)
   - What happens if position DTE is 2 (below threshold)? (should close)
   - What happens if position DTE is 4 (above threshold)? (should not close)
   - What happens if position loss is exactly -40% (at emergency stop)? (should close)
   - What happens if position loss is -45% (beyond emergency stop)? (should close)
   - What happens if position loss is -30% (below emergency stop)? (should not close)

3. **Combined Conditions:**
   - What happens if position DTE is 5 BUT loss is -50%? (should close — emergency stop)
   - What happens if position DTE is 2 AND loss is -10%? (should close — DTE threshold)
   - What happens if position DTE is 10 AND position is profitable (+20%)? (should not close)

4. **Invalid Inputs:**
   - What happens if position_dte is negative? (defensive: return False, don't close)
   - What happens if position_dte is zero? (should close — at expiry)
   - What happens if position_pnl_pct is None? (defensive: return False)
   - What happens if position_pnl_pct is NaN? (defensive: return False)

5. **Configuration Validation:**
   - What happens if force_close_dte is changed from 3 to 1? (should respect new config)
   - What happens if emergency_stop_pct is changed from 0.40 to 0.30? (should respect new config)
   - What happens if max_risk_pct is non-zero? (doesn't affect Strategy C behavior, but validates config)

**Expected Test Behavior:**
- Strategy C tests should cover ~15-20 test cases (simpler than A/B)
- Tests validate that Strategy C **never generates actionable signals**
- Tests validate position closure logic under various DTE/P&L scenarios
- Edge case tests validate fail-safe behavior (never crash, always safe default)

---

### 9. ROLLBACK PLAN

**How to Disable This Feature Without Breaking Existing Functionality:**

**Critical Note:** Strategy C **cannot be disabled** — it is the system-wide safety fallback. If Strategy C is broken, the entire system is unsafe.

However, if Strategy C needs to be temporarily isolated:

1. **Orchestrator bypass:**
   - In orchestrator, if gameplan specifies Strategy C, force Strategy A or B instead
   - **NOT RECOMMENDED** — defeats the purpose of Strategy C

2. **Emergency fallback:**
   - If Strategy C implementation is broken, hardcode a minimal fallback:
     ```python
     # Emergency Strategy C fallback (orchestrator level)
     if gameplan.strategy == "C":
         # Close all positions immediately
         close_all_positions()
         # Reject all new entries
         return None  # No signal
     ```

3. **Tests remain:**
   - Keep Strategy C tests in the suite (cannot skip — critical safety)
   - If Strategy C tests fail, **block deployment** — this is a critical failure

**Dependencies That Won't Break:**
- Task 2.1 (Base Strategy) is independent of Strategy C
- Tasks 2.2 & 2.3 (Strategies A & B) are siblings, not dependents
- Task 2.5+ (Risk Controls, Gateway) **depend on Strategy C functioning**

**Safest Rollback:**
There is no safe rollback for Strategy C. If it's broken, **fix it immediately** or **halt deployment**. Strategy C is the last line of defense for capital preservation.

---

## IMPLEMENTATION GUIDANCE

### Recommended Implementation Order

1. **Start with structure:**
   - Create `src/strategies/strategy_c.py`
   - Define `StrategyC` class inheriting from `StrategyBase`
   - Implement `analyze()` method (simple: always return HOLD)

2. **Implement position closure helper:**
   - Add `should_close_position()` method
   - Implement DTE threshold check
   - Implement emergency stop check
   - Validate against known test scenarios

3. **Add error handling:**
   - Validate inputs to `should_close_position()`
   - Handle None/NaN gracefully (fail-safe: return False)
   - Ensure `analyze()` never raises exceptions

4. **Run tests:**
   - Run `pytest tests/unit/test_strategies.py -k StrategyC`
   - Fix failures iteratively
   - Validate coverage (should hit 90%+ for Strategy C code)

### Code Quality Checkpoints

**Before committing:**
```bash
# Formatting
black src/strategies/strategy_c.py

# Linting
ruff src/strategies/strategy_c.py

# Type checking
mypy src/strategies/strategy_c.py

# Tests
pytest tests/unit/test_strategies.py -k StrategyC -v

# Coverage
pytest --cov=src.strategies.strategy_c tests/unit/test_strategies.py -k StrategyC
```

**Expected Output:**
- ruff: 0 warnings
- black: Already formatted or auto-formatted
- mypy: Success, no issues found
- pytest: All Strategy C tests pass (100%)
- coverage: 90%+ line coverage (simple code, high coverage expected)

### Common Pitfalls to Avoid

1. **Never Let Strategy C Trade:**
   - `analyze()` must **always** return HOLD
   - Do not add logic that could return BUY or SELL under any condition
   - Strategy C is not a strategy — it's a **safety protocol**

2. **Fail-Safe Error Handling:**
   - If in doubt, return HOLD (for `analyze()`)
   - If in doubt, return False (for `should_close_position()`)
   - Never raise exceptions — Strategy C must always work

3. **DTE Threshold Inclusivity:**
   - `position_dte <= force_close_dte` includes the threshold (e.g., 3 DTE triggers close)
   - Use `<=` not `<` to ensure positions close at threshold, not after

4. **Emergency Stop Sign:**
   - Loss percentage is negative: -0.40 means -40% loss
   - Use `position_pnl_pct <= -emergency_stop_pct` (note the negative sign)
   - Don't reverse the logic

5. **Configuration Immutability:**
   - Config is set at initialization and does not change during runtime
   - Don't try to dynamically adjust `force_close_dte` based on market conditions
   - Strategy C is deterministic and predictable

---

## TESTING STRATEGY

### Unit Test Coverage (Coverage 1.1.4)

**Existing tests in `tests/unit/test_strategies.py` validate:**

1. **Class instantiation:**
   - `StrategyC(config)` accepts a `StrategyCConfig` instance
   - Default config values are applied if not provided

2. **Signal generation (always HOLD):**
   - `analyze(market_data)` returns HOLD signal
   - Confidence is always 0.0
   - Entry price, stop loss, take profit are always None
   - Timestamp matches input MarketData

3. **Position closure — DTE threshold:**
   - `should_close_position(dte=3, pnl=0.0)` returns True (at threshold)
   - `should_close_position(dte=2, pnl=0.0)` returns True (below threshold)
   - `should_close_position(dte=4, pnl=0.0)` returns False (above threshold)
   - `should_close_position(dte=0, pnl=0.0)` returns True (at expiry)

4. **Position closure — Emergency stop:**
   - `should_close_position(dte=10, pnl=-0.40)` returns True (at emergency stop)
   - `should_close_position(dte=10, pnl=-0.50)` returns True (beyond emergency stop)
   - `should_close_position(dte=10, pnl=-0.30)` returns False (below emergency stop)

5. **Combined conditions:**
   - `should_close_position(dte=2, pnl=-0.10)` returns True (DTE triggers)
   - `should_close_position(dte=5, pnl=-0.45)` returns True (emergency stop triggers)
   - `should_close_position(dte=10, pnl=0.20)` returns False (no trigger)

6. **Invalid inputs (fail-safe):**
   - `should_close_position(dte=-1, pnl=0.0)` returns False (invalid DTE)
   - `should_close_position(dte=5, pnl=None)` returns False (invalid P&L)
   - `analyze(None)` returns HOLD signal (never crashes)

### Integration Test Coverage

**Integration tests (if any) validate:**
- Strategy C integrates correctly with `StrategyBase` interface
- Strategy C can be instantiated by orchestrator (future task)
- Orchestrator correctly rejects new entries when Strategy C is active
- Existing positions are closed according to Strategy C rules

---

## REFERENCE MATERIALS

**Crucible v4.1 Strategy Library (Strategy C Specification):**

```
### Strategy C: "Cash Preservation" (VIX > 25, Crisis, or Default)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Symbols | None | NO new entries |
| Max Risk % | 0% | Zero new risk |
| Existing Positions | Close all at 3 DTE | Force-close before expiry |
| Emergency Stop | 40% loss | Hard stop on any open position |
| Mode | Alert-only | Monitor and report, do not trade |
```

**Strategy C is also the automatic default when:**
- Morning Gauntlet misses the 9:15 AM deadline
- @Data_Ops issues a DATA QUARANTINE flag
- @CRO triggers the weekly drawdown governor
- 2+ intraday pivots have already occurred
- Any unresolvable disagreement in the committee

---

## POST-IMPLEMENTATION VALIDATION

**After implementation is complete, verify:**

1. **All tests pass:**
   ```bash
   pytest tests/unit/test_strategies.py -k StrategyC -v
   ```

2. **Code quality gates pass:**
   ```bash
   ruff src/strategies/strategy_c.py
   black --check src/strategies/strategy_c.py
   mypy src/strategies/strategy_c.py
   ```

3. **Strategy C is importable:**
   ```python
   from src.strategies import StrategyC
   from src.strategies.config import StrategyCConfig

   config = StrategyCConfig()
   strategy = StrategyC(config)
   print(f"Strategy C initialized: {strategy}")
   ```

4. **Signal generation works (always HOLD):**
   ```python
   from src.strategies.base import MarketData
   from datetime import datetime

   # Any market data — Strategy C always returns HOLD
   data = MarketData(
       symbol="SPY",
       timestamp=datetime.now(),
       price=685.0,
       bid=684.95,
       ask=685.05,
       volume=100_000_000,
       vwap=686.0,
       rsi=50.0,
       ema_fast=685.0,
       ema_slow=684.0,
       bollinger_upper=690.0,
       bollinger_lower=680.0,
       bollinger_middle=685.0
   )

   signal = strategy.analyze(data)
   assert signal.direction == Direction.HOLD
   assert signal.confidence == 0.0
   assert signal.entry_price is None
   ```

5. **Position closure logic works:**
   ```python
   # Test DTE threshold
   assert strategy.should_close_position(dte=3, pnl_pct=0.0) == True
   assert strategy.should_close_position(dte=4, pnl_pct=0.0) == False

   # Test emergency stop
   assert strategy.should_close_position(dte=10, pnl_pct=-0.40) == True
   assert strategy.should_close_position(dte=10, pnl_pct=-0.30) == False
   ```

6. **Documentation is complete:**
   - Class docstring explains what Strategy C does
   - Method docstrings explain parameters and return values
   - Inline comments clarify safety-critical logic

---

## FINAL CHECKLIST

**Before marking Task 2.4 complete:**

- [ ] `src/strategies/strategy_c.py` created
- [ ] `StrategyC` class implemented
- [ ] `analyze()` method always returns HOLD signal
- [ ] `should_close_position()` method implemented
- [ ] DTE threshold logic (≤3 days) implemented
- [ ] Emergency stop logic (≤-40% loss) implemented
- [ ] Fail-safe error handling implemented (never crash)
- [ ] `StrategyC` added to `src/strategies/__init__.py` exports
- [ ] All type hints present (mypy passes)
- [ ] All docstrings present (Google style)
- [ ] ruff + black + mypy pass with zero warnings
- [ ] All Strategy C unit tests pass (from Coverage 1.1.4)
- [ ] Code coverage ≥ 90% for `strategy_c.py`
- [ ] Manual smoke test confirms HOLD-only behavior
- [ ] Manual test confirms position closure logic
- [ ] Task 2.4 marked complete on board (100% progress)
- [ ] Blueprint document archived for future reference

---

**END OF VSC HANDOFF DOCUMENT**

**Next Steps:**
1. Implement `src/strategies/strategy_c.py` following the logic flow above
2. Run tests and iterate until all pass
3. Run quality gates (ruff, black, mypy)
4. Mark Task 2.4 complete on board
5. **Proceed to Task 2.5 (Risk Controls) in a fresh Opus session**

**Estimated Implementation Time:** 2-3 hours (per task description)

**Model Routing Recommendation:** Sonnet (low complexity, well-specified)

**Context Budget:** Low (250-350 lines of code, 15-20 tests)

---

## CRITICAL SAFETY NOTE

Strategy C is the **system-wide failsafe**. If Strategy C is broken, the entire trading system is unsafe. Treat this implementation with the same care as the Risk Layer (Task 2.5). Every line of Strategy C code is safety-critical.

**Test Strategy C exhaustively.** This is not a feature — it is a **circuit breaker**.
