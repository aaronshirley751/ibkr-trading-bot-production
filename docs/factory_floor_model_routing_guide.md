# Factory Floor Model Routing Guide

> **Version:** 1.0
> **Date:** 2026-02-07
> **Source:** Red Team Report RT-MOD-4 Remediation
> **Owners:** @Lead_Quant + @CRO
> **Review Cadence:** Quarterly, or when new models are added to Copilot
> **Subscription:** GitHub Copilot Pro+ (1,500 premium requests/month)

---

## Model Routing Matrix

| Task Class | Recommended Model | Mult. | Monthly Budget Impact | Rationale |
|-----------|-------------------|:-----:|:---------------------:|-----------|
| **Trivial:** linting fixes, formatting, single-line edits, docstring additions | GPT-4.1 or Auto | 0x | Free | No reasoning depth required. Save premium requests. |
| **Simple:** directory scaffolding, empty file stubs, config file creation, `.gitignore` updates | Claude Haiku 4.5 | 0.33x | ~3 sessions = 1 premium request | Structured but simple. Haiku follows file creation patterns well. |
| **Standard:** single-file test implementation, function writing, moderate refactoring | Claude Sonnet 4.5 | 1x | 1:1 | Best cost/performance ratio. Zero-error code editing benchmarks. Strong sequencing. |
| **Blueprint Execution:** multi-file handoff document implementation, test suite chunks | Claude Sonnet 4.5 | 1x | 1:1 | Handles multi-step agent workflows with planning. Default for all handoff docs unless complexity warrants Opus. |
| **Complex:** async/await patterns, IBKR API integration, multi-threaded coordination, intricate dependency chains | Claude Opus 4.6 | 3x | 1 session = 3 premium requests | Deep reasoning justified. Use when Sonnet would likely need 3+ iterations. |
| **Risk-Critical:** risk guards, circuit breakers, position sizing, safety mechanisms | Claude Opus 4.6 | 3x | 1 session = 3 premium requests | Zero tolerance for missed edge cases. @CRO mandates highest capability for capital-risk code. |
| **Experimental:** testing an unfamiliar model's capabilities | Manual select | varies | Deliberate | Never use Auto for evaluation. Pick the model explicitly and log results. |

---

## Anti-Patterns

| Pattern | Why It's Wrong | Do This Instead |
|---------|---------------|-----------------|
| **Auto mode for blueprint execution** | Routes to GPT-5 mini or GPT-4.1 for complex tasks. 10% discount not worth wasted session. | Manually select Sonnet 4.5 or Opus 4.6. |
| **Opus for everything** | Burns 3x premium requests on tasks Sonnet handles equally well. 500 effective sessions vs 1,500. | Reserve Opus for complex/risk-critical only. |
| **Preview models for production work** | GPT-5, GPT-5-Codex (Preview) carry ⚠️ warnings. Known instability, starts/stops without explanation. | Use GA (Generally Available) models only. |
| **GPT-5.2 Codex for sequenced tasks** | Documented poor adherence to step-by-step sequencing. Frequent unexplained interruptions. | Use Claude Sonnet 4.5 for sequencing-heavy work. |
| **Not logging model performance** | Can't improve what you don't measure. Instinct is good but fragile. | Log every session in the Performance Log. |

---

## Budget Planning

**Monthly Capacity at Different Usage Profiles:**

| Profile | Model Mix | Effective Sessions/Month |
|---------|-----------|:------------------------:|
| All Opus | 100% Opus 4.6 (3x) | ~500 |
| Current Practice | 80% Sonnet (1x), 20% Opus (3x) | ~1,150 |
| Optimized | 50% Sonnet (1x), 30% Free/Haiku (0x-0.33x), 20% Opus (3x) | ~1,350 |

The operator's current practice (Sonnet default, Opus for deliberate tests) is already close to optimal. Shifting trivial tasks to free-tier models captures the remaining efficiency.

---

## Model Quick Reference (From Copilot Dropdown)

| Model | Tier | Mult. | Status | Notes |
|-------|------|:-----:|--------|-------|
| GPT-4.1 | Free | 0x | ✅ GA | Good for trivial tasks |
| GPT-4o | Free | 0x | ✅ GA | General purpose, adequate for simple work |
| GPT-5 mini | Free | 0x | ✅ GA | Lightweight, fast |
| Grok Code Fast 1 | Free | 0x | ✅ GA | Not evaluated yet |
| Raptor mini (Preview) | Free | 0x | ⚠️ Preview | Untested |
| Claude Haiku 4.5 | Budget | 0.33x | ✅ GA | Good for structured simple tasks |
| Gemini 3 Flash (Preview) | Budget | 0.33x | ⚠️ Preview | Untested |
| Claude Sonnet 4 | Standard | 1x | ✅ GA | Predecessor, still capable |
| **Claude Sonnet 4.5** | **Standard** | **1x** | **✅ GA** | **DEFAULT — Best cost/performance** |
| GPT-5.1 | Standard | 1x | ✅ GA | Strong but less tested in our workflow |
| GPT-5.1-Codex | Standard | 1x | ✅ GA | Optimized for code, 400K context |
| GPT-5.1-Codex-Max | Standard | 1x | ✅ GA | Extended reasoning variant |
| Gemini 2.5 Pro | Standard | 1x | ✅ GA | Being deprecated |
| Gemini 3 Pro (Preview) | Standard | 1x | ⚠️ Preview | Untested |
| Claude Opus 4.5 | Premium | 3x | ✅ GA | Deep reasoning |
| **Claude Opus 4.6** | **Premium** | **3x** | **✅ GA** | **RESERVE — Complex/risk-critical only** |
| GPT-5 | Standard | 1x | ⚠️ Warning | Known instability — avoid |
| GPT-5-Codex (Preview) | Standard | 1x | ⚠️ Warning | Known instability — avoid |
| GPT-5.1-Codex-Mini (Preview) | Budget | 0.33x | ⚠️ Preview | Untested |
| GPT-5.2 | Standard | 1x | ✅ GA | Not evaluated |
| GPT-5.2-Codex | Standard | 1x | ✅ GA | Operator reports poor sequencing adherence |

---

*This guide is a living document. Update quarterly or when the Session Performance Log reveals routing inefficiencies.*
