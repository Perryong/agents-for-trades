# Technology Stack — v1.2 Paper Trading & Validation

**Project:** TradingAgents — Options Extension
**Milestone:** v1.2 Paper Trading & Validation
**Researched:** 2026-04-03
**Scope:** NEW additions only. Existing stack (Python, LangGraph, LangChain, FastAPI, React 19, TypeScript, Vite 8, Tailwind v4, pandas, yfinance, Tradier) is validated and unchanged.

---

## Context: What Already Exists (Do Not Re-add)

| Concern | Existing | Notes |
|---------|----------|-------|
| HTTP framework | FastAPI, SSE streaming | All new endpoints follow `api/screener_routes.py` pattern |
| Data | yfinance, Tradier, pandas | OHLC data for charts available from existing yfinance layer |
| Frontend | React 19, TypeScript, Tailwind v4, Vite 8 | No peer-dep changes allowed |
| LLM | LangChain multi-provider | Scoring system is pure Python math, no LLM calls |
| Caching | In-process dict with TTL | Sufficient for chart data; no new cache infra |

---

## New Stack Additions

### 1. Frontend: TradingView Lightweight Charts

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| lightweight-charts | ^5.1.0 | Candlestick/OHLC price history; equity curve line chart in track record dashboard | Official TradingView library. Canvas-based (not SVG) — handles 10k+ data points without perf degradation. 35kB gzipped. No React peer dependency — imperative DOM API means zero React version coupling. |

**Integration pattern — use the vanilla imperative API directly:**

```tsx
// frontend/src/components/PriceChart.tsx
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';
import { useRef, useEffect } from 'react';

export function PriceChart({ data }: { data: OHLCBar[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, { width: 800, height: 400 });
    const series = chart.addCandlestickSeries();
    series.setData(data);
    chartRef.current = chart;
    return () => chart.remove();  // cleanup
  }, []);

  // Update series on data change without recreating chart
  useEffect(() => {
    // call series.setData(data) on chartRef
  }, [data]);

  return <div ref={containerRef} />;
}
```

This is the TradingView-documented pattern. No third-party wrapper library is needed or recommended.

**Why not a wrapper library (kaktana, ukorvl, lightweight-charts-react-components):**
All community wrappers lag behind v5 API. The v5 release completely revamped the series creation API (breaking change from v4). Using wrappers introduces a maintenance lag between v5 features and wrapper adoption. The imperative pattern is 20 lines and requires no additional package.

**Why not Recharts:**
Recharts 3.x requires `--legacy-peer-deps` with React 19 (known GitHub issue #4558, peer dep on `react-is`). SVG-based rendering degrades with trade history datasets. Recharts is general-purpose; lightweight-charts is purpose-built for financial time-series.

**Why not react-stockcharts:**
Abandoned — last commit 2019, D3 v4 dependency, no maintenance.

---

### 2. Backend: Alpaca Paper Trading

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| alpaca-py | ^0.43.2 | Submit paper orders (equity + multi-leg options), poll positions and account state | Official Alpaca Python SDK. Replaces the deprecated `alpaca-trade-api` package. `TradingClient(paper=True)` routes all calls to the paper sandbox automatically. |

**Confirmed capabilities (paper environment):**
- `TradingClient('api-key', 'secret-key', paper=True)` — zero config switch to paper env
- Equity: `MarketOrderRequest(symbol, qty, side, time_in_force)`
- Multi-leg options: `order_class=OrderClass.MLEG`, `legs=[...]` with OCC-format symbols (e.g., `SPY250127C00608000` = SPY Jan 27 2025 Call $608)
- Paper accounts have Level 3 options (spreads, straddles, iron condors) **enabled by default** — no approval process, no KYC
- `get_all_positions()`, `get_account()` for portfolio state
- Order callbacks: poll `get_order_by_id()` for fill confirmation

**OCC symbol construction:**
The existing options pipeline (legs builder agent) already selects strikes and expiry. The output must be reformatted to OCC format before Alpaca submission:
```
{UNDERLYING}{YYMMDD}{C|P}{8-digit-strike-padded}
e.g., SPY → expiry 2025-01-27 → Call → $608.00 → SPY250127C00608000
```

**Integration point:**
New `api/paper_trading_routes.py` (APIRouter, following `api/screener_routes.py` pattern). Alpaca credentials added as env vars `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` alongside existing `TRADIER_API_KEY`.

**Why not `alpaca-trade-api` (legacy package):**
Officially deprecated by Alpaca. All new development on `alpaca-py`.

**Why not IBKR / Tastytrade:**
Alpaca paper is free, instant account creation, no KYC, Python SDK matches existing architecture. IBKR requires running TWS/IB Gateway as a local process. Tastytrade has no paper trading API.

---

### 3. Backend: Persistence Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| sqlalchemy | ^2.0.48 | ORM for trade recommendations, paper orders, scoring results | De facto FastAPI persistence standard. Async-native in 2.0 (matches existing async FastAPI event loop). Type-safe, Pydantic-interoperable. |
| aiosqlite | ^0.22.1 | Async SQLite driver for SQLAlchemy 2.0 | Zero infrastructure — file-based DB embedded in Python stdlib driver. Sufficient for local tool data volumes (hundreds to low thousands of rows). Upgrade to PostgreSQL later by changing only the connection string. |

**Connection string:** `sqlite+aiosqlite:///./data/trades.db`

**Session injection:**
```python
# api/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("sqlite+aiosqlite:///./data/trades.db")
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSession() as session:
        yield session
```

**Schema scope for v1.2:**

```
recommendations        — ticker, date, signal, confidence_score, agent_outputs (JSON)
paper_orders           — alpaca_order_id, recommendation_id (FK), symbol, status, fill_price, filled_at
scoring_results        — recommendation_id (FK), outcome (win/loss/neutral), return_pct, scored_at
```

**Why SQLite over PostgreSQL:**
This is a single-user local dev tool. SQLite is zero-infra, built into Python, and adequate for the data volumes involved. The ORM layer means switching to Postgres later requires only a connection string change.

**Why async SQLAlchemy over sync:**
FastAPI is already async. Using `create_async_engine` + `aiosqlite` keeps the event loop clean and consistent with existing SSE streaming patterns. Mixing sync DB calls into an async FastAPI app causes thread-pool overhead.

**Why not Alembic for migrations:**
Premature for v1.2. `Base.metadata.create_all(engine)` on startup is sufficient when the schema is being defined for the first time. Add Alembic if schema migrations are needed in v1.3+.

---

### 4. Backend: Scoring System

**No new library dependencies.** All scoring metrics are pure Python math on existing data:

| Metric | Implementation | Library |
|--------|---------------|---------|
| Win rate | `wins / total_scored` | stdlib |
| Average return % | `mean(return_pct)` | `statistics` (stdlib) |
| Sharpe ratio | `mean_r / std_r * sqrt(252)` annualized | `statistics` (stdlib) or `pandas` (already in requirements) |
| Max drawdown | Rolling max / min on equity curve | `pandas` (already in requirements) |
| Profit factor | `gross_wins / abs(gross_losses)` | stdlib |
| Consecutive wins/losses | Running streak counter | stdlib |

**pandas is already in requirements.txt** — no new dependency for calculations.

**Scoring trigger:** When Alpaca confirms a fill (`order.status == "filled"`), a background task computes `return_pct` against entry price and writes to `scoring_results`. Outcome (win/loss/neutral) is determined when position is closed.

---

## Complete Dependency Delta

### Python — additions to `requirements.txt`

```
alpaca-py>=0.43.2
sqlalchemy>=2.0.48
aiosqlite>=0.22.1
```

### npm — addition to `frontend/package.json` dependencies

```json
"lightweight-charts": "^5.1.0"
```

**Total new packages: 4.** That's it.

---

## What NOT to Add

| Rejected | Reason |
|----------|--------|
| Recharts / Chart.js / Victory | General-purpose charting with SVG rendering and React 19 peer-dep issues. lightweight-charts is the right tool for financial time-series — Canvas-based, financial-domain-native. |
| community wrapper for lightweight-charts | All lag behind v5 API. Imperative pattern is 20 lines and needs no extra package. |
| backtrader | Already in requirements (unused). Backtesting is explicitly deferred to v1.3+. Do NOT wire it into v1.2. |
| redis | Overkill for local scoring persistence. Redis is already in requirements but was superseded by in-process dict for screener cache. Not needed here. |
| Celery / task queues | Paper order submission is fast (<500ms). Scoring can run as a FastAPI `BackgroundTask`. No queue infra needed. |
| PostgreSQL | Out of scope for a local single-user tool. SQLite + SQLAlchemy ORM provides the same API; switch connection string when/if needed. |
| Alembic | Premature for v1.2. `create_all()` on startup is sufficient for a new schema with no existing data to migrate. |
| TA-Lib | Technical indicator overlays would require native binary compilation. The existing Python agents already produce technical analysis. Pass computed indicator data as lightweight-charts series arrays — no TA-Lib needed. |
| WebSocket (ws / socket.io) | Paper trading status can be polled via REST at 5s interval. Alpaca fills settle within seconds. Full WebSocket infra is disproportionate for this use case. |
| alpaca-trade-api (legacy) | Officially deprecated by Alpaca. Use alpaca-py only. |

---

## Integration Points

| New Feature | Attaches To | Notes |
|------------|-------------|-------|
| `<PriceChart>` component | React frontend — new component in `frontend/src/components/` | Receives OHLC bars via `GET /api/chart/{ticker}?days=90` — served by new endpoint that calls existing yfinance data layer. |
| `<EquityCurve>` component | React frontend — track record Dashboard tab | Receives `{date, equity}` data from `GET /api/dashboard/equity-curve`. Rendered as lightweight-charts line series. |
| Paper trading router | FastAPI — new `api/paper_trading_routes.py` | User confirms execution after seeing analysis. POST `/api/paper/execute` accepts final decision payload, submits to Alpaca, persists recommendation + order. |
| SQLAlchemy models | `api/models.py` + `api/database.py` (new files) | Session injected via `Depends(get_db)` into route handlers. |
| Scoring computation | `api/scoring.py` (new module) | Triggered by `BackgroundTasks` when Alpaca confirms fill. Reads from `paper_orders`, writes to `scoring_results`. |
| Dashboard API endpoints | FastAPI — new `api/dashboard_routes.py` | `GET /api/dashboard/summary`, `/equity-curve`, `/trade-history`, `/scoring`. |
| Track record Dashboard tab | React frontend — new tab in existing tab structure | Consumes dashboard endpoints. Table of past trades + equity curve chart + aggregate stats (win rate, Sharpe, avg return). |

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| lightweight-charts 5.1.0 | HIGH | npm result confirmed "latest 3 months ago"; official TradingView library with active maintenance and documented v5 migration path |
| alpaca-py 0.43.2 | HIGH | PyPI confirmed version; official Alpaca SDK with documented multi-leg options support and paper-Level 3 defaults |
| SQLAlchemy 2.0.48 | HIGH | Official SQLAlchemy blog post confirmed Mar 2026 release; 2.0 series is production/stable |
| aiosqlite 0.22.1 | HIGH | PyPI confirmed Dec 23, 2025 release; only async SQLite driver for SQLAlchemy 2.0 async engine |
| Scoring system (no new deps) | HIGH | All metrics expressible with pandas (existing) and stdlib; no novel library needed |
| Imperative chart pattern (no wrapper) | HIGH | Official TradingView docs show this exact pattern for React; avoids v5 wrapper lag |

---

## Sources

- [lightweight-charts npm](https://www.npmjs.com/package/lightweight-charts) — v5.1.0 confirmed
- [lightweight-charts v5 announcement](https://www.tradingview.com/blog/en/tradingview-lightweight-charts-version-5-50837/) — series API revamp, 35kB, multi-pane
- [From v4 to v5 migration guide](https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5) — breaking changes documented
- [Basic React example — official](https://tradingview.github.io/lightweight-charts/tutorials/react/simple) — useRef + useEffect pattern
- [Advanced React example — official](https://tradingview.github.io/lightweight-charts/tutorials/react/advanced) — multi-component imperative chart
- [alpaca-py PyPI](https://pypi.org/project/alpaca-py/) — v0.43.2 confirmed
- [Alpaca-py trading docs](https://alpaca.markets/sdks/python/trading.html) — TradingClient, order request classes
- [Multi-leg Level 3 options in paper — Alpaca changelog](https://docs.alpaca.markets/changelog/multi-leg-level-3-options-trading-in-paper) — paper Level 3 default-enabled
- [alpaca-py mleg example notebook](https://github.com/alpacahq/alpaca-py/blob/master/examples/options-trading-mleg.ipynb) — MLEG order format with OCC symbols
- [SQLAlchemy 2.0.48](https://www.sqlalchemy.org/changelog/CHANGES_2_0_44) — 2.0 series stable, Mar 2026
- [aiosqlite PyPI](https://pypi.org/project/aiosqlite/) — v0.22.1, Dec 2025
- [FastAPI SQL databases guide](https://fastapi.tiangolo.com/tutorial/sql-databases/) — async SQLAlchemy + FastAPI Depends() pattern
- [Recharts React 19 issue #4558](https://github.com/recharts/recharts/issues/4558) — peer dep conflict rationale for not using Recharts
