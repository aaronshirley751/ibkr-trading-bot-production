# Health Monitoring System

External health check monitoring for IBKR Gateway and trading bot infrastructure.

## Overview

The health monitoring system is a dedicated Docker container that continuously validates Gateway health and sends Discord alerts on failures. It provides defense-in-depth monitoring without coupling to bot or Gateway code.

**Key Features:**
- Gateway health checks (container status, port connectivity, memory usage)
- Discord alerts with severity levels (INFO, WARNING, ERROR, CRITICAL)
- Automatic Gateway recovery (single restart attempt on failure)
- Alert throttling to prevent spam
- Independent operation as external observer

## Architecture

```
monitoring/
├── health_check.py       # Main monitoring loop
├── docker_utils.py       # Docker SDK interactions
├── discord_alerts.py     # Discord webhook integration
├── config.py             # Configuration loading
├── models.py             # Data structures
├── alert_throttle.py     # Alert de-duplication
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container image
└── .env.example          # Configuration template
```

## Setup

### 1. Configure Discord Webhook

1. Go to Discord Server Settings > Integrations > Webhooks
2. Create a new webhook for your alerts channel
3. Copy the webhook URL

### 2. Configure Environment

Copy the example configuration:

```bash
cd docker
cp ../monitoring/.env.example .env
```

Edit `.env` and set required values:

```bash
# Required
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# Optional (for @mentions in CRITICAL alerts)
DISCORD_OPERATOR_MENTION=YOUR_DISCORD_USER_ID
```

### 3. Start Monitoring

The monitoring service is included in the main Docker Compose stack:

```bash
cd docker
docker compose up -d health-monitor
```

Verify monitoring is running:

```bash
docker logs health-monitor -f
```

You should see:
- "Health monitoring system started" in logs
- Green "Health Monitoring Started" alert in Discord

## Configuration

All configuration is via environment variables in `docker/.env`. See `monitoring/.env.example` for full documentation.

**Key Parameters:**
- `HEALTH_CHECK_INTERVAL_SECONDS=60` - Check Gateway every 60 seconds
- `MEMORY_WARNING_MB=1536` - Warning alert at 1.5GB memory
- `MEMORY_CRITICAL_MB=1740` - Critical alert at 1.7GB memory
- `ALERT_COOLDOWN_SECONDS=300` - 5 minutes between duplicate alerts

## Alert Severity Levels

| Severity | Color | Trigger | Action |
|----------|-------|---------|--------|
| 🟢 INFO | Green | Monitoring started, Gateway recovered | Informational |
| 🟡 WARNING | Yellow | Gateway memory > 1.5GB | Monitor closely |
| 🔴 ERROR | Red | Gateway down, monitoring error | Auto-recovery attempted |
| 🚨 CRITICAL | Red | Recovery failed | @mention operator |

## Health Check Validation

Monitoring validates Gateway health via:
1. **Container Status:** Docker container running/stopped
2. **Port Connectivity:** Port 4002 accepting connections
3. **Memory Usage:** Memory leak detection (warning/critical thresholds)

## Recovery Behavior

**Gateway Down:**
1. Send ERROR alert to Discord
2. Attempt Gateway container restart (max 1 attempt)
3. Wait up to 60 seconds for port 4002 to respond
4. Send INFO alert if successful, CRITICAL alert if failed

**Gateway Degraded (High Memory):**
1. Send WARNING alert (does NOT restart Gateway)
2. Monitoring continues (scheduled restart at 4:30 PM handles memory leak)

## Alert Throttling

Duplicate alerts suppressed for 5 minutes (configurable). Prevents spam if Gateway repeatedly fails.

**Example:**
- 10:00 AM - Gateway down → ERROR alert sent
- 10:01 AM - Gateway still down → alert throttled (not sent)
- 10:02 AM - Gateway still down → alert throttled (not sent)
- 10:06 AM - Gateway still down → ERROR alert sent again (cooldown expired)

## Testing

### Simulate Gateway Failure

```bash
# Stop Gateway container
docker stop ib-gateway

# Expected behavior:
# 1. Monitor detects failure within 60 seconds
# 2. ERROR alert sent to Discord
# 3. Monitor restarts Gateway
# 4. INFO recovery alert sent when port responds
```

### Simulate Repeated Failures

```bash
# Stop Gateway multiple times quickly
docker stop ib-gateway
sleep 10
docker stop ib-gateway
sleep 10
docker stop ib-gateway

# Expected behavior:
# Only 1 ERROR alert sent (throttling prevents spam)
```

### Check Monitoring Logs

```bash
# View structured JSON logs
docker logs health-monitor -f

# Search for health check results
docker logs health-monitor | grep "Gateway health check completed"
```

## Troubleshooting

### Monitoring Not Starting

**Symptom:** `health-monitor` container exits immediately

**Check:**
```bash
docker logs health-monitor
```

**Common Issues:**
- `DISCORD_WEBHOOK_URL` not set or invalid → Fix `.env` file
- Docker socket not accessible → Verify `/var/run/docker.sock` mount

### Discord Alerts Not Received

**Symptom:** Monitoring running but no Discord alerts

**Check:**
1. Verify webhook URL in `.env` is correct
2. Check Discord channel webhook still exists
3. Check monitoring logs for "Failed to send Discord alert"

**Note:** Discord failure does NOT stop monitoring - logs will continue

### Gateway Not Auto-Recovering

**Symptom:** Gateway down but not restarting

**Check:**
1. Verify Gateway container name matches `GATEWAY_CONTAINER_NAME` in `.env`
2. Check monitoring logs for "Gateway restart failed" errors
3. Verify Docker socket has write permissions (should be read-only, monitoring uses restart API)

## Rollback

### Disable Monitoring

Stop monitoring without affecting Gateway/bot:

```bash
docker compose stop health-monitor
```

### Remove Monitoring

```bash
# Remove from stack
docker compose rm -f health-monitor

# Optional: Comment out health-monitor service in docker-compose.yml
```

## MVP Scope

Current implementation (Phase 1):
- ✅ Gateway health monitoring
- ✅ Discord alerts with severity formatting
- ✅ Gateway auto-recovery (single attempt)
- ✅ Alert throttling

Optional features (future):
- ⏸️ Bot health monitoring (via container or heartbeat)
- ⏸️ System resource monitoring (disk space)
- ⏸️ Gateway log scanning for error patterns

To enable bot monitoring, set in `.env`:
```bash
MONITOR_BOT_HEALTH=true
BOT_DEPLOYMENT_MODE=container  # or heartbeat
```

## Integration with Task 3.1 (Gateway)

Monitoring interacts with Gateway container from Task 3.1:
- **Container Name:** `ib-gateway` (from docker-compose.yml)
- **Health Check:** Port 4002 connectivity
- **Recovery:** Docker API restart command
- **Boundaries:** Monitoring does NOT modify Gateway configuration or credentials

## Logs

Structured JSON logs include:
- `timestamp` - ISO 8601 UTC timestamp
- `level` - INFO, WARNING, ERROR
- `component` - Module name (e.g., `health_monitor`, `docker_utils`)
- `message` - Human-readable description
- `details` - Health check results (status, memory, uptime)

**Example:**
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

## Support

For issues or questions:
1. Check logs: `docker logs health-monitor -f`
2. Verify configuration: `docker exec health-monitor env | grep -E '(GATEWAY|DISCORD)'`
3. Review Discord channel for recent alerts
4. Refer to VSC_HANDOFF_Task_3_3_Health_Check_Monitoring.md for detailed specifications
