# Story 2.2: No-Trade Decision Logic

Status: review

## Story

As a user,
I want the risk judge to produce a documented no-trade decision when conditions don't meet thresholds,
so that I understand why the system chose not to trade and trust that capital is being preserved.

## Tasks / Subtasks

- [x] Created `_should_skip_trade()` — checks aggregated confidence against threshold
- [x] Created `_build_no_trade_summary()` — builds human-readable evaluation summary
- [x] No-trade already handled in 2.1: HOLD/no-JSON → no_trade_reason populated
- [x] 7 tests in test_no_trade_logic.py, all passing

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Added `_should_skip_trade()` and `_build_no_trade_summary()` to risk_manager.py
- These functions enable pre-LLM confidence checking and per-ticker evaluation summaries
- Core no-trade mechanism (HOLD = no JSON = no-trade recommendation) was implemented in Story 2.1

### File List
- `tradingagents/agents/managers/risk_manager.py` (MODIFIED — added 2 functions)
- `tests/agents/test_no_trade_logic.py` (NEW — 7 tests)
