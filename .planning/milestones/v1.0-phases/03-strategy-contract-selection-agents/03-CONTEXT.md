# Phase 3: Strategy & Contract Selection Agents - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Build two agent factory functions — `create_options_strategy_selector` and `create_strike_expiry_selector` — that together select a named options strategy and identify specific liquid contracts for each leg. Extends AgentState with `options_strategy` and `options_legs` fields. No graph wiring (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Strategy Selector Architecture
- Pure LLM agent: reads `volatility_report`, `options_flow_report`, and `investment_plan` text fields from state directly; no structured parsing step
- Inputs: `state["volatility_report"]` + `state["options_flow_report"]` + `state["investment_plan"]`
- Output `options_strategy`: plain string with embedded strategy name and rationale, e.g. `"Bull Call Spread — IV is moderate, directional bias bullish, defined risk preferred"`
- System prompt embeds the full 10-strategy list as a numbered constraint: LLM MUST pick one; prevents hallucinated strategy names
- Defined strategy list: long call, long put, bull call spread, bear put spread, iron condor, covered call, cash-secured put, long straddle, long strangle, calendar spread

### Strike/Expiry Selector Logic
- Python-first: filter options chain by delta/DTE/OI thresholds in Python; LLM not used for selection, only for formatting if needed
- Delta tolerance band: ±0.05 around `options_delta_target` (e.g., target=0.30 → accept 0.25–0.35)
- Output `options_legs`: structured string, one leg per line, e.g. `"LEG 1: BUY CALL AAPL 2026-01-17 $150 δ=0.32 OI=1240 [PASS]"`
- Liquidity fail: embed `[LIQUIDITY FAIL]` marker in `options_legs` string when no contracts satisfy constraints — "No contracts satisfy delta=0.30 ±0.05 within DTE [21,45] with OI>100. [LIQUIDITY FAIL]"
- No separate `options_liquidity_fail` boolean field in AgentState

### AgentState Extension
- Add `options_strategy: Annotated[str, "..."]` and `options_legs: Annotated[str, "..."]` to existing `tradingagents/agents/utils/agent_states.py`
- Same file as all prior phases (no separate options state extension)

### Testing
- Strategy selector tests: pass fixture strings directly in state dict (`{"volatility_report": "IV Rank: 72...", "investment_plan": "Bullish — price target $160", ...}`)
- Strike/expiry tests: use controlled DataFrame fixture (deterministic options chain with known strikes/deltas/OI)
- Strategy selector tests: assert output contains one of the 10 defined strategy names
- All mocks: mock `route_to_vendor` for data layer; mock LLM via MagicMock callable

### Claude's Discretion
- Exact system prompt wording for strategy selector
- How to read strategy name from `options_strategy` string (Phase 4 consumer responsibility)
- Error handling when upstream reports are empty strings
- Which expiry to select when multiple satisfy DTE window (closest to center of window)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/agents/options/volatility_analyst.py` — single-pass LLM factory pattern to follow exactly
- `tradingagents/agents/options/options_flow_analyst.py` — `_parse_tabular_string` and `_compute_flow_metrics` helpers pattern
- `tradingagents/agents/utils/agent_states.py` — AgentState to extend with 2 new fields
- `tradingagents/dataflows/interface.py` — `route_to_vendor("get_options_chain", ...)` and `route_to_vendor("get_options_expirations", ...)` for data

### Established Patterns
- Factory: `def create_X(llm): def node(state): ...; return {"field": result}; return node`
- AgentState fields: `field: Annotated[str, "description"]`
- Tests: `unittest.mock.patch` on `route_to_vendor`, MagicMock LLM with `return_value` on `invoke`

### Integration Points
- `tradingagents/agents/utils/agent_states.py` — add `options_strategy` and `options_legs`
- `tradingagents/agents/options/__init__.py` — export new factories
- `tradingagents/agents/__init__.py` — export new factories
- Phase 4 consumer will read `options_strategy` to determine pricing model and `options_legs` for contract details

</code_context>

<specifics>
## Specific Ideas

- Strategy selector system prompt must list all 10 strategies by name so LLM output is constrained
- Strike/expiry selector: when multiple expirations satisfy DTE window, pick the one closest to the center of the window
- Strike selection: sort filtered contracts by |delta - target| ascending, pick the closest match
- `options_legs` format per leg: `"LEG N: BUY/SELL CALL/PUT {TICKER} {EXPIRY} ${STRIKE} δ={delta} OI={oi} [{PASS|FAIL}]"`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
