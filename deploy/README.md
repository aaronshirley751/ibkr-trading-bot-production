# IBC Controller Deployment Guide

## Overview

This directory contains configuration files for automated IBKR Gateway lifecycle management using IBC Controller on Linux (Ubuntu Server 24.04 LTS or WSL2). The implementation enables zero-touch Gateway startup, authentication, health monitoring, and scheduled daily restarts to mitigate Gateway memory leaks.

## Prerequisites

### System Requirements

- **OS:** Ubuntu Server 24.04 LTS (or WSL2 with systemd enabled)
- **Architecture:** x86_64 (IBC/Gateway are not compatible with ARM)
- **RAM:** Minimum 2GB, recommended 4GB+ for Gateway
- **Network:** Stable internet connection to IBKR servers

### Required Packages

```bash
sudo apt update
sudo apt install -y \
    xvfb \              # Virtual framebuffer for headless GUI
    xterm \             # Terminal emulator (IBC dependency)
    unzip \             # For extracting IBC distribution
    curl \              # For health checks and notifications
    netcat-openbsd      # For port checking (nc command)
```

### Enable systemd in WSL2 (if using WSL2)

Edit `/etc/wsl.conf`:
```ini
[boot]
systemd=true
```

Restart WSL: `wsl --shutdown` from PowerShell, then reopen.

## Installation Steps

### 1. Install IBKR Gateway

Download and install IBKR Gateway stable version:

```bash
# Download Gateway installer (check latest stable version)
wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh

# Make executable
chmod +x ibgateway-stable-standalone-linux-x64.sh

# Install (requires display)
DISPLAY=:99 Xvfb :99 &
./ibgateway-stable-standalone-linux-x64.sh
pkill Xvfb

# Gateway installs to ~/Jts/ibgateway/<version>/
# Note the version number for configuration
```

### 2. Install IBC Controller

Download and install IBC:

```bash
# Download IBC (check latest release at https://github.com/IbcAlpha/IBC/releases)
wget https://github.com/IbcAlpha/IBC/releases/download/3.19.0/IBCLinux-3.19.0.zip

# Install to /opt/ibc/
sudo mkdir -p /opt/ibc
sudo unzip IBCLinux-3.19.0.zip -d /opt/ibc/
sudo chmod +x /opt/ibc/*.sh /opt/ibc/scripts/*.sh
```

### 3. Create Configuration Directories

```bash
# Create configuration directory
sudo mkdir -p /etc/ibkr
sudo mkdir -p /var/log/ibkr

# Copy configuration files from repository
sudo cp deploy/ibkr/config.ini /etc/ibkr/
sudo cp deploy/ibkr/credentials.env.template /etc/ibkr/credentials.env

# Set proper permissions
sudo chmod 600 /etc/ibkr/credentials.env
sudo chown root:root /etc/ibkr/credentials.env
```

### 4. Configure Credentials

Edit `/etc/ibkr/credentials.env`:

```bash
sudo nano /etc/ibkr/credentials.env
```

Set the following values:
- `IBKR_USERNAME`: Your IBKR username
- `IBKR_PASSWORD`: Your IBKR password
- `IBKR_TRADING_MODE`: `paper` (start with paper trading)
- `TWS_MAJOR_VRSN`: Gateway version (e.g., `1030` for 10.30.x)
- `DISCORD_WEBHOOK_URL`: Your Discord webhook URL for notifications

**Security Note:** This file contains sensitive credentials. Never commit it to git or share it.

### 5. Install Systemd Services

```bash
# Copy service files
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo cp deploy/systemd/*.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Validate service files (should show no errors)
systemd-analyze verify /etc/systemd/system/xvfb.service
systemd-analyze verify /etc/systemd/system/ibkr-gateway.service
systemd-analyze verify /etc/systemd/system/ibkr-gateway-restart.timer
systemd-analyze verify /etc/systemd/system/ibkr-gateway-restart.service
```

### 6. Install Helper Scripts

```bash
# Copy scripts
sudo cp deploy/scripts/ibkr-health-check.sh /usr/local/bin/
sudo cp deploy/scripts/ibkr-pre-restart-check.sh /usr/local/bin/

# Make executable
sudo chmod +x /usr/local/bin/ibkr-health-check.sh
sudo chmod +x /usr/local/bin/ibkr-pre-restart-check.sh
```

### 7. Create Service User (Optional but Recommended)

```bash
# Create dedicated user for Gateway
sudo useradd -r -s /bin/bash -m -d /home/trader trader

# Copy Gateway installation to service user
sudo cp -r ~/Jts /home/trader/
sudo chown -R trader:trader /home/trader/Jts

# Update service file User= directive if using different user
```

## Service Management

### Start Services

```bash
# Start Xvfb (virtual display)
sudo systemctl start xvfb

# Start Gateway
sudo systemctl start ibkr-gateway

# Check status
sudo systemctl status ibkr-gateway
```

### Enable Auto-Start on Boot

```bash
sudo systemctl enable xvfb
sudo systemctl enable ibkr-gateway
sudo systemctl enable ibkr-gateway-restart.timer
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u ibkr-gateway -f

# Last 100 lines
sudo journalctl -u ibkr-gateway -n 100

# Gateway output logs
sudo tail -f /var/log/ibkr/gateway.log

# IBC logs (created by IBC in its directory)
sudo tail -f /opt/ibc/logs/ibc-*.txt
```

### Stop Services

```bash
# Stop Gateway
sudo systemctl stop ibkr-gateway

# Stop Xvfb (only if Gateway is stopped)
sudo systemctl stop xvfb
```

## Health Checks

### Manual Health Check

```bash
/usr/local/bin/ibkr-health-check.sh
echo $?  # 0 = healthy, non-zero = unhealthy
```

### Check API Port

```bash
nc -zv localhost 4002
```

### Check Gateway Process

```bash
pgrep -fa ibgateway
```

## Scheduled Restart

The Gateway automatically restarts daily at 4:30 PM ET via systemd timer.

### Check Timer Status

```bash
# List all timers
sudo systemctl list-timers

# Check specific timer
sudo systemctl status ibkr-gateway-restart.timer
```

### Manual Restart

```bash
# Trigger restart immediately
sudo systemctl start ibkr-gateway-restart.service

# Or restart Gateway directly
sudo systemctl restart ibkr-gateway
```

## Troubleshooting

### Gateway Won't Start

1. Check credentials are correct:
   ```bash
   sudo cat /etc/ibkr/credentials.env
   ```

2. Check Xvfb is running:
   ```bash
   systemctl status xvfb
   ```

3. Check Gateway process isn't already running:
   ```bash
   pgrep -fa ibgateway
   # If found, kill it:
   sudo pkill -9 -f ibgateway
   ```

4. Check logs for errors:
   ```bash
   sudo journalctl -u ibkr-gateway --since "10 minutes ago"
   ```

### Authentication Failures

If Gateway fails to authenticate:

1. Verify credentials in `/etc/ibkr/credentials.env`
2. Check if 2FA is enabled (may need IBKR Mobile app approval)
3. Request IBKR to disable 2FA for API logins (improves automation)
4. Check logs: `sudo journalctl -u ibkr-gateway | grep -i auth`

### Port Already in Use

```bash
# Check what's using port 4002
sudo ss -tlnp | grep 4002

# Kill the process if needed
sudo kill -9 <PID>
```

### Service in Failed State

```bash
# Reset failed state
sudo systemctl reset-failed ibkr-gateway

# Check what caused the failure
sudo journalctl -u ibkr-gateway --since "1 hour ago"

# Fix issue, then restart
sudo systemctl start ibkr-gateway
```

### Memory Issues

If Gateway uses excessive memory:

```bash
# Check Gateway memory usage
ps aux | grep ibgateway

# Force restart to reclaim memory
sudo systemctl restart ibkr-gateway
```

## Security Considerations

### Credential Protection

- `/etc/ibkr/credentials.env` has mode 0600 (owner read/write only)
- File owned by root or service user
- Never commit this file to version control
- Credentials not visible in process list or logs

### Firewall Rules

If using a firewall, allow localhost connections:

```bash
# Gateway API port (localhost only)
sudo ufw allow from 127.0.0.1 to 127.0.0.1 port 4002

# For remote access (NOT recommended), restrict by IP:
# sudo ufw allow from <your-ip> to any port 4002
```

### Read-Only API Mode

To enable monitoring-only mode (no order submission), edit `/etc/ibkr/config.ini`:

```ini
ReadOnlyApi=yes
```

**Note:** This disables trading bot order placement. Only use for monitoring instances.

## Migration to Production

### Paper → Live Trading

1. Request CRO approval for live trading
2. Edit `/etc/ibkr/credentials.env`:
   ```bash
   IBKR_TRADING_MODE=live
   IBKR_USERNAME=<live_account_username>
   IBKR_PASSWORD=<live_account_password>
   ```
3. Restart Gateway: `sudo systemctl restart ibkr-gateway`
4. Verify connection: `/usr/local/bin/ibkr-health-check.sh`

### Desktop → Server Migration

1. Backup credentials: `sudo cp /etc/ibkr/credentials.env ~/credentials.backup`
2. On new server, follow installation steps 1-7
3. Copy credentials to new server (via secure method)
4. Enable and start services
5. Verify operation before switching trading bot connection

## Testing Checklist

Before relying on automated Gateway management:

- [ ] Gateway starts successfully: `sudo systemctl start ibkr-gateway`
- [ ] API port responds: `nc -zv localhost 4002`
- [ ] Health check passes: `/usr/local/bin/ibkr-health-check.sh`
- [ ] Services enabled for boot: `systemctl is-enabled ibkr-gateway`
- [ ] Timer scheduled correctly: `systemctl list-timers | grep ibkr`
- [ ] Manual restart works: `sudo systemctl restart ibkr-gateway`
- [ ] Discord notifications received (check webhook)
- [ ] Reboot survival: `sudo reboot`, then check status after boot
- [ ] Crash recovery: `sudo kill -9 $(pgrep ibgateway)`, wait 60 seconds
- [ ] Trading bot connects successfully

## Integration with Trading Bot

The trading bot connects to Gateway via `ib_insync`:

```python
from ib_insync import IB

ib = IB()
ib.connect(
    host='127.0.0.1',
    port=4002,
    clientId=1,
    readonly=False
)
```

**Important:** Gateway must be running before bot startup. The bot implements Strategy C (cash preservation) as default when Gateway is unavailable, providing defense-in-depth safety.

## Related Documentation

- [Task 3.1 Handoff](../docs/VSC_HANDOFF_Task_3_1_IBC_Controller_Config_v1.md) — Complete implementation specification
- [IBC Documentation](https://github.com/IbcAlpha/IBC) — Official IBC Controller documentation
- [Architecture Decisions](../docs/ARCHITECTURE_Gateway_Deployment_Strategy_Decision_v2.md) — Why these choices
- [Alpha Learnings](../docs/alpha_learnings.md) — Field-tested insights

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u ibkr-gateway -n 200`
2. Run health check: `/usr/local/bin/ibkr-health-check.sh`
3. Review troubleshooting section above
4. Check IBC GitHub issues for known problems

---

**Last Updated:** 2026-02-09
**Task:** 3.1 - IBC Controller Configuration Schema
**Status:** Deployment-ready
