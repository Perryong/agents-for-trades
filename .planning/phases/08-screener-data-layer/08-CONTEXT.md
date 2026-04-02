# Phase 8: Screener Data Layer - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the data fetching, scoring, and caching layer that narrows a market universe (~500 tickers) down to 20-50 ranked screener candidates. This phase delivers the data pipeline only — no LLM agent, no API endpoint, no UI.

</domain>

<decisions>
## Implementation Decisions

### Pre-Filter Scoring Model
- Scan S&P 500 universe (~503 tickers) as the default market universe
- Equal-weight composite score across three signals: volume, momentum, unusual activity (⅓ each)
- Unusual activity defined as volume > 2x 20-day average AND price change > 1.5%
- Output is a flat list of candidates sorted by composite score (not grouped by signal type)

### Caching & Session Boundaries
- Use `exchange_calendars` library for NYSE session detection (handles holidays, half-days, exact open/close)
- 15-minute TTL for cache during market hours
- In-memory dict cache keyed by session — resets on process restart, no stale disk files
- Partial fetch failures return available data plus a coverage metric; caller decides threshold

### VENDOR_METHODS Integration
- Two new methods in VENDOR_METHODS: `get_screener_universe` (bulk OHLCV fetch) and `get_screener_signals` (volume/momentum/activity scoring)
- Reuse existing `route_to_vendor` fallback chain for consistency
- New module: `screener_data.py` in `tradingagents/dataflows/`
- Pydantic `ScreenerCandidate` model with ticker, scores, rank for typed output

### Claude's Discretion
- Chunking strategy for bulk yfinance fetch (80-100 per chunk with exponential backoff per STATE.md)
- Internal helper function organization within screener_data.py
- Exact momentum calculation window (e.g., 5-day vs 10-day returns)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/dataflows/interface.py` — VENDOR_METHODS dict, route_to_vendor(), TOOLS_CATEGORIES, get_category_for_method()
- `tradingagents/dataflows/yfinance_cache.py` — existing CSV cache with TTL pattern (reference for cache design)
- `tradingagents/dataflows/y_finance.py` — yfinance data fetching patterns (get_YFin_data_online)
- `tradingagents/dataflows/config.py` — runtime config accessor (get_config/set_config)

### Established Patterns
- Vendor-specific modules import into interface.py with aliased names (e.g., `get_fundamentals as get_yfinance_fundamentals`)
- VENDOR_METHODS maps method name → dict of vendor → implementation function
- TOOLS_CATEGORIES groups methods by domain category
- Factory functions use `create_*` prefix; data functions use `get_*` prefix
- AlphaVantageRateLimitError / TradierRateLimitError trigger vendor fallback in route_to_vendor

### Integration Points
- interface.py VENDOR_METHODS dict needs new `screener_data` category entries
- interface.py TOOLS_CATEGORIES needs new `screener_data` category
- default_config.py DEFAULT_CONFIG needs `screener_data` vendor configuration

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
