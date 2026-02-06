# VSC HANDOFF: Task 1.1.2 Chunk 5 - IBKR Snapshot Capture Script

**Document ID:** `VSC_HANDOFF_task_1_1_2_chunk_5_snapshot_script.md`  
**Created:** 2026-02-06  
**Author:** @Systems_Architect  
**Reviewed By:** @QA_Lead, @CRO (risk validation)  
**Task Reference:** Phase 1 - Test Suite Migration (Task 1.1.2, Chunk 5)  

---

## 1. OBJECTIVE

Create a standalone script that connects to IBKR Gateway (paper trading account) during market hours and captures real market data snapshots for use in test fixtures. The script will collect option chains, historical bars, and Greeks for SPY/QQQ/IWM, saving them as JSON files in `tests/fixtures/ibkr_snapshots/` for realistic test data.

**Why This Matters:**
- Provides **real IBKR data** for test fixtures instead of synthetic/fake data
- Captures actual option chain structures, Greeks, and market behavior
- Creates reproducible test scenarios from real market conditions
- Validates that our data handling code works with actual IBKR API responses
- Enables testing edge cases that only occur in real market data (wide spreads, low volume, etc.)

**Critical Constraint:** This script runs ONLY in paper trading mode, NEVER connects to live account.

---

## 2. FILE STRUCTURE

### Files to Create

```
scripts/capture_ibkr_snapshot.py       # NEW - Main snapshot capture script
tests/fixtures/ibkr_snapshots/         # NEW - Directory for captured data
tests/fixtures/ibkr_snapshots/.gitkeep # NEW - Ensure directory tracked in git
```

### Files to Modify

```
None (pure addition)
```

---

## 3. IMPLEMENTATION SPECIFICATION

### 3.1 Snapshot Capture Script

**File:** `scripts/capture_ibkr_snapshot.py`

```python
#!/usr/bin/env python3
"""IBKR Market Data Snapshot Capture Script.

Connects to IBKR Gateway (paper trading) and captures real market data
for use in test fixtures. Captures option chains, historical bars, and
Greeks for SPY, QQQ, and IWM.

IMPORTANT: This script ONLY connects to paper trading. Never use with live account.

Usage:
    python scripts/capture_ibkr_snapshot.py [--scenario SCENARIO_NAME]

Examples:
    python scripts/capture_ibkr_snapshot.py
    python scripts/capture_ibkr_snapshot.py --scenario high_vix
    python scripts/capture_ibkr_snapshot.py --scenario tight_spreads

Requirements:
    - IBKR Gateway running and connected (paper trading)
    - Market hours (9:30 AM - 4:00 PM ET)
    - Gateway port 4002 (paper trading port)
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import time

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order


class SnapshotCapture(EWrapper, EClient):
    """Captures IBKR market data snapshots for test fixtures."""
    
    def __init__(self):
        EClient.__init__(self, self)
        self.next_order_id: Optional[int] = None
        self.contract_details: Dict[int, List] = {}
        self.option_chains: Dict[str, List] = {}
        self.historical_bars: Dict[str, List] = {}
        self.market_data: Dict[int, Dict] = {}
        self.greeks_data: Dict[int, Dict] = {}
        self.current_request_id = 1000
        self.account_type: Optional[str] = None
        self.accounts: str = ""
        
    def nextValidId(self, orderId: int):
        """Callback when connection established."""
        print(f"✓ Connected to IBKR Gateway. Next Order ID: {orderId}")
        self.next_order_id = orderId
    
    def managedAccounts(self, accountsList: str):
        """Callback for connected accounts - provides audit trail."""
        print(f"  Connected accounts: {accountsList}")
        self.accounts = accountsList
    
    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary - CRITICAL SAFETY CHECK."""
        if tag == "AccountType":
            self.account_type = value
            print(f"  Account Type: {value}")
            
            # CRITICAL SAFETY CHECK - ABORT if not paper trading
            if value != "PAPER":
                print(f"\n{'!'*60}")
                print(f"🔴 SAFETY VIOLATION: Account type is '{value}' not 'PAPER'")
                print(f"🔴 This script ONLY runs on paper trading accounts")
                print(f"🔴 ABORTING to prevent live account access")
                print(f"{'!'*60}\n")
                self.disconnect()
                sys.exit(1)
    
    def accountSummaryEnd(self, reqId: int):
        """Callback when account summary complete."""
        pass
        
    def error(self, reqId: int, errorCode: int, errorString: str):
        """Error handler."""
        # Filter out informational messages
        if errorCode in [2104, 2106, 2158]:  # Market data farm connection messages
            print(f"ℹ Info [{errorCode}]: {errorString}")
        elif errorCode == 200:  # No security definition found
            print(f"⚠ Warning: Contract not found (reqId {reqId})")
        else:
            print(f"✗ Error [{errorCode}] (reqId {reqId}): {errorString}")
    
    def contractDetails(self, reqId: int, contractDetails):
        """Callback for contract details."""
        if reqId not in self.contract_details:
            self.contract_details[reqId] = []
        self.contract_details[reqId].append(contractDetails)
        
    def contractDetailsEnd(self, reqId: int):
        """Callback when all contract details received."""
        count = len(self.contract_details.get(reqId, []))
        print(f"✓ Received {count} contract details for reqId {reqId}")
        
    def historicalData(self, reqId: int, bar):
        """Callback for historical data bars."""
        if reqId not in self.historical_bars:
            self.historical_bars[reqId] = []
        
        bar_data = {
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "wap": bar.wap,  # Weighted average price
            "barCount": bar.barCount,
        }
        self.historical_bars[reqId].append(bar_data)
        
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback when historical data complete."""
        count = len(self.historical_bars.get(reqId, []))
        print(f"✓ Received {count} historical bars for reqId {reqId}")
        
    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Callback for market data price ticks."""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        tick_names = {
            1: "bid",
            2: "ask",
            4: "last",
            6: "high",
            7: "low",
            9: "close",
        }
        
        if tickType in tick_names:
            self.market_data[reqId][tick_names[tickType]] = price
            
    def tickSize(self, reqId: int, tickType: int, size: int):
        """Callback for market data size ticks."""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        tick_names = {
            0: "bidSize",
            3: "askSize",
            5: "lastSize",
            8: "volume",
        }
        
        if tickType in tick_names:
            self.market_data[reqId][tick_names[tickType]] = size
            
    def tickOptionComputation(self, reqId: int, tickType: int, tickAttrib: int,
                             impliedVol: float, delta: float, optPrice: float,
                             pvDividend: float, gamma: float, vega: float,
                             theta: float, undPrice: float):
        """Callback for option Greeks."""
        if reqId not in self.greeks_data:
            self.greeks_data[reqId] = {}
        
        # Only store model Greeks (tickType 13)
        if tickType == 13:
            self.greeks_data[reqId] = {
                "impliedVolatility": impliedVol if impliedVol != -1 else None,
                "delta": delta if delta != -2 else None,
                "gamma": gamma if gamma != -2 else None,
                "vega": vega if vega != -2 else None,
                "theta": theta if theta != -2 else None,
                "optionPrice": optPrice if optPrice != -1 else None,
                "underlyingPrice": undPrice if undPrice != -1 else None,
            }


def create_stock_contract(symbol: str) -> Contract:
    """Create a stock contract."""
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.primaryExchange = "NASDAQ" if symbol in ["QQQ"] else "ARCA"
    return contract


def create_option_contract(symbol: str, right: str, strike: float, expiry: str) -> Contract:
    """Create an option contract.
    
    Args:
        symbol: Underlying symbol (SPY, QQQ, IWM)
        right: Call (C) or Put (P)
        strike: Strike price
        expiry: Expiry date in YYYYMMDD format
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "OPT"
    contract.exchange = "SMART"
    contract.currency = "USD"
    contract.right = right
    contract.strike = strike
    contract.lastTradeDateOrContractMonth = expiry
    contract.multiplier = "100"
    return contract


def get_atm_strike(price: float, symbol: str) -> float:
    """Calculate ATM strike based on current price.
    
    Args:
        price: Current underlying price
        symbol: Symbol (for strike increment logic)
    
    Returns:
        ATM strike price rounded to nearest valid strike
    """
    # SPY/QQQ typically have $1 strikes, IWM has $1 strikes
    increment = 1.0
    
    # Round to nearest increment
    atm = round(price / increment) * increment
    return atm


def get_expiry_dates(days_out: List[int]) -> List[str]:
    """Get expiry dates for options.
    
    Args:
        days_out: List of days from today (e.g., [2, 7, 14])
    
    Returns:
        List of expiry dates in YYYYMMDD format
    """
    expiries = []
    for days in days_out:
        expiry = datetime.now() + timedelta(days=days)
        # Find next Friday (options typically expire on Friday)
        days_until_friday = (4 - expiry.weekday()) % 7
        if days_until_friday == 0 and expiry.weekday() != 4:
            days_until_friday = 7
        expiry = expiry + timedelta(days=days_until_friday)
        expiries.append(expiry.strftime("%Y%m%d"))
    return expiries


def validate_snapshot_completeness(data: Dict) -> bool:
    """Validate snapshot has minimum required data.
    
    Args:
        data: Snapshot data dictionary
    
    Returns:
        True if snapshot meets minimum completeness criteria
    """
    issues = []
    
    for symbol, symbol_data in data["symbols"].items():
        # Check current price
        if not symbol_data.get("currentPrice") or symbol_data.get("currentPrice") == 0:
            issues.append(f"{symbol}: Missing or zero current price")
        
        # Check historical bars (expect ~30-40 bars for 5 days)
        hist_bars = symbol_data.get("historicalBars", [])
        if len(hist_bars) < 20:
            issues.append(
                f"{symbol}: Insufficient historical bars ({len(hist_bars)}, expected 20+)"
            )
        
        # Check option chain (expect 20 contracts: 5 strikes × 2 expiries × 2 rights)
        option_chain = symbol_data.get("optionChain", [])
        if len(option_chain) < 10:
            issues.append(
                f"{symbol}: Insufficient option data ({len(option_chain)}, expected 10+)"
            )
        
        # Check that at least some options have Greeks
        options_with_greeks = sum(
            1 for opt in option_chain
            if opt.get("greeks") and opt["greeks"].get("delta") is not None
        )
        if options_with_greeks == 0 and len(option_chain) > 0:
            issues.append(f"{symbol}: No options have valid Greeks data")
    
    if issues:
        print("\n" + "⚠" * 60)
        print("WARNING: Snapshot incomplete - may not be suitable for testing")
        print("⚠" * 60)
        for issue in issues:
            print(f"  ⚠ {issue}")
        print()
        return False
    
    print("✓ Snapshot completeness validation passed")
    return True


def capture_snapshot(scenario_name: str = "normal") -> Dict:
    """Capture market data snapshot.
    
    Args:
        scenario_name: Scenario identifier (normal, high_vix, tight_spreads, etc.)
    
    Returns:
        Dictionary containing all captured data
    """
    print(f"\n{'='*60}")
    print(f"IBKR Snapshot Capture - Scenario: {scenario_name}")
    print(f"{'='*60}\n")
    
    # Connect to IBKR Gateway (paper trading port 4002)
    app = SnapshotCapture()
    print("Connecting to IBKR Gateway on port 4002 (paper trading)...")
    app.connect("127.0.0.1", 4002, clientId=1)
    
    # Start message processing thread
    import threading
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    
    # Wait for connection
    timeout = 10
    start_time = time.time()
    while app.next_order_id is None:
        if time.time() - start_time > timeout:
            print("✗ Connection timeout")
            sys.exit(1)
        time.sleep(0.1)
    
    print(f"✓ Connected successfully\n")
    
    # CRITICAL SAFETY: Verify account type is PAPER
    print("=" * 60)
    print("SAFETY CHECK: Verifying account type...")
    print("=" * 60)
    app.reqAccountSummary(9999, "All", "AccountType")
    
    # Wait for account type verification
    timeout = 5
    start_time = time.time()
    while app.account_type is None:
        if time.time() - start_time > timeout:
            print("✗ Account type verification timeout")
            app.disconnect()
            sys.exit(1)
        time.sleep(0.1)
    
    if app.account_type != "PAPER":
        print(f"✗ SAFETY FAILURE: Account type '{app.account_type}' is not PAPER")
        app.disconnect()
        sys.exit(1)
    
    print("✓ VERIFIED: Paper trading account confirmed")
    print("✓ Safe to proceed with snapshot capture\n")
    app.cancelAccountSummary(9999)
    
    snapshot_data = {
        "scenario": scenario_name,
        "timestamp": datetime.now().isoformat(),
        "symbols": {},
    }
    
    symbols = ["SPY", "QQQ", "IWM"]
    
    for symbol in symbols:
        print(f"\nCapturing data for {symbol}...")
        
        # 1. Get current stock price
        stock_contract = create_stock_contract(symbol)
        req_id = app.current_request_id
        app.current_request_id += 1
        
        print(f"  Requesting market data (reqId {req_id})...")
        app.reqMktData(req_id, stock_contract, "", True, False, [])
        time.sleep(2)  # Wait for data
        
        stock_price = app.market_data.get(req_id, {}).get("last", 0)
        if stock_price == 0:
            print(f"  ⚠ Warning: No price data for {symbol}, using fallback")
            stock_price = {"SPY": 580, "QQQ": 500, "IWM": 220}.get(symbol, 100)
        
        print(f"  ✓ Current price: ${stock_price:.2f}")
        
        # Cancel market data
        app.cancelMktData(req_id)
        
        # 2. Get historical data (1-hour bars, last 5 days RTH only)
        req_id = app.current_request_id
        app.current_request_id += 1
        
        print(f"  Requesting historical data (reqId {req_id})...")
        app.reqHistoricalData(
            req_id,
            stock_contract,
            "",  # End date (now)
            "5 D",  # Duration
            "1 hour",  # Bar size
            "TRADES",  # What to show
            1,  # RTH only
            1,  # Date format (1 = string)
            False,  # Keep up to date
            []  # Chart options
        )
        time.sleep(3)  # Wait for data
        
        historical_data = app.historical_bars.get(req_id, [])
        print(f"  ✓ Retrieved {len(historical_data)} historical bars")
        
        # 3. Get option chain for ATM strikes
        atm_strike = get_atm_strike(stock_price, symbol)
        strikes = [
            atm_strike - 2,
            atm_strike - 1,
            atm_strike,
            atm_strike + 1,
            atm_strike + 2,
        ]
        
        # Get expiries (2, 7 DTE approximations)
        expiries = get_expiry_dates([2, 7])
        
        option_data = []
        
        for expiry in expiries:
            for strike in strikes:
                for right in ["C", "P"]:
                    option_contract = create_option_contract(symbol, right, strike, expiry)
                    
                    # Request market data
                    req_id = app.current_request_id
                    app.current_request_id += 1
                    
                    app.reqMktData(req_id, option_contract, "", True, False, [])
                    time.sleep(0.5)  # Rate limit
                    
                    # Get data
                    market_data = app.market_data.get(req_id, {})
                    greeks = app.greeks_data.get(req_id, {})
                    
                    if market_data:
                        option_data.append({
                            "contract": {
                                "symbol": symbol,
                                "right": right,
                                "strike": strike,
                                "expiry": expiry,
                            },
                            "marketData": market_data,
                            "greeks": greeks,
                        })
                    
                    # Cancel market data
                    app.cancelMktData(req_id)
        
        print(f"  ✓ Captured {len(option_data)} option contracts")
        
        # Store symbol data
        snapshot_data["symbols"][symbol] = {
            "currentPrice": stock_price,
            "historicalBars": historical_data,
            "optionChain": option_data,
        }
    
    # Disconnect
    app.disconnect()
    print(f"\n✓ Snapshot capture complete\n")
    
    # Validate snapshot completeness
    validate_snapshot_completeness(snapshot_data)
    
    return snapshot_data


def save_snapshot(data: Dict, scenario_name: str):
    """Save snapshot data to JSON file.
    
    Args:
        data: Snapshot data dictionary
        scenario_name: Scenario identifier for filename
    """
    # Create output directory
    output_dir = Path("tests/fixtures/ibkr_snapshots")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{scenario_name}_{timestamp}.json"
    filepath = output_dir / filename
    
    # Save to file
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Snapshot saved to: {filepath}")
    print(f"  File size: {filepath.stat().st_size / 1024:.1f} KB")
    
    # Also create a "latest" symlink-equivalent for this scenario
    latest_path = output_dir / f"snapshot_{scenario_name}_latest.json"
    with open(latest_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Latest snapshot: {latest_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Capture IBKR market data snapshots for test fixtures"
    )
    parser.add_argument(
        "--scenario",
        default="normal",
        help="Scenario name (normal, high_vix, tight_spreads, etc.)"
    )
    
    args = parser.parse_args()
    
    # Safety check - verify we're using paper trading port
    print("\n" + "!"*60)
    print("SAFETY CHECK: This script connects to port 4002 (paper trading)")
    print("Ensure IBKR Gateway is running in PAPER TRADING mode")
    print("!"*60 + "\n")
    
    response = input("Continue with snapshot capture? (yes/no): ")
    if response.lower() not in ["yes", "y"]:
        print("Aborted.")
        sys.exit(0)
    
    try:
        # Capture snapshot
        data = capture_snapshot(args.scenario)
        
        # Save snapshot
        save_snapshot(data, args.scenario)
        
        print("\n" + "="*60)
        print("SNAPSHOT CAPTURE COMPLETE")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

### 3.2 Snapshot Directory Structure

**File:** `tests/fixtures/ibkr_snapshots/.gitkeep`

```
# This file ensures the ibkr_snapshots directory is tracked in git
# Snapshot JSON files are gitignored but the directory structure is preserved
```

---

### 3.3 Update .gitignore

**File:** `.gitignore` (append these lines)

```
# IBKR snapshot data files (keep directory structure, ignore data files)
tests/fixtures/ibkr_snapshots/*.json
!tests/fixtures/ibkr_snapshots/.gitkeep
```

---

## 4. DEPENDENCIES

### Python Imports
```python
import argparse
import json
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
```

**External Dependencies:**
- `ibapi` (already in project dependencies via Poetry)

### Infrastructure Dependencies
- **IBKR Gateway:** Must be running on port 4002 (paper trading)
- **Market Hours:** Script should run during market hours (9:30 AM - 4:00 PM ET)
- **Paper Account:** Must be configured in Gateway settings
- **Network:** Localhost connection to Gateway

---

## 5. INPUT/OUTPUT CONTRACT

### Script Invocation

**Command Line:**
```bash
# Default scenario (normal market conditions)
python scripts/capture_ibkr_snapshot.py

# Named scenario
python scripts/capture_ibkr_snapshot.py --scenario high_vix
python scripts/capture_ibkr_snapshot.py --scenario tight_spreads
python scripts/capture_ibkr_snapshot.py --scenario low_volume
```

### Output File Structure

**File:** `tests/fixtures/ibkr_snapshots/snapshot_normal_20260206_143000.json`

```json
{
  "scenario": "normal",
  "timestamp": "2026-02-06T14:30:00.123456",
  "symbols": {
    "SPY": {
      "currentPrice": 580.25,
      "historicalBars": [
        {
          "date": "20260203  09:30:00",
          "open": 578.50,
          "high": 579.00,
          "low": 578.25,
          "close": 578.75,
          "volume": 1250000,
          "wap": 578.65,
          "barCount": 15234
        }
      ],
      "optionChain": [
        {
          "contract": {
            "symbol": "SPY",
            "right": "C",
            "strike": 580.0,
            "expiry": "20260214"
          },
          "marketData": {
            "bid": 5.20,
            "ask": 5.30,
            "last": 5.25,
            "bidSize": 50,
            "askSize": 75,
            "volume": 12500
          },
          "greeks": {
            "impliedVolatility": 0.18,
            "delta": 0.52,
            "gamma": 0.03,
            "vega": 0.15,
            "theta": -0.08,
            "optionPrice": 5.25,
            "underlyingPrice": 580.25
          }
        }
      ]
    }
  }
}
```

### Data Validation

**Successful Capture Criteria:**
- All 3 symbols (SPY, QQQ, IWM) have data
- Each symbol has current price
- Historical bars: 30-40 bars (5 days × 6.5 hours × ~1 bar/hour)
- Option chain: 20 contracts per symbol (5 strikes × 2 expiries × 2 rights)
- Greeks present for most options (may be -1 for far OTM)

---

## 6. INTEGRATION POINTS

### Usage in Test Fixtures

**Loading snapshot data in tests:**

```python
# In tests/conftest.py
import json
from pathlib import Path

@pytest.fixture
def ibkr_snapshot():
    """Load real IBKR snapshot data."""
    snapshot_path = Path("tests/fixtures/ibkr_snapshots/snapshot_normal_latest.json")
    with open(snapshot_path) as f:
        return json.load(f)

@pytest.fixture
def real_spy_data(ibkr_snapshot):
    """Extract SPY data from snapshot."""
    return ibkr_snapshot["symbols"]["SPY"]
```

**Using in tests:**

```python
def test_option_pricing_with_real_data(real_spy_data):
    """Test pricing logic with real IBKR data."""
    option = real_spy_data["optionChain"][0]
    
    # Verify Greeks are realistic
    assert 0 < option["greeks"]["delta"] < 1
    assert option["greeks"]["impliedVolatility"] > 0
    
    # Test bid-ask spread validation
    spread = option["marketData"]["ask"] - option["marketData"]["bid"]
    assert spread > 0
    assert spread < 2.0  # Reasonable spread for SPY
```

---

## 7. DEFINITION OF DONE

### Code Quality Gates
- [ ] `ruff check scripts/capture_ibkr_snapshot.py` → Zero warnings
- [ ] `black scripts/capture_ibkr_snapshot.py --check` → No formatting needed
- [ ] `mypy scripts/capture_ibkr_snapshot.py` → Type checking passes
- [ ] File exists at correct path: `scripts/capture_ibkr_snapshot.py`
- [ ] Script has executable permissions: `chmod +x scripts/capture_ibkr_snapshot.py`

### Functional Validation
- [ ] Script runs without errors: `python scripts/capture_ibkr_snapshot.py --help`
- [ ] Connects to IBKR Gateway successfully (manual test during market hours)
- [ ] Captures data for all 3 symbols (SPY, QQQ, IWM)
- [ ] Saves JSON file to correct location
- [ ] JSON file structure matches specification
- [ ] .gitignore updated to exclude snapshot JSON files

### Safety Validation
- [ ] **CRITICAL:** Script hardcoded to port 4002 (paper trading)
- [ ] Script includes safety confirmation prompt
- [ ] Script displays warning about paper trading requirement
- [ ] No order placement code present (read-only operations)

### Ready for Use
- [ ] @QA_Lead approval received
- [ ] @CRO safety review approved
- [ ] File committed to version control
- [ ] Directory structure created (tests/fixtures/ibkr_snapshots/)

---

## 8. EDGE CASES & TEST SCENARIOS

### Edge Case 1: Gateway Not Running
**Scenario:** Script run when IBKR Gateway is not active  
**Expected:** Connection timeout after 10 seconds with clear error message
**Handling:** Script exits gracefully with exit code 1

### Edge Case 2: After Market Hours
**Scenario:** Script run when markets are closed  
**Expected:** Some market data may be stale/delayed, historical data still works
**Handling:** Script completes but warns about potentially stale data

### Edge Case 3: No Option Data for Strike
**Scenario:** Far OTM strikes may have no market makers  
**Expected:** Market data returns empty/zero values
**Handling:** Skip contracts with no data, continue with others

### Edge Case 4: Greeks Not Available
**Scenario:** Some option Greeks may return -1 or -2 (no data)  
**Expected:** Greeks stored as None in JSON
**Handling:** Convert sentinel values to None for cleaner JSON

### Edge Case 5: Rate Limiting
**Scenario:** Too many market data requests too quickly  
**Expected:** IBKR may throttle or reject requests
**Handling:** 0.5 second delay between option requests, timeout handling

### Edge Case 6: Contract Not Found
**Scenario:** Expiry date might not have options (holiday, etc.)  
**Expected:** Error code 200 "No security definition found"
**Handling:** Log warning, skip contract, continue with others

### Edge Case 7: Network Interruption
**Scenario:** Connection drops mid-capture  
**Expected:** API callbacks stop arriving
**Handling:** Timeout detection, partial data saved, clear error message

### Edge Case 8: Disk Space Full
**Scenario:** Cannot write JSON file  
**Expected:** IOError when saving file
**Handling:** Catch exception, display error, exit with code 1

---

## 9. ROLLBACK PLAN

### If Snapshot Script Causes Issues

**Rollback Steps:**
1. Delete `scripts/capture_ibkr_snapshot.py`
2. Remove `tests/fixtures/ibkr_snapshots/` directory (keep .gitkeep if desired)
3. Remove snapshot-related entries from `.gitignore`
4. Fall back to synthetic test data from fixtures

**No Production Impact:** This is a development/testing utility script with no runtime dependencies in production code.

### Temporary Disable
```bash
# Rename script to prevent accidental execution
mv scripts/capture_ibkr_snapshot.py scripts/capture_ibkr_snapshot.py.disabled
```

---

## 10. QUALITY VALIDATION COMMANDS

Run these commands in sequence to validate the implementation:

```bash
# 1. Verify file exists and has correct permissions
ls -la scripts/capture_ibkr_snapshot.py

# 2. Make executable (if needed)
chmod +x scripts/capture_ibkr_snapshot.py

# 3. Syntax and style check
ruff check scripts/capture_ibkr_snapshot.py

# 4. Code formatting validation
black scripts/capture_ibkr_snapshot.py --check

# 5. Type checking
mypy scripts/capture_ibkr_snapshot.py

# 6. Verify directory structure
ls -la tests/fixtures/ibkr_snapshots/

# 7. Test script help output
python scripts/capture_ibkr_snapshot.py --help

# 8. Verify .gitignore updated
grep -A 2 "IBKR snapshot" .gitignore
```

**Expected Results:**
- `ls`: File exists, ~15-20KB size, executable permissions
- `ruff`: No warnings or errors
- `black`: "All done! ✨ 🍰 ✨" with no files changed
- `mypy`: "Success: no issues found"
- Directory: exists with .gitkeep file
- Help: Displays usage information
- .gitignore: Contains snapshot exclusion rules

### Manual Testing (During Market Hours)

**ONLY IF IBKR Gateway is running in paper trading mode:**

```bash
# Test connection and capture (aborts before actual capture)
python scripts/capture_ibkr_snapshot.py
# Type "no" at the safety prompt to abort

# Full capture test (REQUIRES MARKET HOURS + PAPER TRADING GATEWAY)
python scripts/capture_ibkr_snapshot.py --scenario test
# Type "yes" to confirm
# Wait for completion (~60-90 seconds)
# Verify JSON file created in tests/fixtures/ibkr_snapshots/
```

---

## 11. FOLLOW-UP TASKS

### Immediate Next Steps (Chunk 6)
1. **Run snapshot capture:** Execute script during market hours to collect real data
2. **Capture multiple scenarios:**
   - Normal market conditions
   - High VIX day
   - Tight spreads (low volatility)
3. **Validate snapshot quality:** Verify data completeness and realism
4. **Update fixtures:** Use snapshot data in conftest.py fixtures

### Future Enhancements (Post-Phase 1)
- Add VIX contract snapshot capture
- Add volume profile analysis to snapshots
- Implement automatic scenario detection (detect high VIX, wide spreads automatically)
- Add snapshot comparison tool to detect market regime changes
- Schedule automatic snapshot capture (cron job during market hours)
- Add snapshot validation rules (missing data detection, outlier detection)

---

## 12. SAFETY REVIEW REQUIREMENTS

**@CRO APPROVAL REQUIRED** before implementation.

### Safety Checklist

**Connection Safety:**
- [ ] Script hardcoded to port 4002 (paper trading port)
- [ ] No command-line option to override port
- [ ] No environment variable to change port
- [ ] Connection string explicitly shows "paper trading" in logs
- [ ] **CRO CONDITION 1:** Account type verification implemented
- [ ] **CRO CONDITION 1:** Script verifies AccountType == "PAPER" after connection
- [ ] **CRO CONDITION 1:** Script aborts if account type is not PAPER
- [ ] **CRO CONDITION 2:** Connection metadata logging (managedAccounts callback)

**Operation Safety:**
- [ ] Script performs ONLY read operations (market data requests)
- [ ] NO order placement code present
- [ ] NO account modification code present
- [ ] NO position modification code present

**User Confirmation:**
- [ ] Safety warning displayed before connection
- [ ] User must type "yes" to proceed
- [ ] Warning emphasizes paper trading requirement

**Data Quality:**
- [ ] **CRO CONDITION 3:** Snapshot completeness validation implemented
- [ ] Validates minimum historical bars per symbol
- [ ] Validates minimum option contracts per symbol
- [ ] Validates Greeks data presence
- [ ] Warns if snapshot incomplete

**Error Handling:**
- [ ] Connection failures exit gracefully
- [ ] Account type verification timeout handled
- [ ] Partial data scenarios handled safely
- [ ] No silent failures that could mask issues

---

## 13. COPILOT-READY PROMPT

**Copy this section to VSCode Copilot Chat:**

```
Create scripts/capture_ibkr_snapshot.py - a standalone script to capture real IBKR market data snapshots for test fixtures.

CRITICAL SAFETY REQUIREMENTS (CRO MANDATED):
- Script must ONLY connect to port 4002 (paper trading)
- Must implement account type verification AFTER connection
- Must call reqAccountSummary(9999, "All", "AccountType") immediately after connection
- Must verify AccountType == "PAPER" before any data requests
- Must disconnect and exit(1) if account type is not PAPER
- Must display safety warning before connecting
- Must require user confirmation to proceed
- NO order placement code - read-only operations only

IMPLEMENTATION REQUIREMENTS:
1. Create file at: scripts/capture_ibkr_snapshot.py
2. Make file executable with shebang: #!/usr/bin/env python3

3. Implement SnapshotCapture class with callbacks:
   - nextValidId() - connection established
   - managedAccounts() - log connected accounts (AUDIT TRAIL)
   - accountSummary() - CRITICAL: verify AccountType == "PAPER", abort if not
   - accountSummaryEnd() - account summary complete
   - error() - error handling
   - contractDetails(), contractDetailsEnd() - contract data
   - historicalData(), historicalDataEnd() - historical bars
   - tickPrice(), tickSize() - market data
   - tickOptionComputation() - Greeks

4. Capture sequence for SPY, QQQ, IWM:
   - Connect to port 4002
   - Verify account type is PAPER (MANDATORY - exits if not)
   - For each symbol:
     * Current stock price (reqMktData with snapshot=True)
     * Historical bars: 5 days, 1-hour, RTH only (reqHistoricalData)
     * Option chain: 5 ATM strikes, 2 expiries (~2DTE, ~7DTE), calls and puts
     * Market data: bid, ask, last, sizes, volume
     * Greeks: IV, delta, gamma, vega, theta

5. Implement validate_snapshot_completeness() function:
   - Check each symbol has current price
   - Check minimum 20 historical bars per symbol
   - Check minimum 10 option contracts per symbol
   - Check at least some options have Greeks
   - Warn if validation fails

6. Save to JSON: tests/fixtures/ibkr_snapshots/snapshot_{scenario}_{timestamp}.json
7. Command-line argument: --scenario (default: "normal")
8. Safety prompt before connecting (user must type "yes")
9. Comprehensive error handling and logging

ALSO CREATE:
- tests/fixtures/ibkr_snapshots/.gitkeep (empty file to track directory)
- Update .gitignore to exclude *.json in ibkr_snapshots/ but keep .gitkeep

VALIDATION:
After implementation:
- chmod +x scripts/capture_ibkr_snapshot.py
- ruff check scripts/capture_ibkr_snapshot.py
- black scripts/capture_ibkr_snapshot.py --check
- mypy scripts/capture_ibkr_snapshot.py
- python scripts/capture_ibkr_snapshot.py --help (should display usage)
- Verify account type verification is present in code

All should pass with zero issues.
```

---

**Document Status:** ✅ Ready for Implementation (CRO CONDITIONS INCORPORATED)  
**Approvals Required:** @CRO (final approval after revision), @QA_Lead (quality review)  
**Next Action:** @CRO final approval, then Factory Floor implementation  

---

**REVISION HISTORY:**

**Rev 1.1 (2026-02-06):** Incorporated @CRO mandatory safety conditions
- Added account type verification (Condition 1 - MANDATORY)
- Added connection metadata logging (Condition 2 - MANDATORY)
- Added snapshot completeness validation (Condition 3 - RECOMMENDED)
- Updated safety checklist with CRO requirements
- Updated Copilot prompt with verification steps

**Rev 1.0 (2026-02-06):** Initial specification

---

*@Systems_Architect revision complete. Document now includes all @CRO mandatory safety conditions and is ready for final approval.*
