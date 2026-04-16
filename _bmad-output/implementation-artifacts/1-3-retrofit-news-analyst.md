# Story 1.3: Retrofit News Analyst with Structured Output

Status: review

## Story

As a user,
I want the news analyst to produce a validated AgentSignal,
so that news sentiment is reliably consumed by the risk judge.

## Acceptance Criteria

1. News analyst returns validated AgentSignal with all required fields
2. Invalid LLM output raises AgentProtocolError with ticker and agent_name
3. news_report string and vol_note_news preserved for backward compatibility
4. New news_signal state key contains serialized AgentSignal dict
5. Existing tests pass — no regressions

## Tasks / Subtasks

- [x] All tasks completed — same pattern as Story 1.2 using shared signal_extraction utility

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Retrofitted news_analyst.py with STRUCTURED_OUTPUT_INSTRUCTION and parse_agent_signal
- Added news_signal to AgentState
- Tests in test_analyst_structured_output.py cover valid signal and missing JSON error cases

### File List
- `tradingagents/agents/analysts/news_analyst.py` (MODIFIED)
- `tradingagents/agents/utils/agent_states.py` (MODIFIED)
- `tests/agents/test_analyst_structured_output.py` (NEW — shared test module)
