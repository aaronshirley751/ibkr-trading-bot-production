# Live Validation Test Suite

## Purpose

Pre-deployment validation tests that connect to real IBKR Gateway to verify:
- API connectivity and authentication
- Market data retrieval (real-time during RTH)
- Order submission (paper trading only)
- Contract qualification
- Position tracking

## Usage

**Prerequisites:**
- IBKR Gateway running (localhost:4002)
- Paper trading mode
- Market hours: 9:30 AM - 4:00 PM ET (for market data tests)

**Run Tests:**
```bash
# All live validation tests
poetry run pytest tests/live_validation/ -v

# Specific test file
poetry run pytest tests/live_validation/test_gateway_connectivity.py -v
```

## Important Notes

- **NOT run in CI/CD** - These tests are excluded from automated pipelines
- **Manual execution only** - Run before deployments
- **Paper trading only** - Never submit live orders
- **Market hours required** - Some tests need RTH for market data

## Test Files

- `test_gateway_connectivity.py` - Basic connection and authentication
- `test_real_market_data.py` - Real-time market data retrieval
- `test_real_order_submission.py` - Paper trading order submission

## Troubleshooting

**If tests fail:**
1. Verify Gateway running: `netstat -an | findstr "4002"` (Windows) or `ss -tln | grep 4002` (Linux)
2. Check paper trading mode in TWS
3. Verify market hours (9:30-4:00 PM ET) for data tests
4. Check IBKR Gateway logs for errors

## Deployment Checklist

Before paper to live transition:
- [ ] All live validation tests pass
- [ ] Paper trading orders execute correctly
- [ ] Position tracking accurate
- [ ] Discord notifications working
- [ ] Raspberry Pi deployment validated
