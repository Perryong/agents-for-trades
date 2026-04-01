# Phase 7: Visual Frontend - Research

**Researched:** 2026-04-01
**Domain:** React + FastAPI + SSE + LangGraph callback hooks
**Confidence:** HIGH

## Summary

Phase 7 adds a web-based GUI over the existing `TradingAgentsGraph` pipeline. The architecture is a two-process dev setup (FastAPI on :8000 + Vite dev server on :5173 with proxy) that becomes a single-process production deploy (FastAPI serves the Vite `dist/` folder). The three hardest sub-problems are: (1) bridging the synchronous LangGraph `.invoke()` / `.stream()` call to async SSE, (2) designing an SSE event schema that maps to the UI stepper, and (3) serving the SPA's catch-all route from FastAPI without clobbering the `/api` routes.

The LangGraph graph already supports callbacks via `TradingAgentsGraph.__init__(callbacks=[...])`. The existing `StatsCallbackHandler` in `cli/stats_handler.py` is the pattern to follow — extend `BaseCallbackHandler` and hook `on_chain_start` / `on_chain_end` to emit node-name events into a thread-safe queue, then drain that queue in the SSE generator.

**Primary recommendation:** Use `sse-starlette` (3.3.4) for `EventSourceResponse`, run LangGraph in a background thread (`asyncio.to_thread`), communicate progress via `asyncio.Queue`, and implement the React frontend with native `EventSource` API plus `useReducer` state management.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Frontend: React + TypeScript built with Vite in a `frontend/` directory
- Backend: FastAPI thin wrapper around `TradingAgentsGraph` — `/api/analyze` endpoint
- Styling: Tailwind CSS — utility-first, no component library
- Deployment: Local-only (same machine) — matches CLI usage model
- State management: React state (useState/useReducer) — no external state library needed for single-user
- FastAPI backend: thin wrapper — `/api/analyze` accepts ticker/date/config JSON, runs `TradingAgentsGraph.propagate()`, returns final decision + all reports
- Real-time progress: Server-Sent Events (SSE) — `/api/analyze/{run_id}/stream` emits agent completion events as they happen
- Frontend in `frontend/` directory alongside existing Python code — separate npm project, proxied to FastAPI in dev
- No microservices — single FastAPI process handles everything
- Single-page app: config sidebar (left) + main content area (right) with tabbed report views + progress panel (top of main area)
- Config sidebar: ticker input, date picker, analyst checkboxes (market/technical/social/news/fundamentals), `enable_options` toggle, LLM provider/model selectors
- Report display: tabbed panels — Market, Technical, Social, News, Fundamentals, Options (when enabled), Debate History, Final Decision
- Agent progress: vertical stepper/timeline showing each agent node with status (pending → running → done)
- Options-specific UI: when `enable_options` toggle is on, additional tabs appear for Volatility Report, Flow Report, Strategy, Legs/Order, Pricing, Greeks
- "Analyze" button triggers the run; results persist in session until next run

### Claude's Discretion
- Exact FastAPI endpoint signatures and response schemas
- SSE event format and agent callback hook implementation
- React component structure and file organization within `frontend/`
- How to hook into LangGraph execution for progress events (callback handlers or state inspection)
- Error handling UI (loading states, API errors, LLM failures)
- Whether to add a simple run history panel (optional enhancement)

### Deferred Ideas (OUT OF SCOPE)
- Multi-user support / authentication — single-user local app for v1
- Run history / persistence — optional enhancement, not core
- Mobile responsive layout — desktop-first for v1
- Real-time chart/graph visualization of the StateGraph node execution
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.4 | UI component framework | Locked decision; current stable |
| TypeScript | ~5.x (Vite template) | Type safety | Locked decision |
| Vite | 8.0.3 | Dev server + bundler | Locked decision; current stable |
| @vitejs/plugin-react | ~5.x | React Fast Refresh + JSX | Official Vite React plugin |
| Tailwind CSS | 4.x | Utility-first CSS | Locked decision |
| @tailwindcss/vite | 4.x | Vite plugin for Tailwind v4 | Replaces PostCSS config in v4 |
| FastAPI | latest (0.115+) | HTTP API + SSE + static serving | Locked decision |
| sse-starlette | 3.3.4 | `EventSourceResponse` for FastAPI | Production-grade SSE; W3C compliant |
| uvicorn | latest | ASGI server | Standard FastAPI runtime |
| pydantic | v2 (bundled with FastAPI) | Request/response schemas | Already in FastAPI dependency tree |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | already in project | Load .env for API keys | Dev startup |
| httpx | latest | Async HTTP in tests | FastAPI async test client |
| pytest-asyncio | latest | Async test support | Testing async FastAPI routes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sse-starlette | Raw `StreamingResponse` with generator | sse-starlette handles keep-alive pings, disconnect detection, and correct headers automatically |
| native `EventSource` | `@microsoft/fetch-event-source` | fetch-event-source supports POST requests and custom headers; use only if GET-based SSE proves limiting |
| `useReducer` | Zustand / Redux | No external state library; reducer is sufficient for single-user local app |
| Tailwind v4 | Tailwind v3 | v4 drops `tailwind.config.js`; uses `@tailwindcss/vite` plugin; `@import "tailwindcss"` in CSS |

**Installation (Python):**
```bash
pip install fastapi sse-starlette uvicorn[standard] httpx pytest-asyncio
```

**Installation (Node):**
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install tailwindcss @tailwindcss/vite
```

## Architecture Patterns

### Recommended Project Structure
```
agents-for-trades/
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, CORS, static mount, SPA catch-all
│   ├── routes.py        # /api/analyze, /api/analyze/{run_id}/stream
│   ├── schemas.py       # Pydantic: AnalyzeRequest, AnalyzeResponse, ProgressEvent
│   └── progress.py      # ProgressCallbackHandler + run_id → Queue registry
├── frontend/
│   ├── index.html
│   ├── vite.config.ts   # proxy /api → :8000 in dev
│   ├── src/
│   │   ├── main.tsx
│   │   ├── index.css    # @import "tailwindcss"
│   │   ├── App.tsx      # root layout (sidebar + main)
│   │   ├── components/
│   │   │   ├── ConfigSidebar.tsx
│   │   │   ├── ProgressStepper.tsx
│   │   │   ├── ReportTabs.tsx
│   │   │   └── ReportPane.tsx
│   │   ├── hooks/
│   │   │   └── useAnalysis.ts   # useReducer + EventSource logic
│   │   └── types.ts             # ProgressEvent, AnalysisResult types
│   └── package.json
└── tradingagents/        # existing — unchanged
```

### Pattern 1: SSE Progress via asyncio.Queue + Background Thread

The LangGraph `graph.invoke()` / `graph.stream()` is synchronous. FastAPI is async. Bridge with `asyncio.to_thread` and a shared `asyncio.Queue`.

**What:** `ProgressCallbackHandler` extends `BaseCallbackHandler` and writes events to a queue. The FastAPI SSE generator drains the queue until a sentinel `None` is received.

**When to use:** Any time a sync blocking call must stream incremental results to an async HTTP response.

```python
# Source: cli/stats_handler.py pattern + asyncio queue pattern
# api/progress.py

import asyncio
import threading
from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler

_run_queues: Dict[str, asyncio.Queue] = {}

def register_run(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _run_queues[run_id] = q
    return q

def get_queue(run_id: str) -> asyncio.Queue | None:
    return _run_queues.get(run_id)

def remove_run(run_id: str) -> None:
    _run_queues.pop(run_id, None)


class ProgressCallbackHandler(BaseCallbackHandler):
    """Emits node start/end events into a run-specific asyncio.Queue."""

    def __init__(self, run_id: str, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self.run_id = run_id
        self.loop = loop

    def _put(self, event: dict) -> None:
        q = get_queue(self.run_id)
        if q:
            asyncio.run_coroutine_threadsafe(q.put(event), self.loop)

    def on_chain_start(self, serialized: Dict[str, Any],
                       inputs: Dict[str, Any], **kwargs) -> None:
        name = kwargs.get("name") or serialized.get("name", "unknown")
        self._put({"type": "node_start", "node": name})

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        name = kwargs.get("name", "unknown")
        self._put({"type": "node_end", "node": name})
```

### Pattern 2: FastAPI SSE Endpoint

```python
# Source: sse-starlette docs (version 3.3.4)
# api/routes.py

import asyncio, uuid, json
from fastapi import APIRouter
from sse_starlette import EventSourceResponse
from .schemas import AnalyzeRequest
from .progress import register_run, remove_run, ProgressCallbackHandler

router = APIRouter(prefix="/api")

@router.post("/analyze/{run_id}/stream")
async def analyze_stream(run_id: str, request: AnalyzeRequest):
    loop = asyncio.get_event_loop()
    q = register_run(run_id)
    handler = ProgressCallbackHandler(run_id, loop)

    async def run_graph():
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        config = request.config_dict()
        ta = TradingAgentsGraph(
            selected_analysts=request.analysts,
            config=config,
            callbacks=[handler],
        )
        # run_in_executor offloads blocking call to thread pool
        final_state, signal = await asyncio.to_thread(
            ta.propagate, request.ticker, request.date
        )
        await q.put({"type": "complete", "state": _serialize_state(final_state)})
        await q.put(None)  # sentinel

    asyncio.create_task(run_graph())

    async def event_generator():
        try:
            while True:
                event = await q.get()
                if event is None:
                    break
                yield {"data": json.dumps(event), "event": event["type"]}
        finally:
            remove_run(run_id)

    return EventSourceResponse(event_generator())
```

### Pattern 3: Vite Dev Proxy Configuration

```typescript
// Source: Vite official docs — server.proxy
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

### Pattern 4: FastAPI Serve SPA in Production

```python
# Source: FastAPI static files docs
# api/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Dev: allow Vite dev server origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes registered first (before static mount)
from .routes import router
app.include_router(router)

# Production: serve Vite dist — mount AFTER API routes
DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=f"{DIST_DIR}/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_catch_all(full_path: str):
        return FileResponse(f"{DIST_DIR}/index.html")
```

### Pattern 5: React useReducer + EventSource

```typescript
// frontend/src/hooks/useAnalysis.ts

import { useReducer, useRef } from 'react'
import type { AnalysisState, ProgressEvent } from '../types'

type Action =
  | { type: 'RESET' }
  | { type: 'NODE_START'; node: string }
  | { type: 'NODE_END'; node: string }
  | { type: 'COMPLETE'; result: AnalysisResult }
  | { type: 'ERROR'; message: string }

function reducer(state: AnalysisState, action: Action): AnalysisState {
  switch (action.type) {
    case 'RESET':     return initialState
    case 'NODE_START': return { ...state, currentNode: action.node }
    case 'NODE_END':   return {
      ...state,
      completedNodes: [...state.completedNodes, action.node]
    }
    case 'COMPLETE':   return { ...state, status: 'done', result: action.result }
    case 'ERROR':      return { ...state, status: 'error', errorMsg: action.message }
    default:           return state
  }
}

export function useAnalysis() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const esRef = useRef<EventSource | null>(null)

  function startAnalysis(runId: string, payload: AnalyzeRequest) {
    dispatch({ type: 'RESET' })
    // POST /api/analyze/{run_id}/stream via native EventSource (GET)
    // OR: use fetch to POST config, then open EventSource on stream URL
    const es = new EventSource(`/api/analyze/${runId}/stream?...`)
    esRef.current = es

    es.addEventListener('node_start', (e) =>
      dispatch({ type: 'NODE_START', node: JSON.parse(e.data).node }))
    es.addEventListener('node_end', (e) =>
      dispatch({ type: 'NODE_END', node: JSON.parse(e.data).node }))
    es.addEventListener('complete', (e) => {
      dispatch({ type: 'COMPLETE', result: JSON.parse(e.data).state })
      es.close()
    })
    es.onerror = () => dispatch({ type: 'ERROR', message: 'Stream error' })
  }

  return { state, startAnalysis }
}
```

**Note on POST vs GET for SSE:** Native `EventSource` only supports GET. Two options:
1. POST config to `/api/analyze` first → receive `run_id` → open EventSource GET on `/api/analyze/{run_id}/stream` (recommended, cleanest separation)
2. Use `@microsoft/fetch-event-source` to POST SSE (adds npm dependency)

Option 1 is recommended: aligns with the CONTEXT.md endpoint design and avoids npm dependency.

### Pattern 6: Tailwind v4 CSS Setup

```css
/* frontend/src/index.css */
@import "tailwindcss";
```

No `tailwind.config.js` needed in v4. The `@tailwindcss/vite` plugin handles content scanning automatically via the Vite plugin.

### Anti-Patterns to Avoid

- **Mounting StaticFiles at `/` before API routes:** FastAPI processes mounts in order — `/api` routes must be registered with `include_router` before any wildcard static mount. If you `app.mount("/", StaticFiles(...))` first, API routes never match.
- **Calling `asyncio.Queue()` from a non-async thread:** `asyncio.Queue` is not thread-safe. Use `asyncio.run_coroutine_threadsafe(q.put(event), loop)` from the callback thread, not `q.put_nowait()` directly.
- **Blocking the FastAPI event loop with `graph.invoke()`:** LangGraph's sync `invoke()` blocks. Always use `asyncio.to_thread()` or `loop.run_in_executor()`.
- **Tailwind v4 with PostCSS config:** v4 does not use `tailwind.config.js` or PostCSS directives (`@tailwind base`). Use `@import "tailwindcss"` only.
- **EventSource with POST body:** Native `EventSource` only supports GET. For POST config, use a two-step flow (POST → get run_id → GET stream) rather than encoding config in query params.
- **SSE endpoint without client disconnect detection:** `sse-starlette` handles this; raw `StreamingResponse` does not automatically detect disconnects, leaking queue consumers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE keep-alive, W3C compliance | Custom generator with manual ping timing | `sse-starlette` `EventSourceResponse` | Handles pings, disconnect, reconnect IDs, correct headers |
| Thread-safe async/sync queue bridge | `threading.Queue` + polling | `asyncio.run_coroutine_threadsafe(q.put(...), loop)` | Standard Python pattern for sync→async handoff |
| Tailwind config scaffolding | Manual `postcss.config.js` setup | `@tailwindcss/vite` plugin | v4's plugin replaces the entire PostCSS chain |
| Tab component | Custom CSS state machine | `useState` + conditional classes | Simple enough to write; no library needed per locked decision |
| Vertical stepper | Third-party component | `div` + Tailwind classes + `status` prop | Single-purpose, trivial to build with utility classes |
| SPA routing in FastAPI | Custom path parsing | Catch-all `/{full_path:path}` returning `index.html` | Standard SPA fallback pattern |

**Key insight:** All three complexity hotspots (SSE plumbing, sync→async bridge, SPA routing) have well-established single-function solutions. The phase complexity is in wiring them together correctly, not in any individual piece.

## Common Pitfalls

### Pitfall 1: Orphaned SSE Queues on Client Disconnect
**What goes wrong:** Client closes browser tab mid-run; the `asyncio.Queue` and LangGraph thread continue running, accumulating events nobody reads.
**Why it happens:** `EventSourceResponse` detects disconnect via `request.is_disconnected()` polling, but the generator must check this explicitly.
**How to avoid:** Use `sse-starlette`'s built-in disconnect detection. Also cancel the background `asyncio.Task` in the `finally` block of the generator.
**Warning signs:** Memory growing steadily during repeated runs; LangGraph processes not terminating.

### Pitfall 2: LangGraph Callback Name Resolution
**What goes wrong:** `on_chain_start` fires for every chain in the graph (LLM chains, tool chains, node wrappers) — not just the named agent nodes.
**Why it happens:** LangGraph wraps each node as a `RunnableSequence`; callbacks receive the Runnable's name, which may be the node name or an internal LangChain name.
**How to avoid:** Filter callback events by checking `kwargs.get("name")` or `serialized.get("name")`. Map known agent node names from the graph setup (e.g., `"Market Analyst"`, `"Options - Volatility Analyst"`) to UI-friendly labels. Use `stream_mode="values"` on the graph for cleaner state snapshots, or inspect `metadata["langgraph_node"]` when using `astream_events`.
**Warning signs:** Progress stepper fires dozens of events per agent step instead of one.

### Pitfall 3: Tailwind v4 vs v3 Setup Confusion
**What goes wrong:** Using v3 setup instructions (`tailwind.config.js`, `@tailwind base; @tailwind components; @tailwind utilities`) with v4 package — styles don't generate.
**Why it happens:** Tailwind v4 is a complete rewrite; the CSS-first config system replaces JS config and PostCSS directives.
**How to avoid:** v4 only needs `npm install tailwindcss @tailwindcss/vite`. Add `tailwindcss()` to Vite plugins. Use `@import "tailwindcss"` in CSS. No other config files needed.
**Warning signs:** CSS file exists but no Tailwind classes are applied; build produces empty stylesheet.

### Pitfall 4: FastAPI Static Mount Shadows API Routes
**What goes wrong:** `/api/analyze` returns `404` or serves `index.html` instead of JSON.
**Why it happens:** `app.mount("/", StaticFiles(...), name="spa")` matches every path — if mounted before `include_router(router)`, it intercepts API requests.
**How to avoid:** Always `include_router(router)` before `app.mount`. Mount static assets under `/assets` rather than `/` to reduce shadow risk. Use catch-all `@app.get("/{full_path:path}")` for the SPA fallback instead of a static mount at `/`.
**Warning signs:** All API routes return 404 in production; works in dev (Vite proxy bypasses the issue).

### Pitfall 5: CORS in Development vs Production
**What goes wrong:** Dev works (Vite proxy avoids CORS); production breaks because React app is served from same origin as FastAPI but CORS middleware is too restrictive or too permissive.
**Why it happens:** Vite dev server proxies `/api` calls — no CORS needed in dev. In production, same origin — no CORS needed either. CORS middleware only needed if frontend and backend are on different origins.
**How to avoid:** For local-only deploy, CORSMiddleware can be omitted in production. In dev, add `allow_origins=["http://localhost:5173"]`. Guard with `if os.getenv("ENV") == "development"`.

### Pitfall 6: `asyncio.Queue` Created in Wrong Thread
**What goes wrong:** `asyncio.Queue()` instantiated in a synchronous context (e.g., a request handler that's not `async def`) or in the LangGraph callback thread — queue becomes associated with the wrong event loop.
**Why it happens:** `asyncio.Queue` is bound to the running event loop at creation time in Python ≤ 3.9; in 3.10+ it's lazily bound, but thread-local access is still unsafe.
**How to avoid:** Create the queue inside the `async def` route handler (or in an async startup context). Pass the `loop` reference explicitly to the callback handler. Use `asyncio.run_coroutine_threadsafe(q.put(event), loop)` from the callback thread — never `q.put_nowait()`.

## Code Examples

### Pydantic Request/Response Schemas

```python
# Source: FastAPI + Pydantic v2 pattern
# api/schemas.py

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class AnalyzeRequest(BaseModel):
    ticker: str
    date: str           # "YYYY-MM-DD"
    analysts: List[str] = ["market", "technical", "social", "news", "fundamentals"]
    enable_options: bool = False
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-4o"
    quick_think_llm: str = "gpt-4o-mini"

    def config_dict(self) -> Dict[str, Any]:
        from tradingagents.default_config import DEFAULT_CONFIG
        cfg = dict(DEFAULT_CONFIG)
        cfg["enable_options"] = self.enable_options
        cfg["llm_provider"] = self.llm_provider
        cfg["deep_think_llm"] = self.deep_think_llm
        cfg["quick_think_llm"] = self.quick_think_llm
        return cfg

class AnalyzeResponse(BaseModel):
    run_id: str         # UUID; client uses this to open SSE stream

class ProgressEvent(BaseModel):
    type: str           # "node_start" | "node_end" | "complete" | "error"
    node: Optional[str] = None
    state: Optional[Dict[str, Any]] = None   # populated on "complete"
    message: Optional[str] = None            # populated on "error"
```

### SSE Event Schema (wire format)

```
event: node_start
data: {"type": "node_start", "node": "Market Analyst"}

event: node_end
data: {"type": "node_end", "node": "Market Analyst"}

event: complete
data: {"type": "complete", "state": {"final_trade_decision": "...", "market_report": "...", ...}}

event: error
data: {"type": "error", "message": "LLM rate limit exceeded"}
```

### Known Agent Node Names (for stepper mapping)

Based on `cli/main.py` `MessageBuffer.ANALYST_MAPPING` and `FIXED_AGENTS`, the UI stepper nodes are:
- Analyst phase: `Market Analyst`, `Technical Analyst`, `Social Analyst`, `News Analyst`, `Fundamentals Analyst`
- Options phase (if enabled): `Options - Volatility Analyst`, `Options - Flow Analyst`, `Options - Strategy Selector`, `Options - Strike/Expiry Selector`, `Options - Pricing Agent`, `Options - Legs Builder`, `Options - Greeks Monitor`
- Research phase: `Bull Researcher`, `Bear Researcher`, `Research Manager`
- Trading phase: `Trader`
- Risk phase: `Aggressive Analyst`, `Conservative Analyst`, `Neutral Analyst`, `Portfolio Manager`

### Vite Config with Proxy

```typescript
// Source: Vite official docs
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

### Vertical Stepper (Tailwind utility pattern)

```tsx
// No library needed — pure Tailwind
// frontend/src/components/ProgressStepper.tsx
type StepStatus = 'pending' | 'running' | 'done'

const statusClass: Record<StepStatus, string> = {
  pending: 'bg-gray-200 text-gray-400',
  running: 'bg-blue-500 text-white animate-pulse',
  done:    'bg-green-500 text-white',
}

function Step({ label, status }: { label: string; status: StepStatus }) {
  return (
    <div className="flex items-start gap-3">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${statusClass[status]}`}>
        {status === 'done' ? '✓' : status === 'running' ? '…' : '○'}
      </div>
      <span className="text-sm mt-1.5">{label}</span>
    </div>
  )
}
```

### Tab Component (Tailwind utility pattern)

```tsx
// Pure React + Tailwind — no external library
const tabs = ['Market', 'Technical', 'Social', 'News', 'Fundamentals', 'Final Decision']

function ReportTabs({ activeTab, onTabChange }: TabProps) {
  return (
    <div className="flex border-b border-gray-200 overflow-x-auto">
      {tabs.map(tab => (
        <button
          key={tab}
          onClick={() => onTabChange(tab)}
          className={`px-4 py-2 text-sm font-medium whitespace-nowrap ${
            activeTab === tab
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          {tab}
        </button>
      ))}
    </div>
  )
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind v3 PostCSS + `tailwind.config.js` | v4 Vite plugin + `@import "tailwindcss"` | Early 2025 (Tailwind v4) | No config file; `@tailwindcss/vite` replaces PostCSS chain entirely |
| React 18 `createRoot` | React 19 `createRoot` (same API) | Dec 2024 | React 19 adds Actions, use() hook; no breaking changes for this use case |
| Vite 5/6 | Vite 8.0.3 | March 2026 | Vite 8 requires Node 20+; API is backward-compatible |
| `@vitejs/plugin-react-swc` | `@vitejs/plugin-react` v5 (Oxc transform) | 2025 | Default plugin uses Oxc in v5+; both work; use default plugin |

**Deprecated/outdated:**
- PostCSS-based Tailwind setup: replaced by `@tailwindcss/vite` plugin in v4
- `@tailwind base/components/utilities` directives: replaced by `@import "tailwindcss"`
- React `render()` from `react-dom`: replaced by `createRoot` in React 18 (already standard)

## Open Questions

1. **LangGraph callback name granularity**
   - What we know: `on_chain_start` fires for every Runnable in the graph, not just agent nodes
   - What's unclear: Whether node names from the options branch (e.g., `"Options - Volatility Analyst"`) are emitted as `on_chain_start` kwargs or only in `astream_events` metadata
   - Recommendation: In Wave 1 of the plan, implement a minimal callback logger that prints all `on_chain_start` event names; use that output to build the exact filter list before building the stepper mapping

2. **Two-step POST + GET vs POST-only SSE**
   - What we know: Native `EventSource` only supports GET; CONTEXT.md describes `/api/analyze/{run_id}/stream`
   - What's unclear: Whether `run_id` should be client-generated (UUID) or server-assigned
   - Recommendation: Client generates UUID v4, POSTs config to `/api/analyze/{run_id}` (which starts background run), then opens `EventSource("/api/analyze/{run_id}/stream")` — this is simpler than server-assigned IDs

3. **Options tab visibility logic**
   - What we know: Options tabs appear when `enable_options` toggle is on
   - What's unclear: Should tabs be hidden before results arrive, or shown as "pending" with empty content
   - Recommendation: Show options tabs in pending state when `enable_options=true`; hide completely when `false`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already in use) |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `pytest tests/graph/ -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

Phase 7 has no formal requirement IDs in REQUIREMENTS.md (listed as TBD). Tests should cover the integration layer:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `/api/analyze/{run_id}` POST accepts valid payload, returns 202 | unit | `pytest tests/api/test_routes.py::test_analyze_post -x` | Wave 0 |
| `/api/analyze/{run_id}/stream` GET opens SSE, emits node events, emits complete | integration | `pytest tests/api/test_routes.py::test_sse_stream -x` | Wave 0 |
| `ProgressCallbackHandler` puts events on queue when `on_chain_end` fires | unit | `pytest tests/api/test_progress.py::test_callback_handler -x` | Wave 0 |
| FastAPI serves `frontend/dist/index.html` for unknown paths in production | unit | `pytest tests/api/test_routes.py::test_spa_fallback -x` | Wave 0 |
| Pydantic `AnalyzeRequest.config_dict()` merges with DEFAULT_CONFIG correctly | unit | `pytest tests/api/test_schemas.py::test_config_dict -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/api/ -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/api/__init__.py` — package init
- [ ] `tests/api/test_routes.py` — API route tests
- [ ] `tests/api/test_progress.py` — callback handler unit tests
- [ ] `tests/api/test_schemas.py` — Pydantic schema tests
- [ ] Add `httpx` and `pytest-asyncio` to dev dependencies: `pip install httpx pytest-asyncio`

## Sources

### Primary (HIGH confidence)
- [Tailwind CSS Vite Guide](https://tailwindcss.com/docs/guides/vite) — v4 installation, vite.config.ts, CSS import
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) — version 3.3.4, EventSourceResponse API
- [FastAPI CORS docs](https://fastapi.tiangolo.com/tutorial/cors/) — CORSMiddleware configuration
- [FastAPI Static Files docs](https://fastapi.tiangolo.com/tutorial/static-files/) — StaticFiles mount pattern
- `cli/stats_handler.py` (project source) — BaseCallbackHandler pattern already in use
- `tradingagents/graph/trading_graph.py` (project source) — `callbacks` parameter on `TradingAgentsGraph.__init__`

### Secondary (MEDIUM confidence)
- [SSE with FastAPI and React (softgrade.org)](https://www.softgrade.org/sse-with-fastapi-react-langgraph/) — FastAPI StreamingResponse + React EventSource pattern; verified against FastAPI and sse-starlette docs
- [LangGraph SSE Streaming fullstack (DeepWiki)](https://deepwiki.com/langchain-ai/langgraph-fullstack-python/2.3-sse-streaming) — LangGraph streaming modes and event format
- [LangChain BaseCallbackHandler API](https://python.langchain.com/api_reference/core/callbacks/langchain_core.callbacks.base.BaseCallbackHandler.html) — `on_chain_start`/`on_chain_end` method signatures

### Tertiary (LOW confidence)
- WebSearch results re: `langgraph_node` metadata in `astream_events` — not verified against official LangGraph docs; treat as hypothesis until tested in Wave 1 discovery task

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified via npm/PyPI search (April 2026 current)
- Architecture: HIGH — patterns derived from project source code + official FastAPI/sse-starlette docs
- SSE + async bridge pattern: HIGH — well-documented Python asyncio pattern; verified against sse-starlette docs
- LangGraph callback name granularity: LOW — requires empirical validation in Wave 1
- Tailwind v4 setup: HIGH — verified against official Tailwind docs

**Research date:** 2026-04-01
**Valid until:** 2026-07-01 (Vite and Tailwind move fast; React 19 stable)
