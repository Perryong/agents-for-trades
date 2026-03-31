---
phase: 02-volatility-flow-agents
plan: "01"
subsystem: agents/options
tags: [volatility, options, agent, langchain, tdd]
dependency_graph:
  requires:
    - 01-options-data-infrastructure (route_to_vendor, get_historical_iv, get_options_chain, get_options_expirations)
  provides:
    - create_volatility_analyst factory
    - AgentState.volatility_report field
    - AgentState.options_flow_report field
    - tradingagents/agents/options/ package
  affects:
    - tradingagents/agents/__init__.py (new export)
    - tradingagents/agents/utils/agent_states.py (new fields)
tech_stack:
  added: []
  patterns:
    - single-pass agent factory (compute in Python, LLM writes narrative)
    - ChatPromptTemplate.from_messages with no MessagesPlaceholder
    - (prompt | llm).invoke({}) with empty dict (no messages thread)
key_files:
  created:
    - tradingagents/agents/options/__init__.py
    - tradingagents/agents/options/volatility_analyst.py
    - tests/agents/__init__.py
    - tests/agents/test_agent_states.py
    - tests/agents/test_volatility_analyst.py
  modified:
    - tradingagents/agents/utils/agent_states.py
    - tradingagents/agents/__init__.py
decisions:
  - "Mock LLM in tests via mock_llm.return_value (LangChain calls LLM as callable, not via .invoke)"
  - "System prompt uses angle-bracket placeholders to avoid LangChain template variable conflicts"
  - "IV rank returns 50.0 when iv_series has fewer than 4 observations (insufficient history)"
metrics:
  duration: 7min
  completed: "2026-03-31"
  tasks_completed: 2
  files_modified: 7
---

# Phase 02 Plan 01: Volatility Analyst Agent Summary

Single-pass volatility analyst factory with IV rank, IV percentile, HV30, skew (delta-based with moneyness fallback), and term structure metrics computed in Python before a single LLM formatting call.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | AgentState extension + options package + test infrastructure | bc620c3 | agent_states.py, options/__init__.py, volatility_analyst.py (stub), agents/__init__.py, tests/agents/__init__.py, tests/agents/test_agent_states.py |
| 2 | Implement volatility analyst agent with unit tests | e4fb7f3 | volatility_analyst.py (full), tests/agents/test_volatility_analyst.py |

## What Was Built

**AgentState extension** (`tradingagents/agents/utils/agent_states.py`): Two new `Annotated[str, ...]` fields added — `volatility_report` and `options_flow_report`. Both sit at the end of the class, consistent with existing field order.

**Options agents package** (`tradingagents/agents/options/`): New `__init__.py` exporting `create_volatility_analyst`. Mirrors the existing pattern of per-subsystem subdirectories under `tradingagents/agents/`.

**Volatility analyst factory** (`tradingagents/agents/options/volatility_analyst.py`):
- `_parse_tabular_string(s)`: Parses `DataFrame.to_string(index=False)` output using `pd.read_csv(io.StringIO, sep=r'\s+', engine='python')`. Returns None for empty or "No " sentinel strings.
- `_compute_iv_metrics(iv_series, current_iv)`: IV rank = (current - min) / (max - min) * 100; IV percentile = ecdf at current_iv. Returns `{"iv_rank": float, "iv_pct": float}`.
- `_compute_hv30(ticker)`: `yf.Ticker(ticker).history("3mo")["Close"].pct_change().rolling(21).std().iloc[-1] * sqrt(252) * 100`.
- `_compute_skew(chain_df)`: Primary path uses delta 0.20–0.30 range for OTM calls/puts; fallback uses strike quartiles. Returns "Put skew elevated (+X%)", "Call skew elevated (X%)", or "Flat skew (+X%)".
- `_compute_term_structure(near_df, far_df)`: Compares median IV. Returns "Contango", "Backwardation", or "Flat" with values.
- `create_volatility_analyst(llm)`: Returns `volatility_analyst_node(state)` closure. Fetches 3 data items via `route_to_vendor`, computes all metrics, invokes `(prompt | llm).invoke({})`, returns `{"volatility_report": result.content}`.

**Test infrastructure** (`tests/agents/`): 21 unit tests total — 5 for AgentState fields/imports, 16 for volatility analyst (factory callable, node return contract, IV rank formula, IV percentile formula, HV30 zero/nonzero cases, empty expirations graceful handling, missing IV graceful handling, no messages key, skew put/call/none, term structure contango/backwardation/none, integration test).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] System prompt used Python {}-style placeholders**
- **Found during:** Task 2 GREEN phase
- **Issue:** `SYSTEM_PROMPT` contained `{iv_rank}`, `{skew_desc}` etc. LangChain's `ChatPromptTemplate` treats curly braces as template variables and raised `KeyError` when `.invoke({})` was called with an empty dict.
- **Fix:** Replaced all `{placeholder}` in SYSTEM_PROMPT with `<placeholder>` (angle brackets). DATA_TEMPLATE (passed as pre-formatted human message content) is unaffected since it is formatted via Python `.format()` before being placed in the template.
- **Files modified:** `tradingagents/agents/options/volatility_analyst.py`
- **Commit:** e4fb7f3

**2. [Rule 1 - Bug] Mock LLM `__ror__` approach did not work with LangChain's RunnableSequence**
- **Found during:** Task 2 GREEN phase
- **Issue:** LangChain builds a `RunnableSequence` from `prompt | llm` and calls the LLM as a callable (`llm(messages)`), not via `llm.invoke()` or `llm.__ror__`. The original mock helper set `mock_llm.__ror__` which was never called.
- **Fix:** Updated `_make_mock_llm()` in tests to set `mock_llm.return_value = mock_response` so that `mock_llm(messages)` returns the mock response. Also set `mock_llm.invoke = ...` for forward compatibility.
- **Files modified:** `tests/agents/test_volatility_analyst.py`
- **Commit:** e4fb7f3

## Known Stubs

None — `create_volatility_analyst` is fully implemented with all metric computations wired to the data layer and LLM.

## Self-Check: PASSED
