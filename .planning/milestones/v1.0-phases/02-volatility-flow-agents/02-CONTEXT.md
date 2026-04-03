# Phase 2: Volatility & Flow Agents - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Build two specialist LangGraph agent factory functions — `create_volatility_analyst` and `create_options_flow_analyst` — that compute their respective metrics from Phase 1's data layer and use a single LLM call to produce a structured one-paragraph report written to `AgentState`. Also extend `AgentState` with the two new report fields. No graph wiring (Phase 5 handles that).

</domain>

<decisions>
## Implementation Decisions

### Agent Architecture
- Single-pass architecture: Python computes all numeric metrics, LLM receives computed values and writes the narrative paragraph (no ReAct tool-calling loop)
- Historical volatility (30-day HV) computed from yfinance stock price data using `pct_change().rolling(21).std() * sqrt(252)`
- Agents write to their named state field only — do NOT add to `AgentState.messages` thread
- Unit tests mock both the data layer (interface calls) and the LLM; no live API calls in tests

### Report Format & Content
- Report is structured prose with labeled metrics, e.g. "IV Rank: 72 (high). IV Percentile: 68th. IV vs HV: Rich (+8pp). Skew: Put skew elevated. Term structure: Contango. Regime: Elevated IV, put-bid market — favor selling premium or buying protection."
- One paragraph per agent (matches ROADMAP "one-paragraph report" spec)
- Numeric metrics embedded in the prose text — no separate numeric AgentState fields alongside the narrative
- LLM writes the full paragraph given structured prompt containing computed metrics and a format template

### AgentState Extension
- New fields `volatility_report` and `options_flow_report` added directly to existing `tradingagents/agents/utils/agent_states.py`
- New agent files placed in `tradingagents/agents/options/` subdirectory (create `__init__.py` too)
- IV rank and IV percentile computed using `get_historical_iv` output from Phase 1 (52-week window)
- Agents assume they are only invoked when options is enabled — no `enable_options` config check inside agent logic

### Claude's Discretion
- Exact LLM prompt wording for both agents
- Whether to use `quick_thinking_llm` or `deep_thinking_llm` (quick preferred — these are formatting tasks)
- Error handling for missing/empty data (e.g. no options chain data returned)
- Specific thresholds for "high" vs "low" IV rank labels in the narrative

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/agents/analysts/market_analyst.py` — reference for `create_*` factory pattern and `ChatPromptTemplate` usage
- `tradingagents/agents/utils/agent_states.py` — AgentState TypedDict to extend with new fields
- `tradingagents/dataflows/interface.py` — `route_to_vendor("get_options_chain", ...)` and `route_to_vendor("get_historical_iv", ...)` for data access
- `tradingagents/dataflows/tradier_utils.py` (Phase 1) — `get_options_chain`, `get_historical_iv`, `get_options_expirations`
- `tradingagents/dataflows/y_finance_options.py` (Phase 1) — fallback with same signatures

### Established Patterns
- All agents are factory functions returning closures: `def create_X(llm): def node(state): ...; return node`
- LLM accessed via parameter (injected at graph-build time), not imported globally
- AgentState fields are `Annotated[str, "description"]`
- Results written as `return {"field_name": result_string}`

### Integration Points
- `tradingagents/agents/utils/agent_states.py` — add `volatility_report` and `options_flow_report`
- `tradingagents/agents/__init__.py` — may need to export new agents
- `tradingagents/agents/options/` — new subdirectory (create with `__init__.py`)

</code_context>

<specifics>
## Specific Ideas

- IV rank formula: `(current_iv - 52w_low) / (52w_high - 52w_low) * 100`
- IV percentile: percentage of days in 52-week window where IV was below current IV
- Skew shape derived from comparing OTM put IV to OTM call IV at same delta distance
- Term structure: compare near-term expiry IV to far-term expiry IV (contango = far > near)
- Flow unusual volume: flag when option volume > 2× average daily OI for that contract
- Put/call ratio divergence: compare today's P/C ratio to 20-day average

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
