# Architecture Patterns

**Domain:** Multi-agent AI trading framework — v1.1 Screener + v1.2 Paper Trading & Validation
**Researched:** 2026-04-03 (v1.2 additions appended to v1.1 document)
**Confidence:** HIGH (codebase direct inspection + verified external API docs)

---

# v1.1 Screener Architecture (archived — shipped 2026-04-02)

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

## Component Boundaries (v1.1)

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

### Unchanged Components (v1.1)

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

## Data Flow (v1.1)

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

## Patterns to Follow (v1.1)

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

## Anti-Patterns to Avoid (v1.1)

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

## Build Order — v1.1 (Dependency-Ordered)

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

## Scalability Considerations (v1.1)

| Concern | At v1.1 (current) | At v1.2+ (if needed) |
|---------|------------------|----------------------|
| Universe size | ~100-500 symbols (S&P 500 or sector ETFs) — yfinance `download()` handles this in ~2s | Larger universes (Russell 2000, ~2000 symbols) need pagination or async fetch |
| Pre-filter latency | ~2s synchronous — acceptable | Switch to async yfinance calls or use a faster data source (Polygon websocket) |
| LLM ranker latency | ~3-5s single call — acceptable | Already single call; little room to optimize beyond model selection |
| Concurrent screener requests | Not anticipated in v1.1 (single-user tool) | Add request queue or per-user rate limiting at API layer |
| Screener result freshness | Session-ephemeral is fine for market hours | If 24/7 use: add TTL cache keyed by `(universe, date)` using same `yfinance_cache.py` pattern |

---

---

# v1.2 Paper Trading & Validation Architecture

**Researched:** 2026-04-03
**Confidence:** HIGH

## Context: Existing Architecture (post v1.1 baseline)

The current system state after v1.1 ships:

```
┌──────────────────────────────────────────────────────────────────────┐
│  React Frontend (Vite, TypeScript, Tailwind v4)                       │
│  App.tsx → mainSection: 'analysis' | 'screener'                       │
│  hooks/useAnalysis.ts (SSE consumer)                                  │
│  hooks/useScreener.ts (POST /api/screen)                              │
├──────────────────────────────────────────────────────────────────────┤
│  FastAPI Backend  (api/main.py)                                        │
│  POST /api/analyze/{run_id}  →  SSE GET /api/analyze/{run_id}/stream  │
│  POST /api/screen            (screener_routes.py — zero SSE coupling) │
├──────────────────────────────────────────────────────────────────────┤
│  LangGraph StateGraph  (TradingAgentsGraph)                           │
│  AgentState: TypedDict — single shared state dict                     │
│  Equity agents (parallel) + Options agents (parallel) → Risk Judge    │
│  All agents: create_* factory functions returning closures            │
├──────────────────────────────────────────────────────────────────────┤
│  Data Layer  (tradingagents/dataflows/)                               │
│  VENDOR_METHODS routing via interface.py                              │
│  yfinance (default) + Alpha Vantage + Tradier                         │
│  Screener data: direct import (no VENDOR_METHODS routing)             │
├──────────────────────────────────────────────────────────────────────┤
│  Persistence  (file-based, no database)                               │
│  analysis_history/{TICKER}/{DATE}/summary.json + full_states_log.json │
│  eval_results/{TICKER}/TradingAgentsStrategy_logs/full_states_log.json│
└──────────────────────────────────────────────────────────────────────┘
```

The existing system has no database, no external broker integration, and no charting. All four v1.2 features are purely additive — nothing in the existing graph or data layer needs to be modified.

---

## System Overview: v1.2 New Components

```
┌──────────────────────────────────────────────────────────────────────────┐
│  React Frontend                                                           │
│  ┌───────────────┐  ┌─────────────────┐  ┌────────────────────────────┐  │
│  │ Analysis tab  │  │  Screener tab   │  │  Track Record tab  [NEW]   │  │
│  │ (existing)    │  │  (existing)     │  │  dashboard + chart         │  │
│  └───────────────┘  └─────────────────┘  └────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  ChartPanel  [NEW]  — TradingView Lightweight Charts v5             │  │
│  │  Rendered inside Analysis tab (below signal banner) + Track Record  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────┤
│  FastAPI Backend                                                           │
│  ┌──────────────────────┐  ┌──────────────────────────────────────────┐   │
│  │  Existing routes     │  │  New routes  [NEW]                       │   │
│  │  /api/analyze (SSE)  │  │  GET  /api/chart/{ticker}  OHLCV data    │   │
│  │  /api/screen         │  │  POST /api/trade           execute order │   │
│  └──────────────────────┘  │  GET  /api/trades          trade log     │   │
│                             │  GET  /api/score/{ticker}  stats/score  │   │
│                             │  PATCH /api/trade/{id}     close trade  │   │
│                             └──────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────────────┤
│  New Backend Modules  [NEW]                                                │
│  ┌──────────────────┐  ┌───────────────────┐  ┌────────────────────────┐  │
│  │  chart_data.py   │  │  alpaca_trader.py  │  │  trade_store.py        │  │
│  │  yfinance OHLCV  │  │  alpaca-py SDK     │  │  SQLite via SQLModel   │  │
│  │  serialised JSON │  │  paper=True client │  │  trade record + score  │  │
│  └──────────────────┘  └───────────────────┘  └────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────┤
│  External Services  [NEW]                                                  │
│  Alpaca Paper Trading API  (paper-api.alpaca.markets)                     │
│  alpaca-py SDK: TradingClient(paper=True)                                 │
│  MarketOrderRequest / OptionOrderRequest (Level 3 auto-enabled on paper)  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries (v1.2)

| Component | New or Modified | Responsibility |
|-----------|-----------------|----------------|
| `api/trade_routes.py` | NEW | `POST /api/trade`, `GET /api/trades`, `GET /api/score/{ticker}`, `PATCH /api/trade/{id}` |
| `api/chart_routes.py` | NEW | `GET /api/chart/{ticker}` OHLCV data endpoint |
| `api/schemas.py` | MODIFIED | Add `TradeRequest`, `TradeRecord`, `ScoreResponse`, `ChartResponse`, `CloseTradeRequest` |
| `api/main.py` | MODIFIED | Register `trade_routes` and `chart_routes` routers |
| `tradingagents/broker/__init__.py` | NEW | Package init |
| `tradingagents/broker/alpaca_trader.py` | NEW | `TradingClient` wrapper, `submit_equity_order`, `submit_options_order` |
| `tradingagents/dataflows/chart_data.py` | NEW | `get_ohlcv(ticker, days)` — yfinance fetch → `list[dict]` |
| `tradingagents/store/__init__.py` | NEW | Package init |
| `tradingagents/store/trade_store.py` | NEW | SQLite CRUD for `TradeRecord`, `compute_score` |
| `frontend/src/components/ChartPanel.tsx` | NEW | TradingView Lightweight Charts React wrapper |
| `frontend/src/components/TrackRecordDashboard.tsx` | NEW | Win rate, P&L, per-ticker score table, trade history |
| `frontend/src/hooks/useTradeRecord.ts` | NEW | `POST /api/trade`, `GET /api/trades`, `PATCH /api/trade/{id}` |
| `frontend/src/hooks/useChart.ts` | NEW | `GET /api/chart/{ticker}` → drives `ChartPanel` |
| `frontend/src/App.tsx` | MODIFIED | Add `'track-record'` to `mainSection` union, render `ChartPanel` in analysis view |

### Unchanged Components (v1.2)

- `tradingagents/graph/trading_graph.py` — no changes
- `tradingagents/graph/setup.py` — no new nodes
- `tradingagents/agents/utils/agent_states.py` — no new fields
- All existing analysts, managers, options agents — no changes
- `api/routes.py` — no changes
- `api/screener_routes.py` — no changes
- `api/progress.py` — no changes

---

## Recommended Project Structure (New Files Only)

```
tradingagents/
├── broker/
│   ├── __init__.py
│   └── alpaca_trader.py        # TradingClient wrapper — paper mode
│
├── store/
│   ├── __init__.py
│   └── trade_store.py          # SQLModel ORM, SQLite, CRUD + score
│
└── dataflows/
    └── chart_data.py           # OHLCV fetch (yfinance), returns serialisable list

api/
├── chart_routes.py             # GET /api/chart/{ticker}
├── trade_routes.py             # POST /api/trade, GET /api/trades, etc.
└── schemas.py                  # [extended] TradeRequest, TradeRecord, ScoreResponse

frontend/src/
├── components/
│   ├── ChartPanel.tsx           # Lightweight Charts v5 wrapper
│   └── TrackRecordDashboard.tsx # Score table, P&L, win rate, trade history
└── hooks/
    ├── useChart.ts              # Fetch OHLCV, drive ChartPanel
    └── useTradeRecord.ts        # Submit, retrieve, close trades
```

---

## Feature 1: TradingView Chart Integration

### Pattern: Imperative DOM via useRef + useEffect

TradingView Lightweight Charts v5 is a pure-canvas library that mutates a DOM node — it does not operate as a React component. The canonical React integration uses `useRef` to hold a reference to the container div, initializes the chart in `useEffect` with an empty dependency array, and returns a cleanup function that calls `chart.remove()`.

**Why direct `lightweight-charts` over wrapper libs:** The community wrappers (kaktana, ukorvl, tradingview-tools) add a thin declarative layer but constrain v4/v5 migration paths. The official documentation provides a React tutorial that is a small setup; the wrapper overhead is not justified for a project that already manages its own state carefully. [Confidence: HIGH — official docs confirmed]

**Data flow:**

```
Analysis completes (state.result present)
    ↓
useChart(ticker) → GET /api/chart/{ticker}?days=90
    ↓
chart_data.py → yf.Ticker(ticker).history(period="3mo", interval="1d")
    ↓
[{"time": "2026-01-02", "open": 140.0, "high": 145.0,
   "low": 139.0, "close": 143.0, "volume": 12000000}, ...]
    ↓
ChartPanel.tsx → series.setData(ohlcv)
    ↓
Optional: series.setMarkers([{time, position, color, shape, text}])
```

**Integration point in App.tsx:** Render `<ChartPanel ticker={currentTicker} />` inside the analysis section after `state.result` is present. Gate on `state.status === 'complete'` so the chart does not mount during a running analysis.

**OHLCV endpoint:**
- `GET /api/chart/{ticker}?days=90`
- Returns `list[dict]` with keys: `time` (ISO date string), `open`, `high`, `low`, `close`, `volume`
- `chart_data.get_ohlcv` reuses the yfinance dependency already in `requirements.txt` — no new Python dependency

---

## Feature 2: Alpaca Paper Trading Execution

### Pattern: Service module behind a FastAPI route — not a LangGraph agent

Trade execution is a side-effect triggered by a user action after analysis completes. It must not be wired into `AgentState` or the graph. The correct placement is a standalone service module called from a FastAPI POST endpoint.

**Architecture decision:** `tradingagents/broker/alpaca_trader.py` is a plain Python module (not a LangGraph node). It instantiates `TradingClient(api_key, secret_key, paper=True)` at module import using env vars `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`.

**Order submission flow:**

```
POST /api/trade
  body: { ticker, signal, quantity, order_type, options_legs? }
    ↓
trade_routes.py resolves signal (BUY/SELL/HOLD)
    ↓ (HOLD → save record with order_id=None, return early)
alpaca_trader.submit_equity_order(ticker, side, qty)
  OR
alpaca_trader.submit_options_order(legs=[{symbol, qty, side}, ...])
    ↓
Alpaca paper-api.alpaca.markets → order response
    ↓
trade_store.save_trade(ticker, signal, order_id, executed_price, ...)
    ↓
Return TradeRecord to frontend
```

**Key constraint — options orders:** Alpaca paper accounts automatically have Level 3 strategies enabled. Multi-leg options use the same `/orders` endpoint as equities. The existing `options_legs` state field is free-text (not typed structs). The route should accept a structured `options_legs` payload from the frontend rather than parsing the free-text string server-side. The frontend constructs the structured payload from the rendered `options_legs` report if the user confirms execution. [Confidence: HIGH — Alpaca docs confirmed paper options access]

**Authentication:** Two env vars added to `.env`: `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`. Paper keys are entirely separate from live keys. The broker module reads them at import; raises `ValueError` with clear message if missing. Add to `.env.example` as empty placeholders.

**New Python dependency:** `alpaca-py` (official SDK, PyPI: `alpaca-py`). This is the only new Python dependency for v1.2.

---

## Feature 3: Recommendation Scoring System

### Pattern: SQLite trade log + computed score at query time

Scoring is the derived layer on top of raw trade records. Store raw rows, compute metrics on read.

**Data model (SQLModel + SQLite):**

```python
class TradeRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ticker: str                    # index
    trade_date: str                # ISO date — matches analysis_history key
    signal: str                    # BUY | SELL | HOLD
    order_id: str | None           # Alpaca order ID; None for HOLD
    executed_price: float | None   # fill price from Alpaca
    executed_at: str | None        # ISO datetime of fill
    outcome: str | None            # WIN | LOSS | NEUTRAL — set on close
    pnl: float | None              # realised P&L — set on close
    analysts_used: str             # comma-separated list
    enable_options: bool           # whether options pipeline was active
    created_at: str                # ISO datetime
```

**Score computation (at query time):**

```python
def compute_score(ticker: str | None = None) -> ScoreResult:
    trades = get_trades(ticker=ticker)
    closed = [t for t in trades if t.outcome is not None]
    wins = [t for t in closed if t.outcome == "WIN"]
    return ScoreResult(
        total=len(trades),
        closed=len(closed),
        win_rate=len(wins) / len(closed) if closed else None,
        total_pnl=sum(t.pnl for t in closed if t.pnl),
        by_ticker=_group_by_ticker(trades),
    )
```

**Why SQLite over JSON file scan:** The existing JSON file approach (one file per ticker/date) requires O(N) filesystem scans to aggregate across all history for a dashboard. SQLite with an index on `ticker` makes this a sub-millisecond query. SQLModel matches the existing Pydantic/FastAPI stack and is officially maintained by the FastAPI author. [Confidence: HIGH]

**Trade outcome lifecycle:**
- On analysis completion + BUY/SELL execution: `outcome=None` (order open, awaiting close)
- On manual close: frontend sends `PATCH /api/trade/{id}` with `pnl` and `outcome`; system sets `WIN|LOSS|NEUTRAL`
- On HOLD signal: record saved with `order_id=None`, `outcome="NEUTRAL"` immediately (no position opened)

**Database file location:** `tradingagents/store/trades.db` (relative to project root). Add to `.gitignore`.

---

## Feature 4: Track Record Dashboard

### Pattern: Third top-level section in App.tsx, polling GET endpoints

The track record dashboard is read-heavy UI. It becomes a third entry in the `mainSection` state alongside `'analysis'` and `'screener'`. No SSE needed — GET on mount plus a refresh button is sufficient for a single-user tool.

**Component structure:**

```
TrackRecordDashboard
├── ScoreSummaryCard         — total trades, win rate, total P&L
├── PerTickerScoreTable      — ticker | trades | wins | win% | P&L
├── TradeHistoryTable        — date | ticker | signal | status | P&L | close btn
└── ChartPanel (embedded)   — price chart for the selected ticker row,
                               with markers at trade dates
```

**Data flow:**

```
User opens Track Record tab
    ↓
GET /api/score          → ScoreResult (summary + per-ticker breakdown)
GET /api/trades         → TradeRecord[] (latest 50, paginated if needed)
    ↓
TrackRecordDashboard renders summary + table
    ↓
User clicks a ticker row
    ↓
GET /api/chart/{ticker} → OHLCV[]
ChartPanel renders with trade-date markers (BUY=up arrow green, SELL=down arrow red)
```

**Chart trade markers:** Lightweight Charts v5 `series.setMarkers([{time, position, color, shape, text}])`. `TradeRecord.trade_date` maps directly to the `time` field (ISO date string). `signal` maps to `position: 'belowBar'` (BUY) or `'aboveBar'` (SELL) and color.

---

## Data Flow Summary: All New Request Flows

```
1. Chart Render Flow
   Analysis complete → user sees signal banner
       ↓
   useChart(ticker) → GET /api/chart/{ticker}?days=90
       ↓
   FastAPI → chart_data.get_ohlcv(ticker, 90) → yfinance
       ↓
   OHLCV JSON → ChartPanel.setData() → canvas render

2. Paper Trade Execution Flow
   User clicks "Execute Paper Trade"
       ↓
   useTradeRecord.submit({ ticker, signal, qty })
   → POST /api/trade
       ↓
   trade_routes.py → alpaca_trader.submit_equity_order()
   → Alpaca paper-api.alpaca.markets
       ↓
   order response → trade_store.save_trade() → SQLite
       ↓
   TradeRecord returned → frontend shows confirmation

3. Close Trade Flow
   User clicks "Close" on a TradeHistoryTable row
       ↓
   PATCH /api/trade/{id}  { pnl: 150.00, outcome: "WIN" }
       ↓
   trade_store.update_trade(id, pnl, outcome) → SQLite
       ↓
   Updated TradeRecord → frontend re-renders row

4. Track Record Fetch Flow
   User opens Track Record tab
       ↓
   GET /api/score → compute_score() reads SQLite
   GET /api/trades → paginated TradeRecord[]
       ↓
   Dashboard renders win rate, P&L, history table
```

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Alpaca Paper API | `alpaca-py` SDK, `TradingClient(paper=True)`, env vars `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` | Paper base URL: `https://paper-api.alpaca.markets`. Paper keys are separate from live keys. Options orders use the same `/orders` endpoint; Level 3 is automatic on paper accounts. [Confidence: HIGH] |
| TradingView Lightweight Charts | npm package `lightweight-charts` v5.x, imperative DOM API via `useRef`/`useEffect` | No React wrapper library. Each `ChartPanel` instance creates and destroys its own chart via `useEffect` cleanup. Pin to `^5`. [Confidence: HIGH] |
| yfinance (existing) | Already in Python deps — reused in `chart_data.py` for OHLCV endpoint | No new data dependency. `Ticker.history()` returns DataFrame; serialise to `list[dict]` for JSON response. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| LangGraph graph ↔ broker module | No coupling at all. Broker is called only from `trade_routes.py` on explicit user action after graph completes. | Never add broker calls inside `AgentState` reducers. The graph must remain a pure analysis pipeline. |
| `trade_store.py` ↔ `analysis_history/` | Shared natural key `(ticker, trade_date)`. Trade records may reference `analysis_history` paths for deep-link UI but do NOT read those files for score computation. | Score is computed solely from SQLite. Do not reintroduce filesystem scans into the score path. |
| `chart_data.py` ↔ existing data layer | `chart_data.py` imports yfinance directly (same as `screener_data.py` pattern — direct import, not `VENDOR_METHODS`). Chart data is display-only, not agent input. | Extend `VENDOR_METHODS` routing only if multi-vendor chart data becomes a requirement. |
| `trade_routes.py` ↔ `screener_routes.py` ↔ `routes.py` | Independent `APIRouter` instances, all registered in `main.py`. Follow the established pattern. | Zero coupling between routers. SSE analysis stream remains fully isolated. |
| Frontend `mainSection` ↔ new tab | Add `'track-record'` to the `mainSection` type union in `App.tsx`. One string controls all three section renders. | No new routing library (react-router) needed for three tabs. |

---

## Architectural Patterns (v1.2)

### Pattern 1: Route-per-feature isolation

**What:** Each new feature gets its own `APIRouter` file (`chart_routes.py`, `trade_routes.py`), registered in `main.py`.
**When to use:** When a new feature has no shared request state with existing routes.
**Trade-offs:** Minor duplication (each file imports FastAPI, schemas), but zero coupling between features — proven correct by the existing analysis/screener separation. The cost is worth it.

### Pattern 2: Service module behind route (not a LangGraph node)

**What:** Side-effect services (Alpaca execution, SQLite writes) live in `tradingagents/broker/` and `tradingagents/store/`, called from routes — never wired into `AgentState`.
**When to use:** Any operation that is user-triggered post-analysis, not part of the AI reasoning chain.
**Trade-offs:** One level of indirection more than inline route code, but the graph remains deterministic and testable without network I/O side effects.

### Pattern 3: Compute-on-read scoring

**What:** Raw `TradeRecord` rows are stored; win rate, P&L totals, and per-ticker breakdowns are computed by reading the SQLite table at query time — not stored as denormalised columns.
**When to use:** When the volume is small (hundreds to low thousands of trades) and the derived metrics are cheap to recompute.
**Trade-offs:** Slight CPU cost per score request; avoids double-write synchronisation bugs. At >1k trades, precompute a daily summary if latency becomes noticeable.

### Pattern 4: Chart markers for trade history overlay

**What:** Lightweight Charts `series.setMarkers([])` overlays BUY/SELL signals on the OHLCV chart. Trade records supply the `time` (ISO date) and `signal` (BUY/SELL) needed to build marker objects.
**When to use:** Whenever "where did we trade" on a price chart is needed.
**Trade-offs:** Markers must be sorted ascending by time. `TradeRecord.trade_date` is already an ISO date string, which Lightweight Charts accepts directly.

---

## Anti-Patterns (v1.2)

### Anti-Pattern 1: Wiring broker execution into AgentState

**What people do:** Add an `alpaca_execution` LangGraph node that submits the order after `final_trade_decision`.
**Why bad:** The graph becomes non-deterministic (network I/O inside graph). Alpaca failures abort the entire analysis run. Graph replay is impossible. Testing the graph requires mocking an external broker.
**Do this instead:** Keep the graph pure — analysis only. Execution is a user-confirmed side-effect via `POST /api/trade` after graph completion.

### Anti-Pattern 2: Scanning `analysis_history/` for score computation

**What people do:** Walk `analysis_history/{TICKER}/{DATE}/summary.json` to build the track record table.
**Why bad:** O(N) filesystem scans that grow linearly with history depth. No schema validation. Fragile to directory structure changes. Makes the dashboard slow after a month of daily use.
**Do this instead:** Write to SQLite on every trade execution. `analysis_history/` is for full report browsing; SQLite is for aggregated metrics.

### Anti-Pattern 3: Global TradingView chart instance

**What people do:** Instantiate `createChart()` outside a React component as a module-level singleton to "avoid re-creation".
**Why bad:** Two `ChartPanel` instances (Analysis tab + Track Record tab) cannot share an instance — the chart is bound to a specific DOM node. Module-level state breaks React's rendering contract.
**Do this instead:** Each `ChartPanel` creates and destroys its own instance in `useEffect`. Pass ticker and data as props. React StrictMode double-invocation is handled correctly by the cleanup function.

### Anti-Pattern 4: Storing Alpaca credentials in committed files

**What people do:** Hard-code paper API keys in `.env` and commit the file, or store them in `default_config.py`.
**Why bad:** Paper keys are financially harmless but training bad habits for when live keys exist. Any committed secret is a pipeline risk.
**Do this instead:** Add `ALPACA_API_KEY=` and `ALPACA_SECRET_KEY=` as empty placeholders in `.env.example`. The existing `.gitignore` already excludes `.env`. The broker module raises a clear `ValueError` at startup if keys are absent.

---

## Build Order — v1.2 (Dependency-Aware)

Feature dependency graph:

```
chart_data.py + chart_routes.py     (no deps on other new features)
    ↓
ChartPanel.tsx                       (depends on chart API endpoint)
    ↓ (reused by)
TrackRecordDashboard.tsx             (depends on chart + trade data)

trade_store.py (SQLite schema)       (no deps on other new features)
    ↓
alpaca_trader.py                     (independent of store; route uses both)
    ↓ combined in
trade_routes.py                      (depends on store + broker)
    ↓
useTradeRecord.ts                    (depends on trade API)
    ↓
TrackRecordDashboard.tsx             (depends on trade data + chart)
```

**Recommended build sequence:**

**Step 1 — Chart endpoint + ChartPanel**
- `tradingagents/dataflows/chart_data.py` — `get_ohlcv(ticker, days) -> list[dict]`
- `api/chart_routes.py` — `GET /api/chart/{ticker}`
- `api/schemas.py` — add `ChartResponse`
- `api/main.py` — register `chart_routes`
- `frontend/src/hooks/useChart.ts`
- `frontend/src/components/ChartPanel.tsx`
- `App.tsx` — render `<ChartPanel>` in analysis view on completion

Gate: chart renders for a completed analysis run. OHLCV data shows correct price history.

**Step 2 — SQLite trade store (foundation)**
- `tradingagents/store/trade_store.py` — `TradeRecord` SQLModel, `save_trade`, `get_trades`, `update_trade`, `compute_score`
- Add `trades.db` to `.gitignore`

Gate: unit tests for CRUD and score computation with in-memory SQLite.

**Step 3 — Alpaca broker + trade execution**
- Add `alpaca-py` to `requirements.txt` / `pyproject.toml`
- `tradingagents/broker/alpaca_trader.py` — `submit_equity_order`, `submit_options_order`
- `api/trade_routes.py` — `POST /api/trade`, `GET /api/trades`, `GET /api/score/{ticker}`, `PATCH /api/trade/{id}`
- `api/schemas.py` — add `TradeRequest`, `TradeRecord`, `ScoreResponse`, `CloseTradeRequest`
- `api/main.py` — register `trade_routes`
- `.env.example` — add `ALPACA_API_KEY=` and `ALPACA_SECRET_KEY=`
- `frontend/src/hooks/useTradeRecord.ts`

Gate: paper trade executes against Alpaca sandbox. Order ID returned. Record persists in SQLite.

**Step 4 — Track Record Dashboard**
- `frontend/src/components/TrackRecordDashboard.tsx`
- `App.tsx` — add `'track-record'` to `mainSection`, render dashboard

Gate: track record tab shows win rate, P&L, history table. Clicking a row shows chart with trade markers.

---

## Scalability Considerations (v1.2)

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-500 trades | SQLite default config. No index tuning needed. Compute-on-read score. |
| 500-5k trades | Add index on `(ticker, trade_date)`. Score query remains fast. No schema changes. |
| 5k+ trades | Precompute daily summary in a background task or on-demand cache. Still SQLite — upgrading to Postgres is a one-line SQLAlchemy URL change via SQLModel. |
| Multi-user | Not a v1.2 concern. Current architecture is single-user. If needed: per-user SQLite files or Postgres + user_id column. |

This system will realistically stay below 500 trades through v1.2. SQLite is the right call.

---

## Sources

**v1.2 sources:**
- Codebase direct inspection: `api/routes.py`, `api/schemas.py`, `api/main.py`, `tradingagents/graph/trading_graph.py`, `tradingagents/agents/utils/agent_states.py`, `tradingagents/graph/setup.py`, `analysis_history/NVDA/2026-04-02/summary.json` — HIGH confidence
- [TradingView Lightweight Charts React tutorial (official)](https://tradingview.github.io/lightweight-charts/tutorials/react/simple) — MEDIUM confidence (WebSearch confirmed, not directly fetched)
- [Lightweight Charts GitHub (v5)](https://github.com/tradingview/lightweight-charts) — HIGH confidence (canonical source)
- [Alpaca paper trading docs](https://docs.alpaca.markets/docs/paper-trading) — HIGH confidence (WebSearch confirmed behavior)
- [alpaca-py SDK GitHub](https://github.com/alpacahq/alpaca-py) — HIGH confidence (official SDK)
- [Alpaca options trading docs (paper Level 3 auto-enabled)](https://docs.alpaca.markets/docs/options-trading) — HIGH confidence
- [FastAPI SQL databases tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/) — HIGH confidence (official FastAPI docs)

**v1.1 sources:**
- Architecture decisions derived from direct codebase analysis. All findings are HIGH confidence.

---

*Architecture research for: agents-for-trades v1.1 (screener) + v1.2 (paper trading & validation)*
*Researched: 2026-04-03*
