# Factory Floor Session Performance Log

> **Purpose:** Track model performance across Factory Floor sessions to enable evidence-based model selection.
> **Source:** Red Team Report RT-MOD-1 Remediation
> **Owner:** Operator (maintained after each Factory Floor session)
> **Review Cadence:** Monthly — use data to refine the Model Routing Guide

## Log

| Date | Task ID | Chunk | Model Used | Multiplier | Iterations | Success | Notes |
|------|---------|-------|-----------|-----------|------------|---------|-------|
| 2026-02-XX | Example-1.1.2 | 3 of 6 | Claude Sonnet 4.5 | 1x | 1 | ✅ | Clean first-pass execution |
| 2026-02-XX | Example-1.1.2 | 5 of 6 | Claude Opus 4.6 | 3x | 2 | ✅ | Complex async, needed retry on type errors |
| | | | | | | | |

## Field Definitions

- **Date:** Session date
- **Task ID:** IBKR board task identifier
- **Chunk:** Which chunk of the handoff document (e.g., "3 of 6")
- **Model Used:** Exact model name from Copilot dropdown
- **Multiplier:** Premium request cost (0x, 0.33x, 1x, 3x)
- **Iterations:** How many times the agent needed to retry/correct before the step passed validation
- **Success:** ✅ = all validation passed, ❌ = abandoned/required manual intervention
- **Notes:** Notable behaviors, failure modes, observations (especially for models being evaluated)

## Monthly Review Template

### Review Period: [Month Year]

**Sessions Logged:** [count]
**Total Premium Requests Consumed:** [sum of multipliers]

**Model Performance Summary:**

| Model | Sessions | Avg Iterations | Success Rate | Notes |
|-------|----------|---------------|-------------|-------|
| Claude Sonnet 4.5 | | | | |
| Claude Opus 4.6 | | | | |
| Claude Haiku 4.5 | | | | |
| GPT-4.1 | | | | |
| Other | | | | |

**Observations:**
- [Any patterns noticed]
- [Models that surprised positively or negatively]
- [Task types that consistently need higher-tier models]

**Routing Guide Updates:**
- [Any changes to recommend based on this month's data]
