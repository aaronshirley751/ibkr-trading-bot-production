# IBKR Gateway Docker Deployment

**Charter & Stone Capital — The Crucible**

Complete deployment guide for running IBKR Gateway via Docker on Windows Desktop (current) or Ubuntu rackmount server (future).

---

## Quick Start

```bash
# 1. Navigate to gateway directory
cd docker/gateway

# 2. Make scripts executable (Linux/WSL only, after cloning)
chmod +x scripts/*.sh

# 3. Create credentials file from template
cp .env.example .env

# 4. Edit .env with your IBKR credentials (use your preferred editor)
notepad .env     # Windows
nano .env        # Linux/WSL

# 5. Start Gateway container
docker compose up -d

# 6. Watch startup logs
docker compose logs -f

# 7. Verify health (wait ~2 minutes for authentication)
docker ps        # Should show "healthy" status

# 8. Test API connection
nc -zv localhost 4002   # Should succeed
```

---

## Prerequisites

### Windows Desktop (Current Platform)

1. **Docker Desktop for Windows**
   - Download: https://www.docker.com/products/docker-desktop/
   - Install with WSL2 backend (default)
   - Minimum 4GB RAM allocated to Docker

2. **WSL2 with Ubuntu** (for running bash scripts)
   ```powershell
   wsl --install -d Ubuntu
   ```

3. **Verify Installation**
   ```powershell
   docker --version
   docker compose version
   ```

### Ubuntu Rackmount (Future Migration)

```bash
# Install Docker Engine
sudo apt update
sudo apt install -y docker.io docker-compose-v2

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker compose version

# Note: After cloning repo, make scripts executable:
# cd docker/gateway && chmod +x scripts/*.sh
```

---

## Pre-Deployment Checklist

**Complete these steps before first deployment:**

### 1. Verify Docker Environment

```powershell
# Check Docker Desktop is running (Windows)
docker --version
docker compose version
# Both should return version info

# Verify WSL2 Ubuntu available (for scheduled restart scripts)
wsl -l -v
# Should show Ubuntu with VERSION 2
```

### 2. Check Port Availability

```powershell
# Ensure ports are not in use (Windows)
netstat -an | findstr "4002"    # Gateway API
netstat -an | findstr "5900"    # VNC (optional)
netstat -an | findstr "6080"    # noVNC (optional)
# All should return empty (ports available)

# Linux/WSL equivalent:
# lsof -i :4002 && lsof -i :5900 && lsof -i :6080
```

### 3. Set Script Permissions (Linux/WSL)

```bash
cd docker/gateway
chmod +x scripts/*.sh

# Verify executable
ls -la scripts/
# Should show -rwxr-xr-x for .sh files
```

### 4. Create Credentials File

```bash
cd docker/gateway
cp .env.example .env
nano .env  # Or use your preferred editor
```

**Important credential notes:**

- ✅ **Start with paper trading:** Set `TRADING_MODE=paper`
- ✅ **Use paper credentials:** Not live account credentials
- ✅ **Special characters:** If password contains `$`, `\`, or quotes, wrap in single quotes:
  ```bash
  TWS_PASSWORD='my$pecial\pass'
  ```

**Verify .env is gitignored:**
```bash
git status docker/gateway/.env
# Should NOT appear in git status (untracked/ignored)
```

### 5. CRO Safety Verification

- [ ] Confirmed `TRADING_MODE=paper` in `.env`
- [ ] Confirmed paper trading credentials (not live)
- [ ] Confirmed `.env` is gitignored (not tracked)

**⚠️ CRO Approval Required:** Only proceed with paper trading initially. Live trading requires explicit CRO approval after validation period.

---

## First Deployment Test

Once pre-deployment checklist is complete:

### Start Container

```bash
cd docker/gateway
docker compose up -d
```

### Monitor Startup (Critical)

```bash
# Watch logs in real-time
docker compose logs -f

# Look for successful login sequence:
# ✅ "Login dialog detected"
# ✅ "Credentials entered"
# ✅ "Main window detected" (or similar success message)
# ❌ "Authentication failed" (indicates wrong credentials)
# ❌ "Connection refused" (indicates network issue)
```

**If 2FA enabled:** Approve login via IBKR Mobile app within 180 seconds.

### Verify Health Status

```bash
# Wait 2+ minutes for authentication and health check
docker ps

# STATUS column should show:
# - "Up X minutes (healthy)" ✅ Success
# - "Up X minutes (health: starting)" ⏳ Still initializing
# - "Up X minutes (unhealthy)" ❌ Problem detected

# Detailed health check
docker inspect --format='{{.State.Health.Status}}' ibkr-gateway
# Should return: "healthy"
```

### Test API Connectivity

```bash
# Linux/WSL/Mac:
nc -zv localhost 4002

# Windows PowerShell:
Test-NetConnection -ComputerName localhost -Port 4002
```

**Expected result:** Connection succeeds (may show protocol error, that's OK).

### Optional: Visual Debugging via VNC

```bash
# Open browser to:
http://localhost:6080

# You should see Gateway GUI
# Useful for watching login process or debugging auth issues
```

---

## Container Image

**Image:** `ghcr.io/gnzsnz/ib-gateway-docker:stable`

**What's Inside:**
- IBKR Gateway (offline installer)
- IBC Controller (automated login)
- Xvfb (virtual display)
- x11vnc (VNC debugging access)
- socat (API port relay)

**Tag Strategy:**
- `stable` — Recommended for production (tested stable Gateway version)
- `latest` — Most recent Gateway version (may have bugs)
- `10.30.1t` — Specific version pinning (for exact reproducibility)

---

## Configuration Files

### docker-compose.yml

Orchestrates the Gateway container:
- Maps port 4002 (Gateway API) to localhost
- Maps ports 5900/6080 (VNC debugging, optional)
- Mounts `config.ini` for IBC settings
- Configures health checks and restart policy
- Loads credentials from `.env` file

**Do not modify** unless you need to change:
- Port mappings (if port 4002 conflicts)
- Resource limits (memory/CPU constraints)
- VNC access (disable for production)

### .env (Credentials)

**CRITICAL:** This file contains your IBKR credentials.

- **Created from:** `.env.example`
- **Required fields:**
  - `TWS_USERID`: Your IBKR username
  - `TWS_PASSWORD`: Your IBKR password
  - `TRADING_MODE`: `paper` or `live`

- **Optional fields:**
  - `VNC_PASSWORD`: Password for VNC debugging
  - `DISCORD_WEBHOOK_URL`: Webhook for restart notifications

**Security:**
- Never commit to git (gitignored)
- Set restrictive permissions: `chmod 600 .env` (Linux/WSL)
- Keep backups in secure location

**Windows users:** If using WSL for scripts, ensure `.env` is readable:
```powershell
# From PowerShell, if needed:
wsl chmod 600 /mnt/c/Users/yourname/path/to/docker/gateway/.env
```

### config.ini (IBC Configuration)

Controls Gateway behavior:
- Auto-accept API connections
- Dismiss warning dialogs
- Handle 2FA timeouts
- Disable Gateway's internal restart (we manage restarts)

**Rarely needs modification** — defaults are optimized for automated trading.

---

## Daily Operations

### Start Gateway

```bash
cd docker/gateway
docker compose up -d
```

**First startup:** Takes ~2 minutes for authentication.

### Check Status

```bash
# Container status
docker ps

# Health check
docker inspect --format='{{.State.Health.Status}}' ibkr-gateway

# View logs
docker compose logs --tail=50

# Real-time logs
docker compose logs -f
```

### Stop Gateway

```bash
docker compose down
```

**Note:** Trading bot will lose connection. Ensure positions are closed before stopping.

### Restart Gateway

```bash
# Graceful restart
docker compose restart

# Or: stop + start
docker compose down
docker compose up -d
```

### View Resource Usage

```bash
docker stats ibkr-gateway
```

Shows CPU, memory, network usage in real-time.

---

## Scheduled Daily Restart (4:30 PM ET)

Mitigates Gateway memory leak by restarting daily after market close.

### Setup on Windows (Task Scheduler)

**Option 1: PowerShell Script** (recommended)

Run in PowerShell as Administrator:
```powershell
$action = New-ScheduledTaskAction `
    -Execute "wsl.exe" `
    -Argument "-d Ubuntu bash /mnt/c/Users/YOURUSERNAME/path/to/docker/gateway/scripts/scheduled-restart.sh"

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "4:30 PM"

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd

Register-ScheduledTask `
    -TaskName "IBKR Gateway Daily Restart" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Restarts IBKR Gateway at 4:30 PM ET to clear memory leak"
```

Replace `YOURUSERNAME` and path with your actual paths.

**Option 2: Task Scheduler GUI**

1. Open Task Scheduler
2. Create Basic Task
3. Name: "IBKR Gateway Daily Restart"
4. Trigger: Daily at 4:30 PM
5. Action: Start a program
   - Program: `wsl.exe`
   - Arguments: `-d Ubuntu bash /mnt/c/Users/YOURUSERNAME/path/to/docker/gateway/scripts/scheduled-restart.sh`
6. Finish

### Setup on Linux (Cron)

```bash
# Edit crontab
crontab -e

# Add line (runs 4:30 PM Mon-Fri):
30 16 * * 1-5 /path/to/docker/gateway/scripts/scheduled-restart.sh
```

### Manual Trigger

```bash
cd docker/gateway
./scripts/scheduled-restart.sh
```

---

## Debugging & Troubleshooting

### VNC Access (Visual Debugging)

Access the Gateway GUI for debugging authentication issues.

**VNC Client:**
```
Host: localhost:5900
Password: (set via VNC_PASSWORD in .env)
```

**Web Browser (noVNC):**
```
URL: http://localhost:6080
```

**Use cases:**
- Watch login process
- Debug 2FA issues
- Manually configure Gateway settings

**Disable in production:** Comment out ports 5900/6080 in `docker-compose.yml`.

### Common Issues

#### Container Won't Start

```bash
# Check if Docker is running
docker ps

# View error in logs
docker compose logs

# Common causes:
# 1. Docker Desktop not running (Windows)
# 2. Port 4002 already in use
# 3. .env file missing or malformed
```

#### Authentication Failures

```bash
# Check logs for auth errors
docker compose logs | grep -i auth

# Common causes:
# 1. Wrong username/password in .env
# 2. 2FA timeout (need IBKR Mobile app approval)
# 3. Account locked (too many failed attempts)

# Solution: Verify .env credentials, restart
docker compose restart
```

#### Port 4002 Already in Use

```bash
# Find what's using port 4002
netstat -ano | findstr :4002    # Windows
lsof -i :4002                   # Linux/Mac

# Kill conflicting process or change port in docker-compose.yml:
# ports:
#   - "127.0.0.1:4003:4002"  # Map to host port 4003 instead
```

#### Container Unhealthy

```bash
# Check health status
docker inspect --format='{{json .State.Health}}' ibkr-gateway | jq

# Common causes:
# 1. Gateway crashed inside container
# 2. API port not responding
# 3. Network issue to IBKR servers

# Solution: Restart container
docker compose restart

# If persistent: Check Gateway logs
docker compose logs | grep -i error
```

#### Two-Factor Authentication Timeout

If using 2FA, approve login within 180 seconds via IBKR Mobile app.

**To disable 2FA for API:**
1. Log into IBKR Account Management
2. Settings → Security → API Authentication
3. Request to disable 2FA for API logins (reduces account protection)

#### Docker Desktop Stopped (Windows)

If Docker Desktop is closed:
```powershell
# Start Docker Desktop (GUI or command)
# Containers auto-start via restart: unless-stopped policy
```

#### WSL2 Shutdown (Windows)

If WSL2 restarts (Windows updates, manual shutdown):
```powershell
# Restart WSL
wsl

# Verify containers restarted
docker ps
```

### Health Check Script

```bash
# Run from host
cd docker/gateway
./scripts/health-check.sh

# Exit codes:
# 0 = healthy
# 1 = container not running
# 2 = container unhealthy
# 3 = API port not responding
```

---

## Migration: Windows → Ubuntu Rackmount

When ready to migrate to production server:

### On Current Windows Machine

```bash
# 1. Stop Gateway
cd docker/gateway
docker compose down

# 2. Backup configuration
# Copy entire docker/gateway/ directory to secure location
```

### On Ubuntu Rackmount Server

```bash
# 1. Clone repository
git clone <your-repo-url>
cd crucible/docker/gateway

# 2. Make scripts executable
chmod +x scripts/*.sh

# 3. Create .env from backup
cp /path/to/backup/.env .env
chmod 600 .env

# 4. Pull container image
docker compose pull

# 5. Start Gateway
docker compose up -d

# 6. Verify
docker ps
docker compose logs
curl -s localhost:4002  # Should connect (protocol error is OK)
```

### Update Trading Bot Connection

No changes needed if bot connects to `localhost:4002`.

If bot runs on different machine, update Gateway port binding in `docker-compose.yml`:
```yaml
ports:
  - "0.0.0.0:4002:4002"  # Expose to all interfaces (behind firewall!)
```

**Security:** Only do this behind a firewall. Never expose 4002 to public internet.

---

## Paper → Live Trading

**⚠️ CRO APPROVAL REQUIRED ⚠️**

1. **Complete paper trading validation:**
   - Minimum 2 weeks paper trading
   - All risk controls validated
   - No capital protection failures

2. **Update credentials:**
   ```bash
   nano docker/gateway/.env

   # Change:
   TRADING_MODE=live
   TWS_USERID=<live_account_username>
   TWS_PASSWORD=<live_account_password>
   ```

3. **Restart Gateway:**
   ```bash
   docker compose restart
   ```

4. **Verify live mode:**
   ```bash
   docker compose logs | grep -i "trading mode"
   # Should show: "Trading mode: live"
   ```

5. **Monitor live trading:**
   - Watch first trades closely
   - Verify position sizing correct
   - Confirm risk guards active

---

## Security Checklist

- [ ] `.env` file not tracked in git (verify: `git status`)
- [ ] `.env` has restrictive permissions (Linux: `chmod 600`)
- [ ] VNC ports (5900/6080) disabled in production
- [ ] API port (4002) only exposed to localhost
- [ ] Credentials not visible in `docker compose config`
- [ ] Credentials not visible in `docker inspect`
- [ ] Discord webhook (if used) is from secure workspace

---

## Resource Requirements

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| RAM | 2GB | 4GB+ | Gateway memory leak accumulates |
| CPU | 2 cores | 4 cores | Minimal usage except during market data floods |
| Disk | 2GB | 5GB | Container image + logs |
| Network | 1 Mbps | 10 Mbps | Stable connection critical |

**Docker Desktop (Windows):**
- Settings → Resources → Memory: Set to 4GB minimum
- Settings → Resources → CPU: 4 CPUs recommended

---

## Backup & Disaster Recovery

### Backup Configuration

```bash
# Create backup directory
mkdir -p ~/ibkr-backups/$(date +%Y%m%d)

# Backup critical files
cp docker/gateway/.env ~/ibkr-backups/$(date +%Y%m%d)/
cp docker/gateway/config.ini ~/ibkr-backups/$(date +%Y%m%d)/
cp docker/gateway/restart.log ~/ibkr-backups/$(date +%Y%m%d)/

# Optional: Backup Gateway settings (if persistence enabled)
# cp -r docker/gateway/tws_settings ~/ibkr-backups/$(date +%Y%m%d)/
```

### Recovery from Backup

```bash
# Restore .env
cp ~/ibkr-backups/YYYYMMDD/.env docker/gateway/.env

# Restart Gateway
cd docker/gateway
docker compose up -d
```

### Fallback: Manual Gateway Launch

If Docker approach fails completely:

1. Download Gateway installer from IBKR website
2. Install natively on Windows/Linux
3. Launch Gateway manually, login via GUI
4. Trading bot connects to localhost:4002 normally

**This bypasses all automation** but allows trading to continue during infrastructure failures.

---

## Testing Checklist

Before relying on automated Gateway:

- [ ] Container starts successfully: `docker compose up -d`
- [ ] Container shows healthy: `docker ps` (after 2min)
- [ ] API responds: `nc -zv localhost 4002`
- [ ] Trading bot connects successfully
- [ ] Manual restart works: `docker compose restart`
- [ ] Scheduled restart script works: `./scripts/scheduled-restart.sh`
- [ ] Health check script works: `./scripts/health-check.sh`
- [ ] Crash recovery: `docker exec ibkr-gateway pkill -9 java` → auto-restart
- [ ] VNC debugging accessible (if enabled)
- [ ] Logs clean: `docker compose logs | grep -i error` (no critical errors)

---

## Additional Resources

- **IBC Documentation:** https://github.com/IbcAlpha/IBC
- **Container Image:** https://github.com/gnzsnz/ib-gateway-docker
- **IBKR API Docs:** https://interactivebrokers.github.io/
- **Docker Compose:** https://docs.docker.com/compose/
- **Task 3.1 Handoff:** [VSC_HANDOFF_Task_3_1_IBC_Controller_Config_Docker_v2.md](../../docs/VSC_HANDOFF_Task_3_1_IBC_Controller_Config_Docker_v2.md)

---

## Support

For issues:
1. Check logs: `docker compose logs`
2. Run health check: `./scripts/health-check.sh`
3. Review troubleshooting section above
4. Check container image GitHub issues

---

**Last Updated:** 2026-02-09
**Task:** 3.1 - IBC Controller Configuration (Docker v2)
**Status:** Production-ready, portable Windows Desktop ↔ Ubuntu Server
