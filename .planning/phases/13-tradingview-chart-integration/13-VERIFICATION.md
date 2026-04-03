---
phase: 13-tradingview-chart-integration
verified: 2026-04-03T12:00:00Z
status: human_needed
score: 12/12 must-haves verified
re_verification: false
human_verification:
  - test: "Run full analysis on a ticker, observe auto-navigation"
    expected: "After analysis completes, browser switches to Chart tab with ticker pre-loaded and overlay active mode rendered (or passive if no eval_results yet)"
    why_human: "Requires running the full analysis pipeline with actual backend; cannot trace auto-nav useEffect behavior from static code"
  - test: "Load AAPL chart with eval_results/AAPL logs present — verify active mode overlay"
    expected: "If take_profit/stop_loss were extracted: green dashed TP line and red dashed SL line appear on chart. Entry dot appears at analysis_date when entry_price was extracted. Expiry arrowDown marker appears when options_legs contains a date."
    why_human: "TP/SL rendering depends on regex extraction from prose. For most real logs these fields will be null, making annotation rendering untestable without live data."
  - test: "Verify timeframe cache behavior"
    expected: "Switching from 6M to 1M and back to 6M shows 6M data instantly (no spinner/re-fetch)"
    why_human: "Client-side Map cache stored in useRef — not inspectable from static analysis. Requires network DevTools observation in browser."
  - test: "Verify dark mode chart colors"
    expected: "Toggling dark mode while Chart tab is active causes chart grid lines and text color to update to dark-mode values (#9ca3af text, #374151 grid)"
    why_human: "Chart is destroyed and recreated on dark prop change (useEffect dep includes dark). Visual check required."
  - test: "Verify 'View Full Analysis' link in action panel"
    expected: "When active mode is visible and user clicks 'View Full Analysis', browser switches to Analysis tab"
    why_human: "onViewAnalysis callback chain (ChartActionPanel -> ChartScreen -> App.tsx setMainSection) requires runtime browser verification."
---

# Phase 13: TradingView Chart Integration — Verification Report

**Phase Goal:** Users can visually orient any analyzed ticker with an interactive price chart showing candlesticks, volume, timeframes, and per-agent signal annotations
**Verified:** 2026-04-03T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All 12 derived truths from the three PLANs are VERIFIED at the code level.

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | GET /api/chart/{ticker}/overlay returns 404 when no analysis logs exist | VERIFIED | `chart_routes.py:91-95` raises HTTPException 404 when dir missing or no glob matches |
| 2 | GET /api/chart/{ticker}/overlay returns ChartOverlayResponse with signal, analysis_date, price fields when logs exist | VERIFIED | `chart_routes.py:108-119` constructs and returns full `ChartOverlayResponse` from parsed log |
| 3 | Overlay endpoint reads most recent log file when multiple exist | VERIFIED | `chart_routes.py:93,97` — `sorted(glob)[-1]` selects latest by filename |
| 4 | User sees a Chart tab in the top navigation bar alongside Analysis and Screener | VERIFIED | `App.tsx:121-131` — three tab buttons with `setMainSection('chart')` |
| 5 | User can type a ticker and see a candlestick chart with OHLCV data from Alpaca | VERIFIED | `useChartData.ts:70-80` — fetches `data.alpaca.markets/v2/stocks/{ticker}/bars` with APCA headers; `ChartScreen.tsx:98-99` renders ChartContainer when bars exist |
| 6 | User sees volume bars displayed below the candlestick chart | VERIFIED | `ChartContainer.tsx:61-68` — HistogramSeries with `priceScaleId: ''` and `scaleMargins: { top: 0.7, bottom: 0 }` |
| 7 | User can click 1D, 1M, 3M, 6M, 1Y preset buttons and the chart re-renders | VERIFIED | `ChartScreen.tsx:62-75` — maps TIMEFRAMES array to buttons with `setTimeframe`; useChartData dep array `[ticker, timeframe]` triggers re-render |
| 8 | Switching timeframes uses client-side cache — no re-fetch for previously loaded combinations | VERIFIED | `useChartData.ts:37,51-57` — `useRef(new Map())` cache hit returns immediately without fetch |
| 9 | After analysis completes, user is auto-navigated to Chart screen with ticker pre-loaded | VERIFIED | `App.tsx:48-55` — `useEffect` on `state.status`, sets `chartTicker` and `setMainSection('chart')` when `'done'`; `lastAnalyzedTicker.current` captured in `handleAnalyze` |
| 10 | In active mode, TP dashed green line, SL dashed red line, entry marker, expiry marker render on chart | VERIFIED | `ChartContainer.tsx:73-123` — `createPriceLine` for TP/SL, `createSeriesMarkers` for entry/expiry with correct colors/styles |
| 11 | In active mode, user sees a pinned bottom action panel with recommendation details and View Full Analysis link | VERIFIED | `ChartScreen.tsx:103-109` — `ChartActionPanel` rendered when `isActiveMode`; `ChartActionPanel.tsx:67-71` contains "View Full Analysis" button |
| 12 | User can cross-navigate: Analysis has View Chart button, Chart has View Full Analysis link | VERIFIED | `App.tsx:186-200` — "View Chart →" after `state.status === 'done'`; `ChartActionPanel.tsx:67-71` — "View Full Analysis" calls `onViewAnalysis` |

**Score:** 12/12 truths verified

---

## Required Artifacts

### Plan 01 Artifacts (Backend)

| Artifact | Status | Details |
|----------|--------|---------|
| `api/chart_routes.py` | VERIFIED | Exists, substantive (120 lines), `chart_router` exported, `get_chart_overlay` implemented, `_extract_signal` and helpers present |
| `api/schemas.py` | VERIFIED | `ChartOverlayResponse` present at line 57-67 with all 10 required fields |
| `tests/api/test_chart_routes.py` | VERIFIED | Exists, 9 tests including `test_overlay_404_no_logs`, `test_overlay_returns_data`, `test_overlay_reads_latest_log` |
| `tests/api/test_chart_schemas.py` | VERIFIED | Exists, 6 tests including `test_overlay_schema` prefix tests |

### Plan 02 Artifacts (Frontend Passive Mode)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/components/ChartScreen.tsx` | VERIFIED | Exists, 112 lines, `ChartScreen` export, uses `useChartData`, `useOverlay`, `ChartContainer`, `ChartTickerPicker`, all 5 timeframe buttons |
| `frontend/src/components/ChartContainer.tsx` | VERIFIED | Exists, 143 lines, `createChart`, `CandlestickSeries`, `HistogramSeries`, `priceScaleId`, `chart.remove()` cleanup, resize observer |
| `frontend/src/hooks/useChartData.ts` | VERIFIED | Exists, 128 lines, `useChartData` export, `data.alpaca.markets` URL, `VITE_ALPACA_KEY`, `new Map()` cache |
| `frontend/src/components/ChartTickerPicker.tsx` | VERIFIED | Exists, 65 lines, `chart_recent_tickers` localStorage key, wraps `TickerAutocomplete` |
| `frontend/src/types.ts` | VERIFIED | `ChartTimeframe`, `AlpacaBar`, `ChartOverlay`, `TIMEFRAME_CONFIG` all present (lines 112-144) |
| `frontend/package.json` | VERIFIED | `"lightweight-charts": "^5.1.0"` present; `node_modules/lightweight-charts/` confirmed present |

### Plan 03 Artifacts (Overlay / Active Mode)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/hooks/useOverlay.ts` | VERIFIED | Exists, 49 lines, `useOverlay` export, fetches `/api/chart/${ticker}/overlay`, 404 -> null (passive mode), other errors -> null + console.error |
| `frontend/src/components/ChartActionPanel.tsx` | VERIFIED | Exists, 77 lines, `ChartActionPanel` export, "View Full Analysis" button, disabled "Confirm Trade" with `title="Available in Phase 14"`, `SignalBadge` with BUY/SELL/HOLD colors |
| `frontend/src/components/ChartContainer.tsx` | VERIFIED | Extended with `overlay?: ChartOverlay | null` prop; `createPriceLine` (TP green, SL red), `createSeriesMarkers` (entry circle, expiry arrowDown), `LineStyle.Dashed` — all present |
| `frontend/src/App.tsx` | VERIFIED | `lastAnalyzedTicker` ref, `chartTicker` state, `setMainSection('chart')` in useEffect, "View Chart →" cross-link, `initialTicker={chartTicker}` and `onViewAnalysis` passed to ChartScreen |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api/main.py` | `api/chart_routes.py` | `app.include_router(chart_router)` | WIRED | `main.py:24-25` — import and registration confirmed |
| `api/chart_routes.py` | `eval_results/{ticker}/TradingAgentsStrategy_logs/` | `Path glob for full_states_log_` | WIRED | `chart_routes.py:18-24,93` — `_log_dir` builds path; `glob.glob(str(log_directory / "full_states_log_*.json"))` |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `useChartData.ts` | `data.alpaca.markets/v2/stocks/{ticker}/bars` | fetch with APCA headers | WIRED | `useChartData.ts:70-84` — URL construction and fetch with `VITE_ALPACA_KEY`/`VITE_ALPACA_SECRET` headers |
| `ChartContainer.tsx` | `lightweight-charts` | `import { createChart, CandlestickSeries, HistogramSeries }` | WIRED | `ChartContainer.tsx:2` — exact import confirmed |
| `ChartScreen.tsx` | `useChartData.ts` | `useChartData(ticker, timeframe)` | WIRED | `ChartScreen.tsx:33` — called with ticker + timeframe state |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `useOverlay.ts` | `/api/chart/{ticker}/overlay` | fetch call | WIRED | `useOverlay.ts:22` — `fetch(\`/api/chart/${ticker}/overlay\`)` |
| `ChartContainer.tsx` | `useOverlay.ts` | overlay prop from ChartScreen | WIRED | `ChartScreen.tsx:99` passes `overlay={overlay}`; `ChartContainer.tsx:71` checks `if (overlay)` and calls `createPriceLine`/`createSeriesMarkers` |
| `App.tsx` | `ChartScreen.tsx` | auto-navigate on analysis complete | WIRED | `App.tsx:48-55` — `useEffect` on `state.status` sets `setMainSection('chart')` with `lastAnalyzedTicker` |

---

## Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|---------|
| CHART-01 | 13-01, 13-02 | User can view candlestick price chart for any analyzed ticker | SATISFIED | `chart_routes.py` serves overlay data; `ChartContainer.tsx` renders `CandlestickSeries`; `useChartData.ts` fetches Alpaca bars |
| CHART-02 | 13-02 | User can view volume bars below the candlestick chart | SATISFIED | `ChartContainer.tsx:61-68` — `HistogramSeries` with `priceScaleId: ''` and `scaleMargins: { top: 0.7 }` |
| CHART-04 | 13-02, 13-03 | User can toggle between daily, weekly, and monthly timeframes | SATISFIED | Five preset buttons (1D/1M/3M/6M/1Y) in `ChartScreen.tsx`; RESEARCH.md D-19 documents this intentional mapping from "daily/weekly/monthly" to the 5 presets |
| CHART-05 | 13-01, 13-03 | User can see per-agent bull/bear signal annotations at the decision point | SATISFIED (with scope note) | TP/SL price lines, entry marker, expiry marker in `ChartContainer.tsx`; `useOverlay.ts` + `/api/chart/{ticker}/overlay`; CONTEXT.md D-15 documents intentional scope reduction to summary-level consensus signal only (per-agent breakdown deferred) |

**Orphaned Requirements Check:** CHART-03 (paper trade entry/exit markers) is NOT claimed by any Phase 13 plan — correctly scoped to Phase 14 per REQUIREMENTS.md traceability table and CONTEXT.md line 140.

---

## Anti-Patterns Scan

Files scanned: `api/chart_routes.py`, `api/schemas.py`, `api/main.py`, `tests/api/test_chart_routes.py`, `tests/api/test_chart_schemas.py`, `frontend/src/hooks/useChartData.ts`, `frontend/src/hooks/useOverlay.ts`, `frontend/src/components/ChartContainer.tsx`, `frontend/src/components/ChartScreen.tsx`, `frontend/src/components/ChartTickerPicker.tsx`, `frontend/src/components/ChartActionPanel.tsx`, `frontend/src/App.tsx`, `frontend/src/types.ts`

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `ChartActionPanel.tsx` | 60-65 | "Confirm Trade" button disabled | INFO | Intentional Phase 13 placeholder per D-29 — not a stub; the button is meant to be non-functional until Phase 14 |

No unintentional TODOs, FIXME, empty returns, or orphaned state variables found. The `overlay?.take_profit === null` fallback in `ChartContainer.tsx` correctly skips annotation rendering rather than rendering fake data — this is the designed behavior per PLAN 03 specification.

---

## Human Verification Required

### 1. Auto-navigation on Analysis Completion

**Test:** Run a full analysis on any ticker. Wait for it to complete.
**Expected:** Browser switches to Chart tab with the analyzed ticker pre-loaded (ticker input shows the symbol). If eval_results exist for that ticker, active mode action panel appears at bottom.
**Why human:** The `useEffect` watching `state.status === 'done'` fires asynchronously at runtime. Static code confirms the logic is wired, but the actual tab transition and ticker population require browser observation.

### 2. Active Mode Overlay Rendering (Requires eval_results Data)

**Test:** Start the app with existing `eval_results/AAPL/TradingAgentsStrategy_logs/` data. Navigate to Chart tab, enter "AAPL".
**Expected:** If the log's `final_trade_decision` contained parseable take_profit/stop_loss values: green dashed TP line and red dashed SL line appear on the chart. Signal badge in action panel shows correct BUY/SELL/HOLD. Analysis date shown correctly.
**Why human:** TP/SL rendering depends on regex extraction succeeding against actual prose text. Per plan specification and SUMMARY.md, most real logs will have `null` for these fields, making annotation rendering conditional and data-dependent.

### 3. Client-Side Cache (No Re-fetch on Timeframe Switch-Back)

**Test:** Load AAPL chart on 6M. Switch to 1M (observe loading spinner). Switch back to 6M.
**Expected:** Switching back to 6M shows data immediately with no loading spinner (cache hit).
**Why human:** The `useRef(new Map())` cache is an in-memory structure not observable from static analysis. Requires network DevTools tab in browser to confirm no second Alpaca request fires.

### 4. Dark Mode Chart Color Adaptation

**Test:** Open Chart tab with a chart rendered. Toggle dark mode via the moon/sun button in the sidebar.
**Expected:** Chart grid lines change from `#e5e7eb` to `#374151`, text color changes from `#4b5563` to `#9ca3af`. Chart is visually correct.
**Why human:** The `dark` prop is in `ChartContainer`'s useEffect dep array, triggering chart recreation. Visual color accuracy requires a human observer.

### 5. "View Full Analysis" Cross-Link Navigation

**Test:** When active mode action panel is visible (requires ticker with eval_results), click "View Full Analysis".
**Expected:** App switches to the Analysis tab displaying the previous analysis results.
**Why human:** The `onViewAnalysis` callback chain traverses ChartActionPanel -> ChartScreen -> App.tsx. The prop-threading is confirmed in code, but the UX transition requires runtime verification.

---

## Gaps Summary

No gaps found. All 12 must-have truths are verified. All required artifacts exist, are substantive, and are wired. All key links confirmed present and connected. All 4 requirement IDs (CHART-01, CHART-02, CHART-04, CHART-05) have implementation evidence. The 5 human verification items require runtime/browser observation and cannot be confirmed from static code analysis alone — they do not indicate missing implementation, only untestable runtime behavior.

**One scope note on CHART-05:** CONTEXT.md D-15 explicitly scopes the annotation to "summary-level only — final consensus output, not per-agent signals." The requirement text says "per-agent bull/bear signal annotations" but the phase context document narrows this to a single consensus signal at the decision point. This was an intentional scope decision made before implementation. The implementation fully satisfies the narrowed scope.

---

_Verified: 2026-04-03T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
