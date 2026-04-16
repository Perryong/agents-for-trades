# Story 8.5: Market Calendar Service

Status: review

## Story
As a developer, I want a market calendar service using exchange_calendars so the system can determine trading days, market hours, and schedule operations around market open/close.

## Tasks / Subtasks
- [x] Task 1: Create tradingagents/services/ package with __init__.py
- [x] Task 2: Create MarketCalendar class wrapping exchange_calendars (XNYS)
- [x] Task 3: Implement methods — is_trading_day, market_open_time, market_close_time, next_trading_day, previous_trading_day, trading_days_in_range
- [x] Task 4: Write 13 tests covering weekdays, weekends, holidays (Christmas, New Year's, MLK Day), early closes, next/previous trading day logic

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- MarketCalendar wraps exchange_calendars XNYS (NYSE) exchange
- All six methods implemented with timezone-aware datetime handling
- 13 tests pass covering normal days, weekends, major holidays, and edge cases
### File List
- tradingagents/services/__init__.py (NEW)
- tradingagents/services/market_calendar.py (NEW)
- tests/services/__init__.py (NEW)
- tests/services/test_market_calendar.py (NEW)
