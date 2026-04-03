# Phase 1: Options Data Infrastructure - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Tradier REST API client and wire it into the existing vendor abstraction layer (`interface.py`) so that options chain data and historical IV are retrievable through the same `VENDOR_METHODS` routing pattern used by equity data. No agent logic — pure data plumbing.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

Key constraints to respect:
- Follow the existing Alpha Vantage client pattern (`requests`-based, in `tradingagents/dataflows/`)
- New file: `tradingagents/dataflows/tradier_utils.py`
- Add `options_data` category to `VENDOR_METHODS` in `interface.py`
- New config keys in `DEFAULT_CONFIG`: `enable_options`, `options_vendor`, `options_delta_target`, `options_dte_window`, `options_min_oi`
- Tradier API key via `TRADIER_API_KEY` env var
- Options chain response must include: strike, expiry, bid, ask, volume, OI, delta, gamma, theta, vega, IV per contract
- Historical IV must cover at least 52-week window

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/dataflows/alpha_vantage_common.py` — AlphaVantageRateLimitError pattern to model Tradier error handling
- `tradingagents/dataflows/alpha_vantage_stock.py` — requests-based API client pattern to follow
- `tradingagents/dataflows/interface.py` — VENDOR_METHODS dict and routing logic to extend
- `tradingagents/dataflows/config.py` — get_config()/set_config() pattern for runtime config access
- `tradingagents/default_config.py` — DEFAULT_CONFIG dict to add new keys to

### Established Patterns
- All dataflow modules use `requests` for HTTP (no httpx/aiohttp)
- API keys read from `os.getenv()` at call time (not at import)
- Rate limit errors raise a typed exception caught by the caller
- Fallback chain: if primary vendor raises rate limit error, caller falls back to yfinance

### Integration Points
- `interface.py` VENDOR_METHODS dict is the single registration point for new tools
- `default_config.py` DEFAULT_CONFIG is the single registration point for new config keys
- `agents/utils/agent_utils.py` will need new @tool-decorated wrapper functions in Phase 5

</code_context>

<specifics>
## Specific Ideas

- Tradier sandbox endpoint: `https://sandbox.tradier.com/v1/` (free, requires registration)
- Tradier production endpoint: `https://api.tradier.com/v1/`
- Relevant Tradier endpoints:
  - Options chain: `GET /markets/options/chains?symbol=AAPL&expiration=2026-01-17&greeks=true`
  - Options expirations: `GET /markets/options/expirations?symbol=AAPL&includeAllRoots=true`
  - Historical IV / quotes: `GET /markets/history?symbol=AAPL&interval=daily&start=2025-01-01`
- yfinance already has basic options chain via `ticker.options` and `ticker.option_chain(date)` — useful as fallback

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
