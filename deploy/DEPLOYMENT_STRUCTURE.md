# Deployment Artifacts - Directory Structure

This directory contains all configuration files and scripts for deploying the IBKR trading bot infrastructure on Linux systems (Ubuntu Server 24.04 LTS or WSL2).

## Directory Layout

```
deploy/
├── README.md                           # Deployment guide (main documentation)
├── ibkr/                              # IBC configuration files
│   ├── config.ini                     # IBC Controller configuration
│   └── credentials.env.template       # Credentials template (copy and populate)
├── scripts/                           # Helper scripts
│   ├── ibkr-health-check.sh          # Gateway health monitoring
│   └── ibkr-pre-restart-check.sh     # Pre-restart validation
└── systemd/                           # Systemd service units
    ├── xvfb.service                   # Virtual framebuffer service
    ├── ibkr-gateway.service           # IBKR Gateway management service
    ├── ibkr-gateway-restart.timer     # Daily restart timer (4:30 PM ET)
    └── ibkr-gateway-restart.service   # Restart oneshot service

# On deployed system, files are copied to:
# /etc/ibkr/                    — Configuration
# /etc/systemd/system/          — Service units
# /usr/local/bin/               — Helper scripts
# /var/log/ibkr/                — Log directory
```

## Quick Start

See [README.md](./README.md) for complete deployment instructions.

**TL;DR for experienced operators:**

```bash
# 1. Install dependencies
sudo apt install xvfb xterm unzip curl netcat-openbsd

# 2. Install IBKR Gateway and IBC (see README.md for download links)

# 3. Copy and configure
sudo mkdir -p /etc/ibkr /var/log/ibkr
sudo cp deploy/ibkr/config.ini /etc/ibkr/
sudo cp deploy/ibkr/credentials.env.template /etc/ibkr/credentials.env
sudo nano /etc/ibkr/credentials.env  # Edit credentials
sudo chmod 600 /etc/ibkr/credentials.env

# 4. Install services and scripts
sudo cp deploy/systemd/* /etc/systemd/system/
sudo cp deploy/scripts/* /usr/local/bin/
sudo chmod +x /usr/local/bin/ibkr-*.sh
sudo systemctl daemon-reload

# 5. Start and enable
sudo systemctl enable --now xvfb ibkr-gateway ibkr-gateway-restart.timer
sudo systemctl status ibkr-gateway

# 6. Verify
nc -zv localhost 4002
/usr/local/bin/ibkr-health-check.sh
```

## Security Notes

- **Never commit `/etc/ibkr/credentials.env`** — Contains sensitive credentials
- Template file `credentials.env.template` is tracked in git as documentation
- Actual `credentials.env` file is gitignored
- On deployment, set permissions: `chmod 600 /etc/ibkr/credentials.env`

## Files Ownership

| File/Directory | Git Tracking | Deployment Location | Permissions |
|----------------|--------------|---------------------|-------------|
| `config.ini` | ✅ Tracked | `/etc/ibkr/` | 644 (readable) |
| `credentials.env.template` | ✅ Tracked | N/A | 644 (readable) |
| `credentials.env` | ❌ Gitignored | `/etc/ibkr/` | 600 (owner only) |
| `*.service`, `*.timer` | ✅ Tracked | `/etc/systemd/system/` | 644 (readable) |
| `*.sh` scripts | ✅ Tracked | `/usr/local/bin/` | 755 (executable) |

## Platform Requirements

- **OS:** Ubuntu Server 24.04 LTS or WSL2 (with systemd enabled)
- **Architecture:** x86_64 (Gateway/IBC not compatible with ARM)
- **RAM:** 2GB minimum, 4GB+ recommended
- **Network:** Stable connection to IBKR servers

## Related Documentation

- **[deploy/README.md](./README.md)** — Complete deployment guide (start here)
- **[docs/VSC_HANDOFF_Task_3_1_IBC_Controller_Config_v1.md](../docs/VSC_HANDOFF_Task_3_1_IBC_Controller_Config_v1.md)** — Implementation specification
- **[docs/ARCHITECTURE_Gateway_Deployment_Strategy_Decision_v2.md](../docs/ARCHITECTURE_Gateway_Deployment_Strategy_Decision_v2.md)** — Architecture decisions and rationale

## Testing Checklist

Before production use:

- [ ] Gateway starts: `systemctl start ibkr-gateway`
- [ ] API port accessible: `nc -zv localhost 4002`
- [ ] Health check passes: `/usr/local/bin/ibkr-health-check.sh`
- [ ] Auto-start enabled: `systemctl is-enabled ibkr-gateway`
- [ ] Timer scheduled: `systemctl list-timers | grep ibkr`
- [ ] Reboot survival: System restart, then verify Gateway runs
- [ ] Crash recovery: Kill process, verify auto-restart
- [ ] Discord notifications working

---

**Task:** 3.1 - IBC Controller Configuration Schema
**Status:** Implementation complete, ready for deployment
**Date:** 2026-02-09
