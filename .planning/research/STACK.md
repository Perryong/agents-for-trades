# Technology Stack — v1.1 Stock Recommendation System

**Project:** TradingAgents v1.1 (Stock Screener / Recommendation)
**Researched:** 2026-04-02
**Scope:** NEW additions only — does not re-document existing v1.0 stack

---

## Context: What Already Exists

The following are confirmed v1.0 capabilities that the new screener MUST integrate
with, not duplicate:

| Concern | Existing Solution | Integration Point |
|---------|-------------------|-------------------|
| Single-stock data | yfinance 0.2.63 via `get_YFin_data_online` | `VENDOR_METHODS["get_stock_data"]` |
| Technical indicators | stockstats 0.6.5 via `get_stock_stats_indicators_window` | `VENDOR_METHODS["get_indicators"]` |
| Fundamentals | yfinance `Ticker.info` via `get_fundamentals` | `VENDOR_METHODS["get_fundamentals"]` |
| LangGraph agents | All `create_*` factory functions, `AgentState` dict | `trading_graph.py` / `setup.py` |
| HTTP caching | `yfinance_cache.py` (`get_cached_text`, `get_cached_dataframe`) | Used by every data module |
| Frontend | React 19, TypeScript, Tailwind v4, Vite 8, SSE streaming | `frontend/src/` |
| Backend | FastAPI with SSE endpoint | `main.py` or equivalent |

---

## New Additions Required

### 1. Market Universe Data (Screener Feed)

**Problem:** The system needs a list of ~20-50 candidates to pass to the LLM screener
agent. There is no existing mechanism to fetch "market movers" — only single-ticker
lookups are supported.

#### Option A: yfinance.screen() / Screener class (CAUTION — LOW confidence)

yfinance 0.2.x added a `Screener` class and `yf.screen()` function with predefined
bodies: `most_actives`, `day_gainers`, `day_losers`, `undervalued_growth_stocks`,
`growth_technology_stocks`.

Usage pattern:
```python
import yfinance as yf
result = yf.screen("most_actives", size=25)
# Returns dict with "quotes" list of ticker dicts
```

**Verdict: Do NOT rely on this as the primary path.** As of April 2025, GitHub issue
#2419 confirmed the `size` and `offset` parameters are broken because the library
sends a GET request where Yahoo's API requires POST. The call silently returns only
25 results regardless of requested size. This is an unofficial scraping layer that
breaks whenever Yahoo changes their API. Confidence: LOW that this is stable.

**Use only as a secondary convenience fallback** for getting 25 most-actives if
`finvizfinance` is unavailable. No install required (already in venv).

#### Option B: finvizfinance 1.3.0 (RECOMMENDED — MEDIUM confidence)

finvizfinance is a Python wrapper for Finviz.com's screener. Current version: 1.3.0
(released January 3, 2026). It scrapes Finviz's HTML screener pages (not an
official API), but the site structure has been stable and the library is actively
maintained with regular updates.

```python
from finvizfinance.screener.overview import Overview

# Most active by volume
foverview = Overview()
foverview.set_filter(signal='ta_unusualvolume')
df = foverview.screener_view()  # Returns pandas DataFrame

# Volume movers in specific index
foverview.set_filter(filters_dict={'Index': 'S&P 500'}, signal='ta_unusualvolume')
df = foverview.screener_view()

# Sector-based filter
foverview.set_filter(filters_dict={'Sector': 'Technology', 'Index': 'S&P 500'})
df = foverview.screener_view()
```

Columns returned include: Ticker, Company, Sector, Industry, Country, Market Cap,
P/E, Price, Change, Volume.

**Why finvizfinance over alternatives:**
- Zero API key required (unlike Polygon.io, FMP, Finnhub)
- Already has free-tier scrapers trusted by the quant community
- Returns structured DataFrames — no parsing needed
- v1.3.0 released January 2026, actively maintained
- Finviz screener signals map directly to what the pre-filter needs:
  `ta_unusualvolume` (unusual volume), `ta_topgainers` (top gainers),
  `ta_toplosers` (top losers)

**Risk:** Scraping-based — can break if Finviz redesigns their HTML.
**Mitigation:** Wrap in try/except with yfinance.screen() fallback (already in venv).

**Install:**
```
finvizfinance>=1.3.0
```

#### Option C: Sector ETF Momentum via yfinance (NO NEW DEPENDENCY)

Sector momentum requires no new libraries. Use yfinance's existing `yf.download()`
(already used by `_get_stock_stats_bulk`) on a fixed list of SPDR sector ETFs:

```python
SECTOR_ETFS = {
    "XLK": "Technology", "XLF": "Financials", "XLV": "Healthcare",
    "XLE": "Energy", "XLI": "Industrials", "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples", "XLU": "Utilities", "XLB": "Materials",
    "XLC": "Communication Services", "XLRE": "Real Estate"
}
# Fetch 30-day returns for each ETF ticker using existing yf.download()
# Rank by 30-day and 5-day return — no new dependency needed
```

This uses existing yfinance data access patterns and existing `yfinance_cache.py`
infrastructure. Confidence: HIGH.

---

### 2. Screener Data Module

A new file `tradingagents/dataflows/screener.py` following the existing module
pattern:

- Uses `finvizfinance` for broad market movers (unusual volume, top gainers/losers)
- Uses `yf.download()` (existing) for sector ETF momentum
- Returns results as normalized Python dicts (not raw DataFrames) — consistent with
  other data modules that return strings or structured dicts
- Plugs into `VENDOR_METHODS` as a new `"screener_data"` category with
  `"finviz"` as primary vendor

**No changes to existing VENDOR_METHODS entries.** New category addition only.

---

### 3. New LangGraph Agent: Screener Agent

A `create_screener_agent` factory following the `create_*` pattern:

- **Input:** `AgentState` with a new `screener_filters` field (dict: index, sector,
  signal type)
- **Output:** Writes to a new `screener_report` field in `AgentState`
- **LLM use:** Uses existing `quick_thinking_llm` — takes the pre-filtered list
  (~20-50 rows) and ranks/explains top 3-5 picks
- **Graph placement:** New entry-point node, runs BEFORE the existing equity/options
  pipeline. User selects a pick from screener results, THEN triggers the full pipeline.

This is architecturally separate from the existing parallel equity+options pipeline —
it feeds the pipeline rather than running alongside it.

---

### 4. Frontend: Screener Results Tab

**What's needed:** A new tab in the existing `ReportTabs` component displaying a
structured table of screener results, with click-to-analyze on each row.

**Approach:** Pure React with `useState` hooks for sort/filter state — no new npm
dependencies. The existing codebase has zero table libraries (just Tailwind v4 +
React 19). Adding a new library for 40-50 rows of screener results is
disproportionate overhead.

**If the table grows complex:** `@tanstack/react-table` v8 is the right choice —
headless (no CSS opinions), tree-shakable, zero peer dependencies beyond React,
works well with Tailwind. It supports client-side sort + filter with ~4KB gzipped.
But this is deferred unless the screener table needs pagination or complex filtering.

**Required frontend additions (no new npm packages for MVP):**
- New entry in `REPORT_TABS` constant for screener view
- New `ScreenerPane.tsx` component: table with Ticker, Company, Sector, Price,
  Change, Volume columns + "Analyze" button per row
- New `ScreenerRequest` type in `types.ts` for triggering screener runs
- New SSE event type for streaming screener results back to frontend
- `useScreener` hook mirroring existing `useAnalysis` hook pattern

**Optional (if table complexity justifies it):**
```
@tanstack/react-table@^8.21
```
Confidence: HIGH (well-maintained, v8 is current as of 2026).

---

## Summary: New Dependencies

| Package | Version | Purpose | Confidence |
|---------|---------|---------|-----------|
| `finvizfinance` | `>=1.3.0` | Broad market screener — unusual volume, gainers, losers, sector | MEDIUM |

**No other new Python dependencies.** Sector ETF momentum uses existing yfinance.
yfinance.screen() (already installed) serves as fallback.

**No new npm dependencies for MVP.** Screener table uses React + Tailwind patterns
already in place. `@tanstack/react-table` is a justified addition only if table
complexity grows beyond a basic sortable list.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Screener feed | finvizfinance | Polygon.io screener API | Requires paid API key; free tier is 5 req/min which is unusable for a universe scan |
| Screener feed | finvizfinance | Financial Modeling Prep (FMP) | Requires API key; free tier limited; another vendor credential to manage |
| Screener feed | finvizfinance | yfinance.screen() | Broken size/offset params as of Apr 2025; unstable unofficial layer |
| Screener feed | finvizfinance | Finnhub `/stock/symbol` + filter loop | Would require iterating 500+ tickers individually — impractical latency |
| Sector momentum | yf.download() (existing) | sector-specific ETF library | No such library needed; 11 ticker symbols downloaded in one batch call |
| Frontend table | Native React + Tailwind | @tanstack/react-table | Justified only if complexity grows; overkill for 20-50 rows at MVP |
| Frontend table | Native React + Tailwind | react-table v7 or AG Grid | react-table v7 is deprecated; AG Grid is enterprise-focused |

---

## Integration with Existing VENDOR_METHODS Pattern

```python
# tradingagents/dataflows/interface.py additions

TOOLS_CATEGORIES = {
    # ... existing categories unchanged ...
    "screener_data": {
        "description": "Broad market screening — movers, volume, sector momentum",
        "tools": [
            "get_market_movers",
            "get_sector_momentum",
        ]
    },
}

VENDOR_METHODS = {
    # ... existing entries unchanged ...
    "get_market_movers": {
        "finviz": get_finviz_market_movers,
        "yfinance": get_yfinance_market_movers,  # fallback using yf.screen()
    },
    "get_sector_momentum": {
        "yfinance": get_yfinance_sector_momentum,  # uses yf.download() on SECTOR_ETFS
    },
}
```

The existing `route_to_vendor` and fallback chain logic handles the finviz ->
yfinance fallback automatically with no changes needed.

---

## Installation

```bash
# Python (add to requirements.txt)
finvizfinance>=1.3.0

# Frontend (defer unless table complexity requires it)
# npm install @tanstack/react-table
```

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| finvizfinance as screener | MEDIUM | v1.3.0 Jan 2026, actively maintained, scraping-based = breakage risk |
| yfinance.screen() as fallback | LOW | Broken size param as of Apr 2025, unofficial, fragile |
| Sector ETF via yf.download() | HIGH | Existing proven pattern, just different tickers |
| No new npm packages for MVP | HIGH | Pattern matches existing codebase; 20-50 rows needs no table library |
| @tanstack/react-table if needed | HIGH | Industry standard, headless, v8 current and stable |
| VENDOR_METHODS integration | HIGH | Pattern is established and tested across all existing data methods |

---

## Sources

- yfinance screener issue #2419 (broken size/offset, April 2025): https://github.com/ranaroussi/yfinance/issues/2419
- yfinance screen() API reference: https://ranaroussi.github.io/yfinance/reference/api/yfinance.screen.html
- finvizfinance PyPI (v1.3.0, January 2026): https://pypi.org/project/finvizfinance/
- finvizfinance screener docs: https://finvizfinance.readthedocs.io/en/latest/screener.html
- TanStack Table v8 sorting guide: https://tanstack.com/table/v8/docs/guide/sorting
- Sector ETF momentum with yfinance (Kaggle): https://www.kaggle.com/code/guillemservera/downloading-sectors-etfs-with-yfinance
- Yahoo Finance most actives (for validating predefined body names): https://finance.yahoo.com/markets/stocks/most-active/
