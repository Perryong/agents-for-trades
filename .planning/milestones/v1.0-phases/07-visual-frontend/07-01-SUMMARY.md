---
phase: 07-visual-frontend
plan: 01
subsystem: api
tags: [fastapi, pydantic, sse, sse-starlette, asyncio, langchain, progress-callback]

# Dependency graph
requires:
  - phase: 05-graph-integration
    provides: TradingAgentsGraph with callbacks parameter support
  - phase: 04-pricing-order-building-greeks
    provides: DEFAULT_CONFIG with options keys
provides:
  - FastAPI app entrypoint with CORS and SPA fallback (api/main.py)
  - POST /api/analyze/{run_id} endpoint returning 202 (api/routes.py)
  - GET /api/analyze/{run_id}/stream SSE endpoint (api/routes.py)
  - Pydantic models: AnalyzeRequest, AnalyzeResponse, ProgressEvent (api/schemas.py)
  - ProgressCallbackHandler + run_id queue registry (api/progress.py)
  - Test suite for all backend API modules (tests/api/)
affects: [07-02-frontend-scaffolding, 07-03-analysis-form, 07-04-progress-stepper, 07-05-report-tabs]

# Tech tracking
tech-stack:
  added: [fastapi, sse-starlette==3.3.4, uvicorn[standard], httpx, pytest-asyncio]
  patterns:
    - asyncio.Queue + run_coroutine_threadsafe for sync-to-async SSE bridge
    - Two-step POST then GET SSE flow (run_id as client-generated key)
    - ProgressCallbackHandler extending BaseCallbackHandler from langchain_core
    - SPA catch-all via @app.get("/{full_path:path}") mounted after API router

key-files:
  created:
    - api/__init__.py
    - api/schemas.py
    - api/progress.py
    - api/routes.py
    - api/main.py
    - tests/api/__init__.py
    - tests/api/test_schemas.py
    - tests/api/test_progress.py
    - tests/api/test_routes.py
  modified: []

key-decisions:
  - "ProgressEvent includes signal: Optional[str] = None to carry the trading signal on complete events (matches wire format)"
  - "asyncio.run_coroutine_threadsafe used in ProgressCallbackHandler._put to safely bridge sync LangGraph thread to async FastAPI loop"
  - "SPA catch-all uses @app.get route (not StaticFiles mount at /) to avoid clobbering API routes"
  - "API routes registered via include_router before any static mount to preserve route precedence"

patterns-established:
  - "Pattern: SSE progress bridge — register_run creates queue, ProgressCallbackHandler puts events, stream_progress drains queue"
  - "Pattern: Two-step client flow — POST /api/analyze/{run_id} to start (202), then GET /api/analyze/{run_id}/stream for events"

requirements-completed: [FE-API-01, FE-API-02, FE-API-03]

# Metrics
duration: 2min
completed: 2026-04-01
---

# Phase 07 Plan 01: FastAPI Backend API Layer Summary

**FastAPI backend with Pydantic schemas, SSE progress streaming via asyncio.Queue, and SPA catch-all — bridging TradingAgentsGraph to the React frontend**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-01T13:56:46Z
- **Completed:** 2026-04-01T13:59:00Z
- **Tasks:** 2
- **Files modified:** 9 created

## Accomplishments

- Pydantic models (AnalyzeRequest with config_dict(), AnalyzeResponse, ProgressEvent with signal field) covering all schema contracts
- ProgressCallbackHandler extends BaseCallbackHandler, emits node_start/node_end events thread-safely via asyncio.run_coroutine_threadsafe onto a per-run asyncio.Queue
- FastAPI routes: POST /api/analyze/{run_id} returns 202, GET /api/analyze/{run_id}/stream delivers SSE events using sse-starlette EventSourceResponse
- FastAPI app with CORS for Vite dev server (localhost:5173), router registered before optional SPA catch-all
- Full test suite: 13 tests across 3 test files, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic schemas and progress callback handler** - `bca4223` (feat)
2. **Task 2: FastAPI routes and app entrypoint with tests** - `0f79079` (feat)

## Files Created/Modified

- `api/__init__.py` - Empty package init
- `api/schemas.py` - AnalyzeRequest, AnalyzeResponse, ProgressEvent Pydantic models
- `api/progress.py` - ProgressCallbackHandler + run_id queue registry (register_run, get_queue, remove_run)
- `api/routes.py` - POST analyze and GET stream SSE endpoints
- `api/main.py` - FastAPI app with CORS, router include, and SPA catch-all
- `tests/api/__init__.py` - Empty package init
- `tests/api/test_schemas.py` - Schema tests including config_dict merge validation
- `tests/api/test_progress.py` - Callback handler queue put tests from sync thread
- `tests/api/test_routes.py` - Route tests for 202 response, SSE error event, SPA fallback

## Decisions Made

- `ProgressEvent` includes `signal: Optional[str] = None` to carry the trading signal in complete events — matches the wire format emitted by routes.py which adds `"signal": signal` to the complete event payload
- `asyncio.run_coroutine_threadsafe` used in `_put` to safely bridge the sync LangGraph callback thread to the FastAPI async event loop — prevents asyncio.Queue corruption from wrong thread
- SPA catch-all implemented as `@app.get("/{full_path:path}")` returning FileResponse rather than `app.mount("/", StaticFiles(...))` — avoids static mount shadowing API routes
- Guard on `os.path.isdir(DIST_DIR)` prevents startup error when frontend/dist doesn't exist in dev mode

## Deviations from Plan

None — plan executed exactly as written, plus the flagged info-level fix:

**Pre-flagged: Added `signal: Optional[str] = None` to ProgressEvent**
- The plan checker identified that the complete event wire format includes `signal` but the plan's schema snippet omitted it
- Added `signal: Optional[str] = None` to ProgressEvent as instructed in `<important_context>`
- Verified in routes.py: `await q.put({"type": "complete", "state": serialized, "signal": signal})`

## Issues Encountered

None — all tests passed on first run.

## Known Stubs

None — all API endpoints are wired to real logic. The `start_analysis` route imports and calls `TradingAgentsGraph.propagate` via `asyncio.to_thread`. Tests mock the graph to avoid real LLM calls.

## User Setup Required

None — no external service configuration required for the backend API layer itself. LLM provider API keys are required at runtime but managed by the existing .env pattern.

## Next Phase Readiness

- API backend complete and tested — Plan 02 (frontend scaffolding) can proxy to `uvicorn api.main:app --port 8000`
- To start the API: `uvicorn api.main:app --reload --port 8000`
- All SSE event types (node_start, node_end, complete, error) are defined and emitted
- ProgressEvent.signal field available for final decision display in UI

---
*Phase: 07-visual-frontend*
*Completed: 2026-04-01*
