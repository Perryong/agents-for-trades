---
phase: 16-track-record-dashboard
plan: 01
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, dashboard, track-record]

# Dependency graph
requires:
  - phase: 15-recommendation-scoring
    provides: Trade ORM model with outcome/pnl_pct fields, SessionDep, existing score_routes pattern
provides:
  - GET /api/dashboard/summary endpoint returning full metric suite
  - GET /api/dashboard/trades endpoint with ticker/type filtering
  - GET /api/dashboard/equity-curve endpoint returning cumulative P&L data points
  - DashboardSummaryResponse, DashboardTradeItem, DashboardTradesResponse, EquityCurvePoint, EquityCurveResponse Pydantic schemas
affects: [16-02-frontend-dashboard, frontend-dashboard-tab]

# Tech tracking
tech-stack:
  added: []
  patterns: [dashboard_router follows score_router APIRouter prefix="/api" pattern, _filter_trades helper for reusable query filtering]

key-files:
  created:
    - api/dashboard_routes.py
  modified:
    - api/schemas.py
    - api/main.py

key-decisions:
  - "Aggregate P&L is sum of pnl_pct for closed trades (not win_rate alone — per STATE.md decision)"
  - "Legacy trades (is_legacy=True) appear in trade list but excluded from summary/equity-curve metrics (no outcome AND no pnl_pct)"
  - "Equity curve sorted by close_time ascending; falls back to analysis_date when close_time is None"
  - "Trades list sorted by entry date descending for most-recent-first display"

patterns-established:
  - "dashboard_router: APIRouter(prefix='/api') — same as score_router, chart_router, trade_router"
  - "_filter_trades helper: accepts all_trades list + optional ticker/trade_type; returns filtered list"
  - "is_legacy detection: outcome is None AND pnl_pct is None"

requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04, DASH-05]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 16 Plan 01: Track Record Dashboard Backend Summary

**Three FastAPI dashboard endpoints with Pydantic schemas: /summary (full metric suite), /trades (filtered history with legacy detection), /equity-curve (cumulative P&L data points for lightweight-charts)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-03T16:23:19Z
- **Completed:** 2026-04-03T16:24:50Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added 5 Pydantic response schemas to api/schemas.py (DashboardSummaryResponse, DashboardTradeItem, DashboardTradesResponse, EquityCurvePoint, EquityCurveResponse)
- Created api/dashboard_routes.py with 3 GET endpoints supporting ticker and type query param filtering
- Registered dashboard_router in api/main.py following established router pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dashboard Pydantic schemas to api/schemas.py** - `e6d249e` (feat)
2. **Task 2: Create dashboard API endpoints and register router** - `2e31342` (feat)

**Plan metadata:** (pending final commit)

## Files Created/Modified

- `api/schemas.py` - Added 5 dashboard Pydantic response schemas after CalibrationResponse
- `api/dashboard_routes.py` - New file: dashboard_router with /summary, /trades, /equity-curve endpoints
- `api/main.py` - Registered dashboard_router via include_router

## Decisions Made

- Followed plan as specified. All endpoint logic mirrors score_routes.py pattern.
- Legacy trade detection: `is_legacy = outcome is None and pnl_pct is None` (per D-12)
- Win rate never returned alone — always with expectancy, avg_winner, avg_loser, profit_factor, aggregate_pnl (per established STATE.md decision)
- Disclaimer added when total_closed < 5 for statistical significance warning

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 3 dashboard backend endpoints are ready for consumption by Plan 02 (React frontend tab)
- Endpoints accept `?ticker=AAPL` and `?type=equity|option` query params for filtering
- Equity curve returns `{time, value}` points compatible with lightweight-charts v5 format
- Legacy trades appear in /trades list with `is_legacy=true` flag, excluded from /summary and /equity-curve

---
*Phase: 16-track-record-dashboard*
*Completed: 2026-04-03*

## Self-Check: PASSED

- FOUND: api/dashboard_routes.py
- FOUND: api/schemas.py
- FOUND: api/main.py
- FOUND: .planning/phases/16-track-record-dashboard/16-01-SUMMARY.md
- FOUND: commit e6d249e (feat(16-01): add dashboard Pydantic schemas)
- FOUND: commit 2e31342 (feat(16-01): create dashboard API endpoints and register router)
