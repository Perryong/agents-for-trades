# Phase 2: Volatility & Flow Agents - Research

**Researched:** 2026-03-31
**Domain:** LangGraph agent factories, options volatility metrics, options flow analysis
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Agent Architecture**
- Single-pass architecture: Python computes all numeric metrics, LLM receives computed values and writes the narrative paragraph (no ReAct tool-calling loop)
- Historical volatility (30-day HV) computed from yfinance stock price data using `pct_change().rolling(21).std() * sqrt(252)`
- Agents write to their named state field only — do NOT add to `AgentState.messages` thread
- Unit tests mock both the data layer (interface calls) and the LLM; no live API calls in tests

**Report Format & Content**
- Report is structured prose with labeled metrics, e.g. "IV Rank: 72 (high). IV Percentile: 68th. IV vs HV: Rich (+8pp). Skew: Put skew elevated. Term structure: Contango. Regime: Elevated IV, put-bid market — favor selling premium or buying protection."
- One paragraph per agent (matches ROADMAP "one-paragraph report" spec)
- Numeric metrics embedded in the prose text — no separate numeric AgentState fields alongside the narrative
- LLM writes the full paragraph given structured prompt containing computed metrics and a format template

**AgentState Extension**
- New fields `volatility_report` and `options_flow_report` added directly to existing `tradingagents/agents/utils/agent_states.py`
- New agent files placed in `tradingagents/agents/options/` subdirectory (create `__init__.py` too)
- IV rank and IV percentile computed using `get_historical_iv` output from Phase 1 (52-week window)
- Agents assume they are only invoked when options is enabled — no `enable_options` config check inside agent logic

### Claude's Discretion
- Exact LLM prompt wording for both agents
- Whether to use `quick_thinking_llm` or `deep_thinking_llm` (quick preferred — these are formatting tasks)
- Error handling for missing/empty data (e.g. no options chain data returned)
- Specific thresholds for "high" vs "low" IV rank labels in the narrative

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-01 | Volatility analyst agent (`volatility_analyst.py`) — outputs IV rank, IV percentile, IV vs 30-day HV (rich/cheap), skew shape, term structure (contango/backwardation), one-line regime summary | Metric computation patterns documented below; HV formula from CONTEXT.md; IV data from `get_historical_iv`; chain data from `get_options_chain` |
| AGENT-02 | Options flow analyst agent (`options_flow_analyst.py`) — outputs unusual volume vs OI, block/sweep detection, put/call ratio divergence vs recent average, net flow bias, one-line directional implication | Flow metrics documented below; all computed from parsed options chain string; no extra data source needed |
</phase_requirements>

## Summary

Phase 2 builds two specialist LangGraph agent factory functions. Each follows the single-pass pattern: Python code parses data from the Phase 1 data layer, computes numeric metrics, then feeds those computed values into a single LLM call that writes the final narrative paragraph. The agents do NOT use a ReAct tool-calling loop — they are pure data-in, narrative-out nodes.

The existing codebase provides clear prior art. All current analysts (`market_analyst`, `fundamentals_analyst`, `technical_analyst`) are factory functions returning closures with `ChatPromptTemplate` and `llm.bind_tools()`. The new agents diverge from this pattern by NOT binding tools — they compute everything in Python first, then pass a pre-filled prompt to the LLM without tool access. This is simpler than the existing agents, not more complex.

The data layer is fully available from Phase 1: `route_to_vendor("get_historical_iv", symbol)` returns a tabular string with `date` and `iv` columns, and `route_to_vendor("get_options_chain", symbol, expiration)` returns a tabular string with strike, option_type, volume, open_interest, iv, delta columns. All metric computation must parse these strings into DataFrames (via `io.StringIO` + `pd.read_csv(sep=r'\s+')`) or work directly with the string output.

**Primary recommendation:** Use `ChatPromptTemplate.from_messages([ ("system", system_msg), ("human", data_prompt) ])` pattern (no MessagesPlaceholder, no messages from state) to produce a simple single-shot LLM call. Return `{"volatility_report": result.content}` directly — no tool call check needed since no tools are bound.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-core | >=0.3.81 (project dep) | `ChatPromptTemplate`, `HumanMessage` | Already in pyproject.toml |
| langchain-openai | >=0.3.23 (project dep) | LLM interface (injected as `llm` param) | Already in pyproject.toml |
| pandas | >=2.3.0 (project dep) | Parse tabular string output from data layer | Already in pyproject.toml |
| yfinance | >=0.2.63 (project dep) | Download price history for 30-day HV | Already in pyproject.toml |
| math (stdlib) | — | `sqrt(252)` for annualization | No install needed |
| io (stdlib) | — | `io.StringIO` to parse tabular strings | No install needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | transitively available via pandas | Rolling std, annualization | `pct_change().rolling(21).std() * math.sqrt(252)` |
| unittest.mock | stdlib | Mock data layer and LLM in tests | All unit tests for these agents |

**Installation:** No new dependencies required — all libraries already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
tradingagents/agents/
├── options/
│   ├── __init__.py               # export create_volatility_analyst, create_options_flow_analyst
│   ├── volatility_analyst.py     # create_volatility_analyst factory
│   └── options_flow_analyst.py   # create_options_flow_analyst factory
└── utils/
    └── agent_states.py           # add volatility_report, options_flow_report fields

tradingagents/agents/__init__.py  # add new imports + __all__ entries

tests/
└── agents/
    ├── __init__.py
    ├── test_volatility_analyst.py
    └── test_options_flow_analyst.py
```

### Pattern 1: Single-Pass Agent Factory (NO tool binding)

The existing analysts use `llm.bind_tools(tools)` and check `len(result.tool_calls) == 0` before extracting the report. The new agents are simpler — no tools, no tool call check.

**What:** Factory function returns a closure. Closure reads state, computes numeric metrics in pure Python, constructs a data-rich prompt, invokes LLM once, returns the narrative.

**When to use:** All agents in this phase. Do NOT use ReAct tool-calling pattern.

**Example structure:**
```python
# Source: derived from market_analyst.py + CONTEXT.md decisions
from langchain_core.prompts import ChatPromptTemplate

def create_volatility_analyst(llm):
    def volatility_analyst_node(state):
        ticker = state["company_of_interest"]
        trade_date = state["trade_date"]

        # --- Step 1: Fetch data from Phase 1 data layer ---
        from tradingagents.dataflows.interface import route_to_vendor
        historical_iv_str = route_to_vendor("get_historical_iv", ticker)
        expirations = route_to_vendor("get_options_expirations", ticker)
        # fetch near and far chain for skew / term structure
        near_chain_str = route_to_vendor("get_options_chain", ticker, expirations[0]) if expirations else ""
        far_chain_str  = route_to_vendor("get_options_chain", ticker, expirations[-1]) if len(expirations) > 1 else ""

        # --- Step 2: Compute metrics in Python ---
        metrics = _compute_volatility_metrics(ticker, historical_iv_str, near_chain_str, far_chain_str)

        # --- Step 3: Single LLM call to write narrative ---
        prompt = ChatPromptTemplate.from_messages([
            ("system", VOLATILITY_SYSTEM_PROMPT),
            ("human", VOLATILITY_DATA_TEMPLATE.format(ticker=ticker, trade_date=trade_date, **metrics)),
        ])
        result = (prompt | llm).invoke({})

        return {"volatility_report": result.content}

    return volatility_analyst_node
```

### Pattern 2: AgentState Extension

**What:** Add new `Annotated[str, "description"]` fields to the existing `AgentState` TypedDict in `agent_states.py`.

**Exact pattern from existing code:**
```python
# Source: tradingagents/agents/utils/agent_states.py (lines 57-77)
class AgentState(MessagesState):
    # ... existing fields ...
    # Add at end of class:
    volatility_report: Annotated[str, "Report from the Volatility Analyst"]
    options_flow_report: Annotated[str, "Report from the Options Flow Analyst"]
```

### Pattern 3: Metric Computation from Tabular Strings

The data layer returns `DataFrame.to_string(index=False)` output. Parsing pattern:

```python
import io
import pandas as pd

def _parse_tabular_string(s: str) -> pd.DataFrame | None:
    """Parse a whitespace-aligned tabular string produced by DataFrame.to_string()."""
    if not s or "No " in s[:50]:  # catch "No options data available..." messages
        return None
    try:
        return pd.read_csv(io.StringIO(s), sep=r'\s+', engine='python')
    except Exception:
        return None
```

### Pattern 4: IV Rank and IV Percentile Computation

```python
# Source: CONTEXT.md ## Specific Ideas
def compute_iv_metrics(iv_series: pd.Series, current_iv: float) -> dict:
    """
    iv_series: float values from 52-week historical IV data
    current_iv: today's ATM IV (last row of historical IV table or from near-term chain)
    """
    iv_min = iv_series.min()
    iv_max = iv_series.max()

    # IV Rank: position of current IV in 52-week range
    iv_rank = ((current_iv - iv_min) / (iv_max - iv_min) * 100) if iv_max != iv_min else 50.0

    # IV Percentile: % of days in window where IV was below current IV
    iv_pct = (iv_series < current_iv).mean() * 100

    return {"iv_rank": round(iv_rank, 1), "iv_pct": round(iv_pct, 1)}
```

### Pattern 5: 30-day Historical Volatility via yfinance

```python
# Source: CONTEXT.md ## Implementation Decisions
import yfinance as yf
import math

def compute_hv30(ticker: str, trade_date: str) -> float | None:
    """Annualized 30-day HV using 21-trading-day rolling window."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="3mo")  # enough for 21-day window
        if hist.empty or "Close" not in hist.columns:
            return None
        hv = hist["Close"].pct_change().rolling(21).std().iloc[-1]
        return round(float(hv) * math.sqrt(252) * 100, 2)  # as percentage
    except Exception:
        return None
```

### Pattern 6: Skew Shape from Options Chain

```python
# Source: CONTEXT.md ## Specific Ideas
def compute_skew(chain_df: pd.DataFrame) -> str:
    """Compare OTM put IV to OTM call IV at same delta distance."""
    if chain_df is None or chain_df.empty:
        return "N/A"
    calls = chain_df[chain_df["option_type"] == "call"].dropna(subset=["iv"])
    puts  = chain_df[chain_df["option_type"] == "put"].dropna(subset=["iv"])
    if calls.empty or puts.empty:
        return "N/A"
    # Use delta-0.25 proxies: OTM calls have delta ~0.25, OTM puts have delta ~-0.25
    # If greeks available, use delta; else use moneyness approximation
    if "delta" in chain_df.columns and chain_df["delta"].notna().any():
        otm_call_iv = calls[calls["delta"].between(0.20, 0.30)]["iv"].mean()
        otm_put_iv  = puts[puts["delta"].between(-0.30, -0.20)]["iv"].mean()
    else:
        # Fallback: upper 25% strikes = OTM calls, lower 25% = OTM puts
        call_threshold = calls["strike"].quantile(0.75)
        put_threshold  = puts["strike"].quantile(0.25)
        otm_call_iv = calls[calls["strike"] >= call_threshold]["iv"].mean()
        otm_put_iv  = puts[puts["strike"] <= put_threshold]["iv"].mean()
    if pd.isna(otm_call_iv) or pd.isna(otm_put_iv):
        return "N/A"
    diff = otm_put_iv - otm_call_iv
    if diff > 0.02:
        return f"Put skew elevated (+{diff:.2%})"
    elif diff < -0.02:
        return f"Call skew elevated ({diff:.2%})"
    else:
        return f"Flat skew ({diff:+.2%})"
```

### Pattern 7: Term Structure (Contango / Backwardation)

```python
# Source: CONTEXT.md ## Specific Ideas
def compute_term_structure(near_chain_df: pd.DataFrame, far_chain_df: pd.DataFrame) -> str:
    """Compare near-term expiry IV to far-term expiry IV."""
    if near_chain_df is None or far_chain_df is None:
        return "N/A"
    near_iv = near_chain_df["iv"].median() if "iv" in near_chain_df.columns else None
    far_iv  = far_chain_df["iv"].median() if "iv" in far_chain_df.columns else None
    if near_iv is None or far_iv is None or pd.isna(near_iv) or pd.isna(far_iv):
        return "N/A"
    if far_iv > near_iv + 0.01:
        return f"Contango (near {near_iv:.1%}, far {far_iv:.1%})"
    elif near_iv > far_iv + 0.01:
        return f"Backwardation (near {near_iv:.1%}, far {far_iv:.1%})"
    else:
        return f"Flat ({near_iv:.1%} near, {far_iv:.1%} far)"
```

### Pattern 8: Options Flow Metrics

```python
# Source: CONTEXT.md ## Specific Ideas
def compute_flow_metrics(chain_df: pd.DataFrame) -> dict:
    """Compute unusual volume, put/call ratio, net flow bias from a single expiry chain."""
    if chain_df is None or chain_df.empty:
        return {"pc_ratio": None, "unusual_count": 0, "net_bias": "N/A"}

    calls = chain_df[chain_df["option_type"] == "call"]
    puts  = chain_df[chain_df["option_type"] == "put"]

    call_vol = calls["volume"].sum() if "volume" in calls.columns else 0
    put_vol  = puts["volume"].sum()  if "volume" in puts.columns  else 0

    # Put/call volume ratio
    pc_ratio = (put_vol / call_vol) if call_vol > 0 else None

    # Unusual volume: contracts where volume > 2× open_interest
    if "volume" in chain_df.columns and "open_interest" in chain_df.columns:
        unusual_mask = (chain_df["volume"] > 2 * chain_df["open_interest"]) & (chain_df["open_interest"] > 0)
        unusual_count = int(unusual_mask.sum())
    else:
        unusual_count = 0

    # Net flow bias (call dominance vs put dominance by volume)
    total_vol = call_vol + put_vol
    if total_vol > 0:
        call_pct = call_vol / total_vol
        if call_pct > 0.6:
            net_bias = f"Call-dominated ({call_pct:.0%} call volume)"
        elif call_pct < 0.4:
            net_bias = f"Put-dominated ({1-call_pct:.0%} put volume)"
        else:
            net_bias = f"Balanced ({call_pct:.0%} calls, {1-call_pct:.0%} puts)"
    else:
        net_bias = "N/A"

    return {"pc_ratio": round(pc_ratio, 2) if pc_ratio else None,
            "unusual_count": unusual_count,
            "net_bias": net_bias}
```

### Anti-Patterns to Avoid

- **Using `llm.bind_tools(tools)` when no tools needed:** The existing analysts all use this pattern, but Phase 2 agents are single-pass and must NOT bind tools. Binding tools with an empty list or unused tools wastes tokens and may confuse some LLM providers.
- **Writing to `state["messages"]`:** CONTEXT.md explicitly forbids adding to the messages thread. Return ONLY `{"volatility_report": ...}` or `{"options_flow_report": ...}`.
- **Calling `result.content` when `result.tool_calls` might exist:** Not a risk here since no tools are bound, but still — do not add the `if len(result.tool_calls) == 0` guard pattern from other analysts. It implies tools exist.
- **Fetching price history inside `route_to_vendor`:** The 30-day HV requires a direct `yfinance.Ticker.history()` call, not through the options data vendor abstraction. Use yfinance directly for price history.
- **Multiple chain fetches when data is unavailable:** Always guard against empty expirations list before fetching chains. A missing expirations list should degrade gracefully to a report acknowledging missing data.
- **Parsing the tabular string with `pd.read_csv(sep=',')`:** The data layer returns `DataFrame.to_string(index=False)` which is whitespace-aligned, not CSV. Use `sep=r'\s+'` with `engine='python'` in `pd.read_csv(io.StringIO(...))`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IV data retrieval | Custom Tradier API calls | `route_to_vendor("get_historical_iv", ticker)` | Phase 1 already built this with caching, fallback, and error handling |
| Options chain retrieval | Custom parsing | `route_to_vendor("get_options_chain", ticker, expiration)` | Phase 1 already built this with Tradier + yfinance fallback |
| Stock price history for HV | Custom downloader | `yf.Ticker(ticker).history(period="3mo")` | yfinance already in dependency stack |
| LLM prompt formatting | String concatenation | `ChatPromptTemplate.from_messages(...)` | Established pattern in every existing analyst |

**Key insight:** The hardest part of these agents is correctly parsing the tabular string format returned by the data layer. The data layer intentionally returns human-readable strings (not DataFrames) to match the existing equity agent contract. Plan to write a shared `_parse_tabular_string()` helper used by both agents.

## Common Pitfalls

### Pitfall 1: Options Return Strings, Not DataFrames
**What goes wrong:** Calling `route_to_vendor("get_options_chain", ...)` and trying to use the result as a DataFrame.
**Why it happens:** The data layer contract (established by the existing equity agents) returns formatted strings, not DataFrames. `tradier_utils.py` and `y_finance_options.py` both return `df.to_string(index=False)`.
**How to avoid:** Always parse with `pd.read_csv(io.StringIO(result), sep=r'\s+', engine='python')` after checking for the "No options data available" sentinel string.
**Warning signs:** `AttributeError: 'str' object has no attribute 'iterrows'` or similar.

### Pitfall 2: yfinance Options Chain Has No Greeks
**What goes wrong:** Computing skew from delta values when yfinance is the vendor — delta is always `None`.
**Why it happens:** `y_finance_options.py` explicitly sets `delta=None, gamma=None, theta=None, vega=None` because yfinance does not provide greeks.
**How to avoid:** Implement delta-based skew as primary path, moneyness-based skew as fallback (see Pattern 6). Check `chain_df["delta"].notna().any()` before using delta.
**Warning signs:** Skew always returning "N/A" in yfinance mode.

### Pitfall 3: Historical IV Series Is Forward-Looking (Expiration Dates, Not Trade Dates)
**What goes wrong:** Treating the `date` column in the historical IV output as past trade dates. It is actually the expiration date of the contracts sampled.
**Why it happens:** Both `tradier_utils.get_historical_iv` and `y_finance_options.get_historical_iv` sample IV by expiration date as an approximation of a true time-series. The "date" is the expiration date, not the observation date.
**How to avoid:** Do not attempt to join the IV series to a calendar. Treat it as an ordered IV sample for rank/percentile computation only.
**Warning signs:** IV rank calculations that look date-confused or produce outlier values.

### Pitfall 4: Empty Expirations List
**What goes wrong:** `route_to_vendor("get_options_expirations", ticker)` returns `[]`, then `expirations[0]` raises `IndexError`.
**Why it happens:** Ticker has no listed options (ETFs, certain stocks), sandbox Tradier returns nothing, or yfinance rate-limited.
**How to avoid:** Guard `if expirations` before indexing. If no expirations, return a report string saying data is unavailable rather than raising.
**Warning signs:** `IndexError: list index out of range` at runtime.

### Pitfall 5: LLM Invocation Pattern Differs from Existing Agents
**What goes wrong:** Copying the existing agent pattern verbatim with `MessagesPlaceholder(variable_name="messages")` and `chain.invoke(state["messages"])`, then trying to filter tool calls.
**Why it happens:** Phase 2 agents do not use the messages thread at all. Passing `state["messages"]` pollutes the prompt with unrelated equity analysis context.
**How to avoid:** Use `ChatPromptTemplate.from_messages([("system", ...), ("human", ...)])` and invoke with `(prompt | llm).invoke({})` (empty dict, no messages).
**Warning signs:** LLM producing incorrect reports that reference equity analysis context not relevant to options.

### Pitfall 6: `quick_think_llm` vs Direct LLM Parameter
**What goes wrong:** Looking up `quick_think_llm` from config inside the agent — the LLM is injected as a parameter.
**Why it happens:** The LLM model is selected at graph-build time and passed into the factory. The agent does not need to look up config.
**How to avoid:** Use the `llm` parameter directly. The caller (graph builder, Phase 5) decides which LLM to pass.

## Code Examples

### Volatility Analyst — Minimal Structure
```python
# Source: derived from CONTEXT.md decisions + existing analyst pattern
from langchain_core.prompts import ChatPromptTemplate
from tradingagents.dataflows.interface import route_to_vendor
import io, math, pandas as pd, yfinance as yf


def create_volatility_analyst(llm):

    def volatility_analyst_node(state: dict) -> dict:
        ticker = state["company_of_interest"]
        trade_date = state["trade_date"]

        # Fetch data
        iv_str = route_to_vendor("get_historical_iv", ticker)
        expirations = route_to_vendor("get_options_expirations", ticker)
        near_chain_str = route_to_vendor("get_options_chain", ticker, expirations[0]) if expirations else ""
        far_chain_str  = route_to_vendor("get_options_chain", ticker, expirations[-1]) if len(expirations) > 1 else ""

        # Compute metrics
        metrics = _compute_all_volatility_metrics(ticker, iv_str, near_chain_str, far_chain_str)

        # Single LLM call
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", _format_data_prompt(ticker, trade_date, metrics)),
        ])
        result = (prompt | llm).invoke({})

        return {"volatility_report": result.content}

    return volatility_analyst_node
```

### Options Flow Analyst — Minimal Structure
```python
# Source: derived from CONTEXT.md decisions
from langchain_core.prompts import ChatPromptTemplate
from tradingagents.dataflows.interface import route_to_vendor


def create_options_flow_analyst(llm):

    def options_flow_analyst_node(state: dict) -> dict:
        ticker = state["company_of_interest"]
        trade_date = state["trade_date"]

        expirations = route_to_vendor("get_options_expirations", ticker)
        # Use nearest expiry for flow analysis (most active)
        chain_str = route_to_vendor("get_options_chain", ticker, expirations[0]) if expirations else ""

        metrics = _compute_all_flow_metrics(chain_str)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", _format_data_prompt(ticker, trade_date, metrics)),
        ])
        result = (prompt | llm).invoke({})

        return {"options_flow_report": result.content}

    return options_flow_analyst_node
```

### Unit Test Pattern (mocking data layer + LLM)
```python
# Source: derived from tests/dataflows/test_tradier_utils.py mock pattern
from unittest.mock import patch, MagicMock

def test_volatility_analyst_returns_report():
    mock_llm = MagicMock()
    mock_llm_response = MagicMock()
    mock_llm_response.content = "IV Rank: 72 (high). IV Percentile: 68th."
    mock_llm.__or__ = lambda self, other: MagicMock(invoke=lambda _: mock_llm_response)

    state = {"company_of_interest": "AAPL", "trade_date": "2026-03-31", "messages": []}

    with patch("tradingagents.agents.options.volatility_analyst.route_to_vendor") as mock_route, \
         patch("tradingagents.agents.options.volatility_analyst.yf") as mock_yf:

        mock_route.side_effect = lambda method, *args: {
            "get_historical_iv": "date    iv\n2025-04-01  0.25\n2025-07-01  0.35\n",
            "get_options_expirations": ["2026-04-17", "2026-06-20"],
            "get_options_chain": "strike  option_type  volume  open_interest  iv  delta\n150.0  call  1000  500  0.28  0.55\n",
        }[method]

        mock_hist = MagicMock()
        mock_hist.empty = False
        mock_hist.__contains__ = lambda self, x: x == "Close"
        mock_yf.Ticker.return_value.history.return_value = mock_hist

        from tradingagents.agents.options.volatility_analyst import create_volatility_analyst
        node = create_volatility_analyst(mock_llm)
        result = node(state)

    assert "volatility_report" in result
    assert isinstance(result["volatility_report"], str)
```

### `__init__.py` Export Pattern
```python
# Source: tradingagents/agents/__init__.py pattern
from .options.volatility_analyst import create_volatility_analyst
from .options.options_flow_analyst import create_options_flow_analyst
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ReAct loop (tool calls + observations) | Single-pass: compute in Python, LLM writes narrative | Phase 2 decision | Deterministic metric computation; LLM is a formatter, not a reasoner |
| LLM selects indicators (market_analyst) | Python computes all metrics; LLM receives pre-computed values | Phase 2 decision | Reproducible, testable, faster, cheaper |

**Deprecated/outdated for this phase:**
- `MessagesPlaceholder` in prompt: not used since we do not pass messages from state
- `llm.bind_tools(tools)`: not used since no tools are needed
- `if len(result.tool_calls) == 0: report = result.content`: not needed since no tool calls possible

## Open Questions

1. **How to handle the case where `get_historical_iv` returns fewer than ~10 data points**
   - What we know: Both Tradier and yfinance `get_historical_iv` sample by expiration date (not daily observations). A ticker with few listed expirations might return only 3-5 rows.
   - What's unclear: What is the minimum sample size for IV rank/percentile to be meaningful?
   - Recommendation: Set a minimum of 4 data points; below that, omit IV rank/percentile from the report and note "Insufficient IV history."

2. **P/C ratio 20-day average — no historical flow data available**
   - What we know: CONTEXT.md mentions "put/call ratio divergence vs recent average." Phase 1 data layer does not store historical flow data — `get_options_chain` returns only the current chain.
   - What's unclear: Whether to skip historical comparison or compare near vs far expiry P/C ratios as a proxy.
   - Recommendation: Report the current P/C ratio only (no historical average); note that multi-day trend analysis is deferred to v2 (DATA-V2-02). Use the current session's P/C ratio as the sole flow signal.

3. **Block/sweep detection without tick data**
   - What we know: CONTEXT.md mentions detecting block/sweep activity. This typically requires trade-level tick data (individual prints). The options chain from Tradier/yfinance gives daily volume and OI, not individual trades.
   - What's unclear: How to approximate block/sweep from snapshot data.
   - Recommendation: Proxy "unusual activity" as volume > 2× OI (from CONTEXT.md) and flag large absolute volume contracts. Do not claim to detect "sweeps" specifically — report as "unusual volume activity." This is honest and avoids overstating what the data supports.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml `[tool.pytest.ini_options]` testpaths = ["tests"]) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/agents/ -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGENT-01 | `create_volatility_analyst` returns a factory | unit | `pytest tests/agents/test_volatility_analyst.py -x` | Wave 0 |
| AGENT-01 | Factory returns a callable node | unit | `pytest tests/agents/test_volatility_analyst.py::test_factory_returns_callable -x` | Wave 0 |
| AGENT-01 | Node returns dict with `volatility_report` key | unit | `pytest tests/agents/test_volatility_analyst.py::test_node_returns_volatility_report -x` | Wave 0 |
| AGENT-01 | Node handles empty expirations gracefully (no crash) | unit | `pytest tests/agents/test_volatility_analyst.py::test_empty_expirations -x` | Wave 0 |
| AGENT-01 | Node handles "No historical IV data" message gracefully | unit | `pytest tests/agents/test_volatility_analyst.py::test_no_historical_iv -x` | Wave 0 |
| AGENT-01 | IV rank formula correct: (current-min)/(max-min)*100 | unit | `pytest tests/agents/test_volatility_analyst.py::test_iv_rank_formula -x` | Wave 0 |
| AGENT-01 | IV percentile: % days below current IV | unit | `pytest tests/agents/test_volatility_analyst.py::test_iv_percentile_formula -x` | Wave 0 |
| AGENT-01 | 30-day HV computation uses 21-day rolling std * sqrt(252) | unit | `pytest tests/agents/test_volatility_analyst.py::test_hv30_formula -x` | Wave 0 |
| AGENT-01 | Does NOT write to `messages` field | unit | `pytest tests/agents/test_volatility_analyst.py::test_no_messages_written -x` | Wave 0 |
| AGENT-02 | `create_options_flow_analyst` factory returns callable | unit | `pytest tests/agents/test_options_flow_analyst.py::test_factory_returns_callable -x` | Wave 0 |
| AGENT-02 | Node returns dict with `options_flow_report` key | unit | `pytest tests/agents/test_options_flow_analyst.py::test_node_returns_flow_report -x` | Wave 0 |
| AGENT-02 | Node handles empty expirations gracefully | unit | `pytest tests/agents/test_options_flow_analyst.py::test_empty_expirations -x` | Wave 0 |
| AGENT-02 | Unusual volume: volume > 2× OI flagged | unit | `pytest tests/agents/test_options_flow_analyst.py::test_unusual_volume_detection -x` | Wave 0 |
| AGENT-02 | P/C ratio computed correctly from chain | unit | `pytest tests/agents/test_options_flow_analyst.py::test_pc_ratio -x` | Wave 0 |
| AGENT-02 | Does NOT write to `messages` field | unit | `pytest tests/agents/test_options_flow_analyst.py::test_no_messages_written -x` | Wave 0 |
| AGENT-01+02 | `AgentState` has `volatility_report` and `options_flow_report` fields | unit | `pytest tests/agents/test_agent_states.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/agents/ -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/agents/__init__.py` — package marker
- [ ] `tests/agents/test_volatility_analyst.py` — covers AGENT-01
- [ ] `tests/agents/test_options_flow_analyst.py` — covers AGENT-02
- [ ] `tests/agents/test_agent_states.py` — verifies new AgentState fields

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `tradingagents/agents/analysts/market_analyst.py` — factory pattern, ChatPromptTemplate usage
- Direct code inspection: `tradingagents/agents/analysts/fundamentals_analyst.py` — factory closure pattern
- Direct code inspection: `tradingagents/agents/utils/agent_states.py` — AgentState TypedDict pattern, Annotated field style
- Direct code inspection: `tradingagents/agents/__init__.py` — export pattern for new agents
- Direct code inspection: `tradingagents/dataflows/interface.py` — `route_to_vendor` API, VENDOR_METHODS
- Direct code inspection: `tradingagents/dataflows/tradier_utils.py` — `get_historical_iv`, `get_options_chain` return format
- Direct code inspection: `tradingagents/dataflows/y_finance_options.py` — fallback, greeks=None, `iv` column name
- Direct code inspection: `tradingagents/default_config.py` — `enable_options`, `options_vendor` keys
- Direct code inspection: `pyproject.toml` — pytest config, dependency versions
- Direct code inspection: `.planning/phases/02-volatility-flow-agents/02-CONTEXT.md` — all locked decisions
- Direct code inspection: `tests/dataflows/test_tradier_utils.py` — mock pattern for data layer tests

### Secondary (MEDIUM confidence)
- `tests/conftest.py` — shared fixture pattern, confirms `mock_tradier_chain_response` fixture structure

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all confirmed in pyproject.toml and existing code
- Architecture: HIGH — factory pattern directly observable in 5 existing agents
- Data layer API: HIGH — read tradier_utils.py and y_finance_options.py source directly
- Metric formulas: HIGH — formulas from CONTEXT.md (locked decisions), standard financial definitions
- Pitfalls: HIGH — derived from direct source inspection of data layer return contracts
- Test patterns: HIGH — derived from existing test files in tests/dataflows/

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable codebase, no external API dependencies introduced in this phase)
