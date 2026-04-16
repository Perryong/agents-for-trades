# Story 1.5: Retrofit Social Media Analyst with Structured Output

Status: review

## Story

As a user,
I want the social media analyst to produce a validated AgentSignal,
so that social sentiment is reliably consumed by the risk judge.

## Acceptance Criteria

1. Social analyst returns validated AgentSignal with all required fields
2. Invalid output raises AgentProtocolError with ticker and agent_name
3. sentiment_report and vol_note_social preserved for backward compatibility
4. New social_signal state key contains serialized AgentSignal dict
5. Existing tests pass — no regressions

## Tasks / Subtasks

- [x] All tasks completed — same pattern using shared signal_extraction utility

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Retrofitted social_media_analyst.py with STRUCTURED_OUTPUT_INSTRUCTION and parse_agent_signal
- Added social_signal to AgentState
- Tests in test_analyst_structured_output.py cover valid signal and missing JSON error cases

### File List
- `tradingagents/agents/analysts/social_media_analyst.py` (MODIFIED)
- `tradingagents/agents/utils/agent_states.py` (MODIFIED)
- `tests/agents/test_analyst_structured_output.py` (NEW — shared test module)
