# Phase 5: Graph Integration - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire all 7 options agents into the existing `StateGraph` as a parallel branch alongside equity analysts. Add conditional routing so the options branch activates when `enable_options` is true and is skipped entirely when false. Equity-only mode remains fully functional. No agent logic changes — pure graph plumbing.

</domain>

<decisions>
## Implementation Decisions

### Options Branch Internal Sequencing
- All 7 options agents run sequentially: volatility_analyst → options_flow_analyst → options_strategy_selector → strike_expiry_selector → options_pricing_agent → options_legs_builder → greeks_monitor
- All options agents use `quick_thinking_llm` — these are formatting/computation agents, not deep reasoning
- Options agents read ticker from `state["company_of_interest"]` and date from `state["trade_date"]` — already in AgentState

### Parallel Branch & Merge Point
- Options branch starts from START — runs in parallel with the first equity analyst
- Merge point: before Bull Researcher — equity analysts and options branch must both complete before investment debate begins with full context
- LangGraph implementation: fan-out from START to both branches; fan-in node before Bull Researcher that waits for both
- Graceful degradation on failure — if options branch fails, options fields stay empty strings, equity flow continues unaffected

### Conditional Routing & Backward Compatibility
- `enable_options=False` (default): conditional edge from START routes only to equity analyst path. Options nodes not visited at all.
- `enable_options` read from `get_config()` at graph compile time — set once before run
- `setup_graph()` API extended with optional `enable_options=False` parameter
- Minimal test updates: assert options fields are absent/empty in equity-only mode; existing tests pass as-is since new AgentState fields default to empty

### Claude's Discretion
- Exact fan-in implementation (LangGraph `add_edge` from both branch endpoints to same target vs dedicated merge node)
- Error handling/try-except wrapping for individual options agents within the chain
- Whether options agents need message clear nodes (like equity analysts do) or can operate without tool calls
- Test structure for integration smoke test (mock all LLMs and data calls vs selective mocking)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/graph/setup.py` — `GraphSetup.setup_graph()` is the single graph construction method; equity analysts wired sequentially with tool/clear cycles
- `tradingagents/graph/conditional_logic.py` — `ConditionalLogic` class with `should_continue_*` methods for each analyst; need to add options-related conditional methods
- `tradingagents/agents/options/__init__.py` — all 7 factory functions already exported
- `tradingagents/agents/utils/agent_states.py` — all 6 options fields already in AgentState
- `tradingagents/default_config.py` — `enable_options`, `options_vendor`, `options_delta_target`, `options_dte_window`, `options_min_oi` already present

### Established Patterns
- All analyst nodes created via `create_X(llm)` factory
- Equity analysts use tool-calling: analyst → conditional(tool_calls?) → tools → loop or clear → next
- Options agents do NOT use tool-calling — they are single-pass (compute + LLM format), so they don't need tool/clear cycles
- Graph compiled via `workflow.compile()` at end of `setup_graph()`

### Integration Points
- `tradingagents/graph/setup.py` — add options nodes, fan-out from START, fan-in before Bull Researcher
- `tradingagents/graph/conditional_logic.py` — add conditional method for `enable_options` routing
- `tradingagents/graph/__init__.py` — may need to export updated components
- `tradingagents/trading_graph.py` (if exists) — may need to pass `enable_options` through

</code_context>

<specifics>
## Specific Ideas

- Options agents are simpler than equity analysts — no tool-calling, no message clear needed
- Each options agent: `workflow.add_node("Options: Volatility Analyst", vol_analyst_node)` etc.
- Sequential chain: `workflow.add_edge("Options: Volatility Analyst", "Options: Flow Analyst")` etc.
- Fan-out: `workflow.add_edge(START, "Market Analyst")` + `workflow.add_edge(START, "Options: Volatility Analyst")` when enabled
- Fan-in: last equity clear → "Bull Researcher", last options agent → "Bull Researcher" (LangGraph handles waiting for all incoming edges)
- Config key `enable_options` already in DEFAULT_CONFIG as `False`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
