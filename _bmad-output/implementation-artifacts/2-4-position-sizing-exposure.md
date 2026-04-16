# Story 2.4: Position Sizing and Portfolio Exposure Limits

Status: review

## Story

As a user,
I want every recommendation to include risk-appropriate position sizing with portfolio exposure guardrails,
so that no single trade threatens my portfolio and total exposure stays within limits.

## Tasks / Subtasks

- [x] TradeSpec.position_size validated as gt=0 (Story 1.1)
- [x] TradeSpec.stop_loss validated relative to direction (BUY: below entry, SELL: above entry) (Story 1.1)
- [x] Risk manager prompt instructs LLM to include position sizing suggestion (% of portfolio) (Story 2.1)
- [x] _should_skip_trade() provides pre-LLM confidence gate (Story 2.2)
- [x] 4 tests in test_position_sizing.py verifying schema-level enforcement

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Position sizing is LLM-recommended and captured in TradeSpec.position_size
- Stop-loss is enforced at schema level — no TradeSpec can exist without valid stop_loss
- Portfolio exposure checking against open positions will be a runtime check in Epic 3 (execution backend) when actual portfolio state is available
- Schema-level guardrails are complete; runtime enforcement deferred to execution layer

### File List
- `tests/agents/test_position_sizing.py` (NEW — 4 tests)
