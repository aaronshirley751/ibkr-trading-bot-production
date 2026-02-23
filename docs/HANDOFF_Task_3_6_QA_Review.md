# VSC HANDOFF: QA Review — Automation Reliability [x86_64]

## Header Block

| Field | Value |
|-------|-------|
| **Task ID** | 3.6 (um43GF5PNUSl_R_9R4AoJmUAMsnb) |
| **Date** | 2026-02-10 |
| **Revision** | 1.0 |
| **Requested By** | Task 3.5 Completion / Phase 3 Sprint |
| **Lead Persona** | @QA_Lead |
| **Supporting Personas** | @CRO (safety validation), @DevOps (deployment testing) |
| **Model Routing** | **Sonnet** (structured review process) |
| **Context Budget** | Moderate (~5K input + 3K output) |
| **Board** | IBKR Project Management |
| **Priority** | Important (gates Phase 3 completion) |

---

## Context Summary

**Phase 3 Status:**
- ✅ Task 3.1 — IBC Controller config (Docker)
- ✅ Task 3.2 — Gateway startup orchestration
- ✅ Task 3.3 — Health check monitoring
- ✅ Task 3.4 — Docker Compose orchestration
- ✅ Task 3.5 — Zero-touch startup sequence
- ⬜ **Task 3.6 — QA Review** ← **THIS TASK**

**Task 3.5 Implementation Summary:**
- **Deliverables:** Complete orchestration module with 92 new tests
- **Test Results:** 619 passing, 108 skipped, 0 failures
- **Quality Gates:** ruff, black, mypy all passing
- **Status:** Implementation complete, pending QA validation

**Critical Questions:**
1. Why are 108 tests skipped? (Are these legitimate or hidden failures?)
2. Why is test count 727 instead of expected 730? (Missing 3 tests)
3. Do the 92 new tests actually cover the 17 blueprint edge cases?
4. Does the orchestrator actually work in practice (not just in tests)?

---

# AGENT EXECUTION BLOCK

---

## 1. Objective

Validate the **zero-touch startup orchestrator** (Task 3.5 deliverable) for production readiness through comprehensive QA review. This review:

1. **Investigates test anomalies** (108 skipped tests, 3-test discrepancy)
2. **Validates test coverage** against blueprint edge cases
3. **Performs manual validation** (dry-run orchestrator execution)
4. **Assesses production readiness** (deployment script, configuration, monitoring)
5. **Secures @CRO sign-off** on failure modes and capital safety
6. **Gates Phase 3 completion** — cannot proceed to Phase 4 without QA approval

**Success Criteria:** Task 3.6 is COMPLETE when:
- All test anomalies explained and resolved
- Manual orchestrator run succeeds
- All 17 blueprint edge cases validated
- @CRO approves failure mode safety
- Phase 3 ready for formal completion signoff

---

## 2. QA Review Process

### Phase 1: Test Integrity Investigation (CRITICAL)

**Objective:** Account for all test discrepancies and validate test suite health.

#### 2.1 Investigate 108 Skipped Tests

**Procedure:**

```bash
# Step 1: List all skipped tests
poetry run pytest --collect-only -q | grep "SKIPPED"

# Step 2: Get detailed skip reasons
poetry run pytest -v --tb=no -ra | grep -A 1 "SKIPPED"

# Step 3: Categorize skips
#   - Expected skips (e.g., `@pytest.mark.skip("Requires live IBKR connection")`)
#   - Temporary skips (e.g., `@pytest.mark.skip("WIP")`)
#   - Suspicious skips (e.g., no clear reason, or "broken")
```

**Expected Categories:**

| Skip Reason | Acceptable? | Action Required |
|-------------|------------|-----------------|
| Live IBKR connection required | ✅ Yes | Document as expected (paper trading tests) |
| Hardware-specific (e.g., Pi tests) | ✅ Yes | Document as obsolete (Pi retired) |
| Integration requires external service | ✅ Yes | Document as expected |
| "WIP" or "TODO" or "broken" | ❌ No | Either fix or remove |
| No reason given | ❌ No | Investigate and categorize |

**Deliverable:** Skipped tests inventory document:

```markdown
# Skipped Tests Inventory — Task 3.6 QA Review

## Summary
- Total skipped: 108
- Acceptable: [count]
- Requires remediation: [count]

## Acceptable Skips
### Live IBKR Connection Tests ([count] tests)
- [test_name] — [reason]
...

### Obsolete Pi-Specific Tests ([count] tests)
- [test_name] — [reason]
...

## Requires Remediation
### Broken Tests ([count] tests)
- [test_name] — [issue] — [remediation plan]
...
```

#### 2.2 Reconcile Test Count Discrepancy

**Baseline Expectation:**
- Phase 2 baseline: 638 tests
- Task 3.5 new tests: 92
- Expected total: 730
- Actual total: 619 passing + 108 skipped = 727

**Discrepancy:** -3 tests

**Investigation Steps:**

```bash
# Step 1: Compare test file list (Phase 2 vs. current)
# Identify any test files deleted or renamed

# Step 2: Check git log for test removals
git log --oneline --since="2026-02-09" -- tests/

# Step 3: Search for test consolidation
# Look for commits that merged duplicate tests
```

**Possible Explanations:**
1. Duplicate tests consolidated (acceptable if documented)
2. Obsolete tests removed (acceptable if documented)
3. Tests accidentally deleted (requires restoration)

**Deliverable:** Test count reconciliation report (include in final QA summary).

---

### Phase 2: Coverage Validation Against Blueprint

**Objective:** Verify that the 92 new tests actually cover the 17 edge cases specified in the Task 3.5 blueprint.

#### 2.3 Edge Case Coverage Checklist

**Blueprint Edge Cases (from HANDOFF_Task_3_5_Zero_Touch_Startup.md, Section 15):**

**Gateway Failure Scenarios:**
- [ ] 15.1.1: Gateway container doesn't exist → Orchestrator creates it
- [ ] 15.1.2: Gateway container exists but stopped → Orchestrator starts it
- [ ] 15.1.3: Gateway starts but never becomes healthy → Restart then FAILURE
- [ ] 15.1.5: Docker daemon not running → FAILURE with clear error

**Gameplan Scenarios:**
- [ ] 15.2.6: Gameplan file missing → Strategy C deployed
- [ ] 15.2.7: Gameplan schema invalid → Strategy C deployed
- [ ] 15.2.8: Gameplan has data_quarantine=true → Strategy C enforced
- [ ] 15.2.9: Gameplan path not configured → Strategy C deployed

**Bot Startup Scenarios:**
- [ ] 15.3.10: Bot crashes immediately on startup → FAILURE with stderr
- [ ] 15.3.11: Bot already running → FAILURE (duplicate prevention)

**Notification Scenarios:**
- [ ] 15.4.12: Discord webhook not configured → Graceful degradation
- [ ] 15.4.13: Discord webhook times out → Orchestrator proceeds

**Idempotency Scenarios:**
- [ ] 15.5.14: Run orchestrator twice → Second run detects bot running
- [ ] 15.5.15: Gateway and bot both already running → Graceful handling

**Race Conditions:**
- [ ] 15.6.16: Gateway becomes healthy exactly at timeout → Success
- [ ] 15.6.17: Gateway crashes during wait loop → Restart attempted

**Validation Procedure:**

```bash
# For each edge case, search for corresponding test:
grep -r "test_gateway_container_doesnt_exist" tests/orchestration/
grep -r "test_gameplan_missing" tests/orchestration/
# ... etc for all 17 edge cases

# Verify test actually exercises the scenario (not just mocked)
# Read test implementation to confirm behavior matches blueprint
```

**Deliverable:** Edge case coverage matrix (include in final QA summary).

---

### Phase 3: Manual Validation (DRY-RUN MODE)

**Objective:** Execute the orchestrator in a controlled environment to verify it actually works.

**CRITICAL SAFETY NOTE:** Do NOT run orchestrator with live Gateway credentials. Use dry-run mode or paper trading configuration only.

#### 2.4 Local Orchestrator Execution

**Pre-requisites:**
```bash
# 1. Ensure Docker Desktop running
docker ps

# 2. Ensure Gateway container NOT running (we'll let orchestrator start it)
docker compose -f docker/gateway/docker-compose.yml down

# 3. Create test gameplan (valid)
mkdir -p state/
cat > state/test_gameplan.json << 'EOF'
{
  "date": "2026-02-10",
  "session_id": "qa_test_001",
  "strategy": "C",
  "regime": "normal",
  "data_quality": {"quarantine_active": false}
}
EOF

# 4. Set environment variables
export GAMEPLAN_PATH="state/test_gameplan.json"
export DISCORD_WEBHOOK_URL=""  # Test graceful degradation
export GATEWAY_HOST="localhost"
export GATEWAY_PORT="4002"
```

**Test Scenarios:**

**Scenario 1: Happy Path (Gateway starts, bot starts)**
```bash
# Run orchestrator
poetry run python -m src.orchestration.startup

# Expected behavior:
# 1. Gateway container starts
# 2. Orchestrator waits for health (up to 120s)
# 3. Gameplan loaded
# 4. Bot starts
# 5. Orchestrator exits with code 0

# Verify:
docker ps | grep ibkr-gateway  # Should be running
# Bot process should be running (check logs)
```

**Scenario 2: Missing Gameplan (Strategy C fallback)**
```bash
# Remove gameplan
rm state/test_gameplan.json

# Run orchestrator
poetry run python -m src.orchestration.startup

# Expected behavior:
# 1. Orchestrator detects missing gameplan
# 2. Strategy C gameplan generated
# 3. Bot starts with Strategy C
# 4. Orchestrator exits with code 0

# Verify:
ls state/emergency_gameplan.json  # Should exist
cat state/emergency_gameplan.json | jq '.strategy'  # Should be "C"
```

**Scenario 3: Docker Not Running (FAILURE)**
```bash
# Stop Docker Desktop
# (or mock this if you don't want to stop Docker)

# Run orchestrator
poetry run python -m src.orchestration.startup

# Expected behavior:
# 1. Orchestrator detects Docker unavailable
# 2. FAILURE with clear error message
# 3. Exit code 1

# Verify logs show: "Docker not available"
```

**Scenario 4: Production Wrapper Script**
```bash
# Test the production startup script
chmod +x docker/gateway/scripts/production-startup.sh
./docker/gateway/scripts/production-startup.sh

# Expected behavior:
# 1. Script runs orchestrator
# 2. Logs to logs/startup_YYYYMMDD_HHMMSS.log
# 3. Exit code matches orchestrator exit code

# Verify:
ls logs/  # Should contain startup log
tail -20 logs/startup_*.log  # Should show orchestrator output
```

**Deliverable:** Manual testing report with screenshot/log evidence for each scenario.

---

### Phase 4: Production Readiness Assessment

**Objective:** Validate deployment configuration and operational requirements.

#### 2.5 Configuration Review

**Checklist:**

- [ ] `.env.example` documents all required environment variables
- [ ] Default values in `OrchestrationConfig` work for development
- [ ] Production values documented for desktop deployment
- [ ] Future rackmount migration path clear (no hardcoded Windows paths)
- [ ] Discord webhook optional (graceful degradation tested)
- [ ] Gameplan path configurable (not hardcoded)
- [ ] Timeout values reasonable (120s Gateway health timeout)

#### 2.6 Error Handling Review

**Checklist:**

- [ ] All subprocess calls have timeout protection
- [ ] All exceptions caught and logged
- [ ] Exit codes documented (0=success, 1=failure)
- [ ] Error messages are actionable (tell operator what to do)
- [ ] No silent failures (every failure path logs + alerts)

#### 2.7 Logging and Observability

**Checklist:**

- [ ] Structured logging (timestamps, levels, context)
- [ ] Log file rotation configured (or documented as future work)
- [ ] Discord alerts at key decision points
- [ ] Alert severity levels appropriate (info/warning/error/critical)
- [ ] Logs contain enough detail for debugging but not sensitive data

#### 2.8 Deployment Documentation

**Checklist:**

- [ ] README.md updated with orchestrator usage
- [ ] Production deployment instructions clear
- [ ] Environment variable setup documented
- [ ] Troubleshooting guide for common failures
- [ ] Rollback procedure documented

---

### Phase 5: CRO Safety Sign-off

**Objective:** Secure final @CRO approval on failure modes and capital safety.

#### 2.9 CRO Review Checklist

**@CRO to validate:**

- [ ] **Strategy C fallback:** Emergency gameplan generator produces valid Strategy C
  - Verify: `strategy: "C"`, `symbols: []`, `max_daily_loss_pct: 0.0`
  - Test: Manually inspect generated `emergency_gameplan.json`

- [ ] **Bounded retry logic:** Gateway restart attempted exactly once (no infinite loops)
  - Verify: `gateway_restart_attempted` flag prevents multiple restarts
  - Test: Check test coverage for this scenario

- [ ] **Timeout enforcement:** Gateway health timeout is 120s (not infinite)
  - Verify: `gateway_health_timeout` config value
  - Test: Confirm timeout actually triggers (not bypassed)

- [ ] **Bot crash detection:** Orchestrator detects bot startup failure within 5s
  - Verify: 5-second sleep + poll check in `_start_bot`
  - Test: Confirm test covers this scenario

- [ ] **Idempotency:** Running orchestrator twice doesn't start duplicate bot
  - Verify: `_bot_already_running` check uses process list
  - Test: Manual test of double-run scenario

- [ ] **No silent capital risk:** All failure paths either deploy Strategy C or exit FAILURE
  - Verify: No path leads to trading with invalid configuration
  - Review: State machine diagram has no "undefined" transitions

**CRO Sign-off:** After validation, @CRO must explicitly approve or request remediation.

---

## 3. Definition of Done

**Task 3.6 is COMPLETE when all of the following are TRUE:**

### 3.1 Test Integrity
- [ ] All 108 skipped tests categorized (acceptable vs. requires remediation)
- [ ] All unacceptable skips either fixed or removed
- [ ] Test count discrepancy (-3 tests) explained and documented
- [ ] Test suite health confirmed (no hidden failures)

### 3.2 Coverage Validation
- [ ] All 17 blueprint edge cases have corresponding tests
- [ ] Edge case coverage matrix completed
- [ ] Any gaps in coverage documented and tracked

### 3.3 Manual Validation
- [ ] Orchestrator dry-run (happy path) succeeds
- [ ] Strategy C fallback tested and verified
- [ ] Docker unavailable failure tested
- [ ] Production wrapper script tested
- [ ] Manual testing report completed

### 3.4 Production Readiness
- [ ] Configuration review checklist complete
- [ ] Error handling review checklist complete
- [ ] Logging and observability checklist complete
- [ ] Deployment documentation checklist complete

### 3.5 CRO Sign-off
- [ ] All CRO safety checklist items verified
- [ ] @CRO provides explicit approval or documents required remediation

### 3.6 Final Deliverables
- [ ] QA Review Summary Report (markdown file)
- [ ] Skipped Tests Inventory
- [ ] Edge Case Coverage Matrix
- [ ] Manual Testing Report
- [ ] CRO Safety Sign-off (inline in QA summary)

---

## 4. QA Review Summary Report Template

**Create this file as final deliverable:**

```markdown
# Task 3.6 QA Review — Automation Reliability

**Date:** 2026-02-10
**Reviewer:** @QA_Lead
**Task:** Task 3.5 Zero-Touch Startup Orchestrator
**Status:** [APPROVED / CONDITIONAL APPROVAL / REJECTED]

---

## Executive Summary

[1-2 paragraph summary of findings]

---

## Test Integrity Investigation

### Skipped Tests Analysis
- **Total Skipped:** 108
- **Acceptable:** [count] ([breakdown])
- **Remediated:** [count] ([details])
- **Outstanding:** [count] ([tracked as separate tasks])

### Test Count Reconciliation
- **Baseline (Phase 2):** 638
- **New Tests (Task 3.5):** 92
- **Expected Total:** 730
- **Actual Total:** 727
- **Discrepancy:** -3 tests
- **Explanation:** [details]

---

## Edge Case Coverage Validation

**Coverage:** [X/17 edge cases validated]

[Insert edge case coverage matrix here]

**Gaps:** [List any gaps and remediation plan]

---

## Manual Validation Results

### Test Scenario Results
| Scenario | Expected Behavior | Actual Behavior | Status |
|----------|-------------------|-----------------|--------|
| Happy path | Gateway + bot start | [observed] | ✅ / ❌ |
| Missing gameplan | Strategy C deployed | [observed] | ✅ / ❌ |
| Docker unavailable | FAILURE | [observed] | ✅ / ❌ |
| Production script | Orchestrator runs | [observed] | ✅ / ❌ |

[Attach logs or screenshots as evidence]

---

## Production Readiness Assessment

### Configuration Review
[Summarize findings from checklist 2.5]

### Error Handling
[Summarize findings from checklist 2.6]

### Logging & Observability
[Summarize findings from checklist 2.7]

### Documentation
[Summarize findings from checklist 2.8]

---

## CRO Safety Sign-off

**@CRO Assessment:**

[CRO reviews failure modes and provides verdict]

**CRO Verdict:** [APPROVED / CONDITIONAL APPROVAL / REJECTED]

**Conditions (if any):** [List required remediations]

---

## Recommendations

### Phase 3 Completion
- [ ] Task 3.6 complete — Phase 3 APPROVED for completion
- [ ] Outstanding issues tracked as Phase 4 tech debt
- [ ] Proceed to Phase 4 planning

### Required Remediations (if any)
[List blocking issues that must be resolved]

### Optional Improvements (non-blocking)
[List nice-to-haves for future enhancement]

---

## Conclusion

[Final verdict and next steps]

**Signed:**
@QA_Lead — [Date]
@CRO — [Date] (if approved)
```

---

## 5. Rollback Plan

**If QA review fails (critical issues found):**

1. **Document failures:** Create detailed issue reports for each blocker
2. **Create remediation tasks:** Add to IBKR Project Management board
3. **Revert if necessary:** If orchestrator is fundamentally broken, revert Task 3.5 commits
4. **Re-plan:** Determine if Task 3.5 needs redesign or just fixes
5. **Re-test:** After remediation, re-run Task 3.6 QA review

**If QA review passes with minor issues:**

1. **Track as tech debt:** Create follow-up tasks for non-blocking improvements
2. **Approve Phase 3 completion:** Minor issues don't block Phase 4
3. **Schedule fixes:** Address tech debt in parallel with Phase 4 work

---

## 6. Success Criteria Summary

**Task 3.6 is COMPLETE and Phase 3 is APPROVED when:**

✅ Test integrity confirmed (skips categorized, count reconciled)
✅ Edge case coverage validated (17/17 or gaps documented)
✅ Manual orchestrator run succeeds (dry-run mode)
✅ Production readiness verified (config, errors, logging, docs)
✅ @CRO approves failure modes and capital safety
✅ QA Review Summary Report delivered

**This completes Phase 3. Proceed to Phase 4 planning.**
