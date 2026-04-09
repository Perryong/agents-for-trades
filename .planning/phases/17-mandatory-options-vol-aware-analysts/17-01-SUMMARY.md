---
phase: 17-mandatory-options-vol-aware-analysts
plan: 01
subsystem: api
tags: [langgraph, agentstate, options, volatility, yfinance, pandas]

# Dependency graph
requires: []
provides:
  - AgentState vol_context field (Optional[str] with _last_value reducer)
  - AgentState vol_note_market, vol_note_technical, vol_note_social, vol_note_news, vol_note_fundamentals fields
  - tradingagents/agents/pre_analysis/ package
  - create_vol_context_node() factory function — computes IV rank, IV/HV ratio, P/C ratio, skew narrative
affects:
  - 17-02 (graph wiring — adds Vol Context node to StateGraph)
  - 17-03 (analyst prompt changes — inject vol_context into system prompts)
  - 18-frontend-vol-aware-ui (vol banner uses vol_context from state)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "create_*() factory pattern for LangGraph nodes — matches existing analyst factories"
    - "pre_analysis package for pre-analyst nodes (distinct from agents/analysts/)"
    - "_parse_chain_table strips # SPOT: metadata lines before pandas CSV parse"
    - "Full try/except wrapping in node closures for non-blocking fallback to None"

key-files:
  created:
    - tradingagents/agents/pre_analysis/__init__.py
    - tradingagents/agents/pre_analysis/vol_context.py
  modified:
    - tradingagents/agents/utils/agent_states.py

key-decisions:
  - "pre_analysis package placed under agents/ (parallel to analysts/) — keeps pre-analysis nodes co-located with agent code"
  - "HV approximation via stdev of IV series — avoids needing price history endpoint, uses available data"
  - "Strip # SPOT: metadata line from chain table before pd.read_csv — yfinance chain prepends this marker"

patterns-established:
  - "create_vol_context_node() factory: returns closure vol_context_node(state: dict) -> dict matching LangGraph node contract"
  - "Graceful degradation: all data fetches wrapped in try/except, returns {vol_context: None} on any failure"
  - "Five vol_note_* fields pre-declared in AgentState for per-analyst audit trail (written by downstream analyst nodes)"

requirements-completed: [VOL-01, VOL-03, VOL-04]

# Metrics
duration: 2min
completed: 2026-04-09
---

# Phase 17 Plan 01: Vol Context State Contract and Node Summary

**AgentState extended with 6 vol fields; create_vol_context_node() factory computes IV rank, IV/HV ratio, P/C ratio, and skew narrative from cached options data with full try/except fallback**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-09T12:29:19Z
- **Completed:** 2026-04-09T12:31:03Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Extended AgentState with `vol_context` and five `vol_note_*` fields, all `Optional[str]` with `_last_value` reducers
- Created `tradingagents/agents/pre_analysis/` package with `create_vol_context_node()` factory
- Node computes 5-metric narrative: IV rank (52-week percentile), IV/HV ratio, P/C ratio, skew direction, soft directive
- Full error fallback — returns `{"vol_context": None}` on empty expirations, missing data, or any exception
- No direct yfinance calls — exclusively uses `get_options_expirations`, `get_options_chain`, `get_historical_iv`
- Handles `# SPOT:` metadata line prepended by yfinance chain table (stripped before pandas parse)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend AgentState with vol_context and vol_note_* fields** - `874af54` (feat)
2. **Task 2: Implement Vol Context node module (pure Python, no LLM)** - `28d27b6` (feat)

## Files Created/Modified

- `tradingagents/agents/utils/agent_states.py` — 6 new Optional[str] fields added after `greeks_report`
- `tradingagents/agents/pre_analysis/__init__.py` — package init, exports `create_vol_context_node`
- `tradingagents/agents/pre_analysis/vol_context.py` — node factory with narrative builder and parsing helpers

## Decisions Made

- HV approximation uses `statistics.stdev()` of the historical IV series rather than a true realized-vol calculation — avoids needing a separate price history fetch, uses data already available from `get_historical_iv()`
- `_parse_chain_table()` explicitly strips lines starting with `#` before CSV parse — required because `get_options_chain()` prepends a `# SPOT:0.0000` metadata line that breaks `pd.read_csv(sep=r"\s+")`
- `pre_analysis/` placed under `agents/` (not `dataflows/`) — this is a node (graph actor), not a data layer function

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- AgentState state contract is finalized — downstream plans can safely reference `vol_context` and `vol_note_*` keys
- `create_vol_context_node()` is importable and tested — ready for graph wiring in Plan 17-02
- The node is non-blocking by design — graph wiring in Plan 17-02 can add it before the analyst fan-out without risk of pipeline failures

---
*Phase: 17-mandatory-options-vol-aware-analysts*
*Completed: 2026-04-09*
