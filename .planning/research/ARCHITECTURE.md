# Architecture Patterns

**Domain:** Stock Recommendation / Screening System integrated into existing multi-agent trading framework
**Researched:** 2026-04-02
**Mode:** Integration architecture — new milestone onto existing codebase

---

## Context: Existing Architecture (v1.0 baseline)

The system being extended has a well-established, consistent architecture that all new components must conform to. Understanding the invariants is the primary job of this document.

### Invariants (do not break these)

| Invariant | Where enforced | Impact if broken |
|-----------|---------------|------------------|
| All agents are `create_*` factory functions returning closures | `tradingagents/agents/` | Graph setup breaks, memory injection fails |
| All agents read/write via `AgentState` (TypedDict over `MessagesState`) | `agent_states.py` | State propagation across graph nodes fails |
| Data access goes through `route_to_vendor(method, ...)` from `interface.py` | `dataflows/interface.py` | Vendor abstraction bypassed, no fallback |
| Graph nodes wired in `setup.py` `GraphSetup.setup_graph()` | `graph/setup.py` | New nodes invisible to the graph orchestrator |
| LLM instances are `quick_thinking_llm` / `deep_thinking_llm` from `TradingAgentsGraph` | `trading_graph.py` | Violates "no new LLM dependencies" constraint |
| LangGraph node names use dash separator (not colon) | `setup.py` OPTIONS_NODES | Node name reserved-character conflict |
| Options pipeline is additive (equity-only mode unchanged) | `setup.py` `enable_options` gate | Regression in equity-only path |

---

## Recommended Architecture

### Decision 1: Screener is a standalone module, NOT a second LangGraph graph

**Verdict:** Build the screener as a standalone Python module at `tradingagents/screener/`, not as a separate `StateGraph`.

**Rationale:**
- The screener has a fundamentally different execution shape from the analysis graph. The analysis graph is a parallel fan-out/fan-in pipeline for a **single ticker**. The screener processes **50+ tickers sequentially** with a lightweight data fetch per ticker, then makes a single LLM ranking call. This is a batch scan, not a conversational multi-agent pipeline.
- A `StateGraph` adds overhead (graph compilation, `AgentState` initialization, SSE streaming machinery) that provides zero value for a batch scan.
- A `StateGraph` would force 50 separate `graph.invoke()` calls (one per candidate), making the pre-filter stage an LLM graph invocation, which is wasteful — the pre-filter is pure Python math.
- The options pipeline was rightly added as nodes to the **existing** graph because it shared the ticker context already in `AgentState`. The screener operates in a separate phase with different inputs.
- The existing `TradingAgentsGraph.propagate()` remains the entry point for the full analysis pipeline. The screener produces a ticker list as output; that list is consumed as input to a subsequent `propagate()` call — a clean handoff, not a merged graph.

**Structure:**
```
tradingagents/
  screener/
    __init__.py            # exports: run_screener, ScreenerResult
    pre_filter.py          # programmatic filters → list[CandidateTicker]
    llm_ranker.py          # create_llm_ranker factory → top picks + rationale
    data_fetcher.py        # screener-specific data via existing route_to_vendor
    models.py              # ScreenerConfig, CandidateTicker, ScreenerResult dataclasses
```

### Decision 2: Pre-filter connects to LLM ranker via plain Python dataclasses

**Data flow within screener:**

```
pre_filter.run_pre_filter(config) -> list[CandidateTicker]
    |
    | (synchronous, pure Python, no LLM)
    v
llm_ranker.rank_candidates(candidates, config, llm) -> ScreenerResult
    |
    | (single LLM call with structured prompt)
    v
ScreenerResult(picks=[TopPick, ...], rationale=str, screened_at=str)
```

`CandidateTicker` is a plain dataclass (not an `AgentState` field), carrying:
- `symbol: str`
- `volume_ratio: float` (volume vs 20-day avg)
- `price_change_pct: float` (1-day)
- `sector: str`
- `market_cap: float`
- `unusual_options_activity: bool` (optional, if options data available)
- `filter_tags: list[str]` (which filters flagged this candidate)

The LLM ranker is a `create_*` factory following the existing pattern:

```python
# tradingagents/screener/llm_ranker.py

def create_llm_ranker(llm):
    def rank_candidates(candidates: list[CandidateTicker], config: ScreenerConfig) -> ScreenerResult:
        # Build prompt from candidates list
        # Single LLM call (quick_thinking_llm is appropriate here)
        # Return ScreenerResult
        ...
    return rank_candidates
```

This matches the factory pattern of every other agent in the codebase. The `llm` argument is injected at construction time from `quick_thinking_llm`, same as analyst agents.

### Decision 3: Screener data fetches via existing vendor layer

**Verdict:** The screener shares the existing `route_to_vendor` / `VENDOR_METHODS` layer. No separate data fetching stack.

**Rationale:**
- The pre-filter needs `get_stock_data` (OHLCV + volume) and optionally `get_options_chain` (for unusual activity flags). Both are already in `VENDOR_METHODS`.
- A new `screener_data` vendor category with `"get_market_movers"` and `"get_sector_movers"` entries should be added to `VENDOR_METHODS` to cover universe-level scans (yfinance `download()` for a predefined index ETF like SPY components or sector ETFs).
- This keeps the vendor abstraction intact. If the user later switches to Polygon for real-time screening, they add a `polygon` key to the new methods — same pattern as Tradier was added for options.

**New VENDOR_METHODS entries:**
```python
"get_market_movers": {
    "yfinance": get_yfinance_market_movers,    # volume leaders from a symbol list
},
"get_sector_snapshot": {
    "yfinance": get_yfinance_sector_snapshot,  # sector ETF momentum
},
```

**New data_vendors config key:**
```python
"screener_data": "yfinance",    # Options: yfinance (only vendor at v1.1)
```

### Decision 4: Screener results flow via new static REST endpoint (not SSE)

**Verdict:** New endpoint `POST /api/screen` returns a synchronous JSON response. No SSE streaming for the screener.

**Rationale:**
- SSE is appropriate when: (a) the operation takes >5 seconds with meaningful incremental progress, and (b) intermediate states have UI value (showing each agent complete). Screener pre-filter runs in ~2s (yfinance batch fetch for ~50 tickers). LLM call adds ~3-5s. Total ~5-8s. A loading spinner is sufficient.
- The screener has no meaningful intermediate state to stream. The pre-filter result (50 candidates) is not worth rendering before the LLM ranking arrives — it's a raw list with no rationale.
- SSE adds complexity: `run_id`, `register_run`, `ProgressCallbackHandler`, `EventSource` client-side. That machinery exists for 10+ sequential agent calls. A single-phase operation doesn't justify it.
- If screening performance degrades significantly (>15s), SSE can be added later following the identical pattern already in `routes.py` — the code path is well-understood.

**New API endpoint:**
```python
# api/routes.py — additive

@router.post("/screen", response_model=ScreenResponse)
async def run_screen(request: ScreenRequest):
    """Run screener pre-filter + LLM ranking. Returns synchronous JSON result."""
    from tradingagents.screener import run_screener
    config = request.config_dict()
    result = await asyncio.to_thread(run_screener, config, llm=quick_thinking_llm)
    return ScreenResponse(picks=result.picks, screened_at=result.screened_at)
```

**New schemas:**
```python
class ScreenRequest(BaseModel):
    date: str                          # "YYYY-MM-DD"
    universe: str = "sp500"           # symbol universe to screen
    min_volume_ratio: float = 1.5     # volume vs 20d avg threshold
    max_candidates: int = 50          # pre-filter output cap
    top_n: int = 5                    # LLM output cap
    llm_provider: str = "openai"
    quick_think_llm: str = "gpt-5-mini"

class TopPick(BaseModel):
    symbol: str
    rationale: str
    confidence: str                   # "high" | "medium" | "low"
    filter_tags: list[str]            # why it was pre-selected

class ScreenResponse(BaseModel):
    picks: list[TopPick]
    screened_at: str
```

### Decision 5: "Select from watchlist → run full pipeline" flow

**Verdict:** Watchlist is frontend-local state, not persisted server-side. Selecting a pick calls the existing `POST /api/analyze/{run_id}` endpoint unchanged.

**Flow:**
```
User clicks "Screen" button
    → POST /api/screen (new endpoint)
    → ScreenResponse { picks: [{symbol, rationale, ...}, ...] }
    → Frontend renders WatchlistPanel (new component)
    → User clicks "Analyze" on a pick
    → Frontend populates existing ticker/date fields in ConfigSidebar
    → Calls existing startAnalysis() → POST /api/analyze/{run_id}
    → Existing SSE stream + progress stepper
```

This design reuses 100% of the existing analysis pipeline entry point. The watchlist is ephemeral UI state — it lives in React component state for the current session. No backend persistence is needed for v1.1 (the PROJECT.md out-of-scope list excludes portfolio tracking).

The ConfigSidebar `ticker` input is controlled state — pre-populating it with a screener pick requires lifting that state or passing a `selectedTicker` prop down. The cleanest approach is to lift ticker/date state to `App.tsx` (they are already partially there) and expose a `onPickSelected(symbol: string)` callback from `WatchlistPanel`.

### Decision 6: New AgentState fields

**Verdict:** No new `AgentState` fields are needed for the screener.

**Rationale:**
- The screener runs outside the `StateGraph`. Its output (`ScreenerResult`) is a standalone dataclass returned from `POST /api/screen`. It never enters the LangGraph state machine.
- When the user selects a screener pick for full analysis, the flow creates a brand new `AgentState` initialized by `Propagator.create_initial_state(symbol, date)` — same as today.
- If a future milestone wants screener context to inform the analysis (e.g., "this ticker was flagged for unusual options activity"), that rationale can be passed as a new `screener_context: str` field in `AgentState`. That is explicitly a v1.2+ concern.

---

## Component Boundaries

| Component | Responsibility | Communicates With | New or Modified |
|-----------|---------------|-------------------|-----------------|
| `tradingagents/screener/pre_filter.py` | Fetch market universe, apply volume/momentum/activity filters, return `list[CandidateTicker]` | `dataflows/interface.route_to_vendor` | NEW |
| `tradingagents/screener/llm_ranker.py` | Accept candidates list, build prompt, call `quick_thinking_llm`, parse `ScreenerResult` | `quick_thinking_llm` (injected) | NEW |
| `tradingagents/screener/data_fetcher.py` | Screener-specific data helpers (market movers, sector ETF data) | `dataflows/y_finance.py` | NEW |
| `tradingagents/screener/models.py` | `ScreenerConfig`, `CandidateTicker`, `TopPick`, `ScreenerResult` dataclasses | — | NEW |
| `tradingagents/dataflows/interface.py` | Add `get_market_movers`, `get_sector_snapshot` to `VENDOR_METHODS` and `TOOLS_CATEGORIES` | `dataflows/y_finance.py` (new functions) | MODIFIED |
| `tradingagents/dataflows/y_finance.py` | Add `get_yfinance_market_movers()`, `get_yfinance_sector_snapshot()` | yfinance | MODIFIED |
| `tradingagents/default_config.py` | Add `screener_data: "yfinance"` to `data_vendors` | — | MODIFIED |
| `api/routes.py` | Add `POST /api/screen` endpoint | `tradingagents/screener` | MODIFIED |
| `api/schemas.py` | Add `ScreenRequest`, `ScreenResponse`, `TopPick` | — | MODIFIED |
| `frontend/src/components/WatchlistPanel.tsx` | Render screener picks, "Analyze" button per pick | `useScreen` hook | NEW |
| `frontend/src/hooks/useScreen.ts` | Call `POST /api/screen`, manage loading/result state | `/api/screen` | NEW |
| `frontend/src/types.ts` | Add `ScreenRequest`, `ScreenResponse`, `TopPick` types | — | MODIFIED |
| `frontend/src/App.tsx` | Add screener tab/panel, lift ticker state for pick selection, wire `onPickSelected` | `WatchlistPanel`, `ConfigSidebar` | MODIFIED |
| `cli/main.py` | Add `screen` Typer subcommand | `tradingagents/screener` | MODIFIED |

### Unchanged Components

These components are **not touched** by the screener milestone:

- `tradingagents/graph/trading_graph.py` — no changes
- `tradingagents/graph/setup.py` — no new nodes
- `tradingagents/agents/utils/agent_states.py` — no new fields
- `tradingagents/agents/analysts/*` — no changes
- `tradingagents/agents/options/*` — no changes
- `tradingagents/agents/managers/*` — no changes
- `tradingagents/graph/propagation.py`, `reflection.py`, `signal_processing.py` — no changes
- `api/progress.py` — no changes (SSE not used for screener)

---

## Data Flow

### Screener Flow

```
POST /api/screen
  { date, universe, min_volume_ratio, max_candidates, top_n, llm_provider, quick_think_llm }
        |
        v
  api/routes.py: run_screen()
        |
        | asyncio.to_thread()
        v
  tradingagents/screener/__init__.run_screener(config, llm)
        |
        +---> pre_filter.run_pre_filter(config)
        |         |
        |         | route_to_vendor("get_market_movers", ...)
        |         v
        |     yfinance: batch download ~100-500 symbols
        |     filter by: volume_ratio > threshold, price_change_pct, sector
        |     returns: list[CandidateTicker] (~20-50 items)
        |
        +---> llm_ranker.rank_candidates(candidates, config)
                  |
                  | quick_thinking_llm.invoke(prompt)
                  v
              ScreenerResult { picks: list[TopPick], screened_at }
        |
        v
  ScreenResponse (JSON) → frontend
```

### Watchlist → Analysis Flow

```
WatchlistPanel: user clicks "Analyze AAPL"
        |
        v
  App.tsx: onPickSelected("AAPL")
        |
        | sets ticker state (lifted from ConfigSidebar)
        v
  ConfigSidebar: ticker field pre-populated with "AAPL"
        |
  User confirms and clicks "Analyze"
        |
        v
  useAnalysis.startAnalysis({ ticker: "AAPL", date, analysts, ... })
        |
        | POST /api/analyze/{run_id}  ← EXISTING, UNCHANGED
        v
  Existing SSE stream → existing progress stepper → existing report tabs
```

---

## Patterns to Follow

### Pattern: `create_*` factory for LLM ranker

The LLM ranker follows the identical factory closure pattern used by all agents. The `llm` is injected at construction; the returned function is stateless (suitable for concurrent calls if needed later).

```python
def create_llm_ranker(llm):
    """Factory: returns rank_candidates closure with bound LLM."""
    def rank_candidates(
        candidates: list[CandidateTicker],
        config: ScreenerConfig,
    ) -> ScreenerResult:
        prompt = _build_ranking_prompt(candidates, config)
        response = llm.invoke(prompt)
        return _parse_response(response.content, candidates)
    return rank_candidates
```

### Pattern: `route_to_vendor` for all data access

New screener data functions call `route_to_vendor` rather than importing yfinance directly. This is the same pattern followed by every agent utility in `agent_utils.py`.

```python
# tradingagents/screener/data_fetcher.py
from tradingagents.dataflows.interface import route_to_vendor

def fetch_market_movers(symbol_list: list[str], date: str) -> list[dict]:
    return route_to_vendor("get_market_movers", symbol_list, date)
```

### Pattern: Graceful degradation for screener data gaps

Options agents use `_safe_options_node` wrapper to catch errors and return empty string fallbacks. The pre-filter should do the same at the symbol level — if one ticker fails to fetch, skip it and continue. A partial candidate list is better than a total failure.

```python
for symbol in universe:
    try:
        data = fetch_single_ticker_metrics(symbol, date)
        candidates.append(data)
    except Exception:
        continue   # skip silently, log at DEBUG level
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Screener as a second StateGraph

**What it looks like:** Creating `ScreenerGraph` with `StateGraph(ScreenerState)`, adding "Pre-Filter Node" and "LLM Ranker Node" as graph nodes.

**Why bad:** `StateGraph` compilation overhead for a two-step sequential operation is pure waste. There is no parallelism, no conditional routing, no debate loops — the two structural justifications for using LangGraph. The `AgentState`/`MessagesState` base adds `messages` list management that the screener doesn't need. The SSE streaming infrastructure assumes a graph is running. This creates a false architectural symmetry that makes the screener harder to test in isolation.

**Instead:** Plain Python module with two functions called sequentially. `run_screener()` calls `run_pre_filter()` then `rank_candidates()`. Tests call each function directly with mock data.

### Anti-Pattern 2: Bypassing route_to_vendor for screener data

**What it looks like:** `import yfinance as yf` directly inside `pre_filter.py`, calling `yf.download(symbols)` inline.

**Why bad:** Creates a direct yfinance dependency in the screener, bypassing the vendor abstraction. When a future vendor (Polygon, Alpaca) provides better universe-level data, there is no swap path. Also skips the caching layer in `yfinance_cache.py`.

**Instead:** Register `get_market_movers` in `VENDOR_METHODS`, implement in `y_finance.py`, call via `route_to_vendor`.

### Anti-Pattern 3: Storing watchlist in backend

**What it looks like:** Adding a `POST /api/watchlist` endpoint that persists tickers to disk or DB. Frontend fetches watchlist on load.

**Why bad:** The screener result is ephemeral (valid for today's market data). A stale watchlist from yesterday has no analytical value. Persistence adds state management complexity (when to expire, how to diff, what happens to stale picks). PROJECT.md explicitly excludes "Portfolio management / position tracking UI."

**Instead:** Watchlist is React component state. It lives for the session duration and resets when the user refreshes. If the user needs to re-screen, they press "Screen" again — the operation is fast enough.

### Anti-Pattern 4: Adding screener_report to AgentState

**What it looks like:** Adding `screener_report: Annotated[str, "Report from Screener"]` to `AgentState`, passing screener context into the analysis graph.

**Why bad:** Conflates two separate operational phases (discovery vs analysis). The analysis graph should produce the same output whether a ticker came from the screener or was manually entered. Injecting screener context risks contaminating the independent analyst agents with prior bias. `AgentState` is already growing (it has 15 fields). Adding screener data that is only populated for some runs creates another "empty string if not used" pattern that makes the state harder to reason about.

**Instead:** If screener context is ever needed in analysis (a v1.2+ decision), pass it as a separate optional `screener_hint` field with explicit documentation of what it means. Do not add it speculatively in v1.1.

---

## Build Order (Dependency-Ordered)

### Phase A: Screener data layer (no LLM dependency)

1. `tradingagents/dataflows/y_finance.py` — add `get_yfinance_market_movers()`, `get_yfinance_sector_snapshot()`
2. `tradingagents/dataflows/interface.py` — register new methods in `VENDOR_METHODS`, `TOOLS_CATEGORIES`
3. `tradingagents/default_config.py` — add `"screener_data": "yfinance"` to `data_vendors`
4. `tradingagents/screener/models.py` — `ScreenerConfig`, `CandidateTicker`, `TopPick`, `ScreenerResult`
5. `tradingagents/screener/data_fetcher.py` — thin wrapper calling `route_to_vendor`
6. `tradingagents/screener/pre_filter.py` — programmatic filter logic; **testable standalone without LLM**

**Gate:** Unit tests for pre-filter with mock yfinance data. Verify candidate output shape, filter thresholds, and graceful skip on bad tickers.

### Phase B: LLM ranker (depends on Phase A models + data)

7. `tradingagents/screener/llm_ranker.py` — `create_llm_ranker` factory
8. `tradingagents/screener/__init__.py` — `run_screener(config, llm)` public entry point

**Gate:** Integration test with a small fixed candidate list. Verify `ScreenerResult` parse is robust to LLM response variation.

### Phase C: API endpoint (depends on Phase B)

9. `api/schemas.py` — `ScreenRequest`, `ScreenResponse`, `TopPick` Pydantic models
10. `api/routes.py` — `POST /api/screen` endpoint

**Gate:** `curl` test against running FastAPI server. Verify JSON shape matches `ScreenResponse`.

### Phase D: Frontend (depends on Phase C API contract)

11. `frontend/src/types.ts` — add screener types
12. `frontend/src/hooks/useScreen.ts` — fetch hook for `POST /api/screen`
13. `frontend/src/components/WatchlistPanel.tsx` — screener UI, "Analyze" button per pick
14. `frontend/src/App.tsx` — add screener tab/panel, lift ticker state, wire `onPickSelected`

**Gate:** Manual test: run screener from UI, verify picks render, click "Analyze", verify existing analysis pipeline starts with correct ticker.

### Phase E: CLI (depends on Phase B, independent of Phase C/D)

15. `cli/main.py` — add `screen` Typer subcommand with Rich table output

**Gate:** `python -m cli screen --date 2026-04-02` returns table of picks.

---

## Scalability Considerations

| Concern | At v1.1 (current) | At v1.2+ (if needed) |
|---------|------------------|----------------------|
| Universe size | ~100-500 symbols (S&P 500 or sector ETFs) — yfinance `download()` handles this in ~2s | Larger universes (Russell 2000, ~2000 symbols) need pagination or async fetch |
| Pre-filter latency | ~2s synchronous — acceptable | Switch to async yfinance calls or use a faster data source (Polygon websocket) |
| LLM ranker latency | ~3-5s single call — acceptable | Already single call; little room to optimize beyond model selection |
| Concurrent screener requests | Not anticipated in v1.1 (single-user tool) | Add request queue or per-user rate limiting at API layer |
| Screener result freshness | Session-ephemeral is fine for market hours | If 24/7 use: add TTL cache keyed by `(universe, date)` using same `yfinance_cache.py` pattern |

---

## Sources

- Codebase reading: `tradingagents/graph/setup.py`, `trading_graph.py`, `agent_states.py` — confirmed StateGraph and AgentState structure (HIGH confidence)
- Codebase reading: `tradingagents/dataflows/interface.py` — confirmed VENDOR_METHODS routing pattern (HIGH confidence)
- Codebase reading: `api/routes.py`, `api/schemas.py` — confirmed SSE endpoint structure (HIGH confidence)
- Codebase reading: `frontend/src/hooks/useAnalysis.ts`, `App.tsx`, `types.ts` — confirmed frontend state and SSE consumption pattern (HIGH confidence)
- Codebase reading: `tradingagents/agents/options/volatility_analyst.py` — confirmed `create_*` factory closure pattern for agents (HIGH confidence)
- Codebase reading: `.planning/PROJECT.md` — confirmed v1.1 requirements and out-of-scope boundaries (HIGH confidence)
- Architecture decisions are derived from direct codebase analysis. No external sources consulted; all findings are HIGH confidence.
