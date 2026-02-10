# VSC Handoff Prompt: Task 3.1.1 Documentation Reconciliation

## Context for Engineer

Task 3.1 Docker deployment is **working correctly** but the documentation drifted from the original v2 specification during troubleshooting. This task reconciles the documentation with actual implementation.

---

## Instructions

Please execute the following three items:

### 1. Delete Orphaned config.ini

The `docker/gateway/config.ini` file is no longer used — the container uses its internal template with environment variable substitution. Delete it:

```bash
cd C:\Users\tasms\IBKR_PROJECT\ibkr-trading-bot-production
rm docker/gateway/config.ini
git add -A
git commit -m "Task 3.1.1: Remove orphaned config.ini (env vars used instead)"
```

### 2. Verify README.md Accuracy

Review `docker/gateway/README.md` and ensure the Quick Start section matches the actual working workflow:

**Actual working workflow:**
```bash
cd docker/gateway
cp .env.example .env
# Edit .env with credentials (NO quotes around password)
docker compose up -d
docker compose logs -f
# Wait for "Login has completed" message
docker ps  # Should show "healthy"
```

**Key points to verify/update in README:**
- No mention of mounting config.ini (we don't use it)
- Password should NOT have quotes in .env
- Health check uses bash /dev/tcp (not netcat)
- Image is from Docker Hub `gnzsnz/ib-gateway:stable` (not ghcr.io)

If any sections reference the old approach, update them.

### 3. Update .env.example Comments

Ensure `.env.example` has accurate comments about password quoting:

```bash
# Your IBKR account password
# NOTE: Do NOT wrap password in quotes - they become part of the value
# Special characters like $ ? , _ are fine without quotes
TWS_PASSWORD=your_password_here
```

### 4. Commit and Push

```bash
git add -A
git commit -m "Task 3.1.1: Documentation reconciliation for Docker deployment v2.1

- Removed orphaned config.ini (env vars used instead of mounted config)
- Updated README.md to match actual working workflow
- Clarified .env password quoting rules
- Verified Quick Start accuracy"

git push
```

---

## Verification Checklist

After completing the above:

- [ ] `docker/gateway/config.ini` no longer exists
- [ ] README.md Quick Start matches actual deployment steps
- [ ] No references to CUSTOM_CONFIG or mounting config.ini
- [ ] Password quoting guidance is clear in .env.example
- [ ] Changes committed and pushed

---

## Notes

The v2 handoff document (`docs/VSC_HANDOFF_Task_3_1_IBC_Controller_Config_Docker_v2.md`) can remain as historical reference — it documents the original design intent. The README.md in `docker/gateway/` is the authoritative deployment guide.

If you prefer, you can also add a note at the top of the v2 handoff:

```markdown
> **Note:** This document reflects the original v2 design. The actual implementation
> differs slightly due to container image behavior discovered during deployment.
> See `docker/gateway/README.md` for the authoritative deployment guide.
```

---

**Estimated time:** 15-30 minutes
**Priority:** Low (documentation debt)
**Board task:** 42rwhf1_FU2ZHH3uMFQBxmUAFhlU
