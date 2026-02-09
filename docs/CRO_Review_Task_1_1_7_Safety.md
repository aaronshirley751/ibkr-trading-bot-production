# CRO SAFETY REVIEW: Task 1.1.7 — test_safety_scenarios.py

**Date:** 2026-02-08
**Reviewer:** @CRO (Chief Risk Officer)
**Target:** `tests/e2e/test_safety_scenarios.py` (commit d626261)
**Verdict:** CLEARED WITH CONDITIONS
**Board Task:** Coverage-1.1.7 (99csrk8qqkuM2jYAV5a2MWUAJifJ)

---

## 1. REVIEW CONTEXT

This review assesses whether the E2E safety scenario tests adequately cover the threat model established in Task 1.1.5 (Threat IDs T-01 through T-12) at the **system integration level**, not just unit isolation.

**Key constraint:** The risk engine (`src/risk/`) and orchestrator are not yet implemented (Phase 2). Therefore 23 of 44 tests are skipped. This review evaluates:

- (A) Whether the 21 ACTIVE tests adequately cover what CAN be tested now
- (B) Whether the 23 SKIPPED tests specify adequate safety criteria for Phase 2
- (C) Whether any MISSING scenarios need to be added

The engineer's Copilot transcript confirms 4 test domains: data quality, risk cascade, PDT enforcement, and widowmaker scenarios.

---

## 2. CRO MANDATORY SAFETY ASSERTIONS

The following assertions are **non-negotiable**. Every one must exist as a named test in `test_safety_scenarios.py` with explicit assertions (not just comments or docstrings). If a test requires Phase 2 modules, it must be present as a properly decorated skip with the exact assertion logic written — ready to activate when the dependency arrives.

### Category A: Strategy C Default Enforcement (Capital Preservation)

These tests verify that EVERY failure mode defaults to Strategy C (no new orders).

| ID | Assertion | Expected Status | Param Reference |
|----|-----------|----------------|-----------------|
| CRO-E2E-001 | Missing gameplan file -> GameplanLoader returns Strategy C defaults | ACTIVE | Strategy C rules |
| CRO-E2E-002 | Corrupt/malformed gameplan JSON -> GameplanLoader returns Strategy C | ACTIVE | Strategy C rules |
| CRO-E2E-003 | Gameplan with `quarantine_active: true` -> system refuses to generate signals | ACTIVE or SKIP | Data quality |
| CRO-E2E-004 | Gameplan with `strategy: "C"` -> system enters monitor-only mode, zero orders | ACTIVE or SKIP | Strategy C params |
| CRO-E2E-005 | Risk engine unavailable (None/exception) -> default to NO orders | SKIP (Phase 2) | Rule 2: fail safe |
| CRO-E2E-006 | Broker connection lost mid-session -> no new orders, existing monitored | SKIP (Phase 2) | Protocol B Tier 1 |
| CRO-E2E-007 | Strategy engine raises exception -> no orders, Strategy C implied | SKIP (Phase 2) | Rule 2: fail safe |

### Category B: PDT Compliance (Regulatory Safety)

| ID | Assertion | Expected Status | Param Reference |
|----|-----------|----------------|-----------------|
| CRO-E2E-008 | 3 day trades recorded -> 4th entry BLOCKED | SKIP (needs risk engine) | PDT: 3/5 days |
| CRO-E2E-009 | Closing existing position when PDT exhausted -> ALLOWED | SKIP (needs risk engine) | Entries only |
| CRO-E2E-010 | PDT rolling window respects 5 business days (not calendar) | SKIP (needs risk engine) | Rolling window |
| CRO-E2E-011 | `pdt_trades_remaining: 0` in gameplan -> blocks all entries from startup | ACTIVE or SKIP | Gameplan hard_limits |
| CRO-E2E-012 | PDT count persists across session restart (state file) | SKIP (needs state mgmt) | Rule 10 |

### Category C: Daily Loss Limit Cascade

| ID | Assertion | Expected Status | Param Reference |
|----|-----------|----------------|-----------------|
| CRO-E2E-013 | Cumulative daily loss reaches $60 -> ALL positions force-closed | SKIP (needs risk + broker) | Daily Loss: $60 |
| CRO-E2E-014 | After daily loss halt -> no new orders for remainder of session | SKIP (needs risk engine) | 10% daily cap |
| CRO-E2E-015 | Daily loss at $59.99 -> trading continues normally | SKIP (needs risk engine) | Boundary: below |
| CRO-E2E-016 | Daily loss at $60.01 -> halt triggered (not just at exactly $60) | SKIP (needs risk engine) | Boundary: above |

### Category D: Weekly Drawdown Governor

| ID | Assertion | Expected Status | Param Reference |
|----|-----------|----------------|-----------------|
| CRO-E2E-017 | Weekly loss reaches 15% ($90) -> Strategy C locked for rest of week | SKIP (needs risk + state) | Governor: 15% |
| CRO-E2E-018 | Governor active -> persists across session restarts within same week | SKIP (needs state mgmt) | Persistence |
| CRO-E2E-019 | Governor resets on Monday (week boundary), not mid-week | SKIP (needs state mgmt) | Week boundary |
| CRO-E2E-020 | `weekly_drawdown_governor_active: true` in gameplan -> Strategy C from startup | ACTIVE or SKIP | Gameplan hard_limits |

### Category E: Widowmaker / Gap-Down Scenarios

| ID | Assertion | Expected Status | Param Reference |
|----|-----------|----------------|-----------------|
| CRO-E2E-021 | 50% overnight gap-down -> stop-loss fills at gap price, not stop price | SKIP (needs broker + risk) | Widowmaker |
| CRO-E2E-022 | Gap-down actual loss > calculated max risk -> records ACTUAL loss | SKIP (needs P&L engine) | Honest P&L |
| CRO-E2E-023 | After widowmaker event -> system does NOT re-enter (no panic re-entry) | SKIP (needs orchestrator) | Strategy C |
| CRO-E2E-024 | Gap-down triggers daily loss limit -> cascade to full halt | SKIP (needs risk cascade) | T-11 compound |

### Category F: Compound Safety Triggers (Threat T-11)

| ID | Assertion | Expected Status | Param Reference |
|----|-----------|----------------|-----------------|
| CRO-E2E-025 | Daily loss + PDT exhaustion simultaneously -> both fire, no conflict | SKIP (needs risk engine) | T-11 |
| CRO-E2E-026 | Weekly governor + data quarantine simultaneously -> Strategy C, no deadlock | SKIP (needs risk + data) | T-11 |
| CRO-E2E-027 | All safety mechanisms fire at once -> graceful degradation to cash | SKIP (needs full stack) | Defense in depth |

### Category G: Dry-Run Mode Enforcement (CRITICAL)

| ID | Assertion | Expected Status | Param Reference |
|----|-----------|----------------|-----------------|
| CRO-E2E-028 | `dry_run=True` -> ZERO calls to broker.placeOrder() regardless of signals | SKIP (needs orchestrator) | Core safety |
| CRO-E2E-029 | `dry_run=True` -> all other logic runs normally (signals, risk, P&L) | SKIP (needs orchestrator) | Dry-run fidelity |
| CRO-E2E-030 | No code path bypasses dry-run check before order submission | SKIP (needs orchestrator) | T-08 bypass |

### Category H: Data Quality Cascade

| ID | Assertion | Expected Status | Param Reference |
|----|-----------|----------------|-----------------|
| CRO-E2E-031 | Stale market data (>15 min old) -> Strategy C, data quarantine | ACTIVE or SKIP | Protocol A Step 2 |
| CRO-E2E-032 | VIX data missing/None -> Strategy C default | ACTIVE or SKIP | Data integrity |
| CRO-E2E-033 | Contradictory price data (high < low) -> data quarantine, Strategy C | ACTIVE or SKIP | Data validation |
| CRO-E2E-034 | `data_quality.stale_fields` non-empty in gameplan -> system applies caution | ACTIVE (GameplanLoader) | Gameplan contract |

---

## 3. VERIFICATION INSTRUCTIONS FOR FACTORY FLOOR

### Step 1: Mapping Audit

Run `pytest tests/e2e/test_safety_scenarios.py --collect-only -q` and compare test names against CRO assertion IDs (CRO-E2E-001 through CRO-E2E-034).

For each CRO assertion, identify:
- **COVERED**: An existing test maps to this assertion (provide test name)
- **PARTIAL**: A test exists but doesn't assert exactly what CRO requires (describe gap)
- **MISSING**: No test covers this assertion (must be added)

### Step 2: Gap Remediation

For any MISSING or PARTIAL assertions:
- If the test can run against currently available modules -> implement as ACTIVE test
- If the test requires Phase 2 modules -> implement as SKIP-decorated test with full assertion logic written (not just a docstring placeholder)

### Step 3: Boundary Precision Check

For assertions involving numeric limits (CRO-E2E-015/016, 017), verify tests use EXACT boundary values from Account Parameters:

| Limit | Below (passes) | At (trigger) | Above (must trigger) |
|-------|---------------|--------------|---------------------|
| Daily Loss $60 | $59.99 | $60.00 | $60.01 |
| Weekly Drawdown 15% | 14.99% ($89.94) | 15.00% ($90.00) | 15.01% ($90.06) |
| PDT 3 trades | 2 trades | 3 trades (last allowed) | 4 trades (blocked) |
| Max Position $120 | $119.99 | $120.00 | $120.01 |
| Max Risk $18 | $17.99 | $18.00 | $18.01 |

Note: Boundary tests for position sizing and risk limits may already exist in the 1.1.5 unit test suite. The E2E requirement is that these boundaries are respected through the FULL pipeline (gameplan -> strategy -> risk -> execution), not just isolated risk engine calls.

### Step 4: Skip Decorator Consistency

All Phase 2 skipped tests must use a consistent decorator pattern:
```python
@pytest.mark.skip(reason="Phase 2: requires [specific module] implementation")
```

The `reason` string must identify the specific dependency, not just "Phase 2".

---

## 4. SIGN-OFF CRITERIA

### For Chunk 1 (Current — Partial Sign-Off)

CRO will issue CLEARED on the active (non-skipped) tests when the mapping audit (Step 1) confirms that CRO-E2E-001, 002, 003, 004, 011, 020, 031, 032, 033, and 034 are covered by existing active tests. These are the 10 assertions testable against currently available modules.

**If any of these 10 assertions are MISSING, they must be added before CRO sign-off.**

### For Phase 2 (Future — Full Sign-Off)

CRO full sign-off on `test_safety_scenarios.py` requires:
1. ALL 34 CRO-E2E assertions have corresponding tests (active, not skipped)
2. ALL tests PASS against implemented modules
3. Coverage report for `src/risk/` shows >=98% (matching 1.1.5 target)
4. No `type: ignore` annotations on safety-critical assertions
5. Boundary tests use `Decimal` or tolerance-aware comparisons (Threat T-02)

**This is a Phase 2 gate. No live deployment without full CRO sign-off.**

---

## 5. RISK POSTURE ASSESSMENT

**Current risk level:** LOW (no trading capability exists yet — tests are specifications)

**Phase 2 risk escalation:** When the risk engine and orchestrator are implemented, the skipped tests become the last line of defense before capital deployment. Any gaps in the safety test suite translate directly to unvalidated risk exposure. The 34 CRO assertions above represent the minimum acceptable test surface for risk-critical E2E validation.

**Recommendation:** When Phase 2 implementation begins for `src/risk/`, schedule a dedicated @CRO review session (Opus, extended thinking) to validate that the implemented risk engine satisfies all 34 E2E safety assertions. This is not a routine QA review — it is a capital safety gate.

---

## 6. HANDOFF SUMMARY

| Item | Detail |
|------|--------|
| **Immediate action** | Engineer runs mapping audit (Step 1) against 34 CRO assertions |
| **Chunk 1 gate** | 10 active assertions must map to existing tests |
| **Gap remediation** | Any MISSING assertions added as tests |
| **Phase 2 gate** | All 34 assertions must be active and passing before deployment |
| **Model recommendation** | Sonnet for mapping audit, Opus for any gap remediation |
| **Estimated effort** | 1-2 hours for audit, 2-4 hours if gaps found |

---

**@CRO — End of Review**

*This document is a permanent safety artifact per Rule 24. Reference in all future reviews of risk and safety test infrastructure.*
