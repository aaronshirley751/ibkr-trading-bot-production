"""
End-to-end tests for complete workflows.

E2E tests validate:
- Full trading cycle (signal
 order
 execution
 tracking)
- Daily gameplan ingestion and application
- Multi-symbol scenarios
- Safety mechanism triggers

Use IBKR snapshot data, moderate speed (<30 seconds per test).
"""
