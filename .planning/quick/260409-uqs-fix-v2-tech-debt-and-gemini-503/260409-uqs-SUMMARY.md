---
plan: 260409-uqs
type: quick-fix
tags: [tech-debt, vol-pipeline, gemini, retry]
key-files:
  modified:
    - tradingagents/graph/propagation.py
    - tradingagents/graph/trading_graph.py
    - tradingagents/agents/analysts/social_media_analyst.py
    - tradingagents/agents/analysts/news_analyst.py
    - tradingagents/agents/analysts/fundamentals_analyst.py
    - tradingagents/llm_clients/google_client.py
decisions:
  - "Gemini retry tuned to 5x/5s base for faster transient error recovery"
  - "vol_note initialized to None before conditional to eliminate NameError risk"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-09"
  tasks: 3
  files: 6
---

# Quick Fix 260409-uqs: v2.0 Tech Debt and Gemini 503 Retry Summary

**One-liner:** Eliminated 5 latent v2.0 bugs — missing vol state fields, stale comment, analyst NameError risk, missing log fields — and improved Gemini 503 recovery from 3x15s to 5x5s retry schedule.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add vol fields to propagation.py initial state; fix stale comment | 4fac614 |
| 2 | Add vol fields to _log_state; guard vol_note NameError in 3 analysts | c94dc76 |
| 3 | Tune Gemini retry: _MAX_RETRIES=5, _BASE_DELAY=5 | e42ea60 |

## Changes Made

### Task 1 — propagation.py
- Added 6 vol-pipeline fields to `create_initial_state()` return dict: `vol_context=None`, `vol_note_market/technical/social/news/fundamentals=None`
- Updated stale comment from "populated only when enable_options=True" to "always active (enable_options toggle removed)"

### Task 2 — trading_graph.py + 3 analyst files
- `_log_state` dict now includes `vol_context` and all five `vol_note_*` fields via `.get()` safe access
- `social_media_analyst.py`, `news_analyst.py`, `fundamentals_analyst.py`: added `vol_note = None` guard before the `if len(result.tool_calls) == 0:` conditional, and removed the redundant `else None` ternary pattern

### Task 3 — google_client.py
- `_MAX_RETRIES`: 3 → 5
- `_BASE_DELAY`: 15s → 5s
- New retry schedule: 5s / 10s / 20s / 40s / 80s (total ~155s max before fallback vs old 105s with only 3 attempts)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All 6 files verified present and correctly modified. All 3 commits verified in git log.
