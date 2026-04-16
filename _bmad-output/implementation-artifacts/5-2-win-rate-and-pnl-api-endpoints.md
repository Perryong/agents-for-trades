# Story 5.2: Win Rate and P&L API Endpoints

Status: review

## Story

As a user,
I want API endpoints that return win rate and P&L metrics over configurable time periods,
so that the frontend can display my performance from day one.

## Acceptance Criteria

1. GET /api/scores/summary accepts optional `period` query param (7d, 4w, 30d)
2. GET /api/scores/rolling returns rolling weekly win rate time series
3. Disclaimer included when fewer than 5 closed trades

## Tasks / Subtasks

- [x] Task 1: Add `period` query param to GET /api/scores/summary
  - [x] Parse period strings: '7d', '4w', '30d' into datetime cutoff
  - [x] Filter trades by close_time > cutoff before computing metrics
- [x] Task 2: Create GET /api/scores/rolling endpoint
  - [x] Returns weekly win rate for last N weeks (default 4)
  - [x] Each week: week_start, win_rate, trade_count, wins, losses
  - [x] Disclaimer when total_closed < 5
- [x] Task 3: Verify imports and endpoint loads
  - [x] Backend module imports clean

## Dev Notes

Extended existing `api/score_routes.py` with period filtering on summary and new rolling endpoint.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Added _parse_period() helper for '7d'/'4w'/'30d' period strings
- GET /api/scores/summary now accepts optional `period` query param
- New GET /api/scores/rolling returns weekly win rate for last N weeks
- RollingWeekPoint and RollingWinRateResponse schemas defined inline
- Disclaimer included when total_closed < 5

### Change Log

- 2026-04-15: Story 5.2 implemented — period filtering + rolling win rate endpoint

### File List

- `api/score_routes.py` — MODIFIED: Added period param to summary, new rolling endpoint
