# VSC HANDOFF: QA-2.6-001 Remediation — mypy Type Error Resolution

**Date:** 2026-02-09
**Task ID:** QA-2.6-001 (Board: IBKR Project Management)
**Type:** Remediation (Quality Gate Compliance)
**Requested By:** @QA_Lead (Phase 2 Completion Review)
**Blueprint Authors:** @Systems_Architect, @QA_Lead
**Estimated Effort:** 1-2 hours
**Model Recommendation:** Sonnet (tactical fix work)
**Context Budget:** Light (remediation, not new feature)

---

## CONTEXT BLOCK

### Purpose

Resolve 38 mypy type errors in the Gateway integration layer (`src/integrations/`) to restore quality gate compliance. These errors were introduced during Task 2.6 implementation when pre-commit hooks were bypassed using `git commit --no-verify` to meet delivery timeline.

**Critical:** This is a **quality-only** remediation. Functional behavior must NOT change. All 62 Gateway integration tests must continue passing. This is pure type annotation cleanup.

### Scope

**In Scope:**
- Add missing type annotations
- Fix incorrect type hints
- Resolve `Any` type usage where specific types can be inferred
- Import required typing constructs (`Optional`, `Union`, `List`, `Dict`, etc.)
- Fix return type mismatches
- Address attribute access type errors

**Out of Scope:**
- Functional logic changes
- Test modifications (unless tests fail due to type fixes)
- Refactoring beyond type safety
- Performance optimization
- Adding new features

### Current State

**Affected Modules (4 files, ~1,800 lines):**
1. `src/integrations/ibkr_gateway.py` — Gateway connection management
2. `src/integrations/market_data_pipeline.py` — Market data subscription and processing
3. `src/integrations/order_executor.py` — Order placement and tracking
4. `src/integrations/position_manager.py` — Position monitoring

**Error Count:** 38 mypy errors (distribution unknown without codebase access)

**Current Quality Status:**
- ✅ ruff (linting): PASS
- ✅ black (formatting): PASS
- ❌ mypy (type checking): FAIL (38 errors)
- ✅ pytest (62 tests): PASS (100%)
- ✅ Coverage: 85.32% (exceeds 85% target)

### Dependencies

**Upstream:** Task 2.6 (Gateway integration) — functionally complete
**Downstream:** Phase 2 formal closure — blocked until this resolves
**Parallel:** Phase 3 (automation layer) — authorized to proceed

### Success Criteria

**Definition of Done:**
- [ ] `poetry run mypy src/integrations/` returns 0 errors
- [ ] `poetry run mypy src/integrations/ --strict` returns 0 errors (stretch goal)
- [ ] All 62 Gateway integration tests still pass (`pytest tests/integration/test_gateway_*.py`)
- [ ] Pre-commit hooks pass without `--no-verify`
- [ ] `git commit` succeeds with hooks enabled
- [ ] ruff and black continue to pass (zero regressions)
- [ ] No functional behavior changes (test assertions unchanged)
- [ ] Task 2.6 approval status updated to FULL APPROVAL
- [ ] Phase 2 marked as formally closed

---

## AGENT EXECUTION BLOCK

### 1. Diagnostic Phase — Identify Error Patterns

**Objective:** Understand the 38 errors before fixing blindly.

**Steps:**

```bash
# Run mypy and capture full error output
poetry run mypy src/integrations/ > mypy_errors.txt 2>&1

# Review error output
cat mypy_errors.txt

# Categorize errors by type
# Common patterns to look for:
# - Missing return type annotations
# - Missing parameter type annotations
# - Incompatible return types
# - Attribute access on 'Any' types
# - Optional type mismatches (None vs. actual type)
# - List/Dict without generic types
```

**Expected Error Categories:**

Based on common mypy issues in ib_insync integrations:

1. **ib_insync type stubs missing** — ib_insync library may lack type hints
2. **Optional[] wrapping needed** — Functions returning None or value
3. **Any type propagation** — ib_insync objects typed as Any leak into our code
4. **Missing return types** — Functions without `-> ReturnType` annotations
5. **Attribute access errors** — Accessing attributes on ib_insync objects mypy doesn't recognize

**Action:** Review `mypy_errors.txt` and create mental model of fix strategy before editing code.

---

### 2. Fix Strategy — Type Annotation Patterns

**Pattern 1: ib_insync Library Types**

ib_insync likely lacks comprehensive type stubs. When mypy complains about ib_insync types:

```python
# Before (mypy error: IB has no attribute "connect")
from ib_insync import IB

def connect(self, ib: IB) -> bool:
    ib.connect()  # Error: "IB" has no attribute "connect"

# After (option 1: type: ignore comment)
def connect(self, ib: IB) -> bool:
    ib.connect()  # type: ignore[attr-defined]

# After (option 2: cast to Any for ib_insync interactions)
from typing import Any, cast

def connect(self, ib: IB) -> bool:
    cast(Any, ib).connect()
```

**Preference:** Use `# type: ignore[attr-defined]` sparingly and only for ib_insync library boundary. Do NOT use for our own code.

**Pattern 2: Optional Return Types**

```python
# Before (error: Incompatible return type)
def get_position(self, symbol: str) -> Position:
    if symbol not in self.positions:
        return None  # Error: None not compatible with Position
    return self.positions[symbol]

# After
from typing import Optional

def get_position(self, symbol: str) -> Optional[Position]:
    if symbol not in self.positions:
        return None
    return self.positions[symbol]
```

**Pattern 3: Missing Function Annotations**

```python
# Before (error: Function is missing type annotation)
def process_data(self, data):
    return data.close

# After
def process_data(self, data: MarketData) -> float:
    return data.close
```

**Pattern 4: Collection Generics**

```python
# Before (error: Missing type parameters for generic type)
def get_symbols(self) -> list:
    return self.symbols

# After
from typing import List

def get_symbols(self) -> List[str]:
    return self.symbols
```

**Pattern 5: Dict Type Annotations**

```python
# Before
def get_config(self) -> dict:
    return {"host": "127.0.0.1"}

# After
from typing import Dict

def get_config(self) -> Dict[str, str]:
    return {"host": "127.0.0.1"}
```

---

### 3. File-by-File Remediation Plan

**Recommended Order:**

1. **Start with `ibkr_gateway.py`** — Foundation module, likely has most errors
2. **Then `market_data_pipeline.py`** — Data flow module
3. **Then `order_executor.py`** — Execution module
4. **Finally `position_manager.py`** — Position tracking module

**For Each File:**

```bash
# 1. Run mypy on single file to isolate errors
poetry run mypy src/integrations/ibkr_gateway.py

# 2. Open file in editor
code src/integrations/ibkr_gateway.py

# 3. Fix errors top-to-bottom (mypy reports line numbers)
#    - Add missing type hints
#    - Fix incorrect type annotations
#    - Add type: ignore comments ONLY for ib_insync library boundaries

# 4. Re-run mypy on file
poetry run mypy src/integrations/ibkr_gateway.py

# 5. Once file passes, run tests for that module
pytest tests/integration/test_gateway_connection.py -v

# 6. Repeat for next file
```

---

### 4. Common Type Imports Needed

Add these to module imports as needed:

```python
from typing import (
    Any,           # Use sparingly, only for ib_insync boundaries
    Dict,          # For dictionary types
    List,          # For list types
    Optional,      # For values that can be None
    Union,         # For multiple possible types
    Tuple,         # For tuple types
    Callable,      # For function types
    cast,          # For explicit type casting
)
```

**Import Organization:**

```python
# Standard library
from typing import Dict, List, Optional

# Third-party
from ib_insync import IB, Contract

# Local
from src.broker.contracts import ContractBuilder
```

---

### 5. Validation Protocol

**After Each File Fix:**

```bash
# Type check the file
poetry run mypy src/integrations/<filename>.py

# Run related tests
pytest tests/integration/test_<module>*.py -v

# Verify no regressions
poetry run ruff check src/integrations/<filename>.py
poetry run black --check src/integrations/<filename>.py
```

**After All Files Fixed:**

```bash
# Full type check of integrations module
poetry run mypy src/integrations/

# Full test suite (all 62 Gateway tests)
pytest tests/integration/test_gateway*.py -v

# Verify full test suite still passes
poetry run pytest

# Verify coverage unchanged
poetry run pytest --cov=src/integrations --cov-report=term

# Quality gates
poetry run ruff check src/integrations/
poetry run black --check src/integrations/
poetry run mypy src/integrations/
```

**Expected Results:**
- mypy: 0 errors (was 38)
- pytest: 62/62 passing (no change)
- Coverage: 85.32% (no change)
- ruff: PASS (no regressions)
- black: PASS (no regressions)

---

### 6. Edge Cases & Gotchas

**Edge Case 1: ib_insync Callback Types**

ib_insync uses callbacks extensively. These may not have type stubs.

```python
# If mypy complains about callback signatures
def on_bar_update(self, bars, hasNewBar):  # Error: missing annotations
    pass

# Fix with type: ignore if ib_insync contract unknown
def on_bar_update(  # type: ignore[no-untyped-def]
    self,
    bars,  # type: ignore[no-untyped-def]
    hasNewBar: bool
) -> None:
    pass
```

**Edge Case 2: Contract Objects**

ib_insync Contract objects may be typed as Any:

```python
# Instead of trying to type ib_insync.Contract
from ib_insync import Contract
from typing import Any

def create_contract(self, symbol: str) -> Any:  # Accept we can't type ib_insync objects
    return Contract(symbol=symbol, secType="OPT")
```

**Edge Case 3: Async Functions**

If any integration code uses async (unlikely but possible):

```python
from typing import Awaitable

async def connect_async(self) -> Awaitable[bool]:
    # implementation
```

**Edge Case 4: Nested Generics**

```python
# Complex return type
def get_positions(self) -> Dict[str, List[Position]]:
    return self._positions_by_symbol
```

---

### 7. Testing Strategy

**Test Categories to Validate:**

1. **Unit Tests (if any exist):**
   ```bash
   pytest tests/unit/test_integrations/ -v
   ```

2. **Integration Tests (62 tests):**
   ```bash
   pytest tests/integration/test_gateway*.py -v
   ```

3. **Type Checking Tests:**
   ```bash
   # Verify mypy catches intentional errors (add a bad type, mypy should fail)
   # Then revert and confirm it passes
   ```

**Regression Prevention:**

- Do NOT modify test assertions
- Do NOT change function signatures that tests depend on
- If a type fix breaks a test, investigate why (may indicate incorrect fix)

**Success Criteria:**
- All existing tests pass (62/62)
- mypy errors: 38 → 0
- No new test failures introduced

---

### 8. Pre-Commit Hook Re-Enablement

**After all fixes complete:**

```bash
# Verify pre-commit hooks work
pre-commit run --all-files

# Should pass:
# - black
# - ruff
# - mypy (the critical one)

# Test commit with hooks enabled
git add src/integrations/
git commit -m "fix(integrations): Resolve 38 mypy type errors (QA-2.6-001)"

# Should succeed without --no-verify flag
```

**If pre-commit fails:**
- Review the specific error
- Fix and retry
- Do NOT use `--no-verify` to bypass

---

### 9. Commit & Documentation

**Commit Message:**

```
fix(integrations): Resolve 38 mypy type errors (QA-2.6-001)

REMEDIATION TASK: Quality gate compliance restoration

Changes:
- Added missing type annotations to 4 Gateway integration modules
- Fixed Optional[] return types for nullable values
- Added typing imports (Dict, List, Optional, etc.)
- Applied type: ignore comments only for ib_insync library boundaries
- Restored pre-commit hook compliance

Scope:
- src/integrations/ibkr_gateway.py
- src/integrations/market_data_pipeline.py
- src/integrations/order_executor.py
- src/integrations/position_manager.py

Impact:
- mypy errors: 38 → 0
- Tests: 62/62 passing (no change)
- Coverage: 85.32% (no change)
- Quality gates: ALL PASS (ruff, black, mypy)

Related:
- Task 2.6: Approval status → FULL APPROVAL
- Task 2.8: Phase 2 review → CONDITIONAL PASS pending this fix
- Phase 2: Formal closure UNBLOCKED

Refs: QA-2.6-001, Task 2.6, Task 2.8
```

**Board Updates Required:**

1. Mark QA-2.6-001 task complete
2. Update Task 2.6 description: "QA 🟡 CONDITIONAL" → "QA ✅ FULL APPROVAL"
3. Update Phase 2 status: "CONDITIONALLY COMPLETE" → "COMPLETE"
4. Notify @QA_Lead and @CRO of remediation completion

---

### 10. Definition of Done Checklist

**Code Quality:**
- [ ] `poetry run mypy src/integrations/` returns 0 errors
- [ ] `poetry run ruff check src/integrations/` returns 0 warnings
- [ ] `poetry run black --check src/integrations/` confirms formatting
- [ ] Pre-commit hooks pass without `--no-verify`

**Testing:**
- [ ] All 62 Gateway integration tests passing
- [ ] Full test suite passing (`pytest`)
- [ ] Coverage at 85.32% or higher (no regression)

**Functional Validation:**
- [ ] No test assertions modified
- [ ] No function signature changes (public API stable)
- [ ] No behavioral changes (pure type annotation)

**Process:**
- [ ] Git commit successful with hooks enabled
- [ ] Commit message follows template above
- [ ] Task QA-2.6-001 marked complete on board
- [ ] Task 2.6 approval status updated to FULL
- [ ] Phase 2 status updated to COMPLETE

**Approvals:**
- [ ] @QA_Lead: Review commit and confirm quality gates
- [ ] @CRO: Confirm no capital risk introduced (should be none)
- [ ] @PM: Mark Phase 2 as formally closed

---

## IMPLEMENTATION GUIDANCE

### Recommended Workflow

**Session 1: Diagnostic (15-20 minutes)**
1. Run full mypy scan, save output
2. Categorize errors by type
3. Identify which files have most errors
4. Plan fix order

**Session 2: Core Fixes (30-45 minutes)**
1. Fix `ibkr_gateway.py` (likely highest error count)
2. Fix `market_data_pipeline.py`
3. Validate tests after each file

**Session 3: Final Fixes (20-30 minutes)**
1. Fix `order_executor.py`
2. Fix `position_manager.py`
3. Run full validation suite

**Session 4: Validation & Commit (15-20 minutes)**
1. Full quality gate validation
2. Pre-commit hook test
3. Git commit with hooks enabled
4. Board updates

**Total Estimated Time:** 1.5-2 hours

### Error Resolution Priority

**Priority 1 (fix first):**
- Missing return type annotations (most common)
- Missing parameter type annotations
- Easy wins that clear many errors

**Priority 2 (fix second):**
- Optional[] type wrapping for nullable values
- Dict/List generic type parameters

**Priority 3 (fix last):**
- ib_insync library boundary type: ignore comments
- Complex nested types
- Edge case type issues

### When Stuck

**If mypy error is unclear:**
1. Read the full error message (line number, description)
2. Check mypy documentation: https://mypy.readthedocs.io/
3. Search for error code (e.g., "error: Incompatible return type")
4. Consider: Is this our code or ib_insync library boundary?

**If fix breaks tests:**
1. Review what changed (type annotation only, or logic?)
2. Check if test assertion was relying on incorrect behavior
3. If in doubt, revert the fix and flag for @Systems_Architect review

**If stuck on ib_insync types:**
1. Use `# type: ignore[attr-defined]` for ib_insync library calls
2. Document why in comment: `# ib_insync lacks type stubs`
3. Focus on typing OUR code correctly, not the library

---

## QUALITY GATES

### Pre-Fix Baseline

```bash
# Capture baseline before starting
poetry run mypy src/integrations/ | tee mypy_baseline.txt
poetry run pytest tests/integration/test_gateway*.py | tee test_baseline.txt
```

### Post-Fix Validation

```bash
# Must all pass
poetry run mypy src/integrations/              # 0 errors
poetry run ruff check src/integrations/        # 0 warnings
poetry run black --check src/integrations/     # All files formatted
poetry run pytest tests/integration/test_gateway*.py -v  # 62/62 passing
pre-commit run --all-files                     # All hooks pass
```

### Acceptance Gate

**Operator must verify:**
- mypy output: "Success: no issues found"
- pytest output: "62 passed"
- pre-commit: "Passed"
- git commit succeeds without `--no-verify`

**If any gate fails:** Fix is incomplete, do not commit.

---

## ROLLBACK PLAN

**If fixes introduce test failures:**

```bash
# Revert all changes
git checkout src/integrations/

# Or revert specific file
git checkout src/integrations/ibkr_gateway.py

# Re-run tests to confirm baseline restored
pytest tests/integration/test_gateway*.py -v
```

**If mypy fixes incomplete:**
- Identify remaining errors
- Continue fixing
- Do NOT commit partial fixes (all 38 must resolve)

**If stuck beyond 2-hour estimate:**
- Document progress (how many errors resolved)
- Flag blockers for @Systems_Architect review
- Update task estimate and due date

---

## HANDOFF NOTES

### Context for Factory Floor

**This is pure type annotation cleanup.** No functional changes permitted. Think of it as adding compiler hints to code that already works correctly.

**The goal:** Make mypy happy without changing what the code does.

**The test:** If ANY of the 62 tests fail after your changes, you changed functional behavior (revert and try again).

**Common pitfall:** Over-constraining types. If mypy forces you to make a type more specific than the code actually handles, you may need `Union[]` or to keep the broader type.

**Success looks like:**
- mypy: 38 errors → 0 errors
- tests: 62 passing → 62 passing (no change)
- coverage: 85.32% → 85.32% (no change)
- Pre-commit hooks: FAIL → PASS

**Time budget:** 1-2 hours. If exceeding, stop and escalate.

---

**Blueprint Status:** ✅ COMPLETE
**Ready for Factory Floor:** YES
**Estimated Effort:** 1-2 hours
**Priority:** Urgent (blocks Phase 2 formal closure)
**Model Recommendation:** Sonnet
**Quality Gates:** mypy (critical), ruff, black, pytest
**Success Metric:** 0 mypy errors, 62/62 tests passing

---

*VSC Handoff Template Version: v2.0*
*Authors: @Systems_Architect, @QA_Lead*
*Task: QA-2.6-001 (IBKR Project Management Board)*
*Charter & Stone Capital — IBKR Trading Bot Project*
*Generated: 2026-02-09*
