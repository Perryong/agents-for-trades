# Milestones

## v1.2 Paper Trading & Validation (Shipped: 2026-04-03)

**Phases completed:** 4 phases, 10 plans, 14 tasks

**Key accomplishments:**

- FastAPI GET /api/chart/{ticker}/overlay endpoint with regex signal extraction, ChartOverlayResponse Pydantic schema, and 15 passing unit tests
- useOverlay.ts
- SQLite trade persistence + Alpaca paper trading integration with equity/options submit, status polling, and 5-trading-day auto-close via three FastAPI REST endpoints
- Trade execution flow wired into Chart Screen: Execute Paper Trade button, confirmation modal, useTrade POST hook, useTradeStatus polling hook, and idle/submitted/filled/rejected/error status display in action panel
- Candlestick chart trade fill/exit markers via createSeriesMarkers plus fire-and-forget auto-close check on chart mount
- Task 1 — Trade model extension + confidence extraction:
- Status:
- Three FastAPI dashboard endpoints with Pydantic schemas: /summary (full metric suite), /trades (filtered history with legacy detection), /equity-curve (cumulative P&L data points for lightweight-charts)
- Complete React dashboard screen with summary stats cards, lightweight-charts equity curve, trade history table with ticker drill-down filtering, asset-class toggle, and paper trading disclaimer — added as 4th nav tab in App.tsx

---

## v1.1 Stock Recommendation System (Shipped: 2026-04-03)

**Phases completed:** 5 phases, 7 plans, 9 tasks

**Key accomplishments:**

- Screener data layer with chunked yfinance bulk fetch, rate-limit backoff, composite scoring (volume/momentum/unusual activity), and NYSE session-boundary cache with 15-min TTL
- LLM screener agent with Pydantic-validated structured output, retry/degradation on malformed JSON, and AgentState isolation guard
- POST /api/screen endpoint with async execution, independent from analysis SSE stream, partial/error response handling
- React screener tab with WatchlistPanel, PickCard score bars, stale indicator, and select-to-analyze prefill flow
- CLI `screen` subcommand with Rich table, --max-picks/--json flags, spinner, and error panel
- 15/15 requirements satisfied, 29 tests across 5 phases, all cross-phase integrations verified

---

## v1.0 Options Pipeline (Shipped: 2026-04-02)

**Phases completed:** 7 phases, 20 plans
**Timeline:** 3 days (2026-03-31 → 2026-04-02)
**Stats:** 121 commits, 137 files changed, ~22,760 lines added, 174 tests passing

**Key accomplishments:**

- Tradier + yfinance options data infrastructure with vendor abstraction routing and rate-limit fallback
- 7 specialist options agents: volatility analyst, flow analyst, strategy selector, strike/expiry selector, pricing agent, legs builder, Greeks monitor
- Stdlib-only Black-Scholes pricing (math.erf, no scipy dependency)
- Parallel options branch wired into LangGraph StateGraph alongside equity agents
- Options-aware debators (aggressive/conservative/neutral) and Risk Manager with 5 enforcement rules
- React + FastAPI visual frontend with SSE streaming, config sidebar, progress stepper, tabbed reports, and dark mode
- 30/30 v1 requirements satisfied, all cross-phase data flows verified

---
