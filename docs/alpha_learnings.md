# Alpha Implementation Learnings

**Purpose:** Document Pi-specific configurations, IBKR Gateway quirks, and infrastructure knowledge discovered during alpha testing. This is reference documentation for production implementation, not production code.

**Alpha Repository Context:** The alpha implementation (ibkr-options-bot) served as a proof-of-concept for validating Pi + IBKR Gateway feasibility. Production implementation uses lessons learned here but builds from clean architecture.

---

## 1. Raspberry Pi Configuration

### Hardware Specs
- **Model:** Raspberry Pi 4
- **RAM:** 4GB minimum (tested configuration)
- **OS:** Debian GNU/Linux Trixie (64-bit arm64)
- **Kernel:** Linux 6.12.47+rpt-rpi-v8
- **Hostname:** Jeremiah
- **IP Address:** 192.168.7.117 (static recommended)
- **SSH User:** saladbar751 (custom username, not default "pi")

### Known Limitations
- **Concurrent symbol processing:** Max 2-3 symbols without performance degradation
- **Historical data requests:** Requests >1000 bars or >1 hour RTH cause Gateway timeouts
- **Market data polling:** 180-second (3-minute) intervals are too aggressive; causes Gateway rate limiting after sustained use
- **Memory constraints:** Gateway + Bot together consume ~1.5GB RAM; leave 1GB+ free for OS
- **Strike count limits:** Max 3-5 near-ATM strikes per symbol to prevent Gateway buffer overflow

### Network Configuration
- **SSH Access:** Custom username configuration via Raspberry Pi Imager (not default "pi")
- **Static IP:** Recommended for reliable SSH access (192.168.7.117 in alpha)
- **Firewall:** None configured (local network trust model)
- **Port Requirements:** 4002 (IBKR Gateway API), 5900 (VNC for Gateway GUI access)

### OS Quirks
- **Python 3.13.5 default:** Debian Trixie ships with Python 3.13; requires pyenv for Python 3.11.9
- **pyenv build dependencies:** `build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git`
- **piwheels mirror:** Automatically used by pip on Pi; significantly faster than PyPI for ARM binaries
- **pandas-ta unavailable:** Not available for Python 3.11 on piwheels/PyPI; confirmed unused in codebase

---

## 2. IBKR Gateway Configuration

### Connection Parameters That Worked

**Successful Manual Installation Path (Fallback):**
- Download: `https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh`
- Install location: `~/Jts/ibgateway`
- Prerequisites: `default-jre xvfb` (X virtual framebuffer for headless)
- API Settings:
  - ✅ Enable ActiveX and Socket Clients
  - ✅ Socket port: 4002 (paper trading)
  - ✅ Allow connections from localhost only
  - ✅ Read-Only API: Unchecked (allows order placement)

**Docker Configuration (Problematic):**
All tested Docker images failed on ARM64 Pi architecture:
- `ghcr.io/gyrasol/ibkr-gateway:latest` - 404 not found (requires GHCR authentication)
- `ghcr.io/gnzsnz/ib-gateway:stable` - Container crash loop ("can't find jars folder")
- `voyz/ib-gateway:paper` - Repository does not exist
- `rylorin/ib-gateway:latest` - Pull access denied
- `ibcontroller/ib-gateway:latest` - Pull access denied

### Quirks Discovered

#### Buffer Overflow Issue (CRITICAL)
**Root Cause:** `reqMktData(snapshot=False)` creates persistent streaming subscriptions
- Gateway auto-subscribes to Greeks (tick type 106) for every option contract
- Gateway auto-subscribes to Model Parameters (tick type 104)
- Subscriptions accumulate without cleanup -> Buffer overflow
- Symptoms: "Output exceeded limit (was: 100413), removed first half" warnings
- Frequency: 8 occurrences in 80 seconds during single-symbol test

**Solution:** `reqMktData(snapshot=True)`
- Eliminates persistent subscriptions (one-time snapshot retrieval)
- Auto-terminating lifecycle (no cleanup required)
- 90% reduction in Gateway log volume
- 100% elimination of buffer warnings
- Validated in Phase 1 testing (single-symbol SPY)

#### Historical Data Limits
**Problem:** Requests for >1 hour RTH or >1000 bars cause timeouts
**Solution:** Limit requests to 1-hour RTH-only windows
- Example working request: 60 bars, 1-min interval, RTH only
- Timeout increase: 3.0s -> 5.0s for snapshot mode semantics

#### Reconnection Behavior
- Gateway maintains connection state across bot restarts if clientId unchanged
- Stale connections cause "clientId already in use" errors
- Solution: Increment clientId on each bot restart or restart Gateway
- Alpha used clientIds: 101, 216, 250, 251, 252

#### Rate Limiting
**Discovery:** After 3 successful cycles, Gateway starts throttling requests
- Symptom: 100% failure rate on historical_prices() after initial success
- Duration: 2+ hours of continuous timeouts with zero recovery
- Cause: Gateway internal queue limits under sustained load
- Solution: Increase cycle interval from 180s to 300s+ (5+ minutes)

### Authentication
- **Paper Trading:** Username/password authentication via .env file
- **2FA:** Not required for paper trading accounts
- **Session Persistence:** Gateway maintains login session until manual logout or restart
- **Credentials Security:** .env file with chmod 600 permissions

---

## 3. Docker Configuration

### Working docker-compose.yml Sections

**Gateway Service (Manual Installation Required on Pi):**
```yaml
# Note: All Docker images failed on ARM64 Pi
# Manual installation recommended (see Section 2)
services:
  gateway-manual:
    image: ubuntu:20.04
    container_name: ibkr-gateway-manual
    environment:
      - DEBIAN_FRONTEND=noninteractive
      - IBKR_USERNAME=${IBKR_USERNAME}
      - IBKR_PASSWORD=${IBKR_PASSWORD}
      - TZ=${TZ:-UTC}
    ports:
      - "4002:4002"
    volumes:
      - ./scripts:/scripts:ro
    command: /scripts/install_and_run_gateway.sh
    restart: unless-stopped
```

**Bot Service (Working):**
```yaml
services:
  bot:
    build: .
    container_name: ibkr-trading-bot
    environment:
      - IBKR_HOST=127.0.0.1
      - IBKR_PORT=4002
      - IBKR_CLIENT_ID=101
      - DRY_RUN=true
    volumes:
      - ./configs:/app/configs:ro
      - ./logs:/app/logs
      - ./state:/app/state
    restart: unless-stopped
    depends_on:
      - gateway
```

### Volume Mounts
- `/app/configs` - Read-only configuration (settings.yaml)
- `/app/logs` - Log rotation directory (bot.log, bot.jsonl)
- `/app/state` - Persistent state (crucible_state.json)
- Permission issues: Ensure container user has write access to logs/ and state/

### Networking
- **Bridge networking:** Default docker network works for localhost Gateway access
- **Port mapping:** 4002:4002 for Gateway API access
- **Host network:** Not required unless specific networking constraints

---

## 4. Data Quality Observations

### Historical Data Behavior
**Request patterns that worked reliably:**
- 60 bars, 1-minute intervals, RTH only
- Single-hour windows (e.g., 9:30-10:30 ET)
- Timeout: 5.0 seconds minimum

**Request patterns that caused timeouts:**
- Multi-hour requests (>1 hour RTH)
- >1000 bars in single request
- Non-RTH (extended hours) data requests
- Concurrent requests from same clientId

**Optimal batch sizes:**
- Single symbol per request
- Max 3-5 strikes per option chain query
- 200ms delay between symbol processing cycles

### Market Data Subscriptions
**Snapshot vs Streaming:**
- `snapshot=False` (streaming): Persistent subscriptions, buffer overflow
- `snapshot=True` (snapshot): One-time retrieval, auto-cleanup, **RECOMMENDED**

**Connection stability:**
- Stable for 3-5 cycles, then Gateway rate limiting activates
- Requires 5-minute minimum intervals between cycles
- Fresh clientId or Gateway restart resolves stale connection issues

---

## 5. Failure Modes Observed

### 1. Gateway Container Crash Loop
**Trigger:** Using Docker images on ARM64 Pi
**Symptom:** "Offline TWS/Gateway version 1015 not installed: can't find jars folder"
**Resolution:** Use manual Gateway installation (x86_64 binaries with emulation not viable)

### 2. Buffer Overflow Warnings
**Trigger:** `snapshot=False` with option contract queries
**Symptom:** "Output exceeded limit" + "EBuffer grew to 9351 bytes"
**Resolution:** Switch to `snapshot=True` in market_data() method

### 3. Historical Data Timeouts (100% failure after initial success)
**Trigger:** 180-second cycle intervals with sustained requests
**Symptom:** First 3 cycles succeed, all subsequent cycles timeout
**Resolution:** Increase interval to 300+ seconds, restart Gateway periodically

### 4. SSH Authentication Failure
**Trigger:** Using default username "pi" with custom Raspberry Pi Imager setup
**Symptom:** Permission denied (publickey)
**Resolution:** Use custom username from Imager configuration

### 5. Python 3.11 Build Failures
**Trigger:** Missing build dependencies for pyenv
**Symptom:** OpenSSL, zlib, readline module import errors
**Resolution:** Install full build-essential + library dev packages before pyenv install

---

## 6. Pi-Specific Workarounds

### Performance Optimization
- **CPU usage:** Single-threaded processing preferred (max_concurrent_symbols=1)
- **Memory management:** Monitor with `free -h`; Gateway can consume 800MB+
- **Polling intervals:** 300 seconds (5 minutes) minimum to avoid Gateway rate limiting
- **Strike count limits:** Max 3-5 strikes per symbol (configurable in settings.yaml)

### Startup Sequence
**Order of operations that worked:**
1. Boot Pi and wait for network (30 seconds)
2. Start IBKR Gateway manually or via systemd service
3. Wait for Gateway port 4002 listening (verify with `ss -tln | grep 4002`)
4. Start bot with proper environment variables
5. Monitor logs for connection success before assuming operational

**Timing delays needed:**
- Gateway startup: 30-45 seconds until port 4002 active
- First API call: Additional 10-15 seconds for Gateway internal initialization
- Between bot restarts: 5 seconds to allow Gateway to release old clientId

### Systemd Service Configuration
**Gateway startup script** (`/etc/systemd/system/ibkr-gateway.service`):
```ini
[Unit]
Description=IBKR Gateway for Trading Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
User=saladbar751
WorkingDirectory=/home/saladbar751/Jts/ibgateway
ExecStart=/home/saladbar751/Jts/ibgateway/ibgateway
Restart=on-failure
RestartSec=30s

[Install]
WantedBy=multi-user.target
```

---

## 7. Things to Avoid

### Known Anti-Patterns
- ❌ **Using Docker images for Gateway on Pi** - All x86_64 images fail on ARM64
- ❌ **snapshot=False for market data** - Causes buffer overflow
- ❌ **Cycle intervals <300 seconds** - Triggers Gateway rate limiting
- ❌ **Strike counts >10** - Overwhelms Gateway with subscription requests
- ❌ **Concurrent symbol processing >2** - Pi CPU becomes bottleneck
- ❌ **Multi-hour historical data requests** - Gateway timeouts inevitable
- ❌ **Reusing same clientId after crashes** - Causes "clientId in use" errors

### Configuration Mistakes
- ❌ Default username "pi" when custom username configured in Imager
- ❌ Timeout values <5 seconds for snapshot mode requests
- ❌ RTH=false for historical data (extended hours data unreliable)
- ❌ Hardcoded IP addresses in configs (use environment variables)
- ❌ Running bot and Gateway in same Docker container (resource contention)

---

## 8. Reference Commands

### Useful Docker Commands
```bash
# View Gateway logs
docker logs ibkr-gateway -f --tail 100

# Restart Gateway to clear stale connections
docker restart ibkr-gateway

# Check Gateway resource usage
docker stats ibkr-gateway

# Clean up stopped containers
docker system prune -a
```

### Useful Pi System Commands
```bash
# Check port 4002 listening (Gateway API)
ss -tln | grep 4002

# Monitor system resources
htop
free -h
df -h

# Check Python environment
which python
python --version
pip list | grep ib-insync

# View bot logs
tail -f ~/ibkr-options-bot/logs/bot.log

# Check systemd service status
systemctl status ibkr-gateway
journalctl -u ibkr-gateway -f
```

### Debugging Connection Issues
```bash
# Test Gateway connectivity (alpha repo script)
cd ~/ibkr-options-bot
python test_ibkr_connection.py --host 127.0.0.1 --port 4002 --client-id 101 --timeout 10

# Quick broker connection test
python -c "from ib_insync import IB; ib = IB(); ib.connect('127.0.0.1', 4002, clientId=101); print('Connected'); ib.disconnect()"
```

---

## 9. Open Questions from Alpha

- [ ] **Is GHCR authentication viable for gyrasol/ibkr-gateway image?** (Requires GitHub PAT with read:packages scope)
- [ ] **Can IBC Controller be compiled for ARM64?** (Would enable containerized Gateway)
- [ ] **What is Gateway's exact rate limit threshold?** (Observed ~3 cycles before throttling)
- [ ] **Can clientId be dynamically generated per session?** (Avoid manual increment on restarts)
- [ ] **Is there a Gateway API to query current subscription count?** (For proactive buffer monitoring)
- [ ] **Does snapshot mode support Level 2 depth data?** (Not tested in alpha)

---

## 10. Production Recommendations

Based on alpha learnings, production implementation should:

1. **Use snapshot mode exclusively** (`snapshot=True`) for all market data requests
2. **Deploy Gateway manually** on Pi (Docker images unreliable on ARM64)
3. **Implement systemd services** for both Gateway and bot auto-start
4. **Use 5-minute minimum cycle intervals** (300 seconds) to prevent rate limiting
5. **Limit strike count to 3-5** near-ATM strikes per symbol
6. **Implement clientId rotation** (increment on each restart or use timestamp-based)
7. **Add Gateway health checks** (port 4002 connectivity before bot cycles)
8. **Monitor system resources** (Gateway + bot should stay under 2GB RAM)
9. **Log Gateway metrics** if possible (subscription count, buffer size)
10. **Plan for Gateway restarts** (nightly or after N hours of operation)

---

**Do NOT copy code from alpha repo. This is configuration and observation documentation only.**

**Last Updated:** February 5, 2026
**Alpha Repository:** https://github.com/aaronshirley751/ibkr-options-bot (private)
**Production Repository:** https://github.com/aaronshirley751/ibkr-trading-bot-production (this repo)
