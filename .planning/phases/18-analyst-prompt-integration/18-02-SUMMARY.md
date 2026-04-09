---
phase: 18-analyst-prompt-integration
plan: 02
subsystem: agents
tags: [vol-context, prompt-injection, langchain, social-analyst, news-analyst, fundamentals-analyst]

# Dependency graph
requires:
  - phase: 18-01
    provides: extract_vol_note() utility, vol_note_market/vol_note_technical pattern established
provides:
  - social_media_analyst injects vol_directive (Moderate) + vol_block, returns vol_note_social
  - news_analyst injects vol_directive (Weak/news-causation) + vol_block, returns vol_note_news
  - fundamentals_analyst injects vol_directive (Weak/IV-threshold) + vol_block, returns vol_note_fundamentals
affects:
  - 19 (frontend vol banner reads all 5 vol_note_* fields)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - vol_context injected via prompt.partial(), not message mutation (same as 18-01)
    - Moderate directive: P/C ratio + flow cross-reference with sentiment (social analyst)
    - Weak directive: only-if-causal framing prevents reflexive vol mention (news analyst)
    - Weak directive: IV rank > 90th percentile threshold gate (fundamentals analyst)

key-files:
  created: []
  modified:
    - tradingagents/agents/analysts/social_media_analyst.py
    - tradingagents/agents/analysts/news_analyst.py
    - tradingagents/agents/analysts/fundamentals_analyst.py

key-decisions:
  - "Weak directive uses 'only if' and 'do not generically mention' phrasing to prevent reflexive vol citation in news/fundamentals"
  - "vol_note returned as None (not omitted) when analyst is mid-tool-call loop (tool_calls != 0)"
  - "Fundamentals IV threshold set at 90th percentile as specified — below threshold vol is explicitly labeled noise"

requirements-completed: [ANALYST-01, ANALYST-02, ANALYST-03]

# Metrics
duration: 3min
completed: 2026-04-09
---

# Phase 18 Plan 02: Analyst Prompt Integration (Social + News + Fundamentals) Summary

**Moderate/Weak vol directives plus vol_block injection applied to social, news, and fundamentals analysts; all 5 equity analysts now emit vol_note_* fields via extract_vol_note() with no message history mutation**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-09T12:55:04Z
- **Completed:** 2026-04-09T12:57:59Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `social_media_analyst.py`: Moderate vol directive — P/C ratio and unusual flow cross-referenced with sentiment data; returns `vol_note_social`
- `news_analyst.py`: Weak vol directive — only if a specific news event is the identifiable cause of elevated IV; returns `vol_note_news`
- `fundamentals_analyst.py`: Weak vol directive — flag only when IV rank exceeds 90th percentile; returns `vol_note_fundamentals`
- All 3 analysts use `extract_vol_note()` from shared `vol_note_utils.py` (no duplication)
- All 3 analysts inject `vol_block` and `vol_directive` via `prompt.partial()` — zero message history mutation confirmed
- Phase completion: 5/5 analysts wired; 5 `state.get("vol_context")` calls; 5 `vol_note_*` return keys; 5 `extract_vol_note` imports

## Task Commits

1. **Task 1: social_media_analyst + news_analyst** — `879adf5` (feat)
2. **Task 2: fundamentals_analyst + cross-analyst verification** — `5b35c4e` (feat)

## Files Modified

- `tradingagents/agents/analysts/social_media_analyst.py` — Moderate directive, vol_block injection, vol_note_social return
- `tradingagents/agents/analysts/news_analyst.py` — Weak (news-causation) directive, vol_block injection, vol_note_news return
- `tradingagents/agents/analysts/fundamentals_analyst.py` — Weak (IV-threshold) directive, vol_block injection, vol_note_fundamentals return

## Verification Results

```
# vol_note_* in analyst return dicts (must be exactly 5):
5 lines found — market, technical, social, news, fundamentals

# extract_vol_note imports in analysts (must be exactly 5):
5 lines found

# state.get("vol_context") calls in analysts (must be exactly 5):
5 lines found

# HumanMessage vol / append vol_context (must be 0):
0 lines found — no message mutation

# extract_vol_note("**Vol Note:** test") == "test":
UTIL OK
```

## Decisions Made

- **Weak directive phrasing is strict:** News and Fundamentals directives use "only if", "do not generically mention", and "only when" — this prevents LLM reflexive vol citation that Moderate/Strong framing allows. The wording is intentionally stronger than "consider".
- **vol_note gated on tool_calls == 0:** Returning `None` (not omitting key) during tool-call loops prevents KeyError downstream while staying consistent with the state field contract.
- **IV 90th percentile is the explicit threshold:** Below it, the directive explicitly labels vol context as "background noise" — this is a deliberate UX/auditability choice, not a placeholder.

## Deviations from Plan

None — plan executed exactly as written. The 4-step pattern established in 18-01 applied cleanly to all three remaining analysts.

## Known Stubs

None — all three analysts fully wire vol_context from state and return extracted vol_note_* fields. No placeholder text or hardcoded values.

## Phase 18 Completion Status

ANALYST-01: All 5 analysts call `state.get("vol_context")` and inject via `prompt.partial()` — confirmed by grep (5 lines each)
ANALYST-02: Market=Strong, Technical/Social=Moderate, News/Fundamentals=Weak directives — confirmed in respective files
ANALYST-03: `extract_vol_note()` in all 5 return dicts; None-safe when vol_context absent — confirmed by grep and util test

## Self-Check: PASSED

- `tradingagents/agents/analysts/social_media_analyst.py` — FOUND (modified)
- `tradingagents/agents/analysts/news_analyst.py` — FOUND (modified)
- `tradingagents/agents/analysts/fundamentals_analyst.py` — FOUND (modified)
- Commit `879adf5` — FOUND
- Commit `5b35c4e` — FOUND

---
*Phase: 18-analyst-prompt-integration*
*Completed: 2026-04-09*
