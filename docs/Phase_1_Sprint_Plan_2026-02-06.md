# Phase 1 Sprint Plan: Test Suite Build-Out (Tasks 1.1.3 – 1.1.8)

**Date:** 2026-02-06
**Prepared By:** @PM with input from @Systems_Architect, @QA_Lead, @CRO
**Board:** IBKR Project Management
**Status:** APPROVED FOR EXECUTION

---

## Executive Summary

Phase 1.1 (Test Infrastructure) established the foundation: architecture blueprint (1.1.1 ✅), test infrastructure with snapshot capture and runtime validation (1.1.2 ✅, 5 chunks complete). We now execute the **test authoring sprint** — six remaining tasks covering four code layers, end-to-end integration, and live validation.

Tasks 1.1.3 through 1.1.6 are **parallelizable** (they test independent layers). Tasks 1.1.7 and 1.1.8 are **sequential gates** requiring all layer tests to pass first.

**Total Estimated Effort:** 52–74 hours
**Recommended Timeline:** 3 weeks (Feb 10 – Feb 28)
**Constraint:** Solo developer with VSC Copilot, evening/weekend availability assumed

---

## Current State (As of 2026-02-06)

| Task | Status | Progress |
|------|--------|----------|
| 1.1.1 – Test Architecture Design Blueprint | ✅ COMPLETE | 100% |
| 1.1.2 – Test Infrastructure & Snapshot Capture | ✅ COMPLETE | 100% (5/5 chunks) |
| 1.1.3 – Broker Layer Tests | ⬜ NOT STARTED | 0% |
| 1.1.4 – Strategy Layer Tests | ⬜ NOT STARTED | 0% |
| 1.1.5 – Risk Layer Tests | ⬜ NOT STARTED | 0% |
| 1.1.6 – Execution Layer Tests | ⬜ NOT STARTED | 0% |
| 1.1.7 – End-to-End System Tests | ⬜ BLOCKED | 0% |
| 1.1.8 – Live Validation Suite | ⬜ BLOCKED | 0% |

---

## Dependency Map

```
1.1.1 ✅ ──► 1.1.2 ✅ ──┬──► 1.1.3 (Broker)    ──┐
                         ├──► 1.1.4 (Strategy)   ──┤
                         ├──► 1.1.5 (Risk) ★      ──┼──► 1.1.7 (E2E) ──► 1.1.8 (Live)
                         └──► 1.1.6 (Execution)  ──┘
```

**Key:**
- ★ = Requires @CRO review (mandatory gate)
- Tasks 1.1.3–1.1.6 are **independent** and can be worked in any order
- Task 1.1.7 is **blocked** until ALL four layer tests pass
- Task 1.1.8 is **blocked** until 1.1.7 passes AND IBKR Gateway is available on Pi

---

## Recommended Execution Sequence

Although 1.1.3–1.1.6 can theoretically run in parallel, a solo developer should sequence them for maximum efficiency. The recommended order optimizes for:

1. **Foundation first** — Broker layer is the lowest-level dependency
2. **Risk early** — CRO review introduces an external dependency (review cycle time)
3. **Strategy before Execution** — Execution tests depend on understanding strategy signal shapes
4. **Execution last** — Builds on patterns from all prior layers

### Sequenced Order

| Order | Task | Est. Effort | Rationale |
|-------|------|-------------|-----------|
| 1st | **1.1.3 – Broker Layer** | 8–12 hrs | Foundation: all other layers depend on broker mocks established here |
| 2nd | **1.1.5 – Risk Layer** ★ | 10–14 hrs | Start early: @CRO review cycle adds calendar time; 98% coverage target is highest |
| 3rd | **1.1.4 – Strategy Layer** | 10–14 hrs | Depends on understanding broker mock patterns from 1.1.3 |
| 4th | **1.1.6 – Execution Layer** | 8–12 hrs | Depends on strategy signal shapes from 1.1.4 and risk guard patterns from 1.1.5 |
| 5th | **1.1.7 – End-to-End** | 12–16 hrs | Integration: requires all four layers passing |
| 6th | **1.1.8 – Live Validation** | 4–6 hrs | Requires IBKR Gateway on Pi hardware + market hours |

---

## Weekly Milestone Plan

### Week 1: Feb 10–14 (Broker + Risk Kick-off)

**Goal:** Complete Broker Layer tests, begin Risk Layer tests
**CRO Review Submitted:** By end of week

| Day | Focus | Deliverable |
|-----|-------|-------------|
| Mon 2/10 | Blueprint handoff: 1.1.3 Broker Layer | @Systems_Architect delivers VSC Handoff (.md file) |
| Mon–Wed | Factory: Implement 1.1.3 | `test_broker_connection.py`, `test_market_data.py`, `test_gateway_communication.py` |
| Wed 2/12 | QA gate: 1.1.3 review | @QA_Lead validates coverage ≥92%, all acceptance criteria |
| Thu 2/13 | Blueprint handoff: 1.1.5 Risk Layer | @Systems_Architect delivers VSC Handoff (.md file) |
| Thu–Fri | Factory: Begin 1.1.5 | Core position sizing and PDT tests |

**Week 1 Exit Criteria:**
- [ ] 1.1.3 COMPLETE — all broker tests passing, ≥92% coverage
- [ ] 1.1.5 IN PROGRESS — core risk guard tests drafted
- [ ] @CRO review of 1.1.5 test plan submitted

### Week 2: Feb 17–21 (Risk Complete + Strategy + Execution Start)

**Goal:** Complete Risk and Strategy layers, begin Execution
**CRO Review Complete:** By mid-week

| Day | Focus | Deliverable |
|-----|-------|-------------|
| Mon–Tue | Factory: Complete 1.1.5 Risk Layer | `test_position_sizing.py`, `test_risk_guards.py`, `test_circuit_breakers.py` |
| Tue 2/18 | CRO gate: 1.1.5 review | @CRO validates safety guard completeness — MANDATORY |
| Wed 2/19 | Blueprint handoff: 1.1.4 Strategy Layer | @Systems_Architect delivers VSC Handoff (.md file) |
| Wed–Fri | Factory: Implement 1.1.4 | `test_strategy_signals.py`, `test_strategy_selection.py`, `test_strategy_execution.py` |
| Fri 2/21 | Blueprint handoff: 1.1.6 Execution Layer | @Systems_Architect delivers VSC Handoff (.md file) |

**Week 2 Exit Criteria:**
- [ ] 1.1.5 COMPLETE — @CRO signed off, ≥98% coverage
- [ ] 1.1.4 COMPLETE — all strategy tests passing, ≥85% coverage
- [ ] 1.1.6 blueprint delivered, Factory ready to begin

### Week 3: Feb 24–28 (Execution + E2E + Live Validation)

**Goal:** Complete all remaining tests, achieve Phase 1.1 closure

| Day | Focus | Deliverable |
|-----|-------|-------------|
| Mon–Tue | Factory: Complete 1.1.6 Execution Layer | `test_order_creation.py`, `test_order_lifecycle.py`, `test_position_tracking.py` |
| Tue 2/25 | QA gate: 1.1.6 review | @QA_Lead validates coverage ≥90% |
| Wed 2/26 | Blueprint handoff: 1.1.7 E2E | @Systems_Architect delivers VSC Handoff (.md file) |
| Wed–Thu | Factory: Implement 1.1.7 | `test_daily_gameplan_ingestion.py`, `test_full_trade_cycle.py`, `test_safety_scenarios.py` |
| Thu 2/27 | QA gate: 1.1.7 review | @QA_Lead + @DevOps validate E2E completeness |
| Fri 2/28 | Factory: 1.1.8 Live Validation | Requires IBKR Gateway on Pi — market hours required |

**Week 3 Exit Criteria:**
- [ ] 1.1.6 COMPLETE — ≥90% coverage
- [ ] 1.1.7 COMPLETE — E2E tests passing against mock Gateway
- [ ] 1.1.8 COMPLETE — live validation suite passing on Pi hardware
- [ ] **PHASE 1.1 CLOSED** — all 8 tasks complete

---

## Task Detail Reference

### 1.1.3 — Broker Layer Tests (92% coverage target)

**Priority:** Important
**Deliverables:** `tests/unit/test_broker_connection.py`, `tests/unit/test_market_data.py`, `tests/integration/test_gateway_communication.py`

**Critical Test Scenarios (from alpha learnings):**
- Connection establishment with retry logic and exponential backoff
- ClientId rotation (timestamp-based) to avoid conflicts
- `snapshot=True` validation — MUST enforce snapshot mode (alpha buffer overflow fix)
- Historical data: 1-hour RTH-only windows with proper timeout propagation
- Contract qualification flow before data requests
- Proper cleanup on disconnect

**Blueprint Note:** This task's blueprint must encode the alpha learnings as test assertions — specifically, any test that creates a market data request MUST assert `snapshot=True`.

---

### 1.1.5 — Risk Layer Tests (98% coverage target) ★ CRO MANDATORY

**Priority:** Urgent
**Deliverables:** `tests/unit/test_position_sizing.py`, `tests/unit/test_risk_guards.py`, `tests/integration/test_circuit_breakers.py`

**Critical Test Scenarios:**
- Max position size: $120 (20% of $600)
- Per-trade risk: $18 (3% of $600)
- PDT compliance: 3 trades / 5 rolling business days
- Daily loss limit: $60 (10%) triggers full halt
- Weekly drawdown governor: 15% triggers Strategy C lock for remainder of week
- Force-close at 3 DTE (never hold to expiry)
- Gap-down scenario: stop-loss gaps through, max loss calculation
- Strategy C auto-deployment on ANY safety violation

**@CRO Review Requirements:**
1. Every risk limit tested at exact boundary (e.g., $59.99 vs $60.00 vs $60.01)
2. No code path exists that bypasses safety guards
3. Concurrent trade scenarios don't exceed aggregate limits
4. PDT rolling window edge cases (trades spanning weekends, holidays)

---

### 1.1.4 — Strategy Layer Tests (85% coverage target)

**Priority:** Important
**Deliverables:** `tests/unit/test_strategy_signals.py`, `tests/unit/test_strategy_selection.py`, `tests/integration/test_strategy_execution.py`

**Critical Test Scenarios:**
- VIX regime boundaries: <15, 15–18, 18–25, 25–30, >30
- Strategy A signals: EMA(8/21) crossover + RSI 50–65 + Price > VWAP
- Strategy B signals: RSI <30 or >70 + Bollinger 2σ touch
- Strategy C: triggered by VIX >25, data quarantine, drawdown governor, or default
- Missing/stale data graceful degradation (never crash, default to Strategy C)
- Catalyst overrides: FOMC, CPI, earnings → position size reduction or Strategy C

---

### 1.1.6 — Execution Layer Tests (90% coverage target)

**Priority:** Important
**Deliverables:** `tests/unit/test_order_creation.py`, `tests/unit/test_order_lifecycle.py`, `tests/integration/test_position_tracking.py`

**Critical Test Scenarios:**
- Order parameter construction from strategy signals
- Dry-run mode NEVER submits orders (critical safety assertion)
- Order lifecycle: submitted → filled → closed
- P&L calculation: realized + unrealized
- Take-profit, stop-loss, and time-stop exit paths
- Partial fills and cancellation handling

---

### 1.1.7 — End-to-End System Tests

**Priority:** Important
**Deliverables:** `tests/e2e/test_daily_gameplan_ingestion.py`, `tests/e2e/test_full_trade_cycle.py`, `tests/e2e/test_safety_scenarios.py`

**Critical Test Scenarios:**
- Full workflow: gameplan JSON → signal → order → execution → tracking → closure
- Strategy C default on missing/malformed gameplan
- Multi-symbol sessions (SPY + QQQ)
- Strategy transitions: A → C on VIX spike, A → B on regime change
- PDT enforcement across multi-day simulation
- Weekly drawdown governor activation and week-long lock

---

### 1.1.8 — Live Validation Suite (Manual, Not CI/CD)

**Priority:** Medium
**Deliverables:** `tests/live_validation/` suite + `docs/deployment_validation_checklist.md`

**Prerequisites:**
- IBKR Gateway running on Pi (localhost:4002)
- Market hours (9:30 AM – 4:00 PM ET) for live data tests
- Paper trading account active

**Tests:**
- Gateway connectivity verification
- Real market data snapshot retrieval (SPY, QQQ, IWM)
- Historical data request (1-hour RTH bars)
- Paper trading order submission and status tracking
- Deployment validation checklist creation

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| IBKR Gateway not available on Pi for 1.1.8 | Blocks Phase 1 closure | Begin Pi Gateway setup in parallel (Week 2) — @DevOps to prepare |
| @CRO review cycle delays 1.1.5 | Pushes Week 2 timeline | Submit test plan for review at end of Week 1, not after completion |
| Test infrastructure gaps discovered | Rework in 1.1.3–1.1.6 | 1.1.2's 5-chunk foundation was thorough; low probability |
| Context window degradation | Quality drops in later sessions | Follow Rule 17: new chat per task, handoff summaries between sessions |
| Copilot agent drift from blueprint | Tests don't match spec | Follow Rule 16: blueprints as downloadable files, not inline chat |

---

## Process Rules for This Sprint

1. **One task per chat session.** Each 1.1.x task gets its own fresh chat. Handoff summary at session close.
2. **Blueprint before Factory.** @Systems_Architect delivers the VSC Handoff as a .md file BEFORE the operator opens VSCode.
3. **Board updates are agentic.** @PM updates the Planner board directly — never asks the operator to do it.
4. **QA gates are mandatory.** No task marked complete without @QA_Lead (or @CRO for 1.1.5) sign-off.
5. **Extended thinking recommended for:** Blueprint creation, CRO risk review, E2E test design (1.1.7).
6. **Extended thinking not needed for:** Task status updates, board management, routine QA checklists.

---

## Board Update Actions (Post-Approval)

Upon operator approval of this plan, @PM will:
1. Set due dates on all six tasks per the weekly milestone schedule
2. Update task descriptions with sequencing notes
3. Unblock 1.1.3 (first in sequence)
4. Create any missing checklist items

---

*Document Version: 1.0*
*Prepared By: @PM, Charter & Stone Capital Workshop*
*Review Required By: Human Operator*
*Next Action: Operator approval → @PM executes board updates → @Systems_Architect begins 1.1.3 blueprint*
