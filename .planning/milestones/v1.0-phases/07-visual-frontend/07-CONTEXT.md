# Phase 7: Visual Frontend - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a React + FastAPI web frontend that wraps the existing `TradingAgentsGraph` pipeline. Users configure analysis parameters (ticker, date, analysts, options toggle) through a GUI, watch real-time agent progress via SSE streaming, and view all reports in a tabbed layout. The existing CLI and programmatic interfaces remain unchanged — the frontend is an additive layer.

</domain>

<decisions>
## Implementation Decisions

### Technology Stack
- Frontend: React + TypeScript built with Vite in a `frontend/` directory
- Backend: FastAPI thin wrapper around `TradingAgentsGraph` — `/api/analyze` endpoint
- Styling: Tailwind CSS — utility-first, no component library
- Deployment: Local-only (same machine) — matches CLI usage model
- State management: React state (useState/useReducer) — no external state library needed for single-user

### Architecture & API Design
- FastAPI backend: thin wrapper — `/api/analyze` accepts ticker/date/config JSON, runs `TradingAgentsGraph.propagate()`, returns final decision + all reports
- Real-time progress: Server-Sent Events (SSE) — `/api/analyze/{run_id}/stream` emits agent completion events as they happen
- Frontend in `frontend/` directory alongside existing Python code — separate npm project, proxied to FastAPI in dev
- No microservices — single FastAPI process handles everything

### UI Layout & Features
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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/graph/trading_graph.py` — `TradingAgentsGraph` class with `propagate(ticker, date)` method — the main entry point to wrap
- `tradingagents/default_config.py` — `DEFAULT_CONFIG` dict with all configurable settings
- `cli/main.py` — existing CLI shows the full configuration flow (ticker, date, analysts, LLM provider) to replicate in GUI
- `cli/stats_handler.py` — callback metrics for LLM/tool usage — pattern for progress tracking

### Established Patterns
- `TradingAgentsGraph(debug=True, config=config)` then `ta.propagate(ticker, date)` — simple programmatic API
- Config is a dict copy of `DEFAULT_CONFIG` with overrides — easy to serialize as JSON
- Agent reports are strings in `AgentState` — can be returned as JSON fields

### Integration Points
- `tradingagents/graph/trading_graph.py` — need to add callback hooks for SSE progress events
- `tradingagents/graph/propagation.py` — `create_initial_state()` shows all state fields to surface in UI
- `tradingagents/default_config.py` — source of truth for all config options to expose in sidebar

</code_context>

<specifics>
## Specific Ideas

- FastAPI app in `api/` directory (new): `api/main.py`, `api/routes.py`, `api/schemas.py`
- Frontend in `frontend/` directory (new): Vite + React + TypeScript + Tailwind
- Dev workflow: `uvicorn api.main:app --reload` + `cd frontend && npm run dev` (Vite proxies API calls)
- Production: `npm run build` generates `frontend/dist/`, FastAPI serves static files from there
- SSE implementation: FastAPI `StreamingResponse` with `text/event-stream` content type
- Agent progress: inject a LangGraph callback that emits SSE events when each node completes

</specifics>

<deferred>
## Deferred Ideas

- Multi-user support / authentication — single-user local app for v1
- Run history / persistence — optional enhancement, not core
- Mobile responsive layout — desktop-first for v1
- Real-time chart/graph visualization of the StateGraph node execution

</deferred>
