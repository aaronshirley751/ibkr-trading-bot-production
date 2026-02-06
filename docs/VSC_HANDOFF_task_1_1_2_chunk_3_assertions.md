# VSC HANDOFF: Task 1.1.2 Chunk 3 - Test Assertion Helpers

**Document ID:** `VSC_HANDOFF_task_1_1_2_chunk_3_assertions.md`
**Created:** 2026-02-06
**Author:** @Systems_Architect
**Reviewed By:** @QA_Lead
**Task Reference:** Phase 1 - Test Suite Migration (Task 1.1.2, Chunk 3)

---

## 1. OBJECTIVE

Create a centralized module of custom assertion helpers that provide domain-specific, descriptive error messages for trading bot test failures. These helpers will improve test readability and maintainability by replacing repetitive assertion patterns with clear, reusable functions.

**Why This Matters:**
- Reduces code duplication across test files
- Provides consistent, descriptive error messages
- Makes test intent clearer and more maintainable
- Simplifies debugging when tests fail

---

## 2. FILE STRUCTURE

### Files to Create

```
tests/helpers/assertions.py          # NEW - Custom assertion helpers
```

### Files to Modify

```
None (pure addition)
```

---

## 3. IMPLEMENTATION SPECIFICATION

### 3.1 Custom Assertion Helpers Module

**File:** `tests/helpers/assertions.py`

```python
"""Custom assertion helpers for trading bot tests."""
from typing import Dict, Optional


def assert_price_within_tolerance(
    actual: float,
    expected: float,
    tolerance: float = 0.01,
    msg: Optional[str] = None
) -> None:
    """Assert that actual price is within tolerance of expected price.

    Args:
        actual: The actual price value
        expected: The expected price value
        tolerance: Acceptable difference (default 1 cent)
        msg: Optional custom error message

    Raises:
        AssertionError: If prices differ by more than tolerance
    """
    diff = abs(actual - expected)
    if diff > tolerance:
        error_msg = (
            f"Price {actual} not within tolerance {tolerance} of expected {expected}. "
            f"Difference: {diff}"
        )
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)


def assert_position_exists(
    portfolio: Dict[str, int],
    symbol: str,
    expected_quantity: int,
    msg: Optional[str] = None
) -> None:
    """Assert that a position exists with the expected quantity.

    Args:
        portfolio: Dictionary mapping symbols to quantities
        symbol: The symbol to check
        expected_quantity: The expected position quantity
        msg: Optional custom error message

    Raises:
        AssertionError: If position doesn't exist or quantity doesn't match
    """
    if symbol not in portfolio:
        error_msg = f"Position for {symbol} not found in portfolio. Portfolio: {portfolio}"
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)

    actual_quantity = portfolio[symbol]
    if actual_quantity != expected_quantity:
        error_msg = (
            f"Position quantity for {symbol} is {actual_quantity}, "
            f"expected {expected_quantity}"
        )
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)


def assert_no_position(
    portfolio: Dict[str, int],
    symbol: str,
    msg: Optional[str] = None
) -> None:
    """Assert that no position exists for the given symbol.

    Args:
        portfolio: Dictionary mapping symbols to quantities
        symbol: The symbol to check
        msg: Optional custom error message

    Raises:
        AssertionError: If position exists for the symbol
    """
    if symbol in portfolio and portfolio[symbol] != 0:
        error_msg = (
            f"Unexpected position for {symbol}: {portfolio[symbol]} shares. "
            f"Expected no position."
        )
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)
```

---

## 4. DEPENDENCIES

### Python Imports
```python
from typing import Dict, Optional
```

**Standard Library Only:** No external dependencies required.

### Integration Dependencies
- Will be imported by test modules across the test suite
- Complements existing fixtures in `tests/conftest.py`
- No runtime dependencies on production code

---

## 5. INPUT/OUTPUT CONTRACT

### `assert_price_within_tolerance`

**Input:**
```python
actual: float          # The actual price from test execution
expected: float        # The expected price value
tolerance: float       # Maximum acceptable difference (default: 0.01)
msg: Optional[str]     # Custom error message prefix
```

**Output:**
```python
None                   # Function returns nothing on success
# Raises AssertionError with descriptive message on failure
```

**Example Usage:**
```python
assert_price_within_tolerance(actual=100.015, expected=100.00, tolerance=0.02)
# Passes: difference is 0.015, within 0.02 tolerance

assert_price_within_tolerance(actual=100.03, expected=100.00, tolerance=0.01)
# Raises: Price 100.03 not within tolerance 0.01 of expected 100.00. Difference: 0.03
```

### `assert_position_exists`

**Input:**
```python
portfolio: Dict[str, int]  # Symbol -> Quantity mapping
symbol: str                # Symbol to verify
expected_quantity: int     # Expected position size
msg: Optional[str]         # Custom error message prefix
```

**Output:**
```python
None                       # Function returns nothing on success
# Raises AssertionError if position missing or quantity wrong
```

**Example Usage:**
```python
portfolio = {"SPY": 100, "QQQ": 50}
assert_position_exists(portfolio, "SPY", 100)  # Passes
assert_position_exists(portfolio, "AAPL", 10)  # Raises: Position for AAPL not found
```

### `assert_no_position`

**Input:**
```python
portfolio: Dict[str, int]  # Symbol -> Quantity mapping
symbol: str                # Symbol to verify absence of
msg: Optional[str]         # Custom error message prefix
```

**Output:**
```python
None                       # Function returns nothing on success
# Raises AssertionError if position exists with non-zero quantity
```

**Example Usage:**
```python
portfolio = {"SPY": 100}
assert_no_position(portfolio, "QQQ")   # Passes
assert_no_position(portfolio, "SPY")   # Raises: Unexpected position for SPY: 100 shares
```

---

## 6. INTEGRATION POINTS

### Test Module Imports
```python
# In any test file
from tests.helpers.assertions import (
    assert_price_within_tolerance,
    assert_position_exists,
    assert_no_position,
)
```

### Usage Pattern in Tests
```python
def test_order_execution(mock_broker):
    # Execute order logic
    result = execute_order(...)

    # Use custom assertions for clarity
    assert_price_within_tolerance(result.fill_price, 100.00, tolerance=0.05)
    assert_position_exists(mock_broker.positions, "SPY", 100)
```

### No Production Code Integration
These helpers are test-only utilities and have no integration with production modules.

---

## 7. DEFINITION OF DONE

### Code Quality Gates
- [ ] `ruff check tests/helpers/assertions.py` → Zero warnings
- [ ] `black tests/helpers/assertions.py --check` → No formatting needed
- [ ] `mypy tests/helpers/assertions.py` → Type checking passes
- [ ] File exists at correct path: `tests/helpers/assertions.py`

### Functional Validation
- [ ] File can be imported: `python -c "from tests.helpers.assertions import assert_price_within_tolerance"`
- [ ] No syntax errors or import failures
- [ ] Module docstring present and accurate

### Documentation
- [ ] Each function has complete docstring with Args, Raises sections
- [ ] Type hints present for all parameters and return values
- [ ] Code comments explain non-obvious logic (none required for this simple module)

### Ready for Integration
- [ ] @QA_Lead approval received
- [ ] File committed to version control
- [ ] Ready for use in migrated test files

---

## 8. EDGE CASES & TEST SCENARIOS

### Edge Case 1: Floating-Point Precision
**Scenario:** Comparing prices that are results of floating-point arithmetic
**Example:**
```python
# This might fail with strict equality due to FP precision
calculated = 0.1 + 0.2  # 0.30000000000000004
assert_price_within_tolerance(calculated, 0.3, tolerance=0.0001)  # Should pass
```
**Mitigation:** Default tolerance of 0.01 (1 cent) handles most practical cases

### Edge Case 2: Empty Portfolio
**Scenario:** Asserting position absence on empty portfolio
**Example:**
```python
assert_no_position({}, "SPY")  # Should pass
```
**Expected:** Passes cleanly - no position in empty dict is valid

### Edge Case 3: Zero Quantity Position
**Scenario:** Portfolio has symbol key but zero quantity
**Example:**
```python
assert_no_position({"SPY": 0}, "SPY")  # Should pass
```
**Expected:** Passes - zero quantity treated as no position

### Edge Case 4: None Values
**Scenario:** Handling None in price comparisons
**Example:**
```python
assert_price_within_tolerance(None, 100.0)  # Will raise TypeError
```
**Expected:** This is intentional - None prices indicate test setup failure

### Edge Case 5: Negative Quantities (Short Positions)
**Scenario:** Future support for short positions
**Example:**
```python
assert_position_exists({"SPY": -100}, "SPY", -100)  # Should work
```
**Expected:** Current implementation supports this - quantity is just an int

### Edge Case 6: Custom Error Messages
**Scenario:** Providing context-specific error messages
**Example:**
```python
assert_position_exists(
    portfolio,
    "SPY",
    100,
    msg="After stop-loss trigger"
)
# Failure: "After stop-loss trigger: Position for SPY not found in portfolio..."
```
**Expected:** Custom message prepended to standard error message

---

## 9. ROLLBACK PLAN

### If Assertions Module Causes Issues

**Rollback Steps:**
1. Remove import statements from any test files using these helpers
2. Delete `tests/helpers/assertions.py`
3. Replace custom assertions with standard `assert` statements in affected tests

**Minimal Impact:** Since this is a new module with no production code dependencies, rollback is trivial. Only test files would need updates.

### Temporary Disable (If Needed)
```python
# In tests/helpers/assertions.py - comment out problematic function
# def assert_price_within_tolerance(...):
#     pass  # Temporarily disabled

# Tests will fail with NameError, making the issue obvious
```

---

## 10. QUALITY VALIDATION COMMANDS

Run these commands in sequence to validate the implementation:

```bash
# 1. Verify file exists
ls -la tests/helpers/assertions.py

# 2. Syntax and style check
ruff check tests/helpers/assertions.py

# 3. Code formatting validation
black tests/helpers/assertions.py --check

# 4. Type checking
mypy tests/helpers/assertions.py

# 5. Import validation (should produce no output)
python -c "from tests.helpers.assertions import assert_price_within_tolerance, assert_position_exists, assert_no_position"

# 6. Verify module docstring
python -c "import tests.helpers.assertions; print(tests.helpers.assertions.__doc__)"
```

**Expected Results:**
- `ls`: File exists, ~2KB size
- `ruff`: No warnings or errors
- `black`: "All done! ✨ 🍰 ✨" with no files changed
- `mypy`: "Success: no issues found"
- Import command: No output (success)
- Docstring: "Custom assertion helpers for trading bot tests."

---

## 11. FOLLOW-UP TASKS

### Immediate Next Steps
1. **Update `tests/helpers/__init__.py`** (if it doesn't exist, create it):
   ```python
   """Test helper modules."""
   from tests.helpers.assertions import (
       assert_price_within_tolerance,
       assert_position_exists,
       assert_no_position,
   )

   __all__ = [
       "assert_price_within_tolerance",
       "assert_position_exists",
       "assert_no_position",
   ]
   ```

2. **Document Usage Patterns:** Consider adding `tests/helpers/README.md` explaining when to use custom assertions vs. standard `assert`

3. **Begin Test Migration:** Start using these helpers in migrated test files

### Future Enhancements (Post-Phase 1)
- Add `assert_order_filled(order, expected_quantity, expected_price)` helper
- Add `assert_risk_limits_respected(positions, account_balance, max_risk_pct)` helper
- Add `assert_strategy_state(strategy, expected_state)` helper
- Consider `pytest-check` integration for multiple soft assertions

---

## 12. COPILOT-READY PROMPT

**Copy this section to VSCode Copilot Chat:**

```
Create tests/helpers/assertions.py with custom assertion helpers for the trading bot test suite.

REQUIREMENTS:
1. Create file at: tests/helpers/assertions.py
2. Implement three assertion functions with full type hints
3. Each function should raise AssertionError with descriptive messages
4. All functions accept optional custom message parameter

FUNCTION 1: assert_price_within_tolerance
- Parameters: actual (float), expected (float), tolerance (float = 0.01), msg (Optional[str] = None)
- Validates actual price is within tolerance of expected
- Default tolerance: 0.01 (1 cent)
- Error message should include actual, expected, and difference

FUNCTION 2: assert_position_exists
- Parameters: portfolio (Dict[str, int]), symbol (str), expected_quantity (int), msg (Optional[str] = None)
- Validates symbol exists in portfolio with expected quantity
- Error if symbol missing: show full portfolio
- Error if quantity wrong: show actual vs expected

FUNCTION 3: assert_no_position
- Parameters: portfolio (Dict[str, int]), symbol (str), msg (Optional[str] = None)
- Validates symbol not in portfolio OR has zero quantity
- Error message should show unexpected quantity found

VALIDATION:
After implementation, run:
- ruff check tests/helpers/assertions.py
- black tests/helpers/assertions.py --check
- mypy tests/helpers/assertions.py

All should pass with zero issues.
```

---

**Document Status:** ✅ Ready for Implementation
**Approvals:** @Systems_Architect (author), @QA_Lead (reviewer)
**Next Action:** Factory Floor implementation via VSCode Copilot

---

*@Systems_Architect signing off. This handoff document is complete and ready for the Factory Floor. The implementation is straightforward with clear validation criteria.*
