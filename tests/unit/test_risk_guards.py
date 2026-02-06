"""
Unit tests for risk management guards and circuit breakers.

Tests cover:
- Daily loss limit enforcement (10% / $60)
- Weekly drawdown governor (15% triggers Strategy C)
- Stop-loss calculation (25% for A, 15% for B)
- Force-close logic at 3 DTE
- Gap-down scenario handling

CRITICAL: This module requires @CRO sign-off before deployment.
Coverage target: 98% (highest standard)
"""

# TODO: Implement tests in Task 1.1.5
