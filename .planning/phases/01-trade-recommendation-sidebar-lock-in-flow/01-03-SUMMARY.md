---
phase: 01-trade-recommendation-sidebar-lock-in-flow
plan: "03"
subsystem: trade-execution
tags: [alpaca, bracket-orders, oco, close-reason, manual-close]
dependency_graph:
  requires: ["01-01", "01-02"]
  provides: [bracket-order-submission, close-reason-detection, manual-close-endpoint]
  affects: [api/trade_routes.py, frontend/src/hooks/useTradeStatus.ts]
tech_stack:
  added: []
  patterns:
    - "Alpaca bracket order: LimitOrderRequest/MarketOrderRequest + OrderClass.BRACKET + TakeProfitRequest + StopLossRequest"
    - "Nested order fetch: GetOrderByIdRequest(nested=True) to inspect bracket leg status"
    - "Frontend slow-poll after fill: clearInterval + setInterval(poll, 10000)"
key_files:
  created: []
  modified:
    - api/trade_routes.py
    - frontend/src/hooks/useTradeStatus.ts
decisions:
  - "Bracket leg IDs stored at submission time via order.legs iteration, with type-based (limit/stop) identification and positional fallback"
  - "Expired entry orders get close_reason=Expired with no outcome (D-12 — entry never filled = no trade)"
  - "poll_trade_status uses nested=True on every call after fill to detect OCO leg completion; this is correct per Alpaca bracket order lifecycle"
  - "useTradeStatus removes filled from TERMINAL_STATUSES — bracket orders must continue polling past entry fill to detect TP/SL leg resolution"
  - "Post-fill slow polling (10s) reduces Alpaca rate limit pressure during the potentially long wait for bracket legs"
metrics:
  duration: "3min"
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_modified: 2
---

# Phase 01 Plan 03: Bracket Order Execution, Close-Reason Detection, Manual Close Summary

**One-liner:** Bracket order execution engine using Alpaca OCO orders with TP/SL leg IDs stored at submission, close-reason auto-detected from leg fill status, manual close cancels OCO then market-closes, and auto-close system removed entirely.

## What Was Built

### Task 1: Bracket Order Submission + Close-Reason Detection + Manual Close (api/trade_routes.py)

**New endpoint `POST /api/trades/bracket`:** Constructs an Alpaca bracket order (parent LimitOrder or MarketOrder + OCO legs via OrderClass.BRACKET). At submission, `order.legs` is iterated to extract TP and SL order IDs (by order_type: limit=TP, stop=SL, with positional fallback). These are stored as `bracket_tp_order_id` / `bracket_sl_order_id` on the Trade record.

**Updated `GET /api/trades/{ticker}/status`:** Now fetches with `GetOrderByIdRequest(nested=True)` to receive bracket leg data. When trade is `filled` and no `close_reason` exists, inspects legs for `OrderStatus.FILLED`. Matches filled leg ID against stored TP/SL IDs to set `close_reason` as `"Target Hit"` or `"Stop-Loss"`, computes P&L, sets outcome, and transitions trade to `"closed"`. Expired unfilled entries are set to `status="expired"` with `close_reason="Expired"` and no outcome (D-12).

**New endpoint `POST /api/trades/{ticker}/close`:** Cancels both OCO bracket legs (ignoring errors for already-filled/canceled legs), then calls `client.close_position()` to market-close the equity position. Sets `close_reason="Manual Close"`, computes P&L if close price is available, transitions to `"closed"`.

**Removed:** `POST /api/trades/check-autoclose` endpoint, `_trading_days_since` helper function, and `exchange_calendars` + `pandas` imports (D-10).

### Task 2: useTradeStatus Bracket Lifecycle Support (frontend/src/hooks/useTradeStatus.ts)

- `TERMINAL_STATUSES` changed from `['filled', 'rejected', 'error']` to `['rejected', 'error', 'closed', 'expired']` — `filled` removed so polling continues after entry fill, `closed` and `expired` added as true terminal states.
- `INITIAL_STATUS` now includes `close_reason: null`.
- Poll response mapping includes `close_reason: data.close_reason ?? null`.
- After receiving `status === 'filled'`, clears the 3s interval and replaces it with a 10s interval to reduce Alpaca rate limit pressure while waiting for bracket leg resolution.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Store bracket leg IDs at submission time | Avoids re-fetching and parsing leg structure on every poll; IDs are stable after order creation |
| Type-based leg identification (limit=TP, stop=SL) with positional fallback | Alpaca returns `order_type` on legs; fallback handles any edge case where type is null |
| `nested=True` on every status poll (not just after fill) | Simpler code; Alpaca returns empty `legs` array for non-bracket orders, so it is harmless for legacy trades |
| Remove `exchange_calendars` + `pandas` imports | Only used by the auto-close system being removed; no other consumers |
| `filled` removed from frontend TERMINAL_STATUSES | Bracket order lifecycle: entry fill is intermediate state, not terminal — position closes when a bracket leg fills |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functionality is wired end-to-end. Backend detects close_reason from live Alpaca bracket leg data. Frontend reads and stores close_reason in TradeStatus state.

## Self-Check: PASSED

Files verified:
- `api/trade_routes.py` — exists, contains all required patterns (bracket endpoint, TakeProfitRequest, StopLossRequest, GetOrderByIdRequest nested, close_reason strings, manual close endpoint, no check-autoclose)
- `frontend/src/hooks/useTradeStatus.ts` — exists, TERMINAL_STATUSES excludes filled, includes closed/expired, INITIAL_STATUS has close_reason, poll maps close_reason, slow-poll at 10s after fill

Commits verified:
- `3906df1` — feat(01-03): bracket order submission, close-reason detection, manual close
- `2d3aa43` — feat(01-03): update useTradeStatus for bracket order lifecycle
