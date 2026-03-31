# Requirements: TradingAgents — Options Extension

**Defined:** 2026-03-31
**Core Value:** Trader receives a complete, executable options recommendation derived from the same AI analytical process that drives the equity decision

## v1 Requirements

### Options Data Infrastructure

- [ ] **DATA-01**: Tradier API client integrated using existing `requests`-based pattern (same as Alpha Vantage)
- [ ] **DATA-02**: Options chain data retrievable per ticker: strikes, expiries, bid/ask, volume, open interest, greeks (delta, gamma, theta, vega), IV per contract
- [ ] **DATA-03**: Options vendor abstraction layer added to `interface.py` using existing `VENDOR_METHODS` routing pattern with a new `options_data` category
- [ ] **DATA-04**: Tradier API key configured via `.env` and `DEFAULT_CONFIG`
- [ ] **DATA-05**: Historical IV data retrievable per ticker over 52-week window (for IV rank/percentile calculation)

### New Options Agents

- [ ] **AGENT-01**: Volatility analyst agent (`volatility_analyst.py`) — outputs IV rank, IV percentile, IV vs 30-day HV (rich/cheap), skew shape, term structure (contango/backwardation), one-line regime summary
- [ ] **AGENT-02**: Options flow analyst agent (`options_flow_analyst.py`) — outputs unusual volume vs OI, block/sweep detection, put/call ratio divergence vs recent average, net flow bias, one-line directional implication
- [ ] **AGENT-03**: Options strategy selector agent (`options_strategy_selector.py`) — maps directional bias + IV view + time horizon + risk preference to single strategy from defined list; includes one-sentence rationale
- [ ] **AGENT-04**: Strike and expiry selector agent (`strike_expiry_selector.py`) — selects specific expiry date and strike(s) per leg given strategy type, delta targets, DTE window, OI threshold; outputs liquidity pass/fail per leg
- [ ] **AGENT-05**: Options pricing agent (`options_pricing_agent.py`) — computes Black-Scholes theoretical value per leg, net structure value, market mid, edge ($ and %), one-line verdict (fairly priced / positive edge / overpriced)
- [ ] **AGENT-06**: Options legs builder agent (`options_legs_builder.py`) — generates structured multi-leg order (BUY/SELL, contract count, ticker, expiry, strike, option type, limit price); outputs net debit/credit, max profit, max loss, breakeven; flags wide bid/ask (>10% of mid)
- [ ] **AGENT-07**: Greeks monitor agent (`greeks_monitor.py`) — computes portfolio-level net delta, gamma, theta, vega from open positions; flags: delta heavy (|delta| > $5k), pin/gamma risk (gamma > 0.10 within 5 DTE), high decay cost (theta < -$200/day), vol sensitive (|vega| > $500 per 1% IV)

### Graph Integration

- [ ] **GRAPH-01**: Options agents wired into `StateGraph` as parallel branch alongside existing equity agents
- [ ] **GRAPH-02**: `AgentState` extended with options-specific fields: `volatility_report`, `options_flow_report`, `options_strategy`, `options_legs`, `options_pricing_report`, `greeks_report`
- [ ] **GRAPH-03**: Options branch results available to Risk Judge before final decision
- [ ] **GRAPH-04**: Existing equity-only mode remains fully functional — options branch is additive (can be enabled/disabled via config)
- [ ] **GRAPH-05**: `DEFAULT_CONFIG` updated with options settings: `enable_options`, `options_vendor`, `options_delta_target`, `options_dte_window`, `options_min_oi`

### Debator Agent Updates

- [ ] **DEBATE-01**: Aggressive debator prompt extended with options-specific assessment: defined vs undefined max loss, payoff shape (long premium / short premium), Greeks risk flags (excess theta decay, uncapped vega, conflicting delta), assignment and pin risk
- [ ] **DEBATE-02**: Conservative debator prompt extended with same options-specific assessment additions
- [ ] **DEBATE-03**: Neutral debator prompt extended with same options-specific assessment additions
- [ ] **DEBATE-04**: All three debators adjust their stance (aggressive / conservative / neutral) to reflect options-specific risks in addition to directional risk

### Risk Manager Updates

- [ ] **RISK-01**: Risk Manager enforces max loss gate — rejects any trade where max loss is undefined unless portfolio collateral is documented
- [ ] **RISK-02**: Risk Manager requires defined exit rule for short premium strategies (condors, strangles, naked puts/calls) — e.g. "close at 2x premium received" or "close at 21 DTE"
- [ ] **RISK-03**: Risk Manager checks for early assignment risk on short ITM legs of spreads, flagging proximity to ex-dividend dates
- [ ] **RISK-04**: Risk Manager verifies net Greeks of proposed trade do not exceed portfolio thresholds (defers to Greeks Monitor output)
- [ ] **RISK-05**: Risk Manager flags any strategy with negative theta on a position intended to be held more than 30 days without a catalyst

### Black-Scholes Pricing

- [ ] **PRICE-01**: Black-Scholes implementation for call and put theoretical value (inputs: underlying price, strike, time to expiry, risk-free rate, dividend yield, IV)
- [ ] **PRICE-02**: Risk-free rate sourced from config or fetched (e.g. 3-month T-bill rate)
- [ ] **PRICE-03**: Dividend yield sourced from existing fundamentals data (yfinance already retrieves this)

## v2 Requirements

### Enhanced Data

- **DATA-V2-01**: Real-time IV surface / skew visualization output
- **DATA-V2-02**: Historical options flow data for multi-day trend analysis
- **DATA-V2-03**: Polygon.io as alternative options vendor

### Portfolio Management

- **PORT-01**: Persistent open options positions tracker (survives process restart)
- **PORT-02**: Greeks monitor running against live portfolio state, not just proposed trade
- **PORT-03**: Automatic exit rule enforcement (alert when 2x premium or 21 DTE threshold hit)

### Backtesting

- **BACK-01**: Options strategy backtesting via backtrader integration (dependency already present)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live broker order submission | Analysis and order generation only — no automated trade execution |
| Real-time streaming data | Batch/on-demand only, consistent with existing equity pipeline |
| Options portfolio UI / dashboard | Out of scope for v1 — CLI output sufficient |
| Volatility surface modelling (full smile) | IV skew analysis via agent prompt is sufficient; full surface model is quant research scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 to DATA-05 | Phase 1 | Pending |
| AGENT-01, AGENT-02 | Phase 2 | Pending |
| AGENT-03, AGENT-04 | Phase 3 | Pending |
| AGENT-05, AGENT-06, AGENT-07 | Phase 4 | Pending |
| PRICE-01 to PRICE-03 | Phase 4 | Pending |
| GRAPH-01 to GRAPH-05 | Phase 5 | Pending |
| DEBATE-01 to DEBATE-04 | Phase 6 | Pending |
| RISK-01 to RISK-05 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after initialization*
