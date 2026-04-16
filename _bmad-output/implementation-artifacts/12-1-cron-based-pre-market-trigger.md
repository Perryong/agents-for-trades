# Story 12-1: Cron-Based Pre-Market Trigger

**Epic:** 12 - Pre-Market Automation
**Status:** review

## Description
PreMarketScheduler class with configurable schedule_time, market calendar integration, and threading.Timer-based scheduling. Skips non-trading days. Runs as daemon thread.

## Acceptance Criteria
- PreMarketScheduler accepts configurable schedule_time (default 08:30 ET)
- Integrates with market calendar to skip weekends and holidays
- Uses threading.Timer for next-run scheduling
- Daemon thread — does not block process exit
- Logs each scheduled/skipped trigger with reason

## Technical Notes
- Use `exchange_calendars` or similar for NYSE trading day lookup
- Timer re-arms after each trigger fires
- Graceful shutdown via cancel() on the active timer

## Files
| File | Action |
|------|--------|
| `tradingagents/services/scheduler.py` | NEW |
