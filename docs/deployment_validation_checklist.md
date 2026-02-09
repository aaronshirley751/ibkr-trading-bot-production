# Deployment Validation Checklist — Task 1.1.8

**Validation Date:** ________________
**Operator:** ________________
**IBKR Gateway Version:** ________________
**Paper Account ID:** ________________

---

## PURPOSE

This checklist validates the trading bot's integration with IBKR Gateway under real market conditions using a paper trading account. This is the **final Phase 1 gate** before transitioning to Phase 2 (source code implementation).

**Success Criteria:** All validation scenarios pass with paper trading account. Bot demonstrates stable operation for a minimum 2-hour market hours session with zero critical failures.

---

## SECTION 1: PRE-VALIDATION SETUP

### 1.1 Gateway Accessibility
- [ ] IBKR Gateway installed and running
- [ ] Gateway accessible at `127.0.0.1:4002`
- [ ] Gateway version is 995.2+ (recommended)
- [ ] Gateway API enabled in settings
- [ ] Gateway auto-restart disabled (manual control for validation)
- [ ] Gateway logs location verified: `~/ibkr_gateway/logs/ibgateway.log`

**Notes:** _______________________________________________

### 1.2 Paper Trading Account
- [ ] Paper trading credentials confirmed (not live account)
- [ ] Account type verified as "PAPER" in TWS
- [ ] Account balance ≥ $100,000 (virtual capital)
- [ ] No existing positions from prior testing (or documented below)
- [ ] Order history cleared or known state documented

**Existing Positions (if any):** _______________________________________________

### 1.3 Network & Infrastructure
- [ ] Internet connection stable (ping test to IBKR servers < 50ms)
- [ ] System clock synchronized via NTP
- [ ] No firewall blocking ports 4002 (paper trading)
- [ ] Pi/system hardware resources available (CPU < 50%, RAM < 70%)

**Ping Test Results:** _______________________________________________

### 1.4 Configuration Files
- [ ] `config/live_validation_config.yaml` present and valid
- [ ] Paper trading port (4002) confirmed in config
- [ ] Test contract expiry date updated (weekly options: next Friday)
- [ ] Timeout values appropriate for live environment (30s+)

**Config File Last Updated:** _______________________________________________

### 1.5 Market Hours Confirmation
- [ ] Current time is within market hours (9:30 AM - 4:00 PM ET)
- [ ] No major market events scheduled (FOMC, earnings, etc.)
- [ ] VIX < 30 (normal volatility for testing)
- [ ] Market is open (not early close or holiday)

**Market Conditions:** _______________________________________________

### 1.6 Python Environment
- [ ] Poetry environment activated
- [ ] All dependencies installed (`poetry install --with dev`)
- [ ] Pytest installed and accessible
- [ ] No import errors when running `pytest --collect-only`

**Python Version:** _______________________________________________

---

## SECTION 2: AUTOMATED TEST EXECUTION

### 2.1 Broker Connectivity Tests
Execute: `pytest tests/live_validation/test_live_broker_connectivity.py -v`

- [ ] `test_gateway_authentication` — PASS
- [ ] `test_account_info_retrieval` — PASS
- [ ] `test_account_balance_retrieval` — PASS
- [ ] `test_position_retrieval_empty_account` — PASS
- [ ] `test_gateway_reconnection_resilience` — PASS
- [ ] `test_gateway_connection_stability` — PASS

**Notes:** _______________________________________________

### 2.2 Market Data Tests
Execute: `pytest tests/live_validation/test_live_market_data.py -v`

- [ ] `test_market_data_subscription_spy` — PASS
- [ ] `test_historical_data_retrieval_spy` — PASS
- [ ] `test_market_data_multiple_symbols` — PASS
- [ ] `test_market_data_stream_quality` — PASS (or acceptable failure rate documented)
- [ ] `test_market_data_quote_freshness_validation` — PASS
- [ ] `test_option_contract_qualification` — PASS

**Notes:** _______________________________________________

### 2.3 Order Execution Tests
Execute: `pytest tests/live_validation/test_live_order_execution.py -v`

- [ ] `test_paper_trading_limit_order_submission` — PASS
- [ ] `test_paper_trading_position_tracking` — PASS
- [ ] `test_paper_trading_order_cancellation` — PASS
- [ ] `test_paper_trading_close_position` — PASS
- [ ] `test_paper_trading_multiple_orders` — PASS

**Notes:** _______________________________________________

### 2.4 Resilience Tests
Execute: `pytest tests/live_validation/test_live_resilience.py -v`

- [ ] `test_network_timeout_handling` — PASS
- [ ] `test_api_rate_limit_handling` — PASS
- [ ] `test_market_data_staleness_detection` — PASS
- [ ] `test_gateway_error_recovery` — PASS
- [ ] `test_concurrent_request_handling` — PASS
- [ ] `test_extended_session_stability` — PASS
- [ ] `test_invalid_order_rejection` — PASS

**Notes:** _______________________________________________

### 2.5 Full Suite Execution
Execute: `pytest tests/live_validation/ -v`

- [ ] All tests executed successfully
- [ ] Zero critical failures
- [ ] Total execution time: _______ minutes
- [ ] Pass rate: _______% (target: 100%)

**Summary:** _______________________________________________

---

## SECTION 3: MANUAL VALIDATION STEPS

### 3.1 TWS Position Verification
- [ ] Open TWS on desktop
- [ ] Navigate to Portfolio → Positions
- [ ] Verify positions match test execution (if any)
- [ ] Manually close any open test positions
- [ ] Confirm paper account is flat (no open positions)

**Final Positions:** _______________________________________________

### 3.2 TWS Order History Review
- [ ] Navigate to TWS → Trade Log
- [ ] Verify test orders are visible
- [ ] Confirm all test orders are either Filled or Cancelled (no Pending)
- [ ] Verify order timestamps match test execution
- [ ] No unexpected orders present

**Order Count:** _______________________________________________

### 3.3 Gateway Logs Review
Execute: `tail -n 100 ~/ibkr_gateway/logs/ibgateway.log`

- [ ] Review last 100 log lines
- [ ] Look for errors, warnings, or disconnection events
- [ ] Document any anomalies

**Log Anomalies:** _______________________________________________

### 3.4 Performance Metrics
- [ ] Average order fill time: _______ seconds (target: < 30s)
- [ ] Average quote freshness: _______ seconds (target: < 5s)
- [ ] Gateway uptime during test session: _______% (target: 100%)
- [ ] Connection latency: _______ ms (target: < 100ms)

**Performance Summary:** _______________________________________________

---

## SECTION 4: POST-VALIDATION CLEANUP

### 4.1 Close All Test Positions
Execute: `python scripts/close_all_positions.py --paper-trading`

- [ ] Script execution successful
- [ ] All positions closed
- [ ] Paper account balance verified

**Final Account Balance:** _______________________________________________

### 4.2 Archive Test Logs
```bash
mkdir -p logs/live_validation/$(date +%Y%m%d)
cp pytest_report.txt logs/live_validation/$(date +%Y%m%d)/
cp ~/ibkr_gateway/logs/ibgateway.log logs/live_validation/$(date +%Y%m%d)/
```

- [ ] Logs archived successfully
- [ ] Archive location: `logs/live_validation/________`

### 4.3 Update Project Board
- [ ] Mark Task 1.1.8 complete on IBKR Project Management board
- [ ] Add validation results summary in comments
- [ ] Upload archived logs as attachments
- [ ] Tag @QA_Lead and @CRO for review

**Board Updated:** _______________________________________________

### 4.4 Gateway Shutdown (Optional)
- [ ] If not proceeding to bot testing immediately
- [ ] Execute: `pkill -f "ibgateway"`
- [ ] Verify Gateway process terminated

**Gateway Shutdown:** _______________________________________________

---

## SECTION 5: VALIDATION SIGN-OFF

### 5.1 Test Results Summary

| Test Category | Tests Run | Pass | Fail | Pass Rate |
|--------------|-----------|------|------|-----------|
| Broker Connectivity | __ | __ | __ | __% |
| Market Data | __ | __ | __ | __% |
| Order Execution | __ | __ | __ | __% |
| Resilience | __ | __ | __ | __% |
| **TOTAL** | __ | __ | __ | __% |

**Target:** 100% pass rate (zero critical failures)

### 5.2 Known Issues / Exceptions

| Issue | Severity | Acceptance Rationale |
|-------|----------|---------------------|
| (example: Quote stream quality 90% instead of 100%) | Low | Acceptable for Phase 1: normal market volatility |
|  |  |  |
|  |  |  |

### 5.3 Validation Decision

- [ ] **PASS** — All criteria met, proceed to Phase 2
- [ ] **PASS WITH EXCEPTIONS** — Minor issues documented, proceed with caveats
- [ ] **FAIL** — Critical issues found, do NOT proceed to Phase 2

**Decision Rationale:** _______________________________________________

### 5.4 Approvals

**QA Lead Approval:**
Signature: ________________ Date: ________________

**CRO Approval (Safety Sign-Off):**
Signature: ________________ Date: ________________

**PM Authorization (Phase 2 Kickoff):**
Signature: ________________ Date: ________________

---

## SECTION 6: KNOWN LIMITATIONS (ACCEPTABLE FOR PHASE 1)

### 6.1 Paper Trading vs. Live Trading Differences
- [ ] Instant fills (no slippage modeling) — ACCEPTED
- [ ] No assignment risk on short options — ACCEPTED
- [ ] Unlimited buying power (no margin calls) — ACCEPTED
- [ ] No bid-ask spread impact (always fills at limit price) — ACCEPTED

**These differences are acceptable for Phase 1 validation. Phase 4 (live trading) will require additional validation with real capital at risk.**

### 6.2 Validation Scope Limitations
- [ ] Single-day validation (not multi-week endurance) — ACCEPTED
- [ ] Normal market conditions only (not stress-tested) — ACCEPTED
- [ ] Single symbol focus (SPY primarily) — ACCEPTED
- [ ] No extended hours testing — ACCEPTED

---

## SECTION 7: ROLLBACK PLAN (IF VALIDATION FAILS)

### 7.1 Failure Severity Assessment

**Critical Failure (> 20% test failures):**
- Action: Do NOT proceed to Phase 2
- Timeline: Investigate root cause, fix issues, re-run validation
- Decision: Phase 2 start date deferred until validation passes

**Gateway Instability (Frequent Disconnections):**
- Action: Investigate Gateway configuration, network stability, or Pi hardware
- Timeline: Resolve within 1 week or escalate to architectural decision
- Alternative: Consider Desktop Gateway with IBC Controller

**Paper vs. Live Discrepancies:**
- Action: Document discrepancies, adjust risk parameters for live trading
- Timeline: Document findings, proceed to Phase 2 with noted caveats

### 7.2 Remediation Procedure

If validation uncovers critical issues:

1. Tag current state: `git tag phase1-validation-blocked-YYYYMMDD`
2. Create hotfix branch: `git checkout -b hotfix/live-validation-fixes`
3. Implement fixes, re-run automated tests (Tasks 1.1.1–1.1.7)
4. Re-run live validation (Task 1.1.8)
5. Merge hotfix to main: `git merge hotfix/live-validation-fixes`
6. Tag validated state: `git tag phase1-validation-passed-YYYYMMDD`

---

## APPENDIX A: VALIDATION ENVIRONMENT DETAILS

**System Information:**
- OS: _______________________________________________
- Python Version: _______________________________________________
- Poetry Version: _______________________________________________
- IBKR Gateway Version: _______________________________________________
- Network: _______________________________________________

**Test Configuration:**
- Config File: `config/live_validation_config.yaml`
- Test Suite: `tests/live_validation/`
- Log Output: `logs/live_validation/`

**Contact Information:**
- Operator: _______________________________________________
- Technical Support: _______________________________________________
- Escalation Contact: _______________________________________________

---

*End of Deployment Validation Checklist*

**Instructions:**
1. Complete all checklist items sequentially during validation session
2. Document any deviations or anomalies in Notes sections
3. Obtain all required approvals before proceeding to Phase 2
4. Archive completed checklist with validation logs for audit trail
