# Story 5.3: Basic Performance Display in Frontend

Status: review

## Story

As a user,
I want to see my win rate and P&L metrics in the app,
so that I can assess whether the system is profitable from the first week.

## Acceptance Criteria

1. Win rate displayed prominently (32px mono, green ≥70%, amber 50-69%, red <50%)
2. Rolling 4-week win rate shown from /api/scores/rolling
3. "Need more trades for reliable metrics" when < 5 closed trades
4. All numbers use monospace font, positive green, negative red

## Tasks / Subtasks

- [x] Task 1: Add RollingWinRateData types to types.ts
- [x] Task 2: Add useRollingWinRate hook to useDashboard.ts
- [x] Task 3: Add win rate hero section to TrackRecordScreen
  - [x] 32px mono bold win rate with threshold coloring
  - [x] Rolling 4-week mini display with weekly values
  - [x] "Need more trades" message when total_closed < 5
- [x] Task 4: Update existing Win Rate StatCard color thresholds (≥70% green, 50-69% amber, <50% red)
- [x] Task 5: Build verification — tsc + vite: zero errors

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Added RollingWeekPoint + RollingWinRateData types
- Added useRollingWinRate hook (fetches GET /api/scores/rolling?weeks=4)
- Added prominent win rate hero (32px mono) with threshold-based coloring
- Added rolling 4-week mini display showing weekly win rates
- Added "Need more trades" warning when total_closed < 5
- Updated StatCard win rate color: ≥70% green, 50-69% amber, <50% red
- Build clean

### Change Log

- 2026-04-15: Story 5.3 implemented — win rate hero, rolling display, threshold coloring

### File List

- `frontend/src/types.ts` — MODIFIED: Added RollingWeekPoint, RollingWinRateData types
- `frontend/src/hooks/useDashboard.ts` — MODIFIED: Added useRollingWinRate hook
- `frontend/src/components/TrackRecordScreen.tsx` — MODIFIED: Win rate hero, rolling display, threshold colors
