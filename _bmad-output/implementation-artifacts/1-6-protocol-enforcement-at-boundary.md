# Story 1.6: Protocol Enforcement at LLM Client Boundary

Status: review

## Story

As a developer,
I want the LLM client layer to support protocol validation and token tracking,
so that every agent response is validated before reaching the pipeline.

## Acceptance Criteria

1. The shared `parse_agent_signal()` utility validates every agent response against AgentSignal schema
2. Valid responses return AgentSignal instances; invalid responses raise AgentProtocolError with raw response context
3. Token usage for LLM calls is trackable via LangChain callbacks
4. Unit tests verify both valid and invalid response handling

## Analysis: What Was Already Implemented

Protocol enforcement is effectively complete from Stories 1.2-1.5:

- `tradingagents/agents/utils/signal_extraction.py` provides:
  - `STRUCTURED_OUTPUT_INSTRUCTION` — appended to every analyst's system prompt
  - `extract_agent_signal_json()` — extracts JSON from LLM response content
  - `parse_agent_signal()` — validates against AgentSignal schema, raises AgentProtocolError on failure
- All 5 analysts (fundamentals, news, market, technical, social) call `parse_agent_signal()` on every final response
- AgentProtocolError includes `ticker` and `agent_name` for debugging
- 25 tests cover valid and invalid response handling across all analysts

The LLM client layer (`factory.py`, `base_client.py`) returns raw LangChain LLM instances. The agents call `llm.bind_tools()` and invoke directly — protocol enforcement at the agent output boundary (via `parse_agent_signal`) is the correct architectural pattern for this tool-calling setup.

Token tracking is available via LangChain's built-in callback system (`callbacks` kwarg already supported in `OpenAIClient.get_llm()`). Per-run token tracking will be implemented in Epic 7 (Pipeline Resilience) when the `agent_results` table captures `token_count` per agent.

## Tasks / Subtasks

- [x] Task 1: Protocol enforcement via shared utility (completed in Stories 1.2-1.5)
  - [x] `parse_agent_signal()` validates every agent response at the boundary
  - [x] Invalid responses raise `AgentProtocolError` with ticker and agent_name
  - [x] All 5 analysts use the shared utility consistently

- [x] Task 2: Tests verify valid and invalid handling (completed in Stories 1.2-1.5)
  - [x] 25 tests across `test_fundamentals_analyst.py` and `test_analyst_structured_output.py`
  - [x] Tests cover: valid signal extraction, missing JSON error, invalid schema error

- [x] Task 3: Token tracking infrastructure exists (no changes needed)
  - [x] LangChain callbacks kwarg already supported in all LLM clients
  - [x] Per-agent token tracking deferred to Epic 7 (agent_results table)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Story was effectively completed by the shared signal_extraction utility created during Stories 1.2-1.5
- No additional code changes needed — the architectural decision to enforce at the agent output boundary (not the LLM client boundary) is correct for a tool-calling system
- Token tracking infrastructure exists via LangChain callbacks; per-run tracking deferred to Epic 7

### File List
- No new files — work completed in prior stories
