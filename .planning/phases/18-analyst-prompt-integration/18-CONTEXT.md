# Phase 18: Analyst Prompt Integration - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

All 5 equity analysts receive the vol context narrative in their prompts with per-analyst directive strength. Each analyst produces an auditable `vol_note` field. This phase modifies analyst factory functions and prompt templates only — no graph wiring or frontend changes.

</domain>

<decisions>
## Implementation Decisions

### Prompt structure (from Phase 17 CONTEXT.md D-09)
- Option C hybrid: system message sets directive weight, user message delivers vol data
- `prompt.partial()` for injection — NOT message mutation (avoids polluting tool-calling loop)
- Vol context read from `state["vol_context"]` — if None (fetch failed), omit from prompt entirely

### Narrative directive (from D-10)
- Vol narrative itself contains soft directive: "Consider these conditions when forming your assessment"
- System message adds per-analyst framing on top

### Per-analyst directive strength (from D-11)

| Analyst | Directive Strength | System Message Framing |
|---------|-------------------|----------------------|
| Market | Strong | "Volatility conditions are a primary market signal. Weight them heavily in your analysis." |
| Technical | Moderate | "Use volatility context to confirm or contradict your technical signals." |
| Social | Moderate | "Put/call ratio and unusual flow overlap with sentiment signals. Factor them in." |
| News | Weak | "Reference volatility only if news events are driving the elevated vol." |
| Fundamentals | Weak | "Flag volatility only if IV rank exceeds 90th percentile — otherwise focus on fundamentals." |

### Auditable vol_note output (from D-12)
- Each analyst must produce a `vol_note` field (1 sentence) in their output
- Extracted via regex from analyst response content (same pattern as Trader's JSON extraction)
- Written to `state["vol_note_market"]`, `state["vol_note_technical"]`, etc.
- Nullable for weak-relevance analysts (News, Fundamentals) — but must still attempt extraction
- Pattern: `**Vol Note:** {sentence}` at end of analyst output

### Claude's Discretion
- Exact system message wording (table above is guidance, not verbatim)
- Regex pattern for vol_note extraction
- How to handle extraction failure (default to None, not error)
- Whether to add vol_note to the complete SSE event's serialized state

</decisions>

<specifics>
## Specific Ideas

- Vol note should read like: "Given elevated IV at 78th percentile, this bullish technical setup may already be priced into options premiums."
- The vol_note is for audit trail — it proves the analyst considered vol context, not just received it

</specifics>

<canonical_refs>
## Canonical References

### Analyst factory functions (all 5 need modification)
- `tradingagents/agents/analysts/market_analyst.py` — Market analyst prompt template + output parsing
- `tradingagents/agents/analysts/technical_analyst.py` — Technical analyst
- `tradingagents/agents/analysts/social_media_analyst.py` — Social analyst
- `tradingagents/agents/analysts/news_analyst.py` — News analyst
- `tradingagents/agents/analysts/fundamentals_analyst.py` — Fundamentals analyst

### State contract (from Phase 17)
- `tradingagents/agents/utils/agent_states.py` — `vol_context` and `vol_note_*` fields already declared

### Existing prompt patterns
- `tradingagents/agents/analysts/market_analyst.py` — Reference for ChatPromptTemplate + bind_tools pattern
- `tradingagents/agents/researchers/trader.py` — Reference for regex extraction of structured fields from LLM output

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChatPromptTemplate` with `prompt.partial()` — already used in analyst factories
- Regex extraction pattern from Trader agent — proven pattern for extracting labeled fields from LLM output

### Established Patterns
- Analyst factory: `create_*_analyst(llm)` → returns closure `analyst_node(state) -> dict`
- Tool-calling loop: `prompt | llm.bind_tools(tools)` — vol injection must NOT interfere with this
- State write: analyst returns `{"market_report": content, ...}` — add `"vol_note_market": extracted_note`

### Integration Points
- `state["vol_context"]` — read by each analyst (populated by Vol Context node in Phase 17)
- `state["vol_note_*"]` — written by each analyst (declared in AgentState in Phase 17)

</code_context>

<deferred>
## Deferred Ideas

- Structured output enforcement via function calling for vol_note — defer to future if regex proves unreliable
- Vol regime detection adjusting analyst behavior more dramatically — separate phase

</deferred>

---

*Phase: 18-analyst-prompt-integration*
*Context gathered: 2026-04-09*
