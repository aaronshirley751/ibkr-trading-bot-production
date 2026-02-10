# VSC HANDOFF: Task 3.3 — Health Check Monitoring System

**Date:** 2026-02-10
**Task ID:** ObBJqkKB9U-uGgmsz_5MN2UAMDSE
**Board:** IBKR Project Management
**Requested By:** P3-S7 Handoff Prompt
**Designed By:** @Systems_Architect + @DevOps

---

## Model Routing Recommendation

**Recommended Model:** Sonnet
**Context Budget:** Light-Moderate
**Estimated Token Cost:** ~8K input + 3K output
**Extended Thinking:** Not required (straightforward implementation logic)

**Rationale:** This is a structured monitoring implementation with clear logic flow and well-defined health check patterns. Sonnet handles this complexity efficiently. Reserve Opus for complex architectural decisions or multi-system integration challenges.

---

# AGENT EXECUTION BLOCK

## 1. Objective

Implement an external health check monitoring system that:
- Validates IBKR Gateway and trading bot health continuously
- Detects failures via Docker API, port checks, and resource monitoring
- Sends Discord alerts with appropriate severity levels (INFO, WARNING, ERROR, CRITICAL)
- Attempts automatic Gateway recovery on failure (single attempt only)
- Operates independently as a dedicated Docker container
- Provides defense-in-depth monitoring without coupling to bot or Gateway code

This monitoring system acts as an external observer, detecting and alerting on system failures that could impact trading operations. It does NOT monitor trading performance (P&L, strategy execution) — only infrastructure health.

---

## 2. File Structure

### New Files to Create

**Monitoring Application:**
```
monitoring/
├── health_check.py          # Main monitoring logic and orchestration
├── discord_alerts.py        # Discord webhook integration with severity formatting
├── docker_utils.py          # Docker SDK interactions (container health, restart)
├── config.py                # Configuration loading from environment variables
├── models.py                # Data structures for health status
├── alert_throttle.py        # De-duplication and throttling for Discord alerts
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image for monitoring service
└── .env.example             # Configuration template with all parameters
```

**Integration Updates:**
```
docker/
├── docker-compose.yml       # Add monitoring service definition
└── .env                     # Add monitoring environment variables (operator creates from .env.example)
```

**Optional (if bot monitoring via heartbeat chosen):**
```
src/
└── heartbeat.py             # Bot writes heartbeat file with connection status
```

### Files to Modify

**docker/docker-compose.yml:**
- Add `health-monitor` service definition
- Configure volumes for Docker socket access
- Set restart policy to `unless-stopped`
- Link to Gateway container for health checks

---

## 3. Logic Flow (Pseudo-code)

### Main Monitoring Loop (`health_check.py`)

```python
def main():
    """
    Main monitoring loop - runs continuously in container.
    """
    config = load_config_from_env()  # Load thresholds, webhook URL, intervals
    alert_throttle = AlertThrottle(config.ALERT_COOLDOWN_SECONDS)
    docker_client = initialize_docker_client()

    log_info("Health monitoring system started")
    send_discord_alert(severity="INFO", message="Health monitoring system started")

    while True:
        try:
            # Phase 1: Check Gateway health
            gateway_status, gateway_details = check_gateway_health(docker_client, config)

            # Phase 2: Handle Gateway failures
            if gateway_status == "down":
                handle_gateway_failure(docker_client, config, alert_throttle)
            elif gateway_status == "degraded":
                handle_gateway_degradation(gateway_details, alert_throttle)
            elif gateway_status == "healthy":
                handle_gateway_recovery(alert_throttle)  # Clear alerts if previously failing

            # Phase 3: Check bot health (optional - see decision below)
            if config.MONITOR_BOT_HEALTH:
                bot_status, bot_details = check_bot_health(docker_client, config)
                handle_bot_status(bot_status, bot_details, alert_throttle)

            # Phase 4: Check system health (optional)
            if config.MONITOR_SYSTEM_HEALTH:
                system_status = check_system_health()
                handle_system_status(system_status, alert_throttle)

            # Phase 5: Sleep until next check
            sleep(config.HEALTH_CHECK_INTERVAL_SECONDS)

        except Exception as e:
            log_error(f"Monitoring loop error: {e}")
            send_discord_alert(
                severity="ERROR",
                message=f"Monitoring system encountered error: {str(e)}"
            )
            sleep(config.ERROR_RECOVERY_INTERVAL_SECONDS)  # Longer sleep on error
```

### Gateway Health Check (`docker_utils.py`)

```python
def check_gateway_health(docker_client, config) -> tuple[str, dict]:
    """
    Check Gateway container health via multiple validators.

    Returns:
        status: "healthy" | "degraded" | "down"
        details: {
            "container_running": bool,
            "port_responding": bool,
            "memory_usage_mb": int,
            "container_status": str,
            "uptime_seconds": int
        }
    """
    details = {}

    # Check 1: Container exists and is running
    try:
        container = docker_client.containers.get(config.GATEWAY_CONTAINER_NAME)
        details["container_running"] = container.status == "running"
        details["container_status"] = container.status
        details["uptime_seconds"] = calculate_uptime(container)
    except docker.errors.NotFound:
        details["container_running"] = False
        details["container_status"] = "not_found"
        return "down", details
    except Exception as e:
        log_error(f"Docker API error checking Gateway container: {e}")
        return "down", details

    # If container not running, Gateway is down
    if not details["container_running"]:
        return "down", details

    # Check 2: Port 4002 responding
    details["port_responding"] = check_port_connection(
        host=config.GATEWAY_HOST,
        port=config.GATEWAY_PORT,
        timeout=config.PORT_CHECK_TIMEOUT_SECONDS
    )

    # Check 3: Memory usage
    try:
        stats = container.stats(stream=False)
        memory_usage_bytes = stats["memory_stats"]["usage"]
        details["memory_usage_mb"] = memory_usage_bytes / (1024 * 1024)
    except Exception as e:
        log_warning(f"Failed to get Gateway memory stats: {e}")
        details["memory_usage_mb"] = None

    # Determine status from checks
    if not details["port_responding"]:
        return "down", details  # Port not responding = Gateway unusable

    # Gateway is up, check if degraded
    if details["memory_usage_mb"] is not None:
        if details["memory_usage_mb"] > config.MEMORY_CRITICAL_MB:
            return "degraded", details  # Memory leak detected
        elif details["memory_usage_mb"] > config.MEMORY_WARNING_MB:
            details["memory_warning"] = True

    return "healthy", details


def check_port_connection(host: str, port: int, timeout: int) -> bool:
    """
    Test if Gateway port is accepting connections.
    """
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        log_error(f"Port check error: {e}")
        return False


def calculate_uptime(container) -> int:
    """
    Calculate container uptime in seconds.
    """
    from dateutil import parser
    from datetime import datetime, timezone

    started_at = container.attrs["State"]["StartedAt"]
    started_time = parser.isoparse(started_at)
    now = datetime.now(timezone.utc)
    uptime = (now - started_time).total_seconds()
    return int(uptime)
```

### Gateway Failure Handling (`health_check.py`)

```python
def handle_gateway_failure(docker_client, config, alert_throttle):
    """
    Gateway is down - attempt auto-recovery, send alerts.
    """
    alert_key = "gateway_down"

    # Check if we've already alerted and attempted recovery recently
    if alert_throttle.should_throttle(alert_key):
        log_info("Gateway down, but alert throttled (recently sent)")
        return

    # Send initial failure alert
    send_discord_alert(
        severity="ERROR",
        title="Gateway Down",
        message="IBKR Gateway container is not running or port 4002 is unresponsive.",
        fields={
            "Container": config.GATEWAY_CONTAINER_NAME,
            "Expected Port": config.GATEWAY_PORT,
            "Action": "Attempting auto-recovery..."
        }
    )

    # Attempt Gateway restart (max 1 attempt per failure)
    recovery_success = attempt_gateway_restart(docker_client, config)

    if recovery_success:
        send_discord_alert(
            severity="INFO",
            title="Gateway Recovery Successful",
            message="Gateway container restarted and port 4002 is now responding.",
            fields={
                "Container": config.GATEWAY_CONTAINER_NAME,
                "Recovery Time": f"{datetime.now()}"
            }
        )
        alert_throttle.record_alert(alert_key)  # Throttle future alerts
    else:
        send_discord_alert(
            severity="CRITICAL",
            title="Gateway Recovery Failed",
            message="Automatic Gateway restart failed. Manual intervention required.",
            fields={
                "Container": config.GATEWAY_CONTAINER_NAME,
                "Action Required": "Operator must investigate Gateway logs and restart manually"
            },
            ping_operator=True  # @mention operator in Discord
        )
        alert_throttle.record_alert(alert_key)


def attempt_gateway_restart(docker_client, config) -> bool:
    """
    Attempt to restart Gateway container.

    Returns:
        True if restart successful and port responding
        False if restart failed or port still unresponsive
    """
    try:
        container = docker_client.containers.get(config.GATEWAY_CONTAINER_NAME)

        log_info(f"Restarting Gateway container {config.GATEWAY_CONTAINER_NAME}")
        container.restart(timeout=config.GATEWAY_RESTART_TIMEOUT_SECONDS)

        # Wait for Gateway to be ready (give it time to initialize)
        import time
        for attempt in range(config.GATEWAY_READY_MAX_ATTEMPTS):
            time.sleep(config.GATEWAY_READY_CHECK_INTERVAL_SECONDS)

            if check_port_connection(
                host=config.GATEWAY_HOST,
                port=config.GATEWAY_PORT,
                timeout=config.PORT_CHECK_TIMEOUT_SECONDS
            ):
                log_info("Gateway restart successful - port responding")
                return True

        log_error("Gateway restarted but port not responding after timeout")
        return False

    except docker.errors.NotFound:
        log_error("Gateway container not found - cannot restart")
        return False
    except Exception as e:
        log_error(f"Gateway restart failed: {e}")
        return False
```

### Gateway Degradation Handling

```python
def handle_gateway_degradation(details: dict, alert_throttle):
    """
    Gateway is running but showing warning signs (high memory).
    """
    alert_key = "gateway_degraded"

    if alert_throttle.should_throttle(alert_key):
        return

    memory_mb = details.get("memory_usage_mb")

    send_discord_alert(
        severity="WARNING",
        title="Gateway Memory Usage High",
        message="Gateway container memory usage approaching leak threshold.",
        fields={
            "Memory Usage": f"{memory_mb:.1f} MB",
            "Warning Threshold": f"{config.MEMORY_WARNING_MB} MB",
            "Critical Threshold": f"{config.MEMORY_CRITICAL_MB} MB",
            "Recommended Action": "Monitor closely. Gateway will auto-restart at scheduled time (4:30 PM)."
        }
    )

    alert_throttle.record_alert(alert_key)
```

### Bot Health Check (Optional — See Decision Below)

```python
def check_bot_health(docker_client, config) -> tuple[str, dict]:
    """
    Check bot health - implementation depends on bot deployment method.

    Option 1: Bot runs as Docker container
    Option 2: Bot runs as native process
    Option 3: Bot writes heartbeat file (monitoring reads it)

    Returns:
        status: "running" | "idle" | "stopped" | "unknown"
        details: {
            "process_running": bool,
            "last_heartbeat": datetime | None,
            "gateway_connected": bool | None
        }
    """
    # Implementation depends on operator's bot deployment choice
    # See Section 8 for decision matrix

    if config.BOT_DEPLOYMENT_MODE == "container":
        return check_bot_container(docker_client, config)
    elif config.BOT_DEPLOYMENT_MODE == "heartbeat":
        return check_bot_heartbeat(config)
    else:
        return "unknown", {}
```

### Discord Alert Formatting (`discord_alerts.py`)

```python
def send_discord_alert(
    severity: str,
    title: str,
    message: str,
    fields: dict = None,
    ping_operator: bool = False
):
    """
    Send formatted Discord webhook alert with severity-based styling.

    severity: INFO | WARNING | ERROR | CRITICAL
    """
    import requests
    from config import config

    # Severity color mapping
    colors = {
        "INFO": 0x00FF00,      # Green
        "WARNING": 0xFFFF00,   # Yellow
        "ERROR": 0xFF0000,     # Red
        "CRITICAL": 0xFF0000   # Red (same as ERROR)
    }

    # Severity emoji mapping
    emojis = {
        "INFO": "🟢",
        "WARNING": "🟡",
        "ERROR": "🔴",
        "CRITICAL": "🚨"
    }

    embed = {
        "title": f"{emojis.get(severity, '')} {title}",
        "description": message,
        "color": colors.get(severity, 0x808080),
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {
            "text": f"Charter & Stone Health Monitor | {severity}"
        }
    }

    if fields:
        embed["fields"] = [
            {"name": k, "value": str(v), "inline": True}
            for k, v in fields.items()
        ]

    content = ""
    if ping_operator and config.DISCORD_OPERATOR_MENTION:
        content = f"<@{config.DISCORD_OPERATOR_MENTION}>"

    payload = {
        "content": content,
        "embeds": [embed]
    }

    try:
        response = requests.post(
            config.DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        log_info(f"Discord alert sent: {severity} - {title}")
    except Exception as e:
        log_error(f"Failed to send Discord alert: {e}")
        # Don't fail monitoring if Discord is down - just log
```

### Alert Throttling (`alert_throttle.py`)

```python
class AlertThrottle:
    """
    Prevents alert spam by tracking recent alerts and enforcing cooldown periods.
    """

    def __init__(self, cooldown_seconds: int = 300):
        """
        cooldown_seconds: Minimum time between identical alerts (default 5 min)
        """
        self.cooldown_seconds = cooldown_seconds
        self.last_alert_time: dict[str, datetime] = {}

    def should_throttle(self, alert_key: str) -> bool:
        """
        Returns True if this alert should be suppressed (sent recently).
        """
        if alert_key not in self.last_alert_time:
            return False

        last_time = self.last_alert_time[alert_key]
        elapsed = (datetime.now() - last_time).total_seconds()

        return elapsed < self.cooldown_seconds

    def record_alert(self, alert_key: str):
        """
        Record that an alert was sent.
        """
        self.last_alert_time[alert_key] = datetime.now()

    def clear_alert(self, alert_key: str):
        """
        Clear alert throttle (for recovery notifications).
        """
        if alert_key in self.last_alert_time:
            del self.last_alert_time[alert_key]
```

---

## 4. Dependencies

### Python Libraries

Add to `monitoring/requirements.txt`:

```txt
docker==7.0.0          # Docker SDK for Python (container management)
requests==2.31.0       # Discord webhook HTTP calls
python-dateutil==2.8.2 # Timestamp parsing for container uptime
pydantic==2.5.0        # Configuration validation
pydantic-settings==2.1.0  # Environment variable loading

# Optional dependencies
# psutil==5.9.6        # System resource monitoring (disk, CPU)
```

### System Dependencies

- **Docker Engine:** Must be accessible via `/var/run/docker.sock` (mounted in container)
- **Network Access:** Monitoring container must reach Gateway port 4002 and Discord webhook URL
- **Python 3.11+:** Match bot environment for consistency

### Integration with Existing Stack

- **Gateway (Task 3.1):** Monitoring restarts Gateway container via Docker API
- **Bot (Task 3.2):** Optional bot health monitoring (see decision below)
- **Docker Compose:** Monitoring service added to existing compose file

---

## 5. Input/Output Contract

### Input: Environment Variables

Configuration loaded from `.env` file or environment:

```bash
# Discord Integration
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...  # REQUIRED
DISCORD_OPERATOR_MENTION=123456789012345678  # Optional: Discord user ID for @mentions

# Gateway Configuration
GATEWAY_CONTAINER_NAME=gateway  # Docker container name from Task 3.1
GATEWAY_HOST=localhost          # Gateway hostname (localhost if same machine)
GATEWAY_PORT=4002               # Gateway API port
GATEWAY_RESTART_TIMEOUT_SECONDS=30  # Docker restart timeout
GATEWAY_READY_MAX_ATTEMPTS=12       # Max attempts to verify port after restart
GATEWAY_READY_CHECK_INTERVAL_SECONDS=5  # Interval between ready checks

# Health Check Configuration
HEALTH_CHECK_INTERVAL_SECONDS=60     # How often to check Gateway health
PORT_CHECK_TIMEOUT_SECONDS=3         # Timeout for port connection test
ERROR_RECOVERY_INTERVAL_SECONDS=120  # Sleep longer after monitoring errors

# Memory Thresholds
MEMORY_WARNING_MB=1536   # 1.5 GB - send warning
MEMORY_CRITICAL_MB=1740  # 1.7 GB - send error (near restart threshold)

# Alert Throttling
ALERT_COOLDOWN_SECONDS=300  # 5 minutes between duplicate alerts

# Bot Monitoring (Optional)
MONITOR_BOT_HEALTH=false          # Enable bot health checks
BOT_DEPLOYMENT_MODE=none          # none | container | heartbeat
BOT_CONTAINER_NAME=trading-bot    # If container mode
BOT_HEARTBEAT_FILE=/data/bot_heartbeat.json  # If heartbeat mode

# System Monitoring (Optional)
MONITOR_SYSTEM_HEALTH=false       # Enable system resource checks
DISK_WARNING_PERCENT=80           # Disk usage warning threshold
```

### Output: Health Status

Monitoring produces three types of output:

1. **Structured Logs (JSON):** Written to stdout, captured by Docker
2. **Discord Alerts:** Webhook notifications with severity formatting
3. **Recovery Actions:** Automatic Gateway container restart on failure

**Log Format:**
```json
{
  "timestamp": "2026-02-10T14:32:15Z",
  "level": "INFO",
  "component": "health_monitor",
  "message": "Gateway health check completed",
  "details": {
    "status": "healthy",
    "container_running": true,
    "port_responding": true,
    "memory_usage_mb": 1245.3,
    "uptime_seconds": 3600
  }
}
```

---

## 6. Integration Points

### Gateway Container (Task 3.1)

**Integration:** Monitoring interacts with Gateway via Docker API

- **Health Check:** Validates container status, port connectivity, memory usage
- **Recovery:** Restarts Gateway container on failure
- **Assumptions:** Gateway container named `gateway`, exposed on port 4002

**Boundaries:**
- Monitoring does NOT modify Gateway configuration
- Monitoring does NOT inspect Gateway internal state (credentials, positions)
- Monitoring trusts Gateway's Docker health checks as secondary validation

### Bot Process (Task 3.2)

**Integration:** Optional bot health monitoring (see decision below)

- **If Enabled:** Bot health validated via container check or heartbeat file
- **If Disabled:** Monitoring focuses exclusively on Gateway infrastructure

**Boundaries:**
- Monitoring does NOT restart bot (bot may be stopped intentionally)
- Monitoring does NOT inspect bot trading logic or strategy state
- Bot should self-report critical errors via logging (monitoring may scan logs in future)

### Discord Webhook

**Integration:** Monitoring sends alerts to Discord channel via webhook

- **Webhook URL:** Configured via `DISCORD_WEBHOOK_URL` environment variable
- **Severity Levels:** INFO (green), WARNING (yellow), ERROR (red), CRITICAL (red + @mention)
- **Throttling:** Duplicate alerts suppressed for configurable cooldown period

**Boundaries:**
- Discord failure does NOT stop monitoring (logs error and continues)
- Monitoring assumes Discord webhooks are configured correctly (no retry logic for invalid URLs)

### Docker Compose Stack

**Integration:** Monitoring service added to existing `docker-compose.yml`

```yaml
services:
  gateway:
    # Existing Gateway service from Task 3.1
    ...

  health-monitor:
    build:
      context: ../monitoring
      dockerfile: Dockerfile
    container_name: health-monitor
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro  # Docker API access
    environment:
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
      - GATEWAY_CONTAINER_NAME=gateway
      - GATEWAY_HOST=gateway  # Use service name for Docker network
      - GATEWAY_PORT=4002
      # ... other config from .env
    depends_on:
      - gateway
    networks:
      - ibkr-network
```

---

## 7. Definition of Done

### Functional Requirements

- [ ] Monitoring script/container checks Gateway health every 1 minute
- [ ] Gateway container status validated (running vs. stopped)
- [ ] Gateway port 4002 connectivity validated (connection test)
- [ ] Gateway memory usage monitored (warning at 1.5GB, critical at 1.7GB)
- [ ] Discord alerts sent with appropriate severity (INFO, WARNING, ERROR, CRITICAL)
- [ ] Alert throttling prevents duplicate alerts within 5-minute cooldown
- [ ] Gateway auto-recovery attempted on failure (max 1 attempt)
- [ ] Recovery success/failure logged and alerted via Discord
- [ ] Monitoring container restarts automatically if it crashes (Docker restart policy)

### Configuration

- [ ] All configuration via environment variables (`.env` file)
- [ ] `.env.example` provided with all parameters documented
- [ ] Discord webhook URL validated at startup (test alert sent)
- [ ] Monitoring fails fast if required config missing (DISCORD_WEBHOOK_URL)

### Logging and Observability

- [ ] Logs structured as JSON (timestamp, level, component, message, details)
- [ ] Log rotation configured (prevent disk fill)
- [ ] Health check results logged at INFO level
- [ ] Errors logged at ERROR level with full exception details
- [ ] Monitoring startup logged with configuration summary

### Quality Gates

- [ ] Code passes `ruff` linter with zero warnings
- [ ] Code passes `black` formatter check
- [ ] Code passes `mypy` type checking
- [ ] Unit tests for health check logic (mock Docker API)
- [ ] Integration test simulates Gateway failure → restart → recovery
- [ ] Integration test validates alert throttling behavior

### Review Requirements

- [ ] @DevOps review: Monitoring container doesn't interfere with Gateway/bot operation
- [ ] @DevOps review: Docker socket permissions secure (read-only mount)
- [ ] @DevOps review: Resource usage acceptable (monitoring is lightweight)
- [ ] @QA_Lead review: Alert logic tested with simulated failures
- [ ] @QA_Lead review: Edge cases covered (see Section 8)
- [ ] @CRO review: No capital risk from monitoring operations (monitoring is read-only except Gateway restart)

---

## 8. Edge Cases to Test

### Gateway Failure Scenarios

**Test Case 1: Gateway Container Stopped**
- **Setup:** Stop Gateway container manually: `docker stop gateway`
- **Expected:** Monitoring detects → sends ERROR alert → attempts restart → sends recovery INFO alert
- **Validation:** Gateway port 4002 responding after restart

**Test Case 2: Gateway Container Stopped, Restart Fails**
- **Setup:** Remove Gateway container: `docker rm gateway` (restart cannot succeed)
- **Expected:** Monitoring detects → sends ERROR alert → restart fails → sends CRITICAL alert with @mention
- **Validation:** Operator receives Discord ping, monitoring continues checking

**Test Case 3: Gateway Port Unresponsive (Container Running)**
- **Setup:** Gateway container running but port 4002 not accepting connections (simulate with firewall rule?)
- **Expected:** Monitoring detects port failure → treats as "down" → restarts container
- **Validation:** Port responds after restart

**Test Case 4: Gateway Memory Usage High**
- **Setup:** Wait for Gateway memory to exceed 1.5GB (natural leak) or simulate with memory stress
- **Expected:** Monitoring sends WARNING alert (not ERROR)
- **Validation:** Alert severity is WARNING (yellow), message mentions scheduled restart at 4:30 PM

**Test Case 5: Gateway Memory Usage Critical**
- **Setup:** Wait for Gateway memory to exceed 1.7GB
- **Expected:** Monitoring sends ERROR alert (red)
- **Validation:** Monitoring does NOT restart Gateway (memory warning is not a restart trigger, only scheduled restart handles this)

### Alert Throttling Scenarios

**Test Case 6: Repeated Gateway Failures**
- **Setup:** Stop Gateway, wait for alert, stop again within 5 minutes
- **Expected:** First failure → ERROR alert sent. Second failure → alert throttled (not sent). After 5 min cooldown → alert sent again.
- **Validation:** Only 2 Discord messages in 10 minutes (not 10+ messages)

**Test Case 7: Gateway Recovers After Failure**
- **Setup:** Stop Gateway → monitoring restarts it → Gateway healthy
- **Expected:** ERROR alert on failure → INFO alert on recovery → subsequent health checks do NOT send INFO alerts (only state changes trigger alerts)
- **Validation:** Discord shows clear "down → recovered" narrative

### Monitoring System Failures

**Test Case 8: Discord Webhook Invalid**
- **Setup:** Set `DISCORD_WEBHOOK_URL` to invalid URL
- **Expected:** Monitoring logs error but CONTINUES health checks (Discord failure doesn't stop monitoring)
- **Validation:** Logs show "Failed to send Discord alert" but health checks continue every minute

**Test Case 9: Monitoring Container Crashes**
- **Setup:** Kill monitoring container process: `docker kill health-monitor`
- **Expected:** Docker restart policy (`unless-stopped`) restarts monitoring container automatically
- **Validation:** Monitoring resumes within 10 seconds, sends INFO "Monitoring started" alert

**Test Case 10: Docker Daemon Unreachable**
- **Setup:** Stop Docker daemon (or break `/var/run/docker.sock` mount)
- **Expected:** Monitoring logs error, sends CRITICAL alert "Cannot access Docker API"
- **Validation:** Monitoring does NOT crash, waits for Docker to recover

### Bot Health Monitoring (If Enabled)

**Test Case 11: Bot Stopped (Operator-Controlled)**
- **Setup:** Stop bot container: `docker stop trading-bot`
- **Expected:** Monitoring detects bot stopped → sends INFO alert (not ERROR) → "Bot stopped (may be intentional)"
- **Validation:** Operator is notified but not alarmed (bot stops are normal outside market hours)

**Test Case 12: Bot Crashed Unexpectedly**
- **Setup:** Bot exits with error code (simulated crash)
- **Expected:** Monitoring detects bot not running → checks if during market hours → sends WARNING or ERROR depending on time
- **Validation:** Severity reflects market hours context

### System Resource Monitoring (If Enabled)

**Test Case 13: Disk Space Low**
- **Setup:** Fill disk to 85% (above 80% warning threshold)
- **Expected:** Monitoring sends WARNING alert "Disk space low: 85% used"
- **Validation:** Alert includes disk path and usage percentage

**Test Case 14: Network Partition Prevents Discord**
- **Setup:** Block outbound HTTPS to Discord (firewall rule)
- **Expected:** Monitoring logs "Failed to send Discord alert" but continues health checks
- **Validation:** When network recovers, alerts resume (no queue — monitoring is stateless)

---

## 9. Rollback Plan

### Disable Monitoring Completely

**Method 1: Stop Container**
```bash
docker compose stop health-monitor
```
- Monitoring stops immediately
- Gateway and bot continue running
- No alerts sent

**Method 2: Remove Service**
```bash
# Comment out health-monitor service in docker-compose.yml
docker compose up -d --remove-orphans
```
- Monitoring container removed
- Gateway and bot unaffected

### Disable Auto-Recovery Only

**Method 1: Environment Variable**
```bash
# In .env file
MAX_RECOVERY_ATTEMPTS=0
```
- Monitoring continues health checks
- Discord alerts still sent
- Gateway NOT automatically restarted

**Method 2: Code Change (If Emergency)**
- Comment out `attempt_gateway_restart()` call in `handle_gateway_failure()`
- Rebuild monitoring container
- Monitoring detects failures but only alerts

### Revert to Manual Gateway Management

If monitoring proves unreliable:
1. Stop monitoring container: `docker compose stop health-monitor`
2. Operator manually restarts Gateway when needed: `docker restart gateway`
3. Monitoring can be re-enabled later after fixes

### Emergency Stop (Operator Override)

If monitoring is causing problems (e.g., restart loop):
```bash
# Stop monitoring immediately
docker kill health-monitor

# Prevent auto-restart
docker update --restart=no health-monitor
```

---

# CONTEXT BLOCK

## Task Dependencies and Continuity

### Task 3.1: Gateway Deployment (Completed)

**What Was Delivered:**
- IBKR Gateway running as Docker container `gateway`
- Gateway exposed on port 4002
- Gateway health check: `bash -c 'cat < /dev/tcp/localhost/4002'`
- Gateway scheduled restart at 4:30 PM ET (memory leak mitigation)
- Docker Compose configuration in `docker/gateway/docker-compose.yml`

**Integration Point:**
- Task 3.3 monitoring system interacts with this Gateway container via Docker API
- Monitoring validates Gateway health independently (defense-in-depth)
- Monitoring can restart Gateway on failure (Docker API: `container.restart()`)

**Assumptions:**
- Gateway container name is `gateway` (configurable via env var)
- Gateway port 4002 is the canonical health check endpoint
- Gateway memory leak pattern: gradual increase to ~1.7GB before scheduled restart

### Task 3.2: Bot Startup Orchestration (Completed)

**What Was Delivered:**
- Bot validates Gateway readiness at startup
- Bot waits for Gateway port 4002 to respond before trading
- Bot does NOT continuously monitor Gateway after startup

**Integration Point:**
- Task 3.3 monitoring fills the gap: continuous Gateway health checks
- Bot assumes Gateway remains available after initial check (Task 3.3 detects if assumption breaks)
- Bot does NOT need to implement health monitoring — that's Task 3.3's responsibility

**Boundaries:**
- Bot focuses on trading logic
- Monitoring focuses on infrastructure reliability
- Bot and monitoring are decoupled (monitoring doesn't depend on bot code)

### Task 3.3: Health Monitoring (This Task)

**What This Task Delivers:**
- External monitoring container watching Gateway health
- Discord alerts on Gateway failures
- Automatic Gateway recovery (single restart attempt)
- Optional bot health monitoring (decision required — see below)

**Next Steps (Future Tasks):**
- Task 3.4: Logs aggregation (if planned) — monitoring logs should integrate
- Task 3.5: Production deployment checklist — includes verifying monitoring operational
- Task 3.6: Runbook for operator response to alerts

---

## Architectural Decisions

### Decision 1: Monitoring Architecture ✅ DECIDED

**Option Chosen: Dedicated Monitoring Container (Option B)**

**Rationale:**
- **Decoupling:** Monitoring operates independently of cron, reducing failure modes
- **Reliability:** Docker restart policy provides automatic recovery of monitoring itself
- **Docker-native:** Monitoring already interacts with Docker API for Gateway health checks
- **Consistency:** Aligns with Docker Compose architecture from Task 3.1
- **Flexibility:** Can scale to monitor multiple services without cron complexity

**Trade-offs Accepted:**
- Slightly higher resource usage (monitoring container always running ~10-20MB memory)
- Monitoring requires Docker API access (`/var/run/docker.sock` mounted read-only)

**Alternative (Rejected):** Cron-based script (Option A)
- Simpler initial setup
- Lower resource usage (runs on-demand)
- BUT: Cron itself is a failure point, harder to monitor the monitor, less graceful for continuous checks

### Decision 2: Bot Health Monitoring ⚠️ OPERATOR DECISION REQUIRED

**Options:**

**Option A: No Bot Monitoring (Recommended for MVP)**
- Monitoring focuses exclusively on Gateway infrastructure
- Bot failures detected by operator (no automated alerts)
- Bot is expected to self-report critical errors via logging
- Simplest implementation, no bot coupling

**Option B: Bot Container Monitoring**
- Monitoring checks if bot container is running
- Limited visibility (container running ≠ bot healthy)
- Requires bot deployed as Docker container
- Adds complexity to monitoring logic

**Option C: Bot Heartbeat File**
- Bot writes heartbeat file with timestamp + connection status
- Monitoring reads heartbeat file to verify bot alive
- More informative than container check
- Requires bot code changes (add heartbeat logic)

**Recommendation:** Start with **Option A (No Bot Monitoring)** for MVP. Reasoning:
1. Gateway is the critical failure point — bot cannot trade without Gateway
2. Bot failures are less catastrophic (can be restarted manually without data loss)
3. Monitoring bot health requires assumptions about "healthy" vs "idle" (market hours context)
4. Can add bot monitoring in later sprint if needed (non-blocking)

**Operator Action Required:** Confirm bot monitoring strategy in `.env` configuration:
```bash
MONITOR_BOT_HEALTH=false  # MVP: Gateway only
# or
MONITOR_BOT_HEALTH=true
BOT_DEPLOYMENT_MODE=container  # or heartbeat
```

### Decision 3: Alert Severity Thresholds

**Gateway Down:** ERROR severity (red alert)
- **Trigger:** Container stopped OR port 4002 not responding
- **Action:** Auto-restart attempted, recovery result alerted
- **Rationale:** Gateway down = trading impossible, requires immediate attention

**Gateway Degraded:** WARNING severity (yellow alert)
- **Trigger:** Memory usage > 1.5GB (warning) or > 1.7GB (approaching critical)
- **Action:** Alert only, no auto-restart (scheduled restart at 4:30 PM handles this)
- **Rationale:** Memory leak is known issue, operator aware, not immediate crisis

**Monitoring Error:** ERROR severity (red alert)
- **Trigger:** Monitoring cannot access Docker API, Discord webhook fails repeatedly
- **Action:** Alert if possible, log error, continue checking
- **Rationale:** Monitoring failure = blind spot, operator must be aware

**Recovery Success:** INFO severity (green alert)
- **Trigger:** Gateway restarted and port responding again
- **Action:** Confirmation alert to operator
- **Rationale:** Operator needs closure on failure → recovery loop

### Decision 4: Auto-Recovery Strategy

**Gateway Auto-Restart:** YES (single attempt per failure)
- **Rationale:** Gateway failures are recoverable via restart, operator may not be watching 24/7
- **Limit:** Max 1 restart attempt per failure (prevents restart loop)
- **Escalation:** If restart fails → CRITICAL alert with @mention operator

**Bot Auto-Restart:** NO
- **Rationale:** Bot may be stopped intentionally (outside market hours, operator maintenance)
- **Manual Restart:** Operator must explicitly restart bot after investigating failure

---

## Alpha Learnings and Considerations

### Gateway Memory Leak Pattern

**Observed Behavior (from Task 3.1 testing):**
- Gateway memory usage increases gradually over time
- Peaks around 1.7GB by end of trading day
- Scheduled restart at 4:30 PM ET mitigates leak

**Monitoring Implications:**
- Memory warning at 1.5GB gives early signal
- Memory critical at 1.7GB indicates leak approaching scheduled restart
- Monitoring does NOT restart Gateway for memory warnings (only scheduled restart does this)
- If Gateway hits 1.7GB before scheduled restart → WARNING alert only (operator informed, not acted upon)

### Gateway Responsiveness Under Load

**Alpha Observation:** Gateway can become briefly unresponsive under market data load
- Typically recovers within seconds
- Not a failure requiring restart

**Monitoring Implications:**
- Port check timeout set to 3 seconds (allows brief unresponsiveness)
- Single failed port check does NOT trigger alert (wait for next check cycle)
- Only sustained port failure (2+ consecutive checks) triggers alert and recovery

### Defense-in-Depth Philosophy

**Layers of Health Validation:**
1. **Gateway's Built-in Health Check:** Docker validates port 4002 (internal)
2. **Bot Startup Check (Task 3.2):** Bot validates Gateway before trading (startup only)
3. **External Monitoring (Task 3.3):** Continuous validation from outside (this task)

**Why Multiple Layers:**
- Gateway's internal check can pass while API is unresponsive (edge case)
- Bot startup check is one-time (doesn't detect mid-session failures)
- External monitoring provides continuous verification and alerting

---

## Configuration Reference

### Environment Variables (Complete List)

```bash
# ============================================
# Discord Integration
# ============================================
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/abcdefghijk
# Required. Obtain from Discord: Server Settings > Integrations > Webhooks

DISCORD_OPERATOR_MENTION=123456789012345678
# Optional. Your Discord user ID for @mentions in CRITICAL alerts.
# To find: Right-click your name in Discord > Copy ID (Developer Mode enabled)

# ============================================
# Gateway Configuration
# ============================================
GATEWAY_CONTAINER_NAME=gateway
# Docker container name for IBKR Gateway (from Task 3.1)

GATEWAY_HOST=gateway
# Hostname or IP for Gateway. Use 'gateway' if on Docker network, 'localhost' if same machine

GATEWAY_PORT=4002
# IBKR Gateway API port (configured in Task 3.1)

GATEWAY_RESTART_TIMEOUT_SECONDS=30
# How long to wait for Gateway container restart command

GATEWAY_READY_MAX_ATTEMPTS=12
# How many times to check if Gateway port responds after restart (12 attempts * 5s = 60s max)

GATEWAY_READY_CHECK_INTERVAL_SECONDS=5
# Interval between port checks after restart

# ============================================
# Health Check Configuration
# ============================================
HEALTH_CHECK_INTERVAL_SECONDS=60
# How often to check Gateway health (every 1 minute recommended)

PORT_CHECK_TIMEOUT_SECONDS=3
# Timeout for port connection test (allows brief unresponsiveness)

ERROR_RECOVERY_INTERVAL_SECONDS=120
# If monitoring encounters error, sleep longer before retrying (2 minutes)

# ============================================
# Memory Thresholds
# ============================================
MEMORY_WARNING_MB=1536
# 1.5 GB - Send WARNING alert when Gateway memory exceeds this

MEMORY_CRITICAL_MB=1740
# 1.7 GB - Send ERROR alert (near scheduled restart threshold)

# ============================================
# Alert Throttling
# ============================================
ALERT_COOLDOWN_SECONDS=300
# Minimum time between duplicate alerts (5 minutes prevents spam)

# ============================================
# Bot Monitoring (Optional)
# ============================================
MONITOR_BOT_HEALTH=false
# Enable bot health checks (true | false). Recommended: false for MVP.

BOT_DEPLOYMENT_MODE=none
# Bot deployment type: none | container | heartbeat
# - none: No bot monitoring
# - container: Monitor bot Docker container
# - heartbeat: Monitor bot heartbeat file

BOT_CONTAINER_NAME=trading-bot
# Docker container name for bot (if BOT_DEPLOYMENT_MODE=container)

BOT_HEARTBEAT_FILE=/data/bot_heartbeat.json
# Path to bot heartbeat file (if BOT_DEPLOYMENT_MODE=heartbeat)

# ============================================
# System Monitoring (Optional)
# ============================================
MONITOR_SYSTEM_HEALTH=false
# Enable system resource monitoring (disk, Docker daemon)

DISK_WARNING_PERCENT=80
# Disk usage warning threshold (percent)
```

---

## Implementation Guidance

### Phase 1: Core Monitoring (MVP)

**Focus:** Gateway health checks, Discord alerts, auto-recovery

**Files to Create:**
1. `monitoring/health_check.py` — Main monitoring loop
2. `monitoring/docker_utils.py` — Gateway health check logic
3. `monitoring/discord_alerts.py` — Discord webhook integration
4. `monitoring/config.py` — Environment variable loading
5. `monitoring/alert_throttle.py` — Alert de-duplication
6. `monitoring/Dockerfile` — Container image
7. `monitoring/requirements.txt` — Dependencies
8. `monitoring/.env.example` — Configuration template

**Integration:**
- Update `docker/docker-compose.yml` to add `health-monitor` service
- Create `docker/.env` from `.env.example` (operator fills in Discord webhook URL)

**Testing:**
- Simulate Gateway failure: `docker stop gateway`
- Verify: ERROR alert sent, Gateway restarted, INFO recovery alert sent
- Verify: Alert throttling prevents spam (stop Gateway multiple times quickly)

### Phase 2: Bot Monitoring (Optional — Defer to Later Sprint)

**If Operator Chooses to Enable:**
- Decide on bot deployment mode (container vs. heartbeat)
- If heartbeat: Add heartbeat writing to bot code (`src/heartbeat.py`)
- Implement `check_bot_health()` in monitoring
- Add bot-specific alert logic

**Recommendation:** Implement Phase 1 first, validate in production, then add bot monitoring if needed.

### Phase 3: Advanced Features (Future)

**Potential Enhancements:**
- System resource monitoring (disk space, Docker daemon health)
- Gateway log scanning for error patterns
- Monitoring dashboard (web UI showing health history)
- Alert escalation (if repeated failures, escalate to phone/SMS)

---

## VSCode Copilot Implementation Tips

### Prompt Sequence for Factory Floor

**Step 1: Create Monitoring Directory Structure**
```
Create monitoring directory with files:
- health_check.py (main monitoring loop)
- docker_utils.py (Docker SDK interactions)
- discord_alerts.py (webhook integration)
- config.py (environment variable loading with pydantic)
- models.py (health status data structures)
- alert_throttle.py (de-duplication logic)
- requirements.txt (dependencies)
- Dockerfile (monitoring container image)
- .env.example (configuration template)
```

**Step 2: Implement Docker Health Checks**
```
In monitoring/docker_utils.py, implement check_gateway_health():
- Use docker.from_env() to get client
- Get Gateway container by name (config.GATEWAY_CONTAINER_NAME)
- Check container.status == "running"
- Check port connection with socket (timeout 3 seconds)
- Get container memory stats from container.stats()
- Return status (healthy/degraded/down) and details dict
```

**Step 3: Implement Discord Alerts**
```
In monitoring/discord_alerts.py, implement send_discord_alert():
- Accept severity (INFO/WARNING/ERROR/CRITICAL), title, message, fields, ping_operator
- Map severity to Discord embed colors (green/yellow/red)
- Add severity emoji (🟢/🟡/🔴/🚨)
- Build embed with timestamp and footer
- Send POST to config.DISCORD_WEBHOOK_URL
- Handle failures gracefully (log error, don't crash)
```

**Step 4: Implement Main Monitoring Loop**
```
In monitoring/health_check.py, implement main():
- Load config from environment
- Initialize Docker client and alert throttle
- Send startup INFO alert
- Loop forever:
  - Call check_gateway_health()
  - If down: handle_gateway_failure() (restart + alert)
  - If degraded: handle_gateway_degradation() (alert only)
  - Sleep HEALTH_CHECK_INTERVAL_SECONDS
- Catch exceptions, log errors, continue monitoring
```

**Step 5: Add to Docker Compose**
```
In docker/docker-compose.yml, add health-monitor service:
- Build from monitoring/Dockerfile
- Mount /var/run/docker.sock read-only
- Pass environment variables from .env
- Set restart: unless-stopped
- Depend on gateway service
```

**Step 6: Testing**
```
Test monitoring:
1. Start stack: docker compose up -d
2. Check monitoring logs: docker logs health-monitor -f
3. Simulate failure: docker stop gateway
4. Verify: ERROR alert in Discord, Gateway restarted, INFO alert sent
5. Simulate repeated failure: stop Gateway 3 times quickly
6. Verify: Only 1 ERROR alert sent (throttling works)
```

---

## Success Criteria

This VSC Handoff Document is considered complete and ready for Factory Floor implementation when:

✅ **Architecture Decision Made:** Monitoring container approach (Option B) confirmed
✅ **Bot Monitoring Decision Documented:** Operator aware of options, MVP defaults to no bot monitoring
✅ **File Structure Defined:** All files listed with clear purposes
✅ **Logic Flow Specified:** Pseudo-code covers main loop, health checks, failure handling, alerts
✅ **Dependencies Listed:** Python libraries, system requirements, integration points clear
✅ **Configuration Documented:** All environment variables explained with examples
✅ **Definition of Done:** Acceptance criteria enumerated, review gates identified
✅ **Edge Cases Enumerated:** Test scenarios cover failures, throttling, monitoring self-failures
✅ **Rollback Plan Provided:** Operator knows how to disable monitoring if needed
✅ **Integration Boundaries Clear:** Monitoring interacts with Gateway (Task 3.1), decoupled from bot (Task 3.2)

**Operator Next Steps:**
1. Review this handoff document
2. Confirm bot monitoring decision (default: disabled for MVP)
3. Proceed to Factory Floor (P3-S8) with VSCode + Copilot for implementation
4. Expected implementation time: 2-3 hours
5. Test with simulated Gateway failures before declaring Task 3.3 complete

---

**Document Version:** 1.0
**Date:** 2026-02-10
**Estimated Implementation Time:** 2-3 hours (Phase 1 MVP)
**Factory Floor Session:** P3-S8 (next session)
**Board Task:** ObBJqkKB9U-uGgmsz_5MN2UAMDSE
**Blocking Dependencies:** None (Tasks 3.1 and 3.2 complete)
