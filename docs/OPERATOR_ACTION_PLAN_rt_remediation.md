# OPERATOR ACTION PLAN — Red Team Remediation Implementation

> **Date:** 2026-02-07
> **Context:** Red Team Report Rev 1.1 — Conditional Pass Remediation
> **Tasks Created on IBKR Board:** RT-REM-1 through RT-REM-5

---

## WHAT THE BOARDROOM HAS PRODUCED (Ready for You)

The following files are attached to this action plan. They are complete deliverables from the responsible personas:

| File | Owner | Purpose |
|------|-------|---------|
| `VSC_HANDOFF_TEMPLATE_v2.md` | @Systems_Architect | New handoff document template (RT-REM-1) |
| `copilot-instructions.md` | @DevOps | Copilot Agent Mode context priming file (RT-REM-2) |
| `factory_floor_model_routing_guide.md` | @Lead_Quant + @CRO | Model selection doctrine (RT-REM-3) |
| `factory_floor_session_log.md` | @QA_Lead | Session performance tracking template (RT-REM-4) |

---

## WHAT YOU NEED TO DO

### Action 1: Add Copilot Instructions to Repository (RT-REM-2)
**Where:** GitHub repository / VSCode
**Time:** ~5 minutes
**Priority:** Do this first — immediate value, zero cost

**Steps:**

1. Open your `ibkr-trading-bot-production` repository in VSCode
2. Check if a `.github/` directory already exists at the repo root:
   ```bash
   ls -la .github/
   ```
   It should already exist (it holds your `workflows/ci.yml` from Task 0.4).

3. Create the file `.github/copilot-instructions.md` using the content from the attached `copilot-instructions.md` file. You can do this by:
   - Copying the attached file directly into `.github/copilot-instructions.md`, OR
   - Opening VSCode, creating a new file at `.github/copilot-instructions.md`, and pasting the content

4. Commit and push:
   ```bash
   git add .github/copilot-instructions.md
   git commit -m "RT-REM-2: Add Copilot Agent Mode instruction file

   - Project conventions, IBKR quirks, quality standards
   - Automatically included in every Copilot agent session context
   - Source: Red Team Report Rev 1.1 remediation"
   git push origin main
   ```

5. **Verify it works:** Open a new Copilot Agent Mode chat in VSCode. At the start of the session, the agent should now have awareness of project conventions without being told. Test by asking: "What port should IBKR Gateway use for paper trading?" — it should answer 4002 without you providing context.

**Optional enhancement:** You can also create a `.vscode/copilot-instructions.md` with workspace-specific overrides if needed in the future. For now, the `.github/` level file covers everything.

---

### Action 2: Add Handoff Template v2 to Repository (RT-REM-1)
**Where:** GitHub repository / VSCode
**Time:** ~2 minutes
**Priority:** Blocking condition for Red Team full pass

**Steps:**

1. Copy the attached `VSC_HANDOFF_TEMPLATE_v2.md` into your `docs/` directory:
   ```bash
   cp [downloaded file] docs/VSC_HANDOFF_TEMPLATE_v2.md
   ```

2. Commit and push:
   ```bash
   git add docs/VSC_HANDOFF_TEMPLATE_v2.md
   git commit -m "RT-REM-1: Add VSC Handoff Template v2 (agent-execution-primary)

   - Agent Execution Block is now the primary content
   - Per-step validation replaces end-only validation
   - Model routing hint and context budget in header
   - Context Block moved to end (human reference, agent can skip)
   - Source: Red Team Report Rev 1.1 remediation"
   git push origin main
   ```

3. **No further action needed now.** The next time the Boardroom produces a blueprint, @Systems_Architect will use this template. You'll see the difference in the document structure.

---

### Action 3: Add Model Routing Guide to Repository (RT-REM-3)
**Where:** GitHub repository / VSCode
**Time:** ~2 minutes
**Priority:** Non-blocking, do before next project adopts this methodology

**Steps:**

1. Copy the attached `factory_floor_model_routing_guide.md` into your `docs/` directory:
   ```bash
   cp [downloaded file] docs/factory_floor_model_routing_guide.md
   ```

2. Commit and push:
   ```bash
   git add docs/factory_floor_model_routing_guide.md
   git commit -m "RT-REM-3: Add Factory Floor model routing guide

   - Model selection matrix by task class
   - Anti-patterns and budget planning reference
   - Quick reference for all Copilot dropdown models
   - Source: Red Team Report Rev 1.1 remediation"
   git push origin main
   ```

3. **Reference this guide** when opening a new Copilot Agent Mode session. Glance at the task you're about to execute, match it to the matrix, and select the appropriate model from the dropdown before handing off the blueprint.

---

### Action 4: Add Session Performance Log to Repository (RT-REM-4)
**Where:** GitHub repository / VSCode
**Time:** ~2 minutes to set up, ~30 seconds per session to maintain
**Priority:** Non-blocking, start logging whenever convenient

**Steps:**

1. Copy the attached `factory_floor_session_log.md` into your `docs/` directory:
   ```bash
   cp [downloaded file] docs/factory_floor_session_log.md
   ```

2. Commit and push:
   ```bash
   git add docs/factory_floor_session_log.md
   git commit -m "RT-REM-4: Add Factory Floor session performance log

   - Tracking template for model performance by task type
   - Monthly review template for routing guide refinement
   - Source: Red Team Report Rev 1.1 remediation"
   git push origin main
   ```

3. **After each Factory Floor session**, add a row to the log table. This takes ~30 seconds:
   - What task/chunk did you run?
   - What model did you use?
   - How many iterations before validation passed?
   - Did it succeed?
   - Anything notable?

4. **Monthly:** Fill in the review template at the bottom. Look for patterns. Update the routing guide if data suggests changes.

---

### Action 5: Claude Code Evaluation (RT-REM-5)
**Where:** N/A — this is a future task
**Time:** ~2-3 hours when scheduled
**Priority:** Post-Phase 1 only. Do not schedule during active sprint work.

**No action required now.** The task is on the IBKR board in the Planning bucket. When Phase 1 is deployed and you have bandwidth for tooling evaluation, the task description contains the full protocol:
1. Pick a completed handoff document
2. Install Claude Code (`npm install -g @anthropic-ai/claude-code`)
3. Execute the same handoff via Claude Code
4. Compare results against the Copilot execution
5. Write up findings

---

### Action 6: Update Claude Desktop Project Instructions (Optional)
**Where:** Claude Desktop → This Project → Project Instructions
**Time:** ~5 minutes
**Priority:** Optional but recommended

If you want the Boardroom to automatically reference the new template when producing blueprints, consider adding a note to the Crucible system prompt. Specifically, in the **Protocol C: System Blueprinting** section, you could add:

> **Template Requirement:** All VSC Handoff Documents must follow the v2 template structure defined in `docs/VSC_HANDOFF_TEMPLATE_v2.md`. The Agent Execution Block is the primary content. The Context Block is supplementary. Include model routing recommendation and context budget in the header.

This is optional because the Boardroom team is already aware of the template change from this session. Adding it to the instructions makes it persistent across future sessions and context windows.

---

## SUMMARY — Execution Order

| # | Action | Where | Time | Priority |
|---|--------|-------|------|----------|
| 1 | Add `copilot-instructions.md` to `.github/` | VSCode → Git | 5 min | 🔴 Do first |
| 2 | Add `VSC_HANDOFF_TEMPLATE_v2.md` to `docs/` | VSCode → Git | 2 min | 🔴 Blocking |
| 3 | Add `factory_floor_model_routing_guide.md` to `docs/` | VSCode → Git | 2 min | 🟡 Soon |
| 4 | Add `factory_floor_session_log.md` to `docs/` | VSCode → Git | 2 min | 🟡 Soon |
| 5 | Claude Code evaluation | Terminal | 2-3 hrs | ⚪ Post Phase 1 |
| 6 | Update Crucible system prompt (optional) | Claude Desktop | 5 min | ⚪ Optional |

**Total immediate time commitment: ~11 minutes for Actions 1-4.**

---

*@Chief_of_Staff — Remediation delegation complete. All Boardroom deliverables produced. Operator action plan issued. Board tasks created and tracked.*
