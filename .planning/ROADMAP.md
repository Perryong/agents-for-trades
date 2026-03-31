# Roadmap: TradingAgents — Options Extension

**Total phases:** 6
**Milestone:** v1 — Options Pipeline

## Phases

- [x] **Phase 1: Options Data Infrastructure** - Tradier client, options chain + historical IV, vendor abstraction layer, config keys (completed 2026-03-31)
- [x] **Phase 2: Volatility & Flow Agents** - IV regime analysis agent and options flow analysis agent (completed 2026-03-31)
- [ ] **Phase 3: Strategy & Contract Selection Agents** - Strategy selector agent and strike/expiry selector agent
- [ ] **Phase 4: Pricing, Order Building & Greeks** - Black-Scholes utility, pricing agent, legs builder, Greeks monitor
- [ ] **Phase 5: Graph Integration** - Options branch wired into StateGraph, AgentState extended, enable_options config flag
- [ ] **Phase 6: Debator & Risk Manager Updates** - Options-aware prompts for all debators and Risk Manager enforcement rules

---

## Phase Details

### Phase 1: Options Data Infrastructure

**Goal:** The system can retrieve options chain data and historical IV from Tradier, routed through the same vendor abstraction layer used by equity data.
**Depends on:** Nothing (foundation)
**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — Tradier API client (tradier_utils.py) with test infrastructure and unit tests
- [x] 01-02-PLAN.md — yfinance options fallback module (y_finance_options.py) with matching function signatures
- [x] 01-03-PLAN.md — Vendor abstraction wiring (interface.py + default_config.py) with config keys and fallback routing

**Success criteria:**
- [ ] `interface.get_options_chain("AAPL")` returns a populated dataframe with strike, expiry, bid, ask, volume, OI, delta, gamma, theta, vega, IV columns
- [ ] `interface.get_historical_iv("AAPL")` returns at least 52 weeks of daily IV observations
- [ ] Swapping `options_vendor` in config routes calls without changing agent code
- [ ] Running in equity-only mode (default config) produces no errors and no Tradier calls

---

### Phase 2: Volatility & Flow Agents

**Goal:** Two specialist agents can independently characterize the IV environment and options market flow for a ticker, each producing a structured one-paragraph report.
**Depends on:** Phase 1
**Requirements:** AGENT-01, AGENT-02
**Plans:** 2/2 plans complete

Plans:
- [x] 02-01-PLAN.md — AgentState extension + volatility analyst agent (IV rank, IV percentile, HV, skew, term structure)
- [x] 02-02-PLAN.md — Options flow analyst agent (unusual volume, P/C ratio, net flow bias)

**Success criteria:**
- [ ] `volatility_analyst` node populates `state["volatility_report"]` with IV rank, IV percentile, HV comparison, skew descriptor, term structure descriptor, and regime summary string
- [ ] `options_flow_analyst` node populates `state["options_flow_report"]` with unusual volume flag, sweep/block flag, put/call ratio divergence, net bias, and directional implication string
- [ ] Both agents call only `quick_thinking_llm` / `deep_thinking_llm` — no new LLM dependencies
- [ ] Both agents are importable and callable standalone (unit testable without graph)

---

### Phase 3: Strategy & Contract Selection Agents

**Goal:** Given directional bias and IV view from upstream agents, the system selects a single named options strategy and then identifies specific liquid contracts for each leg.
**Depends on:** Phase 2
**Requirements:** AGENT-03, AGENT-04
**Plans:** 2 plans

Plans:
- [ ] 03-01-PLAN.md — Options strategy selector agent + AgentState extension with options_strategy and options_legs fields
- [ ] 03-02-PLAN.md — Strike and expiry selector agent with Python-first deterministic contract filtering

**Success criteria:**
- [ ] `options_strategy` field in state names exactly one strategy from the defined list with a rationale string
- [ ] `strike_expiry_selector` selects contracts that satisfy the configured `options_delta_target`, `options_dte_window`, and `options_min_oi` thresholds
- [ ] Each leg in the output carries a liquidity pass/fail flag based on OI threshold
- [ ] If no liquid contracts satisfy constraints, the agent emits a `liquidity_fail` flag rather than selecting an illiquid contract

---

### Phase 4: Pricing, Order Building & Greeks

**Goal:** The system computes theoretical value and edge for the selected structure, produces a complete executable multi-leg order, and provides portfolio-level Greeks with threshold flags.
**Depends on:** Phase 3
**Requirements:** AGENT-05, AGENT-06, AGENT-07, PRICE-01, PRICE-02, PRICE-03

### Plans
1. Black-Scholes utility — implement `tradingagents/agents/options/utils/black_scholes.py`; functions for call and put theoretical value; inputs: underlying price, strike, time to expiry, risk-free rate, dividend yield, IV; risk-free rate from config or fetched (3-month T-bill); dividend yield sourced from existing yfinance fundamentals data
2. Options pricing agent — implement `tradingagents/agents/options/options_pricing_agent.py` using `create_options_pricing_agent` factory; compute BS theoretical value per leg, net structure value, market mid, edge in $ and %; emit one-line verdict (fairly priced / positive edge / overpriced); write to `AgentState["options_pricing_report"]`
3. Options legs builder agent — implement `tradingagents/agents/options/options_legs_builder.py` using `create_options_legs_builder` factory; generate structured multi-leg order (BUY/SELL, contract count, ticker, expiry, strike, option type, limit price); output net debit/credit, max profit, max loss, breakeven; flag wide bid/ask (>10% of mid); write final order to `AgentState["options_legs"]`
4. Greeks monitor agent — implement `tradingagents/agents/options/greeks_monitor.py` using `create_greeks_monitor` factory; compute portfolio-level net delta, gamma, theta, vega; flag delta heavy (|delta| > $5k), pin/gamma risk (gamma > 0.10 within 5 DTE), high decay cost (theta < -$200/day), vol sensitive (|vega| > $500 per 1% IV); write to `AgentState["greeks_report"]`

**Success criteria:**
- [ ] `black_scholes.call_price` and `black_scholes.put_price` return values within 1% of known benchmark prices for standard test cases
- [ ] `options_pricing_report` contains theoretical value, market mid, edge ($ and %), and a verdict string for each leg and the net structure
- [ ] `options_legs` contains a complete executable order: action, quantity, ticker, expiry, strike, type, limit price, max profit, max loss, breakeven, and wide-spread flag
- [ ] `greeks_report` contains net delta, gamma, theta, vega and a boolean flag for each of the four threshold conditions

---

### Phase 5: Graph Integration

**Goal:** Options agents run as a parallel branch inside the existing StateGraph; the options branch activates when `enable_options` is true and the equity-only path remains fully functional without it.
**Depends on:** Phase 4
**Requirements:** GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05

### Plans
1. AgentState extension — add `volatility_report`, `options_flow_report`, `options_strategy`, `options_legs`, `options_pricing_report`, `greeks_report` fields to `AgentState`; all fields optional with `None` default so equity-only mode is unaffected
2. Graph wiring — add options branch nodes to `StateGraph` in parallel with equity analyst nodes; connect branch output to the Risk Judge (risk manager) node; add `DEFAULT_CONFIG` keys (`enable_options`, `options_vendor`, `options_delta_target`, `options_dte_window`, `options_min_oi`); add conditional routing so options nodes are skipped when `enable_options` is false
3. Integration smoke test — run full graph with `enable_options=True` on a single ticker end-to-end; verify all six options state fields are populated; run with `enable_options=False` and verify equity output is identical to pre-extension baseline

**Success criteria:**
- [ ] Full graph run with `enable_options=True` produces a final decision that includes both equity analysis and options recommendation fields
- [ ] All six options state fields (`volatility_report`, `options_flow_report`, `options_strategy`, `options_legs`, `options_pricing_report`, `greeks_report`) are non-null after a complete options-enabled run
- [ ] Full graph run with `enable_options=False` (default) produces output identical in structure to the pre-extension equity-only run — no errors, no missing fields
- [ ] Options branch nodes execute in parallel with equity analyst nodes, not sequentially after them

---

### Phase 6: Debator & Risk Manager Updates

**Goal:** All three debators reason about options-specific risk (max loss shape, Greeks, assignment/pin risk) and the Risk Manager enforces five options-specific rules before approving any options trade.
**Depends on:** Phase 5
**Requirements:** DEBATE-01, DEBATE-02, DEBATE-03, DEBATE-04, RISK-01, RISK-02, RISK-03, RISK-04, RISK-05

### Plans
1. Debator prompt extensions — add options-specific assessment block to prompts in `aggressive_debator.py`, `conservative_debator.py`, `neutral_debator.py`; block covers: defined vs undefined max loss, payoff shape (long/short premium), Greeks risk flags (excess theta, uncapped vega, conflicting delta), assignment risk, pin risk; each debator adjusts stance to reflect options risks
2. Risk Manager enforcement rules — add five conditional checks to `risk_manager.py` that activate when options fields are present in state: max loss gate (reject undefined max loss without documented collateral), exit rule requirement (short premium strategies must have a defined exit rule), early assignment check (flag short ITM legs near ex-dividend dates), Greeks threshold gate (defer to `greeks_report` flags), negative theta flag (flag theta-negative positions held >30 days without catalyst)

**Success criteria:**
- [ ] In a full graph run with `enable_options=True`, the aggressive debator output contains explicit options-specific language (references to max loss, payoff shape, or Greeks risk)
- [ ] In a full graph run with `enable_options=True`, the conservative and neutral debator outputs similarly contain options-specific assessment language
- [ ] Risk Manager rejects (or explicitly flags) a proposed options trade where max loss is undefined and no collateral is documented
- [ ] Risk Manager output for a short premium strategy includes an exit rule requirement note
- [ ] Equity-only runs produce no changes to debator or Risk Manager behavior

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Options Data Infrastructure | 3/3 | Complete   | 2026-03-31 |
| 2. Volatility & Flow Agents | 2/2 | Complete   | 2026-03-31 |
| 3. Strategy & Contract Selection Agents | 0/2 | Not started | - |
| 4. Pricing, Order Building & Greeks | 0/4 | Not started | - |
| 5. Graph Integration | 0/3 | Not started | - |
| 6. Debator & Risk Manager Updates | 0/2 | Not started | - |

---

## Milestone: v1 Complete

**Definition of done:**
- [ ] A full graph run with `enable_options=True` produces a final decision containing: equity direction, named options strategy, specific leg-by-leg order (ticker, expiry, strike, action, limit price), net debit/credit, max profit/loss, breakeven, and Greeks risk flags
- [ ] All three debators incorporate options-specific assessment in their arguments
- [ ] Risk Manager enforces all five options rules and blocks undefined-risk trades
- [ ] Running with `enable_options=False` (default) is indistinguishable from the pre-extension system
- [ ] All 30 v1 requirements mapped and implemented (DATA-01 to DATA-05, AGENT-01 to AGENT-07, GRAPH-01 to GRAPH-05, DEBATE-01 to DEBATE-04, RISK-01 to RISK-05, PRICE-01 to PRICE-03)

---

*Roadmap created: 2026-03-31*
*Requirements coverage: 30/30 v1 requirements mapped*
