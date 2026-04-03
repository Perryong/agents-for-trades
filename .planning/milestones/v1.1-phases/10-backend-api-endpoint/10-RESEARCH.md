# Phase 10: Backend API Endpoint - Research

**Researched:** 2026-04-02
**Domain:** FastAPI route + Pydantic schemas + asyncio.to_thread integration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### API Design
- `POST /api/screen` accepts optional JSON body with `max_picks` (default 5, hard cap 10) and `universe` (default "sp500")
- Response wrapped in standard envelope: `{status: "success"|"partial"|"error", data: ScreenerResult dict, screened_at: ISO timestamp}`
- LLM failures return 200 with partial results + error field (matches agent's graceful degradation from Phase 9)
- No auth or rate limiting for v1.1 — internal tool, no public exposure

#### FastAPI Integration
- New `api/screener_routes.py` file with its own `APIRouter`, included in `api/main.py` — keeps screener logic separate from analysis SSE stream
- Use existing `default_config.py` + `create_llm_client()` factory for LLM instance
- Sync endpoint logic with `asyncio.to_thread()` for the blocking `run_screener()` call — FastAPI handles threading, keeps event loop free for SSE streams

### Claude's Discretion
- Pydantic request/response schema naming and organization
- Error message wording
- Exact import path organization within api/ module

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | `POST /api/screen` endpoint returns synchronous JSON with ranked picks and `screened_at` timestamp | FastAPI sync-via-asyncio.to_thread pattern; ScreenerResult already carries `screened_at`; envelope schema maps directly |
| API-02 | Screener endpoint is independent from analysis SSE stream — no coupling between screener and pipeline | Separate `APIRouter` in `screener_routes.py`; `asyncio.to_thread()` runs blocking call in thread pool without touching SSE queue |
</phase_requirements>

---

## Summary

Phase 10 adds a single `POST /api/screen` endpoint to the existing FastAPI application. The full Phase 9 screener pipeline (`run_screener(config, llm)`) is synchronous and takes 5-8 seconds; the correct FastAPI integration is `asyncio.to_thread()` — the same pattern already used in `api/routes.py` for `ta.propagate`. The new route lives in `api/screener_routes.py`, wired into `api/main.py` with one `app.include_router()` call.

The codebase already provides every building block: `APIRouter`, `ScreenerResult` Pydantic model, `DEFAULT_CONFIG`, and `create_llm_client()`. This phase is primarily a thin integration — define two schemas (`ScreenRequest`, `ScreenResponse`), wrap `run_screener()` in a thread, and serialize the result into the response envelope.

The independence requirement (API-02) is satisfied structurally: `screener_routes.py` shares no state with `api/routes.py`. The SSE queue mechanism (`register_run` / `get_queue`) is not touched. There is no shared mutable state between the two routes.

**Primary recommendation:** Mirror the existing `api/routes.py` pattern exactly — `APIRouter(prefix="/api")`, `asyncio.to_thread()` for the blocking call, Pydantic schemas in `api/schemas.py` — then add `app.include_router(screener_router)` in `main.py`.

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (project dep) | HTTP framework, router, automatic OpenAPI | Already powering `/api/analyze` |
| Pydantic v2 | (project dep via FastAPI) | Request/response schema validation | BaseModel pattern already used in `api/schemas.py` |
| asyncio (stdlib) | Python 3.10+ | `asyncio.to_thread()` for blocking call offload | Already used in `api/routes.py` line 31 |
| `tradingagents.agents.screener.screener_agent` | Phase 9 output | `run_screener(config, llm)` entry point | Built in Phase 9; `ScreenerResult` already has all required fields |
| `tradingagents.llm_clients.factory` | Phase <9 | `create_llm_client(provider, model)` | Existing factory; used by all agents |
| `tradingagents.default_config` | Phase <9 | `DEFAULT_CONFIG` base dict | Same dict AnalyzeRequest.config_dict() copies |

No new packages required. All dependencies are present.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` + `pytest-asyncio` | (dev deps present) | Async test client for endpoint tests | Already used in `tests/api/test_routes.py` |

---

## Architecture Patterns

### Recommended File Layout

```
api/
├── __init__.py          # (empty, unchanged)
├── main.py              # +1 line: app.include_router(screener_router)
├── routes.py            # unchanged (analysis SSE routes)
├── screener_routes.py   # NEW: POST /api/screen
├── schemas.py           # +2 new models: ScreenRequest, ScreenResponse
└── progress.py          # unchanged (SSE queue)

tests/api/
├── test_screener_routes.py   # NEW: endpoint tests
└── (existing test files unchanged)
```

### Pattern 1: Sync-blocking call via asyncio.to_thread (ESTABLISHED IN PROJECT)

The analysis route already uses this pattern. Apply identically to the screener.

**What:** Run a synchronous, blocking function inside an async FastAPI handler without blocking the event loop.
**When to use:** Any time the called code is not async-native (LangChain chains, pandas, yfinance).

```python
# Source: api/routes.py (existing, line 31)
final_state, signal = await asyncio.to_thread(
    ta.propagate, request.ticker, request.date
)

# Screener equivalent (api/screener_routes.py):
result: ScreenerResult = await asyncio.to_thread(run_screener, config, llm)
```

The key point: `asyncio.to_thread()` runs the callable in `ThreadPoolExecutor` managed by the event loop. The SSE stream (`stream_progress`) runs in the same event loop but in `asyncio.Queue.get()` — they do not share any thread-local state, so concurrent execution is safe.

### Pattern 2: APIRouter with shared prefix (ESTABLISHED IN PROJECT)

```python
# Source: api/routes.py (existing, line 8)
router = APIRouter(prefix="/api")

# Screener equivalent (api/screener_routes.py):
screener_router = APIRouter(prefix="/api")

@screener_router.post("/screen", response_model=ScreenResponse)
async def screen(request: ScreenRequest):
    ...
```

Register in `api/main.py`:
```python
from .screener_routes import screener_router
app.include_router(screener_router)
```

### Pattern 3: config_dict() from request (ESTABLISHED IN PROJECT)

`AnalyzeRequest.config_dict()` copies `DEFAULT_CONFIG` and overlays request fields. `ScreenRequest` needs the same pattern, covering: `llm_provider`, `quick_think_llm`, `screener_n_picks`, `screener_max_candidates`.

```python
# api/schemas.py — new models (follow AnalyzeRequest style)
class ScreenRequest(BaseModel):
    max_picks: int = Field(default=5, ge=1, le=10)
    universe: str = "sp500"
    llm_provider: str = "openai"
    quick_think_llm: str = "gpt-5-mini"

    def config_dict(self) -> dict:
        from tradingagents.default_config import DEFAULT_CONFIG
        cfg = dict(DEFAULT_CONFIG)
        cfg["screener_n_picks"] = self.max_picks
        cfg["llm_provider"] = self.llm_provider
        cfg["quick_think_llm"] = self.quick_think_llm
        return cfg


class ScreenResponse(BaseModel):
    status: str           # "success" | "partial" | "error"
    data: dict            # ScreenerResult.model_dump()
    screened_at: str      # ISO 8601 UTC string (echoed from ScreenerResult)
```

### Pattern 4: Response envelope + status derivation

`ScreenerResult.error` is `None` on success and populated on graceful degradation (LLM parse failure). Map to envelope status:

```python
status = "partial" if result.error else "success"
```

LLM/network errors that raise exceptions are caught and return `status="error"` with a 200 (matching project convention: LLM failures do not return 4xx/5xx to clients).

### Anti-Patterns to Avoid

- **Importing from `api/routes.py`:** Do not import `router`, `register_run`, or `get_queue` from routes.py — these are the SSE queue objects and must not be touched from the screener path.
- **Calling `run_screener()` without `asyncio.to_thread()`:** Direct `await`-ing a sync function blocks the event loop and starves active SSE streams.
- **Creating the LLM client at module import time:** Create it inside the handler (or lazily) so the API starts cleanly without requiring API keys to be set.
- **Using `response_model=ScreenerResult` directly:** `ScreenerResult.screened_at` is a `datetime`; FastAPI serializes it but returning it directly bypasses the envelope. Use `ScreenResponse` with `data: dict` and serialize with `.model_dump(mode="json")`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request validation (max_picks range, types) | Manual if/raise checks | `Field(ge=1, le=10)` on ScreenRequest | Pydantic raises 422 with structured error automatically |
| Blocking call offload | Thread + asyncio.Queue | `asyncio.to_thread()` | Single-line; handles thread pool lifecycle, propagates exceptions |
| Response serialization of datetime | Manual `.isoformat()` | `ScreenerResult.model_dump(mode="json")` | Pydantic v2 `mode="json"` converts datetime → ISO string automatically |
| Route registration | Manual URL parsing | `app.include_router(screener_router)` | FastAPI standard; maintains OpenAPI schema |

---

## Common Pitfalls

### Pitfall 1: `datetime` serialization in `model_dump()`
**What goes wrong:** `ScreenerResult.screened_at` is a `datetime` object. `model_dump()` without `mode="json"` returns the raw `datetime`, which is not JSON-serializable.
**Why it happens:** Pydantic v2's default `model_dump()` returns Python-native types.
**How to avoid:** Always call `result.model_dump(mode="json")` when putting the dict into a JSON response.
**Warning signs:** `TypeError: Object of type datetime is not JSON serializable` at runtime.

### Pitfall 2: LLM client creation raises on missing env var
**What goes wrong:** If `create_llm_client()` is called at module import time (module-level), the API server fails to start when the API key env var is not set.
**Why it happens:** The OpenAI client constructor reads `OPENAI_API_KEY` immediately.
**How to avoid:** Create the LLM client inside the handler function body (per-request), or use `functools.lru_cache` with explicit invalidation. Per-request creation is simplest and correct for v1.1 (no auth layer yet).
**Warning signs:** Import error or `AuthenticationError` on `uvicorn` startup, not on first request.

### Pitfall 3: `universe` parameter not wired to screener data layer
**What goes wrong:** `ScreenRequest.universe` is accepted but `get_screener_signals()` in Phase 8 does not currently accept a universe filter — it always fetches the S&P 500.
**Why it happens:** Phase 8 hardcodes the universe; Phase 10 exposes it in the API for forward-compatibility.
**How to avoid:** Pass `universe` into `config` dict and document that the data layer ignores it in v1.1. Do NOT raise an error if `universe != "sp500"` — the request should succeed with default behavior.
**Warning signs:** Would appear as a runtime KeyError if code tried `config["universe"]` in the data layer.

### Pitfall 4: Concurrent calls not actually independent
**What goes wrong:** A screener call and an analysis SSE stream run concurrently; they appear to interfere.
**Root cause to verify:** The only shared module-level state in the API is `_runs: dict` in `api/progress.py`. The screener must never call `register_run`, `get_queue`, or `remove_run`.
**How to avoid:** `screener_routes.py` must import nothing from `api/progress.py`.
**Warning signs:** SSE stream drops events or screener result appears in a stream queue.

---

## Code Examples

### Full screener route (api/screener_routes.py)

```python
# Source: project pattern derived from api/routes.py
import asyncio
from fastapi import APIRouter
from .schemas import ScreenRequest, ScreenResponse

screener_router = APIRouter(prefix="/api")


@screener_router.post("/screen", response_model=ScreenResponse)
async def screen(request: ScreenRequest):
    """Run the screener pipeline and return ranked picks as JSON.

    Calls run_screener() in a thread pool via asyncio.to_thread() so the
    event loop remains free for concurrent SSE streams (API-02).
    """
    from tradingagents.agents.screener.screener_agent import run_screener
    from tradingagents.llm_clients.factory import create_llm_client

    config = request.config_dict()
    llm = create_llm_client(
        provider=config["llm_provider"],
        model=config["quick_think_llm"],
    )

    try:
        result = await asyncio.to_thread(run_screener, config, llm)
        status = "partial" if result.error else "success"
        return ScreenResponse(
            status=status,
            data=result.model_dump(mode="json"),
            screened_at=result.screened_at.isoformat(),
        )
    except Exception as exc:
        return ScreenResponse(
            status="error",
            data={"error": str(exc)},
            screened_at="",
        )
```

### Schema models to add to api/schemas.py

```python
from pydantic import Field

class ScreenRequest(BaseModel):
    max_picks: int = Field(default=5, ge=1, le=10)
    universe: str = "sp500"
    llm_provider: str = "openai"
    quick_think_llm: str = "gpt-5-mini"

    def config_dict(self) -> Dict[str, Any]:
        from tradingagents.default_config import DEFAULT_CONFIG
        cfg = dict(DEFAULT_CONFIG)
        cfg["screener_n_picks"] = self.max_picks
        cfg["llm_provider"] = self.llm_provider
        cfg["quick_think_llm"] = self.quick_think_llm
        return cfg


class ScreenResponse(BaseModel):
    status: str           # "success" | "partial" | "error"
    data: Dict[str, Any]  # ScreenerResult.model_dump(mode="json") or error dict
    screened_at: str      # ISO 8601 UTC — empty string on hard error
```

### Wiring in api/main.py (one-line addition)

```python
from .screener_routes import screener_router
app.include_router(screener_router)   # add after existing include_router(router)
```

### Test pattern (tests/api/test_screener_routes.py)

```python
# Source: tests/api/test_routes.py (established pattern)
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from api.main import app

@pytest.mark.asyncio
async def test_screen_returns_200_with_picks():
    mock_result = MagicMock()
    mock_result.error = None
    mock_result.screened_at = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)
    mock_result.model_dump.return_value = {
        "picks": [{"ticker": "AAPL", "score": 0.92, "rationale": "...",
                   "confidence": 0.88, "key_metrics": {}}],
        "screened_at": "2026-04-02T12:00:00+00:00",
        "candidate_count": 50,
        "model_used": "ChatOpenAI",
        "error": None,
    }

    with patch("api.screener_routes.run_screener", return_value=mock_result), \
         patch("api.screener_routes.create_llm_client", return_value=MagicMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/screen", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "screened_at" in body
    assert "data" in body
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml `[tool.pytest.ini_options]` testpaths=["tests"]) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/api/test_screener_routes.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | POST /api/screen returns 200 JSON with picks and screened_at | unit (mocked run_screener) | `uv run pytest tests/api/test_screener_routes.py::test_screen_returns_200_with_picks -x` | Wave 0 |
| API-01 | max_picks defaults to 5, hard cap at 10 | unit | `uv run pytest tests/api/test_screener_routes.py::test_screen_max_picks_cap -x` | Wave 0 |
| API-01 | LLM failure returns status="partial" with error field | unit | `uv run pytest tests/api/test_screener_routes.py::test_screen_partial_on_llm_failure -x` | Wave 0 |
| API-01 | Exception in run_screener returns status="error" (not 500) | unit | `uv run pytest tests/api/test_screener_routes.py::test_screen_error_on_exception -x` | Wave 0 |
| API-02 | Concurrent screen + analyze requests both succeed | integration | `uv run pytest tests/api/test_screener_routes.py::test_screen_independent_from_sse -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/api/test_screener_routes.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/api/test_screener_routes.py` — covers API-01 (4 tests) and API-02 (1 test)

*(Existing `tests/api/__init__.py` already present — no framework install needed)*

---

## Open Questions

1. **`universe` parameter scope in v1.1**
   - What we know: `ScreenRequest.universe` defaults to "sp500"; `get_screener_signals()` in Phase 8 does not accept a universe parameter
   - What's unclear: Should unrecognized universe values fail silently or log a warning?
   - Recommendation: Accept and ignore in v1.1 — pass through to config dict, data layer ignores it. No error raised. Add a `# TODO v2: wire universe to data layer` comment.

2. **LLM client per-request vs. cached**
   - What we know: `create_llm_client()` constructs a new HTTP client per call; per-request creation adds ~1ms overhead
   - What's unclear: Whether module-level caching is appropriate without auth scoping
   - Recommendation: Per-request creation for v1.1 (simplest, no shared state risk). Caching deferred to v2 with explicit lifecycle management.

---

## Sources

### Primary (HIGH confidence)

- `api/routes.py` (project source) — `asyncio.to_thread()` pattern, `APIRouter(prefix="/api")`, background task structure
- `api/schemas.py` (project source) — `AnalyzeRequest.config_dict()` pattern, Pydantic BaseModel conventions
- `api/main.py` (project source) — `app.include_router()` registration pattern
- `tradingagents/agents/screener/screener_agent.py` (Phase 9 output) — `run_screener(config, llm)` signature, `ScreenerResult` fields, graceful degradation behavior
- `tradingagents/llm_clients/factory.py` (project source) — `create_llm_client(provider, model)` signature
- `tests/api/test_routes.py` (project source) — `AsyncClient + ASGITransport` test pattern, `patch()` usage

### Secondary (MEDIUM confidence)

- FastAPI official docs (asyncio.to_thread): `asyncio.to_thread()` is the documented approach for running sync code in async FastAPI handlers without blocking the event loop
- Pydantic v2 docs: `model_dump(mode="json")` converts datetime → ISO string automatically

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already installed; signatures verified from source
- Architecture: HIGH — patterns copied verbatim from existing working routes
- Pitfalls: HIGH — identified from direct code inspection of Phase 9 output and existing API layer
- Test patterns: HIGH — copied from `tests/api/test_routes.py`

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable domain; FastAPI + Pydantic v2 patterns do not change frequently)
