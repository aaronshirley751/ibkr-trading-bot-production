# Docker Deployment — Unified Stack

**Charter & Stone Capital — The Crucible**

Unified Docker stack for IBKR Gateway, Trading Bot, and Health Monitoring.

---

## Quick Start

```bash
cd docker
docker compose up -d
```

This starts all services:
- **gateway** — IBKR Gateway (port 4002)
- **trading-bot** — Trading bot (connects to Gateway)
- **health-monitor** — Health monitoring system

---

## Verify Status

```bash
docker ps
docker logs ibkr-gateway
docker logs trading-bot
docker logs health-monitor
```

---

## Stop All Services

```bash
docker compose down
```

## Restart Services

```bash
docker compose restart
```

---

## Configuration

Environment variables in `docker/.env`:
- `IBKR_USERNAME` — IBKR account username
- `IBKR_PASSWORD` — IBKR account password
- `TRADING_MODE` — "paper" or "live" (currently: paper)
- `GATEWAY_PORT` — Default 4002 (paper), 4001 (live)
- `DRY_RUN` — Default "true" (safe mode)
- `DISCORD_WEBHOOK_URL` — Discord alerts webhook

---

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| **Windows Desktop** | ✅ Active | Docker Desktop with WSL2 backend |
| **Ubuntu Rackmount** | 🔮 Future | Docker Engine on bare metal |

**Same configuration files work on both platforms.** Migration = copy files + start container.

---

## Getting Started (Unified Stack)

### First-Time Setup

```bash
# 1. Navigate to docker directory
cd docker

# 2. Verify environment file exists and has credentials
cat .env | grep -E "IBKR_USERNAME|IBKR_PASSWORD|DISCORD_WEBHOOK_URL"

# 3. Start all services
docker compose up -d

# 4. Verify all containers running
docker ps
# Should show: ibkr-gateway (healthy), trading-bot (healthy), health-monitor (Up)

# 5. Monitor logs
docker compose logs -f
```

---

## Troubleshooting

**Gateway not starting:**
```bash
docker logs ibkr-gateway --tail 50
# Check for authentication errors, port conflicts
```

**Bot not connecting:**
```bash
docker logs trading-bot --tail 50
# Verify GATEWAY_HOST=gateway in environment
# Check network: docker network inspect docker_trading-network
```

**Health monitor not alerting:**
```bash
docker logs health-monitor --tail 50
# Verify DISCORD_WEBHOOK_URL in .env
```

---

## Architecture

```
┌─────────────────┐
│  trading-bot    │────┐
└─────────────────┘    │
                       ▼
┌─────────────────┐  ┌─────────────────┐
│ health-monitor  │◄─┤  ibkr-gateway   │
└─────────────────┘  └─────────────────┘
         │                    │
         ▼                    ▼
   Discord Alerts        IBKR Servers
```

All services on shared network: `docker_trading-network`

---

## Migration Notes (2026-02-10)

**Task 3.4 Unified Stack Migration:**
- ✅ Migrated from standalone `docker/gateway/docker-compose.yml` to unified stack
- ✅ First bot container startup completed
- ✅ Legacy standalone Gateway config preserved at `docker/gateway/docker-compose.backup.yml`
- ✅ Fixed Gateway environment configuration (added complete IBC settings)
- ✅ Fixed Dockerfile Poetry command syntax (`--without dev` instead of `--no-dev`)
- ✅ Fixed Gateway TrustedIPs restriction (changed from 127.0.0.1 to allow Docker network)

### Known Issues (Post-Migration)

⚠️ **TWS API Authentication Timeout**: Bot successfully connects to Gateway port 4002 but TWS API handshake times out. Gateway is healthy and properly configured. Issue appears to be timing/initialization-related. Bot retries automatically (up to 30 attempts).
  - Status: Under investigation
  - Workaround: Bot continues retrying; may eventually connect after Gateway fully initializes
  - Next steps: Investigate ib-insync connection parameters, client ID settings, Gateway startup timing

---

## Security

**Critical files (DO NOT COMMIT):**
- `.env` — Contains IBKR credentials
- `gateway/.env` — Legacy Gateway credentials (deprecated)
- `data/gameplan.json` — Trading strategy configuration
- `bot-logs/` — May contain sensitive information

All are gitignored. See [`.gitignore`](../.gitignore) for complete list.

---

## Task 3.4 Status

✅ Unified stack deployed
✅ Gateway migrated and healthy
✅ Health monitor operational
✅ Bot container built and running
⚠️ Bot-Gateway API authentication pending (retry loop active)

---

## Links

- **[Task 3.4 Migration Handoff](../docs/P3-S10_Task_3_4_Migration_Validation_Handoff.md)** — Migration procedure
- **[Gateway Deployment Guide (Legacy)](gateway/README.md)** — Standalone Gateway setup (deprecated)
- **[Task 3.1 Handoff](../docs/VSC_HANDOFF_Task_3_1_IBC_Controller_Config_Docker_v2.md)** — Gateway implementation

---

**Contact:** See operator logs for detailed troubleshooting


- `bot/` — Trading bot container (future)
- `monitoring/` — Prometheus/Grafana (future)
- `database/` — TimescaleDB for metrics (future)
- `discord-notifier/` — Alert service (future)

**Multi-container orchestration:** Will use single `docker-compose.yml` at repository root, with service definitions in subdirectories.

---

## Migration Path

### Phase 3.1 (Current)
- Single container: IBKR Gateway
- Docker Compose in `docker/gateway/`
- Bot runs on host (Phase 2 implementation)

### Phase 3.4 (Future)
- Multi-container setup
- Bot, Gateway, monitoring all containerized
- Orchestrated via repository root `docker-compose.yml`
- Shared network for inter-container communication

---

**Last Updated:** 2026-02-09
**Task:** 3.1 - IBC Controller Configuration (Docker)
**Status:** Gateway deployment complete, bot containerization pending
