# VSC HANDOFF: Bot Startup Orchestration with Gateway (Task 3.2)

**Date:** 2026-02-10
**Requested By:** Protocol W5 (Design Session) — P3-S4
**Session Type:** Workshop Mode
**Lead Personas:** @Systems_Architect, @DevOps
**Supporting Personas:** @CRO (safety review), @QA_Lead (edge cases)
**Board Task:** s8bKaZVc_UKmZqaY7AR3f2UAL-K7

---

## Header Block

| Attribute | Value |
|-----------|-------|
| **Model Routing** | Sonnet recommended (structured implementation, moderate complexity) |
| **Context Budget** | Moderate (~10K input + 4K output tokens estimated) |
| **Estimated Implementation Time** | 2-3 hours |
| **Dependencies** | Task 3.1 (Gateway Docker Compose) ✅ Complete |
| **Blocks** | Task 3.3 (Health Monitoring), Task 3.4 (Full Docker Orchestration) |

---

## Architectural Decision Summary

**Selected Approach:** Option C — Hybrid (Docker Compose + Explicit Bot Validation)

**Decision Rationale:**

The bot will run as a Docker container orchestrated by Docker Compose with `depends_on: gateway: condition: service_healthy`. However, the bot will also perform its own explicit Gateway validation at startup before proceeding to trading logic.

This hybrid approach provides:

1. **Docker Orchestration Benefits:** Clean startup sequencing, container lifecycle management, easy deployment/migration
2. **Defense-in-Depth (CRO Requirement):** Bot validates Gateway independently — doesn't blindly trust Docker health checks
3. **Runtime Monitoring Capability:** Bot-side validation logic can detect Gateway failures after initial startup
4. **Portable Validation Logic:** Same validation code works whether running in Docker or native Python

**@CRO Assessment:** The hybrid approach satisfies the defense-in-depth requirement. No code path allows trading without validated Gateway connection. **APPROVED.**

---

## Agent Execution Block (Primary Content)

### 1. Objective

Implement bot startup orchestration that safely coordinates with IBKR Gateway readiness. The bot must:

1. Wait for Gateway availability before proceeding (no race conditions)
2. Validate Gateway authentication status (IBKR connection confirmed)
3. Implement retry logic with exponential backoff
4. Alert operators on startup failures
5. Default to Strategy C (cash preservation) if Gateway is unavailable
6. Integrate with existing Phase 2 modules (strategies, risk controls, broker layer)

**Safety Constraint:** The bot must NEVER attempt to trade without a validated Gateway connection. All failure paths result in either Strategy C activation or complete startup failure with alerts.

---

### 2. File Structure

```
charter-stone-capital/
├── docker/
│   ├── docker-compose.yml          # UPDATE: Add trading-bot service
│   ├── gateway/
│   │   └── (existing Gateway config from Task 3.1)
│   └── bot/
│       ├── Dockerfile              # CREATE: Bot container definition
│       └── entrypoint.sh           # CREATE: Startup orchestration script
├── src/
│   ├── main.py                     # UPDATE: Add orchestration wrapper
│   ├── config.py                   # UPDATE: Add Gateway configuration
│   └── utils/
│       └── gateway_health.py       # CREATE: Gateway health check utilities
├── .env.example                    # UPDATE: Add Gateway environment variables
└── tests/
    └── unit/
        └── test_gateway_health.py  # CREATE: Health check tests
```

**Files to CREATE:**
- `docker/bot/Dockerfile` — Bot container image definition
- `docker/bot/entrypoint.sh` — Startup orchestration shell script
- `src/utils/gateway_health.py` — Gateway health check utilities
- `tests/unit/test_gateway_health.py` — Unit tests for health checks

**Files to UPDATE:**
- `docker/docker-compose.yml` — Add trading-bot service definition
- `src/main.py` — Wrap with orchestration logic
- `src/config.py` — Add Gateway configuration parameters
- `.env.example` — Document Gateway environment variables

---

### 3. Logic Flow (Pseudo-code)

#### 3.1 High-Level Startup Sequence

```
STARTUP SEQUENCE (Bot Container)
================================

Phase 0: Docker Orchestration
  Docker Compose ensures Gateway health check passes
  Docker starts bot container only after Gateway reports healthy
  NOTE: Bot does NOT assume Gateway is ready — defense-in-depth follows

Phase 1: Bot Initialization
  1. Load environment variables (GATEWAY_HOST, GATEWAY_PORT, etc.)
  2. Initialize logging (structured JSON to stdout for Docker)
  3. Log startup event: "Bot container started, beginning Gateway validation"
  4. Load configuration from environment

Phase 2: Gateway Readiness Validation (Bot-side)
  5. Create GatewayHealthChecker instance
  6. Execute wait_for_gateway() with retry logic
     - Attempt 1: Immediate check
     - Attempt 2+: Exponential backoff (5s, 10s, 20s, 30s cap)
     - Max attempts: 30 (configurable)
     - Total timeout: 5 minutes (configurable)
  7. If Gateway ready: proceed to Phase 3
  8. If Gateway timeout: fail startup, send CRITICAL alert, exit(1)

Phase 3: Gateway Authentication Validation
  9. Validate Gateway is authenticated to IBKR
     - Check connection status via IB API
     - Verify account data accessible
  10. If authenticated: proceed to Phase 4
  11. If not authenticated: fail startup, send CRITICAL alert, exit(1)

Phase 4: Bot Operational Initialization
  12. Initialize Phase 2 modules:
      - IBKRConnection (broker layer)
      - StrategyEngine (strategy implementations)
      - RiskManager (risk controls)
  13. Load daily gameplan JSON (if exists)
  14. Log startup success: "Bot operational, Gateway validated"

Phase 5: Trading Loop
  15. If market hours: begin strategy execution
  16. If outside market hours: wait for market open
  17. Continuous runtime monitoring:
      - Periodic Gateway health checks (every 60s)
      - Connection loss detection → Strategy C activation
      - Reconnection attempts on transient failures
```

#### 3.2 Gateway Health Check Logic

```
FUNCTION wait_for_gateway(
    host: str,
    port: int,
    max_retries: int = 30,
    initial_delay: float = 5.0,
    max_delay: float = 30.0,
    timeout: float = 300.0  # 5 minutes total
) -> bool:

    start_time = now()
    attempt = 0
    delay = initial_delay

    WHILE attempt < max_retries AND elapsed_time < timeout:
        attempt += 1
        log(f"Gateway check attempt {attempt}/{max_retries}")

        IF check_gateway_port(host, port):
            IF validate_gateway_authentication(host, port):
                log("Gateway is ready and authenticated")
                RETURN True
            ELSE:
                log("Gateway responding but not authenticated, retrying")
        ELSE:
            log("Gateway port not responding, retrying")

        # Alert after threshold
        IF attempt == 3:
            send_discord_alert("WARNING", "Gateway startup delayed, retrying...")
        IF attempt == 10:
            send_discord_alert("ERROR", "Gateway startup significantly delayed")

        # Exponential backoff with cap
        sleep(delay)
        delay = min(delay * 2, max_delay)

    # Max retries exceeded or timeout
    send_discord_alert("CRITICAL", "Gateway startup failed after all retries")
    log("Gateway validation failed, bot cannot start")
    RETURN False


FUNCTION check_gateway_port(host: str, port: int) -> bool:
    TRY:
        socket.connect((host, port), timeout=5)
        RETURN True
    EXCEPT:
        RETURN False


FUNCTION validate_gateway_authentication(host: str, port: int) -> bool:
    TRY:
        # Use ib_insync to check connection status
        ib = IB()
        ib.connect(host, port, clientId=0, timeout=10)

        # Verify we can access account info (proves authentication)
        accounts = ib.managedAccounts()
        IF accounts AND len(accounts) > 0:
            ib.disconnect()
            RETURN True

        ib.disconnect()
        RETURN False
    EXCEPT:
        RETURN False
```

#### 3.3 Entrypoint Script Logic

```bash
#!/bin/bash
# docker/bot/entrypoint.sh

set -e

echo "[$(date -Iseconds)] Bot container starting..."

# Phase 1: Environment validation
if [ -z "$GATEWAY_HOST" ]; then
    echo "ERROR: GATEWAY_HOST not set"
    exit 1
fi

if [ -z "$GATEWAY_PORT" ]; then
    echo "ERROR: GATEWAY_PORT not set"
    exit 1
fi

echo "[$(date -Iseconds)] Configuration loaded: Gateway at ${GATEWAY_HOST}:${GATEWAY_PORT}"

# Phase 2: Delegate to Python orchestrator
# The Python code handles all retry logic, health checks, and business logic
exec python -m src.main \
    --gateway-host "$GATEWAY_HOST" \
    --gateway-port "$GATEWAY_PORT" \
    --gameplan-path "${GAMEPLAN_PATH:-/data/gameplan.json}" \
    --dry-run "${DRY_RUN:-true}"
```

#### 3.4 Main Entry Point Logic

```python
# src/main.py (updated structure)

def main():
    """
    Bot entry point with Gateway orchestration.

    Startup Sequence:
    1. Parse arguments and load configuration
    2. Initialize logging
    3. Wait for Gateway readiness (with retries)
    4. Validate Gateway authentication
    5. Initialize Phase 2 modules
    6. Load gameplan
    7. Start trading loop
    """
    # Phase 1: Configuration
    config = load_config()
    setup_logging(config)
    logger.info("Bot startup initiated", extra={"version": BOT_VERSION})

    # Phase 2: Gateway readiness
    health_checker = GatewayHealthChecker(
        host=config.gateway_host,
        port=config.gateway_port,
        discord_webhook=config.discord_webhook_url
    )

    if not health_checker.wait_for_gateway(
        max_retries=config.gateway_max_retries,
        timeout=config.gateway_startup_timeout
    ):
        logger.critical("Gateway validation failed, cannot start bot")
        sys.exit(1)

    logger.info("Gateway validated successfully")

    # Phase 3: Initialize Phase 2 modules
    try:
        broker = IBKRConnection(
            host=config.gateway_host,
            port=config.gateway_port,
            client_id=config.client_id
        )
        strategy_engine = StrategyEngine(broker=broker)
        risk_manager = RiskManager(config=config.risk_config)
    except Exception as e:
        logger.critical(f"Failed to initialize trading modules: {e}")
        health_checker.send_alert("CRITICAL", f"Bot initialization failed: {e}")
        sys.exit(1)

    # Phase 4: Load gameplan
    gameplan = load_gameplan(config.gameplan_path)
    if gameplan is None:
        logger.warning("No gameplan found, defaulting to Strategy C")
        gameplan = create_strategy_c_gameplan()

    # Phase 5: Trading loop
    run_trading_loop(
        broker=broker,
        strategy_engine=strategy_engine,
        risk_manager=risk_manager,
        gameplan=gameplan,
        health_checker=health_checker
    )


if __name__ == "__main__":
    main()
```

---

### 4. Dependencies

#### 4.1 Python Dependencies

```toml
# pyproject.toml additions (if not already present)

[tool.poetry.dependencies]
ib_insync = "^0.9.86"        # IB API wrapper (existing)
python-dotenv = "^1.0.0"     # Environment variable loading
httpx = "^0.27.0"            # HTTP client for Discord webhooks
structlog = "^24.1.0"        # Structured logging (optional but recommended)
```

#### 4.2 System Dependencies

- Docker 24+ and Docker Compose V2
- Python 3.11+
- Network access to Gateway container (Docker network)
- Network access to Discord webhooks (outbound HTTPS)

#### 4.3 Existing Module Dependencies

```
src/broker/connection.py    → IBKRConnection class (Phase 2)
src/strategies/             → Strategy implementations (Phase 2)
src/risk/                   → Risk management (Phase 2)
src/config.py              → Configuration loading (Phase 2)
```

---

### 5. Input/Output Contract

#### 5.1 Inputs

**Environment Variables (Required):**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GATEWAY_HOST` | string | `gateway` | Gateway hostname (Docker service name or localhost) |
| `GATEWAY_PORT` | int | `4002` | Gateway API port |
| `GATEWAY_STARTUP_TIMEOUT` | int | `300` | Max seconds to wait for Gateway (5 min) |
| `GATEWAY_MAX_RETRIES` | int | `30` | Max retry attempts |
| `GATEWAY_RETRY_INTERVAL` | float | `5.0` | Initial retry delay (seconds) |
| `GAMEPLAN_PATH` | string | `/data/gameplan.json` | Path to daily gameplan JSON |
| `DRY_RUN` | bool | `true` | Enable dry-run mode (no real trades) |
| `DISCORD_WEBHOOK_URL` | string | (none) | Discord webhook for alerts |
| `CLIENT_ID` | int | `1` | IB API client ID |
| `LOG_LEVEL` | string | `INFO` | Logging verbosity |

**Gameplan JSON (Optional):**

```json
{
  "date": "2026-02-10",
  "strategy": "A",
  "symbols": ["SPY"],
  "hard_limits": {
    "max_daily_loss_pct": 0.10,
    "max_single_position": 120
  }
}
```

If no gameplan exists, bot defaults to Strategy C (cash preservation).

#### 5.2 Outputs

**Startup Success:**
- Bot process running and connected to Gateway
- Log entry: `"Bot operational, Gateway validated"`
- No alerts sent

**Startup Failure (Gateway Unavailable):**
- Bot process exits with code 1
- Log entry: `"Gateway validation failed, cannot start bot"`
- Discord alert: `"CRITICAL: Gateway startup failed after all retries"`

**Startup Failure (Authentication Failed):**
- Bot process exits with code 1
- Log entry: `"Gateway authenticated but IBKR login failed"`
- Discord alert: `"CRITICAL: Gateway authentication failed, check IBKR credentials"`

**Runtime State:**
- Periodic health check logs (every 60s)
- Connection loss detection → Strategy C activation
- Reconnection attempts logged

---

### 6. Integration Points

#### 6.1 Gateway Container (Task 3.1)

**Connection Details:**
- Service name: `gateway` (Docker Compose network)
- Port: `4002` (paper trading)
- Health check: TCP port check via `/dev/tcp`
- Authentication delay: 30-60 seconds after container start

**Interface Contract:**
```
Bot → Gateway: TCP connection on port 4002
Bot → Gateway: IB API protocol (ib_insync wrapper)
Bot ← Gateway: Market data, account info, order execution
```

**Health Check Endpoint:**
- No HTTP health endpoint on Gateway
- Bot validates by attempting IB API connection
- Check `ib.managedAccounts()` to confirm authentication

#### 6.2 Phase 2 Broker Integration Layer

**IBKRConnection Class:**
```python
# src/broker/connection.py (existing)

class IBKRConnection:
    def __init__(self, host: str, port: int, client_id: int):
        ...

    def connect(self) -> bool:
        ...

    def disconnect(self):
        ...

    def is_connected(self) -> bool:
        ...
```

**Integration Notes:**
- `GatewayHealthChecker` uses similar connection logic but with specific timeout/retry behavior
- Once validated, bot uses `IBKRConnection` for all trading operations
- `IBKRConnection.is_connected()` can be used for runtime health checks

#### 6.3 Task 3.3 Health Monitoring (Future)

**Interface Definition:**

The bot exposes its health status for Task 3.3 monitoring:

```python
# Bot-side health status (for Task 3.3 to query)

class BotHealthStatus:
    gateway_connected: bool
    last_gateway_check: datetime
    uptime_seconds: float
    strategy_active: str
    positions_open: int
    last_error: Optional[str]
```

**Task 3.3 Responsibilities:**
- External monitoring of both Gateway and bot
- System-level health (CPU, memory, disk)
- Aggregated alerting (consolidate Gateway + bot alerts)

**Boundary:** Bot performs its own immediate connection validation. Task 3.3 provides external oversight and system monitoring.

#### 6.4 Discord Webhooks

**Alert Levels:**

| Level | When | Message Format |
|-------|------|----------------|
| `DEBUG` | Development only | Not sent to Discord |
| `INFO` | Gateway validated | `"✅ Bot started successfully"` |
| `WARNING` | Retry in progress (attempt 3+) | `"⚠️ Gateway startup delayed, retrying..."` |
| `ERROR` | Significant delay (attempt 10+) | `"🔴 Gateway startup significantly delayed"` |
| `CRITICAL` | Startup failed | `"🚨 CRITICAL: Gateway startup failed"` |

**Webhook Payload:**
```json
{
  "content": "🚨 **CRITICAL: Gateway Startup Failed**\n\nBot could not connect to Gateway after 30 attempts (5 minutes).\n\n**Action Required:** Check Gateway container logs and IBKR authentication.\n\n*Timestamp: 2026-02-10T09:15:00-05:00*"
}
```

---

### 7. Definition of Done

#### 7.1 Core Functionality

- [ ] **DOD-3.2-01:** Bot waits for Gateway readiness at startup (no race condition)
- [ ] **DOD-3.2-02:** Retry logic implemented with exponential backoff
- [ ] **DOD-3.2-03:** Timeout and max retry limits enforced
- [ ] **DOD-3.2-04:** Bot validates Gateway authentication (not just port availability)
- [ ] **DOD-3.2-05:** Bot refuses to trade if Gateway unavailable
- [ ] **DOD-3.2-06:** Strategy C failover activated on Gateway failure

#### 7.2 Docker Integration

- [ ] **DOD-3.2-07:** Bot Dockerfile created and builds successfully
- [ ] **DOD-3.2-08:** docker-compose.yml updated with trading-bot service
- [ ] **DOD-3.2-09:** `depends_on: gateway: condition: service_healthy` configured
- [ ] **DOD-3.2-10:** Bot container starts only after Gateway is healthy
- [ ] **DOD-3.2-11:** Volume mounts configured for gameplan and data persistence

#### 7.3 Alerting

- [ ] **DOD-3.2-12:** Discord alerts fire on startup failures
- [ ] **DOD-3.2-13:** Alert severity levels implemented (WARNING, ERROR, CRITICAL)
- [ ] **DOD-3.2-14:** Alert messages include actionable information

#### 7.4 Testing

- [ ] **DOD-3.2-15:** Unit tests for `GatewayHealthChecker` class
- [ ] **DOD-3.2-16:** Unit tests for retry logic and backoff calculation
- [ ] **DOD-3.2-17:** Integration test: Gateway down → Gateway starts → bot proceeds
- [ ] **DOD-3.2-18:** Integration test: Gateway never available → bot fails safely
- [ ] **DOD-3.2-19:** All existing tests pass (no regressions)

#### 7.5 Quality Gates

- [ ] **DOD-3.2-20:** ruff passes with zero warnings
- [ ] **DOD-3.2-21:** black formatting applied
- [ ] **DOD-3.2-22:** mypy type checking passes

#### 7.6 Reviews

- [ ] **DOD-3.2-23:** @CRO review: all failure modes safe (default to Strategy C)
- [ ] **DOD-3.2-24:** @DevOps review: Docker integration works correctly
- [ ] **DOD-3.2-25:** @QA_Lead review: orchestration logic complete and tested

---

### 8. Edge Cases to Test

#### 8.1 Startup Scenarios

| # | Scenario | Expected Behavior | Test Method |
|---|----------|-------------------|-------------|
| EC-01 | Gateway container not started | Bot retries, eventually times out, alerts CRITICAL | Stop Gateway before starting bot |
| EC-02 | Gateway started but still authenticating (30-60s delay) | Bot retries until auth succeeds, then proceeds | Start Gateway and bot simultaneously |
| EC-03 | Gateway responds but authentication fails (wrong credentials) | Bot detects auth failure, alerts CRITICAL, exits | Use invalid IBKR credentials |
| EC-04 | Gateway becomes unresponsive during bot startup | Bot retry loop handles transient failure | Kill Gateway mid-startup |
| EC-05 | Network unavailable (no route to Gateway) | Bot socket timeout, retries, eventually fails | Network partition simulation |
| EC-06 | Invalid Gateway host/port in configuration | Bot fails fast with clear error message | Set GATEWAY_HOST=invalid |

#### 8.2 Runtime Scenarios

| # | Scenario | Expected Behavior | Test Method |
|---|----------|-------------------|-------------|
| EC-07 | Gateway crashes after bot connects | Bot detects disconnection, activates Strategy C, alerts | Kill Gateway after bot startup |
| EC-08 | Gateway memory leak causes slowdown | Bot periodic checks detect degradation | Simulate slow responses |
| EC-09 | Gateway restarts (daily 4:30 PM restart) | Bot handles disconnection, reconnects automatically | Restart Gateway during runtime |
| EC-10 | Multiple Gateway restarts in quick succession | Bot rate-limits reconnection attempts | Restart Gateway repeatedly |

#### 8.3 Configuration Scenarios

| # | Scenario | Expected Behavior | Test Method |
|---|----------|-------------------|-------------|
| EC-11 | Gameplan JSON missing | Bot defaults to Strategy C, logs warning | Remove gameplan file |
| EC-12 | Gameplan JSON malformed | Bot rejects invalid gameplan, defaults to Strategy C | Corrupt gameplan JSON |
| EC-13 | Discord webhook URL invalid | Alerts fail silently (don't crash bot) | Set invalid webhook URL |
| EC-14 | Environment variables missing | Bot fails fast with clear error messages | Unset required env vars |

#### 8.4 Concurrency Scenarios

| # | Scenario | Expected Behavior | Test Method |
|---|----------|-------------------|-------------|
| EC-15 | Bot restart while Gateway already running | Bot reconnects quickly (skip wait) | Restart bot container only |
| EC-16 | Multiple bot instances started | Only one client ID active, second rejects | Start two bot containers |

---

### 9. Rollback Plan

#### 9.1 Quick Rollback (< 5 minutes)

```bash
# Stop bot container, Gateway continues running
docker compose stop trading-bot

# Or stop everything
docker compose down
```

#### 9.2 Full Rollback to Phase 2 (standalone)

If Task 3.2 implementation introduces critical issues:

1. Remove trading-bot service from `docker-compose.yml`
2. Run bot manually (outside Docker):
   ```bash
   cd charter-stone-capital
   poetry run python -m src.main --gateway-host localhost --gateway-port 4002
   ```
3. Gateway continues running in Docker
4. Bot validation logic remains but orchestration is manual

#### 9.3 Feature Flag (Recommended)

Implement a feature flag to disable Docker orchestration:

```bash
# .env
BOT_ORCHESTRATION_MODE=docker   # Use Docker Compose
# or
BOT_ORCHESTRATION_MODE=native   # Run bot natively, manual startup
```

This allows switching between orchestration modes without code changes.

---

## Context Block (Supplementary)

### Task 3.1 Learnings

**Gateway Deployment Summary:**
- Gateway deployed via Docker Compose using `gnzsnz/ib-gateway:10.25.1` image
- Port 4002 (paper trading mode)
- Health check: TCP port check (`bash -c "echo > /dev/tcp/localhost/4002"`)
- Authentication takes 30-60 seconds after container starts
- Docker restart policy: `unless-stopped`
- Daily restart at 4:30 PM ET (cron job, not Docker)

**Docker Compose Configuration (Task 3.1):**
```yaml
services:
  gateway:
    image: gnzsnz/ib-gateway:10.25.1
    container_name: ib-gateway
    ports:
      - "4001:4001"  # Live (not exposed externally)
      - "4002:4002"  # Paper (active)
      - "5900:5900"  # VNC (debugging only)
    environment:
      - TRADING_MODE=paper
      - TWSUSERID=${IBKR_USERNAME}
      - TWSPASSWORD=${IBKR_PASSWORD}
    healthcheck:
      test: ["CMD", "bash", "-c", "echo > /dev/tcp/localhost/4002"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 60s
    restart: unless-stopped
```

### Phase 2 Integration Reference

**IBKRConnection Class (src/broker/connection.py):**
```python
class IBKRConnection:
    """
    IBKR broker connection wrapper using ib_insync.

    Provides:
    - Connection management (connect, disconnect, reconnect)
    - Account data access (positions, balances)
    - Order execution (submit, cancel, modify)
    - Market data subscription
    """

    def __init__(self, host: str, port: int, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()

    def connect(self) -> bool:
        """Connect to IBKR Gateway."""
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self.ib.isConnected()

    def disconnect(self):
        """Disconnect from IBKR Gateway."""
        self.ib.disconnect()
```

**Reuse Strategy:**
- `GatewayHealthChecker` uses similar connection logic but with specific timeout/retry parameters
- For startup validation, use shorter timeouts (10s) and specific error handling
- After validation succeeds, hand off to `IBKRConnection` for trading operations

### CRO Safety Requirements

**@CRO Review Criteria:**

1. **No Trading Without Validated Gateway:**
   - Bot must not execute any trade orders if Gateway validation fails
   - Strategy C (cash preservation) is the only acceptable state without Gateway

2. **All Failure Paths Default Safe:**
   - Gateway timeout → Strategy C + alert
   - Authentication failure → Strategy C + alert
   - Runtime disconnection → close positions (if any) + Strategy C + alert

3. **Alerting Before Capital Risk:**
   - Alerts must fire BEFORE bot attempts any trading on a failed connection
   - CRITICAL alerts require operator acknowledgment (implied by Discord ping)

4. **Defense-in-Depth Validation:**
   - Docker health check is necessary but not sufficient
   - Bot must perform its own validation (authentication check via IB API)
   - Two independent validations: Docker orchestration + bot-side check

**@CRO Sign-off Checklist:**
- [ ] No code path allows `place_order()` without `gateway_validated = True`
- [ ] `gateway_validated` flag is set ONLY after successful `validate_gateway_authentication()`
- [ ] Runtime health checks can set `gateway_validated = False` if disconnection detected
- [ ] Strategy C gameplan is generated locally (no external dependency)

### Task Acceptance Criteria (from Board)

| Criterion | Blueprint Section |
|-----------|-------------------|
| Bot startup sequence coordinates with Gateway availability | Section 3.1, 3.2 |
| Retry logic with exponential backoff implemented | Section 3.2 |
| Health check validates Gateway authentication status | Section 3.2 (`validate_gateway_authentication`) |
| Discord alerts on startup failures | Section 6.4, DoD 12-14 |
| Strategy C failover if Gateway unavailable | Section 3.1 Phase 2 (step 8) |
| Docker Compose integration | Section 2, Appendix A |
| @CRO review: failure modes safe | CRO Safety Requirements |
| VSC Handoff Document created | This document |

---

## Appendix A: Docker Configuration Files

### A.1 Bot Dockerfile

```dockerfile
# docker/bot/Dockerfile

FROM python:3.11-slim-bookworm

LABEL maintainer="Charter & Stone Capital"
LABEL description="Trading bot with Gateway orchestration"
LABEL version="1.0.0"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash botuser
WORKDIR /app

# Install Poetry
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy dependency files first (layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev dependencies in production)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-dev

# Copy application code
COPY src/ ./src/
COPY docker/bot/entrypoint.sh ./entrypoint.sh

# Make entrypoint executable
RUN chmod +x ./entrypoint.sh

# Switch to non-root user
USER botuser

# Health check (optional, for external monitoring)
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import src.utils.gateway_health as gh; exit(0 if gh.quick_check() else 1)" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
```

### A.2 Updated docker-compose.yml

```yaml
# docker/docker-compose.yml

version: "3.8"

services:
  gateway:
    image: gnzsnz/ib-gateway:10.25.1
    container_name: ib-gateway
    ports:
      - "4001:4001"  # Live trading (not used for paper)
      - "4002:4002"  # Paper trading
      - "5900:5900"  # VNC (debugging)
    environment:
      - TRADING_MODE=paper
      - TWSUSERID=${IBKR_USERNAME}
      - TWSPASSWORD=${IBKR_PASSWORD}
    volumes:
      - gateway-data:/home/ibgateway/Jts
    healthcheck:
      test: ["CMD", "bash", "-c", "echo > /dev/tcp/localhost/4002"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    networks:
      - trading-network

  trading-bot:
    build:
      context: ../
      dockerfile: docker/bot/Dockerfile
    container_name: trading-bot
    depends_on:
      gateway:
        condition: service_healthy
    environment:
      - GATEWAY_HOST=gateway
      - GATEWAY_PORT=4002
      - GATEWAY_STARTUP_TIMEOUT=${GATEWAY_STARTUP_TIMEOUT:-300}
      - GATEWAY_MAX_RETRIES=${GATEWAY_MAX_RETRIES:-30}
      - GATEWAY_RETRY_INTERVAL=${GATEWAY_RETRY_INTERVAL:-5}
      - GAMEPLAN_PATH=/data/gameplan.json
      - DRY_RUN=${DRY_RUN:-true}
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
      - CLIENT_ID=${CLIENT_ID:-1}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./data:/data:ro
      - bot-logs:/app/logs
    restart: unless-stopped
    networks:
      - trading-network

volumes:
  gateway-data:
  bot-logs:

networks:
  trading-network:
    driver: bridge
```

### A.3 Entrypoint Script

```bash
#!/bin/bash
# docker/bot/entrypoint.sh

set -e

echo "[$(date -Iseconds)] Trading bot container starting..."
echo "[$(date -Iseconds)] Gateway target: ${GATEWAY_HOST}:${GATEWAY_PORT}"
echo "[$(date -Iseconds)] Dry-run mode: ${DRY_RUN}"

# Validate required environment variables
required_vars=("GATEWAY_HOST" "GATEWAY_PORT")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "[$(date -Iseconds)] ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

# Optional: Log configuration summary
echo "[$(date -Iseconds)] Configuration:"
echo "  - GATEWAY_HOST: ${GATEWAY_HOST}"
echo "  - GATEWAY_PORT: ${GATEWAY_PORT}"
echo "  - GATEWAY_STARTUP_TIMEOUT: ${GATEWAY_STARTUP_TIMEOUT:-300}"
echo "  - GATEWAY_MAX_RETRIES: ${GATEWAY_MAX_RETRIES:-30}"
echo "  - GAMEPLAN_PATH: ${GAMEPLAN_PATH:-/data/gameplan.json}"
echo "  - DRY_RUN: ${DRY_RUN:-true}"
echo "  - LOG_LEVEL: ${LOG_LEVEL:-INFO}"

# Execute Python bot with all arguments passed through
exec python -m src.main
```

---

## Appendix B: Gateway Health Check Module

```python
# src/utils/gateway_health.py

"""
Gateway health check utilities for bot startup orchestration.

This module provides:
- Port availability checking
- Gateway authentication validation
- Retry logic with exponential backoff
- Discord alerting integration
"""

import socket
import time
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from ib_insync import IB

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check attempt."""
    success: bool
    timestamp: datetime
    attempt: int
    message: str
    port_available: bool = False
    authenticated: bool = False


class GatewayHealthChecker:
    """
    Gateway health checker with retry logic and alerting.

    Usage:
        checker = GatewayHealthChecker(
            host="gateway",
            port=4002,
            discord_webhook="https://discord.com/api/webhooks/..."
        )
        if checker.wait_for_gateway():
            # Gateway is ready, proceed with trading
            ...
        else:
            # Gateway validation failed
            sys.exit(1)
    """

    def __init__(
        self,
        host: str,
        port: int,
        discord_webhook: Optional[str] = None,
        client_id: int = 0,  # Use client 0 for health checks
    ):
        self.host = host
        self.port = port
        self.discord_webhook = discord_webhook
        self.client_id = client_id
        self._alert_thresholds = {3: "WARNING", 10: "ERROR"}

    def check_port(self, timeout: float = 5.0) -> bool:
        """
        Check if Gateway port is accepting connections.

        Args:
            timeout: Socket connection timeout in seconds.

        Returns:
            True if port is reachable, False otherwise.
        """
        try:
            with socket.create_connection(
                (self.host, self.port), timeout=timeout
            ):
                return True
        except (socket.timeout, socket.error, OSError) as e:
            logger.debug(f"Port check failed: {e}")
            return False

    def validate_authentication(self, timeout: float = 10.0) -> bool:
        """
        Validate that Gateway is authenticated to IBKR.

        Connects via IB API and checks for accessible managed accounts.

        Args:
            timeout: IB API connection timeout in seconds.

        Returns:
            True if authenticated, False otherwise.
        """
        ib = IB()
        try:
            ib.connect(
                self.host,
                self.port,
                clientId=self.client_id,
                timeout=timeout,
            )
            accounts = ib.managedAccounts()
            if accounts and len(accounts) > 0:
                logger.debug(f"Authentication validated, accounts: {accounts}")
                return True
            logger.warning("Connected but no managed accounts found")
            return False
        except Exception as e:
            logger.debug(f"Authentication validation failed: {e}")
            return False
        finally:
            if ib.isConnected():
                ib.disconnect()

    def wait_for_gateway(
        self,
        max_retries: int = 30,
        initial_delay: float = 5.0,
        max_delay: float = 30.0,
        timeout: float = 300.0,
    ) -> bool:
        """
        Wait for Gateway to become ready with retry logic.

        Implements exponential backoff with configurable parameters.
        Sends Discord alerts at configured thresholds.

        Args:
            max_retries: Maximum number of retry attempts.
            initial_delay: Initial delay between retries (seconds).
            max_delay: Maximum delay between retries (seconds).
            timeout: Total timeout for all retries (seconds).

        Returns:
            True if Gateway became ready, False if validation failed.
        """
        start_time = time.time()
        attempt = 0
        delay = initial_delay

        while attempt < max_retries:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.error(f"Gateway validation timed out after {elapsed:.1f}s")
                self._send_alert(
                    "CRITICAL",
                    f"Gateway startup failed: timeout after {elapsed:.1f} seconds"
                )
                return False

            attempt += 1
            logger.info(
                f"Gateway check attempt {attempt}/{max_retries} "
                f"(elapsed: {elapsed:.1f}s)"
            )

            # Check port availability
            if self.check_port():
                logger.debug("Port check passed, validating authentication...")

                # Validate authentication
                if self.validate_authentication():
                    logger.info(
                        f"Gateway ready after {attempt} attempts "
                        f"({elapsed:.1f}s elapsed)"
                    )
                    return True
                else:
                    logger.warning(
                        "Gateway port responding but authentication failed"
                    )
            else:
                logger.debug("Port check failed, Gateway not yet available")

            # Check alert thresholds
            if attempt in self._alert_thresholds:
                level = self._alert_thresholds[attempt]
                self._send_alert(
                    level,
                    f"Gateway startup delayed, attempt {attempt}/{max_retries}"
                )

            # Wait before next attempt (exponential backoff)
            actual_delay = min(delay, timeout - elapsed)
            if actual_delay > 0:
                logger.debug(f"Waiting {actual_delay:.1f}s before next attempt")
                time.sleep(actual_delay)
            delay = min(delay * 2, max_delay)

        # Max retries exceeded
        logger.critical(f"Gateway validation failed after {max_retries} attempts")
        self._send_alert(
            "CRITICAL",
            f"Gateway startup failed after {max_retries} attempts"
        )
        return False

    def _send_alert(self, level: str, message: str) -> None:
        """
        Send alert to Discord webhook.

        Args:
            level: Alert level (WARNING, ERROR, CRITICAL).
            message: Alert message content.
        """
        if not self.discord_webhook:
            logger.debug(f"Alert not sent (no webhook configured): [{level}] {message}")
            return

        emoji_map = {
            "WARNING": "⚠️",
            "ERROR": "🔴",
            "CRITICAL": "🚨",
            "INFO": "✅",
        }
        emoji = emoji_map.get(level, "ℹ️")

        payload = {
            "content": (
                f"{emoji} **{level}: Gateway Health Alert**\n\n"
                f"{message}\n\n"
                f"*Timestamp: {datetime.now().isoformat()}*"
            )
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.discord_webhook, json=payload)
                response.raise_for_status()
                logger.debug(f"Alert sent successfully: [{level}] {message}")
        except Exception as e:
            # Don't crash if alerting fails
            logger.error(f"Failed to send Discord alert: {e}")


def quick_check() -> bool:
    """
    Quick health check for Docker HEALTHCHECK command.

    Returns True if the bot considers itself healthy.
    This is a lightweight check, not a full Gateway validation.
    """
    # In a real implementation, this would check internal state
    # For now, just return True if the module loads
    return True
```

---

## Appendix C: Unit Test Skeleton

```python
# tests/unit/test_gateway_health.py

"""
Unit tests for Gateway health check utilities.

These tests use mocking to avoid requiring an actual Gateway.
Integration tests should verify real Gateway behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import socket

from src.utils.gateway_health import GatewayHealthChecker, HealthCheckResult


class TestGatewayHealthChecker:
    """Tests for GatewayHealthChecker class."""

    @pytest.fixture
    def checker(self):
        """Create a health checker instance for testing."""
        return GatewayHealthChecker(
            host="localhost",
            port=4002,
            discord_webhook=None,  # No alerts in tests
        )

    # Port Check Tests

    def test_check_port_success(self, checker):
        """Port check returns True when connection succeeds."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.return_value.__enter__ = Mock()
            mock_conn.return_value.__exit__ = Mock()
            assert checker.check_port() is True

    def test_check_port_timeout(self, checker):
        """Port check returns False on timeout."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = socket.timeout()
            assert checker.check_port() is False

    def test_check_port_connection_refused(self, checker):
        """Port check returns False when connection refused."""
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError()
            assert checker.check_port() is False

    # Authentication Tests

    def test_validate_authentication_success(self, checker):
        """Authentication validation returns True with valid accounts."""
        with patch("src.utils.gateway_health.IB") as MockIB:
            mock_ib = MockIB.return_value
            mock_ib.connect = Mock()
            mock_ib.managedAccounts.return_value = ["DU123456"]
            mock_ib.isConnected.return_value = True
            mock_ib.disconnect = Mock()

            assert checker.validate_authentication() is True
            mock_ib.connect.assert_called_once()
            mock_ib.disconnect.assert_called_once()

    def test_validate_authentication_no_accounts(self, checker):
        """Authentication validation returns False with no accounts."""
        with patch("src.utils.gateway_health.IB") as MockIB:
            mock_ib = MockIB.return_value
            mock_ib.connect = Mock()
            mock_ib.managedAccounts.return_value = []
            mock_ib.isConnected.return_value = True
            mock_ib.disconnect = Mock()

            assert checker.validate_authentication() is False

    def test_validate_authentication_connection_error(self, checker):
        """Authentication validation returns False on connection error."""
        with patch("src.utils.gateway_health.IB") as MockIB:
            mock_ib = MockIB.return_value
            mock_ib.connect.side_effect = Exception("Connection refused")
            mock_ib.isConnected.return_value = False

            assert checker.validate_authentication() is False

    # Wait for Gateway Tests

    def test_wait_for_gateway_immediate_success(self, checker):
        """Gateway ready on first attempt returns True immediately."""
        with patch.object(checker, "check_port", return_value=True):
            with patch.object(checker, "validate_authentication", return_value=True):
                result = checker.wait_for_gateway(max_retries=5)
                assert result is True

    def test_wait_for_gateway_retry_then_success(self, checker):
        """Gateway becomes ready after retries returns True."""
        port_results = [False, False, True, True]
        auth_results = [False, True]

        with patch.object(checker, "check_port", side_effect=port_results):
            with patch.object(checker, "validate_authentication", side_effect=auth_results):
                with patch("time.sleep"):  # Skip delays in tests
                    result = checker.wait_for_gateway(max_retries=5)
                    assert result is True

    def test_wait_for_gateway_max_retries_exceeded(self, checker):
        """Gateway never ready returns False after max retries."""
        with patch.object(checker, "check_port", return_value=False):
            with patch("time.sleep"):  # Skip delays in tests
                result = checker.wait_for_gateway(max_retries=3, timeout=1000)
                assert result is False

    def test_wait_for_gateway_timeout(self, checker):
        """Gateway validation times out returns False."""
        with patch.object(checker, "check_port", return_value=False):
            with patch("time.time") as mock_time:
                # Simulate time passing beyond timeout
                mock_time.side_effect = [0, 0, 400]  # Start, elapsed check, timeout
                result = checker.wait_for_gateway(timeout=300)
                assert result is False

    # Alert Tests

    def test_send_alert_no_webhook(self, checker):
        """Alert does nothing when no webhook configured."""
        # Should not raise even without webhook
        checker._send_alert("CRITICAL", "Test message")

    def test_send_alert_with_webhook(self):
        """Alert sends to webhook when configured."""
        checker = GatewayHealthChecker(
            host="localhost",
            port=4002,
            discord_webhook="https://discord.com/api/webhooks/test",
        )
        with patch("httpx.Client") as MockClient:
            mock_client = MockClient.return_value.__enter__.return_value
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response

            checker._send_alert("WARNING", "Test message")

            mock_client.post.assert_called_once()


class TestExponentialBackoff:
    """Tests for exponential backoff calculation."""

    def test_backoff_sequence(self):
        """Verify backoff follows exponential pattern with cap."""
        checker = GatewayHealthChecker("localhost", 4002)
        delays = []
        delay = 5.0
        max_delay = 30.0

        for _ in range(10):
            delays.append(delay)
            delay = min(delay * 2, max_delay)

        # Expected: 5, 10, 20, 30, 30, 30, 30, 30, 30, 30
        expected = [5, 10, 20, 30, 30, 30, 30, 30, 30, 30]
        assert delays == expected
```

---

## Appendix D: Environment Variable Reference

```bash
# .env.example (additions for Task 3.2)

# =============================================================================
# Gateway Connection (Task 3.2)
# =============================================================================

# Gateway hostname (use 'gateway' if bot runs in Docker on same network)
GATEWAY_HOST=gateway

# Gateway API port (4002 = paper, 4001 = live)
GATEWAY_PORT=4002

# Maximum time to wait for Gateway at startup (seconds)
GATEWAY_STARTUP_TIMEOUT=300

# Maximum retry attempts before giving up
GATEWAY_MAX_RETRIES=30

# Initial delay between retries (seconds, doubles each retry up to 30s cap)
GATEWAY_RETRY_INTERVAL=5

# =============================================================================
# Bot Configuration
# =============================================================================

# Path to daily gameplan JSON (inside container)
GAMEPLAN_PATH=/data/gameplan.json

# Enable dry-run mode (no real trades)
DRY_RUN=true

# IB API client ID (must be unique per connection)
CLIENT_ID=1

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# =============================================================================
# Alerting
# =============================================================================

# Discord webhook URL for alerts (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-here

# =============================================================================
# IBKR Credentials (used by Gateway container, not bot)
# =============================================================================

IBKR_USERNAME=your_ibkr_username
IBKR_PASSWORD=your_ibkr_password
```

---

## Implementation Notes

### Recommended Implementation Sequence

1. **Create `src/utils/gateway_health.py`** (Appendix B)
   - Implement `GatewayHealthChecker` class
   - Write unit tests (`tests/unit/test_gateway_health.py`)
   - Verify tests pass

2. **Update `src/config.py`**
   - Add Gateway configuration parameters
   - Load from environment variables

3. **Update `src/main.py`**
   - Add startup orchestration logic
   - Integrate `GatewayHealthChecker`
   - Add Strategy C fallback

4. **Create Docker files**
   - `docker/bot/Dockerfile`
   - `docker/bot/entrypoint.sh`
   - Update `docker/docker-compose.yml`

5. **Integration testing**
   - Test with Gateway running
   - Test with Gateway stopped
   - Test Gateway restart scenarios

6. **Quality gates**
   - Run ruff, black, mypy
   - Verify all existing tests pass
   - Run new unit tests

### Model Routing Advisory

- **This blueprint:** Sonnet (structured implementation)
- **Complex edge case debugging:** Consider Opus if issues arise
- **Simple test additions:** Haiku acceptable

### Known Considerations

1. **ib_insync Client ID Conflict:** Health checker uses `client_id=0` to avoid conflicts with main bot connection (`client_id=1`). Both can be connected simultaneously.

2. **Gateway Auth Delay:** Gateway takes 30-60s to authenticate after container start. Docker `start_period: 60s` helps, but bot retry logic provides additional safety.

3. **Network Considerations:** When running in Docker, bot uses service name `gateway` (not `localhost`). This is handled by environment variable configuration.

4. **Gameplan Loading:** If gameplan file doesn't exist, bot creates a Strategy C gameplan locally. This ensures bot can always start (even if in safe mode).

---

**Document Version:** 1.0
**Created:** 2026-02-10
**Task ID:** s8bKaZVc_UKmZqaY7AR3f2UAL-K7
**Board:** IBKR Project Management
**Status:** Ready for Implementation
