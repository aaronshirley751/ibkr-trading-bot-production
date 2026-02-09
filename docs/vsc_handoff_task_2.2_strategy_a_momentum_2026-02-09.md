# VSC HANDOFF: Task 2.2 — Strategy A (Momentum Breakout)

**Date:** 2026-02-09
**Task ID:** RlsDGv8AT0aVS-xHOiQM12UACW_s
**Requested By:** Phase 2 Implementation Sprint
**Model Routing:** Sonnet (implementation complexity: moderate)
**Estimated Context Budget:** Medium (~400-600 lines of code)

---

## CONTEXT BLOCK

### Why This Task Exists

Strategy A is the primary offensive trading strategy for normal market conditions (VIX < 18). It capitalizes on momentum breakouts using EMA crossover signals, confirmed by RSI and VWAP positioning. This is a trending-market strategy designed for the Crucible's "complacency" and "normal" regime classifications.

### What Was Already Built (Dependencies)

**Task 2.1 (Base Strategy) — COMPLETE ✅**
- `StrategyBase` abstract class with `analyze()` and `generate_signal()` methods
- `Signal` dataclass with confidence validation (0.0-1.0 range)
- `Direction` enum (LONG, SHORT, NEUTRAL)
- `MarketData` input contract
- `StrategyAConfig` configuration dataclass

All base infrastructure is in place. Strategy A implementation inherits from `StrategyBase`.

### Architectural Context

**Module Location:** `src/strategies/strategy_a.py`

**Integration Points:**
- Inherits from `src.strategies.base.StrategyBase`
- Uses `src.strategies.config.StrategyAConfig` for parameters
- Accepts `src.strategies.base.MarketData` as input
- Returns `src.strategies.base.Signal` as output

**Risk Enforcement:** Strategy A respects the 0.5 confidence gate enforced at the execution layer (tested in Coverage 1.1.6). Low-confidence signals (< 0.5) will be filtered out before order submission.

### What Success Looks Like

When complete, the orchestrator can instantiate `StrategyA`, pass it market data, and receive actionable trading signals for SPY/QQQ with proper confidence scoring. All existing Strategy A tests (Coverage 1.1.4, ~25 tests) must pass.

---

## AGENT EXECUTION BLOCK

### 1. OBJECTIVE

Implement Strategy A (Momentum Breakout) as a concrete class inheriting from `StrategyBase`. The strategy uses EMA 8/21 crossover as the primary signal, with RSI 50-65 and price > VWAP as confirmation filters. Designed for VIX < 18 trending markets.

---

### 2. FILE STRUCTURE

**Files to Create:**
```
src/strategies/strategy_a.py
```

**Files to Modify:**
```
src/strategies/__init__.py  (add StrategyA export)
```

**No files to delete.**

---

### 3. LOGIC FLOW (Pseudo-code)

```
CLASS StrategyA extends StrategyBase:

    CONSTRUCTOR(config: StrategyAConfig):
        self.config = config
        # EMA periods: 8 (fast), 21 (slow)
        # RSI range: 50-65 (momentum without overbought)
        # VWAP: price must be above VWAP (buyers in control)

    METHOD analyze(data: MarketData) -> Signal:
        """
        Generate trading signal based on momentum breakout logic.

        Entry Conditions (LONG signal):
        1. EMA(8) crosses above EMA(21) — bullish momentum
        2. RSI in range [50, 65] — momentum present but not overbought
        3. Price > VWAP — buyers dominating
        4. All conditions must be true simultaneously

        Entry Conditions (SHORT signal):
        5. EMA(8) crosses below EMA(21) — bearish momentum
        6. RSI in range [35, 50] — momentum present but not oversold
        7. Price < VWAP — sellers dominating
        8. All conditions must be true simultaneously

        Confidence Calculation:
        - Base confidence: 0.6 (Strategy A is inherently directional)
        - Bonus: +0.1 if RSI is in the "sweet spot" (55-60 for LONG, 40-45 for SHORT)
        - Bonus: +0.1 if price is significantly above/below VWAP (>0.2% for LONG, <-0.2% for SHORT)
        - Penalty: -0.2 if volume is below 50% of 20-day average (weak conviction)
        - Confidence clamped to [0.0, 1.0]

        Exit Strategy:
        - Take profit: 15% gain
        - Stop loss: 25% loss
        - Time stop: 90 minutes if no trigger
        """

        # Step 1: Calculate indicators
        ema_fast = calculate_ema(data.close, period=8)
        ema_slow = calculate_ema(data.close, period=21)
        rsi = calculate_rsi(data.close, period=14)
        vwap = data.vwap  # Assume provided in MarketData

        # Step 2: Detect crossover
        ema_cross_bullish = (ema_fast > ema_slow) AND (previous_ema_fast <= previous_ema_slow)
        ema_cross_bearish = (ema_fast < ema_slow) AND (previous_ema_fast >= previous_ema_slow)

        # Step 3: Apply filters
        IF ema_cross_bullish:
            IF (50 <= rsi <= 65) AND (data.close > vwap):
                direction = Direction.LONG
                confidence = calculate_confidence_long(rsi, data.close, vwap, data.volume)
                RETURN Signal(
                    direction=direction,
                    confidence=confidence,
                    entry_price=data.close,
                    stop_loss=data.close * 0.75,  # 25% below entry
                    take_profit=data.close * 1.15,  # 15% above entry
                    timestamp=data.timestamp
                )

        IF ema_cross_bearish:
            IF (35 <= rsi <= 50) AND (data.close < vwap):
                direction = Direction.SHORT
                confidence = calculate_confidence_short(rsi, data.close, vwap, data.volume)
                RETURN Signal(
                    direction=direction,
                    confidence=confidence,
                    entry_price=data.close,
                    stop_loss=data.close * 1.25,  # 25% above entry (for short)
                    take_profit=data.close * 0.85,  # 15% below entry (for short)
                    timestamp=data.timestamp
                )

        # Step 4: No signal (conditions not met)
        RETURN Signal(
            direction=Direction.NEUTRAL,
            confidence=0.0,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            timestamp=data.timestamp
        )

    HELPER METHOD calculate_ema(prices: List[float], period: int) -> float:
        """
        Exponential Moving Average calculation.
        EMA = (Price_today * K) + (EMA_yesterday * (1 - K))
        where K = 2 / (period + 1)
        """
        IF len(prices) < period:
            RAISE ValueError("Insufficient data for EMA calculation")

        K = 2 / (period + 1)
        ema = prices[0]  # Start with first price

        FOR price in prices[1:]:
            ema = (price * K) + (ema * (1 - K))

        RETURN ema

    HELPER METHOD calculate_rsi(prices: List[float], period: int = 14) -> float:
        """
        Relative Strength Index calculation.
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss over period
        """
        IF len(prices) < period + 1:
            RAISE ValueError("Insufficient data for RSI calculation")

        gains = []
        losses = []

        FOR i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            IF change > 0:
                gains.append(change)
                losses.append(0)
            ELSE:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        IF avg_loss == 0:
            RETURN 100  # All gains, maximal RSI

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        RETURN rsi

    HELPER METHOD calculate_confidence_long(rsi, price, vwap, volume) -> float:
        """
        Calculate signal confidence for LONG positions.
        """
        base_confidence = 0.6

        # RSI sweet spot bonus (55-60 is ideal momentum)
        IF 55 <= rsi <= 60:
            base_confidence += 0.1

        # Strong price > VWAP bonus (>0.2% above)
        vwap_distance = (price - vwap) / vwap
        IF vwap_distance > 0.002:
            base_confidence += 0.1

        # Volume penalty (low volume = weak conviction)
        # Assume volume_ratio is provided in MarketData or calculated
        # IF volume < 50% of 20-day average:
        #     base_confidence -= 0.2

        # Clamp to [0.0, 1.0]
        RETURN max(0.0, min(1.0, base_confidence))

    HELPER METHOD calculate_confidence_short(rsi, price, vwap, volume) -> float:
        """
        Calculate signal confidence for SHORT positions.
        """
        base_confidence = 0.6

        # RSI sweet spot bonus (40-45 is ideal for shorts)
        IF 40 <= rsi <= 45:
            base_confidence += 0.1

        # Strong price < VWAP bonus (<-0.2% below)
        vwap_distance = (price - vwap) / vwap
        IF vwap_distance < -0.002:
            base_confidence += 0.1

        # Volume penalty (same as LONG)
        # IF volume < 50% of 20-day average:
        #     base_confidence -= 0.2

        # Clamp to [0.0, 1.0]
        RETURN max(0.0, min(1.0, base_confidence))
```

---

### 4. DEPENDENCIES

**Required Imports:**
```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from src.strategies.base import StrategyBase, Signal, Direction, MarketData
from src.strategies.config import StrategyAConfig
```

**External Libraries:**
- No additional libraries required (EMA/RSI calculated from scratch)
- Alternative: Could use `pandas.Series.ewm()` for EMA if preferred, but not required

**Configuration Schema (already defined in Task 2.1):**
```python
@dataclass
class StrategyAConfig:
    ema_fast_period: int = 8
    ema_slow_period: int = 21
    rsi_period: int = 14
    rsi_min_long: int = 50
    rsi_max_long: int = 65
    rsi_min_short: int = 35
    rsi_max_short: int = 50
    take_profit_pct: float = 0.15  # 15%
    stop_loss_pct: float = 0.25    # 25%
    time_stop_minutes: int = 90
```

---

### 5. INPUT/OUTPUT CONTRACT

**Input:**
- `MarketData` dataclass instance containing:
  - `symbol: str` (e.g., "SPY", "QQQ")
  - `timestamp: datetime`
  - `open: float`
  - `high: float`
  - `low: float`
  - `close: float`
  - `volume: int`
  - `vwap: float` (volume-weighted average price)
  - `historical_close: List[float]` (for EMA/RSI calculation, min 21 data points)

**Output:**
- `Signal` dataclass instance containing:
  - `direction: Direction` (LONG, SHORT, or NEUTRAL)
  - `confidence: float` (0.0 to 1.0)
  - `entry_price: Optional[float]` (None if NEUTRAL)
  - `stop_loss: Optional[float]` (None if NEUTRAL)
  - `take_profit: Optional[float]` (None if NEUTRAL)
  - `timestamp: datetime`

**Error Handling:**
- Raise `ValueError` if `MarketData.historical_close` has fewer than 21 data points (insufficient for EMA 21)
- Raise `ValueError` if RSI calculation receives insufficient data (< 15 data points)
- Return `NEUTRAL` signal (confidence 0.0) if any indicator calculation fails or conditions aren't met

---

### 6. INTEGRATION POINTS

**How This Connects to Existing Codebase:**

1. **Base Class Inheritance:**
   - `StrategyA` inherits from `StrategyBase` (implemented in Task 2.1)
   - Must implement `analyze(data: MarketData) -> Signal` abstract method
   - Inherits `generate_signal()` wrapper method

2. **Configuration:**
   - Uses `StrategyAConfig` from `src.strategies.config` (Task 2.1)
   - Config is passed to constructor and stored as instance variable

3. **Test Suite Integration:**
   - Existing Strategy A tests in `tests/unit/test_strategies.py` (Coverage 1.1.4) will validate this implementation
   - Tests cover: EMA crossover detection, RSI filtering, VWAP confirmation, confidence calculation, edge cases

4. **Future Orchestrator Integration (Task 2.6+):**
   - Orchestrator will instantiate `StrategyA(config)` when gameplan specifies Strategy A
   - Orchestrator will call `strategy.analyze(market_data)` to get signals
   - Execution layer (Coverage 1.1.6) will filter signals with confidence < 0.5

---

### 7. DEFINITION OF DONE

**Acceptance Criteria (from Task 2.2 board description):**

- [ ] `StrategyA` class created in `src/strategies/strategy_a.py`
- [ ] EMA 8/21 crossover logic implemented and tested
- [ ] RSI 50-65 (LONG) and 35-50 (SHORT) filter implemented
- [ ] VWAP confirmation logic implemented (price > VWAP for LONG, price < VWAP for SHORT)
- [ ] Position sizing parameters enforced (20% max position, 3% max risk per trade — enforced at Risk Layer, not here)
- [ ] Take profit 15%, stop loss 25% implemented in signal generation
- [ ] Time stop 90 minutes noted in config (enforcement happens at execution layer)
- [ ] All Strategy A unit tests pass (from Coverage 1.1.4)
- [ ] Integration tests with mock market data pass
- [ ] `StrategyA` is importable from `src.strategies` module

**Quality Gates:**
- [ ] `ruff .` passes with zero warnings
- [ ] `black .` formatting applied
- [ ] `mypy src/strategies/strategy_a.py` passes with zero errors
- [ ] `pytest tests/unit/test_strategies.py -k StrategyA` passes 100%

**Code Quality Standards:**
- Type hints on all methods and parameters
- Docstrings on class and public methods (Google style)
- No magic numbers (all parameters from `StrategyAConfig`)
- Error handling for insufficient data edge cases

---

### 8. EDGE CASES TO TEST

**Test Scenarios (from Coverage 1.1.4):**

1. **EMA Crossover Detection:**
   - What happens if EMA fast crosses above EMA slow (bullish signal)?
   - What happens if EMA fast crosses below EMA slow (bearish signal)?
   - What happens if EMAs are parallel (no crossover)?
   - What happens if historical data is exactly 21 points (minimum for EMA 21)?

2. **RSI Filtering:**
   - What happens if RSI is 50 (at LONG threshold)?
   - What happens if RSI is 65 (at LONG upper bound)?
   - What happens if RSI is 70 (overbought, should reject LONG)?
   - What happens if RSI is 45 (at SHORT threshold)?
   - What happens if RSI is 30 (oversold, should reject SHORT)?

3. **VWAP Confirmation:**
   - What happens if price is exactly at VWAP (boundary case)?
   - What happens if price is 0.1% above VWAP (should pass for LONG)?
   - What happens if price is 0.5% above VWAP (strong LONG signal)?
   - What happens if VWAP is missing or null (error handling)?

4. **Confidence Calculation:**
   - What happens if RSI is in the "sweet spot" (55-60 for LONG)?
   - What happens if price is significantly above VWAP (>0.2%)?
   - What happens if volume is below 50% of average (penalty should apply)?
   - What happens if all bonuses apply (max confidence should be 0.8)?

5. **Data Quality Edge Cases:**
   - What happens if historical_close has only 20 data points (insufficient for EMA 21)?
   - What happens if historical_close is empty?
   - What happens if close price is zero or negative (invalid data)?
   - What happens if VWAP is missing from MarketData?

6. **Signal Generation Edge Cases:**
   - What happens if all conditions are met for LONG (should return LONG with confidence 0.6+)?
   - What happens if EMA crossover occurs but RSI is out of range (should return NEUTRAL)?
   - What happens if RSI is in range but no VWAP confirmation (should return NEUTRAL)?
   - What happens if multiple signals conflict (e.g., EMA bullish but price < VWAP)?

**Expected Test Behavior:**
- Strategy A tests should cover ~25 test cases (per Coverage 1.1.4)
- Tests use mocked `MarketData` with known indicator values
- Tests validate both signal generation and confidence scoring
- Edge case tests validate error handling and boundary conditions

---

### 9. ROLLBACK PLAN

**How to Disable This Feature Without Breaking Existing Functionality:**

1. **Remove from exports:**
   - Remove `StrategyA` from `src/strategies/__init__.py`
   - This prevents orchestrator from importing the strategy

2. **Skip in orchestrator:**
   - If orchestrator already has Strategy A integration, add a feature flag:
     ```python
     ENABLE_STRATEGY_A = False  # Disable Strategy A

     if gameplan.strategy == "A" and not ENABLE_STRATEGY_A:
         # Fall back to Strategy C (cash preservation)
         return StrategyCConfig()
     ```

3. **Tests remain:**
   - Keep Strategy A tests in the suite but mark them as `@pytest.mark.skip(reason="Strategy A disabled")`
   - This preserves the test specification for future re-enablement

**Dependencies That Won't Break:**
- Task 2.1 (Base Strategy) is independent of Strategy A
- Tasks 2.3 and 2.4 (Strategies B and C) are siblings, not dependents
- Task 2.5+ (Risk Controls, Gateway) don't care which specific strategy is active

**Safest Rollback:**
- Delete `src/strategies/strategy_a.py`
- Remove `StrategyA` export from `__init__.py`
- Update orchestrator to reject Strategy A selection in gameplan (default to Strategy C)

---

## IMPLEMENTATION GUIDANCE

### Recommended Implementation Order

1. **Start with structure:**
   - Create `src/strategies/strategy_a.py`
   - Define `StrategyA` class inheriting from `StrategyBase`
   - Stub out `analyze()` method returning NEUTRAL signal

2. **Implement indicators (bottom-up):**
   - Implement `calculate_ema()` helper method
   - Implement `calculate_rsi()` helper method
   - Validate against known test values (e.g., RSI for known price series)

3. **Implement signal logic:**
   - Add EMA crossover detection
   - Add RSI filtering
   - Add VWAP confirmation
   - Return LONG/SHORT signals when conditions are met

4. **Implement confidence scoring:**
   - Add `calculate_confidence_long()` helper
   - Add `calculate_confidence_short()` helper
   - Validate confidence ranges (must be 0.0-1.0)

5. **Add error handling:**
   - Validate `MarketData.historical_close` length
   - Handle missing VWAP gracefully
   - Catch edge cases in indicator calculations

6. **Run tests:**
   - Run `pytest tests/unit/test_strategies.py -k StrategyA`
   - Fix failures iteratively
   - Validate coverage (should hit 85%+ for Strategy A code)

### Code Quality Checkpoints

**Before committing:**
```bash
# Formatting
black src/strategies/strategy_a.py

# Linting
ruff src/strategies/strategy_a.py

# Type checking
mypy src/strategies/strategy_a.py

# Tests
pytest tests/unit/test_strategies.py -k StrategyA -v

# Coverage
pytest --cov=src.strategies.strategy_a tests/unit/test_strategies.py -k StrategyA
```

**Expected Output:**
- ruff: 0 warnings
- black: Already formatted or auto-formatted
- mypy: Success, no issues found
- pytest: All Strategy A tests pass (100%)
- coverage: 85%+ line coverage

### Common Pitfalls to Avoid

1. **EMA Calculation Errors:**
   - EMA requires historical data — don't use just the current price
   - EMA "warm-up" period: need at least `period` data points
   - Off-by-one errors in indexing historical_close

2. **RSI Boundary Conditions:**
   - RSI is inclusive on bounds: `50 <= rsi <= 65` includes both 50 and 65
   - Don't reverse the logic: `rsi >= 50 and rsi <= 65` not `rsi > 50`
   - Handle division by zero when average loss is 0

3. **Confidence Clamping:**
   - Always clamp confidence to [0.0, 1.0] after bonuses/penalties
   - Don't let confidence go negative or exceed 1.0
   - Validate in tests: `assert 0.0 <= signal.confidence <= 1.0`

4. **Signal Direction vs. Price Movement:**
   - LONG signal means "buy" (expect price to go up)
   - SHORT signal means "sell" (expect price to go down)
   - Stop loss for LONG is *below* entry price (e.g., `entry * 0.75`)
   - Stop loss for SHORT is *above* entry price (e.g., `entry * 1.25`)

5. **MarketData Contract:**
   - Assume `MarketData.vwap` is provided by the data layer
   - Don't try to calculate VWAP from scratch in Strategy A
   - Assume `historical_close` is a list of floats (most recent last)

---

## TESTING STRATEGY

### Unit Test Coverage (Coverage 1.1.4)

**Existing tests in `tests/unit/test_strategies.py` validate:**

1. **Class instantiation:**
   - `StrategyA(config)` accepts a `StrategyAConfig` instance
   - Default config values are applied if not provided

2. **EMA calculation:**
   - EMA(8) and EMA(21) are calculated correctly for known price series
   - EMA raises `ValueError` if insufficient data points

3. **RSI calculation:**
   - RSI returns correct values for known price series
   - RSI handles all-gains and all-losses edge cases
   - RSI raises `ValueError` if insufficient data points

4. **Crossover detection:**
   - Bullish crossover: EMA(8) crosses above EMA(21)
   - Bearish crossover: EMA(8) crosses below EMA(21)
   - No crossover: EMAs are parallel or diverging

5. **Signal generation:**
   - LONG signal when: EMA bullish cross + RSI 50-65 + price > VWAP
   - SHORT signal when: EMA bearish cross + RSI 35-50 + price < VWAP
   - NEUTRAL signal when conditions are not met

6. **Confidence scoring:**
   - Base confidence is 0.6
   - Bonuses applied correctly (RSI sweet spot, VWAP distance)
   - Confidence is clamped to [0.0, 1.0]

7. **Stop loss and take profit:**
   - Stop loss is 25% below entry for LONG (entry * 0.75)
   - Take profit is 15% above entry for LONG (entry * 1.15)
   - Stop loss is 25% above entry for SHORT (entry * 1.25)
   - Take profit is 15% below entry for SHORT (entry * 0.85)

### Integration Test Coverage

**Integration tests (if any) validate:**
- Strategy A integrates correctly with `StrategyBase` interface
- Strategy A can be instantiated by orchestrator (future task)
- Signal output format matches what execution layer expects

---

## REFERENCE MATERIALS

**Crucible v4.1 Strategy Library (Strategy A Specification):**

```
### Strategy A: "Momentum Breakout" (VIX < 18, Trending Markets)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Symbols | SPY, QQQ (max 2) | Highest liquidity |
| EMA Fast/Slow | 8 / 21 | Standard momentum crossover |
| RSI Range | 50–65 | Momentum without overbought |
| VWAP Condition | Price > VWAP | Buyers in control |
| Max Risk % | 3% ($18) | Survivable loss |
| Max Position % | 20% ($120) | Single-contract territory |
| Take Profit | 15% | |
| Stop Loss | 25% | Wide enough for intraday swings |
| Time Stop | 90 minutes | Close if no trigger |
| Expiry | Weekly, min 2 DTE | Never 0DTE |
| Moneyness | ATM | Best liquidity |
```

**Note:** Position sizing (20% max, 3% risk) is enforced at the **Risk Layer (Task 2.5)**, not in Strategy A itself. Strategy A only generates signals with stop loss and take profit levels.

---

## POST-IMPLEMENTATION VALIDATION

**After implementation is complete, verify:**

1. **All tests pass:**
   ```bash
   pytest tests/unit/test_strategies.py -k StrategyA -v
   ```

2. **Code quality gates pass:**
   ```bash
   ruff src/strategies/strategy_a.py
   black --check src/strategies/strategy_a.py
   mypy src/strategies/strategy_a.py
   ```

3. **Strategy A is importable:**
   ```python
   from src.strategies import StrategyA
   from src.strategies.config import StrategyAConfig

   config = StrategyAConfig()
   strategy = StrategyA(config)
   print(f"Strategy A initialized: {strategy}")
   ```

4. **Signal generation works end-to-end:**
   ```python
   from src.strategies.base import MarketData
   from datetime import datetime

   # Create mock market data (EMA bullish, RSI 55, price > VWAP)
   data = MarketData(
       symbol="SPY",
       timestamp=datetime.now(),
       open=685.0,
       high=690.0,
       low=684.0,
       close=688.5,
       volume=100_000_000,
       vwap=686.0,  # Close is above VWAP
       historical_close=[680.0, 682.0, 683.5, 685.0, 686.0, 687.0, 688.5]  # Uptrend
   )

   signal = strategy.analyze(data)
   assert signal.direction == Direction.LONG
   assert 0.5 <= signal.confidence <= 1.0
   assert signal.stop_loss < signal.entry_price
   assert signal.take_profit > signal.entry_price
   ```

5. **Documentation is complete:**
   - Class docstring explains what Strategy A does
   - Method docstrings explain parameters and return values
   - Inline comments clarify complex logic (e.g., confidence calculation)

---

## FINAL CHECKLIST

**Before marking Task 2.2 complete:**

- [ ] `src/strategies/strategy_a.py` created
- [ ] `StrategyA` class implemented
- [ ] `calculate_ema()` helper implemented
- [ ] `calculate_rsi()` helper implemented
- [ ] `calculate_confidence_long()` helper implemented
- [ ] `calculate_confidence_short()` helper implemented
- [ ] EMA crossover detection logic implemented
- [ ] RSI filtering logic implemented
- [ ] VWAP confirmation logic implemented
- [ ] Signal generation returns correct `Signal` dataclass
- [ ] Stop loss and take profit levels calculated correctly
- [ ] Error handling for insufficient data implemented
- [ ] `StrategyA` added to `src/strategies/__init__.py` exports
- [ ] All type hints present (mypy passes)
- [ ] All docstrings present (Google style)
- [ ] ruff + black + mypy pass with zero warnings
- [ ] All Strategy A unit tests pass (from Coverage 1.1.4)
- [ ] Code coverage ≥ 85% for `strategy_a.py`
- [ ] Manual smoke test with mock `MarketData` passes
- [ ] Task 2.2 marked complete on board (100% progress)
- [ ] Blueprint document archived for future reference

---

**END OF VSC HANDOFF DOCUMENT**

**Next Steps:**
1. Implement `src/strategies/strategy_a.py` following the logic flow above
2. Run tests and iterate until all pass
3. Run quality gates (ruff, black, mypy)
4. Mark Task 2.2 complete on board
5. Proceed to Task 2.3 (Strategy B - Mean Reversion)

**Estimated Implementation Time:** 3-4 hours (per task description)

**Model Routing Recommendation:** Sonnet (moderate complexity, well-specified)

**Context Budget:** Medium (400-600 lines of code, 25 tests)
