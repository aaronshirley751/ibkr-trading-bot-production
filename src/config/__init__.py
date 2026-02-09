"""
Configuration module.

Provides centralized configuration for the trading system.
"""

from src.config.risk_config import RiskConfig, DEFAULT_RISK_CONFIG

__all__ = [
    "RiskConfig",
    "DEFAULT_RISK_CONFIG",
]
