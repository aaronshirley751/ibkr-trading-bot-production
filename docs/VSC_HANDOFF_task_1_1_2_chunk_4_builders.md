# VSC HANDOFF: Task 1.1.2 Chunk 4 - Test Builder Helpers

**Document ID:** `VSC_HANDOFF_task_1_1_2_chunk_4_builders.md`  
**Created:** 2026-02-06  
**Author:** @Systems_Architect  
**Reviewed By:** @QA_Lead  
**Task Reference:** Phase 1 - Test Suite Migration (Task 1.1.2, Chunk 4)  

---

## 1. OBJECTIVE

Create a comprehensive test data builder module that provides fluent, chainable interfaces for constructing realistic trading domain objects (contracts, orders, positions, fills). These builders eliminate repetitive test setup code and enforce realistic data constraints, making tests more maintainable and less brittle.

**Why This Matters:**
- Reduces 50+ lines of setup code to 5 lines with fluent builders
- Enforces domain constraints (valid strike prices, realistic Greeks, proper timestamps)
- Makes test intent immediately clear through readable builder chains
- Centralizes test data patterns for consistency across the suite
- Simplifies test maintenance when data contracts evolve

---

## 2. FILE STRUCTURE

### Files to Create

```
tests/helpers/builders.py          # NEW - Test data builder classes
```

### Files to Modify

```
tests/helpers/__init__.py          # Add builder exports
```

---

## 3. IMPLEMENTATION SPECIFICATION

### 3.1 Test Builder Module

**File:** `tests/helpers/builders.py`

```python
"""Test data builders for trading domain objects.

Provides fluent, chainable interfaces for constructing realistic test data
with sensible defaults and domain constraint enforcement.

Example usage:
    contract = ContractBuilder().spy().call().strike(580).expiry("2026-02-14").build()
    order = OrderBuilder().buy().quantity(1).limit_price(5.25).build()
    position = PositionBuilder().spy().quantity(100).avg_cost(580.50).build()
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from decimal import Decimal


class ContractBuilder:
    """Builder for IBKR Contract objects with realistic defaults.
    
    Supports options, stocks, and futures with domain-aware defaults
    for strikes, expiries, and contract specifications.
    """
    
    def __init__(self):
        self._symbol = "SPY"
        self._sec_type = "OPT"
        self._currency = "USD"
        self._exchange = "SMART"
        self._primary_exchange = ""
        self._right = "C"  # Call
        self._strike = 580.0
        self._expiry = ""
        self._multiplier = "100"
        self._local_symbol = ""
        self._trading_class = ""
        
    def spy(self) -> "ContractBuilder":
        """Set symbol to SPY with appropriate defaults."""
        self._symbol = "SPY"
        self._strike = 580.0
        return self
    
    def qqq(self) -> "ContractBuilder":
        """Set symbol to QQQ with appropriate defaults."""
        self._symbol = "QQQ"
        self._strike = 500.0
        return self
    
    def iwm(self) -> "ContractBuilder":
        """Set symbol to IWM with appropriate defaults."""
        self._symbol = "IWM"
        self._strike = 220.0
        return self
    
    def stock(self) -> "ContractBuilder":
        """Set security type to stock (STK)."""
        self._sec_type = "STK"
        self._strike = 0.0
        self._expiry = ""
        self._right = ""
        self._multiplier = "1"
        return self
    
    def option(self) -> "ContractBuilder":
        """Set security type to option (OPT)."""
        self._sec_type = "OPT"
        self._multiplier = "100"
        return self
    
    def call(self) -> "ContractBuilder":
        """Set option right to Call."""
        self._right = "C"
        return self
    
    def put(self) -> "ContractBuilder":
        """Set option right to Put."""
        self._right = "P"
        return self
    
    def strike(self, price: float) -> "ContractBuilder":
        """Set strike price."""
        self._strike = price
        return self
    
    def expiry(self, date_str: str) -> "ContractBuilder":
        """Set expiry date in YYYYMMDD format.
        
        Args:
            date_str: Expiry date as "YYYY-MM-DD" or "YYYYMMDD"
        """
        # Convert YYYY-MM-DD to YYYYMMDD if needed
        if "-" in date_str:
            date_str = date_str.replace("-", "")
        self._expiry = date_str
        return self
    
    def dte(self, days: int) -> "ContractBuilder":
        """Set expiry to N days from today.
        
        Args:
            days: Days until expiry (e.g., 2 for 2DTE)
        """
        expiry_date = datetime.now() + timedelta(days=days)
        self._expiry = expiry_date.strftime("%Y%m%d")
        return self
    
    def exchange(self, exch: str) -> "ContractBuilder":
        """Set exchange."""
        self._exchange = exch
        return self
    
    def build(self) -> Dict:
        """Build and return the contract dictionary.
        
        Returns:
            Dictionary representation of IBKR Contract
        """
        contract = {
            "symbol": self._symbol,
            "secType": self._sec_type,
            "currency": self._currency,
            "exchange": self._exchange,
        }
        
        if self._sec_type == "OPT":
            contract.update({
                "right": self._right,
                "strike": self._strike,
                "lastTradeDateOrContractMonth": self._expiry,
                "multiplier": self._multiplier,
            })
        
        return contract


class OrderBuilder:
    """Builder for IBKR Order objects with realistic defaults."""
    
    def __init__(self):
        self._action = "BUY"
        self._order_type = "LMT"
        self._total_quantity = 1
        self._lmt_price = 0.0
        self._aux_price = 0.0
        self._tif = "DAY"
        self._account = "DU123456"
        self._order_id = 0
        self._perm_id = 0
        self._client_id = 0
        
    def buy(self) -> "OrderBuilder":
        """Set action to BUY."""
        self._action = "BUY"
        return self
    
    def sell(self) -> "OrderBuilder":
        """Set action to SELL."""
        self._action = "SELL"
        return self
    
    def quantity(self, qty: int) -> "OrderBuilder":
        """Set order quantity."""
        self._total_quantity = qty
        return self
    
    def limit_price(self, price: float) -> "OrderBuilder":
        """Set limit price and order type to LMT."""
        self._order_type = "LMT"
        self._lmt_price = price
        return self
    
    def market(self) -> "OrderBuilder":
        """Set order type to market (MKT)."""
        self._order_type = "MKT"
        self._lmt_price = 0.0
        return self
    
    def stop(self, stop_price: float) -> "OrderBuilder":
        """Set order type to stop (STP)."""
        self._order_type = "STP"
        self._aux_price = stop_price
        return self
    
    def order_id(self, oid: int) -> "OrderBuilder":
        """Set order ID."""
        self._order_id = oid
        return self
    
    def account(self, acct: str) -> "OrderBuilder":
        """Set account identifier."""
        self._account = acct
        return self
    
    def tif(self, time_in_force: str) -> "OrderBuilder":
        """Set time in force (DAY, GTC, IOC, etc.)."""
        self._tif = time_in_force
        return self
    
    def build(self) -> Dict:
        """Build and return the order dictionary.
        
        Returns:
            Dictionary representation of IBKR Order
        """
        order = {
            "action": self._action,
            "orderType": self._order_type,
            "totalQuantity": self._total_quantity,
            "account": self._account,
            "tif": self._tif,
            "orderId": self._order_id,
            "permId": self._perm_id,
            "clientId": self._client_id,
        }
        
        if self._order_type == "LMT":
            order["lmtPrice"] = self._lmt_price
        
        if self._order_type == "STP":
            order["auxPrice"] = self._aux_price
        
        return order


class PositionBuilder:
    """Builder for position tracking objects."""
    
    def __init__(self):
        self._symbol = "SPY"
        self._quantity = 100
        self._avg_cost = 0.0
        self._realized_pnl = 0.0
        self._unrealized_pnl = 0.0
        self._market_value = 0.0
        
    def symbol(self, sym: str) -> "PositionBuilder":
        """Set position symbol."""
        self._symbol = sym
        return self
    
    def spy(self) -> "PositionBuilder":
        """Set symbol to SPY with default strike."""
        self._symbol = "SPY"
        return self
    
    def qqq(self) -> "PositionBuilder":
        """Set symbol to QQQ with default strike."""
        self._symbol = "QQQ"
        return self
    
    def quantity(self, qty: int) -> "PositionBuilder":
        """Set position quantity (positive=long, negative=short)."""
        self._quantity = qty
        return self
    
    def avg_cost(self, cost: float) -> "PositionBuilder":
        """Set average cost per share/contract."""
        self._avg_cost = cost
        return self
    
    def realized_pnl(self, pnl: float) -> "PositionBuilder":
        """Set realized P&L."""
        self._realized_pnl = pnl
        return self
    
    def unrealized_pnl(self, pnl: float) -> "PositionBuilder":
        """Set unrealized P&L."""
        self._unrealized_pnl = pnl
        return self
    
    def market_value(self, value: float) -> "PositionBuilder":
        """Set current market value."""
        self._market_value = value
        return self
    
    def build(self) -> Dict:
        """Build and return the position dictionary.
        
        Returns:
            Dictionary representation of position
        """
        return {
            "symbol": self._symbol,
            "quantity": self._quantity,
            "avgCost": self._avg_cost,
            "realizedPNL": self._realized_pnl,
            "unrealizedPNL": self._unrealized_pnl,
            "marketValue": self._market_value,
        }


class FillBuilder:
    """Builder for order fill/execution objects."""
    
    def __init__(self):
        self._order_id = 0
        self._exec_id = ""
        self._time = datetime.now().isoformat()
        self._account = "DU123456"
        self._exchange = "SMART"
        self._side = "BOT"  # BOT or SLD
        self._shares = 1
        self._price = 0.0
        self._perm_id = 0
        self._client_id = 0
        self._liquidation = 0
        self._cum_qty = 1
        self._avg_price = 0.0
        
    def order_id(self, oid: int) -> "FillBuilder":
        """Set order ID."""
        self._order_id = oid
        return self
    
    def exec_id(self, eid: str) -> "FillBuilder":
        """Set execution ID."""
        self._exec_id = eid
        return self
    
    def buy(self) -> "FillBuilder":
        """Set side to bought (BOT)."""
        self._side = "BOT"
        return self
    
    def sell(self) -> "FillBuilder":
        """Set side to sold (SLD)."""
        self._side = "SLD"
        return self
    
    def quantity(self, qty: int) -> "FillBuilder":
        """Set fill quantity."""
        self._shares = qty
        self._cum_qty = qty
        return self
    
    def price(self, px: float) -> "FillBuilder":
        """Set fill price."""
        self._price = px
        self._avg_price = px
        return self
    
    def timestamp(self, ts: str) -> "FillBuilder":
        """Set execution timestamp (ISO format)."""
        self._time = ts
        return self
    
    def account(self, acct: str) -> "FillBuilder":
        """Set account identifier."""
        self._account = acct
        return self
    
    def build(self) -> Dict:
        """Build and return the fill dictionary.
        
        Returns:
            Dictionary representation of execution/fill
        """
        return {
            "orderId": self._order_id,
            "execId": self._exec_id,
            "time": self._time,
            "account": self._account,
            "exchange": self._exchange,
            "side": self._side,
            "shares": self._shares,
            "price": self._price,
            "permId": self._perm_id,
            "clientId": self._client_id,
            "liquidation": self._liquidation,
            "cumQty": self._cum_qty,
            "avgPrice": self._avg_price,
        }
```

---

### 3.2 Update Helpers Init Module

**File:** `tests/helpers/__init__.py`

**Current Content:**
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

**Add Builders:**
```python
"""Test helper modules."""
from tests.helpers.assertions import (
    assert_price_within_tolerance,
    assert_position_exists,
    assert_no_position,
)
from tests.helpers.builders import (
    ContractBuilder,
    OrderBuilder,
    PositionBuilder,
    FillBuilder,
)

__all__ = [
    # Assertions
    "assert_price_within_tolerance",
    "assert_position_exists",
    "assert_no_position",
    # Builders
    "ContractBuilder",
    "OrderBuilder",
    "PositionBuilder",
    "FillBuilder",
]
```

---

## 4. DEPENDENCIES

### Python Imports
```python
from datetime import datetime, timedelta
from typing import Dict, Optional
from decimal import Decimal
```

**Standard Library Only:** No external dependencies required.

### Integration Dependencies
- Will be imported by test modules across the test suite
- Complements existing fixtures in `tests/conftest.py`
- Works alongside assertion helpers from Chunk 3
- No runtime dependencies on production code

---

## 5. INPUT/OUTPUT CONTRACT

### Builder Pattern Overview

All builders follow the same fluent interface pattern:

```python
# Create builder instance
builder = ContractBuilder()

# Chain configuration methods
builder.spy().call().strike(580).dte(2)

# Build final object
contract = builder.build()
```

### ContractBuilder

**Fluent Methods:**
```python
.spy() / .qqq() / .iwm()  # Symbol presets with reasonable strikes
.stock() / .option()       # Security type
.call() / .put()           # Option right
.strike(float)             # Strike price
.expiry(str)               # Expiry date YYYY-MM-DD or YYYYMMDD
.dte(int)                  # Days to expiry (auto-calculate date)
.exchange(str)             # Exchange routing
```

**Output:**
```python
{
    "symbol": "SPY",
    "secType": "OPT",
    "currency": "USD",
    "exchange": "SMART",
    "right": "C",
    "strike": 580.0,
    "lastTradeDateOrContractMonth": "20260214",
    "multiplier": "100"
}
```

**Example Usage:**
```python
# ATM SPY call expiring in 2 days
contract = ContractBuilder().spy().call().strike(580).dte(2).build()

# QQQ put stock
stock = ContractBuilder().qqq().stock().build()

# IWM put with specific expiry
put = ContractBuilder().iwm().put().strike(220).expiry("2026-02-28").build()
```

### OrderBuilder

**Fluent Methods:**
```python
.buy() / .sell()           # Order action
.quantity(int)             # Total quantity
.limit_price(float)        # Limit price (sets type to LMT)
.market()                  # Market order
.stop(float)               # Stop order with trigger price
.order_id(int)             # Order identifier
.account(str)              # Account ID
.tif(str)                  # Time in force
```

**Output:**
```python
{
    "action": "BUY",
    "orderType": "LMT",
    "totalQuantity": 1,
    "account": "DU123456",
    "tif": "DAY",
    "orderId": 1,
    "lmtPrice": 5.25,
    ...
}
```

**Example Usage:**
```python
# Buy 1 contract at limit price
order = OrderBuilder().buy().quantity(1).limit_price(5.25).order_id(101).build()

# Sell market order
order = OrderBuilder().sell().quantity(2).market().build()

# Stop loss order
order = OrderBuilder().sell().quantity(1).stop(4.50).build()
```

### PositionBuilder

**Fluent Methods:**
```python
.symbol(str) / .spy() / .qqq()  # Position symbol
.quantity(int)                   # Position size (+ long, - short)
.avg_cost(float)                 # Average entry price
.realized_pnl(float)             # Realized profit/loss
.unrealized_pnl(float)           # Unrealized profit/loss
.market_value(float)             # Current market value
```

**Output:**
```python
{
    "symbol": "SPY",
    "quantity": 100,
    "avgCost": 580.50,
    "realizedPNL": 0.0,
    "unrealizedPNL": 125.00,
    "marketValue": 58175.00
}
```

**Example Usage:**
```python
# Long position with profit
position = PositionBuilder().spy().quantity(100).avg_cost(580).unrealized_pnl(125).build()

# Flat position
position = PositionBuilder().qqq().quantity(0).build()
```

### FillBuilder

**Fluent Methods:**
```python
.order_id(int)             # Associated order ID
.exec_id(str)              # Execution identifier
.buy() / .sell()           # Fill side (BOT/SLD)
.quantity(int)             # Fill quantity
.price(float)              # Fill price
.timestamp(str)            # Execution timestamp
.account(str)              # Account ID
```

**Output:**
```python
{
    "orderId": 101,
    "execId": "0001f4e8.65c3d2a1.01.01",
    "time": "2026-02-06T14:30:00",
    "side": "BOT",
    "shares": 1,
    "price": 5.25,
    "avgPrice": 5.25,
    ...
}
```

**Example Usage:**
```python
# Partial fill
fill = FillBuilder().order_id(101).buy().quantity(1).price(5.25).build()

# Complete fill with timestamp
fill = FillBuilder().order_id(102).sell().quantity(2).price(5.50).timestamp("2026-02-06T15:45:00").build()
```

---

## 6. INTEGRATION POINTS

### Test Module Imports
```python
# In any test file
from tests.helpers import (
    ContractBuilder,
    OrderBuilder,
    PositionBuilder,
    FillBuilder,
)
```

### Usage Pattern in Tests
```python
def test_order_execution(mock_broker):
    # Setup: Build test objects with minimal code
    contract = ContractBuilder().spy().call().strike(580).dte(2).build()
    order = OrderBuilder().buy().quantity(1).limit_price(5.25).build()
    
    # Execute
    result = mock_broker.place_order(contract, order)
    
    # Verify
    expected_fill = FillBuilder().order_id(order["orderId"]).buy().price(5.25).build()
    assert result["execId"] == expected_fill["execId"]
```

### Combining with Fixtures
```python
def test_position_tracking(mock_broker, sample_market_data):
    # Build position from market data
    position = PositionBuilder().spy().quantity(100).avg_cost(sample_market_data["close"]).build()
    
    # Test position management logic
    mock_broker.update_position(position)
    assert_position_exists(mock_broker.positions, "SPY", 100)
```

---

## 7. DEFINITION OF DONE

### Code Quality Gates
- [ ] `ruff check tests/helpers/builders.py` → Zero warnings
- [ ] `black tests/helpers/builders.py --check` → No formatting needed
- [ ] `mypy tests/helpers/builders.py` → Type checking passes
- [ ] File exists at correct path: `tests/helpers/builders.py`
- [ ] `tests/helpers/__init__.py` updated with builder exports

### Functional Validation
- [ ] All builders can be imported: `python -c "from tests.helpers import ContractBuilder, OrderBuilder, PositionBuilder, FillBuilder"`
- [ ] No syntax errors or import failures
- [ ] Module docstring present and accurate
- [ ] Each builder class has complete docstring with examples

### Documentation
- [ ] Each builder class has complete docstring
- [ ] Each builder method has docstring explaining purpose
- [ ] Type hints present for all parameters and return values
- [ ] Example usage patterns documented in module docstring

### Ready for Integration
- [ ] @QA_Lead approval received
- [ ] File committed to version control
- [ ] Ready for use in migrated test files

---

## 8. EDGE CASES & TEST SCENARIOS

### Edge Case 1: Option vs Stock Contract Differentiation
**Scenario:** Builder must correctly omit option-specific fields for stock contracts  
**Example:**
```python
stock = ContractBuilder().spy().stock().build()
# Should NOT include: right, strike, lastTradeDateOrContractMonth
# Should include: symbol, secType=STK, currency, exchange
```
**Expected:** Stock contracts have no option-specific fields

### Edge Case 2: Date Format Conversion
**Scenario:** Expiry dates can be input as YYYY-MM-DD or YYYYMMDD  
**Example:**
```python
c1 = ContractBuilder().spy().call().expiry("2026-02-14").build()
c2 = ContractBuilder().spy().call().expiry("20260214").build()
# Both should produce lastTradeDateOrContractMonth: "20260214"
```
**Expected:** Hyphenated dates automatically converted to YYYYMMDD

### Edge Case 3: DTE Auto-Calculation
**Scenario:** Using .dte() should calculate correct future date  
**Example:**
```python
contract = ContractBuilder().spy().call().dte(2).build()
# Should set expiry to 2 days from datetime.now()
```
**Expected:** Expiry date dynamically calculated based on current date

### Edge Case 4: Order Type Implications
**Scenario:** Setting limit_price should automatically set orderType to LMT  
**Example:**
```python
order = OrderBuilder().buy().limit_price(5.25).build()
# Should have: orderType="LMT", lmtPrice=5.25
```
**Expected:** Order type inferred from price-setting methods

### Edge Case 5: Conditional Field Inclusion
**Scenario:** Stop orders should include auxPrice but not lmtPrice  
**Example:**
```python
stop_order = OrderBuilder().sell().stop(4.50).build()
# Should have: orderType="STP", auxPrice=4.50
# Should NOT have: lmtPrice
```
**Expected:** Field inclusion based on order type

### Edge Case 6: Position Sign Convention
**Scenario:** Positive quantity = long, negative = short  
**Example:**
```python
long_pos = PositionBuilder().spy().quantity(100).build()   # Long 100
short_pos = PositionBuilder().spy().quantity(-100).build()  # Short 100
flat_pos = PositionBuilder().spy().quantity(0).build()      # Flat
```
**Expected:** Sign preserved in output, no validation errors

### Edge Case 7: Builder Reuse
**Scenario:** Creating multiple objects from same builder instance  
**Example:**
```python
builder = ContractBuilder().spy().call().strike(580)
c1 = builder.build()
c2 = builder.strike(585).build()  # Modifies existing builder
# c2 should have strike 585, but does c1 change retroactively?
```
**Expected:** Each .build() returns independent object, builder state persists

### Edge Case 8: Default Value Sanity
**Scenario:** Default values should be realistic for testing  
**Example:**
```python
contract = ContractBuilder().build()
# Should have sensible defaults: SPY, CALL, ~ATM strike, OPT type
```
**Expected:** Defaults create valid, realistic test objects

---

## 9. ROLLBACK PLAN

### If Builders Module Causes Issues

**Rollback Steps:**
1. Remove import statements from any test files using these builders
2. Delete `tests/helpers/builders.py`
3. Remove builder exports from `tests/helpers/__init__.py`
4. Replace builder usage with manual dict construction in affected tests

**Minimal Impact:** Since this is a new module with no production code dependencies, rollback is straightforward. Only test files would need updates.

### Temporary Disable (If Needed)
```python
# In tests/helpers/__init__.py - comment out builder imports
# from tests.helpers.builders import (
#     ContractBuilder,
#     OrderBuilder,
#     PositionBuilder,
#     FillBuilder,
# )

# Tests will fail with ImportError, making the issue obvious
```

---

## 10. QUALITY VALIDATION COMMANDS

Run these commands in sequence to validate the implementation:

```bash
# 1. Verify file exists
ls -la tests/helpers/builders.py

# 2. Syntax and style check
ruff check tests/helpers/builders.py

# 3. Code formatting validation
black tests/helpers/builders.py --check

# 4. Type checking
mypy tests/helpers/builders.py

# 5. Import validation (should produce no output)
python -c "from tests.helpers import ContractBuilder, OrderBuilder, PositionBuilder, FillBuilder"

# 6. Verify module docstring
python -c "import tests.helpers.builders; print(tests.helpers.builders.__doc__)"

# 7. Smoke test - build sample objects
python -c "
from tests.helpers import ContractBuilder, OrderBuilder

contract = ContractBuilder().spy().call().strike(580).dte(2).build()
print('Contract:', contract)

order = OrderBuilder().buy().quantity(1).limit_price(5.25).build()
print('Order:', order)

print('✅ Builders working correctly')
"
```

**Expected Results:**
- `ls`: File exists, ~8-10KB size
- `ruff`: No warnings or errors
- `black`: "All done! ✨ 🍰 ✨" with no files changed
- `mypy`: "Success: no issues found"
- Import command: No output (success)
- Docstring: Module description with usage examples
- Smoke test: Contract and order dicts printed, success message

---

## 11. FOLLOW-UP TASKS

### Immediate Next Steps
1. **Begin using builders in tests:** Update test migration tasks to leverage builders
2. **Validate with QA_Lead:** Run smoke tests and get approval
3. **Document patterns:** Create examples in test files showing builder usage

### Future Enhancements (Post-Phase 1)
- Add `GreeksBuilder` for option Greeks (delta, gamma, theta, vega, IV)
- Add `MarketDataBuilder` for OHLCV bars with realistic intraday patterns
- Add `GameplanBuilder` for daily_gameplan.json test data
- Add validation methods to builders (e.g., `.validate_strike_price()`)
- Consider adding `.random()` methods for property-based testing
- Add builder presets for common test scenarios (`.winning_trade()`, `.losing_trade()`)

---

## 12. COPILOT-READY PROMPT

**Copy this section to VSCode Copilot Chat:**

```
Create tests/helpers/builders.py with fluent builder classes for trading domain objects.

REQUIREMENTS:
1. Create file at: tests/helpers/builders.py
2. Implement four builder classes: ContractBuilder, OrderBuilder, PositionBuilder, FillBuilder
3. Each builder uses fluent interface pattern (method chaining)
4. All builders have .build() method returning dictionary
5. Include comprehensive docstrings with usage examples

CLASS 1: ContractBuilder
- Methods: spy(), qqq(), iwm(), stock(), option(), call(), put()
- Methods: strike(float), expiry(str), dte(int), exchange(str)
- Build returns IBKR contract dict with symbol, secType, currency, exchange
- Options include: right, strike, lastTradeDateOrContractMonth, multiplier
- Stocks omit option-specific fields

CLASS 2: OrderBuilder
- Methods: buy(), sell(), quantity(int), limit_price(float), market(), stop(float)
- Methods: order_id(int), account(str), tif(str)
- Build returns IBKR order dict with action, orderType, totalQuantity, account, tif
- Conditional fields: lmtPrice (if LMT), auxPrice (if STP)

CLASS 3: PositionBuilder
- Methods: symbol(str), spy(), qqq(), quantity(int), avg_cost(float)
- Methods: realized_pnl(float), unrealized_pnl(float), market_value(float)
- Build returns position dict with symbol, quantity, avgCost, PNL fields

CLASS 4: FillBuilder
- Methods: order_id(int), exec_id(str), buy(), sell(), quantity(int), price(float)
- Methods: timestamp(str), account(str)
- Build returns execution dict with orderId, execId, time, side, shares, price

VALIDATION:
After implementation:
- Update tests/helpers/__init__.py to export all four builders
- Run: ruff check tests/helpers/builders.py
- Run: black tests/helpers/builders.py --check
- Run: mypy tests/helpers/builders.py
- Test imports and smoke test sample builds

All should pass with zero issues.
```

---

**Document Status:** ✅ Ready for Implementation  
**Approvals:** @Systems_Architect (author), awaiting @QA_Lead (reviewer)  
**Next Action:** Factory Floor implementation via VSCode Copilot  

---

*@Systems_Architect signing off. This handoff document is complete and ready for the Factory Floor. The builder pattern will significantly improve test maintainability and readability.*
