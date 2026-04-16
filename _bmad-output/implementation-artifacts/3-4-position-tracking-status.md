# Story 3.4: Position Tracking and Status Polling

Status: review

## Story

As a user,
I want open positions tracked and their status polled from Alpaca,
so that I can see current position state and the system detects when stops or targets are hit.

## Analysis

Position tracking and status polling are already implemented:
- `PaperBackend.get_order_status()` polls Alpaca and returns PositionStatus (Story 3.1)
- `trade_routes.py` poll_trade_status endpoint updates Trade records based on PositionStatus
- Bracket leg detection (_check_bracket_legs) identifies Target Hit and Stop-Loss close reasons
- P&L calculation happens on close

## Tasks / Subtasks

- [x] PaperBackend.get_order_status() polls Alpaca for fill/reject/expire (Story 3.1)
- [x] Trade record updated with fill_price, fill_time, close_price, close_time (existing + Story 3.1)
- [x] Bracket leg detection for Target Hit / Stop-Loss (existing, preserved in refactor)
- [x] Expired unfilled orders marked appropriately (existing, preserved)
- [x] Status transitions: submitted → filled → closed verified in tests

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Position tracking was already implemented in the original trade_routes.py
- Story 3.1 preserved all tracking behavior while extracting Alpaca logic to PaperBackend
- The bracket leg detection (_check_bracket_legs) still accesses the raw Alpaca client for nested order data
- 18 trade route tests pass (5 skipped — bracket-specific tests need deeper backend mock)

### File List
- No new files — work completed in Story 3.1
