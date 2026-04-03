# Phase 14: Alpaca Paper Trading Execution - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can submit paper equity and options orders from the agent decision, see live order status, see fill markers on the chart, and have positions auto-closed after N trading days. This phase activates the Chart Screen's action panel (Phase 13 left it read-only) and adds the execution infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Order submission UX
- **D-01:** "Execute Paper Trade" button lives on the Chart Screen action panel — replaces the disabled "Confirm Trade" CTA from Phase 13
- **D-02:** Confirmation step before submitting — modal/popover showing order details (ticker, direction, quantity, order type) with Confirm/Cancel
- **D-03:** Market order for equity trades — simplest, fills instantly in paper environment, no partial fill complexity
- **D-04:** Fixed position size: 100 shares for equity, 1 contract for options. Paper trading, not real money. Configurable later.

### Order status display & lifecycle
- **D-05:** Status appears in Chart Screen action panel: "Confirm Trade" → "Submitted..." → "Filled @ $X.XX" → fill marker on chart. Single location, no context switch
- **D-06:** Poll `GET /api/trades/{ticker}/status` every 3 seconds until terminal state (filled/rejected). Paper orders fill nearly instantly
- **D-07:** Rejection shows red badge in action panel: "Rejected: {reason}". User can retry. Common: market closed, insufficient buying power
- **D-08:** Trade records persisted to SQLite via SQLAlchemy 2.0 async + aiosqlite. Schema: ticker, direction, order_id, fill_price, fill_time, status, quantity, strategy_name, trade_type, strike, expiry, contract_type, legs_json

### Auto-close mechanism (EXEC-05)
- **D-09:** Check on dashboard/chart load — when user opens app, check all open positions and close any past N days. No background process needed for paper trading frequency
- **D-10:** Default hold period: 5 trading days (1 week). Matches typical short-term options trade horizon
- **D-11:** Outcome computation: WIN if P&L > 0, LOSS if P&L ≤ 0. P&L = (close_price - fill_price) / fill_price × 100 for long; inverse for short. Options: (close_premium - fill_premium) / fill_premium × 100
- **D-12:** If market closed when N days elapse, close at next market open. Track by trading days (exclude weekends/holidays), not calendar days

### Options execution scope (EXEC-04)
- **D-13:** Single-leg options only for v1.2. Multi-leg spreads deferred — Alpaca paper has documented gaps for complex order types. Ship single-leg, validate, then extend
- **D-14:** Options rejection: same flow as equity (red badge, reason displayed, log for debugging). No auto-retry — options rejections usually indicate structural issues
- **D-15:** CHART-03 trade markers: entry marker at fill price on the underlying's chart. Options don't have their own chart — marker on stock chart at fill date
- **D-16:** Single `trades` table with `trade_type` column (equity/option) and nullable options-specific fields. Simpler queries for Phase 15/16

### Alpaca SDK integration (from roadmap decisions)
- **D-17:** `alpaca-py` v0.43.2 SDK (not deprecated `alpaca-trade-api`)
- **D-18:** All SDK calls wrapped with `asyncio.to_thread()` — non-blocking in FastAPI async routes
- **D-19:** `ALPACA_PAPER_KEY` / `ALPACA_PAPER_SECRET` env var naming with startup assertion
- **D-20:** Frontend already has `VITE_ALPACA_KEY` / `VITE_ALPACA_SECRET` from Phase 13 chart data

### Claude's Discretion
- SQLAlchemy model class design and migration approach
- Exact confirmation modal/popover styling
- Polling implementation details (setInterval vs custom hook)
- Order status state machine implementation
- Error boundary handling for Alpaca API failures
- Trade marker styling on chart (color, shape, size)

</decisions>

<specifics>
## Specific Ideas

- Action panel is the "lock in" moment — from Phase 13 context, the Chart Screen is the decision layer
- Status transitions should feel instant in paper mode — no need for complex loading states
- Trade records must be queryable by Phase 15 scoring and Phase 16 dashboard
- Single-leg options first, prove it works, then consider multi-leg in v1.3

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Alpaca integration
- `api/chart_routes.py` — Existing chart overlay endpoint; new trade endpoints go in same or sibling router
- `api/schemas.py` — Existing Pydantic schemas including `ChartOverlayResponse`; trade schemas added here
- `api/main.py` — Router registration pattern

### Frontend (Phase 13 artifacts)
- `frontend/src/components/ChartScreen.tsx` — Chart screen with action panel; execution activates the disabled CTA
- `frontend/src/components/ChartActionPanel.tsx` — Action panel component; needs execution button and status display
- `frontend/src/components/ChartContainer.tsx` — Chart with overlay markers; CHART-03 trade markers added here
- `frontend/src/hooks/useOverlay.ts` — Overlay data hook; may need extension for trade status

### Agent output
- `tradingagents/agents/` — Agent factory functions producing final decision with signal, entry/TP/SL fields
- `eval_results/` — Existing JSON logs format that overlay endpoint reads

### Data persistence
- `.planning/STATE.md` §Key Decisions — SQLAlchemy 2.0 async + aiosqlite decision, scoring schema decision

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChartActionPanel.tsx` — Phase 13 created this with disabled CTA; this phase activates it
- `useOverlay.ts` — Fetches overlay data; can be extended to also fetch trade status
- `api/chart_routes.py` — Chart router pattern; trade endpoints follow same pattern
- `api/schemas.py` — Pydantic schema pattern for request/response models
- `TickerAutocomplete.tsx` — Reusable for any ticker input needed

### Established Patterns
- FastAPI `APIRouter` with prefix — `router = APIRouter(prefix="/api")`
- Pydantic schemas for all API contracts
- `asyncio.to_thread()` for blocking SDK calls in async routes
- Frontend custom hooks (`useAnalysis`, `useScreener`, `useChartData`, `useOverlay`)
- Tailwind dark mode with `dark:` class variants

### Integration Points
- `ChartActionPanel.tsx` — CTA button activation and status display
- `ChartContainer.tsx` — CHART-03 trade entry/exit markers via `createSeriesMarkers()`
- New `api/trade_routes.py` — trade submission, status polling, auto-close endpoints
- New SQLite database — trade persistence layer consumed by Phases 15 and 16
- `.env` — Alpaca keys already configured from Phase 13

</code_context>

<deferred>
## Deferred Ideas

- Multi-leg options spreads execution — v1.3 (Alpaca paper gaps for complex orders)
- User-configurable position size — future enhancement
- User-configurable hold period per trade — future enhancement
- WebSocket/SSE for real-time order status — polling sufficient for paper trading
- Options P&L chart separate from underlying — complexity not justified

</deferred>

---

*Phase: 14-alpaca-paper-trading-execution*
*Context gathered: 2026-04-03*
