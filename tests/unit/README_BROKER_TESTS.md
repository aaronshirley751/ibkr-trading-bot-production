# Broker Layer Tests - TDD Status

## Overview
Coverage-1.1.3 broker layer tests document expected behavior for `src/broker/` module that doesn't exist yet. This is intentional TDD (Test-Driven Development) approach.

## Test Files

### 1. `test_broker_connection.py`
**Status**: Most tests require `src/broker/connection.py` implementation
**Passing Tests** (logic validation only):
- `test_client_id_uniqueness()` ✅ - Validates timestamp-based ClientId generation algorithm

**Pending Tests** (await broker implementation):
- Connection establishment
- Retry logic with exponential backoff
- Timeout handling
- Connection cleanup
- Parameter validation
- State checks

### 2. `test_market_data.py`
**Status**: Most tests require  `src/broker/market_data.py` implementation
**Passing Tests** (data validation logic):
- `test_market_data_validation()` ✅ - Validates OHLCV field presence
- `test_stale_data_detection()` ✅ - Validates 5-minute staleness threshold
- `test_fresh_data_passes_staleness_check()` ✅ - Validates fresh data logic
- `test_missing_field_handling()` ✅ - Validates missing field detection
- `test_market_data_bid_ask_spread_validation()` ✅ - Validates bid/ask relationships
- `test_zero_volume_handling()` ✅ - Validates illiquid security detection
- `test_historical_bars_ohlcv_validation()` ✅ - Validates bar data structure

**Pending Tests** (await broker implementation):
- **🔴 CRITICAL**: `test_snapshot_mode_enforcement()` - Validates snapshot=True requirement
- **🔴 CRITICAL**: `test_contract_qualification_before_data_request()` - Validates qualification ordering
- **🔴 CRITICAL**: `test_historical_data_timeout_propagation()` - Validates timeout threading
- Contract qualification rejection
- Market data error handling
- Concurrent requests
- Historical data RTH enforcement

### 3. `test_gateway_communication.py`
**Status**: All tests require `src/broker/` implementation + Gateway mock infrastructure
**Passing Tests**:
- `test_client_id_uniqueness_across_connections()` ✅ - Validates ClientId collision prevention

**Pending Tests** (await broker implementation):
- **🔴 CRITICAL**: Full workflow with snapshot=True validation
- **🔴 CRITICAL**: Timeout propagation through entire stack
- **🔴 CRITICAL**: Historical data RTH-only enforcement
- Concurrent request handling
- Gateway disconnection recovery
- Error recovery degradation to Strategy C
- Stale data triggers Strategy C
- Contract qualification failures
- Multi-step workflow error handling

## Critical Alpha Learnings Encoded

1. **🔴 snapshot=True MUST be enforced** (prevents buffer overflow)
   - Test: `test_snapshot_mode_enforcement()`
   - Status: Pending broker implementation
   - Regression Risk: HIGH - Production incident 2024-01-15

2. **🔴 Contract qualification MUST occur before data requests**
   - Test: `test_contract_qualification_before_data_request()`
   - Status: Pending broker implementation
   - Regression Risk: MEDIUM - Invalid symbols crash strategy

3. **🔴 Timeout MUST propagate through entire call stack**
   - Test: `test_timeout_propagation_through_layers()`
   - Status: Pending broker implementation
   - Regression Risk: MEDIUM - Silent hangs in production

4. **Historical data: 1-hour RTH-only windows**
   - Test: `test_historical_data_rth_enforcement()`
   - Status: Pending broker implementation
   - Regression Risk: LOW - Alpha strategy requirement

5. **ClientId: Timestamp-based for uniqueness**
   - Test: `test_client_id_uniqueness()` ✅
   - Status: PASSING
   - Regression Risk: LOW - Gateway rejects duplicate ClientIds

## Expected Test Results (Current State)

```
Total Tests: 35
- Passing: 9 (data validation logic)
- Failing: 26 (require src/broker/ implementation)
- Coverage: 0% (no production code exists yet)
```

## When To Re-Run Full Suite

Execute full test suite AFTER implementing:
1. `src/broker/connection.py` - Connection management with retry logic
2. `src/broker/market_data.py` - Market data requests with snapshot enforcement
3. `src/broker/gateway.py` - Gateway communication wrapper
4. Mock Gateway infrastructure in `tests/conftest.py`

## Quality Gates

**Current Status**: Blueprint compliance ✅
- ✅ All 3 test files created (265 + 495 + 531 lines)
- ✅ All CRITICAL alpha learnings documented as assertions
- ✅ TDD approach followed (tests first, code later)
- ⏳ Coverage target (≥92%) - Pending broker implementation
- ⏳ All tests passing - Pending broker implementation

**Next Steps**:
1. Implement `src/broker/connection.py`
2. Implement `src/broker/market_data.py`
3. Build mock Gateway infrastructure
4. Re-run tests, expect ≥92% coverage
5. Validate CRITICAL assertions enforce alpha learnings

## Documentation

Full specifications: `docs/vsc_handoff_coverage_1.1.3_broker_layer_tests.md` (563 lines)

---
**Generated**: Coverage-1.1.3 Task
**Author**: GitHub Copilot (Claude Sonnet 4.5)
**Date**: 2025-01-XX
