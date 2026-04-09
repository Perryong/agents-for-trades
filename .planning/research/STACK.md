# Technology Stack — v2.0 Vol-Aware Analyst Pipeline

**Project:** TradingAgents — Options Extension
**Milestone:** v2.0 Vol-Aware Analysis Pipeline
**Researched:** 2026-04-09
**Confidence:** HIGH
**Scope:** NEW additions only. Existing stack is validated and unchanged.

---

## Context: What Already Exists (Do Not Re-add)

| Concern | Existing | Version | Notes |
|---------|----------|---------|-------|
| Graph framework | LangGraph StateGraph | 1.1.3 | All new nodes follow `add_node` / `add_edge` pattern |
| LLM abstraction | langchain-core | 1.2.23 | `ChatPromptTemplate`, `SystemMessage`, `HumanMessage` available |
| Structured output | Pydantic v2 BaseModel | 2.12.5 | Already used for screener agent JSON output |
| Data layer | yfinance + Tradier | yfinance 1.2.0 | `get_options_chain()`, `get_historical_iv()` already implemented |
| Caching | `get_cached_text()` in yfinance_cache.py | — | Smart cache with `is_good` quality guard; reuse for vol context |
| Agent state | `AgentState(MessagesState)` TypedDict | — | `_last_value` reducer pattern for all new fields |
| Error handling | `_safe_options_node()` wrapper | — | Try/catch with empty-string fallback; reuse for Vol Context node |
| Frontend | React 19, TypeScript, Tailwind v4 | — | No peer-dep changes |

---

## New Stack Additions for v2.0

### Summary

**Zero new Python packages. Zero new npm packages.**

Every capability needed for v2.0 is already present in the installed stack. The work is architectural — adding a graph node, extending prompts, and updating frontend layout — not dependency work.

---

### 1. Vol Context Node: Pure Python Data Computation

**No new libraries.** The Vol Context node is a Python function that reads from the existing data layer.

| Existing Asset | What It Provides | Used For |
|----------------|------------------|----------|
| `get_options_chain(symbol, expiration)` in `y_finance_options.py` | Options chain with IV, volume, OI per contract | P/C ratio, skew direction, IV from near-term expiry |
| `get_historical_iv(symbol)` in `y_finance_options.py` | Median IV per expiration date over trailing period | IV rank, IV vs HV calculation |
| `get_cached_text()` in `yfinance_cache.py` | Smart cache with TTL and `is_good` quality guard | Cache the vol narrative; don't re-fetch within TTL |
| `_safe_options_node()` in `setup.py` | Try/catch wrapper returning empty-string fallback | Wrap Vol Context node so analyst pipeline is non-blocking |

**Vol narrative construction is pure Python arithmetic:**
- IV rank = percentile position of current IV within 52-week IV range (no library needed)
- IV vs HV ratio = current_iv / hv30 (already computed in `volatility_analyst.py`)
- P/C ratio = sum(put volume) / sum(call volume) from options chain
- Skew direction = compare 25-delta put IV to 25-delta call IV from chain

**Why not reuse the existing `volatility_analyst.py` LLM agent for the pre-fetch:**
That agent runs after Trader in the options pipeline and produces a full markdown report. The Vol Context node is a lighter pre-fetch that produces a single narrative paragraph — no LLM call needed. Arithmetic only. This keeps Vol Context latency under 1 second (vs 10-30 seconds for an LLM call) and avoids burning tokens before any analyst has run.

---

### 2. Prompt Engineering: System + User Hybrid (D-09)

**No new libraries.** `langchain_core.messages.SystemMessage` and `langchain_core.messages.HumanMessage` are already in langchain-core 1.2.23.

The D-09 hybrid structure splits vol context injection into two parts:

```python
from langchain_core.messages import SystemMessage, HumanMessage

# System message: role framing + directive strength (per-analyst)
# User message: the vol narrative paragraph (identical for all analysts)

# Market Analyst (Strong directive)
system_directive = (
    "Volatility IS market conditions. The vol context below reflects how options "
    "markets are pricing risk right now — weight it heavily in your assessment. "
    "If IV is elevated, that IS the market telling you something."
)

# Technical Analyst (Moderate directive)
system_directive = (
    "The vol context below may confirm or contradict price action. Elevated IV "
    "during a breakout suggests conviction; elevated IV during consolidation "
    "suggests fear. Incorporate where relevant."
)

# News Analyst (Weak directive)
system_directive = (
    "Reference the vol context only if news events appear to be driving the "
    "elevated volatility. Otherwise, focus on your primary analysis."
)
```

**Why system message for directive, user message for data:**
System messages set behavioral framing that persists across tool-calling loops. User messages deliver factual context. Splitting them means the per-analyst directive is not diluted by the shared vol paragraph, and the shared paragraph is not repeated in the system message of every analyst. This is the documented LangChain best practice for role-specific context injection.

**Why not a single concatenated system message (Option A rejected by D-09):**
Concatenating everything into the system message makes the per-analyst directive invisible — it reads as one block of instructions. The split gives clear separation between "how to use this context" (system) and "here is the context" (user).

**Why not a separate LangChain chain step (over-engineered for this use case):**
Vol injection is a string interpolation, not a transformation pipeline. Adding a LangChain `RunnableLambda` or `RunnablePassthrough` to inject a string adds indirection with no benefit. Direct `state["vol_context"]` read in the analyst's prompt construction is simpler and consistent with how `state["trade_date"]` and `state["company_of_interest"]` are already injected.

---

### 3. `vol_note` Field: Free-Text Extraction Over Structured Output

**Approach: Free-text extraction from prose report (defer structured output enforcement).**

The 17-CONTEXT.md defers `vol_note` structured output enforcement to a follow-up phase if free-text works. Research confirms this is the right call for v2.0.

**Why free-text works here:**
The analyst is instructed to include `vol_note` as a labeled field at the end of its report (e.g., `**Vol Note:** <one sentence>`). Regex extraction on a clearly labeled line is reliable when the LLM is instructed to produce it in a fixed format. The Trader agent already uses this pattern — a JSON block at the end of prose output — and it works.

**Pattern (consistent with Trader agent):**
```python
# In analyst prompt:
"End your report with exactly this line:\n**Vol Note:** <one sentence referencing how vol context affected your assessment>"

# Extraction in analyst node:
import re
match = re.search(r'\*\*Vol Note:\*\*\s*(.+)', report)
vol_note = match.group(1).strip() if match else None
```

**Why NOT `with_structured_output` (Pydantic BaseModel) for analysts:**
The tool-calling analysts (market, social, news, fundamentals) already use `llm.bind_tools(tools)`. You cannot chain `bind_tools` and `with_structured_output` on the same LLM call — they are mutually exclusive. Switching to structured output would require abandoning the tool-calling loop architecture, which is a major refactor. Free-text extraction preserves the existing agent architecture unchanged.

**Why NOT a second LLM call to extract `vol_note`:**
Adds token cost and latency for every analyst. The labeled-field pattern makes extraction deterministic enough without a second call.

**When to revisit:** If `vol_note` extraction fails more than ~10% of runs in testing, add a validation step. If all 5 analysts are eventually converted to single-pass (no tool calls), `with_structured_output` becomes viable.

---

### 4. LangGraph Node Registration: Existing Pattern

**No new LangGraph APIs.** The Vol Context node follows the identical registration pattern as all other nodes.

```python
# In setup.py — Vol Context node addition:
workflow.add_node("Vol Context", vol_context_node)

# Fan-out from Vol Context to all equity analysts (replaces direct START -> analysts)
workflow.add_conditional_edges(
    "Vol Context",
    route_equity_start,     # existing function — returns equity_entries list
    equity_entries,
)

# START now goes to Vol Context only
workflow.add_edge(START, "Vol Context")
```

**Node naming:** "Vol Context" — no colon, consistent with "Options - X" pattern. LangGraph 1.1.3 reserves `:` in node names (documented in existing KEY_DECISIONS).

**Frontend node list:** Add `"Vol Context"` to `EQUITY_NODES` (or a new `PRE_NODES` constant) in `frontend/src/types.ts`. The 17-CONTEXT.md leaves this choice to implementation — recommend adding it as the first entry in a new `PRE_NODES` constant to keep semantics clear (it is not an analyst, it is pre-processing).

---

### 5. AgentState Extension

**No new patterns.** Add two fields following the existing `_last_value` reducer pattern.

```python
# In agent_states.py — additions to AgentState:
vol_context: Annotated[str, _last_value]          # vol narrative paragraph; empty string if fetch failed
vol_context_available: Annotated[bool, _last_value]  # flag for Risk Judge weighting
```

**Why `vol_context_available` as a separate boolean:**
The Risk Judge prompt can read this flag to adjust weighting — "if vol context was unavailable, do not penalize the analysts for not referencing it." This is cleaner than checking `if state["vol_context"] == ""`.

---

### 6. Frontend: Tab Grouping + Collapsible Banner

**No new npm packages.** Both features use existing React 19 + TypeScript + Tailwind v4.

**Tab grouping (D-07):**
Add section header `<div>` elements above the existing tab row in `ReportTabs.tsx`. Pure CSS layout — three `<span>` labels (Equity / Options / Decision) positioned above the relevant tab buttons. No component library needed.

**Collapsible vol banner (D-08):**
Use the HTML `<details>` / `<summary>` element pattern. Available in all modern browsers, zero JavaScript needed for open/close behavior.

```tsx
// In ReportPane.tsx — vol context banner above each analyst tab content:
<details open={isFirstView}>
  <summary className="cursor-pointer text-sm font-medium text-amber-400 py-2">
    Vol Context — {volContextAvailable ? 'Available' : 'Unavailable'}
  </summary>
  <div className="text-sm text-slate-300 p-3 bg-slate-800 rounded mb-4">
    {volContext || 'Vol context was not available for this ticker.'}
  </div>
</details>
```

**Why `<details>/<summary>` over a custom accordion component:**
Zero JavaScript for toggle behavior, native browser accessibility (keyboard navigable), no Tailwind plugin needed. The existing codebase has no accordion component — building one adds complexity for a feature that `<details>` handles natively.

**Default state:** `open` attribute controls expand/collapse. Pass `open={true}` on first render, remove on subsequent renders by tracking in localStorage (or leave always-open — per 17-CONTEXT.md specifics, default expanded is preferred).

---

## Complete Dependency Delta

**Zero new packages.**

```
Python additions:   none
npm additions:      none
```

All capabilities are present in the existing installed stack:
- langchain-core 1.2.23 — `SystemMessage`, `HumanMessage`, `ChatPromptTemplate`
- pydantic 2.12.5 — `BaseModel`, `Field`, `Optional` (available if structured output needed later)
- langgraph 1.1.3 — `StateGraph.add_node()`, `add_edge()`, `add_conditional_edges()`
- yfinance 1.2.0 — options chain and IV history data
- React 19 + Tailwind v4 — `<details>/<summary>`, CSS section headers

---

## What NOT to Add

| Rejected | Reason | Pattern Instead |
|----------|--------|----------------|
| `with_structured_output` for analyst `vol_note` | Mutually exclusive with `bind_tools` — would require removing tool-calling loops from 4 analysts | Labeled field in prose + regex extraction (Trader agent pattern) |
| Second LLM call to extract `vol_note` | Doubles token cost per analyst (5x overhead) for a field that can be extracted with a regex | Labeled field format in the prompt instruction |
| LangChain `RunnableLambda` / `RunnablePassthrough` for vol injection | Adds indirection to a string interpolation — no benefit | Direct `state["vol_context"]` read in prompt construction |
| Separate "vol_note" tab in frontend | Adds a 14th tab; vol context is shared context not an analyst output | Collapsible banner pinned above existing analyst content |
| React accordion/disclosure component library (Radix, headlessui) | No existing component library in codebase; `<details>/<summary>` is native and sufficient | `<details open>` / `<summary>` HTML elements |
| LLM call in Vol Context node | Adds 10-30 seconds and token cost before any analyst runs; context can be computed arithmetically | Pure Python arithmetic on existing data layer output |
| New caching infrastructure for vol context | Existing `get_cached_text()` with `is_good` guard already handles this correctly | Reuse `yfinance_cache.get_cached_text()` with 30-min TTL |
| Dedicated vol_context database table | Vol context is ephemeral per analysis run — no cross-run value | Stays in `AgentState` only; not persisted |

---

## Integration Points

| New Feature | Attaches To | File |
|------------|-------------|------|
| Vol Context node (Python arithmetic) | `setup.py` — inserts before analyst fan-out | `tradingagents/graph/setup.py` |
| `vol_context` + `vol_context_available` fields | `AgentState` TypedDict | `tradingagents/agents/utils/agent_states.py` |
| Per-analyst system directive strings | Each analyst factory function | `tradingagents/agents/analysts/{market,technical,social,news,fundamentals}_analyst.py` |
| `vol_note` regex extraction | Each analyst node's return dict | Same 5 analyst files |
| "Vol Context" node name in progress tracking | `ProgressCallbackHandler._GRAPH_NODES` set | `tradingagents/graph/trading_graph.py` |
| "Vol Context" node in frontend node list | `PRE_NODES` constant (new) or `EQUITY_NODES[0]` | `frontend/src/types.ts` |
| `vol_context` field in `AnalysisResult` | SSE complete event payload | `frontend/src/types.ts` |
| Remove `enable_options` toggle | `ConfigSidebar.tsx`, `AnalyzeRequest`, `schemas.py`, `setup.py` | 4 files |
| Tab section headers (Equity/Options/Decision) | `ReportTabs.tsx` | `frontend/src/components/ReportTabs.tsx` |
| Collapsible vol banner | `ReportPane.tsx` — above analyst content | `frontend/src/components/ReportPane.tsx` |

---

## Version Compatibility

| Package | Version | Compatibility Note |
|---------|---------|-------------------|
| langchain-core | 1.2.23 | `SystemMessage` + `HumanMessage` stable since 0.1.x; no breaking changes in this area |
| langgraph | 1.1.3 | `add_node` / `add_edge` / `add_conditional_edges` API stable; no changes needed |
| pydantic | 2.12.5 | v2 `BaseModel` with `Optional` fields available if `vol_note` structured output added later |
| yfinance | 1.2.0 | `get_options_chain()` and `get_historical_iv()` already tested in production (v1.0) |

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Zero new dependencies | HIGH | All required primitives verified present in installed environment |
| Free-text `vol_note` extraction | HIGH | Identical pattern already proven in Trader agent JSON block extraction |
| `<details>/<summary>` collapsible | HIGH | Native HTML; no library dependency; works in all modern browsers |
| Vol Context node arithmetic | HIGH | Same data functions used by `volatility_analyst.py` (v1.0, shipped) |
| `with_structured_output` incompatibility with `bind_tools` | HIGH | LangChain documented constraint — both configure the LLM call; cannot combine |
| LangGraph node insertion pattern | HIGH | Directly read from `setup.py` source; no API guesswork |

---

## Sources

- Installed environment: `python -c "import importlib.metadata; ..."` — package versions confirmed directly
- `tradingagents/agents/utils/agent_states.py` — `AgentState` TypedDict, `_last_value` reducer pattern
- `tradingagents/graph/setup.py` — `_safe_options_node()`, node registration, edge wiring patterns
- `tradingagents/agents/analysts/market_analyst.py` — existing prompt structure (`ChatPromptTemplate`, `bind_tools`)
- `tradingagents/agents/analysts/technical_analyst.py` — single-pass (no tool loop) pattern for reference
- `tradingagents/agents/trader/trader.py` — labeled JSON block extraction pattern (reference for `vol_note`)
- `tradingagents/agents/options/volatility_analyst.py` — existing IV arithmetic; confirms reusability for Vol Context node
- `tradingagents/dataflows/yfinance_cache.py` — `get_cached_text()` with `is_good` guard
- `frontend/src/types.ts` — `EQUITY_NODES`, `OPTIONS_NODES`, `getNodeList()`, `REPORT_TABS`, `AnalysisResult`
- `.planning/phases/17-mandatory-options-vol-aware-analysts/17-CONTEXT.md` — all implementation decisions (D-01 through D-13)

---

*Stack research for: v2.0 Vol-Aware Analyst Pipeline*
*Researched: 2026-04-09*
