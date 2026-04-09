---
phase: 17-mandatory-options-vol-aware-analysts
plan: 02
subsystem: api
tags: [langgraph, options, vol-context, graph-wiring, sse, progress]

# Dependency graph
requires:
  - phase: 17-01
    provides: create_vol_context_node factory function in tradingagents/agents/pre_analysis/__init__.py
provides:
  - LangGraph graph wired with Vol Context node as first node before all equity analysts
  - START -> Vol Context -> fan-out to equity analysts (was START -> fan-out directly)
  - All 7 OPTIONS_NODES unconditionally registered in graph (no enable_options conditional)
  - "Vol Context" added to SSE _GRAPH_NODES set in api/progress.py
  - enable_options field removed from AnalyzeRequest; config_dict() always passes True
affects: [17-03-frontend-tab-restructure, any code reading AnalyzeRequest.enable_options]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unconditional options pipeline: no if/else toggle, always-on via D-06"
    - "Vol Context as graph entry gate: START -> single node -> fan-out pattern"

key-files:
  created: []
  modified:
    - tradingagents/graph/setup.py
    - api/progress.py
    - api/schemas.py

key-decisions:
  - "D-06 enforced: enable_options removed from AnalyzeRequest; hardcoded True in config_dict()"
  - "Fan-out source changed atomically: START no longer fans out to analysts directly; Vol Context is the new source"
  - "Comment referencing enable_options removed from setup.py to satisfy zero-reference criteria"

patterns-established:
  - "Atomic edge replacement: removing START conditional edge and adding Vol Context edge in single Edit to prevent dual-path bug (Pitfall 1)"
  - "Always-on options: OPTIONS_NODES registered unconditionally outside any if block"

requirements-completed: [VOL-02, OPT-02]

# Metrics
duration: 15min
completed: 2026-04-09
---

# Phase 17 Plan 02: Graph Wiring — Vol Context Node and Always-On Options Summary

**Vol Context node wired as START gate before all equity analysts; OPTIONS_NODES always registered; enable_options toggle fully removed from backend**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-09T12:35:00Z
- **Completed:** 2026-04-09T12:50:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Changed graph flow from START -> [fan-out to analysts] to START -> Vol Context -> [fan-out to analysts], ensuring vol_context is populated before any analyst runs
- Made all 7 OPTIONS_NODES unconditionally registered in the graph (removed if/else enable_options block)
- Removed enable_options field from AnalyzeRequest schema and hardcoded True in config_dict()
- Added "Vol Context" to SSE progress handler _GRAPH_NODES set so it appears in real-time progress stream

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire Vol Context node and make options unconditional** - `dabf93e` (feat)
2. **Task 2: Add Vol Context to SSE nodes, remove enable_options field** - `e8ebf1a` (feat)

## Files Created/Modified
- `tradingagents/graph/setup.py` - Added create_vol_context_node import; registered Vol Context node; changed START -> Vol Context -> fan-out; unconditional OPTIONS_NODES; removed get_config/enable_options entirely
- `api/progress.py` - Added "Vol Context" as first entry in _GRAPH_NODES set
- `api/schemas.py` - Removed enable_options field from AnalyzeRequest; config_dict() hardcodes cfg["enable_options"] = True

## Decisions Made
- The comment `# Options pipeline — always registered (no enable_options conditional)` was updated to not include "enable_options" as a word, satisfying the zero-reference acceptance criteria while still documenting intent via `(D-06)`
- Atomic replacement of START conditional edge (as required by Pitfall 1 from PITFALLS.md): both the new `add_edge(START, "Vol Context")` and the new `add_conditional_edges("Vol Context", ...)` were added while removing the old `add_conditional_edges(START, ...)` in a single edit

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all changes applied cleanly. Import verification passed immediately.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend graph wiring complete: Vol Context runs first, options always-on
- Remaining backend concern: analyst prompts need vol_context injection (plan 17-03 or later)
- Frontend still has enable_options references that plan 17-03 addresses (ConfigSidebar, types.ts, App.tsx)

---
*Phase: 17-mandatory-options-vol-aware-analysts*
*Completed: 2026-04-09*
