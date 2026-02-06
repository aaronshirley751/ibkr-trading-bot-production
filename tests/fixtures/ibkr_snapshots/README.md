# IBKR Snapshot Fixtures

## Status: PLACEHOLDER DATA

**Current snapshots are synthetic placeholders created 2026-02-06 for test infrastructure development.**

These files contain realistic structure matching actual IBKR API responses but do NOT contain real market data.

---

## Replacement Required: Monday 2026-02-09, 9:30 AM ET

### Instructions for Capturing Real IBKR Data

**Prerequisites:**
- IBKR Gateway running (paper trading mode, port 4002)
- Market hours: 9:30 AM - 4:00 PM ET (RTH)
- Paper trading accounts receive free real-time data during RTH

**Command:**
```bash
# Run from repository root
poetry run python scripts/capture_ibkr_snapshot.py --symbols SPY QQQ IWM
```

**Expected Duration:** 5-10 minutes

**Expected Output:**
- `spy_YYYYMMDD_HHMM_[regime]_vix.json`
- `qqq_YYYYMMDD_HHMM_[regime]_vix.json`
- `iwm_YYYYMMDD_HHMM_[regime]_vix.json`

**After Capture:**
```bash
# Delete placeholder files
rm tests/fixtures/ibkr_snapshots/*_PLACEHOLDER.json

# Commit real snapshots
git add tests/fixtures/ibkr_snapshots/
git commit -m "Replace placeholder snapshots with real IBKR data captured during RTH"
git push origin main
```

---

## File Structure

Each snapshot contains:
- **metadata**: Capture timestamp, VIX level, regime classification, symbol info
- **underlying**: Stock price, bid/ask, volume
- **option_chain**: Array of option contracts with market data and Greeks
  - 5 strikes (2 OTM, ATM, 2 ITM)
  - 3 expiries (2 DTE, 5 DTE, 7 DTE)
  - Both calls and puts
- **historical_bars**: 60 1-minute bars (OHLCV + VWAP)

---

## Snapshot Scenarios Needed

**Priority 0 (Critical):**
- Normal regime (VIX 15-18) - SPY, QQQ, IWM ✅ PLACEHOLDER
- Elevated regime (VIX 22-25) - SPY ⏳ PENDING

**Priority 1 (Important):**
- High volatility (VIX 28-32) - SPY ⏳ PENDING

**Priority 2 (Nice-to-have):**
- Pre-market (8:00 AM ET) - SPY ⏳ PENDING
- Close approach (3:45 PM ET) - SPY ⏳ PENDING

---

## Troubleshooting

**If snapshot capture fails with "Failed to get valid price":**

1. **Verify market hours:** Must be 9:30 AM - 4:00 PM ET
2. **Check Gateway connection:** `netstat -an | findstr "4002"` (Windows) or `ss -tln | grep 4002` (Linux)
3. **Verify paper trading account:** Check TWS login shows "Paper Trading" mode
4. **Check for delayed data config:** During RTH, paper accounts should receive live data automatically

**If issues persist:**
- Capture during mid-day (12:00-1:00 PM ET) for peak liquidity
- Try single symbol first: `poetry run python scripts/capture_ibkr_snapshot.py --symbols SPY`
- Check IBKR Gateway logs for error messages

---

**Last Updated:** 2026-02-06
**Status:** PLACEHOLDER - Real capture scheduled for 2026-02-09 9:30 AM ET
