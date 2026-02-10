# Docker Deployment

**Charter & Stone Capital — The Crucible**

Docker-based infrastructure for IBKR Gateway and future trading bot components.

---

## Directory Structure

```
docker/
└── gateway/                    # IBKR Gateway container deployment
    ├── README.md              # Complete deployment guide (START HERE)
    ├── docker-compose.yml     # Container orchestration
    ├── .env.example           # Credentials template
    ├── config.ini             # IBC configuration
    └── scripts/
        ├── health-check.sh    # Health monitoring
        └── scheduled-restart.sh # Daily restart automation
```

---

## Quick Links

- **[Gateway Deployment Guide](gateway/README.md)** — Complete setup instructions
- **[Task 3.1 Handoff](../docs/VSC_HANDOFF_Task_3_1_IBC_Controller_Config_Docker_v2.md)** — Implementation specification

---

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| **Windows Desktop** | ✅ Active | Docker Desktop with WSL2 backend |
| **Ubuntu Rackmount** | 🔮 Future | Docker Engine on bare metal |

**Same configuration files work on both platforms.** Migration = copy files + start container.

---

## Getting Started

### First-Time Setup

```bash
# 1. Navigate to gateway
cd docker/gateway

# 2. Make scripts executable (Linux/WSL only)
chmod +x scripts/*.sh

# 3. Create credentials
cp .env.example .env
nano .env  # Fill in IBKR credentials

# 4. Start Gateway
docker compose up -d

# 5. Verify
docker ps  # Should show "healthy" after ~2 minutes
```

**Detailed instructions:** See [gateway/README.md](gateway/README.md)

---

## Security

**Critical files (DO NOT COMMIT):**
- `gateway/.env` — Contains IBKR credentials
- `gateway/restart.log` — May contain sensitive information
- `gateway/tws_settings/` — Gateway persistence (if enabled)

All are gitignored. See [.gitignore](../.gitignore) for complete list.

---

## Future Components (Phase 3+)

This directory will eventually contain:

- `gateway/` — IBKR Gateway (current)
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
