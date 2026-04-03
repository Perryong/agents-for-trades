# Project Research Summary

**Project:** TradingAgents — v1.2 Paper Trading & Validation
**Domain:** AI multi-agent trading framework — paper execution, interactive charting, recommendation scoring, track record dashboard
**Researched:** 2026-04-03
**Confidence:** HIGH

---

## Executive Summary

v1.2 is a pure additive milestone that bolts four capabilities onto a shipping system: TradingView candlestick charts, Alpaca paper trade execution, recommendation scoring, and a track record dashboard. The existing stack (FastAPI, LangGraph, React 19, Tailwind v4, yfinance, Tradier) is unchanged. Four new packages cover the entire delta: `lightweight-charts ^5.1.0` (frontend), `alpaca-py ^0.43.2`, `sqlalchemy ^2.0.48`, and `aiosqlite ^0.22.1` (backend). All four are version-confirmed against their package registries, have official documentation for the integration patterns required, and introduce zero conflicts with existing peer dependencies.

The recommended build order flows from lowest to highest coupling: charts first (pure frontend, uses data already in the yfinance pipeline), then Alpaca paper execution (the gateway feature that makes trade records possible), then scoring (pure Python aggregation once trade records exist), then the track record dashboard (consumes scoring and chart data). Each stage is independently testable and delivers visible value before the next one begins. The LangGraph graph, AgentState, all existing agents, and existing API routes are untouched throughout.

The primary risks are not technical complexity — the libraries are mature and the patterns are established — but correctness of the feedback loop. Win rate displayed alone is actively misleading; the scoring schema must be defined before any code is written; paper fills have no slippage and will systematically overstate real-world edge. These are design-time decisions that cannot be retrofitted once the dashboard is in production. The second risk cluster is async correctness: the FastAPI event loop is already in production with SSE streaming, and any blocking synchronous Alpaca SDK call inside an `async def` handler will stall SSE delivery visibly.

---

## Key Findings

### Recommended Stack

The existing stack handles everything except chart rendering, broker execution, and persistence. The four new packages solve exactly those gaps. `lightweight-charts v5` is the correct charting choice: MIT license, 35kB gzipped, Canvas-based (no SVG performance cliff with trade history datasets), no React peer-dependency coupling, and an official TradingView documentation tutorial covering the exact React `useRef + useEffect` integration pattern needed. All community wrappers (kaktana, ukorvl) lag behind the v5 API breaking changes and must be rejected.

`alpaca-py` (not the deprecated `alpaca-trade-api`) is the only correct Alpaca SDK. Paper mode is a single constructor flag: `TradingClient(paper=True)`. Level 3 options (spreads, straddles, iron condors) are enabled by default in paper accounts with no approval process or KYC required. SQLAlchemy 2.0 async with `aiosqlite` matches the existing FastAPI async event loop and is upgradeable to PostgreSQL by changing only the connection string when and if needed — the ORM layer provides the abstraction.

**Core new technologies:**
- `lightweight-charts ^5.1.0`: Financial candlestick + volume + marker charts — purpose-built Canvas library; v5 API is a hard breaking change from v4; must use only the official v5 patterns
- `alpaca-py ^0.43.2`: Paper trade execution (equity + multi-leg options) — `TradingClient(paper=True)` routes all calls to the paper sandbox automatically; no URL configuration needed
- `sqlalchemy ^2.0.48` + `aiosqlite ^0.22.1`: Async SQLite persistence for trade records, scoring results, and paper order state — zero infrastructure, ORM abstraction allows future database upgrade by changing only the connection string

**Explicitly rejected (do not add):**
- Recharts / Chart.js / Victory: React 19 peer-dependency conflicts and SVG rendering performance issues with trade history datasets
- Community lightweight-charts wrappers: all target v3/v4, unmaintained against the v5 API
- Alembic: premature for a new schema with no existing data; `create_all()` on startup is sufficient
- Redis / Celery: no queue or cache infrastructure needed at paper trading order volumes
- `backtrader`: explicitly deferred to v1.3+ per PROJECT.md; must not be wired in during v1.2
- `alpaca-trade-api` (legacy): officially deprecated; use `alpaca-py` only

### Expected Features

**Must have (table stakes):**
- TradingView candlestick + volume bars — users orient visually before reading agent reports; absence registers as a regression from professional tool expectations
- Alpaca paper order submission (equity) — core v1.2 requirement; without execution capability the milestone delivers no value
- Order status display (submitted / filled / rejected) — silent execution is untrustworthy and makes the track record unreliable
- Recommendation scoring with win rate + expectancy + profit factor — win rate alone is actively misleading and must never be the only displayed metric
- Track record dashboard with summary stats + trade history table — the minimum answer to "how is this system doing?"

**Should have (differentiators):**
- Paper trade markers on price chart (fill price annotated as chart overlay) — closes the execution-to-visualization loop visually
- Equity curve chart in track record (running P&L over time) — shows whether system is improving over the live paper period
- Per-ticker breakdown in track record — identifies familiar vs unfamiliar ticker performance patterns
- Multi-timeframe toggle on chart (daily / weekly / monthly) — traders make decisions across timeframes
- Trade outcome auto-close via Alpaca positions API after N trading days

**Defer to follow-up or v1.3+:**
- Options multi-leg paper order via Alpaca (translation layer from `OptionsLegsBuilderReport` to Alpaca legs array is high complexity; tackle after equity order lifecycle is stable and proven)
- Per-agent accuracy scoring (requires structured individual agent votes; partially available in existing reports but not fully typed)
- Confidence-calibration view (requires matching confidence scores against outcomes over time — meaningful only after several months of paper history)
- Custom backtesting engine (explicitly v1.3+ per PROJECT.md)
- Portfolio rebalancing / dynamic position sizing engine

### Architecture Approach

v1.2 adds three new backend modules and two new React component areas, all purely additive. Zero changes are made to the existing LangGraph graph, `AgentState` TypedDict, agent factory functions, or existing API routes. The execution layer (`tradingagents/broker/alpaca_trader.py`) is a plain Python service module called from a FastAPI POST endpoint — not a LangGraph node. Persistence uses SQLAlchemy 2.0 async with a session-injected `get_db()` dependency following the FastAPI canonical pattern. The chart data endpoint routes through the existing `VENDOR_METHODS` abstraction in `interface.py` rather than calling yfinance directly, preserving vendor swap capability for the whole system.

**Major components:**
1. `tradingagents/broker/alpaca_trader.py` — `TradingClient(paper=True)` wrapper; `submit_equity_order` and `submit_options_order` methods; all synchronous SDK calls wrapped with `asyncio.to_thread()` to protect the event loop
2. `tradingagents/store/trade_store.py` — SQLAlchemy ORM `TradeRecord` model; CRUD operations plus `compute_score()` calculated at read time; SQLite via `aiosqlite`
3. `tradingagents/dataflows/chart_data.py` — `get_ohlcv(ticker, days)` via `VENDOR_METHODS` routing; returns a JSON-serializable list for `ChartPanel`
4. `api/trade_routes.py` + `api/chart_routes.py` — new FastAPI `APIRouter` instances following the `api/screener_routes.py` pattern; endpoints: `POST /api/trade`, `GET /api/trades`, `GET /api/score/{ticker}`, `PATCH /api/trade/{id}`, `GET /api/chart/{ticker}`
5. `frontend/src/components/ChartPanel.tsx` — `useRef + useEffect + chart.remove()` cleanup pattern; `chart.addSeries(CandlestickSeries, options)` v5 API; conditional render gated on `status === 'complete'`
6. `frontend/src/components/TrackRecordDashboard.tsx` — new "Track Record" tab in `App.tsx`; win rate + expectancy + profit factor stats cards + trade history table + equity curve line chart; persistent slippage disclaimers

**Key patterns inherited from existing codebase:**
- All new API routers follow the `api/screener_routes.py` model (APIRouter, Pydantic schemas, no SSE coupling)
- Async SDK calls use `asyncio.to_thread()` — same as the screener endpoint
- No new `AgentState` fields; no new LangGraph nodes; no SSE for new endpoints

**Unchanged components (do not touch):**
- `tradingagents/graph/trading_graph.py`, `graph/setup.py`, `agents/utils/agent_states.py`
- All existing analysts, managers, and options agents
- `api/routes.py`, `api/screener_routes.py`, `api/progress.py`

### Critical Pitfalls

1. **lightweight-charts v5 API incompatibility with v4 tutorials** — The v5 series creation API is a hard breaking change: `addLineSeries()` does not exist in v5; it is replaced by `chart.addSeries(CandlestickSeries, options)`. Most tutorials indexed by search engines target v3 or v4. React StrictMode (enabled by default in Vite projects) double-invokes `useEffect`; without a `chart.remove()` cleanup function, two chart instances mount silently and produce memory leaks. Fix: use only the official TradingView v5 React tutorial; always return `chart.remove()` in `useEffect` cleanup; never use community wrapper libraries.

2. **Alpaca paper vs. live API key and URL mismatch** — Paper keys require `paper=True` in the `TradingClient` constructor, which routes calls to the paper base URL automatically. Using live keys in paper mode (or vice versa) produces generic 401/403 errors that look like account configuration problems. Fix: always pass `paper=True` explicitly; name env vars `ALPACA_PAPER_KEY` / `ALPACA_PAPER_SECRET` (never an ambiguous `ALPACA_KEY`); add a startup assertion that rejects configuration where paper mode is active but the base URL does not contain `paper-api`.

3. **Blocking synchronous Alpaca SDK calls inside async FastAPI routes** — `alpaca-py` `TradingClient` methods (`submit_order`, `get_order`, `get_all_positions`) are synchronous. Calling them directly inside `async def` handlers blocks the event loop for 100-500ms per call. During that block, SSE events cannot be dispatched and the analysis progress stepper freezes visibly. Fix: wrap every SDK call with `asyncio.to_thread()`. Validate under concurrent load by opening two browser tabs running analysis simultaneously and confirming SSE delivery does not stall when an order is submitted in one tab.

4. **Win rate as the standalone headline metric** — Win rate without average winner and loser sizes and expectancy is actively misleading: 67% win rate with 0.5:1 risk-reward loses money; 40% win rate with 3:1 risk-reward makes money. Fix: display win rate, average winner, average loser, profit factor, and expectancy together; never win rate alone. Design the scoring schema to capture `price_at_decision`, `recommended_target_price`, `recommended_stop_price`, and `target_horizon_days` before any scoring code is written.

5. **Trade log schema insufficient for scoring** — Existing `analysis_history/` JSON logs record decisions but not the fields needed to measure outcome quality. Retrofitting historical records is destructive and introduces price data inaccuracies. Fix: define the v1.2 schema with a `schema_version` field before implementation begins; v1.2 records go into SQLite (separate from the old JSON files); pre-v1.2 logs are available in the history view but excluded from quantitative metrics; set the track record start date to the v1.2 deployment date.

---

## Implications for Roadmap

### Phase 1: TradingView Chart Integration

**Rationale:** Zero broker dependency; OHLCV data already exists in the yfinance pipeline; delivers immediate visible value without any execution infrastructure; validates the lightweight-charts v5 React integration pattern before any other feature depends on it.
**Delivers:** `ChartPanel.tsx` with candlestick + volume bars; `GET /api/chart/{ticker}` OHLCV endpoint via `VENDOR_METHODS` routing; `useChart.ts` hook; chart renders below the signal banner on analysis completion; foundation for paper trade marker overlay in Phase 2.
**Addresses:** Table-stakes features — candlestick view, volume bars.
**Avoids:** Pitfall 1 (v5 API incompatibility) by establishing the correct React pattern in isolation first; Pitfall 12 (data vendor divergence) by routing through `interface.py` rather than calling yfinance directly in the chart endpoint.
**Research flag:** Standard — official TradingView v5 React tutorial is authoritative and complete. No additional research needed.

### Phase 2: Alpaca Paper Trading Execution

**Rationale:** Gateway feature for the entire milestone. Trade records in the database are the prerequisite for Phases 3 and 4. The order lifecycle (submitted → filled → rejected → closed) must be proven end-to-end before any feature that reads fill prices is built.
**Delivers:** `alpaca_trader.py` broker module; `trade_routes.py` with `POST /api/trade`; SQLite schema (`TradeRecord` model with `order_id`, `executed_price`, `outcome`, `pnl` fields); `ALPACA_PAPER_KEY` / `ALPACA_PAPER_SECRET` env vars; order status polling loop (5s interval, 12 iterations, `timeout` state if not filled); "Execute Paper Trade" confirmation button in the Analysis tab; chart trade markers once fill price is available.
**Addresses:** Equity paper order submission (table stakes); order status display (table stakes); paper trade chart markers (differentiator).
**Avoids:** Pitfall 2 (key/URL mismatch) via explicit `paper=True` and startup assertion; Pitfall 3 (options multi-leg — scope to equity-only for Phase 2 MVP); Pitfall 4 (event loop blocking) via `asyncio.to_thread()`; Pitfall 9 (stale "pending" orders) via the polling loop and explicit order state machine.
**Research flag:** Standard for equity orders. Options multi-leg should be validated against a scratch paper account before implementation (Pitfall 3 documents gaps in Alpaca bracket order support for options); scope options execution as a sub-phase contingent on that validation.

### Phase 3: Recommendation Scoring System

**Rationale:** Pure Python aggregation once `TradeRecord` rows exist. No new infrastructure. The schema must be locked in Phase 2 before any scoring metric is displayed. Deferred outcome evaluation (N-trading-day scoring trigger) is an architectural decision that must be made before implementation.
**Delivers:** `compute_score()` in `trade_store.py` returning win rate + expectancy + profit factor + average winner + average loser; `GET /api/score/{ticker}` and `GET /api/score` aggregate endpoints; `PATCH /api/trade/{id}` close-trade endpoint; deferred evaluation mechanism (pending vs. scored states); `scoring_results` table in SQLite.
**Addresses:** Win rate calculation (table stakes); per-ticker breakdown (differentiator); outcome auto-close (differentiator).
**Avoids:** Pitfall 5 (win rate alone) — expose the full metric suite from day one, never win rate as a standalone headline; Pitfall 7 (schema insufficiency) — schema locked in Phase 2 before any scoring reads exist; Pitfall 11 (confidence score as proxy for outcome) — scoring requires deferred evaluation, not same-day calculation against the AI's stated confidence.
**Research flag:** No additional research needed. All metrics (Sharpe ratio, profit factor, expectancy) are expressible with pandas already in requirements and Python stdlib.

### Phase 4: Track Record Dashboard

**Rationale:** Consumes Phase 2 trade records and Phase 3 score metrics. Final integration phase that makes the system's self-evaluation visible. All data dependencies are satisfied by this point.
**Delivers:** New "Track Record" tab in `App.tsx`; `TrackRecordDashboard.tsx` with stats cards + trade history table + equity curve line chart (reusing Phase 1 lightweight-charts setup as a line series); persistent disclaimer about simulated performance and assumed position sizing; configurable fixed-dollar position size displayed explicitly; separate equity vs. options performance views.
**Addresses:** Track record summary stats (table stakes); trade history table (table stakes); equity curve chart (differentiator); per-ticker and equity/options split views (differentiators).
**Avoids:** Pitfall 6 (paper fill overstatement) — persistent dashboard disclaimer; Pitfall 10 (relative returns without position sizing) — configurable fixed-dollar assumed position displayed in the UI; Pitfall 15 (mixing equity and options metrics) — separate views for each asset class with appropriate metrics per category.
**Research flag:** Standard. React tab + table + stats card patterns are established in the existing codebase. Equity curve reuses Phase 1 chart setup (line series instead of candlestick).

### Phase Ordering Rationale

- **Phase 1 before Phase 2:** Charts have zero broker dependency and validate the most likely technical pitfall (v5 API incompatibility) in isolation. Establishing the chart component first reduces the blast radius of v5 integration mistakes.
- **Phase 2 before Phase 3:** Scoring requires fill prices from confirmed Alpaca paper fills stored in the database. There are no meaningful records to score until at least one trade is executed and closed.
- **Phase 3 before Phase 4:** The dashboard is a read layer on top of scored trade records. Building the dashboard before the scoring schema is locked risks displaying the wrong metrics in ways that are difficult to reverse once users have seen them.
- **Equity orders before options multi-leg:** Options multi-leg translation (from `OptionsLegsBuilderReport` to Alpaca `legs` array with OCC-format symbols) is the highest-complexity item in the milestone. Establishing the full equity order lifecycle first means the options path inherits a proven end-to-end flow with known failure modes.

### Research Flags

Phases needing deeper investigation during planning:

- **Phase 2 (options multi-leg sub-scope):** Alpaca's support for bracket orders and certain complex order types on options contracts has documented gaps in the paper environment (PITFALLS.md Pitfall 3). Before committing to options multi-leg execution scope, validate with a test order against a scratch paper account. If gaps persist, options execution remains out of scope for v1.2.
- **Phase 3 (deferred outcome evaluation mechanism):** The N-trading-day scoring trigger requires a deferred evaluation step. No background job infrastructure currently exists in the project. The mechanism must be chosen during Phase 3 planning: (a) manual "close trade" button in the dashboard UI, (b) Alpaca positions API polled on dashboard load to compute unrealized P&L, or (c) a lightweight APScheduler background task. This is a required architecture decision before any scoring code is written.

Phases with standard patterns (skip additional research):

- **Phase 1 (charts):** Official TradingView v5 React tutorial is authoritative and directly applicable. No research phase needed.
- **Phase 3 (score metrics):** Standard trading performance metrics are expressible with pandas (existing dependency) and Python stdlib. No library research needed.
- **Phase 4 (dashboard):** React tab, table, and stats card patterns are already present in the codebase. Equity curve chart reuses Phase 1 chart setup. No research phase needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions confirmed against npm and PyPI; official documentation covers all integration patterns; rejection rationale for alternatives is grounded in confirmed issues (Recharts GitHub #4558, alpaca-trade-api deprecation notice) |
| Features | HIGH | Feature priority derived from user expectation analysis, existing pipeline capability assessment, and explicit Alpaca API documentation confirming paper Level 3 options access |
| Architecture | HIGH | Based on direct codebase inspection plus verified external API docs; component boundaries explicitly matched to existing patterns; invariants confirmed by reading source files |
| Pitfalls | HIGH (Alpaca/charting) / MEDIUM (scoring methodology) | Alpaca and lightweight-charts pitfalls sourced from official changelogs and confirmed GitHub issues; scoring pitfalls are domain knowledge with community consensus across multiple sources |

**Overall confidence:** HIGH

### Gaps to Address

- **Options multi-leg paper order scope:** Alpaca docs confirm Level 3 paper support exists, but community reports document gaps in complex order type support for options in the paper environment. Validate with a test order before committing to options execution scope in Phase 2. If gaps persist, options execution stays out of v1.2 scope.

- **Deferred outcome evaluation mechanism:** The scoring system requires marking trades as `pending_outcome` and evaluating them after N trading days. No background job infrastructure currently exists in the project. This mechanism must be chosen during Phase 3 planning before any scoring code is written. The three candidate approaches (manual trigger, Alpaca positions API on dashboard load, APScheduler background task) each have different tradeoffs that need a deliberate decision.

- **Historical log compatibility for track record display:** Pre-v1.2 `analysis_history/` JSON files will not have the fields needed for quantitative scoring. The dashboard must handle this gracefully — show historical records in the trade history view but exclude them from quantitative metrics. This UI design decision should be confirmed before Phase 4 implementation begins to avoid a retroactive schema conflict.

---

## Sources

### Primary (HIGH confidence)
- `https://www.npmjs.com/package/lightweight-charts` — v5.1.0 confirmed as latest
- `https://tradingview.github.io/lightweight-charts/tutorials/react/simple` — official v5 React integration pattern (`useRef + useEffect + chart.remove()`)
- `https://tradingview.github.io/lightweight-charts/tutorials/react/advanced` — multi-component chart pattern
- `https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5` — v5 breaking changes (series API revamp, CommonJS dropped)
- `https://pypi.org/project/alpaca-py/` — v0.43.2 confirmed
- `https://docs.alpaca.markets/docs/paper-trading` — paper trading official documentation
- `https://docs.alpaca.markets/changelog/multi-leg-level-3-options-trading-in-paper` — Level 3 paper options confirmed enabled by default
- `https://github.com/alpacahq/alpaca-py/blob/master/examples/options-trading-mleg.ipynb` — mleg order format with OCC symbols
- `https://www.sqlalchemy.org/changelog/CHANGES_2_0_44` — SQLAlchemy 2.0 series stable, Mar 2026 release confirmed
- `https://pypi.org/project/aiosqlite/` — v0.22.1 confirmed Dec 2025
- `https://fastapi.tiangolo.com/tutorial/sql-databases/` — async SQLAlchemy + FastAPI `Depends()` pattern
- Direct codebase inspection — existing invariants, component patterns, `AgentState` structure, `VENDOR_METHODS` routing, SSE streaming machinery

### Secondary (MEDIUM confidence)
- `https://github.com/recharts/recharts/issues/4558` — Recharts React 19 peer-dep conflict (community-reported, confirmed via issue thread)
- `https://www.babypips.com/trading/trading-performance-metrics` — trading performance metric definitions
- `https://www.luxalgo.com/blog/top-5-metrics-for-evaluating-trading-strategies/` — expectancy, profit factor, Sharpe definitions
- `https://tradefundrr.com/trading-performance-tracking/` — track record dashboard design patterns
- `https://alpaca.markets/sdks/python/trading.html` — alpaca-py SDK trading reference and order classes
- `https://dev.to/tradehorde/we-built-an-ai-trading-tool-that-actually-keeps-score-53ap` — AI trading tool track record UX patterns

### Tertiary (LOW confidence — validate before implementing)
- Community forum reports on Alpaca options bracket order gaps in the paper environment — validate with a live test order before committing options multi-leg execution to Phase 2 scope

---

*Research completed: 2026-04-03*
*Ready for roadmap: yes*
