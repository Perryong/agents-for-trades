# Phase 9: LLM Screener Agent - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the LLM screener agent that takes pre-filtered candidates from Phase 8's data layer and returns ranked top picks with rationale. This phase delivers the agent module only — no API endpoint, no frontend, no CLI.

</domain>

<decisions>
## Implementation Decisions

### Agent Architecture
- Use JSON mode with Pydantic validation for structured LLM output — prompt asks for JSON array, parse with `ScreenerResult.model_validate()`
- Handle malformed LLM responses by retrying once with stricter prompt, then returning partial results with error flag for graceful degradation
- Single-shot prompt with all candidates (≤50) plus scoring rubric — keeps token count manageable
- Pass pre-summarized metrics per ticker (score, volume ratio, momentum, sector) to the LLM, not raw DataFrames

### ScreenerResult Data Model
- Configurable number of picks, default 5, hard cap at 10
- Confidence scale: 0.0-1.0 float
- Key metrics per pick: volume_ratio, momentum_5d, sector, market_cap
- ScreenerResult includes metadata: screened_at timestamp, candidate_count, model_used

### Isolation & Integration
- Agent lives in `tradingagents/agents/screener/screener_agent.py` — new subdirectory consistent with `agents/options/`, `agents/analysts/` pattern
- AgentState isolation enforced via validation at `run_screener()` entry — raise TypeError if ScreenerResult passed to pipeline (per RANK-03)
- Import `get_screener_signals` from `screener_data.py` directly for data integration (not via route_to_vendor)

### Claude's Discretion
- Exact prompt wording and scoring rubric content
- LLM temperature setting for ranking
- Internal helper function organization

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/agents/analysts/*.py` — `create_*` factory pattern returning closures
- `tradingagents/dataflows/screener_data.py` — `get_screener_signals()`, `ScreenerCandidate` model (Phase 8 output)
- `tradingagents/default_config.py` — `quick_thinking_llm` / `deep_thinking_llm` config
- `tradingagents/llm_clients/factory.py` — `create_llm_client()` for LLM instantiation

### Established Patterns
- Factory functions: `create_*(llm)` returns a closure that takes `AgentState` and returns updated state
- LLM invocation: `llm.invoke([SystemMessage(...), HumanMessage(...)])` via LangChain
- Options agents in `agents/options/` provide the closest pattern for a new agent subdirectory
- `quick_thinking_llm` used for cost-efficient agents (per RANK-01)

### Integration Points
- Phase 8: `tradingagents/dataflows/screener_data.py` provides `get_screener_signals()` returning `list[ScreenerCandidate]`
- `tradingagents/agents/__init__.py` — re-exports all `create_*` factories
- Phase 10 (downstream): API endpoint will call `run_screener()` directly

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
