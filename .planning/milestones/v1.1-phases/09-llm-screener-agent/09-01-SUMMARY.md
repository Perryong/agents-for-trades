---
phase: 09-llm-screener-agent
plan: 01
subsystem: screener-agent
tags: [llm, screener, pydantic, tdd, rank]
dependency_graph:
  requires:
    - "tradingagents/dataflows/screener_data.py (ScreenerCandidate, get_screener_signals)"
    - "langchain_core.prompts (ChatPromptTemplate)"
  provides:
    - "tradingagents/agents/screener/screener_agent.py (TopPick, ScreenerResult, create_screener_agent, run_screener)"
    - "tradingagents/agents/screener/__init__.py (re-exports)"
  affects:
    - "tradingagents/agents/__init__.py (create_screener_agent added to exports)"
tech_stack:
  added:
    - "None — uses existing langchain_core, pydantic, json, re (stdlib)"
  patterns:
    - "create_* factory pattern (same as volatility_analyst.py)"
    - "Pydantic BaseModel for structured LLM output"
    - "ChatPromptTemplate.from_messages for LLM prompt construction"
    - "TDD: RED (tests only) -> GREEN (implementation) -> committed separately"
key_files:
  created:
    - "tradingagents/agents/screener/screener_agent.py"
    - "tradingagents/agents/screener/__init__.py"
    - "tests/agents/test_screener_agent.py"
  modified:
    - "tradingagents/agents/__init__.py"
decisions:
  - "Returned picks list from _parse_screener_response (not ScreenerResult) so caller assembles metadata — avoids duplicate model construction"
  - "STRICT_PROMPT_PREFIX avoids curly braces to prevent LangChain template variable interpolation errors"
  - "Fixed mock LLM pattern to use mock_llm.return_value = mock_response (LangChain calls LLM as callable in RunnableSequence)"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-02"
  tasks_completed: 2
  files_created: 3
  files_modified: 1
---

# Phase 9 Plan 1: LLM Screener Agent Summary

**One-liner:** LLM screener agent with TopPick/ScreenerResult Pydantic models, create_screener_agent factory, retry + graceful degradation for malformed JSON, and AgentState isolation guard.

## Objective

Build the LLM screener agent module that ranks pre-filtered stock candidates using an LLM, producing top 3-5 picks with rationale and confidence scores. Bridges Phase 8's data layer (ScreenerCandidate) with Phase 10's API endpoint.

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Create Pydantic models and test scaffolds (TDD) | b5e491a (RED), bf0bedc (GREEN) | Done |
| 2 | Wire screener agent into agents/__init__.py | 2a07fe7 | Done |

## What Was Built

### Models

- `TopPick(BaseModel)`: ticker, score (0-1), rationale, confidence (0-1), key_metrics dict, optional sector/market_cap fields
- `ScreenerResult(BaseModel)`: picks list, screened_at (UTC datetime), candidate_count, model_used, optional error field

### Functions

- `_format_candidates_for_prompt(candidates)`: projects each ScreenerCandidate to ticker + composite/volume/momentum scores as numbered list; omits DataFrames and coverage_note
- `_parse_screener_response(content, n_picks)`: strips markdown fences via regex, parses JSON, validates TopPick list; returns None on any failure
- `create_screener_agent(llm)`: factory returning closure; reads n_picks from config; retries once with stricter prompt on parse failure; degrades to composite-score auto-selection on second failure
- `run_screener(config, llm)`: calls get_screener_signals, creates agent, validates ScreenerResult type, returns result
- `_validate_not_agent_state(obj)`: raises TypeError if dict contains AgentState sentinel keys

### Test Suite

7 unit tests in `tests/agents/test_screener_agent.py` (all pass):
1. `test_factory_returns_callable` — RANK-01
2. `test_factory_closure_accepts_candidates` — RANK-01
3. `test_run_screener_returns_top_picks` — RANK-02 (mocked get_screener_signals)
4. `test_top_pick_fields_present` — RANK-04
5. `test_screener_result_raises_on_pipeline_entry` — RANK-03
6. `test_top_pick_json_structure` — RANK-04
7. `test_malformed_json_graceful_degradation` — RANK-04

## Verification Results

```
uv run pytest tests/agents/test_screener_agent.py -x -q
7 passed in 1.81s

uv run pytest tests/ -q --ignore=tests/api/test_routes.py
189 passed in 3.90s

python -c "from tradingagents.agents import create_screener_agent; print('OK')"
OK

python -c "from tradingagents.agents.screener import run_screener, TopPick, ScreenerResult; print('OK')"
OK
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mock LLM pattern incompatible with LangChain RunnableSequence**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan's suggested mock used `mock_llm.__or__ = lambda self, other: self` which doesn't intercept `prompt | llm` correctly — LangChain's `ChatPromptTemplate.__or__` creates a RunnableSequence, which then calls `llm.invoke(messages)`. The `__or__` override was on the instance (not the class) so Python's dunder dispatch used the LLM class's own `__or__`, not the instance override. Result: `result.content` was a MagicMock, not the intended string.
- **Fix:** Changed mock to use `mock_llm.return_value = mock_response` (callable path) + `mock_llm.invoke = MagicMock(return_value=mock_response)`. This matches the pattern used in `test_volatility_analyst.py`.
- **Files modified:** `tests/agents/test_screener_agent.py`
- **Commit:** bf0bedc

**2. [Rule 1 - Bug] STRICT_PROMPT_PREFIX contained literal curly braces causing LangChain KeyError**
- **Found during:** Task 1 GREEN phase (test_malformed_json_graceful_degradation)
- **Issue:** `STRICT_PROMPT_PREFIX` contained `'{' and end with '}'` — LangChain's `ChatPromptTemplate` treats `{...}` as template variable placeholders. This caused a KeyError when the strict retry prompt was built.
- **Fix:** Replaced `'{'` and `'}'` with plain English "curly brace" in the prefix string.
- **Files modified:** `tradingagents/agents/screener/screener_agent.py`
- **Commit:** bf0bedc

**3. [Rule 1 - Bug] Retry used wrong prompt variable**
- **Found during:** Code review during GREEN phase
- **Issue:** First retry attempt used `prompt` (original) instead of `strict_prompt` (stricter prefix).
- **Fix:** Changed `(prompt | llm).invoke({})` to `(strict_prompt | llm).invoke({})` in retry path.
- **Files modified:** `tradingagents/agents/screener/screener_agent.py`
- **Commit:** bf0bedc

## Known Stubs

None — all data flows are wired. The `get_screener_signals` function is called live (mocked only in tests). The LLM is caller-supplied (no hardcoded fallback).

## Self-Check: PASSED

All files found and all commits exist:
- tradingagents/agents/screener/screener_agent.py: FOUND
- tradingagents/agents/screener/__init__.py: FOUND
- tests/agents/test_screener_agent.py: FOUND
- Commit b5e491a (RED tests): FOUND
- Commit bf0bedc (GREEN implementation): FOUND
- Commit 2a07fe7 (Task 2 wiring): FOUND
