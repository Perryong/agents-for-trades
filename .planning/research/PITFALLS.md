# Pitfalls Research — Vol-Aware Context Injection into Multi-Agent LLM Pipeline

**Domain:** Adding volatility pre-processing and mandatory options to an existing LangGraph multi-agent analysis system
**Researched:** 2026-04-09
**Confidence:** HIGH (codebase-derived), MEDIUM (LLM prompt-anchoring behavior)
**Context:** Phase 17 of the TradingAgents system. Adding a Vol Context pre-processing node before 5 parallel equity analysts, mandatory `vol_note` output field, removing `enable_options` toggle, and restructuring frontend tabs. Based on direct codebase inspection of `setup.py`, `agent_states.py`, `y_finance_options.py`, `ConfigSidebar.tsx`, `types.ts`, and `App.tsx`.

---

## Critical Pitfalls

---

### Pitfall 1: Vol Context Node Changes Fan-Out Source — Breaks START-to-Analyst Edge Wiring

**What goes wrong:**
The current graph wires `START` directly to all 5 equity analysts in parallel via `workflow.add_conditional_edges(START, route_equity_start, equity_entries)`. When the Vol Context node is inserted before the analysts, `START` must connect to `Vol Context` and `Vol Context` must fan-out to the analysts. If the developer adds the Vol Context node but forgets to change the START edge origin, both `START → Vol Context` AND `START → [5 analysts]` edges exist simultaneously. LangGraph will then run the Vol Context node AND fan-out to analysts from START in the same tick — the analysts fire before vol context is ready, so `state["vol_context"]` is `None` or missing when they read it.

**Why it happens:**
The `route_equity_start` function and `workflow.add_conditional_edges(START, ...)` call are co-located in `setup_graph()`. It is easy to add `workflow.add_node("Vol Context", ...)` and a new fan-out from `Vol Context` without removing or replacing the existing START conditional edge. Python does not error on duplicate edge definitions in LangGraph — it silently accepts both.

**How to avoid:**
Replace the `workflow.add_conditional_edges(START, route_equity_start, equity_entries)` call entirely. The new flow is:
1. `workflow.add_edge(START, "Vol Context")` — sequential, single entry point
2. A new `route_after_vol_context` conditional edge from `"Vol Context"` that fans out to all equity entries

Do not add the Vol Context node without simultaneously removing the `START → analysts` conditional edge. Treat this as a single atomic replacement, not an additive change.

**Warning signs:**
- Analysts produce reports without any vol context despite Vol Context node appearing in the progress stepper
- `state["vol_context"]` is `None` inside an analyst that ran successfully
- LangGraph graph visualization shows two paths from START (if you dump the graph structure)
- Progress stepper shows "Vol Context" completing simultaneously with the first analyst node, not before it

**Phase to address:** Vol Context graph node implementation — first task before any prompt changes.

---

### Pitfall 2: Vol Context Node Blocking Behavior Adds Latency Multiplied by Every Run

**What goes wrong:**
Inserting a synchronous network-bound node (yfinance options data fetch) before all 5 parallel analysts means every single analysis run now has an added sequential blocking step. The yfinance options chain fetch and historical IV fetch can take 2-5 seconds each under normal load, and 10-15 seconds on rate-limit or slow network. Previously, the 5 analysts fired immediately. Now every run is delayed by this pre-fetch regardless of whether the vol data is useful to the specific ticker being analyzed (e.g., a ticker with no options chain).

**Why it happens:**
The decision to make Vol Context a named graph node (D-03, D-04) is correct for debuggability, but the data fetching inside it is synchronous. `get_options_chain()` and `get_historical_iv()` from `y_finance_options.py` call `yf.Ticker(symbol).option_chain(exp)` — blocking HTTP calls with no async support. The caching layer (`yfinance_cache.py`) helps on repeat calls but not on first runs.

**How to avoid:**
- Vol Context must use `get_cached_text()` with the existing `yfinance_cache.py` cache layer for both IV and chain data — never bypass the cache.
- Implement the non-blocking failure mode from D-05 immediately: if any data fetch raises an exception or returns an empty result, set `state["vol_context"] = None` and proceed. Never let the Vol Context node block indefinitely.
- Set an explicit timeout on the data fetches (e.g., `signal.alarm` on Unix or `concurrent.futures.ThreadPoolExecutor` with `timeout=` kwarg on Windows) to cap the worst case at ~8 seconds.
- Validate against the cache-hit path: on second run of same ticker within 30 minutes, Vol Context should complete in under 200ms.

**Warning signs:**
- Analysis runs that previously completed in 90s now consistently take 100-110s for first run of a ticker
- Progress stepper shows "Vol Context" stuck for >10 seconds on any run
- After-hours runs are slower than market-hours runs for the same ticker (cache not populated after market close)

**Phase to address:** Vol Context node implementation — wrap all data fetches in try/except with timeout before wiring into graph.

---

### Pitfall 3: After-Hours Vol Summary Computes Zeros for IV/Bid/Ask — Produces Misleading Narratives

**What goes wrong:**
After market hours, yfinance returns options chain data where most contracts have `bid=0`, `ask=0`, `volume=0`, and `impliedVolatility` near zero (e.g., `0.00001`). The existing `get_options_chain()` already handles this with the `_has_live_quotes()` quality check and an `is_good` validator that keeps the last market-hours cache rather than overwriting with after-hours zeros. However, when building the vol narrative for the Vol Context node, the developer may write new data-extraction logic that reads directly from a fresh yfinance fetch rather than going through `get_cached_text()` with the `is_good` guard. This produces a narrative like "IV rank: 2%, P/C ratio: 0.0, skew: flat" which is technically the after-hours data, not the true vol picture.

**Why it happens:**
The developer building the vol summary computation is different from whoever built the caching layer. The existing `_has_live_quotes()` guard and `is_good` pattern are not obvious — they're buried in `y_finance_options.py`. It is tempting to write a new `compute_vol_summary()` function that calls `yf.Ticker(symbol).option_chain(exp)` directly for speed, bypassing the cache.

**How to avoid:**
- Vol summary data extraction must go through `get_cached_text()` (or `get_options_chain()` which already wraps it), never directly through `yf.Ticker().option_chain()`.
- Before computing P/C ratio and skew, validate bid/ask quality the same way `_has_live_quotes()` does: require at least 10% of rows have non-zero bid or ask. If the chain fails this check, the narrative should say "Vol data unavailable (after-hours)" rather than fabricating a false zero-vol reading.
- When `get_historical_iv()` returns all near-zero IVs, detect this as an after-hours artifact: if median IV across all expirations is below `MIN_IV_THRESHOLD` (0.005), treat as missing data.
- Test the Vol Context node explicitly during after-hours (e.g., Saturday morning run) and verify the narrative reads "vol data unavailable" rather than "IV rank: 0%".

**Warning signs:**
- Vol narrative generated after market close shows "IV rank: 0-3%" or "P/C ratio: 0.0" for a normally liquid ticker
- Analysts receiving the vol context report "low volatility environment" for a ticker mid-earnings-cycle
- Cache directory shows a fresh write to `yfinance_options_chain-*.txt` after hours that is much smaller than the market-hours version (few non-zero rows)

**Phase to address:** Vol Context node implementation — validate data quality before narrative generation.

---

### Pitfall 4: Prompt Anchoring — All Analysts Over-Weight Volatility, Analysis Diversity Collapses

**What goes wrong:**
When all 5 analysts receive the same vol context paragraph with directive phrases like "weight heavily" or "consider these conditions when forming your assessment," the LLM has a strong completion pressure to reference and agree with the vol narrative. This is especially acute for high-IV scenarios: if the narrative says "IV is elevated at the 78th percentile — options are pricing in significantly more volatility," all 5 analysts may independently conclude "therefore we should be cautious / reduce exposure" — producing a false consensus. The Bull Researcher then has little genuine bullish material to work with because all 5 upstream reports skewed cautious. The debate collapses toward a single view, defeating the purpose of multi-agent diverse analysis.

**Why it happens:**
LLMs are trained to be helpful and consistent. When given context prefixed with a directive, they treat it as instruction rather than information. Injecting the same directive-laden paragraph into every analyst's system message creates artificial correlation across what should be independent analytical views.

**How to avoid:**
- The directive in the narrative itself must be **informational only** — factual data, no normative guidance ("IV rank is 78" not "IV is high and you should be cautious").
- Per-analyst directive strength (D-11) should be carried in the **system message framing**, not repeated in the narrative. The framing for Fundamentals (Weak) should be: "Note: current options pricing shows elevated IV. Flag this only if it materially changes your fundamental view." Not "consider these conditions heavily."
- The News and Fundamentals analysts (Weak relevance) should receive vol context in a separate, clearly demarcated section at the end of their prompt with an explicit instruction that their primary job remains their core domain analysis.
- After implementation, manually run 3 back-to-back analyses on the same ticker and compare analyst reports. If all 5 analysts reach the same directional conclusion in the same language, anchoring has occurred.
- The `vol_note` field requirement reinforces anchoring if analysts feel they must justify their view against vol. Keep the `vol_note` as "what I noticed about vol conditions" not "how vol changed my conclusion."

**Warning signs:**
- All 5 analyst reports contain the phrase "given the elevated implied volatility" or similar
- Bull Researcher cannot find bullish material when IV is high, regardless of fundamentals
- Risk debate is shorter than usual (less disagreement = false consensus from anchoring)
- Removing vol context from one run and comparing — if the directional conclusions are identical, vol context added no information

**Phase to address:** Analyst prompt integration — review per-analyst directive wording explicitly before wiring all 5 prompts.

---

### Pitfall 5: `vol_note` Field Silently Missing — Structured Output Extraction Fails Quietly

**What goes wrong:**
D-12 requires analysts to produce a `vol_note` field. If this is implemented as free-text extraction (the deferred option from D-12) using regex or string parsing on the analyst's prose output, the extraction will silently fail whenever the LLM produces a response that doesn't match the expected format. The `market_report` is currently populated from `result.content` only when `len(result.tool_calls) == 0`. Bolting a `vol_note` extraction onto this path via regex ("look for `Vol Note:` prefix") will fail whenever the LLM uses different phrasing ("Volatility Note:", "Regarding implied volatility:", etc.). The field will be `None` and downstream auditability is lost without any error.

**Why it happens:**
Analysts are tool-calling agents — their final message is a natural language report, not a structured output. The current pattern extracts `report = result.content` verbatim. Adding field extraction on top of this is fragile because LLMs do not reliably follow formatting instructions in long tool-calling conversations.

**How to avoid:**
Option A (recommended for this phase): Add a simple **post-processing extraction** function that uses multiple fallback patterns: try `"Vol Note:"`, then `"Volatility Note:"`, then `"vol_note:"`, then extract the last sentence of the report that mentions "IV" or "volatility." If all fail, set `vol_note = "[not extracted]"` and log a warning — never raise an exception.

Option B (robust, deferred as noted in 17-CONTEXT.md): Enforce via structured output / function calling. Add a `with_structured_output(AnalystOutput)` wrapper where `AnalystOutput` is a Pydantic model with `report: str` and `vol_note: Optional[str]`. The LLM is reliably instructed to return JSON. This requires prompt changes to all 5 analysts. Defer to a follow-up phase if timeline is tight.

Do NOT leave `vol_note` extraction as "we'll add it later" — the field must be populated (even with a fallback sentinel) or the Debate/Risk Judge auditability rationale from D-12 is void.

**Warning signs:**
- `state["vol_note_market"]` (or equivalent) is `None` or missing in the final state
- Inconsistent: sometimes the field is present, sometimes not, across different LLM providers
- Risk Judge references "market analyst's volatility note" but the note is empty
- The auditability feature appears in the UI but shows blank for most runs

**Phase to address:** Analyst prompt integration — implement extraction with fallback before connecting to AgentState.

---

### Pitfall 6: Removing `enable_options` Toggle Creates a Cascade of Stale References

**What goes wrong:**
`enable_options` currently threads through 6 locations: `ConfigSidebar.tsx` state, `handleAnalyze()` in `App.tsx`, `AnalyzeRequest` interface in `types.ts`, `getNodeList(enableOptions)` call in `App.tsx`, `ProgressStepper` props, `ReportTabs` component, and `api/schemas.py` backend. If the developer removes the toggle from the UI but does not update all 6 locations, TypeScript will catch some issues at compile time (if the prop is removed from the interface) but not others (if `enableOptions` state still exists in `App.tsx` but is hardcoded to `false`, the `getNodeList()` call will omit all OPTIONS_NODES from the progress counter — the Vol Context node will appear to never complete).

**Why it happens:**
The `enable_options` boolean was designed as an end-to-end feature gate. Removing a feature gate is architecturally simple in concept but requires touching every consumption point. The React pattern of passing `enableOptions` as props through the component tree means there is no single place to change — it must be traced from state declaration through every prop chain.

**How to avoid:**
Execute removal as a single PR with this specific order:
1. `api/schemas.py` — change `enable_options` default to `True`, make it a constant (not a field). Or remove and always pass `True` in `config_dict()`.
2. `tradingagents/graph/setup.py` — remove `cfg.get("enable_options", False)` conditional; options nodes always added.
3. `types.ts` — update `getNodeList()` to remove the `enableOptions` parameter; always include `OPTIONS_NODES`. Remove `optionsOnly` flag from `REPORT_TABS`.
4. `App.tsx` — remove `enableOptions` state, update `getNodeList()` call, update all component props that pass `enableOptions`.
5. `ConfigSidebar.tsx` — remove the toggle checkbox and the `enableOptions` state field.
6. `ProgressStepper` and `ReportTabs` — remove the `enableOptions` prop.

Run `tsc --noEmit` after each file change. Any remaining `enableOptions` reference is a missed location.

**Warning signs:**
- Progress stepper shows OPTIONS_NODES but the total count is wrong (getNodeList still passed `false` somewhere)
- Options report tabs are missing after removing `optionsOnly` filtering
- Backend still receives `enable_options: false` from frontend (stale `AnalyzeRequest` interface)
- TypeScript compiles but options report tabs are absent at runtime

**Phase to address:** Frontend toggle removal — dedicated task before any tab restructuring.

---

### Pitfall 7: `AgentState` Missing `vol_context` Field Causes LangGraph Fan-Out Merge Errors

**What goes wrong:**
LangGraph's fan-in merge requires that every key written by any parallel branch has a defined reducer in `AgentState`. When the Vol Context node writes `state["vol_context"]` and all 5 analysts then read it (but don't write it), there is no reducer conflict. However, if the `vol_context` key is not declared in `AgentState` (the TypedDict), LangGraph may not merge it correctly across the fan-in point, depending on version behavior. More critically, if `vol_note` fields are added per-analyst (e.g., `vol_note_market`, `vol_note_technical`) without `_last_value` reducers, LangGraph will raise a `ValueError` at graph compile time about missing reducers for keys that multiple branches might write.

**Why it happens:**
`AgentState` currently uses `Annotated[str, _last_value]` for all report fields. The `_last_value` reducer is explicitly defined to handle concurrent writes from parallel branches. Any new field added without an `Annotated[..., _last_value]` wrapper will fail during parallel fan-in if more than one branch writes to it. The `vol_context` field (written only by Vol Context node) is safe without a reducer, but `vol_note_*` fields per analyst need reducers even though each analyst writes to its own key.

**How to avoid:**
Add all new fields to `AgentState` with `Annotated[str, _last_value]` reducers:
```python
# In agent_states.py
vol_context: Annotated[Optional[str], _last_value]  # written once by Vol Context node
vol_note_market: Annotated[Optional[str], _last_value]
vol_note_technical: Annotated[Optional[str], _last_value]
vol_note_social: Annotated[Optional[str], _last_value]
vol_note_news: Annotated[Optional[str], _last_value]
vol_note_fundamentals: Annotated[Optional[str], _last_value]
```
Do this **before** writing any node that reads or writes these fields. LangGraph validates the state schema at `workflow.compile()` time — compile the graph once after adding state fields to catch missing reducers early.

**Warning signs:**
- `ValueError: No reducer found for key "vol_context"` at graph compile time
- Graph compiles but `vol_context` is None in analyst nodes despite Vol Context node running successfully
- Intermittent `KeyError: 'vol_context'` during the fan-in phase when analysts complete

**Phase to address:** AgentState extension — first task, before Vol Context node implementation.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Free-text `vol_note` extraction via regex | No prompt restructuring needed | Silent extraction failures; auditability is illusory | Only in Phase 17 if structured output is deferred — must log when extraction fails |
| Single shared vol narrative for all analysts | Simple implementation | Anchoring risk (Pitfall 4); no per-analyst filtering of irrelevant data | Acceptable for Phase 17 with weak-directive framing for News/Fundamentals |
| Hardcode `enable_options = True` in `config_dict()` rather than removing the field entirely | Minimal backend change | `enable_options` remains in `AnalyzeRequest` schema, confusing future developers | Never — remove the field cleanly |
| Skip the `is_good` quality check when computing vol summary | Faster implementation | After-hours zeros produce misleading narratives (Pitfall 3) | Never |
| Add Vol Context node without removing START→analysts edge | Simpler diff | Analysts run before vol context is ready (Pitfall 1) | Never |

---

## Integration Gotchas

Common mistakes when connecting the Vol Context node into the existing pipeline.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| yfinance options data for IV rank | Fresh fetch on every run to get current data | Use `get_cached_text()` with `is_good=_has_live_quotes` — cache persists market-hours data through after-hours runs |
| LangGraph `add_conditional_edges` for fan-out | Adding new fan-out without removing existing START fan-out | Replace START edge entirely; one edge origin per source node |
| `AgentState` new fields | Adding fields after node implementation | Add all new state fields with reducers before writing any node |
| Analyst prompt modification | Modifying system message string after chain is bound | The chain is compiled at factory call time; rebuild the prompt template cleanly rather than patching strings |
| `getNodeList()` in types.ts | Passing hardcoded `true` to `getNodeList(true)` as a quick fix | Update the function signature to remove the parameter entirely |
| Backend `config_dict()` | Leaving `enable_options` as a passthrough field | Set to constant `True` in `config_dict()` and remove from `AnalyzeRequest` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous yfinance fetch in Vol Context node | First run of each unique ticker takes 5-15s longer than before | Enforce timeout on data fetches; rely on cache for repeat runs | Every first run of every ticker |
| Computing IV rank from multiple expiration fetches | Vol Context node takes 20-30s because it fetches all expiration chains | Compute IV rank from `get_historical_iv()` only (one fetch with 6h cache) — never loop over all expirations in the hot path | Always — never fetch all chains at runtime |
| Vol narrative appended directly to `messages` list | Messages list grows by ~500 tokens per analyst call as vol context is carried through every tool-calling round | Pass vol context via state field (`state["vol_context"]`), not via message history | After 3+ tool call rounds per analyst — each round sends full message history |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Vol Context banner defaults to expanded on every tab switch | Banner takes vertical space and obscures analyst report content on every navigation | Remember collapsed/expanded preference in component state, not localStorage — persists for the session but resets on new analysis |
| Removing options toggle without communicating the change | Users who previously ran equity-only analysis now always get the longer options pipeline run | Add a one-time notice in the progress area: "Options analysis is now always included" |
| Tab group section headers ("Equity / Options / Decision") added without adjusting tab row width | Tab row overflows horizontally on laptop-width displays | Test at 1280px width — if tabs overflow, implement horizontal scroll or reduce tab padding |
| Vol Context tab shown in progress stepper but with no report tab | User clicks "Vol Context" in the stepper expecting to see a tab, but there is no content tab for it (it's shown in the collapsible banner instead) | Vol Context must NOT appear as a clickable stepper node that implies a report exists; it should appear as a non-clickable status indicator or use a distinct visual treatment |

---

## "Looks Done But Isn't" Checklist

- [ ] **Vol Context node:** Verify `state["vol_context"]` is populated with real data (not None) for a liquid ticker at market hours before wiring analyst prompts.
- [ ] **After-hours data quality:** Run the Vol Context node manually on a Saturday — verify the narrative says "data unavailable" not "IV rank: 0%".
- [ ] **Fan-out ordering:** Verify in LangGraph event stream that `node_end` for `Vol Context` appears before any `node_start` for equity analysts — if analysts start simultaneously with Vol Context, the edge wiring is wrong.
- [ ] **vol_note extraction:** Run all 5 analysts and verify `vol_note_*` fields are non-empty in `AgentState` final state for at least 3 consecutive runs.
- [ ] **enable_options removal:** Run `grep -r "enable_options" frontend/src/` after removal — must return zero results.
- [ ] **Options pipeline always runs:** Submit an analysis request without the old toggle and verify the backend graph includes all OPTIONS_NODES in the compiled graph (check LangGraph graph node list at startup).
- [ ] **Progress stepper node count:** Verify `getNodeList()` returns the correct count including "Vol Context" and all OPTIONS_NODES without duplication.
- [ ] **Anchoring sanity check:** Run the same ticker with and without vol context injected. If the directional conclusion is identical and analysts use identical phrasing, anchoring has occurred and directive wording must be softened.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Fan-out wiring bug (Pitfall 1) | LOW | Fix edge wiring in `setup.py`, recompile graph, re-run — no state migration needed |
| After-hours zeros in narrative (Pitfall 3) | LOW | Add `is_good` guard to vol summary fetcher, clear affected cache files, re-run |
| Prompt anchoring discovered post-ship (Pitfall 4) | MEDIUM | Rewrite per-analyst directive wording; no graph changes needed; test with 5 back-to-back runs |
| `vol_note` silently missing (Pitfall 5) | LOW | Add fallback extraction chain; re-run does not require any state migration |
| Stale `enable_options` references (Pitfall 6) | MEDIUM | Systematic grep + TypeScript compile pass; requires touching 6 files but no data migration |
| Missing AgentState reducers (Pitfall 7) | LOW | Add fields to `agent_states.py`, graph fails to compile until fixed — caught at startup |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Fan-out edge wiring (Pitfall 1) | Vol Context node implementation — graph wiring task | Run LangGraph event stream and confirm `Vol Context node_end` precedes all `analyst node_start` events |
| Blocking latency (Pitfall 2) | Vol Context node implementation — data fetching task | Benchmark first-run and cache-hit run durations; cache-hit must be under 200ms |
| After-hours zeros (Pitfall 3) | Vol Context node implementation — data quality task | Saturday morning test run; narrative must show "unavailable" not zeros |
| Prompt anchoring (Pitfall 4) | Analyst prompt integration — directive wording review | Compare 3 runs with vol context vs 3 without; directional diversity must be preserved |
| vol_note silent failure (Pitfall 5) | Analyst prompt integration — field extraction task | Verify non-None vol_note fields in final AgentState for 5 consecutive runs across 2 LLM providers |
| enable_options cascade (Pitfall 6) | Frontend toggle removal — dedicated cleanup task | `grep -r "enable_options" frontend/src/` returns zero; TypeScript compile clean |
| AgentState missing reducers (Pitfall 7) | AgentState extension — first task before any node code | Graph compiles at startup without ValueError; vol_context readable in all analyst nodes |

---

## Sources

- Direct codebase inspection: `tradingagents/graph/setup.py` (fan-out wiring, options node registration)
- Direct codebase inspection: `tradingagents/agents/utils/agent_states.py` (reducer pattern, `_last_value`)
- Direct codebase inspection: `tradingagents/dataflows/y_finance_options.py` (`_has_live_quotes`, `MIN_IV_THRESHOLD`, after-hours zero behavior)
- Direct codebase inspection: `tradingagents/dataflows/yfinance_cache.py` (`is_good` pattern, cache quality guard)
- Direct codebase inspection: `tradingagents/agents/analysts/market_analyst.py` (current prompt structure, `result.content` extraction pattern)
- Direct codebase inspection: `frontend/src/types.ts` (`getNodeList(enableOptions)` signature, `optionsOnly` flag pattern, REPORT_TABS)
- Direct codebase inspection: `frontend/src/App.tsx` (`enableOptions` state threading through 6 locations)
- Direct codebase inspection: `frontend/src/components/ConfigSidebar.tsx` (toggle location, `handleAnalyze` payload)
- Direct codebase inspection: `api/schemas.py` (`enable_options` in `config_dict()`, backend propagation)
- Phase 17 context decisions: `.planning/phases/17-mandatory-options-vol-aware-analysts/17-CONTEXT.md` (D-01 through D-13)

---
*Pitfalls research for: Vol-aware multi-agent LLM pipeline (Phase 17 — Mandatory Options & Vol-Aware Analysts)*
*Researched: 2026-04-09*
