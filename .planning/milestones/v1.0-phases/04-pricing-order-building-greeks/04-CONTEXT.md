# Phase 4: Pricing, Order Building & Greeks - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Build Black-Scholes pricing utility, options pricing agent, options legs builder agent, and Greeks monitor agent. Extends AgentState with `options_pricing_report` and `greeks_report` fields. The legs builder overwrites the existing `options_legs` field with a full executable order (augmenting Phase 3's contract selection with limit price, contract count, max profit/loss, breakeven). No graph wiring (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Black-Scholes Inputs & Pricing Agent Data Flow
- Risk-free rate: config default `0.05` (5%) — simple, deterministic, no extra API call
- Dividend yield: `0.0` default, override from yfinance fundamentals `info["dividendYield"]` if available in state flow
- Time to expiry: calendar days from `trade_date` to expiry date / 365.25 (standard)
- Pricing agent reads Phase 3's `options_legs` string via regex — no Tradier re-fetch for pricing inputs

### options_legs Field & Order Structure
- Legs builder overwrites the same `options_legs` field — Phase 3's basic contract info replaced with full executable order
- Contract count: fixed 1 contract per leg — position sizing is caller's responsibility
- Limit price: market mid (avg of bid/ask) from parsed options chain data
- Wide bid/ask flag threshold: >10% of mid as stated in ROADMAP

### Greeks Monitor Data Source & Aggregation
- Greeks data: re-fetch options chain from Tradier for full per-contract gamma/theta/vega; delta already in `options_legs` string but re-fetched for consistency
- Portfolio aggregation: dollar-adjusted — net_delta = Σ(sign × delta × contracts × 100 × underlying_price); sign = +1 BUY, -1 SELL
- Thresholds applied to dollar-adjusted Greeks (matches ROADMAP: delta_heavy = |dollar_delta| > $5,000)
- Graceful fallback when Tradier unavailable: use delta from `options_legs` string, set gamma/theta/vega to 0.0, flag report with "Greeks unavailable — Tradier data required"

### Claude's Discretion
- Exact Black-Scholes implementation details (normal CDF approximation vs scipy.stats.norm)
- Edge verdict thresholds: what constitutes "positive edge" vs "fairly priced" vs "overpriced"
- Exact LLM prompt wording for pricing agent verdict
- Error handling for malformed `options_legs` strings from Phase 3
- Directory structure: `tradingagents/agents/options/utils/` for black_scholes.py

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/agents/options/volatility_analyst.py` — single-pass LLM factory pattern to follow exactly
- `tradingagents/agents/options/strike_expiry_selector.py` — Python-first data processing + structured string output pattern
- `tradingagents/agents/utils/agent_states.py` — AgentState TypedDict to extend with `options_pricing_report` and `greeks_report`
- `tradingagents/dataflows/interface.py` — `route_to_vendor("get_options_chain", ...)` for Greeks re-fetch
- `tradingagents/agents/options/__init__.py` — export new factories

### Established Patterns
- Factory: `def create_X(llm): def node(state): ...; return {"field": result}; return node`
- AgentState fields: `field: Annotated[str, "description"]`
- Tests: `unittest.mock.patch` on `route_to_vendor`, MagicMock LLM with `return_value` on `invoke`
- System prompt uses angle-bracket placeholders (not curly braces) to avoid LangChain template conflicts
- Modules keep helpers local (no shared utils across agents) per established pattern

### Integration Points
- `tradingagents/agents/utils/agent_states.py` — add `options_pricing_report` and `greeks_report`
- `tradingagents/agents/options/__init__.py` — export `create_options_pricing_agent`, `create_options_legs_builder`, `create_greeks_monitor`
- `tradingagents/agents/__init__.py` — export new factories
- Phase 3 `options_legs` format consumed: `"LEG N: BUY/SELL CALL/PUT {TICKER} {EXPIRY} ${STRIKE} δ={delta} OI={oi} [{PASS|FAIL}]"`
- Phase 4 `options_legs` output format: full executable order with limit price, max profit/loss, breakeven, wide spread flag

</code_context>

<specifics>
## Specific Ideas

- Black-Scholes location: `tradingagents/agents/options/utils/black_scholes.py` with `__init__.py` in `utils/`
- BS inputs: underlying_price, strike, time_to_expiry (years), risk_free_rate, dividend_yield, implied_volatility
- Export: `call_price(S, K, T, r, q, sigma)` and `put_price(S, K, T, r, q, sigma)`
- Edge calculation: `(theoretical_value - market_mid) / market_mid * 100` as percentage
- Verdict logic: edge > +5% = "positive edge"; edge < -5% = "overpriced"; otherwise "fairly priced"
- Greeks monitor threshold flags exactly per REQUIREMENTS: delta_heavy (|dollar_delta| > $5k), pin_risk (gamma > 0.10 within 5 DTE), high_decay (theta < -$200/day), vol_sensitive (|dollar_vega| > $500 per 1% IV)
- `options_legs` final format per leg: `"LEG N: BUY/SELL CALL/PUT {TICKER} {EXPIRY} ${STRIKE} limit=${limit:.2f} qty=1 [{WIDE_SPREAD|OK}]"` followed by summary line: `"NET: debit=${debit:.2f} max_profit=${mp} max_loss=${ml} breakeven=${be:.2f}"`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
