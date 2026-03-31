# Phase 3: Strategy & Contract Selection Agents - Research

**Researched:** 2026-03-31
**Domain:** LangChain agent factories, options strategy selection logic, pandas-based options chain filtering
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Strategy Selector Architecture**
- Pure LLM agent: reads `volatility_report`, `options_flow_report`, and `investment_plan` text fields from state directly; no structured parsing step
- Inputs: `state["volatility_report"]` + `state["options_flow_report"]` + `state["investment_plan"]`
- Output `options_strategy`: plain string with embedded strategy name and rationale, e.g. `"Bull Call Spread — IV is moderate, directional bias bullish, defined risk preferred"`
- System prompt embeds the full 10-strategy list as a numbered constraint: LLM MUST pick one; prevents hallucinated strategy names
- Defined strategy list: long call, long put, bull call spread, bear put spread, iron condor, covered call, cash-secured put, long straddle, long strangle, calendar spread

**Strike/Expiry Selector Logic**
- Python-first: filter options chain by delta/DTE/OI thresholds in Python; LLM not used for selection, only for formatting if needed
- Delta tolerance band: ±0.05 around `options_delta_target` (e.g., target=0.30 → accept 0.25–0.35)
- Output `options_legs`: structured string, one leg per line, e.g. `"LEG 1: BUY CALL AAPL 2026-01-17 $150 δ=0.32 OI=1240 [PASS]"`
- Liquidity fail: embed `[LIQUIDITY FAIL]` marker in `options_legs` string when no contracts satisfy constraints — "No contracts satisfy delta=0.30 ±0.05 within DTE [21,45] with OI>100. [LIQUIDITY FAIL]"
- No separate `options_liquidity_fail` boolean field in AgentState

**AgentState Extension**
- Add `options_strategy: Annotated[str, "..."]` and `options_legs: Annotated[str, "..."]` to existing `tradingagents/agents/utils/agent_states.py`
- Same file as all prior phases (no separate options state extension)

**Testing**
- Strategy selector tests: pass fixture strings directly in state dict (`{"volatility_report": "IV Rank: 72...", "investment_plan": "Bullish — price target $160", ...}`)
- Strike/expiry tests: use controlled DataFrame fixture (deterministic options chain with known strikes/deltas/OI)
- Strategy selector tests: assert output contains one of the 10 defined strategy names
- All mocks: mock `route_to_vendor` for data layer; mock LLM via MagicMock callable

### Claude's Discretion
- Exact system prompt wording for strategy selector
- How to read strategy name from `options_strategy` string (Phase 4 consumer responsibility)
- Error handling when upstream reports are empty strings
- Which expiry to select when multiple satisfy DTE window (closest to center of window)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-03 | Options strategy selector agent (`options_strategy_selector.py`) — maps directional bias + IV view + time horizon + risk preference to single strategy from defined list; includes one-sentence rationale | Factory pattern from `create_volatility_analyst`; LLM constraint via numbered strategy list in system prompt; reads three state text fields |
| AGENT-04 | Strike and expiry selector agent (`strike_expiry_selector.py`) — selects specific expiry date and strike(s) per leg given strategy type, delta targets, DTE window, OI threshold; outputs liquidity pass/fail per leg | Python-first DataFrame filtering via `route_to_vendor("get_options_chain")`; deterministic selection rules; `[PASS]`/`[LIQUIDITY FAIL]` markers in string output |
</phase_requirements>

## Summary

Phase 3 builds two agent factory functions that extend the options pipeline started in Phases 1 and 2. Both follow the established single-pass factory pattern: `def create_X(llm): def node(state): ...; return {"field": result}; return node`. The codebase already contains two fully-working reference implementations (`create_volatility_analyst` and `create_options_flow_analyst`) that define every convention this phase must follow — prompt format, LLM invocation, state field writing, test mock patterns.

The strategy selector (`AGENT-03`) is a pure LLM agent: it receives three prose strings from state, assembles them into a prompt, and must output a string that contains exactly one name from the 10-strategy list. The system prompt acts as the constraint layer by embedding the full numbered list with an explicit requirement to pick one. The strike/expiry selector (`AGENT-04`) is a Python-first agent: it calls `route_to_vendor` to fetch the options chain and expirations, filters by DTE window and delta band in pandas, picks expiry and strikes deterministically, then formats each leg as a structured string. LLM is not used for contract selection logic.

Both agents write to new AgentState fields (`options_strategy`, `options_legs`) that must be added to `agent_states.py`. Both follow the established testing convention of mocking `route_to_vendor` with a side-effect function and mocking the LLM via `MagicMock` with `return_value` set (not `__ror__`).

**Primary recommendation:** Copy the `create_volatility_analyst` factory structure exactly for the strategy selector; copy the `create_options_flow_analyst` Python-first compute pattern for the strike/expiry selector. Do not deviate from established patterns.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain_core` | already installed | `ChatPromptTemplate.from_messages`, prompt/LLM chain | Same version used by all existing agents |
| `pandas` | already installed | DataFrame filtering, delta/DTE/OI arithmetic | Used by `_parse_tabular_string` in existing agents |
| `unittest.mock` | stdlib | `patch`, `MagicMock` for test isolation | Established project test convention |
| `pytest` | already installed | Test runner, fixture system | Existing test suite uses pytest throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `datetime` | stdlib | DTE calculation (`date.fromisoformat(expiry) - date.today()`) | Strike/expiry selector: compute days-to-expiry from string expiry date |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python-first delta filtering | LLM selecting strikes | LLM selection is non-deterministic; Python guarantees reproducible, testable contract selection |
| Plain string output for `options_strategy` | Structured dict in AgentState | Structured dict would require TypedDict extension; plain string is consistent with all other report fields |

**No additional installations required.** All dependencies are already present in the project.

## Architecture Patterns

### Recommended Project Structure
```
tradingagents/agents/options/
├── volatility_analyst.py         # Phase 2 reference — single-pass LLM factory
├── options_flow_analyst.py       # Phase 2 reference — Python-first compute factory
├── options_strategy_selector.py  # Phase 3 NEW — pure LLM factory (AGENT-03)
└── strike_expiry_selector.py     # Phase 3 NEW — Python-first factory (AGENT-04)

tests/agents/
├── test_agent_states.py          # Phase 3 additions: options_strategy, options_legs
├── test_options_strategy_selector.py  # Phase 3 NEW
└── test_strike_expiry_selector.py     # Phase 3 NEW
```

### Pattern 1: Pure LLM Factory (options_strategy_selector)
**What:** Factory wraps an LLM call; all inputs come from state as prose strings; constraint list embedded in system prompt.
**When to use:** When the selection decision is conceptual/reasoning-based (e.g., "which strategy fits this market view?") and determinism is enforced by output constraint, not by code.
**Example:**
```python
# Source: tradingagents/agents/options/volatility_analyst.py (established pattern)

SYSTEM_PROMPT = (
    "You are an expert options strategist. Given the market analysis below, "
    "select EXACTLY ONE strategy from this numbered list:\n\n"
    "1. long call\n2. long put\n3. bull call spread\n4. bear put spread\n"
    "5. iron condor\n6. covered call\n7. cash-secured put\n"
    "8. long straddle\n9. long strangle\n10. calendar spread\n\n"
    "Output format: <strategy name> — <one-sentence rationale>\n"
    "You MUST use the exact strategy name from the list above. "
    "Do not invent names. Output the single line only."
)

def create_options_strategy_selector(llm):
    def options_strategy_selector_node(state: dict) -> dict:
        volatility_report = state.get("volatility_report", "")
        options_flow_report = state.get("options_flow_report", "")
        investment_plan = state.get("investment_plan", "")

        data_content = (
            f"Volatility Analysis:\n{volatility_report}\n\n"
            f"Options Flow Analysis:\n{options_flow_report}\n\n"
            f"Investment Plan:\n{investment_plan}\n\n"
            "Select the appropriate options strategy."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", data_content),
        ])

        result = (prompt | llm).invoke({})
        return {"options_strategy": result.content}

    return options_strategy_selector_node
```

### Pattern 2: Python-First Filtering Factory (strike_expiry_selector)
**What:** Factory fetches options chain via `route_to_vendor`, filters with pandas (DTE window, delta band, OI floor), picks best candidates deterministically, formats as structured leg string.
**When to use:** When contract selection must be deterministic, testable with controlled fixtures, and not subject to LLM non-determinism.
**Example:**
```python
# Source: adapted from options_flow_analyst.py Python-first pattern

def create_strike_expiry_selector(llm):
    def strike_expiry_selector_node(state: dict) -> dict:
        ticker = state["company_of_interest"]
        config = get_config()
        delta_target = config.get("options_delta_target", 0.30)
        dte_min = config.get("options_dte_min", 21)
        dte_max = config.get("options_dte_max", 45)
        min_oi = config.get("options_min_oi", 100)

        # 1. Get expirations, filter by DTE window
        expirations = route_to_vendor("get_options_expirations", ticker)
        today = date.today()
        valid_expirations = []
        for exp in expirations:
            dte = (date.fromisoformat(exp) - today).days
            if dte_min <= dte <= dte_max:
                valid_expirations.append((exp, dte))

        if not valid_expirations:
            return {"options_legs": f"No expirations within DTE [{dte_min},{dte_max}]. [LIQUIDITY FAIL]"}

        # 2. Pick expiry closest to center of DTE window
        dte_center = (dte_min + dte_max) / 2
        selected_expiry, _ = min(valid_expirations, key=lambda x: abs(x[1] - dte_center))

        # 3. Fetch chain and filter by delta band and OI
        chain_str = route_to_vendor("get_options_chain", ticker, selected_expiry)
        chain_df = _parse_tabular_string(chain_str)

        if chain_df is None or chain_df.empty:
            return {"options_legs": f"No chain data for {selected_expiry}. [LIQUIDITY FAIL]"}

        delta_lo = delta_target - 0.05
        delta_hi = delta_target + 0.05

        calls = chain_df[
            (chain_df["option_type"] == "call") &
            (chain_df["delta"].between(delta_lo, delta_hi)) &
            (chain_df["open_interest"] >= min_oi)
        ].copy()

        if calls.empty:
            return {
                "options_legs": (
                    f"No contracts satisfy delta={delta_target} ±0.05 within "
                    f"DTE [{dte_min},{dte_max}] with OI>{min_oi}. [LIQUIDITY FAIL]"
                )
            }

        # 4. Pick closest delta match
        calls["delta_diff"] = (calls["delta"] - delta_target).abs()
        best = calls.nsmallest(1, "delta_diff").iloc[0]

        leg_line = (
            f"LEG 1: BUY CALL {ticker} {selected_expiry} "
            f"${best['strike']:.0f} δ={best['delta']:.2f} "
            f"OI={int(best['open_interest'])} [PASS]"
        )
        return {"options_legs": leg_line}

    return strike_expiry_selector_node
```

### Pattern 3: AgentState Extension
**What:** Add two `Annotated[str, "description"]` fields to the existing `AgentState` class.
**When to use:** Every new options pipeline output field goes here.
**Example:**
```python
# Source: tradingagents/agents/utils/agent_states.py (existing pattern)
class AgentState(MessagesState):
    # ... existing fields ...
    volatility_report: Annotated[str, "Report from the Volatility Analyst"]
    options_flow_report: Annotated[str, "Report from the Options Flow Analyst"]
    # Phase 3 additions:
    options_strategy: Annotated[str, "Options strategy selected by the Strategy Selector"]
    options_legs: Annotated[str, "Specific contracts selected by the Strike/Expiry Selector"]
```

### Pattern 4: Mock LLM for Testing
**What:** `MagicMock` with `return_value` set so that `(prompt | llm).invoke({})` returns a response with `.content`.
**When to use:** Every LLM-using agent test in this project.
**Example:**
```python
# Source: tests/agents/test_volatility_analyst.py (established pattern)
def _make_mock_llm(content="mock strategy output"):
    mock_response = MagicMock()
    mock_response.content = content
    mock_llm = MagicMock()
    mock_llm.return_value = mock_response      # LangChain calls llm(messages)
    mock_llm.invoke = MagicMock(return_value=mock_response)  # fallback
    return mock_llm, mock_response
```

### Anti-Patterns to Avoid
- **LLM for strike selection:** Never ask LLM to pick a specific strike or delta — outputs are non-deterministic and cannot be unit-tested with fixed assertions.
- **Structured dict in AgentState for options_strategy:** All options pipeline fields use plain strings to match the existing `volatility_report` / `options_flow_report` convention.
- **Using `__ror__` mock:** The project established (Phase 2, plan 02-01) that mocking LLM via `return_value` is correct; `__ror__` causes LangChain RunnableSequence failures.
- **Curly-brace placeholders in system prompt:** Phase 2 established that angle-bracket `<placeholder>` style avoids LangChain `ChatPromptTemplate` variable conflicts.
- **Importing from separate options state module:** All state fields live in `agent_states.py` — no separate file.
- **Writing to `messages` in return dict:** Options agent nodes must NOT write to `state["messages"]`; return dict has exactly one key.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Strategy name constraint | Custom LLM output parser with regex | System prompt numbered list + assertion in tests | The numbered list in the system prompt is the constraint; regex extraction is Phase 4 consumer's responsibility |
| DTE calculation | Custom calendar logic | `datetime.date.fromisoformat(exp) - datetime.date.today()` | Standard library; no edge cases beyond what `.days` provides |
| Delta filtering | Custom options math | pandas `.between(lo, hi)` on `delta` column | Chain data already has delta from Tradier/yfinance data layer |
| Closest expiry selection | Sort loop | `min(valid_expirations, key=lambda x: abs(x[1] - dte_center))` | One-liner idiom, no loop needed |
| Closest delta selection | Manual iteration | `df.nsmallest(1, "delta_diff")` after computing `abs(delta - target)` | Pandas built-in, tested idiom used for top-N in options_flow_analyst |
| Multi-leg spread assembly | Separate per-leg agent | Single `strike_expiry_selector` node outputs all legs as lines | Phase scope is single-node output; multi-leg is just multiple lines in `options_legs` string |

**Key insight:** The entire selection pipeline is deterministic Python once the LLM constraint is encoded in the system prompt. Avoid introducing any additional decision points that require LLM calls in the strike/expiry selector.

## Common Pitfalls

### Pitfall 1: LLM Hallcinates Strategy Name
**What goes wrong:** LLM outputs `"Debit Bull Spread"` or `"Vertical Spread"` instead of `"bull call spread"` — Phase 4 consumer can't parse it.
**Why it happens:** Without explicit constraint, LLMs use varied terminology for the same strategy.
**How to avoid:** System prompt must embed the numbered list with `"You MUST use the exact strategy name from the list above"` — see Pattern 1 above.
**Warning signs:** Test that asserts output `in STRATEGY_LIST` fails intermittently.

### Pitfall 2: Empty Upstream Reports Causing LLM Confusion
**What goes wrong:** `state["investment_plan"]` is an empty string; LLM receives empty inputs and may hallucinate or output generic text that doesn't contain a valid strategy name.
**Why it happens:** AgentState fields default to empty string before upstream agents run.
**How to avoid:** Strategy selector should handle empty inputs with a guard: if all three input fields are empty, return a fallback `options_strategy` string (e.g., `"iron condor — no upstream analysis available [FALLBACK]"`) without calling LLM, or proceed and let LLM choose from the constrained list.
**Warning signs:** Test with empty state dict strings fails the strategy-name assertion.

### Pitfall 3: DTE Off-by-One (today vs trade_date)
**What goes wrong:** DTE computed using `datetime.date.today()` (server time) rather than `state["trade_date"]` (the analysis date) — produces wrong expiry selection during backtesting.
**Why it happens:** `date.today()` is a global — it uses the real current date, not the analysis date.
**How to avoid:** Parse `state["trade_date"]` as `date.fromisoformat(state["trade_date"])` and compute DTE relative to that date.
**Warning signs:** Tests pass today but would fail if run with historical trade_dates.

### Pitfall 4: Delta Sign Convention for Puts
**What goes wrong:** For a bear put spread, the delta target is intended to be 0.30 magnitude, but puts have negative delta (e.g., -0.30). Filtering `chain_df["delta"].between(0.25, 0.35)` misses all put contracts.
**Why it happens:** Call delta is positive (0 to 1), put delta is negative (-1 to 0).
**How to avoid:** For put legs, apply `abs(chain_df["delta"]).between(delta_lo, delta_hi)` or negate the target. The strategy type (call vs put) determines the sign convention.
**Warning signs:** Strike/expiry selector returns `[LIQUIDITY FAIL]` for all put-based strategies in tests.

### Pitfall 5: No Contracts Pass OI Filter on Test Fixture
**What goes wrong:** Deterministic test fixture has all OI values below `options_min_oi` default (100), so every test returns `[LIQUIDITY FAIL]`.
**Why it happens:** Test fixture designed for other tests may have small OI values.
**How to avoid:** Strike/expiry selector test fixtures must explicitly include contracts with OI > 100 and contracts with OI < 100 to test both pass and fail paths.
**Warning signs:** All `[PASS]` assertions fail; all `[LIQUIDITY FAIL]` assertions pass.

### Pitfall 6: `_parse_tabular_string` Not Duplicated Locally
**What goes wrong:** `strike_expiry_selector.py` imports `_parse_tabular_string` from `options_flow_analyst` — creates a module coupling that breaks if `options_flow_analyst` is refactored.
**Why it happens:** It's tempting to reuse the function rather than copy it.
**How to avoid:** Phase 2 established (plan 02-02 decision): "Duplicate `_parse_tabular_string` locally in each module to keep modules independent." Copy it into `strike_expiry_selector.py`.
**Warning signs:** `ImportError` if import path changes; circular import risk.

### Pitfall 7: `__init__.py` Export Not Updated
**What goes wrong:** New factories are importable by path but not from `tradingagents.agents.options` or `tradingagents.agents` package.
**Why it happens:** Both `__init__.py` files require manual update.
**How to avoid:** Add exports to both `tradingagents/agents/options/__init__.py` and `tradingagents/agents/__init__.py`. Existing tests for `test_agent_states.py` check importability from the package.
**Warning signs:** `from tradingagents.agents.options import create_options_strategy_selector` raises `ImportError`.

## Code Examples

Verified patterns from project source code:

### Factory Shell
```python
# Source: tradingagents/agents/options/options_flow_analyst.py
def create_options_flow_analyst(llm):
    def options_flow_analyst_node(state: dict) -> dict:
        ticker: str = state["company_of_interest"]
        trade_date: str = state["trade_date"]
        # ... compute ...
        return {"options_flow_report": result.content}
    return options_flow_analyst_node
```

### LLM Chain Invocation
```python
# Source: tradingagents/agents/options/volatility_analyst.py
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", data_content),
])
result = (prompt | llm).invoke({})
return {"volatility_report": result.content}
```

### Angle-Bracket System Prompt Placeholders
```python
# Source: tradingagents/agents/options/volatility_analyst.py
# Use <placeholder> not {placeholder} to avoid LangChain template conflicts
SYSTEM_PROMPT = (
    "...Always embed the labeled metrics in this exact format:\n\n"
    "IV Rank: <iv_rank> (<iv_rank_label>). ..."
)
```

### route_to_vendor Call Pattern
```python
# Source: tradingagents/agents/options/options_flow_analyst.py
expirations: list = route_to_vendor("get_options_expirations", ticker)
chain_str: str = route_to_vendor("get_options_chain", ticker, expirations[0])
```

### Mock route_to_vendor in Tests
```python
# Source: tests/agents/test_options_flow_analyst.py
def _make_route_side_effect(expirations=None, chain_str=VALID_CHAIN_STR):
    if expirations is None:
        expirations = ["2026-04-17", "2026-06-20"]
    def _side_effect(method, *args, **kwargs):
        if method == "get_options_expirations":
            return expirations
        elif method == "get_options_chain":
            return chain_str
        return ""
    return _side_effect

with patch("tradingagents.agents.options.options_flow_analyst.route_to_vendor",
           side_effect=_make_route_side_effect()):
    node = create_options_flow_analyst(mock_llm)
    result = node(state)
```

### AgentState Annotated Field
```python
# Source: tradingagents/agents/utils/agent_states.py
class AgentState(MessagesState):
    volatility_report: Annotated[str, "Report from the Volatility Analyst"]
    options_flow_report: Annotated[str, "Report from the Options Flow Analyst"]
    # Pattern for Phase 3 additions:
    options_strategy: Annotated[str, "Options strategy selected by the Strategy Selector"]
    options_legs: Annotated[str, "Specific contracts selected by the Strike/Expiry Selector"]
```

### Controlled DataFrame Fixture for Strike/Expiry Tests
```python
# Derived from: tests/agents/test_options_flow_analyst.py fixture pattern

CONTROLLED_CHAIN_STR = (
    "strike  option_type  volume  open_interest  iv    delta\n"
    "145.0   call         500     200            0.28  0.22\n"   # delta=0.22, below target 0.30 band
    "150.0   call         600     300            0.26  0.30\n"   # delta=0.30, exact match, OI=300 PASS
    "155.0   call         400     50             0.24  0.38\n"   # delta=0.38, above band; OI=50 fail
    "145.0   put          300     250            0.32 -0.30\n"   # put delta=-0.30 for put-leg tests
    "140.0   put          200     150            0.35 -0.22\n"   # put delta=-0.22
)
```

### 10-Strategy List (canonical)
```python
# Source: CONTEXT.md decisions — locked list
STRATEGY_LIST = [
    "long call",
    "long put",
    "bull call spread",
    "bear put spread",
    "iron condor",
    "covered call",
    "cash-secured put",
    "long straddle",
    "long strangle",
    "calendar spread",
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM picks strikes | Python pandas filter + deterministic sort | Phase 2 decision (plan 02-02) | Strike/expiry tests are fully deterministic |
| `{placeholder}` in system prompts | `<placeholder>` angle brackets | Phase 2 decision (plan 02-01) | No LangChain template variable conflicts |
| Mock LLM via `__ror__` | Mock LLM via `return_value` | Phase 2 decision (plan 02-01) | RunnableSequence calls LLM as callable |

**Deprecated/outdated:**
- Structured dict output for agent fields: all options pipeline agents use plain `str` fields — consistent with `volatility_report`, `options_flow_report` precedent.

## Open Questions

1. **Multi-leg strategy leg count**
   - What we know: `options_legs` is a multi-line string, one leg per line. Spreads need 2 legs.
   - What's unclear: For `bull call spread`, should `strike_expiry_selector` fetch two strikes (buy lower, sell higher)? The CONTEXT.md says "select expiry and strike(s)" implying it handles multi-leg.
   - Recommendation: Implement single-leg for now (most strategies only need one leg direction); add a second leg for spreads by fetching a second delta target (e.g., sell leg at `delta_target - 0.15`). Both legs go into the same `options_legs` string on separate `LEG N:` lines. This is Claude's discretion territory per CONTEXT.md.

2. **Strategy type → call/put mapping**
   - What we know: `strike_expiry_selector` receives `options_strategy` from the previous node (via state), but the phase does not wire nodes into the graph yet (Phase 5).
   - What's unclear: In isolated testing, how does `strike_expiry_selector` know to fetch call vs put contracts without strategy context?
   - Recommendation: Read `state.get("options_strategy", "")` in the strike/expiry selector node; parse for keywords like "call", "put", "condor", "straddle" to determine leg types. If empty, default to call contracts matching `options_delta_target`.

3. **`options_delta_target` config key availability**
   - What we know: `DEFAULT_CONFIG` was extended in Phase 1 (plan 01-03) with options config keys including `options_delta_target`, `options_dte_window`, `options_min_oi`.
   - What's unclear: The exact key names for DTE min/max (could be `options_dte_window: [21, 45]` list or `options_dte_min`/`options_dte_max` separate keys).
   - Recommendation: Read the config in the strike/expiry selector via `get_config()` and handle both a list key (`options_dte_window`) and fallback to separate min/max keys.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no install needed) |
| Config file | `pytest.ini` or inferred from project root |
| Quick run command | `pytest tests/agents/test_options_strategy_selector.py tests/agents/test_strike_expiry_selector.py tests/agents/test_agent_states.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGENT-03 | Factory returns callable | unit | `pytest tests/agents/test_options_strategy_selector.py::test_factory_returns_callable -x` | Wave 0 |
| AGENT-03 | Node returns dict with `options_strategy` key containing str | unit | `pytest tests/agents/test_options_strategy_selector.py::test_node_returns_options_strategy -x` | Wave 0 |
| AGENT-03 | Output contains one of 10 strategy names | unit | `pytest tests/agents/test_options_strategy_selector.py::test_output_contains_valid_strategy_name -x` | Wave 0 |
| AGENT-03 | Return dict does NOT contain `messages` key | unit | `pytest tests/agents/test_options_strategy_selector.py::test_no_messages_written -x` | Wave 0 |
| AGENT-03 | Empty upstream reports do not crash | unit | `pytest tests/agents/test_options_strategy_selector.py::test_empty_reports_no_crash -x` | Wave 0 |
| AGENT-04 | Factory returns callable | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_factory_returns_callable -x` | Wave 0 |
| AGENT-04 | Node returns dict with `options_legs` key containing str | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_node_returns_options_legs -x` | Wave 0 |
| AGENT-04 | Selects contract within delta tolerance band | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_delta_band_filtering -x` | Wave 0 |
| AGENT-04 | Picks expiry closest to DTE window center | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_expiry_center_selection -x` | Wave 0 |
| AGENT-04 | `[LIQUIDITY FAIL]` when no contracts satisfy constraints | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_liquidity_fail_marker -x` | Wave 0 |
| AGENT-04 | `[PASS]` marker in output for valid contract | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_pass_marker_present -x` | Wave 0 |
| AGENT-04 | Return dict does NOT contain `messages` key | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_no_messages_written -x` | Wave 0 |
| AGENT-03 + AGENT-04 | AgentState has `options_strategy` and `options_legs` fields as `Annotated[str, ...]` | unit | `pytest tests/agents/test_agent_states.py -x` | Partial — file exists, needs 2 new tests |

### Sampling Rate
- **Per task commit:** `pytest tests/agents/ -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/agents/test_options_strategy_selector.py` — covers AGENT-03 (new file)
- [ ] `tests/agents/test_strike_expiry_selector.py` — covers AGENT-04 (new file)
- [ ] `tests/agents/test_agent_states.py` — needs 2 new tests for `options_strategy` and `options_legs` fields (file exists, append only)

*(No framework install needed — pytest already present)*

## Sources

### Primary (HIGH confidence)
- `tradingagents/agents/options/volatility_analyst.py` — factory pattern, LLM chain, prompt format, angle-bracket placeholders
- `tradingagents/agents/options/options_flow_analyst.py` — Python-first compute pattern, `_parse_tabular_string`, `route_to_vendor` usage
- `tradingagents/agents/utils/agent_states.py` — `Annotated[str, "..."]` field pattern, `MessagesState` inheritance
- `tradingagents/agents/options/__init__.py` — export pattern to replicate
- `tradingagents/agents/__init__.py` — top-level export pattern to replicate
- `tests/agents/test_volatility_analyst.py` — `_make_mock_llm` pattern, route side-effect helper, assert patterns
- `tests/agents/test_options_flow_analyst.py` — same mock patterns, DataFrame fixture construction
- `tests/agents/test_agent_states.py` — Annotated field test pattern to replicate for new fields
- `.planning/phases/03-strategy-contract-selection-agents/03-CONTEXT.md` — locked decisions, strategy list, output formats

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — confirms Phase 2 decisions on mock LLM pattern and angle-bracket prompts
- `.planning/REQUIREMENTS.md` — AGENT-03 and AGENT-04 requirement text

### Tertiary (LOW confidence)
- None — all findings verified from project source files.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns verified in existing codebase
- Architecture: HIGH — factory pattern, test mocking, AgentState extension all directly observed in working Phase 2 code
- Pitfalls: HIGH (delta sign convention, DTE trade_date) / MEDIUM (multi-leg spread complexity) — verified from code + documented Phase 2 decisions

**Research date:** 2026-03-31
**Valid until:** Stable — patterns are internal project conventions, not external library APIs. Valid as long as Phase 2 code is not refactored.
