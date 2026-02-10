# DEPRECATED: Native Linux Deployment Files

**Status:** DEPRECATED as of 2026-02-09

**Reason:** Project migrated to Docker-based deployment strategy for platform portability.

## What Happened

This directory originally contained systemd service units and native Linux configuration for direct IBC/Gateway deployment on Ubuntu Server.

**Architecture change:** Project now uses Docker containers for Gateway deployment, enabling:
- Same configuration on Windows Desktop (Docker Desktop) and Ubuntu rackmount (Docker Engine)
- Simplified migration path
- Better isolation and resource management
- Consistent behavior across platforms

## Current Implementation

**Active deployment location:** `docker/gateway/`

See:
- `docker/gateway/docker-compose.yml` — Primary configuration
- `docker/gateway/README.md` — Deployment guide
- `docs/VSC_HANDOFF_Task_3_1_IBC_Controller_Config_Docker_v2.md` — Implementation spec

## Files in This Directory (Obsolete)

All files in this directory are deprecated and should NOT be used:

- `systemd/*.service` — Replaced by Docker restart policies
- `systemd/*.timer` — Replaced by host-side scheduled task
- `ibkr/config.ini` — Superseded by Docker-mounted config
- `ibkr/credentials.env.template` — Superseded by Docker `.env` file
- `scripts/*.sh` — Functionality moved to Docker health checks

## Migration Path

If you deployed using these files:

1. Stop systemd services: `sudo systemctl stop ibkr-gateway xvfb`
2. Disable services: `sudo systemctl disable ibkr-gateway xvfb`
3. Follow new Docker deployment: See `docker/gateway/README.md`

---

**Do not delete this directory** — Retained for historical reference and potential fallback scenario.
