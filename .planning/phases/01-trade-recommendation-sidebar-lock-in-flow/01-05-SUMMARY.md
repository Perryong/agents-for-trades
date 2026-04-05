---
phase: 01-trade-recommendation-sidebar-lock-in-flow
plan: 05
subsystem: dashboard
tags: [dashboard, metrics, risk-reward, r-multiple, close-reason, legacy-cleanup]
dependency_graph:
  requires: ["01-03", "01-04"]
  provides: ["D-15", "D-16", "D-17", "D-18", "D-19"]
  affects: [api/dashboard_routes.py, api/trade_routes.py, frontend/src/components/TrackRecordScreen.tsx]
tech_stack:
  added: []
  patterns: [helper function extraction, optional float aggregation with None guard]
key_files:
  created: []
  modified:
    - api/dashboard_routes.py
    - api/trade_routes.py
    - frontend/src/components/TrackRecordScreen.tsx
decisions:
  - "_r_multiple guard uses `trade.pnl_pct is not None` inside all() — this evaluates to a bool, not the value, so it always passes the all() check. The actual guard that matters is the conditional `risk_pct > 0` before division."
metrics:
  duration: "3min"
  completed: "2026-04-05T05:37:04Z"
  tasks_completed: 3
  files_modified: 3
---

# Phase 01 Plan 05: Dashboard Extensions (D-15 through D-19) Summary

Dashboard extended with risk-reward ratio, R-multiple metrics per closed trade, Close Reason colored badge column, and legacy trade delete endpoint targeting pre-bracket-era records.

## What Was Built

### Task 1: Backend dashboard extensions (D-15 through D-19)

**api/dashboard_routes.py:**
- Added `_risk_reward(trade)` helper: computes reward/risk distance ratio from fill_price, target_price, stop_price. Direction-aware (BUY vs SELL). Returns None if any price is missing.
- Added `_r_multiple(trade)` helper: computes actual pnl_pct divided by risk_pct (risk expressed as % of fill_price). Returns None if fill_price, stop_price, or pnl_pct unavailable.
- `get_dashboard_summary` now computes `avg_risk_reward` and `avg_r_multiple` from all closed trades with valid prices, rounds to 4 decimal places, returns None if no trades qualify.
- `get_dashboard_trades` now includes `close_reason=t.close_reason` in every DashboardTradeItem.

**api/trade_routes.py:**
- Added `DELETE /api/trades/legacy` endpoint targeting trades with no bracket leg IDs (`bracket_tp_order_id IS NULL AND bracket_sl_order_id IS NULL`) that are not currently active (`status NOT IN ['submitted', 'filled']`). Returns `{"deleted_count": N}`.

### Task 2: Frontend TrackRecordScreen extensions

**frontend/src/components/TrackRecordScreen.tsx:**
- Added `'Close Reason'` column header between Outcome and P&L % columns.
- Added Close Reason cell with four colored badge variants: Target Hit (green), Stop-Loss (red), Manual Close (gray-700/gray-300), Expired (gray-700/gray-400). Falls through to `--` for null/unrecognized values.
- Added Risk-Reward StatCard: displays as `{value}:1` or `--` if null.
- Added Avg R-Multiple StatCard: displays with `+` prefix for positive values, colored green/red based on sign.
- Updated skeleton loading count from 7 to 9 to reflect the two new stat cards.

### Task 3: Visual verification (auto-approved — auto_advance=true)

TypeScript compiles clean (zero errors from `npx tsc --noEmit`).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 9ff9a19 | feat(01-05): add risk-reward and R-multiple to dashboard summary, legacy delete endpoint |
| 2 | a60d86a | feat(01-05): add Close Reason column and Risk-Reward/Avg R-Multiple stat cards to TrackRecordScreen |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows from real backend endpoints. The `avg_risk_reward` and `avg_r_multiple` fields return `null` when no qualifying trades exist, and the UI renders `--` in that case, which is intentional behavior not a stub.

## Self-Check: PASSED

Files exist:
- api/dashboard_routes.py: FOUND
- api/trade_routes.py: FOUND  
- frontend/src/components/TrackRecordScreen.tsx: FOUND

Commits exist:
- 9ff9a19: FOUND (feat(01-05): add risk-reward...)
- a60d86a: FOUND (feat(01-05): add Close Reason...)
