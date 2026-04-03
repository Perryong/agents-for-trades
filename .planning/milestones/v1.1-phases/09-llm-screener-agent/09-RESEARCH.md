# Phase 9: LLM Screener Agent - Research

**Researched:** 2026-04-02
**Domain:** LangChain single-pass LLM agent, Pydantic structured output, AgentState isolation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Agent Architecture**
- Use JSON mode with Pydantic validation for structured LLM output — prompt asks for JSON array, parse with `ScreenerResult.model_validate()`
- Handle malformed LLM responses by retrying once with stricter prompt, then returning partial results with error flag for graceful degradation
- Single-shot prompt with all candidates (≤50) plus scoring rubric — keeps token count manageable
- Pass pre-summarized metrics per ticker (score, volume ratio, momentum, sector) to the LLM, not raw DataFrames

**ScreenerResult Data Model**
- Configurable number of picks, default 5, hard cap at 10
- Confidence scale: 0.0-1.0 float
- Key metrics per pick: volume_ratio, momentum_5d, sector, market_cap
- ScreenerResult includes metadata: screened_at timestamp, candidate_count, model_used

**Isolation & Integration**
- Agent lives in `tradingagents/agents/screener/screener_agent.py` — new subdirectory consistent with `agents/options/`, `agents/analysts/` pattern
- AgentState isolation enforced via validation at `run_screener()` entry — raise TypeError if ScreenerResult passed to pipeline (per RANK-03)
- Import `get_screener_signals` from `screener_data.py` directly for data integration (not via route_to_vendor)

### Claude's Discretion
- Exact prompt wording and scoring rubric content
- LLM temperature setting for ranking
- Internal helper function organization

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RANK-01 | `create_screener_agent` factory follows existing `create_*` pattern, uses `quick_thinking_llm` for cost control | Factory pattern is well-established in codebase; `quick_thinking_llm` is `config["quick_think_llm"]` resolved via `create_llm_client()` |
| RANK-02 | LLM ranker accepts pre-filtered candidates (hard cap 50) and returns top 3-5 picks with rationale and confidence score | Single-shot prompt pattern verified in `volatility_analyst.py`; JSON mode with Pydantic `model_validate()` confirmed working |
| RANK-03 | Screener output uses dedicated `ScreenerResult` model — never written to `AgentState` | `AgentState` is a TypedDict (`MessagesState` subclass) — adding a non-declared key raises no error at assignment, so the guard must be a `run_screener()` entry check that raises `TypeError` explicitly |
| RANK-04 | Structured JSON output per pick: ticker, score, rationale, key metrics (volume, momentum, sector) | Pydantic `BaseModel` used throughout codebase (`ScreenerCandidate` in Phase 8); `TopPick` model uses same pattern |
</phase_requirements>

---

## Summary

Phase 9 builds a standalone LLM agent that takes the `list[ScreenerCandidate]` from Phase 8's `get_screener_signals()` and returns a `ScreenerResult` containing ranked top picks with rationale. The agent is fully isolated from the analysis pipeline's `AgentState`.

The codebase has a mature, consistent pattern for single-pass LLM agents (established in the options pipeline: `volatility_analyst.py`, `options_strategy_selector.py`). The screener agent follows the same structure: `create_screener_agent(llm)` factory returns a callable, Python prepares the data context, one `(prompt | llm).invoke({})` call produces output, Pydantic validates the JSON response. The critical novelty of this phase is (1) JSON array output rather than freeform prose, and (2) the `run_screener()` top-level entry point that is not a LangGraph node but a standalone callable — which also enforces the `ScreenerResult`/`AgentState` isolation guarantee.

The factory signature diverges from existing agents in one important way: the returned closure accepts `(config, llm)` as named parameters (per the success criteria `run_screener(config, llm)`) rather than an `AgentState` dict. This is intentional — the screener agent is never wired into a LangGraph `StateGraph`; it is called directly by the API (Phase 10) and CLI (Phase 12).

**Primary recommendation:** Model the implementation on `volatility_analyst.py` (single-pass, no tools, `(prompt | llm).invoke({})`), add a Pydantic `ScreenerResult` + `TopPick` model, and wrap everything in a `run_screener(config, llm)` entry point with a `TypeError` guard.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.x (transitive via langchain-core) | `ScreenerResult` and `TopPick` models; `model_validate()` for JSON parsing | Already used in codebase (`ScreenerCandidate` in Phase 8) |
| langchain-core | >=0.3.81 | `ChatPromptTemplate`, `SystemMessage`, `HumanMessage`, LLM invocation | Project-wide LangChain standard |
| langchain-openai | >=0.3.23 | `ChatOpenAI` / `UnifiedChatOpenAI` for LLM backend | Already the primary LLM client |
| json (stdlib) | stdlib | `json.loads()` for raw LLM response parsing before Pydantic validation | No additional install |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime (stdlib) | stdlib | `screened_at` timestamp in `ScreenerResult` | Always — metadata field |
| typing (stdlib) | stdlib | `Optional`, `List` type hints | Throughout model definitions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual JSON parse + Pydantic | `.with_structured_output(ScreenerResult)` | `with_structured_output` requires provider support for function-calling/JSON schema mode; manual parse + retry gives more control over the partial-result degradation path and is consistent with the codebase's existing patterns |
| `ChatPromptTemplate` | `SystemMessage` + `HumanMessage` directly | Either works; `ChatPromptTemplate.from_messages` is the codebase standard |

**Installation:** No new packages required. All dependencies are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

```
tradingagents/agents/screener/
├── __init__.py              # re-exports create_screener_agent, run_screener
└── screener_agent.py        # all implementation: models + factory + entry point

tests/agents/
└── test_screener_agent.py   # unit tests (Wave 0 gap)
```

Also update:
```
tradingagents/agents/__init__.py   # add create_screener_agent import + __all__ entry
```

### Pattern 1: Single-Pass LLM Agent Factory

This is the established codebase pattern for agents that compute data in Python and make one LLM call for the structured output. The screener agent follows it exactly.

**What:** `create_screener_agent(llm)` returns a closure. The closure serializes candidates to a JSON-friendly string, builds a `ChatPromptTemplate`, calls `(prompt | llm).invoke({})`, parses `result.content` as JSON, and validates with `ScreenerResult.model_validate()`.

**When to use:** Any agent that does not need tool calls or multi-turn messages.

**Example (from `volatility_analyst.py`):**
```python
# Source: tradingagents/agents/options/volatility_analyst.py
def create_volatility_analyst(llm):
    def volatility_analyst_node(state: dict) -> dict:
        # ... Python computation ...
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", data_content),
        ])
        result = (prompt | llm).invoke({})
        return {"volatility_report": result.content}
    return volatility_analyst_node
```

For the screener agent the pattern adapts slightly: the closure does not read from `AgentState` and does not return a state update dict. Instead it returns a `ScreenerResult` directly (or raises `TypeError` if given one to validate as state).

### Pattern 2: Pydantic Model for Structured Output

**What:** Define `TopPick(BaseModel)` and `ScreenerResult(BaseModel)`. After getting `result.content` from the LLM, call `json.loads()` then `ScreenerResult.model_validate(parsed)`. If that raises `ValidationError`, retry once with stricter prompt.

**Example (modeled after `ScreenerCandidate` in `screener_data.py`):**
```python
# Source: tradingagents/dataflows/screener_data.py
class ScreenerCandidate(BaseModel):
    ticker: str
    volume_score: float
    momentum_score: float
    unusual_activity_score: float
    composite_score: float
    rank: int
    coverage_note: Optional[str] = None
```

The `TopPick` and `ScreenerResult` models follow the same structure.

### Pattern 3: `run_screener()` Entry Point with Isolation Guard

**What:** `run_screener(config, llm)` is the public API. It (1) calls `get_screener_signals()` directly, (2) instantiates the inner agent closure via `create_screener_agent(llm)`, (3) enforces that `ScreenerResult` is never an `AgentState` by raising `TypeError` if a caller passes one to the pipeline.

The guard is implemented at the function boundary, not inside the LangGraph state machine. Since `AgentState` is a TypedDict, a `ScreenerResult` object simply cannot be assigned to a valid `AgentState` key (TypedDicts do not dynamically accept unknown keys at runtime in a meaningful way). The `TypeError` guard makes this explicit and testable.

```python
# Guard pattern
def run_screener(config: dict, llm) -> ScreenerResult:
    candidates, coverage = get_screener_signals(
        max_candidates=config.get("screener_max_candidates", 50)
    )
    agent = create_screener_agent(llm)
    result = agent(candidates, config)
    # Ensure result is never confused with AgentState
    if not isinstance(result, ScreenerResult):
        raise TypeError(
            f"run_screener must return ScreenerResult, got {type(result)}"
        )
    return result
```

### Pattern 4: Single-Retry Degradation for Malformed JSON

**What:** First attempt parses raw LLM response as JSON. On `json.JSONDecodeError` or `pydantic.ValidationError`, retry once with a stricter prompt that demands exactly-shaped JSON. If the retry also fails, return a `ScreenerResult` with an `error` flag and whatever partial picks could be extracted.

**When to use:** Required — success criterion 4 explicitly demands graceful degradation.

```python
def _parse_screener_response(content: str, n_picks: int) -> ScreenerResult | None:
    try:
        data = json.loads(content)
        return ScreenerResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None  # triggers retry
```

### Anti-Patterns to Avoid

- **Writing ScreenerResult to AgentState:** `AgentState` is a `MessagesState` TypedDict with declared fields only. Adding an undeclared key silently fails in LangGraph — it won't raise, just won't propagate. The `TypeError` guard in `run_screener()` makes the boundary explicit.
- **Using `bind_tools` or `MessagesPlaceholder`:** The screener agent is single-pass, no tools, no conversation history. Adding these adds latency and cost for no benefit.
- **Passing raw DataFrames to the LLM:** The context decision is to pass pre-summarized metrics (score, volume_ratio, momentum_5d, sector, market_cap) — not raw OHLCV DataFrames. Serialize `ScreenerCandidate` fields only.
- **Hardcoding the number of picks:** `n_picks` must be configurable via `config` with default 5, hard cap 10.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output validation | Custom regex parser | `pydantic.BaseModel.model_validate()` | Handles nested types, type coercion, optional fields, and produces clear error messages |
| JSON extraction from LLM response | String slicing / regex | `json.loads()` + `model_validate()` | Handles whitespace, escaped chars, nested objects |
| LLM client instantiation | Direct `ChatOpenAI(...)` | `create_llm_client()` from `tradingagents/llm_clients/factory.py` | Handles provider routing, GPT-5 temperature stripping, callback injection |
| Retry logic | Custom sleep loop | Single retry with prompt reformulation then partial result | LLM JSON failures are rare; a single retry is sufficient and keeps latency low |

**Key insight:** The "hard" part of this agent is not the LLM call — it is the clean separation between `ScreenerResult` and `AgentState`. Everything else is a direct application of existing patterns.

---

## Common Pitfalls

### Pitfall 1: LLM Returns Prose Instead of JSON

**What goes wrong:** The LLM ignores the JSON-only instruction and returns explanatory text wrapping the JSON, or returns Markdown fences (` ```json ... ``` `).

**Why it happens:** `gpt-5-mini` and similar quick models sometimes add preamble ("Here is the ranked list:") before the JSON block, especially if the system prompt is not firm enough.

**How to avoid:** System prompt must open with "Respond with ONLY a JSON object — no preamble, no postamble, no markdown fences." In the retry, also strip Markdown fences with a regex before `json.loads()`.

**Warning signs:** `json.JSONDecodeError` on first character being `H` (for "Here") or backtick.

### Pitfall 2: `model_validate()` Fails on Integer Scores

**What goes wrong:** LLM returns `"score": 8` (integer 0-10) instead of `"score": 0.8` (float 0.0-1.0). Pydantic raises `ValidationError` if the field type is `float` and the value is outside the expected range.

**Why it happens:** LLMs often default to 1-10 scoring unless the prompt is explicit about the scale AND provides an example.

**How to avoid:** Scoring rubric in the prompt must say "score: float between 0.0 and 1.0 (e.g., 0.85 = strong pick)". Consider using `float` with `ge=0.0, le=1.0` in the Pydantic field definition with `Field(...)`.

**Warning signs:** `ValidationError: value is not a valid float` or scores consistently above 1.0.

### Pitfall 3: `ScreenerResult` Key Accidentally Enters AgentState

**What goes wrong:** A downstream caller (Phase 10 API endpoint) passes `ScreenerResult` where an `AgentState` dict is expected, causing silent type mismatch.

**Why it happens:** Both are plain Python objects; Python does not enforce this at call sites.

**How to avoid:** The `run_screener()` entry point validates its return is `ScreenerResult` and does NOT accept `AgentState` as input. The test suite includes a specific test that attempting to pass `ScreenerResult` through the pipeline entry raises `TypeError`.

**Warning signs:** Analysis pipeline receives empty or `None` for expected `AgentState` fields.

### Pitfall 4: Candidates Serialized with Too Much Data

**What goes wrong:** Passing all `ScreenerCandidate` fields (including raw `coverage_note`, all scores) to the LLM inflates the prompt unnecessarily and can confuse the ranking rubric.

**Why it happens:** Developer serializes the full Pydantic model instead of projecting to the relevant fields.

**How to avoid:** Create a helper `_format_candidates_for_prompt(candidates: list[ScreenerCandidate]) -> str` that projects to only: `ticker`, `composite_score`, `volume_ratio_score`, `momentum_score`. The `sector` and `market_cap` fields mentioned in the locked decisions are NOT present in `ScreenerCandidate` (Phase 8 output). These will need to be omitted or fetched separately. See Open Questions.

**Warning signs:** Prompt length unexpectedly long; LLM returns rankings based on non-relevant fields.

---

## Code Examples

### ScreenerCandidate Fields Available from Phase 8

```python
# Source: tradingagents/dataflows/screener_data.py
class ScreenerCandidate(BaseModel):
    ticker: str
    volume_score: float         # normalized [0, 1]
    momentum_score: float       # normalized [0, 1]
    unusual_activity_score: float  # normalized [0, 1]
    composite_score: float      # equal-weight mean of three scores
    rank: int                   # 1-indexed rank (1 = best)
    coverage_note: Optional[str] = None
    # NOTE: No sector or market_cap field — see Open Questions
```

### Factory Closure Shape (Target)

```python
# Modeled on: tradingagents/agents/options/volatility_analyst.py
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError
import json

def create_screener_agent(llm):
    def screener_agent(
        candidates: list[ScreenerCandidate],
        config: dict,
    ) -> ScreenerResult:
        n_picks = min(config.get("screener_n_picks", 5), 10)
        candidate_text = _format_candidates_for_prompt(candidates)
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", candidate_text),
        ])
        result = (prompt | llm).invoke({})
        parsed = _parse_screener_response(result.content, n_picks)
        if parsed is None:
            # Retry once with stricter prompt
            ...
        return parsed or _partial_result(candidates[:n_picks])
    return screener_agent
```

### AgentState Isolation Guard

```python
# run_screener is the public entry point — never wired into StateGraph
def run_screener(config: dict, llm) -> ScreenerResult:
    from tradingagents.dataflows.screener_data import get_screener_signals
    candidates, _ = get_screener_signals(
        max_candidates=config.get("screener_max_candidates", 50)
    )
    agent = create_screener_agent(llm)
    result = agent(candidates, config)
    if not isinstance(result, ScreenerResult):
        raise TypeError(
            f"Expected ScreenerResult, got {type(result).__name__}. "
            "ScreenerResult must never enter AgentState."
        )
    return result
```

### Mock LLM Pattern for Tests

```python
# Source pattern: tests/agents/test_volatility_analyst.py
def _make_mock_llm(content: str):
    mock_response = MagicMock()
    mock_response.content = content
    mock_llm = MagicMock()
    mock_llm.return_value = mock_response   # (prompt | llm)(messages) path
    mock_llm.invoke = MagicMock(return_value=mock_response)
    return mock_llm
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain `OutputParser` classes | Pydantic `model_validate()` directly | LangChain v0.2+ | OutputParser is still available but Pydantic direct validation is simpler and testable without mocking parsers |
| `llm.with_structured_output(schema)` | Manual JSON parse + Pydantic | Project convention (established in options pipeline) | `with_structured_output` is valid but couples to provider-specific JSON schema APIs; manual parse gives control over retry/degradation path |

---

## Open Questions

1. **`sector` and `market_cap` fields in TopPick**
   - What we know: The locked decision specifies `TopPick` key metrics include `volume_ratio`, `momentum_5d`, `sector`, `market_cap`. However, `ScreenerCandidate` (Phase 8 output) does NOT contain `sector` or `market_cap` — only `volume_score`, `momentum_score`, `unusual_activity_score`, `composite_score`, `rank`.
   - What's unclear: Should `sector` and `market_cap` be fetched from yfinance per candidate (adds latency and yfinance calls), or should they be `Optional[str] = None` fields in `TopPick` that the LLM is asked to infer/estimate (unreliable), or should the locked decision be treated as aspirational and omitted from `TopPick` for now?
   - Recommendation: Make `sector` and `market_cap` `Optional[str] = None` in `TopPick`. The LLM likely knows the sector/market cap for S&P 500 tickers from training data, but flag these as potentially stale. Do NOT make a yfinance call per candidate — that would undermine the "pre-summarized metrics" architectural decision.

2. **`create_screener_agent` vs. `run_screener` signatures**
   - What we know: RANK-01 requires `create_screener_agent` factory; success criterion says `run_screener(config, llm)`. Both must exist.
   - What's unclear: Does `create_screener_agent(llm)` return a closure that takes `(candidates, config)`, or does `run_screener` call `create_screener_agent(llm)` internally and the factory closure only takes `candidates`?
   - Recommendation: `create_screener_agent(llm)` returns a closure `(candidates: list[ScreenerCandidate], config: dict) -> ScreenerResult`. `run_screener(config, llm)` is a thin wrapper that calls `get_screener_signals()` then calls the agent closure. This keeps the factory testable in isolation.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.2 |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| Quick run command | `pytest tests/agents/test_screener_agent.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RANK-01 | `create_screener_agent(llm)` returns a callable | unit | `pytest tests/agents/test_screener_agent.py::test_factory_returns_callable -x` | Wave 0 |
| RANK-01 | Factory closure is not a LangGraph node (does not accept AgentState dict) | unit | `pytest tests/agents/test_screener_agent.py::test_factory_closure_accepts_candidates -x` | Wave 0 |
| RANK-02 | `run_screener(config, llm)` with 50 candidates returns `ScreenerResult` with 3-5 `TopPick` objects | unit | `pytest tests/agents/test_screener_agent.py::test_run_screener_returns_top_picks -x` | Wave 0 |
| RANK-02 | Result contains ticker, score, rationale, confidence per pick | unit | `pytest tests/agents/test_screener_agent.py::test_top_pick_fields_present -x` | Wave 0 |
| RANK-03 | `ScreenerResult` not in `AgentState` — passing to pipeline raises `TypeError` | unit | `pytest tests/agents/test_screener_agent.py::test_screener_result_raises_on_pipeline_entry -x` | Wave 0 |
| RANK-04 | JSON output includes ticker, score, rationale, key_metrics | unit | `pytest tests/agents/test_screener_agent.py::test_top_pick_json_structure -x` | Wave 0 |
| RANK-04 | Malformed JSON triggers retry then partial result (no crash) | unit | `pytest tests/agents/test_screener_agent.py::test_malformed_json_graceful_degradation -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/agents/test_screener_agent.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/agents/test_screener_agent.py` — covers RANK-01, RANK-02, RANK-03, RANK-04 (7 tests above)

---

## Sources

### Primary (HIGH confidence)
- Direct codebase reading — `tradingagents/agents/options/volatility_analyst.py` (single-pass LLM agent pattern)
- Direct codebase reading — `tradingagents/agents/options/options_strategy_selector.py` (ChatPromptTemplate pattern)
- Direct codebase reading — `tradingagents/dataflows/screener_data.py` (`ScreenerCandidate` model, `get_screener_signals()` API)
- Direct codebase reading — `tradingagents/agents/utils/agent_states.py` (`AgentState` TypedDict definition — confirms no `ScreenerResult` field exists)
- Direct codebase reading — `tradingagents/default_config.py` (`quick_think_llm` key)
- Direct codebase reading — `tradingagents/graph/trading_graph.py` (`quick_thinking_llm` instantiation via `create_llm_client()`)
- Direct codebase reading — `tests/agents/test_volatility_analyst.py` (mock LLM pattern, test structure)
- Direct codebase reading — `pyproject.toml` (pytest config, dependency versions)

### Secondary (MEDIUM confidence)
- Pydantic v2 `model_validate()` API — confirmed present via `ScreenerCandidate` usage in `screener_data.py` (Pydantic BaseModel import verified)

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in project; no new packages needed
- Architecture: HIGH — directly derived from two existing agents in the same codebase
- Pitfalls: HIGH — derived from reading actual LLM agent tests and the single open question about sector/market_cap fields which is flagged explicitly

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable patterns; only risk is LangChain API changes, unlikely within 30 days)
