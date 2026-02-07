# VSC HANDOFF TEMPLATE v2 — Agent-Execution-Primary

> **Template Version:** 2.0
> **Effective Date:** 2026-02-07
> **Source:** Red Team Report RT-MAJ-1 Remediation
> **Usage:** All future VSC Handoff Documents produced by @Systems_Architect must follow this structure.

---

## TEMPLATE — Copy Below This Line For New Handoffs

---

# HANDOFF: [Task ID] — [Feature Name]

| Field | Value |
|-------|-------|
| **Task ID** | [e.g., Coverage-1.1.3] |
| **Date** | [YYYY-MM-DD] |
| **Chunk** | [N of M] |
| **Requested By** | [Protocol/Agent/Operator] |
| **Recommended Model** | [Claude Sonnet 4.5 · 1x / Claude Opus 4.6 · 3x / Claude Haiku 4.5 · 0.33x] |
| **Context Budget** | [Light (<200 lines) / Moderate (200-400 lines) / Heavy (400+ lines, consider splitting)] |
| **Depends On** | [Prior chunk or task ID, or "None"] |

---

## 1. AGENT EXECUTION BLOCK

> **THIS IS THE PRIMARY CONTENT.** Hand this entire document to Copilot Agent Mode.
> The agent should execute these steps sequentially. Each step includes the file path,
> the action, the content or change, and a per-step validation command.

### Step 1: [Action Description]

**File:** `[exact/path/to/file.py]`
**Action:** CREATE | MODIFY | DELETE

```python
# Exact content or diff to apply
```

**Validate:**
```bash
[single command to verify this step, e.g., "ruff check path/to/file.py"]
```

---

### Step 2: [Action Description]

**File:** `[exact/path/to/file.py]`
**Action:** CREATE | MODIFY | DELETE

```python
# Exact content or diff to apply
```

**Validate:**
```bash
[single command to verify this step]
```

---

### Step [N]: [Continue pattern...]

---

## 2. VALIDATION BLOCK

> Run these commands **after all steps are complete.** All must pass.

```bash
# 1. Linting
poetry run ruff check [target paths]

# 2. Formatting
poetry run black --check [target paths]

# 3. Type checking
poetry run mypy [target paths]

# 4. Tests
poetry run pytest [target test paths] -v

# 5. Feature-specific validation
[any additional validation commands]
```

**Expected Results:**
- ruff: 0 errors
- black: "All done! ✨ 🍰 ✨" or equivalent
- mypy: "Success: no issues found"
- pytest: All tests pass (specify expected count if known)

---

## 3. GIT BLOCK

```bash
git add [specific files or paths]
git commit -m "[Task ID] Chunk [N]: [concise description]

- [bullet point of what was done]
- [bullet point of what was done]

[Any relevant context for commit history]"
git push origin main
```

---

## 4. CONTEXT BLOCK (Human Reference — Agent Can Skip)

> **This section exists for the operator's understanding.** It explains *why* decisions
> were made. The agent does not need this to execute the steps above.

### Objective
[One paragraph: what this feature does and why it matters]

### Architecture Notes
[How this fits into the broader system. Dependencies, integration points, design rationale.]

### Edge Cases Considered
- [What happens if X fails?]
- [What happens if Y is null/missing?]
- [What happens if Z times out?]

### Rollback Plan
[How to disable this feature without breaking existing functionality]

---

## 5. DEFINITION OF DONE

- [ ] All steps in Agent Execution Block completed
- [ ] All Validation Block commands pass
- [ ] Git commit pushed to main
- [ ] CI pipeline passes (GitHub Actions)
- [ ] [Feature-specific acceptance criteria]
- [ ] [Feature-specific acceptance criteria]

---

**Document Status:** [✅ Ready for Implementation / 🔄 Draft / ⏳ Awaiting Review]
**Approvals:** [@Systems_Architect (author)] [, @CRO (if risk-critical)] [, @QA_Lead (if test-related)]

---

## TEMPLATE USAGE NOTES (Remove from actual handoffs)

### When to Use Which Model Recommendation

| Task Characteristics | Recommended Model | Multiplier |
|---------------------|-------------------|-----------|
| Trivial: linting, formatting, config edits | GPT-4.1 or Auto | 0x |
| Simple: scaffolding, stubs, single-file | Claude Haiku 4.5 | 0.33x |
| Standard: multi-file implementation, tests | Claude Sonnet 4.5 | 1x |
| Complex: async patterns, API integration, risk-critical | Claude Opus 4.6 | 3x |

### Context Budget Guidelines

| Budget | Line Count | Guidance |
|--------|-----------|----------|
| Light | <200 lines | Single chunk, agent handles easily |
| Moderate | 200-400 lines | Single chunk, may need focused agent attention |
| Heavy | 400+ lines | **Split into multiple chunks.** Copilot's practical context window (64-128K tokens) means large documents lose coherence. |

### Key Differences from Template v1

1. **Agent Execution Block is FIRST** — not buried after pages of context
2. **Per-step validation** — agent can verify as it goes, not just at the end
3. **Model routing hint in header** — operator knows which model to select before opening Copilot
4. **Context budget in header** — signals whether this chunk is appropriately sized
5. **Context Block is LAST** — clearly marked as optional for the agent
6. **No separate "Copilot-Ready Prompt"** — the entire document IS the prompt
