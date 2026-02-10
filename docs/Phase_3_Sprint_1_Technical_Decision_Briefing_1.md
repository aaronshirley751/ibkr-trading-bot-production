# Phase 3 Sprint 1 — Technical Decision Briefing for Factory Floor Engineer

**Date:** 2026-02-10
**Purpose:** Assess current bot deployment architecture and recommend path forward for Tasks 3.4-3.6
**Audience:** Factory Floor Engineer (Implementation Lead)
**Prepared By:** @Chief_of_Staff, @PM, @Systems_Architect

---

## Context: Where We Are

### Sprint 1 Progress (50% Complete)

You've completed 3 major tasks:

**Task 3.1: Gateway Docker Deployment** (Commits: 2b8c753, 31703c1)
- Gateway runs in Docker container
- Defined in: `docker/gateway/docker-compose.yml`
- Container name: `gateway` (or similar)
- Port: 4002 exposed
- Health checks: Built-in Docker healthcheck using bash `/dev/tcp/localhost/4002`
- Auto-restart: Docker restart policy configured

**Task 3.2: Bot Startup Orchestration** (Commit: 5983414)
- Bot validates Gateway readiness at startup
- Retry logic with exponential backoff
- 20 new tests added, 527 total tests passing
- **QUESTION:** How is the bot currently deployed? (See questions below)

**Task 3.3: Health Monitoring System** (Commit: 93a7143)
- Monitoring runs in Docker containers (`gateway-monitor`, `bot-monitor`)
- Defined in: `monitoring/docker-compose.monitoring.yml`
- Checks Gateway + Bot health every 60 seconds
- Discord alerts on failures
- Auto-recovery for Gateway (single attempt)

---

## Critical Questions for You

### Question 1: Bot Deployment Architecture

**Please describe the current bot deployment:**

**Option A: Bot is Containerized (Docker)**
- [ ] Yes, the bot runs in a Docker container
- [ ] Dockerfile exists at: `________________________` (fill in path)
- [ ] Bot service defined in: `________________________` (docker-compose file path)
- [ ] Container name: `________________________`
- [ ] How does bot container start? (Auto with compose? Manually? Systemd?)

**Option B: Bot Runs Natively (Not Containerized)**
- [ ] Yes, the bot runs as a native Python process (not Docker)
- [ ] Entrypoint script: `________________________` (e.g., `python src/main.py`)
- [ ] How does bot start? (Manually? Systemd service? Cron? Script?)
- [ ] Working directory: `________________________`

**Option C: Unclear/Mixed**
- [ ] I'm not sure — need to check the codebase
- [ ] It depends on the environment (development vs. production)

**Action Item:** Please check the repository and fill in the blanks above.

**How to verify:**
```bash
# Check if bot Dockerfile exists
ls -la docker/bot/Dockerfile
ls -la Dockerfile

# Check if bot is in a compose file
grep -r "trading-bot\|ibkr-bot\|bot:" docker/ monitoring/

# Check if bot is running as Docker container right now
docker ps | grep -i bot

# Check if bot runs natively
ps aux | grep python | grep -i bot
```

---

### Question 2: Docker Compose File Structure

**Current state — please verify:**

**Gateway Compose File:**
- Path: `docker/gateway/docker-compose.yml`
- Services defined: `gateway` (IBKR Gateway container)
- Status: ✅ Operational

**Monitoring Compose File:**
- Path: `monitoring/docker-compose.monitoring.yml`
- Services defined: `gateway-monitor`, `bot-monitor` (health check containers)
- Status: ✅ Operational

**Question:** Are these two compose files **currently run together** or **separately**?

- [ ] **Together:** I run `docker compose -f docker/gateway/docker-compose.yml -f monitoring/docker-compose.monitoring.yml up -d`
- [ ] **Separately:** I run them in separate commands:
  - `docker compose -f docker/gateway/docker-compose.yml up -d` (for Gateway)
  - `docker compose -f monitoring/docker-compose.monitoring.yml up -d` (for Monitoring)
- [ ] **Other:** (describe): `___________________________________________`

**Question:** Do the containers communicate correctly across these separate compose files?
- [ ] Yes — all containers on same Docker network, everything works
- [ ] No — there are networking issues
- [ ] Not sure — haven't tested cross-compose communication

**Action Item:** Please describe the current startup procedure you follow when starting the system.

---

### Question 3: Bot-Gateway Communication

**How does the bot connect to the Gateway?**

Please check the bot's configuration and fill in:

**Gateway Connection Details:**
- Gateway host used by bot: `________________________` (e.g., `localhost`, `gateway`, `127.0.0.1`)
- Gateway port used by bot: `________________________` (should be 4002)
- Configuration source: `________________________` (e.g., `.env`, hardcoded, command-line arg)

**If bot is containerized:**
- [ ] Bot and Gateway are on the same Docker network
- [ ] Docker network name: `________________________`
- [ ] Bot connects to Gateway via container name (e.g., `gateway:4002`)

**If bot is native:**
- [ ] Bot connects to Gateway via `localhost:4002` or `127.0.0.1:4002`

**Verification Test:**
When both Gateway and bot are running, does the bot successfully connect to Gateway?
- [ ] Yes — bot connects and can query market data / place orders (in dry-run mode)
- [ ] No — there are connection issues
- [ ] Not tested yet

---

### Question 4: Current Startup Sequence

**Please describe step-by-step how you currently start the entire system:**

**Example Answer:**
```
1. Start Gateway: `docker compose -f docker/gateway/docker-compose.yml up -d`
2. Wait 60 seconds for Gateway to authenticate
3. Start Monitoring: `docker compose -f monitoring/docker-compose.monitoring.yml up -d`
4. Start Bot: `python src/main.py` (or `docker compose -f bot/docker-compose.yml up -d`)
5. Verify all healthy: Check Discord for alerts, check `docker ps`, check bot logs
```

**Your Answer:**
```
1. ___________________________________________________________
2. ___________________________________________________________
3. ___________________________________________________________
4. ___________________________________________________________
5. ___________________________________________________________
```

**Follow-up:** How many steps are manual vs. automated?
- Manual steps: `______` (e.g., "Steps 1-4 are manual")
- Automated: `______` (e.g., "Once started, restarts are automatic via Docker")

---

### Question 5: System Boot Behavior

**What happens when the host machine (your desktop or the future rackmount server) reboots?**

**Gateway:**
- [ ] Starts automatically (Docker restart policy or systemd service)
- [ ] Requires manual start (`docker compose up -d`)
- [ ] Not sure

**Monitoring:**
- [ ] Starts automatically
- [ ] Requires manual start
- [ ] Not sure

**Bot:**
- [ ] Starts automatically
- [ ] Requires manual start
- [ ] Not sure

**Goal for Task 3.5 (Zero-Touch Startup):**
After system reboot → everything starts automatically → no manual intervention → system is operational.

**Question:** Are we already at this goal, or is manual intervention currently required?
- [ ] Already zero-touch (everything starts automatically)
- [ ] Partially automated (some things start automatically, some require manual start)
- [ ] Fully manual (nothing starts automatically after reboot)

---

### Question 6: Preferred Docker Compose Strategy

**If we unify the compose files, which structure do you prefer?**

**Option A: Single Unified File**
```
docker-compose.yml
services:
  gateway:
    # IBKR Gateway
  trading-bot:
    # Trading bot (if containerized)
    depends_on:
      gateway:
        condition: service_healthy
  gateway-monitor:
    # Gateway health monitor
  bot-monitor:
    # Bot health monitor
```

**Pros:**
- Single command to start everything: `docker compose up -d`
- Easier to understand dependencies
- Simpler for zero-touch startup (one systemd service)

**Cons:**
- Larger file, potentially harder to navigate
- Changes to one service require reloading all

**Option B: Separate Files with Shared Network**
```
docker/gateway/docker-compose.yml       # Gateway
monitoring/docker-compose.monitoring.yml # Monitoring
docker/bot/docker-compose.yml           # Bot (if containerized)
```

**Pros:**
- Modular — can start/stop components independently
- Easier to maintain separate concerns

**Cons:**
- More complex startup: `docker compose -f file1.yml -f file2.yml -f file3.yml up -d`
- Requires shared Docker network configuration

**Your Preference:**
- [ ] **Option A:** Unified single file
- [ ] **Option B:** Separate files
- [ ] **No preference:** Either works

---

## Decision Framework

Based on your answers above, we'll recommend one of three paths:

### Path A: Quick Consolidation (2-3 hours)
**Best if:**
- Bot is already containerized
- Separate compose files work but would benefit from unification
- Minimal additional work needed

**Work:**
- Merge compose files into unified stack (or establish shared network)
- Validate all containers communicate
- Mark Task 3.4 complete
- Proceed to Task 3.5 (zero-touch startup)

---

### Path B: Bot Containerization + Full Orchestration (4-6 hours)
**Best if:**
- Bot is currently running natively
- You want full Docker containerization before proceeding

**Work:**
- Create Dockerfile for bot
- Add bot service to docker-compose.yml
- Configure volumes (gameplan JSON, logs, data persistence)
- Test bot container connects to Gateway
- Unify with monitoring services
- Mark Task 3.4 complete
- Proceed to Task 3.5 (zero-touch startup)

---

### Path C: Defer Task 3.4, Focus on Zero-Touch Startup (3-4 hours)
**Best if:**
- Current setup works well enough
- Prefer to focus on auto-start behavior (Task 3.5)
- Can revisit compose consolidation later if needed

**Work:**
- Skip Task 3.4 for now (defer to backlog)
- Implement zero-touch startup (systemd services for Docker Compose)
- Ensure system boots → everything starts automatically
- Mark Task 3.5 complete
- Then Task 3.6 (QA review + 48-hour stability test)

---

## Information We Need From You

**Please provide:**

1. **Bot deployment status** (containerized vs. native — see Question 1)
2. **Current compose file structure** (unified vs. separate — see Question 2)
3. **Bot-Gateway communication details** (how does bot connect — see Question 3)
4. **Current startup procedure** (step-by-step — see Question 4)
5. **Boot behavior** (what auto-starts — see Question 5)
6. **Compose strategy preference** (unified vs. separate — see Question 6)

**How to provide this information:**

Option 1: Fill in the blanks in this document and send it back
Option 2: Create a short text summary answering the 6 questions
Option 3: Pair with @PM/Boardroom for 15-minute Q&A session

---

## Additional Context (If Helpful)

### Current Repository Structure (Best Guess)

```
ibkr-trading-bot/
├── docker/
│   └── gateway/
│       └── docker-compose.yml          # Gateway service (Task 3.1)
├── monitoring/
│   ├── docker-compose.monitoring.yml   # Monitoring services (Task 3.3)
│   ├── health_check.py
│   ├── discord_alerts.py
│   └── ... (14 files total)
├── src/
│   ├── main.py                         # Bot entrypoint (Task 3.2)
│   ├── broker/                         # Phase 2 - Gateway integration
│   ├── strategies/                     # Phase 2 - Strategy A/B/C
│   ├── risk/                           # Phase 2 - Risk controls
│   └── ...
├── tests/                              # 527 passing tests
├── docker-compose.yml                  # ??? Does this exist? Unified file?
└── Dockerfile                          # ??? Does this exist? Bot container?
```

**Please verify:**
- Does `docker-compose.yml` exist at repo root? What's in it?
- Does `Dockerfile` exist at repo root? What does it build?
- Does `docker/bot/` directory exist?

---

### Task 3.4 Original Scope (from Phase 3 Kickoff Plan)

**Title:** Implement Docker Compose orchestration [x86_64 target]

**Original Intent:**
- Multi-container stack (Gateway + Bot + supporting services)
- Networking configuration
- Volume mounts for persistent data
- Health checks and restart policies
- Production-grade orchestration

**What's Already Done (Tasks 3.1-3.3):**
- ✅ Gateway in Docker with health checks and restart policy
- ✅ Monitoring in Docker with health checks
- ✅ Bot startup logic implemented (waits for Gateway)
- ✅ All services communicate (assumed working based on Task 3.2/3.3 completion)

**What Might Be Missing:**
- Bot containerization (if currently native)
- Unified compose file (if currently separate files)
- Systemd integration for auto-start on boot (this is Task 3.5)

---

### Why This Matters

**Goal:** Phase 3 aims for **zero-touch automation**. The system should:
1. Start automatically on boot (no manual intervention)
2. Recover automatically from failures
3. Alert operator when manual intervention is needed
4. Run reliably for 48+ hours without babysitting

**Current State:**
- Tasks 3.1-3.3 handle automatic recovery ✅
- Task 3.4 handles orchestration (partially done?)
- Task 3.5 handles auto-start on boot (not done yet)
- Task 3.6 validates everything works (48-hour test)

**Your input helps us:**
- Avoid duplicate work (if Task 3.4 is already done)
- Focus effort on what's actually missing
- Choose the right path forward (A, B, or C)

---

## Timeline Estimate (After Your Input)

**Path A (Quick Consolidation):**
- Task 3.4: 2-3 hours
- Task 3.5: 4-5 hours (design + implementation)
- Task 3.6: 90 min + 48-hour wait
- **Total:** 2-3 days

**Path B (Bot Containerization + Full Orchestration):**
- Task 3.4: 4-6 hours
- Task 3.5: 4-5 hours
- Task 3.6: 90 min + 48-hour wait
- **Total:** 3-4 days

**Path C (Defer 3.4, Focus on Auto-Start):**
- Task 3.5: 4-5 hours
- Task 3.6: 90 min + 48-hour wait
- **Total:** 2-3 days (Task 3.4 deferred to backlog)

---

## Next Steps

**Please:**
1. Review this document
2. Answer the 6 questions (fill in blanks or provide summary)
3. Indicate path preference (A, B, or C) if you have one
4. Send back to @PM/Boardroom

**We'll then:**
1. Analyze your responses
2. Recommend the optimal path forward
3. Prepare handoff prompt for next session
4. Proceed with Sprint 1 completion

---

**Thank you for your meticulous engineering work on Tasks 3.1-3.3. The quality has been exceptional. This decision briefing ensures we maintain that quality and efficiency for the sprint finish.**

---

**Document Version:** 1.0
**Prepared By:** @Chief_of_Staff, @PM, @Systems_Architect
**Date:** 2026-02-10
**Purpose:** Technical decision support for Tasks 3.4-3.6 path selection
