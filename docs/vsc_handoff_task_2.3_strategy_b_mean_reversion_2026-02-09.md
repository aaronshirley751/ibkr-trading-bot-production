# VSC HANDOFF: Task 2.3 — Strategy B (Mean Reversion)

**Date:** 2026-02-09
**Task ID:** wCBJA5ANI0aUj8P8tN0blWUAADZv
**Requested By:** Phase 2 Implementation Sprint
**Model Routing:** Sonnet (implementation complexity: medium)
**Estimated Context Budget:** Medium (~450-550 lines of code)

---

## CONTEXT BLOCK

### Why This Task Exists

Strategy B is the defensive mean-reversion strategy for choppy, elevated-volatility markets (VIX 18-25). It capitalizes on short-term price extremes using RSI oversold/overbought signals confirmed by Bollinger Band touches. This strategy assumes price will revert to the mean after overextension, making it effective when markets are range-bound rather than trending.

### What Was Already Built (Dependencies)

**Task 2.1 (Base Strategy) — COMPLETE ✅**
- `StrategyBase` abstract class with `analyze()` method
- `Signal` dataclass with confidence validation
- `Direction` enum (LONG, SHORT, NEUTRAL)
- `MarketData` input contract
- `StrategyBConfig` configuration dataclass

**Task 2.2 (Strategy A) — IN PROGRESS**
- Provides architectural pattern for concrete strategy implementation
- Demonstrates indicator calculation helpers (EMA, RSI)
- Shows confidence scoring approach

All base infrastructure is in place. Strategy B follows the same pattern as Strategy A but with different indicator logic.

### Architectural Context

**Module Location:** `src/strategies/strategy_b.py`

**Integration Points:**
- Inherits from `src.strategies.base.StrategyBase`
- Uses `src.strategies.config.StrategyBConfig` for parameters
- Accepts `src.strategies.base.MarketData` as input
- Returns `src.strategies.base.Signal` as output

**Risk Enforcement:** Strategy B respects the 0.5 confidence gate enforced at the execution layer. Lower position sizing (10% max vs Strategy A's 20%) reflects higher market volatility.

### What Success Looks Like

When complete, the orchestrator can instantiate `StrategyB`, pass it market data from choppy/elevated VIX markets, and receive actionable mean-reversion signals for SPY with proper confidence scoring. All existing Strategy B tests (Coverage 1.1.4, subset of ~25 strategy tests) must pass.

---

## AGENT EXECUTION BLOCK

### 1. OBJECTIVE

Implement Strategy B (Mean Reversion Fade) as a concrete class inheriting from `StrategyBase`. The strategy uses RSI extremes (oversold/overbought) as primary signals, with Bollinger Band touches as confirmation. Designed for VIX 18-25 choppy markets where price reverts after overextension.

---

### 2. FILE STRUCTURE

**Files to Create:**
```
src/strategies/strategy_b.py
```

**Files to Modify:**
```
src/strategies/__init__.py  (add StrategyB export)
```

**No files to delete.**

---

### 3. LOGIC FLOW (Pseudo-code)

```
CLASS StrategyB extends StrategyBase:

    CONSTRUCTOR(config: StrategyBConfig):
        self.config = config
        # RSI oversold: 30, overbought: 70
        # Bollinger Bands: 2 standard deviations (σ)
        # Position sizing: 10% max (reduced for higher volatility)

    METHOD analyze(data: MarketData) -> Signal:
        """
        Generate trading signal based on mean-reversion logic.

        Entry Conditions (LONG signal - fade oversold):
        1. RSI ≤ 30 — deeply oversold
        2. Price touches lower Bollinger Band (close ≤ BB_lower) — confirmation of extreme
        3. Both conditions must be true simultaneously

        Entry Conditions (SHORT signal - fade overbought):
        4. RSI ≥ 70 — deeply overbought
        5. Price touches upper Bollinger Band (close ≥ BB_upper) — confirmation of extreme
        6. Both conditions must be true simultaneously

        Confidence Calculation:
        - Base confidence: 0.5 (mean reversion is less reliable than momentum)
        - Bonus: +0.15 if RSI is at extreme (≤25 for LONG, ≥75 for SHORT)
        - Bonus: +0.1 if price breaches Bollinger Band (not just touches)
        - Penalty: -0.15 if VIX is outside Strategy B range (not 18-25)
        - Confidence clamped to [0.0, 1.0]

        Exit Strategy:
        - Take profit: 8% gain (quicker scalp than Strategy A)
        - Stop loss: 15% loss (tighter than Strategy A due to higher vol)
        - Time stop: 45 minutes (faster exit for mean reversion)
        """

        # Step 1: Calculate indicators
        rsi = calculate_rsi(data.historical_close, period=14)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            data.historical_close,
            period=20,
            std_dev=2
        )

        # Step 2: Check for oversold condition (LONG signal)
        IF rsi <= 30:
            IF data.close <= bb_lower:
                direction = Direction.LONG
                confidence = calculate_confidence_long(
                    rsi, data.close, bb_lower, data.vix
                )
                RETURN Signal(
                    direction=direction,
                    confidence=confidence,
                    entry_price=data.close,
                    stop_loss=data.close * 0.85,  # 15% below entry
                    take_profit=data.close * 1.08,  # 8% above entry
                    timestamp=data.timestamp
                )

        # Step 3: Check for overbought condition (SHORT signal)
        IF rsi >= 70:
            IF data.close >= bb_upper:
                direction = Direction.SHORT
                confidence = calculate_confidence_short(
                    rsi, data.close, bb_upper, data.vix
                )
                RETURN Signal(
                    direction=direction,
                    confidence=confidence,
                    entry_price=data.close,
                    stop_loss=data.close * 1.15,  # 15% above entry (for short)
                    take_profit=data.close * 0.92,  # 8% below entry (for short)
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

    HELPER METHOD calculate_rsi(prices: List[float], period: int = 14) -> float:
        """
        Relative Strength Index calculation.
        Same implementation as Strategy A — can be extracted to shared utility if desired.

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

    HELPER METHOD calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """
        Bollinger Bands calculation.

        BB_middle = Simple Moving Average (SMA) over period
        BB_upper = SMA + (std_dev * standard_deviation)
        BB_lower = SMA - (std_dev * standard_deviation)

        Returns: (upper_band, middle_band, lower_band)
        """
        IF len(prices) < period:
            RAISE ValueError("Insufficient data for Bollinger Bands calculation")

        # Calculate SMA (middle band)
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period

        # Calculate standard deviation
        variance = sum((p - sma) ** 2 for p in recent_prices) / period
        std = variance ** 0.5

        # Calculate bands
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)

        RETURN (upper_band, sma, lower_band)

    HELPER METHOD calculate_confidence_long(
        rsi: float,
        price: float,
        bb_lower: float,
        vix: float
    ) -> float:
        """
        Calculate signal confidence for LONG positions (fade oversold).
        """
        base_confidence = 0.5

        # Extreme oversold bonus (RSI ≤ 25)
        IF rsi <= 25:
            base_confidence += 0.15

        # Bollinger Band breach bonus (price < lower band, not just touching)
        IF price < bb_lower:
            base_confidence += 0.1

        # VIX regime penalty (Strategy B expects VIX 18-25)
        IF vix < 18 OR vix > 25:
            base_confidence -= 0.15

        # Clamp to [0.0, 1.0]
        RETURN max(0.0, min(1.0, base_confidence))

    HELPER METHOD calculate_confidence_short(
        rsi: float,
        price: float,
        bb_upper: float,
        vix: float
    ) -> float:
        """
        Calculate signal confidence for SHORT positions (fade overbought).
        """
        base_confidence = 0.5

        # Extreme overbought bonus (RSI ≥ 75)
        IF rsi >= 75:
            base_confidence += 0.15

        # Bollinger Band breach bonus (price > upper band, not just touching)
        IF price > bb_upper:
            base_confidence += 0.1

        # VIX regime penalty (Strategy B expects VIX 18-25)
        IF vix < 18 OR vix > 25:
            base_confidence -= 0.15

        # Clamp to [0.0, 1.0]
        RETURN max(0.0, min(1.0, base_confidence))
```

---

### 4. DEPENDENCIES

**Required Imports:**
```python
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime

from src.strategies.base import StrategyBase, Signal, Direction, MarketData
from src.strategies.config import StrategyBConfig
```

**External Libraries:**
- No additional libraries required (RSI and Bollinger Bands calculated from scratch)
- Note: RSI implementation can be shared with Strategy A if refactored to a utilities module

**Configuration Schema (already defined in Task 2.1):**
```python
@dataclass
class StrategyBConfig:
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    bb_period: int = 20
    bb_std_dev: float = 2.0
    take_profit_pct: float = 0.08  # 8%
    stop_loss_pct: float = 0.15    # 15%
    time_stop_minutes: int = 45
```

---

### 5. INPUT/OUTPUT CONTRACT

**Input:**
- `MarketData` dataclass instance containing:
  - `symbol: str` (e.g., "SPY" — Strategy B trades SPY only)
  - `timestamp: datetime`
  - `open: float`
  - `high: float`
  - `low: float`
  - `close: float`
  - `volume: int`
  - `vwap: float` (not used in Strategy B, but part of standard MarketData)
  - `vix: float` (VIX level for regime validation)
  - `historical_close: List[float]` (for RSI/BB calculation, min 20 data points)

**Output:**
- `Signal` dataclass instance containing:
  - `direction: Direction` (LONG, SHORT, or NEUTRAL)
  - `confidence: float` (0.0 to 1.0)
  - `entry_price: Optional[float]` (None if NEUTRAL)
  - `stop_loss: Optional[float]` (None if NEUTRAL)
  - `take_profit: Optional[float]` (None if NEUTRAL)
  - `timestamp: datetime`

**Error Handling:**
- Raise `ValueError` if `MarketData.historical_close` has fewer than 20 data points (insufficient for BB 20)
- Raise `ValueError` if RSI calculation receives insufficient data (< 15 data points)
- Return `NEUTRAL` signal (confidence 0.0) if any indicator calculation fails or conditions aren't met

---

### 6. INTEGRATION POINTS

**How This Connects to Existing Codebase:**

1. **Base Class Inheritance:**
   - `StrategyB` inherits from `StrategyBase` (implemented in Task 2.1)
   - Must implement `analyze(data: MarketData) -> Signal` abstract method

2. **Configuration:**
   - Uses `StrategyBConfig` from `src.strategies.config` (Task 2.1)
   - Config is passed to constructor and stored as instance variable

3. **Test Suite Integration:**
   - Existing Strategy B tests in `tests/unit/test_strategies.py` (Coverage 1.1.4) will validate this implementation
   - Tests cover: RSI extremes, Bollinger Band touches, confidence calculation, VIX regime validation

4. **Future Orchestrator Integration (Task 2.6+):**
   - Orchestrator will instantiate `StrategyB(config)` when gameplan specifies Strategy B
   - Orchestrator will call `strategy.analyze(market_data)` to get signals
   - Execution layer will filter signals with confidence < 0.5

---

### 7. DEFINITION OF DONE

**Acceptance Criteria (from Task 2.3 board description):**

- [ ] `StrategyB` class created in `src/strategies/strategy_b.py`
- [ ] RSI oversold (≤30) and overbought (≥70) detection implemented
- [ ] Bollinger Band calculation implemented (20-period SMA ± 2σ)
- [ ] Bollinger Band touch confirmation logic implemented
- [ ] Position sizing parameters noted (10% max position, 2% max risk — enforced at Risk Layer)
- [ ] Take profit 8%, stop loss 15% implemented in signal generation
- [ ] Time stop 45 minutes noted in config (enforcement happens at execution layer)
- [ ] All Strategy B unit tests pass (from Coverage 1.1.4)
- [ ] Integration tests with mock market data pass
- [ ] `StrategyB` is importable from `src.strategies` module

**Quality Gates:**
- [ ] `ruff .` passes with zero warnings
- [ ] `black .` formatting applied
- [ ] `mypy src/strategies/strategy_b.py` passes with zero errors
- [ ] `pytest tests/unit/test_strategies.py -k StrategyB` passes 100%

**Code Quality Standards:**
- Type hints on all methods and parameters
- Docstrings on class and public methods (Google style)
- No magic numbers (all parameters from `StrategyBConfig`)
- Error handling for insufficient data edge cases

---

### 8. EDGE CASES TO TEST

**Test Scenarios (from Coverage 1.1.4):**

1. **RSI Extreme Detection:**
   - What happens if RSI is exactly 30 (oversold threshold)?
   - What happens if RSI is exactly 70 (overbought threshold)?
   - What happens if RSI is 25 (extreme oversold, bonus confidence)?
   - What happens if RSI is 75 (extreme overbought, bonus confidence)?
   - What happens if RSI is 50 (neutral, no signal)?

2. **Bollinger Band Touch Detection:**
   - What happens if price exactly touches lower BB (close == bb_lower)?
   - What happens if price breaches lower BB (close < bb_lower)?
   - What happens if price exactly touches upper BB (close == bb_upper)?
   - What happens if price breaches upper BB (close > bb_upper)?
   - What happens if price is within bands (no BB confirmation)?

3. **VIX Regime Validation:**
   - What happens if VIX is exactly 18 (Strategy B lower bound)?
   - What happens if VIX is exactly 25 (Strategy B upper bound)?
   - What happens if VIX is 15 (below range, confidence penalty)?
   - What happens if VIX is 30 (above range, confidence penalty)?
   - What happens if VIX is 21 (mid-range, no penalty)?

4. **Confidence Calculation:**
   - What happens if RSI is extreme (≤25 or ≥75) AND BB is breached (max bonuses)?
   - What happens if RSI is at threshold (30/70) AND BB is only touched (base confidence)?
   - What happens if VIX is out of range (penalty applies)?
   - What happens if all bonuses apply but VIX penalty also applies (net confidence)?

5. **Data Quality Edge Cases:**
   - What happens if historical_close has only 19 data points (insufficient for BB 20)?
   - What happens if historical_close is empty?
   - What happens if close price is zero or negative (invalid data)?
   - What happens if VIX is missing from MarketData?

6. **Signal Generation Edge Cases:**
   - What happens if RSI ≤ 30 but price doesn't touch BB lower (should return NEUTRAL)?
   - What happens if price touches BB lower but RSI > 30 (should return NEUTRAL)?
   - What happens if both LONG and SHORT conditions are met simultaneously (impossible, but defensive check)?
   - What happens if Bollinger Bands are flat (zero standard deviation)?

**Expected Test Behavior:**
- Strategy B tests should cover ~20-25 test cases (subset of Coverage 1.1.4 strategy tests)
- Tests use mocked `MarketData` with known RSI/BB values
- Tests validate both signal generation and confidence scoring
- Edge case tests validate error handling and boundary conditions

---

### 9. ROLLBACK PLAN

**How to Disable This Feature Without Breaking Existing Functionality:**

1. **Remove from exports:**
   - Remove `StrategyB` from `src/strategies/__init__.py`
   - This prevents orchestrator from importing the strategy

2. **Skip in orchestrator:**
   - If orchestrator already has Strategy B integration, add a feature flag:
     ```python
     ENABLE_STRATEGY_B = False  # Disable Strategy B

     if gameplan.strategy == "B" and not ENABLE_STRATEGY_B:
         # Fall back to Strategy C (cash preservation)
         return StrategyCConfig()
     ```

3. **Tests remain:**
   - Keep Strategy B tests in the suite but mark them as `@pytest.mark.skip(reason="Strategy B disabled")`
   - This preserves the test specification for future re-enablement

**Dependencies That Won't Break:**
- Task 2.1 (Base Strategy) is independent of Strategy B
- Tasks 2.2 (Strategy A) and 2.4 (Strategy C) are siblings, not dependents
- Task 2.5+ (Risk Controls, Gateway) don't care which specific strategy is active

**Safest Rollback:**
- Delete `src/strategies/strategy_b.py`
- Remove `StrategyB` export from `__init__.py`
- Update orchestrator to reject Strategy B selection in gameplan (default to Strategy C)

---

## IMPLEMENTATION GUIDANCE

### Recommended Implementation Order

1. **Start with structure:**
   - Create `src/strategies/strategy_b.py`
   - Define `StrategyB` class inheriting from `StrategyBase`
   - Stub out `analyze()` method returning NEUTRAL signal

2. **Implement indicators (bottom-up):**
   - Implement `calculate_rsi()` helper method (can copy from Strategy A if desired)
   - Implement `calculate_bollinger_bands()` helper method
   - Validate against known test values

3. **Implement signal logic:**
   - Add RSI extreme detection (≤30 for LONG, ≥70 for SHORT)
   - Add Bollinger Band touch/breach detection
   - Return LONG/SHORT signals when both conditions are met

4. **Implement confidence scoring:**
   - Add `calculate_confidence_long()` helper
   - Add `calculate_confidence_short()` helper
   - Validate confidence ranges (must be 0.0-1.0)

5. **Add error handling:**
   - Validate `MarketData.historical_close` length (min 20 for BB)
   - Handle missing VIX gracefully
   - Catch edge cases in indicator calculations (e.g., zero std dev for BB)

6. **Run tests:**
   - Run `pytest tests/unit/test_strategies.py -k StrategyB`
   - Fix failures iteratively
   - Validate coverage (should hit 85%+ for Strategy B code)

### Code Quality Checkpoints

**Before committing:**
```bash
# Formatting
black src/strategies/strategy_b.py

# Linting
ruff src/strategies/strategy_b.py

# Type checking
mypy src/strategies/strategy_b.py

# Tests
pytest tests/unit/test_strategies.py -k StrategyB -v

# Coverage
pytest --cov=src.strategies.strategy_b tests/unit/test_strategies.py -k StrategyB
```

**Expected Output:**
- ruff: 0 warnings
- black: Already formatted or auto-formatted
- mypy: Success, no issues found
- pytest: All Strategy B tests pass (100%)
- coverage: 85%+ line coverage

### Common Pitfalls to Avoid

1. **Bollinger Band Calculation Errors:**
   - SMA is the mean of the last `period` prices, not all prices
   - Standard deviation uses the same `period` window as SMA
   - Upper band = SMA + (std_dev_multiplier * std), not SMA * std_dev_multiplier
   - Handle case where all prices are identical (std = 0, bands collapse to SMA)

2. **RSI Threshold Inclusivity:**
   - RSI ≤ 30 includes both 30 and values below (e.g., 25, 20)
   - RSI ≥ 70 includes both 70 and values above (e.g., 75, 80)
   - Don't use strict inequality (`<` or `>`) unless intended

3. **Confidence Clamping:**
   - Always clamp confidence to [0.0, 1.0] after bonuses/penalties
   - VIX penalty can make confidence negative — must clamp to 0.0 minimum
   - Validate in tests: `assert 0.0 <= signal.confidence <= 1.0`

4. **Mean Reversion Logic:**
   - LONG signal when oversold (expecting price to bounce UP from extreme)
   - SHORT signal when overbought (expecting price to fall DOWN from extreme)
   - This is opposite of momentum strategies (which chase price direction)

5. **VIX Dependency:**
   - Strategy B requires `MarketData.vix` for regime validation
   - Handle missing VIX gracefully (e.g., default to no penalty, or return NEUTRAL)
   - Orchestrator must ensure VIX is provided when Strategy B is active

---

## TESTING STRATEGY

### Unit Test Coverage (Coverage 1.1.4)

**Existing tests in `tests/unit/test_strategies.py` validate:**

1. **Class instantiation:**
   - `StrategyB(config)` accepts a `StrategyBConfig` instance
   - Default config values are applied if not provided

2. **RSI calculation:**
   - RSI returns correct values for known price series
   - RSI handles all-gains and all-losses edge cases
   - RSI raises `ValueError` if insufficient data points

3. **Bollinger Bands calculation:**
   - BB upper/middle/lower bands are calculated correctly for known price series
   - BB handles case where std = 0 (all prices identical)
   - BB raises `ValueError` if insufficient data points

4. **Extreme detection:**
   - Oversold: RSI ≤ 30
   - Overbought: RSI ≥ 70
   - Boundary cases: RSI = 30, RSI = 70

5. **Signal generation:**
   - LONG signal when: RSI ≤ 30 AND price ≤ BB_lower
   - SHORT signal when: RSI ≥ 70 AND price ≥ BB_upper
   - NEUTRAL signal when conditions are not met

6. **Confidence scoring:**
   - Base confidence is 0.5
   - Bonuses applied correctly (extreme RSI, BB breach)
   - VIX penalty applied when VIX is out of range [18, 25]
   - Confidence is clamped to [0.0, 1.0]

7. **Stop loss and take profit:**
   - Stop loss is 15% below entry for LONG (entry * 0.85)
   - Take profit is 8% above entry for LONG (entry * 1.08)
   - Stop loss is 15% above entry for SHORT (entry * 1.15)
   - Take profit is 8% below entry for SHORT (entry * 0.92)

### Integration Test Coverage

**Integration tests (if any) validate:**
- Strategy B integrates correctly with `StrategyBase` interface
- Strategy B can be instantiated by orchestrator (future task)
- Signal output format matches what execution layer expects

---

## REFERENCE MATERIALS

**Crucible v4.1 Strategy Library (Strategy B Specification):**

```
### Strategy B: "Mean Reversion Fade" (VIX 18–25, Choppy Markets)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Symbols | SPY only | Single symbol reduces complexity |
| RSI Oversold/Overbought | 30 / 70 | Deep extremes only |
| Bollinger Band | Touch 2σ band | Confirmation of extreme |
| Max Risk % | 2% ($12) | Reduced sizing for higher vol |
| Max Position % | 10% ($60) | Half of Strategy A |
| Take Profit | 8% | Quick scalp |
| Stop Loss | 15% | Tighter for mean reversion |
| Time Stop | 45 minutes | Faster exit |
| Expiry | Weekly, min 5 DTE | More time value for reversion |
| Moneyness | 1 strike OTM | Cheaper premium |
```

**Note:** Position sizing (10% max, 2% risk) is enforced at the **Risk Layer (Task 2.5)**, not in Strategy B itself. Strategy B only generates signals with stop loss and take profit levels.

---

## POST-IMPLEMENTATION VALIDATION

**After implementation is complete, verify:**

1. **All tests pass:**
   ```bash
   pytest tests/unit/test_strategies.py -k StrategyB -v
   ```

2. **Code quality gates pass:**
   ```bash
   ruff src/strategies/strategy_b.py
   black --check src/strategies/strategy_b.py
   mypy src/strategies/strategy_b.py
   ```

3. **Strategy B is importable:**
   ```python
   from src.strategies import StrategyB
   from src.strategies.config import StrategyBConfig

   config = StrategyBConfig()
   strategy = StrategyB(config)
   print(f"Strategy B initialized: {strategy}")
   ```

4. **Signal generation works end-to-end:**
   ```python
   from src.strategies.base import MarketData
   from datetime import datetime

   # Create mock market data (RSI oversold, price touches BB lower)
   data = MarketData(
       symbol="SPY",
       timestamp=datetime.now(),
       open=685.0,
       high=686.0,
       low=683.0,
       close=683.5,  # At lower BB
       volume=80_000_000,
       vwap=686.0,
       vix=21.0,  # Within Strategy B range [18, 25]
       historical_close=[690.0, 688.0, 687.0, 685.5, 684.0, 683.5]  # Downtrend
   )

   signal = strategy.analyze(data)
   assert signal.direction == Direction.LONG  # Fade oversold
   assert 0.5 <= signal.confidence <= 1.0
   assert signal.stop_loss < signal.entry_price
   assert signal.take_profit > signal.entry_price
   ```

5. **Documentation is complete:**
   - Class docstring explains what Strategy B does
   - Method docstrings explain parameters and return values
   - Inline comments clarify complex logic (e.g., confidence calculation)

---

## FINAL CHECKLIST

**Before marking Task 2.3 complete:**

- [ ] `src/strategies/strategy_b.py` created
- [ ] `StrategyB` class implemented
- [ ] `calculate_rsi()` helper implemented
- [ ] `calculate_bollinger_bands()` helper implemented
- [ ] `calculate_confidence_long()` helper implemented
- [ ] `calculate_confidence_short()` helper implemented
- [ ] RSI extreme detection logic implemented (≤30 for LONG, ≥70 for SHORT)
- [ ] Bollinger Band touch/breach logic implemented
- [ ] VIX regime validation implemented (penalty if VIX not in [18, 25])
- [ ] Signal generation returns correct `Signal` dataclass
- [ ] Stop loss and take profit levels calculated correctly
- [ ] Error handling for insufficient data implemented
- [ ] `StrategyB` added to `src/strategies/__init__.py` exports
- [ ] All type hints present (mypy passes)
- [ ] All docstrings present (Google style)
- [ ] ruff + black + mypy pass with zero warnings
- [ ] All Strategy B unit tests pass (from Coverage 1.1.4)
- [ ] Code coverage ≥ 85% for `strategy_b.py`
- [ ] Manual smoke test with mock `MarketData` passes
- [ ] Task 2.3 marked complete on board (100% progress)
- [ ] Blueprint document archived for future reference

---

**END OF VSC HANDOFF DOCUMENT**

**Next Steps:**
1. Implement `src/strategies/strategy_b.py` following the logic flow above
2. Run tests and iterate until all pass
3. Run quality gates (ruff, black, mypy)
4. Mark Task 2.3 complete on board
5. Proceed to Task 2.4 (Strategy C - Cash Preservation)

**Estimated Implementation Time:** 3-4 hours (per task description)

**Model Routing Recommendation:** Sonnet (medium complexity, well-specified)

**Context Budget:** Medium (450-550 lines of code, 20-25 tests)
