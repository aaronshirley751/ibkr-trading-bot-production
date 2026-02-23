"""
Orchestration module for zero-touch startup automation.

This module provides:
- StartupOrchestrator: Main orchestration state machine
- OrchestrationConfig: Configuration management
- Gateway health validation and lifecycle management

Usage:
    poetry run python -m src.orchestration.startup

The orchestrator is the single entry point for production operations,
coordinating Gateway startup, health validation, gameplan loading,
and bot initialization.
"""

from src.orchestration.config import OrchestrationConfig
from src.orchestration.health import GatewayHealthChecker
from src.orchestration.startup import StartupOrchestrator, StartupState

__all__ = [
    "OrchestrationConfig",
    "GatewayHealthChecker",
    "StartupOrchestrator",
    "StartupState",
]
