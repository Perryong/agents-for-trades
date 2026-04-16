# Story 1.2: Retrofit Fundamentals Analyst with Structured Output

Status: review

## Story

As a user,
I want the fundamentals analyst to produce a validated AgentSignal,
so that its analysis is machine-readable and reliably consumed by the risk judge.

## Acceptance Criteria

1. The fundamentals analyst returns a validated `AgentSignal` with all required fields (signal_direction, confidence, time_horizon, evidence, data_freshness, valid_until)
2. The LLM is prompted to produce structured JSON output matching the `AgentSignal` schema
3. Invalid LLM output raises `AgentProtocolError` with ticker and agent_name context
4. The `fundamentals_report` state key still receives a string report for backward compatibility
5. The `vol_note_fundamentals` extraction continues to work
6. Existing tests pass — no regressions

## Tasks / Subtasks

- [x] Task 1: Add structured output prompt to fundamentals analyst (AC: #2)
  - [x] Added `_STRUCTURED_OUTPUT_INSTRUCTION` constant with JSON schema example appended to system prompt
  - [x] LLM produces prose report first, then appends fenced JSON block

- [x] Task 2: Parse structured output from LLM response (AC: #1, #3)
  - [x] Created `extract_agent_signal_json()` function with fenced block + fallback regex
  - [x] Validates against `AgentSignal` schema using constructor
  - [x] Raises `AgentProtocolError(message, ticker=ticker, agent_name="fundamentals")` on failure

- [x] Task 3: Maintain backward compatibility (AC: #4, #5)
  - [x] `fundamentals_report` still returned as string
  - [x] `vol_note_fundamentals` still extracted via `extract_vol_note()`
  - [x] New `fundamentals_signal` key contains serialized AgentSignal dict
  - [x] Tool call responses (intermediate steps) return None for signal

- [x] Task 4: Update AgentState to include signal field (AC: #1)
  - [x] Added `fundamentals_signal: Annotated[Optional[dict], _last_value]` to AgentState

- [x] Task 5: Write tests (AC: #1, #3, #6)
  - [x] 9 tests: valid signal, preserved report, vol note extraction, missing JSON error, tool call skip, JSON extraction helpers
  - [x] No regressions — 6 pre-existing failures in greeks/screener/config tests unrelated

## Dev Notes

### How the Fundamentals Analyst Works Today

`create_fundamentals_analyst(llm)` returns a closure `fundamentals_analyst_node(state)` that:
1. Reads `state["trade_date"]` and `state["company_of_interest"]` (ticker)
2. Optionally reads `state["vol_context"]` for volatility context
3. Constructs a `ChatPromptTemplate` with system message + tools
4. Calls `chain = prompt | llm.bind_tools(tools)` and invokes with `state["messages"]`
5. If no tool calls, extracts `result.content` as the report and `extract_vol_note(report)` for vol_note
6. Returns `{"messages": [result], "fundamentals_report": report, "vol_note_fundamentals": vol_note}`

The LLM may call tools (get_fundamentals, get_balance_sheet, etc.) first, then produce a final report. The report is only captured when `len(result.tool_calls) == 0` (the final response after tool use).

### Structured Output Strategy

**Approach: Prompt-based JSON extraction (not LLM structured output mode)**

The analyst uses `llm.bind_tools(tools)` which means the LLM makes tool calls first, then produces a final text response. We cannot use LLM-native structured output mode (like OpenAI's `response_format`) because the agent needs to call tools first.

**Strategy:**
1. Add instructions to the system prompt asking the LLM to append a ````json` block at the end of its report with the AgentSignal fields
2. Parse the JSON block from the response content using a regex or string split
3. Validate against `AgentSignal` schema
4. Keep the prose report as `fundamentals_report` for backward compatibility

**JSON extraction pattern:**
```python
import json
import re

def extract_agent_signal_json(content: str) -> dict:
    """Extract JSON block from LLM response content."""
    # Look for ```json ... ``` block
    match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Fallback: try to find raw JSON object at end of content
    match = re.search(r'(\{[^{]*"signal_direction"[^}]*\})\s*$', content, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError("No AgentSignal JSON block found in response")
```

### Critical: What NOT to Do

- Do NOT change the tool binding or tool calling behavior — tools must still work
- Do NOT remove the prose report — `fundamentals_report` must still be a string for downstream consumers (research manager, bull/bear researchers)
- Do NOT modify `vol_note_utils.py` — vol_note extraction continues as-is
- Do NOT modify other analyst files (news, market, social) — those are Stories 1.3-1.5
- Do NOT modify `protocol.py` or `exceptions.py` — those are done (Story 1.1)
- Do NOT try to use LLM structured output mode — it's incompatible with tool use

### State Key Convention

The new `fundamentals_signal` key stores a `dict` (not an `AgentSignal` instance) because LangGraph state uses TypedDict which requires JSON-serializable values. Store via `signal.model_dump(mode="json")`.

### Architecture Compliance

- Import `AgentSignal` from `tradingagents.agents.protocol`
- Import `AgentProtocolError` from `tradingagents.exceptions`
- snake_case for all new functions and variables
- New state key follows existing pattern: `fundamentals_signal` alongside `fundamentals_report`

### Previous Story Intelligence (Story 1.1)

- `AgentSignal` is at `tradingagents/agents/protocol.py` with fields: signal_direction (Literal), confidence (0-100), time_horizon (Literal), evidence (list[str]), data_freshness (datetime), valid_until (datetime)
- `AgentProtocolError` is at `tradingagents/exceptions.py` with optional `ticker` and `agent_name` kwargs
- Pydantic v2 — use `model_validate()` or constructor, not v1 patterns

### Testing Strategy

Mock the LLM to return controlled responses. The test should NOT make real LLM calls.

```python
# Pattern for mocking:
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

def make_mock_response(content, tool_calls=None):
    msg = MagicMock(spec=AIMessage)
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg
```

Test both the happy path (valid JSON in response) and the error path (missing/malformed JSON).

### Project Structure Notes

- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Modify: `tradingagents/agents/utils/agent_states.py` (add `fundamentals_signal` key)
- Create: `tests/agents/test_fundamentals_analyst.py`

### References

- [Source: tradingagents/agents/analysts/fundamentals_analyst.py — current implementation]
- [Source: tradingagents/agents/utils/agent_states.py — AgentState definition]
- [Source: tradingagents/agents/protocol.py — AgentSignal schema (Story 1.1)]
- [Source: tradingagents/exceptions.py — AgentProtocolError (Story 1.1)]
- [Source: tradingagents/agents/utils/vol_note_utils.py — vol note extraction]
- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Output Protocol]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation.

### Completion Notes List

- Retrofitted `fundamentals_analyst.py` with structured output: LLM now appends a fenced JSON block matching `AgentSignal` schema
- Created `extract_agent_signal_json()` utility function with fenced block regex + raw JSON fallback
- Backward compatible: `fundamentals_report` (string), `vol_note_fundamentals` (string), and new `fundamentals_signal` (dict) all returned
- Tool call responses (intermediate LLM steps) skip signal extraction — `fundamentals_signal` is None until final response
- Added `fundamentals_signal` to `AgentState` in `agent_states.py`
- 9 new tests, all passing. 78 total related tests pass. No regressions from our changes.

### File List

- `tradingagents/agents/analysts/fundamentals_analyst.py` (MODIFIED)
- `tradingagents/agents/utils/agent_states.py` (MODIFIED — added fundamentals_signal)
- `tests/agents/test_fundamentals_analyst.py` (NEW)
