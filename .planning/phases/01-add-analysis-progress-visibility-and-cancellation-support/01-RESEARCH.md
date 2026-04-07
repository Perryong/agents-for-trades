# Phase 01: Add Analysis Progress Visibility and Cancellation Support - Research

**Researched:** 2026-04-07
**Domain:** FastAPI SSE streaming + React useReducer + threading.Event cancellation
**Confidence:** HIGH

## Summary

This phase adds two capabilities to the existing TradingAgents app: a global progress status bar visible across all tabs, and a cancellation mechanism that works from any tab. The backend already has all the infrastructure needed — `ProgressCallbackHandler`, `_run_queues`, `asyncio.Queue`, and SSE via `sse_starlette`. The frontend has `useAnalysis` (useReducer), `ProgressStepper`, and the tab navigation layout in `App.tsx`. No new libraries are required.

The core backend work is: extend `_run_queues` to also hold a `threading.Event` per run, make `ProgressCallbackHandler` check that event between LangChain callbacks, and add a `DELETE /api/analyze/{run_id}` endpoint that sets the event. The core frontend work is: add a `cancelAnalysis()` function to `useAnalysis`, a `CANCEL` / `CANCELLED` action type to the reducer, run_id tracking in the hook, and a `GlobalStatusBar` component rendered between the tab nav and content area in `App.tsx`.

**Primary recommendation:** Extend existing modules in-place — do not create new abstraction layers. The _run_queues dict, ProgressCallbackHandler, and useAnalysis hook are the three mutation sites; everything else is additive.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Progress Visibility**
- Add a global status bar at the top of the app (below the tab nav) showing "Analyzing {TICKER}... {N}/{total} agents done" — visible on all tabs, not just Analysis
- No elapsed time per agent — current done/running/pending states are sufficient
- Keep auto-navigation to Chart on completion but ensure user can navigate back to see full results
- Show summary count (e.g., "8/17 agents complete") in the global status bar for at-a-glance progress

**Cancellation UX**
- Cancel button appears in the global status bar next to progress text — an X or "Cancel" button always accessible from any tab
- Single click cancels immediately — no confirmation modal; analysis can be re-started cheaply
- Discard all partial results after cancel — reset to idle state; partial agent reports are incomplete and misleading
- Status bar shows "Cancelling..." briefly then returns to idle — clear state transition

**Backend Cancellation**
- Use a `threading.Event` flag passed to the callback handler; check it between nodes; raise exception to abort graph execution
- API endpoint: `DELETE /api/analyze/{run_id}` — RESTful design, sets the cancel flag and returns 204
- Let in-flight LLM calls finish, then abort before next node — safe, avoids mid-call interruption (LLM calls are 5-30s)
- Send `{"type": "cancelled"}` SSE event — frontend knows cancellation was intentional, distinct from error

### Claude's Discretion
- Exact styling/positioning of the global status bar
- Animation choices for the cancelling state
- Whether the status bar auto-hides after idle timeout

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | present | REST endpoint + SSE | Already used for all routes |
| sse_starlette | present | `EventSourceResponse` | Established pattern in routes.py |
| threading.Event | stdlib | Cancellation flag across threads | Safe for sync→async boundary; no extra deps |
| React 19 | present | UI | Already used |
| Tailwind CSS 4 | present | Styling | Already used |

### No new dependencies required

All needed capabilities exist in the current stack. `threading.Event` is stdlib. The SSE pattern is already shipping.

**Installation:** None needed.

**Version verification:** Not applicable — no new packages.

---

## Architecture Patterns

### Recommended Project Structure (changes only)

```
api/
├── progress.py          # extend: add cancel_event per run, cancel_run(), AnalysisCancelledError
├── routes.py            # extend: add DELETE /api/analyze/{run_id}; pass cancel_event to run_graph()
frontend/src/
├── types.ts             # extend: add 'cancelling' | 'cancelled' to AnalysisStatus; CANCEL/CANCELLED actions
├── hooks/useAnalysis.ts # extend: add runIdRef, cancelAnalysis(), CANCEL/CANCELLED dispatch
├── components/
│   └── GlobalStatusBar.tsx  # new: status bar component
└── App.tsx              # extend: render GlobalStatusBar between tab nav and content area
```

### Pattern 1: threading.Event Cancellation Flag

**What:** `register_run()` creates both an `asyncio.Queue` and a `threading.Event`. The `ProgressCallbackHandler` holds a reference to the event and checks `event.is_set()` at the start of each `on_chain_start` callback. When set, it raises a custom `AnalysisCancelledError` which propagates up through LangGraph, exits `asyncio.to_thread`, and is caught in the `run_graph()` try/except to emit the `{"type": "cancelled"}` SSE event.

**When to use:** Any scenario where a sync thread must be aborted from an async context.

**Example:**

```python
# api/progress.py

class AnalysisCancelledError(Exception):
    """Raised inside the LangGraph thread when the cancel event is set."""
    pass

# _run_queues value is now a tuple: (asyncio.Queue, threading.Event)
_run_queues: Dict[str, tuple[asyncio.Queue, threading.Event]] = {}

def register_run(run_id: str) -> tuple[asyncio.Queue, threading.Event]:
    q: asyncio.Queue = asyncio.Queue()
    cancel_event = threading.Event()
    _run_queues[run_id] = (q, cancel_event)
    return q, cancel_event

def get_queue(run_id: str) -> Optional[asyncio.Queue]:
    entry = _run_queues.get(run_id)
    return entry[0] if entry else None

def get_cancel_event(run_id: str) -> Optional[threading.Event]:
    entry = _run_queues.get(run_id)
    return entry[1] if entry else None

def cancel_run(run_id: str) -> bool:
    """Set the cancel flag. Returns True if the run was found."""
    event = get_cancel_event(run_id)
    if event:
        event.set()
        return True
    return False

def remove_run(run_id: str) -> None:
    _run_queues.pop(run_id, None)


class ProgressCallbackHandler(BaseCallbackHandler):
    def __init__(self, run_id: str, loop: asyncio.AbstractEventLoop,
                 cancel_event: threading.Event) -> None:
        super().__init__()
        self.run_id = run_id
        self.loop = loop
        self.cancel_event = cancel_event
        self._lock = threading.Lock()

    def _check_cancel(self) -> None:
        if self.cancel_event.is_set():
            raise AnalysisCancelledError("Analysis cancelled by user")

    def on_chain_start(self, serialized, inputs, **kwargs) -> None:
        self._check_cancel()  # check BEFORE emitting start event
        name = kwargs.get("name") or serialized.get("name", "unknown")
        self._put({"type": "node_start", "node": name})

    def on_chain_end(self, outputs, **kwargs) -> None:
        self._check_cancel()  # check AFTER node ends, BEFORE next node
        name = kwargs.get("name", "unknown")
        self._put({"type": "node_end", "node": name})
    # on_llm_start / on_llm_end: do NOT check — let in-flight LLM calls finish
```

### Pattern 2: DELETE Endpoint in FastAPI

**What:** A DELETE route that calls `cancel_run()` and returns 204. Must handle the case where run_id is unknown (run already finished or never existed) with 404.

**Example:**

```python
# api/routes.py

from fastapi import HTTPException
from .progress import cancel_run

@router.delete("/analyze/{run_id}", status_code=204)
async def cancel_analysis(run_id: str):
    """Cancel a running analysis by setting its cancel flag.
    Returns 204 if cancelled, 404 if run_id not found.
    """
    found = cancel_run(run_id)
    if not found:
        raise HTTPException(status_code=404, detail="Run not found or already complete")
```

### Pattern 3: run_graph() catches AnalysisCancelledError

**What:** The existing `try/except Exception as e` in `run_graph()` must distinguish `AnalysisCancelledError` from real errors to emit the correct SSE event type.

**Example:**

```python
# api/routes.py — inside start_analysis()

async def run_graph():
    try:
        # ... existing ta.propagate call ...
        await q.put({"type": "complete", "state": serialized, "signal": signal})
    except AnalysisCancelledError:
        await q.put({"type": "cancelled"})
    except Exception as e:
        await q.put({"type": "error", "message": str(e)})
    finally:
        await q.put(None)  # sentinel unchanged
```

### Pattern 4: Frontend useAnalysis — cancelAnalysis + runIdRef

**What:** The hook must track the current `run_id` in a ref (so `cancelAnalysis()` can read it without stale closure), expose `cancelAnalysis()` that calls `DELETE /api/analyze/{run_id}`, dispatches `CANCEL` immediately for optimistic UI, then transitions to `CANCELLED`/`RESET` when the SSE `cancelled` event arrives.

**Example:**

```typescript
// frontend/src/hooks/useAnalysis.ts

// New status values
type AnalysisStatus = 'idle' | 'running' | 'cancelling' | 'done' | 'error';

// New actions
type Action =
  | { type: 'RESET' }
  | { type: 'STARTED' }
  | { type: 'NODE_START'; node: string }
  | { type: 'NODE_END'; node: string }
  | { type: 'COMPLETE'; result: AnalysisResult }
  | { type: 'ERROR'; message: string }
  | { type: 'CANCEL' }     // optimistic: set status='cancelling'
  | { type: 'CANCELLED' }; // confirmed: reset to idle

// New ref
const runIdRef = useRef<string | null>(null);

const cancelAnalysis = useCallback(async () => {
  const runId = runIdRef.current;
  if (!runId) return;
  dispatch({ type: 'CANCEL' }); // immediate UI feedback
  try {
    await fetch(`/api/analyze/${runId}`, { method: 'DELETE' });
  } catch {
    // Best-effort; SSE cancelled event will confirm
  }
}, []);

// In startAnalysis — store runId:
runIdRef.current = runId;

// In SSE event listener — handle cancelled:
es.addEventListener('cancelled', () => {
  isRunningRef.current = false;
  runIdRef.current = null;
  dispatch({ type: 'CANCELLED' });
  es.close();
});

// Reducer additions:
case 'CANCEL':
  return { ...state, status: 'cancelling' };
case 'CANCELLED':
  return initialState; // full reset to idle
```

### Pattern 5: GlobalStatusBar Component

**What:** A thin banner rendered between the tab nav and the content area in `App.tsx`. Visible on all tabs when `status === 'running' | 'cancelling'`. Auto-hides when idle/done/error (or optionally fades after a delay — Claude's discretion).

**Key data needed from App.tsx:** `state.status`, `state.completedNodes.length`, total node count (computed from `enableOptions`), current ticker (`lastAnalyzedTicker.current`), and `cancelAnalysis()`.

**Example:**

```tsx
// frontend/src/components/GlobalStatusBar.tsx

interface GlobalStatusBarProps {
  status: AnalysisStatus;
  completedCount: number;
  totalCount: number;
  ticker: string;
  onCancel: () => void;
}

export function GlobalStatusBar({ status, completedCount, totalCount, ticker, onCancel }: GlobalStatusBarProps) {
  if (status !== 'running' && status !== 'cancelling') return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-blue-50 dark:bg-blue-900/30 border-b border-blue-200 dark:border-blue-800 text-sm">
      <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse flex-shrink-0" />
      <span className="text-blue-700 dark:text-blue-300 flex-1">
        {status === 'cancelling'
          ? 'Cancelling...'
          : `Analyzing ${ticker}... ${completedCount}/${totalCount} agents done`}
      </span>
      {status === 'running' && (
        <button
          onClick={onCancel}
          aria-label="Cancel analysis"
          className="text-blue-600 dark:text-blue-400 hover:text-red-600 dark:hover:text-red-400 font-medium transition-colors"
        >
          Cancel
        </button>
      )}
    </div>
  );
}
```

**Integration in App.tsx** — placed between the tab nav `<div>` and the `mainSection === 'analysis' ?` conditional:

```tsx
// App.tsx — expose cancelAnalysis from useAnalysis
const { state, startAnalysis, cancelAnalysis } = useAnalysis();

// Compute total for status bar
const totalNodes = getNodeList(enableOptions).length; // import getNodeList or inline computation

// Render (between tab nav and content):
<GlobalStatusBar
  status={state.status}
  completedCount={state.completedNodes.length}
  totalCount={totalNodes}
  ticker={lastAnalyzedTicker.current}
  onCancel={cancelAnalysis}
/>
```

Note: `getNodeList` already exists in `ProgressStepper.tsx` — export it or duplicate the single-line computation in App.tsx to avoid coupling.

### Anti-Patterns to Avoid

- **Checking cancel_event inside on_llm_start/on_llm_end:** The user decision is to let in-flight LLM calls finish. Only check at `on_chain_start` and `on_chain_end` (between nodes).
- **Dispatching CANCELLED from the DELETE response:** The DELETE is fire-and-forget (best-effort). Wait for the SSE `cancelled` event to confirm before resetting state.
- **Passing state.status as a dep to cancelAnalysis useCallback:** Would recreate the function on each status change. Use `runIdRef` to avoid the stale closure.
- **Returning partial results on cancel:** The decision is to discard — `CANCELLED` dispatches `initialState`, not a partial result.
- **Showing cancel button during 'cancelling' status:** Once cancelling begins, the button should disappear (or be disabled) to prevent double-dispatch.
- **Setting _run_queues value to just a Queue:** After this change it becomes a tuple. All callers of `get_queue` and `register_run` must be updated to destructure correctly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe cancellation signal | Custom shared state / sentinel in Queue | `threading.Event` | stdlib; is_set() is atomic; designed for this pattern |
| SSE event typing | New SSE library | Existing `EventSourceResponse` + named event types | Already shipping; just add 'cancelled' event type |
| Global state for progress | Redux / Zustand / Context API | Lift state from useAnalysis into App.tsx props | State is already in App.tsx via `const { state } = useAnalysis()`; only add props to GlobalStatusBar |

**Key insight:** The existing architecture already solved the hard problems (async/sync bridge, SSE streaming, useReducer state). This phase is pure extension — new event type, new action type, new endpoint, new component.

---

## Common Pitfalls

### Pitfall 1: AnalysisCancelledError Silently Swallowed by LangGraph

**What goes wrong:** LangGraph's internal exception handling may catch the exception before it exits `asyncio.to_thread`, logging it as a graph error rather than propagating it up.

**Why it happens:** LangGraph wraps node execution in try/except internally in some versions. The exception raised inside a LangChain callback may be treated as a non-fatal callback error.

**How to avoid:** Test the cancellation path explicitly. If `AnalysisCancelledError` is swallowed, alternative: check `cancel_event` inside the `run_graph()` coroutine itself using a polling approach — wrap `asyncio.to_thread` with a concurrent cancel watcher. But the callback approach is preferred (CONTEXT.md decision). If the callback raise doesn't propagate, document and escalate.

**Warning signs:** Cancel button produces "Cancelling..." state that never resolves, and the `cancelled` SSE event never arrives.

### Pitfall 2: Stale run_id in cancelAnalysis

**What goes wrong:** If `runIdRef` isn't updated before the SSE connection opens, `cancelAnalysis` reads `null` and the DELETE goes nowhere.

**Why it happens:** The runId is generated in `startAnalysis`. It must be stored in `runIdRef.current = runId` before the `EventSource` is created, not after.

**How to avoid:** Assign `runIdRef.current = runId` immediately after generation, before any async operations.

**Warning signs:** DELETE request is never sent; network tab shows no DELETE call.

### Pitfall 3: SSE 'cancelled' Event Not Reaching Frontend

**What goes wrong:** The SSE stream closes before the `cancelled` event is yielded, so the frontend stays stuck in 'cancelling'.

**Why it happens:** The `finally: await q.put(None)` sentinel triggers `remove_run()` in `event_generator`. If `cancelled` and `None` are put into the queue synchronously, the generator may process `None` (sentinel) and return before yielding the `cancelled` event.

**How to avoid:** The order `await q.put({"type": "cancelled"})` followed by `await q.put(None)` is correct — queue preserves FIFO order. The generator yields the cancelled event, then hits None and breaks. Confirm this ordering in `run_graph()`.

**Warning signs:** Frontend stays in 'cancelling' permanently. Network tab shows SSE stream closed but 'cancelled' event not present in stream.

### Pitfall 4: register_run() Return Value Breaking Existing Callers

**What goes wrong:** `register_run()` currently returns a single `asyncio.Queue`. Changing it to return a tuple breaks `start_analysis` which currently does `q = register_run(run_id)`.

**Why it happens:** Signature change without updating all callers.

**How to avoid:** Update `start_analysis` to `q, cancel_event = register_run(run_id)` at the same time as the signature change. There is only one caller (`routes.py:start_analysis`).

**Warning signs:** `TypeError: cannot unpack non-iterable Queue object` at startup of first analysis.

### Pitfall 5: GlobalStatusBar Total Count Mismatch

**What goes wrong:** The status bar shows "8/15 agents done" when options are enabled but ProgressStepper shows 22 total agents — the two counts disagree.

**Why it happens:** The total node count depends on `enableOptions`. Both must use the same `getNodeList(enableOptions)` computation.

**How to avoid:** Export `getNodeList` from `types.ts` or `ProgressStepper.tsx` and use it as the single source of truth. In App.tsx, compute `totalNodes = getNodeList(enableOptions).length`.

**Warning signs:** The count in the status bar doesn't match the number of items in the Analysis tab's ProgressStepper.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no config file — uses default discovery) |
| Config file | none (pytest defaults) |
| Quick run command | `pytest tests/graph/test_progress_cancel.py -x` |
| Full suite command | `pytest tests/ -x --ignore=tests/dataflows` |

Note: Frontend has no test framework configured (no vitest/jest config in `frontend/package.json`). Frontend validation is manual smoke-test only.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| PROG-01 | `register_run()` creates queue + cancel_event tuple | unit | `pytest tests/graph/test_progress_cancel.py::test_register_run_returns_tuple -x` | Wave 0 |
| PROG-02 | `cancel_run()` sets the cancel event and returns True | unit | `pytest tests/graph/test_progress_cancel.py::test_cancel_run_sets_event -x` | Wave 0 |
| PROG-03 | `cancel_run()` returns False for unknown run_id | unit | `pytest tests/graph/test_progress_cancel.py::test_cancel_run_unknown -x` | Wave 0 |
| PROG-04 | `ProgressCallbackHandler.on_chain_start` raises `AnalysisCancelledError` when event is set | unit | `pytest tests/graph/test_progress_cancel.py::test_handler_raises_on_cancel -x` | Wave 0 |
| PROG-05 | `DELETE /api/analyze/{run_id}` returns 204 when run exists | integration | `pytest tests/graph/test_progress_cancel.py::test_delete_endpoint_204 -x` | Wave 0 |
| PROG-06 | `DELETE /api/analyze/{unknown_id}` returns 404 | integration | `pytest tests/graph/test_progress_cancel.py::test_delete_endpoint_404 -x` | Wave 0 |
| PROG-07 | Global status bar renders with correct text format | manual smoke | N/A — no frontend test framework | manual |
| PROG-08 | Cancel button hidden during 'cancelling' state | manual smoke | N/A | manual |

### Sampling Rate
- **Per task commit:** `pytest tests/graph/test_progress_cancel.py -x`
- **Per wave merge:** `pytest tests/ -x --ignore=tests/dataflows`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/graph/test_progress_cancel.py` — covers PROG-01 through PROG-06
- [ ] `tests/graph/__init__.py` — already exists (no gap)
- [ ] `tests/conftest.py` — already exists; add FastAPI TestClient fixture if needed for endpoint tests

*(Frontend: no test infrastructure to install — vitest not in devDependencies and was not requested)*

---

## Code Examples

### Verified Pattern: Check cancel in LangChain callback (confirmed from existing handler pattern)

```python
# Source: api/progress.py (existing on_chain_start pattern, extended)
def on_chain_start(self, serialized, inputs, **kwargs) -> None:
    self._check_cancel()  # new — raises AnalysisCancelledError if event.is_set()
    name = kwargs.get("name") or serialized.get("name", "unknown")
    self._put({"type": "node_start", "node": name})
```

### Verified Pattern: Existing SSE event stream with sentinel (confirmed from routes.py)

```python
# Source: api/routes.py — event_generator() existing pattern
while True:
    event = await asyncio.wait_for(q.get(), timeout=1800)
    if event is None:  # sentinel unchanged
        break
    yield {"data": json.dumps(event), "event": event["type"]}
```

Adding `cancelled` event works with zero changes to `event_generator` — the event dict `{"type": "cancelled"}` is yielded with `event="cancelled"` automatically via `event["type"]`.

### Verified Pattern: useReducer action extension (confirmed from useAnalysis.ts)

```typescript
// Source: frontend/src/hooks/useAnalysis.ts — existing reducer pattern
case 'CANCELLED':
  return initialState;  // same as RESET — discards all partial results
case 'CANCEL':
  return { ...state, status: 'cancelling' };
```

### Verified Pattern: Node count computation (confirmed from ProgressStepper.tsx)

```typescript
// Source: frontend/src/components/ProgressStepper.tsx — getNodeList
function getNodeList(enableOptions: boolean): string[] {
  return [
    ...EQUITY_NODES,
    ...(enableOptions ? OPTIONS_NODES : []),
    ...RESEARCH_NODES,
    ...TRADING_NODES,
    ...RISK_NODES,
  ];
}
// Equity: 5, Options: 7, Research: 3, Trading: 1, Risk: 4 = 15 or 22 total
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No cancellation | threading.Event checked at node boundaries | This phase | Safe abort without mid-LLM interruption |
| Progress only on Analysis tab | Global status bar across all tabs | This phase | User can navigate freely during analysis |
| run_queues stores Queue only | run_queues stores (Queue, Event) tuple | This phase | All callers of register_run must destructure |

---

## Open Questions

1. **Does LangGraph propagate exceptions raised inside LangChain callbacks?**
   - What we know: `ProgressCallbackHandler` is a `BaseCallbackHandler`; raising inside `on_chain_start` is the standard documented pattern for aborting.
   - What's unclear: The specific LangGraph version in this project may swallow callback exceptions rather than re-raise them through the graph execution.
   - Recommendation: Test this in Wave 0 with a minimal stub (mock graph that calls the handler). If swallowed, fall back to checking `cancel_event` in a wrapper around `ta.propagate` using `asyncio.to_thread` with a polling watcher task.

2. **Export getNodeList or duplicate in App.tsx?**
   - What we know: `getNodeList` is currently unexported, defined inside `ProgressStepper.tsx`.
   - What's unclear: Whether coupling App.tsx to ProgressStepper.tsx internals is preferable to a small duplication.
   - Recommendation: Move `getNodeList` to `types.ts` (alongside `EQUITY_NODES` etc.) and export it. It only depends on types-level constants already in that file.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `api/progress.py` — confirmed existing queue pattern, handler structure
- Direct code inspection: `api/routes.py` — confirmed `asyncio.create_task`, `run_graph()` structure, `EventSourceResponse`
- Direct code inspection: `frontend/src/hooks/useAnalysis.ts` — confirmed useReducer pattern, esRef, isRunningRef, runId generation
- Direct code inspection: `frontend/src/components/ProgressStepper.tsx` — confirmed getNodeList, node constants
- Direct code inspection: `frontend/src/types.ts` — confirmed AnalysisStatus union, node lists
- Direct code inspection: `frontend/src/App.tsx` — confirmed tab nav structure, state usage pattern
- Python `threading.Event` stdlib docs — `is_set()` is atomic, designed for cross-thread signaling

### Secondary (MEDIUM confidence)
- FastAPI router DELETE endpoint pattern — standard FastAPI convention, HTTPException 404

### Tertiary (LOW confidence)
- LangChain callback exception propagation through LangGraph — needs validation in Wave 0 (see Open Questions)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code confirmed by direct file inspection; no new libraries
- Architecture: HIGH — patterns confirmed by reading existing code; extension not replacement
- Pitfalls: MEDIUM — structural pitfalls confirmed; LangGraph exception propagation is LOW (needs test)

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable stack; FastAPI/React/LangChain APIs unlikely to break in 30 days)
