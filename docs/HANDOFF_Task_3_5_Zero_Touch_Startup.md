# VSC HANDOFF: Zero-Touch Startup Sequence

## Header Block

| Field | Value |
|-------|-------|
| **Task ID** | 3.5 (Guw8I8Q4wk2gQfIZQ9X8wmUAIMUV) |
| **Date** | 2026-02-10 |
| **Revision** | 1.0 |
| **Requested By** | Phase 3 Sprint / Operator Authorization |
| **Lead Personas** | @Systems_Architect, @DevOps |
| **Supporting Personas** | @CRO (safety validation), @QA_Lead (test specifications) |
| **Model Routing** | **Opus (MANDATORY)** â€” Complex orchestration, multiple failure modes, extended thinking required |
| **Context Budget** | Heavy (~10K input + 4K output) â€” Recommend fresh chat |
| **Board** | IBKR Project Management |
| **Priority** | URGENT |

---

## Context Summary

**What Exists (Phase 3 Completed Work):**
- âœ… Gateway deployed via Docker Compose (Task 3.1)
- âœ… Gateway startup orchestration with health checks (Task 3.2)
- âœ… External health monitoring system (Task 3.3)
- âœ… Docker Compose multi-container orchestration (Task 3.4)
- âœ… TWS API authentication timeout resolved (Task 3.4.1)

**Current State:**
- Gateway can start automatically via `docker compose up -d`
- Bot must be started manually by operator
- Bot validates Gateway readiness at startup (Phase 3.2 logic)
- Health monitoring runs independently

**The Gap:**
Task 3.5 is the **capstone automation task** that ties everything together into a hands-free production workflow. The operator should be able to walk away from the desktop, and the system should:
1. Start Gateway container
2. Wait for Gateway authentication
3. Validate health checks
4. Start bot with validated configuration
5. Handle failures gracefully
6. Alert operator only when manual intervention is required

**Deployment Target:**
- **Primary:** Windows 11 Desktop (Docker Desktop with WSL2)
- **Future:** Ubuntu Server 24.04 rackmount (Docker Engine on bare metal)
- **Requirement:** Same orchestration code works on both platforms

---

# AGENT EXECUTION BLOCK

---

## 1. Objective

Implement the **Startup Orchestrator** â€” a Python module that coordinates the complete zero-touch startup sequence for production trading operations. This orchestrator:

1. **Validates prerequisites** before attempting startup
2. **Launches Gateway container** if not already running
3. **Waits for Gateway authentication** with timeout and retry logic
4. **Validates health checks** before proceeding
5. **Starts bot** with validated gameplan configuration
6. **Handles failures** with appropriate fallback strategies
7. **Sends alerts** to operator via Discord at decision points
8. **Enables production deployment** with no manual intervention

**Key Principle:** The orchestrator is the **single entry point** for production operations. Operator never manually starts Gateway or bot â€” orchestrator handles everything.

---

## 2. Architecture Decision: Orchestrator as Separate Module

**Design Choice:** The orchestrator is a **standalone module** (`src/orchestration/startup.py`), not integrated into the bot's main entry point.

**Rationale:**
- **Separation of concerns:** Startup coordination vs. trading logic
- **Independent testing:** Can test orchestration without running full bot
- **Flexible deployment:** Can be invoked by systemd, cron, or Windows Task Scheduler
- **Error isolation:** Orchestrator failures don't corrupt bot state
- **Future extensibility:** Can add shutdown orchestration, health coordination, etc.

**Invocation Patterns:**

```bash
# Development (manual invocation)
poetry run python -m src.orchestration.startup

# Production (systemd on Linux)
ExecStart=/path/to/poetry run python -m src.orchestration.startup

# Production (Windows Task Scheduler)
wsl -d Ubuntu poetry run python -m src.orchestration.startup
```

---

## 3. File Structure

**New Files to Create:**

```
src/
â”œâ”€â”€ orchestration/
â”‚   â”œâ”€â”€ __init__.py                    # Module initialization
â”‚   â”œâ”€â”€ startup.py                     # Main orchestrator (THIS TASK)
â”‚   â”œâ”€â”€ config.py                      # Orchestration configuration
â”‚   â””â”€â”€ health.py                      # Gateway health validation (reuse from Task 3.2)
â”œâ”€â”€ notifications/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ discord.py                     # Discord webhook alerts
â””â”€â”€ main.py                            # Bot entry point (MODIFIED â€” validate prerequisites)

tests/
â”œâ”€â”€ orchestration/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ test_startup_orchestrator.py   # Orchestration logic tests
â”‚   â”œâ”€â”€ test_gateway_health.py         # Gateway validation tests
â”‚   â””â”€â”€ test_failure_recovery.py       # Failure scenario tests
â””â”€â”€ integration/
    â””â”€â”€ test_zero_touch_startup.py     # E2E startup flow test

docker/
â””â”€â”€ gateway/
    â”œâ”€â”€ docker-compose.yml             # MODIFIED â€” add orchestrator service (optional)
    â””â”€â”€ scripts/
        â””â”€â”€ production-startup.sh      # Wrapper for production deployment
```

**Files to Modify:**
- `src/main.py` â€” Add prerequisite validation (orchestrator already started?)
- `docker/gateway/docker-compose.yml` â€” Optional: Add orchestrator as service

---

## 4. Startup Sequence State Machine

The orchestrator implements a **state machine** with clear transitions and failure modes:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   INITIALIZING  â”‚ â† Entry point
â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â”œâ”€â”€â–º Validate environment
         â”œâ”€â”€â–º Load configuration
         â”œâ”€â”€â–º Check Docker availability
         â”‚
         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ GATEWAY_STARTINGâ”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â”œâ”€â”€â–º Check if Gateway container exists
         â”œâ”€â”€â–º If not running â†’ docker compose up -d gateway
         â”œâ”€â”€â–º If already running â†’ proceed to validation
         â”‚
         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ GATEWAY_WAITING â”‚ â† Polling loop with timeout
â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â”œâ”€â”€â–º Poll Gateway health endpoint (localhost:4002)
         â”œâ”€â”€â–º Check Docker container health status
         â”œâ”€â”€â–º Wait for "healthy" state
         â”œâ”€â”€â–º Timeout: 120 seconds (configurable)
         â”œâ”€â”€â–º Retry interval: 5 seconds
         â”‚
         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ GATEWAY_VALIDATEDâ”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â”œâ”€â”€â–º Confirm API port responding
         â”œâ”€â”€â–º Confirm Docker health check passing
         â”œâ”€â”€â–º Optional: Validate authentication status via TWS API handshake
         â”‚
         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ GAMEPLAN_LOADINGâ”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â”œâ”€â”€â–º Check if gameplan JSON exists
         â”œâ”€â”€â–º Validate gameplan schema
         â”œâ”€â”€â–º If data_quarantine = true â†’ Force Strategy C
         â”œâ”€â”€â–º If no gameplan â†’ Alert operator, deploy Strategy C
         â”‚
         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   BOT_STARTING  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â”œâ”€â”€â–º Invoke bot main.py with validated config
         â”œâ”€â”€â–º Pass Gateway connection parameters
         â”œâ”€â”€â–º Pass gameplan path
         â”œâ”€â”€â–º Set log level
         â”‚
         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   BOT_RUNNING   â”‚ â† Orchestrator hands off to bot
â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â”œâ”€â”€â–º Orchestrator exits with SUCCESS
         â”œâ”€â”€â–º Bot assumes control
         â”œâ”€â”€â–º Health monitoring (Task 3.3) continues independently
         â”‚
         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚    SUCCESS      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

FAILURE PATHS:
â”œâ”€â–º GATEWAY_TIMEOUT      â†’ Alert operator, exit FAILURE
â”œâ”€â–º GATEWAY_UNHEALTHY    â†’ Attempt restart (1x), then alert
â”œâ”€â–º GAMEPLAN_INVALID     â†’ Deploy Strategy C, alert
â”œâ”€â–º GAMEPLAN_MISSING     â†’ Deploy Strategy C, alert
â”œâ”€â–º BOT_START_FAILED     â†’ Alert operator, exit FAILURE
â””â”€â–º DOCKER_UNAVAILABLE   â†’ Alert operator, exit FAILURE
```

**Critical Design Points:**

1. **No infinite retries:** Orchestrator attempts Gateway restart once. If that fails, human intervention required.
2. **Strategy C failover:** Invalid/missing gameplan â†’ automatic Strategy C deployment (zero trading, alert-only mode).
3. **Timeout enforcement:** Gateway must become healthy within 120 seconds. If not, assume failure.
4. **Idempotency:** Running orchestrator twice in a row should be safe (detect already-running components).
5. **Exit codes:** Clear exit codes for systemd/cron monitoring (0 = success, 1 = failure, 2 = partial success).

---

## 5. Detailed Logic Flow (Pseudo-code)

### 5.1 Main Orchestrator Entry Point

```python
# src/orchestration/startup.py

import sys
import time
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from src.orchestration.config import OrchestrationConfig
from src.orchestration.health import GatewayHealthChecker
from src.notifications.discord import DiscordNotifier
from src.gameplan.loader import load_gameplan, validate_gameplan_schema


class StartupState(Enum):
    INITIALIZING = "initializing"
    GATEWAY_STARTING = "gateway_starting"
    GATEWAY_WAITING = "gateway_waiting"
    GATEWAY_VALIDATED = "gateway_validated"
    GAMEPLAN_LOADING = "gameplan_loading"
    BOT_STARTING = "bot_starting"
    BOT_RUNNING = "bot_running"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class StartupContext:
    """Tracks orchestration state across transitions."""
    state: StartupState
    gateway_healthy: bool = False
    gateway_restart_attempted: bool = False
    gameplan_path: Optional[Path] = None
    gameplan_valid: bool = False
    error_message: Optional[str] = None


class StartupOrchestrator:
    """
    Zero-touch startup coordinator for production trading operations.

    Responsibilities:
    - Gateway lifecycle management
    - Health validation
    - Gameplan validation
    - Bot initialization
    - Failure recovery
    - Operator notifications
    """

    def __init__(self, config: OrchestrationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.notifier = DiscordNotifier(config.discord_webhook_url)
        self.health_checker = GatewayHealthChecker(
            host=config.gateway_host,
            port=config.gateway_port,
            timeout=config.health_check_timeout
        )
        self.context = StartupContext(state=StartupState.INITIALIZING)

    def run(self) -> int:
        """
        Execute complete startup sequence.

        Returns:
            Exit code: 0 = success, 1 = failure, 2 = partial success (Strategy C deployed)
        """
        try:
            self.logger.info("Starting zero-touch orchestration")
            self.notifier.send_info("ðŸš€ Starting trading system startup")

            # State machine execution
            while self.context.state not in [StartupState.SUCCESS, StartupState.FAILURE]:
                self._transition()

            if self.context.state == StartupState.SUCCESS:
                self.logger.info("Startup orchestration complete â€” bot running")
                self.notifier.send_info("âœ… Trading system operational")
                return 0
            else:
                self.logger.error(f"Startup failed: {self.context.error_message}")
                self.notifier.send_critical(f"âŒ Startup failed: {self.context.error_message}")
                return 1

        except Exception as e:
            self.logger.exception("Unexpected orchestration failure")
            self.notifier.send_critical(f"ðŸ’¥ Orchestrator crashed: {str(e)}")
            return 1

    def _transition(self):
        """Execute next state transition."""
        transitions = {
            StartupState.INITIALIZING: self._initialize,
            StartupState.GATEWAY_STARTING: self._start_gateway,
            StartupState.GATEWAY_WAITING: self._wait_for_gateway,
            StartupState.GATEWAY_VALIDATED: self._validate_gateway,
            StartupState.GAMEPLAN_LOADING: self._load_gameplan,
            StartupState.BOT_STARTING: self._start_bot,
            StartupState.BOT_RUNNING: self._finalize,
        }

        handler = transitions.get(self.context.state)
        if handler:
            handler()
        else:
            raise RuntimeError(f"No handler for state: {self.context.state}")


def main():
    """CLI entry point for orchestrator."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    config = OrchestrationConfig.from_env()
    orchestrator = StartupOrchestrator(config)
    exit_code = orchestrator.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

### 5.2 State: INITIALIZING

```python
def _initialize(self):
    """Validate prerequisites before attempting startup."""
    self.logger.info("Validating startup prerequisites")

    # Check 1: Docker available?
    if not self._docker_available():
        self.context.state = StartupState.FAILURE
        self.context.error_message = "Docker not available (is Docker Desktop running?)"
        return

    # Check 2: Gameplan path configured?
    gameplan_path = self.config.gameplan_path
    if not gameplan_path or not gameplan_path.exists():
        self.logger.warning(f"Gameplan not found at {gameplan_path} â€” will deploy Strategy C")
        # Don't fail â€” we can proceed with Strategy C
    else:
        self.context.gameplan_path = gameplan_path

    # Check 3: Discord webhook configured?
    if not self.config.discord_webhook_url:
        self.logger.warning("Discord webhook not configured â€” alerts will be logged only")

    # Check 4: Already running?
    if self._bot_already_running():
        self.context.state = StartupState.FAILURE
        self.context.error_message = "Bot already running (check process list)"
        return

    self.logger.info("Prerequisites validated â€” proceeding to Gateway startup")
    self.context.state = StartupState.GATEWAY_STARTING

def _docker_available(self) -> bool:
    """Check if Docker CLI is available and responding."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def _bot_already_running(self) -> bool:
    """Check if bot process already exists."""
    import psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'src.main' in ' '.join(cmdline):
                self.logger.warning(f"Bot already running (PID {proc.info['pid']})")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False
```

### 5.3 State: GATEWAY_STARTING

```python
def _start_gateway(self):
    """Ensure Gateway container is running."""
    self.logger.info("Checking Gateway container status")

    import subprocess

    # Check if container exists and is running
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=ibkr-gateway", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "Up" in result.stdout:
            self.logger.info("Gateway container already running")
            self.context.state = StartupState.GATEWAY_WAITING
            return
    except subprocess.TimeoutExpired:
        self.context.state = StartupState.FAILURE
        self.context.error_message = "Docker command timed out"
        return

    # Container not running â€” start it
    self.logger.info("Starting Gateway container")
    self.notifier.send_info("ðŸ”§ Starting IBKR Gateway")

    try:
        compose_dir = self.config.docker_compose_dir
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "gateway"],
            cwd=compose_dir,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            self.context.state = StartupState.FAILURE
            self.context.error_message = f"Gateway container start failed: {result.stderr}"
            return

        self.logger.info("Gateway container started â€” waiting for health")
        self.context.state = StartupState.GATEWAY_WAITING

    except subprocess.TimeoutExpired:
        self.context.state = StartupState.FAILURE
        self.context.error_message = "Gateway container start timed out (>60s)"
```

### 5.4 State: GATEWAY_WAITING

```python
def _wait_for_gateway(self):
    """Poll Gateway until healthy or timeout."""
    self.logger.info("Waiting for Gateway to become healthy")

    timeout = self.config.gateway_health_timeout  # Default: 120 seconds
    retry_interval = self.config.gateway_health_retry_interval  # Default: 5 seconds
    max_attempts = timeout // retry_interval

    for attempt in range(1, max_attempts + 1):
        self.logger.debug(f"Gateway health check attempt {attempt}/{max_attempts}")

        # Check 1: Docker health status
        docker_healthy = self._check_docker_health()

        # Check 2: API port responding
        api_responsive = self.health_checker.check_api_port()

        if docker_healthy and api_responsive:
            self.logger.info(f"Gateway healthy after {attempt * retry_interval}s")
            self.context.gateway_healthy = True
            self.context.state = StartupState.GATEWAY_VALIDATED
            return

        if attempt < max_attempts:
            time.sleep(retry_interval)

    # Timeout reached â€” attempt recovery
    self.logger.warning("Gateway health timeout â€” attempting recovery")
    if not self.context.gateway_restart_attempted:
        self.context.gateway_restart_attempted = True
        self._restart_gateway()
        self.context.state = StartupState.GATEWAY_WAITING  # Retry wait loop
    else:
        self.context.state = StartupState.FAILURE
        self.context.error_message = "Gateway failed to become healthy (timeout + restart failed)"

def _check_docker_health(self) -> bool:
    """Check Docker container health status."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", "ibkr-gateway"],
            capture_output=True,
            text=True,
            timeout=5
        )
        health = result.stdout.strip()
        return health == "healthy"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False

def _restart_gateway(self):
    """Attempt Gateway container restart (one-time recovery)."""
    self.logger.warning("Attempting Gateway restart (auto-recovery)")
    self.notifier.send_warning("âš ï¸ Gateway not responding â€” attempting restart")

    import subprocess
    try:
        compose_dir = self.config.docker_compose_dir
        result = subprocess.run(
            ["docker", "compose", "restart", "gateway"],
            cwd=compose_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            self.logger.info("Gateway restart command succeeded â€” waiting for health")
        else:
            self.logger.error(f"Gateway restart failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        self.logger.error("Gateway restart timed out")
```

### 5.5 State: GATEWAY_VALIDATED

```python
def _validate_gateway(self):
    """Final Gateway validation before bot startup."""
    self.logger.info("Performing final Gateway validation")

    # Validation 1: API port responding
    if not self.health_checker.check_api_port():
        self.context.state = StartupState.FAILURE
        self.context.error_message = "Gateway API port not responding (validation failed)"
        return

    # Validation 2: Docker health check
    if not self._check_docker_health():
        self.context.state = StartupState.FAILURE
        self.context.error_message = "Gateway Docker health check failed (validation failed)"
        return

    # Optional Validation 3: TWS API handshake (if implemented)
    # This would use Phase 2's IBKRConnection to confirm Gateway is fully authenticated
    # Deferred to future enhancement if needed

    self.logger.info("Gateway validation passed â€” proceeding to gameplan")
    self.context.state = StartupState.GAMEPLAN_LOADING
```

### 5.6 State: GAMEPLAN_LOADING

```python
def _load_gameplan(self):
    """Load and validate daily gameplan JSON."""
    self.logger.info("Loading daily gameplan")

    # Case 1: No gameplan path configured
    if not self.context.gameplan_path:
        self.logger.warning("No gameplan configured â€” deploying Strategy C")
        self.notifier.send_warning("âš ï¸ No gameplan found â€” Strategy C deployed")
        self._deploy_strategy_c()
        return

    # Case 2: Gameplan file missing
    if not self.context.gameplan_path.exists():
        self.logger.warning(f"Gameplan file not found: {self.context.gameplan_path}")
        self.notifier.send_warning(f"âš ï¸ Gameplan missing â€” Strategy C deployed")
        self._deploy_strategy_c()
        return

    # Case 3: Load and validate gameplan
    try:
        gameplan = load_gameplan(self.context.gameplan_path)

        # Schema validation
        if not validate_gameplan_schema(gameplan):
            self.logger.error("Gameplan schema validation failed")
            self.notifier.send_error("âŒ Invalid gameplan schema â€” Strategy C deployed")
            self._deploy_strategy_c()
            return

        # Data quarantine check
        if gameplan.get("data_quality", {}).get("quarantine_active", False):
            self.logger.warning("Data quarantine active â€” forcing Strategy C")
            self.notifier.send_warning("âš ï¸ Data quarantine â€” Strategy C enforced")
            self._deploy_strategy_c()
            return

        self.logger.info(f"Gameplan loaded: Strategy {gameplan['strategy']}")
        self.context.gameplan_valid = True
        self.context.state = StartupState.BOT_STARTING

    except Exception as e:
        self.logger.exception("Gameplan loading failed")
        self.notifier.send_error(f"âŒ Gameplan error: {str(e)} â€” Strategy C deployed")
        self._deploy_strategy_c()

def _deploy_strategy_c(self):
    """Create emergency Strategy C gameplan."""
    from src.gameplan.generator import generate_strategy_c

    strategy_c_path = self.config.emergency_gameplan_path
    generate_strategy_c(output_path=strategy_c_path)

    self.logger.info(f"Strategy C gameplan generated: {strategy_c_path}")
    self.context.gameplan_path = strategy_c_path
    self.context.gameplan_valid = True
    self.context.state = StartupState.BOT_STARTING
```

### 5.7 State: BOT_STARTING

```python
def _start_bot(self):
    """Launch bot process with validated configuration."""
    self.logger.info("Starting trading bot")
    self.notifier.send_info("ðŸ¤– Starting trading bot")

    import subprocess

    # Build bot command
    cmd = [
        "poetry", "run", "python", "-m", "src.main",
        "--gateway-host", self.config.gateway_host,
        "--gateway-port", str(self.config.gateway_port),
        "--gameplan", str(self.context.gameplan_path),
        "--log-level", self.config.bot_log_level
    ]

    try:
        # Start bot as background process
        # Orchestrator does NOT wait for bot to finish â€” it hands off control
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Give bot 5 seconds to crash on startup errors
        time.sleep(5)

        if process.poll() is not None:
            # Bot exited immediately â€” startup failed
            stderr = process.stderr.read()
            self.context.state = StartupState.FAILURE
            self.context.error_message = f"Bot startup failed: {stderr}"
            return

        self.logger.info(f"Bot started successfully (PID {process.pid})")
        self.context.state = StartupState.BOT_RUNNING

    except Exception as e:
        self.context.state = StartupState.FAILURE
        self.context.error_message = f"Bot start failed: {str(e)}"
```

### 5.8 State: BOT_RUNNING & SUCCESS

```python
def _finalize(self):
    """Final state â€” orchestrator hands off to bot."""
    self.logger.info("Orchestration complete â€” bot operational")
    self.context.state = StartupState.SUCCESS
```

---

## 6. Configuration Schema

```python
# src/orchestration/config.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os


@dataclass
class OrchestrationConfig:
    """Configuration for startup orchestrator."""

    # Gateway connection
    gateway_host: str = "localhost"
    gateway_port: int = 4002

    # Docker paths
    docker_compose_dir: Path = Path(__file__).parent.parent.parent / "docker" / "gateway"

    # Gateway health check
    gateway_health_timeout: int = 120  # seconds
    gateway_health_retry_interval: int = 5  # seconds
    health_check_timeout: int = 5  # seconds per check

    # Gameplan
    gameplan_path: Optional[Path] = None
    emergency_gameplan_path: Path = Path(__file__).parent.parent.parent / "state" / "emergency_gameplan.json"

    # Bot configuration
    bot_log_level: str = "INFO"

    # Notifications
    discord_webhook_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "OrchestrationConfig":
        """Load configuration from environment variables."""
        return cls(
            gateway_host=os.getenv("GATEWAY_HOST", "localhost"),
            gateway_port=int(os.getenv("GATEWAY_PORT", "4002")),
            docker_compose_dir=Path(os.getenv("DOCKER_COMPOSE_DIR", cls.docker_compose_dir)),
            gateway_health_timeout=int(os.getenv("GATEWAY_HEALTH_TIMEOUT", "120")),
            gameplan_path=Path(p) if (p := os.getenv("GAMEPLAN_PATH")) else None,
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
            bot_log_level=os.getenv("BOT_LOG_LEVEL", "INFO"),
        )
```

---

## 7. Discord Notification Module

```python
# src/notifications/discord.py

import requests
import logging
from typing import Optional
from datetime import datetime


class DiscordNotifier:
    """Discord webhook notification sender."""

    COLORS = {
        "info": 3447003,      # Blue
        "warning": 16776960,  # Yellow
        "error": 16711680,    # Red
        "critical": 10038562, # Dark red
    }

    def __init__(self, webhook_url: Optional[str]):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)

    def send_info(self, message: str):
        self._send("info", "â„¹ï¸ Info", message)

    def send_warning(self, message: str):
        self._send("warning", "âš ï¸ Warning", message)

    def send_error(self, message: str):
        self._send("error", "âŒ Error", message)

    def send_critical(self, message: str):
        self._send("critical", "ðŸš¨ Critical", message)

    def _send(self, level: str, title: str, message: str):
        """Send Discord webhook notification."""
        if not self.webhook_url:
            self.logger.warning(f"Discord webhook not configured â€” alert not sent: {message}")
            return

        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": self.COLORS[level],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Charter & Stone Capital â€” The Crucible"}
            }]
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            self.logger.debug(f"Discord alert sent: {message}")
        except requests.RequestException as e:
            self.logger.error(f"Failed to send Discord alert: {e}")
```

---

## 8. Gateway Health Checker (Reuse from Task 3.2)

```python
# src/orchestration/health.py

import socket
import logging


class GatewayHealthChecker:
    """Gateway health validation."""

    def __init__(self, host: str, port: int, timeout: int = 5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def check_api_port(self) -> bool:
        """Check if Gateway API port is responding."""
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout):
                self.logger.debug(f"Gateway API port {self.port} responding")
                return True
        except (socket.timeout, socket.error, OSError) as e:
            self.logger.debug(f"Gateway API port {self.port} not responding: {e}")
            return False
```

---

## 9. Strategy C Generator (Emergency Gameplan)

```python
# src/gameplan/generator.py

import json
from pathlib import Path
from datetime import datetime


def generate_strategy_c(output_path: Path):
    """Generate emergency Strategy C gameplan."""
    gameplan = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "session_id": f"emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "regime": "crisis",
        "strategy": "C",
        "symbols": [],
        "position_size_multiplier": 0.0,
        "vix_at_analysis": 0.0,
        "vix_source_verified": False,
        "bias": "neutral",
        "expected_behavior": "mean_reverting",
        "key_levels": {},
        "catalysts": ["Emergency deployment â€” no trading authorized"],
        "earnings_blackout": [],
        "geo_risk": "high",
        "alert_message": "âš ï¸ EMERGENCY STRATEGY C â€” No trading. Operator intervention required.",
        "data_quality": {
            "quarantine_active": True,
            "stale_fields": ["all"],
            "last_verified": datetime.utcnow().isoformat()
        },
        "hard_limits": {
            "max_daily_loss_pct": 0.0,
            "max_single_position": 0,
            "pdt_trades_remaining": 0,
            "force_close_at_dte": 1,
            "weekly_drawdown_governor_active": True,
            "max_intraday_pivots": 0
        },
        "scorecard": {
            "yesterday_pnl": 0.0,
            "yesterday_hit_rate": 0.0,
            "regime_accuracy": False,
            "weekly_cumulative_pnl": 0.0
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(gameplan, object, indent=2)
```

---

## 10. Integration with Bot Main Entry Point

**Modification to `src/main.py`:**

```python
# src/main.py

import sys
import logging
from pathlib import Path

from src.orchestration.config import OrchestrationConfig


def validate_prerequisites():
    """Ensure orchestrator has already started (safety check)."""
    # This is a defense-in-depth check â€” bot should NOT be started manually
    # Orchestrator should be the only entry point in production

    # Check 1: Gameplan exists?
    config = OrchestrationConfig.from_env()
    if not config.gameplan_path or not config.gameplan_path.exists():
        logging.error("Bot started without valid gameplan â€” abort")
        sys.exit(1)

    # Check 2: Gateway reachable?
    from src.orchestration.health import GatewayHealthChecker
    health_checker = GatewayHealthChecker(config.gateway_host, config.gateway_port)
    if not health_checker.check_api_port():
        logging.error("Bot started but Gateway not reachable â€” abort")
        sys.exit(1)

    logging.info("Bot prerequisites validated")


def main():
    """Bot entry point."""
    logging.basicConfig(level=logging.INFO)

    # Prerequisite validation (orchestrator should have done this, but double-check)
    validate_prerequisites()

    # ... rest of existing bot logic ...


if __name__ == "__main__":
    main()
```

---

## 11. Production Deployment Wrapper Script

```bash
# docker/gateway/scripts/production-startup.sh

#!/bin/bash
# =============================================================================
# Production Startup Script
# =============================================================================
#
# Invokes the zero-touch orchestrator for production deployment.
# Use this as the target for systemd or Windows Task Scheduler.
#
# Linux (systemd):
#   ExecStart=/path/to/production-startup.sh
#
# Windows (Task Scheduler via WSL):
#   wsl -d Ubuntu /path/to/production-startup.sh
#
# =============================================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${REPO_DIR}/logs"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="${LOG_DIR}/startup_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Log startup
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting production orchestrator" | tee -a "$LOG_FILE"

# Change to repository directory
cd "$REPO_DIR"

# Load environment (if .env exists)
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Invoke orchestrator
poetry run python -m src.orchestration.startup 2>&1 | tee -a "$LOG_FILE"

# Capture exit code
EXIT_CODE=${PIPESTATUS[0]}

# Log result
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Startup orchestration SUCCESS" | tee -a "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Startup orchestration FAILED (exit code: $EXIT_CODE)" | tee -a "$LOG_FILE"
fi

exit $EXIT_CODE
```

---

## 12. Dependencies

**Python Packages (add to `pyproject.toml`):**

```toml
[tool.poetry.dependencies]
psutil = "^5.9.0"      # Process detection (already running check)
requests = "^2.31.0"   # Discord webhook (may already exist)
```

**No new external services required** â€” all dependencies already available from Phase 2 and Phase 3.1-3.4.

---

## 13. Integration Points

### 13.1 Phase 2 Dependencies

**Gameplan Loader (`src/gameplan/loader.py`):**
- Orchestrator uses existing gameplan loading logic
- Validation functions already implemented in Task 2.7

**Gateway Connection (`src/broker/connection.py`):**
- Health checker can reuse connection logic if needed
- Task 3.2 already implemented basic health validation

### 13.2 Phase 3 Dependencies

**Task 3.1 (Docker Compose):**
- Orchestrator invokes `docker compose up -d gateway`
- Uses health checks defined in docker-compose.yml

**Task 3.3 (Health Monitoring):**
- Orchestrator validates Gateway health at startup
- Health monitoring continues independently after bot starts

---

## 14. Definition of Done

### 14.1 Core Functionality

- [ ] Orchestrator module created in `src/orchestration/startup.py`
- [ ] State machine implements all transitions (INITIALIZING â†’ SUCCESS/FAILURE)
- [ ] Gateway startup logic functional (detect running, start if needed)
- [ ] Gateway health validation with 120s timeout
- [ ] Gateway restart recovery (one-time attempt)
- [ ] Gameplan loading with validation
- [ ] Strategy C emergency deployment
- [ ] Bot process launch with validated config
- [ ] Exit codes: 0 (success), 1 (failure)

### 14.2 Notifications

- [ ] Discord module implements info/warning/error/critical levels
- [ ] Alerts sent at key decision points (Gateway start, failures, Strategy C)
- [ ] Graceful degradation if webhook not configured (log-only mode)

### 14.3 Configuration

- [ ] OrchestrationConfig loads from environment variables
- [ ] All timeouts and paths configurable
- [ ] Defaults work for development (no env vars required)

### 14.4 Error Handling

- [ ] Docker unavailable â†’ FAILURE with clear message
- [ ] Gateway timeout â†’ FAILURE after restart attempt
- [ ] Invalid gameplan â†’ Strategy C deployment (not failure)
- [ ] Missing gameplan â†’ Strategy C deployment (not failure)
- [ ] Bot start failure â†’ FAILURE with stderr capture
- [ ] Unexpected exceptions caught and logged

### 14.5 Production Deployment

- [ ] `production-startup.sh` script created
- [ ] Script executable: `chmod +x docker/gateway/scripts/production-startup.sh`
- [ ] Script logs to `logs/startup_YYYYMMDD_HHMMSS.log`
- [ ] Script works on both Windows (WSL) and Linux

### 14.6 Testing

- [ ] Unit tests: `tests/orchestration/test_startup_orchestrator.py`
  - Test state transitions
  - Test timeout logic
  - Test restart recovery
  - Test Strategy C fallback
- [ ] Integration tests: `tests/integration/test_zero_touch_startup.py`
  - Test full startup sequence (mocked Docker)
  - Test Gateway health validation
  - Test bot launch
- [ ] All existing tests pass (638 tests)
- [ ] CI/CD pipeline passes

### 14.7 Documentation

- [ ] README.md updated with orchestrator usage
- [ ] Environment variables documented in .env.example
- [ ] Production deployment instructions added

### 14.8 Review Sign-offs

- [ ] @Systems_Architect: Architecture review
- [ ] @DevOps: Deployment strategy review
- [ ] @CRO: Failure modes safe (Strategy C fallback validated)
- [ ] @QA_Lead: Test coverage adequate

---

## 15. Edge Cases to Test

### 15.1 Gateway Failure Scenarios

1. **Gateway container doesn't exist:**
   - Expected: Orchestrator starts it via `docker compose up -d`
   - Test: Delete container, run orchestrator, verify creation

2. **Gateway container exists but stopped:**
   - Expected: Orchestrator starts it
   - Test: Stop container, run orchestrator, verify startup

3. **Gateway starts but never becomes healthy (timeout):**
   - Expected: Restart attempt, then FAILURE
   - Test: Mock health check to always fail, verify restart and timeout

4. **Gateway becomes unhealthy after initial validation:**
   - Expected: Orchestrator hands off to bot, health monitoring (Task 3.3) detects
   - Test: Not orchestrator's responsibility (out of scope for Task 3.5)

5. **Docker daemon not running:**
   - Expected: FAILURE with clear error message
   - Test: Stop Docker Desktop, run orchestrator, verify error

### 15.2 Gameplan Scenarios

6. **Gameplan file missing:**
   - Expected: Strategy C deployed, alert sent, bot starts
   - Test: Delete gameplan, verify Strategy C creation

7. **Gameplan schema invalid:**
   - Expected: Strategy C deployed, alert sent, bot starts
   - Test: Corrupt gameplan JSON, verify Strategy C fallback

8. **Gameplan has data_quarantine = true:**
   - Expected: Strategy C enforced, original gameplan ignored
   - Test: Set quarantine flag, verify Strategy C

9. **Gameplan path not configured:**
   - Expected: Strategy C deployed, alert sent
   - Test: Unset GAMEPLAN_PATH, verify Strategy C

### 15.3 Bot Startup Scenarios

10. **Bot crashes immediately on startup:**
    - Expected: FAILURE, stderr logged, alert sent
    - Test: Introduce syntax error in bot, verify detection

11. **Bot already running:**
    - Expected: FAILURE (prevent duplicate instances)
    - Test: Start bot manually, run orchestrator, verify detection

### 15.4 Notification Scenarios

12. **Discord webhook not configured:**
    - Expected: Orchestrator proceeds, alerts logged only
    - Test: Unset webhook URL, verify log-only operation

13. **Discord webhook times out:**
    - Expected: Orchestrator proceeds, logs error
    - Test: Invalid webhook URL, verify graceful degradation

### 15.5 Idempotency Scenarios

14. **Run orchestrator twice:**
    - Expected: First run succeeds, second run detects bot already running
    - Test: Run orchestrator, wait for bot start, run again, verify detection

15. **Gateway and bot both already running:**
    - Expected: Orchestrator detects both, exits cleanly or FAILs
    - Test: Start both manually, run orchestrator, verify behavior

### 15.6 Race Conditions

16. **Gateway becomes healthy exactly at timeout:**
    - Expected: Success (health check wins race)
    - Test: Mock slow health check, verify edge case handling

17. **Gateway crashes during orchestrator wait loop:**
    - Expected: Health check fails, restart attempted
    - Test: Kill Gateway mid-wait, verify recovery

---

## 16. Rollback Plan

**To disable zero-touch startup:**

1. **Stop using orchestrator:**
   - Remove systemd service or Windows Task Scheduler entry
   - Return to manual Gateway start: `docker compose up -d gateway`
   - Return to manual bot start: `poetry run python -m src.main`

2. **Revert code changes:**
   - Bot (`src/main.py`) prerequisite validation is defensive only â€” no breaking changes
   - Orchestrator is standalone module â€” can be ignored without side effects

3. **Remove orchestrator artifacts:**
   - Delete `src/orchestration/` directory (optional)
   - Delete `tests/orchestration/` directory (optional)
   - Remove psutil dependency from pyproject.toml (optional)

**No production risk** â€” orchestrator is additive, not replacing existing manual workflows.

---

## 17. Future Enhancements (Out of Scope for Task 3.5)

**Potential Phase 4+ improvements:**

1. **Graceful shutdown orchestration:**
   - Complement to startup: close positions, stop bot, stop Gateway
   - Triggered by signal (SIGTERM) or scheduled time

2. **Intraday restart coordination:**
   - Orchestrator handles mid-day Gateway restarts without stopping bot
   - Bot pauses trading, orchestrator restarts Gateway, bot resumes

3. **Multi-bot orchestration:**
   - Coordinate multiple bot instances (different strategies, different accounts)
   - Shared Gateway instance

4. **Advanced health validation:**
   - TWS API handshake confirmation (not just port check)
   - Account balance verification
   - Connection latency measurement

5. **State persistence:**
   - Orchestrator writes state file (last startup time, last failure, recovery attempts)
   - Used for debugging and audit trail

6. **Systemd service file generation:**
   - Orchestrator generates `.service` file for Linux deployment
   - Windows Task Scheduler XML export

**These are explicitly deferred** to keep Task 3.5 focused on the core zero-touch startup requirement.

---

## 18. Success Criteria Summary

**Task 3.5 is COMPLETE when:**

1. âœ… Operator can run `poetry run python -m src.orchestration.startup` and the system autonomously:
   - Starts Gateway if needed
   - Waits for Gateway health
   - Validates gameplan (or deploys Strategy C)
   - Starts bot
   - Exits with success code

2. âœ… Operator receives Discord alerts at each critical decision point

3. âœ… System handles all documented failure scenarios gracefully (Strategy C fallback, restart recovery, clear error messages)

4. âœ… Production wrapper script (`production-startup.sh`) works on both Windows (WSL) and Linux

5. âœ… All tests pass (unit + integration)

6. âœ… @CRO approves failure modes and Strategy C deployment logic

7. âœ… @QA_Lead approves test coverage

8. âœ… Task 3.6 (QA Review) can proceed with this orchestrator as the validation target

---

**This completes the Task 3.5 handoff specification. Proceed to Opus with extended thinking for implementation.**
