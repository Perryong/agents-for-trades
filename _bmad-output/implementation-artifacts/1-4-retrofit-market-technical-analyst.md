# Story 1.4: Retrofit Market/Technical Analyst with Structured Output

Status: review

## Story

As a user,
I want the market/technical analysts to produce validated AgentSignals,
so that technical analysis is reliably consumed by the risk judge.

## Acceptance Criteria

1. Both market and technical analysts return validated AgentSignal
2. Invalid output raises AgentProtocolError with ticker and agent_name
3. market_report, technical_report, vol_notes preserved for backward compatibility
4. New market_signal and technical_signal state keys contain serialized AgentSignal dicts
5. Technical analyst (no tool binding) always produces signal — no tool_calls check needed
6. Existing tests pass — no regressions

## Tasks / Subtasks

- [x] All tasks completed — same pattern using shared signal_extraction utility
- [x] Market analyst: vol_note extraction preserved outside if block (original behavior)
- [x] Technical analyst: uses prompt | llm (no bind_tools), always produces report + signal

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Retrofitted market_analyst.py and technical_analyst.py with STRUCTURED_OUTPUT_INSTRUCTION and parse_agent_signal
- Market analyst preserves original behavior of extracting vol_note outside the tool_calls check
- Technical analyst has no tool binding — always produces report and signal (no conditional)
- Added market_signal and technical_signal to AgentState
- Tests in test_analyst_structured_output.py cover both analysts

### File List
- `tradingagents/agents/analysts/market_analyst.py` (MODIFIED)
- `tradingagents/agents/analysts/technical_analyst.py` (MODIFIED)
- `tradingagents/agents/utils/agent_states.py` (MODIFIED)
- `tests/agents/test_analyst_structured_output.py` (NEW — shared test module)
