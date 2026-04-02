# Phase 10: Backend API Endpoint - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `POST /api/screen` endpoint to the existing FastAPI application that calls the screener agent and returns ranked picks as JSON. This phase delivers the API endpoint only — no frontend changes, no CLI changes.

</domain>

<decisions>
## Implementation Decisions

### API Design
- `POST /api/screen` accepts optional JSON body with `max_picks` (default 5, hard cap 10) and `universe` (default "sp500")
- Response wrapped in standard envelope: `{status: "success"|"partial"|"error", data: ScreenerResult dict, screened_at: ISO timestamp}`
- LLM failures return 200 with partial results + error field (matches agent's graceful degradation from Phase 9)
- No auth or rate limiting for v1.1 — internal tool, no public exposure

### FastAPI Integration
- New `api/screener_routes.py` file with its own `APIRouter`, included in `api/main.py` — keeps screener logic separate from analysis SSE stream
- Use existing `default_config.py` + `create_llm_client()` factory for LLM instance
- Sync endpoint logic with `asyncio.to_thread()` for the blocking `run_screener()` call — FastAPI handles threading, keeps event loop free for SSE streams

### Claude's Discretion
- Pydantic request/response schema naming and organization
- Error message wording
- Exact import path organization within api/ module

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/routes.py` — existing `APIRouter(prefix="/api")` with `/analyze` endpoint pattern
- `api/schemas.py` — existing Pydantic request/response schemas (AnalyzeRequest, AnalyzeResponse)
- `api/main.py` — FastAPI app with CORS middleware, `app.include_router(router)`
- `tradingagents/agents/screener/screener_agent.py` — `run_screener(config, llm)` returns `ScreenerResult`
- `tradingagents/default_config.py` — `DEFAULT_CONFIG` dict
- `tradingagents/llm_clients/factory.py` — `create_llm_client()` factory

### Established Patterns
- Routes use `APIRouter(prefix="/api")` in `api/routes.py`
- Schemas defined in `api/schemas.py` with Pydantic BaseModel
- Analysis endpoint uses async background task + SSE for long-running ops
- Config dict passed to graph/agent constructors

### Integration Points
- `api/main.py` — needs `app.include_router(screener_router)` for new route file
- Phase 9: `run_screener(config, llm)` is the entry point to call
- Phase 11 (downstream): Frontend will call `POST /api/screen`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
