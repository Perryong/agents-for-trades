# Phase 5: Graph Integration - Research

**Researched:** 2026-04-01
**Domain:** LangGraph StateGraph wiring — parallel branch, conditional routing, fan-in
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Options agents run sequentially within their branch: volatility_analyst → options_flow_analyst → options_strategy_selector → strike_expiry_selector → options_pricing_agent → options_legs_builder → greeks_monitor
- All options agents use `quick_thinking_llm`
- Options agents read ticker from `state["company_of_interest"]` and date from `state["trade_date"]`
- Options branch starts from START — runs in parallel with the first equity analyst
- Merge point: before Bull Researcher — both equity and options branches must complete before debate begins
- LangGraph implementation: fan-out from START to both branches; fan-in node before Bull Researcher that waits for both
- Graceful degradation: if options branch fails, options fields stay empty strings, equity flow continues unaffected
- `enable_options=False` (default): conditional edge from START routes only to equity analyst path; options nodes not visited at all
- `enable_options` read from `get_config()` at graph compile time — set once before run
- `setup_graph()` API extended with optional `enable_options=False` parameter
- Minimal test updates: assert options fields are absent/empty in equity-only mode; existing tests pass as-is since new AgentState fields default to empty

### Claude's Discretion
- Exact fan-in implementation (LangGraph `add_edge` from both branch endpoints to same target vs dedicated merge node)
- Error handling / try-except wrapping for individual options agents within the chain
- Whether options agents need message clear nodes or can operate without tool calls
- Test structure for integration smoke test (mock all LLMs and data calls vs selective mocking)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GRAPH-01 | Options agents wired into StateGraph as parallel branch alongside existing equity agents | Verified: LangGraph 1.1.3 supports multiple START edges as parallel branches; fan-in to single node works |
| GRAPH-02 | AgentState extended with options fields: volatility_report, options_flow_report, options_strategy, options_legs, options_pricing_report, greeks_report | Already implemented in agent_states.py — all 6 fields confirmed present with Annotated[str, ...] type |
| GRAPH-03 | Options branch results available to Risk Judge before final decision | Merge point before Bull Researcher puts all options state in scope for entire debate + risk path |
| GRAPH-04 | Equity-only mode remains fully functional — options branch additive | Verified: conditional_edges from START returning list; disabled mode omits options nodes entirely |
| GRAPH-05 | DEFAULT_CONFIG updated with options settings | Already implemented — all 5 keys present: enable_options, options_vendor, options_delta_target, options_dte_window, options_min_oi |
</phase_requirements>

---

## Summary

Phase 5 is pure graph plumbing — no new agent logic. The codebase audit confirms that GRAPH-02 (AgentState fields) and GRAPH-05 (DEFAULT_CONFIG keys) are already implemented from prior phases. The only work is in `tradingagents/graph/setup.py` and `tradingagents/graph/conditional_logic.py`.

LangGraph 1.1.3 (installed) natively supports fan-out from START by returning a list from a conditional router, and fan-in by pointing multiple branch endpoints at the same destination node. This has been verified by live execution: when `enable_options=False`, options nodes are not visited and the state fields remain as initialized; when `enable_options=True`, both branches execute concurrently and merge their state before the debate nodes run.

The integration smoke test requires mocking all 7 options agent factory outputs (they each return a dict with one key) plus mocking all LLM and data layer calls. The equity-only baseline assertion is straightforward — run with `enable_options=False` and confirm the six options state fields are absent or empty.

**Primary recommendation:** Use `add_conditional_edges(START, route_fn, ["Market Analyst", "Options: Volatility Analyst"])` for the fan-out and `add_edge("Options: Greeks Monitor", "Bull Researcher")` plus `add_edge("Msg Clear {last_equity}", "Bull Researcher")` for the fan-in. LangGraph handles the implicit synchronization.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langgraph | 1.1.3 (installed) | StateGraph wiring, conditional routing, fan-out/fan-in | Already in use throughout the project |
| langchain-core | installed (project dependency) | ChatPromptTemplate, Runnable interface | Used by all existing agents |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 7.4.4 (installed) | Test runner for integration smoke test | All tests in this project use pytest |
| unittest.mock | stdlib | Mock LLMs and data layer for testing | Established pattern in all options agent tests |

**Installation:** No new dependencies required for this phase.

---

## Architecture Patterns

### Current Graph Flow (equity-only)
```
START
  └── Market Analyst ──(tool calls?)──→ tools_market ─┐
                                                       └──→ Msg Clear Market
                                                              └──→ Technical Analyst → ... → Msg Clear {last}
                                                                                                └──→ Bull Researcher
                                                                                                       ↕ (debate rounds)
                                                                                                     Bear Researcher
                                                                                                       └──→ Research Manager
                                                                                                              └──→ Trader
                                                                                                                     └──→ Aggressive Analyst ↔ Conservative Analyst ↔ Neutral Analyst
                                                                                                                                                └──→ Risk Judge → END
```

### Target Graph Flow (with options branch)
```
START
  ├── Market Analyst ──(tool calls?)──→ tools_market ─┐
  │                                                    └──→ Msg Clear Market → ... → Msg Clear {last_equity} ──┐
  │                                                                                                              │
  └── Options: Volatility Analyst                                                                               │
       └──→ Options: Flow Analyst                                                                               │
             └──→ Options: Strategy Selector                                                                    │
                   └──→ Options: Strike/Expiry                                                                  │
                         └──→ Options: Pricing Agent                                                            │
                               └──→ Options: Legs Builder                                                       │
                                     └──→ Options: Greeks Monitor ──────────────────────────────────────────────┤
                                                                                                                 ↓
                                                                                                          Bull Researcher
                                                                                                              ↕ ...
                                                                                                           Risk Judge → END
```

### Pattern 1: Conditional Fan-Out from START
**What:** `add_conditional_edges` on START returns a list of node names — either 1 or 2 destinations depending on `enable_options`.
**When to use:** When options branch must be entirely skipped (not just short-circuited) to preserve equity-only baseline.

```python
# Source: verified live with LangGraph 1.1.3
def route_from_start(state: AgentState):
    config = get_config()
    first_equity = selected_analysts[0].capitalize()
    if config.get("enable_options", False):
        return [f"{first_equity} Analyst", "Options: Volatility Analyst"]
    return [f"{first_equity} Analyst"]

workflow.add_conditional_edges(
    START,
    route_from_start,
    [f"{first_equity} Analyst", "Options: Volatility Analyst"],
)
```

**Key:** The third argument to `add_conditional_edges` is the exhaustive list of possible destination nodes. When the router returns a list, LangGraph fans out to all listed nodes simultaneously.

### Pattern 2: Implicit Fan-In via Multiple Incoming Edges
**What:** Point both branch endpoints at the same node. LangGraph 1.1.3 waits for all active incoming edges before executing the target node.
**When to use:** Merging parallel branches without a dedicated merge node.

```python
# Source: verified live with LangGraph 1.1.3
# Equity path last clear node → Bull Researcher
workflow.add_edge(f"Msg Clear {last_equity}", "Bull Researcher")
# Options path last agent → Bull Researcher
workflow.add_edge("Options: Greeks Monitor", "Bull Researcher")
```

LangGraph tracks which branches are active. When `enable_options=False`, only the equity edge fires and Bull Researcher starts immediately. When both branches are active, Bull Researcher waits for both.

### Pattern 3: Sequential Options Chain (no tool/clear cycles)
**What:** Options agents are single-pass (Python computes + LLM formats). They do NOT use `bind_tools`, `MessagesPlaceholder`, or the messages thread. No conditional tool-call check needed.
**When to use:** All 7 options agents.

```python
# Source: codebase inspection (volatility_analyst.py)
# Each options agent returns ONE state key, not "messages"
# Node chaining is just add_edge — no conditional needed
workflow.add_node("Options: Volatility Analyst", create_volatility_analyst(self.quick_thinking_llm))
workflow.add_node("Options: Flow Analyst",        create_options_flow_analyst(self.quick_thinking_llm))
# ...
workflow.add_edge("Options: Volatility Analyst", "Options: Flow Analyst")
workflow.add_edge("Options: Flow Analyst",        "Options: Strategy Selector")
# ...
workflow.add_edge("Options: Greeks Monitor",      "Bull Researcher")
```

### Pattern 4: Graceful Degradation with try/except in Node Wrapper
**What:** Wrap each options agent factory call in try/except so a data layer failure returns the empty-string fallback rather than crashing the graph.
**When to use:** Per the locked decision on graceful degradation.

```python
def _safe_options_node(factory_fn, state_key, llm):
    """Wrap an options agent factory to catch errors and return empty string."""
    inner = factory_fn(llm)
    def node(state: dict) -> dict:
        try:
            return inner(state)
        except Exception:
            return {state_key: ""}
    return node
```

### Anti-Patterns to Avoid
- **Direct `add_edge(START, ...)` for conditional routing:** Using two unconditional START edges is not the same as conditional routing — both nodes would always run. Use `add_conditional_edges` from START instead.
- **Adding conditional logic after options nodes:** Options nodes are single-pass with no tool calls; do NOT add `should_continue_options_*` style conditionals that check `messages[-1].tool_calls`.
- **Checking `enable_options` inside individual agent nodes:** `enable_options` determines graph routing at compile-time via the conditional edge — individual nodes should never need to inspect this config key.
- **Forgetting to add options nodes to the `add_conditional_edges` possible-destinations list:** LangGraph requires all reachable node names to be declared in the third argument.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Branch synchronization | Custom waiting/locking logic | LangGraph fan-in via multiple incoming edges | LangGraph 1.1.3 handles this natively; verified by experiment |
| Conditional branch skipping | `if enable_options: return {}` inside each node | `add_conditional_edges(START, ...)` returning list | Proper graph routing avoids visiting skipped nodes at all |
| State merging after parallel execution | Manual dict merge node | LangGraph TypedDict reducer | LangGraph merges returned dict into state automatically |

**Key insight:** LangGraph 1.1.3 handles all parallel execution primitives natively. The graph author only needs to declare edges; the runtime handles scheduling, fan-out, fan-in, and state merging.

---

## Common Pitfalls

### Pitfall 1: State Field Not Initialized → KeyError at Fan-In
**What goes wrong:** `Bull Researcher` accesses `state["volatility_report"]` but the key was never set because the initial state dict in `Propagator.create_initial_state` does not include it.
**Why it happens:** `AgentState` defines optional fields but `create_initial_state` only explicitly sets equity fields. LangGraph may raise a KeyError when a node reads an unset key from a TypedDict state.
**How to avoid:** Add all six options fields to `Propagator.create_initial_state` with `""` defaults, mirroring the existing pattern for `market_report`, `technical_report`, etc.
**Warning signs:** `KeyError: 'volatility_report'` in the Bull Researcher node during integration test.

### Pitfall 2: Fan-In Node Runs Before Both Branches Complete
**What goes wrong:** Bull Researcher starts with only equity output; options state fields are still empty.
**Why it happens:** If the equity clear node and the options chain terminate node both point at Bull Researcher, LangGraph 1.1.3 waits for all active incoming branches by default — but only if both branches are active. When `enable_options=False`, only one branch fires.
**How to avoid:** This is handled automatically by LangGraph. The concern is if `add_conditional_edges` destination list is wrong or if an options node incorrectly writes to `messages` (triggering tool detection). Verify each options agent returns ONLY its report key dict, not `messages`.
**Warning signs:** Options fields are empty even with `enable_options=True`; check node return values do not include `messages`.

### Pitfall 3: `setup_graph()` Called Before `set_config()`
**What goes wrong:** The route function reads `get_config()` at call time; if `TradingAgentsGraph.__init__` calls `set_config(self.config)` before `setup_graph()`, the config is correct. If order is reversed, `get_config()` returns the default config (with `enable_options=False`).
**Why it happens:** `setup_graph()` now reads config via `get_config()` inside the route closure.
**How to avoid:** The route closure is a function that is called at graph *execution* time, not at compile time. `get_config()` is evaluated each time a graph invocation starts, so as long as `set_config` is called before `graph.invoke()`, the order of `setup_graph()` vs `set_config()` does not matter. Verified by inspecting `trading_graph.py` — `set_config` is called in `__init__` before `setup_graph`.

### Pitfall 4: `setup_graph()` Signature Change Breaks Callers
**What goes wrong:** `TradingAgentsGraph` calls `self.graph_setup.setup_graph(selected_analysts)` — adding a required `enable_options` param breaks this call site.
**Why it happens:** API change in `setup_graph`.
**How to avoid:** Add `enable_options=False` as a keyword argument with default. `TradingAgentsGraph.__init__` passes `enable_options=self.config.get("enable_options", False)` to the call. Alternatively (cleaner): the route closure reads `get_config()` directly — no parameter needed.

### Pitfall 5: `_log_state` Missing Options Fields → KeyError on Logging
**What goes wrong:** `TradingAgentsGraph._log_state` tries to read `final_state["volatility_report"]` etc. but the field is not in the hard-coded state dict extraction.
**Why it happens:** `_log_state` currently enumerates equity fields explicitly. Options fields need to be added.
**How to avoid:** Add all six options keys to `_log_state` when logging the state. Include a try/get pattern since options fields may be absent in equity-only mode.

---

## Code Examples

### Node Registration for Options Chain
```python
# Source: codebase pattern from setup.py + verified LangGraph docs
from tradingagents.agents import (
    create_volatility_analyst,
    create_options_flow_analyst,
    create_options_strategy_selector,
    create_strike_expiry_selector,
    create_options_pricing_agent,
    create_options_legs_builder,
    create_greeks_monitor,
)

OPTIONS_NODES = [
    ("Options: Volatility Analyst",    create_volatility_analyst),
    ("Options: Flow Analyst",          create_options_flow_analyst),
    ("Options: Strategy Selector",     create_options_strategy_selector),
    ("Options: Strike/Expiry",         create_strike_expiry_selector),
    ("Options: Pricing Agent",         create_options_pricing_agent),
    ("Options: Legs Builder",          create_options_legs_builder),
    ("Options: Greeks Monitor",        create_greeks_monitor),
]

for node_name, factory_fn in OPTIONS_NODES:
    workflow.add_node(node_name, factory_fn(self.quick_thinking_llm))

# Sequential chain
for i in range(len(OPTIONS_NODES) - 1):
    workflow.add_edge(OPTIONS_NODES[i][0], OPTIONS_NODES[i+1][0])
```

### Conditional Router for START
```python
# Source: verified live with LangGraph 1.1.3
def route_from_start(state: AgentState):
    from tradingagents.dataflows.config import get_config
    cfg = get_config()
    first_equity = f"{selected_analysts[0].capitalize()} Analyst"
    if cfg.get("enable_options", False):
        return [first_equity, "Options: Volatility Analyst"]
    return [first_equity]

# selected_analysts captured in closure
all_possible_starts = [f"{selected_analysts[0].capitalize()} Analyst", "Options: Volatility Analyst"]
workflow.add_conditional_edges(START, route_from_start, all_possible_starts)
```

### Propagator Initial State Update
```python
# Source: propagation.py — extend with options fields
return {
    # ... existing fields ...
    "market_report": "",
    "technical_report": "",
    "fundamentals_report": "",
    "sentiment_report": "",
    "news_report": "",
    # Options pipeline fields — empty string default, populated only when enable_options=True
    "volatility_report": "",
    "options_flow_report": "",
    "options_strategy": "",
    "options_legs": "",
    "options_pricing_report": "",
    "greeks_report": "",
}
```

### Integration Smoke Test Pattern
```python
# Source: established pattern from test_volatility_analyst.py
from unittest.mock import patch, MagicMock

def _make_mock_llm(content="mock report"):
    mock_resp = MagicMock()
    mock_resp.content = content
    mock_llm = MagicMock()
    mock_llm.return_value = mock_resp
    mock_llm.invoke = MagicMock(return_value=mock_resp)
    return mock_llm

def test_full_graph_options_enabled():
    with patch("tradingagents.dataflows.config.get_config") as mock_cfg, \
         patch("tradingagents.dataflows.interface.route_to_vendor") as mock_vendor:
        mock_cfg.return_value = {**DEFAULT_CONFIG, "enable_options": True}
        mock_vendor.return_value = ""   # options agents handle empty data gracefully
        # ... build TradingAgentsGraph with mocked LLMs ...
        # ... assert all 6 options fields non-None in final_state ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangGraph 0.x: explicit `Send` for fan-out | LangGraph 1.x: `add_conditional_edges` returning list for fan-out | LangGraph 1.0 | Simpler API, same behavior |
| Separate merge nodes for fan-in | Implicit fan-in via multiple edges to same node | LangGraph 1.x | No extra node code needed |

**Deprecated/outdated:**
- `Send` object from `langgraph.constants`: Still supported but not needed for simple parallel branches. `add_conditional_edges` returning a list is the standard approach for static fan-out in LangGraph 1.x.

---

## Open Questions

1. **Should `_log_state` in `trading_graph.py` log options fields?**
   - What we know: `_log_state` hard-codes equity field names. Adding options fields improves observability.
   - What's unclear: Whether the planner should include this as an explicit task or treat it as part of the setup.py task.
   - Recommendation: Include as a sub-task within the `trading_graph.py` extension task. Use `.get("volatility_report", "")` pattern so equity-only runs don't log empty keys.

2. **Error handling granularity: per-node try/except vs branch-level try/except?**
   - What we know: CONTEXT.md requires graceful degradation if the options branch fails.
   - What's unclear: Whether to wrap each of the 7 nodes individually or wrap the entire chain with a single error handler.
   - Recommendation: Wrap each node individually using a `_safe_options_node` helper. This allows partial results (e.g., volatility report succeeds, flow analyst fails) to be preserved, and makes error attribution easier.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 |
| Config file | none (pytest.ini / pyproject.toml not detected) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GRAPH-01 | Options nodes present in compiled graph when enable_options=True | integration | `pytest tests/graph/test_graph_integration.py -x` | Wave 0 |
| GRAPH-01 | Options nodes absent / not visited when enable_options=False | integration | `pytest tests/graph/test_graph_integration.py -x` | Wave 0 |
| GRAPH-02 | AgentState has all 6 options fields | unit | `pytest tests/agents/test_agent_states.py -x` | Exists (all pass) |
| GRAPH-03 | Options state fields populated before Bull Researcher executes | integration | `pytest tests/graph/test_graph_integration.py -x` | Wave 0 |
| GRAPH-04 | equity-only run produces identical output to pre-extension baseline | integration | `pytest tests/graph/test_graph_integration.py::test_equity_only_mode -x` | Wave 0 |
| GRAPH-05 | DEFAULT_CONFIG has enable_options, options_vendor, options_delta_target, options_dte_window, options_min_oi | unit | `pytest tests/graph/test_default_config.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/agents/test_agent_states.py tests/graph/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/graph/__init__.py` — init for graph test module
- [ ] `tests/graph/test_graph_integration.py` — covers GRAPH-01, GRAPH-03, GRAPH-04
- [ ] `tests/graph/test_default_config.py` — covers GRAPH-05

*(GRAPH-02 is already covered by the existing `tests/agents/test_agent_states.py` which passes.)*

---

## Sources

### Primary (HIGH confidence)
- LangGraph 1.1.3 (installed, verified by live execution) — fan-out via `add_conditional_edges` returning list, implicit fan-in via multiple edges to same node, conditional routing from START
- `tradingagents/graph/setup.py` — existing graph wiring pattern
- `tradingagents/graph/conditional_logic.py` — existing conditional logic pattern
- `tradingagents/agents/utils/agent_states.py` — all 6 options fields already present
- `tradingagents/default_config.py` — all 5 options config keys already present
- `tradingagents/graph/propagation.py` — initial state creation (options fields missing — confirmed gap)
- `tradingagents/agents/options/volatility_analyst.py` — confirmed single-pass, no tool calls, returns `{"volatility_report": content}`
- `tradingagents/graph/trading_graph.py` — `_log_state` confirmed does not include options fields

### Secondary (MEDIUM confidence)
- LangGraph official behavior inferred from `pip show langgraph` version 1.1.3 + live execution experiment
- Test infrastructure from `tests/agents/test_agent_states.py` — confirmed GRAPH-02 tests already pass

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — LangGraph 1.1.3 verified installed and tested live
- Architecture: HIGH — all patterns verified by live LangGraph execution and codebase inspection
- Pitfalls: HIGH — derived from direct inspection of `propagation.py`, `_log_state`, and agent return value contracts

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable LangGraph API — only changes if LangGraph major version bumps)
