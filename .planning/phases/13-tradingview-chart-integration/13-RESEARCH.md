# Phase 13: TradingView Chart Integration - Research

**Researched:** 2026-04-03
**Domain:** lightweight-charts v5 + Alpaca Market Data API + FastAPI chart overlay endpoint
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Screen architecture**
- D-01: Chart Screen is a top-level peer in the app nav alongside Analysis and Screener — not a child component of analysis
- D-02: Full viewport — chart owns the entire main content area, no fixed height constraints
- D-03: Two modes: Passive (browse any stock, clean chart) and Active (agent overlays + action panel after analysis)
- D-04: Analysis completion navigates user to Chart Screen with agent layer pre-loaded
- D-05: Cross-links: Analysis has "View Chart" button; Chart has "View Full Analysis" back-link

**Chart library**
- D-06: `lightweight-charts v5.1.0` via npm — direct import, no community wrapper
- D-07: React integration via `useRef` + `useEffect` pattern (official v5 tutorial approach)

**OHLCV data delivery**
- D-08: Frontend fetches Alpaca bars API directly — no backend proxy for price data
- D-09: Alpaca endpoint: `GET https://data.alpaca.markets/v2/stocks/{ticker}/bars?timeframe=1Day&start=...&feed=iex`
- D-10: Alpaca API keys exposed to frontend via Vite env vars (`VITE_ALPACA_KEY` / `VITE_ALPACA_SECRET`)
- D-11: `ALPACA_PAPER_KEY`/`ALPACA_PAPER_SECRET` env vars serve dual purpose: chart data (Phase 13) + execution (Phase 14)

**Agent overlay data**
- D-12: New backend endpoint `GET /api/chart/{ticker}/overlay` returns agent signal data
- D-13: Overlay returns 404 = passive mode; overlay returns data = active mode
- D-14: Both fetches (Alpaca bars + backend overlay) fire in parallel on ticker load/switch

**Agent signal annotations (CHART-05)**
- D-15: Summary-level only — final consensus output, not per-agent signals
- D-16: Five visual elements: entry marker dot, TP horizontal dashed line (green), SL horizontal dashed line (red), expiry vertical dashed line (amber), strategy name label
- D-17: Data sources: entry price from Alpaca fill, TP + SL from agent final decision, expiry from options contract metadata
- D-18: Most recent analysis only by default; prior analyses available as muted grey ghost layers via toggle

**Timeframe presets**
- D-19: Five presets: 1D (15min bars, today only), 1M (1Day bars), 3M (1Day bars), 6M (1Day bars, default), 1Y (1Day bars)
- D-20: Preset toggle buttons only — no custom date range picker
- D-21: Client-side cache per ticker per timeframe — switching is instant without re-fetch

**Timeframe behavior**
- D-22: Overlay annotations persist across all timeframes
- D-23: Entry dot only renders if entry date falls within current view window; does not pin at edge
- D-24: 1D = today/most recent trading day only — historical intraday day-picker deferred
- D-25: Smart default timeframe in active mode: entry <2 weeks = 1M, <6 weeks = 3M, older = 6M. Passive defaults to 6M

**Ticker selection**
- D-26: Self-contained ticker picker on chart screen — type-to-search dropdown + recent tickers (last 5, localStorage)
- D-27: No sidebar round-trip required; selecting a ticker fires both data fetches simultaneously

**Action panel (active mode)**
- D-28: Pinned bottom panel in active mode showing: recommended strike/expiry, Confirm Trade CTA (Phase 14), View Full Analysis back-link
- D-29: Confirm Trade CTA renders as read-only recommendation display in Phase 13

### Claude's Discretion
- Chart color scheme / dark mode integration with existing Tailwind dark mode
- Exact ticker search implementation (reuse TickerAutocomplete component or new)
- Loading states and skeleton UI while Alpaca data fetches
- Ghost layer toggle UI placement and interaction
- Responsive behavior if window is narrow

### Deferred Ideas (OUT OF SCOPE)
- Historical intraday day-picker (select which day to view 15-min bars)
- Custom date range picker
- Per-agent signal annotations on chart (individual signals belong on Analysis screen)
- Confirm Trade execution button (Phase 14)
- Trade entry/exit markers from Alpaca fills (CHART-03) — Phase 14
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHART-01 | User can view candlestick price chart for any analyzed ticker | lightweight-charts v5 CandlestickSeries + Alpaca bars API direct fetch |
| CHART-02 | User can view volume bars below the candlestick chart | HistogramSeries with priceScaleId:'' + scaleMargins overlay pattern |
| CHART-04 | User can toggle between daily, weekly, and monthly timeframes | Five preset buttons; client-side Map cache keyed by `${ticker}-${timeframe}`; Alpaca timeframe param |
| CHART-05 | User can see per-agent bull/bear signal annotations at the decision point | createSeriesMarkers for entry dot; series.createPriceLine for TP/SL; ISeriesPrimitive vertical line for expiry; backend overlay endpoint |
</phase_requirements>

---

## Summary

Phase 13 integrates the TradingView `lightweight-charts` v5.1.0 library into the React frontend to create a dedicated Chart Screen — a full-viewport, peer-level navigation section alongside Analysis and Screener. The chart fetches OHLCV price data directly from the Alpaca Market Data REST API from the browser (CORS has been supported since January 2021), while agent overlay data (entry price, TP/SL/expiry) comes from a new FastAPI backend endpoint.

The key complexity is in two areas: (1) the lightweight-charts v5 API changed significantly from v4 — all series creation now uses `chart.addSeries(SeriesClass, options)`, markers require `createSeriesMarkers()` separately, and vertical lines require a custom series primitive (no built-in vertical line API); (2) the backend overlay endpoint must LLM-parse the unstructured `final_trade_decision` text to extract entry price, TP, and SL — these values are not stored as discrete fields in the current `AgentState`. The overlay endpoint reads from the `eval_results/{ticker}/TradingAgentsStrategy_logs/` JSON logs written by `TradingAgentsGraph.log_states()`.

**Primary recommendation:** Build the chart screen in three incremental layers: (1) bare chart + Alpaca data + timeframe switching, (2) volume histogram, (3) agent overlay annotations. The overlay endpoint is the highest-risk task and should be architected as a JSON extraction from the latest log file, not a database query (no DB exists yet in Phase 13).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lightweight-charts | 5.1.0 | Interactive candlestick + volume chart | Official TradingView library; no community wrapper needed for v5; 35kB base bundle |
| React | 19.2.4 | UI framework | Already in project |
| TypeScript | 5.9.3 | Type safety | Already in project |
| Tailwind CSS v4 | 4.2.2 | Styling | Already in project (Vite plugin, `dark:` variant pattern) |
| Vite | 8.0.1 | Build tool | Already in project |

### Supporting (Phase 13 additions)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none) | — | No new JS dependencies needed | lightweight-charts is the only addition |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| lightweight-charts direct | react-lightweight-charts wrapper | Wrapper targets v3/v4; v5 is breaking change — wrapper not updated; direct import is the v5-documented approach |
| Alpaca direct fetch | Backend proxy | Adds latency and backend complexity; Alpaca CORS works (fixed Jan 2021); acceptable given API keys are already intended to be in Vite env vars (paper keys, low risk) |
| Custom overlay state | Zustand/Redux | Overkill for this use case; local component state + custom hooks is sufficient given the patterns in `useAnalysis.ts` and `useScreener.ts` |

**Installation:**
```bash
cd frontend && npm install lightweight-charts@5.1.0
```

**Version verification:** `npm view lightweight-charts version` returns `5.1.0` (verified 2026-04-03, published 2025-12-16).

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── components/
│   ├── ChartScreen.tsx         # Top-level section — owns full viewport, mode state
│   ├── ChartContainer.tsx      # useRef wrapper: creates/destroys IChartApi
│   ├── ChartTickerPicker.tsx   # Reuses or wraps TickerAutocomplete + recent tickers
│   └── ChartActionPanel.tsx    # Pinned bottom panel (active mode only)
├── hooks/
│   ├── useChartData.ts         # Fetches Alpaca bars; client-side cache Map
│   └── useOverlay.ts           # Fetches /api/chart/{ticker}/overlay; 404 = passive
api/
├── chart_routes.py             # GET /api/chart/{ticker}/overlay
└── schemas.py                  # ChartOverlayResponse pydantic model
```

### Pattern 1: lightweight-charts v5 React Integration (useRef + useEffect)

**What:** Mount and destroy chart imperatively inside useEffect; store references in useRef to avoid stale closures.

**When to use:** Always — this is the only supported React pattern for v5 (no native React wrapper exists).

**Critical v5 API changes from v4:**
- Series creation: `chart.addSeries(CandlestickSeries, options)` — NOT `chart.addCandlestickSeries(options)`
- Markers: `createSeriesMarkers(series, markers)` — imported separately, NOT `series.setMarkers()`
- Watermarks: moved to `createTextWatermark(pane, options)` plugin — not a chart option
- Plugin interface names: `ISeriesPrimitivePaneView` → `IPrimitivePaneView`

**Example:**
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/react/simple
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import { useRef, useEffect } from 'react';

export function ChartContainer({ data, volumeData }: ChartContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      layout: {
        background: { color: 'transparent' },
        textColor: '#9ca3af', // Tailwind gray-400
      },
      grid: {
        vertLines: { color: '#374151' },   // gray-700
        horzLines: { color: '#374151' },
      },
      rightPriceScale: { borderColor: '#374151' },
      timeScale: { borderColor: '#374151' },
    });
    chartRef.current = chart;

    // Candlestick series (v5 syntax)
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',       // green-500
      downColor: '#ef4444',     // red-500
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });
    candleSeries.setData(data);

    // Volume histogram — overlay (priceScaleId: '') with scaleMargins
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#6b7280',           // gray-500 default
      priceFormat: { type: 'volume' },
      priceScaleId: '',           // overlay — not tied to left/right scale
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.7, bottom: 0 },
    });
    volumeSeries.setData(volumeData);

    chart.timeScale().fitContent();

    // Resize handler
    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, volumeData]);

  return <div ref={containerRef} className="w-full h-full" />;
}
```

### Pattern 2: Agent Overlay — Price Lines (TP/SL)

**What:** Horizontal dashed lines pinned to price values using `series.createPriceLine()`.

**When to use:** For TP (green) and SL (red) horizontal lines after overlay data is loaded.

**Example:**
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/how_to/price-line
import { LineStyle } from 'lightweight-charts';

// After candleSeries is created:
const tpLine = candleSeries.createPriceLine({
  price: overlayData.take_profit,
  color: '#22c55e',       // green-500
  lineWidth: 1,
  lineStyle: LineStyle.Dashed,
  axisLabelVisible: true,
  title: 'TP',
});

const slLine = candleSeries.createPriceLine({
  price: overlayData.stop_loss,
  color: '#ef4444',       // red-500
  lineWidth: 1,
  lineStyle: LineStyle.Dashed,
  axisLabelVisible: true,
  title: 'SL',
});

// Cleanup:
candleSeries.removePriceLine(tpLine);
candleSeries.removePriceLine(slLine);
```

### Pattern 3: Agent Overlay — Entry Dot (Series Marker)

**What:** Circle marker pinned to a specific bar date using `createSeriesMarkers()` (v5 separate import).

**When to use:** For the entry marker dot. Only render when the entry date falls within the visible timeframe window.

**Example:**
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/how_to/series-markers
import { createSeriesMarkers } from 'lightweight-charts';

const markers = createSeriesMarkers(candleSeries, [
  {
    time: overlayData.entry_date,   // 'YYYY-MM-DD' string or Unix timestamp
    position: 'belowBar',
    color: '#3b82f6',                // blue-500
    shape: 'circle',
    text: overlayData.strategy_name,
    size: 1,
  },
]);

// Cleanup:
markers.detach();
```

### Pattern 4: Agent Overlay — Expiry Vertical Line (Series Primitive)

**What:** There is no built-in vertical line in lightweight-charts v5. A custom ISeriesPrimitive must be implemented as a canvas renderer.

**When to use:** For the expiry line (amber dashed vertical at the options contract expiry date).

**Implementation approach:** Implement a minimal `ISeriesPrimitive` with a `paneViews()` method that draws a vertical line using `CanvasRenderingContext2D`. The time-to-x coordinate conversion uses the chart's `ITimeScaleApi.timeToCoordinate()`.

```typescript
// Minimal vertical line primitive pattern
// Source: https://tradingview.github.io/lightweight-charts/docs/plugins/series-primitives
import type { ISeriesPrimitive, IPrimitivePaneView, IPrimitivePaneRenderer } from 'lightweight-charts';

class VerticalLineRenderer implements IPrimitivePaneRenderer {
  constructor(private x: number, private color: string) {}
  draw(target: CanvasRenderingContext2D): void {
    target.save();
    target.strokeStyle = this.color;
    target.lineWidth = 1;
    target.setLineDash([4, 4]);
    target.beginPath();
    target.moveTo(this.x, 0);
    target.lineTo(this.x, target.canvas.height);
    target.stroke();
    target.restore();
  }
}

class VerticalLinePaneView implements IPrimitivePaneView {
  constructor(private series: ISeriesApi<any>, private time: string, private color: string) {}
  zOrder(): PrimitivePaneViewZOrder { return 'normal'; }
  renderer(): IPrimitivePaneRenderer {
    const x = this.series.priceToCoordinate(0) !== null
      ? this.series.chart().timeScale().timeToCoordinate(this.time) ?? -1
      : -1;
    return new VerticalLineRenderer(x, this.color);
  }
}
```

**Simpler alternative:** Render the expiry date as a series marker (`shape: 'arrowDown'` or `'circle'` at the expiry bar's price, `position: 'aboveBar'`). This avoids the primitive entirely but is less visually distinct than a full vertical line.

**Recommendation:** Start with the series marker approach for expiry (D-16 says "expiry vertical dashed line (amber)" but the complexity of a full custom primitive may not be worth it for Phase 13). Use a marker at the expiry bar with amber color. Only escalate to a custom primitive if the visual is deemed insufficient.

### Pattern 5: Alpaca Bars — Direct Browser Fetch

**What:** Call Alpaca's data API from the browser using fetch with APCA headers.

**When to use:** Every time a new ticker+timeframe combination is needed (cache miss).

**CORS status:** Fixed by Alpaca in January 2021 (GitHub issue #152 resolved). `data.alpaca.markets` now returns valid `Access-Control-Allow-Origin` headers for browser preflight requests. HIGH confidence.

**Example:**
```typescript
// Source: https://docs.alpaca.markets/reference/stockbarsingle-1
async function fetchAlpacaBars(
  ticker: string,
  timeframe: '15Min' | '1Day',
  start: string,  // 'YYYY-MM-DD'
  end?: string,
): Promise<AlpacaBar[]> {
  const url = new URL(`https://data.alpaca.markets/v2/stocks/${ticker}/bars`);
  url.searchParams.set('timeframe', timeframe);
  url.searchParams.set('start', start);
  if (end) url.searchParams.set('end', end);
  url.searchParams.set('feed', 'iex');    // free tier; use 'sip' with subscription
  url.searchParams.set('limit', '1000');
  url.searchParams.set('sort', 'asc');

  const response = await fetch(url.toString(), {
    headers: {
      'APCA-API-KEY-ID': import.meta.env.VITE_ALPACA_KEY,
      'APCA-API-SECRET-KEY': import.meta.env.VITE_ALPACA_SECRET,
    },
  });

  if (!response.ok) {
    throw new Error(`Alpaca API error ${response.status}`);
  }

  const json = await response.json();
  // Single-symbol endpoint returns { bars: [...], next_page_token: string|null }
  return json.bars as AlpacaBar[];
  // Note: handle next_page_token for large ranges if needed
}

// Transform to lightweight-charts CandlestickData format
function toBarsData(bars: AlpacaBar[]): CandlestickData[] {
  return bars.map(b => ({
    time: b.t.slice(0, 10),  // 'YYYY-MM-DD' for daily; or Unix timestamp for intraday
    open: b.o,
    high: b.h,
    low: b.l,
    close: b.c,
  }));
}
```

**Timeframe mapping for 5 presets:**

| Preset | Alpaca timeframe | start | end |
|--------|-----------------|-------|-----|
| 1D (today) | `15Min` | today | today |
| 1M | `1Day` | 30 days ago | today |
| 3M | `1Day` | 90 days ago | today |
| 6M (default) | `1Day` | 180 days ago | today |
| 1Y | `1Day` | 365 days ago | today |

### Pattern 6: Backend Chart Overlay Endpoint

**What:** New FastAPI endpoint at `GET /api/chart/{ticker}/overlay` that reads from the most recent log file for the ticker and LLM-parses the `final_trade_decision` text to extract entry/TP/SL.

**Critical discovery:** `AgentState` stores `final_trade_decision` as an unstructured markdown string. There are NO discrete `entry_price`, `take_profit`, or `stop_loss` fields in the current schema. The overlay endpoint must either:
  1. Parse the log file using an LLM call (consistent with project patterns — `SignalProcessor` already does this for signal extraction)
  2. Return a best-effort extraction with potential nulls

**Data source:** `eval_results/{ticker}/TradingAgentsStrategy_logs/full_states_log_{date}.json` — these files are written by `TradingAgentsGraph.log_states()` after each analysis run.

**Example endpoint:**
```python
# api/chart_routes.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import glob

chart_router = APIRouter(prefix="/api")

@chart_router.get("/chart/{ticker}/overlay")
async def get_chart_overlay(ticker: str):
    """Return agent signal overlay data for the most recent analysis of a ticker.
    Returns 404 if no analysis exists (passive mode signal to frontend).
    """
    log_dir = Path(f"eval_results/{ticker.upper()}/TradingAgentsStrategy_logs")
    if not log_dir.exists():
        raise HTTPException(status_code=404, detail="No analysis found")

    log_files = sorted(glob.glob(str(log_dir / "full_states_log_*.json")))
    if not log_files:
        raise HTTPException(status_code=404, detail="No analysis found")

    latest_log_path = log_files[-1]  # most recent by filename date
    with open(latest_log_path, encoding="utf-8") as f:
        log_data = json.load(f)

    # log_data is { "YYYY-MM-DD": { ... agent state ... } }
    latest_date = sorted(log_data.keys())[-1]
    state = log_data[latest_date]

    # Extract signal fields (LLM parsing of final_trade_decision)
    # Phase 13: best-effort extraction; Phase 14 will store these as structured fields
    overlay = await _extract_overlay_from_state(ticker, state)
    if overlay is None:
        raise HTTPException(status_code=404, detail="Cannot extract overlay from analysis")

    return overlay
```

**Pydantic schema for overlay response:**
```python
class ChartOverlayResponse(BaseModel):
    ticker: str
    analysis_date: str           # 'YYYY-MM-DD'
    signal: str                  # 'BUY' | 'SELL' | 'HOLD'
    entry_price: float | None    # None if not parseable
    take_profit: float | None
    stop_loss: float | None
    expiry_date: str | None      # 'YYYY-MM-DD' from options_legs, None for equity
    strategy_name: str | None    # e.g., 'Bull Call Spread'
    options_legs: str            # raw string for action panel display
    final_trade_decision: str    # full text for Analysis back-link context
```

### Pattern 7: App.tsx Navigation Extension

**What:** Add "Chart" as a third peer section in the existing tab bar pattern.

**Current state:** `mainSection` is `'analysis' | 'screener'` — extend to `'analysis' | 'screener' | 'chart'`.

**Navigation trigger on analysis complete:** In `useAnalysis.ts`, when `status === 'done'`, App.tsx should auto-navigate to Chart with the current ticker. This requires lifting the `ticker` state or passing it through the analysis state.

**Example diff in App.tsx:**
```typescript
const [mainSection, setMainSection] = useState<'analysis' | 'screener' | 'chart'>('analysis');
const [chartTicker, setChartTicker] = useState<string>('');

// On analysis complete — navigate to chart
useEffect(() => {
  if (state.status === 'done' && state.result) {
    setChartTicker(currentAnalysisTicker);
    setMainSection('chart');
  }
}, [state.status]);
```

### Pattern 8: Client-Side Cache

**What:** A `Map<string, CandlestickData[]>` in `useChartData` hook keyed by `${ticker}-${timeframe}` prevents redundant Alpaca fetches when switching timeframes.

```typescript
const cacheRef = useRef(new Map<string, CandlestickData[]>());
const cacheKey = `${ticker}-${timeframe}`;
if (cacheRef.current.has(cacheKey)) {
  setData(cacheRef.current.get(cacheKey)!);
  return;
}
// ... fetch from Alpaca, then:
cacheRef.current.set(cacheKey, transformedData);
```

### Anti-Patterns to Avoid

- **Creating chart instance in render body:** The chart must be created inside `useEffect` (or `useLayoutEffect`). Creating it in the render function causes React re-renders to multiply chart instances.
- **Using v4 series creation syntax:** `chart.addCandlestickSeries()` does not exist in v5. The linter/TypeScript will catch this but only if types are imported correctly.
- **Calling `series.setMarkers()` in v5:** This API was removed. Always import and use `createSeriesMarkers(series, markers)`.
- **Missing chart.remove() cleanup:** Without the return function in useEffect calling `chart.remove()`, switching tickers causes stacked chart instances — a major memory leak.
- **Using 'sip' feed without subscription:** Free Alpaca accounts only have access to 'iex'. Using 'sip' returns a 403/subscription error. Always use `feed=iex` unless explicitly upgraded.
- **Keying volume data by same time as candle:** The volume `HistogramSeries` requires each bar's `time` to match the candlestick `time` exactly — misalignment causes "Data must be asc order" errors.
- **Blocking the resize observer path:** Calling `chart.applyOptions({ width: ... })` during chart creation before the DOM is painted causes zero-width charts. Always read `containerRef.current.clientWidth` after mount.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Candlestick rendering | Canvas-based OHLC renderer | `chart.addSeries(CandlestickSeries)` | Performance-optimized WebGL rendering, crosshair, tooltips all built in |
| Volume histogram | D3 bar chart overlay | `chart.addSeries(HistogramSeries, { priceScaleId: '' })` | Synchronized time axis, automatic scaling, per-bar color |
| Horizontal TP/SL lines | Absolutely-positioned div | `series.createPriceLine()` | Price-scale synchronized — lines move correctly with chart zoom/pan |
| Entry dot annotation | SVG overlay | `createSeriesMarkers()` | Correctly placed on bar time coordinate; handles pan/zoom automatically |
| Client-side data cache | localStorage serialization | `useRef(new Map())` | In-memory is sufficient for session; localStorage would need serialization logic and size limits |
| Ticker autocomplete | New search component | Reuse `TickerAutocomplete.tsx` | Already built, already fetches `/api/tickers`, handles keyboard navigation |
| Signal text parsing | Regex on `final_trade_decision` | LLM extraction (follow `SignalProcessor` pattern) | `final_trade_decision` is markdown prose — regex is fragile; LLM is the project pattern |

**Key insight:** lightweight-charts handles all the chart rendering complexity. The real implementation work is data plumbing (Alpaca fetch + transform) and the overlay data extraction from unstructured text.

---

## Common Pitfalls

### Pitfall 1: v4 vs v5 API Confusion
**What goes wrong:** Copying older examples (pre-2024) that use `addCandlestickSeries()` or `series.setMarkers()` — TypeScript will error, but only if types are imported.
**Why it happens:** The internet has far more v4 examples than v5; migration guide is the authoritative source.
**How to avoid:** Always import from `lightweight-charts` v5 named exports: `createChart`, `CandlestickSeries`, `HistogramSeries`, `createSeriesMarkers`, `LineStyle`.
**Warning signs:** TypeScript type error "Property 'addCandlestickSeries' does not exist on type 'IChartApi'".

### Pitfall 2: Chart Memory Leak on Re-render
**What goes wrong:** Chart mounts correctly, but navigating away and back creates a second (or nth) chart instance inside the same container div.
**Why it happens:** `useEffect` cleanup not returning `chart.remove()`, or the effect dependency array changes causing re-mount without cleanup.
**How to avoid:** Always include `return () => { chart.remove(); }` in the useEffect. Use `useRef` for the chart instance — not state — so re-renders don't re-trigger the effect.
**Warning signs:** Multiple crosshairs visible, doubled price scales, degrading performance over time.

### Pitfall 3: Volume Time Axis Misalignment
**What goes wrong:** Volume histogram bars don't line up with candlestick bars, or chart throws "Data must be in ascending order" error.
**Why it happens:** Alpaca bars come pre-sorted asc, but after transformation if any UTC-to-local conversion occurs, `time` strings diverge between candle and volume data.
**How to avoid:** Use `b.t.slice(0, 10)` for daily bars (gives `YYYY-MM-DD`). For intraday, use UTC Unix timestamp (`Math.floor(new Date(b.t).getTime() / 1000)`). Apply the same transformation to both series.
**Warning signs:** Console error from lightweight-charts about data ordering.

### Pitfall 4: Alpaca Pagination Not Handled
**What goes wrong:** Alpaca returns at most 1000 bars per request. For 1Y with daily bars, 252 bars < 1000 — fine. For intraday 15-min bars over 1 month, the limit may truncate data.
**Why it happens:** Alpaca returns `next_page_token` when results are paginated; ignoring it means incomplete chart data.
**How to avoid:** For Phase 13's 5 presets: 1D = ~26 bars (6.5 hours × 4 bars/hr), 1M = ~21 bars, 3M = ~63, 6M = ~126, 1Y = ~252. All comfortably under 1000 — no pagination needed for daily bars. For 15-min intraday (1D), max 26 bars — also fine.
**Warning signs:** Chart looks correct but ends before the expected end date.

### Pitfall 5: `entry_price` Not in AgentState
**What goes wrong:** Overlay endpoint tries to return entry price from `final_state["entry_price"]` — key does not exist.
**Why it happens:** The current `AgentState` stores `final_trade_decision` as unstructured prose. No structured trade fields are persisted to the log JSON.
**How to avoid:** The overlay endpoint must LLM-parse the `final_trade_decision` text (following `SignalProcessor` pattern) OR return `entry_price: null` for Phase 13 and render the entry dot at the analysis date's close price as a fallback. Structured storage is a Phase 14 concern.
**Warning signs:** KeyError in Python overlay endpoint, or null entry dot on chart.

### Pitfall 6: Dark Mode Chart Colors
**What goes wrong:** Chart renders with white background and dark text — looks disconnected from the app's dark theme.
**Why it happens:** lightweight-charts defaults to light theme; `layout.background.color` defaults to white.
**How to avoid:** Pass theme-aware colors to `createChart`. Subscribe to the Tailwind dark class toggle and call `chart.applyOptions({ layout: { ... } })` when dark mode changes. The existing `dark` state in App.tsx should be passed as a prop to ChartContainer.
**Warning signs:** White rectangle in dark mode UI.

### Pitfall 7: Expiry Vertical Line Complexity
**What goes wrong:** Implementing a custom `ISeriesPrimitive` for the expiry vertical line takes disproportionate time relative to its visual value.
**Why it happens:** The plugin API requires canvas renderer classes implementing multiple TypeScript interfaces — a significant detour from the core chart functionality.
**How to avoid:** Use a `createSeriesMarkers` marker at the expiry bar date as a first implementation (amber arrow or circle `aboveBar`). Only escalate to a full `ISeriesPrimitive` vertical line if the visual is insufficient.
**Warning signs:** Spending more than 2 hours on the expiry line visual.

---

## Code Examples

Verified patterns from official sources:

### CandlestickSeries + HistogramSeries Volume Overlay (v5)
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/how_to/price-and-volume
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

const chart = createChart(container, { /* options */ });

const candleSeries = chart.addSeries(CandlestickSeries, {
  upColor: '#22c55e',
  downColor: '#ef4444',
  borderVisible: false,
  wickUpColor: '#22c55e',
  wickDownColor: '#ef4444',
});

const volumeSeries = chart.addSeries(HistogramSeries, {
  priceFormat: { type: 'volume' },
  priceScaleId: '',    // '' = overlay (no dedicated scale)
});
volumeSeries.priceScale().applyOptions({
  scaleMargins: { top: 0.7, bottom: 0 },
});

// Volume data with per-bar color (green for up, red for down bars)
volumeSeries.setData(
  candleData.map(b => ({
    time: b.time,
    value: b.volume,
    color: b.close >= b.open ? '#22c55e33' : '#ef444433',  // semi-transparent
  }))
);
```

### series.createPriceLine for TP/SL Horizontal Lines
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/how_to/price-line
import { LineStyle } from 'lightweight-charts';

const tpLine = candleSeries.createPriceLine({
  price: 185.50,
  color: '#22c55e',
  lineWidth: 1,
  lineStyle: LineStyle.Dashed,
  axisLabelVisible: true,
  title: 'TP',
});
// Remove when overlay changes:
candleSeries.removePriceLine(tpLine);
```

### createSeriesMarkers for Entry Dot (v5 — separate import)
```typescript
// Source: https://tradingview.github.io/lightweight-charts/tutorials/how_to/series-markers
import { createSeriesMarkers } from 'lightweight-charts';

const markers = createSeriesMarkers(candleSeries, [
  {
    time: '2026-03-15',
    position: 'belowBar',
    color: '#3b82f6',
    shape: 'circle',
    text: 'Bull Call Spread',
    size: 2,
  },
]);
// Cleanup:
markers.detach();
```

### Alpaca Bars Fetch (Browser, Single Symbol)
```typescript
// Source: https://docs.alpaca.markets/reference/stockbarsingle-1
const response = await fetch(
  `https://data.alpaca.markets/v2/stocks/AAPL/bars?timeframe=1Day&start=2025-10-03&feed=iex&sort=asc&limit=1000`,
  {
    headers: {
      'APCA-API-KEY-ID': import.meta.env.VITE_ALPACA_KEY,
      'APCA-API-SECRET-KEY': import.meta.env.VITE_ALPACA_SECRET,
    },
  }
);
const { bars, next_page_token } = await response.json();
// bars: Array<{ t: string, o: number, h: number, l: number, c: number, v: number, n: number, vw: number }>
```

### Backend Overlay Endpoint Pattern (FastAPI)
```python
# api/chart_routes.py — follows existing screener_routes.py convention
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json, glob, asyncio

chart_router = APIRouter(prefix="/api")

@chart_router.get("/chart/{ticker}/overlay")
async def get_chart_overlay(ticker: str):
    log_dir = Path(f"eval_results/{ticker.upper()}/TradingAgentsStrategy_logs")
    if not log_dir.exists():
        raise HTTPException(status_code=404, detail="No analysis found")
    files = sorted(glob.glob(str(log_dir / "full_states_log_*.json")))
    if not files:
        raise HTTPException(status_code=404, detail="No analysis found")
    with open(files[-1], encoding="utf-8") as f:
        log_data = json.load(f)
    latest_date = sorted(log_data.keys())[-1]
    state = log_data[latest_date]
    # ... LLM-parse final_trade_decision for entry_price, tp, sl
    # ... parse options_legs for expiry_date, strategy_name
    return { "ticker": ticker, "analysis_date": latest_date, ... }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `chart.addCandlestickSeries(opts)` | `chart.addSeries(CandlestickSeries, opts)` | v5.0 (Nov 2024) | All old examples and wrappers are broken |
| `series.setMarkers([...])` | `createSeriesMarkers(series, [...])` | v5.0 (Nov 2024) | Must import separately; old method removed |
| Watermark as chart option | `createTextWatermark(pane, opts)` plugin | v5.0 | Not relevant for Phase 13 but worth knowing |
| Community wrapper `react-lightweight-charts` | Direct import with useRef+useEffect | v5.0 | Wrapper not updated; official docs show direct pattern |
| Plugin interface `ISeriesPrimitivePaneView` | `IPrimitivePaneView` | v5.0 | Renamed — any plugin tutorial using old name is outdated |

**Deprecated/outdated:**
- `addLineSeries()`, `addCandlestickSeries()`, `addHistogramSeries()` — removed in v5; use `addSeries(TypeClass, opts)`
- `series.setMarkers()` — removed in v5; use `createSeriesMarkers()`
- Community npm packages `lightweight-charts-react`, `react-lightweight-charts` — target v3/v4; incompatible with v5 API

---

## Open Questions

1. **LLM extraction of entry_price / TP / SL from final_trade_decision**
   - What we know: `final_trade_decision` is unstructured markdown prose from the Risk Manager. Sample analysis of AAPL (2026-04-02) confirms no discrete price fields.
   - What's unclear: Reliability of LLM extraction — risk manager output format varies by run and provider.
   - Recommendation: Phase 13 scope: extract signal, analysis_date, options_legs (for expiry/strategy). For entry_price/TP/SL: attempt LLM extraction via `SignalProcessor`-style call; return `null` on failure; render entry dot at analysis_date close price as fallback. Document that Phase 14 should add structured storage.

2. **Vite env var dual-use for Alpaca keys**
   - What we know: D-11 says `ALPACA_PAPER_KEY`/`ALPACA_PAPER_SECRET` are used for both chart data (Phase 13) and execution (Phase 14). Vite env vars must be prefixed `VITE_` to be exposed to the browser.
   - What's unclear: Whether the `.env` will need two separate names (`ALPACA_PAPER_KEY` for backend + `VITE_ALPACA_KEY` for frontend) or one set with a `VITE_` prefix that both read.
   - Recommendation: Use separate `.env` entries — `VITE_ALPACA_KEY` (frontend chart) and `ALPACA_PAPER_KEY` (backend execution in Phase 14). Both can hold the same value. Document this in `env.example`.

3. **Expiry date parsing from options_legs**
   - What we know: `options_legs` is an unstructured string (sample: `"No order — contract selection failed"`). When options are active, it would contain leg descriptions.
   - What's unclear: Consistent format for extracting expiry date across different options strategies.
   - Recommendation: Attempt regex extraction of `YYYY-MM-DD` patterns from `options_legs`; fall back to `null`. If null, omit the expiry marker from the chart — do not block the overlay endpoint.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `pytest tests/api/ -x -q` |
| Full suite command | `pytest tests/ -x -q` |
| Frontend tests | None — no vitest/jest configured; frontend validation is manual browser smoke test |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHART-01 | GET /api/chart/{ticker}/overlay returns 404 when no logs exist | unit | `pytest tests/api/test_chart_routes.py::test_overlay_404_no_logs -x` | ❌ Wave 0 |
| CHART-01 | GET /api/chart/{ticker}/overlay returns overlay data when logs exist | unit | `pytest tests/api/test_chart_routes.py::test_overlay_returns_data -x` | ❌ Wave 0 |
| CHART-02 | ChartOverlayResponse Pydantic schema validates correctly | unit | `pytest tests/api/test_chart_schemas.py -x` | ❌ Wave 0 |
| CHART-04 | Timeframe start date calculation is correct for all 5 presets | unit | `pytest tests/api/test_chart_routes.py::test_timeframe_dates -x` | ❌ Wave 0 |
| CHART-05 | Overlay endpoint correctly reads most recent log file | unit | `pytest tests/api/test_chart_routes.py::test_overlay_reads_latest_log -x` | ❌ Wave 0 |
| CHART-01/02 | Chart screen renders without crashing (smoke) | manual | Browser: navigate to Chart tab, enter AAPL, verify chart loads | — |
| CHART-04 | Timeframe toggle updates chart data (smoke) | manual | Browser: switch 6M → 1M → 1Y, verify re-renders | — |
| CHART-05 | Active mode shows overlays after analysis (smoke) | manual | Browser: run analysis, verify auto-navigate to chart with TP/SL lines | — |

### Sampling Rate
- **Per task commit:** `pytest tests/api/ -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green + manual smoke test of Chart screen before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/api/test_chart_routes.py` — covers CHART-01, CHART-04, CHART-05 (mock log files)
- [ ] `tests/api/test_chart_schemas.py` — covers CHART-02 (Pydantic schema validation)
- [ ] `api/chart_routes.py` — new file (endpoint implementation)
- [ ] `api/schemas.py` — add `ChartOverlayResponse` model

---

## Sources

### Primary (HIGH confidence)
- `npm view lightweight-charts` — version 5.1.0 confirmed 2026-04-03, published 2025-12-16
- https://tradingview.github.io/lightweight-charts/tutorials/react/simple — official React useRef+useEffect pattern
- https://tradingview.github.io/lightweight-charts/tutorials/how_to/price-and-volume — volume histogram overlay with `priceScaleId: ''`
- https://tradingview.github.io/lightweight-charts/tutorials/how_to/price-line — `series.createPriceLine()` with `LineStyle.Dashed`
- https://tradingview.github.io/lightweight-charts/tutorials/how_to/series-markers — `createSeriesMarkers()` v5 pattern
- https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5 — breaking changes: `addSeries(TypeClass)`, `createSeriesMarkers`, plugin renames
- https://docs.alpaca.markets/reference/stockbarsingle-1 — single-symbol bars response format `{ bars: [...] }`
- https://github.com/alpacahq/Alpaca-API/issues/152 — CORS fixed January 2021 (resolved/closed)
- Project source: `eval_results/AAPL/TradingAgentsStrategy_logs/full_states_log_2026-04-02.json` — confirms `final_trade_decision` is unstructured prose
- Project source: `tradingagents/agents/utils/agent_states.py` — confirms no `entry_price`/`take_profit`/`stop_loss` fields in `AgentState`

### Secondary (MEDIUM confidence)
- https://tradingview.github.io/lightweight-charts/docs/panes — multi-pane API overview (code in tutorial, not shown verbatim)
- https://tradingview.github.io/lightweight-charts/docs/plugins/series-primitives — ISeriesPrimitive interface for custom vertical line
- https://docs.alpaca.markets/docs/market-data-faq — free tier = IEX feed only; SIP requires subscription

### Tertiary (LOW confidence)
- WebSearch community examples for volume histogram color per-bar pattern — widely used but not from official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — version verified via npm registry
- Architecture: HIGH — all patterns sourced from official lightweight-charts v5 docs and project codebase analysis
- Pitfalls: HIGH — v4→v5 breaking changes from official migration guide; AgentState gap from direct code inspection
- Alpaca CORS: HIGH — GitHub issue resolution confirmed
- Overlay LLM parsing: MEDIUM — approach is sound (follows existing SignalProcessor), reliability depends on agent output format which varies

**Research date:** 2026-04-03
**Valid until:** 2026-07-03 (stable library; 90 days before re-verification needed)
