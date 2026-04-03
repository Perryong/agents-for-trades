# Phase 16: Track Record Dashboard - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can open a Track Record tab and see a complete, self-contained view of system performance — summary stats, chronological trade history, equity curve, per-ticker breakdown, and equity vs options split. This is the final phase of v1.2.

</domain>

<decisions>
## Implementation Decisions

### Dashboard layout & navigation
- **D-01:** New top-level "Track Record" tab in app nav (4th peer alongside Analysis, Screener, Chart). Self-contained view, not nested
- **D-02:** Single scrollable page: summary stats cards → equity curve chart → trade history table → per-ticker breakdown. Linear flow, no sub-tabs
- **D-03:** Persistent yellow banner at top: "Paper Trading Results — Not Real Money". Always visible, not dismissable
- **D-04:** Empty state: friendly message with link to Chart screen when no trades exist

### Equity curve & data API
- **D-05:** Equity curve uses lightweight-charts v5 `LineSeries` — cumulative P&L on Y-axis, trade close dates on X-axis. Green above zero, red below
- **D-06:** Three API endpoints: `GET /api/dashboard/summary`, `GET /api/dashboard/trades`, `GET /api/dashboard/equity-curve`
- **D-07:** Per-ticker: `GET /api/dashboard/trades?ticker=AAPL` — filter parameter. Frontend groups by ticker for breakdown
- **D-08:** Equity vs options split: `?type=equity` or `?type=option` filter. Frontend toggle buttons: "All" / "Equity" / "Options". Metrics recalculate per filter

### Trade history table
- **D-09:** Columns: Ticker, Direction (BUY/SELL badge), Entry Date, Outcome (WIN/LOSS/OPEN badge), P&L %, Strategy Name. Sorted by entry date descending
- **D-10:** Per-ticker drill-down: click ticker name → filters entire dashboard to that ticker. "Clear filter" button to return
- **D-11:** No pagination — show all trades. Paper trading generates <100 trades typically
- **D-12:** Pre-v1.2 JSON logs shown with "Legacy" badge and no outcome/P&L (greyed out). Excluded from quantitative metrics

### Claude's Discretion
- Summary stats card grid layout and styling
- Equity curve chart dimensions and colors
- Table row styling and hover states
- Filter button group styling
- Loading states and skeleton UI
- Responsive behavior

</decisions>

<specifics>
## Specific Ideas

- This is the capstone view — "did the AI make money?"
- Linear scroll design: stats → curve → table → per-ticker. User reads top-to-bottom
- Paper trading disclaimer is non-negotiable — prevents any illusion of real performance
- Legacy logs visible but clearly differentiated — audit trail without polluting metrics

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data layer
- `api/models.py` — Trade model with all scoring columns
- `api/score_routes.py` — Existing scoring endpoints (reuse summary metrics)
- `api/schemas.py` — Existing Pydantic schemas
- `api/db.py` — Async session factory

### Frontend
- `frontend/src/App.tsx` — App nav (add 4th tab)
- `frontend/src/components/ChartContainer.tsx` — lightweight-charts v5 useRef+useEffect pattern (reuse for equity curve)
- `frontend/src/components/ScoringCard.tsx` — Existing metrics card (reuse or adapt for dashboard)
- `frontend/src/types.ts` — Existing TypeScript interfaces

### Project decisions
- `.planning/STATE.md` §Key Decisions — "Win rate never displayed alone", "Historical JSON log compatibility"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ScoringCard.tsx` — Phase 15 metrics card; reuse for dashboard summary stats
- `ChartContainer.tsx` — lightweight-charts v5 pattern; adapt for equity curve LineSeries
- `useScores.ts` — Phase 15 scoring hooks; reuse or adapt for dashboard data
- Tailwind dark mode — existing `dark:` class patterns

### Established Patterns
- Top-level nav tabs in `App.tsx` (Analysis/Screener/Chart)
- Custom hooks for data fetching (`useAnalysis`, `useScreener`, `useChartData`, `useOverlay`, `useScores`)
- FastAPI `APIRouter` with prefix

### Integration Points
- `App.tsx` — add "Track Record" as 4th nav tab
- New `api/dashboard_routes.py` — dashboard-specific endpoints
- New `frontend/src/components/TrackRecordScreen.tsx` — dashboard screen
- Existing `api/models.py` Trade table — read-only queries

</code_context>

<deferred>
## Deferred Ideas

- Per-agent accuracy breakdown (SCORE-04) — v1.3
- Backtesting comparison view — v1.3
- Export to CSV/PDF — future enhancement
- Social comparison / leaderboard — out of scope (single-user tool)

</deferred>

---

*Phase: 16-track-record-dashboard*
*Context gathered: 2026-04-03*
