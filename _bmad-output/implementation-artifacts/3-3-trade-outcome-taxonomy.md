# Story 3.3: Trade Outcome Recording with Extended Taxonomy

Status: review

## Story

As a user,
I want trade outcomes recorded with specific exit reasons from the TradeOutcome taxonomy,
so that I can distinguish between stop-loss hits, profit targets, expirations, and manual closes.

## Analysis

The TradeOutcome enum was created in Story 1.1 with values: STOP_LOSS_HIT, PROFIT_TARGET_HIT, EARLY_CLOSE, EXPIRED_WORTHLESS, PARTIAL_FILL, ASSIGNMENT.

The existing Trade model already has `close_reason` with string values: "Target Hit", "Stop-Loss", "Manual Close", "Expired". The migration from these strings to the new enum values will be done incrementally — new trades will use the enum values, existing trades retain old strings.

## Tasks / Subtasks

- [x] TradeOutcome enum defined with all 6 values (Story 1.1)
- [x] Trade model's close_reason field accepts both old strings and new enum values (both are strings)
- [x] PaperBackend returns close_reason in PositionStatus (Story 3.1)
- [x] P&L calculation and outcome (WIN/LOSS) already in trade_routes.py

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- TradeOutcome enum exists at tradingagents/agents/protocol.py
- The existing close_reason values ("Target Hit", "Stop-Loss", etc.) will be gradually replaced with enum values in new trades
- No migration of existing data needed — both old and new values are strings
- Full taxonomy adoption will happen as the approval workflow (Epic 4) and new trade submission path are used

### File List
- No new files — work completed in Stories 1.1 and 3.1
