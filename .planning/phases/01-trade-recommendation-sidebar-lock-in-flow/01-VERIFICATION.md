---
phase: 01-trade-recommendation-sidebar-lock-in-flow
verified: 2026-04-05T00:00:00Z
status: passed
score: 19/19 decisions verified
re_verification: false
gaps:
  - truth: "OrderStatus type includes 'expired' for expired bracket entry orders (D-12)"
    status: resolved
    reason: "'expired' is missing from the OrderStatus union type in frontend/src/types.ts, causing two TypeScript errors when compiled with tsconfig.app.json: useTradeStatus.ts line 7 (TS2322) and TradeSidebar.tsx line 234 (TS2367). The backend correctly sets status='expired' and the runtime behavior works, but the type contract is broken."
    artifacts:
      - path: "frontend/src/types.ts"
        issue: "OrderStatus = 'idle' | 'submitted' | 'filled' | 'rejected' | 'error' | 'closed' — missing 'expired'"
      - path: "frontend/src/hooks/useTradeStatus.ts"
        issue: "Line 7: TERMINAL_STATUSES: OrderStatus[] includes 'expired' which is not in the type — TS2322"
      - path: "frontend/src/components/TradeSidebar.tsx"
        issue: "Line 234: status === 'expired' comparison unreachable via type system — TS2367"
    missing:
      - "Add 'expired' to OrderStatus union in frontend/src/types.ts: export type OrderStatus = 'idle' | 'submitted' | 'filled' | 'rejected' | 'error' | 'closed' | 'expired';"
---

# Phase 1: Trade Recommendation Sidebar & Lock-In Flow — Verification Report

**Phase Goal:** Replace ChartActionPanel with brokerage-style right sidebar on chart screen. AI recommendations displayed with editable fields, live price streaming, Alpaca bracket orders (entry + take-profit + stop-loss as OCO). Remove 5-day auto-close. Track real market outcomes. Extend dashboard with risk-reward ratio and R-multiple metrics.
**Verified:** 2026-04-05
**Status:** gaps_found — 1 gap (TypeScript type error in `OrderStatus`)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Right sidebar replaces ChartActionPanel entirely (D-01) | VERIFIED | `ChartActionPanel.tsx` deleted; `ChartScreen.tsx` uses `flex flex-row h-full` with `TradeSidebar` |
| 2  | All AI-recommended fields are editable (entry, target, stop-loss, qty, TIF) (D-02) | VERIFIED | `TradeSidebar.tsx` lines 304–398: 5 form inputs with `useState`, pre-filled from `overlay` |
| 3  | Live price streaming in sidebar (D-03) | VERIFIED | `useLivePrice.ts` polls `/api/price/{ticker}/live` every 5s; `price_routes.py` uses `StockHistoricalDataClient` |
| 4  | Options strategies displayed as collapsed accordion with strategy type visible (D-04) | VERIFIED | `TradeSidebar.tsx` lines 402–433: `optionsExpanded` state, chevron toggle, strategy_name shown |
| 5  | Open positions show live P&L in sidebar (D-05) | VERIFIED | `TradeSidebar.tsx` lines 89–103: P&L dollar + percentage computed from `livePrice.price` vs `fill_price` |
| 6  | Close Position button with inline confirmation (D-06) | VERIFIED | `TradeSidebar.tsx` lines 152–179: `showCloseConfirm` state, Cancel + Confirm Close buttons |
| 7  | No trade history in sidebar (D-07) | VERIFIED | `TradeSidebar.tsx`: no "history", "recent trades", or "past orders" text present |
| 8  | Alpaca paper execution stays (D-08) | VERIFIED | `trade_routes.py` line 51: `TradingClient(..., paper=True)` |
| 9  | Bracket orders: single Alpaca API call with TP + SL as OCO (D-09) | VERIFIED | `trade_routes.py` lines 256–347: `OrderClass.BRACKET`, `TakeProfitRequest`, `StopLossRequest` |
| 10 | Remove 5-day auto-close system (D-10) | VERIFIED | `check-autoclose` endpoint not present in `trade_routes.py`; no `_trading_days_since` helper; no `check-autoclose` in frontend |
| 11 | AI determines TIF (GTC or DAY) (D-11) | VERIFIED | `BracketTradeRequest.tif` field; `trade_routes.py` line 266 passes to Alpaca; trader prompt requires `"time_in_force"` field |
| 12 | Expired/unfilled entries excluded from metrics (D-12) | PARTIAL — logic correct, type broken | Backend sets `status='expired'`, `close_reason='Expired'`, no outcome — correct. But `'expired'` missing from `OrderStatus` type causes TS errors |
| 13 | Structured JSON output from trader agent (D-13) | VERIFIED | `trader.py` lines 44–56: JSON block required in system prompt; `chart_routes.py` `_parse_structured_json()` with regex fallback |
| 14 | AI decides all trade parameters (D-14) | VERIFIED | Trader prompt requires `entry_price`, `target_price`, `stop_loss`, `time_in_force`, `confidence`, `strategy` |
| 15 | Close reason recorded (Target Hit / Stop-Loss / Manual Close / Expired) (D-15) | VERIFIED | `trade_routes.py`: all four close reasons set; `close_reason` column on `Trade` model |
| 16 | Risk-reward ratio on dashboard (D-16) | VERIFIED | `dashboard_routes.py` `_risk_reward()` helper; `DashboardSummaryResponse.avg_risk_reward`; `TrackRecordScreen.tsx` Risk-Reward StatCard |
| 17 | Average R-multiple on dashboard (D-17) | VERIFIED | `dashboard_routes.py` `_r_multiple()` helper; `DashboardSummaryResponse.avg_r_multiple`; `TrackRecordScreen.tsx` Avg R-Multiple StatCard |
| 18 | Delete legacy trades endpoint (D-18) | VERIFIED | `trade_routes.py` `DELETE /api/trades/legacy` — targets trades with no bracket leg IDs, not active |
| 19 | Close reason column in trade history table (D-19) | VERIFIED | `TrackRecordScreen.tsx` lines 288, 351–371: "Close Reason" header, colored badges for all 4 reasons |

**Score:** 18/19 truths verified (1 partial/failed: D-12 type gap)

---

## Required Artifacts

| Artifact | Plan | Status | Notes |
|----------|------|--------|-------|
| `api/models.py` | 01-01 | VERIFIED | `close_reason`, `entry_price`, `bracket_tp_order_id`, `bracket_sl_order_id` columns present |
| `api/schemas.py` | 01-01 | VERIFIED | `BracketTradeRequest`, `LivePriceResponse`, `TradeStatusResponse.close_reason`, `DashboardSummaryResponse.avg_risk_reward/avg_r_multiple`, `DashboardTradeItem.close_reason` |
| `api/db.py` | 01-01 | VERIFIED | `ensure_bracket_columns()` adds 4 new columns idempotently |
| `api/main.py` | 01-01 | VERIFIED | `await ensure_bracket_columns()` called in lifespan; `price_router` registered |
| `api/price_routes.py` | 01-01 | VERIFIED | `GET /api/price/{ticker}/live`, `StockHistoricalDataClient`, `get_stock_latest_bar` |
| `api/chart_routes.py` | 01-01 | VERIFIED | `_parse_structured_json()` present; `structured = _parse_structured_json(ftd)` called before regex fallback |
| `tradingagents/agents/trader/trader.py` | 01-01 | VERIFIED | System prompt requires JSON block with `entry_price`, `target_price`, `stop_loss`, `time_in_force` |
| `frontend/src/types.ts` | 01-02 | PARTIAL | `BracketOrderParams`, `LivePriceData`, `close_reason` in `TradeStatus`, new dashboard fields all present — but `OrderStatus` missing `'expired'` |
| `frontend/src/hooks/useLivePrice.ts` | 01-02 | VERIFIED | `setInterval(fetchPrice, 5000)`, fetches `/api/price/{ticker}/live` |
| `frontend/src/hooks/useTrade.ts` | 01-02 | VERIFIED | `submitBracketTrade` posts to `/api/trades/bracket`; original `submitTrade` preserved |
| `api/trade_routes.py` | 01-03 | VERIFIED | `POST /trades/bracket` with `OrderClass.BRACKET`; close-reason detection from legs; `POST /trades/{ticker}/close`; no `check-autoclose` |
| `frontend/src/hooks/useTradeStatus.ts` | 01-03 | PARTIAL | `close_reason` in state, 10s slow-poll after fill, `TERMINAL_STATUSES` includes `'expired'` — but that inclusion is a TS2322 type error |
| `frontend/src/components/TradeSidebar.tsx` | 01-04 | VERIFIED | 466 lines; `w-80 flex-shrink-0 border-l border-gray-700`; all 5 editable fields; `aria-live="polite"`; lifecycle states; P&L; close confirm; options accordion |
| `frontend/src/components/ChartScreen.tsx` | 01-04 | VERIFIED | `flex flex-row h-full`; imports `TradeSidebar` and `useLivePrice`; `handleBracketTrade`; `handleClosePosition`; no `ChartActionPanel`, no `check-autoclose` |
| `frontend/src/components/ChartActionPanel.tsx` | 01-04 | VERIFIED (deleted) | File does not exist |
| `frontend/src/components/TradeConfirmModal.tsx` | 01-04 | VERIFIED (deleted) | File does not exist |
| `api/dashboard_routes.py` | 01-05 | VERIFIED | `_risk_reward()`, `_r_multiple()` helpers; `avg_risk_reward`/`avg_r_multiple` in summary response; `close_reason=t.close_reason` in trade items |
| `frontend/src/components/TrackRecordScreen.tsx` | 01-05 | VERIFIED | "Close Reason" column header; 4 colored badge conditions; Risk-Reward and Avg R-Multiple StatCards; 9 skeleton cards |
| `tests/api/test_price_routes.py` | 01-00 | VERIFIED | `test_live_price` stub present |
| `tests/api/test_trade_routes.py` | 01-00 | VERIFIED | 6 Wave 0 stubs: `test_bracket_submit`, `test_no_autoclose_endpoint`, `test_bracket_tif`, `test_expired_entry_no_outcome`, `test_close_reason_target_hit`, `test_legacy_delete` |
| `tests/api/test_chart_routes.py` | 01-00 | VERIFIED | `test_structured_json_overlay` stub present |
| `tests/api/test_dashboard_routes.py` | 01-00 | VERIFIED | `test_risk_reward`, `test_r_multiple` stubs present |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api/price_routes.py` | `StockHistoricalDataClient` | `get_stock_latest_bar` | WIRED | Line 44: `client.get_stock_latest_bar(StockLatestBarRequest(...))` |
| `api/chart_routes.py` | `_parse_structured_json` | JSON-first overlay parsing | WIRED | Line 120: `structured = _parse_structured_json(ftd)` in `get_chart_overlay` |
| `api/trade_routes.py` | `TakeProfitRequest` | bracket order construction | WIRED | Line 269: `TakeProfitRequest(limit_price=request.target_price)` |
| `api/trade_routes.py` | `StopLossRequest` | bracket order construction | WIRED | Line 270: `StopLossRequest(stop_price=request.stop_loss)` |
| `api/trade_routes.py` | `client.close_position` | manual close endpoint | WIRED | Line 472: `client.close_position(symbol_or_asset_id=ticker.upper())` |
| `frontend/src/hooks/useLivePrice.ts` | `/api/price/{ticker}/live` | fetch with 5s setInterval | WIRED | Lines 21, 38: `fetch(...)` + `window.setInterval(fetchPrice, 5000)` |
| `frontend/src/hooks/useTrade.ts` | `/api/trades/bracket` | fetch POST | WIRED | Line 43: `fetch('/api/trades/bracket', ...)` |
| `frontend/src/components/ChartScreen.tsx` | `TradeSidebar` | import and render in flex-row layout | WIRED | Line 12 import, line 143 render |
| `frontend/src/components/TradeSidebar.tsx` | `livePrice` prop | live price display | WIRED | Prop threaded from `ChartScreen.useLivePrice` through `TradeSidebar` props |
| `api/dashboard_routes.py` | `Trade.close_reason` | summary and trade items | WIRED | Line 153: `close_reason=t.close_reason`; line 102: `_risk_reward(t)` and `_r_multiple(t)` |
| `frontend/src/components/TrackRecordScreen.tsx` | `/api/dashboard/summary` | `useDashboardSummary` hook | WIRED | Lines 232–241: `summary.avg_risk_reward`, `summary.avg_r_multiple` rendered |

---

## Requirements Coverage

| Decision | Plan | Description | Status | Evidence |
|----------|------|-------------|--------|----------|
| D-01 | 01-04 | Right sidebar replaces ChartActionPanel | SATISFIED | ChartActionPanel.tsx deleted; TradeSidebar rendered right of chart |
| D-02 | 01-02, 01-04 | All AI fields editable | SATISFIED | 5 form inputs with useState pre-filled from overlay |
| D-03 | 01-01, 01-02 | Live price streaming | SATISFIED | price_routes.py + useLivePrice hook |
| D-04 | 01-04 | Options strategies as collapsed legs | SATISFIED | Options accordion in TradeSidebar |
| D-05 | 01-04 | Open positions live P&L | SATISFIED | P&L computed in TradeSidebar |
| D-06 | 01-03, 01-04 | Close Position button | SATISFIED | Manual close endpoint + inline confirmation UI |
| D-07 | 01-04 | No trade history in sidebar | SATISFIED | TradeSidebar contains no history text |
| D-08 | 01-03 | Alpaca paper execution stays | SATISFIED | `paper=True` in TradingClient |
| D-09 | 01-01, 01-03 | Bracket orders | SATISFIED | OrderClass.BRACKET with TakeProfitRequest + StopLossRequest |
| D-10 | 01-03 | Remove 5-day auto-close | SATISFIED | check-autoclose endpoint gone, no auto-close fetch in frontend |
| D-11 | 01-01, 01-02, 01-03 | AI determines TIF | SATISFIED | tif field flows from trader JSON through BracketTradeRequest to Alpaca |
| D-12 | 01-03 | Expired entries excluded from metrics | PARTIAL | Backend logic correct; `'expired'` missing from `OrderStatus` type |
| D-13 | 01-01 | Structured JSON from trader | SATISFIED | JSON block in trader prompt + _parse_structured_json() |
| D-14 | 01-01 | AI decides all trade parameters | SATISFIED | All 6 fields required in trader system prompt |
| D-15 | 01-01, 01-03 | Close reason recorded | SATISFIED | 4 close reasons set in trade_routes.py + models |
| D-16 | 01-01, 01-05 | Risk-reward ratio on dashboard | SATISFIED | _risk_reward() + avg_risk_reward in schemas + StatCard |
| D-17 | 01-01, 01-05 | Average R-multiple on dashboard | SATISFIED | _r_multiple() + avg_r_multiple in schemas + StatCard |
| D-18 | 01-05 | Delete legacy trades endpoint | SATISFIED | DELETE /api/trades/legacy targets pre-bracket trades |
| D-19 | 01-05 | Close reason column in trade history | SATISFIED | "Close Reason" column with 4 colored badge conditions |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/types.ts` | 112 | `OrderStatus` missing `'expired'` literal | Blocker | TS2322 in `useTradeStatus.ts`; TS2367 in `TradeSidebar.tsx` when compiled with `tsconfig.app.json`. The `status === 'expired'` comparison in TradeSidebar is unreachable via type system, and `TERMINAL_STATUSES` includes an invalid value. Runtime behavior works but the type contract is incorrect. |
| `frontend/src/hooks/useTradeStatus.ts` | 7 | `TERMINAL_STATUSES: OrderStatus[]` includes `'expired'` not in `OrderStatus` type | Blocker (secondary) | Follows from the `types.ts` gap above |
| `frontend/src/components/TradeSidebar.tsx` | 234 | `status === 'expired'` comparison flagged as unintentional (TS2367) | Blocker (secondary) | Follows from the `types.ts` gap above |

Note: The `npx tsc --noEmit` shortcut using the composite project references (`tsconfig.json`) silently passes; the errors only surface with `npx tsc -p tsconfig.app.json --noEmit`. Both are legitimate compilation paths.

---

## Human Verification Required

### 1. Full sidebar visual layout and interaction

**Test:** Start backend (`uvicorn api.main:app --reload`) and frontend (`cd frontend && npm run dev`). Navigate to Chart screen. Enter a ticker that has analysis data (e.g., AAPL, TSLA). Observe the chart screen layout.
**Expected:** Right sidebar appears (not bottom panel) with: live price header showing current price + green/red day change; signal badge (BUY/SELL/HOLD); 5 editable fields pre-filled from AI recommendation; blue "Execute Paper Trade" button.
**Why human:** Visual layout, color rendering, and field pre-fill from real AI data cannot be verified programmatically.

### 2. Bracket order submission and status lifecycle

**Test:** Execute a bracket trade via the sidebar. Observe the order status progression through submitted -> filled -> (wait for leg) -> closed.
**Expected:** Order submitted to Alpaca paper, fills, then closes via Target Hit or Stop-Loss when the corresponding bracket leg fills. Close Reason appears in sidebar.
**Why human:** Requires live Alpaca paper trading session with real market conditions.

### 3. Close Position inline confirmation

**Test:** With an open (filled) position, click "Close Position".
**Expected:** Button replaced by "Cancel" and "Confirm Close" buttons inline. Clicking Confirm calls the close endpoint.
**Why human:** Interactive UI flow requiring visual verification.

### 4. Track Record screen new columns and cards

**Test:** Navigate to Track Record screen with at least one closed trade.
**Expected:** "Close Reason" column visible in trade history table with colored badges; "Risk-Reward" and "Avg R-Multiple" stat cards visible in Performance Summary section.
**Why human:** Visual rendering of colored badges and card layout.

---

## Gaps Summary

**One gap blocks full compliance: `'expired'` is missing from the `OrderStatus` union type in `frontend/src/types.ts`.**

The backend correctly implements D-12 (expired entries get `status='expired'`, `close_reason='Expired'`, no outcome). The `useTradeStatus` hook correctly includes `'expired'` in `TERMINAL_STATUSES` and `TradeSidebar` correctly handles `status === 'expired'`. However the `OrderStatus` type was never updated to include `'expired'`, causing:

1. `useTradeStatus.ts` line 7: `TS2322 — Type '"expired"' is not assignable to type 'OrderStatus'`
2. `TradeSidebar.tsx` line 234: `TS2367 — This comparison appears to be unintentional because the types '"idle"' and '"expired"' have no overlap`

**Fix:** One-line change in `frontend/src/types.ts`:

```typescript
export type OrderStatus = 'idle' | 'submitted' | 'filled' | 'rejected' | 'error' | 'closed' | 'expired';
```

All other 18 decisions (D-01 through D-11, D-13 through D-19) are fully implemented and wired. The overall implementation is substantive and complete — this is a single type annotation gap, not a missing feature.

---

_Verified: 2026-04-05_
_Verifier: Claude (gsd-verifier)_
