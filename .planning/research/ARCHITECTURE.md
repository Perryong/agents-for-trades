# Architecture Patterns

**Domain:** Vol-Aware Multi-Agent Analysis Pipeline (Phase 17)
**Researched:** 2026-04-09
**Confidence:** HIGH — all findings from direct codebase inspection

---

## Current Architecture (Baseline)

```
START
  ├── Market Analyst ──────────────────────────┐
  ├── Technical Analyst ───────────────────────┤
  ├── Social Analyst ──────────────────────────►── Bull/Bear Debate ── Research Manager ── Trader
  ├── News Analyst ───────────────────────────┤
  └── Fundamentals Analyst ────────────────────┘
                                                        Trader
                                                          │
                                   Options - Volatility Analyst (sequential, 7 nodes)
                                   ...
                                   Options - Greeks Monitor
                                          │
                              Risk Debate (Aggressive/Conservative/Neutral)
                                          │
                                       Risk Judge
                                          │
                                         END
```

Fan-out from START uses `add_conditional_edges` with a router returning all equity analyst node names. Fan-in is implicit — LangGraph holds Bull Researcher until all `Msg Clear *` nodes complete. Options pipeline is conditional on `enable_options` config flag. All options agents wrapped by `_safe_options_node()` for graceful failure.

---

## Target Architecture (Phase 17)

```
START
  │
Vol Context   <- NEW: synchronous Python node, no LLM, ~200-500ms
  │
  ├── Market Analyst ──────────────────────────┐
  ├── Technical Analyst ───────────────────────┤
  ├── Social Analyst ──────────────────────────►── Bull/Bear Debate ── Research Manager ── Trader
  ├── News Analyst ───────────────────────────┤
  └── Fundamentals Analyst ────────────────────┘
                                                        Trader
                                                          │
                                   Options - Volatility Analyst (always-on, unchanged)
                                   ...
                                   Options - Greeks Monitor
                                          │
                              Risk Debate (unchanged)
                                          │
                                       Risk Judge
                                          │
                                         END
```

The only structural graph change: `START → Vol Context → [fan-out]` replaces `START → [fan-out]`. The `add_conditional_edges` call moves from START to the Vol Context node. Options pipeline becomes unconditional (no `enable_options` branch).

---

## Component Boundaries

### New: Vol Context Node

| Attribute | Value |
|-----------|-------|
| File | `tradingagents/agents/pre_analysis/vol_context.py` (new file) |
| Factory | `create_vol_context_node()` — returns a plain closure, no LLM |
| Graph node name | `"Vol Context"` |
| Reads from state | `state["company_of_interest"]`, `state["trade_date"]` |
| Writes to state | `state["vol_context"]` — string narrative or None |
| Error behavior | Inline try/except returns `{"vol_context": None}` — never raises |

The node calls three existing data functions in sequence:

1. `get_options_expirations(ticker)` — if empty, return `{"vol_context": None}` immediately
2. `get_options_chain(ticker, expirations[0])` — nearest expiry; derive P/C ratio and skew from call/put IV columns
3. `get_historical_iv(ticker)` — derive IV rank: `(current_iv - min_iv) / (max_iv - min_iv)`

It assembles a template narrative from computed values — no LLM call. The existing `Options - Volatility Analyst` (LLM-based, runs after Trader) is unchanged and continues to perform the deep vol analysis for the options strategy pipeline.

### Modified: Five Analyst Factory Functions

Each analyst in `tradingagents/agents/analysts/` receives the same structural change:

- Read `vol_context = state.get("vol_context")` at node entry (use `.get()` not direct indexing — old state dicts may lack the key)
- Build `vol_block = f"\n\n## Vol Context\n{vol_context}\n"` if non-None, else empty string
- Inject `vol_directive` into system message via `prompt.partial()` — directive strength varies per analyst (see table below)
- Inject `vol_block` into system message via `prompt.partial()` — keeps data out of the message history that cycles through the tool-calling loop
- Add `{analyst}_vol_note` to the return dict — extracted from LLM output or empty string

Directive strength per analyst (decision D-11):

| Analyst | Strength | System Message Framing |
|---------|----------|----------------------|
| Market | Strong | Vol IS market conditions — weight IV rank and flow as primary inputs |
| Technical | Moderate | Elevated/compressed vol can confirm or contradict price action — integrate explicitly |
| Social | Moderate | P/C ratio and unusual flow are direct positioning sentiment measures — cite if material |
| News | Weak | Reference vol context only if a news event is the identifiable cause of elevated IV |
| Fundamentals | Weak | Flag vol context only when IV rank exceeds 90 — otherwise noise relative to fundamentals |

### Modified: AgentState

File: `tradingagents/agents/utils/agent_states.py`

New fields added to the `AgentState` TypedDict:

```python
# Vol Context pre-analysis
vol_context: Annotated[Optional[str], _last_value]

# Per-analyst vol acknowledgment (audit trail)
market_vol_note: Annotated[str, _last_value]
technical_vol_note: Annotated[str, _last_value]
social_vol_note: Annotated[str, _last_value]
news_vol_note: Annotated[str, _last_value]
fundamentals_vol_note: Annotated[str, _last_value]
```

`vol_context` is written once by Vol Context before the parallel fan-out — no concurrent write conflicts. Each `*_vol_note` is written by exactly one analyst branch — no conflicts. The existing `_last_value` reducer applies to all.

### Modified: Graph Setup

File: `tradingagents/graph/setup.py`

Three specific changes:

1. Import and register Vol Context node:
   ```python
   from tradingagents.agents.pre_analysis.vol_context import create_vol_context_node
   workflow.add_node("Vol Context", create_vol_context_node())
   ```

2. Move fan-out edge from START to Vol Context:
   ```python
   # Remove: workflow.add_conditional_edges(START, route_equity_start, equity_entries)
   # Add:
   workflow.add_edge(START, "Vol Context")
   workflow.add_conditional_edges("Vol Context", route_equity_start, equity_entries)
   ```

3. Remove `enable_options` conditional branching — unconditionally add all options nodes and wire `Trader → OPTIONS_NODES[0]`:
   ```python
   # Remove the if/else enable_options blocks entirely
   # Always execute:
   for node_name, factory_fn in OPTIONS_NODES:
       state_key = _OPTIONS_STATE_KEYS[factory_fn.__name__]
       workflow.add_node(node_name, _safe_options_node(factory_fn, state_key, self.quick_thinking_llm))
   workflow.add_edge("Trader", OPTIONS_NODES[0][0])
   for i in range(len(OPTIONS_NODES) - 1):
       workflow.add_edge(OPTIONS_NODES[i][0], OPTIONS_NODES[i + 1][0])
   workflow.add_edge(OPTIONS_NODES[-1][0], "Aggressive Analyst")
   ```

Also remove the `cfg = get_config(); enable_options = cfg.get(...)` read from `setup_graph()` — no longer needed.

### Modified: Progress Handler

File: `api/progress.py`

Add `"Vol Context"` to `ProgressCallbackHandler._GRAPH_NODES` set:

```python
_GRAPH_NODES = {
    "Vol Context",         # NEW
    "Market Analyst",
    # ... existing entries unchanged
}
```

### Modified: Backend Schema

File: `api/schemas.py`

```python
class AnalyzeRequest(BaseModel):
    ticker: str
    date: str
    analysts: List[str] = [...]
    # REMOVE: enable_options: bool = False
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-5.2"
    quick_think_llm: str = "gpt-5-mini"

    def config_dict(self) -> Dict[str, Any]:
        cfg = dict(DEFAULT_CONFIG)
        cfg["enable_options"] = True   # always-on — hardcoded
        # ... rest unchanged
```

---

## Frontend Component Changes

### types.ts

| Change | Detail |
|--------|--------|
| Remove `enable_options` from `AnalyzeRequest` | Options always-on |
| Add `vol_context: string` to `AnalysisResult` | Empty string when unavailable |
| Add `*_vol_note` fields to `AnalysisResult` | One per analyst — not displayed yet, in state for future use |
| Remove `optionsOnly?` from `ReportTab` | All tabs always visible |
| Add `group: 'equity' \| 'options' \| 'decision'` to `ReportTab` | Drives section headers |
| Update `REPORT_TABS` assignments | equity: market/technical/social/news/fundamentals; options: volatility/flow/strategy/legs/pricing/greeks; decision: debate/final-decision |
| Update `getNodeList()` — remove parameter | Add `'Vol Context'` as first entry, `OPTIONS_NODES` unconditional |

### ConfigSidebar.tsx

- Remove `enableOptions` state variable
- Remove the "Enable Options Analysis" checkbox block (lines 146-157 in current file)
- Remove `enable_options: enableOptions` from the `onAnalyze` call object
- The `AnalyzeRequest` type change in `types.ts` will surface the missing field as a TypeScript error — fixing it completes the removal

### ReportTabs.tsx

- Remove `enableOptions` prop from `ReportTabsProps`
- Remove `const visibleTabs = REPORT_TABS.filter(t => !t.optionsOnly || enableOptions)` — all tabs always shown
- Add section header rendering between groups: iterate groups in order (`equity` → `options` → `decision`), render a non-interactive label before each group's tabs
- Section labels are styled distinctly from tab buttons (e.g., small uppercase text in muted color, not a button)

### ReportPane.tsx

New props added:

```typescript
interface ReportPaneProps {
  content: string | null;
  status: AnalysisStatus;
  tabLabel?: string;
  volContext?: string | null;    // NEW
  tabGroup?: 'equity' | 'options' | 'decision';  // NEW
}
```

Vol banner renders when `tabGroup === 'equity'` and `volContext` is non-null and non-empty. Banner placement: above the action bar (Copy/Export PDF). Banner behavior:
- Default: expanded on first render (`useState(true)`)
- Collapsed state persisted via `localStorage` key `vol-banner-collapsed`
- Toggle button shows a chevron icon; clicking collapses/expands the narrative text
- Banner header always visible when collapsed (shows "Vol Context" label + toggle)

### App.tsx

- Remove `enableOptions` state and `setEnableOptions` call
- Change `getNodeList(enableOptions)` to `getNodeList()`
- Pass `volContext={state.result?.vol_context ?? null}` to `ReportPane`
- Pass `tabGroup={currentTab?.group}` to `ReportPane`
- Remove `enableOptions` prop from `<ReportTabs />`

---

## Data Flow: Vol Context Through the Pipeline

```
Vol Context node
  reads:  state["company_of_interest"], state["trade_date"]
  calls:  get_options_expirations() → get_options_chain() → get_historical_iv()
  writes: state["vol_context"] = narrative string | None

All 5 Analyst nodes (parallel, run after Vol Context)
  read:   state["vol_context"]
  inject: vol_directive into system message (strength varies per analyst)
          vol_block into system message via prompt.partial (data section)
  write:  state["{analyst}_report"], state["{analyst}_vol_note"]

Bull/Bear Debate, Research Manager, Trader
  vol_context available in state but NOT specially injected
  analyst reports already incorporate vol reasoning — no additional wiring needed

Options - Volatility Analyst (after Trader)
  unchanged — full LLM deep vol analysis
  writes: state["volatility_report"]

Risk Judge
  state["vol_context"] accessible for completeness check
  existing logic unchanged — vol context already threaded through analyst reports
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: LLM Call in Vol Context Node

Vol Context must not invoke an LLM. An LLM call here would:
- Add 3-8 seconds of latency before any analyst starts (all analysts blocked)
- Add LLM cost per run for a task that is purely template assembly
- Create a new LLM failure mode that blocks the entire analyst fan-out

The narrative is assembled from computed metrics using a Python string template. The deep vol interpretation belongs in the existing `Options - Volatility Analyst` which runs after Trader.

### Anti-Pattern 2: Injecting Vol Context into state["messages"]

Prepending a `HumanMessage` to `state["messages"]` would persist through the entire tool-calling loop (analyst → tools → analyst cycles). Each loop iteration would re-read the vol block, potentially confusing the model about context timing. Use `prompt.partial("vol_block", vol_block)` to inject into the prompt template instead — the vol data appears once in the assembled prompt, not in the cycled message history.

### Anti-Pattern 3: Partial enable_options Removal

The `enable_options` flag exists in three places that must all be cleaned:
1. `api/schemas.py` — `AnalyzeRequest.enable_options` field and `config_dict()` passthrough
2. `tradingagents/graph/setup.py` — the `if enable_options:` branching blocks
3. `frontend/src/types.ts` — `AnalyzeRequest.enable_options` interface field

Removing only the frontend checkbox while leaving the backend default `False` would silently disable options on every run. All three must change in Step 5.

### Anti-Pattern 4: Vol Context Positioned After OPTIONS_NODES in getNodeList

`getNodeList()` drives the ProgressStepper count and GlobalStatusBar completion display. Vol Context must be the first entry — it runs before any analyst. Placing it elsewhere in the list causes the stepper to show an out-of-order completion.

---

## Suggested Build Order

### Step 1 — AgentState Extension
**File:** `tradingagents/agents/utils/agent_states.py`
Add `vol_context` (Optional[str]) and 5 `*_vol_note` (str) fields. No behavior change. Safe to land alone.

### Step 2 — Vol Context Node
**File:** `tradingagents/agents/pre_analysis/vol_context.py` (new)
Implement narrative builder using `get_historical_iv()` + `get_options_chain()`. Unit-testable in isolation by mocking dataflow calls. Depends on Step 1 (state field must exist).

### Step 3 — Graph Wiring
**Files:** `tradingagents/graph/setup.py`, `api/progress.py`
Wire Vol Context into graph. Remove `enable_options` branching — options always-on. Add `"Vol Context"` to `_GRAPH_NODES`. Depends on Step 2.

### Step 4 — Analyst Prompt Modifications
**Files:** All 5 analyst files in `tradingagents/agents/analysts/`
Add vol directive + vol data injection per D-09/D-11. Add `vol_note` extraction to return dicts. Depends on Step 3 (Vol Context guaranteed to run before analysts in the graph).

### Step 5 — Backend Schema Cleanup
**File:** `api/schemas.py`
Remove `enable_options` field. Hardcode `True` in `config_dict()`. Depends on Steps 3-4 (options pipeline always present in graph before schema asserts always-on).

### Step 6 — Frontend Types
**File:** `frontend/src/types.ts`
Remove `enable_options` from `AnalyzeRequest`. Add `vol_context` + `*_vol_note` to `AnalysisResult`. Replace `optionsOnly` with `group` on `ReportTab`. Update `REPORT_TABS`. Update `getNodeList()`. Can parallel with Steps 4-5.

### Step 7 — ConfigSidebar Cleanup
**File:** `frontend/src/components/ConfigSidebar.tsx`
Remove checkbox and state. Depends on Step 6 (type change surfaces TypeScript error that confirms what to delete).

### Step 8 — Tab Grouping
**File:** `frontend/src/components/ReportTabs.tsx`
Remove `enableOptions` prop. Add section header rendering between groups. Depends on Step 6.

### Step 9 — Vol Banner
**File:** `frontend/src/components/ReportPane.tsx`
Add `volContext` and `tabGroup` props. Implement collapsible banner with localStorage persistence. Depends on Step 6.

### Step 10 — App.tsx Wiring
**File:** `frontend/src/App.tsx`
Remove `enableOptions` state. Update `getNodeList()` call. Pass `volContext` and `tabGroup` to ReportPane. Remove `enableOptions` from ReportTabs. Depends on Steps 6-9.

### Dependency Summary

```
Step 1 (AgentState)
  └── Step 2 (Vol Context module)
        └── Step 3 (Graph wiring)
              └── Step 4 (Analyst prompts)
                    └── Step 5 (Schema cleanup)

Step 6 (Frontend types) — parallel with Steps 4-5
  ├── Step 7 (ConfigSidebar)
  ├── Step 8 (Tab grouping)
  └── Step 9 (Vol banner)
        └── Step 10 (App.tsx)
```

Backend track (Steps 1-5) and frontend track (Steps 6-10) are independent after Step 5/6 interface agreement (what fields flow through SSE complete event). Both tracks can proceed in parallel once `AnalysisResult` field additions are agreed.

---

## Scalability Considerations

| Concern | Phase 17 Impact |
|---------|-----------------|
| Vol data latency | Vol Context adds at most one uncached fetch (~300ms yfinance). Cache hits add ~5ms. Analysts are not blocked by the LLM — they start immediately after Vol Context writes to state. |
| Parallel fan-out unchanged | All 5 analysts still start simultaneously from Vol Context — same parallelism as current START fan-out. |
| Options pipeline complexity | Removing the conditional branch simplifies `setup_graph()` — fewer code paths, easier to reason about. |
| State size | 6 new string fields (5 vol_note + 1 vol_context) — negligible. |
| Frontend tab rendering | Simplifies from conditional filter to unconditional group render — fewer edge cases. |

---

## Sources

All findings from direct codebase inspection (HIGH confidence — no training data assumptions):

- `tradingagents/graph/setup.py` — graph topology, OPTIONS_NODES, _safe_options_node, enable_options branching
- `tradingagents/agents/utils/agent_states.py` — AgentState TypedDict, _last_value reducer pattern
- `tradingagents/agents/analysts/market_analyst.py` — ChatPromptTemplate + prompt.partial() + tool-calling loop pattern
- `api/progress.py` — ProgressCallbackHandler._GRAPH_NODES, cancel event wiring
- `api/schemas.py` — AnalyzeRequest.enable_options, config_dict() passthrough
- `frontend/src/types.ts` — getNodeList(), REPORT_TABS, ReportTab.optionsOnly, AnalysisResult fields
- `frontend/src/components/ReportTabs.tsx` — enableOptions filter, tab rendering
- `frontend/src/components/ReportPane.tsx` — current prop interface, action bar
- `frontend/src/App.tsx` — enableOptions state, getNodeList call site, component wiring
- `frontend/src/components/ConfigSidebar.tsx` — enableOptions checkbox location and state
- `tradingagents/dataflows/y_finance_options.py` — get_historical_iv(), get_options_chain(), get_options_expirations() — reusable for Vol Context node
- `.planning/phases/17-mandatory-options-vol-aware-analysts/17-CONTEXT.md` — decisions D-01 through D-13
