---
phase: 14-alpaca-paper-trading-execution
plan: 02
subsystem: frontend
tags: [react, typescript, hooks, polling, confirmation-modal, trade-execution, alpaca, paper-trading]

# Dependency graph
requires:
  - phase: 14-alpaca-paper-trading-execution
    plan: 01
    provides: POST /api/trades and GET /api/trades/{ticker}/status endpoints
provides:
  - Trade execution UX in Chart Screen action panel
  - useTradeStatus polling hook (every 3s, stops on terminal state)
  - useTrade submission hook (POST /api/trades)
  - TradeConfirmModal confirmation dialog
  - Activated ChartActionPanel with status state machine
affects:
  - 14-03 (chart markers — reads tradeStatus.fill_price and tradeStatus.close_time)
  - Plan 03 uses TradeStatus.close_time for exit marker rendering

# Tech tracking
tech-stack:
  added: []
  patterns:
    - useEffect + window.setInterval polling every 3000ms with clearInterval cleanup on unmount/orderId change
    - Immediate poll on orderId set, then interval; stops on terminal state ['filled', 'rejected', 'error']
    - useTrade wraps fetch POST with isSubmitting state; re-throws on non-2xx with error body detail

key-files:
  created:
    - frontend/src/hooks/useTradeStatus.ts
    - frontend/src/hooks/useTrade.ts
    - frontend/src/components/TradeConfirmModal.tsx
  modified:
    - frontend/src/types.ts (added OrderStatus, TradeStatus, TradeRequest, TradeResponse)
    - frontend/src/components/ChartActionPanel.tsx (replaced disabled CTA with full status machine)
    - frontend/src/components/ChartScreen.tsx (wired useTrade, useTradeStatus, TradeConfirmModal)

key-decisions:
  - "isSubmitting from useTrade reflected as 'submitted' status in ChartActionPanel during modal-to-API latency"
  - "canExecuteOptions uses LEG 1: regex on overlay.options_legs — disables execute button when options_legs cannot be parsed"
  - "Immediate poll on orderId set to minimize perceived latency before first status update"
  - "TradeStatus INITIAL_STATUS (idle) returned when orderId is null — no polling cost in passive mode"

# Metrics
duration: ~3min
completed: 2026-04-03
---

# Phase 14 Plan 02: Frontend Trade Execution UX Summary

**Trade execution flow wired into Chart Screen: Execute Paper Trade button, confirmation modal, useTrade POST hook, useTradeStatus polling hook, and idle/submitted/filled/rejected/error status display in action panel**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-03T15:11:39Z
- **Completed:** 2026-04-03T15:13:59Z (Task 1 complete; Task 2 is human-verify checkpoint)
- **Tasks:** 2 (Task 1 automated, Task 2 human-verify checkpoint — approved)
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- Added `OrderStatus`, `TradeStatus`, `TradeRequest`, and `TradeResponse` types to `frontend/src/types.ts`; `TradeStatus.close_time` is present for downstream Plan 03 chart marker consumption
- Created `useTradeStatus` hook: polls `GET /api/trades/{ticker}/status?order_id=...` every 3 seconds using `window.setInterval`, stops on terminal states (`filled`, `rejected`, `error`), cleans up on unmount
- Created `useTrade` hook: submits `POST /api/trades` as JSON, surfaces `isSubmitting` boolean for loading UI
- Created `TradeConfirmModal`: centered dark-backdrop modal showing ticker, direction badge (green BUY / red SELL), quantity, order type, trade type, and optional strategy name; Cancel and Confirm Trade buttons
- Replaced disabled "Confirm Trade" CTA in `ChartActionPanel` with full status machine: idle → Execute Paper Trade button, submitted → amber spinner, filled → green "Filled @ $X.XX", rejected → red badge with reason + Retry, error → red badge + Retry
- Added HOLD signal guard (disables execute, tooltip "No trade signal") and options parse guard (disables execute when `LEG 1:` not found in options_legs)
- Wired `ChartScreen` to open modal on execute, submit trade on confirm, and pass `useTradeStatus` result to `ChartActionPanel`

## Task Commits

1. **Task 1: Create trade hooks, confirmation modal, and activate action panel** — `886d950` (feat)
2. **Task 2: Verify trade execution UX in browser** — Human-verify checkpoint; approved by user

## Files Created/Modified

- `frontend/src/types.ts` — Added OrderStatus, TradeStatus, TradeRequest, TradeResponse type exports
- `frontend/src/hooks/useTradeStatus.ts` — Polling hook with setInterval/clearInterval lifecycle management
- `frontend/src/hooks/useTrade.ts` — Fetch POST hook with isSubmitting state
- `frontend/src/components/TradeConfirmModal.tsx` — Confirmation dialog with order details and Confirm/Cancel buttons
- `frontend/src/components/ChartActionPanel.tsx` — Replaced disabled CTA, added props (ticker, onExecute, tradeStatus, canExecuteOptions), implemented 5-state status display
- `frontend/src/components/ChartScreen.tsx` — Added modal state, trade hooks, canExecuteOptions logic, updated ChartActionPanel props

## Decisions Made

- `isSubmitting` from `useTrade` overlaid as `status: 'submitted'` in the panel during the modal-close-to-API-response gap, preventing flicker back to idle
- `canExecuteOptions` regex `/LEG\s+1:/i` — case-insensitive, handles spacing variation in legs builder output
- Immediate `poll()` call before `setInterval` reduces visible "Submitted..." hold time in most paper fill scenarios

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all status transitions wire to live API responses. The `TradeStatus` object is fully populated from the polling endpoint; no hardcoded mock values flow to the UI.

## Self-Check: PASSED

- FOUND: frontend/src/hooks/useTradeStatus.ts
- FOUND: frontend/src/hooks/useTrade.ts
- FOUND: frontend/src/components/TradeConfirmModal.tsx
- FOUND: frontend/src/components/ChartActionPanel.tsx (contains "Execute Paper Trade")
- FOUND: frontend/src/components/ChartScreen.tsx (contains useTradeStatus, useTrade, TradeConfirmModal)
- FOUND: frontend/src/types.ts (contains OrderStatus, TradeStatus, TradeRequest, TradeResponse, close_time)
- FOUND: commit 886d950
- TypeScript: Exit code 0 (no errors)

## Next Phase Readiness

- Execute Paper Trade UX is fully functional end-to-end against `POST /api/trades` and `GET /api/trades/{ticker}/status`
- `TradeStatus.close_time` is available in the polling response — Plan 03 can read this field to render exit markers on the chart
- `useTradeStatus` hook can be reused or extended in Plan 03 for the chart marker polling pattern
- Rejected orders show reason text and offer retry — no additional UX work needed for Plan 03

---
*Phase: 14-alpaca-paper-trading-execution*
*Completed: 2026-04-03*
