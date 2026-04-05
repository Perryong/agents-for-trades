---
phase: 01-trade-recommendation-sidebar-lock-in-flow
plan: 02
subsystem: frontend-types-hooks
tags: [typescript, hooks, bracket-order, live-price]
dependency_graph:
  requires: []
  provides: [BracketOrderParams, LivePriceData, useLivePrice, submitBracketTrade]
  affects: [frontend/src/types.ts, frontend/src/hooks/useLivePrice.ts, frontend/src/hooks/useTrade.ts]
tech_stack:
  added: []
  patterns: [setInterval polling, fetch with error swallow, backward-compatible hook extension]
key_files:
  created:
    - frontend/src/hooks/useLivePrice.ts
  modified:
    - frontend/src/types.ts
    - frontend/src/hooks/useTrade.ts
decisions:
  - "Extend useTrade rather than create new hook — backward compat, single isSubmitting state shared across both submit paths"
  - "useLivePrice silently swallows fetch errors — UI-SPEC requires '--' display not error state"
metrics:
  duration: "1 minute"
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_modified: 3
---

# Phase 01 Plan 02: Frontend Types & Hooks for Bracket Orders Summary

**One-liner:** BracketOrderParams/LivePriceData interfaces + useLivePrice polling hook + useTrade bracket submission, TypeScript clean.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Add bracket order and live price types to types.ts | 1fc8e24 | Done |
| 2 | Create useLivePrice hook and update useTrade for bracket orders | adf4822 | Done |

## What Was Built

**frontend/src/types.ts** — Extended with:
- `OrderStatus` union now includes `'closed'`
- `TradeStatus.close_reason: string | null` — tracks "Target Hit" / "Stop-Loss" / "Manual Close" / "Expired"
- `BracketOrderParams` interface — ticker, direction, trade_type, entry_price, target_price, stop_loss, quantity, tif, strategy_name, analysis_date, confidence
- `LivePriceData` interface — ticker, price, open, change_pct, timestamp
- `DashboardSummary.avg_risk_reward: number | null`
- `DashboardSummary.avg_r_multiple: number | null`
- `DashboardTradeItem.close_reason: string | null`

**frontend/src/hooks/useLivePrice.ts** — New hook. Polls `/api/price/{ticker}/live` every 5 seconds via `setInterval`. Clears interval on ticker change and on unmount. Silently ignores fetch errors (UI shows "--" per UI-SPEC).

**frontend/src/hooks/useTrade.ts** — Extended with `submitBracketTrade(params: BracketOrderParams)` posting to `/api/trades/bracket`. Original `submitTrade` function preserved unchanged. Both paths share the single `isSubmitting` state.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `npx tsc --noEmit`: exits 0 (clean)
- `grep -c "BracketOrderParams" frontend/src/types.ts`: 1
- `grep -c "LivePriceData" frontend/src/types.ts`: 1
- `grep -c "useLivePrice" frontend/src/hooks/useLivePrice.ts`: 1

## Known Stubs

None — types and hooks are complete interfaces with no placeholder values. The `/api/price/{ticker}/live` and `/api/trades/bracket` endpoints are backend concerns addressed in other plans.

## Self-Check: PASSED
