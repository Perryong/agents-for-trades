---
phase: 05-graph-integration
plan: 02
subsystem: testing
tags: [langgraph, pytest, mocking, integration-tests, options]

# Dependency graph
requires:
  - phase: 05-01
    provides: "Options branch wired into StateGraph with _safe_options_node wrapper and all 7 OPTIONS_NODES"
provides:
  - "End-to-end smoke tests verifying options-enabled graph populates all 6 state fields"
  - "Equity-only smoke test confirming options fields stay empty when enable_options=False"
  - "Graceful degradation smoke test confirming graph completes and returns empty field when one agent fails"
affects: [06-debator-risk-manager-updates]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_make_proper_mock_llm: AIMessage-based mock with bind_tools returning self for equity agent tool-call loop"
    - "_make_smoke_graph: direct GraphSetup instantiation with single 'market' analyst for minimal graph overhead"
    - "Patching OPTIONS_NODES with __name__-set factory for graceful degradation testing"

key-files:
  created: []
  modified:
    - tests/graph/test_graph_integration.py

key-decisions:
  - "Mock LLM must use AIMessage(content='mock report', tool_calls=[]) so conditional_logic routes to Msg Clear (not tools)"
  - "bind_tools.return_value = mock_llm so bound chain .invoke() returns AIMessage, not a nested MagicMock"
  - "OPTIONS_NODES patched with failing_flow_factory.__name__ = 'create_options_flow_analyst' to satisfy _OPTIONS_STATE_KEYS lookup"
  - "Module-level patches (tradingagents.agents.options.volatility_analyst.route_to_vendor) required because dataflows.interface.route_to_vendor patch does not reach imported symbols in options modules"

patterns-established:
  - "Options data patches: patch at module level (agents.options.X.route_to_vendor) in addition to dataflows.interface.route_to_vendor"
  - "Graceful degradation test: patch OPTIONS_NODES list directly with __name__-aliased factory, not create_options_flow_analyst in setup module"

requirements-completed: [GRAPH-01, GRAPH-03, GRAPH-04]

# Metrics
duration: 2min
completed: 2026-04-01
---

# Phase 5 Plan 2: Graph Integration Smoke Tests Summary

**Three end-to-end smoke tests validating options-enabled, equity-only, and graceful degradation graph execution using AIMessage mocks and OPTIONS_NODES patching**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-01T13:02:08Z
- **Completed:** 2026-04-01T13:04:29Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `test_full_graph_options_enabled_populates_all_fields`: confirms all 6 options state fields are non-empty after full graph run with `enable_options=True`
- Added `test_full_graph_equity_only_no_options_content`: confirms options fields remain empty strings when `enable_options=False`
- Added `test_options_branch_failure_graceful_degradation`: confirms graph completes and failed agent's field is `""` while upstream agent and equity pipeline succeed
- Added helper functions `_make_proper_mock_llm`, `_make_smoke_graph`, `_make_options_data_patches` for reusable smoke test setup
- Full test suite: 149 tests pass (8 graph integration tests, no regressions)

## Task Commits

1. **Task 1: Add end-to-end integration smoke tests** - `e813661` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `tests/graph/test_graph_integration.py` - Extended with 3 smoke tests + helper infrastructure (267 lines added, 524 total)

## Decisions Made

- Used `AIMessage(content="mock report", tool_calls=[])` for the mock LLM response — LangGraph's `conditional_logic.should_continue_market` checks `last_message.tool_calls`; an empty list routes to `Msg Clear` instead of the tool node, preventing infinite loops
- Set `bind_tools.return_value = mock_llm` so the RunnableSequence `prompt | mock_llm.bind_tools(tools)` resolves to the configured mock when `.invoke()` is called
- Patched `tradingagents.agents.options.volatility_analyst.route_to_vendor` and `tradingagents.agents.options.options_flow_analyst.route_to_vendor` at module level — the dataflows-level patch alone does not reach symbols already bound via `from tradingagents.dataflows.interface import route_to_vendor` at import time
- Set `failing_flow_factory.__name__ = "create_options_flow_analyst"` before injecting into `OPTIONS_NODES` — setup.py looks up `_OPTIONS_STATE_KEYS[factory_fn.__name__]` to find the state key for the `_safe_options_node` wrapper

## Deviations from Plan

None - plan executed exactly as written. Tests went GREEN immediately because Plan 01 already implemented the graph wiring (expected outcome for integration smoke tests against completed implementation).

## Issues Encountered

- **MagicMock bind_tools returns nested mock** — initial mock LLM using plain `MagicMock()` returned a new MagicMock from `bind_tools()`, so `.invoke()` returned a MagicMock instead of AIMessage, causing `NotImplementedError: Unsupported message type` in LangGraph's message coercion. Fixed by using `AIMessage` and setting `bind_tools.return_value = mock_llm`.
- **OPTIONS_NODES patch requires __name__ match** — patching `create_options_flow_analyst` in setup module does not affect the already-bound list. Patching `OPTIONS_NODES` directly requires the factory's `__name__` to match `_OPTIONS_STATE_KEYS` keys.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All graph integration tests pass (8/8)
- Options-enabled, equity-only, and graceful degradation behavior verified end-to-end
- Ready for Phase 06: Debator & Risk Manager updates

## Self-Check: PASSED

- tests/graph/test_graph_integration.py: FOUND
- .planning/phases/05-graph-integration/05-02-SUMMARY.md: FOUND
- commit e813661: FOUND

---
*Phase: 05-graph-integration*
*Completed: 2026-04-01*
