# Feature Research

**Domain:** Vol-aware multi-agent LLM analysis pipeline — mandatory options + volatility context injection
**Researched:** 2026-04-09
**Confidence:** HIGH (codebase verified, domain confirmed from prior milestones and external research)

---

## Context: What Already Exists

This milestone is additive. The existing system already has:

- 5 parallel equity analysts (Market, Technical, Social, News, Fundamentals) writing to `AgentState` keys
- 7 options agents running after Trader in a sequential chain
- `enable_options` toggle in ConfigSidebar that gates both the options pipeline and 7 report tabs
- `REPORT_TABS` with `optionsOnly` flag on 6 tabs; `getNodeList(enableOptions: boolean)` conditional
- `_safe_options_node()` wrapper in `setup.py` for graceful failure isolation
- `AgentState` with per-analyst report keys and 6 options pipeline keys
- `vol_context` field is NOT yet in `AgentState` — new for this milestone

Features below are scoped to what NEW behavior this milestone introduces.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that, once the milestone goal is stated ("vol-aware analysts"), users assume exist. Missing these makes the feature feel broken or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Vol Context pre-fetch node in pipeline | If vol is "always on", every analyst must receive it — a toggle-off state is incoherent | MEDIUM | New graph node before analyst fan-out. Uses existing `get_options_chain()` + `get_historical_iv()`. Must write `vol_context` to `AgentState`. |
| IV rank, IV/HV ratio, P/C ratio, skew in vol narrative | These are the 4 standard metrics every options-informed trader expects in a vol summary (tastytrade, thinkorswim both surface these as a primary unit) | LOW | Computed from already-fetched chain data — no new data calls needed beyond what options pipeline uses |
| Vol narrative as human-readable paragraph | Raw numbers alone (IV=0.38, HV=0.22) are not actionable for an LLM analyst; a briefing-note format is the standard professional idiom | LOW | Example: "IV is at the 78th percentile — options are pricing in significantly more volatility than realized. P/C ratio of 1.3 suggests defensive positioning." |
| Vol context injected into all 5 analyst system prompts | A "vol-aware system" where analysts don't actually see vol context is not vol-aware | MEDIUM | Requires editing 5 analyst factory functions. Hybrid prompt structure (D-09): system message sets directive weight, user message delivers the narrative |
| Per-analyst directive strength (Strong / Moderate / Weak) | Different analysts have different vol relevance; a blanket directive risks making the news analyst over-weight vol on non-vol-driven news days | LOW | Market=Strong, Technical=Moderate, Social=Moderate, News=Weak, Fundamentals=Weak (per D-11). Achieved by varying system message framing text only |
| `vol_note` field in analyst output | Without a structured field, there is no way to audit whether the analyst actually engaged with vol context or ignored it; debate/risk stages have no traceability | MEDIUM | Must be explicitly prompted in each analyst's output instructions. Nullable for Weak-strength analysts (News, Fundamentals) but still solicited. Free-text extraction in this milestone (structured enforcement deferred per D-12) |
| Options always-on (toggle removed) | The milestone explicitly makes options mandatory; a toggle that can disable it contradicts the feature | LOW | Remove `enable_options` from `ConfigSidebar`, `AnalyzeRequest`, `schemas.py` config passthrough. Set always `True` in backend. Four touch-points: ConfigSidebar.tsx, App.tsx, types.ts, schemas.py |
| Vol Context node visible in progress stepper | Named nodes are the system's contract with the user — a silent pre-fetch hides latency and prevents failure visibility | LOW | Add "Vol Context" to node list in `types.ts`. Add to `ProgressCallbackHandler._GRAPH_NODES` in backend. Aligns with D-04 rationale: debuggability + consistent architecture |
| Graceful degradation if vol fetch fails | Tickers without options data (some ETFs, recently listed stocks) must not break the pipeline | LOW | Uses existing `_safe_options_node()` pattern. Failure leaves `vol_context` empty string; analysts fall back to no-vol-context behavior. Risk Judge can weight accordingly per D-05 |

### Differentiators (Competitive Advantage)

Features that go beyond what a user would assume and create genuine analytical edge.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Analyst-role-calibrated directive strength | Prevents over-weighting vol in analysts where it is tertiary (news analyst reading macro when IV spikes for unrelated reasons); creates more coherent cross-analyst reasoning | LOW | System message wording only — no architectural change. E.g., Fundamentals directive: "Flag only if IV rank >90 — extreme vol regimes can distort earnings-based valuations." |
| Soft directive embedded in narrative text | "Consider these conditions when forming your assessment" inside the narrative itself creates a second layer of grounding distinct from the system prompt directive | LOW | Part of vol narrative template. Specified in D-01 and 17-CONTEXT specifics. No extra implementation — wording baked into template |
| Vol banner collapsible at top of every analyst tab | Users can read each analyst's report in the context of the vol conditions that analyst was operating under — analyst reports and vol context become a unified artifact | MEDIUM | Requires `ReportPane.tsx` modification. Vol context string passed as prop. Default: expanded on first view, collapsed on revisit (localStorage key). No new data fetch — reads `vol_context` from `AnalysisResult` |
| Tab grouping with section headers (Equity / Options / Decision) | 13 flat tabs is cognitively expensive; grouped sections match the analyst's mental model of the pipeline stages | LOW | Section header dividers above tab row in `ReportTabs`. CSS-only or minimal React change. `REPORT_TABS` gains a `group` field |
| Traceability from vol narrative to final decision | `vol_note` in each analyst output creates an audit trail: vol narrative → analyst acknowledgment → debate → risk judge → final decision. No published multi-agent trading system reviewed provides this level of within-pipeline auditability | MEDIUM | Requires prompt engineering + output parsing for 5 analysts. Downstream stages (Debate, Risk Judge) inherit traceability via conversation history |
| Pipeline architecture: named pre-fetch node before parallel fan-out | Vol Context runs as a visible named node in the graph, not silent initialization code. Failure is observable and debuggable. Architecture matches the pattern used by peer multi-agent systems (TradingGroup, ATLAS) | LOW | `workflow.add_node("Vol Context", vol_context_node)` + edge before analyst fan-out. Follows existing `add_node` + `add_edge` pattern |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Vol Context as its own report tab | Seems natural — "there's a new node, give it a tab" | Vol context is shared input to analysts, not an analyst output. A tab implies it is a peer to Market Analyst or Volatility Analyst — wrong mental model. Also burns a tab slot when total count is explicitly held at 13 (D-13) | Pin as collapsible banner inside every analyst tab (D-08). Vol context is ambient context, not an output |
| Per-analyst vol narrative (5 different paragraphs, one per analyst) | Seems more "personalized" per analyst | Identical shared narrative is the correct design (D-02): analysts stay connected because they reason from the same facts. Divergent narratives introduce inconsistency in cross-analyst debate and in the Risk Judge synthesis | One narrative paragraph for all 5 analysts; directive strength varies via system message only |
| LLM-generated vol narrative (call an LLM to write the briefing) | LLM might write better prose than a template | Adds a 6th LLM call before analysts even start — latency and cost with no advantage. Vol metrics are deterministic facts; a template is faster, cheaper, deterministic, and easier to debug | Template-computed narrative from structured vol metrics (IV rank, IV/HV, P/C, skew direction) |
| Blocking pipeline on vol fetch failure | "If vol fails, the analysis is incomplete — stop" | Kills analysis for any ticker without clean options data. Degrades UX severely for what is context enrichment, not a critical gate | Non-blocking: empty `vol_context` + Risk Judge flag. Analysts run without vol context; result is still valid equity analysis |
| Structured output enforcement for `vol_note` via function calling | Guarantees the field exists and is well-formed | Adds schema complexity to 5 analysts that currently use free-form tool-calling patterns. High risk of breaking existing output flows in this milestone | Free-text extraction of `vol_note` in this milestone; structured output enforcement deferred explicitly per D-12 in 17-CONTEXT |
| Vol regime classification ("low / normal / elevated / extreme") | Seems like a useful abstraction for analysts | Requires defining thresholds per ticker / sector / VIX regime — non-trivial and highly debatable. A misclassification ("normal" when market views it as "elevated") poisons all 5 analyst prompts simultaneously | IV rank number + soft narrative direction covers the same ground without threshold risk. Regime classification explicitly deferred in 17-CONTEXT deferred items |
| Cross-run vol context cache (reuse vol across multiple ticker runs in a screener sequence) | Efficiency when running screener picks in sequence | Market-wide vol (VIX, sector vol) is reusable but ticker-specific IV rank is not. Mixing them creates staleness bugs. Single-ticker flow does not need this | Per-run fetch with existing `yfinance_cache.py` smart caching (15-min TTL already handles within-session freshness) |

---

## Feature Dependencies

```
[AgentState.vol_context field] (new — prerequisite for all other features)
    └── required by: [Vol Context Node]
    └── required by: [Per-Analyst Vol Directive injection]
    └── required by: [Vol Banner in ReportPane]

[Vol Context Node]
    └── requires: [AgentState.vol_context field]
    └── requires: [get_options_chain() + get_historical_iv()] (already exist)
    └── requires: [_safe_options_node() wrapper] (already exists — reuse pattern)
    └── enables: [Per-Analyst Vol Directive injection]
    └── enables: [ProgressStepper "Vol Context" node]

[Per-Analyst Vol Directive injection] (all 5 analysts)
    └── requires: [Vol Context Node] (must run first)
    └── requires: [vol_context in AgentState] (must be populated)
    └── enables: [vol_note field in analyst output]

[vol_note field in analyst output]
    └── requires: [Per-Analyst Vol Directive injection] (analysts must be prompted for it)
    └── enhances: [Debate/Risk Judge stages] (traceability benefit — implicit via conversation history)

[Always-On Options — toggle removal]
    └── conflicts with: [getNodeList(enableOptions)] (must be simplified — remove param)
    └── conflicts with: [REPORT_TABS optionsOnly flag] (must be removed)
    └── requires: [Remove enable_options from ConfigSidebar, App.tsx, types.ts, schemas.py]

[Tab Grouping (Equity / Options / Decision)]
    └── requires: [Always-On Options] (grouping only makes sense when all 13 tabs are always present)
    └── enhances: [Vol Banner] (visual coherence — banner + grouping together)

[Vol Banner in ReportPane]
    └── requires: [vol_context in AnalysisResult type] (new field exposed via SSE complete event)
    └── requires: [Vol Context Node] (must produce the string)
    └── enhances: [Tab Grouping] (context visible alongside each section)

[ProgressStepper "Vol Context" node]
    └── requires: [Vol Context Node registered in graph]
    └── requires: [getNodeList() updated] (always includes "Vol Context", not conditional)

[vol_context in AnalysisResult + SSE payload]
    └── requires: [Vol Context Node writes to AgentState.vol_context]
    └── required by: [Vol Banner in ReportPane]
```

### Dependency Notes

- **AgentState.vol_context is the root prerequisite.** The new field must exist in `agent_states.py` before Vol Context node can write to it, and before any analyst can read from it. This change should be done first in implementation ordering.
- **Vol Context Node must run before analyst fan-out.** LangGraph topology: `START → Vol Context → [Market, Technical, Social, News, Fundamentals parallel] → ...`. Edge ordering in `setup.py` enforces this.
- **Always-On Options is a prerequisite for Tab Grouping.** Grouping tabs into Equity / Options / Decision sections only makes visual sense when all 13 tabs are always present. Do not add grouping while the toggle still exists.
- **optionsOnly flag removal is a simplification, not a risk.** The `optionsOnly` conditional in `REPORT_TABS` and `getNodeList(enableOptions)` disappears. Frontend becomes simpler. No new logic introduced.

---

## MVP Definition

This milestone is a single deliverable, not a product launch. "MVP" here means the minimum implementation that fully delivers the stated milestone goal.

### Launch With (this milestone — all P1)

- [ ] `AgentState.vol_context` field added to `agent_states.py`
- [ ] Vol Context graph node — pre-fetch IV rank, IV/HV, P/C ratio, skew; write narrative to `vol_context`
- [ ] "Vol Context" added to node list in `types.ts` (always-present, not conditional) and to backend `ProgressCallbackHandler._GRAPH_NODES`
- [ ] All 5 analyst system prompts updated with vol directive (directive strength calibrated per D-11 table)
- [ ] `vol_note` field solicited in analyst prompt outputs (free-text extraction, not enforced structured output)
- [ ] `enable_options` toggle removed from ConfigSidebar.tsx, App.tsx, types.ts, schemas.py
- [ ] `REPORT_TABS` `optionsOnly` flags removed; `getNodeList()` simplified to always include OPTIONS_NODES
- [ ] Tab grouping section headers (Equity / Options / Decision) in ReportTabs component
- [ ] Collapsible vol context banner in ReportPane (reads `vol_context` from `AnalysisResult`)
- [ ] `vol_context` exposed in `AnalysisResult` type (TypeScript) and SSE complete event payload

### Add After Validation (follow-on)

- [ ] Structured output enforcement for `vol_note` (function calling / Pydantic schema) — add when free-text extraction proves unreliable across LLM providers
- [ ] Vol note values surfaced in Debate/Risk Judge tab UI alongside each analyst's acknowledgment — adds auditability visualization

### Future Consideration (v2+)

- [ ] Vol regime classification ("low / normal / elevated / extreme") with per-regime analyst behavior adjustment — requires threshold research and A/B validation
- [ ] Cross-run vol context cache for multi-ticker screener sequences — only valuable once bulk analysis mode is added
- [ ] Vol narrative comparison across tickers in track record dashboard — meaningful only with sufficient trade history

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `AgentState.vol_context` field | HIGH | LOW | P1 |
| Vol Context node (pre-fetch + narrative compute) | HIGH | MEDIUM | P1 |
| ProgressStepper "Vol Context" node (frontend + backend) | MEDIUM | LOW | P1 |
| Per-analyst prompt injection (all 5 analysts) | HIGH | MEDIUM | P1 |
| Directive strength calibration (Strong / Moderate / Weak) | HIGH | LOW | P1 |
| `vol_note` field solicited in analyst outputs | MEDIUM | LOW | P1 |
| Always-on options — toggle removal (4 touch-points) | HIGH | LOW | P1 |
| `getNodeList()` simplification (remove enableOptions param) | MEDIUM | LOW | P1 |
| `REPORT_TABS` optionsOnly flag removal | MEDIUM | LOW | P1 |
| Tab grouping (Equity / Options / Decision headers) | MEDIUM | LOW | P1 |
| Collapsible vol banner in ReportPane | MEDIUM | MEDIUM | P1 |
| `vol_context` in AnalysisResult type + SSE payload | HIGH | LOW | P1 |
| Structured output enforcement for `vol_note` | MEDIUM | HIGH | P2 |
| Vol note values in Debate/Risk Judge UI | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for milestone — all P1 items together constitute the complete milestone
- P2: Add after validation of free-text approach
- P3: Nice to have, future consideration

---

## Domain Context: How Vol-Aware Multi-Agent Systems Work

Based on research into current multi-agent LLM trading systems (TradingGroup 2025, ATLAS 2026, QuantAgent 2025):

**Shared pre-computation before parallel agents is the established pattern.** Pre-computing market regime context before specialist agents run is accepted in academic multi-agent trading systems. TradingGroup injects volatility coefficients computed from 10-day HV into per-agent take-profit thresholds before parallel agents execute. ATLAS uses ATR as a shared input that conditions all agent behavior under volatile regimes. The "Vol Context node before parallel analyst fan-out" architecture (D-03) matches this consensus.

**Narrative format outperforms raw numbers for LLM consumption.** Published systems and professional platforms (tastytrade IVx summary, thinkorswim vol scan) both present vol as a narrative summary, not a raw float dump. The briefing-note format specified in 17-CONTEXT matches what LLMs reason best from.

**Role-calibrated directive strength is not standard in published research — this is a genuine differentiator.** Published systems inject a single vol signal uniformly across all agents. Per-analyst directive strength calibrated to relevance (Market=Strong, News=Weak) is above current SOTA and is the primary architectural differentiator of this milestone.

**Professional platforms surface IV rank as a prominently-displayed ambient indicator.** tastytrade pins IV rank alongside every options chain view; thinkorswim exposes it as a watchlist column always visible during analysis. The collapsible vol banner pinned at the top of every analyst tab mirrors this convention: vol context is ambient and always accessible, not buried in a sub-menu.

**`vol_note` field for auditability reflects emerging best practice in financial multi-agent systems.** 2025 research on role-based multi-agent financial pipelines highlights per-agent decision logging and episodic verbal memory as key for compliance and audit trails. The `vol_note` field implements the same principle at individual analyst output level — making it possible to trace whether a bullish Market Analyst actually engaged with elevated IV or reasoned around it.

---

## Sources

- 17-CONTEXT.md (codebase, 2026-04-09) — All implementation decisions D-01 through D-13. Primary source, HIGH confidence.
- `frontend/src/types.ts` (codebase) — Existing REPORT_TABS, getNodeList, AnalysisResult. Verified current state.
- `tradingagents/agents/utils/agent_states.py` (codebase) — AgentState schema. Verified current state.
- `tradingagents/graph/setup.py` (codebase) — `_safe_options_node`, OPTIONS_NODES, GraphSetup. Verified current state.
- `tradingagents/agents/analysts/market_analyst.py` (codebase) — Analyst prompt structure. Verified current state.
- TradingGroup (August 2025): https://arxiv.org/html/2508.17565v1 — vol coefficient injection pattern before parallel agents
- ATLAS (January 2026): https://arxiv.org/html/2510.15949v2 — ATR-based shared vol context across agents, sentiment+technical stability under vol
- QuantAgent (September 2025): https://arxiv.org/html/2509.09995v3 — RiskAgent vol integration pattern
- tastytrade volatility metrics help: https://support.tastytrade.com/support/s/solutions/articles/43000539059 — IV rank, IVx, HV professional presentation conventions (MEDIUM confidence — official docs)
- Role-based multi-agent LLM evaluation (FinNLP 2025): https://aclanthology.org/2025.finnlp-2.19.pdf — auditability and episodic verbal memory patterns (MEDIUM confidence)

---

*Feature research for: vol-aware multi-agent analysis pipeline (Phase 17)*
*Researched: 2026-04-09*
