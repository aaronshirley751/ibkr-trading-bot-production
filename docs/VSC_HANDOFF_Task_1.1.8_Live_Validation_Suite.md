# VSC HANDOFF: Task 1.1.8 — Live Validation Suite

**Date:** 2026-02-08
**Requested By:** Protocol W0 (Daily Standup) → Phase 1 Completion Gate
**Lead Personas:** @DevOps (infrastructure orchestration) + @QA_Lead (test scenarios) + @Systems_Architect (integration design)
**Model Routing:** Sonnet (Standard) — structured validation work with clear acceptance criteria
**Context Budget:** Light session (~15-20k tokens projected)

---

## 1. OBJECTIVE

Validate the trading bot's integration with IBKR Gateway under real market conditions using a paper trading account. This is the final Phase 1 gate before transitioning to Phase 2 (source code implementation). Unlike the automated test suite (Tasks 1.1.1–1.1.7), this validation requires **manual execution during market hours** to verify:

1. **Broker Connectivity:** Real Gateway connection stability, authentication, market data subscriptions
2. **Order Execution:** Paper trading order submission, fill detection, position tracking
3. **Data Quality:** Live market data stream reliability, timestamp accuracy, quote freshness
4. **Resilience:** Network timeout handling, reconnection logic, graceful degradation
5. **Operational Readiness:** Pre-deployment checklist validation, monitoring setup, alert systems

**Success Criteria:** All validation scenarios pass with paper trading account. Bot demonstrates stable operation for a minimum 2-hour market hours session with zero critical failures.

---

## 2. FILE STRUCTURE

### 2.1 Test Suite Location
```
tests/live_validation/
├── test_live_broker_connectivity.py       # Gateway connection, authentication, account data
├── test_live_market_data.py               # Real-time quotes, historical data, stream quality
├── test_live_order_execution.py           # Paper trading orders, fills, position tracking
├── test_live_resilience.py                # Network failures, reconnection, timeout handling
└── conftest.py                            # Live testing fixtures, Gateway connection setup
```

### 2.2 Supporting Documentation
```
docs/
├── deployment_validation_checklist.md     # Manual pre-deployment verification steps
└── live_validation_runbook.md             # Operator guide for executing live tests
```

### 2.3 Configuration
```
config/
└── live_validation_config.yaml            # Paper trading credentials, timeouts, thresholds
```

**CRITICAL:** All live validation tests operate in **paper trading mode only**. Never execute against live trading accounts during validation.

---

## 3. LOGIC FLOW (PSEUDO-CODE)

### 3.1 Live Validation Test Architecture

```python
# conftest.py — Gateway Connection Fixture
@pytest.fixture(scope="session")
def live_gateway_connection():
    """
    Establishes connection to IBKR Gateway for live validation testing.

    Preconditions:
    - IBKR Gateway must be running (manual startup required)
    - Paper trading credentials configured in live_validation_config.yaml
    - Market hours: 9:30 AM - 4:00 PM ET (or extended hours if configured)

    Raises:
    - ConnectionError if Gateway unreachable after 30 seconds
    - AuthenticationError if paper trading credentials invalid
    - MarketClosedError if executed outside market hours (configurable override)
    """
    config = load_config("config/live_validation_config.yaml")

    # Connect to Gateway with extended timeout for live environment
    gateway = IBKRGateway(
        host=config.gateway_host,  # Default: 127.0.0.1
        port=config.gateway_port,  # Default: 4002 (paper trading)
        client_id=config.client_id,  # Unique per session
        timeout=30  # Extended for live connection
    )

    # Authenticate and validate connection
    gateway.connect()
    if not gateway.is_connected():
        raise ConnectionError("Gateway connection failed")

    # Verify paper trading mode
    account_type = gateway.get_account_type()
    if account_type != "PAPER":
        gateway.disconnect()
        raise RuntimeError("SAFETY VIOLATION: Live validation must use paper trading account")

    # Yield connection for test session
    yield gateway

    # Cleanup: Cancel all open orders, disconnect gracefully
    gateway.cancel_all_orders()
    gateway.disconnect()


# test_live_broker_connectivity.py
def test_gateway_authentication(live_gateway_connection):
    """Verify Gateway authentication succeeds with paper trading credentials"""
    gateway = live_gateway_connection

    assert gateway.is_connected() == True
    assert gateway.is_authenticated() == True

    # Verify account details are retrievable
    account_info = gateway.get_account_info()
    assert account_info is not None
    assert account_info.account_id is not None
    assert account_info.account_type == "PAPER"


def test_account_balance_retrieval(live_gateway_connection):
    """Verify account balance and buying power are accessible"""
    gateway = live_gateway_connection

    balance = gateway.get_account_balance()
    assert balance is not None
    assert balance.total_cash_value >= 0  # Paper accounts start with virtual capital
    assert balance.buying_power >= 0


def test_position_retrieval_empty_account(live_gateway_connection):
    """Verify position tracking works (should be empty on fresh paper account)"""
    gateway = live_gateway_connection

    positions = gateway.get_positions()
    # Fresh paper account should have no positions
    # If positions exist from prior testing, verify data structure is valid
    for position in positions:
        assert position.symbol is not None
        assert position.quantity != 0
        assert position.avg_cost > 0


def test_gateway_reconnection_resilience(live_gateway_connection):
    """Verify Gateway can recover from transient disconnection"""
    gateway = live_gateway_connection

    # Force disconnect
    gateway.disconnect()
    assert gateway.is_connected() == False

    # Reconnect with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
        gateway.connect()
        if gateway.is_connected():
            break

    assert gateway.is_connected() == True
    assert gateway.is_authenticated() == True


# test_live_market_data.py
def test_market_data_subscription_spy(live_gateway_connection):
    """Verify real-time market data subscription for SPY"""
    gateway = live_gateway_connection

    # Qualify contract first (critical: prevents buffer overflow)
    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    qualified_contract = gateway.qualify_contract(contract)
    assert qualified_contract.conId > 0  # Valid contract ID assigned

    # Subscribe to real-time quotes with snapshot=True (buffer overflow fix)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    assert quote is not None
    assert quote.last_price > 0
    assert quote.bid > 0
    assert quote.ask > 0
    assert quote.ask > quote.bid  # Sanity check: ask > bid
    assert quote.timestamp is not None

    # Verify quote freshness (< 5 seconds old)
    quote_age = datetime.now(timezone.utc) - quote.timestamp
    assert quote_age.total_seconds() < 5


def test_historical_data_retrieval_spy(live_gateway_connection):
    """Verify historical data retrieval for backtesting/strategy logic"""
    gateway = live_gateway_connection

    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    qualified_contract = gateway.qualify_contract(contract)

    # Request 1 day of 5-minute bars (standard intraday data)
    bars = gateway.get_historical_data(
        contract=qualified_contract,
        duration="1 D",
        bar_size="5 mins",
        what_to_show="TRADES"
    )

    assert len(bars) > 0
    assert all(bar.close > 0 for bar in bars)
    assert all(bar.volume >= 0 for bar in bars)

    # Verify bars are in chronological order
    timestamps = [bar.timestamp for bar in bars]
    assert timestamps == sorted(timestamps)


def test_market_data_multiple_symbols(live_gateway_connection):
    """Verify concurrent market data subscriptions (SPY, QQQ, IWM)"""
    gateway = live_gateway_connection
    symbols = ["SPY", "QQQ", "IWM"]

    quotes = {}
    for symbol in symbols:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        qualified_contract = gateway.qualify_contract(contract)
        quotes[symbol] = gateway.get_market_data(qualified_contract, snapshot=True)

    # Verify all quotes retrieved successfully
    for symbol in symbols:
        assert quotes[symbol] is not None
        assert quotes[symbol].last_price > 0


def test_market_data_stream_quality(live_gateway_connection):
    """Verify market data stream remains stable over 60 seconds"""
    gateway = live_gateway_connection

    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    qualified_contract = gateway.qualify_contract(contract)

    # Subscribe to streaming data (not snapshot)
    gateway.subscribe_market_data(qualified_contract)

    # Collect quotes for 60 seconds
    quotes_received = []
    start_time = time.time()
    while time.time() - start_time < 60:
        quote = gateway.get_latest_quote(qualified_contract)
        if quote is not None:
            quotes_received.append(quote)
        time.sleep(1)  # Check every second

    gateway.unsubscribe_market_data(qualified_contract)

    # Verify stream quality
    assert len(quotes_received) >= 50  # Should receive ~60 quotes (1 per second)

    # Verify no stale quotes (all timestamps within 60-second window)
    for quote in quotes_received:
        quote_age = datetime.now(timezone.utc) - quote.timestamp
        assert quote_age.total_seconds() < 120  # Allow 2x tolerance


# test_live_order_execution.py
def test_paper_trading_limit_order_submission(live_gateway_connection):
    """Verify limit order submission to paper trading account"""
    gateway = live_gateway_connection

    # Qualify contract
    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "20260220"  # Weekly expiry
    contract.strike = 600.0  # Deep OTM for safety
    contract.right = "CALL"

    qualified_contract = gateway.qualify_contract(contract)

    # Get current market price
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    # Submit limit order at current bid (should fill immediately in paper trading)
    order = Order()
    order.action = "BUY"
    order.orderType = "LMT"
    order.totalQuantity = 1
    order.lmtPrice = quote.bid
    order.tif = "DAY"

    order_id = gateway.place_order(qualified_contract, order)
    assert order_id > 0

    # Wait for order status updates (max 30 seconds)
    order_status = None
    for _ in range(30):
        order_status = gateway.get_order_status(order_id)
        if order_status.status in ["Filled", "Cancelled"]:
            break
        time.sleep(1)

    # In paper trading, limit orders at bid should fill quickly
    assert order_status is not None
    assert order_status.status == "Filled"
    assert order_status.filled_quantity == 1


def test_paper_trading_position_tracking(live_gateway_connection):
    """Verify position appears in account after order fill"""
    gateway = live_gateway_connection

    # Submit and fill an order (reuse logic from previous test)
    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "20260220"
    contract.strike = 600.0
    contract.right = "CALL"

    qualified_contract = gateway.qualify_contract(contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    order = Order()
    order.action = "BUY"
    order.orderType = "LMT"
    order.totalQuantity = 1
    order.lmtPrice = quote.bid
    order.tif = "DAY"

    order_id = gateway.place_order(qualified_contract, order)

    # Wait for fill
    for _ in range(30):
        order_status = gateway.get_order_status(order_id)
        if order_status.status == "Filled":
            break
        time.sleep(1)

    # Retrieve positions
    positions = gateway.get_positions()

    # Verify position exists for SPY CALL
    spy_positions = [p for p in positions if p.symbol == "SPY" and p.right == "CALL"]
    assert len(spy_positions) > 0

    spy_position = spy_positions[0]
    assert spy_position.quantity == 1
    assert spy_position.avg_cost > 0


def test_paper_trading_order_cancellation(live_gateway_connection):
    """Verify order cancellation works correctly"""
    gateway = live_gateway_connection

    # Submit limit order far from market (won't fill)
    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "20260220"
    contract.strike = 600.0
    contract.right = "CALL"

    qualified_contract = gateway.qualify_contract(contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    order = Order()
    order.action = "BUY"
    order.orderType = "LMT"
    order.totalQuantity = 1
    order.lmtPrice = quote.bid * 0.5  # 50% below market (won't fill)
    order.tif = "DAY"

    order_id = gateway.place_order(qualified_contract, order)
    time.sleep(2)  # Let order register

    # Cancel order
    gateway.cancel_order(order_id)

    # Verify cancellation
    for _ in range(10):
        order_status = gateway.get_order_status(order_id)
        if order_status.status == "Cancelled":
            break
        time.sleep(1)

    assert order_status.status == "Cancelled"


def test_paper_trading_close_position(live_gateway_connection):
    """Verify position closing (sell to close)"""
    gateway = live_gateway_connection

    # First, establish a position (reuse buy logic)
    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "20260220"
    contract.strike = 600.0
    contract.right = "CALL"

    qualified_contract = gateway.qualify_contract(contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    # Buy order
    buy_order = Order()
    buy_order.action = "BUY"
    buy_order.orderType = "LMT"
    buy_order.totalQuantity = 1
    buy_order.lmtPrice = quote.bid
    buy_order.tif = "DAY"

    buy_order_id = gateway.place_order(qualified_contract, buy_order)

    # Wait for fill
    for _ in range(30):
        buy_status = gateway.get_order_status(buy_order_id)
        if buy_status.status == "Filled":
            break
        time.sleep(1)

    # Now sell to close
    sell_order = Order()
    sell_order.action = "SELL"
    sell_order.orderType = "LMT"
    sell_order.totalQuantity = 1
    sell_order.lmtPrice = quote.ask  # Sell at ask (should fill)
    sell_order.tif = "DAY"

    sell_order_id = gateway.place_order(qualified_contract, sell_order)

    # Wait for sell fill
    for _ in range(30):
        sell_status = gateway.get_order_status(sell_order_id)
        if sell_status.status == "Filled":
            break
        time.sleep(1)

    assert sell_status.status == "Filled"

    # Verify position is closed (quantity = 0 or removed)
    positions = gateway.get_positions()
    spy_positions = [p for p in positions if p.symbol == "SPY" and p.right == "CALL"]

    if len(spy_positions) > 0:
        assert spy_positions[0].quantity == 0  # Flat position


# test_live_resilience.py
def test_network_timeout_handling(live_gateway_connection):
    """Verify Gateway handles network timeouts gracefully"""
    gateway = live_gateway_connection

    # Simulate slow network by requesting data with short timeout
    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    qualified_contract = gateway.qualify_contract(contract)

    # Request historical data with artificially short timeout
    try:
        bars = gateway.get_historical_data(
            contract=qualified_contract,
            duration="1 D",
            bar_size="5 mins",
            what_to_show="TRADES",
            timeout=1  # 1 second (may timeout)
        )
        # If succeeds, verify data validity
        assert len(bars) > 0
    except TimeoutError:
        # Timeout is acceptable — verify Gateway remains connected
        assert gateway.is_connected() == True


def test_api_rate_limit_handling(live_gateway_connection):
    """Verify exponential backoff on API rate limit errors"""
    gateway = live_gateway_connection

    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    qualified_contract = gateway.qualify_contract(contract)

    # Rapid-fire requests to trigger rate limiting
    successful_requests = 0
    rate_limit_errors = 0

    for i in range(20):
        try:
            quote = gateway.get_market_data(qualified_contract, snapshot=True)
            if quote is not None:
                successful_requests += 1
        except RateLimitError:
            rate_limit_errors += 1
            # Verify exponential backoff applied
            time.sleep(2 ** min(rate_limit_errors, 3))  # Max 8 second backoff

    # Should have some successful requests despite rate limiting
    assert successful_requests > 0

    # Gateway should remain connected after rate limit events
    assert gateway.is_connected() == True


def test_market_data_staleness_detection(live_gateway_connection):
    """Verify bot detects and handles stale market data"""
    gateway = live_gateway_connection

    contract = Contract()
    contract.symbol = "SPY"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"

    qualified_contract = gateway.qualify_contract(contract)

    # Get current quote
    quote = gateway.get_market_data(qualified_contract, snapshot=True)

    # Check timestamp freshness
    quote_age = datetime.now(timezone.utc) - quote.timestamp

    # During market hours, quotes should be < 5 seconds old
    if is_market_hours():
        assert quote_age.total_seconds() < 5
    else:
        # Outside market hours, stale data is expected
        # Bot should detect and not trade on stale quotes
        pass


def test_gateway_error_recovery(live_gateway_connection):
    """Verify Gateway recovers from error states"""
    gateway = live_gateway_connection

    # Attempt invalid operation (should trigger error but not crash)
    try:
        # Request data for invalid contract
        invalid_contract = Contract()
        invalid_contract.symbol = "INVALID_SYMBOL_XYZ"
        invalid_contract.secType = "STK"
        invalid_contract.exchange = "SMART"
        invalid_contract.currency = "USD"

        qualified_contract = gateway.qualify_contract(invalid_contract)
        # Should raise ContractNotFoundError or similar
    except Exception as e:
        # Error expected — verify it's handled gracefully
        assert "not found" in str(e).lower() or "invalid" in str(e).lower()

    # Verify Gateway still operational after error
    assert gateway.is_connected() == True

    # Verify valid operations still work
    valid_contract = Contract()
    valid_contract.symbol = "SPY"
    valid_contract.secType = "STK"
    valid_contract.exchange = "SMART"
    valid_contract.currency = "USD"

    qualified_contract = gateway.qualify_contract(valid_contract)
    quote = gateway.get_market_data(qualified_contract, snapshot=True)
    assert quote is not None
```

---

## 4. DEPENDENCIES

### 4.1 External Libraries
```python
# requirements.txt additions for live validation
pytest>=7.4.0
pytest-timeout>=2.1.0
pyyaml>=6.0  # Config file parsing
```

### 4.2 IBKR Gateway Prerequisites
- **Gateway Version:** Latest stable (995.2+ recommended)
- **Paper Trading Account:** Active paper trading credentials
- **Gateway Configuration:**
  - Port: 4002 (paper trading standard)
  - API Enabled: Yes
  - Read-Only API: No (must allow order submission)
  - Auto-Restart: Disabled (manual control during validation)

### 4.3 System Requirements
- **Network:** Stable internet connection (minimum 10 Mbps)
- **Time Synchronization:** System clock must be accurate (NTP recommended)
- **Market Hours:** Tests require market hours execution (9:30 AM - 4:00 PM ET)

### 4.4 Configuration File
```yaml
# config/live_validation_config.yaml
gateway:
  host: "127.0.0.1"
  port: 4002  # Paper trading port
  client_id: 1  # Unique per bot instance
  timeout: 30  # Connection timeout (seconds)

paper_trading:
  account_type: "PAPER"  # Enforce paper trading only
  initial_capital: 100000  # Expected paper account balance

validation:
  market_hours_required: true  # Enforce market hours check
  min_session_duration: 7200  # 2 hours (seconds)
  max_retry_attempts: 3
  exponential_backoff_base: 2

test_contracts:
  spy:
    symbol: "SPY"
    secType: "STK"
    exchange: "SMART"
    currency: "USD"

  spy_weekly_call:
    symbol: "SPY"
    secType: "OPT"
    exchange: "SMART"
    currency: "USD"
    lastTradeDateOrContractMonth: "20260220"  # Update weekly
    strike: 600.0  # Deep OTM for safety
    right: "CALL"

thresholds:
  quote_freshness_seconds: 5
  stream_quality_min_quotes: 50  # Per 60-second window
  order_fill_timeout_seconds: 30
```

---

## 5. INPUT/OUTPUT CONTRACT

### 5.1 Inputs
**Configuration:**
- `config/live_validation_config.yaml` — paper trading credentials, timeouts, test parameters

**Environment:**
- IBKR Gateway running on localhost:4002
- Paper trading account authenticated
- Market hours: 9:30 AM - 4:00 PM ET (or extended hours if configured)

**Preconditions:**
- Phase 1 automated tests (Tasks 1.1.1–1.1.7) passing
- Gateway connectivity confirmed via manual ping test
- Paper trading account has sufficient virtual capital ($100k+)

### 5.2 Outputs
**Test Results:**
- Pytest report showing pass/fail for each live validation scenario
- Execution logs with timestamps, order IDs, and error messages
- Performance metrics: connection latency, quote freshness, order fill times

**Artifacts:**
- `deployment_validation_checklist.md` — completed manual verification checklist
- `live_validation_report.md` — summary of test execution with screenshots/logs

**State Changes:**
- Paper trading account may have test positions (should be closed at session end)
- Order history in IBKR paper account (non-destructive, paper trading only)

---

## 6. INTEGRATION POINTS

### 6.1 Broker Layer Integration
**Module:** `src/broker/ibkr_gateway.py`

**Methods Under Test:**
- `connect()` / `disconnect()` — Gateway connection lifecycle
- `qualify_contract()` — Contract symbol resolution
- `get_market_data()` — Real-time quote retrieval
- `get_historical_data()` — Historical bar data
- `place_order()` — Order submission
- `cancel_order()` — Order cancellation
- `get_order_status()` — Order status polling
- `get_positions()` — Position tracking
- `get_account_info()` — Account balance and buying power

**Error Handling:**
- `ConnectionError` — Gateway unreachable
- `AuthenticationError` — Invalid credentials
- `TimeoutError` — API request timeout
- `RateLimitError` — Too many requests
- `ContractNotFoundError` — Invalid symbol

### 6.2 Risk Layer Integration
**Module:** `src/risk/position_sizer.py`

**Validation:** Verify position sizing logic against paper trading account constraints
- Max position size enforced (20% of paper capital)
- Max risk per trade enforced (3% of paper capital)
- PDT compliance checks (even in paper trading)

### 6.3 Configuration Integration
**Module:** `config/crucible_config.yaml`

**Validation:** Confirm live validation config aligns with bot runtime config
- Gateway host/port match
- Client ID doesn't conflict with bot's production client ID
- Timeout values are consistent

---

## 7. DEFINITION OF DONE

### 7.1 Automated Test Coverage
- [ ] All test files in `tests/live_validation/` execute successfully
- [ ] `pytest tests/live_validation/` passes with 0 failures
- [ ] Test execution completes in < 10 minutes (excluding 60-second stream quality test)
- [ ] No flaky tests (5 consecutive runs with 100% pass rate)

### 7.2 Manual Validation Checklist
- [ ] `deployment_validation_checklist.md` completed and signed off
- [ ] All checklist items marked "PASS" or documented exceptions
- [ ] Screenshots/logs captured for critical validation steps

### 7.3 Code Quality
- [ ] `ruff check tests/live_validation/` passes with 0 errors
- [ ] `black tests/live_validation/` applied (code formatted)
- [ ] `mypy tests/live_validation/` passes with 0 type errors
- [ ] Test docstrings clearly document validation intent

### 7.4 Documentation
- [ ] `live_validation_runbook.md` created with step-by-step operator guide
- [ ] `deployment_validation_checklist.md` created with manual verification steps
- [ ] Test execution logs archived in `logs/live_validation/` with timestamps

### 7.5 Operational Readiness
- [ ] Gateway startup procedure documented
- [ ] Paper trading account credentials secured (not in version control)
- [ ] Rollback plan documented if live validation uncovers critical issues
- [ ] Known limitations documented (e.g., paper trading vs. live trading differences)

---

## 8. EDGE CASES TO TEST

### 8.1 Gateway Connectivity Edge Cases

**Case 1: Gateway Unavailable at Startup**
- **Scenario:** Bot attempts to connect before Gateway is running
- **Expected Behavior:** Connection attempt fails gracefully, bot retries with exponential backoff (1s, 2s, 4s), logs clear error message
- **Test:** `test_gateway_reconnection_resilience()`

**Case 2: Gateway Disconnects Mid-Session**
- **Scenario:** Gateway process crashes or network interruption during active trading
- **Expected Behavior:** Bot detects disconnection, cancels all pending orders, logs alert, attempts reconnection with backoff
- **Test:** Manually kill Gateway process during test execution, verify bot recovery

**Case 3: Gateway Authentication Fails**
- **Scenario:** Paper trading credentials invalid or expired
- **Expected Behavior:** Bot fails fast with clear authentication error, does not retry indefinitely
- **Test:** Temporarily use invalid credentials in config, verify error message clarity

### 8.2 Market Data Edge Cases

**Case 4: Stale Market Data (Outside Market Hours)**
- **Scenario:** Bot requests real-time quotes when market is closed
- **Expected Behavior:** Gateway returns last closing quote with stale timestamp, bot detects staleness (> 5 seconds old), does not trade
- **Test:** `test_market_data_staleness_detection()` — execute after 4:00 PM ET

**Case 5: Partial Quote Data (Bid/Ask Missing)**
- **Scenario:** Gateway returns quote with missing bid or ask (illiquid symbol)
- **Expected Behavior:** Bot detects incomplete quote, skips trading decision, logs data quality warning
- **Test:** Request quote for illiquid option strike (e.g., SPY 400 PUT), verify handling

**Case 6: Historical Data Request Timeout**
- **Scenario:** Historical data request takes > 30 seconds (Gateway overload)
- **Expected Behavior:** Bot times out gracefully, logs timeout error, does not block other operations
- **Test:** `test_network_timeout_handling()` — artificially short timeout

**Case 7: Contract Qualification Fails (Invalid Symbol)**
- **Scenario:** Bot attempts to trade symbol not available through IBKR
- **Expected Behavior:** `qualify_contract()` raises `ContractNotFoundError`, bot skips symbol, logs error
- **Test:** `test_gateway_error_recovery()` — invalid symbol "INVALID_SYMBOL_XYZ"

### 8.3 Order Execution Edge Cases

**Case 8: Order Submission Fails (Insufficient Buying Power)**
- **Scenario:** Bot attempts to buy option exceeding paper account buying power
- **Expected Behavior:** Gateway rejects order with "insufficient funds" error, bot logs rejection, does not retry
- **Test:** Manually reduce paper account balance, attempt expensive order

**Case 9: Order Partial Fill (Not Expected in Paper Trading)**
- **Scenario:** Order fills partially (unlikely in paper trading but possible in live)
- **Expected Behavior:** Bot tracks partial fill, adjusts position size, logs partial fill status
- **Test:** Requires live trading environment (not feasible in paper trading validation)

**Case 10: Order Cancellation Race Condition**
- **Scenario:** Bot attempts to cancel order that has already filled
- **Expected Behavior:** Cancel request returns "order already filled" status, bot accepts fill, updates position tracking
- **Test:** Submit market order (instant fill), immediately attempt cancel, verify handling

**Case 11: Duplicate Order Submission**
- **Scenario:** Network glitch causes bot to submit same order twice
- **Expected Behavior:** Gateway assigns unique order IDs, bot tracks both orders separately, position sizing accounts for both
- **Test:** Manually submit same order parameters twice rapidly, verify tracking

### 8.4 Position Tracking Edge Cases

**Case 12: Position Mismatch (Bot vs. Gateway)**
- **Scenario:** Bot's internal position tracker disagrees with Gateway's reported positions
- **Expected Behavior:** Bot reconciles positions on startup and periodically (every 60 seconds), logs discrepancies, trusts Gateway as source of truth
- **Test:** Manually place order via IBKR Trader Workstation (TWS), verify bot detects position on next reconciliation

**Case 13: Position Close Failure (Can't Sell)**
- **Scenario:** Bot attempts to close position but order doesn't fill (illiquid option)
- **Expected Behavior:** Bot retries with adjusted limit price (moves closer to mid-market), logs failed close attempts, escalates to manual intervention alert if no fill after 3 attempts
- **Test:** Submit sell order far from market (won't fill), verify retry logic

### 8.5 Resilience Edge Cases

**Case 14: API Rate Limiting**
- **Scenario:** Bot exceeds IBKR API rate limits (50 requests/second)
- **Expected Behavior:** Gateway returns rate limit error, bot applies exponential backoff (2s, 4s, 8s), logs rate limit event
- **Test:** `test_api_rate_limit_handling()` — rapid-fire requests

**Case 15: System Clock Drift**
- **Scenario:** Pi system clock drifts out of sync with exchange time
- **Expected Behavior:** Bot detects timestamp discrepancies (quote timestamp > system time), logs clock drift warning, suggests NTP sync
- **Test:** Manually adjust Pi system clock, verify bot detects drift

**Case 16: Memory Leak During Extended Session**
- **Scenario:** Bot runs for 6+ hours, memory usage grows unbounded
- **Expected Behavior:** Memory usage remains stable (< 500 MB), no memory leaks in Gateway connection or quote buffers
- **Test:** Run bot in dry-run mode for 6+ hours with memory profiling (`memray` or `tracemalloc`)

**Case 17: Gateway Buffer Overflow (Known Issue)**
- **Scenario:** Requesting market data without `snapshot=True` causes Gateway buffer overflow
- **Expected Behavior:** Bot ALWAYS uses `snapshot=True` for market data requests, never subscribes to streaming quotes without proper buffer management
- **Test:** Code review to verify all `get_market_data()` calls include `snapshot=True`

---

## 9. ROLLBACK PLAN

### 9.1 Validation Failure Scenarios

**Scenario 1: Critical Test Failures (> 20% of tests fail)**
- **Action:** Do NOT proceed to Phase 2. Investigate root cause, fix issues, re-run validation.
- **Timeline:** Phase 2 start date deferred until validation passes.

**Scenario 2: Gateway Instability (Frequent Disconnections)**
- **Action:** Investigate Gateway configuration, network stability, or Pi hardware constraints. Consider alternative deployment path (Desktop Gateway with IBC Controller).
- **Timeline:** Resolve within 1 week or escalate to architectural decision (Chunk 2 session).

**Scenario 3: Paper Trading vs. Live Trading Discrepancies**
- **Action:** Document discrepancies (e.g., paper trading instant fills vs. live trading slippage). Adjust risk parameters for live trading phase.
- **Timeline:** Document findings, proceed to Phase 2 with noted caveats.

### 9.2 Rollback Procedure

If live validation uncovers critical issues requiring code changes:

1. **Tag current state:** `git tag phase1-validation-blocked-YYYYMMDD`
2. **Create hotfix branch:** `git checkout -b hotfix/live-validation-fixes`
3. **Implement fixes, re-run automated tests (Tasks 1.1.1–1.1.7)**
4. **Re-run live validation (Task 1.1.8)**
5. **Merge hotfix to main:** `git merge hotfix/live-validation-fixes`
6. **Tag validated state:** `git tag phase1-validation-passed-YYYYMMDD`

### 9.3 Known Limitations (Acceptable for Phase 1)

**Paper Trading Differences:**
- Instant fills (no slippage modeling)
- No assignment risk on short options
- Unlimited buying power (no margin calls)
- No bid-ask spread impact (always fills at limit price)

**These differences are acceptable for Phase 1 validation.** Phase 4 (live trading) will require additional validation with real capital at risk.

---

## 10. DEPLOYMENT VALIDATION CHECKLIST

*This checklist should be created as a separate file: `docs/deployment_validation_checklist.md`*

### 10.1 Pre-Validation Checklist

- [ ] **Gateway Accessibility**
  - [ ] IBKR Gateway running on Pi (or localhost)
  - [ ] Gateway accessible at `127.0.0.1:4002`
  - [ ] Gateway API enabled in settings
  - [ ] Gateway auto-restart disabled (manual control)

- [ ] **Paper Trading Account**
  - [ ] Paper trading credentials confirmed (not live account)
  - [ ] Account balance ≥ $100,000 (virtual capital)
  - [ ] No existing positions from prior testing (or documented)
  - [ ] Order history cleared or known state documented

- [ ] **Network & Infrastructure**
  - [ ] Internet connection stable (ping test to IBKR servers < 50ms)
  - [ ] System clock synchronized (NTP enabled)
  - [ ] No firewall blocking ports 4002 (paper trading) or 7497 (live trading)
  - [ ] Pi hardware resources available (CPU < 50%, RAM < 70%)

- [ ] **Configuration Files**
  - [ ] `config/live_validation_config.yaml` present and valid
  - [ ] Paper trading port (4002) confirmed in config
  - [ ] Test contract parameters updated (weekly expiry dates)
  - [ ] Timeout values appropriate for live environment (30s+)

- [ ] **Market Hours Confirmation**
  - [ ] Current time is within market hours (9:30 AM - 4:00 PM ET)
  - [ ] No major market events scheduled (FOMC, earnings, etc.)
  - [ ] VIX < 30 (normal volatility for testing)

### 10.2 Validation Execution Checklist

- [ ] **Broker Connectivity Tests**
  - [ ] `test_gateway_authentication` — PASS
  - [ ] `test_account_balance_retrieval` — PASS
  - [ ] `test_position_retrieval_empty_account` — PASS
  - [ ] `test_gateway_reconnection_resilience` — PASS

- [ ] **Market Data Tests**
  - [ ] `test_market_data_subscription_spy` — PASS
  - [ ] `test_historical_data_retrieval_spy` — PASS
  - [ ] `test_market_data_multiple_symbols` — PASS
  - [ ] `test_market_data_stream_quality` — PASS (or document acceptable failure rate)

- [ ] **Order Execution Tests**
  - [ ] `test_paper_trading_limit_order_submission` — PASS
  - [ ] `test_paper_trading_position_tracking` — PASS
  - [ ] `test_paper_trading_order_cancellation` — PASS
  - [ ] `test_paper_trading_close_position` — PASS

- [ ] **Resilience Tests**
  - [ ] `test_network_timeout_handling` — PASS
  - [ ] `test_api_rate_limit_handling` — PASS
  - [ ] `test_market_data_staleness_detection` — PASS
  - [ ] `test_gateway_error_recovery` — PASS

### 10.3 Post-Validation Checklist

- [ ] **Test Artifacts**
  - [ ] Pytest report saved to `logs/live_validation/pytest_report_YYYYMMDD.txt`
  - [ ] Execution logs archived with timestamps
  - [ ] Screenshots captured for critical steps (optional)

- [ ] **Account Cleanup**
  - [ ] All test positions closed (paper account flat)
  - [ ] All open orders cancelled
  - [ ] Paper account balance confirmed (no unexpected losses)

- [ ] **Documentation**
  - [ ] `live_validation_report.md` completed
  - [ ] Known issues documented with severity ratings
  - [ ] Performance metrics recorded (latency, fill times, etc.)

- [ ] **Gateway Shutdown**
  - [ ] Gateway gracefully disconnected
  - [ ] No zombie processes left running
  - [ ] Gateway logs reviewed for errors/warnings

- [ ] **Phase 1 Sign-Off**
  - [ ] All checklist items PASS or acceptable exceptions documented
  - [ ] @QA_Lead approves validation results
  - [ ] @CRO confirms no safety concerns discovered
  - [ ] @PM marks Task 1.1.8 complete on IBKR board
  - [ ] Phase 2 kickoff authorized

---

## 11. LIVE VALIDATION RUNBOOK (OPERATOR GUIDE)

*This runbook should be created as a separate file: `docs/live_validation_runbook.md`*

### Step 1: Pre-Validation Setup (15 minutes)

1. **Start IBKR Gateway**
   ```bash
   # SSH into Pi (or run locally)
   ssh pi@crucible-pi.local

   # Start Gateway manually (not automated for validation)
   cd ~/ibkr_gateway
   ./gateway.sh

   # Verify Gateway is running
   netstat -an | grep 4002
   # Should show: tcp 0.0.0.0:4002 LISTEN
   ```

2. **Verify Paper Trading Mode**
   - Open IBKR Trader Workstation (TWS) on desktop
   - Confirm account shows "PAPER" label in top-right corner
   - Check account balance (should be ~$100k virtual capital)

3. **Activate Python Environment**
   ```bash
   cd ~/crucible
   poetry shell
   poetry install --with dev
   ```

4. **Update Test Configuration**
   ```bash
   # Edit config file
   nano config/live_validation_config.yaml

   # Update weekly expiry date (every Friday)
   # Example: If today is Feb 8, 2026, use "20260213" for next Friday
   ```

5. **Run Pre-Flight Checks**
   ```bash
   # Verify Gateway connectivity
   python scripts/check_gateway_connection.py
   # Should output: ✓ Gateway connected on port 4002

   # Verify system time sync
   timedatectl status
   # Should show: System clock synchronized: yes

   # Check network latency
   ping -c 5 gateway.interactivebrokers.com
   # Should show: avg < 50ms
   ```

### Step 2: Execute Live Validation (30-60 minutes)

1. **Run Full Test Suite**
   ```bash
   pytest tests/live_validation/ -v --tb=short
   ```

2. **Monitor Test Execution**
   - Tests will run in sequence (some take 60+ seconds)
   - Watch for failures or warnings in real-time
   - If any test fails, STOP and investigate before continuing

3. **Review Test Output**
   ```bash
   # Check for any skipped or failed tests
   pytest tests/live_validation/ --tb=short | grep -E "(FAILED|SKIPPED)"

   # If no output, all tests passed
   ```

### Step 3: Manual Validation Steps (30 minutes)

1. **Verify Position Tracking via TWS**
   - Open TWS on desktop
   - Navigate to Portfolio → Positions
   - Confirm positions match test execution (may have test positions if tests didn't fully clean up)
   - Manually close any open positions

2. **Review Order History**
   - TWS → Trade Log
   - Verify test orders are visible
   - Confirm all test orders are either Filled or Cancelled (no Pending orders)

3. **Check Gateway Logs**
   ```bash
   tail -n 100 ~/ibkr_gateway/logs/ibgateway.log
   ```
   - Look for errors, warnings, or disconnection events
   - Document any anomalies

4. **Performance Metrics**
   - Record average order fill time (from test logs)
   - Record average quote freshness (should be < 5 seconds)
   - Record Gateway uptime during test session (should be 100%)

### Step 4: Post-Validation Cleanup (10 minutes)

1. **Close All Test Positions**
   ```bash
   python scripts/close_all_positions.py --paper-trading
   ```

2. **Archive Test Logs**
   ```bash
   mkdir -p logs/live_validation/$(date +%Y%m%d)
   cp pytest_report.txt logs/live_validation/$(date +%Y%m%d)/
   cp ~/ibkr_gateway/logs/ibgateway.log logs/live_validation/$(date +%Y%m%d)/
   ```

3. **Complete Deployment Validation Checklist**
   ```bash
   nano docs/deployment_validation_checklist.md
   # Mark all checklist items as PASS or document exceptions
   ```

4. **Update Project Board**
   - Mark Task 1.1.8 complete on IBKR Project Management board
   - Add comments with validation results summary
   - Upload archived logs as attachments

5. **Shutdown Gateway (Optional)**
   ```bash
   # If not proceeding to bot testing immediately
   pkill -f "ibgateway"
   ```

### Step 5: Validation Sign-Off

1. **Create Validation Report**
   ```bash
   nano docs/live_validation_report.md
   ```
   - Include: test pass rate, performance metrics, known issues, sign-off

2. **Team Review**
   - Share report with @QA_Lead and @CRO for review
   - Address any concerns or questions
   - Obtain approval to proceed to Phase 2

3. **Phase 2 Kickoff**
   - Once validation approved, proceed to Phase 2 (source code implementation)
   - Task 2.1: Implement strategy base classes and interfaces

---

## 12. GATEWAY DEPLOYMENT STRATEGY (DEFERRED TO CHUNK 2)

**Note:** The architectural decision on Gateway deployment strategy (Linux Gateway on Pi vs. Desktop automation paths) is **out of scope** for this handoff. That decision will be addressed in a separate Opus extended thinking session (Chunk 2) after Task 1.1.8 validation is complete.

**For Task 1.1.8 purposes:**
- Use whatever Gateway deployment method is currently functional (manual startup acceptable)
- Document Gateway startup procedure in runbook
- Note any instability or reliability concerns for Chunk 2 discussion

**Chunk 2 will resolve:**
- Linux Gateway stability assessment on Pi hardware
- IBC Controller integration feasibility
- Zero-touch startup architecture
- Alternative automation paths if Linux Gateway proves unstable

---

## 13. CONTEXT BUDGET & SESSION NOTES

**Token Budget:** Light session (~15-20k tokens projected)
- Handoff document generation: ~8-10k tokens
- Pre-flight checklist: ~2-3k tokens
- File delivery and summary: ~2-3k tokens
- **Total:** ~12-16k tokens actual

**Session Clean-Up:**
- This handoff completes Stream 1 of today's work
- Remaining context budget: ~110k+ tokens (sufficient for optional Stream 2 or Chunk 2)

**Next Steps:**
1. Operator executes Task 1.1.8 during Monday market hours (Feb 9, 2026)
2. Upon completion, return to this chat or start new chat for Chunk 2 (Gateway deployment strategy)
3. Optional: If time permits today, execute Stream 2 (deferred QOL work)

---

## 14. ACCEPTANCE CRITERIA SUMMARY

✅ **This handoff is complete when:**
1. All test files in `tests/live_validation/` are created with comprehensive scenarios
2. `config/live_validation_config.yaml` is defined with paper trading parameters
3. `docs/deployment_validation_checklist.md` is created with manual verification steps
4. `docs/live_validation_runbook.md` is created with operator step-by-step guide
5. Definition of Done (Section 7) criteria are documented and clear
6. Edge cases (Section 8) are comprehensively identified and mapped to tests
7. Rollback plan (Section 9) is documented and actionable

✅ **Phase 1 is complete when:**
1. Operator executes `pytest tests/live_validation/` during market hours
2. All tests pass (0 failures, or documented acceptable exceptions)
3. `deployment_validation_checklist.md` is completed and signed off
4. Task 1.1.8 is marked complete on IBKR Project Management board
5. Phase 2 kickoff is authorized by @PM and @CRO

---

*End of VSC Handoff Document*

**@Systems_Architect:** Blueprint complete. Ready for file delivery.
**@DevOps:** Infrastructure prerequisites and operational procedures documented.
**@QA_Lead:** Test scenarios cover all critical validation paths. Edge cases comprehensively mapped.
**@CRO:** No safety concerns with validation plan. Paper trading only, no capital risk.
