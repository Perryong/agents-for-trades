---
phase: 13-tradingview-chart-integration
plan: "02"
subsystem: frontend
tags: [chart, lightweight-charts, alpaca, react, typescript]
dependency_graph:
  requires: []
  provides: [ChartScreen, ChartContainer, useChartData, ChartTickerPicker]
  affects: [frontend/src/App.tsx]
tech_stack:
  added: [lightweight-charts@5.1.0]
  patterns: [useRef+useEffect chart lifecycle, client-side Map cache, Alpaca Market Data API direct fetch]
key_files:
  created:
    - frontend/src/hooks/useChartData.ts
    - frontend/src/components/ChartContainer.tsx
    - frontend/src/components/ChartTickerPicker.tsx
    - frontend/src/components/ChartScreen.tsx
  modified:
    - frontend/src/types.ts
    - frontend/src/App.tsx
    - frontend/package.json
decisions:
  - "lightweight-charts v5 addSeries(CandlestickSeries) API used — not deprecated addCandlestickSeries()"
  - "priceScaleId='' for volume overlay panel to avoid conflicts with price scale"
  - "Unix timestamps for 15Min bars, date strings for daily bars (lightweight-charts requirement)"
metrics:
  duration: "3 minutes"
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 7
---

# Phase 13 Plan 02: Chart Screen — Candlestick + Volume Chart Summary

Candlestick + volume chart screen with 5 timeframe presets, ticker search, and client-side caching, using lightweight-charts v5.1.0 and Alpaca Market Data API direct browser fetch.

## What Was Built

### Task 1: Install lightweight-charts, create types and useChartData hook
- Installed `lightweight-charts@5.1.0` into `frontend/package.json`
- Appended `ChartTimeframe`, `AlpacaBar`, `ChartOverlay`, and `TIMEFRAME_CONFIG` to `frontend/src/types.ts`
- Created `frontend/src/hooks/useChartData.ts` — fetches Alpaca `/v2/stocks/{ticker}/bars`, transforms to `CandlestickData[]` + `HistogramData[]`, uses `useRef(new Map())` cache keyed by `${ticker}-${timeframe}`
- **Commit:** `9aa3934`

### Task 2: Create ChartContainer, ChartTickerPicker, ChartScreen and wire into App.tsx
- Created `frontend/src/components/ChartContainer.tsx` — `createChart` + `CandlestickSeries` + `HistogramSeries` via `useRef`+`useEffect`, cleanup with `chart.remove()`, resize observer
- Created `frontend/src/components/ChartTickerPicker.tsx` — wraps `TickerAutocomplete`, persists recent tickers (max 5) to `localStorage['chart_recent_tickers']`
- Created `frontend/src/components/ChartScreen.tsx` — ticker picker + 5 timeframe toggle buttons (1D/1M/3M/6M/1Y), loading spinner, error display, chart render
- Updated `frontend/src/App.tsx` — extended `mainSection` type to `'analysis' | 'screener' | 'chart'`, added Chart tab button and `<ChartScreen dark={dark} />` section
- **Commit:** `ade4134`

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `addSeries(CandlestickSeries)` v5 API | v5 removed `addCandlestickSeries()`; using the correct factory pattern from the plan |
| `priceScaleId: ''` for volume | Assigns volume to an overlay panel separate from the main price scale, matching the plan's margin spec |
| Unix timestamps for 15Min bars | lightweight-charts requires numeric time for intraday bars; date strings only work for daily+ |
| Default timeframe: 6M | Per D-25 passive mode — shows meaningful history without overwhelming detail |

## Verification Results

- `npx tsc --noEmit` — exits 0 (no type errors)
- `npm run build` — exits 0, bundle: 499.82 kB JS (155 kB gzip), 22.84 kB CSS

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. Chart fetches live data from Alpaca when `VITE_ALPACA_KEY` and `VITE_ALPACA_SECRET` env vars are present. Empty ticker state shows a prompt rather than stub data.

## Self-Check: PASSED
