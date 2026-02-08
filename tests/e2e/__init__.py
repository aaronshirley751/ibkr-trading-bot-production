"""
End-to-end tests for complete trading workflows.

E2E tests validate the full orchestration path with all real components
wired together (except the actual IBKR Gateway, which remains mocked).

Implemented test files:
- test_daily_gameplan_ingestion.py — Gameplan loading, validation, parameter application
- test_full_trade_cycle.py — Complete trade lifecycle across all layers
- test_safety_scenarios.py — Safety mechanism enforcement under failure conditions

Tests using existing strategy/broker components are FUNCTIONAL.
Tests requiring the Phase 2 TradingOrchestrator are marked @pytest.mark.skip.
"""
