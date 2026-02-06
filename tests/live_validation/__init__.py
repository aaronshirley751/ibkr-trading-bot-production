"""
Live validation tests for pre-deployment checks.

WARNING: These tests connect to real IBKR Gateway.
- NOT run in CI/CD (manual execution only)
- Require IBKR Gateway running (localhost:4002)
- Require market hours for market data tests
- Paper trading only (no live orders)

Run before paper to live deployment transitions.
"""
