---
phase: 14-alpaca-paper-trading-execution
plan: 03
subsystem: frontend
tags: [react, typescript, hooks, chart-markers, lightweight-charts, trade-visualization, alpaca, paper-trading, auto-close]

# Dependency graph
requires:
  - phase: 14-alpaca-paper-trading-execution
    plan: 01
    provides: POST /api/trades/check-autoclose endpoint, TradeStatusResponse with close_time
  - phase: 14-alpaca-paper-trading-execution
    plan: 02
    provides: useTradeStatus hook, TradeStatus TypeScript interface (includes close_time)
provides:
  - Trade fill marker (green arrowUp / red arrowDown) on candlestick chart at fill date/price
  - Trade exit marker (purple square) on candlestick chart at close date/price
  - Auto-close check fires on ChartScreen mount (fire-and-forget POST to check-autoclose)
  - useTradeMarker hook for deriving chart marker data from TradeStatus
affects:
  - Phase 15 (Scoring) — trade markers provide visual confirmation of fill execution for validation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - createSeriesMarkers called with array of markers to render fill + exit in a single call
    - Fire-and-forget fetch in useEffect with empty dep array (mount-only)
    - Hook derives presentation-ready marker props from typed TradeStatus (no as-any, close_time is typed)

key-files:
  created:
    - frontend/src/hooks/useTradeMarker.ts
  modified:
    - frontend/src/components/ChartContainer.tsx (added tradeMarker prop, fill + exit marker rendering)
    - frontend/src/components/ChartScreen.tsx (import useTradeMarker, auto-close effect, pass tradeMarker)

key-decisions:
  - "useTradeMarker accepts direction as second param — overlay.signal passed from ChartScreen so hook stays pure (no overlay coupling)"
  - "tradeMarker rendered separately from overlay markers — independent createSeriesMarkers call avoids marker ordering conflicts"
  - "Auto-close check uses empty dependency array (mount-only) per D-09 — no ticker dependency to avoid repeat calls on ticker change"
  - "close_time used directly from typed TradeStatus interface — no unsafe casts required"

# Metrics
duration: ~2min
completed: 2026-04-03
---

# Phase 14 Plan 03: Trade Markers and Auto-Close Summary

**Candlestick chart trade fill/exit markers via createSeriesMarkers plus fire-and-forget auto-close check on chart mount**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-03T15:19:04Z
- **Completed:** 2026-04-03T15:21:00Z (Task 1 complete; Task 2 is human-verify checkpoint)
- **Tasks:** 2 (Task 1 automated, Task 2 human-verify checkpoint — approved by user)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Created `useTradeMarker` hook: accepts `tradeStatus: TradeStatus | null` and `direction: string`, returns a `TradeMarkerProps | null` object ready for ChartContainer; uses `tradeStatus.close_time` directly from the typed interface (no `as any`)
- Extended `ChartContainer` with optional `tradeMarker` prop: renders a green `arrowUp` (BUY) or red `arrowDown` (SELL) FILL marker at the fill date, and optionally a purple `square` CLOSE marker at the close date; uses a single `createSeriesMarkers(candleSeries, markers)` call
- Added `tradeMarker` to the ChartContainer `useEffect` dependency array — markers re-render reactively when trade state changes
- Wired `ChartScreen`: imports `useTradeMarker`, fires `POST /api/trades/check-autoclose` on mount (fire-and-forget, empty dep array per D-09), derives `tradeMarker` from `tradeStatus` + `overlay?.signal`, passes it to `<ChartContainer>`
- Existing overlay annotations (TP/SL price lines, entry dot, expiry marker) are unchanged and continue rendering independently

## Task Commits

1. **Task 1: Create trade marker hook, extend ChartContainer with fill/exit markers, wire auto-close on load** — `b07926f` (feat)
2. **Task 2: Verify trade markers on chart and auto-close behavior** — Human-verify checkpoint; approved by user

## Files Created/Modified

- `frontend/src/hooks/useTradeMarker.ts` — Hook returning TradeMarkerProps with fillDate, fillPrice, direction, optional closeDate/closePrice; reads close_time as typed field
- `frontend/src/components/ChartContainer.tsx` — Added TradeMarker interface, tradeMarker prop, FILL/CLOSE marker rendering via createSeriesMarkers
- `frontend/src/components/ChartScreen.tsx` — Added useTradeMarker import, mount-only auto-close effect, tradeMarker derivation, tradeMarker prop on ChartContainer

## Decisions Made

- `useTradeMarker` takes `direction` as a second parameter (not reading overlay internally) — keeps the hook decoupled from ChartOverlay; ChartScreen passes `overlay?.signal ?? 'BUY'`
- Trade markers rendered in a separate `createSeriesMarkers` call after overlay markers — avoids ordering issues with the overlay entry dot and expiry markers
- Auto-close `useEffect` has empty dependency array — fires once on ChartScreen mount regardless of ticker, matching D-09 intent (passive background trigger, not per-ticker)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all marker data flows from live `useTradeStatus` polling results. Markers only render when `tradeStatus.status === 'filled'` and real fill_price/fill_time are present from the Alpaca response.

## Self-Check: PASSED

- FOUND: frontend/src/hooks/useTradeMarker.ts
- FOUND: frontend/src/components/ChartContainer.tsx (contains tradeMarker prop, FILL $, CLOSE $, createSeriesMarkers(candleSeries, markers))
- FOUND: frontend/src/components/ChartScreen.tsx (contains check-autoclose, useTradeMarker, tradeMarker={tradeMarker})
- FOUND: commit b07926f
- TypeScript: Exit code 0 (no errors)

## Next Phase Readiness

- Fill and exit markers render on the candlestick chart — user confirmed via Task 2 visual verification
- Auto-close fires on page load — closed positions produce exit markers on next chart view
- Phase 14 (Alpaca Paper Trading Execution) is fully complete
- Phase 15 (Scoring) can begin: trade records with fill_price, close_price, pnl_pct, outcome are persisted in SQLite via Plan 01's trade_routes.py

---
*Phase: 14-alpaca-paper-trading-execution*
*Completed: 2026-04-03*
