---
phase: 01-trade-recommendation-sidebar-lock-in-flow
plan: 04
subsystem: ui
tags: [react, typescript, tailwind, tradingsidebar, live-price, bracket-order]

# Dependency graph
requires:
  - phase: 01-02
    provides: BracketOrderParams type, useLivePrice hook, useTrade.submitBracketTrade
  - phase: 01-03
    provides: TradeStatus with close_reason field, useTradeStatus hook

provides:
  - TradeSidebar component (320px right sidebar with full brokerage-style UI)
  - Restructured ChartScreen layout (flex-row with chart left, sidebar right)
  - Inline close position confirmation (no modal)
  - Live P&L display (dollar + percentage)
  - Lifecycle state machine (idle/submitted/filled/closed/rejected/error/expired)

affects: [02-track-record-screen, any phase referencing ChartActionPanel or TradeConfirmModal]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TradeSidebar as the confirmation surface (no modal needed — sidebar IS confirmation per D-02)
    - Inline two-button destructive confirmation (Cancel/Confirm Close) replaces modal pattern
    - Lifecycle state machine via OrderStatus type rendering different button states
    - P&L computed from livePrice + tradeStatus.fill_price in component (not hook)

key-files:
  created:
    - frontend/src/components/TradeSidebar.tsx
  modified:
    - frontend/src/components/ChartScreen.tsx
  deleted:
    - frontend/src/components/ChartActionPanel.tsx
    - frontend/src/components/TradeConfirmModal.tsx

key-decisions:
  - "Tasks 1 and 2 executed as a single atomic write — TradeSidebar was built complete in one pass including lifecycle states and P&L, committed as Task 1"
  - "P&L calculation uses locally destructured `price` alias from `livePrice?.price` rather than inline access for null-safety"
  - "useScoreSummary and useCalibration hooks removed from ChartScreen — they were only consumed by ChartActionPanel which is deleted"
  - "auto-close check-autoclose useEffect removed per D-10 as specified in plan"

patterns-established:
  - "TradeSidebar: scrollable body (flex-1 overflow-y-auto) + fixed bottom (flex-shrink-0) layout pattern for sidebar panels"
  - "Sidebar renders only when overlay !== null — chart takes full width in passive mode"

requirements-completed: [D-01, D-02, D-04, D-05, D-06, D-07]

# Metrics
duration: 2min
completed: 2026-04-05
---

# Phase 01 Plan 04: TradeSidebar Component Summary

**320px brokerage-style right sidebar replaces bottom ChartActionPanel with editable bracket order form, live P&L, and inline close confirmation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-05T05:30:33Z
- **Completed:** 2026-04-05T05:32:33Z
- **Tasks:** 3 (Tasks 1+2 combined in single write, Task 3 separate)
- **Files modified:** 4 (1 created, 1 modified, 2 deleted)

## Accomplishments

- Created TradeSidebar.tsx (320px) with live price header, signal metadata, 5 editable order fields, options legs accordion, and full lifecycle state machine
- Live P&L display (dollar + percentage, green/red) in OpenPositionPanel when position filled
- Inline two-button close confirmation (Cancel / Confirm Close) — no modal required
- ChartScreen restructured from flex-col to flex-row layout; sidebar replaces bottom panel
- Deleted ChartActionPanel.tsx and TradeConfirmModal.tsx as specified

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Create TradeSidebar with full lifecycle, P&L, and close confirmation** - `10b93cc` (feat)
2. **Task 3: Restructure ChartScreen and delete old components** - `4d4a3e6` (feat)

**Plan metadata:** (docs commit — below)

## Files Created/Modified

- `frontend/src/components/TradeSidebar.tsx` — New 320px right sidebar: live price header (aria-live), signal badge, 5-field bracket order form, options legs accordion, OpenPositionPanel with live P&L, full lifecycle state machine (7 states), inline close confirmation
- `frontend/src/components/ChartScreen.tsx` — Restructured to flex-row, adds useLivePrice, handleBracketTrade, handleClosePosition, removed showConfirmModal/check-autoclose/score hooks
- `frontend/src/components/ChartActionPanel.tsx` — Deleted (replaced by TradeSidebar)
- `frontend/src/components/TradeConfirmModal.tsx` — Deleted (sidebar is confirmation surface per D-02)

## Decisions Made

- Tasks 1 and 2 were implemented in a single atomic write since the lifecycle states and P&L were designed together with the static layout — no separate commit for Task 2 was needed as it was complete in the Task 1 file
- Removed `useScoreSummary` and `useCalibration` imports from ChartScreen as they were exclusively consumed by the now-deleted ChartActionPanel

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- TradeSidebar is ready for visual testing against live Alpaca paper trades
- ChartScreen layout restructure is complete; passive mode (no overlay) still works as before
- All 5 order fields pre-filled from AI overlay data and editable before execution
- Phase 01-05 (TrackRecord updates: close reason column, risk-reward + avg R-multiple stat cards) can proceed immediately

---
*Phase: 01-trade-recommendation-sidebar-lock-in-flow*
*Completed: 2026-04-05*
