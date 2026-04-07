# Phase 1: Add analysis progress visibility and cancellation support - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds two capabilities: (1) a global progress indicator visible across all tabs showing which agents are done during analysis, and (2) the ability to cancel a running analysis from anywhere in the app, with backend support for graceful graph execution termination.

</domain>

<decisions>
## Implementation Decisions

### Progress Visibility
- Add a global status bar at the top of the app (below the tab nav) showing "Analyzing {TICKER}... {N}/{total} agents done" — visible on all tabs, not just Analysis
- No elapsed time per agent — current done/running/pending states are sufficient
- Keep auto-navigation to Chart on completion but ensure user can navigate back to see full results
- Show summary count (e.g., "8/17 agents complete") in the global status bar for at-a-glance progress

### Cancellation UX
- Cancel button appears in the global status bar next to progress text — an X or "Cancel" button always accessible from any tab
- Single click cancels immediately — no confirmation modal; analysis can be re-started cheaply
- Discard all partial results after cancel — reset to idle state; partial agent reports are incomplete and misleading
- Status bar shows "Cancelling..." briefly then returns to idle — clear state transition

### Backend Cancellation
- Use a `threading.Event` flag passed to the callback handler; check it between nodes; raise exception to abort graph execution
- API endpoint: `DELETE /api/analyze/{run_id}` — RESTful design, sets the cancel flag and returns 204
- Let in-flight LLM calls finish, then abort before next node — safe, avoids mid-call interruption (LLM calls are 5-30s)
- Send `{"type": "cancelled"}` SSE event — frontend knows cancellation was intentional, distinct from error

### Claude's Discretion
- Exact styling/positioning of the global status bar
- Animation choices for the cancelling state
- Whether the status bar auto-hides after idle timeout

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ProgressStepper.tsx` — already renders done/running/pending per agent with green checkmark/blue pulse/gray dot; can extract node counting logic
- `useAnalysis.ts` — useReducer pattern with `completedNodes[]`, `currentNode`, `status`; needs new CANCEL and CANCELLED action types
- `ProgressCallbackHandler` in `api/progress.py` — LangChain callback handler; needs cancel flag checking between nodes
- `_run_queues` dict in `api/progress.py` — can store cancel Event alongside queue

### Established Patterns
- SSE streaming via `sse_starlette.EventSourceResponse` with typed events (node_start, node_end, complete, error)
- Thread-safe event queue: sync LangGraph thread → `asyncio.run_coroutine_threadsafe` → async queue → SSE stream
- `esRef` pattern in useAnalysis for managing EventSource lifecycle
- `isRunningRef` pattern for avoiding stale closures in callbacks

### Integration Points
- `api/routes.py` — add DELETE endpoint for cancel; modify `run_graph()` to accept cancel Event
- `api/progress.py` — extend `register_run()` to also create a cancel Event; add `cancel_run()` function; modify `ProgressCallbackHandler` to check cancel flag
- `frontend/src/App.tsx` — add global status bar component between tab nav and content area
- `frontend/src/hooks/useAnalysis.ts` — add `cancelAnalysis()` function that calls DELETE and dispatches CANCELLED; add run_id tracking
- `frontend/src/types.ts` — add 'cancelled' to AnalysisStatus union; add CANCELLED action type

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
